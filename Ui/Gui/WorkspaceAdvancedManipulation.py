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

from Core.Globals import _workspace_dir_lock
from Core.Configs import load_ark_config, should_exclude_file


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
            ark_config = load_ark_config(workspace_dir) if workspace_dir else {}
            exclusion_patterns = ark_config.get("exclusion_patterns", [])
            valid_files = []
            excluded = 0
            for f in files:
                if os.path.commonpath([f, workspace_dir]) == workspace_dir:
                    if workspace_dir and should_exclude_file(
                        f, workspace_dir, exclusion_patterns
                    ):
                        excluded += 1
                        continue
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
                if excluded > 0:
                    gui_instance.log_i18n(
                        f"⏩ Exclusion appliquée : {excluded} fichier(s) ignoré(s) (ark.yml).",
                        f"⏩ Exclusion applied: {excluded} file(s) ignored (ark.yml).",
                    )
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
        for item in selected_items:
            rel_path = item.text()
            workspace_dir = getattr(gui_instance, "workspace_dir", None)
            abs_path = (
                os.path.join(workspace_dir, rel_path) if workspace_dir else rel_path
            )
            if abs_path in gui_instance.python_files:
                gui_instance.python_files.remove(abs_path)
            if abs_path in gui_instance.selected_files:
                gui_instance.selected_files.remove(abs_path)
            gui_instance.file_list.takeItem(gui_instance.file_list.row(item))

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
        from Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace

        urls = event.mimeData().urls()
        added = 0
        excluded = 0
        workspace_dir = getattr(gui_instance, "workspace_dir", None)
        ark_config = load_ark_config(workspace_dir) if workspace_dir else {}
        exclusion_patterns = ark_config.get("exclusion_patterns", [])

        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                files = SetupWorkspace.list_python_files(path)
                for f in files:
                    if workspace_dir and not os.path.commonpath([f, workspace_dir]) == workspace_dir:
                        continue
                    if should_exclude_file(f, workspace_dir, exclusion_patterns):
                        excluded += 1
                        continue
                    if f not in gui_instance.python_files:
                        gui_instance.python_files.append(f)
                        rel = os.path.relpath(f, workspace_dir) if workspace_dir else f
                        if hasattr(gui_instance, "file_list"):
                            gui_instance.file_list.addItem(rel)
                        added += 1
            elif path.endswith(".py"):
                if (
                    workspace_dir
                    and not os.path.commonpath([path, workspace_dir]) == workspace_dir
                ):
                    gui_instance.log_i18n(
                        f"⚠️ Ignoré (hors workspace): {path}",
                        f"⚠️ Ignored (outside workspace): {path}",
                    )
                    continue
                if workspace_dir and should_exclude_file(
                    path, workspace_dir, exclusion_patterns
                ):
                    excluded += 1
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
            workspace_dir = getattr(gui_instance, "workspace_dir", None)

            gui_instance.python_files.clear()
            gui_instance.selected_files.clear()

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

            gui_instance.workspace_dir = None if not keep_dir else workspace_dir

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
