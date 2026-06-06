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
SetupWorkspace — logique pure de gestion et d'initialisation du workspace.

Ce module ne contient AUCUNE dépendance Qt. Les interactions utilisateur
sont gérées par Ui.Gui.Dialogs.WorkspaceDialog.
"""

import os
from typing import List


class SetupWorkspace:
    """Logique métier pour l'initialisation et le scan du workspace."""

    @staticmethod
    def list_python_files(folder: str) -> List[str]:
        """
        Récupère récursivement tous les fichiers Python d'un dossier.

        Args:
          folder: Dossier à scanner.

        Returns:
          Liste des chemins absolus vers les fichiers .py.
        """
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
        """
        Crée le dossier du workspace s'il n'existe pas.

        Returns:
          True si le dossier existe ou a été créé, False sinon.
        """
        try:
            if not os.path.isdir(folder):
                os.makedirs(folder, exist_ok=True)
            return True
        except Exception:
            return False
