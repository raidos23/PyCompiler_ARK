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
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from PySide6.QtCore import Qt, QSize, QTimer, QProcess, QThread
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QComboBox,
    QPushButton,
    QLabel,
    QTextEdit,
    QProgressBar,
    QFileDialog,
    QStatusBar,
    QMessageBox,
    QLineEdit,
    QGridLayout,
    QFrame,
    QSplitter,
    QTabWidget,
    QScrollArea,
    QSizePolicy,
)
from PySide6.QtGui import QIcon, QAction, QFont, QPixmap

from Core.engines_loader import (
    available_engines,
    get_engine,
    create as create_engine,
)
from Core.engines_loader.validator import check_engine_compatibility
from Core.allversion import get_core_version, get_engine_sdk_version
import Core.engines_loader as engines_loader


class CompilationThread(QThread):
    """Thread pour exécuter la compilation sans bloquer l'UI."""

    output_ready = None  # Signal(str)
    error_ready = None   # Signal(str)
    finished = None      # Signal(int) - code de retour

    def __init__(self, program, args, env, working_dir=None):
        super().__init__()
        self.program = program
        self.args = args
        self.env = env
        self.working_dir = working_dir

    def run(self):
        """Exécute le processus de compilation."""
        try:
            proc = subprocess.Popen(
                [self.program] + self.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=self.env,
                cwd=self.working_dir,
                bufsize=1,
            )

            # Lire la sortie en temps réel
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line and self.output_ready:
                    self.output_ready.emit(line.rstrip())

            # Lire stderr à la fin
            stderr = proc.stderr.read()
            if stderr and self.error_ready:
                for line in stderr.strip().split("\n"):
                    if line:
                        self.error_ready.emit(line.rstrip())

            # Signaler la fin
            return_code = proc.wait()
            if self.finished:
                self.finished.emit(return_code)

        except Exception as e:
            if self.error_ready:
                self.error_ready.emit(f"Error: {str(e)}")
            if self.finished:
                self.finished.emit(1)


class EnginesStandaloneGui(QMainWindow):
    """
    Application autonome GUI pour gérer et exécuter les moteurs de compilation.

    Cette classe fournit une interface utilisateur complète pour:
    - Lister les moteurs disponibles
    - Sélectionner et configurer un moteur
    - Compiler des fichiers avec le moteur choisi
    - Afficher les résultats et logs
    """

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        language: str = "en",
        theme: str = "dark",
    ):
        """
        Initialise l'application standalone engines GUI.

        Args:
            workspace_dir: Chemin du workspace (optionnel)
            language: Code de langue ('en' ou 'fr')
            theme: Nom du thème ('light' ou 'dark')
        """
        super().__init__()

        self.workspace_dir = workspace_dir
        self.language = language
        self.theme = theme
        self.selected_engine_id = None
        self.selected_file = None

        # Configuration de la fenêtre
        self.setWindowTitle("Engines Standalone - PyCompiler ARK++")
        self.resize(1400, 850)
        self.setMinimumSize(1100, 700)
        self.showMaximized()

        # Chargement des icônes
        self._load_icons()

        # Configuration de l'interface
        self._setup_ui()
        self._apply_theme(theme)
        self._apply_language(language)

        # Chargement des moteurs
        self._refresh_engines()

        # Centre la fenêtre sur l'écran
        self._center_window()

    def _load_icons(self):
        """Charge les icônes de l'application."""
        self.icons = {
            "compile": self._create_icon("▶", "#4caf50"),
            "browse": self._create_icon("📁", "#2196f3"),
            "refresh": self._create_icon("🔄", "#ff9800"),
            "clear": self._create_icon("🗑️", "#f44336"),
            "check": self._create_icon("✓", "#4caf50"),
            "warning": self._create_icon("⚠️", "#ff9800"),
            "error": self._create_icon("✗", "#f44336"),
        }

    def _create_icon(self, text: str, color: str = "#000000") -> QIcon:
        """Crée une icône simple à partir de texte et couleur."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal avec marge réduite
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # === En-tête ===
        header_layout = QHBoxLayout()

        title_label = QLabel("Engines Standalone")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #4da6ff;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Version info
        version_label = QLabel(
            f"Core: {get_core_version()} | SDK: {get_engine_sdk_version()}"
        )
        version_label.setStyleSheet("color: #888; font-size: 11px;")
        header_layout.addWidget(version_label)

        main_layout.addLayout(header_layout)

        # === Séparateur fin ===
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #404040; max-height: 2px;")
        main_layout.addWidget(separator)

        # === Splitter principal ===
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(main_splitter)

        # === Panneau supérieur avec splitter horizontal ===
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # === Section Configuration (gauche) ===
        config_container = QWidget()
        config_layout = QGridLayout(config_container)
        config_layout.setSpacing(10)
        config_layout.setContentsMargins(3, 3, 3, 3)
        config_layout.setColumnStretch(0, 1)
        config_layout.setColumnStretch(1, 1)
        config_layout.setRowStretch(0, 1)
        config_layout.setRowStretch(1, 1)

        # Moteur (top-left)
        engine_group = QGroupBox("Engine Configuration")
        engine_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        engine_layout = QVBoxLayout()
        engine_layout.setSpacing(3)

        self.compiler_tabs = QTabWidget()
        self.compiler_tabs.setDocumentMode(False)
        self.compiler_tabs.setTabsClosable(False)
        self.compiler_tabs.setMovable(False)
        self.compiler_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        engine_layout.addWidget(self.compiler_tabs)

        compat_btn = QPushButton("Check Compatibility")
        compat_btn.setMinimumHeight(28)
        compat_btn.clicked.connect(self._check_compatibility)
        engine_layout.addWidget(compat_btn)

        self.compat_status_label = QLabel("")
        self.compat_status_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        engine_layout.addWidget(self.compat_status_label)

        engine_group.setLayout(engine_layout)
        config_layout.addWidget(engine_group, 0, 0)

        # Fichier (top-right)
        file_group = QGroupBox("File / Project Configuration")
        file_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        file_layout = QVBoxLayout()
        file_layout.setSpacing(5)

        file_label = QLabel("File to compile:")
        file_layout.addWidget(file_label)

        file_input_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a Python file to compile...")
        self.file_path_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_path_edit.setMinimumHeight(30)
        file_input_layout.addWidget(self.file_path_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.setMinimumHeight(30)
        browse_btn.setMinimumWidth(80)
        browse_btn.clicked.connect(self._browse_file)
        file_input_layout.addWidget(browse_btn)

        file_layout.addLayout(file_input_layout)
        file_group.setLayout(file_layout)
        config_layout.addWidget(file_group, 0, 1)

        # Workspace
        workspace_group = QGroupBox("Workspace")
        workspace_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        workspace_layout = QGridLayout()
        workspace_layout.setSpacing(5)
        workspace_layout.setColumnStretch(1, 1)

        workspace_label = QLabel("Workspace:")
        workspace_layout.addWidget(workspace_label, 0, 0)

        self.workspace_edit = QLineEdit()
        if self.workspace_dir:
            self.workspace_edit.setText(self.workspace_dir)
        self.workspace_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.workspace_edit.setMinimumHeight(28)
        workspace_layout.addWidget(self.workspace_edit, 0, 1)

        workspace_browse_btn = QPushButton("Browse")
        workspace_browse_btn.setMinimumHeight(28)
        workspace_browse_btn.setMinimumWidth(70)
        workspace_browse_btn.clicked.connect(self._browse_workspace)
        workspace_layout.addWidget(workspace_browse_btn, 0, 2)

        workspace_group.setLayout(workspace_layout)
        config_layout.addWidget(workspace_group)

        # Actions (bottom-right)
        actions_group = QGroupBox("Actions")
        actions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(8)

        self.compile_btn = QPushButton("Compile")
        self.compile_btn.setMinimumHeight(32)
        self.compile_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """
        )
        self.compile_btn.clicked.connect(self._run_compilation)
        actions_layout.addWidget(self.compile_btn)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setMinimumHeight(32)
        dry_run_btn.clicked.connect(self._dry_run)
        button_row.addWidget(dry_run_btn)

        refresh_btn = QPushButton("Refresh Engines")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.clicked.connect(self._refresh_engines)
        button_row.addWidget(refresh_btn)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.setMinimumHeight(32)
        clear_log_btn.clicked.connect(self._clear_log)
        button_row.addWidget(clear_log_btn)

        actions_layout.addLayout(button_row)
        actions_group.setLayout(actions_layout)
        config_layout.addWidget(actions_group, 1, 1)

        top_splitter.addWidget(config_container)

        # === Section Log (droite avec plus d'espace) ===
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setSpacing(5)
        log_layout.setContentsMargins(3, 3, 3, 3)

        log_group = QGroupBox("Compilation Log")
        log_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout_inner = QVBoxLayout()
        log_layout_inner.setSpacing(3)

        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setReadOnly(True)
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_text.setStyleSheet(
            """
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
        """
        )
        log_layout_inner.addWidget(self.log_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(14)
        log_layout_inner.addWidget(self.progress_bar)

        log_group.setLayout(log_layout_inner)
        log_layout.addWidget(log_group)

        top_splitter.addWidget(log_container)

        # Définir les proportions (30% config, 70% log)
        top_splitter.setSizes([400, 800])

        main_splitter.addWidget(top_splitter)

        # === Barre de statut ===
        self.statusBar = QStatusBar()
        self.statusBar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.statusBar.setMinimumHeight(20)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Définir les proportions du splitter vertical
        main_splitter.setSizes([600, 200])

    def _center_window(self):
        """Centre la fenêtre sur l'écran."""
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def _apply_theme(self, theme_name: str):
        """Applique le thème visuel."""
        if theme_name == "dark":
            self.setStyleSheet(
                """
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    font-size: 12px;
                    border: 1px solid #404040;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 8px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 12px;
                }
                QComboBox, QLineEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #404040;
                    border-radius: 4px;
                    padding: 6px;
                    font-size: 12px;
                }
                QComboBox:focus, QLineEdit:focus {
                    border-color: #4da6ff;
                }
                QPushButton {
                    background-color: #3d3d3d;
                    color: #ffffff;
                    border: 1px solid #505050;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
                QTabWidget::pane {
                    border: 1px solid #404040;
                    background-color: #252525;
                }
                QTabBar::tab {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    padding: 8px 12px;
                    border: 1px solid #404040;
                    border-bottom: none;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background-color: #3d3d3d;
                    border-bottom: 2px solid #4da6ff;
                }
                QStatusBar {
                    background-color: #252525;
                    color: #aaaaaa;
                    font-size: 11px;
                }
            """
            )
        else:  # light theme
            self.setStyleSheet(
                """
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                    color: #000000;
                }
                QGroupBox {
                    font-weight: bold;
                    font-size: 12px;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 8px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 8px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #000000;
                    font-size: 12px;
                }
                QComboBox, QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 6px;
                    font-size: 12px;
                }
                QComboBox:focus, QLineEdit:focus {
                    border-color: #0066cc;
                }
                QPushButton {
                    background-color: #e0e0e0;
                    color: #000000;
                    border: 1px solid #bbbbbb;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """
            )

    def _apply_language(self, lang_code: str):
        """Applique la langue de l'interface."""
        self.language = lang_code

        # Traductions
        translations = {
            "en": {
                "engine_config": "Engine Configuration",
                "file_config": "File / Project Configuration",
                "workspace": "Workspace",
                "file_to_compile": "File to compile:",
                "workspace_label": "Workspace:",
                "browse": "Browse",
                "check_compat": "Check Compatibility",
                "compile": "Compile",
                "dry_run": "Dry Run",
                "refresh": "Refresh Engines",
                "clear_log": "Clear Log",
                "actions": "Actions",
                "version": "Version:",
                "required_core": "Required Core:",
                "log": "Compilation Log",
                "ready": "Ready",
                "select_engine": "Please select an engine first",
                "select_file": "Please select a file first",
                "running": "Running compilation...",
                "completed": "Compilation completed!",
                "failed": "Compilation failed!",
                "compatible": "✓ Engine is compatible",
                "not_compatible": "✗ Engine has compatibility issues",
            },
            "fr": {
                "engine_config": "Configuration du Moteur",
                "file_config": "Configuration Fichier / Projet",
                "workspace": "Workspace",
                "file_to_compile": "Fichier à compiler :",
                "workspace_label": "Workspace :",
                "browse": "Parcourir",
                "check_compat": "Vérifier Compatibilité",
                "compile": "Compiler",
                "dry_run": "Simulation",
                "refresh": "Rafraîchir",
                "clear_log": "Effacer Log",
                "actions": "Actions",
                "version": "Version :",
                "required_core": "Core Requis :",
                "log": "Log de Compilation",
                "ready": "Prêt",
                "select_engine": "Veuillez sélectionner un moteur",
                "select_file": "Veuillez sélectionner un fichier",
                "running": "Compilation en cours...",
                "completed": "Compilation terminée !",
                "failed": "Échec de la compilation !",
                "compatible": "✓ Moteur compatible",
                "not_compatible": "✗ Problèmes de compatibilité",
            },
        }

        tr = translations.get(lang_code, translations["en"])

        # Mise à jour des labels
        for child in self.findChildren(QGroupBox):
            title = child.title().lower()
            if "engine" in title or "moteur" in title:
                child.setTitle(tr["engine_config"])
            elif "file" in title or "fichier" in title:
                child.setTitle(tr["file_config"])
            elif "workspace" in title:
                child.setTitle(tr["workspace"])
            elif "action" in title:
                child.setTitle(tr["actions"])
            elif "log" in title:
                child.setTitle(tr["log"])

    def _refresh_engines(self):
        """Rafraîchit la liste des moteurs disponibles et crée leurs onglets."""
        # Nettoyer les onglets existants
        self.compiler_tabs.clear()
        self.engines_info = {}

        engine_ids = available_engines()

        if not engine_ids:
            # Pas de moteurs : afficher un message
            no_engine_widget = QWidget()
            no_engine_layout = QVBoxLayout()
            no_engine_label = QLabel("No engines available.\nPlease check ENGINES folder.")
            no_engine_label.setStyleSheet("color: #888; font-size: 14px;")
            no_engine_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_engine_layout.addWidget(no_engine_label)
            no_engine_widget.setLayout(no_engine_layout)
            self.compiler_tabs.addTab(no_engine_widget, "No Engines")
            self._log("No engines available. Please check ENGINES folder.")
            self.statusBar.showMessage("No engines available")
            return

        # Utiliser le mécanisme standard de bind_tabs comme dans l'application principale
        try:
            engines_loader.registry.bind_tabs(self)
            self._log(f"Loaded {len(engine_ids)} engine(s)")
            self.statusBar.showMessage(f"Ready - {len(engine_ids)} engines loaded")
        except Exception as e:
            self._log(f"Error binding engine tabs: {e}")
            # Fallback : créer les onglets manuellement
            for eid in engine_ids:
                try:
                    engine_cls = get_engine(eid)
                    if engine_cls:
                        name = getattr(engine_cls, "name", eid)
                        version = getattr(engine_cls, "version", "1.0.0")
                        required_core = getattr(
                            engine_cls, "required_core_version", "1.0.0"
                        )

                        self.engines_info[eid] = {
                            "name": name,
                            "version": version,
                            "required_core": required_core,
                            "class": engine_cls,
                        }

                        # Essayer de créer l'onglet via create_tab
                        create_tab = getattr(engine_cls, "create_tab", None)
                        if callable(create_tab):
                            result = create_tab(self)
                            if result:
                                widget, label = result
                                self.compiler_tabs.addTab(widget, label)
                        else:
                            # Pas de create_tab : créer un onglet par défaut
                            default_widget = self._create_default_engine_widget(
                                eid, name, version, required_core
                            )
                            self.compiler_tabs.addTab(default_widget, name)

                except Exception as e:
                    self._log(f"Error loading engine {eid}: {e}")

    def _create_default_engine_widget(
        self, engine_id: str, name: str, version: str, required_core: str
    ) -> QWidget:
        """Crée un widget par défaut pour un moteur sans create_tab."""
        widget = QWidget()
        layout = QGridLayout()
        layout.setSpacing(8)

        layout.addWidget(QLabel(f"<b>Engine:</b> {name} ({engine_id})"), 0, 0, 1, 2)
        layout.addWidget(QLabel(f"<b>Version:</b> {version}"), 1, 0)
        layout.addWidget(QLabel(f"<b>Required Core:</b> {required_core}"), 1, 1)

        # Info label
        info_label = QLabel(
            "This engine uses default configuration.\n"
            "Configure options in the main application for full functionality."
        )
        info_label.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label, 2, 0, 1, 2)

        widget.setLayout(layout)
        return widget

    def _check_compatibility(self):
        """Vérifie la compatibilité du moteur de l'onglet courant."""
        # Récupérer l'ID du moteur depuis l'onglet courant
        current_index = self.compiler_tabs.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, "Warning", "No engine tab selected")
            return

        try:
            engine_id = engines_loader.registry.get_engine_for_tab(current_index)
            if not engine_id:
                # Essayer le fallback avec engines_info
                if self.engines_info:
                    engine_id = list(self.engines_info.keys())[current_index]
                else:
                    QMessageBox.warning(self, "Warning", "No engine available")
                    return
        except Exception:
            engine_id = None

        if not engine_id:
            QMessageBox.warning(self, "Warning", "No engine available")
            return

        try:
            # Récupérer la classe du moteur
            engine_cls = None
            if engine_id in self.engines_info:
                engine_cls = self.engines_info[engine_id].get("class")
            if not engine_cls:
                engine_cls = get_engine(engine_id)

            if not engine_cls:
                QMessageBox.warning(
                    self, "Warning", f"Engine class not found: {engine_id}"
                )
                return

            result = check_engine_compatibility(
                engine_cls,
                get_core_version(),
                get_engine_sdk_version(),
            )

            if result.is_compatible:
                self.compat_status_label.setText("✓ Compatible")
                self.compat_status_label.setStyleSheet(
                    "color: #4caf50; font-weight: bold; font-size: 11px;"
                )
                self._log(f"Engine {engine_id} is compatible")
            else:
                self.compat_status_label.setText("✗ Not compatible")
                self.compat_status_label.setStyleSheet(
                    "color: #f44336; font-weight: bold; font-size: 11px;"
                )
                self._log(f"Engine {engine_id} compatibility issues:")
                for req in result.missing_requirements:
                    self._log(f"  - {req}")
                if result.error_message:
                    self._log(f"  Error: {result.error_message}")

        except Exception as e:
            self._log(f"Error checking compatibility: {e}")

    def _browse_file(self):
        """Ouvre une boîte de dialogue pour sélectionner un fichier."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python file to compile",
            self.workspace_edit.text() or ".",
            "Python files (*.py);;All files (*)",
        )

        if file_path:
            self.file_path_edit.setText(file_path)
            self.selected_file = file_path

    def _browse_workspace(self):
        """Ouvre une boîte de dialogue pour sélectionner un workspace."""
        workspace_dir = QFileDialog.getExistingDirectory(
            self, "Select workspace directory", self.workspace_edit.text() or "."
        )

        if workspace_dir:
            self.workspace_edit.setText(workspace_dir)
            self.workspace_dir = workspace_dir

    def _run_compilation(self):
        """Exécute la compilation avec le moteur de l'onglet courant."""
        # Récupérer l'ID du moteur depuis l'onglet courant
        current_index = self.compiler_tabs.currentIndex()
        if current_index < 0:
            QMessageBox.warning(
                self,
                "Warning",
                (
                    "Please select an engine tab first"
                    if self.language == "en"
                    else "Veuillez sélectionner un onglet de moteur d'abord"
                ),
            )
            return

        try:
            engine_id = engines_loader.registry.get_engine_for_tab(current_index)
            if not engine_id:
                # Fallback avec engines_info
                if self.engines_info:
                    engine_id = list(self.engines_info.keys())[current_index]
                else:
                    QMessageBox.warning(
                        self,
                        "Warning",
                        (
                            "No engine available"
                            if self.language == "en"
                            else "Aucun moteur disponible"
                        ),
                    )
                    return
        except Exception:
            engine_id = None

        if not engine_id:
            QMessageBox.warning(
                self,
                "Warning",
                (
                    "No engine available"
                    if self.language == "en"
                    else "Aucun moteur disponible"
                ),
            )
            return

        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(
                self,
                "Warning",
                (
                    "Please select a file to compile"
                    if self.language == "en"
                    else "Veuillez sélectionner un fichier à compiler"
                ),
            )
            return

        # Mise à jour du workspace
        self.workspace_dir = self.workspace_edit.text()

        # Afficher le statut
        self.statusBar.showMessage(
            "Running compilation..."
            if self.language == "en"
            else "Compilation en cours..."
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.compile_btn.setEnabled(False)

        # Logger le début
        self._log("=" * 50)
        self._log(f"Starting compilation with {engine_id}")
        self._log(f"File: {file_path}")
        if self.workspace_dir:
            self._log(f"Workspace: {self.workspace_dir}")
        self._log("=" * 50)

        try:
            # Get the engine instance from registry (has the tab configuration)
            engine = engines_loader.registry.get_instance(engine_id)

            # If no stored instance, create one (fallback)
            if not engine:
                engine = create_engine(engine_id)

            # Préparer les arguments avec le GUI pour accéder aux options
            result = engine.program_and_args(self, file_path)

            if result:
                program, args = result
                cmd = [program] + args
                cmd_str = " ".join(cmd)

                self._log(f"Command: {cmd_str}")

                # Préparer l'environnement
                env = os.environ.copy()
                if self.workspace_dir:
                    env["ARK_WORKSPACE"] = self.workspace_dir

                # Exécuter la commande dans un thread séparé
                self._log("Executing...")

                # Timer pour mettre à jour le statut
                self._start_time = datetime.now()

                # Créer et configurer le thread
                working_dir = os.path.dirname(file_path) if file_path else None
                self.compilation_thread = CompilationThread(program, args, env, working_dir)
                self.compilation_thread.output_ready.connect(self._log)
                self.compilation_thread.error_ready.connect(self._on_compilation_error)
                self.compilation_thread.finished.connect(self._on_compilation_finished)
                self.compilation_thread.start()

            else:
                self._log(
                    "Failed to build command"
                    if self.language == "en"
                    else "Échec de la construction de la commande"
                )

        except Exception as e:
            self._log(f"Error: {str(e)}")

    def _on_compilation_error(self, message):
        """Affiche les erreurs de compilation."""
        self._log(f"STDERR: {message}")

    def _on_compilation_finished(self, return_code):
        """Appelé lorsque la compilation est terminée."""
        self._log("=" * 50)

        end_time = datetime.now()
        duration = (end_time - self._start_time).total_seconds()

        if return_code == 0:
            self._log(
                "Compilation successful!"
                if self.language == "en"
                else "Compilation réussie !"
            )
            self.statusBar.showMessage(
                "Compilation successful!"
                if self.language == "en"
                else "Compilation terminée !"
            )
        else:
            self._log(
                f"Compilation failed with code {return_code}"
                if self.language == "en"
                else f"Échec de la compilation (code {return_code})"
            )
            self.statusBar.showMessage(
                "Compilation failed"
                if self.language == "en"
                else "Échec de la compilation"
            )

        self._log(f"Duration: {duration:.2f}s")
        self._log("=" * 50)

        self.progress_bar.setVisible(False)
        self.compile_btn.setEnabled(True)

    def _dry_run(self):
        """Affiche la commande sans l'exécuter en utilisant l'onglet courant."""
        # Récupérer l'ID du moteur depuis l'onglet courant
        current_index = self.compiler_tabs.currentIndex()
        if current_index < 0:
            QMessageBox.warning(self, "Warning", "Please select an engine tab first")
            return

        try:
            engine_id = engines_loader.registry.get_engine_for_tab(current_index)
            if not engine_id:
                # Fallback avec engines_info
                if self.engines_info:
                    engine_id = list(self.engines_info.keys())[current_index]
                else:
                    QMessageBox.warning(self, "Warning", "No engine available")
                    return
        except Exception:
            engine_id = None

        if not engine_id:
            QMessageBox.warning(self, "Warning", "No engine available")
            return

        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please select a file to compile")
            return

        try:
            # Get the engine instance from registry (has the tab configuration)
            engine = engines_loader.registry.get_instance(engine_id)

            # If no stored instance, create one (fallback)
            if not engine:
                engine = create_engine(engine_id)

            result = engine.program_and_args(self, file_path)

            if result:
                program, args = result
                cmd = [program] + args
                cmd_str = " ".join(cmd)

                self._log(f"[DRY RUN] Command: {cmd_str}")
                QMessageBox.information(self, "Dry Run", f"Command:\n\n{cmd_str}")
            else:
                self._log("Failed to build command")

        except Exception as e:
            self._log(f"Error: {str(e)}")

    def _clear_log(self):
        """Efface le log."""
        self.log_text.clear()

    def _log(self, message: str):
        """Ajoute un message au log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        # Défiler automatiquement vers le bas
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


def launch_engines_gui(
    workspace_dir: Optional[str] = None, language: str = "en", theme: str = "dark"
) -> int:
    """Lance l'application Engines Standalone GUI.

    Args:
        workspace_dir: Chemin du workspace (optionnel)
        language: Code de langue ('en' ou 'fr')
        theme: Nom du thème ('light' ou 'dark')

    Returns:
        Code de retour de l'application
    """
    app = QApplication(sys.argv)
    app.setApplicationName("PyCompiler ARK++ Engines")
    app.setOrganizationName("PyCompiler")

    window = EnginesStandaloneGui(
        workspace_dir=workspace_dir, language=language, theme=theme
    )
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_engines_gui())

