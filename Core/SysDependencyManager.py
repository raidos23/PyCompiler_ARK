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
Thin bridge Plugins between engines and the operating system for system-level interactions.

This module exposes generic helpers only. Engines (Nuitka, PyOxidizer, etc.)
are responsible for their own dependency policy and user interaction logic
(consent dialogs, exact package lists, commands, etc.).

Provided helpers:
- tr(parent, fr, en): simple translation helper leveraging GUI state
- detect_linux_package_manager(): detect apt/dnf/pacman/zypper
- ask_sudo_password(parent): masked input prompt for sudo
- which(cmd): shutil.which wrapper
- shell_run(cmd | list[str], cwd=None, on_output=None, on_error=None, on_finished=None): non-blocking, headless
- run_sudo_shell(cmd_str, password, cwd=None, on_output=None, on_error=None, on_finished=None): non-blocking, headless (Linux)
- open_urls(urls): open URLs in default browser
"""

import os
import platform
import shutil
import subprocess
import time
import webbrowser
from collections.abc import Callable
from typing import Any, Optional, Union

from PySide6.QtCore import QProcess, QTimer

# Import du système Dialog thread-safe de Plugins_SDK
# (Import not used here, but kept in skeleton if needed for future extensions)


class SysDependencyManager:
    """
    Base class for system dependency management.
    Provides generic logic for detecting package managers and running shell commands.
    """

    def __init__(self, parent_widget=None):
        self.parent_widget = parent_widget
        self._cancelled_procs: set[int] = set()
        # UI delegate callbacks — registered by SysDependencyUI (Ui layer)
        self._ui_callbacks: dict = {}

    def _call_ui(self, method: str, *args, **kwargs) -> Any:
        """Invoke a registered UI callback by name. Returns None if no delegate registered."""
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
        try:
            if proc is not None:
                self._cancelled_procs.discard(id(proc))
        except Exception:
            pass

    def _mark_process_cancelled(self, proc: Optional[QProcess]) -> None:
        try:
            if proc is not None:
                self._cancelled_procs.add(id(proc))
        except Exception:
            pass

    def _is_process_cancelled(self, proc: Optional[QProcess]) -> bool:
        try:
            return proc is not None and id(proc) in self._cancelled_procs
        except Exception:
            return False

    def _log_cancel(self, fr: str, en: str) -> None:
        text = self.tr(fr, en)
        self._call_ui("safe_log", text)
        try:
            self._dbg(text)
        except Exception:
            pass

    def _cancel_task(
        self,
        proc: Optional[QProcess],
        dlg: Optional[Any],
        label_fr: str,
        label_en: str,
    ) -> None:
        self._mark_process_cancelled(proc)
        self._log_cancel(
            f"🛑 Annulation demandée: {label_fr}.",
            f"🛑 Cancellation requested: {label_en}.",
        )
        try:
            if proc is not None and proc.state() != QProcess.NotRunning:
                from Core.process_killer import kill_process_tree
                kill_process_tree(proc.processId())
        except Exception:
            pass
        self._call_ui("close_dialog", dlg)
        try:
            if proc is not None:
                self._unregister_task(proc)
        except Exception:
            pass

    def _bind_cancel_button(
        self,
        dlg: Optional[Any],
        proc: Optional[QProcess],
        label_fr: str,
        label_en: str,
    ) -> None:
        """Logic to bind cancel button, implemented in UI layer if needed."""
        self._call_ui("bind_cancel_button", dlg, proc, label_fr, label_en)

    # ------------- Debug/telemetry helpers -------------
    def set_debug(self, enabled: bool = True) -> None:
        self._debug_enabled = bool(enabled)

    def _dbg(self, message: str) -> None:
        try:
            if not getattr(self, "_debug_enabled", True):
                return
            buf = getattr(self, "_debug_buffer", None)
            if buf is None:
                buf = []
                self._debug_buffer = buf
            line = str(message)
            buf.append(line)
            if len(buf) > 1000:
                del buf[: len(buf) - 1000]

            # Use UI callback for logging if available
            self._call_ui("log_debug", line)
        except Exception:
            pass

    def get_debug_log(self) -> str:
        try:
            return "\n".join(getattr(self, "_debug_buffer", [])[-1000:])
        except Exception:
            return ""

    # ------------- Generic helpers -------------
    def tr(self, fr: str, en: str) -> str:
        res = self._call_ui("tr", fr, en)
        if res is not None:
            return res
        # Pure logic fallback: return English if no UI translator available
        return en

    def detect_linux_package_manager(self) -> Optional[str]:
        """Detect common Linux package managers: apt, dnf, yum, pacman, zypper."""
        for pm in ("apt", "dnf", "yum", "pacman", "zypper"):
            if shutil.which(pm):
                return pm
        return None

    def ask_sudo_password(self) -> Optional[str]:
        """Ask for sudo password using UI callback."""
        return self._call_ui("ask_sudo_password")

    # ------------- MessageBox helpers -------------
    def msg_info(self, *args, **kwargs) -> None:
        self._call_ui("msg_info", *args, **kwargs)

    def msg_warning(self, *args, **kwargs) -> None:
        self._call_ui("msg_warning", *args, **kwargs)

    def msg_error(self, *args, **kwargs) -> None:
        self._call_ui("msg_error", *args, **kwargs)

    def ask_yes_no(self, *args, **kwargs) -> bool:
        res = self._call_ui("ask_yes_no", *args, **kwargs)
        return bool(res) if res is not None else False

    def prompt_text(self, *args, **kwargs) -> tuple[Optional[str], bool]:
        res = self._call_ui("prompt_text", *args, **kwargs)
        return res if res is not None else (None, False)

    def which(self, cmd: str) -> Optional[str]:
        """Wrapper around shutil.which."""
        return shutil.which(cmd)

    def shell_run(
        self,
        cmd: Union[str, list[str]],
        cwd: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int, QProcess.ExitStatus], None]] = None,
    ) -> Optional[QProcess]:
        """
        Non-blocking execution of a command without sudo using QProcess.
        Does not display any dialog and streams output via callbacks.
        Returns the QProcess instance or None on failure.
        """
        try:
            proc = QProcess(self.parent_widget)
            if cwd:
                proc.setWorkingDirectory(cwd)

            if isinstance(cmd, list) and cmd:
                program, args = cmd[0], list(cmd[1:])
                proc.setProgram(program)
                proc.setArguments(args)
            else:
                # Use bash -lc for shell features when a string command is provided
                proc.setProgram("/bin/bash")
                proc.setArguments(["-lc", str(cmd)])

            def _emit_output(p: QProcess, is_error: bool = False):
                try:
                    data = (
                        p.readAllStandardError().data().decode()
                        if is_error
                        else p.readAllStandardOutput().data().decode()
                    )
                    if data:
                        try:
                            self._dbg(
                                ("STDERR: " if is_error else "STDOUT: ") + data.strip()
                            )
                        except Exception:
                            pass
                        if is_error and callable(on_error):
                            on_error(data)
                        elif (not is_error) and callable(on_output):
                            on_output(data)
                except Exception:
                    pass

            def _on_finished(ec: int, es: QProcess.ExitStatus):
                try:
                    if callable(on_finished):
                        on_finished(ec, es)
                finally:
                    self._unregister_task(proc)

            proc.readyReadStandardOutput.connect(lambda p=proc: _emit_output(p, False))
            proc.readyReadStandardError.connect(lambda p=proc: _emit_output(p, True))
            proc.finished.connect(_on_finished)

            # Register task for potential global coordination (dialog=None)
            try:
                self._register_task(proc, None, "commande système", "system command")
            except Exception:
                pass

            try:
                self._dbg(
                    f"shell_run start: program={proc.program()} args={' '.join(proc.arguments())} cwd={cwd or ''}"
                )
            except Exception:
                pass
            proc.start()
            self._last_process = proc
            return proc
        except Exception:
            return None

    def run_sudo_shell(
        self,
        cmd_str: str,
        password: str,
        cwd: Optional[str] = None,
        on_output: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
        on_finished: Optional[Callable[[int, QProcess.ExitStatus], None]] = None,
        timeout_s: Optional[int] = None,
    ) -> Optional[QProcess]:
        """
        Non-blocking execution of a sudo-enabled shell command string on Linux using QProcess.
        No dialog is shown. The sudo password is written to stdin when the process starts.
        Streams output via callbacks and returns the QProcess instance or None on failure.
        """
        try:
            if platform.system() != "Linux":
                self.msg_error(
                    "Plateforme non supportée",
                    "Unsupported platform",
                    "Cette opération sudo est supportée uniquement sous Linux.",
                    "This sudo operation is supported on Linux only.",
                )
                return None

            proc = QProcess(self.parent_widget)
            if cwd:
                proc.setWorkingDirectory(cwd)
            proc.setProgram("/bin/bash")
            proc.setArguments(["-lc", cmd_str])

            def _emit_output(p: QProcess, is_error: bool = False):
                try:
                    data = (
                        p.readAllStandardError().data().decode()
                        if is_error
                        else p.readAllStandardOutput().data().decode()
                    )
                    if data:
                        # Auto-respond to sudo password prompts if they reappear
                        try:
                            low = data.lower()
                            if (
                                password
                                and ("password" in low)
                                and (
                                    "sudo" in low
                                    or "[sudo]" in low
                                    or "password for" in low
                                )
                            ):
                                p.write((password + "\n").encode("utf-8"))
                                try:
                                    self._dbg(
                                        "sudo: password prompt detected, password re-sent"
                                    )
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        try:
                            self._dbg(
                                ("STDERR: " if is_error else "STDOUT: ") + data.strip()
                            )
                        except Exception:
                            pass
                        if is_error and callable(on_error):
                            on_error(data)
                        elif (not is_error) and callable(on_output):
                            on_output(data)
                except Exception:
                    pass

            def _on_started():
                try:
                    if password:
                        proc.write((password + "\n").encode("utf-8"))
                except Exception:
                    pass

            def _on_finished(ec: int, es: QProcess.ExitStatus):
                try:
                    if callable(on_finished):
                        on_finished(ec, es)
                finally:
                    self._unregister_task(proc)

            proc.started.connect(_on_started)
            proc.readyReadStandardOutput.connect(lambda p=proc: _emit_output(p, False))
            proc.readyReadStandardError.connect(lambda p=proc: _emit_output(p, True))
            proc.finished.connect(_on_finished)

            try:
                self._register_task(proc, None, "commande sudo", "sudo command")
            except Exception:
                pass

            def _on_timeout():
                try:
                    self._dbg(f"sudo shell timeout after {timeout_s}s; killing")
                    from Core.process_killer import kill_process_tree
                    kill_process_tree(proc.processId())
                except Exception:
                    pass

            # Optional timeout to enforce robustness
            if timeout_s and int(timeout_s) > 0:
                try:
                    timer = QTimer(self.parent_widget)
                    timer.setSingleShot(True)
                    timer.timeout.connect(_on_timeout)
                    timer.start(int(timeout_s) * 1000)
                    proc.finished.connect(lambda *_: timer.stop())
                    self._last_timer = timer
                except Exception:
                    pass

            try:
                self._dbg(
                    f"sudo shell start: program={proc.program()} args={' '.join(proc.arguments())} cwd={cwd or ''}"
                )
            except Exception:
                pass
            proc.start()
            self._last_process = proc
            return proc
        except Exception:
            return None

    def open_urls(self, urls: list[str]) -> None:
        for u in urls or []:
            try:
                webbrowser.open(u)
            except Exception:
                pass

    # ------------- Package installation delegation -------------
    def install_packages_linux(
        self,
        packages: list[str],
        pm: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Any:
        """Delegate to UI if available, else return None (not supported headlessly via this method)."""
        return self._call_ui("install_packages_linux", packages, pm, password)

    def install_packages_windows(self, packages: list[dict]) -> Any:
        """Delegate to UI if available, else return None."""
        return self._call_ui("install_packages_windows", packages)

    # ------------- Windows package installs (winget) -------------
    def detect_windows_package_manager(self) -> Optional[str]:
        """Detect winget (preferred) or choco on Windows."""
        try:
            if platform.system() != "Windows":
                return None
            if shutil.which("winget"):
                return "winget"
            if shutil.which("choco"):
                return "choco"
        except Exception:
            return None
        return None

    # ------------- GUI logic moved to SysDependencyUI -------------


from Core.Compiler.utils import check_internet_connection


def check_system_packages(packages: list[str]) -> bool:
    """
    Check if system packages/tools are installed.
    Returns True if all packages/tools are available, False otherwise.
    Uses shutil.which() to check for command availability.
    """
    try:
        if not packages:
            return True
        for pkg in packages:
            if pkg and not shutil.which(pkg):
                return False
        return True
    except Exception:
        return False


def install_system_packages(packages: list[str], gui=None) -> bool:
    """
    Install system packages using the appropriate package manager.
    In Core, this is a pure logic entry point (headless/CI).
    GUI-specific logic is handled in the UI layer.
    """
    return _install_system_packages_logic(packages)


def _install_system_packages_logic(packages: list[str]) -> bool:
    """Install system packages without Qt UI for CLI/CI contexts."""
    try:
        if not check_internet_connection():
            return False

        pkgs = [str(p).strip() for p in (packages or []) if str(p).strip()]
        if not pkgs:
            return True

        system = platform.system().lower()
        if system != "linux":
            # Keep behavior explicit for now: only Linux is supported in CI path.
            return False

        pm = None
        for candidate in ("apt", "dnf", "yum", "pacman", "zypper"):
            if shutil.which(candidate):
                pm = candidate
                break
        if not pm:
            return False

        def _with_privilege(args: list[str]) -> list[str]:
            try:
                if hasattr(os, "geteuid") and os.geteuid() == 0:
                    return list(args)
            except Exception:
                pass
            # CI/CD mode: strictly non-interactive sudo.
            return ["sudo", "-n"] + list(args)

        steps: list[list[str]]
        run_env = os.environ.copy()
        if pm == "apt":
            # apt-get is more stable than apt for non-interactive automation.
            run_env["DEBIAN_FRONTEND"] = "noninteractive"
            steps = [
                _with_privilege(["apt-get", "-o", "Acquire::Retries=3", "update"]),
                _with_privilege(
                    [
                        "apt-get",
                        "-o",
                        "Dpkg::Options::=--force-confdef",
                        "-o",
                        "Dpkg::Options::=--force-confnew",
                        "-o",
                        "Acquire::Retries=3",
                        "install",
                        "-y",
                        "--no-install-recommends",
                        *pkgs,
                    ]
                ),
            ]
        elif pm == "dnf":
            steps = [_with_privilege(["dnf", "install", "-y", *pkgs])]
        elif pm == "yum":
            steps = [_with_privilege(["yum", "install", "-y", *pkgs])]
        elif pm == "pacman":
            steps = [
                _with_privilege(["pacman", "-Sy", "--noconfirm"]),
                _with_privilege(["pacman", "-S", "--noconfirm", "--needed", *pkgs]),
            ]
        else:
            steps = [
                _with_privilege(
                    [
                        "zypper",
                        "--non-interactive",
                        "--gpg-auto-import-keys",
                        "--no-gpg-checks",
                        "install",
                        "-y",
                        *pkgs,
                    ]
                )
            ]

        for cmd in steps:
            ok = False
            # Retry transient failures (network mirrors, temporary locks, etc.).
            for attempt in range(3):
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=1800,
                    check=False,
                    env=run_env,
                )
                if proc.returncode == 0:
                    ok = True
                    break
                if attempt < 2:
                    time.sleep(2)
            if not ok:
                return False
        return True
    except Exception:
        return False
