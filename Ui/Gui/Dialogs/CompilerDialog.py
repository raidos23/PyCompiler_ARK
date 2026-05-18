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
CompilerDialog — couche GUI du pipeline de compilation.

Contient tous les éléments d'interface liés à la compilation :
- Classes de signaux Qt (CompilationSignals, MainProcessSignals)
- Fonctions de connexion UI (compile_all, handle_finished, …)
- Dialogues (prompt entrypoint, error dialog)
- Gestion de la barre de progression

La logique métier (CompilationThread, CompilerCore, MainProcess)
reste dans Core/Compiler/.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import QObject, Signal
from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from Ui.Gui.Compilation.compiler import CompilationStatus
from Ui.Gui.Compilation.mainprocess import ProcessState, MainProcess
from Ui.Gui.Compilation.helpers import (
    get_main_process,
    resolve_default_engine_id,
    run_bcasl_before_compile,
    bcasl_report_allows_compile,
)
from Core.Compiler import create
from Ui.i18n import log_with_level, log_i18n_level


# ============================================================================
# DIALOG HELPERS
# ============================================================================


def _prompt_for_required_entrypoint(self, *, missing_path: str | None = None) -> None:
    """Show a blocking dialog when compilation has no valid entrypoint."""

    def _t(fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    workspace_dir = getattr(self, "workspace_dir", None)
    try:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle(_t("Point d'entrée requis", "Entrypoint required"))
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
        box.setText(_t(text_fr, text_en))
        btn_select = box.addButton(
            _t("Choisir un fichier", "Choose file"), QMessageBox.AcceptRole
        )
        box.addButton(_t("Annuler", "Cancel"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() != btn_select or not workspace_dir:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            _t("Choisir le point d'entrée", "Choose entrypoint"),
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


def show_error_dialog(self, title: str, message: str) -> None:
    """Show a critical error dialog."""
    try:
        QMessageBox.critical(self, self.tr("Erreur", "Error"), message)
    except Exception:
        pass


# ============================================================================
# PROGRESS HELPERS
# ============================================================================


def _set_progress_indeterminate(self) -> None:
    """Switch the progress bar to indeterminate (busy) mode."""
    if not getattr(self, "progress", None):
        return
    try:
        self.progress.setRange(0, 0)
        self.progress.setValue(0)
    except Exception:
        pass


# ============================================================================
# COMPILATION SLOT — connected to compile button
# ============================================================================


def compile_all(self) -> None:
    """Slot connected to the compile button. Starts compilation using EngineRunner as source of truth."""

    def _t(fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    if not self.workspace_dir:
        log_i18n_level(self, "warning", "Aucun workspace sélectionné.", "No workspace selected.")
        try:
            box = QMessageBox(self)
            box.setWindowTitle(_t("Workspace manquant", "Workspace missing"))
            box.setText(_t("Sélectionnez un Workspace pour continuer.", "Select a Workspace to continue."))
            btn_ws = box.addButton(_t("Choisir Workspace", "Select Workspace"), QMessageBox.AcceptRole)
            box.addButton(_t("Annuler", "Cancel"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() == btn_ws:
                try:
                    self.select_workspace()
                except Exception:
                    pass
        except Exception:
            pass
        return

    # Load project configuration
    try:
        from Core.Configs import load_ark_config, get_entrypoint
        from Core.Locking import build_context_from_ark_config

        cfg = load_ark_config(self.workspace_dir)
        entry_rel = get_entrypoint(cfg)
    except Exception as e:
        log_i18n_level(self, "error", f"Erreur config: {e}", f"Config error: {e}")
        return

    if not entry_rel:
        log_i18n_level(self, "warning", "Point d'entrée requis avant compilation.", "Entrypoint required before compilation.")
        _prompt_for_required_entrypoint(self)
        return

    entrypoint_file = os.path.join(self.workspace_dir, entry_rel)
    if not os.path.isfile(entrypoint_file):
        try:
            missing_display = os.path.relpath(entrypoint_file, self.workspace_dir)
        except Exception:
            missing_display = entrypoint_file
        log_i18n_level(self, "error",
            f"Point d'entrée introuvable ou obsolète : {missing_display}",
            f"Entrypoint missing or obsolete: {missing_display}",
        )
        _prompt_for_required_entrypoint(self, missing_path=missing_display)
        return

    _set_progress_indeterminate(self)

    # Resolve engine
    engine_id = None
    try:
        import Core.engine as engines_loader
        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception:
        pass

    if not engine_id:
        engine_id = resolve_default_engine_id()

    # Save GUI state to disk (persists tab settings)
    try:
        from Core.EngineConfigManager import save_engine_config_for_gui
        save_engine_config_for_gui(self, engine_id)
    except Exception:
        pass

    # Build lock payload (CLI-like behavior for reproducibility)
    try:
        from Core.Locking import build_lock_payload, write_lock_files
        lock_payload = build_lock_payload(Path(self.workspace_dir), cfg, engine_id=engine_id)
        write_lock_files(Path(self.workspace_dir), lock_payload)
        
        # Use engine config from lock (source of truth)
        engine_config = lock_payload.get("engine", {}).get("config") or {}
    except Exception as e:
        log_i18n_level(self, "warning", f"Erreur locking (ignorée): {e}", f"Locking error (ignored): {e}")
        engine_config = {}

    # Retrieve engine instance
    engine = None
    try:
        import Core.engine as engines_loader
        engine = engines_loader.registry.get_instance(engine_id)
    except Exception:
        engine = None
    
    if engine is None:
        try:
            engine = create(engine_id)
        except Exception as e:
            log_i18n_level(self, "error",
                f"Erreur création moteur '{engine_id}': {e}",
                f"Engine creation error '{engine_id}': {e}",
            )
            return

    # Prepare context and config for EngineRunner
    try:
        context = build_context_from_ark_config(cfg)
        # If no explicit engine_config was derived from lock, fallback to live GUI state
        if not engine_config and hasattr(engine, "get_config"):
            engine_config = engine.get_config(self)
    except Exception as e:
        log_i18n_level(self, "error", f"Erreur préparation contexte: {e}", f"Context prep error: {e}")
        return

    self.set_controls_enabled(False)
    log_i18n_level(
        self,
        "info",
        "🔍 Lancement de la phase de pré-compilation (BCASL)...",
        "🔍 Starting pre-compilation phase (BCASL)...",
    )

    def _after_bcasl(_report=None) -> None:
        if getattr(self, "_cancel_requested_during_precompile", False):
            self.set_controls_enabled(True)
            log_i18n_level(self, "info",
                "Compilation annulée avant le démarrage (phase BCASL).",
                "Compilation cancelled before start (BCASL phase).",
            )
            return
        if not bcasl_report_allows_compile(self, _report):
            log_i18n_level(
                self,
                "error",
                "❌ Échec de la validation BCASL. La compilation ne peut pas continuer.",
                "❌ BCASL validation failed. Compilation cannot continue.",
            )
            self.set_controls_enabled(True)
            return

        log_i18n_level(
            self,
            "success",
            "✅ Phase BCASL terminée avec succès.",
            "✅ BCASL phase completed successfully.",
        )

        try:            log_i18n_level(self, "info",
                f"Démarrage de la compilation avec {engine.name}...",
                f"Starting compilation with {engine.name}...",
            )
            
            # Start compilation using the EngineRunner path
            main_process = get_main_process()
            
            # Connection logic
            if not hasattr(main_process, "_gui_connected"):
                main_process.output_ready.connect(lambda msg: _handle_output(self, msg))
                main_process.error_ready.connect(lambda msg: _handle_error(self, msg))
                main_process.progress_update.connect(lambda pct, msg: _handle_progress(self, pct, msg))
                main_process.log_message.connect(lambda level, msg: _handle_log(self, level, msg))
                main_process.compilation_started.connect(lambda info: _handle_compilation_started(self, info))
                main_process.compilation_finished.connect(lambda code, info: handle_finished(self, code, info))
                main_process.state_changed.connect(lambda state: _handle_state_changed(self, state))
                main_process._gui_connected = True

            # The actual compilation call. We'll ensure tools inside the thread now
            # to keep the GUI responsive.
            success = main_process.compile_from_context(
                workspace=self.workspace_dir,
                engine_id=engine_id,
                context=context,
                engine_config=engine_config
            )
            
            if not success:
                self.set_controls_enabled(True)
                
        except Exception as e:
            self.set_controls_enabled(True)
            log_i18n_level(self, "error",
                f"Erreur démarrage compilation : {e}",
                f"Compilation start error: {e}",
            )

    run_bcasl_before_compile(self, _after_bcasl)


def start_compilation_process(self, engine_id: str, file_path: str) -> bool:
    """Start a single compilation process using MainProcess and EngineRunner with build locking."""
    try:
        from Core.Configs import load_ark_config
        from Core.Locking import build_context_from_ark_config, build_lock_payload, write_lock_files
        from Core.EngineConfigManager import save_engine_config_for_gui

        save_engine_config_for_gui(self, engine_id)
    except Exception:
        pass

    # Build lock payload (CLI-like behavior for reproducibility)
    try:
        cfg = load_ark_config(self.workspace_dir)
        lock_payload = build_lock_payload(Path(self.workspace_dir), cfg, engine_id=engine_id)
        write_lock_files(Path(self.workspace_dir), lock_payload)
        
        # Use engine config from lock (source of truth)
        engine_config = lock_payload.get("engine", {}).get("config") or {}
    except Exception as e:
        log_i18n_level(self, "warning", f"Erreur locking (ignorée): {e}", f"Locking error (ignored): {e}")
        engine_config = {}

    # Resolve engine
    engine = None
    try:
        import Core.engine as engines_loader
        engine = engines_loader.registry.get_instance(engine_id)
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = create(engine_id)
        except Exception as e:
            log_i18n_level(self, "error",
                f"Erreur création moteur '{engine_id}': {e}",
                f"Engine creation error '{engine_id}': {e}",
            )
            return False

    def _do_start() -> bool:
        # Prepare context for EngineRunner
        try:
            context = build_context_from_ark_config(cfg)
            
            # Use specific file_path as entry point
            try:
                rel_path = os.path.relpath(file_path, self.workspace_dir)
                if not rel_path.startswith(".."):
                    context.entry_point = rel_path
                else:
                    context.entry_point = file_path
            except Exception:
                context.entry_point = file_path
                
            # If no explicit engine_config was derived from lock, fallback to live GUI state
            if not engine_config and hasattr(engine, "get_config"):
                engine_config = engine.get_config(self)
        except Exception as e:
            log_i18n_level(self, "error", f"Erreur préparation contexte: {e}", f"Context prep error: {e}")
            return False

        main_process = get_main_process()
        if not hasattr(main_process, "_gui_connected"):
            main_process.output_ready.connect(lambda msg: _handle_output(self, msg))
            main_process.error_ready.connect(lambda msg: _handle_error(self, msg))
            main_process.progress_update.connect(lambda pct, msg: _handle_progress(self, pct, msg))
            main_process.log_message.connect(lambda level, msg: _handle_log(self, level, msg))
            main_process.compilation_started.connect(lambda info: _handle_compilation_started(self, info))
            main_process.compilation_finished.connect(lambda code, info: handle_finished(self, code, info))
            main_process.state_changed.connect(lambda state: _handle_state_changed(self, state))
            main_process._gui_connected = True

        success = main_process.compile_from_context(
            workspace=self.workspace_dir,
            engine_id=engine_id,
            context=context,
            engine_config=engine_config
        )

        if not success:
            self.set_controls_enabled(True)

        if success:
            log_i18n_level(self, "info",
                f"Démarrage {engine.name} pour {os.path.basename(file_path)}...",
                f"Starting {engine.name} for {os.path.basename(file_path)}...",
            )

        return success

    try:
        self._cancel_requested_during_precompile = False
    except Exception:
        pass

    self.set_controls_enabled(False)
    _set_progress_indeterminate(self)
    log_i18n_level(
        self,
        "info",
        "🔍 Lancement de la phase de pré-compilation (BCASL)...",
        "🔍 Starting pre-compilation phase (BCASL)...",
    )

    result = {"value": None}

    def _after_bcasl(_report=None) -> None:
        if getattr(self, "_cancel_requested_during_precompile", False):
            self.set_controls_enabled(True)
            log_i18n_level(self, "info",
                "Compilation annulée avant le démarrage (phase BCASL).",
                "Compilation cancelled before start (BCASL phase).",
            )
            result["value"] = False
            return
        if not bcasl_report_allows_compile(self, _report):
            log_i18n_level(
                self,
                "error",
                "❌ Échec de la validation BCASL. La compilation ne peut pas continuer.",
                "❌ BCASL validation failed. Compilation cannot continue.",
            )
            self.set_controls_enabled(True)
            result["value"] = False
            return
        
        log_i18n_level(
            self,
            "success",
            "✅ Phase BCASL terminée avec succès.",
            "✅ BCASL phase completed successfully.",
        )
        
        ok = False
        try:
            ok = _do_start()
        except Exception as e:
            log_i18n_level(self, "error",
                f"Erreur démarrage compilation : {e}",
                f"Compilation start error: {e}",
            )
        if not ok:
            self.set_controls_enabled(True)
        result["value"] = ok

    run_bcasl_before_compile(self, _after_bcasl)
    if result["value"] is not None:
        return bool(result["value"])
    return True
    if result["value"] is not None:
        return bool(result["value"])
    return True


def try_start_processes(self) -> bool:
    """Try to start compilation for all selected files."""
    if not self.python_files:
        log_i18n_level(self, "warning", "Aucun fichier à compiler.", "No files to compile.")
        return False

    engine_id = None
    try:
        import Core.engine as engines_loader

        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception:
        pass

    if not engine_id:
        engine_id = _resolve_default_engine_id()

    return start_compilation_process(self, engine_id, self.python_files[0])


def _continue_compile_all(self) -> None:
    """Continue compilation of remaining files after one completes."""
    pass


def cancel_all_compilations(self) -> None:
    """Cancel all running compilations, including pre-compilation (BCASL)."""
    # 1. Handle pre-compilation (BCASL) cancellation
    self._cancel_requested_during_precompile = True
    try:
        from bcasl.Loader import ensure_bcasl_thread_stopped
        ensure_bcasl_thread_stopped(self)
    except Exception:
        pass

    # 2. Handle main process cancellation
    get_main_process().cancel()
    
    # 3. Enable controls
    self.set_controls_enabled(True)
    log_i18n_level(self, "info", "Annulation demandée.", "Cancellation requested.")


def handle_stdout(self, message: str) -> None:
    """Handle standard output from the compilation process."""
    _handle_output(self, message)


def handle_stderr(self, message: str) -> None:
    """Handle error output from the compilation process."""
    _handle_error(self, message)


def try_install_missing_modules(self, engine_id: str) -> None:
    """Try to install missing modules for the specified engine."""
    pass


# ============================================================================
# MAINPROCESS SIGNAL HANDLERS
# ============================================================================


def _handle_output(self, message: str) -> None:
    """Handle stdout output from MainProcess."""
    if message:
        log_with_level(self, "info", message)


def _handle_error(self, message: str) -> None:
    """Handle stderr output from MainProcess."""
    if message:
        log_with_level(self, "error", message)


def _handle_progress(self, progress: int, message: str) -> None:
    """Handle progress update from MainProcess (kept indeterminate)."""
    _set_progress_indeterminate(self)


def _handle_log(self, level: str, message: str) -> None:
    """Handle log messages from MainProcess."""
    log_with_level(self, level, message)


def _handle_compilation_started(self, info: dict) -> None:
    """Handle compilation-started signal from MainProcess."""
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
        log_i18n_level(self, "info",
            f"Démarrage compilation: {os.path.basename(file_path)} avec {engine}",
            f"Starting compilation: {os.path.basename(file_path)} with {engine}",
        )


def handle_finished(self, return_code: int, info: dict) -> None:
    """Handle compilation-finished signal from MainProcess."""
    # Update compilation statistics
    try:
        if not hasattr(self, "_compilation_stats") or not isinstance(
            getattr(self, "_compilation_stats", None), dict
        ):
            self._compilation_stats = {
                "files": {}, "engines": {}, "total_time": 0.0,
                "total_count": 0, "success": 0, "failed": 0, "canceled": 0,
                "min_time": None, "max_time": None, "last_file": None,
                "last_duration": None, "last_status": None, "last_timestamp": None,
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
        stats["min_time"] = float(duration) if min_time is None else min(float(min_time), float(duration))
        stats["max_time"] = float(duration) if max_time is None else max(float(max_time), float(duration))

        if return_code == 0:
            stats["success"] = int(stats.get("success", 0)) + 1
        elif return_code == -1:
            stats["canceled"] = int(stats.get("canceled", 0)) + 1
        else:
            stats["failed"] = int(stats.get("failed", 0)) + 1

        if engine_id:
            eng_stats = stats["engines"].get(engine_id)
            if not isinstance(eng_stats, dict):
                eng_stats = {"count": 0, "total_time": 0.0, "success": 0, "failed": 0, "canceled": 0}
            eng_stats["count"] = int(eng_stats.get("count", 0)) + 1
            eng_stats["total_time"] = float(eng_stats.get("total_time", 0.0)) + float(duration)
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
                fstats = {"count": 0, "total_time": 0.0, "min_time": None, "max_time": None, "last_time": 0.0}
            fstats["count"] = int(fstats.get("count", 0)) + 1
            fstats["total_time"] = float(fstats.get("total_time", 0.0)) + float(duration)
            fstats["last_time"] = float(duration)
            min_t = fstats.get("min_time")
            max_t = fstats.get("max_time")
            fstats["min_time"] = float(duration) if min_t is None else min(float(min_t), float(duration))
            fstats["max_time"] = float(duration) if max_t is None else max(float(max_t), float(duration))
            stats["files"][file_path] = fstats

        stats["last_file"] = file_path
        stats["last_duration"] = float(duration)
        stats["last_status"] = int(return_code)
        stats["last_timestamp"] = time.time()

        try:
            self._compilation_times = {f: fs.get("last_time", 0.0) for f, fs in stats["files"].items()}
        except Exception:
            pass
    except Exception:
        pass

    # Re-enable controls
    self.set_controls_enabled(True)

    if hasattr(self, "progress") and self.progress:
        try:
            self.progress.setRange(0, 100)
            self.progress.setValue(100 if return_code == 0 else 0)
        except Exception:
            pass

    if return_code == 0:
        log_i18n_level(self, "success", "Compilation terminée avec succès!", "Compilation completed successfully!")

        engine_id = info.get("engine")
        if engine_id:
            try:
                engine = create(engine_id)
            except Exception:
                engine = None
            if engine and hasattr(engine, "on_success"):
                fp = info.get("file")
                if fp:
                    try:
                        engine.on_success(self, fp)
                    except Exception as e:
                        log_i18n_level(self, "warning", f"Erreur on_success: {e}", f"on_success error: {e}")

        _continue_compile_all(self)
    elif return_code == -1:
        log_i18n_level(self, "info", "Compilation annulée.", "Compilation cancelled.")
    else:
        log_i18n_level(self, "error",
            f"Compilation échouée (code: {return_code})",
            f"Compilation failed (code: {return_code})",
        )


def _handle_state_changed(self, state: ProcessState) -> None:
    """Handle state-changed signal from MainProcess."""
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
