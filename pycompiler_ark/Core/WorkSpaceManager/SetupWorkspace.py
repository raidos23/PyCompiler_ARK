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

"""SetupWorkspace — pure workspace management and initialization logic.

This module contains NO Qt dependencies. User interactions
are managed by Ui.Gui.Dialogs.WorkspaceDialog."""

import os
from typing import List


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
