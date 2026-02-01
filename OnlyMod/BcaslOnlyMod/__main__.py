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
BcaslOnlyMod - Point d'entrée principal

Module autonome permettant d'exécuter et configurer les plugins BCASL
indépendamment de l'application principale PyCompiler ARK.

Utilisation:
    python -m OnlyMod.BcaslOnlyMod [options]

Options:
    -w, --workspace DIR    Répertoire du workspace
    -l, --language LANG    Langue de l'interface (en/fr)
    -t, --theme THEME      Thème visuel (light/dark)
    -g, --gui              Lancer l'interface graphique
    --list-plugins         Lister les plugins disponibles
    -r, --run              Exécuter les plugins (mode CLI)
    --timeout SECONDS      Timeout d'exécution des plugins

Exemples:
    # Lancer l'interface graphique
    python -m OnlyMod.BcaslOnlyMod --gui
    
    # Lancer avec workspace spécifique
    python -m OnlyMod.BcaslOnlyMod --gui --workspace /path/to/workspace
    
    # Lister les plugins (mode CLI)
    python -m OnlyMod.BcaslOnlyMod --list-plugins
    
    # Exécuter les plugins (mode CLI)
    python -m OnlyMod.BcaslOnlyMod --run --workspace /path/to/workspace
"""

from __future__ import annotations

import sys


def main():
    """Point d'entrée principal du module."""
    from .app import main as app_main

    sys.exit(app_main())


if __name__ == "__main__":
    main()

