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

import os

from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox

from Core.Globals import _workspace_dir_cache, _workspace_dir_lock


class WorkspaceAdvancedManipulation:
    """Gestion avancée de la manipulation du workspace (drag & drop, sélection fichiers, etc.)."""

    @staticmethod
    def select_files_manually(gui_instance):
        """
        Ouvre une boîte de dialogue pour sélectionner manuellement des fichiers Python.

        Args:
            gui_instance: Instance de l'interface GUI
        """
        workspace_dir = getattr(gui_instance, "workspace_dir", None)

        if not workspace_dir:
            QMessageBox.warning(
                gui_instance,
                gui_instance.tr("Attention", "Warning"),
                gui_instance.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return

        files, _ = QFileDialog.getOpenFileNames(
            gui_instance,
            gui_instance.tr("Sélectionner des fichiers Python", "Select Python Files"),
            workspace_dir,
            gui_instance.tr("Fichiers Python (*.py)", "Python Files (*.py)"),
        )
        if files:
            valid_files = []
            for f in files:
                if os.path.commonpath([f, workspace_dir]) == workspace_dir:
                    valid_files.append(f)
                else:
                    QMessageBox.warning(
                        gui_instance,
                        gui_instance.tr(
                            "Fichier hors workspace", "File outside workspace"
                        ),
                        gui_instance.tr(
                            f"Le fichier {f} est en dehors du workspace et sera ignoré.",
                            f"The file {f} is outside the workspace and will be ignored.",
                        ),
                    )
            if valid_files:
                gui_instance.selected_files = valid_files
                gui_instance.log_i18n(
                    f"✅ {len(valid_files)} fichier(s) sélectionné(s) manuellement.\n",
                    f"✅ {len(valid_files)} file(s) selected manually.\n",
                )
                if hasattr(gui_instance, "update_command_preview"):
                    gui_instance.update_command_preview()

    @staticmethod
    def remove_selected_file(gui_instance):
        """
        Supprime les fichiers sélectionnés de la liste.

        Args:
            gui_instance: Instance de l'interface GUI
        """
        if not hasattr(gui_instance, "file_list"):
            return

        selected_items = gui_instance.file_list.selectedItems()
        for item in selected_items:
            # Récupère le chemin relatif affiché
            rel_path = item.text()
            # Construit le chemin absolu si workspace_dir défini
            workspace_dir = getattr(gui_instance, "workspace_dir", None)
            abs_path = (
                os.path.join(workspace_dir, rel_path) if workspace_dir else rel_path
            )
            # Supprime de python_files si présent
            if abs_path in gui_instance.python_files:
                gui_instance.python_files.remove(abs_path)
            # Supprime de selected_files si présent
            if abs_path in gui_instance.selected_files:
                gui_instance.selected_files.remove(abs_path)
            # Supprime l'item de la liste graphique
            gui_instance.file_list.takeItem(gui_instance.file_list.row(item))

        if hasattr(gui_instance, "update_command_preview"):
            gui_instance.update_command_preview()

    @staticmethod
    def handle_drag_enter_event(gui_instance, event: QDropEvent):
        """
        Gère l'événement dragEnter pour accepter les fichiers droppés.

        Args:
            gui_instance: Instance de l'interface GUI
            event: L'événement de drag
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    @staticmethod
    def handle_drop_event(gui_instance, event: QDropEvent):
        """
        Gère l'événement drop pour ajouter les fichiers droppés.

        Args:
            gui_instance: Instance de l'interface GUI
            event: L'événement de drop

        Returns:
            Nombre de fichiers ajoutés
        """
        from Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace

        urls = event.mimeData().urls()
        added = 0

        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                added += SetupWorkspace.add_py_files_from_folder(gui_instance, path)
            elif path.endswith(".py"):
                # Vérifie que le fichier est dans workspace (si défini)
                workspace_dir = getattr(gui_instance, "workspace_dir", None)
                if (
                    workspace_dir
                    and not os.path.commonpath([path, workspace_dir]) == workspace_dir
                ):
                    gui_instance.log_i18n(
                        f"⚠️ Ignoré (hors workspace): {path}",
                        f"⚠️ Ignored (outside workspace): {path}",
                    )
                    continue
                if path not in gui_instance.python_files:
                    gui_instance.python_files.append(path)
                    relative_path = (
                        os.path.relpath(path, workspace_dir) if workspace_dir else path
                    )
                    if hasattr(gui_instance, "file_list"):
                        gui_instance.file_list.addItem(relative_path)
                    added += 1

        gui_instance.log_i18n(
            f"✅ {added} fichier(s) ajouté(s) via drag & drop.",
            f"✅ {added} file(s) added via drag & drop.",
        )

        if hasattr(gui_instance, "update_command_preview"):
            gui_instance.update_command_preview()

        return added

    @staticmethod
    def get_workspace_status(gui_instance) -> dict:
        """
        Retourne un dictionnaire avec le statut actuel du workspace.

        Args:
            gui_instance: Instance de l'interface GUI

        Returns:
            Dictionnaire avec les informations du workspace
        """
        workspace_dir = getattr(gui_instance, "workspace_dir", None)
        python_files = getattr(gui_instance, "python_files", [])
        selected_files = getattr(gui_instance, "selected_files", [])

        return {
            "workspace_dir": workspace_dir,
            "file_count": len(python_files),
            "selected_count": len(selected_files),
            "is_valid": bool(workspace_dir and os.path.isdir(workspace_dir)),
            "has_files": len(python_files) > 0,
        }

    @staticmethod
    def clear_workspace(gui_instance, keep_dir: bool = True) -> bool:
        """
        Efface le workspace actuel.

        Args:
            gui_instance: Instance de l'interface GUI
            keep_dir: Si True, garde le dossier mais efface les fichiers

        Returns:
            True si succès
        """
        try:
            workspace_dir = getattr(gui_instance, "workspace_dir", None)

            # Effacer les listes
            gui_instance.python_files.clear()
            gui_instance.selected_files.clear()

            if hasattr(gui_instance, "file_list"):
                gui_instance.file_list.clear()

            # Mettre à jour l'interface
            if hasattr(gui_instance, "label_folder") and not keep_dir:
                gui_instance.label_folder.setText(
                    gui_instance.tr(
                        "Dossier sélectionné : (aucun)", "Selected folder: (none)"
                    )
                )

            gui_instance.workspace_dir = None if not keep_dir else workspace_dir

            # Vider le cache global
            try:
                global _workspace_dir_cache
                with _workspace_dir_lock:
                    _workspace_dir_cache = None
            except Exception:
                pass

            if hasattr(gui_instance, "update_command_preview"):
                gui_instance.update_command_preview()

            try:
                gui_instance.save_preferences()
            except Exception:
                pass

            return True

        except Exception as e:
            gui_instance.log_i18n(
                f"❌ Erreur lors de l'effacement du workspace: {e}",
                f"❌ Error clearing workspace: {e}",
            )
            return False
