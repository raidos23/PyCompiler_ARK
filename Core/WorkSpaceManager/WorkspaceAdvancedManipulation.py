# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

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
