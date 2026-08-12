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

"""WorkspaceAdvancedManipulation"""

import os
from typing import List
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QFileDialog, QMessageBox

from pycompiler_ark.Ui import output


@staticmethod
def list_python_files(folder: str) -> List[str]:
    """Recursively retrieves all Python files in a folder.

    Args:
        folder: Folder to scan.

    Returns:
    List of absolute paths to .py files."""
    py_files = []
    if not folder or not os.path.isdir(folder):
        return py_files

    for root, _, files in os.walk(folder):
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))

    return sorted(py_files)


@staticmethod
def create_workspace_dir(folder: str) -> bool:
    """Creates the workspace folder if it does not exist.

    Returns:
      True if the folder exists or has been created, False otherwise."""
    try:
        if not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        return True
    except Exception:
        return False


def get_workspace_status(gui_instance) -> dict:
    """
    Return dictionary describing current workspace status.

    Args:
      gui_instance: GUI instance (or any object with workspace_dir, python_files,
                    selected_files attributes).

    Returns:
      Workspace status information dict.
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


def clear_workspace_data(gui_instance, keep_dir: bool = True) -> None:
    """
    Pure business logic for clearing workspace state in the GUI instance.
    """
    if hasattr(gui_instance, "python_files"):
        gui_instance.python_files.clear()
    if hasattr(gui_instance, "selected_files"):
        gui_instance.selected_files.clear()

    if not keep_dir:
        setattr(gui_instance, "workspace_dir", None)


def add_files(gui_instance, files: list[str]) -> tuple[int, int]:
    """
    Filter and add files to the workspace.
    Returns (added_count, excluded_count).
    """
    workspace_dir = getattr(gui_instance, "workspace_dir", None)
    python_files = getattr(gui_instance, "python_files", [])

    valid_files, excluded, _ = filter_workspace_files(files, workspace_dir)

    added = 0
    for f in valid_files:
        if f not in python_files:
            python_files.append(f)
            added += 1

    return added, excluded


def remove_files(gui_instance, abs_paths: list[str]) -> None:
    """
    Remove files from the workspace state.
    """
    python_files = getattr(gui_instance, "python_files", [])
    selected_files = getattr(gui_instance, "selected_files", [])

    for path in abs_paths:
        if path in python_files:
            python_files.remove(path)
        if path in selected_files:
            selected_files.remove(path)


def resolve_dropped_files(paths: list[str]) -> list[str]:
    """
    Business logic to resolve a list of file/directory paths into a flat list of Python files.
    """

    all_files = []
    for path in paths:
        if not path:
            continue
        if os.path.isdir(path):
            all_files.extend(list_python_files(path))
        elif path.endswith(".py"):
            all_files.append(path)
    return all_files


def filter_workspace_files(
    files: list[str], workspace_dir: str | None
) -> tuple[list[str], int, list[str]]:
    """
    Filter files according to ark.yml exclusion patterns and workspace containment.

    Returns:
      (valid_files, excluded_count, exclusion_patterns)
    """
    from pycompiler_ark.Core.configs import (
        load_ark_config,
        should_exclude_file,
    )

    ark_config = load_ark_config(workspace_dir) if workspace_dir else {}
    workspace_cfg = ark_config.get("workspace", {})
    exclusion_patterns = []
    if isinstance(workspace_cfg, dict):
        exclusion_patterns = workspace_cfg.get("exclude", [])

    valid_files = []
    excluded_count = 0

    for f in files:
        if workspace_dir:
            # Check if within workspace
            try:
                if os.path.commonpath([f, workspace_dir]) != workspace_dir:
                    continue
            except Exception:
                continue

            # Check exclusion patterns
            if should_exclude_file(f, workspace_dir, exclusion_patterns):
                excluded_count += 1
                continue

        valid_files.append(f)

    return valid_files, excluded_count, exclusion_patterns


class SetupWorkspace:
    """Business logic for initializing and scanning the workspace."""

    @staticmethod
    def list_python_files(folder: str) -> List[str]:
        """Recursively retrieves all Python files in a folder.

        Args:
          folder: Folder to scan.

        Returns:
          List of absolute paths to .py files."""
        py_files = []
        if not folder or not os.path.isdir(folder):
            return py_files

        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith(".py"):
                    py_files.append(os.path.join(root, f))

        return sorted(py_files)

    @staticmethod
    def create_workspace_dir(folder: str) -> bool:
        """Creates the workspace folder if it does not exist.

        Returns:
          True if the folder exists or has been created, False otherwise."""
        try:
            if not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            return True
        except Exception:
            return False


class WorkspaceAdvancedManipulation:
    """Qt workspace management (drag & drop, selection, cleaning)"""

    @staticmethod
    def select_files_manually(gui_instance):
        """Open a Python file selection dialog."""
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
            gui_instance.tr(
                "Sélectionner des fichiers Python", "Select Python Files"
            ),
            workspace_dir,
            gui_instance.tr("Fichiers Python (*.py)", "Python Files (*.py)"),
        )
        if files:
            added, excluded = add_files(gui_instance, files)

            # Warning for files outside workspace
            for f in files:
                try:
                    if os.path.commonpath([f, workspace_dir]) != workspace_dir:
                        QMessageBox.warning(
                            gui_instance,
                            gui_instance.tr(
                                "Fichier hors workspace",
                                "File outside workspace",
                            ),
                            gui_instance.tr(
                                f"Le fichier {f} est en dehors du workspace et sera ignoré.",
                                f"The file {f} is outside the workspace and will be ignored.",
                            ),
                        )
                except Exception:
                    pass

            if added > 0:
                output.info(
                    (
                        f"✅ {added} fichier(s) sélectionné(s) manuellement.\n",
                        f"✅ {added} file(s) selected manually.\n",
                    ),
                    gui=gui_instance,
                )
                if excluded > 0:
                    output.info(
                        (
                            f"⏩ Exclusion appliquée : {excluded} fichier(s) ignoré(s) (ark.yml).",
                            f"⏩ Exclusion applied: {excluded} file(s) ignored (ark.yml).",
                        ),
                        gui=gui_instance,
                    )

                # Update UI list widget
                if hasattr(gui_instance, "refresh_file_list"):
                    gui_instance.refresh_file_list()
                elif hasattr(gui_instance, "file_list"):
                    gui_instance.file_list.clear()
                    for f in gui_instance.python_files:
                        rel = (
                            os.path.relpath(f, workspace_dir)
                            if workspace_dir
                            else f
                        )
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
        """Delete selected files from UI list and internal state."""
        if not hasattr(gui_instance, "file_list"):
            return

        selected_items = gui_instance.file_list.selectedItems()
        if not selected_items:
            return

        workspace_dir = getattr(gui_instance, "workspace_dir", None)
        abs_paths_to_remove = []

        for item in selected_items:
            rel_path = item.text()
            abs_path = (
                os.path.join(workspace_dir, rel_path)
                if workspace_dir
                else rel_path
            )
            abs_paths_to_remove.append(abs_path)
            gui_instance.file_list.takeItem(gui_instance.file_list.row(item))

        remove_files(gui_instance, abs_paths_to_remove)

        if hasattr(gui_instance, "update_command_preview"):
            gui_instance.update_command_preview()

    @staticmethod
    def handle_drag_enter_event(gui_instance, event: QDropEvent):
        """Accept or reject the dragEnter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    @staticmethod
    def handle_drop_event(gui_instance, event: QDropEvent):
        """Process the drop event and add the dropped Python files/folders."""

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
                    rel = (
                        os.path.relpath(f, workspace_dir)
                        if workspace_dir
                        else f
                    )
                    gui_instance.file_list.addItem(rel)

        # Log ignored files outside workspace
        for f in all_dropped_files:
            try:
                if (
                    workspace_dir
                    and os.path.commonpath([f, workspace_dir]) != workspace_dir
                ):
                    output.warn(
                        (
                            f"⚠️ Ignoré (hors workspace): {f}",
                            f"⚠️ Ignored (outside workspace): {f}",
                        ),
                        gui=gui_instance,
                    )
            except Exception:
                pass

        output.info(
            (
                f"✅ {added} fichier(s) ajouté(s) via drag & drop.",
                f"✅ {added} file(s) added via drag & drop.",
            ),
            gui=gui_instance,
        )
        if excluded > 0:
            output.info(
                (
                    f"⏩ Exclusion appliquée : {excluded} fichier(s) ignoré(s) (ark.yml).",
                    f"⏩ Exclusion applied: {excluded} file(s) ignored (ark.yml).",
                ),
                gui=gui_instance,
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
        """Empty the current state of the workspace."""
        try:
            workspace_dir = getattr(gui_instance, "workspace_dir", None)

            # Business logic to clear internal state
            clear_workspace_data(gui_instance, keep_dir=keep_dir)

            # UI logic to clear widgets
            if hasattr(gui_instance, "file_list"):
                gui_instance.file_list.clear()

            if hasattr(gui_instance, "label_folder") and not keep_dir:
                gui_instance.label_folder.setText(
                    gui_instance.tr(
                        "Dossier sélectionné : (aucun)",
                        "Selected folder: (none)",
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
                            gui_instance.label_workspace_status.setText(
                                str(val)
                            )
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
                                gui_instance.tr(
                                    "Workspace : Aucun", "Workspace: None"
                                )
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
            output.error(
                (
                    f"❌ Erreur lors de l'effacement du workspace: {e}",
                    f"❌ Error clearing workspace: {e}",
                ),
                gui=gui_instance,
            )
            return False
