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

from PySide6.QtWidgets import QFileDialog, QMessageBox

from Core.Venv_Manager.Manager import VenvManager


class VenvManagerUI(VenvManager):
    """
    Extension GUI de VenvManager.

    Responsibilities:
    - Manuel venv selection dialog (QFileDialog)
    - Invalid-venv confirmation dialog (QMessageBox)
    - Updating parent widget labels (venv_label, venv_path_edit)
    - Registering all UI callbacks into VenvManager's _ui_callbacks dict

    All business logic (process management, validation, pip install) stays
    in the parent VenvManager class.
    """

    def __init__(self, parent_widget):
        super().__init__(parent_widget)
        # Register UI callbacks so Core methods can trigger GUI updates
        self._ui_callbacks.update(
            {
                "update_venv_label": self._update_venv_label,
                "update_venv_path_edit": self._update_venv_path_edit,
                "ask_recreate_invalid_venv": self._ask_recreate_invalid_venv,
                "show_error_dialog": self._show_error_dialog,
            }
        )

    # ------------------------------------------------------------------
    # UI callback implementations
    # ------------------------------------------------------------------

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
