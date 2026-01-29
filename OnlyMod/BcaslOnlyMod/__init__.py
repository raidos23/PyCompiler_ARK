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
BCASL Standalone Module (only_mod)

Permet d'utiliser BCASL de manière indépendante sans lancer l'application complète.
Réutilise les fonctions du package bcasl et fournit une interface GUI simple.

Features:
    - Standalone GUI application for BCASL management
    - Plugin configuration and ordering
    - Workspace selection and configuration
    - Execution logging and reporting
    - Asynchronous and synchronous execution modes

Usage:
    python -m bcasl.only_mod [workspace_path]

    Or programmatically:
    from OnlyMod.BcaslOnlyMod import BcaslStandaloneApp
    app = BcaslStandaloneApp(workspace_dir="/path/to/workspace")
"""

from __future__ import annotations

from .app import BcaslStandaloneApp, main

__version__ = "1.1.0"
__all__ = ["BcaslStandaloneApp", "main"]
