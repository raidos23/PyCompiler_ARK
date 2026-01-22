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
Module command_helpers.py — Helpers pour la construction et l'exécution de commandes

Ce module fournit des utilitaires de bas niveau pour la construction sécurisée
de commandes de compilation, la validation des arguments et l'exécution de processus.
Il est utilisé par le module mainprocess.py pour orchestrer les compilations.

Fonctions principales:
    - validate_args: Validation et normalisation des arguments CLI
    - build_env: Construction d'un environnement minimal pour les processus
    - normalized_program_and_args: Normalisation couple (programme, arguments)
    - run_process: Exécution générique de processus (QProcess ou subprocess)

Usage typique (dans mainprocess.py):

    from .command_helpers import (
        validate_args,
        build_env,
        normalized_program_and_args,
        run_process,
    )

    def compiler_function(self, gui, file):
        # Validation des arguments
        args = validate_args(["--input", file])

        # Construction de l'environnement
        env = build_env(None, extra={"PYTHONPATH": "/custom/path"})

        # Normalisation programme + arguments
        prog, args = normalized_program_and_args("python", args)

        # Exécution du processus
        code, stdout, stderr = run_process(gui, prog, args, env=env)
"""

from __future__ import annotations

import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional, Union

# Tentative d'import de QProcess pour l'intégration Qt
# QProcess est préféré quand disponible car il offre une meilleure
# intégration avec l'événement loop de PySide6
try:
    from PySide6.QtCore import QProcess  # type: ignore
except Exception:  # pragma: no cover - Qt peut ne pas être installé
    QProcess = None  # type: ignore

# Type alias pour les chemins (str ou Path)
Pathish = Union[str, Path]


# ============================================================================
# SECTION 1 : VALIDATION DES ARGUMENTS CLI
# ============================================================================
# Ces fonctions assurent la sécurité et la robustesse des arguments passés
# aux processus externes. Elles préviennent les injections et les erreurs.


def validate_args(args: Sequence[Any], *, max_len: int = 4096) -> list[str]:
    """Valide et normalise une séquence d'arguments CLI.

    Cette fonction effectue plusieurs vérifications de sécurité:
    1. Rejette les valeurs None
    2. Rejette les caractères de contrôle (newline, null, etc.)
    3. Limite la longueur de chaque argument
    4. Convertit tous les types en chaînes de caractères

    Args:
        args: Séquence d'arguments à valider (peut contenir des Path, nombres, etc.)
        max_len: Longueur maximale autorisée par argument (défaut: 4096)

    Returns:
        Liste de chaînes de caractères validées

    Raises:
        ValueError: Si un argument est None, contient des caractères invalides,
                   ou dépasse la longueur maximale

    Exemple:
        >>> validate_args(["--input", "file.py", 123])
        ['--input', 'file.py', '123']
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


# ============================================================================
# SECTION 2 : CONSTRUCTION DE L'ENVIRONNEMENT
# ============================================================================
# Construit un dictionnaire d'environnement sécurisé pour les processus.
# Filtre les variables pour ne garder que celles jugées sûres.


# Variables d'environnement par défaut conservées
# Ce sont les variables essentielles pour le bon fonctionnement des
# processus Python et du système
_DEF_ENV_KEYS = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TMP", "TEMP")


def build_env(
    base: Optional[Mapping[str, str]] = None,
    *,
    whitelist: Optional[Sequence[str]] = None,
    extra: Optional[Mapping[str, str]] = None,
    minimal_path: Optional[str] = None,
) -> dict[str, str]:
    """Construit un dictionnaire d'environnement pour subprocess/QProcess.

    Cette fonction crée un environnement minimal et sécurisé en:
    1. Partant d'un mapping vide ou d'un 'base' fourni
    2. Ne conservant que les variables whitelisted (ou un ensemble par défaut)
    3. Ajoutant/écrasant avec les valeurs 'extra'
    4. Éventuellement remplaçant PATH par 'minimal_path'

    Args:
        base: Environnement de base à utiliser (si None, commence vide)
        whitelist: Liste des variables d'environnement à conserver
        extra: Variables supplémentaires à ajouter/écraser
        minimal_path: Valeur fixe pour PATH (si fourni, écrase le PATH existant)

    Returns:
        Dictionnaire contenant l'environnement construit

    Exemple:
        >>> env = build_env(
        ...     base=os.environ,
        ...     whitelist=["PATH", "HOME"],
        ...     extra={"MY_VAR": "value"},
        ...     minimal_path="/custom/bin"
        ... )
    """
    env: dict[str, str] = {}
    src = dict(base or {})
    allow = set(whitelist or _DEF_ENV_KEYS)
    for k, v in src.items():
        if k in allow and isinstance(v, str):
            env[k] = v
    if minimal_path is not None:
        env["PATH"] = minimal_path
    if extra:
        for k, v in extra.items():
            if isinstance(k, str) and isinstance(v, str):
                env[k] = v
    return env


# ============================================================================
# SECTION 3 : NORMALISATION PROGRAMME + ARGUMENTS
# ============================================================================
# Combine la conversion en chaîne et la validation des arguments.


def normalized_program_and_args(
    program: Pathish, args: Sequence[Any]
) -> tuple[str, list[str]]:
    """Normalise le programme et ses arguments en types sûrs.

    Cette fonction:
    1. Convertit le chemin du programme en chaîne de caractères
    2. Valide tous les arguments avec validate_args

    Args:
        program: Chemin vers l'exécutable (str ou Path)
        args: Séquence d'arguments pour le programme

    Returns:
        Tuple (programme_str, args_validés)

    Exemple:
        >>> normalized_program_and_args(Path("/usr/bin/python"), ["-c", "print(1)"])
        ('/usr/bin/python', ['-c', 'print(1)'])
    """
    prog_str = str(program)
    return prog_str, validate_args(args)


# ============================================================================
# SECTION 4 : EXÉCUTION DE PROCESSUS
# ============================================================================
# Exécution générique avec support QProcess (Qt) et subprocess (fallback).


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
    """Exécute un processus en utilisant QProcess (Qt) ou subprocess.

    Cette fonction est le point d'entrée principal pour l'exécution de
    processus dans PyCompiler ARK. Elle offre plusieurs avantages:
    - Utilisation de QProcess pour une meilleure intégration Qt
    - Fallback automatique vers subprocess si QProcess indisponible
    - Gestion automatique du répertoire de travail (depuis gui.workspace_dir)
    - Support des callbacks pour stdout/stderr

    Args:
        gui: Instance GUI (MainWindow) contenant workspace_dir et log
        program: Chemin vers l'exécutable
        args: Arguments à passer au programme
        cwd: Répertoire de travail (si None, utilise gui.workspace_dir)
        env: Variables d'environnement (si None, utilise l'environnement courant)
        timeout_ms: Timeout en millisecondes (défaut: 300s = 5min)
        on_stdout: Callback optionnel appelé avec les données stdout
        on_stderr: Callback optionnel appelé avec les données stderr

    Returns:
        Tuple (exit_code, stdout, stderr):
            - exit_code: Code de retour du processus
            - stdout: Sortie standard capturée
            - stderr: Sortie d'erreur capturée

    Note:
        Les callbacks on_stdout/on_stderr sont appelés après la complétion
        du processus, avec le contenu complet des buffers (pas de streaming).

    Exemple:
        >>> code, out, err = run_process(
        ...     gui, "python", ["-c", "print('hello')"],
        ...     timeout_ms=60000
        ... )
        >>> print(out)
        hello
    """
    prog_str, arg_list = normalized_program_and_args(program, args)

    # Répertoire de travail par défaut depuis la GUI
    if cwd is None:
        try:
            ws = getattr(gui, "workspace_dir", None)
            if ws:
                cwd = ws
        except Exception:
            cwd = None

    # Point de départ pour la mesure de performance
    time.perf_counter()

    # Tentative d'utilisation de QProcess (préféré pour l'intégration Qt)
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
                # Forcément kill si pas arrêté
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

    # Fallback: utilisation de subprocess standard
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
