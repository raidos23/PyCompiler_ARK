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
Engines Standalone Module — Module de Gestion des Moteurs de Compilation

Module autonome permettant d'exécuter les moteurs de compilation PyCompiler ARK++
sans lancer l'application principale.

Fonctionnalités:
    - Interface graphique complète pour gérer les moteurs de compilation
    - Mode CLI pour lister les moteurs et vérifier la compatibilité
    - Support de plusieurs moteurs : PyInstaller, Nuitka, cx_Freeze
    - Thèmes clair/sombre et langues anglais/français

Utilisation:
    # Interface GUI
    python -m Core.engines_loader.engines_only_mod

    # Mode CLI - lister les moteurs
    python -m Core.engines_loader.engines_only_mod --list-engines

    # Mode CLI - vérifier compatibilité
    python -m Core.engines_loader.engines_only_mod --check-compat nuitka

Documentation complète : voir README.md
"""

from __future__ import annotations

# Exports publics - import différé pour éviter les circular imports
from .app import EnginesStandaloneApp  # Classe principale pour usage programmatique
from .gui import EnginesStandaloneGui  # Interface graphique


def launch_engines_gui(
    workspace_dir: str = None, language: str = "en", theme: str = "dark"
) -> int:
    """Lance l'application Engines Standalone GUI.

    Args:
        workspace_dir: Chemin du workspace (optionnel)
        language: Code de langue ('en' ou 'fr')
        theme: Nom du thème ('light' ou 'dark')

    Returns:
        Code de retour de l'application
    """
    from .gui import launch_engines_gui as _launch

    return _launch(workspace_dir, language, theme)


def main():
    """Point d'entrée principal du module."""
    from . import __main__ as _main_module

    return _main_module.main()


__version__ = "1.0.0"
__all__ = [
    "EnginesStandaloneApp",
    "EnginesStandaloneGui",
    "launch_engines_gui",
    "main",
]
