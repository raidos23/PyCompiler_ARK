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

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QComboBox, QPushButton, QLabel, QTextEdit, QProgressBar,
    QFileDialog, QStatusBar, QMessageBox, QLineEdit, QGridLayout,
    QFrame, QSplitter
)
from PySide6.QtGui import QIcon, QAction, QFont, QPixmap

from Core.engines_loader import (
    available_engines,
    get_engine,
    create as create_engine,
)
from Core.engines_loader.validator import check_engine_compatibility
from Core.allversion import get_core_version, get_engine_sdk_version


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
        self.resize(900, 700)
        
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
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === En-tête ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Engines Standalone")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #4da6ff;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Version info
        version_label = QLabel(f"Core: {get_core_version()} | SDK: {get_engine_sdk_version()}")
        version_label.setStyleSheet("color: #888; font-size: 12px;")
        header_layout.addWidget(version_label)
        
        main_layout.addLayout(header_layout)
        
        # === Séparateur ===
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #404040;")
        main_layout.addWidget(separator)
        
        # === Layout principal avec splitters ===
        content_splitter = QSplitter(Qt.Vertical)
        content_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(content_splitter)
        
        # Panneau de configuration (haut)
        config_widget = QWidget()
        config_layout = QGridLayout(config_widget)
        config_layout.setSpacing(15)
        
        # === Section Moteur ===
        engine_group = QGroupBox("Engine Configuration")
        engine_layout = QGridLayout()
        
        engine_label = QLabel("Engine:")
        engine_layout.addWidget(engine_label, 0, 0)
        
        self.engine_combo = QComboBox()
        self.engine_combo.setMinimumWidth(200)
        self.engine_combo.currentIndexChanged.connect(self._on_engine_changed)
        engine_layout.addWidget(self.engine_combo, 0, 1)
        
        self.engine_version_label = QLabel("Version: -")
        self.engine_version_label.setStyleSheet("color: #888;")
        engine_layout.addWidget(self.engine_version_label, 0, 2)
        
        engine_layout.addWidget(QLabel("Required Core:"), 1, 0)
        self.core_version_label = QLabel("-")
        self.core_version_label.setStyleSheet("color: #888;")
        engine_layout.addWidget(self.core_version_label, 1, 1, 1, 2)
        
        # Bouton vérifier compatibilité
        compat_btn = QPushButton("Check Compatibility")
        compat_btn.clicked.connect(self._check_compatibility)
        engine_layout.addWidget(compat_btn, 2, 0)
        
        self.compat_status_label = QLabel("")
        self.compat_status_label.setStyleSheet("font-weight: bold;")
        engine_layout.addWidget(self.compat_status_label, 2, 1, 1, 2)
        
        engine_group.setLayout(engine_layout)
        config_layout.addWidget(engine_group, 0, 0)
        
        # === Section Fichier ===
        file_group = QGroupBox("File / Project Configuration")
        file_layout = QGridLayout()
        
        file_label = QLabel("File to compile:")
        file_layout.addWidget(file_label, 0, 0)
        
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a Python file to compile...")
        file_layout.addWidget(self.file_path_edit, 0, 1)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn, 0, 2)
        
        file_group.setLayout(file_layout)
        config_layout.addWidget(file_group, 1, 0)
        
        # === Section Workspace ===
        workspace_group = QGroupBox("Workspace")
        workspace_layout = QGridLayout()
        
        workspace_label = QLabel("Workspace:")
        workspace_layout.addWidget(workspace_label, 0, 0)
        
        self.workspace_edit = QLineEdit()
        if self.workspace_dir:
            self.workspace_edit.setText(self.workspace_dir)
        workspace_layout.addWidget(self.workspace_edit, 0, 1)
        
        workspace_browse_btn = QPushButton("Browse")
        workspace_browse_btn.clicked.connect(self._browse_workspace)
        workspace_layout.addWidget(workspace_browse_btn, 0, 2)
        
        workspace_group.setLayout(workspace_layout)
        config_layout.addWidget(workspace_group, 2, 0)
        
        content_splitter.addWidget(config_widget)
        
        # === Section Actions ===
        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(0, 10, 0, 10)
        
        self.compile_btn = QPushButton("Compile")
        self.compile_btn.setMinimumHeight(40)
        self.compile_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.compile_btn.clicked.connect(self._run_compilation)
        actions_layout.addWidget(self.compile_btn)
        
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setMinimumHeight(40)
        dry_run_btn.clicked.connect(self._dry_run)
        actions_layout.addWidget(dry_run_btn)
        
        refresh_btn = QPushButton("Refresh Engines")
        refresh_btn.setMinimumHeight(40)
        refresh_btn.clicked.connect(self._refresh_engines)
        actions_layout.addWidget(refresh_btn)
        
        actions_layout.addStretch()
        
        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.clicked.connect(self._clear_log)
        actions_layout.addWidget(clear_log_btn)
        
        actions_widget.setLayout(actions_layout)
        content_splitter.addWidget(actions_widget)
        
        # === Section Logs (bas) ===
        log_group = QGroupBox("Compilation Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(20)
        log_layout.addWidget(self.progress_bar)
        
        log_group.setLayout(log_layout)
        content_splitter.addWidget(log_group)
        
        # Définir les proportions du splitter
        content_splitter.setSizes([300, 80, 300])
        
        # === Barre de statut ===
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Initialiser les dimensions des groupes
        self._init_group_dimensions()
    
    def _init_group_dimensions(self):
        """Initialise les dimensions minimales des groupes."""
        self.engine_combo.setMinimumContentsLength(15)
    
    def _center_window(self):
        """Centre la fenêtre sur l'écran."""
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def _apply_theme(self, theme_name: str):
        """Applique le thème visuel."""
        if theme_name == "dark":
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #404040;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #ffffff;
                }
                QComboBox, QLineEdit {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #404040;
                    border-radius: 4px;
                    padding: 5px;
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
                }
                QPushButton:hover {
                    background-color: #4d4d4d;
                }
            """)
        else:  # light theme
            self.setStyleSheet("""
                QMainWindow, QWidget {
                    background-color: #f5f5f5;
                    color: #000000;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 1px solid #cccccc;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 5px;
                }
                QLabel {
                    color: #000000;
                }
                QComboBox, QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 5px;
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
                }
                QPushButton:hover {
                    background-color: #d0d0d0;
                }
            """)
    
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
            }
        }
        
        tr = translations.get(lang_code, translations["en"])
        
        # Mise à jour des labels
        for child in self.findChildren(QGroupBox):
            if "engine" in child.title().lower() or "moteur" in child.title().lower():
                child.setTitle(tr["engine_config"])
            elif "file" in child.title().lower() or "fichier" in child.title().lower():
                child.setTitle(tr["file_config"])
            elif "workspace" in child.title().lower():
                child.setTitle(tr["workspace"])
            elif "log" in child.title().lower():
                child.setTitle(tr["log"])
    
    def _refresh_engines(self):
        """Rafraîchit la liste des moteurs disponibles."""
        self.engine_combo.clear()
        self.engines_info = {}
        
        engine_ids = available_engines()
        
        for eid in engine_ids:
            try:
                engine_cls = get_engine(eid)
                if engine_cls:
                    name = getattr(engine_cls, "name", eid)
                    version = getattr(engine_cls, "version", "1.0.0")
                    required_core = getattr(engine_cls, "required_core_version", "1.0.0")
                    
                    self.engine_combo.addItem(f"{name} ({eid})", eid)
                    self.engines_info[eid] = {
                        "name": name,
                        "version": version,
                        "required_core": required_core,
                        "class": engine_cls,
                    }
            except Exception as e:
                self._log(f"Error loading engine {eid}: {e}")
        
        if engine_ids:
            self._log(f"Loaded {len(engine_ids)} engine(s)")
            self.statusBar.showMessage(f"Ready - {len(engine_ids)} engines loaded")
        else:
            self._log("No engines available. Please check ENGINES folder.")
            self.statusBar.showMessage("No engines available")
    
    def _on_engine_changed(self, index):
        """Appelé lorsque l'utilisateur sélectionne un moteur."""
        if index < 0:
            return
            
        engine_id = self.engine_combo.currentData()
        self.selected_engine_id = engine_id
        
        if engine_id in self.engines_info:
            info = self.engines_info[engine_id]
            self.engine_version_label.setText(f"Version: {info['version']}")
            self.core_version_label.setText(info['required_core'])
            self._log(f"Selected engine: {info['name']} v{info['version']}")
    
    def _check_compatibility(self):
        """Vérifie la compatibilité du moteur sélectionné."""
        engine_id = self.engine_combo.currentData()
        if not engine_id:
            QMessageBox.warning(self, "Warning", "Please select an engine first")
            return
        
        try:
            engine_cls = self.engines_info[engine_id]["class"]
            result = check_engine_compatibility(
                engine_cls,
                get_core_version(),
                get_engine_sdk_version(),
            )
            
            if result.is_compatible:
                self.compat_status_label.setText("✓ Compatible")
                self.compat_status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
                self._log(f"Engine {engine_id} is compatible")
            else:
                self.compat_status_label.setText("✗ Not compatible")
                self.compat_status_label.setStyleSheet("color: #f44336; font-weight: bold;")
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
            "Python files (*.py);;All files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.selected_file = file_path
    
    def _browse_workspace(self):
        """Ouvre une boîte de dialogue pour sélectionner un workspace."""
        workspace_dir = QFileDialog.getExistingDirectory(
            self,
            "Select workspace directory",
            self.workspace_edit.text() or "."
        )
        
        if workspace_dir:
            self.workspace_edit.setText(workspace_dir)
            self.workspace_dir = workspace_dir
    
    def _run_compilation(self):
        """Exécute la compilation."""
        engine_id = self.engine_combo.currentData()
        if not engine_id:
            QMessageBox.warning(self, "Warning", 
                               "Please select an engine first" if self.language == "en" 
                               else "Veuillez sélectionner un moteur d'abord")
            return
        
        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(self, "Warning",
                               "Please select a file to compile" if self.language == "en"
                               else "Veuillez sélectionner un fichier à compiler")
            return
        
        # Mise à jour du workspace
        self.workspace_dir = self.workspace_edit.text()
        
        # Afficher le statut
        self.statusBar.showMessage("Running compilation..." if self.language == "en" 
                                   else "Compilation en cours...")
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
            # Créer le moteur
            engine = create_engine(engine_id)
            
            # Préparer les arguments
            result = engine.program_and_args(None, file_path)
            
            if result:
                program, args = result
                cmd = [program] + args
                cmd_str = " ".join(cmd)
                
                self._log(f"Command: {cmd_str}")
                
                # Préparer l'environnement
                env = os.environ.copy()
                if self.workspace_dir:
                    env["ARK_WORKSPACE"] = self.workspace_dir
                
                # Exécuter la commande
                self._log("Executing...")
                
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env,
                    cwd=os.path.dirname(file_path) if file_path else None,
                    bufsize=1,
                )
                
                # Timer pour mettre à jour le statut
                start_time = datetime.now()
                
                # Lire la sortie en temps réel
                while True:
                    line = proc.stdout.readline()
                    if not line and proc.poll() is not None:
                        break
                    if line:
                        self._log(line.rstrip())
                
                # Lire stderr
                stderr = proc.stderr.read()
                if stderr:
                    self._log(f"STDERR:\n{stderr}")
                
                # Récupérer le code de retour
                return_code = proc.wait()
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                self._log("=" * 50)
                if return_code == 0:
                    self._log("Compilation successful!" if self.language == "en" 
                             else "Compilation réussie !")
                    self.statusBar.showMessage("Compilation successful!" if self.language == "en"
                                              else "Compilation terminée !")
                else:
                    self._log(f"Compilation failed with code {return_code}" if self.language == "en"
                             else f"Échec de la compilation (code {return_code})")
                    self.statusBar.showMessage("Compilation failed" if self.language == "en"
                                              else "Échec de la compilation")
                self._log(f"Duration: {duration:.2f}s")
                self._log("=" * 50)
                
            else:
                self._log("Failed to build command" if self.language == "en"
                         else "Échec de la construction de la commande")
                
        except Exception as e:
            self._log(f"Error: {str(e)}")
        finally:
            self.progress_bar.setVisible(False)
            self.compile_btn.setEnabled(True)
    
    def _dry_run(self):
        """Affiche la commande sans l'exécuter."""
        engine_id = self.engine_combo.currentData()
        if not engine_id:
            QMessageBox.warning(self, "Warning", "Please select an engine first")
            return
        
        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please select a file to compile")
            return
        
        try:
            engine = create_engine(engine_id)
            result = engine.program_and_args(None, file_path)
            
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


def launch_engines_gui(workspace_dir: Optional[str] = None, language: str = "en", 
                       theme: str = "dark") -> int:
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
        workspace_dir=workspace_dir,
        language=language,
        theme=theme
    )
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_engines_gui())

