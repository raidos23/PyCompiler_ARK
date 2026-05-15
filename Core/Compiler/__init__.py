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

Main compiler orchestration module for PyCompiler ARK.

This module connects GUI actions to compilation runtime services:
- command preparation and validation
- process lifecycle management
- BCASL pre-compile gating
- cancellation and UI feedback
"""

from __future__ import annotations

# ============================================================================
# IMPORTS STANDARD
# ============================================================================
import os
import sys
import time
from typing import Optional

# ============================================================================
# IMPORTS TIERS (PySide6)
# ============================================================================
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

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
from Core.i18n import log_with_level, log_i18n_level

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


def _resolve_default_engine_id() -> str:
    """Resolve a default engine dynamically from the registered engines."""
    try:
        import EngineLoader as engines_loader

        engine_ids = list(engines_loader.available_engines())
        if engine_ids:
            return str(engine_ids[0])
    except Exception:
        pass
    return "engine"


def _prompt_for_required_entrypoint(self, *, missing_path: str | None = None) -> None:
    """Show a blocking dialog when compilation has no valid entrypoint."""

    def _t(_key: str, fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    workspace_dir = getattr(self, "workspace_dir", None)
    try:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(
            _t(
                "msg_entrypoint_required_title",
                "Point d'entrée requis",
                "Entrypoint required",
            )
        )
        if missing_path:
            text_fr = (
                "Le point d'entrée configuré est introuvable ou obsolète:\n"
                f"{missing_path}\n\n"
                "Sélectionnez un fichier Python valide avant de compiler."
            )
            text_en = (
                "The configured entrypoint is missing or obsolete:\n"
                f"{missing_path}\n\n"
                "Select a valid Python file before compiling."
            )
        else:
            text_fr = (
                "La compilation nécessite un point d'entrée.\n\n"
                "Sélectionnez le fichier Python principal avant de compiler."
            )
            text_en = (
                "Compilation requires an entrypoint.\n\n"
                "Select the main Python file before compiling."
            )
        box.setText(_t("msg_entrypoint_required_text", text_fr, text_en))
        btn_select = box.addButton(
            _t("action_select_entrypoint", "Choisir un fichier", "Choose file"),
            QMessageBox.AcceptRole,
        )
        box.addButton(_t("action_cancel", "Annuler", "Cancel"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() != btn_select or not workspace_dir:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            _t(
                "dialog_select_entrypoint",
                "Choisir le point d'entrée",
                "Choose entrypoint",
            ),
            workspace_dir,
            "Python Files (*.py)",
        )
        if not file_path:
            return
        try:
            rel_path = os.path.relpath(
                os.path.realpath(file_path), os.path.realpath(workspace_dir)
            )
        except Exception:
            return
        if rel_path.startswith(".."):
            return
        if hasattr(self, "set_entrypoint"):
            self.set_entrypoint(rel_path)
    except Exception:
        pass


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
    """Return the singleton `MainProcess` instance, creating it on demand."""
    global _main_process
    if _main_process is None:
        _main_process = MainProcess()
    return _main_process


def _run_bcasl_before_compile(self, on_done) -> None:
    """Run BCASL pre-compile stage, then invoke `on_done(report)`."""
    try:
        from bcasl import run_pre_compile_async
    except Exception:
        if callable(on_done):
            try:
                on_done(None)
            except Exception:
                pass
        return
    try:
        log_i18n_level(
            self,
            "info",
            "Pré-compilation (BCASL) si activée...",
            "Pre-compilation (BCASL) if enabled...",
        )
    except Exception:
        pass
    try:
        run_pre_compile_async(self, on_done)
    except Exception:
        if callable(on_done):
            try:
                on_done(None)
            except Exception:
                pass


def _bcasl_report_allows_compile(self, report) -> bool:
    """Return True when BCASL pre-compile report allows compilation to continue."""
    # Sécurité fail-fast: si BCASL plante/échoue, on bloque la compilation.
    try:
        if report is None:
            log_i18n_level(
                self,
                "error",
                "BCASL a échoué ou n'a pas retourné de rapport. Compilation bloquée.",
                "BCASL failed or returned no report. Compilation blocked.",
            )
            return False

        if isinstance(report, dict):
            status = str(report.get("status", "")).strip().lower()
            if status in {"disabled", "skipped"}:
                return True
            if "ok" in report:
                ok = bool(report.get("ok"))
                if not ok:
                    log_i18n_level(
                        self,
                        "error",
                        "BCASL a signalé un échec. Compilation bloquée.",
                        "BCASL reported a failure. Compilation blocked.",
                    )
                return ok
            return True

        if hasattr(report, "ok"):
            ok = bool(getattr(report, "ok"))
            if not ok:
                log_i18n_level(
                    self,
                    "error",
                    "BCASL a signalé des erreurs plugins. Compilation bloquée.",
                    "BCASL reported plugin errors. Compilation blocked.",
                )
            return ok
    except Exception:
        log_i18n_level(
            self,
            "error",
            "Erreur lors de la validation du rapport BCASL. Compilation bloquée.",
            "Error while validating BCASL report. Compilation blocked.",
        )
        return False
    return True


def compile_all(self) -> None:
    """
    Slot connected to the compile button.
    Starts compilation for all selected Python files.
    """

    def _t(_key: str, fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    # Vérifier le workspace
    if not self.workspace_dir:
        log_i18n_level(
            self,
            "warning",
            "Aucun workspace sélectionné.",
            "No workspace selected.",
        )
        try:
            box = QMessageBox(self)
            box.setWindowTitle(
                _t("msg_no_workspace_title", "Workspace manquant", "Workspace missing")
            )
            box.setText(
                _t(
                    "msg_no_workspace_text",
                    "Sélectionnez un Workspace pour continuer.",
                    "Select a Workspace to continue.",
                )
            )
            btn_ws = box.addButton(
                _t("action_select_workspace", "Choisir Workspace", "Select Workspace"),
                QMessageBox.AcceptRole,
            )
            box.addButton(
                _t("action_cancel", "Annuler", "Cancel"), QMessageBox.RejectRole
            )
            box.exec()
            if box.clickedButton() == btn_ws:
                try:
                    self.select_workspace()
                except Exception:
                    pass
        except Exception:
            pass
        return

    files_to_compile = []
    entry_rel = None
    entrypoint_file = None
    try:
        from Core.ArkConfig import load_ark_config, get_entrypoint

        cfg = load_ark_config(self.workspace_dir)
        entry_rel = get_entrypoint(cfg)
    except Exception:
        entry_rel = None

    if not entry_rel:
        log_i18n_level(
            self,
            "warning",
            "Point d'entrée requis avant compilation.",
            "Entrypoint required before compilation.",
        )
        _prompt_for_required_entrypoint(self)
        return

    entrypoint_file = os.path.join(self.workspace_dir, entry_rel)
    if not os.path.isfile(entrypoint_file):
        try:
            missing_display = os.path.relpath(entrypoint_file, self.workspace_dir)
        except Exception:
            missing_display = entrypoint_file
        log_i18n_level(
            self,
            "error",
            f"Point d'entrée introuvable ou obsolète : {missing_display}",
            f"Entrypoint missing or obsolete: {missing_display}",
        )
        _prompt_for_required_entrypoint(self, missing_path=missing_display)
        return

    files_to_compile = [entrypoint_file]
    log_i18n_level(
        self,
        "info",
        f"Compilation du point d'entrée : {os.path.relpath(entrypoint_file, self.workspace_dir)}",
        f"Compiling entrypoint: {os.path.relpath(entrypoint_file, self.workspace_dir)}",
    )

    _set_progress_indeterminate(self)

    # Obtenir le moteur de compilation actif
    engine_id = None
    try:
        import EngineLoader as engines_loader

        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception as e:
        log_i18n_level(
            self,
            "warning",
            f"Erreur détection moteur: {e}",
            f"Engine detection error: {e}",
        )

    if not engine_id:
        engine_id = _resolve_default_engine_id()

    # Sauvegarder la configuration UI de l'engine actif dans le workspace
    try:
        from Core.EngineConfigManager import save_engine_config_for_gui

        save_engine_config_for_gui(self, engine_id)
    except Exception:
        pass

    # Obtenir le moteur (instance)
    engine = None
    try:
        import EngineLoader as engines_loader

        engine = engines_loader.registry.get_instance(engine_id)
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = create(engine_id)
        except Exception as e:
            log_i18n_level(
                self,
                "error",
                f"Erreur création moteur '{engine_id}': {e}",
                f"Engine creation error '{engine_id}': {e}",
            )
            return
    else:
        try:
            if not getattr(engine, "_gui", None):
                engine._gui = self
        except Exception:
            pass

    # Réinitialiser l'annulation anticipée (avant démarrage du process moteur)
    try:
        self._cancel_requested_during_precompile = False
    except Exception:
        pass

    # Désactiver les contrôles pendant la pré-compilation + compilation
    self.set_controls_enabled(False)

    def _after_bcasl(_report=None) -> None:
        if getattr(self, "_cancel_requested_during_precompile", False):
            try:
                self._cancel_requested_during_precompile = False
            except Exception:
                pass
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "info",
                "Compilation annulée avant le démarrage (phase BCASL).",
                "Compilation cancelled before start (BCASL phase).",
            )
            return
        if not _bcasl_report_allows_compile(self, _report):
            self.set_controls_enabled(True)
            return
        try:
            log_i18n_level(
                self,
                "info",
                f"Démarrage de la compilation avec {engine.name}...",
                f"Starting compilation with {engine.name}...",
            )
            # Initialiser MainProcess si nécessaire
            main_process = _get_main_process()
            main_process.set_workspace(self.workspace_dir)
            main_process.set_engine(engine_id)
            # Compiler chaque fichier
            _start_compilation_queue(self, engine, files_to_compile)
        except Exception as e:
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "error",
                f"Erreur démarrage compilation : {e}",
                f"Compilation start error: {e}",
            )

    _run_bcasl_before_compile(self, _after_bcasl)


def _start_compilation_queue(self, engine, files_to_compile: list) -> None:
    """Start compilation of a queue of files."""
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

    # Charger les patterns d'exclusion depuis ArkConfig
    exclusion_patterns = main_process.get_exclusion_patterns()
    excluded_count = 0

    # Compiler chaque fichier avec vérification des exclusions
    for file_path in files_to_compile:
        # Vérifier si le fichier doit être exclu
        if main_process.should_exclude(file_path):
            log_i18n_level(
                self,
                "info",
                f"Fichier exclu: {os.path.basename(file_path)}",
                f"File excluded: {os.path.basename(file_path)}",
            )
            excluded_count += 1
            continue

        if not os.path.exists(file_path):
            log_i18n_level(
                self,
                "warning",
                f"Fichier non trouvé: {file_path}",
                f"File not found: {file_path}",
            )
            continue

        # Vérifier les prérequis du moteur
        if hasattr(engine, "ensure_tools_installed"):
            if not engine.ensure_tools_installed(self):
                log_i18n_level(
                    self,
                    "warning",
                    "Outils manquants, compilation annulée.",
                    "Missing tools, compilation cancelled.",
                )
                self.set_controls_enabled(True)
                return

        # Construire la commande
        cmd = engine.build_command(self, file_path)
        if not cmd:
            log_i18n_level(
                self,
                "error",
                f"Erreur construction commande pour {file_path}",
                f"Command build error for {file_path}",
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

        log_i18n_level(
            self,
            "info",
            f"Compilation de {os.path.basename(file_path)}...",
            f"Compiling {os.path.basename(file_path)}...",
        )

        # break  # Un seul fichier à la fois pour l'instant

    # Afficher le résumé des exclusions
    if excluded_count > 0:
        log_i18n_level(
            self,
            "info",
            f"{excluded_count} fichier(s) exclu(s) selon les patterns de ark.yml",
            f"{excluded_count} file(s) excluded according to ark.yml patterns",
        )


def cancel_all_compilations(self) -> bool:
    """
    Slot connected to the cancel button.
    Cancels all ongoing compilations.
    """
    main_process = _get_main_process()

    # Étape 1: marquer l'annulation immédiatement (BCASL -> compile).
    try:
        self._cancel_requested_during_precompile = True
    except Exception:
        pass

    cancelled = False

    # Étape 2: arrêter le process de compilation au plus tôt.
    try:
        if main_process.is_compiling:
            cancelled = bool(main_process.cancel()) or cancelled
    except Exception:
        pass

    # Étape 3: stopper BCASL thread + workers (mode agressif).
    bcasl_was_running = False
    try:
        bcasl_thread = getattr(self, "_bcasl_thread", None)
        bcasl_was_running = bool(
            bcasl_thread is not None
            and hasattr(bcasl_thread, "isRunning")
            and bcasl_thread.isRunning()
        )
    except Exception:
        bcasl_was_running = False
    try:
        from bcasl.Loader import ensure_bcasl_thread_stopped

        ensure_bcasl_thread_stopped(self, timeout_ms=200)
        if bcasl_was_running:
            cancelled = True
    except Exception:
        pass
    try:
        from bcasl.executor import kill_active_workers

        if kill_active_workers() > 0:
            cancelled = True
    except Exception:
        pass

    # Étape 4: réactiver l'UI sans attendre.
    try:
        self.set_controls_enabled(True)
    except Exception:
        pass

    if cancelled:
        log_i18n_level(
            self,
            "info",
            "Annulation forcée demandée (compilation + BCASL).",
            "Forced cancellation requested (compilation + BCASL).",
        )
        return True

    log_i18n_level(
        self, "info", "Aucune compilation en cours.", "No compilation in progress."
    )
    return False


def handle_stdout(self, proc: QProcess) -> None:
    """Handle stdout from a QProcess (legacy method)."""
    data = proc.readAllStandardOutput()
    if data.isEmpty():
        return
    try:
        text = bytes(data).decode("utf-8", errors="replace").strip()
        if text:
            log_with_level(self, "info", text)
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
            log_with_level(self, "error", text)
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

    log_i18n_level(
        self,
        "info",
        f"Installation des modules manquants: {modules}",
        f"Installing missing modules: {modules}",
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
    # Sauvegarder la configuration UI de l'engine actif dans le workspace
    try:
        from Core.EngineConfigManager import save_engine_config_for_gui

        save_engine_config_for_gui(self, engine_id)
    except Exception:
        pass

    # Obtenir le moteur (instance)
    engine = None
    try:
        import EngineLoader as engines_loader

        engine = engines_loader.registry.get_instance(engine_id)
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = create(engine_id)
        except Exception as e:
            log_i18n_level(
                self,
                "error",
                f"Erreur création moteur '{engine_id}': {e}",
                f"Engine creation error '{engine_id}': {e}",
            )
            return False
    else:
        try:
            if not getattr(engine, "_gui", None):
                engine._gui = self
        except Exception:
            pass

    def _do_start() -> bool:
        # Vérifier les prérequis
        if not engine.ensure_tools_installed(self):
            return False

        # Construire la commande
        cmd = engine.build_command(self, file_path)
        if not cmd:
            log_i18n_level(
                self,
                "error",
                f"Erreur construction commande pour {file_path}",
                f"Command build error for {file_path}",
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
            log_i18n_level(
                self,
                "info",
                f"Démarrage {engine.name} pour {os.path.basename(file_path)}...",
                f"Starting {engine.name} for {os.path.basename(file_path)}...",
            )

        return success

    # Réinitialiser l'annulation anticipée (avant démarrage du process moteur)
    try:
        self._cancel_requested_during_precompile = False
    except Exception:
        pass

    # Désactiver les contrôles pendant la pré-compilation + compilation
    self.set_controls_enabled(False)
    _set_progress_indeterminate(self)

    result = {"value": None}

    def _after_bcasl(_report=None) -> None:
        if getattr(self, "_cancel_requested_during_precompile", False):
            try:
                self._cancel_requested_during_precompile = False
            except Exception:
                pass
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "info",
                "Compilation annulée avant le démarrage (phase BCASL).",
                "Compilation cancelled before start (BCASL phase).",
            )
            result["value"] = False
            return
        if not _bcasl_report_allows_compile(self, _report):
            self.set_controls_enabled(True)
            result["value"] = False
            return
        ok = False
        try:
            ok = _do_start()
        except Exception as e:
            log_i18n_level(
                self,
                "error",
                f"Erreur démarrage compilation : {e}",
                f"Compilation start error: {e}",
            )
        if not ok:
            self.set_controls_enabled(True)
        result["value"] = ok

    _run_bcasl_before_compile(self, _after_bcasl)
    if result["value"] is not None:
        return bool(result["value"])
    return True


def try_start_processes(self) -> bool:
    """
    Try to start compilation processes for all selected files.
    Returns True if at least one process started.
    """
    if not self.python_files:
        log_i18n_level(
            self, "warning", "Aucun fichier à compiler.", "No files to compile."
        )
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
        engine_id = _resolve_default_engine_id()

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
        log_with_level(self, "info", message)


def _set_progress_indeterminate(self) -> None:
    """Show an indeterminate progress bar."""
    if not getattr(self, "progress", None):
        return
    try:
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
    except Exception:
        pass


def _handle_compilation_started(self, info: dict) -> None:
    """Handle compilation started signal from MainProcess."""
    file_path = info.get("file", "")
    engine = info.get("engine", "")
    _set_progress_indeterminate(self)
    try:
        if file_path:
            if not hasattr(self, "_compilation_start"):
                self._compilation_start = {}
            self._compilation_start[file_path] = time.perf_counter()
    except Exception:
        pass
    if file_path and engine:
        log_i18n_level(
            self,
            "info",
            f"Démarrage compilation: {os.path.basename(file_path)} avec {engine}",
            f"Starting compilation: {os.path.basename(file_path)} with {engine}",
        )


def _handle_error(self, message: str) -> None:
    """Handle error output from MainProcess."""
    if message:
        log_with_level(self, "error", message)


def _handle_progress(self, progress: int, message: str) -> None:
    """Handle progress update from MainProcess."""
    # Always keep indeterminate to avoid misleading progress.
    _set_progress_indeterminate(self)


def _handle_log(self, level: str, message: str) -> None:
    """Handle log messages from MainProcess."""
    log_with_level(self, level, message)


def handle_finished(self, return_code: int, info: dict) -> None:
    """Handle compilation finished from MainProcess."""
    # Mettre à jour les statistiques de compilation
    try:
        if not hasattr(self, "_compilation_stats") or not isinstance(
            getattr(self, "_compilation_stats", None), dict
        ):
            self._compilation_stats = {
                "files": {},
                "engines": {},
                "total_time": 0.0,
                "total_count": 0,
                "success": 0,
                "failed": 0,
                "canceled": 0,
                "min_time": None,
                "max_time": None,
                "last_file": None,
                "last_duration": None,
                "last_status": None,
                "last_timestamp": None,
            }

        file_path = info.get("file")
        engine_id = info.get("engine")
        duration = None
        if file_path:
            try:
                start_map = getattr(self, "_compilation_start", {})
                if file_path in start_map:
                    duration = time.perf_counter() - start_map.pop(file_path)
            except Exception:
                duration = None
        if duration is None:
            duration = info.get("duration")

        if duration is None:
            duration = 0.0
        if duration < 0:
            duration = 0.0

        stats = self._compilation_stats
        stats["total_count"] = int(stats.get("total_count", 0)) + 1
        stats["total_time"] = float(stats.get("total_time", 0.0)) + float(duration)
        min_time = stats.get("min_time")
        max_time = stats.get("max_time")
        stats["min_time"] = (
            float(duration)
            if min_time is None
            else min(float(min_time), float(duration))
        )
        stats["max_time"] = (
            float(duration)
            if max_time is None
            else max(float(max_time), float(duration))
        )

        if return_code == 0:
            stats["success"] = int(stats.get("success", 0)) + 1
        elif return_code == -1:
            stats["canceled"] = int(stats.get("canceled", 0)) + 1
        else:
            stats["failed"] = int(stats.get("failed", 0)) + 1

        if engine_id:
            eng_stats = stats["engines"].get(engine_id)
            if not isinstance(eng_stats, dict):
                eng_stats = {
                    "count": 0,
                    "total_time": 0.0,
                    "success": 0,
                    "failed": 0,
                    "canceled": 0,
                }
            eng_stats["count"] = int(eng_stats.get("count", 0)) + 1
            eng_stats["total_time"] = float(eng_stats.get("total_time", 0.0)) + float(
                duration
            )
            if return_code == 0:
                eng_stats["success"] = int(eng_stats.get("success", 0)) + 1
            elif return_code == -1:
                eng_stats["canceled"] = int(eng_stats.get("canceled", 0)) + 1
            else:
                eng_stats["failed"] = int(eng_stats.get("failed", 0)) + 1
            stats["engines"][engine_id] = eng_stats

        if file_path:
            fstats = stats["files"].get(file_path)
            if not isinstance(fstats, dict):
                fstats = {
                    "count": 0,
                    "total_time": 0.0,
                    "min_time": None,
                    "max_time": None,
                    "last_time": 0.0,
                }
            fstats["count"] = int(fstats.get("count", 0)) + 1
            fstats["total_time"] = float(fstats.get("total_time", 0.0)) + float(
                duration
            )
            fstats["last_time"] = float(duration)
            min_time = fstats.get("min_time")
            max_time = fstats.get("max_time")
            fstats["min_time"] = (
                float(duration)
                if min_time is None
                else min(float(min_time), float(duration))
            )
            fstats["max_time"] = (
                float(duration)
                if max_time is None
                else max(float(max_time), float(duration))
            )
            stats["files"][file_path] = fstats

        stats["last_file"] = file_path
        stats["last_duration"] = float(duration)
        stats["last_status"] = int(return_code)
        stats["last_timestamp"] = time.time()

        # Compatibilité rétro: dict simple fichier -> dernière durée
        try:
            self._compilation_times = {
                f: fs.get("last_time", 0.0) for f, fs in stats["files"].items()
            }
        except Exception:
            pass
    except Exception:
        pass

    # Réactiver les contrôles
    self.set_controls_enabled(True)

    if hasattr(self, "progress") and self.progress:
        try:
            self.progress.setRange(0, 100)
            self.progress.setValue(100 if return_code == 0 else 0)
        except Exception:
            pass

    if return_code == 0:
        log_i18n_level(
            self,
            "success",
            "Compilation terminée avec succès!",
            "Compilation completed successfully!",
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
                        log_i18n_level(
                            self,
                            "warning",
                            f"Erreur on_success: {e}",
                            f"on_success error: {e}",
                        )

        # Continuer avec les autres fichiers si nécessaire
        _continue_compile_all(self)
    elif return_code == -1:
        log_i18n_level(self, "info", "Compilation annulée.", "Compilation cancelled.")
    else:
        log_i18n_level(
            self,
            "error",
            f"Compilation échouée (code: {return_code})",
            f"Compilation failed (code: {return_code})",
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
    log_with_level(self, "state", f"État: {state_name}")
