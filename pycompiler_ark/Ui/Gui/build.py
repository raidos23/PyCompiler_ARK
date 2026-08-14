# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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
by delegating to Core.engine_runner.
"""

from __future__ import annotations

import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from ...Core.engine_runner import (
    BuildContext,
    run_engine_compile_streaming,
)

from typing import Any, Optional

from .. import output

# Singleton MainProcess (initialised on first use)
_main_process: Optional[MainProcess] = None


def get_main_process() -> MainProcess:
    """Return the singleton `MainProcess` instance, creating it on demand."""
    global _main_process
    if _main_process is None:
        _main_process = MainProcess()
    return _main_process


def resolve_default_engine_id() -> str:
    """Resolve a default engine dynamically from the registered engines."""
    try:
        from ...Core import engine as engines_loader

        engine_ids = list(engines_loader.available_engines())
        if engine_ids:
            return str(engine_ids[0])
    except Exception:
        pass
    return "engine"


def run_bcasl_before_compile(
    gui_instance,
    on_done,
    build_context: Optional[Any] = None,
    ark_config: Optional[dict] = None,
) -> None:
    """
    Run BCASL pre-compile stage, then invoke `on_done(report)`.
    Optimized: Checks activation state before launching the async thread.
    """
    try:
        from pathlib import Path

        from ...bcasl.Loader import BCASL_DISABLED_REPORT, _is_bcasl_enabled
        from .Dialogs.BcaslDialog import run_pre_compile_async
    except Exception:
        if callable(on_done):
            on_done(None)
        return

    ws = getattr(gui_instance, "workspace_dir", None)
    if not ws:
        if callable(on_done):
            on_done(None)
        return

    # Optimization: Short-circuit if BCASL is disabled to avoid thread overhead
    enabled = True
    try:
        if ark_config:
            enabled = bool(
                ark_config.get("plugins", {}).get("bcasl_enabled", True)
            )
        else:
            enabled = _is_bcasl_enabled(Path(ws))
    except Exception:
        pass

    if not enabled:
        try:
            output.info(
                (
                    "BCASL désactivé dans ark.yml. Exécution ignorée.",
                    "BCASL disabled in ark.yml. Skipping execution.",
                ),
                gui=gui_instance,
            )
        except Exception:
            pass
        if callable(on_done):
            on_done(dict(BCASL_DISABLED_REPORT))
        return

    try:
        output.info(
            ("Pré-compilation (BCASL)...", "Pre-compilation (BCASL)..."),
            gui=gui_instance,
        )
    except Exception:
        pass

    try:
        run_pre_compile_async(
            gui_instance, on_done, build_context=build_context
        )
    except Exception:
        if callable(on_done):
            on_done(None)


def bcasl_report_allows_compile(gui_instance, report) -> bool:
    """
    Return True when BCASL pre-compile report allows compilation to continue.
    Robustly handles dicts, objects, and lists.
    """
    try:
        if report is None:
            # Fallback check if the thread returned nothing
            try:
                from pathlib import Path

                from ...bcasl.Loader import _is_bcasl_enabled

                ws = getattr(gui_instance, "workspace_dir", None)
                if ws and not _is_bcasl_enabled(Path(ws).resolve()):
                    return True
            except Exception:
                pass
            return False

        # 1. Handle Disabled Report (Dict)
        if isinstance(report, dict):
            try:
                from ...bcasl.Loader import is_bcasl_disabled_report

                if is_bcasl_disabled_report(report):
                    return True
            except Exception:
                pass

            # Simple check for 'ok' key
            if "ok" in report:
                res = report.get("ok")
                return (
                    bool(res)
                    if not isinstance(res, (list, tuple, set))
                    else all(res)
                )
            return True

        # 2. Handle ExecutionReport object
        if hasattr(report, "ok"):
            ok_val = getattr(report, "ok")
            # If it's a property returning bool, use it directly
            if isinstance(ok_val, bool):
                return ok_val
            # If it's a list (legacy/compat), check all
            try:
                return all(ok_val)
            except Exception:
                return bool(ok_val)

        # 3. Handle List of Results
        if isinstance(report, (list, tuple)):
            return all(getattr(item, "success", True) for item in report)

    except Exception:
        try:
            output.error(
                (
                    "Erreur lors de la validation du rapport BCASL. Compilation bloquée.",
                    "Error while validating BCASL report. Compilation blocked.",
                ),
                gui=gui_instance,
            )
        except Exception:
            pass
        return False

    return True


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
    log_message_triggered = Signal(str, str, str)  # level, fr, en

    def __init__(self, original_gui: Any):
        super().__init__()
        self._gui = original_gui
        self.workspace_dir = getattr(original_gui, "workspace_dir", None)
        self.use_system_python = getattr(
            original_gui, "use_system_python", False
        )

        # Mirror managers
        self.venv_manager = getattr(original_gui, "venv_manager", None)
        self.sys_deps_manager = getattr(original_gui, "sys_deps_manager", None)

    def tr(self, fr, en):
        # tr is generally thread-safe as it returns strings, but we fallback to en if needed
        try:
            return self._gui.tr(fr, en)
        except Exception:
            return en

    def log_message(self, fr: str, en: str, level: str | None = None) -> None:
        self.log_message_triggered.emit(level or "info", fr, en)

    def log_message_level(self, level: str, fr: str, en: str) -> None:
        self.log_message_triggered.emit(level, fr, en)

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
    Delegates the heavy lifting to Core.engine_runner.run_engine_compile_streaming.
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
            self.bridge.log_message_triggered.connect(
                self._handle_bridge_log_message
            )

        self.cancel_requested = False
        self.start_time: Optional[datetime] = None

    def _handle_bridge_log(self, level, message):
        self.log_requested.emit(level, message)

    def _handle_bridge_log_message(self, level, fr, en):
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
                self.log_requested.emit(
                    "info",
                    "🔒 Generating compilation lock file (background)...",
                )
                from ...Core.engine_runner import (
                    resolve_engine_command,
                )
                from ...Core.utils import (
                    get_interpreter_version_str,
                )
                from ...Core.Venv_Manager.Manager import VenvManager
                from ..Cli.helpers import (
                    build_context_object_from_ark_config,
                    build_lock_payload,
                    engine_config_from_lock,
                    write_lock_files,
                )

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
                        self.engine_id,
                        self.context,
                        self.engine_config,
                        gui=self.bridge,
                    )
                    resolved_command = {
                        "program": prog,
                        "args": args,
                        "env": env,
                    }
                except Exception as e:
                    self.log_requested.emit(
                        "warning", f"Auto-mapping not persisted in lock: {e}"
                    )

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
                self.context = build_context_object_from_ark_config(
                    self.ark_config
                )
                self.engine_config = engine_config_from_lock(lock_payload)

            except Exception as e:
                self.log_requested.emit(
                    "error", f"Lock generation failed: {e}"
                )

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
            "warning",
            "Legacy compile() called. Use compile_from_context() instead.",
        )
        if not file_path:
            return False

        ctx = BuildContext(
            project_name=os.path.basename(file_path),
            entry_point=os.path.basename(file_path),
            output_dir="dist/",
            exclude_packages=[],
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
        """Cancel current compilation."""
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


# ArkConfig imports for managing exclusions
from pycompiler_ark.Core.configs import (
    DEFAULT_EXCLUDE_PATTERNS,
    load_ark_config,
    should_exclude_file,
)

from ...Core.engine.build_context import BuildContext


class ProcessState(Enum):
    """Possible states of the main process."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    COMPILING = "compiling"
    CANCELLING = "cancelling"
    ERROR = "error"


class MainProcess(QObject):
    """
    Main process class used to orchestrate compilation.

    Coordinates the full compilation flow:
    - Workspace initialization
    - Engine selection and configuration
    - Compilation execution
    - Error handling and cancellation

    Uses `CompilerCore` for the underlying execution.
    """

    # Signaux
    state_changed = Signal(ProcessState)
    log_message = Signal(str, str)  # niveau, message
    compilation_started = Signal(dict)
    compilation_finished = Signal(int, dict)
    engine_ready = Signal(str)
    workspace_changed = Signal(str)
    output_ready = Signal(str)
    error_ready = Signal(str)
    progress_update = Signal(int, str)

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        parent: Optional[QObject] = None,
    ):
        """
        Initialize the main process.

        Args:
          workspace_dir: Optional workspace path.
          parent: Optional parent object.
        """
        super().__init__(parent)

        # État interne
        self._state = ProcessState.IDLE
        self._workspace_dir: Optional[str] = None
        self._current_file: Optional[str] = None
        self._current_engine: Optional[str] = None

        # Composants
        self.compiler = CompilerCore()
        self._connect_signals()

        # Workspace
        if workspace_dir:
            self.set_workspace(workspace_dir)

        self._set_state(ProcessState.READY)

    def _connect_signals(self) -> None:
        """Connect compiler signals to process-level signals."""
        # Signaux du compilateur vers le processus
        self.compiler.output_ready.connect(self.output_ready.emit)
        self.compiler.error_ready.connect(self.error_ready.emit)
        self.compiler.finished.connect(self._on_compilation_finished)
        self.compiler.status_changed.connect(self._on_status_changed)
        self.compiler.progress_update.connect(self.progress_update.emit)
        self.compiler.log_message.connect(self.log_message.emit)

    def _set_state(self, state: ProcessState) -> None:
        """Update process state."""
        self._state = state
        self.state_changed.emit(state)

    @property
    def state(self) -> ProcessState:
        """Return current process state."""
        return self._state

    @property
    def workspace_dir(self) -> Optional[str]:
        """Return workspace path."""
        return self._workspace_dir

    @property
    def current_file(self) -> Optional[str]:
        """Return the file currently being compiled."""
        return self._current_file

    @property
    def current_engine(self) -> Optional[str]:
        """Return the current compilation engine."""
        return self._current_engine

    @property
    def is_ready(self) -> bool:
        """Return True when the process is ready."""
        return self._state in (ProcessState.READY, ProcessState.IDLE)

    @property
    def is_compiling(self) -> bool:
        """Return True when a compilation is currently running."""
        return self._state == ProcessState.COMPILING

    @property
    def is_idle(self) -> bool:
        """Return True when the process is idle."""
        return self._state == ProcessState.IDLE

    def set_workspace(self, workspace_dir: str) -> bool:
        """
        Set workspace directory.

        Args:
         workspace_dir: Path du workspace

        Returns:
         True si le workspace a été défini, False sinon
        """
        if not workspace_dir or not os.path.isdir(workspace_dir):
            self.log_message.emit(
                "error", f"Invalid workspace directory: {workspace_dir}"
            )
            return False

        self._workspace_dir = workspace_dir

        # Configurer les variables d'environnement
        os.environ["ARK_WORKSPACE"] = workspace_dir

        self.log_message.emit("info", f"Workspace set to: {workspace_dir}")
        self.workspace_changed.emit(workspace_dir)

        return True

    def set_file(self, file_path: str) -> bool:
        """Set file to compile.

        Args:
         file_path: Python file path

        Returns:
         True if the file has been defined, False otherwise"""
        if not file_path or not os.path.isfile(file_path):
            self.log_message.emit("error", f"File not found: {file_path}")
            return False

        self._current_file = file_path
        self.log_message.emit("info", f"File set: {file_path}")

        return True

    def set_engine(self, engine_id: str) -> None:
        """Set compilation engine to use.

        Args:
         engine_id: Engine identifier"""
        self._current_engine = engine_id
        self.log_message.emit("info", f"Engine selected: {engine_id}")
        self.engine_ready.emit(engine_id)

    def compile(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        engine_id: Optional[str] = None,
        file_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
    ) -> bool:
        """Start a compilation.

        Args:
         program: Program to execute
         args: Compile arguments
         env: Environment variables (optional)
         engine_id: Engine identifier (optional)
         file_path: File path (optional)
         workspace_dir: Working directory (optional)

        Returns:
         True if compilation has started, False otherwise"""
        if self.is_compiling:
            self.log_message.emit("warning", "Compilation already in progress")
            return False

        if not file_path:
            self.log_message.emit(
                "error", "Compilation requires an entrypoint file"
            )
            return False
        if not os.path.isfile(file_path):
            self.log_message.emit(
                "error", f"Entrypoint missing or obsolete: {file_path}"
            )
            return False

        # Mettre à jour le workspace si fourni
        if workspace_dir and workspace_dir != self._workspace_dir:
            self._workspace_dir = workspace_dir

        # Vérifier l'exclusion avant de lancer la compilation
        if file_path and self._workspace_dir:
            if self.should_exclude(file_path):
                self.log_message.emit(
                    "warning", f"File excluded by ARK config: {file_path}"
                )
                return False

        # Déterminer le répertoire de travail
        working_dir = workspace_dir or self._workspace_dir
        if file_path:
            working_dir = working_dir or os.path.dirname(file_path)

        # Déterminer les variables d'environnement
        compile_env = env or {}
        if self._workspace_dir:
            compile_env["ARK_WORKSPACE"] = self._workspace_dir

        # Préparer les infos de compilation
        compile_info = {
            "engine": engine_id or self._current_engine,
            "file": file_path or self._current_file,
            "workspace": working_dir,
            "command": " ".join([program] + args),
        }

        # Émettre le signal de début
        self.compilation_started.emit(compile_info)

        # Démarrer la compilation
        success = self.compiler.compile(
            program=program,
            args=args,
            env=compile_env,
            working_dir=working_dir,
            engine_id=engine_id or self._current_engine,
            file_path=file_path or self._current_file,
            workspace_dir=working_dir,
        )

        if success:
            self._set_state(ProcessState.COMPILING)
            self.log_message.emit("info", "Compilation started")

        return success

    def cancel(self) -> bool:
        """Cancel current compilation.

        Returns:
         True if cancellation was requested, False otherwise"""
        if not self.is_compiling:
            return False

        self._set_state(ProcessState.CANCELLING)
        return self.compiler.cancel()

    def dry_run(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        workspace_dir: Optional[str] = None,
    ) -> str:
        """Simulate compilation without execution.

        Args:
         program: Program to execute
         args: Arguments
         env: Environment variables (optional)
         workspace_dir: Working directory (optional)

        Returns:
         Description of the command to execute"""
        working_dir = workspace_dir or self._workspace_dir
        return self.compiler.dry_run(program, args, env, working_dir)

    def _on_compilation_finished(self, return_code: int) -> None:
        """Called when compilation is finished."""
        compile_info = {
            "engine": self._current_engine,
            "file": self._current_file,
            "workspace": self._workspace_dir,
            "duration": self.compiler.duration,
        }

        self.compilation_finished.emit(return_code, compile_info)

        if self._state == ProcessState.CANCELLING:
            self._set_state(ProcessState.READY)
        elif return_code == 0:
            self._set_state(ProcessState.READY)
        else:
            self._set_state(ProcessState.ERROR)

    def _on_status_changed(self, status: CompilationStatus) -> None:
        """Called when compiler status changes."""
        # Traduire le statut du compilateur vers l'état du processus
        if status == CompilationStatus.RUNNING:
            self._set_state(ProcessState.COMPILING)
        elif status == CompilationStatus.SUCCESS:
            self._set_state(ProcessState.READY)
        elif status == CompilationStatus.FAILED:
            self._set_state(ProcessState.ERROR)
        elif status == CompilationStatus.CANCELLED:
            self._set_state(ProcessState.READY)
        else:
            self._set_state(ProcessState.READY)

    def get_compilation_info(self) -> Dict[str, Any]:
        """Return current compilation information.

        Returns:
         Dictionary with compilation information"""
        return {
            "engine": self._current_engine,
            "file": self._current_file,
            "workspace": self._workspace_dir,
            "state": self._state.value,
            "is_compiling": self.is_compiling,
            "duration": self.compiler.duration,
        }

    def compile_from_context(
        self,
        workspace: Path | str,
        engine_id: str,
        context: BuildContext,
        engine_config: Optional[Dict[str, Any]] = None,
        is_rebuild: bool = False,
        gui: Any = None,
        ark_config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Start an async compilation from a :class:`BuildContext`.

        Delegates to :class:`CompilerCore` which uses the unified core logic.

        Args:
            workspace:     Absolute path to the project workspace.
            engine_id:     Registered engine identifier.
            context:       BuildContext describing the project.
            engine_config: Optional per-engine config overrides.
            is_rebuild:    Whether this is a rebuild from a lock file.
            gui:           Optional GUI instance for auto-mapping and logging.
            ark_config:    Optional raw ark config for deferred lock generation.

        Returns:
            ``True`` if the compilation thread started successfully.
        """
        workspace = Path(workspace)

        # Mettre à jour le workspace
        self._workspace_dir = str(workspace)
        self._current_engine = engine_id
        self._current_file = context.entry_point

        # Émettre le signal de début (approximation pour compatibilité UI)
        compile_info = {
            "engine": engine_id,
            "file": context.entry_point,
            "workspace": str(workspace),
            "command": "[Resolved by Core]",
        }
        self.compilation_started.emit(compile_info)

        return self.compiler.compile_from_context(
            workspace=workspace,
            engine_id=engine_id,
            context=context,
            engine_config=engine_config,
            is_rebuild=is_rebuild,
            gui=gui,
            ark_config=ark_config,
        )

    def reset(self) -> None:
        """Reset process state for a new compilation."""
        self._current_file = None
        self._current_engine = None
        self._set_state(ProcessState.READY)
        self.log_message.emit("info", "Process reset")

    # =========================================================================
    # FONCTIONS DE GESTION DES EXCLUSIONS (intégration ArkConfig)
    # =========================================================================

    def get_exclusion_patterns(self) -> List[str]:
        """Return configured exclusion patterns.

        Returns:
         List of exclusion patterns"""
        if self._workspace_dir:
            try:
                config = load_ark_config(self._workspace_dir)
                # Pour la compilation, on utilise désormais build: exclude
                build_cfg = config.get("build", {})
                if isinstance(build_cfg, dict):
                    return build_cfg.get("exclude", DEFAULT_EXCLUDE_PATTERNS)
            except Exception:
                pass
        return DEFAULT_EXCLUDE_PATTERNS

    def should_exclude(self, file_path: str) -> bool:
        """Determines whether a file must be excluded from compilation.

        Args:
         file_path: Absolute path of the file to check

        Returns:
         True if the file must be excluded, False otherwise"""
        if not self._workspace_dir:
            return False
        patterns = self.get_exclusion_patterns()
        return should_exclude_file(file_path, self._workspace_dir, patterns)
