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
SysDependencyUI — GUI layer for system dependency management.

This class extends SysDependencyManager (Core) with UI logic
(dialogs, progress bars, message boxes).
"""

import platform
from typing import Any, Optional

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox

from Core.SysDependencyManager import SysDependencyManager
from Ui.Gui.WidgetsCreator import ProgressDialog


class SysDependencyUI(SysDependencyManager):
    """
    GUI extension of SysDependencyManager.
    """

    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        # Register UI callbacks
        self._ui_callbacks.update(
            {
                "tr": self._ui_tr,
                "log_debug": self._ui_log_debug,
                "safe_log": self._ui_safe_log,
                "register_task": self._ui_register_task,
                "unregister_task": self._ui_unregister_task,
                "close_dialog": self._ui_close_dialog,
                "bind_cancel_button": self._ui_bind_cancel_button,
                "ask_sudo_password": self.ask_sudo_password,
                "msg_info": self.msg_info,
                "msg_warning": self.msg_warning,
                "msg_error": self.msg_error,
                "ask_yes_no": self.ask_yes_no,
                "prompt_text": self.prompt_text,
                "install_packages_linux": self.install_packages_linux,
                "install_packages_windows": self.install_packages_windows,
            }
        )

    def _ui_tr(self, fr: str, en: str) -> str:
        try:
            if hasattr(self.parent_widget, "tr"):
                return self.parent_widget.tr(fr, en)
        except Exception:
            pass
        try:
            from Ui.i18n import tr_fr_en

            return tr_fr_en(self.parent_widget, fr, en)
        except Exception:
            return en

    def _ui_log_debug(self, message: str) -> None:
        pw = self.parent_widget
        if pw is not None:
            try:
                if hasattr(pw, "log_debug") and callable(pw.log_debug):
                    pw.log_debug(message)
                elif hasattr(pw, "append_debug") and callable(pw.append_debug):
                    pw.append_debug(message)
                elif hasattr(pw, "logger") and hasattr(pw.logger, "debug"):
                    pw.logger.debug(message)
                else:
                    try:
                        from Ui.i18n import log_with_level

                        log_with_level(pw, "state", message)
                    except Exception:
                        pass
            except Exception:
                pass

    def _ui_safe_log(self, text: str) -> None:
        try:
            if (
                self.parent_widget is not None
                and hasattr(self.parent_widget, "_safe_log")
                and callable(self.parent_widget._safe_log)
            ):
                self.parent_widget._safe_log(text)
        except Exception:
            pass

    def _ui_register_task(
        self, proc: QProcess, dlg: Optional[Any], label_fr: str, label_en: str
    ) -> None:
        try:
            if self.parent_widget is None:
                return
            tasks = getattr(self.parent_widget, "_sysdep_tasks", None)
            if tasks is None:
                tasks = []
                setattr(self.parent_widget, "_sysdep_tasks", tasks)
            tasks.append(
                {
                    "process": proc,
                    "dialog": dlg,
                    "label_fr": label_fr,
                    "label_en": label_en,
                }
            )
        except Exception:
            pass

    def _ui_unregister_task(self, proc: QProcess) -> None:
        try:
            if self.parent_widget is None or not hasattr(
                self.parent_widget, "_sysdep_tasks"
            ):
                return
            tasks = getattr(self.parent_widget, "_sysdep_tasks")
            for t in list(tasks):
                if t.get("process") is proc:
                    tasks.remove(t)
        except Exception:
            pass

    def _ui_close_dialog(self, dlg: Optional[Any]) -> None:
        try:
            if dlg is not None and hasattr(dlg, "close"):
                dlg.close()
        except Exception:
            pass

    def _ui_bind_cancel_button(
        self,
        dlg: Optional[Any],
        proc: Optional[QProcess],
        label_fr: str,
        label_en: str,
    ) -> None:
        try:
            if hasattr(dlg, "btn_cancel") and dlg.btn_cancel:
                dlg.btn_cancel.clicked.connect(
                    lambda: self._cancel_task(proc, dlg, label_fr, label_en)
                )
        except Exception:
            pass

    def ask_sudo_password(self) -> Optional[str]:
        """Ask for sudo password using a masked input dialog."""
        pwd, ok = QInputDialog.getText(
            self.parent_widget,
            self.tr(
                "Mot de passe administrateur requis", "Administrator password required"
            ),
            self.tr(
                "Pour installer les dépendances, entrez votre mot de passe administrateur :",
                "To install dependencies, enter your administrator password:",
            ),
            QLineEdit.Password,
        )
        if ok and pwd:
            return pwd
        return None

    # ------------- MessageBox helpers -------------
    def msg_info(
        self, title_fr: str, title_en: str, body_fr: str, body_en: str
    ) -> None:
        """Show an information message box (no return)."""
        try:
            QMessageBox.information(
                self.parent_widget,
                self.tr(title_fr, title_en),
                self.tr(body_fr, body_en),
            )
        except Exception:
            pass

    def msg_warning(
        self, title_fr: str, title_en: str, body_fr: str, body_en: str
    ) -> None:
        """Show a warning message box (no return)."""
        try:
            QMessageBox.warning(
                self.parent_widget,
                self.tr(title_fr, title_en),
                self.tr(body_fr, body_en),
            )
        except Exception:
            pass

    def msg_error(
        self, title_fr: str, title_en: str, body_fr: str, body_en: str
    ) -> None:
        """Show an error (critical) message box (no return)."""
        try:
            QMessageBox.critical(
                self.parent_widget,
                self.tr(title_fr, title_en),
                self.tr(body_fr, body_en),
            )
        except Exception:
            pass

    def ask_yes_no(
        self,
        title_fr: str,
        title_en: str,
        text_fr: str,
        text_en: str,
        default_yes: bool = True,
    ) -> bool:
        """Ask a Yes/No question. Return True if Yes selected, else False."""
        try:
            msg = QMessageBox(self.parent_widget)
            msg.setIcon(QMessageBox.Question)
            msg.setWindowTitle(self.tr(title_fr, title_en))
            msg.setText(self.tr(text_fr, text_en))
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes if default_yes else QMessageBox.No)
            return msg.exec() == QMessageBox.Yes
        except Exception:
            return False

    def prompt_text(
        self,
        title_fr: str,
        title_en: str,
        label_fr: str,
        label_en: str,
        default: str = "",
        password: bool = False,
    ) -> tuple[Optional[str], bool]:
        """Prompt a text input. If password=True, mask input. Return (value|None, ok)."""
        try:
            echo = QLineEdit.Password if password else QLineEdit.Normal
            val, ok = QInputDialog.getText(
                self.parent_widget,
                self.tr(title_fr, title_en),
                self.tr(label_fr, label_en),
                echo,
                default,
            )
            return (val if ok else None), bool(ok)
        except Exception:
            return None, False

    # ------------- Windows package installs (winget) -------------
    def install_packages_windows(self, packages: list[dict]) -> Optional[QProcess]:
        """
        Install Windows packages via winget with a progress dialog.
        """
        try:
            from Core.Compiler.utils import check_internet_connection

            if not check_internet_connection():
                self.msg_error(
                    "Pas de connexion internet",
                    "No internet connection",
                    "Une connexion internet est requise pour installer des dépendances Windows via winget.",
                    "An internet connection is required to install Windows dependencies via winget.",
                )
                return None

            if platform.system() != "Windows":
                self.msg_error(
                    "Plateforme non supportée",
                    "Unsupported platform",
                    "L'installation automatisée via winget est disponible uniquement sous Windows.",
                    "Automated install via winget is available on Windows only.",
                )
                return None
            if not packages:
                return None
            pm = self.detect_windows_package_manager()
            if pm != "winget":
                # Fallback: open official pages if winget unavailable
                self.msg_warning(
                    "Gestionnaire indisponible",
                    "Manager unavailable",
                    "winget est indisponible. L'installation guidée sera proposée.",
                    "winget is unavailable. Guided installation will be proposed.",
                )
                return None
            names = ", ".join([p.get("id", "?") for p in packages])
            try:
                self._dbg(f"winget install: {names}")
            except Exception:
                pass
            # Progress dialog
            dlg = ProgressDialog(
                self.tr(
                    "Installation des dépendances Windows",
                    "Installing Windows dependencies",
                ),
                self.parent_widget,
                cancelable=True,
            )
            dlg.set_message(self.tr("Préparation…", "Preparing…"))
            dlg.progress.setRange(0, 0)
            dlg.show()
            queue = list(packages)
            proc = QProcess(self.parent_widget)
            state = {"cancelled": False}

            def _cancel_winget():
                if state["cancelled"]:
                    return
                state["cancelled"] = True
                self._cancel_task(
                    proc, dlg, "installation winget", "winget installation"
                )

            try:
                btn = getattr(dlg, "btn_cancel", None)
                if btn is not None:
                    btn.clicked.connect(_cancel_winget)
            except Exception:
                pass

            def _start_next():
                if state["cancelled"] or self._is_process_cancelled(proc):
                    return
                if not queue:
                    try:
                        dlg.close()
                    except Exception:
                        pass
                    self._unregister_task(proc)
                    return
                pkg = queue.pop(0)
                pkg_id = str(pkg.get("id", "")).strip()
                override = str(pkg.get("override", "")).strip()
                if not pkg_id:
                    _start_next()
                    return
                args = [
                    "install",
                    "--id",
                    pkg_id,
                    "-e",
                    "--source",
                    "winget",
                    "--silent",
                    "--accept-source-agreements",
                    "--accept-package-agreements",
                ]
                if override:
                    args += ["--override", override]
                try:
                    dlg.set_message(
                        self.tr(f"Installation: {pkg_id}", f"Installing: {pkg_id}")
                    )
                except Exception:
                    pass
                proc.setProgram("winget")
                proc.setArguments(args)
                try:
                    self._dbg(f"winget start: id={pkg_id} args={' '.join(args)}")
                except Exception:
                    pass
                proc.start()

            def _on_output(p: QProcess, error: bool = False):
                if state["cancelled"] or self._is_process_cancelled(proc):
                    return
                try:
                    data = (
                        p.readAllStandardError().data().decode()
                        if error
                        else p.readAllStandardOutput().data().decode()
                    )
                    try:
                        self._dbg(
                            ("winget STDERR: " if error else "winget STDOUT: ")
                            + data.strip()
                        )
                    except Exception:
                        pass
                    lines = [ln for ln in data.strip().splitlines() if ln.strip()]
                    if lines:
                        dlg.set_message(lines[-1][:200])
                except Exception:
                    pass

            def _on_finished(_ec, _es):
                if state["cancelled"] or self._is_process_cancelled(proc):
                    return
                _start_next()

            proc.readyReadStandardOutput.connect(lambda p=proc: _on_output(p, False))
            proc.readyReadStandardError.connect(lambda p=proc: _on_output(p, True))
            proc.finished.connect(_on_finished)
            # register task and kick off
            self._register_task(proc, dlg, "installation winget", "winget install")
            _start_next()
            self._last_progress_dialog = dlg
            self._last_process = proc
            return proc
        except Exception:
            return None

    # ------------- Progress helpers for system installs -------------
    def start_process_with_progress(
        self,
        program: str,
        args: list[str] | None = None,
        cwd: Optional[str] = None,
        title_fr: str = "Installation des dépendances système",
        title_en: str = "Installing system dependencies",
        start_msg_fr: str = "Démarrage...",
        start_msg_en: str = "Starting...",
    ) -> Optional[QProcess]:
        """
        Launch process with indeterminate progress dialog.
        """
        try:
            dlg = ProgressDialog(
                self.tr(title_fr, title_en), self.parent_widget, cancelable=True
            )
            dlg.set_message(self.tr(start_msg_fr, start_msg_en))
            dlg.progress.setRange(0, 0)  # indéterminé
            dlg.show()
            proc = QProcess(self.parent_widget)
            self._bind_cancel_button(
                dlg, proc, "installation des dépendances", "dependencies installation"
            )
            if cwd:
                proc.setWorkingDirectory(cwd)
            proc.setProgram(program)
            proc.setArguments(list(args or []))

            # Mise à jour du message avec la dernière ligne reçue
            def _on_output(p: QProcess, error: bool = False):
                if self._is_process_cancelled(proc):
                    return
                try:
                    data = (
                        p.readAllStandardError().data().decode()
                        if error
                        else p.readAllStandardOutput().data().decode()
                    )
                    lines = [ln for ln in data.strip().splitlines() if ln.strip()]
                    if lines:
                        dlg.set_message(lines[-1])
                except Exception:
                    pass

            proc.readyReadStandardOutput.connect(lambda p=proc: _on_output(p, False))
            proc.readyReadStandardError.connect(lambda p=proc: _on_output(p, True))

            def _on_finished_wrapper(_ec, _es):
                try:
                    dlg.close()
                except Exception:
                    pass
                finally:
                    self._unregister_task(proc)

            proc.finished.connect(_on_finished_wrapper)
            # Register task for global coordination (quit handling)
            self._register_task(
                proc, dlg, "installation des dépendances", "dependencies installation"
            )
            proc.start()
            # Conserver des refs sur l'instance pour éviter la GC
            self._last_progress_dialog = dlg
            self._last_process = proc
            return proc
        except Exception:
            try:
                # En cas d'échec, fermer la boîte si elle existe
                if getattr(self, "_last_progress_dialog", None):
                    self._last_progress_dialog.close()
            except Exception:
                pass
            return None

    def run_sudo_shell_with_progress(
        self,
        cmd_str: str,
        password: str,
        cwd: Optional[str] = None,
        title_fr: str = "Installation des dépendances système",
        title_en: str = "Installing system dependencies",
        start_msg_fr: str = "Démarrage...",
        start_msg_en: str = "Starting...",
        timeout_s: Optional[int] = None,
    ) -> Optional[QProcess]:
        """
        Run shell command (Linux) expecting sudo -S on stdin with indeterminate progress dialog.
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
            dlg = ProgressDialog(
                self.tr(title_fr, title_en), self.parent_widget, cancelable=True
            )
            dlg.set_message(self.tr(start_msg_fr, start_msg_en))
            dlg.progress.setRange(0, 0)
            dlg.show()
            proc = QProcess(self.parent_widget)
            self._bind_cancel_button(
                dlg, proc, "installation des dépendances", "dependencies installation"
            )
            if cwd:
                proc.setWorkingDirectory(cwd)
            # Utiliser bash -lc pour exécuter la chaîne
            proc.setProgram("/bin/bash")
            proc.setArguments(["-lc", cmd_str])

            # maj message sur sortie
            def _on_output(p: QProcess, error: bool = False):
                if self._is_process_cancelled(proc):
                    return
                try:
                    data = (
                        p.readAllStandardError().data().decode()
                        if error
                        else p.readAllStandardOutput().data().decode()
                    )
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
                            proc.write((password + "\n").encode("utf-8"))
                            try:
                                self._dbg(
                                    "sudo: password prompt detected (progress), password re-sent"
                                )
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        self._dbg(("STDERR: " if error else "STDOUT: ") + data.strip())
                    except Exception:
                        pass
                    lines = [ln for ln in data.strip().splitlines() if ln.strip()]
                    if lines:
                        dlg.set_message(lines[-1])
                except Exception:
                    pass

            def _on_started():
                try:
                    if password:
                        proc.write((password + "\n").encode("utf-8"))
                except Exception:
                    pass

            proc.started.connect(_on_started)
            proc.readyReadStandardOutput.connect(lambda p=proc: _on_output(p, False))
            proc.readyReadStandardError.connect(lambda p=proc: _on_output(p, True))

            def _on_finished_wrapper(_ec, _es):
                try:
                    dlg.close()
                except Exception:
                    pass
                finally:
                    self._unregister_task(proc)

            proc.finished.connect(_on_finished_wrapper)
            # Register task for global coordination (quit handling)
            self._register_task(
                proc, dlg, "installation des dépendances", "dependencies installation"
            )

            def _on_timeout():
                try:
                    self._dbg(f"sudo shell (progress) timeout after {timeout_s}s; killing")
                    from Core.process_killer import kill_process_tree
                    kill_process_tree(proc.processId())
                    dlg.set_message(self.tr("Délai dépassé", "Timed out"))
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
                    f"sudo shell (progress) start: program={proc.program()} args={' '.join(proc.arguments())} cwd={cwd or ''}"
                )
            except Exception:
                pass
            proc.start()
            self._last_progress_dialog = dlg
            self._last_process = proc
            return proc
        except Exception:
            try:
                if getattr(self, "_last_progress_dialog", None):
                    self._last_progress_dialog.close()
            except Exception:
                pass
            return None

    def install_packages_linux(
        self,
        packages: list[str],
        pm: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Optional[QProcess]:
        """
        GUI version of linux package installation with progress dialog.
        """
        try:
            from Core.Compiler.utils import check_internet_connection

            if not check_internet_connection():
                self.msg_error(
                    "Pas de connexion internet",
                    "No internet connection",
                    "Une connexion internet est requise pour installer des dépendances système.",
                    "An internet connection is required to install system dependencies.",
                )
                return None

            if platform.system() != "Linux":
                self.msg_error(
                    "Plateforme non supportée",
                    "Unsupported platform",
                    "L'installation de paquets système automatisée est disponible uniquement sous Linux.",
                    "Automated system package install is available on Linux only.",
                )
                return None
            if not packages:
                return None
            pm = pm or self.detect_linux_package_manager()
            if not pm:
                self.msg_error(
                    "Gestionnaire non détecté",
                    "Package manager not detected",
                    "Impossible de détecter apt/dnf/yum/pacman/zypper.",
                    "Unable to detect apt/dnf/yum/pacman/zypper.",
                )
                return None

            try:
                self._dbg(f"linux install pm={pm} packages={packages}")
            except Exception:
                pass
            if password is None:
                password = self.ask_sudo_password() or ""
                if not password:
                    self.msg_warning(
                        "Mot de passe requis",
                        "Password required",
                        "Aucun mot de passe fourni. Installation annulée.",
                        "No password provided. Installation cancelled.",
                    )
                    return None
            pkgs = " ".join(packages)
            if pm == "apt":
                cmd = (
                    "set -euo pipefail; for i in 1 2 3; do "
                    "sudo -S env DEBIAN_FRONTEND=noninteractive apt-get -o Acquire::Retries=3 update -yq && "
                    'sudo -S env DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::="--force-confdef" '
                    '-o Dpkg::Options::="--force-confnew" -o Acquire::Retries=3 install -yq --no-install-recommends '
                    + pkgs
                    + " "
                    '&& break || { ec=$?; echo "SYSDEP: apt attempt $i failed (exit=$ec), retrying..."; sleep 5; }; done'
                )
            elif pm == "dnf":
                cmd = (
                    "set -euo pipefail; for i in 1 2 3; do "
                    "sudo -S dnf -y install --setopt=install_weak_deps=False --best --allowerasing "
                    + pkgs
                    + " "
                    '&& break || { ec=$?; echo "SYSDEP: dnf attempt $i failed (exit=$ec), retrying..."; sleep 5; }; done'
                )
            elif pm == "yum":
                cmd = (
                    "set -euo pipefail; for i in 1 2 3; do "
                    "sudo -S yum -y install " + pkgs + " "
                    '&& break || { ec=$?; echo "SYSDEP: yum attempt $i failed (exit=$ec), retrying..."; sleep 5; }; done'
                )
            elif pm == "pacman":
                cmd = (
                    "set -euo pipefail; for i in 1 2 3; do "
                    "sudo -S pacman -Sy --noconfirm && sudo -S pacman -S --noconfirm --needed "
                    + pkgs
                    + " "
                    '&& break || { ec=$?; echo "SYSDEP: pacman attempt $i failed (exit=$ec), retrying..."; sleep 5; }; done'
                )
            else:  # zypper
                cmd = (
                    "set -euo pipefail; for i in 1 2 3; do "
                    "sudo -S zypper --non-interactive --gpg-auto-import-keys --no-gpg-checks install -y "
                    + pkgs
                    + " "
                    '&& break || { ec=$?; echo "SYSDEP: zypper attempt $i failed (exit=$ec), retrying..."; sleep 5; }; done'
                )
            try:
                self._dbg(f"linux install cmd: {cmd}")
            except Exception:
                pass
            return self.run_sudo_shell_with_progress(
                cmd,
                password,
                title_fr="Installation des dépendances système",
                title_en="Installing system dependencies",
                start_msg_fr="Téléchargement/installation...",
                start_msg_en="Downloading/Installing...",
                timeout_s=3600,
            )
        except Exception:
            return None


def install_system_packages(packages: list[str], gui) -> bool:
    """
    GUI-specific implementation for installing system packages.
    """
    try:
        manager = SysDependencyUI(gui)
        system = platform.system().lower()

        if system == "linux":
            # For Linux, use the install_packages_linux method
            process = manager.install_packages_linux(packages)
            if process:
                # Wait for completion (simplified - in practice should be async)
                process.waitForFinished(300000)  # 5 minutes timeout
                return process.exitCode() == 0
        elif system == "windows":
            # For Windows, convert package names to winget format
            winget_packages = []
            for pkg in packages:
                # Basic mapping
                if pkg == "build-essential":
                    winget_packages.append(
                        {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                    )
                elif pkg == "python3-dev":
                    winget_packages.append({"id": "Python.Python.3"})
                else:
                    # Generic fallback
                    winget_packages.append({"id": pkg})

            process = manager.install_packages_windows(winget_packages)
            if process:
                process.waitForFinished(300000)  # 5 minutes timeout
                return process.exitCode() == 0
        else:
            # Unsupported platform
            return False

        return False
    except Exception:
        return False
