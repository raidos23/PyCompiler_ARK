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
Engines Standalone Module — Module de Gestion des Engines de Compilation

Module standalone permettant d'executer les compilation engines PyCompiler ARK
sans lancer l'application maine.

Fonctionnalités:
  - Interface graphique complète pour gérer les compilation engines
  - Mode CLI pour lister les engines et checkr la compatibilité
  - Support de plusieurs engines via le registre EngineLoader
  - Thèmes clair/sombre et languages anglais/français

Utilisation:
  # Interface GUI
  python -m OnlyMod.EngineOnlyMod

  # Mode CLI - lister les engines
  python -m OnlyMod.EngineOnlyMod --list-engines

  # Mode CLI - checkr compatibilité
  python -m OnlyMod.EngineOnlyMod --check-compat <engine_id>

Documentation complète : voir README.md
"""

from __future__ import annotations

# Exports publics - import différé pour éviter les circular imports
from .app import EnginesStandaloneApp  # Classe principale pour usage programmatique
from .gui import EnginesStandaloneGui  # Interface graphique


def launch_engines_gui(
    workspace_dir: str = None,
    language: str = "en",
    theme: str = "dark",
) -> int:
    """Launch the Engines Standalone GUI application.

    Args:
      workspace_dir: Chemin du workspace (optionnel)
      language: Code de language ('en' ou 'fr')
      theme: Nom du theme ('light' ou 'dark')

    Returns:
      Code de retour de l'application
    """
    from .gui import launch_engines_gui as _launch

    return _launch(workspace_dir, language, theme)


def launch_prog_engine_gui(
    engine_id: str,
    workspace_dir: str = None,
    language: str = "en",
    theme: str = "dark",
) -> int:
    """Launch dedicated GUI for one engine with config editor."""
    from .gui import launch_prog_engine_gui as _launch

    return _launch(engine_id, workspace_dir, language, theme)


def main():
    """Main module entry point."""
    from . import __main__ as _main_module

    return _main_module.main()


__version__ = "1.0.0"
__all__ = [
    "EnginesStandaloneApp",
    "EnginesStandaloneGui",
    "launch_engines_gui",
    "launch_prog_engine_gui",
    "main",
]
