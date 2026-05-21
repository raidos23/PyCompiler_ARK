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
VenvManagerUI — couche GUI du gestionnaire de venv.

Cette classe étend VenvManager (Core) avec la logique d'interface
utilisateur (dialogues, sélection de dossier, mise à jour des labels).

La logique métier (détection, validation, processus pip) reste dans Core.
"""

import os

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from Core.Venv_Manager.Manager import VenvManager
from Ui.Gui.WidgetsCreator import ProgressDialog


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
                "log_i18n": self._ui_log_i18n,
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
            from Ui.i18n import log_with_level

            log_with_level(self.parent, level, text)
        except Exception:
            pass

    def _ui_log_i18n(self, level: str, text_fr: str, text_en: str) -> None:
        """Log an internationalized message via the UI logging system."""
        try:
            from Ui.i18n import log_i18n_level

            log_i18n_level(self.parent, level, text_fr, text_en)
        except Exception:
            pass

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
            if hasattr(self.parent, "venv_path_edit") and self.parent.venv_path_edit:
                self.parent.venv_path_edit.setText(text)
        except Exception:
            pass

    def _ask_recreate_invalid_venv(self, venv_root: str, reason: str) -> bool:
        """Show a QMessageBox asking the user to confirm venv deletion/recreation.
        Returns True if the user accepted, False otherwise.
        """
        try:
            title = "Environnement virtuel invalide / Invalid virtual environment"
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

    def _update_progress_progress(self, id: str, value: int, total: int) -> None:
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
                        self._safe_log(
                            "ℹ️ Python système incomplet: "
                            + ", ".join(sorted(set(missing)))
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
                self._safe_log(f"✅ Venv valide sélectionné: {path}")
                try:
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    self.save_workspace_pref(workspace_dir)
                except Exception:
                    pass
            else:
                self._safe_log(f"❌ Venv refusé: {reason}")
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
                            _t("Créer un venv", "Create venv"), QMessageBox.ActionRole
                        )
                    box.addButton(_t("Annuler", "Cancel"), QMessageBox.RejectRole)
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
    # Workspace preference management (Moved from VenvManager)
    # ------------------------------------------------------------------

    def _workspace_pref_path(self, workspace_dir: str) -> str:
        """Return the resolved workspace path information."""
        return os.path.join(os.path.abspath(workspace_dir), ".ark", "pref.json")

    def _read_workspace_pref(self, workspace_dir: str) -> dict | None:
        """Execute _read_workspace_pref logic for this component."""
        try:
            path = self._workspace_pref_path(workspace_dir)
            if not os.path.isfile(path):
                return None
            with open(path, encoding="utf-8") as f:
                import json

                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _write_workspace_pref(self, workspace_dir: str, data: dict) -> None:
        """Execute _write_workspace_pref logic for this component."""
        try:
            path = self._workspace_pref_path(workspace_dir)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            import json

            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    def _clear_workspace_pref(self, workspace_dir: str) -> None:
        """Clear the related cached state or UI values."""
        try:
            path = self._workspace_pref_path(workspace_dir)
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass

    def _pref_label_system(self) -> str:
        """Execute _pref_label_system logic for this component."""
        return self.tr(
            "Venv sélectionné : Python système",
            "Venv selected: System Python",
        )

    def _pref_label_none(self) -> str:
        """Execute _pref_label_none logic for this component."""
        return self.tr("Venv sélectionné : Aucun", "Venv selected: None")

    def apply_workspace_pref(self, workspace_dir: str) -> bool:
        """Apply saved venv/system selection from .ark/pref.json if available."""
        try:
            data = self._read_workspace_pref(workspace_dir)
            if not data:
                return False
            mode = str(data.get("venv_mode", "")).strip().lower()
            venv_path = data.get("venv_path")
            if mode == "system":
                try:
                    setattr(self.parent, "use_system_python", True)
                except Exception:
                    pass
                try:
                    self.parent.venv_path_manuel = None
                except Exception:
                    pass
                try:
                    if hasattr(self.parent, "venv_path"):
                        setattr(self.parent, "venv_path", None)
                except Exception:
                    pass
                self._update_venv_label(self._pref_label_system())
                self._update_venv_path_edit(self._pref_label_system())
                return True
            if mode == "venv" and isinstance(venv_path, str) and venv_path:
                venv_path = os.path.abspath(venv_path)
                ok, _ = self.validate_venv_strict(venv_path)
                if ok:
                    try:
                        setattr(self.parent, "use_system_python", False)
                    except Exception:
                        pass
                    try:
                        self.parent.venv_path_manuel = venv_path
                    except Exception:
                        pass
                    try:
                        if hasattr(self.parent, "venv_path"):
                            setattr(self.parent, "venv_path", venv_path)
                    except Exception:
                        pass
                    self._update_venv_label(f"Venv sélectionné : {venv_path}")
                    self._update_venv_path_edit(venv_path)
                    return True
                self._clear_workspace_pref(workspace_dir)
            return False
        except Exception:
            return False

    def save_workspace_pref(self, workspace_dir: str | None) -> None:
        """Persist current venv/system selection for a workspace."""
        if not workspace_dir:
            return
        try:
            if getattr(self.parent, "use_system_python", False):
                self._write_workspace_pref(
                    workspace_dir,
                    {"venv_mode": "system", "venv_path": None},
                )
                return
            venv_path = getattr(self.parent, "venv_path_manuel", None)
            if not venv_path:
                venv_path = getattr(self.parent, "venv_path", None)
            if venv_path:
                self._write_workspace_pref(
                    workspace_dir,
                    {"venv_mode": "venv", "venv_path": os.path.abspath(venv_path)},
                )
                return
        except Exception:
            pass
        self._clear_workspace_pref(workspace_dir)

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
        self._ui_log("success", "✅ Utilisation de Python système pour la compilation.")
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
                        self._update_venv_label(f"Venv sélectionné : {venv_path}")
                self.save_workspace_pref(os.path.dirname(venv_path))
            except Exception:
                pass

