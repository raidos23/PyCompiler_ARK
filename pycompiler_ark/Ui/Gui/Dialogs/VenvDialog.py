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

"""VenvManagerUI — GUI layer of the venv manager.

This class extends VenvManager (Core) with interface logic
user (dialogues, folder selection, updating labels).

The business logic (detection, validation, pip process) remains in Core."""

import os

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from pycompiler_ark.Ui import output

from ....Core.Venv_Manager.Manager import VenvManager
from ..WidgetsCreator import ProgressDialog
from ... import output


class VenvManagerUI(VenvManager):
    """
    Extension GUI de VenvManager.

    Responsibilities:
    - Manuel venv selection dialog (QFileDialog)
    - Invalid-venv confirmation dialog (QMessageBox)
    - Updating parent widget labels (venv_label, venv_path_edit)
    - Managing ProgressDialog instances via callbacks
    - Registering all UI callbacks into VenvManager's _ui_callbacks dict
    """

    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        self._progress_dialogs: dict[str, ProgressDialog] = {}

        # Register UI callbacks so Core methods can trigger GUI updates
        self._ui_callbacks.update(
            {
                "tr": self._ui_tr,
                "log": self._ui_log,
                "log_message": self._ui_log_message,
                "on_pref_applied": self._on_pref_applied,
                "update_venv_label": self._update_venv_label,
                "update_venv_path_edit": self._update_venv_path_edit,
                "ask_recreate_invalid_venv": self._ask_recreate_invalid_venv,
                "show_error_dialog": self._show_error_dialog,
                "show_progress": self._show_progress,
                "update_progress_message": self._update_progress_message,
                "update_progress_progress": self._update_progress_progress,
                "close_progress": self._close_progress,
                "is_progress_visible": self._is_progress_visible,
                "bind_cancel": self._bind_cancel,
                "process_events": self._process_events,
            }
        )

    # ------------------------------------------------------------------
    # UI callback implementations
    # ------------------------------------------------------------------

    def _ui_tr(self, fr: str, en: str) -> str:
        """Translate text via the UI translator."""
        try:
            if hasattr(self.parent, "tr"):
                return self.parent.tr(fr, en)
        except Exception:
            pass
        return en

    def _ui_log(self, level: str, text: str) -> None:
        """Log a message via the UI logging system."""
        try:
            output.log(level, text)
        except Exception:
            pass

    def _ui_log_message(self, level: str, text_fr: str, text_en: str) -> None:
        """Log an internationalized message via the UI logging system."""
        try:
            output.log(level, (text_fr, text_en))
        except Exception:
            pass

    def _on_pref_applied(self, mode: str, venv_path: str | None) -> None:
        """Handle UI updates when a preference is applied from pycompiler_ark.Core."""
        if mode == "system":
            try:
                if hasattr(self.parent, "venv_path"):
                    setattr(self.parent, "venv_path", None)
            except Exception:
                pass
            self._update_venv_label(self._pref_label_system())
            self._update_venv_path_edit(self._pref_label_system())
        elif mode == "venv" and venv_path:
            try:
                if hasattr(self.parent, "venv_path"):
                    setattr(self.parent, "venv_path", venv_path)
            except Exception:
                pass
            self._update_venv_label(f"Venv sélectionné : {venv_path}")
            self._update_venv_path_edit(venv_path)

    def _update_venv_label(self, text: str) -> None:
        """Set the venv label on the parent widget if it exists."""
        try:
            if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                self.parent.venv_label.setText(text)
        except Exception:
            pass

    def _update_venv_path_edit(self, text: str) -> None:
        """Set the venv path edit field on the parent widget if it exists."""
        try:
            if (
                hasattr(self.parent, "venv_path_edit")
                and self.parent.venv_path_edit
            ):
                self.parent.venv_path_edit.setText(text)
        except Exception:
            pass

    def _ask_recreate_invalid_venv(self, venv_root: str, reason: str) -> bool:
        """Show a QMessageBox asking the user to confirm venv deletion/recreation.
        Returns True if the user accepted, False otherwise.
        """
        try:
            title = (
                "Environnement virtuel invalide / Invalid virtual environment"
            )
            folder = os.path.basename(os.path.normpath(venv_root))
            msg = (
                "L'environnement virtuel du workspace est invalide :\n"
                f"- {reason}\n\n"
                f"Voulez-vous supprimer le dossier '{folder}' et le recréer ?\n\n"
                "The workspace virtual environment is invalid:\n"
                f"- {reason}\n\n"
                f"Do you want to delete the '{folder}' folder and recreate it?"
            )
            reply = QMessageBox.question(
                self.parent,
                title,
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            return reply == QMessageBox.Yes
        except Exception:
            return False

    def _show_error_dialog(self, title: str, text: str) -> None:
        """Show a critical QMessageBox error dialog."""
        try:
            QMessageBox.critical(self.parent, title, text)
        except Exception:
            pass

    def _show_progress(self, id: str, title: str, cancel_label: str) -> None:
        """Create and show a progress dialog."""
        try:
            self._close_progress(id)
            dlg = ProgressDialog(title, self.parent, cancelable=True)
            self._progress_dialogs[id] = dlg
            dlg.show()
        except Exception:
            pass

    def _update_progress_message(self, id: str, message: str) -> None:
        """Update the message of a progress dialog."""
        try:
            dlg = self._progress_dialogs.get(id)
            if dlg:
                dlg.set_message(message)
        except Exception:
            pass

    def _update_progress_progress(
        self, id: str, value: int, total: int
    ) -> None:
        """Update the progress bar of a progress dialog."""
        try:
            dlg = self._progress_dialogs.get(id)
            if dlg:
                if total > 0:
                    dlg.set_progress(value, total)
                else:
                    # If total is 0, it might mean indeterminate
                    dlg.progress.setRange(0, 0)
        except Exception:
            pass

    def _close_progress(self, id: str) -> None:
        """Close a progress dialog."""
        try:
            dlg = self._progress_dialogs.pop(id, None)
            if dlg:
                dlg.close()
        except Exception:
            pass

    def _is_progress_visible(self, id: str) -> bool:
        """Check if a progress dialog is visible."""
        try:
            dlg = self._progress_dialogs.get(id)
            return bool(dlg and dlg.isVisible())
        except Exception:
            return False

    def _bind_cancel(self, id: str, callback) -> None:
        """Bind a cancellation callback to a progress dialog."""
        try:
            dlg = self._progress_dialogs.get(id)
            if dlg and hasattr(dlg, "btn_cancel") and dlg.btn_cancel:
                dlg.btn_cancel.clicked.connect(callback)
        except Exception:
            pass

    def _process_events(self) -> None:
        """Process pending UI events."""
        try:
            QApplication.processEvents()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # GUI-only methods (moved from VenvManager)
    # ------------------------------------------------------------------

    def select_venv_manually(self) -> None:
        """Open dialog to manually select a venv or switch to system Python."""
        workspace_dir = getattr(self.parent, "workspace_dir", None)
        if not workspace_dir:
            QMessageBox.warning(
                self.parent,
                self.tr("Attention", "Warning"),
                self.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return

        try:
            ok_sys, missing, has_source = self._can_use_system_python()
            if ok_sys:
                title = self.parent.tr("Suggestion de venv", "Venv suggestion")
                if has_source:
                    msg = self.parent.tr(
                        "Python système contient les dépendances nécessaires.\n"
                        "Souhaitez-vous l'utiliser ?",
                        "System Python has the required dependencies.\n"
                        "Do you want to use it?",
                    )
                else:
                    msg = self.parent.tr(
                        "Aucun fichier de dépendances détecté.\n"
                        "Souhaitez-vous utiliser Python système ?",
                        "No dependency file detected.\n"
                        "Do you want to use System Python?",
                    )
                reply = QMessageBox.question(
                    self.parent, title, msg, QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._apply_system_python()
                    return
            else:
                if missing:
                    try:
                        output.log(
                            f"ℹ️ Python système incomplet (dépendances manquantes: {', '.join(sorted(set(missing)))})"
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        folder = QFileDialog.getExistingDirectory(
            self.parent,
            self.parent.tr("Choisir un dossier venv", "Choose a venv folder"),
            "",
        )
        if folder:
            path = os.path.abspath(folder)
            ok, reason = self.validate_venv_strict(path)
            if ok:
                try:
                    setattr(self.parent, "use_system_python", False)
                except Exception:
                    pass
                self.parent.venv_path_manuel = path
                self._update_venv_label(f"Venv sélectionné : {path}")
                output.success(f"✅ Venv valide sélectionné: {path}")
                try:
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    self.save_workspace_pref(workspace_dir)
                except Exception:
                    pass
            else:
                output.warn(f"❌ Venv refusé: {reason}")
                self.parent.venv_path_manuel = None
                try:
                    setattr(self.parent, "use_system_python", False)
                except Exception:
                    pass
                self._update_venv_label(self._pref_label_none())
                try:
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    self.save_workspace_pref(workspace_dir)
                except Exception:
                    pass
                # Propose retry or venv creation
                try:

                    def _t(fr: str, en: str) -> str:
                        try:
                            return self.parent.tr(fr, en)
                        except Exception:
                            return en

                    box = QMessageBox(self.parent)
                    box.setWindowTitle(_t("Venv invalide", "Invalid Venv"))
                    box.setText(
                        _t(
                            "Le dossier sélectionné n'est pas un venv valide. Réessayer ou créer un venv ?",
                            "The selected folder is not a valid venv. Retry or create a venv?",
                        )
                    )
                    if reason:
                        try:
                            box.setInformativeText(str(reason))
                        except Exception:
                            pass
                    btn_retry = box.addButton(
                        _t("Réessayer", "Retry"), QMessageBox.AcceptRole
                    )
                    btn_create = None
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    if workspace_dir:
                        btn_create = box.addButton(
                            _t("Créer un venv", "Create venv"),
                            QMessageBox.ActionRole,
                        )
                    box.addButton(
                        _t("Annuler", "Cancel"), QMessageBox.RejectRole
                    )
                    box.exec()
                    if box.clickedButton() == btn_retry:
                        self.select_venv_manually()
                        return
                    if btn_create and box.clickedButton() == btn_create:
                        try:
                            self.create_venv_if_needed(workspace_dir)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
        else:
            self.parent.venv_path_manuel = None
            try:
                setattr(self.parent, "use_system_python", False)
            except Exception:
                pass
            self._update_venv_label(self._pref_label_none())
            try:
                workspace_dir = getattr(self.parent, "workspace_dir", None)
                self.save_workspace_pref(workspace_dir)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Workspace preference management (Delegated to Core)
    # ------------------------------------------------------------------

    def _pref_label_system(self) -> str:
        """Execute _pref_label_system logic for this component."""
        return self.tr(
            "Venv sélectionné : Python système",
            "Venv selected: System Python",
        )

    def _pref_label_none(self) -> str:
        """Execute _pref_label_none logic for this component."""
        return self.tr("Venv sélectionné : Aucun", "Venv selected: None")

    def _apply_system_python(self) -> None:
        """Apply system Python selection and update UI."""
        try:
            setattr(self.parent, "use_system_python", True)
        except Exception:
            pass
        try:
            self.parent.venv_path_manuel = None
        except Exception:
            pass
        self._update_venv_label(self._pref_label_system())
        self._ui_log(
            "success", "✅ Utilisation de Python système pour la compilation."
        )
        try:
            workspace_dir = getattr(self.parent, "workspace_dir", None)
            self.save_workspace_pref(workspace_dir)
        except Exception:
            pass

    def get_active_task_labels(self, lang: str) -> list[str]:
        """Return active venv task labels in requested language ('English' or 'French')."""
        labels_fr = {
            "create": "création du venv",
            "reqs": "installation des dépendances",
            "check": "vérification/installation du venv",
        }
        labels_en = {
            "create": "venv creation",
            "reqs": "dependencies installation",
            "check": "venv check/installation",
        }
        L = labels_en if lang == "English" else labels_fr
        out = []

        if self._is_progress_visible("venv_creation"):
            out.append(L["create"])
        if self._is_progress_visible("reqs_install"):
            out.append(L["reqs"])
        if self._is_progress_visible("tools_check"):
            out.append(L["check"])

        return out

    def _on_venv_created(self, process, code, status, venv_path):
        """Override to handle UI state update after venv creation."""
        # Call base implementation for business logic (logging, requirements)
        super()._on_venv_created(process, code, status, venv_path)

        if code == 0 and not self._is_cancel_requested():
            try:
                if not getattr(self.parent, "use_system_python", False):
                    if not getattr(self.parent, "venv_path_manuel", None):
                        self.parent.venv_path_manuel = venv_path
                        self._update_venv_label(
                            f"Venv sélectionné : {venv_path}"
                        )
                self.save_workspace_pref(os.path.dirname(venv_path))
            except Exception:
                pass
