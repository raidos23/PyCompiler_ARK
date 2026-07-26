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
SysDependencyUI — GUI layer for system dependency management.
Uses native elevation (pkexec / UAC). Thread-safe proxying.
"""

import platform
import shutil
from typing import Any, Optional

from PySide6.QtCore import QObject, QProcess, Qt, QTimer
from PySide6.QtWidgets import QMessageBox

from ....Core.SysDependencyManager import SysDependencyManager
from ..WidgetsCreator import ProgressDialog


class SysDependencyUI(SysDependencyManager):
    """
    GUI extension of SysDependencyManager.
    Proxies GUI calls to the main thread to avoid segfaults and PySide6 signature errors.
    """

    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self._ui_callbacks.update(
            {
                "tr": self._ui_tr,
                "register_task": self._ui_register_task,
                "unregister_task": self._ui_unregister_task,
            }
        )
        # Internal storage for progress dialog
        self._progress_dlg = None

    def _ui_tr(self, fr: str, en: str) -> str:
        try:
            from ...i18n import tr_fr_en

            return tr_fr_en(self.parent_widget, fr, en)
        except Exception:
            return en

    def _ui_register_task(
        self, proc: QProcess, dlg: Optional[Any], label_fr: str, label_en: str
    ) -> None:
        if self.parent_widget is None:
            return
        # Task registration is generally thread-safe for list operations
        try:
            tasks = getattr(self.parent_widget, "_sysdep_tasks", [])
            tasks.append(
                {
                    "process": proc,
                    "dialog": dlg,
                    "label_fr": label_fr,
                    "label_en": label_en,
                }
            )
            setattr(self.parent_widget, "_sysdep_tasks", tasks)
        except Exception:
            pass

    def _ui_unregister_task(self, proc: QProcess) -> None:
        if self.parent_widget is None:
            return
        try:
            tasks = getattr(self.parent_widget, "_sysdep_tasks", [])
            setattr(
                self.parent_widget,
                "_sysdep_tasks",
                [t for t in tasks if t.get("process") is not proc],
            )
        except Exception:
            pass

    def _invoke_gui(self, method: callable, *args):
        """
        Invoke a method on the GUI thread using QTimer.singleShot.
        This is the most compatible way to pass a lambda/callable across threads in PySide6.
        """
        if self.parent_widget:
            # QTimer.singleShot(0, context, callable) ensures execution in context's thread
            QTimer.singleShot(0, self.parent_widget, lambda: method(*args))
        else:
            method(*args)

    def tr(self, fr: str, en: str) -> str:
        """Translation helper."""
        return self._ui_tr(fr, en)

    def msg_error(self, fr: str, en: str) -> None:
        def _show():
            QMessageBox.critical(
                self.parent_widget, self.tr("Erreur", "Error"), self.tr(fr, en)
            )

        self._invoke_gui(_show)

    def _show_progress(
        self, title_fr: str, title_en: str, msg_fr: str, msg_en: str
    ):
        def _create():
            # Close existing one if any
            if self._progress_dlg:
                try:
                    self._progress_dlg.close()
                except Exception:
                    pass

            self._progress_dlg = ProgressDialog(
                self.tr(title_fr, title_en), self.parent_widget
            )
            self._progress_dlg.set_message(self.tr(msg_fr, msg_en))
            self._progress_dlg.show()

        self._invoke_gui(_create)

    def _update_progress(self, msg: str):
        def _upd():
            if self._progress_dlg:
                self._progress_dlg.set_message(msg)

        self._invoke_gui(_upd)

    def _close_progress(self):
        def _close():
            if self._progress_dlg:
                self._progress_dlg.close()
                self._progress_dlg = None

        self._invoke_gui(_close)

    def install_packages(self, packages: list[str]) -> Optional[QProcess]:
        """
        Unified entry point for package installation with GUI feedback.
        """
        cmd = self.get_install_command(packages)
        if not cmd:
            self.msg_error(
                "Impossible de générer la commande d'installation (Gestionnaire de paquets manquant).",
                "Cannot generate installation command (Missing package manager).",
            )
            return None

        self._show_progress(
            "Installation système",
            "System installation",
            "Installation des dépendances...",
            "Installing dependencies...",
        )

        def _on_output(text: str):
            lines = [l for l in text.strip().splitlines() if l.strip()]
            if lines:
                self._update_progress(lines[-1][:100])

        def _on_finished(ec, es):
            self._close_progress()
            if ec != 0:
                self.msg_error(
                    "L'installation a échoué.", "Installation failed."
                )

        # Elevation is required for system packages
        proc = self.run_elevated_shell(
            cmd, on_output=_on_output, on_finished=_on_finished
        )

        if proc and self._progress_dlg:
            # Handle cancellation: if user cancels the dialog, kill the process
            self._progress_dlg.canceled.connect(proc.terminate)

        return proc

    def install_packages_linux(
        self, packages: list[str]
    ) -> Optional[QProcess]:
        # Deprecated: use install_packages
        return self.install_packages(packages)

    def install_packages_windows(
        self, packages: list[dict]
    ) -> Optional[QProcess]:
        # Deprecated: use install_packages
        ids = [pkg.get("id") for pkg in packages if pkg.get("id")]
        return self.install_packages(ids)


def install_system_packages(packages: list[str], gui) -> bool:
    mgr = SysDependencyUI(gui)
    return mgr.install_packages(packages) is not None
