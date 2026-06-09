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

from PySide6.QtWidgets import QFileDialog, QMessageBox

from pycompiler_ark.Core.Compiler import create
from pycompiler_ark.Ui.Gui.Compilation.helpers import (
    bcasl_report_allows_compile,
    get_main_process,
    run_bcasl_before_compile,
)
from pycompiler_ark.Ui.Gui.Compilation.mainprocess import ProcessState
from pycompiler_ark.Ui.i18n import log_i18n_level, log_with_level

# Shared helpers from CLI for exact code alignment
from pycompiler_ark.Ui.Cli.helpers import (
    load_ark_config,
    validate_ark_config,
    build_lock_payload,
    write_lock_files,
    build_context_object_from_ark_config,
    build_context_object_from_lock,
    engine_config_from_lock,
    cache_rebuild_lock,
    compare_lock_payloads,
)

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
    """Slot connected to the compile button. Starts compilation using shared logic aligned with CLI."""

    def _t(fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    if not self.workspace_dir:
        log_i18n_level(
            self, "warning", "Aucun workspace sélectionné.", "No workspace selected."
        )
        try:
            box = QMessageBox(self)
            box.setWindowTitle(_t("Workspace manquant", "Workspace missing"))
            box.setText(
                _t(
                    "Sélectionnez un Workspace pour continuer.",
                    "Select a Workspace to continue.",
                )
            )
            btn_ws = box.addButton(
                _t("Choisir Workspace", "Select Workspace"), QMessageBox.AcceptRole
            )
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

    # Workspace directory
    ws = Path(self.workspace_dir)

    # 1. Reset state for a new build
    try:
        self._cancel_requested_during_precompile = False
        self._is_rebuild = False
        get_main_process().reset()
    except Exception:
        pass

    # 2. Load and Validate (Aligned with CLI)
    try:
        config = load_ark_config(ws)
        validated = validate_ark_config(ws, config)
    except Exception as e:
        log_i18n_level(self, "error", f"Erreur config: {e}", f"Config error: {e}")
        return

    _set_progress_indeterminate(self)

    # 3. Resolve engine (GUI: Prefer selected tab, then config)
    engine_id = None
    try:
        import pycompiler_ark.Core.engine as engines_loader

        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception:
        pass

    if not engine_id:
        engine_id = str(validated.config["build"]["engine"])

    # Housekeeping: Save GUI tab settings to disk
    try:
        from pycompiler_ark.Core.engine.ConfigManager import save_engine_config_for_gui

        save_engine_config_for_gui(self, engine_id)
    except Exception:
        pass

    # 4. Preparation (Resolve initial context and engine config)
    try:
        # Use BuildContext helper to get initial context
        context = build_context_object_from_ark_config(validated.config)
        # load the engine config from disk
        from pycompiler_ark.Core.Locking import read_engine_config

        engine_config = read_engine_config(ws, engine_id)
    except Exception as e:
        log_i18n_level(
            self,
            "error",
            f"Erreur préparation compilation: {e}",
            f"Build prep error: {e}",
        )
        return

    # Retrieve engine instance for display name
    engine = None
    try:
        import pycompiler_ark.Core.engine as engines_loader

        engine = engines_loader.registry.get_instance(engine_id)
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = engines_loader.create(engine_id)
        except Exception:
            pass
    engine_name = getattr(engine, "name", engine_id)

    self.set_controls_enabled(False)

    log_i18n_level(
        self,
        "info",
        "🔍 Lancement de la phase de pré-compilation (BCASL)...",
        "🔍 Starting pre-compilation phase (BCASL)...",
    )

    def _after_bcasl(_report=None) -> None:
        nonlocal context, engine_config

        # Ensure we only process the callback for the current active build
        if _after_bcasl != getattr(self, "_active_bcasl_callback", None):
            return

        if getattr(self, "_cancel_requested_during_precompile", False):
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "info",
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
            try:
                from pycompiler_ark.Ui.Gui.Dialogs.BcaslDialog import (
                    ensure_bcasl_thread_stopped,
                )

                ensure_bcasl_thread_stopped(self)
            except Exception:
                pass
            self.set_controls_enabled(True)
            return

        log_i18n_level(
            self,
            "success",
            "✅ Phase BCASL terminée avec succès.",
            "✅ BCASL phase completed successfully.",
        )

        try:
            log_i18n_level(
                self,
                "info",
                f"Démarrage de la compilation avec {engine_name}...",
                f"Starting compilation with {engine_name}...",
            )

            # Start compilation using the EngineRunner path
            main_process = get_main_process()

            # OPTIMIZATION: Disable expensive auto-scan for GUI builds
            # This prevents scanning ALL files in the workspace which is slow and often unnecessary.
            os.environ["PYCOMPILER_SKIP_SCAN"] = "1"

            # Connection logic
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

            # The actual compilation call (passing ark_config for background lock generation)
            success = main_process.compile_from_context(
                workspace=ws,
                engine_id=engine_id,
                context=context,
                engine_config=engine_config,
                is_rebuild=False,
                gui=self,
                ark_config=validated.config,
            )

            if not success:
                self.set_controls_enabled(True)

        except Exception as e:
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "error",
                f"Erreur démarrage compilation : {e}",
                f"Compilation start error: {e}",
            )

    self._active_bcasl_callback = _after_bcasl
    # Pass validated config to short-circuit if BCASL is disabled
    ark_cfg = getattr(validated, "config", None) if "validated" in locals() else None
    run_bcasl_before_compile(
        self, _after_bcasl, build_context=context, ark_config=ark_cfg
    )


def rebuild_from_lock(self, lock_path: Path) -> None:
    """Rebuild the project using a specific lock file, following CLI logic."""
    if not self.workspace_dir:
        return
    ws = Path(self.workspace_dir)

    try:
        # Reset state for a new build
        self._cancel_requested_during_precompile = False
        get_main_process().reset()
    except Exception:
        pass

    try:
        from pycompiler_ark.Core.Locking import load_yaml_file

        log_i18n_level(
            self,
            "info",
            f"🔒 Chargement du verrou: {lock_path.name}",
            f"🔒 Loading lock file: {lock_path.name}",
        )
        lock_payload = load_yaml_file(lock_path)
        engine_id = str(((lock_payload.get("engine") or {}).get("name")) or "").strip()

        if not engine_id:
            raise ValueError("Invalid lock file: missing engine name")

        entry_file = str(
            ((lock_payload.get("project") or {}).get("entry")) or ""
        ).strip()
        if not entry_file:
            raise ValueError("Invalid lock file: missing project.entry")

        entry_path = ws / Path(entry_file)
        if not entry_path.is_file():
            # Show a nice dialog as this is a GUI
            _prompt_for_required_entrypoint(self, missing_path=str(entry_path))
            return

        # Context and Config from lock (Aligned with CLI)
        context = build_context_object_from_lock(lock_payload)
        self._is_rebuild = True
        self._rebuild_lock_payload = lock_payload

        # Alignement Git (Exact CLI Logic)
        try:
            from pycompiler_ark.Ui.Cli.helpers import ensure_correct_git_commit

            def _confirm(msg: str) -> bool:
                from PySide6.QtWidgets import QMessageBox

                ans = QMessageBox.question(
                    self,
                    self.tr("Alignement Git", "Git Alignment"),
                    msg,
                    QMessageBox.Yes | QMessageBox.No,
                )
                return ans == QMessageBox.Yes

            if not ensure_correct_git_commit(ws, lock_payload, confirm_cb=_confirm):
                log_i18n_level(
                    self,
                    "warning",
                    "Compilation annulée: Mismatch Git non résolu.",
                    "Compilation cancelled: Git mismatch not resolved.",
                )
                return
        except Exception as e:
            log_i18n_level(
                self,
                "warning",
                f"Échec vérification Git: {e}",
                f"Git verification failed: {e}",
            )

        engine_config = engine_config_from_lock(lock_payload)

        # Shared Python version resolution for locking/comparison (Aligned with CLI)
        self._python_version = None
        try:
            from pycompiler_ark.Core.Compiler.utils import get_interpreter_version_str
            from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager

            vm = VenvManager(self)
            vpython = vm.resolve_project_venv()
            if vpython:
                vpath = vm.python_path(vpython)
                self._python_version = get_interpreter_version_str(vpath)
            else:
                self._python_version = get_interpreter_version_str()
        except Exception:
            pass

        # Retrieve engine instance for display name
        engine = None
        try:
            import pycompiler_ark.Core.engine as engines_loader

            engine = engines_loader.registry.get_instance(engine_id)
        except Exception:
            engine = None
        if engine is None:
            try:
                engine = create(engine_id)
            except Exception:
                pass
        engine_name = getattr(engine, "name", engine_id)

        self.set_controls_enabled(False)

        _set_progress_indeterminate(self)

        # BCASL PRE-COMPILE (Aligned with CLI)
        log_i18n_level(
            self,
            "info",
            "🔍 Lancement de la phase de pré-compilation (BCASL)...",
            "🔍 Starting pre-compilation phase (BCASL)...",
        )

        def _after_bcasl(_report=None) -> None:
            nonlocal context, engine_config

            # Ensure we only process the callback for the current active build
            if _after_bcasl != getattr(self, "_active_bcasl_callback", None):
                return

            if not bcasl_report_allows_compile(self, _report):
                try:
                    from pycompiler_ark.Ui.Gui.Dialogs.BcaslDialog import (
                        ensure_bcasl_thread_stopped,
                    )

                    ensure_bcasl_thread_stopped(self)
                except Exception:
                    pass
                self.set_controls_enabled(True)
                return

            log_i18n_level(
                self,
                "info",
                f"Démarrage de la reconstruction avec {engine_name}...",
                f"Starting rebuild with {engine_name}...",
            )

            main_process = get_main_process()
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

            success = main_process.compile_from_context(
                workspace=ws,
                engine_id=engine_id,
                context=context,
                engine_config=engine_config,
                is_rebuild=True,
                gui=self,
            )

            if not success:
                self.set_controls_enabled(True)

        self._active_bcasl_callback = _after_bcasl
        run_bcasl_before_compile(self, _after_bcasl, build_context=context)

    except Exception as e:
        log_i18n_level(
            self,
            "error",
            f"Erreur lors de la reconstruction: {e}",
            f"Rebuild error: {e}",
        )
        self.set_controls_enabled(True)


def start_compilation_process(self, engine_id: str, file_path: str) -> bool:
    """Start a single compilation process using shared logic aligned with CLI."""
    if not self.workspace_dir:
        return False
    ws = Path(self.workspace_dir)

    # 0. Reset state for a new build
    try:
        self._cancel_requested_during_precompile = False
        self._is_rebuild = False
        get_main_process().reset()
    except Exception:
        pass

    # 1. Load and Validate (Aligned with CLI)
    try:
        cfg = load_ark_config(ws)
        validated = validate_ark_config(ws, cfg)
    except Exception as e:
        log_i18n_level(self, "error", f"Erreur config: {e}", f"Config error: {e}")
        return False

    # Housekeeping: Save GUI tab settings to disk
    try:
        from pycompiler_ark.Core.engine.ConfigManager import save_engine_config_for_gui

        save_engine_config_for_gui(self, engine_id)
    except Exception:
        pass

    # 2. Preparation (Resolve initial context and engine config)
    try:
        # Context from config (base context)
        context = build_context_object_from_ark_config(validated.config)

        # Override entrypoint for single file compilation
        try:
            rel_path = os.path.relpath(file_path, str(ws))
            if not rel_path.startswith(".."):
                context.entry_point = rel_path
            else:
                context.entry_point = file_path
        except Exception:
            context.entry_point = file_path

        # load the engine config from disk
        from pycompiler_ark.Core.Locking import read_engine_config

        engine_config = read_engine_config(ws, engine_id)

    except Exception as e:
        log_i18n_level(
            self,
            "error",
            f"Erreur préparation compilation: {e}",
            f"Build prep error: {e}",
        )
        return False

    # Retrieve engine instance for display name
    engine = None
    try:
        import pycompiler_ark.Core.engine as engines_loader

        engine = engines_loader.registry.get_instance(engine_id)
    except Exception:
        engine = None
    if engine is None:
        try:
            engine = engines_loader.create(engine_id)
        except Exception:
            pass
    engine_name = getattr(engine, "name", engine_id)

    self.set_controls_enabled(False)
    _set_progress_indeterminate(self)

    # 3. BCASL (GUI async)
    log_i18n_level(
        self,
        "info",
        "🔍 Lancement de la phase de pré-compilation (BCASL)...",
        "🔍 Starting pre-compilation phase (BCASL)...",
    )

    def _after_bcasl(_report=None) -> None:
        nonlocal context, engine_config

        # Ensure we only process the callback for the current active build
        if _after_bcasl != getattr(self, "_active_bcasl_callback", None):
            return

        if getattr(self, "_cancel_requested_during_precompile", False):
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "info",
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
            try:
                from pycompiler_ark.Ui.Gui.Dialogs.BcaslDialog import (
                    ensure_bcasl_thread_stopped,
                )

                ensure_bcasl_thread_stopped(self)
            except Exception:
                pass
            self.set_controls_enabled(True)
            return

        log_i18n_level(
            self,
            "success",
            "✅ Phase BCASL terminée avec succès.",
            "✅ BCASL phase completed successfully.",
        )

        try:
            log_i18n_level(
                self,
                "info",
                f"Démarrage {engine_name} pour {os.path.basename(file_path)}...",
                f"Starting {engine_name} for {os.path.basename(file_path)}...",
            )

            # OPTIMIZATION: Disable expensive auto-scan for GUI builds
            os.environ["PYCOMPILER_SKIP_SCAN"] = "1"

            main_process = get_main_process()
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

            success = main_process.compile_from_context(
                workspace=ws,
                engine_id=engine_id,
                context=context,
                engine_config=engine_config,
                is_rebuild=False,
                gui=self,
                ark_config=validated.config,
            )

            if not success:
                self.set_controls_enabled(True)

        except Exception as e:
            self.set_controls_enabled(True)
            log_i18n_level(
                self,
                "error",
                f"Erreur démarrage compilation : {e}",
                f"Compilation start error: {e}",
            )

    self._active_bcasl_callback = _after_bcasl
    # Pass validated config to short-circuit if BCASL is disabled
    ark_cfg = getattr(validated, "config", None) if "validated" in locals() else None
    run_bcasl_before_compile(
        self, _after_bcasl, build_context=context, ark_config=ark_cfg
    )
    return True


def try_start_processes(self) -> bool:
    """Try to start compilation for all selected files."""
    if not self.python_files:
        log_i18n_level(
            self, "warning", "Aucun fichier à compiler.", "No files to compile."
        )
        return False

    engine_id = None
    try:
        import pycompiler_ark.Core.engine as engines_loader

        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
    except Exception:
        pass
    from pycompiler_ark.Ui.Gui.Compilation.helpers import resolve_default_engine_id

    if not engine_id:
        engine_id = resolve_default_engine_id()

    return start_compilation_process(self, engine_id, self.python_files[0])


def _continue_compile_all(self) -> None:
    """Continue compilation of remaining files after one completes."""
    pass


def cancel_all_compilations(self) -> None:
    """Cancel all running compilations, including pre-compilation (BCASL)."""
    # 1. Handle pre-compilation (BCASL) cancellation
    self._cancel_requested_during_precompile = True
    try:
        from pycompiler_ark.Ui.Gui.Dialogs.BcaslDialog import (
            ensure_bcasl_thread_stopped,
        )

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
        log_i18n_level(
            self,
            "info",
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
            min_t = fstats.get("min_time")
            max_t = fstats.get("max_time")
            fstats["min_time"] = (
                float(duration) if min_t is None else min(float(min_t), float(duration))
            )
            fstats["max_time"] = (
                float(duration) if max_t is None else max(float(max_t), float(duration))
            )
            stats["files"][file_path] = fstats

        stats["last_file"] = file_path
        stats["last_duration"] = float(duration)
        stats["last_status"] = int(return_code)
        stats["last_timestamp"] = time.time()

        try:
            self._compilation_times = {
                f: fs.get("last_time", 0.0) for f, fs in stats["files"].items()
            }
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
        log_i18n_level(
            self,
            "success",
            "Compilation terminée avec succès!",
            "Compilation completed successfully!",
        )

        # Integrity Check (Aligned with CLI)
        if getattr(self, "_is_rebuild", False) and getattr(
            self, "_rebuild_lock_payload", None
        ):
            try:
                if not self.workspace_dir:
                    return
                ws = Path(self.workspace_dir)

                log_i18n_level(
                    self,
                    "info",
                    "Vérification de l'intégrité du verrou après compilation...",
                    "Performing lock integrity check after compilation...",
                )
                current_config = load_ark_config(ws)
                validated = validate_ark_config(ws, current_config)
                regenerated = build_lock_payload(
                    ws,
                    validated.config,
                    engine_id=info.get("engine", ""),
                    python_version=getattr(self, "_python_version", None),
                )

                rebuild_cache = cache_rebuild_lock(ws, regenerated)
                comparison_ok, diffs = compare_lock_payloads(
                    self._rebuild_lock_payload, regenerated, return_diff=True
                )

                if not comparison_ok:
                    log_i18n_level(
                        self,
                        "warning",
                        "⚠️ Mismatch fonctionnel détecté : le verrou actuel diffère de celui utilisé pour le rebuild.",
                        "⚠️ Functional mismatch detected: the current configuration differs from the one in the lock file.",
                    )
                    for d in diffs:
                        log_with_level(self, "info", f"  - {d}")

                    if rebuild_cache:
                        log_i18n_level(
                            self,
                            "info",
                            f"Verrou de comparaison généré : {rebuild_cache}",
                            f"Comparison lock generated: {rebuild_cache}",
                        )
                else:
                    log_i18n_level(
                        self,
                        "success",
                        "✅ Intégrité du verrou confirmée (Équivalence Fonctionnelle).",
                        "✅ Lock integrity confirmed (Functional Equivalence).",
                    )
            except Exception as exc:
                log_i18n_level(
                    self,
                    "warning",
                    f"Impossible de regénérer le verrou de comparaison: {exc}",
                    f"Unable to regenerate comparison lock: {exc}",
                )

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
                        log_i18n_level(
                            self,
                            "warning",
                            f"Erreur on_success: {e}",
                            f"on_success error: {e}",
                        )

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
