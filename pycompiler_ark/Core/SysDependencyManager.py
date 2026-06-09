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
Bridge between engines and the operating system for system-level interactions.
Uses native elevation (pkexec on Linux, UAC on Windows).
"""

import os
import platform
import shutil
import subprocess
import webbrowser
from collections.abc import Callable
from typing import Any, Optional, Union

from PySide6.QtCore import QProcess, QObject


class SysDependencyManager:
    """
    Base class for system dependency management.
    Handles command execution and package manager detection.
    """

    def __init__(self, parent_widget: Optional[QObject] = None):
        # parent_widget is used for UI callbacks and global task registration
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

    def _register_task(self, proc: QProcess, dlg: Optional[Any], label_fr: str, label_en: str) -> None:
        self._call_ui("register_task", proc, dlg, label_fr, label_en)

    def _unregister_task(self, proc: QProcess) -> None:
        self._call_ui("unregister_task", proc)

    def tr(self, fr: str, en: str) -> str:
        res = self._call_ui("tr", fr, en)
        return res if res is not None else en

    def detect_linux_package_manager(self) -> Optional[str]:
        for pm in ("apt", "dnf", "yum", "pacman", "zypper"):
            if shutil.which(pm):
                return pm
        return None

    def detect_macos_package_manager(self) -> Optional[str]:
        if shutil.which("brew"):
            return "brew"
        return None

    def which(self, cmd: str) -> Optional[str]:
        return shutil.which(cmd)

    def get_install_command(self, packages: list[str]) -> Optional[str]:
        """
        Generate the appropriate installation command string for the current platform.
        Returns None if no supported package manager is found.
        """
        if not packages:
            return None

        system = platform.system()
        if system == "Linux":
            pm = self.detect_linux_package_manager()
            if not pm:
                return None
            pkgs = " ".join(packages)
            # Standard install command for most Linux package managers
            return f"{pm} install -y {pkgs}"

        elif system == "Windows":
            if not shutil.which("winget"):
                return None
            # Building a combined winget command
            parts = [
                f"winget install --id {p} --silent --accept-source-agreements --accept-package-agreements"
                for p in packages
            ]
            return " && ".join(parts)

        elif system == "Darwin":  # macOS
            pm = self.detect_macos_package_manager()
            if pm == "brew":
                pkgs = " ".join(packages)
                return f"brew install {pkgs}"

        return None

    def shell_run(
        self,
        cmd: Union[str, list[str]],
        cwd: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int, QProcess.ExitStatus], None]] = None,
    ) -> Optional[QProcess]:
        """Runs a command without elevation."""
        try:
            proc = QProcess()
            if cwd:
                proc.setWorkingDirectory(cwd)

            if isinstance(cmd, list):
                proc.setProgram(cmd[0])
                proc.setArguments(cmd[1:])
            else:
                proc.setProgram(
                    "/bin/bash" if platform.system() != "Windows" else "cmd.exe"
                )
                args = (
                    ["-lc", cmd]
                    if platform.system() != "Windows"
                    else ["/c", cmd]
                )
                proc.setArguments(args)

            def _read_output():
                # Use errors='replace' to avoid crashes on Windows with non-UTF8 encodings
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

            # Note: The process is registered for global cleanup tracking
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
        """Runs a command with native elevation (pkexec on Linux)."""
        if platform.system() == "Linux":
            full_cmd = f"pkexec bash -lc '{cmd_str}'"
            return self.shell_run(full_cmd, cwd, on_output, on_finished)
        elif platform.system() == "Windows":
            return self.shell_run(cmd_str, cwd, on_output, on_finished)
        return None

    def open_urls(self, urls: list[str]) -> None:
        for u in urls or []:
            webbrowser.open(u)


from pycompiler_ark.Core.Compiler.utils import check_internet_connection

def check_system_packages(packages: list[str]) -> bool:
    return all(shutil.which(pkg) for pkg in packages if pkg)

def install_system_packages(packages: list[str], gui=None) -> bool:
    """Headless/CI install entry point."""
    if not check_internet_connection(): return False
    pkgs = [p.strip() for p in packages if p.strip()]
    if not pkgs: return True
    
    pm = SysDependencyManager().detect_linux_package_manager()
    if not pm: return False

    cmd_prefix = ["sudo", "-n"] 
    if pm == "apt":
        steps = [cmd_prefix + ["apt-get", "update"], cmd_prefix + ["apt-get", "install", "-y"] + pkgs]
    else:
        steps = [cmd_prefix + [pm, "install", "-y"] + pkgs]

    for cmd in steps:
        if subprocess.run(cmd).returncode != 0: return False
    return True
