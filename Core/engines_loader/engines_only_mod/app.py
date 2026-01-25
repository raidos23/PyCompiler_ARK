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
Engines Standalone GUI Application

Interface complète pour exécuter les moteurs de compilation indépendamment
de l'application principale PyCompiler ARK.

Fournit une interface utilisateur moderne permettant de:
- Sélectionner et configurer un moteur de compilation
- Sélectionner des fichiers sources ou un workspace
- Exécuter la compilation avec le moteur choisi
- Afficher les résultats, logs et rapports de compilation

Ce module réutilise les fonctions de Core.engines_loader pour:
- Découverte et enregistrement des moteurs (registry)
- Vérification de compatibilité (validator)
- Construction et exécution des commandes de compilation
"""

from __future__ import annotations

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Importations des modules engines_loader (réutilisation du code existant)
from Core.engines_loader import (
    CompilerEngine,
    registry,
    unload_all,
    available_engines,
    get_engine,
    create as create_engine,
)
from Core.engines_loader.validator import (
    check_engine_compatibility,
    validate_engines_compatibility,
)
from Core.allversion import get_core_version, get_engine_sdk_version

# Configuration du logging
logger = logging.getLogger(__name__)


class MockGUI:
    """
    Mock GUI object pour fournir une interface compatible avec les moteurs.

    Cette classe simule les propriétés et méthodes du GUI principal
    nécessaires aux moteurs de compilation, permettant leur exécution
    en mode standalone sans l'application complète.
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir
        self.log = MockLog()
        self._tr = {}

    def tr(self, fr_text: str, en_text: str) -> str:
        """Traduit le texte selon la langue préférée (défaut: anglais)."""
        try:
            lang = getattr(self, "language_pref", "en")
            if lang and lang.lower().startswith("fr"):
                return fr_text
            return en_text
        except Exception:
            return en_text


class MockLog:
    """Mock log object qui collecte les messages pour affichage."""

    def __init__(self):
        self.messages: List[str] = []

    def append(self, message: str) -> None:
        """Ajoute un message au log."""
        self.messages.append(message)
        print(message)

    def clear(self) -> None:
        """Efface le log."""
        self.messages.clear()

    def get_value(self) -> str:
        """Retourne le contenu complet du log."""
        return "\n".join(self.messages)


class LanguageManager:
    """Gestionnaire de langues pour l'application."""

    def __init__(self):
        self.strings = self._get_default_strings()
        self.current_language = "en"

    def _get_default_strings(self) -> dict:
        """Retourne les chaînes par défaut en anglais et français."""
        return {
            # Titres et headers
            "app_title": "Engines Standalone - Compilation Engine Manager",
            "app_title_fr": "Engines Standalone - Gestionnaire de Moteurs de Compilation",
            "engine_config": "Engine Configuration",
            "engine_config_fr": "Configuration du Moteur",
            "file_config": "File Configuration",
            "file_config_fr": "Configuration Fichier",
            "execution_config": "Execution Options",
            "execution_config_fr": "Options d'Exécution",
            # Labels
            "engine_label": "Engine:",
            "engine_label_fr": "Moteur :",
            "engine_version": "Version:",
            "engine_version_fr": "Version :",
            "engine_core_required": "Required Core:",
            "engine_core_required_fr": "Core Requis :",
            "file_label": "File/Project:",
            "file_label_fr": "Fichier/Projet :",
            "no_file": "No file selected",
            "no_file_fr": "Aucun fichier sélectionné",
            "browse_button": "Browse...",
            "browse_button_fr": "Parcourir...",
            "workspace_label": "Workspace:",
            "workspace_label_fr": "Workspace :",
            "no_workspace": "No workspace selected",
            "no_workspace_fr": "Aucun workspace sélectionné",
            # Boutons
            "run_compile": "Compile",
            "run_compile_fr": "Compiler",
            "check_compat": "Check Compatibility",
            "check_compat_fr": "Vérifier Compatibilité",
            "clear_log": "Clear Log",
            "clear_log_fr": "Effacer Log",
            "exit_button": "Exit",
            "exit_button_fr": "Quitter",
            "refresh_engines": "Refresh Engines",
            "refresh_engines_fr": "Rafraîchir",
            # Status
            "ready": "Ready",
            "ready_fr": "Prêt",
            "running": "Running compilation...",
            "running_fr": "Compilation en cours...",
            "completed": "Compilation completed",
            "completed_fr": "Compilation terminée",
            "failed": "Compilation failed",
            "failed_fr": "Échec de la compilation",
            "no_engine": "No engine selected",
            "no_engine_fr": "Aucun moteur sélectionné",
            # Messages
            "select_engine": "Please select an engine first",
            "select_engine_fr": "Veuillez sélectionner un moteur d'abord",
            "select_file": "Please select a file or workspace",
            "select_file_fr": "Veuillez sélectionner un fichier ou workspace",
            "engine_not_found": "Engine not found: {engine}",
            "engine_not_found_fr": "Moteur non trouvé : {engine}",
            "compilation_success": "Compilation successful!",
            "compilation_success_fr": "Compilation réussie !",
            "compilation_failed": "Compilation failed: {error}",
            "compilation_failed_fr": "Échec de la compilation : {error}",
            "compatibility_ok": "Engine is compatible",
            "compatibility_ok_fr": "Moteur compatible",
            "compatibility_issue": "Compatibility issues detected",
            "compatibility_issue_fr": "Problèmes de compatibilité détectés",
            "no_engines": "No engines available. Please check ENGINES folder.",
            "no_engines_fr": "Aucun moteur disponible. Vérifiez le dossier ENGINES.",
            "engines_loaded": "Loaded {count} engine(s)",
            "engines_loaded_fr": "{count} moteur(s) chargé(s)",
            "dry_run_label": "Dry run mode",
            "dry_run_label_fr": "Mode simulation",
        }

    def set_language(self, lang_code: str) -> None:
        """Définit la langue actuelle."""
        self.current_language = lang_code

    def get(self, key: str, default: str = "") -> str:
        """Récupère une chaîne traduite."""
        lang_key = (
            f"{key}_{self.current_language}" if self.current_language != "en" else key
        )
        if lang_key in self.strings:
            return self.strings[lang_key]
        return self.strings.get(key, default)

    def format(self, key: str, **kwargs) -> str:
        """Récupère une chaîne formatée."""
        template = self.get(key, "")
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError):
            return template


class ThemeManager:
    """Gestionnaire de thèmes pour l'application."""

    def __init__(self):
        self.current_theme = "dark"
        self.colors = self._get_default_colors()

    def _get_default_colors(self) -> dict:
        """Retourne les couleurs par défaut pour le thème sombre."""
        return {
            "bg_primary": "#1e1e1e",
            "bg_secondary": "#2d2d2d",
            "text_primary": "#ffffff",
            "text_secondary": "#b0b0b0",
            "accent": "#4da6ff",
            "success": "#4caf50",
            "error": "#f44336",
            "warning": "#ff9800",
            "border": "#404040",
            "group_bg": "#252525",
        }

    def set_theme(self, theme_name: str) -> bool:
        """Définit le thème actuel."""
        if theme_name == "light":
            self.current_theme = "light"
            self.colors = {
                "bg_primary": "#ffffff",
                "bg_secondary": "#f5f5f5",
                "text_primary": "#000000",
                "text_secondary": "#666666",
                "accent": "#0066cc",
                "success": "#28a745",
                "error": "#dc3545",
                "warning": "#ffc107",
                "border": "#cccccc",
                "group_bg": "#f9f9f9",
            }
            return True
        elif theme_name == "dark":
            self.current_theme = "dark"
            self.colors = self._get_default_colors()
            return True
        return False

    def get_stylesheet(self) -> str:
        """Génère la feuille de style pour le thème actuel."""
        c = self.colors
        return f"""
            QMainWindow {{
                background-color: {c['bg_primary']};
                color: {c['text_primary']};
            }}
            QWidget {{
                background-color: {c['bg_primary']};
                color: {c['text_primary']};
            }}
            QGroupBox {{
                background-color: {c['group_bg']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px 0 3px;
            }}
            QPushButton {{
                background-color: {c['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
            QPushButton:disabled {{
                background-color: {c['text_secondary']};
            }}
            QTextEdit {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px;
                font-family: monospace;
            }}
            QLabel {{
                color: {c['text_primary']};
            }}
            QComboBox {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QProgressBar {{
                background-color: {c['bg_secondary']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {c['success']};
                border-radius: 3px;
            }}
            QStatusBar {{
                background-color: {c['bg_secondary']};
                color: {c['text_primary']};
                border-top: 1px solid {c['border']};
            }}
        """


class EnginesStandaloneApp:
    """
    Application autonome pour gérer et exécuter les moteurs de compilation.

    Cette classe fournit une interface CLI/TUI pour:
    - Lister les moteurs disponibles
    - Sélectionner et configurer un moteur
    - Compiler des fichiers avec le moteur choisi
    - Afficher les résultats et logs

    Attributes:
        gui: MockGUI object pour compatibilité avec les moteurs
        language_manager: Gestionnaire de langues
        theme_manager: Gestionnaire de thèmes
    """

    def __init__(
        self,
        engine_id: Optional[str] = None,
        file_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
        language: str = "en",
        theme: str = "dark",
        dry_run: bool = False,
        headless: bool = False,
    ):
        """
        Initialise l'application standalone engines.

        Args:
            engine_id: ID du moteur à utiliser (optionnel)
            file_path: Chemin du fichier à compiler (optionnel)
            workspace_dir: Chemin du workspace (optionnel)
            language: Code de langue ('en' ou 'fr')
            theme: Nom du thème ('light' ou 'dark')
            dry_run: Si True, affiche uniquement la commande sans exécuter
            headless: Si True, fonctionne sans interface GUI (mode CLI)
        """
        self.gui = MockGUI(workspace_dir)
        self.language_manager = LanguageManager()
        self.theme_manager = ThemeManager()

        # Paramètres d'exécution
        self.selected_engine_id = engine_id
        self.selected_file = file_path
        self.workspace_dir = workspace_dir
        self.dry_run = dry_run
        self.headless = headless

        # État de l'application
        self._is_running = False
        self._engines_cache = None

        # Configuration langue et thème
        self.language_manager.set_language(language)
        self.theme_manager.set_theme(theme)

    def load_engines(self) -> List[Dict[str, Any]]:
        """
        Charge et retourne la liste des moteurs disponibles.

        Returns:
            Liste de dictionnaires contenant les informations des moteurs
        """
        if self._engines_cache is not None:
            return self._engines_cache

        engines = []
        engine_ids = available_engines()

        for eid in engine_ids:
            try:
                engine_cls = get_engine(eid)
                if engine_cls:
                    engine_info = {
                        "id": eid,
                        "name": getattr(engine_cls, "name", eid),
                        "version": getattr(engine_cls, "version", "1.0.0"),
                        "required_core": getattr(
                            engine_cls, "required_core_version", "1.0.0"
                        ),
                        "required_sdk": getattr(
                            engine_cls, "required_sdk_version", "1.0.0"
                        ),
                        "class": engine_cls,
                    }
                    engines.append(engine_info)
            except Exception as e:
                logger.error(f"Error loading engine {eid}: {e}")

        self._engines_cache = engines
        return engines

    def get_engine_info(self, engine_id: str) -> Optional[Dict[str, Any]]:
        """
        Retourne les informations d'un moteur spécifique.

        Args:
            engine_id: ID du moteur

        Returns:
            Dictionnaire avec les informations du moteur ou None
        """
        engines = self.load_engines()
        for engine in engines:
            if engine["id"] == engine_id:
                return engine
        return None

    def check_engine_compatibility(self, engine_id: str) -> Dict[str, Any]:
        """
        Vérifie la compatibilité d'un moteur avec le système.

        Args:
            engine_id: ID du moteur à vérifier

        Returns:
            Dictionnaire avec le résultat de la vérification
        """
        engine_info = self.get_engine_info(engine_id)
        if not engine_info:
            return {
                "compatible": False,
                "message": self.language_manager.get("engine_not_found").format(
                    engine=engine_id
                ),
            }

        try:
            result = check_engine_compatibility(
                engine_info["class"],
                get_core_version(),
                get_engine_sdk_version(),
            )

            return {
                "compatible": result.is_compatible,
                "message": result.error_message if not result.is_compatible else None,
                "missing_requirements": result.missing_requirements,
            }
        except Exception as e:
            return {
                "compatible": False,
                "message": str(e),
                "missing_requirements": [],
            }

    def build_command(self, engine_id: str, file_path: str) -> Optional[List[str]]:
        """
        Construit la commande de compilation pour un moteur et fichier donnés.

        Args:
            engine_id: ID du moteur
            file_path: Chemin du fichier à compiler

        Returns:
            Liste de chaînes de commande ou None si erreur
        """
        engine_info = self.get_engine_info(engine_id)
        if not engine_info:
            return None

        try:
            engine = create_engine(engine_id)
            result = engine.program_and_args(self.gui, file_path)

            if result:
                program, args = result
                return [program] + args
            return None
        except Exception as e:
            logger.error(f"Error building command: {e}")
            return None

    def run_compilation(
        self,
        engine_id: str,
        file_path: str,
        dry_run: bool = False,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Exécute la compilation avec le moteur spécifié.

        Args:
            engine_id: ID du moteur à utiliser
            file_path: Chemin du fichier à compiler
            dry_run: Si True, affiche seulement la commande
            env: Variables d'environnement additionnelles

        Returns:
            Dictionnaire avec le résultat de la compilation
        """
        start_time = datetime.now()

        # Vérifications préliminaires
        if not engine_id:
            return {
                "success": False,
                "error": self.language_manager.get("no_engine"),
                "return_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
            }

        if not file_path:
            return {
                "success": False,
                "error": self.language_manager.get("select_file"),
                "return_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
            }

        # Vérifier compatibilité moteur
        compat = self.check_engine_compatibility(engine_id)
        if not compat["compatible"]:
            return {
                "success": False,
                "error": compat.get("message", "Compatibility check failed"),
                "return_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
            }

        # Construire la commande
        cmd = self.build_command(engine_id, file_path)
        if not cmd:
            return {
                "success": False,
                "error": "Failed to build compilation command",
                "return_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_ms": 0,
            }

        # Mode dry run
        if dry_run or self.dry_run:
            return {
                "success": True,
                "dry_run": True,
                "command": " ".join(cmd),
                "cmd_list": cmd,
                "return_code": 0,
                "stdout": f"[DRY RUN] Command: {' '.join(cmd)}",
                "stderr": "",
                "duration_ms": 0,
                "message": self.language_manager.get("dry_run_label"),
            }

        # Préparer l'environnement
        execution_env = os.environ.copy()
        if env:
            execution_env.update(env)

        # Exécuter la commande
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=execution_env,
                cwd=os.path.dirname(file_path) if file_path else None,
            )

            stdout, stderr = proc.communicate()

            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            success = proc.returncode == 0

            return {
                "success": success,
                "return_code": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "duration_ms": duration_ms,
                "command": " ".join(cmd),
                "cmd_list": cmd,
            }

        except Exception as e:
            end_time = datetime.now()
            duration_ms = (end_time - start_time).total_seconds() * 1000

            return {
                "success": False,
                "error": str(e),
                "return_code": -1,
                "stdout": "",
                "stderr": "",
                "duration_ms": duration_ms,
            }

    def execute(self) -> Dict[str, Any]:
        """
        Exécute l'application avec les paramètres configurés.

        Returns:
            Dictionnaire avec le résultat de l'exécution
        """
        results = {
            "engines": self.load_engines(),
            "selected_engine": self.selected_engine_id,
            "selected_file": self.selected_file,
            "compilation": None,
        }

        # Si un moteur et un fichier sont spécifiés, exécuter la compilation
        if self.selected_engine_id and self.selected_file:
            results["compilation"] = self.run_compilation(
                self.selected_engine_id,
                self.selected_file,
                dry_run=self.dry_run,
            )

        return results

    def print_summary(self) -> None:
        """Affiche un résumé de l'état de l'application."""
        print("\n" + "=" * 60)
        print("ENGINES STANDALONE - Application Summary")
        print("=" * 60)

        engines = self.load_engines()
        print(f"\nAvailable engines ({len(engines)}):")
        for eng in engines:
            compat = self.check_engine_compatibility(eng["id"])
            status = "OK" if compat["compatible"] else "FAIL"
            print(f"  [{status}] {eng['name']} ({eng['id']}) v{eng['version']}")

        if self.selected_engine_id:
            print(f"\nSelected engine: {self.selected_engine_id}")

        if self.selected_file:
            print(f"File to compile: {self.selected_file}")

        if self.dry_run:
            print("\nMode: Dry-run (simulation)")

        print()


def run_cli(
    engine_id: Optional[str] = None,
    file_path: Optional[str] = None,
    workspace_dir: Optional[str] = None,
    language: str = "en",
    theme: str = "dark",
    dry_run: bool = False,
    list_engines: bool = False,
    check_compat: Optional[str] = None,
) -> None:
    """
    Point d'entrée CLI pour l'application standalone engines.

    Args:
        engine_id: Moteur à utiliser
        file_path: Fichier à compiler
        workspace_dir: Workspace du projet
        language: Langue de l'interface
        theme: Thème visuel
        dry_run: Mode simulation
        list_engines: Lister les moteurs disponibles
        check_compat: Vérifier la compatibilité d'un moteur
    """
    app = EnginesStandaloneApp(
        engine_id=engine_id,
        file_path=file_path,
        workspace_dir=workspace_dir,
        language=language,
        theme=theme,
        dry_run=dry_run,
        headless=True,
    )

    if list_engines:
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
        return

    if check_compat:
        result = app.check_engine_compatibility(check_compat)
        print(f"\nCompatibility check for: {check_compat}")
        if result["compatible"]:
            print("  OK - Engine is compatible")
        else:
            print("  FAIL - Engine has compatibility issues:")
            if result.get("missing_requirements"):
                for req in result["missing_requirements"]:
                    print(f"     - {req}")
            if result.get("message"):
                print(f"     Message: {result['message']}")
        return

    if engine_id and file_path:
        result = app.run_compilation(engine_id, file_path, dry_run=dry_run)
        print(f"\nCompilation result with {engine_id}:\n")
        if result.get("dry_run"):
            print(f"[SIMULATION] Command: {result.get('command', '')}")
        elif result["success"]:
            print("Compilation successful!")
            if result.get("stdout"):
                print("\nOutput:")
                print(result["stdout"])
        else:
            print("Compilation failed")
            if result.get("error"):
                print(f"Error: {result['error']}")
            if result.get("stderr"):
                print("\nStderr:")
                print(result["stderr"])
    else:
        app.print_summary()


def main():
    """Point d'entrée principal pour l'application standalone."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Engines Standalone - Execute compilation engines independently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List available engines
    python -m Core.engines_loader.engines_only_mod --list-engines
    
    # Check engine compatibility
    python -m Core.engines_loader.engines_only_mod --check-compat nuitka
    
    # Compile a file with a specific engine (dry-run)
    python -m Core.engines_loader.engines_only_mod --engine nuitka --dry-run script.py
    
    # Compile a file with a specific engine
    python -m Core.engines_loader.engines_only_mod --engine pyinstaller --file script.py
        """,
    )

    parser.add_argument(
        "-e",
        "--engine",
        help="Engine ID to use for compilation",
    )
    parser.add_argument(
        "-f",
        "--file",
        help="File to compile",
    )
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
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="Show command without executing",
    )
    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List available engines",
    )
    parser.add_argument(
        "--check-compat",
        metavar="ENGINE_ID",
        help="Check engine compatibility",
    )

    args = parser.parse_args()

    run_cli(
        engine_id=args.engine,
        file_path=args.file,
        workspace_dir=args.workspace,
        language=args.language,
        theme=args.theme,
        dry_run=args.dry_run,
        list_engines=args.list_engines,
        check_compat=args.check_compat,
    )


if __name__ == "__main__":
    main()
