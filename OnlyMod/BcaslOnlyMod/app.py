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
BCASL Standalone GUI Application

Interface complète pour exécuter BCASL indépendamment du compilateur principal.
Fournit une interface utilisateur moderne avec système de thème intégré.
"""

from __future__ import annotations

import os
import sys
import logging
import json
from pathlib import Path
from typing import Optional, Callable, Dict, Any

try:
    from PySide6.QtWidgets import (
        QApplication,
        QPyCompilerArkGui,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QTextEdit,
        QFileDialog,
        QMessageBox,
        QProgressBar,
        QCheckBox,
        QComboBox,
        QGroupBox,
        QSplitter,
    )
    from PySide6.QtCore import Qt, QThread, Signal, Slot, QTimer
    from PySide6.QtGui import QFont, QColor, QIcon, QPixmap
except ImportError:
    print("Error: PySide6 is required. Install it with: pip install PySide6")
    sys.exit(1)

from bcasl import (
    run_pre_compile_async,
    run_pre_compile,
    ensure_bcasl_thread_stopped,
    open_bc_loader_dialog,
    resolve_bcasl_timeout,
)
from bcasl.Loader import _load_workspace_config

# Configure logging
logger = logging.getLogger(__name__)


class LanguageManager:
    """Manages application languages loaded from JSON files."""

    def __init__(self):
        self.languages = {}
        self.current_language = "en"
        self.strings = {}
        self._load_languages()

    def _load_languages(self):
        """Load languages from JSON files in languages directory."""
        languages_dir = Path(__file__).parent / "languages"

        if not languages_dir.exists():
            logger.warning(f"Languages directory not found: {languages_dir}")
            self._load_default_language()
            return

        try:
            for lang_file in sorted(languages_dir.glob("*.json")):
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        lang_data = json.load(f)
                        lang_code = lang_data.get("code", lang_file.stem)
                        self.languages[lang_code] = {
                            "name": lang_data.get("name", lang_code),
                            "native_name": lang_data.get("native_name", lang_code),
                            "strings": lang_data.get("strings", {}),
                        }
                except Exception as e:
                    logger.error(f"Failed to load language from {lang_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading languages: {e}")
            self._load_default_language()

        if self.languages:
            self.current_language = list(self.languages.keys())[0]
            self.strings = self.languages[self.current_language]["strings"].copy()
        else:
            self._load_default_language()

    def _load_default_language(self):
        """Load default English language as fallback."""
        self.languages = {
            "en": {
                "name": "English",
                "native_name": "English",
                "strings": {
                    "app_title": "BCASL Standalone - Before Compilation Actions System Loader",
                    "workspace_config": "Workspace Configuration",
                    "workspace_label": "Workspace:",
                    "no_workspace": "No workspace selected",
                    "browse_button": "Browse...",
                    "config_summary": "Configuration summary",
                    "execution_log": "Execution Log:",
                    "run_async": "Run asynchronously",
                    "theme_label": "Theme:",
                    "configure_plugins": "⚙️ Configure Plugins",
                    "run_bcasl": "▶️ Run BCASL",
                    "clear_log": "🗑️ Clear Log",
                    "exit_button": "Exit",
                    "ready": "Ready",
                    "running": "Running BCASL...",
                    "completed": "Completed",
                    "failed": "Failed",
                },
            }
        }
        self.current_language = "en"
        self.strings = self.languages["en"]["strings"].copy()

    def set_language(self, lang_code: str) -> bool:
        """Set the current language."""
        if lang_code not in self.languages:
            return False
        self.current_language = lang_code
        self.strings = self.languages[lang_code]["strings"].copy()
        return True

    def get_language_names(self) -> list:
        """Get list of available language codes."""
        return list(self.languages.keys())

    def get_language_display_names(self) -> list:
        """Get list of available language display names."""
        return [self.languages[code]["name"] for code in self.get_language_names()]

    def get(self, key: str, default: str = "") -> str:
        """Get translated string."""
        return self.strings.get(key, default)

    def format(self, key: str, **kwargs) -> str:
        """Get translated string with formatting."""
        template = self.strings.get(key, "")
        try:
            return template.format(**kwargs)
        except KeyError:
            return template


class ThemeManager:
    """Manages application themes loaded from JSON files."""

    def __init__(self):
        self.THEMES = {}
        self.current_theme = "light"
        self.colors = {}
        self._load_themes()

    def _load_themes(self):
        """Load themes from JSON files in themes directory."""
        themes_dir = Path(__file__).parent / "themes"

        if not themes_dir.exists():
            logger.warning(f"Themes directory not found: {themes_dir}")
            self._load_default_themes()
            return

        try:
            for theme_file in sorted(themes_dir.glob("*.json")):
                try:
                    with open(theme_file, "r", encoding="utf-8") as f:
                        theme_data = json.load(f)
                        theme_id = theme_data.get("id", theme_file.stem)
                        self.THEMES[theme_id] = {
                            "name": theme_data.get("name", theme_id),
                            "description": theme_data.get("description", ""),
                            "colors": theme_data.get("colors", {}),
                        }
                except Exception as e:
                    logger.error(f"Failed to load theme from {theme_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading themes: {e}")
            self._load_default_themes()

        # Set default theme
        if self.THEMES:
            self.current_theme = list(self.THEMES.keys())[0]
            self.colors = self.THEMES[self.current_theme]["colors"].copy()
        else:
            self._load_default_themes()

    def _load_default_themes(self):
        """Load default themes as fallback."""
        self.THEMES = {
            "light": {
                "name": "Light",
                "description": "Clean light theme with blue accents",
                "colors": {
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
                },
            },
            "dark": {
                "name": "Dark",
                "description": "Dark theme for low-light environments",
                "colors": {
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
                },
            },
        }
        self.current_theme = "light"
        self.colors = self.THEMES["light"]["colors"].copy()

    def set_theme(self, theme_name: str) -> bool:
        """Set the current theme."""
        if theme_name not in self.THEMES:
            return False
        self.current_theme = theme_name
        self.colors = self.THEMES[theme_name]["colors"].copy()
        return True

    def get_theme_names(self) -> list:
        """Get list of available theme names."""
        return list(self.THEMES.keys())

    def get_theme_display_names(self) -> list:
        """Get list of available theme display names."""
        return [self.THEMES[tid]["name"] for tid in self.get_theme_names()]

    def get_stylesheet(self) -> str:
        """Generate stylesheet for current theme."""
        return f"""
            QPyCompilerArkGui {{
                background-color: {self.colors['bg_primary']};
                color: {self.colors['text_primary']};
            }}
            QWidget {{
                background-color: {self.colors['bg_primary']};
                color: {self.colors['text_primary']};
            }}
            QGroupBox {{
                background-color: {self.colors['group_bg']};
                border: 1px solid {self.colors['border']};
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
                background-color: {self.colors['accent']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._lighten(self.colors['accent'], 20)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken(self.colors['accent'], 20)};
            }}
            QPushButton:disabled {{
                background-color: {self.colors['text_secondary']};
                color: {self.colors['bg_secondary']};
            }}
            QTextEdit {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px;
                font-family: monospace;
            }}
            QLabel {{
                color: {self.colors['text_primary']};
            }}
            QCheckBox {{
                color: {self.colors['text_primary']};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.colors['accent']};
                border: 1px solid {self.colors['accent']};
                border-radius: 3px;
            }}
            QComboBox {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QProgressBar {{
                background-color: {self.colors['bg_secondary']};
                border: 1px solid {self.colors['border']};
                border-radius: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['success']};
                border-radius: 3px;
            }}
            QStatusBar {{
                background-color: {self.colors['bg_secondary']};
                color: {self.colors['text_primary']};
                border-top: 1px solid {self.colors['border']};
            }}
        """

    @staticmethod
    def _lighten(color: str, percent: int) -> str:
        """Lighten a hex color."""
        try:
            color = color.lstrip("#")
            rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
            rgb = tuple(min(255, int(c + (255 - c) * percent / 100)) for c in rgb)
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except:
            return color

    @staticmethod
    def _darken(color: str, percent: int) -> str:
        """Darken a hex color."""
        try:
            color = color.lstrip("#")
            rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
            rgb = tuple(int(c * (100 - percent) / 100) for c in rgb)
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except:
            return color


class BcaslStandaloneApp(QPyCompilerArkGui):
    """Application autonome pour exécuter BCASL avec système de thème.

    Fournit une interface utilisateur pour:
    - Sélectionner un workspace
    - Configurer les plugins BCASL
    - Exécuter les actions de pré-compilation
    - Afficher les résultats et les logs
    - Gérer les thèmes d'interface
    """

    def __init__(self, workspace_dir: Optional[str] = None):
        super().__init__()
        self.workspace_dir = workspace_dir
        self.log = None
        self._bcasl_thread = None
        self._bcasl_worker = None
        self._bcasl_ui_bridge = None
        self._is_running = False
        self._config_cache = None
        self._last_config_load_time = 0

        # Initialize language and theme managers
        self.language_manager = LanguageManager()
        self.theme_manager = ThemeManager()
        self._load_language_preference()
        self._load_theme_preference()

        self.setWindowTitle(self.language_manager.get("app_title", "BCASL Standalone"))
        self.setGeometry(100, 100, 1100, 800)
        self.setMinimumSize(900, 650)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Workspace selection group
        self.ws_group = QGroupBox(
            self.language_manager.get("workspace_config", "Workspace Configuration")
        )
        ws_layout = QHBoxLayout(self.ws_group)
        self.ws_label = QLabel(
            self.language_manager.get("workspace_label", "Workspace:")
        )
        self.ws_label.setMinimumWidth(80)
        self.ws_display = QLabel(
            workspace_dir
            or self.language_manager.get("no_workspace", "No workspace selected")
        )
        self.ws_display.setToolTip(
            self.language_manager.get(
                "config_summary", "Currently selected workspace directory"
            )
        )
        self.ws_browse_btn = QPushButton(
            self.language_manager.get("browse_button", "Browse...")
        )
        self.ws_browse_btn.setMaximumWidth(100)
        self.ws_browse_btn.clicked.connect(self._select_workspace)
        ws_layout.addWidget(self.ws_label)
        ws_layout.addWidget(self.ws_display)
        ws_layout.addStretch()
        ws_layout.addWidget(self.ws_browse_btn)
        layout.addWidget(self.ws_group)

        # Config info
        self.config_info = QLabel(
            self.language_manager.get("no_config", "No configuration loaded")
        )
        self.config_info.setToolTip(
            self.language_manager.get(
                "config_summary",
                "Configuration summary: enabled plugins, file patterns, etc.",
            )
        )
        layout.addWidget(self.config_info)

        # Log output
        self.log_label = QLabel(
            self.language_manager.get("execution_log", "Execution Log:")
        )
        log_label_font = QFont()
        log_label_font.setBold(True)
        self.log_label.setFont(log_label_font)
        layout.addWidget(self.log_label)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(280)
        layout.addWidget(self.log)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMaximumHeight(20)
        layout.addWidget(self.progress)

        # Options and theme
        options_layout = QHBoxLayout()
        self.chk_async = QCheckBox(
            self.language_manager.get("run_async", "Run asynchronously")
        )
        self.chk_async.setChecked(True)
        self.chk_async.setToolTip(
            self.language_manager.get(
                "run_async_tooltip",
                "Execute BCASL in background thread for better responsiveness",
            )
        )
        options_layout.addWidget(self.chk_async)

        # Language selector
        self.lang_label = QLabel(
            self.language_manager.get("language_label", "Language:")
        )
        self.lang_combo = QComboBox()

        # Store code -> display name mapping
        self._lang_codes = self.language_manager.get_language_names()
        self._lang_display_names = [
            self.language_manager.languages[code]["native_name"]
            for code in self._lang_codes
        ]

        # Add display names to combo
        self.lang_combo.addItems(self._lang_display_names)

        # Set current language by display name
        current_index = self._lang_codes.index(self.language_manager.current_language)
        self.lang_combo.setCurrentIndex(current_index)

        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.lang_combo.setMaximumWidth(150)

        # Theme selector
        self.theme_label = QLabel(self.language_manager.get("theme_label", "Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.theme_manager.THEMES.keys()))
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self.theme_combo.setMaximumWidth(120)

        options_layout.addStretch()
        options_layout.addWidget(self.lang_label)
        options_layout.addWidget(self.lang_combo)
        options_layout.addWidget(self.theme_label)
        options_layout.addWidget(self.theme_combo)
        layout.addLayout(options_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_config = QPushButton(
            self.language_manager.get("configure_plugins", "⚙️ Configure Plugins")
        )
        self.btn_config.setToolTip(
            self.language_manager.get(
                "configure_plugins_tooltip", "Open plugin configuration dialog"
            )
        )
        self.btn_config.clicked.connect(self._open_config_dialog)
        self.btn_run = QPushButton(
            self.language_manager.get("run_bcasl", "▶️ Run BCASL")
        )
        self.btn_run.setToolTip(
            self.language_manager.get(
                "run_bcasl_tooltip", "Execute BCASL pre-compilation actions"
            )
        )
        self.btn_run.clicked.connect(self._run_bcasl)
        self.btn_clear = QPushButton(
            self.language_manager.get("clear_log", "🗑️ Clear Log")
        )
        self.btn_clear.setToolTip(
            self.language_manager.get("clear_log_tooltip", "Clear the execution log")
        )
        self.btn_clear.clicked.connect(self.log.clear)
        self.btn_exit = QPushButton(self.language_manager.get("exit_button", "Exit"))
        self.btn_exit.setToolTip(
            self.language_manager.get("exit_tooltip", "Close the application")
        )
        self.btn_exit.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_config)
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_exit)
        layout.addLayout(btn_layout)

        # Status bar
        self.statusBar().showMessage(self.language_manager.get("ready", "Ready"))

        # Apply theme
        self._apply_theme()

        # Load initial config if workspace provided
        if workspace_dir:
            self._load_config_info()

    def _load_language_preference(self):
        """Load language preference from config file."""
        try:
            config_file = Path.home() / ".bcasl_language"
            if config_file.exists():
                with open(config_file, "r") as f:
                    data = json.load(f)
                    lang = data.get("language", "en")
                    if lang in self.language_manager.get_language_names():
                        self.language_manager.set_language(lang)
        except Exception:
            pass

    def _save_language_preference(self):
        """Save language preference to config file."""
        try:
            config_file = Path.home() / ".bcasl_language"
            with open(config_file, "w") as f:
                json.dump({"language": self.language_manager.current_language}, f)
        except Exception:
            pass

    def _load_theme_preference(self):
        """Load theme preference from config file."""
        try:
            config_file = Path.home() / ".bcasl_theme"
            if config_file.exists():
                with open(config_file, "r") as f:
                    data = json.load(f)
                    theme = data.get("theme", "light")
                    if theme in self.theme_manager.THEMES:
                        self.theme_manager.set_theme(theme)
        except Exception:
            pass

    def _save_theme_preference(self):
        """Save theme preference to config file."""
        try:
            config_file = Path.home() / ".bcasl_theme"
            with open(config_file, "w") as f:
                json.dump({"theme": self.theme_manager.current_theme}, f)
        except Exception:
            pass

    def _on_language_changed(self, index: int):
        """Handle language change."""
        if index < 0 or index >= len(self._lang_codes):
            return

        lang_code = self._lang_codes[index]
        if self.language_manager.set_language(lang_code):
            self._save_language_preference()
            self._update_ui_texts()

            # Update language combo display names after language change
            self._lang_display_names = [
                self.language_manager.languages[code]["native_name"]
                for code in self._lang_codes
            ]

    def _on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        if self.theme_manager.set_theme(theme_name):
            self._apply_theme()
            self._save_theme_preference()

    def _apply_theme(self):
        """Apply current theme to the application."""
        stylesheet = self.theme_manager.get_stylesheet()
        self.setStyleSheet(stylesheet)

    def _update_ui_texts(self):
        """Update all UI text elements with current language."""
        self.setWindowTitle(self.language_manager.get("app_title", "BCASL Standalone"))
        self.ws_group.setTitle(
            self.language_manager.get("workspace_config", "Workspace Configuration")
        )
        self.ws_label.setText(
            self.language_manager.get("workspace_label", "Workspace:")
        )
        if not self.workspace_dir:
            self.ws_display.setText(
                self.language_manager.get("no_workspace", "No workspace selected")
            )
        self.ws_display.setToolTip(
            self.language_manager.get(
                "config_summary", "Currently selected workspace directory"
            )
        )

        if (
            self.config_info.text() == "No configuration loaded"
            or self.config_info.text().startswith("Aucune configuration")
        ):
            self.config_info.setText(
                self.language_manager.get("no_config", "No configuration loaded")
            )
        self.config_info.setToolTip(
            self.language_manager.get(
                "config_summary",
                "Configuration summary: enabled plugins, file patterns, etc.",
            )
        )

        self.log_label.setText(
            self.language_manager.get("execution_log", "Execution Log:")
        )
        self.chk_async.setText(
            self.language_manager.get("run_async", "Run asynchronously")
        )
        self.chk_async.setToolTip(
            self.language_manager.get(
                "run_async_tooltip",
                "Execute BCASL in background thread for better responsiveness",
            )
        )

        self.ws_browse_btn.setText(
            self.language_manager.get("browse_button", "Browse...")
        )
        self.lang_label.setText(
            self.language_manager.get("language_label", "Language:")
        )
        self.theme_label.setText(self.language_manager.get("theme_label", "Theme:"))

        self.btn_config.setText(
            self.language_manager.get("configure_plugins", "⚙️ Configure Plugins")
        )
        self.btn_config.setToolTip(
            self.language_manager.get(
                "configure_plugins_tooltip", "Open plugin configuration dialog"
            )
        )
        self.btn_run.setText(self.language_manager.get("run_bcasl", "▶️ Run BCASL"))
        self.btn_run.setToolTip(
            self.language_manager.get(
                "run_bcasl_tooltip", "Execute BCASL pre-compilation actions"
            )
        )
        self.btn_clear.setText(self.language_manager.get("clear_log", "🗑️ Clear Log"))
        self.btn_clear.setToolTip(
            self.language_manager.get("clear_log_tooltip", "Clear the execution log")
        )
        self.btn_exit.setText(self.language_manager.get("exit_button", "Exit"))
        self.btn_exit.setToolTip(
            self.language_manager.get("exit_tooltip", "Close the application")
        )

        # Update status bar if showing "Ready"
        status_text = self.statusBar().currentMessage()
        if status_text in ["Ready", "Prêt"]:
            self.statusBar().showMessage(self.language_manager.get("ready", "Ready"))

    def _select_workspace(self):
        """Select workspace directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            self.language_manager.get("select_workspace", "Select Workspace Directory"),
            self.workspace_dir or os.path.expanduser("~"),
        )
        if folder:
            self.workspace_dir = folder
            self.ws_display.setText(folder)
            self._load_config_info()
            self.log.append(
                self.language_manager.format("workspace_selected", path=folder) + "\n"
            )

    def _load_config_info(self):
        """Load and display configuration info."""
        if not self.workspace_dir:
            self.config_info.setText(
                self.language_manager.get("no_workspace", "No workspace selected")
            )
            return

        try:
            cfg = _load_workspace_config(Path(self.workspace_dir))
            plugins = cfg.get("plugins", {})
            enabled_count = sum(
                1
                for v in plugins.values()
                if isinstance(v, dict)
                and v.get("enabled", True)
                or isinstance(v, bool)
                and v
            )
            total_count = len(plugins)
            file_patterns = cfg.get("file_patterns", [])
            exclude_patterns = cfg.get("exclude_patterns", [])

            info = (
                f"{self.language_manager.format('plugins_enabled', enabled=enabled_count, total=total_count)} | "
                f"{self.language_manager.format('file_patterns', count=len(file_patterns))} | "
                f"{self.language_manager.format('exclude_patterns', count=len(exclude_patterns))}"
            )
            self.config_info.setText(info)
        except Exception as e:
            self.config_info.setText(
                self.language_manager.format("error_loading_config", error=str(e))
            )

    def _open_config_dialog(self):
        """Open plugin configuration dialog."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                self.language_manager.get("warning", "Warning"),
                self.language_manager.get(
                    "select_workspace_first", "Please select a workspace first."
                ),
            )
            return
        try:
            open_bc_loader_dialog(self)
            self._load_config_info()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.language_manager.get("error", "Error"),
                self.language_manager.format("config_dialog_error", error=str(e)),
            )

    def _run_bcasl(self):
        """Run BCASL."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                self.language_manager.get("warning", "Warning"),
                self.language_manager.get(
                    "select_workspace_first", "Please select a workspace first."
                ),
            )
            return

        if self._is_running:
            QMessageBox.information(
                self,
                "Information",
                self.language_manager.get(
                    "bcasl_running",
                    "BCASL is already running. Please wait for it to complete.",
                ),
            )
            return

        self._is_running = True
        self.btn_run.setEnabled(False)
        self.btn_config.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(0)  # Indeterminate progress
        self.statusBar().showMessage(
            self.language_manager.get("running", "Running BCASL...")
        )
        self.log.append("\n" + "=" * 60)
        self.log.append(
            self.language_manager.get(
                "starting_execution", "Starting BCASL execution..."
            )
        )
        self.log.append("=" * 60 + "\n")

        def on_done(report):
            """Callback when BCASL completes."""
            self._is_running = False
            self.btn_run.setEnabled(True)
            self.btn_config.setEnabled(True)
            self.progress.setVisible(False)

            if report is None:
                self.log.append(
                    "\n"
                    + self.language_manager.get(
                        "execution_failed",
                        "❌ BCASL execution failed or was cancelled.",
                    )
                    + "\n"
                )
                self.statusBar().showMessage(
                    self.language_manager.get("failed", "Failed")
                )
            else:
                try:
                    self.log.append("\n" + "=" * 60)
                    self.log.append(
                        self.language_manager.get(
                            "execution_report", "BCASL Execution Report:"
                        )
                    )
                    self.log.append("=" * 60 + "\n")
                    for item in report:
                        if item.success:
                            status = self.language_manager.get("plugin_ok", "✅ OK")
                        else:
                            status = self.language_manager.format(
                                "plugin_fail", error=item.error
                            )
                        self.log.append(
                            f"  {item.plugin_id}: {status} ({item.duration_ms:.1f}ms)\n"
                        )
                    self.log.append("\n" + report.summary() + "\n")
                    self.statusBar().showMessage(
                        self.language_manager.get("completed", "Completed")
                        if report.ok
                        else self.language_manager.get(
                            "completed_errors", "Completed with errors"
                        )
                    )
                except Exception as e:
                    self.log.append(
                        "\n"
                        + self.language_manager.format(
                            "error_displaying_report", error=str(e)
                        )
                        + "\n"
                    )
                    self.statusBar().showMessage(
                        self.language_manager.get("completed", "Completed")
                    )

        try:
            if self.chk_async.isChecked():
                run_pre_compile_async(self, on_done)
            else:
                report = run_pre_compile(self)
                on_done(report)
        except Exception as e:
            self.log.append(
                "\n"
                + self.language_manager.format("error_running_bcasl", error=str(e))
                + "\n"
            )
            self._is_running = False
            self.btn_run.setEnabled(True)
            self.btn_config.setEnabled(True)
            self.progress.setVisible(False)
            self.statusBar().showMessage(self.language_manager.get("error", "Error"))

    def closeEvent(self, event):
        """Handle window close."""
        try:
            ensure_bcasl_thread_stopped(self)
        except Exception:
            pass
        event.accept()


def main():
    """Main entry point for standalone BCASL application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="BCASL Standalone - Before Compilation Actions System Loader"
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        help="Path to workspace directory (optional)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = BcaslStandaloneApp(workspace_dir=args.workspace)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
