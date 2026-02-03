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
BcaslOnlyMod Application - Application Standalone pour les Plugins BCASL

Module autonome permettant d'exécuter et configurer les plugins BCASL
indépendamment de l'application principale PyCompiler ARK.

Fonctionnalités:
    - Interface graphique complète pour gérer les plugins BCASL
    - Découverte automatique des plugins dans le dossier Plugins/
    - Activation/désactivation individuelle des plugins
    - Réordonnancement de l'exécution des plugins
    - Exécution synchrone et asynchrone des plugins
    - Affichage des rapports d'exécution détaillés
    - Support des thèmes clair/sombre
    - Support multilingue (EN/FR)

Utilisation:
    # Interface GUI
    python -m OnlyMod.BcaslOnlyMod

    # Via l'application
    from OnlyMod.BcaslOnlyMod import launch_bcasl_gui
    launch_bcasl_gui(workspace_dir="/path/to/workspace", language="fr", theme="dark")
"""

from __future__ import annotations

import os
import sys
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

# Importations des modules PyCompiler ARK
from Core.allversion import get_core_version, get_bcasl_version

# Importations BCASL
from bcasl import (
    BCASL,
    BcPluginBase,
    PluginMeta,
    PreCompileContext,
    ExecutionReport,
)
from bcasl.Loader import _discover_bcasl_meta
from bcasl.tagging import compute_tag_order

# Importations GUI
from .gui import BcaslStandaloneGui


# Variable globale pour la langue
_CURRENT_LANGUAGE = "en"


def tr(en_text: str, fr_text: str) -> str:
    """Fonction de traduction simple pour BcaslOnlyMod."""
    return fr_text if _CURRENT_LANGUAGE == "fr" else en_text


class LanguageManager:
    """Gestionnaire de langues pour l'application."""

    def __init__(self, lang_code: str = "en"):
        self.current_language = lang_code
        global _CURRENT_LANGUAGE
        _CURRENT_LANGUAGE = lang_code
        self.strings = self._get_strings()

    def _get_strings(self) -> Dict[str, Dict[str, str]]:
        """Retourne les chaînes traduites."""
        return {
            "en": {
                "app_title": "BCASL Standalone - Plugin Manager",
                "global_enable": "Enable BCASL",
                "plugins": "Plugins",
                "execution": "Execution",
                "log": "Execution Log",
                "run": "Run Plugins",
                "cancel": "Cancel",
                "clear_log": "Clear Log",
                "ready": "Ready",
                "running": "Running plugins...",
                "completed": "Completed",
                "failed": "Failed",
                "no_plugins": "No plugins available",
                "discovered": "Discovered {count} plugin(s)",
                "starting": "Starting BCASL execution",
                "workspace": "Workspace: {path}",
                "enabled": "Enabled plugins: {count}",
                "report": "Execution Report",
                "all_ok": "All plugins executed successfully",
                "some_failed": "Some plugins failed",
                "cancelled": "Execution cancelled",
                "no_workspace": "Please select a workspace folder first.",
                "no_plugins_enabled": "No plugins enabled. Please enable at least one plugin.",
            },
            "fr": {
                "app_title": "BCASL Standalone - Gestionnaire de Plugins",
                "global_enable": "Activer BCASL",
                "plugins": "Plugins",
                "execution": "Execution",
                "log": "Journal d'Exécution",
                "run": "Exécuter les Plugins",
                "cancel": "Annuler",
                "clear_log": "Effacer Log",
                "ready": "Prêt",
                "running": "Exécution des plugins...",
                "completed": "Terminé",
                "failed": "Échec",
                "no_plugins": "Aucun plugin disponible",
                "discovered": "{count} plugin(s) découvert(s)",
                "starting": "Début de l'exécution BCASL",
                "workspace": "Workspace : {path}",
                "enabled": "Plugins activés : {count}",
                "report": "Rapport d'Exécution",
                "all_ok": "Tous les plugins exécutés avec succès",
                "some_failed": "Certains plugins ont échoué",
                "cancelled": "Exécution annulée",
                "no_workspace": "Veuillez d'abord sélectionner un dossier workspace.",
                "no_plugins_enabled": "Aucun plugin activé. Veuillez activer au moins un plugin.",
            },
        }

    def get(self, key: str, **kwargs) -> str:
        """Récupère une chaîne traduite avec formatage optionnel."""
        lang_strings = self.strings.get(self.current_language, self.strings["en"])
        default_strings = self.strings.get("en", {})

        text = lang_strings.get(key, default_strings.get(key, key))

        try:
            return text.format(**kwargs) if kwargs else text
        except (KeyError, ValueError):
            return text


class ThemeManager:
    """Gestionnaire de thèmes pour l'application."""

    def __init__(self, theme_name: str = "dark"):
        self.current_theme = theme_name
        self.colors = self._get_theme_colors(theme_name)

    def _get_theme_colors(self, theme_name: str) -> Dict[str, str]:
        """Retourne les couleurs du thème."""
        if theme_name == "dark":
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
        else:  # light
            return {
                "bg_primary": "#f5f5f5",
                "bg_secondary": "#ffffff",
                "text_primary": "#000000",
                "text_secondary": "#666666",
                "accent": "#0066cc",
                "success": "#28a745",
                "error": "#dc3545",
                "warning": "#ffc107",
                "border": "#cccccc",
                "group_bg": "#f9f9f9",
            }

    def set_theme(self, theme_name: str) -> bool:
        """Définit le thème actuel."""
        if theme_name in ("light", "dark"):
            self.current_theme = theme_name
            self.colors = self._get_theme_colors(theme_name)
            return True
        return False


class BcaslOnlyModApp:
    """
    Application autonome pour gérer et exécuter les plugins BCASL.

    Cette classe fournit une interface programmatique pour:
    - Découvrir les plugins BCASL disponibles
    - Gérer l'activation/désactivation des plugins
    - Réordonner l'exécution des plugins
    - Exécuter les plugins de pré-compilation
    - Afficher les rapports d'exécution
    """

    # Variable de classe pour la langue
    _language = "en"

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        language: str = "en",
        theme: str = "dark",
        headless: bool = False,
    ):
        """
        Initialise l'application BcaslOnlyMod.

        Args:
            workspace_dir: Chemin du workspace (optionnel)
            language: Code de langue ('en' ou 'fr')
            theme: Nom du thème ('light' ou 'dark')
            headless: Si True, fonctionne sans interface GUI (mode CLI)
        """
        self.workspace_dir = workspace_dir
        self.headless = headless
        BcaslOnlyModApp._language = language

        # Gestionnaires
        self.language_manager = LanguageManager(language)
        self.theme_manager = ThemeManager(theme)

        # État de l'application
        self.plugins_meta: Dict[str, Dict[str, Any]] = {}
        self.config: Dict[str, Any] = {}
        self.Plugins_dir: Optional[Path] = None
        self.repo_root: Optional[Path] = None

        # Initialisation
        self._init_paths()
        self._load_config()
        self._discover_plugins()

    def _init_paths(self):
        """Initialise les chemins."""
        try:
            self.repo_root = Path(__file__).resolve().parents[1]
            self.Plugins_dir = self.repo_root / "Plugins"
        except Exception:
            pass

    def _load_config(self):
        """Charge la configuration BCASL."""
        from bcasl.Loader import _load_workspace_config

        self.config = {}
        if self.workspace_dir:
            workspace_root = Path(self.workspace_dir).resolve()
            self.config = _load_workspace_config(workspace_root)

    def _discover_plugins(self):
        """Découvre les plugins BCASL disponibles."""
        if not self.Plugins_dir or not self.Plugins_dir.exists():
            return

        self.plugins_meta = _discover_bcasl_meta(self.Plugins_dir)

    def get_plugins_info(self) -> List[Dict[str, Any]]:
        """Retourne la liste des plugins avec leurs informations."""
        if not self.plugins_meta:
            return []

        try:
            order = compute_tag_order(self.plugins_meta)
        except Exception:
            order = sorted(self.plugins_meta.keys())

        plugins = []
        for pid in order:
            meta = self.plugins_meta.get(pid, {})
            plugins.append(
                {
                    "id": pid,
                    "name": meta.get("name", pid),
                    "version": meta.get("version", ""),
                    "description": meta.get("description", ""),
                    "author": meta.get("author", ""),
                    "tags": meta.get("tags", []),
                    "requirements": meta.get("requirements", []),
                }
            )

        return plugins

    def get_plugin_order(self, config: Optional[Dict[str, Any]] = None) -> List[str]:
        """Calcule l'ordre d'exécution des plugins."""
        cfg = config or self.config
        plugin_order = cfg.get("plugin_order", []) if isinstance(cfg, dict) else []

        if plugin_order:
            plugin_order = [pid for pid in plugin_order if pid in self.plugins_meta]
        else:
            try:
                plugin_order = compute_tag_order(self.plugins_meta)
            except Exception:
                plugin_order = sorted(self.plugins_meta.keys())

        return plugin_order

    def get_enabled_plugins(
        self, config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, bool]:
        """Retourne l'état d'activation des plugins."""
        cfg = config or self.config
        plugins_cfg = cfg.get("plugins", {}) if isinstance(cfg, dict) else {}

        enabled = {}
        for pid in self.plugins_meta:
            try:
                pentry = plugins_cfg.get(pid, {})
                if isinstance(pentry, dict):
                    enabled[pid] = pentry.get("enabled", True)
                elif isinstance(pentry, bool):
                    enabled[pid] = pentry
                else:
                    enabled[pid] = True
            except Exception:
                enabled[pid] = True

        return enabled

    def run_plugins(
        self,
        workspace_dir: Optional[str] = None,
        plugin_order: Optional[List[str]] = None,
        enabled_plugins: Optional[Dict[str, bool]] = None,
        config: Optional[Dict[str, Any]] = None,
        timeout: float = 0.0,
        log_callback: Optional[callable] = None,
    ) -> Optional[ExecutionReport]:
        """Exécute les plugins BCASL de manière synchrone."""
        ws_dir = workspace_dir or self.workspace_dir
        if not ws_dir:
            if log_callback:
                log_callback(self.language_manager.get("no_workspace"))
            return None

        ws_root = Path(ws_dir).resolve()
        cfg = config or self.config

        if not ws_root.exists():
            if log_callback:
                log_callback(f"Error: Workspace not found: {ws_root}")
            return None

        order = plugin_order or self.get_plugin_order(cfg)
        enabled = enabled_plugins or self.get_enabled_plugins(cfg)

        active_order = [pid for pid in order if enabled.get(pid, False)]
        if not active_order:
            if log_callback:
                log_callback(self.language_manager.get("no_plugins_enabled"))
            return None

        if log_callback:
            log_callback("=" * 50)
            log_callback(self.language_manager.get("starting"))
            log_callback(self.language_manager.get("workspace", path=ws_root))
            log_callback(self.language_manager.get("enabled", count=len(active_order)))
            log_callback("=" * 50)

        try:
            manager = BCASL(
                ws_root,
                config=cfg,
                plugin_timeout_s=timeout,
            )
        except Exception as e:
            if log_callback:
                log_callback(f"Error creating BCASL manager: {e}")
            return None

        if self.Plugins_dir and self.Plugins_dir.exists():
            loaded, errors = manager.load_plugins_from_directory(self.Plugins_dir)
            if log_callback:
                log_callback(f"BCASL: {loaded} plugin(s) charge(s)")
                for mod, msg in errors or []:
                    log_callback(f"Plugin '{mod}': {msg}")

        for pid, is_enabled in enabled.items():
            if not is_enabled:
                manager.disable_plugin(pid)

        for idx, pid in enumerate(order):
            try:
                manager.set_priority(pid, idx)
            except Exception:
                pass

        workspace_meta = {
            "workspace_name": ws_root.name,
            "workspace_path": str(ws_root),
            "file_patterns": cfg.get("file_patterns", []),
            "exclude_patterns": cfg.get("exclude_patterns", []),
            "required_files": cfg.get("required_files", []),
        }

        ctx = PreCompileContext(
            ws_root,
            config=cfg,
            workspace_metadata=workspace_meta,
        )

        try:
            report = manager.run_pre_compile(ctx)
        except Exception as e:
            if log_callback:
                log_callback(f"Error running plugins: {e}")
            return None

        if log_callback:
            log_callback("=" * 50)
            log_callback(self.language_manager.get("report"))
            log_callback("-" * 30)

            for item in report:
                state = "OK" if item.success else f"FAIL: {item.error}"
                log_callback(f"  - {item.name}: {state} ({item.duration_ms:.1f} ms)")

            log_callback("-" * 30)
            log_callback(report.summary())

            if report.ok:
                log_callback(self.language_manager.get("all_ok"))
            else:
                log_callback(self.language_manager.get("some_failed"))

            log_callback("=" * 50)

        return report

    def print_summary(self):
        """Affiche un résumé de l'état de l'application."""
        print("\n" + "=" * 60)
        print("BCASL STANDALONE - Application Summary")
        print("=" * 60)

        print(f"\nCore Version: {get_core_version()}")
        print(f"BCASL Version: {get_bcasl_version()}")

        if self.workspace_dir:
            print(f"Workspace: {self.workspace_dir}")

        plugins = self.get_plugins_info()
        print(f"\nAvailable plugins ({len(plugins)}):")

        for plugin in plugins:
            tags = plugin.get("tags", [])
            phase = ""
            if tags:
                from bcasl.tagging import get_tag_phase_name

                phase = get_tag_phase_name(tags[0])

            print(f"  - {plugin['name']} ({plugin['id']})")
            print(f"      Version: {plugin['version']}")
            if phase:
                print(f"      Phase: {phase}")
            if tags:
                print(f"      Tags: {', '.join(tags)}")

        print()

    def launch_gui(
        self,
        workspace_dir: Optional[str] = None,
        language: Optional[str] = None,
        theme: Optional[str] = None,
    ) -> int:
        """Lance l'interface graphique."""
        from .gui import launch_bcasl_gui

        ws = workspace_dir or self.workspace_dir
        lang = language or self.language_manager.current_language
        thm = theme or self.theme_manager.current_theme

        return launch_bcasl_gui(
            workspace_dir=ws,
            language=lang,
            theme=thm,
        )


def run_cli(
    workspace_dir: Optional[str] = None,
    language: str = "en",
    theme: str = "dark",
    list_plugins: bool = False,
    run: bool = False,
    timeout: float = 0.0,
) -> None:
    """Point d'entrée CLI pour l'application standalone BCASL."""
    global _CURRENT_LANGUAGE
    _CURRENT_LANGUAGE = language

    app = BcaslOnlyModApp(
        workspace_dir=workspace_dir,
        language=language,
        theme=theme,
        headless=True,
    )

    if list_plugins:
        plugins = app.get_plugins_info()
        print(f"\nAvailable BCASL plugins ({len(plugins)}):\n")

        from bcasl.tagging import get_tag_phase_name

        for plugin in plugins:
            tags = plugin.get("tags", [])
            phase = get_tag_phase_name(tags[0]) if tags else "Default"

            print(f"  * {plugin['name']}")
            print(f"      ID: {plugin['id']}")
            print(f"      Version: {plugin['version']}")
            if plugin.get("description"):
                print(f"      Description: {plugin['description']}")
            print(f"      Phase: {phase}")
            if tags:
                print(f"      Tags: {', '.join(tags)}")
            print()
        return

    if run:

        def log_callback(msg: str):
            print(f"[LOG] {msg}")

        report = app.run_plugins(
            workspace_dir=workspace_dir,
            timeout=timeout,
            log_callback=log_callback,
        )

        if report:
            if report.ok:
                print("\nAll plugins executed successfully")
            else:
                print(
                    f"\n{sum(1 for item in report if not item.success)} plugin(s) failed"
                )
        return

    app.print_summary()


def main():
    """Point d'entrée principal pour l'application standalone."""
    parser = argparse.ArgumentParser(
        description="BCASL Standalone - Execute BCASL plugins independently",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # List available plugins
    python -m OnlyMod.BcaslOnlyMod --list-plugins
    
    # Run plugins in workspace
    python -m OnlyMod.BcaslOnlyMod --run --workspace /path/to/workspace
    
    # Run plugins with timeout (30 seconds)
    python -m OnlyMod.BcaslOnlyMod --run --workspace /path/to/workspace --timeout 30
    
    # Launch GUI with French language
    python -m OnlyMod.BcaslOnlyMod --gui --language fr
        """,
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
        "--list-plugins",
        action="store_true",
        help="List available BCASL plugins",
    )
    parser.add_argument(
        "-r",
        "--run",
        action="store_true",
        help="Execute BCASL plugins",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=0.0,
        help="Plugin execution timeout in seconds (0 = unlimited)",
    )
    parser.add_argument(
        "-g",
        "--gui",
        action="store_true",
        help="Launch GUI interface",
    )

    args = parser.parse_args()

    if args.gui:
        from .gui import launch_bcasl_gui

        sys.exit(
            launch_bcasl_gui(
                workspace_dir=args.workspace,
                language=args.language,
                theme=args.theme,
            )
        )

    run_cli(
        workspace_dir=args.workspace,
        language=args.language,
        theme=args.theme,
        list_plugins=args.list_plugins,
        run=args.run,
        timeout=args.timeout,
    )


if __name__ == "__main__":
    main()
