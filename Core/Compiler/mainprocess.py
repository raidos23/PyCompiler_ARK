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
Module mainprocess.py - Gestion des processus de compilation PyCompiler ARK++

Ce module contient toutes les fonctions de gestion des processus de compilation,
y compris le démarrage, la surveillance, la gestion des erreurs et l'annulation
des compilations. Il gère également l'interface utilisateur dynamique pour les
moteurs externes et l'installation automatique des modules manquants.
"""

# ============================================================================
# SECTION 1 : IMPORTATIONS
# ============================================================================
# Ce fichier utilise plusieurs catégories d'importations organisées par fonctionnalité.
# 1. Bibliothèques standard Python (utilitaires système, gestion de fichiers, regex)
# 2. Framework PySide6 pour l'interface graphique et les processus Qt
# 3. Modules locaux du projet (gestion des moteurs, utilitaires, préférences)
# ============================================================================

# --- Imports des bibliothèques standard Python ---
import json  # Manipulation de données JSON (parsing, sérialisation)
import os  # Opérations sur le système de fichiers (chemins, création de répertoires)
import platform  # Détection du système d'exploitation (Windows/Linux)
import re  # Expressions régulières (détection de modules manquants)
import subprocess  # Exécution de processus externes (pip install)
import time  # Minuteries et délais (pour pip install retry)
from typing import Any, Optional  # Type hints pour les fonctions

# --- Imports du framework PySide6 (Qt pour Python) ---
# QProcess : Gestion des processus externes avec signaux/slots Qt
# QTimer : Minuteries pour les timeouts et délais de grâce
from PySide6.QtCore import QProcess, QTimer

# --- Imports des widgets Qt utilisés pour l'interface dynamique ---
# QCheckBox : Cases à cocher pour les options dynamiques
# QLabel : Étiquettes pour afficher du texte
# QMessageBox : Boîtes de dialogue pour les messages utilisateur
# QPlainTextEdit : Zones de texte multiligne
# QPushButton : Boutons cliquables
# QWidget : Classe de base pour tous les widgets
from PySide6.QtWidgets import (
    QCheckBox,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QWidget,
)

# --- Imports des modules locaux du projet PyCompiler ARK ---
# process_killer : Fonctions pour tuer les arbres de processus
# engines_loader : Gestionnaire de moteurs de compilation
# clamp_text, redact_secrets : Utilitaires pour le logging sécurisé
# compute_for_all : Constructeur automatique de commandes
# MAX_PARALLEL : Constante définissant le nombre max de compilations parallèles
from Core.Compiler.process_killer import _kill_process_tree, _kill_all_descendants
from Core import engines_loader as engines_loader
from engine_sdk.utils import clamp_text, redact_secrets
from Core.Compiler.command_helpers import run_process
from Core.Auto_Command_Builder import compute_for_all
from Core.preferences import MAX_PARALLEL

# Note : Support ACASL supprimé (obsolète)

# ============================================================================
# SECTION 0 : VENV/PIP HELPERS (MOVED FROM engine_sdk/utils.py)
# ============================================================================
# These functions were moved from engine_sdk/utils.py to centralize
# venv and pip management logic in mainprocess.py
# ============================================================================


def resolve_project_venv(gui: Any) -> Optional[str]:
    """Resolve the project venv path using VenvManager when available, else workspace/venv."""
    try:
        vm = getattr(gui, "venv_manager", None)
        if vm:
            vroot = vm.resolve_project_venv()
            if vroot and os.path.isdir(vroot):
                return vroot
    except Exception:
        pass
    try:
        ws = getattr(gui, "workspace_dir", None)
        if ws:
            v = os.path.join(ws, "venv")
            return v if os.path.isdir(v) else None
    except Exception:
        pass
    return None


def pip_executable(vroot: str) -> str:
    """Return pip executable path under a venv root (cross-platform)."""
    name = "pip.exe" if platform.system() == "Windows" else "pip"
    return os.path.join(
        vroot, "Scripts" if platform.system() == "Windows" else "bin", name
    )


def pip_show(gui: Any, pip_exe: str, package: str, *, timeout_ms: int = 180000) -> int:
    """Run 'pip show <package>' and return exit code (0 if installed).
    Falls back to 'python -m pip' if the venv pip executable is missing.
    """
    prog = pip_exe
    args = ["show", package]
    try:
        if not os.path.isfile(pip_exe):
            import sys as _sys

            prog = _sys.executable
            args = ["-m", "pip", "show", package]
    except Exception:
        try:
            import sys as _sys

            prog = _sys.executable
            args = ["-m", "pip", "show", package]
        except Exception:
            prog = pip_exe
            args = ["show", package]
    code, _out, _err = run_process(gui, prog, args, timeout_ms=timeout_ms)
    return int(code)


def pip_install(
    gui: Any, pip_exe: str, package: str, *, timeout_ms: int = 600000
) -> int:
    """Run 'pip install <package>' and return exit code (0 if success).
    - Uses the venv pip when available, else falls back to 'python -m pip'
    - Retries once on failure after a short delay to improve robustness.
    """
    prog = pip_exe
    args = ["install", package]
    try:
        if not os.path.isfile(pip_exe):
            import sys as _sys

            prog = _sys.executable
            args = ["-m", "pip", "install", package]
    except Exception:
        try:
            import sys as _sys

            prog = _sys.executable
            args = ["-m", "pip", "install", package]
        except Exception:
            prog = pip_exe
            args = ["install", package]
    code, _out, _err = run_process(gui, prog, args, timeout_ms=timeout_ms)
    if code != 0:
        try:
            time.sleep(1.0)
        except Exception:
            pass
        code, _out, _err = run_process(gui, prog, args, timeout_ms=timeout_ms)
    return int(code)


# ============================================================================
# SECTION 2 : GESTION DES PROCESSUS DE COMPILATION
# ============================================================================
# Cette section contient toutes les fonctions liées au cycle de vie des processus
# de compilation :
# - Démarrage des processus (try_start_processes, start_compilation_process)
# - Traitement des sorties (handle_stdout, handle_stderr)
# - Finalisation et nettoyage (handle_finished)
# - Gestion des erreurs et annulation (cancel_all_compilations, try_install_missing_modules)
# ============================================================================


def try_start_processes(self):
    """
    Fonction principale de gestion de la file d'attente des compilations.

    Cette fonction tente de démarrer de nouveaux processus de compilation
    tant que le nombre maximum de processus parallèles n'est pas atteint
    et qu'il y a des fichiers dans la file d'attente.

    Args:
        self: Instance de la classe principale (GUI)

    Returns:
        None
    """
    # Import nécessaire pour forcer le rafraîchissement de l'interface Qt
    from PySide6.QtWidgets import QApplication

    # ========================================================================
    # Boucle principale de traitement de la file d'attente
    # ========================================================================
    # Tant que le nombre de processus actifs est inférieur au maximum autorisé
    # ET qu'il reste des fichiers dans la file d'attente, on lance les compilations
    while len(self.processes) < MAX_PARALLEL and self.queue:
        # Extraction du premier fichier de la file d'attente
        file, to_compile = self.queue.pop(0)

        # Lancement de la compilation seulement si le fichier n'est pas ignoré
        if to_compile:
            self.start_compilation_process(file)
        # Note : Si to_compile == False (fichier ignoré), on ne modifie pas la
        # barre de progression et on passe directement au suivant dans la file

    # ========================================================================
    # Vérification de fin de toutes les compilations
    # ========================================================================
    # Si aucun processus n'est actif ET la file d'attente est vide,
    # alors toutes les compilations sont terminées
    if not self.processes and not self.queue:
        # Affichage de la barre de progression à 100%
        self.progress.setRange(0, 1)
        self.progress.setValue(1)

        # Forcer Qt à rafraîchir l'interface pour afficher les changements
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()

        # Message de confirmation dans le journal
        self.log.append("✔️ Toutes les compilations sont terminées.\n")

        # ========================================================================
        # Exécution des hooks de succès des moteurs de compilation
        # ========================================================================
        # Chaque moteur peut avoir une fonction on_success() appelée après
        # la compilation réussie pour effectuer des actions supplémentaires
        try:
            hooks = getattr(self, "_pending_engine_success_hooks", [])
            for eng, fpath in hooks:
                try:
                    # Appel du hook de succès du moteur
                    eng.on_success(self, fpath)
                except Exception:
                    # En cas d'erreur dans le hook, on log un avertissement
                    try:
                        self.log.append(
                            f"⚠️ on_success du moteur '{getattr(eng, 'id', '?')}' a échoué."
                        )
                    except Exception:
                        pass
        except Exception:
            pass
        finally:
            # Nettoyage de la liste des hooks en attente
            try:
                if hasattr(self, "_pending_engine_success_hooks"):
                    self._pending_engine_success_hooks.clear()
            except Exception:
                pass

        # ========================================================================
        # Restauration de l'interface utilisateur
        # ========================================================================
        # Réactivation des onglets du compilateur s'ils existent
        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            self.compiler_tabs.setEnabled(True)

        # Réactivation des contrôles de l'interface
        self.set_controls_enabled(True)

        # Sauvegarde des préférences utilisateur
        self.save_preferences()

        # Fin de la fonction
        return


def start_compilation_process(self, file):
    """
    Démarre un processus de compilation pour un fichier donné.

    Cette fonction:
    1. Détermine le moteur de compilation actif (PyInstaller, Nuitka, etc.)
    2. Instancie le moteur et vérifie les outils requis
    3. Configure l'environnement du processus
    4. Crée et configure le processus QProcess
    5. Met en place les minuteries de timeout
    6. Lance le processus de compilation

    Args:
        self: Instance de la classe principale (GUI)
        file: Chemin absolu du fichier Python à compiler

    Returns:
        None
    """
    import time

    file_basename = os.path.basename(file)

    # ========================================================================
    # Étape 1: Détermination du moteur de compilation actif
    # ========================================================================
    # On récupère l'index de l'onglet UI actif et on le mappe vers un moteur
    # Via le registre des moteurs (engines_loader.registry)
    try:
        idx = (
            self.compiler_tabs.currentIndex()
            if hasattr(self, "compiler_tabs") and self.compiler_tabs
            else 0
        )
        engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception:
        print("No engine detected")

    # ========================================================================
    # Étape 2: Instanciation du moteur de compilation
    # ========================================================================
    # Création d'une instance du moteur via le registre
    try:
        engine = engines_loader.registry.create(engine_id)
    except Exception as e:
        self.log.append(f"❌ Impossible d'instancier le moteur '{engine_id}': {e}")
        return

    # ========================================================================
    # Étape 3: Vérification des outils requis
    # ========================================================================
    # Le moteur peut installer automatiquement les outils manquants (pip, etc.)
    if not engine.ensure_tools_installed(self):
        return

    # ========================================================================
    # Étape 4: Vérifications préliminaires (preflight)
    # ========================================================================
    # Le moteur peut vérifier que le fichier est compilable
    if not engine.preflight(self, file):
        return

    # ========================================================================
    # Étape 5: Récupération des arguments de compilation
    # ========================================================================
    # Le moteur retourne la commande complète (programme + arguments)
    prog_args = engine.program_and_args(self, file)
    if not prog_args:
        return
    program, args = prog_args

    # ========================================================================
    # Étape 6: Configuration de la barre de progression
    # ========================================================================
    # Mode indéterminé (animation) pendant la compilation
    from PySide6.QtWidgets import QApplication

    self.progress.setRange(0, 0)
    QApplication.processEvents()

    # ========================================================================
    # Étape 7: Configuration de l'environnement du processus
    # ========================================================================
    # Le moteur peut surcharger les variables d'environnement
    try:
        env = engine.environment(self, file)
    except Exception:
        env = None
    if env:
        try:
            from PySide6.QtCore import QProcessEnvironment

            penv = QProcessEnvironment()
            for k, v in env.items():
                penv.insert(str(k), str(v))
        except Exception:
            penv = None
    else:
        penv = None

    # ========================================================================
    # Étape 8: Logging de la commande de compilation
    # ========================================================================
    # Affichage de la commande dans le journal (avec secrets masqués)
    cmd_preview = " ".join([program] + args)
    try:
        cmd_preview_log = clamp_text(redact_secrets(cmd_preview), max_len=1000)
    except Exception:
        cmd_preview_log = cmd_preview
    if engine_id == "nuitka":
        self.log.append(
            f"▶️ Lancement compilation Nuitka : {file_basename}\nCommande : {cmd_preview_log}\n"
        )
    else:
        self.log.append(
            f"▶️ Lancement compilation : {file_basename}\nCommande : {cmd_preview_log}\n"
        )

    # ========================================================================
    # Étape 9: Configuration du fichier sentinelle pour annulation
    # ========================================================================
    # Ce fichier permet une annulation coopérative du processus
    try:
        cancel_dir = os.path.join(
            self.workspace_dir or os.getcwd(), ".pycompiler", "cancel"
        )
        os.makedirs(cancel_dir, exist_ok=True)
        cancel_file = os.path.join(cancel_dir, f"{engine_id}_{file_basename}.cancel")
        if os.path.isfile(cancel_file):
            os.remove(cancel_file)
    except Exception:
        cancel_file = None

    # ========================================================================
    # Étape 10: Création et configuration du processus QProcess
    # ========================================================================
    process = QProcess(self)
    if penv is not None:
        try:
            process.setProcessEnvironment(penv)
        except Exception:
            pass
    process.setProgram(program)
    process.setArguments(args)
    process.setWorkingDirectory(self.workspace_dir)
    process.file_path = file
    process.file_basename = file_basename
    process._start_time = time.time()
    process._engine_id = engine_id
    process._cancel_file = cancel_file

    # ========================================================================
    # Étape 11: Connexion des signaux du processus
    # ========================================================================
    # readyReadStandardOutput: données stdout reçues
    # readyReadStandardError: données stderr reçues
    # finished: processus terminé
    process.readyReadStandardOutput.connect(lambda p=process: self.handle_stdout(p))
    process.readyReadStandardError.connect(lambda p=process: self.handle_stderr(p))
    process.finished.connect(lambda ec, es, p=process: self.handle_finished(p, ec, es))

    # ========================================================================
    # Étape 12: Ajout aux processus actifs
    # ========================================================================
    self.processes.append(process)
    self.current_compiling.add(file)

    # ========================================================================
    # Étape 13: Mise à jour optionnelle de l'interface
    # ========================================================================
    if hasattr(self, "update_compiler_options_enabled"):
        try:
            self.update_compiler_options_enabled()
        except Exception:
            pass

    # ========================================================================
    # Étape 14: Configuration du timeout avec arrêt propre puis kill
    # ========================================================================
    try:
        # Récupération du timeout depuis le moteur, l'environnement ou défaut
        try:
            timeout_sec = int(
                getattr(
                    engine,
                    "get_timeout_seconds",
                    lambda _gui: int(
                        os.environ.get("PYCOMPILER_PROCESS_TIMEOUT", "1800")
                    ),
                )(self)
            )
        except Exception:
            timeout_sec = int(os.environ.get("PYCOMPILER_PROCESS_TIMEOUT", "1800"))

        if timeout_sec and timeout_sec > 0:
            # Création de la minuterie de timeout
            t = QTimer(self)
            t.setSingleShot(True)

            # Fonction appelée lors du timeout
            def _on_timeout(proc=process, seconds=timeout_sec):
                try:
                    self.log.append(
                        f"⏱️ Timeout ({seconds}s) pour {getattr(proc, 'file_basename', '?')}. Arrêt en cours…"
                    )
                except Exception:
                    pass
                # Tentative d'arrêt propre (SIGTERM)
                try:
                    if proc.state() != QProcess.NotRunning:
                        proc.terminate()
                except Exception:
                    pass
                # Si l'arrêt propre échoue, on force le kill
                try:
                    proc.kill()
                except Exception:
                    pass

                # ========================================================================
                # Délai de grâce avant kill forcé
                # ========================================================================
                # On attend 10 secondes pour que le processus se termine proprement
                grace = QTimer(self)
                grace.setSingleShot(True)

                def _force_kill(p=proc):
                    if p.state() != QProcess.NotRunning:
                        try:
                            self.log.append(
                                f"🛑 Arrêt forcé du processus {getattr(p, 'file_basename', '?')} après délai de grâce."
                            )
                        except Exception:
                            pass
                        # Kill full process tree if possible
                        try:
                            pid2 = int(p.processId())
                        except Exception:
                            pid2 = None
                        if pid2:
                            _kill_process_tree(pid2, timeout=3.0, log=self.log.append)
                        try:
                            p.kill()
                        except Exception:
                            pass

                grace.timeout.connect(_force_kill)
                grace.start(10000)  # 10s grâce
                proc._grace_kill_timer = grace

            # Connexion de la minuterie et démarrage
            t.timeout.connect(_on_timeout)
            t.start(int(timeout_sec * 1000))
            process._timeout_timer = t

            # Fonction pour annuler la minuterie quand le processus finit normalement
            def _cancel_timer(_ec, _es, timer=t):
                try:
                    timer.stop()
                except Exception:
                    pass

            process.finished.connect(_cancel_timer)
    except Exception:
        pass

    # ========================================================================
    # Étape 15: Lancement du processus de compilation
    # ========================================================================
    process.start()
    try:
        idx = (
            self.compiler_tabs.currentIndex()
            if hasattr(self, "compiler_tabs") and self.compiler_tabs
            else 0
        )
        engine_id = engines_loader.registry.get_engine_for_tab(idx) or (
            "pyinstaller" if idx == 0 else "nuitka"
        )
    except Exception:
        engine_id = "pyinstaller"

    # Instancier le moteur de compilation
    try:
        engine = engines_loader.registry.create(engine_id)
    except Exception as e:
        self.log.append(f"❌ Impossible d'instancier le moteur '{engine_id}': {e}")
        return

    # S'assurer que les outils requis sont installés
    if not engine.ensure_tools_installed(self):
        return

    # Vérifications préliminaires avant compilation
    if not engine.preflight(self, file):
        return
    prog_args = engine.program_and_args(self, file)
    if not prog_args:
        return
    program, args = prog_args
    # Logging human-friendly and progress indeterminate
    from PySide6.QtWidgets import QApplication

    self.progress.setRange(0, 0)
    QApplication.processEvents()
    # Environnement processus (moteur peut surcharger)
    try:
        env = engine.environment(self, file)
    except Exception:
        env = None
    if env:
        try:
            from PySide6.QtCore import QProcessEnvironment

            penv = QProcessEnvironment()
            for k, v in env.items():
                penv.insert(str(k), str(v))
        except Exception:
            penv = None
    else:
        penv = None
    cmd_preview = " ".join([program] + args)
    try:
        cmd_preview_log = clamp_text(redact_secrets(cmd_preview), max_len=1000)
    except Exception:
        cmd_preview_log = cmd_preview
    if engine_id == "nuitka":
        self.log.append(
            f"▶️ Lancement compilation Nuitka : {file_basename}\nCommande : {cmd_preview_log}\n"
        )
    else:
        self.log.append(
            f"▶️ Lancement compilation : {file_basename}\nCommande : {cmd_preview_log}\n"
        )
    # Démarrage du processus QProcess
    # Chemin du fichier sentinelle pour annulation coopérative
    try:
        cancel_dir = os.path.join(
            self.workspace_dir or os.getcwd(), ".pycompiler", "cancel"
        )
        os.makedirs(cancel_dir, exist_ok=True)
        cancel_file = os.path.join(cancel_dir, f"{engine_id}_{file_basename}.cancel")
        if os.path.isfile(cancel_file):
            os.remove(cancel_file)
    except Exception:
        cancel_file = None

    # Création et configuration du processus
    process = QProcess(self)
    if penv is not None:
        try:
            process.setProcessEnvironment(penv)
        except Exception:
            pass
    process.setProgram(program)
    process.setArguments(args)
    process.setWorkingDirectory(self.workspace_dir)
    process.file_path = file
    process.file_basename = file_basename
    process._start_time = time.time()
    process._engine_id = engine_id
    process._cancel_file = cancel_file

    # Connexion des signaux du processus
    process.readyReadStandardOutput.connect(lambda p=process: self.handle_stdout(p))
    process.readyReadStandardError.connect(lambda p=process: self.handle_stderr(p))
    process.finished.connect(lambda ec, es, p=process: self.handle_finished(p, ec, es))

    # Ajout à la liste des processus actifs
    self.processes.append(process)
    self.current_compiling.add(file)

    # Mise à jour optionnelle des états UI dépendants
    if hasattr(self, "update_compiler_options_enabled"):
        try:
            self.update_compiler_options_enabled()
        except Exception:
            pass
    # Timeout configurable avec arrêt propre puis kill
    try:
        # Méthode engine.get_timeout_seconds si dispo; sinon env/défaut
        try:
            timeout_sec = int(
                getattr(
                    engine,
                    "get_timeout_seconds",
                    lambda _gui: int(
                        os.environ.get("PYCOMPILER_PROCESS_TIMEOUT", "1800")
                    ),
                )(self)
            )
        except Exception:
            timeout_sec = int(os.environ.get("PYCOMPILER_PROCESS_TIMEOUT", "1800"))
        if timeout_sec and timeout_sec > 0:
            t = QTimer(self)
            t.setSingleShot(True)

            def _on_timeout(proc=process, seconds=timeout_sec):
                try:
                    self.log.append(
                        f"⏱️ Timeout ({seconds}s) pour {getattr(proc, 'file_basename', '?')}. Arrêt en cours…"
                    )
                except Exception:
                    pass
                try:
                    if proc.state() != QProcess.NotRunning:
                        proc.terminate()
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
                # Délai de grâce puis kill forcé
                grace = QTimer(self)
                grace.setSingleShot(True)

                def _force_kill(p=proc):
                    if p.state() != QProcess.NotRunning:
                        try:
                            self.log.append(
                                f"🛑 Arrêt forcé du processus {getattr(p, 'file_basename', '?')} après délai de grâce."
                            )
                        except Exception:
                            pass
                        # Kill full process tree if possible
                        try:
                            pid2 = int(p.processId())
                        except Exception:
                            pid2 = None
                        if pid2:
                            _kill_process_tree(pid2, timeout=3.0, log=self.log.append)
                        try:
                            p.kill()
                        except Exception:
                            pass

                grace.timeout.connect(_force_kill)
                grace.start(10000)  # 10s grâce
                proc._grace_kill_timer = grace

            t.timeout.connect(_on_timeout)
            t.start(int(timeout_sec * 1000))
            process._timeout_timer = t

            def _cancel_timer(_ec, _es, timer=t):
                try:
                    timer.stop()
                except Exception:
                    pass

            process.finished.connect(_cancel_timer)
    except Exception:
        pass
    process.start()


def handle_stdout(self, process):
    """
    Gestionnaire pour la sortie standard du processus de compilation.

    Cette fonction traite les données de sortie standard, interprète les
    événements JSON Lines pour la progression déterministe, gère le pont
    UI pour les moteurs externes, et détecte la fin de compilation Nuitka.

    Args:
        self: Instance de la classe principale (GUI)
        process: Objet QProcess du processus en cours

    Returns:
        None
    """
    # ========================================================================
    # Lecture des données stdout du processus
    # ========================================================================
    data = process.readAllStandardOutput().data().decode()

    # ========================================================================
    # Traitement des événements JSON Lines
    # ========================================================================
    # Les moteurs peuvent envoyer des événements structurés en JSON Lines
    # pour indiquer la progression, afficher des messages, ou créer des widgets UI
    try:
        for line in data.splitlines():
            lt = line.strip()
            if lt.startswith("{") and lt.endswith("}"):
                try:
                    evt = json.loads(lt)
                    if isinstance(evt, dict):
                        # ========================================================================
                        # Événements de progression
                        # ========================================================================
                        # Format: {"progress": {"current": 1, "total": 10}}
                        prog = evt.get("progress")
                        if isinstance(prog, dict):
                            cur = prog.get("current")
                            total = prog.get("total")
                            if (
                                isinstance(cur, int)
                                and isinstance(total, int)
                                and total > 0
                            ):
                                self.progress.setRange(0, total)
                                self.progress.setValue(min(cur, total))

                        # ========================================================================
                        # Événements d'étape (stage)
                        # ========================================================================
                        # Format: {"stage": "Analyse des imports..."}
                        stage = evt.get("stage")
                        if isinstance(stage, str) and stage:
                            self.log.append(f"⏩ {stage}")

                        # ========================================================================
                        # Pont UI pour les moteurs externes/binaires
                        # ========================================================================
                        # Les moteurs peuvent demander l'affichage de widgets via JSON
                        ui_req = evt.get("ui")
                        if isinstance(ui_req, dict):
                            try:
                                # ========================================================================
                                # Fonction helper pour envoyer des événements au moteur
                                # ========================================================================
                                def _emit_event(
                                    ev: str, wid: str, payload: dict | None = None
                                ):
                                    try:
                                        resp = {
                                            "ui": {
                                                "type": "event",
                                                "id": wid,
                                                "event": ev,
                                            }
                                        }
                                        if payload:
                                            resp["ui"]["payload"] = payload
                                        payload_bytes = (
                                            json.dumps(resp, ensure_ascii=False) + "\n"
                                        ).encode("utf-8")
                                        process.write(payload_bytes)
                                        process.flush()
                                    except Exception:
                                        pass

                                # ========================================================================
                                # 1) Boîtes de message (msg_box)
                                # ========================================================================
                                # Format: {"msg_box": {"type": "info|warn|error|question", "title": "...", "text": "...", "id": "..."}}
                                msg = ui_req.get("msg_box")
                                if isinstance(msg, dict):
                                    from PySide6.QtWidgets import QMessageBox as _QMB

                                    mtype = str(msg.get("type", "info")).lower()
                                    title = str(msg.get("title", "Information"))
                                    text = str(msg.get("text", ""))
                                    default_yes = bool(msg.get("default_yes", True))
                                    box = _QMB(self)
                                    box.setText(text)
                                    box.setWindowTitle(title)
                                    if mtype in ("warn", "warning"):
                                        box.setIcon(_QMB.Warning)
                                    elif mtype in ("error", "critical"):
                                        box.setIcon(_QMB.Critical)
                                    elif mtype in ("question", "ask"):
                                        box.setIcon(_QMB.Question)
                                    else:
                                        box.setIcon(_QMB.Information)
                                    if mtype in ("question", "ask"):
                                        btns = _QMB.Yes | _QMB.No
                                        box.setStandardButtons(btns)
                                        box.setDefaultButton(
                                            _QMB.Yes if default_yes else _QMB.No
                                        )
                                    else:
                                        box.setStandardButtons(_QMB.Ok)
                                        box.setDefaultButton(_QMB.Ok)
                                    res = box.exec()
                                    result = (
                                        "yes"
                                        if (
                                            mtype in ("question", "ask")
                                            and res == _QMB.Yes
                                        )
                                        else (
                                            "no"
                                            if mtype in ("question", "ask")
                                            else "ok"
                                        )
                                    )
                                    resp = {
                                        "ui": {
                                            "type": "msg_box",
                                            "id": msg.get("id"),
                                            "result": result,
                                        }
                                    }
                                    try:
                                        payload = (
                                            json.dumps(resp, ensure_ascii=False) + "\n"
                                        ).encode("utf-8")
                                        process.write(payload)
                                        process.flush()
                                    except Exception:
                                        pass

                                # ========================================================================
                                # 2) Widgets dynamiques (label, button, checkbox, text)
                                # ========================================================================
                                # Format: {"widget": {"op": "add|set|remove", "id": "...", "type": "...", "props": {...}}}
                                widget = ui_req.get("widget")
                                if isinstance(widget, dict):
                                    try:
                                        op = widget.get("op")
                                        wid = str(widget.get("id", ""))
                                        if not wid:
                                            raise ValueError("missing widget id")
                                        engine_id = getattr(process, "_engine_id", None)
                                        if not engine_id:
                                            raise RuntimeError(
                                                "unknown engine id for process"
                                            )
                                        # Find dynamic area container
                                        cont = None
                                        try:
                                            tabs = getattr(self, "compiler_tabs", None)
                                            if tabs:
                                                for i in range(tabs.count()):
                                                    tw = tabs.widget(i)
                                                    if not tw:
                                                        continue
                                                    c = tw.findChild(
                                                        QWidget,
                                                        f"engine_dynamic_area_{engine_id}",
                                                    )
                                                    if c:
                                                        cont = c
                                                        break
                                        except Exception:
                                            cont = None
                                        if cont is None:
                                            raise RuntimeError("dynamic area not found")
                                        if not hasattr(self, "_external_ui_widgets"):
                                            self._external_ui_widgets = {}
                                        widgets = self._external_ui_widgets.setdefault(
                                            engine_id, {}
                                        )

                                        # ========================================================================
                                        # Fonction pour appliquer les propriétés au widget
                                        # ========================================================================
                                        def _apply_props(_w, props: dict):
                                            try:
                                                if "text" in props:
                                                    if isinstance(
                                                        _w, (QLabel, QPushButton)
                                                    ):
                                                        _w.setText(str(props["text"]))
                                                    elif isinstance(_w, QPlainTextEdit):
                                                        _w.setPlainText(
                                                            str(props["text"])
                                                        )
                                                if "placeholder" in props and hasattr(
                                                    _w, "setPlaceholderText"
                                                ):
                                                    _w.setPlaceholderText(
                                                        str(props["placeholder"])
                                                    )
                                                if "checked" in props and isinstance(
                                                    _w, QCheckBox
                                                ):
                                                    _w.setChecked(
                                                        bool(props["checked"])
                                                    )
                                                if "enabled" in props:
                                                    _w.setEnabled(
                                                        bool(props["enabled"])
                                                    )
                                                if "visible" in props:
                                                    _w.setVisible(
                                                        bool(props["visible"])
                                                    )
                                                if "tooltip" in props:
                                                    _w.setToolTip(str(props["tooltip"]))
                                            except Exception:
                                                pass

                                        lay = cont.layout()
                                        if op == "add":
                                            wtype = widget.get("type")
                                            props = widget.get("props") or {}
                                            w = None
                                            if wtype == "label":
                                                w = QLabel()
                                            elif wtype == "button":
                                                w = QPushButton()
                                            elif wtype == "checkbox":
                                                w = QCheckBox()
                                            elif wtype == "text":
                                                w = QPlainTextEdit()
                                            if w is not None:
                                                w.setObjectName(wid)
                                                _apply_props(w, props)
                                                if lay is not None:
                                                    lay.addWidget(w)
                                                widgets[wid] = w
                                                try:
                                                    if isinstance(w, QPushButton):
                                                        w.clicked.connect(
                                                            lambda checked=False, wid=wid: _emit_event(
                                                                "clicked", wid
                                                            )
                                                        )
                                                    elif isinstance(w, QCheckBox):
                                                        w.stateChanged.connect(
                                                            lambda _s, wid=wid, w=w: _emit_event(
                                                                "changed",
                                                                wid,
                                                                {
                                                                    "checked": w.isChecked()
                                                                },
                                                            )
                                                        )
                                                    elif isinstance(w, QPlainTextEdit):
                                                        w.textChanged.connect(
                                                            lambda wid=wid, w=w: _emit_event(
                                                                "changed",
                                                                wid,
                                                                {
                                                                    "text": w.toPlainText()[
                                                                        :5000
                                                                    ]
                                                                },
                                                            )
                                                        )
                                                except Exception:
                                                    pass
                                        elif op == "set":
                                            props = widget.get("props") or {}
                                            w = widgets.get(wid) or cont.findChild(
                                                QWidget, wid
                                            )
                                            if w is not None:
                                                _apply_props(w, props)
                                        elif op == "remove":
                                            w = widgets.pop(wid, None)
                                            if w is None:
                                                w = cont.findChild(QWidget, wid)
                                            if w is not None:
                                                try:
                                                    if lay is not None:
                                                        lay.removeWidget(w)
                                                except Exception:
                                                    pass
                                                w.deleteLater()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass

    # ========================================================================
    # Affichage des données brutes dans le journal
    # ========================================================================
    self.log.append(data)

    # ========================================================================
    # Détection de la fin de compilation Nuitka
    # ========================================================================
    # Nuitka affiche "Successfully created" quand la compilation est terminée
    if "Successfully created" in data or "Nuitka: Successfully created" in data:
        # Forcer la barre à 100% et sortir du mode animation
        self.progress.setRange(0, 1)
        self.progress.setValue(1)

        # S'assurer que le message est à la fin du log
        lines = data.strip().splitlines()
        for line in lines:
            if "Nuitka: Successfully created" in line or "Successfully created" in line:
                self.log.append(f"<b style='color:green'>{line}</b>")

        # Forcer la terminaison du process si besoin
        if process.state() != QProcess.NotRunning:
            self.log.append(
                "<span style='color:orange;'>ℹ️ Nuitka a signalé la fin de compilation dans le log, mais le process n'est pas terminé. Forçage du kill (arbre) et nettoyage UI...</span>"
            )
            try:
                pidx = int(process.processId())
            except Exception:
                pidx = None
            if pidx:
                _kill_process_tree(pidx, timeout=3.0, log=self.log.append)
            try:
                process.kill()
            except Exception:
                pass
            process.waitForFinished(2000)

            # Nettoyage manuel si le signal finished ne se déclenche pas
            if process in self.processes:
                self.handle_finished(process, 0, QProcess.NormalExit)

    # Note : La progression Nuitka (--show-progress) est désactivée
    # La barre reste indéterminée pendant toute la compilation
    try:
        for line in data.splitlines():
            lt = line.strip()
            if lt.startswith("{") and lt.endswith("}"):
                try:
                    evt = json.loads(lt)
                    if isinstance(evt, dict):
                        prog = evt.get("progress")
                        if isinstance(prog, dict):
                            cur = prog.get("current")
                            total = prog.get("total")
                            if (
                                isinstance(cur, int)
                                and isinstance(total, int)
                                and total > 0
                            ):
                                self.progress.setRange(0, total)
                                self.progress.setValue(min(cur, total))
                        stage = evt.get("stage")
                        if isinstance(stage, str) and stage:
                            self.log.append(f"⏩ {stage}")
                        # UI bridge for external/binary engines: handle simple UI requests via JSON lines
                        ui_req = evt.get("ui")
                        if isinstance(ui_req, dict):
                            try:
                                # Helper to emit UI events back to the engine
                                def _emit_event(
                                    ev: str, wid: str, payload: dict | None = None
                                ):
                                    try:
                                        resp = {
                                            "ui": {
                                                "type": "event",
                                                "id": wid,
                                                "event": ev,
                                            }
                                        }
                                        if payload:
                                            resp["ui"]["payload"] = payload
                                        payload_bytes = (
                                            json.dumps(resp, ensure_ascii=False) + "\n"
                                        ).encode("utf-8")
                                        process.write(payload_bytes)
                                        process.flush()
                                    except Exception:
                                        pass

                                # 1) Message boxes {type,title,text,default_yes,id}
                                msg = ui_req.get("msg_box")
                                if isinstance(msg, dict):
                                    from PySide6.QtWidgets import QMessageBox as _QMB

                                    mtype = str(msg.get("type", "info")).lower()
                                    title = str(msg.get("title", "Information"))
                                    text = str(msg.get("text", ""))
                                    default_yes = bool(msg.get("default_yes", True))
                                    box = _QMB(self)
                                    box.setText(text)
                                    box.setWindowTitle(title)
                                    if mtype in ("warn", "warning"):
                                        box.setIcon(_QMB.Warning)
                                    elif mtype in ("error", "critical"):
                                        box.setIcon(_QMB.Critical)
                                    elif mtype in ("question", "ask"):
                                        box.setIcon(_QMB.Question)
                                    else:
                                        box.setIcon(_QMB.Information)
                                    if mtype in ("question", "ask"):
                                        btns = _QMB.Yes | _QMB.No
                                        box.setStandardButtons(btns)
                                        box.setDefaultButton(
                                            _QMB.Yes if default_yes else _QMB.No
                                        )
                                    else:
                                        box.setStandardButtons(_QMB.Ok)
                                        box.setDefaultButton(_QMB.Ok)
                                    res = box.exec()
                                    result = (
                                        "yes"
                                        if (
                                            mtype in ("question", "ask")
                                            and res == _QMB.Yes
                                        )
                                        else (
                                            "no"
                                            if mtype in ("question", "ask")
                                            else "ok"
                                        )
                                    )
                                    resp = {
                                        "ui": {
                                            "type": "msg_box",
                                            "id": msg.get("id"),
                                            "result": result,
                                        }
                                    }
                                    try:
                                        payload = (
                                            json.dumps(resp, ensure_ascii=False) + "\n"
                                        ).encode("utf-8")
                                        process.write(payload)
                                        process.flush()
                                    except Exception:
                                        pass

                                # 2) Dynamic widgets {widget:{op,id,type?,props?}}
                                widget = ui_req.get("widget")
                                if isinstance(widget, dict):
                                    try:
                                        op = widget.get("op")
                                        wid = str(widget.get("id", ""))
                                        if not wid:
                                            raise ValueError("missing widget id")
                                        engine_id = getattr(process, "_engine_id", None)
                                        if not engine_id:
                                            raise RuntimeError(
                                                "unknown engine id for process"
                                            )
                                        # Find dynamic area container
                                        cont = None
                                        try:
                                            tabs = getattr(self, "compiler_tabs", None)
                                            if tabs:
                                                for i in range(tabs.count()):
                                                    tw = tabs.widget(i)
                                                    if not tw:
                                                        continue
                                                    c = tw.findChild(
                                                        QWidget,
                                                        f"engine_dynamic_area_{engine_id}",
                                                    )
                                                    if c:
                                                        cont = c
                                                        break
                                        except Exception:
                                            cont = None
                                        if cont is None:
                                            raise RuntimeError("dynamic area not found")
                                        if not hasattr(self, "_external_ui_widgets"):
                                            self._external_ui_widgets = {}
                                        widgets = self._external_ui_widgets.setdefault(
                                            engine_id, {}
                                        )

                                        def _apply_props(_w, props: dict):
                                            try:
                                                if "text" in props:
                                                    if isinstance(
                                                        _w, (QLabel, QPushButton)
                                                    ):
                                                        _w.setText(str(props["text"]))
                                                    elif isinstance(_w, QPlainTextEdit):
                                                        _w.setPlainText(
                                                            str(props["text"])
                                                        )
                                                if "placeholder" in props and hasattr(
                                                    _w, "setPlaceholderText"
                                                ):
                                                    _w.setPlaceholderText(
                                                        str(props["placeholder"])
                                                    )
                                                if "checked" in props and isinstance(
                                                    _w, QCheckBox
                                                ):
                                                    _w.setChecked(
                                                        bool(props["checked"])
                                                    )
                                                if "enabled" in props:
                                                    _w.setEnabled(
                                                        bool(props["enabled"])
                                                    )
                                                if "visible" in props:
                                                    _w.setVisible(
                                                        bool(props["visible"])
                                                    )
                                                if "tooltip" in props:
                                                    _w.setToolTip(str(props["tooltip"]))
                                            except Exception:
                                                pass

                                        lay = cont.layout()
                                        if op == "add":
                                            wtype = widget.get("type")
                                            props = widget.get("props") or {}
                                            w = None
                                            if wtype == "label":
                                                w = QLabel()
                                            elif wtype == "button":
                                                w = QPushButton()
                                            elif wtype == "checkbox":
                                                w = QCheckBox()
                                            elif wtype == "text":
                                                w = QPlainTextEdit()
                                            if w is not None:
                                                w.setObjectName(wid)
                                                _apply_props(w, props)
                                                if lay is not None:
                                                    lay.addWidget(w)
                                                widgets[wid] = w
                                                try:
                                                    if isinstance(w, QPushButton):
                                                        w.clicked.connect(
                                                            lambda checked=False, wid=wid: _emit_event(
                                                                "clicked", wid
                                                            )
                                                        )
                                                    elif isinstance(w, QCheckBox):
                                                        w.stateChanged.connect(
                                                            lambda _s, wid=wid, w=w: _emit_event(
                                                                "changed",
                                                                wid,
                                                                {
                                                                    "checked": w.isChecked()
                                                                },
                                                            )
                                                        )
                                                    elif isinstance(w, QPlainTextEdit):
                                                        w.textChanged.connect(
                                                            lambda wid=wid, w=w: _emit_event(
                                                                "changed",
                                                                wid,
                                                                {
                                                                    "text": w.toPlainText()[
                                                                        :5000
                                                                    ]
                                                                },
                                                            )
                                                        )
                                                except Exception:
                                                    pass
                                        elif op == "set":
                                            props = widget.get("props") or {}
                                            w = widgets.get(wid) or cont.findChild(
                                                QWidget, wid
                                            )
                                            if w is not None:
                                                _apply_props(w, props)
                                        elif op == "remove":
                                            w = widgets.pop(wid, None)
                                            if w is None:
                                                w = cont.findChild(QWidget, wid)
                                            if w is not None:
                                                try:
                                                    if lay is not None:
                                                        lay.removeWidget(w)
                                                except Exception:
                                                    pass
                                                w.deleteLater()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                except Exception:
                    pass
    except Exception:
        pass
    self.log.append(data)

    # Détection de la fin Nuitka dans le log
    if "Successfully created" in data or "Nuitka: Successfully created" in data:
        # Forcer la barre à 100% et sortir du mode animation
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        # S'assurer que le message est à la fin du log
        lines = data.strip().splitlines()
        for line in lines:
            if "Nuitka: Successfully created" in line or "Successfully created" in line:
                self.log.append(f"<b style='color:green'>{line}</b>")
        # Forcer la terminaison du process si besoin
        if process.state() != QProcess.NotRunning:
            self.log.append(
                "<span style='color:orange;'>ℹ️ Nuitka a signalé la fin de compilation dans le log, mais le process n'est pas terminé. Forçage du kill (arbre) et nettoyage UI...</span>"
            )
            try:
                pidx = int(process.processId())
            except Exception:
                pidx = None
            if pidx:
                _kill_process_tree(pidx, timeout=3.0, log=self.log.append)
            try:
                process.kill()
            except Exception:
                pass
            process.waitForFinished(2000)
            # Nettoyage manuel si le signal finished ne se déclenche pas
            if process in self.processes:
                self.handle_finished(process, 0, QProcess.NormalExit)
    # --- Progression Nuitka (--show-progress) ---
    # Désormais, la barre reste indéterminée pendant toute la compilation
    # (aucune mise à jour de valeur ici)


def handle_stderr(self, process):
    """
    Gestionnaire pour la sortie d'erreur du processus de compilation.

    Cette fonction traite les données d'erreur standard et les affiche
    en rouge dans le journal de log.

    Args:
        self: Instance de la classe principale (GUI)
        process: Objet QProcess du processus en cours

    Returns:
        None
    """
    # ========================================================================
    # Lecture des données stderr du processus
    # ========================================================================
    # Les erreurs et warnings sont affichés en rouge dans le journal
    data = process.readAllStandardError().data().decode()
    self.log.append(f"<span style='color:red;'>{data}</span>")


def handle_finished(self, process, exit_code, exit_status):
    # Suppression de la réactivation ici (gérée à la toute fin dans try_start_processes)
    import time

    import psutil

    file = process.file_path
    file_basename = process.file_basename

    # Stop and dispose any timers attached to the process to avoid late callbacks
    try:
        t = getattr(process, "_timeout_timer", None)
        if t:
            try:
                t.stop()
            except Exception:
                pass
            try:
                t.deleteLater()
            except Exception:
                pass
    except Exception:
        pass
    try:
        g = getattr(process, "_grace_kill_timer", None)
        if g:
            try:
                g.stop()
            except Exception:
                pass
            try:
                g.deleteLater()
            except Exception:
                pass
    except Exception:
        pass
    # Cleanup cooperative cancellation sentinel if present
    try:
        cfile = getattr(process, "_cancel_file", None)
        if cfile and os.path.isfile(cfile):
            os.remove(cfile)
    except Exception:
        pass

    # Mesure du temps de compilation
    elapsed = None
    if hasattr(process, "_start_time"):
        elapsed = time.time() - process._start_time
        if not hasattr(self, "_compilation_times"):
            self._compilation_times = {}
        self._compilation_times[file_basename] = elapsed

    # Mesure mémoire (si psutil dispo)
    mem_info = None
    try:
        p = psutil.Process()
        mem_info = p.memory_info().rss / (1024 * 1024)
    except Exception:
        mem_info = None

    if exit_code == 0:
        msg = f"✅ {file_basename} compilé avec succès."
        if elapsed:
            msg += f" Temps de compilation : {elapsed:.2f} secondes."
        if mem_info:
            msg += f" Mémoire utilisée (processus GUI) : {mem_info:.1f} Mo."
        # Suppression de la vérification stricte du dossier/fichier de sortie
        self.log.append(msg + "\n")
        self.log.append(
            "<span style='color:#7faaff;'>ℹ️ Certains messages d’erreur ou de warning peuvent apparaître dans les logs, mais si l’exécutable fonctionne, ils ne sont pas bloquants.</span>\n"
        )
        # Enregistrer un callback différé on_success du moteur, exécuté après ACASL
        try:
            eng_from_proc = getattr(process, "_engine_id", None)
            if eng_from_proc:
                # Créer une instance moteur dédiée pour le hook (stateless)
                try:
                    engine_obj = engines_loader.registry.create(eng_from_proc)
                except Exception:
                    engine_obj = None
                if engine_obj is not None:
                    if not hasattr(self, "_pending_engine_success_hooks"):
                        self._pending_engine_success_hooks = []
                    # Stocker (engine_obj, file) pour exécution post-ACASL
                    self._pending_engine_success_hooks.append((engine_obj, file))
        except Exception:
            pass
        # Trace du dernier fichier réussi par moteur (utilisé par ACASL)
        try:
            if not hasattr(self, "_last_success_files"):
                self._last_success_files = {}
            eng_from_proc = getattr(process, "_engine_id", None)
            if eng_from_proc:
                self._last_success_files[eng_from_proc] = file
                self._last_success_engine_id = eng_from_proc
        except Exception:
            pass
    else:
        # Ajout d'un affichage détaillé pour les erreurs inattendues
        # Use saved stderr data to avoid accessing deleted C++ object
        error_details = getattr(process, "_final_stderr", "")
        self.log.append(
            f"<span style='color:red;'>❌ La compilation de {file_basename} ({file}) a échoué (code {exit_code}).</span>\n"
        )
        if error_details:
            self.log.append(
                f"<span style='color:red;'>Détails de l'erreur :<br><pre>{error_details}</pre></span>"
            )
        try:
            self.show_error_dialog(file_basename, file, exit_code, error_details)

            # Auto-install modules manquants si activé
            if self.opt_auto_install.isChecked():
                self.try_install_missing_modules(process)

        except:
            pass
    if process in self.processes:
        self.processes.remove(process)
    if file in self.current_compiling:
        self.current_compiling.remove(file)

    # Ne pas toucher à la barre ici : elle sera gérée dans try_start_processes

    # Si toutes les compilations sont terminées, afficher un résumé
    if not self.processes and not self.queue and hasattr(self, "_compilation_times"):
        self.log.append("\n<b>Résum�� des performances :</b>")
        total = 0
        for fname, t in self._compilation_times.items():
            self.log.append(f"- {fname} : {t:.2f} secondes")
            total += t
        self.log.append(f"<b>Temps total de compilation :</b> {total:.2f} secondes\n")

    # Essaye de lancer d’autres compilations dans la file d’attente
    self.try_start_processes()


def try_install_missing_modules(self, process):
    output = process.readAllStandardError().data().decode()
    missing_modules = re.findall(r"No module named '([\w\d_]+)'", output)
    if not hasattr(self, "_already_tried_modules"):
        self._already_tried_modules = set()
    if not hasattr(self, "_install_report"):
        self._install_report = []
    if missing_modules:
        # Use venv_manager to get the correct pip path
        venv_manager = getattr(self, "venv_manager", None)
        if venv_manager:
            venv_path = venv_manager.resolve_project_venv()
            if venv_path:
                pip_exe = venv_manager.pip_path(venv_path)
            else:
                # Fallback to hardcoded path
                pip_exe = os.path.join(
                    self.workspace_dir,
                    "venv",
                    "Scripts" if platform.system() == "Windows" else "bin",
                    "pip",
                )
        else:
            # Fallback to hardcoded path
            pip_exe = os.path.join(
                self.workspace_dir,
                "venv",
                "Scripts" if platform.system() == "Windows" else "bin",
                "pip",
            )
        all_installed = True
        new_modules = [
            m for m in missing_modules if m not in self._already_tried_modules
        ]
        if not new_modules:
            self.log.append(
                "❌ Boucle d'installation stoppée : mêmes modules manquants détectés à nouveau."
            )
            self.log.append("Rapport final :")
            for line in self._install_report:
                self.log.append(line)
            self._already_tried_modules.clear()
            self._install_report.clear()
            return
        for module in new_modules:
            self._already_tried_modules.add(module)
            self.log.append(
                f"📦 Tentative d'installation du module manquant : {module}"
            )
            try:
                subprocess.run([pip_exe, "install", module], check=True)
                msg = f"✅ Module {module} installé avec succès."
                self.log.append(msg)
                self._install_report.append(msg)
            except Exception as e:
                msg = f"❌ Échec d'installation de {module} : {e}"
                self.log.append(msg)
                self._install_report.append(msg)
                all_installed = False
        # Relancer la compilation après installation, si tout s'est bien passé
        if all_installed:
            reply = QMessageBox.question(
                self,
                self.tr("Relancer la compilation", "Restart build"),
                self.tr(
                    "Des modules manquants ont été installés. Voulez-vous relancer la compilation de ce fichier ?",
                    "Missing modules were installed. Do you want to restart the build for this file?",
                ),
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.log.append(
                    "🔁 Relance de la compilation après installation des modules manquants..."
                )
                self.queue.insert(0, process.file_path)
                self.try_start_processes()
            else:
                self.log.append(
                    "⏹️ Compilation non relancée après installation des modules. Rapport final :"
                )
                for line in self._install_report:
                    self.log.append(line)
                self._already_tried_modules.clear()
                self._install_report.clear()
        else:
            self.log.append(
                "❌ Certains modules n'ont pas pu être installés. Compilation non relancée."
            )
            self.log.append("Rapport final :")
            for line in self._install_report:
                self.log.append(line)
            self._already_tried_modules.clear()
            self._install_report.clear()
    else:
        # Si plus de modules manquants, afficher le rapport final
        if hasattr(self, "_install_report") and self._install_report:
            self.log.append("Rapport final :")
            for line in self._install_report:
                self.log.append(line)
            self._already_tried_modules.clear()
            self._install_report.clear()


def show_error_dialog(
    self, filename, filepath=None, exit_code=None, error_details=None
):
    # Mode silencieux : ne rien afficher si la case est cochée
    if hasattr(self, "opt_silent_errors") and self.opt_silent_errors.isChecked():
        return
    dlg = QMessageBox(self)
    dlg.setWindowTitle(self.tr("Erreur de compilation", "Build error"))
    base = self.tr(
        "La compilation de {filename} a échoué.", "Build of {filename} failed."
    )
    msg = base.format(filename=filename)
    if filepath:
        msg += f"\n{self.tr('Fichier', 'File')} : {filepath}"
    if exit_code is not None:
        msg += "\n{} : {}".format(self.tr("Code d'erreur", "Error code"), exit_code)
    if error_details:
        msg += f"\n\n{self.tr('Détails techniques', 'Technical details')} :\n{error_details}"
    dlg.setText(msg)
    dlg.setIcon(QMessageBox.Icon.Critical)
    dlg.exec()


def cancel_all_compilations(self):
    # Flag to prevent new spawns during hard cancel
    try:
        self._closing = True
    except Exception:
        pass
    # Stop background venv tasks if any
    try:
        if hasattr(self, "venv_manager") and self.venv_manager:
            self.venv_manager.terminate_tasks()
    except Exception:
        pass
    # Stop BCASL (pre-compile) threads/processes explicitly
    try:
        from bcasl.Loader import ensure_bcasl_thread_stopped

        ensure_bcasl_thread_stopped(self)
    except Exception:
        pass
    errors = []
    # Kill all known QProcesses immediately and their trees
    for process in self.processes[:]:
        try:
            # Cooperative cancel sentinel
            try:
                cfile = getattr(process, "_cancel_file", None)
                if cfile:
                    os.makedirs(os.path.dirname(cfile), exist_ok=True)
                    with open(cfile, "w", encoding="utf-8") as _f:
                        _f.write("1")
            except Exception:
                pass
            # Kill process tree fast
            try:
                pid = int(process.processId())
            except Exception:
                pid = None
            if pid:
                _kill_process_tree(pid, timeout=1.0, log=self.log.append)
            # Ensure QProcess object is stopped as well
            try:
                if process.state() != QProcess.NotRunning:
                    process.kill()
                    process.waitForFinished(1000)
            except Exception:
                pass
        except Exception as e:
            errors.append(str(e))
            self.log.append(f"❌ Erreur lors de l'arrêt d'un process : {e}")
        # Remove from list idempotently
        if process in self.processes:
            try:
                self.processes.remove(process)
            except ValueError:
                pass
    # ACASL removed: no post-compile thread to stop
    try:
        _kill_all_descendants(timeout=1.0, log=self.log.append)
    except Exception:
        pass
    # Clear any pending queue and UI state
    self.queue.clear()
    self.current_compiling.clear()
    try:
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
    except Exception:
        pass
    self.set_controls_enabled(True)
    if errors:
        self.log.append(
            "❌ Certains processus n'ont pas pu être arrêtés (voir erreurs ci-dessus)."
        )
    else:
        self.log.append(
            "⛔ Toutes les compilations ont été annulées et tous les processus enfants tués.\n"
        )
