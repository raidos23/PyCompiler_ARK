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
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from Core.Compiler.engine_runner import BuildContext, run_engine_compile_streaming


class CompilationStatus(Enum):
    """Compilation status."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SUCCESS = "success"
    FAILED = "failed"


class CompilationThread(QThread):
    """
    Thread used to run compilation without blocking the UI.
    Delegates the heavy lifting to Core.Compiler.run_engine_compile_streaming.
    """

    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)
    progress_update = Signal(int, str)

    def __init__(
        self,
        workspace: Path,
        engine_id: str,
        context: BuildContext,
        engine_config: Optional[Dict[str, Any]] = None,
        is_rebuild: bool = False,
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
        self.cancel_requested = False
        self.start_time: Optional[datetime] = None

    def run(self) -> None:
        """Run the compilation process."""
        self.start_time = datetime.now()
        self.cancel_requested = False

        self.progress_update.emit(0, "Process started")

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
        # Détecter les patterns de progression courants
        progress_patterns = [
            r"\[(\d+)%\]",
            r"Progress:\s*(\d+)",
            r"(\d+)/(\d+)",
        ]

        import re

        for pattern in progress_patterns:
            match = re.search(pattern, line)
            if match:
                if len(match.groups()) == 1:
                    progress = int(match.group(1))
                    self.progress_update.emit(progress, line)
                elif len(match.groups()) == 2:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    if total > 0:
                        progress = int((current / total) * 100)
                        self.progress_update.emit(progress, line)
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
            entry_point=os.path.basename(file_path),
            output_dir="dist/",
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
    ) -> bool:
        """
        Start an async compilation from a BuildContext.
        """
        if self.is_running():
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
        )

        # Connecter les signaux
        self._thread.output_ready.connect(self.output_ready.emit)
        self._thread.error_ready.connect(self.error_ready.emit)
        self._thread.finished.connect(self._on_finished)
        self._thread.progress_update.connect(self.progress_update.emit)

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
