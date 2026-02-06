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
PyCompiler ARK - Compiler Core Module

Module principal du compilateur pour PyCompiler ARK.
Gère l'exécution des processus de compilation avec support threading
et communication en temps réel avec l'interface utilisateur.

Classes principales:
- CompilerCore: Classe principale du compilateur
- CompilationThread: Thread pour exécution non-bloquante
- MainProcess: Processus principal de compilation
- ProcessKiller: Gestion des processus

Fonctions:
- kill_process: Tue un processus
- kill_process_tree: Tue un processus et ses enfants
- build_command: Construit une commande de compilation
- validate_command: Valide une commande de compilation

Note: Les fonctions de command_helpers.py ont été intégrées dans mainprocess.py
      pour supporter l'intégration avec ArkConfigManager pour les exclusions.
"""

from __future__ import annotations

# ============================================================================
# IMPORTS STANDARD
# ============================================================================
import os
import sys
from typing import Optional

# ============================================================================
# IMPORTS TIERS (PySide6)
# ============================================================================
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QMessageBox

# ============================================================================
# IMPORTS LOCAUX - Core.Compiler
# ============================================================================

# Importations de compiler.py
from Core.Compiler.compiler import (
    CompilationStatus,
    CompilationSignals,
    CompilationThread,
    CompilerCore,
)

# Importations de mainprocess.py
from Core.Compiler.mainprocess import (
    ProcessState,
    MainProcessSignals,
    MainProcess,
    # Fonctions intégrées depuis l'ancien command_helpers.py
    build_command,
    validate_command,
    escape_arguments,
    sanitize_path,
    CommandBuilder,
    detect_python_executable,
    get_interpreter_version,
    check_module_available,
)

# Importations de process_killer.py
from Core.Compiler.process_killer import (
    ProcessInfo,
    ProcessKiller,
    kill_process,
    kill_process_tree,
    get_process_info,
)

# Importations de EngineLoader
from EngineLoader.registry import get_engine, create

__all__ = [
    # compiler.py
    "CompilationStatus",
    "CompilationSignals",
    "CompilationThread",
    "CompilerCore",
    # mainprocess.py
    "ProcessState",
    "MainProcessSignals",
    "MainProcess",
    # Fonctions de construction de commande (intégrées depuis command_helpers.py)
    "build_command",
    "validate_command",
    "escape_arguments",
    "sanitize_path",
    "CommandBuilder",
    "detect_python_executable",
    "get_interpreter_version",
    "check_module_available",
    # process_killer.py
    "ProcessInfo",
    "ProcessKiller",
    "kill_process",
    "kill_process_tree",
    "get_process_info",
    # UI Connection functions
    "compile_all",
    "cancel_all_compilations",
    "handle_stdout",
    "handle_stderr",
    "handle_finished",
    "show_error_dialog",
    "try_install_missing_modules",
    "start_compilation_process",
    "try_start_processes",
    "_continue_compile_all",
]

__version__ = "1.0.0"
__author__ = "Ague Samuel Amen"


# ============================================================================
# FONCTIONS DE CONNEXION UI - PyCompiler ARK
# ============================================================================
# Ces fonctions connectent les boutons de l'interface utilisateur
# (compile_btn, cancel_btn) au système de compilation Core/Compiler
# ============================================================================


# Instance globale de MainProcess (initialisée par PyCompilerArkGui)
_main_process: Optional[MainProcess] = None


def _get_main_process() -> MainProcess:
    """Retourne l'instance de MainProcess, en la créant si nécessaire."""
    global _main_process
    if _main_process is None:
        _main_process = MainProcess()
    return _main_process


def compile_all(self) -> None:
    """
    Slot connected to the compile button.
    Starts compilation for all selected Python files.
    """
    # Vérifier les fichiers sélectionnés
    files_to_compile = self.python_files.copy()
    if not files_to_compile:
        self.log_i18n(
            "⚠️ Aucun fichier Python sélectionné.", "⚠️ No Python files selected."
        )
        return

    # Vérifier le workspace
    if not self.workspace_dir:
        self.log_i18n("⚠️ Aucun workspace sélectionné.", "⚠️ No workspace selected.")
        return

    # Obtenir le moteur de compilation actif
    engine_id = None
    try:
        import EngineLoader as engines_loader

        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception as e:
        self.log_i18n(
            f"⚠️ Erreur détection moteur: {e}", f"⚠️ Engine detection error: {e}"
        )

    if not engine_id:
        engine_id = "pyinstaller"  # Moteur par défaut

    # Obtenir le moteur (instance)
    try:
        engine = create(engine_id)
    except Exception as e:
        self.log_i18n(
            f"❌ Erreur création moteur '{engine_id}': {e}",
            f"❌ Engine creation error '{engine_id}': {e}",
        )
        return

    self.log_i18n(
        f"🚀 Démarrage de la compilation avec {engine.name}...",
        f"🚀 Starting compilation with {engine.name}...",
    )

    # Initialiser MainProcess si nécessaire
    main_process = _get_main_process()
    main_process.set_workspace(self.workspace_dir)
    main_process.set_engine(engine_id)

    # Désactiver les contrôles pendant la compilation
    self.set_controls_enabled(False)

    # Compiler chaque fichier
    _start_compilation_queue(self, engine, files_to_compile)


def _start_compilation_queue(self, engine, files_to_compile: list) -> None:
    """Démarre la compilation d'une file de fichiers."""
    main_process = _get_main_process()

    # Connecter les signaux de MainProcess si pas déjà fait
    if not hasattr(main_process, "_gui_connected"):
        main_process.output_ready.connect(lambda msg: _handle_output(self, msg))
        main_process.error_ready.connect(lambda msg: _handle_error(self, msg))
        main_process.progress_update.connect(
            lambda pct, msg: _handle_progress(self, pct, msg)
        )
        main_process.log_message.connect(
            lambda level, msg: _handle_log(self, level, msg)
        )
        main_process.compilation_started.connect(
            lambda info: _handle_compilation_started(self, info)
        )
        main_process.compilation_finished.connect(
            lambda code, info: handle_finished(self, code, info)
        )
        main_process.state_changed.connect(
            lambda state: _handle_state_changed(self, state)
        )
        main_process._gui_connected = True

    # Charger les patterns d'exclusion depuis ArkConfigManager
    exclusion_patterns = main_process.get_exclusion_patterns()
    excluded_count = 0

    # Compiler chaque fichier avec vérification des exclusions
    for file_path in files_to_compile:
        # Vérifier si le fichier doit être exclu
        if main_process.should_exclude(file_path):
            self.log_i18n(
                f"⏩ Fichier exclu: {os.path.basename(file_path)}",
                f"⏩ File excluded: {os.path.basename(file_path)}",
            )
            excluded_count += 1
            continue

        if not os.path.exists(file_path):
            self.log_i18n(
                f"⚠️ Fichier non trouvé: {file_path}", f"⚠️ File not found: {file_path}"
            )
            continue

        # Vérifier les prérequis du moteur
        if hasattr(engine, "ensure_tools_installed"):
            if not engine.ensure_tools_installed(self):
                self.log_i18n(
                    "⚠️ Outils manquants, compilation annulée.",
                    "⚠️ Missing tools, compilation cancelled.",
                )
                self.set_controls_enabled(True)
                return

        # Construire la commande
        cmd = engine.build_command(self, file_path)
        if not cmd:
            self.log_i18n(
                f"❌ Erreur construction commande pour {file_path}",
                f"❌ Command build error for {file_path}",
            )
            continue

        # Obtenir l'environnement
        env = engine.environment() if hasattr(engine, "environment") else None

        # Lancer la compilation
        program = cmd[0]
        args = cmd[1:]

        main_process.compile(
            program=program,
            args=args,
            env=env,
            engine_id=engine.id,
            file_path=file_path,
            workspace_dir=self.workspace_dir,
        )

        self.log_i18n(
            f"📦 Compilation de {os.path.basename(file_path)}...",
            f"📦 Compiling {os.path.basename(file_path)}...",
        )

        # break  # Un seul fichier à la fois pour l'instant

    # Afficher le résumé des exclusions
    if excluded_count > 0:
        self.log_i18n(
            f"⏩ {excluded_count} fichier(s) exclu(s) selon les patterns de ARK_Main_Config.yml",
            f"⏩ {excluded_count} file(s) excluded according to ARK_Main_Config.yml patterns",
        )


def cancel_all_compilations(self) -> bool:
    """
    Slot connected to the cancel button.
    Cancels all ongoing compilations.
    """
    main_process = _get_main_process()

    if main_process.is_compiling:
        success = main_process.cancel()
        if success:
            self.log_i18n(
                "⏹️ Annulation de la compilation demandée...",
                "⏹️ Compilation cancellation requested...",
            )
        else:
            self.log_i18n(
                "⚠️ Impossible d'annuler la compilation.",
                "⚠️ Unable to cancel compilation.",
            )
        return success
    else:
        self.log_i18n("ℹ️ Aucune compilation en cours.", "ℹ️ No compilation in progress.")
        return False


def handle_stdout(self, proc: QProcess) -> None:
    """Handle stdout from a QProcess (legacy method)."""
    data = proc.readAllStandardOutput()
    if data.isEmpty():
        return
    try:
        text = bytes(data).decode("utf-8", errors="replace").strip()
        if text:
            self.log.append(text)
    except Exception:
        pass


def handle_stderr(self, proc: QProcess) -> None:
    """Handle stderr from a QProcess (legacy method)."""
    data = proc.readAllStandardError()
    if data.isEmpty():
        return
    try:
        text = bytes(data).decode("utf-8", errors="replace").strip()
        if text:
            self.log.append(f"❌ {text}")
    except Exception:
        pass


def show_error_dialog(self, title: str, message: str) -> None:
    """Show an error dialog."""
    QMessageBox.critical(self, self.tr("Erreur", "Error"), message)


def try_install_missing_modules(self, modules: list) -> bool:
    """
    Try to install missing Python modules.
    Returns True if installation succeeded or no install needed.
    """
    if not modules:
        return True

    self.log_i18n(
        f"📦 Installation des modules manquants: {modules}",
        f"📦 Installing missing modules: {modules}",
    )

    # Delegates to venv_manager
    if hasattr(self, "venv_manager") and self.venv_manager:
        venv_path = self.venv_manager.resolve_project_venv()
        if venv_path:
            return self.venv_manager.ensure_tools_installed(venv_path, modules)

    return False


def start_compilation_process(self, engine_id: str, file_path: str) -> bool:
    """
    Start a single compilation process using MainProcess.

    Args:
        self: GUI instance
        engine_id: ID of the compilation engine
        file_path: Path to the Python file to compile

    Returns:
        True if compilation started, False otherwise
    """
    # Obtenir le moteur (instance)
    try:
        engine = create(engine_id)
    except Exception as e:
        self.log_i18n(
            f"❌ Erreur création moteur '{engine_id}': {e}",
            f"❌ Engine creation error '{engine_id}': {e}",
        )
        return False

    # Vérifier les prérequis
    if not engine.ensure_tools_installed(self):
        return False

    # Construire la commande
    cmd = engine.build_command(self, file_path)
    if not cmd:
        self.log_i18n(
            f"❌ Erreur construction commande pour {file_path}",
            f"❌ Command build error for {file_path}",
        )
        return False

    # Obtenir l'environnement
    env = engine.environment() if hasattr(engine, "environment") else None

    # Initialiser MainProcess
    main_process = _get_main_process()
    main_process.set_workspace(self.workspace_dir)
    main_process.set_engine(engine_id)

    # Connecter les signaux si pas déjà fait
    if not hasattr(main_process, "_gui_connected"):
        main_process.output_ready.connect(lambda msg: _handle_output(self, msg))
        main_process.error_ready.connect(lambda msg: _handle_error(self, msg))
        main_process.progress_update.connect(
            lambda pct, msg: _handle_progress(self, pct, msg)
        )
        main_process.log_message.connect(
            lambda level, msg: _handle_log(self, level, msg)
        )
        main_process.compilation_finished.connect(
            lambda code, info: handle_finished(self, code, info)
        )
        main_process.state_changed.connect(
            lambda state: _handle_state_changed(self, state)
        )
        main_process._gui_connected = True

    # Lancer la compilation
    program = cmd[0]
    args = cmd[1:]

    success = main_process.compile(
        program=program,
        args=args,
        env=env,
        engine_id=engine_id,
        file_path=file_path,
        workspace_dir=self.workspace_dir,
    )

    if success:
        self.log_i18n(
            f"🚀 Démarrage {engine.name} pour {os.path.basename(file_path)}...",
            f"🚀 Starting {engine.name} for {os.path.basename(file_path)}...",
        )

    return success


def try_start_processes(self) -> bool:
    """
    Try to start compilation processes for all selected files.
    Returns True if at least one process started.
    """
    if not self.python_files:
        self.log_i18n("⚠️ Aucun fichier à compiler.", "⚠️ No files to compile.")
        return False

    # Obtenir le moteur actif
    engine_id = None
    try:
        import EngineLoader as engines_loader

        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception:
        pass

    if not engine_id:
        engine_id = "pyinstaller"

    # Compiler le premier fichier
    return start_compilation_process(self, engine_id, self.python_files[0])


def _continue_compile_all(self) -> None:
    """
    Continue compilation of remaining files after one completes.
    Called from handle_finished when a compilation succeeds.
    """
    # Cette fonction est appelée après chaque compilation réussie
    # Elle peut être utilisée pour compiler les fichiers suivants en file d'attente
    pass


def _handle_output(self, message: str) -> None:
    """Handle output from MainProcess."""
    if message:
        self.log.append(message)


def _handle_compilation_started(self, info: dict) -> None:
    """Handle compilation started signal from MainProcess."""
    file_path = info.get("file", "")
    engine = info.get("engine", "")
    if file_path and engine:
        self.log_i18n(
            f"🚀 Démarrage compilation: {os.path.basename(file_path)} avec {engine}",
            f"🚀 Starting compilation: {os.path.basename(file_path)} with {engine}",
        )


def _handle_error(self, message: str) -> None:
    """Handle error output from MainProcess."""
    if message:
        self.log.append(f"❌ {message}")


def _handle_progress(self, progress: int, message: str) -> None:
    """Handle progress update from MainProcess."""
    if hasattr(self, "progress") and self.progress:
        self.progress.setValue(progress)


def _handle_log(self, level: str, message: str) -> None:
    """Handle log messages from MainProcess."""
    prefix = {
        "info": "ℹ️",
        "warning": "⚠️",
        "error": "❌",
        "success": "✅",
    }.get(level, "📝")
    self.log.append(f"{prefix} {message}")


def handle_finished(self, return_code: int, info: dict) -> None:
    """Handle compilation finished from MainProcess."""
    # Réactiver les contrôles
    self.set_controls_enabled(True)

    if hasattr(self, "progress") and self.progress:
        self.progress.setValue(100 if return_code == 0 else 0)

    if return_code == 0:
        self.log_i18n(
            "✅ Compilation terminée avec succès!",
            "✅ Compilation completed successfully!",
        )

        # Appeler on_success du moteur si disponible
        engine_id = info.get("engine")
        if engine_id:
            try:
                engine = create(engine_id)
            except Exception:
                engine = None
            if engine and hasattr(engine, "on_success"):
                file_path = info.get("file")
                if file_path:
                    try:
                        engine.on_success(self, file_path)
                    except Exception as e:
                        self.log_i18n(
                            f"⚠️ Erreur on_success: {e}", f"⚠️ on_success error: {e}"
                        )

        # Continuer avec les autres fichiers si nécessaire
        _continue_compile_all(self)
    elif return_code == -1:
        self.log_i18n("⏹️ Compilation annulée.", "⏹️ Compilation cancelled.")
    else:
        self.log_i18n(
            f"❌ Compilation échouée (code: {return_code})",
            f"❌ Compilation failed (code: {return_code})",
        )


def _handle_state_changed(self, state: ProcessState) -> None:
    """Handle state changes from MainProcess."""
    state_names = {
        ProcessState.IDLE: "Inactif",
        ProcessState.INITIALIZING: "Initialisation",
        ProcessState.READY: "Prêt",
        ProcessState.COMPILING: "Compilation en cours...",
        ProcessState.CANCELLING: "Annulation...",
        ProcessState.ERROR: "Erreur",
    }
    state_name = state_names.get(state, str(state))
    self.log.append(f"📊 État: {state_name}")
