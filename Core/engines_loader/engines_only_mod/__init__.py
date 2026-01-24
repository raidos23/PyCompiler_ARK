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
Engines Standalone Module

Application autonome permettant d'exécuter les moteurs de compilation
individuellement sans lancer l'application complète PyCompiler ARK.

Ce module réutilise les fonctions de Core/engines_loader pour:
- Découverte et enregistrement des moteurs
- Compilation avec un moteur spécifique
- Affichage des résultats et logs

Usage:
    python -m Core.engines_loader.engines_only_mod [options]

    Ou programmatiquement:
    from bcasl.only_mod.engines_only_mod import EnginesStandaloneApp
    app = EnginesStandaloneApp()
"""

from __future__ import annotations

from .app import EnginesStandaloneApp, main

__version__ = "1.0.0"
__all__ = ["EnginesStandaloneApp", "main"]

