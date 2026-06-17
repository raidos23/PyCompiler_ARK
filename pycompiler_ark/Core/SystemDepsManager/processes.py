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

"""Process execution helpers for system commands."""

from __future__ import annotations

import platform
import webbrowser
from collections.abc import Callable
from typing import Any, Optional, Union

from PySide6.QtCore import QObject, QProcess


class ProcessBridge:
    """Thin wrapper around QProcess execution and UI task registration."""

    def __init__(self, parent_widget: Optional[QObject] = None):
        self.parent_widget = parent_widget
        self._ui_callbacks: dict = {}

    def _call_ui(self, method: str, *args, **kwargs) -> Any:
        fn = self._ui_callbacks.get(method)
        if callable(fn):
            try:
                return fn(*args, **kwargs)
            except Exception:
                pass
        return None

    def _register_task(
        self, proc: QProcess, dlg: Optional[Any], label_fr: str, label_en: str
    ) -> None:
        self._call_ui("register_task", proc, dlg, label_fr, label_en)

    def _unregister_task(self, proc: QProcess) -> None:
        self._call_ui("unregister_task", proc)

    def shell_run(
        self,
        cmd: Union[str, list[str]],
        cwd: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int, QProcess.ExitStatus], None]] = None,
    ) -> Optional[QProcess]:
        try:
            proc = QProcess()
            if cwd:
                proc.setWorkingDirectory(cwd)

            if isinstance(cmd, list):
                proc.setProgram(cmd[0])
                proc.setArguments(cmd[1:])
            else:
                proc.setProgram("/bin/bash" if platform.system() != "Windows" else "cmd.exe")
                proc.setArguments(["-lc", cmd] if platform.system() != "Windows" else ["/c", cmd])

            def _read_output():
                raw = proc.readAllStandardOutput().data().decode(errors="replace")
                if on_output:
                    on_output(raw)

            def _read_error():
                raw = proc.readAllStandardError().data().decode(errors="replace")
                if on_output:
                    on_output(raw)

            proc.readyReadStandardOutput.connect(_read_output)
            proc.readyReadStandardError.connect(_read_error)

            def _finished_wrapper(ec, es):
                if on_finished:
                    on_finished(ec, es)
                self._unregister_task(proc)

            proc.finished.connect(_finished_wrapper)
            self._register_task(proc, None, "commande système", "system command")
            proc.start()
            return proc
        except Exception:
            return None

    def run_elevated_shell(
        self,
        cmd_str: str,
        cwd: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int, QProcess.ExitStatus], None]] = None,
    ) -> Optional[QProcess]:
        if platform.system() == "Linux":
            return self.shell_run(f"pkexec bash -lc '{cmd_str}'", cwd, on_output, on_finished)
        if platform.system() == "Windows":
            return self.shell_run(cmd_str, cwd, on_output, on_finished)
        return None

    def open_urls(self, urls: list[str]) -> None:
        for u in urls or []:
            webbrowser.open(u)
