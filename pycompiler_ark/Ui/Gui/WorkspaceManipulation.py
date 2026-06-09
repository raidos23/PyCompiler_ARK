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
WorkspaceAdvancedManipulation — interactions Qt avancées avec le workspace.

Ce module gère les événements Qt (drag & drop, sélection de fichiers, nettoyage)
et délègue toute la logique fichier pure à Core.WorkSpaceManager.
"""

import os

from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox


class WorkspaceAdvancedManipulation:
    """Gestion Qt avancée du workspace (drag & drop, sélection, nettoyage)."""

    @staticmethod
    def select_files_manually(gui_instance):
        """Ouvrir un dialog de sélection de fichiers Python."""
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
            from pycompiler_ark.Core.WorkSpaceManager.WorkspaceManipulation import (
                add_files,
            )

            added, excluded = add_files(gui_instance, files)

            # Warning for files outside workspace
            for f in files:
                try:
                    if os.path.commonpath([f, workspace_dir]) != workspace_dir:
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
                except Exception:
                    pass

            if added > 0:
                gui_instance.log_i18n(
                    f"✅ {added} fichier(s) sélectionné(s) manuellement.\n",
                    f"✅ {added} file(s) selected manually.\n",
                )
                if excluded > 0:
                    gui_instance.log_i18n(
                        f"⏩ Exclusion appliquée : {excluded} fichier(s) ignoré(s) (ark.yml).",
                        f"⏩ Exclusion applied: {excluded} file(s) ignored (ark.yml).",
                    )

                # Update UI list widget
                if hasattr(gui_instance, "refresh_file_list"):
                    gui_instance.refresh_file_list()
                elif hasattr(gui_instance, "file_list"):
                    gui_instance.file_list.clear()
                    for f in gui_instance.python_files:
                        rel = os.path.relpath(f, workspace_dir) if workspace_dir else f
                        gui_instance.file_list.addItem(rel)

                if hasattr(gui_instance, "update_command_preview"):
                    gui_instance.update_command_preview()
                try:
                    if hasattr(gui_instance, "apply_file_filter"):
                        gui_instance.apply_file_filter()
                except Exception:
                    pass

    @staticmethod
    def remove_selected_file(gui_instance):
        """Supprimer les fichiers sélectionnés de la liste UI et de l'état interne."""
        if not hasattr(gui_instance, "file_list"):
            return

        selected_items = gui_instance.file_list.selectedItems()
        if not selected_items:
            return

        from pycompiler_ark.Core.WorkSpaceManager.WorkspaceManipulation import (
            remove_files,
        )

        workspace_dir = getattr(gui_instance, "workspace_dir", None)
        abs_paths_to_remove = []

        for item in selected_items:
            rel_path = item.text()
            abs_path = (
                os.path.join(workspace_dir, rel_path) if workspace_dir else rel_path
            )
            abs_paths_to_remove.append(abs_path)
            gui_instance.file_list.takeItem(gui_instance.file_list.row(item))

        remove_files(gui_instance, abs_paths_to_remove)

        if hasattr(gui_instance, "update_command_preview"):
            gui_instance.update_command_preview()

    @staticmethod
    def handle_drag_enter_event(gui_instance, event: QDropEvent):
        """Accepter ou refuser l'événement dragEnter."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    @staticmethod
    def handle_drop_event(gui_instance, event: QDropEvent):
        """Traiter l'événement drop et ajouter les fichiers/dossiers Python déposés."""
        from pycompiler_ark.Core.WorkSpaceManager.WorkspaceManipulation import (
            add_files,
            resolve_dropped_files,
        )

        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        workspace_dir = getattr(gui_instance, "workspace_dir", None)

        all_dropped_files = resolve_dropped_files(paths)

        added, excluded = add_files(gui_instance, all_dropped_files)

        # Update UI list widget
        if added > 0:
            if hasattr(gui_instance, "refresh_file_list"):
                gui_instance.refresh_file_list()
            elif hasattr(gui_instance, "file_list"):
                gui_instance.file_list.clear()
                for f in gui_instance.python_files:
                    rel = os.path.relpath(f, workspace_dir) if workspace_dir else f
                    gui_instance.file_list.addItem(rel)

        # Log ignored files outside workspace
        for f in all_dropped_files:
            try:
                if (
                    workspace_dir
                    and os.path.commonpath([f, workspace_dir]) != workspace_dir
                ):
                    gui_instance.log_i18n(
                        f"⚠️ Ignoré (hors workspace): {f}",
                        f"⚠️ Ignored (outside workspace): {f}",
                    )
            except Exception:
                pass

        gui_instance.log_i18n(
            f"✅ {added} fichier(s) ajouté(s) via drag & drop.",
            f"✅ {added} file(s) added via drag & drop.",
        )
        if excluded > 0:
            gui_instance.log_i18n(
                f"⏩ Exclusion appliquée : {excluded} fichier(s) ignoré(s) (ark.yml).",
                f"⏩ Exclusion applied: {excluded} file(s) ignored (ark.yml).",
            )
        try:
            if hasattr(gui_instance, "apply_file_filter"):
                gui_instance.apply_file_filter()
        except Exception:
            pass

        if hasattr(gui_instance, "update_command_preview"):
            gui_instance.update_command_preview()

        return added

    @staticmethod
    def clear_workspace(gui_instance, keep_dir: bool = True) -> bool:
        """Vider l'état courant du workspace."""
        try:
            from pycompiler_ark.Core.WorkSpaceManager.WorkspaceManipulation import (
                clear_workspace_data,
            )

            workspace_dir = getattr(gui_instance, "workspace_dir", None)

            # Business logic to clear internal state
            clear_workspace_data(gui_instance, keep_dir=keep_dir)

            # UI logic to clear widgets
            if hasattr(gui_instance, "file_list"):
                gui_instance.file_list.clear()

            if hasattr(gui_instance, "label_folder") and not keep_dir:
                gui_instance.label_folder.setText(
                    gui_instance.tr(
                        "Dossier sélectionné : (aucun)", "Selected folder: (none)"
                    )
                )
            if hasattr(gui_instance, "label_workspace_status"):
                try:
                    tr_map = getattr(gui_instance, "_tr", None)
                    if isinstance(tr_map, dict):
                        if keep_dir and workspace_dir:
                            tmpl = (
                                tr_map.get("label_workspace_status")
                                or "Workspace: {path}"
                            )
                            gui_instance.label_workspace_status.setText(
                                str(tmpl).replace("{path}", str(workspace_dir))
                            )
                        else:
                            val = (
                                tr_map.get("label_workspace_status_none")
                                or "Workspace: None"
                            )
                            gui_instance.label_workspace_status.setText(str(val))
                    else:
                        if keep_dir and workspace_dir:
                            gui_instance.label_workspace_status.setText(
                                gui_instance.tr(
                                    f"Workspace : {workspace_dir}",
                                    f"Workspace: {workspace_dir}",
                                )
                            )
                        else:
                            gui_instance.label_workspace_status.setText(
                                gui_instance.tr("Workspace : Aucun", "Workspace: None")
                            )
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
