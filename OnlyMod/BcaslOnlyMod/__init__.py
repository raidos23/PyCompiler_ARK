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
BcaslOnlyMod - Module autonome pour gérer les plugins BCASL

Interface complète pour exécuter et configurer les plugins BCASL
indépendamment de l'application principale PyCompiler ARK.

Fournit une interface utilisateur moderne permettant de:
- Découvrir et lister les plugins BCASL disponibles
- Activer/désactiver les plugins
- Réordonner l'exécution des plugins
- Exécuter les plugins de pré-compilation
- Afficher les rapports d'exécution
"""

from __future__ import annotations

from .gui import BcaslStandaloneGui, launch_bcasl_gui
from .app import BcaslOnlyModApp

__version__ = "1.0.0"
__author__ = "Ague Samuel Amen"

__all__ = [
    "BcaslStandaloneGui",
    "BcaslOnlyModApp",
    "launch_bcasl_gui",
]

