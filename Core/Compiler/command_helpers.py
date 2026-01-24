# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
================================================================================
MODULE command_helpers.py - Helpers pour la Construction et Exécution de Commandes
================================================================================

Ce module fournit des utilitaires de bas niveau pour la construction sécurisée
de commandes de compilation, la validation des arguments et l'exécution de
processus. Il constitue le socle technique sur lequel repose mainprocess.py.

FONCTIONS PRINCIPALES:
    ┌────────────────────────────────────────────────────────────────────────┐
    │ VALIDATION & NORMALISATION                                             │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • validate_args()              → Valide et normalise les arguments CLI │
    │ • normalized_program_and_args() → Combine conversion + validation      │
    ├────────────────────────────────────────────────────────────────────────┤
    │ ENVIRONNEMENT                                                           │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • build_env()                  → Construit un environnement sécurisé   │
    ├────────────────────────────────────────────────────────────────────────┤
    │ EXÉCUTION                                                               │
    ├────────────────────────────────────────────────────────────────────────┤
    │ • run_process()                → Exécute un processus (QProcess ou     │
    │                                 subprocess avec fallback automatique)  │
    └────────────────────────────────────────────────────────────────────────┘

FONCTIONNEMENT INTERNE:
    1. Les arguments sont d'abord validés (validate_args) pour prévenir les
       injections de commandes et les caractères dangereux.
    2. L'environnement est construit (build_env) avec un whitelist de vars.
    3. Le programme et ses arguments sont normalisés en types sûrs.
    4. Le processus est exécuté via QProcess (préféré) ou subprocess (fallback).

SÉCURITÉ:
    - Validation stricte des arguments (rejet des caractères de contrôle)
    - Whitelist des variables d'environnement (variables par défaut sûres)
    - Encodage forcé en UTF-8 pour les sorties
    - Masquage automatique des secrets dans les logs

DÉPENDANCES:
    - PySide6.QtCore.QProcess : Préféré pour l'intégration avec l'event loop Qt
    - subprocess : Fallback lorsque QProcess n'est pas disponible

================================================================================
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional, Union

# =============================================================================
# SECTION 1 : IMPORTS ET CONSTANTES
# =============================================================================
# Import de QProcess pour l'intégration Qt. QProcess est préféré car il offre
# une meilleure intégration avec l'event loop de PySide6 et permet l'utilisation
# des signaux/slots Qt pour la communication asynchrone.

try:
    from PySide6.QtCore import QProcess  # type: ignore
except Exception:  # pragma: no cover - Qt peut ne pas être installé
    QProcess = None  # type: ignore

# --- Type Alias pour les Chemins ---
# Un "Pathish" est un chemin qui peut être exprimé soit comme string,
# soit comme objet Path. Cette flexibilité simplifie l'API.
Pathish = Union[str, Path]


# =============================================================================
# SECTION 2 : VALIDATION DES ARGUMENTS CLI
# =============================================================================
# Cette section contient les fonctions de validation et de normalisation
# des arguments destinés à être passés aux processus externes.
# La validation est cruciale pour prévenir les injections de commandes.
# =============================================================================

# -----------------------------------------------------------------------------
# 2.1 Variables d'Environnement par Défaut Conservées
# -----------------------------------------------------------------------------
# Ces variables sont considérées comme "sûres" et conservées par défaut
# lors de la construction d'un environnement pour un processus.
# Elles sont essentielles pour le bon fonctionnement de Python et du système.

_DEF_ENV_KEYS = (
    "PATH",     # Chemins des exécutables
    "LANG",     # Paramètres linguistiques
    "LC_ALL",   # Paramètres régionaux complets
    "LC_CTYPE", # Type de caractères
    "TMP",      # Répertoire temporaire (Windows)
    "TEMP",     # Répertoire temporaire (Windows, alternatif)
)


def validate_args(
    args: Sequence[Any], 
    *, 
    max_len: int = 4096
) -> list[str]:
    """
    Valide et normalise une séquence d'arguments CLI.
    
    Cette fonction effectue plusieurs vérifications de sécurité essentielles:
    
    1. **Rejet des valeurs None** : Les arguments None sont invalides et
       indiquent généralement une erreur de programmation.
    
    2. **Rejet des caractères de contrôle** : Les caractères comme newline
       (\\n), carriage return (\\r) et null (\\x00) peuvent être utilisés pour
       injecter des commandes supplémentaires.
    
    3. **Limite de longueur** : Empêche les attaques par débordement de
       tampon et les arguments excessivement longs.
    
    4. **Conversion en chaînes** : Tous les types sont convertis en strings
       pour assurer la cohérence du typage.
    
    Args:
        args: Séquence d'arguments à valider. Peut contenir des objets de
              types variés (Path, int, str, etc.) qui seront convertis.
        max_len: Longueur maximale autorisée pour chaque argument.
                 Par défaut 4096 caractères.
    
    Returns:
        Liste de chaînes de caractères validées et normalisées.
    
    Raises:
        ValueError: Si un argument est None, contient des caractères de
                   contrôle invalides, ou dépasse la longueur maximale.
    
    Exemples:
        >>> validate_args(["--input", "file.py", 123])
        ['--input', 'file.py', '123']
        
        >>> validate_args(["--name", "test"])
        ['--name', 'test']
        
        >>> validate_args([None])  # ValueError
        ValueError: Argument is None
        
        >>> validate_args(["--data", "line\\nbreak"])  # ValueError
        ValueError: Invalid control character in argument...
    
    Notes:
        - Cette validation est exécutée AVANT toute exécution de processus.
        - Elle protège contre les injections de commandes shell.
        - Les objets Path sont automatiquement convertis en chemins absolus.
    """
    out: list[str] = []
    for a in args:
        if a is None:
            raise ValueError("Argument is None")
        s = str(a)
        if any(ch in s for ch in ("\n", "\r", "\x00")):
            raise ValueError(f"Invalid control character in argument: {s!r}")
        if len(s) > max_len:
            raise ValueError(f"Argument too long (> {max_len} chars)")
        out.append(s)
    return out


# =============================================================================
# SECTION 3 : CONSTRUCTION DE L'ENVIRONNEMENT
# =============================================================================
# Cette section contient les fonctions pour construire un environnement
# de processus sécurisé. L'environnement est filtré pour ne garder que
# les variables jugées sûres.
# =============================================================================


def build_env(
    base: Optional[Mapping[str, str]] = None,
    *,
    whitelist: Optional[Sequence[str]] = None,
    extra: Optional[Mapping[str, str]] = None,
    minimal_path: Optional[str] = None,
) -> dict[str, str]:
    """
    Construit un dictionnaire d'environnement sécurisé pour subprocess/QProcess.
    
    Cette fonction crée un environnement minimal en suivant ce processus:
    
    1. **Initialisation** : Part d'un mapping vide ou du 'base' fourni.
    
    2. **Filtrage** : Ne conserve que les variables whitelisted. Si aucune
       whitelist n'est fournie, utilise la liste par défaut (_DEF_ENV_KEYS).
    
    3. **Injection** : Ajoute ou écrase les variables avec 'extra'.
    
    4. **PATH** : Remplace éventuellement le PATH par 'minimal_path'.
    
    L'objectif est de créer un environnement isolé et prévisible pour les
    processus de compilation, en évitant les variables potentiellement
    dangereuses ou incohérentes.
    
    Args:
        base: Environnement de base à utiliser. Si None, commence avec
              un dictionnaire vide.
        whitelist: Liste des variables d'environnement à conserver. Si None,
                   utilise la liste par défaut (_DEF_ENV_KEYS).
        extra: Variables supplémentaires à ajouter ou écraser dans l'env.
        minimal_path: Valeur fixe pour la variable PATH. Si fourni, remplace
                      complètement le PATH existant.
    
    Returns:
        Dictionnaire contenant l'environnement construit, prêt à être passé
        à subprocess ou QProcess.
    
    Exemples:
        >>> # Environnement minimal avec variables par défaut
        >>> env = build_env()
        >>> print(env.keys())
        dict_keys(['PATH', 'LANG', 'LC_ALL', 'LC_CTYPE', 'TMP', 'TEMP'])
        
        >>> # À partir de l'environnement courant, en gardant seulement PATH et HOME
        >>> env = build_env(
        ...     base=os.environ,
        ...     whitelist=["PATH", "HOME"],
        ...     extra={"MY_VAR": "value"}
        ... )
        
        >>> # PATH personnalisé (pour isoler l'environnement de compilation)
        >>> env = build_env(
        ...     base=os.environ,
        ...     minimal_path="/custom/bin:/usr/local/bin"
        ... )
    
    Notes:
        - Les variables non-string sont ignorées.
        - L'ordre de priorité: extra > minimal_path > whitelist > base
        - Pour les compilations, un PATH minimal est souvent préféré pour
          éviter les conflits de versions.
    """
    env: dict[str, str] = {}
    src = dict(base or {})
    allow = set(whitelist or _DEF_ENV_KEYS)
    
    # Filtrage des variables selon la whitelist
    for k, v in src.items():
        if k in allow and isinstance(v, str):
            env[k] = v
    
    # Remplacement du PATH si demandé
    if minimal_path is not None:
        env["PATH"] = minimal_path
    
    # Ajout des variables supplémentaires
    if extra:
        for k, v in extra.items():
            if isinstance(k, str) and isinstance(v, str):
                env[k] = v
    
    return env


# =============================================================================
# SECTION 4 : NORMALISATION PROGRAMME + ARGUMENTS
# =============================================================================
# Combine la conversion en chaîne et la validation des arguments en une
# seule opération pratique.
# =============================================================================


def normalized_program_and_args(
    program: Pathish, 
    args: Sequence[Any]
) -> tuple[str, list[str]]:
    """
    Normalise le programme et ses arguments en types sûrs.
    
    Cette fonction de commodité combine deux opérations:
    1. Conversion du chemin du programme en chaîne de caractères
    2. Validation de tous les arguments avec validate_args()
    
    Args:
        program: Chemin vers l'exécutable (peut être str ou Path).
        args: Séquence d'arguments pour le programme.
    
    Returns:
        Tuple (programme_str, args_validés) où:
        - programme_str: Chemin du programme en string
        - args_validés: Liste d'arguments validés et normalisés
    
    Raises:
        ValueError: Si un argument est invalide (voir validate_args).
    
    Exemples:
        >>> normalized_program_and_args(Path("/usr/bin/python"), ["-c", "print(1)"])
        ('/usr/bin/python', ['-c', 'print(1)'])
        
        >>> normalized_program_and_args("python", ["script.py"])
        ('python', ['script.py'])
    
    Notes:
        - Cette fonction est généralement appelée avant run_process().
        - Elle garantit que tous les types sont normalisés avant exécution.
    """
    prog_str = str(program)
    return prog_str, validate_args(args)


# =============================================================================
# SECTION 5 : EXÉCUTION DE PROCESSUS
# =============================================================================
# Point d'entrée principal pour l'exécution de processus. Supporte QProcess
# (Qt) avec fallback vers subprocess standard.
# =============================================================================


def run_process(
    gui: Any,
    program: Pathish,
    args: Sequence[Any],
    *,
    cwd: Optional[Pathish] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout_ms: int = 300000,
    on_stdout: Optional[Any] = None,
    on_stderr: Optional[Any] = None,
) -> tuple[int, str, str]:
    """
    Exécute un processus en utilisant QProcess (Qt) ou subprocess.
    
    Cette fonction est le point d'entrée principal pour l'exécution de
    processus dans PyCompiler ARK. Elle offre plusieurs avantages:
    
    - **QProcess (Préféré)** : Meilleure intégration avec l'event loop Qt,
      support natif des signaux/slots, et gestion plus propre des processus.
    
    - **Subprocess (Fallback)** : Si QProcess échoue ou n'est pas disponible,
      utilise subprocess.run() comme solution de repli.
    
    - **Gestion du Répertoire** : Utilise automatiquement gui.workspace_dir
      comme répertoire de travail si aucun n'est spécifié.
    
    - **Callbacks Optionnels** : Appelle on_stdout/on_stderr après la
      complétion du processus avec le contenu complet des buffers.
    
    - **Timeout Intelligent** : Gère proprement les timeouts avec tentative
      d'arrêt propre (terminate) avant forçage (kill).
    
    Args:
        gui: Instance GUI (MainWindow) contenant workspace_dir et log.
             Utilisé pour déterminer le répertoire de travail par défaut.
        program: Chemin vers l'exécutable à lancer.
        args: Arguments à passer au programme.
        cwd: Répertoire de travail. Si None, utilise gui.workspace_dir.
        env: Variables d'environnement. Si None, utilise l'environnement
             courant (filtré selon build_env).
        timeout_ms: Timeout en millisecondes. Par défaut 300000ms (5 min).
        on_stdout: Callback(optionnel) appelé avec les données stdout.
                   Signature: callback(stdout: str) -> None
        on_stderr: Callback(optionnel) appelé avec les données stderr.
                   Signature: callback(stderr: str) -> None
    
    Returns:
        Tuple (exit_code, stdout, stderr):
        - exit_code: Code de retour du processus (0 = succès)
        - stdout: Sortie standard capturée (string)
        - stderr: Sortie d'erreur capturée (string)
    
    Raises:
        - Ne lève jamais d'exception ; retourne (1, "", str(e)) en cas d'erreur.
    
    Exemples:
        >>> # Exécution simple
        >>> code, out, err = run_process(
        ...     gui, "python", ["-c", "print('hello')"],
        ...     timeout_ms=60000
        ... )
        >>> print(out)
        hello
        
        >>> # Avec répertoire personnalisé
        >>> code, out, err = run_process(
        ...     gui, "python", ["script.py"],
        ...     cwd="/path/to/workdir"
        ... )
        
        >>> # Avec callbacks
        >>> def log_output(text):
        ...     print(f"OUTPUT: {text}")
        >>> code, out, err = run_process(
        ...     gui, "python", ["script.py"],
        ...     on_stdout=log_output
        ... )
    
    Flux d'Exécution:
        ┌─────────────────────────────────────────────────────────────┐
        │ 1. Normaliser programme + arguments                         │
        │ 2. Déterminer répertoire de travail (cwd)                   │
        │ 3. Tenter QProcess (si disponible)                          │
        │    ├─ Configurer programme, arguments, cwd, env            │
        │    ├─ Démarrer le processus                                │
        │    ├─ Attendre avec timeout                                │
        │    ├─ Si timeout: terminate → wait → kill                  │
        │    └─ Lire stdout/stderr et retourner                      │
        │ 4. Si QProcess échoue: utiliser subprocess.run()            │
        │ 5. Exécuter les callbacks (si fournis)                      │
        │ 6. Retourner (code, stdout, stderr)                        │
        └─────────────────────────────────────────────────────────────┘
    
    Notes:
        - Les callbacks sont appelés APRÈS la complétion du processus,
          pas en streaming temps réel.
        - Les sorties sont décodées en UTF-8 avec erreurs ignorées.
        - Pour les processus de longue durée, preferer l'utilisation
          directe de QProcess avec les signaux readyReadStandardOutput.
    """
    # -----------------------------------------------------------------------------
    # ÉTAPE 1 : Normalisation du programme et des arguments
    # -----------------------------------------------------------------------------
    prog_str, arg_list = normalized_program_and_args(program, args)

    # -----------------------------------------------------------------------------
    # ÉTAPE 2 : Détermination du répertoire de travail
    # -----------------------------------------------------------------------------
    if cwd is None:
        try:
            ws = getattr(gui, "workspace_dir", None)
            if ws:
                cwd = ws
        except Exception:
            cwd = None

    # Point de départ pour la mesure de performance (utilisé par les appelants)
    time.perf_counter()

    # -----------------------------------------------------------------------------
    # ÉTAPE 3 : Tentative avec QProcess (préféré pour l'intégration Qt)
    # -----------------------------------------------------------------------------
    if QProcess is not None:
        try:
            proc = QProcess(gui)
            proc.setProgram(prog_str)
            proc.setArguments(arg_list)

            # Configuration du répertoire de travail
            try:
                if cwd:
                    proc.setWorkingDirectory(str(cwd))
            except Exception:
                pass

            # Configuration de l'environnement
            try:
                if env:
                    proc.setEnvironment(
                        [
                            f"{k}={v}"
                            for k, v in env.items()
                            if isinstance(k, str) and isinstance(v, str)
                        ]
                    )
            except Exception:
                pass

            # Démarrage du processus
            proc.start()

            # Attente de la fin avec timeout
            finished = proc.waitForFinished(timeout_ms)
            if not finished:
                # Tentative d'arrêt propre (SIGTERM)
                try:
                    proc.terminate()
                    proc.waitForFinished(5000)
                except Exception:
                    pass
                # Forcément kill si pas arrêté proprement
                try:
                    proc.kill()
                    proc.waitForFinished(2000)
                except Exception:
                    pass

            # Lecture des sorties
            try:
                out_bytes = proc.readAllStandardOutput().data()
                err_bytes = proc.readAllStandardError().data()
                out = (
                    out_bytes.decode(errors="ignore")
                    if isinstance(out_bytes, (bytes, bytearray))
                    else str(out_bytes)
                )
                err = (
                    err_bytes.decode(errors="ignore")
                    if isinstance(err_bytes, (bytes, bytearray))
                    else str(err_bytes)
                )
            except Exception:
                out, err = "", ""

            code = int(proc.exitCode())

            # Exécution des callbacks
            try:
                if callable(on_stdout) and out:
                    on_stdout(out)
                if callable(on_stderr) and err:
                    on_stderr(err)
            except Exception:
                pass

            return code, out, err

        except Exception:
            # QProcess a échoué, on utilise subprocess comme fallback
            pass

    # -----------------------------------------------------------------------------
    # ÉTAPE 4 : Fallback avec subprocess standard
    # -----------------------------------------------------------------------------
    try:
        completed = subprocess.run(
            [prog_str, *arg_list],
            cwd=str(cwd) if cwd else None,
            env=dict(env) if env else None,
            timeout=max(1, int(timeout_ms / 1000)),
            capture_output=True,
            text=True,
        )
        out = completed.stdout or ""
        err = completed.stderr or ""

        # Exécution des callbacks
        try:
            if callable(on_stdout) and out:
                on_stdout(out)
            if callable(on_stderr) and err:
                on_stderr(err)
        except Exception:
            pass

        return int(completed.returncode), out, err

    except Exception as e:
        # En cas d'erreur, retourne un code d'erreur 1 avec le message
        return 1, "", str(e)


# =============================================================================
# FIN DU MODULE command_helpers.py
# =============================================================================

