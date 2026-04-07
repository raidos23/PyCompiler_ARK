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

from PySide6.QtCore import Qt, QSize, QTimer, QProcess, QThread, Signal
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

from EngineLoader import (
    available_engines,
    get_engine,
    create as create_engine,
)
from EngineLoader.validator import check_engine_compatibility
from Core.allversion import get_core_version, get_engine_sdk_version
import EngineLoader as engines_loader
from Core.process_security import secure_command, hardened_popen_kwargs


class CompilationThread(QThread):
    """Thread pour exécuter la compilation sans bloquer l'UI."""

    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)

    def __init__(self, program, args, env, working_dir=None):
        super().__init__()
        self.program = program
        self.args = args
        self.env = env
        self.working_dir = working_dir
        self.cancel_requested = False
        self.process = None

    def run(self):
        """Exécute le processus de compilation."""
        try:
            safe_program, safe_args, safe_env = secure_command(
                self.program, self.args, self.env
            )
            proc = subprocess.Popen(
                [safe_program] + safe_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=safe_env,
                cwd=self.working_dir,
                bufsize=1,
                **hardened_popen_kwargs(),
            )

            import select
            import time

            # Utiliser select pour lire stdout et stderr en temps réel
            while True:
                # Vérifier si l'annulation a été demandée
                if self.cancel_requested:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)  # Attendre que le processus se termine
                    except subprocess.TimeoutExpired:
                        proc.kill()  # Forcer la terminaison si nécessaire
                    if self.finished:
                        self.finished.emit(-1)  # Code spécial pour annulation
                    return

                # Vérifier si le processus est terminé
                if proc.poll() is not None:
                    break

                # Utiliser select pour attendre des données sur stdout ou stderr
                ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.1)

                for stream in ready:
                    if stream == proc.stdout and self.output_ready:
                        line = proc.stdout.readline()
                        if line:
                            self.output_ready.emit(line.rstrip())
                    elif stream == proc.stderr and self.error_ready:
                        line = proc.stderr.readline()
                        if line:
                            self.error_ready.emit(line.rstrip())

                time.sleep(0.01)  # Petit délai pour éviter la surcharge CPU

            # Lire tout ce qui reste dans les buffers après la fin du processus
            remaining_stdout = proc.stdout.read()
            if remaining_stdout and self.output_ready:
                for line in remaining_stdout.strip().split("\n"):
                    if line:
                        self.output_ready.emit(line.rstrip())

            remaining_stderr = proc.stderr.read()
            if remaining_stderr and self.error_ready:
                for line in remaining_stderr.strip().split("\n"):
                    if line:
                        self.error_ready.emit(line.rstrip())

            # Signaler la fin
            return_code = proc.returncode
            if self.finished:
                self.finished.emit(return_code)

        except Exception as e:
            if self.error_ready:
                self.error_ready.emit(f"Error: {str(e)}")
            if self.finished:
                self.finished.emit(1)

    def cancel(self):
        """Demande l'annulation de la compilation."""
        self.cancel_requested = True


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

        # État du venv
        self.venv_path: Optional[str] = None
        self.venv_manager = None

        # Configuration de la fenêtre
        self.setWindowTitle("Engines Standalone - PyCompiler ARK")
        self.resize(1200, 780)
        self.setMinimumSize(960, 640)

        # Chargement des icônes
        self._load_icons()

        # Configuration de l'interface
        self._setup_ui()
        self._apply_theme(theme)
        self._apply_language(language)

        # Chargement des moteurs
        self._refresh_engines()

        # Initialisation du gestionnaire de venv
        self._init_venv_manager()

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
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # === En-tête ===
        header_container = QVBoxLayout()
        header_container.setSpacing(6)
        header_top = QHBoxLayout()
        header_top.setSpacing(8)

        title_label = QLabel("Engines Standalone")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #4da6ff;")
        header_top.addWidget(title_label)
        header_top.addStretch()

        # Version info (top right)
        version_label = QLabel(
            f"Core: {get_core_version()} | SDK: {get_engine_sdk_version()}"
        )
        version_label.setStyleSheet("color: #888; font-size: 11px;")
        header_top.addWidget(version_label)

        header_container.addLayout(header_top)

        # === Section Venv ===
        venv_layout = QHBoxLayout()
        venv_layout.setSpacing(6)

        # Label venv
        venv_label = QLabel("Venv:")
        venv_label.setStyleSheet("font-weight: bold; font-size: 12px; color: #aaaaaa;")
        venv_layout.addWidget(venv_label)

        # Champ d'affichage du chemin du venv
        self.venv_path_edit = QLineEdit()
        self.venv_path_edit.setPlaceholderText("Select a virtual environment...")
        self.venv_path_edit.setReadOnly(True)
        self.venv_path_edit.setMinimumWidth(220)
        self.venv_path_edit.setMaximumWidth(360)
        self.venv_path_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """)
        venv_layout.addWidget(self.venv_path_edit)

        # Bouton sélectionner venv
        self.btn_select_venv = QPushButton("📁")
        self.btn_select_venv.setMinimumSize(32, 28)
        self.btn_select_venv.setToolTip("Select virtual environment folder")
        self.btn_select_venv.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4da6ff;
            }
        """)
        self.btn_select_venv.clicked.connect(self._select_venv)
        venv_layout.addWidget(self.btn_select_venv)

        # Bouton auto-détecter venv
        self.btn_autodetect_venv = QPushButton("🔍")
        self.btn_autodetect_venv.setMinimumSize(32, 28)
        self.btn_autodetect_venv.setToolTip("Auto-detect best virtual environment")
        self.btn_autodetect_venv.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #4caf50;
            }
        """)
        self.btn_autodetect_venv.clicked.connect(self._autodetect_venv)
        venv_layout.addWidget(self.btn_autodetect_venv)

        # Bouton clear venv
        self.btn_clear_venv = QPushButton("✕")
        self.btn_clear_venv.setMinimumSize(32, 28)
        self.btn_clear_venv.setToolTip("Clear venv selection")
        self.btn_clear_venv.setStyleSheet("""
            QPushButton {
                background-color: #404040;
                color: white;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #f44336;
            }
        """)
        self.btn_clear_venv.clicked.connect(self._clear_venv)
        venv_layout.addWidget(self.btn_clear_venv)

        venv_layout.addStretch(1)
        header_container.addLayout(venv_layout)

        main_layout.addLayout(header_container)

        # === Séparateur fin ===
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #404040; max-height: 2px;")
        main_layout.addWidget(separator)

        # === Splitter principal ===
        main_splitter = QSplitter(Qt.Vertical)
        main_splitter.setChildrenCollapsible(True)
        main_splitter.setHandleWidth(6)
        main_splitter.setCollapsible(0, True)
        main_splitter.setCollapsible(1, True)
        main_layout.addWidget(main_splitter)

        # === Panneau supérieur avec splitter horizontal ===
        top_splitter = QSplitter(Qt.Horizontal)
        top_splitter.setChildrenCollapsible(True)
        top_splitter.setHandleWidth(6)
        top_splitter.setCollapsible(0, True)
        top_splitter.setCollapsible(1, True)
        top_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # === Section Configuration (gauche) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(8)
        left_layout.setContentsMargins(4, 4, 4, 4)

        # Moteur
        engine_group = QGroupBox("Engine Configuration")
        engine_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        engine_layout = QVBoxLayout()
        engine_layout.setSpacing(6)

        self.compiler_tabs = QTabWidget()
        self.compiler_tabs.setDocumentMode(False)
        self.compiler_tabs.setTabsClosable(False)
        self.compiler_tabs.setMovable(False)
        self.compiler_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        engine_layout.addWidget(self.compiler_tabs)

        compat_btn = QPushButton("Check Compatibility")
        compat_btn.setMinimumHeight(30)
        compat_btn.clicked.connect(self._check_compatibility)
        engine_layout.addWidget(compat_btn)

        self.compat_status_label = QLabel("")
        self.compat_status_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        engine_layout.addWidget(self.compat_status_label)

        engine_group.setLayout(engine_layout)

        # Projet (Fichier + Workspace)
        project_group = QGroupBox("Project")
        project_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        project_layout = QVBoxLayout()
        project_layout.setSpacing(6)

        file_row = QHBoxLayout()
        file_row.setSpacing(6)
        file_label = QLabel("File:")
        file_label.setMinimumWidth(70)
        file_row.addWidget(file_label)

        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a Python file to compile...")
        self.file_path_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.file_path_edit.setMinimumHeight(28)
        file_row.addWidget(self.file_path_edit)

        browse_btn = QPushButton("Browse")
        browse_btn.setMinimumHeight(28)
        browse_btn.setMinimumWidth(80)
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        project_layout.addLayout(file_row)

        workspace_row = QHBoxLayout()
        workspace_row.setSpacing(6)
        workspace_label = QLabel("Workspace:")
        workspace_label.setMinimumWidth(70)
        workspace_row.addWidget(workspace_label)

        self.workspace_edit = QLineEdit()
        if self.workspace_dir:
            self.workspace_edit.setText(self.workspace_dir)
        self.workspace_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.workspace_edit.setMinimumHeight(28)
        workspace_row.addWidget(self.workspace_edit)

        workspace_browse_btn = QPushButton("Browse")
        workspace_browse_btn.setMinimumHeight(28)
        workspace_browse_btn.setMinimumWidth(80)
        workspace_browse_btn.clicked.connect(self._browse_workspace)
        workspace_row.addWidget(workspace_browse_btn)
        project_layout.addLayout(workspace_row)

        project_group.setLayout(project_layout)

        # Actions
        actions_group = QGroupBox("Actions")
        actions_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        actions_layout = QVBoxLayout()
        actions_layout.setSpacing(6)

        self.compile_btn = QPushButton("Compile")
        self.compile_btn.setMinimumHeight(30)
        self.compile_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
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

        # Cancel button
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(30)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """)
        self.cancel_btn.clicked.connect(self._cancel_compilation)
        self.cancel_btn.setEnabled(False)  # Disabled by default
        actions_layout.addWidget(self.cancel_btn)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setMinimumHeight(28)
        dry_run_btn.clicked.connect(self._dry_run)
        button_row.addWidget(dry_run_btn)

        refresh_btn = QPushButton("Refresh Engines")
        refresh_btn.setMinimumHeight(28)
        refresh_btn.clicked.connect(self._refresh_engines)
        button_row.addWidget(refresh_btn)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.setMinimumHeight(28)
        clear_log_btn.clicked.connect(self._clear_log)
        button_row.addWidget(clear_log_btn)

        actions_layout.addLayout(button_row)
        actions_group.setLayout(actions_layout)

        # Splitter between project/actions and engine for fresh ergonomics
        left_splitter = QSplitter(Qt.Vertical)
        left_splitter.setChildrenCollapsible(True)
        left_splitter.setHandleWidth(6)
        left_splitter.setCollapsible(0, True)
        left_splitter.setCollapsible(1, True)

        engine_wrap = QWidget()
        engine_wrap_layout = QVBoxLayout(engine_wrap)
        engine_wrap_layout.setContentsMargins(0, 0, 0, 0)
        engine_wrap_layout.addWidget(engine_group)

        lower_wrap = QWidget()
        lower_layout = QVBoxLayout(lower_wrap)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(8)
        lower_layout.addWidget(project_group)
        lower_layout.addWidget(actions_group)
        lower_layout.addStretch(1)

        left_splitter.addWidget(engine_wrap)
        left_splitter.addWidget(lower_wrap)
        left_splitter.setSizes([620, 300])

        left_layout.addWidget(left_splitter)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setWidget(left_panel)

        top_splitter.addWidget(left_scroll)

        # === Section Log (droite avec plus d'espace) ===
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setSpacing(6)
        log_layout.setContentsMargins(4, 4, 4, 4)

        log_group = QGroupBox("Compilation Log")
        log_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout_inner = QVBoxLayout()
        log_layout_inner.setSpacing(6)

        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setReadOnly(True)
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        log_layout_inner.addWidget(self.log_text)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(14)
        log_layout_inner.addWidget(self.progress_bar)

        log_group.setLayout(log_layout_inner)
        log_layout.addWidget(log_group)

        top_splitter.addWidget(log_container)

        # Définir les proportions (40% config, 60% log)
        top_splitter.setSizes([520, 780])

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

    def _init_venv_manager(self):
        """Initialise le gestionnaire de venv et détecte le venv."""
        try:
            from Core.Venv_Manager.Manager import VenvManager

            self.venv_manager = VenvManager(self)
            self._detect_venv()
        except Exception as e:
            self._log(f"⚠️ Impossible d'initialiser le gestionnaire de venv: {e}")

    def _detect_venv(self):
        """Détecte automatiquement le meilleur venv disponible."""
        if not self.venv_manager or not self.workspace_dir:
            return

        try:
            detected = self.venv_manager.resolve_existing_venv(self.workspace_dir)
            if detected:
                self.venv_path = detected
                if self._is_valid(self.venv_path_edit):
                    self.venv_path_edit.setText(detected)
                self._log(f"✅ Venv auto-détecté: {detected}")
        except Exception as e:
            self._log(f"⚠️ Erreur détection venv: {e}")

    def _select_venv(self):
        """Ouvre une boîte de dialogue pour sélectionner le venv."""
        if not self.venv_manager:
            QMessageBox.warning(
                self,
                "Warning",
                "Venv manager not initialized.",
            )
            return

        current_path = self.venv_path or ""

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Virtual Environment Folder",
            current_path,
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            ok, reason = self.venv_manager.validate_venv_strict(folder)
            if ok:
                self.venv_path = folder
                self.venv_path_edit.setText(folder)
                self._log(f"✅ Virtual environment selected: {folder}")
                try:
                    if self.venv_manager and self.workspace_dir:
                        self.venv_manager.save_workspace_pref(self.workspace_dir)
                except Exception:
                    pass
            else:
                QMessageBox.warning(
                    self,
                    "Invalid Venv",
                    f"The selected folder is not a valid virtual environment:\n{reason}",
                )
                self._log(f"❌ Invalid venv selected: {reason}")

    def _autodetect_venv(self):
        """Auto-détecte le meilleur venv disponible."""
        if not self.venv_manager:
            QMessageBox.warning(
                self,
                "Warning",
                "Venv manager not initialized.",
            )
            return

        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a workspace folder first.",
            )
            return

        self._log("Auto-detecting virtual environment...")

        detected = self.venv_manager.resolve_existing_venv(self.workspace_dir)

        if detected:
            self.venv_path = detected
            self.venv_path_edit.setText(detected)
            self._log(f"✅ Best venv auto-detected: {detected}")
            try:
                if self.venv_manager and self.workspace_dir:
                    self.venv_manager.save_workspace_pref(self.workspace_dir)
            except Exception:
                pass
        else:
            self._log("No virtual environment found in workspace.")
            QMessageBox.information(
                self,
                "No Venv Found",
                "No valid virtual environment was found in the workspace.\n"
                "Please select one manually or create a new venv.",
            )

    def _clear_venv(self):
        """Efface la sélection du venv."""
        self.venv_path = None
        self.venv_path_edit.clear()
        self.venv_path_edit.setPlaceholderText("Select a virtual environment...")

        try:
            if self.venv_manager and self.workspace_dir:
                self.venv_manager.save_workspace_pref(self.workspace_dir)
        except Exception:
            pass

        self._log("Venv selection cleared")

    def _is_valid(self, widget) -> bool:
        """Vérifie si un widget Qt est toujours valide.

        Contrairement à hasattr(), cette méthode vérifie si l'objet C++
        sous-jacent n'a pas été détruit.

        Args:
            widget: Le widget Qt à vérifier

        Returns:
            True si le widget est valide, False sinon
        """
        if widget is None:
            return False
        try:
            # Tentative d'accès à une propriété du widget
            # Si l'objet C++ a été détruit, une RuntimeError sera levée
            widget.objectName()
            return True
        except RuntimeError:
            return False

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
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #1f1f1f;
                    width: 10px;
                    margin: 2px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical {
                    background: #3d3d3d;
                    min-height: 24px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #4a4a4a;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
                QStatusBar {
                    background-color: #252525;
                    color: #aaaaaa;
                    font-size: 11px;
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
                QScrollArea {
                    background: transparent;
                    border: none;
                }
                QScrollBar:vertical {
                    background: #f0f0f0;
                    width: 10px;
                    margin: 2px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical {
                    background: #c0c0c0;
                    min-height: 24px;
                    border-radius: 5px;
                }
                QScrollBar::handle:vertical:hover {
                    background: #b0b0b0;
                }
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                    height: 0px;
                }
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                    background: none;
                }
            """)

    def _apply_language(self, lang_code: str):
        """Applique la langue de l'interface."""
        self.language = lang_code

        # Traductions
        translations = {
            "en": {
                "engine_config": "Engine Configuration",
                "project": "Project",
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
                "project": "Projet",
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
            elif "project" in title or "projet" in title:
                child.setTitle(tr["project"])
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
            no_engine_label = QLabel(
                "No engines available.\nPlease check ENGINES folder."
            )
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
        self.cancel_btn.setEnabled(True)

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

                # Récupérer le venv à utiliser
                if not self.venv_path and self.venv_manager and self.workspace_dir:
                    detected = self.venv_manager.resolve_existing_venv(
                        self.workspace_dir
                    )
                    if detected:
                        self.venv_path = detected
                        if self._is_valid(self.venv_path_edit):
                            self.venv_path_edit.setText(detected)

                if self.venv_path:
                    self._log(f"Using virtual environment: {self.venv_path}")

                # Préparer l'environnement
                env = os.environ.copy()
                if self.workspace_dir:
                    env["ARK_WORKSPACE"] = self.workspace_dir
                if self.venv_path:
                    env["ARK_VENV_PATH"] = self.venv_path

                # Exécuter la commande dans un thread séparé
                self._log("Executing...")

                # Timer pour mettre à jour le statut
                self._start_time = datetime.now()

                # Créer et configurer le thread
                working_dir = os.path.dirname(file_path) if file_path else None
                self.compilation_thread = CompilationThread(
                    program, args, env, working_dir
                )
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

    def _cancel_compilation(self):
        """Annule la compilation en cours."""
        if (
            hasattr(self, "compilation_thread")
            and self.compilation_thread
            and self.compilation_thread.isRunning()
        ):
            self._log("Cancelling compilation...")
            self.statusBar.showMessage(
                "Cancelling compilation..."
                if self.language == "en"
                else "Annulation de la compilation..."
            )
            self.compilation_thread.cancel()
            self.cancel_btn.setEnabled(False)

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
        if self._is_valid(self.log_text):
            try:
                self.log_text.clear()
            except (RuntimeError, AttributeError):
                pass  # Ignorer si le widget a été supprimé

    def _log(self, message: str):
        """Ajoute un message au log."""
        try:
            from pycompiler_ark import onlymod_log

            onlymod_log(message, gui=self)
            return
        except Exception:
            pass

        # Fallback direct (si le centraliseur n'est pas dispo)
        if not self._is_valid(self.log_text):
            return
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except (RuntimeError, AttributeError):
            pass


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
    app.setApplicationName("PyCompiler ARK Engines")
    app.setOrganizationName("raidos23")

    window = EnginesStandaloneGui(
        workspace_dir=workspace_dir, language=language, theme=theme
    )
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_engines_gui())
