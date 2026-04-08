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
Compiler Core Module

Main compiler module for PyCompiler ARK.
Handles compilation process execution with threading support
and real-time communication with the user interface.

Provides:
- `CompilationThread` class for non-blocking execution
- `CompilerCore` class for compilation orchestration
- Signals for UI communication
"""

from __future__ import annotations

import os
import sys
import subprocess
import select
import time
import signal
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QThread, Signal, QObject
from Core.process_security import secure_command, hardened_popen_kwargs


class CompilationStatus(Enum):
    """Compilation status."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SUCCESS = "success"
    FAILED = "failed"


class CompilationSignals(QObject):
    """Signals used to communicate with the user interface."""

    output_ready = Signal(str)  # Signal pour stdout
    error_ready = Signal(str)  # Signal pour stderr
    finished = Signal(int)  # Code de retour
    status_changed = Signal(CompilationStatus)  # Changement de statut
    progress_update = Signal(int, str)  # Progression, message


class CompilationThread(QThread):
    """
  Thread used to run compilation without blocking the UI.

  Handles compilation process execution with:
  - Real-time stdout and stderr reading
  - Cancellation support
  - Clean resource handling
  """

    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)
    progress_update = Signal(int, str)

    def __init__(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
    Initialize the compilation thread.

    Args:
      program: Executable path.
      args: Argument list.
      env: Optional environment variables.
      working_dir: Optional working directory.
      timeout: Optional timeout in seconds.
    """
        super().__init__()
        self.program = program
        self.args = args
        self.env = env
        self.working_dir = working_dir
        self.timeout = timeout
        self.cancel_requested = False
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[datetime] = None
        self._live_output_disabled = False
        self._stream_warning_emitted = False
        self._proc_lock = threading.Lock()

    def run(self) -> None:
        """Run the compilation process."""
        self.start_time = datetime.now()
        self.cancel_requested = False

        try:
            # Préparer/valider la commande et l'environnement
            program, args, env = secure_command(self.program, self.args, self.env)
            wd = self._validate_working_dir(self.working_dir)

            # Créer le processus
            with self._proc_lock:
                self.process = subprocess.Popen(
                    [program] + args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    cwd=wd,
                    bufsize=1,
                    **hardened_popen_kwargs(),
                )

            self.progress_update.emit(0, "Process started")

            # Boucle principale de lecture
            self._read_output()

            # Lire les données restantes
            self._read_remaining()

            # Signaler la fin
            return_code = self._current_return_code()
            if self.cancel_requested:
                return_code = -1
            self.finished.emit(return_code)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.error_ready.emit(error_msg)
            self.finished.emit(1)
        finally:
            self._close_streams()

    def _read_output(self) -> None:
        """Read stdout and stderr in real time."""
        while True:
            # Vérifier l'annulation
            if self.cancel_requested:
                self._terminate_process()
                return

            # Vérifier si le processus est terminé
            if self.process is None or self.process.poll() is not None:
                break

            streams = self._available_live_streams()
            if not streams:
                self._warn_missing_live_streams()
                self._live_output_disabled = True
                break

            # Utiliser select pour attendre des données
            try:
                ready, _, _ = select.select(streams, [], [], 0.1)

                for stream in ready:
                    if stream == self.process.stdout:
                        line = self.process.stdout.readline()
                        if line:
                            self.output_ready.emit(line.rstrip())
                            self._update_progress(line)
                    elif stream == self.process.stderr:
                        line = self.process.stderr.readline()
                        if line:
                            self.error_ready.emit(line.rstrip())
                            self._update_progress(line)

            except Exception:
                self._warn_missing_live_streams()
                self._live_output_disabled = True
                break

            time.sleep(0.01)

    def _read_remaining(self) -> None:
        """Read remaining buffered data after process completion."""
        if self.process is None:
            return

        # Lire stdout restant
        try:
            if self.process.stdout is None:
                remaining_stdout = None
            else:
                remaining_stdout = self.process.stdout.read()
            if remaining_stdout:
                for line in remaining_stdout.strip().split("\n"):
                    if line:
                        self.output_ready.emit(line.rstrip())
        except Exception:
            pass

        # Lire stderr restant
        try:
            if self.process.stderr is None:
                remaining_stderr = None
            else:
                remaining_stderr = self.process.stderr.read()
            if remaining_stderr:
                for line in remaining_stderr.strip().split("\n"):
                    if line:
                        self.error_ready.emit(line.rstrip())
        except Exception:
            pass

    def _available_live_streams(self) -> list:
        """Return stdout/stderr streams that can be safely monitored in real time."""
        if self.process is None:
            return []
        streams = []
        try:
            if getattr(self.process, "stdout", None) is not None:
                streams.append(self.process.stdout)
        except Exception:
            pass
        try:
            if getattr(self.process, "stderr", None) is not None:
                streams.append(self.process.stderr)
        except Exception:
            pass
        return streams

    def _warn_missing_live_streams(self) -> None:
        """Emit a single warning when live stdout/stderr monitoring is unavailable."""
        if self._stream_warning_emitted:
            return
        self._stream_warning_emitted = True
        self.error_ready.emit(
            "Warning: stdout/stderr unavailable; stopping real-time output reading."
        )

    def _update_progress(self, line: str) -> None:
        """Update progress based on process output."""
        # Détecter les patterns de progression courants
        progress_patterns = [
            r"\[(\d+)%\]",
            r"Progress:\s*(\d+)",
            r"(\d+)/(\d+)",
        ]

        for pattern in progress_patterns:
            import re

            match = re.search(pattern, line)
            if match:
                if len(match.groups()) == 1:
                    progress = int(match.group(1))
                    self.progress_update.emit(progress, line)
                elif len(match.groups()) == 2:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    progress = int((current / total) * 100)
                    self.progress_update.emit(progress, line)
                break

    def _terminate_process(self) -> None:
        """Stop the process and its process group as quickly as possible."""
        with self._proc_lock:
            proc = self.process
        if proc is None:
            return

        # 1) Fast graceful stop.
        try:
            if os.name != "nt":
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except Exception:
                    proc.terminate()
            else:
                proc.terminate()
        except Exception:
            pass
        if self._wait_process(proc, timeout=0.2):
            return

        # 2) Hard kill (process tree on Windows, process group on POSIX).
        try:
            if os.name == "nt":
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                        timeout=1,
                    )
                except Exception:
                    proc.kill()
            else:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    proc.kill()
        except Exception:
            pass
        self._wait_process(proc, timeout=0.6)
        self._close_streams()

    def cancel(self) -> None:
        """Request cancellation of the compilation."""
        self.cancel_requested = True
        self._terminate_process()

    def _validate_working_dir(self, working_dir: Optional[str]) -> Optional[str]:
        if not working_dir:
            return None
        wd = os.path.abspath(str(working_dir))
        if not os.path.isdir(wd):
            raise FileNotFoundError(f"Working directory not found: {wd}")
        return wd

    def _current_return_code(self) -> int:
        with self._proc_lock:
            proc = self.process
        if proc is None:
            return 1
        rc = proc.returncode
        if rc is None:
            return 1
        return int(rc)

    def _wait_process(self, proc: subprocess.Popen, timeout: float) -> bool:
        try:
            proc.wait(timeout=timeout)
            return True
        except Exception:
            return False

    def _close_streams(self) -> None:
        with self._proc_lock:
            proc = self.process
        if proc is None:
            return
        for stream_name in ("stdout", "stderr", "stdin"):
            try:
                stream = getattr(proc, stream_name, None)
                if stream is not None:
                    stream.close()
            except Exception:
                pass

    @property
    def duration(self) -> Optional[float]:
        """Return execution duration in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None


class CompilerCore(QObject):
    """
  Main compiler class.

  Handles compilation with support for:
  - Asynchronous execution via threads
  - Real-time cancellation
  - Log and error collection
  - Compilation state management
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

    Args:
      parent: Optional parent object.
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
    def current_engine(self) -> Optional[str]:
        """Return the current compilation engine."""
        return self._current_engine

    @property
    def current_file(self) -> Optional[str]:
        """Return the file currently being compiled."""
        return self._current_file

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
    Start a compilation.

    Args:
      program: Executable path
      args: Argument list
      env: Environment variables (optional)
      working_dir: Working directory (optional)
      engine_id: Identifiant du moteur (optionnel)
      file_path: Path du file à compiler (optionnel)
      workspace_dir: Path du workspace (optionnel)

    Returns:
      True si la compilation a démarré, False sinon
    """
        if self.is_running:
            self.log_message.emit("warning", "Compilation already in progress")
            return False

        # Stocker les infos
        self._current_engine = engine_id
        self._current_file = file_path
        self._workspace_dir = workspace_dir

        # Créer le thread
        try:
            safe_program, safe_args, safe_env = secure_command(program, args, env)
        except Exception as e:
            self.log_message.emit("error", f"Unsafe compile command blocked: {e}")
            return False

        self._thread = CompilationThread(
            program=safe_program,
            args=safe_args,
            env=safe_env,
            working_dir=working_dir,
        )

        # Connecter les signaux
        self._thread.output_ready.connect(self.output_ready.emit)
        self._thread.error_ready.connect(self.error_ready.emit)
        self._thread.finished.connect(self._on_finished)
        self._thread.progress_update.connect(self.progress_update.emit)

        # Changer le statut
        self._set_status(CompilationStatus.RUNNING)
        self.log_message.emit(
            "info", f"Starting compilation with {engine_id or 'unknown'}"
        )

        # Démarrer le thread
        self._thread.start()

        return True

    def cancel(self) -> bool:
        """
    Cancel current compilation.

    Returns:
      True si l'annulation a été demandée, False sinon
    """
        if not self.is_running:
            return False

        if self._thread:
            self._thread.cancel()
            self.log_message.emit("info", "Cancellation requested")
            try:
                if self._thread.isRunning():
                    self._thread.wait(150)
                if self._thread.isRunning():
                    self._thread.terminate()
                    self._thread.wait(200)
            except Exception:
                pass
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
            duration = self.duration
            if duration:
                self.log_message.emit(
                    "error",
                    f"Compilation failed (code {return_code}) in {duration:.2f}s",
                )
            else:
                self.log_message.emit(
                    "error", f"Compilation failed with code {return_code}"
                )

        self.finished.emit(return_code)

    def get_command_line(self, program: str, args: List[str]) -> str:
        """
    Return the formatted command line.

    Args:
      program: Programme à exécuter
      args: Arguments

    Returns:
      Ligne de commande formatée
    """
        cmd = [program] + args
        return " ".join(cmd)

    def dry_run(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
    ) -> str:
        """
    Simulate compilation and return the command.

    Args:
      program: Programme à exécuter
      args: Arguments
      env: Environment variables (optional)
      working_dir: Working directory (optional)

    Returns:
      Commande formatée
    """
        cmd = self.get_command_line(program, args)
        result = f"[DRY RUN] Command: {cmd}\n"
        result += f"Working directory: {working_dir or 'current'}\n"

        if env:
            env_info = "\n  ".join(
                [f"{k}={v}" for k, v in env.items() if "ARK" in k or "PATH" in k]
            )
            result += f"Environment:\n  {env_info}"

        return result
