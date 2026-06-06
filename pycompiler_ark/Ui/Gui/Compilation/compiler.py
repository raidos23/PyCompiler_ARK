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
Compiler GUI Module

Handles compilation process execution with threading support
by delegating to Core.Compiler.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from pycompiler_ark.Core.Compiler.engine_runner import BuildContext, run_engine_compile_streaming


class CompilationStatus(Enum):
    """Compilation status."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SUCCESS = "success"
    FAILED = "failed"


# Pre-compiled regex patterns for progress detection
PROGRESS_PATTERNS = [
    re.compile(r"\[(\d+)%\]"),
    re.compile(r"Progress:\s*(\d+)"),
    re.compile(r"(\d+)/(\d+)"),
]


class SafeGuiBridge(QObject):
    """
    Thread-safe bridge between the compilation background thread and the UI.
    Prevents segfaults by not accessing GUI widgets directly from the thread.
    """

    log_triggered = Signal(str, str)  # level, message
    log_i18n_triggered = Signal(str, str, str)  # level, fr, en

    def __init__(self, original_gui: Any):
        super().__init__()
        self._gui = original_gui
        self.workspace_dir = getattr(original_gui, "workspace_dir", None)
        self.use_system_python = getattr(original_gui, "use_system_python", False)

        # Mirror managers
        self.venv_manager = getattr(original_gui, "venv_manager", None)
        self.sys_deps_manager = getattr(original_gui, "sys_deps_manager", None)

    def tr(self, fr, en):
        # tr is generally thread-safe as it returns strings, but we fallback to en if needed
        try:
            return self._gui.tr(fr, en)
        except Exception:
            return en

    def _safe_log(self, text, text_en=None, level=None):
        if text_en:
            self.log_i18n_triggered.emit(level or "info", text, text_en)
        else:
            self.log_triggered.emit(level or "info", text)

    @property
    def log(self):
        # We return ourselves as the log object so that log.append() works
        return self

    def append(self, message: str):
        # engine_runner calls gui.log.append(message)
        self.log_triggered.emit("info", message)


class CompilationThread(QThread):
    """
    Thread used to run compilation without blocking the UI.
    Delegates the heavy lifting to Core.Compiler.run_engine_compile_streaming.
    """

    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)
    progress_update = Signal(int, str)
    log_requested = Signal(str, str)  # level, message

    def __init__(
        self,
        workspace: Path,
        engine_id: str,
        context: BuildContext,
        engine_config: Optional[Dict[str, Any]] = None,
        is_rebuild: bool = False,
        gui: Any = None,
        ark_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the compilation thread.
        """
        super().__init__()
        self.workspace = workspace
        self.engine_id = engine_id
        self.context = context
        self.engine_config = engine_config
        self.is_rebuild = is_rebuild
        self.ark_config = ark_config

        # Create a safe bridge instead of using the raw GUI object
        self.bridge = SafeGuiBridge(gui) if gui else None
        if self.bridge:
            # Connect bridge signals to emit via the thread
            self.bridge.log_triggered.connect(self._handle_bridge_log)
            self.bridge.log_i18n_triggered.connect(self._handle_bridge_log_i18n)

        self.cancel_requested = False
        self.start_time: Optional[datetime] = None

    def _handle_bridge_log(self, level, message):
        self.log_requested.emit(level, message)

    def _handle_bridge_log_i18n(self, level, fr, en):
        # Use simple translation for the signal
        msg = self.bridge.tr(fr, en) if self.bridge else en
        self.log_requested.emit(level, msg)

    def run(self) -> None:
        """Run the compilation process."""
        self.start_time = datetime.now()
        self.cancel_requested = False

        self.progress_update.emit(0, "Process started")

        # Optimization: Disable expensive auto-scan in background thread by default for GUI
        if os.environ.get("PYCOMPILER_SKIP_SCAN") is None:
            os.environ["PYCOMPILER_SKIP_SCAN"] = "1"

        # DEFERRED LOCK GENERATION (Move from UI thread to background)
        if not self.is_rebuild and self.ark_config:
            try:
                self.log_requested.emit("info", "🔒 Generating compilation lock file (background)...")
                from pycompiler_ark.Ui.Cli.helpers import (
                    build_lock_payload,
                    write_lock_files,
                    engine_config_from_lock,
                    build_context_object_from_ark_config
                )
                from pycompiler_ark.Core.Compiler.engine_runner import resolve_engine_command
                from pycompiler_ark.Core.Compiler.utils import get_interpreter_version_str
                from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager

                # 1. Resolve Python Version
                python_version = None
                try:
                    vm = VenvManager(self.bridge)
                    vpython = vm.resolve_project_venv()
                    if vpython:
                        vpath = vm.python_path(vpython)
                        python_version = get_interpreter_version_str(vpath)
                    else:
                        python_version = get_interpreter_version_str()
                except Exception:
                    pass

                # 2. Resolve Command (Pre-resolution for lock)
                resolved_command = None
                try:
                    prog, args, env = resolve_engine_command(
                        self.engine_id, self.context, self.engine_config, gui=self.bridge
                    )
                    resolved_command = {"program": prog, "args": args, "env": env}
                except Exception as e:
                    self.log_requested.emit("warning", f"Auto-mapping not persisted in lock: {e}")

                # 3. Build and Write Lock
                lock_payload = build_lock_payload(
                    self.workspace,
                    self.ark_config,
                    engine_id=self.engine_id,
                    python_version=python_version,
                    resolved_command=resolved_command,
                )
                write_lock_files(self.workspace, lock_payload)

                # 4. Final Alignment: refresh context and config from lock
                self.context = build_context_object_from_ark_config(self.ark_config)
                self.engine_config = engine_config_from_lock(lock_payload)

            except Exception as e:
                self.log_requested.emit("error", f"Lock generation failed: {e}")

        def _on_stdout(line: str):
            self.output_ready.emit(line)
            self._update_progress(line)

        def _on_stderr(line: str):
            self.error_ready.emit(line)

        def _stop_signal():
            return self.cancel_requested

        try:
            result = run_engine_compile_streaming(
                workspace=self.workspace,
                engine_id=self.engine_id,
                context=self.context,
                engine_config=self.engine_config,
                on_stdout=_on_stdout,
                on_stderr=_on_stderr,
                stop_signal=_stop_signal,
                is_rebuild=self.is_rebuild,
                gui=self.bridge,  # PASS THE BRIDGE
            )

            return_code = result.get("return_code", 1)
            if self.cancel_requested:
                return_code = -1

            self.finished.emit(return_code)
        except Exception as e:
            self.error_ready.emit(f"Error: {str(e)}")
            self.finished.emit(1)

    def _update_progress(self, line: str) -> None:
        """Update progress based on process output."""
        for pattern in PROGRESS_PATTERNS:
            match = pattern.search(line)
            if match:
                groups = match.groups()
                if len(groups) == 1:
                    try:
                        progress = int(groups[0])
                        self.progress_update.emit(progress, line)
                    except (ValueError, TypeError):
                        pass
                elif len(groups) == 2:
                    try:
                        current = int(groups[0])
                        total = int(groups[1])
                        if total > 0:
                            progress = int((current / total) * 100)
                            self.progress_update.emit(progress, line)
                    except (ValueError, TypeError):
                        pass
                break

    def cancel(self) -> None:
        """Request cancellation of the compilation."""
        self.cancel_requested = True

    @property
    def duration(self) -> Optional[float]:
        """Return execution duration in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None


class CompilerCore(QObject):
    """
    Main compiler class for the GUI.
    Orchestrates CompilationThread.
    """

    # Signaux
    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)
    status_changed = Signal(CompilationStatus)
    progress_update = Signal(int, str)
    log_message = Signal(str, str)  # niveau, message

    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialize the compiler.
        """
        super().__init__(parent)
        self._thread: Optional[CompilationThread] = None
        self._status = CompilationStatus.IDLE
        self._current_engine: Optional[str] = None
        self._current_file: Optional[str] = None
        self._workspace_dir: Optional[str] = None

    @property
    def status(self) -> CompilationStatus:
        """Return current compilation status."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Return True when a compilation is currently running."""
        return self._status == CompilationStatus.RUNNING

    @property
    def duration(self) -> Optional[float]:
        """Return the duration of the last compilation."""
        if self._thread:
            return self._thread.duration
        return None

    def compile(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        engine_id: Optional[str] = None,
        file_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
    ) -> bool:
        """
        Legacy compile method. Use compile_from_context instead.
        """
        self.log_message.emit(
            "warning", "Legacy compile() called. Use compile_from_context() instead."
        )
        if not file_path:
            return False

        ctx = BuildContext(
            project_name=os.path.basename(file_path),
            entry_point=os.path.basename(file_path),
            output_dir="dist/",
            exclude_patterns=[],
            include_packages=[],
            data_mappings=[],
        )
        return self.compile_from_context(
            workspace=Path(workspace_dir or os.getcwd()),
            engine_id=engine_id or "unknown",
            context=ctx,
        )

    def compile_from_context(
        self,
        workspace: Path,
        engine_id: str,
        context: BuildContext,
        engine_config: Optional[Dict[str, Any]] = None,
        is_rebuild: bool = False,
        gui: Any = None,
        ark_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Start an async compilation from a BuildContext.
        """
        if self.is_running:
            self.log_message.emit("warning", "Compilation already in progress")
            return False

        self._current_engine = engine_id
        self._current_file = context.entry_point
        self._workspace_dir = str(workspace)

        # Disconnect old thread if it exists to avoid side effects from lingering processes
        if self._thread is not None:
            try:
                self._thread.output_ready.disconnect()
                self._thread.error_ready.disconnect()
                self._thread.finished.disconnect()
                self._thread.progress_update.disconnect()
            except Exception:
                pass

        self._thread = CompilationThread(
            workspace=workspace,
            engine_id=engine_id,
            context=context,
            engine_config=engine_config,
            is_rebuild=is_rebuild,
            gui=gui,
            ark_config=ark_config,
        )

        # Connecter les signaux
        self._thread.output_ready.connect(self.output_ready.emit)
        self._thread.error_ready.connect(self.error_ready.emit)
        self._thread.finished.connect(self._on_finished)
        self._thread.progress_update.connect(self.progress_update.emit)
        self._thread.log_requested.connect(self.log_message.emit)

        # Changer le statut
        self._set_status(CompilationStatus.RUNNING)
        self.log_message.emit("info", f"Starting compilation with {engine_id}")

        # Démarrer le thread
        self._thread.start()

        return True

    def cancel(self) -> bool:
        """
        Cancel current compilation.
        """
        if not self.is_running or not self._thread:
            return False

        self._thread.cancel()
        self._set_status(CompilationStatus.CANCELLED)
        self.log_message.emit("info", "Compilation cancellation requested")
        return True

    def _set_status(self, status: CompilationStatus) -> None:
        """Update compilation status."""
        self._status = status
        self.status_changed.emit(status)

    def _on_finished(self, return_code: int) -> None:
        """Called when compilation is finished."""
        if return_code == -1:
            self._set_status(CompilationStatus.CANCELLED)
            self.log_message.emit("info", "Compilation cancelled")
        elif return_code == 0:
            self._set_status(CompilationStatus.SUCCESS)
            duration = self.duration
            if duration:
                self.log_message.emit(
                    "success", f"Compilation successful! ({duration:.2f}s)"
                )
            else:
                self.log_message.emit("success", "Compilation successful!")
        else:
            self._set_status(CompilationStatus.FAILED)
            self.log_message.emit(
                "error", f"Compilation failed with code {return_code}"
            )

        self.finished.emit(return_code)

    def dry_run(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
    ) -> str:
        """
        Simulate compilation and return the command.
        """
        cmd = " ".join([program] + args)
        result = f"[DRY RUN] Command: {cmd}\n"
        result += f"Working directory: {working_dir or 'current'}\n"
        return result
