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
Python dependency analysis for PyCompiler ARK.
Inclut la détection, la sugmanagement et l'installation automatique des modules manquants.

Optimisations appliquées:
- Caching des résultats stdlib via @lru_cache
- Parallélisation des vérifications pip via ThreadPoolExecutor
- Utilisation de importlib.metadata au lieu de subprocess pip show
- Async I/O pour les opérations bloquantes

Statut: module utilisable pour une sugmanagement/installation basique. Les
fonctions d'auto-analysis avancée mentionnées dans la feuille de route ne sont
pas nécessaires à l'exécution et sont désactivées/neutralisées pour éviter tout
impact en production. La logique UI (suggest_missing_dependencies) a été déplacée
vers la couche UI.
"""

from __future__ import annotations

from .analyser import (
    _check_module_installed,
    _is_stdlib_module,
    collect_internal_modules,
    collect_project_dependencies,
    write_requirements_txt,
)

__all__ = [
    "_check_module_installed",
    "_is_stdlib_module",
    "collect_internal_modules",
    "collect_project_dependencies",
    "write_requirements_txt",
]
