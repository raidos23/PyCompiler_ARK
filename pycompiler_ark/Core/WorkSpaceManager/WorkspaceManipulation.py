# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague

"""
WorkspaceAdvancedManipulation — logique pure de statut du workspace.

Les interactions Qt (drag & drop, dialogs, widgets) ont été déplacées dans
`Ui/Gui/WorkspaceAdvancedManipulation.py`.

Ce module conserve uniquement la fonction pure `get_workspace_status()`.
"""

import os


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
    from pycompiler_ark.Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace

    all_files = []
    for path in paths:
        if not path:
            continue
        if os.path.isdir(path):
            all_files.extend(SetupWorkspace.list_python_files(path))
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
    from pycompiler_ark.Core.Configs import load_ark_config, should_exclude_file

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
