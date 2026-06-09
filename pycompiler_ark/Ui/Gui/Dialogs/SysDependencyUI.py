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
Uses native elevation (pkexec / UAC). No password handling.
"""

import platform
import shutil
from typing import Any, Optional

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QMessageBox

from pycompiler_ark.Core.SysDependencyManager import SysDependencyManager
from pycompiler_ark.Ui.Gui.WidgetsCreator import ProgressDialog


class SysDependencyUI(SysDependencyManager):
    """
    GUI extension of SysDependencyManager.
    Simplified: delegates authentication to the OS.
    """

    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self._ui_callbacks.update({
            "tr": self._ui_tr,
            "register_task": self._ui_register_task,
            "unregister_task": self._ui_unregister_task,
        })

    def _ui_tr(self, fr: str, en: str) -> str:
        try:
            from pycompiler_ark.Ui.i18n import tr_fr_en
            return tr_fr_en(self.parent_widget, fr, en)
        except Exception:
            return en

    def _ui_register_task(self, proc: QProcess, dlg: Optional[Any], label_fr: str, label_en: str) -> None:
        if self.parent_widget is None: return
        tasks = getattr(self.parent_widget, "_sysdep_tasks", [])
        tasks.append({"process": proc, "dialog": dlg, "label_fr": label_fr, "label_en": label_en})
        setattr(self.parent_widget, "_sysdep_tasks", tasks)

    def _ui_unregister_task(self, proc: QProcess) -> None:
        if self.parent_widget is None: return
        tasks = getattr(self.parent_widget, "_sysdep_tasks", [])
        setattr(self.parent_widget, "_sysdep_tasks", [t for t in tasks if t.get("process") is not proc])

    def msg_error(self, fr: str, en: str) -> None:
        QMessageBox.critical(self.parent_widget, self.tr("Erreur", "Error"), self.tr(fr, en))

    def install_packages_linux(self, packages: list[str]) -> Optional[QProcess]:
        pm = self.detect_linux_package_manager()
        if not pm:
            self.msg_error("Gestionnaire de paquets non détecté.", "Package manager not detected.")
            return None

        pkgs = " ".join(packages)
        cmd = f"{pm} install -y {pkgs}"
        
        dlg = ProgressDialog(self.tr("Installation système", "System installation"), self.parent_widget)
        dlg.set_message(self.tr("Installation des dépendances...", "Installing dependencies..."))
        dlg.show()

        def _on_output(text: str):
            lines = [l for l in text.strip().splitlines() if l.strip()]
            if lines: dlg.set_message(lines[-1][:100])

        def _on_finished(ec, es):
            dlg.close()
            if ec != 0: self.msg_error("L'installation a échoué.", "Installation failed.")

        return self.run_elevated_shell(cmd, on_output=_on_output, on_finished=_on_finished)

    def install_packages_windows(self, packages: list[dict]) -> Optional[QProcess]:
        if not shutil.which("winget"):
            self.msg_error("winget est requis sur Windows.", "winget is required on Windows.")
            return None

        # On combine les installs en une seule commande shell pour retourner un seul QProcess
        ids = [pkg.get("id") for pkg in packages if pkg.get("id")]
        if not ids: return None
        
        # Commande Windows qui enchaîne les winget
        cmd_parts = [f"winget install --id {pid} --silent --accept-source-agreements --accept-package-agreements" for pid in ids]
        full_cmd = " && ".join(cmd_parts)
        
        dlg = ProgressDialog(self.tr("Installation Windows", "Windows installation"), self.parent_widget)
        dlg.set_message(self.tr("Préparation de winget...", "Preparing winget..."))
        dlg.show()

        def _on_output(text: str):
            lines = [l for l in text.strip().splitlines() if l.strip()]
            if lines: dlg.set_message(lines[-1][:100])

        def _on_finished(ec, es):
            dlg.close()
            if ec != 0: self.msg_error("L'installation winget a échoué.", "winget installation failed.")

        return self.shell_run(full_cmd, on_output=_on_output, on_finished=_on_finished)

def install_system_packages(packages: list[str], gui) -> bool:
    mgr = SysDependencyUI(gui)
    if platform.system() == "Linux":
        return mgr.install_packages_linux(packages) is not None
    elif platform.system() == "Windows":
        win_pkgs = [{"id": p} for p in packages]
        return mgr.install_packages_windows(win_pkgs) is not None
    return False
