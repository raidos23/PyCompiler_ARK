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
Engines Standalone Module Entry Point

Permet d'exécuter l'application moteurs de compilation de manière autonome:
    python -m Core.engines_loader.engines_only_mod [options]

Sans arguments, lance l'interface GUI complète.
Avec --list-engines ou --check-compat, lance en mode CLI.

Exemples:
    # Lancer l'interface GUI
    python -m Core.engines_loader.engines_only_mod

    # Lister les moteurs disponibles (CLI mode)
    python -m Core.engines_loader.engines_only_mod --list-engines

    # Vérifier la compatibilité d'un moteur
    python -m Core.engines_loader.engines_only_mod --check-compat nuitka

    # Compiler un fichier (mode dry-run)
    python -m Core.engines_loader.engines_only_mod --engine nuitka -f script.py --dry-run
"""

import argparse
import sys

from .gui import launch_engines_gui


def run_cli(args):
    """Exécute en mode CLI."""
    from .app import EnginesStandaloneApp
    
    app = EnginesStandaloneApp(
        engine_id=args.engine,
        file_path=args.file,
        workspace_dir=args.workspace,
        language=args.language,
        theme=args.theme,
        dry_run=args.dry_run,
        headless=True,
    )
    
    if args.list_engines:
        engines = app.load_engines()
        print(f"\nAvailable engines ({len(engines)}):\n")
        for eng in engines:
            compat = app.check_engine_compatibility(eng["id"])
            status = "OK" if compat["compatible"] else "FAIL"
            print(f"  [{status}] {eng['name']}")
            print(f"       ID: {eng['id']}")
            print(f"       Version: {eng['version']}")
            print(f"       Required Core: {eng['required_core']}")
            print()
        return 0
    
    if args.check_compat:
        result = app.check_engine_compatibility(args.check_compat)
        print(f"\nCompatibility check for: {args.check_compat}")
        if result["compatible"]:
            print("  OK - Engine is compatible")
        else:
            print("  FAIL - Engine has compatibility issues:")
            if result.get("missing_requirements"):
                for req in result["missing_requirements"]:
                    print(f"     - {req}")
            if result.get("message"):
                print(f"     Message: {result['message']}")
        return 0
    
    if args.dry_run:
        if args.engine and args.file:
            result = app.run_compilation(args.engine, args.file, dry_run=True)
            print(f"\n[DRY RUN] Command: {result.get('command', '')}")
            return 0
        else:
            print("Error: --dry-run requires --engine and --file")
            return 1
    
    return 0


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Engines Standalone - Execute compilation engines independently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
    # Lancer l'interface GUI
    python -m Core.engines_loader.engines_only_mod
    
    # Lister les moteurs disponibles
    python -m Core.engines_loader.engines_only_mod --list-engines
    
    # Vérifier la compatibilité d'un moteur
    python -m Core.engines_loader.engines_only_mod --check-compat nuitka
    
    # Compiler un fichier (dry-run)
    python -m Core.engines_loader.engines_only_mod --engine nuitka -f script.py --dry-run
        """,
    )
    
    # Options GUI
    parser.add_argument(
        "-w",
        "--workspace",
        help="Project workspace directory",
    )
    parser.add_argument(
        "-l",
        "--language",
        choices=["en", "fr"],
        default="en",
        help="Interface language (default: en)",
    )
    parser.add_argument(
        "-t",
        "--theme",
        choices=["light", "dark"],
        default="dark",
        help="UI theme (default: dark)",
    )
    
    # Options CLI
    parser.add_argument(
        "-e",
        "--engine",
        help="Engine ID to use for compilation (CLI mode)",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="File to compile (CLI mode)",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show command without executing (CLI mode)",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List available engines (CLI mode)",
    )
    parser.add_argument(
        "--check-compat",
        metavar="ENGINE_ID",
        help="Check engine compatibility (CLI mode)",
    )
    
    args = parser.parse_args()
    
    # Déterminer le mode d'exécution
    cli_mode = args.list_engines or args.check_compat or args.dry_run or args.engine or args.file
    
    if cli_mode:
        # Mode CLI
        return run_cli(args)
    else:
        # Mode GUI
        return launch_engines_gui(
            workspace_dir=args.workspace,
            language=args.language,
            theme=args.theme,
        )


if __name__ == "__main__":
    sys.exit(main())

