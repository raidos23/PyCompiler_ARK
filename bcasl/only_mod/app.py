# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Ague Samuel Amen
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
        QMainWindow,
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
                    with open(theme_file, 'r', encoding='utf-8') as f:
                        theme_data = json.load(f)
                        theme_id = theme_data.get('id', theme_file.stem)
                        self.THEMES[theme_id] = {
                            'name': theme_data.get('name', theme_id),
                            'description': theme_data.get('description', ''),
                            'colors': theme_data.get('colors', {})
                        }
                except Exception as e:
                    logger.error(f"Failed to load theme from {theme_file}: {e}")
        except Exception as e:
            logger.error(f"Error loading themes: {e}")
            self._load_default_themes()
        
        # Set default theme
        if self.THEMES:
            self.current_theme = list(self.THEMES.keys())[0]
            self.colors = self.THEMES[self.current_theme]['colors'].copy()
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
                }
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
                }
            },
        }
        self.current_theme = "light"
        self.colors = self.THEMES["light"]["colors"].copy()
    
    def set_theme(self, theme_name: str) -> bool:
        """Set the current theme."""
        if theme_name not in self.THEMES:
            return False
        self.current_theme = theme_name
        self.colors = self.THEMES[theme_name]['colors'].copy()
        return True
    
    def get_theme_names(self) -> list:
        """Get list of available theme names."""
        return list(self.THEMES.keys())
    
    def get_theme_display_names(self) -> list:
        """Get list of available theme display names."""
        return [self.THEMES[tid]['name'] for tid in self.get_theme_names()]
    
    def get_stylesheet(self) -> str:
        """Generate stylesheet for current theme."""
        return f"""
            QMainWindow {{
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
            color = color.lstrip('#')
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            rgb = tuple(min(255, int(c + (255 - c) * percent / 100)) for c in rgb)
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except:
            return color
    
    @staticmethod
    def _darken(color: str, percent: int) -> str:
        """Darken a hex color."""
        try:
            color = color.lstrip('#')
            rgb = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            rgb = tuple(int(c * (100 - percent) / 100) for c in rgb)
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        except:
            return color


class BcaslStandaloneApp(QMainWindow):
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
        
        # Initialize theme manager
        self.theme_manager = ThemeManager()
        self._load_theme_preference()

        self.setWindowTitle("BCASL Standalone - Before Compilation Actions System Loader")
        self.setGeometry(100, 100, 1100, 800)
        self.setMinimumSize(900, 650)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # Workspace selection group
        ws_group = QGroupBox("Workspace Configuration")
        ws_layout = QHBoxLayout(ws_group)
        ws_label = QLabel("Workspace:")
        ws_label.setMinimumWidth(80)
        self.ws_display = QLabel(workspace_dir or "No workspace selected")
        self.ws_display.setToolTip("Currently selected workspace directory")
        ws_btn = QPushButton("Browse...")
        ws_btn.setMaximumWidth(100)
        ws_btn.clicked.connect(self._select_workspace)
        ws_layout.addWidget(ws_label)
        ws_layout.addWidget(self.ws_display)
        ws_layout.addStretch()
        ws_layout.addWidget(ws_btn)
        layout.addWidget(ws_group)

        # Config info
        self.config_info = QLabel("No configuration loaded")
        self.config_info.setToolTip("Configuration summary: enabled plugins, file patterns, etc.")
        layout.addWidget(self.config_info)

        # Log output
        log_label = QLabel("Execution Log:")
        log_label_font = QFont()
        log_label_font.setBold(True)
        log_label.setFont(log_label_font)
        layout.addWidget(log_label)
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
        self.chk_async = QCheckBox("Run asynchronously")
        self.chk_async.setChecked(True)
        self.chk_async.setToolTip("Execute BCASL in background thread for better responsiveness")
        options_layout.addWidget(self.chk_async)
        
        # Theme selector
        theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(self.theme_manager.THEMES.keys()))
        self.theme_combo.setCurrentText(self.theme_manager.current_theme)
        self.theme_combo.currentTextChanged.connect(self._on_theme_changed)
        self.theme_combo.setMaximumWidth(120)
        options_layout.addStretch()
        options_layout.addWidget(theme_label)
        options_layout.addWidget(self.theme_combo)
        layout.addLayout(options_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_config = QPushButton("⚙️ Configure Plugins")
        self.btn_config.setToolTip("Open plugin configuration dialog")
        self.btn_config.clicked.connect(self._open_config_dialog)
        self.btn_run = QPushButton("▶️ Run BCASL")
        self.btn_run.setToolTip("Execute BCASL pre-compilation actions")
        self.btn_run.clicked.connect(self._run_bcasl)
        self.btn_clear = QPushButton("🗑️ Clear Log")
        self.btn_clear.setToolTip("Clear the execution log")
        self.btn_clear.clicked.connect(self.log.clear)
        self.btn_exit = QPushButton("Exit")
        self.btn_exit.setToolTip("Close the application")
        self.btn_exit.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_config)
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_exit)
        layout.addLayout(btn_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Apply theme
        self._apply_theme()

        # Load initial config if workspace provided
        if workspace_dir:
            self._load_config_info()

    def _load_theme_preference(self):
        """Load theme preference from config file."""
        try:
            config_file = Path.home() / ".bcasl_theme"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    theme = data.get('theme', 'light')
                    if theme in self.theme_manager.THEMES:
                        self.theme_manager.set_theme(theme)
        except Exception:
            pass

    def _save_theme_preference(self):
        """Save theme preference to config file."""
        try:
            config_file = Path.home() / ".bcasl_theme"
            with open(config_file, 'w') as f:
                json.dump({'theme': self.theme_manager.current_theme}, f)
        except Exception:
            pass

    def _on_theme_changed(self, theme_name: str):
        """Handle theme change."""
        if self.theme_manager.set_theme(theme_name):
            self._apply_theme()
            self._save_theme_preference()

    def _apply_theme(self):
        """Apply current theme to the application."""
        stylesheet = self.theme_manager.get_stylesheet()
        self.setStyleSheet(stylesheet)

    def _select_workspace(self):
        """Select workspace directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Workspace Directory",
            self.workspace_dir or os.path.expanduser("~"),
        )
        if folder:
            self.workspace_dir = folder
            self.ws_display.setText(folder)
            self._load_config_info()
            self.log.append(f"✅ Workspace selected: {folder}\n")

    def _load_config_info(self):
        """Load and display configuration info."""
        if not self.workspace_dir:
            self.config_info.setText("No workspace selected")
            return

        try:
            cfg = _load_workspace_config(Path(self.workspace_dir))
            plugins = cfg.get("plugins", {})
            enabled_count = sum(
                1
                for v in plugins.values()
                if isinstance(v, dict) and v.get("enabled", True)
                or isinstance(v, bool) and v
            )
            total_count = len(plugins)
            file_patterns = cfg.get("file_patterns", [])
            exclude_patterns = cfg.get("exclude_patterns", [])

            info = (
                f"Plugins: {enabled_count}/{total_count} enabled | "
                f"File patterns: {len(file_patterns)} | "
                f"Exclude patterns: {len(exclude_patterns)}"
            )
            self.config_info.setText(info)
        except Exception as e:
            self.config_info.setText(f"Error loading config: {e}")

    def _open_config_dialog(self):
        """Open plugin configuration dialog."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a workspace first.",
            )
            return
        try:
            open_bc_loader_dialog(self)
            self._load_config_info()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open config dialog: {e}")

    def _run_bcasl(self):
        """Run BCASL."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a workspace first.",
            )
            return

        if self._is_running:
            QMessageBox.information(
                self,
                "Information",
                "BCASL is already running. Please wait for it to complete.",
            )
            return

        self._is_running = True
        self.btn_run.setEnabled(False)
        self.btn_config.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(0)  # Indeterminate progress
        self.statusBar().showMessage("Running BCASL...")
        self.log.append("\n" + "=" * 60)
        self.log.append("Starting BCASL execution...")
        self.log.append("=" * 60 + "\n")

        def on_done(report):
            """Callback when BCASL completes."""
            self._is_running = False
            self.btn_run.setEnabled(True)
            self.btn_config.setEnabled(True)
            self.progress.setVisible(False)

            if report is None:
                self.log.append("\n❌ BCASL execution failed or was cancelled.\n")
                self.statusBar().showMessage("Failed")
            else:
                try:
                    self.log.append("\n" + "=" * 60)
                    self.log.append("BCASL Execution Report:")
                    self.log.append("=" * 60 + "\n")
                    for item in report:
                        status = "✅ OK" if item.success else f"❌ FAIL: {item.error}"
                        self.log.append(
                            f"  {item.plugin_id}: {status} ({item.duration_ms:.1f}ms)\n"
                        )
                    self.log.append("\n" + report.summary() + "\n")
                    self.statusBar().showMessage(
                        "Completed" if report.ok else "Completed with errors"
                    )
                except Exception as e:
                    self.log.append(f"\n⚠️ Error displaying report: {e}\n")
                    self.statusBar().showMessage("Completed")

        try:
            if self.chk_async.isChecked():
                run_pre_compile_async(self, on_done)
            else:
                report = run_pre_compile(self)
                on_done(report)
        except Exception as e:
            self.log.append(f"\n❌ Error: {e}\n")
            self._is_running = False
            self.btn_run.setEnabled(True)
            self.btn_config.setEnabled(True)
            self.progress.setVisible(False)
            self.statusBar().showMessage("Error")

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
