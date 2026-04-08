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
Engines Standalone GUI Application.

This module provides a dedicated GUI to run compilation engines independently
from the main PyCompiler ARK application.
"""

from __future__ import annotations

import os
import sys
import json
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
    QPlainTextEdit,
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

try:
    from Core.AdvancedConfigEditor import _SimpleHighlighter
except Exception:
    _SimpleHighlighter = None


class _ProgLog:
    """Minimal log adapter for prog-engine GUI compatibility."""

    def __init__(self):
        self.messages: list[str] = []

    def append(self, message: str) -> None:
        self.messages.append(str(message))

    def clear(self) -> None:
        self.messages.clear()

    def get_value(self) -> str:
        return "\n".join(self.messages)


class CompilationThread(QThread):
    """Run compilation in a background thread to keep UI responsive."""

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
        """Execute the compilation process."""
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
        """Request cancellation of the running compilation."""
        self.cancel_requested = True


class EnginesStandaloneGui(QMainWindow):
    """
    Standalone GUI used to manage and execute compilation engines.

    The window allows engine selection, compilation execution, and log viewing.
    """

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        language: str = "en",
        theme: str = "dark",
    ):
        """
        Initialize the standalone engines GUI application.

        Args:
            workspace_dir: Optional workspace path.
            language: UI language code (`en` or `fr`).
            theme: Theme name (`light` or `dark`).
        """
        super().__init__()

        self.workspace_dir = workspace_dir
        self.language = language
        self.theme = theme
        self.selected_engine_id = None
        self.selected_file = None
        self.entrypoint_file = None
        self._entrypoint_relpath = None

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
        self._load_entrypoint_from_workspace()
        self._apply_entrypoint_marker()

        # Centre la fenêtre sur l'écran
        self._center_window()

    def _load_icons(self):
        """Load application icons."""
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
        """Create a simple icon placeholder from text and color."""
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)
        return QIcon(pixmap)

    def _setup_ui(self):
        """Build and connect the main user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Header
        header_container = QWidget()
        header_container.setObjectName("header_card")
        header_layout = QVBoxLayout(header_container)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(4)

        header_top = QHBoxLayout()
        header_top.setSpacing(8)

        title_label = QLabel("Engines Standalone")
        title_label.setObjectName("header_title")
        header_top.addWidget(title_label)
        header_top.addStretch()

        version_label = QLabel(
            f"Core: {get_core_version()} | SDK: {get_engine_sdk_version()}"
        )
        version_label.setObjectName("header_meta")
        header_top.addWidget(version_label)
        header_layout.addLayout(header_top)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setObjectName("header_separator")
        header_layout.addWidget(separator)
        main_layout.addWidget(header_container)

        # Main body split in 3 clear zones: project/actions | engine config | logs
        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setChildrenCollapsible(False)
        body_splitter.setHandleWidth(6)
        main_layout.addWidget(body_splitter, 1)

        # Left sidebar: project + venv + actions
        left_panel = QWidget()
        left_panel.setObjectName("sidebar_panel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        left_layout.setContentsMargins(0, 0, 0, 0)

        project_group = QGroupBox("Project")
        project_group.setObjectName("panel_group")
        project_layout = QGridLayout(project_group)
        project_layout.setHorizontalSpacing(8)
        project_layout.setVerticalSpacing(8)

        workspace_label = QLabel("Workspace:")
        workspace_label.setMinimumWidth(72)
        self.workspace_edit = QLineEdit()
        if self.workspace_dir:
            self.workspace_edit.setText(self.workspace_dir)
        self.workspace_edit.setPlaceholderText("Select workspace folder...")
        self.workspace_edit.setMinimumHeight(30)
        workspace_browse_btn = QPushButton("Browse")
        workspace_browse_btn.setObjectName("secondary_button")
        workspace_browse_btn.setMinimumHeight(30)
        workspace_browse_btn.setMinimumWidth(84)
        workspace_browse_btn.clicked.connect(self._browse_workspace)
        project_layout.addWidget(workspace_label, 0, 0)
        project_layout.addWidget(self.workspace_edit, 0, 1)
        project_layout.addWidget(workspace_browse_btn, 0, 2)

        file_label = QLabel("File:")
        file_label.setMinimumWidth(72)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a Python file (entrypoint)...")
        self.file_path_edit.setMinimumHeight(30)
        browse_file_btn = QPushButton("Browse")
        browse_file_btn.setObjectName("secondary_button")
        browse_file_btn.setMinimumHeight(30)
        browse_file_btn.setMinimumWidth(84)
        browse_file_btn.clicked.connect(self._browse_file)
        project_layout.addWidget(file_label, 1, 0)
        project_layout.addWidget(self.file_path_edit, 1, 1)
        project_layout.addWidget(browse_file_btn, 1, 2)

        self.entrypoint_info_label = QLabel("Entrypoint: not set")
        self.entrypoint_info_label.setObjectName("subtle_label")
        project_layout.addWidget(self.entrypoint_info_label, 2, 0, 1, 3)
        left_layout.addWidget(project_group)

        venv_group = QGroupBox("Virtual Environment")
        venv_group.setObjectName("panel_group")
        venv_layout = QVBoxLayout(venv_group)
        venv_layout.setSpacing(8)

        self.venv_path_edit = QLineEdit()
        self.venv_path_edit.setObjectName("venv_path_input")
        self.venv_path_edit.setPlaceholderText("Select a virtual environment...")
        self.venv_path_edit.setReadOnly(True)
        self.venv_path_edit.setMinimumHeight(30)
        venv_layout.addWidget(self.venv_path_edit)

        venv_btn_row = QHBoxLayout()
        venv_btn_row.setSpacing(6)
        self.btn_select_venv = QPushButton("📁")
        self.btn_select_venv.setObjectName("tool_button")
        self.btn_select_venv.setMinimumSize(32, 30)
        self.btn_select_venv.setToolTip("Select virtual environment folder")
        self.btn_select_venv.clicked.connect(self._select_venv)
        venv_btn_row.addWidget(self.btn_select_venv)

        self.btn_autodetect_venv = QPushButton("🔍")
        self.btn_autodetect_venv.setObjectName("tool_button")
        self.btn_autodetect_venv.setMinimumSize(32, 30)
        self.btn_autodetect_venv.setToolTip("Auto-detect best virtual environment")
        self.btn_autodetect_venv.clicked.connect(self._autodetect_venv)
        venv_btn_row.addWidget(self.btn_autodetect_venv)

        self.btn_clear_venv = QPushButton("✕")
        self.btn_clear_venv.setObjectName("tool_button")
        self.btn_clear_venv.setMinimumSize(32, 30)
        self.btn_clear_venv.setToolTip("Clear venv selection")
        self.btn_clear_venv.clicked.connect(self._clear_venv)
        venv_btn_row.addWidget(self.btn_clear_venv)
        venv_btn_row.addStretch(1)
        venv_layout.addLayout(venv_btn_row)
        left_layout.addWidget(venv_group)

        actions_group = QGroupBox("Actions")
        actions_group.setObjectName("panel_group")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(8)

        self.compile_btn = QPushButton("Compile")
        self.compile_btn.setObjectName("compile_btn")
        self.compile_btn.setMinimumHeight(34)
        self.compile_btn.clicked.connect(self._run_compilation)
        actions_layout.addWidget(self.compile_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setMinimumHeight(34)
        self.cancel_btn.clicked.connect(self._cancel_compilation)
        self.cancel_btn.setEnabled(False)
        actions_layout.addWidget(self.cancel_btn)

        button_row = QGridLayout()
        button_row.setHorizontalSpacing(6)
        button_row.setVerticalSpacing(6)

        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("secondary_button")
        dry_run_btn.setMinimumHeight(30)
        dry_run_btn.clicked.connect(self._dry_run)
        button_row.addWidget(dry_run_btn, 0, 0)

        refresh_btn = QPushButton("Refresh Engines")
        refresh_btn.setObjectName("secondary_button")
        refresh_btn.setMinimumHeight(30)
        refresh_btn.clicked.connect(self._refresh_engines)
        button_row.addWidget(refresh_btn, 0, 1)

        clear_log_btn = QPushButton("Clear Log")
        clear_log_btn.setObjectName("secondary_button")
        clear_log_btn.setMinimumHeight(30)
        clear_log_btn.clicked.connect(self._clear_log)
        button_row.addWidget(clear_log_btn, 1, 0, 1, 2)

        actions_layout.addLayout(button_row)
        left_layout.addWidget(actions_group)
        left_layout.addStretch(1)
        left_panel.setMinimumWidth(340)
        left_panel.setMaximumWidth(440)
        body_splitter.addWidget(left_panel)

        # Center: engine tabs + compatibility
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        center_layout.setSpacing(10)
        center_layout.setContentsMargins(0, 0, 0, 0)

        engine_group = QGroupBox("Engine Configuration")
        engine_group.setObjectName("panel_group")
        engine_layout = QVBoxLayout(engine_group)
        engine_layout.setSpacing(8)

        self.compiler_tabs = QTabWidget()
        self.compiler_tabs.setDocumentMode(False)
        self.compiler_tabs.setTabsClosable(False)
        self.compiler_tabs.setMovable(False)
        self.compiler_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        engine_layout.addWidget(self.compiler_tabs)

        compat_row = QHBoxLayout()
        compat_row.setSpacing(8)
        compat_btn = QPushButton("Check Compatibility")
        compat_btn.setObjectName("secondary_button")
        compat_btn.setMinimumHeight(30)
        compat_btn.clicked.connect(self._check_compatibility)
        compat_row.addWidget(compat_btn)

        self.compat_status_label = QLabel("")
        self.compat_status_label.setObjectName("compat_status")
        compat_row.addWidget(self.compat_status_label, 1)
        engine_layout.addLayout(compat_row)
        center_layout.addWidget(engine_group, 1)
        body_splitter.addWidget(center_panel)

        # Right: logs and progress
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setSpacing(10)
        log_layout.setContentsMargins(0, 0, 0, 0)

        log_group = QGroupBox("Compilation Log")
        log_group.setObjectName("panel_group")
        log_layout_inner = QVBoxLayout(log_group)
        log_layout_inner.setSpacing(8)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("log")
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setReadOnly(True)
        self.log_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_layout_inner.addWidget(self.log_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(14)
        log_layout_inner.addWidget(self.progress_bar)
        log_layout.addWidget(log_group)
        body_splitter.addWidget(log_container)
        body_splitter.setSizes([360, 680, 520])

        self.statusBar = QStatusBar()
        self.statusBar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.statusBar.setMinimumHeight(20)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def _center_window(self):
        """Center the window on the primary screen."""
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)

    def _init_venv_manager(self):
        """Initialize the venv manager and run auto-detection."""
        try:
            from Core.Venv_Manager.Manager import VenvManager

            self.venv_manager = VenvManager(self)
            self._detect_venv()
        except Exception as e:
            self._log(f"⚠️ Impossible d'initialiser le gestionnaire de venv: {e}")

    def _detect_venv(self):
        """Auto-detect the best virtual environment for the workspace."""
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
        """Open a dialog to select a virtual environment folder."""
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
        """Run virtual environment auto-detection explicitly."""
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
        """Clear current virtual environment selection."""
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
        """Return whether a Qt widget still has a valid underlying C++ object.

        Args:
            widget: Qt widget to validate.

        Returns:
            `True` when widget is valid, otherwise `False`.
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
        """Apply the exact Arctic Light QSS from themes/."""
        _ = theme_name  # Kept for signature compatibility.
        try:
            qss_path = (
                Path(__file__).resolve().parents[2] / "themes" / "arctic_light.qss"
            )
            css = qss_path.read_text(encoding="utf-8")
            self.setStyleSheet(css)
        except Exception:
            # Keep the window usable even if theme loading fails.
            self.setStyleSheet("")
            self.statusBar().showMessage("Arctic theme unavailable: fallback active")

    def _apply_language(self, lang_code: str):
        """Apply UI language labels."""
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
        """Refresh available engines and rebuild their tabs."""
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
        """Create a fallback widget for engines without `create_tab`."""
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
        """Check compatibility of the engine in the current tab."""
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

    def _load_entrypoint_from_workspace(self) -> None:
        """Load entrypoint from ARK_Main_Config.yml for current workspace."""
        self._entrypoint_relpath = None
        self.entrypoint_file = None
        ws = (self.workspace_edit.text() or "").strip()
        if not ws:
            return
        try:
            from Core.ArkConfigManager import get_entrypoint, load_ark_config

            cfg = load_ark_config(ws)
            rel = get_entrypoint(cfg)
            if rel:
                abs_path = os.path.join(ws, rel)
                if os.path.isfile(abs_path):
                    self._entrypoint_relpath = rel
                    self.entrypoint_file = abs_path
        except Exception:
            return

    def _apply_entrypoint_marker(self) -> None:
        """Refresh entrypoint labels and file preview."""
        if self.selected_file:
            try:
                ws = self.workspace_edit.text().strip() or self.workspace_dir or ""
                rel = (
                    os.path.relpath(self.selected_file, ws).replace("\\", "/")
                    if ws
                    else self.selected_file
                )
            except Exception:
                rel = self.selected_file
            self.entrypoint_info_label.setText(f"Entrypoint (this build only): {rel}")
            if self._is_valid(self.file_path_edit):
                self.file_path_edit.setText(self.selected_file)
            return

        rel = self._entrypoint_relpath
        if rel:
            self.entrypoint_info_label.setText(f"Entrypoint (config): {rel}")
            if self._is_valid(self.file_path_edit):
                self.file_path_edit.setText(self.entrypoint_file or rel)
        else:
            self.entrypoint_info_label.setText("Entrypoint: not set")
            if self._is_valid(self.file_path_edit):
                self.file_path_edit.clear()

    def _browse_file(self) -> None:
        """Select a Python file as temporary build entrypoint (no config write)."""
        start_dir = self.workspace_edit.text().strip() or self.workspace_dir or "."
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Python file (temporary entrypoint)",
            start_dir,
            "Python files (*.py);;All files (*)",
        )
        if not file_path:
            return

        abs_file = os.path.abspath(file_path)
        ws = self.workspace_edit.text().strip()
        if not ws:
            ws = os.path.dirname(abs_file)
            self.workspace_edit.setText(ws)
        ws = os.path.abspath(ws)
        self.workspace_dir = ws

        # If selected file is outside current workspace, align workspace to file folder.
        try:
            common = os.path.commonpath([ws, abs_file])
        except Exception:
            common = ""
        if common != ws:
            ws = os.path.dirname(abs_file)
            self.workspace_dir = ws
            self.workspace_edit.setText(ws)

        self.selected_file = abs_file

        self._apply_entrypoint_marker()
        self._detect_venv()
        self._log("Temporary entrypoint selected for this build only")

    def _resolve_compile_target(self) -> str | None:
        """Resolve compile target from session selection first, then config."""
        if self.selected_file and os.path.isfile(self.selected_file):
            return self.selected_file
        if self.entrypoint_file and os.path.isfile(self.entrypoint_file):
            return self.entrypoint_file
        return None

    def _browse_workspace(self):
        """Open a dialog to select a workspace directory."""
        workspace_dir = QFileDialog.getExistingDirectory(
            self, "Select workspace directory", self.workspace_edit.text() or "."
        )

        if workspace_dir:
            self.workspace_edit.setText(workspace_dir)
            self.workspace_dir = workspace_dir
            self.selected_file = None
            self._load_entrypoint_from_workspace()
            self._apply_entrypoint_marker()
            self._detect_venv()

    def _run_compilation(self):
        """Run compilation with the engine from the active tab."""
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

        file_path = self._resolve_compile_target()
        if not file_path:
            QMessageBox.warning(
                self,
                "Warning",
                (
                    "Configure a workspace entrypoint before compiling"
                    if self.language == "en"
                    else "Configurez un point d'entrée du workspace avant de compiler"
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
        """Cancel the active compilation thread if running."""
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
        """Handle compilation stderr output."""
        self._log(f"STDERR: {message}")

    def _on_compilation_finished(self, return_code):
        """Finalize UI state when compilation ends."""
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
        """Display the generated command without running it."""
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

        file_path = self._resolve_compile_target()
        if not file_path:
            QMessageBox.warning(
                self,
                "Warning",
                "Configure a workspace entrypoint before dry-run",
            )
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
        """Clear the log pane."""
        if self._is_valid(self.log_text):
            try:
                self.log_text.clear()
            except (RuntimeError, AttributeError):
                pass  # Ignorer si le widget a été supprimé

    def _log(self, message: str):
        """Append a timestamped message to the log pane."""
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
    """Launch the standalone engines GUI.

    Args:
        workspace_dir: Optional workspace path.
        language: UI language code (`en` or `fr`).
        theme: Theme name (`light` or `dark`).

    Returns:
        Application exit code.
    """
    app = QApplication(sys.argv)
    app.setApplicationName("PyCompiler ARK Engines")
    app.setOrganizationName("raidos23")

    window = EnginesStandaloneGui(
        workspace_dir=workspace_dir, language=language, theme=theme
    )
    window.show()

    return app.exec()


class ProgEngineConfigGui(QMainWindow):
    """Dedicated GUI for fast single-engine configuration editing."""

    def __init__(
        self,
        engine_id: str | None,
        workspace_dir: Optional[str] = None,
        language: str = "en",
        theme: str = "dark",
    ):
        super().__init__()
        self.engine_id = str(engine_id or "").strip() or None
        self.workspace_dir = (
            os.path.abspath(str(workspace_dir)) if workspace_dir else None
        )
        self.language = language
        self.theme = theme
        self._tr = {}
        self.venv_path = None
        self.venv_manager = None
        self._editor_push_guard = False
        self._tab_push_guard = False
        self._pending_editor_apply = False
        self._pending_tab_sync = False
        self._engines_by_id: dict[str, object] = {}
        self._tab_engine_map: dict[int, str] = {}
        self.log = _ProgLog()

        target = self.engine_id or "all"
        self.setWindowTitle(f"Prog Engine - {target}")
        self.resize(1320, 820)
        self.setMinimumSize(1024, 640)

        self._setup_ui()
        self._apply_theme()
        self._load_engine_tabs()
        self._load_workspace_config()
        self._sync_editor_from_tab()

    def tr(self, fr_text: str, en_text: str) -> str:
        """Simple i18n bridge used by engines."""
        try:
            if str(self.language).lower().startswith("fr"):
                return fr_text
        except Exception:
            pass
        return en_text

    def _setup_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self.header_label = QLabel(
            f"Engine: {self.engine_id or 'all'} | Workspace: {self.workspace_dir or '(required)'}",
            self,
        )
        self.header_label.setObjectName("prog_header")
        root.addWidget(self.header_label)

        workspace_row = QHBoxLayout()
        workspace_row.setSpacing(6)
        workspace_row.addWidget(QLabel("Workspace:", self))
        self.workspace_edit = QLineEdit(self)
        self.workspace_edit.setPlaceholderText("Select workspace folder...")
        if self.workspace_dir:
            self.workspace_edit.setText(self.workspace_dir)
        workspace_row.addWidget(self.workspace_edit, 1)
        self.workspace_browse_btn = QPushButton("Browse", self)
        self.workspace_browse_btn.setMinimumHeight(30)
        self.workspace_browse_btn.clicked.connect(self._select_workspace)
        workspace_row.addWidget(self.workspace_browse_btn)
        self.workspace_clear_btn = QPushButton("Clear", self)
        self.workspace_clear_btn.setMinimumHeight(30)
        self.workspace_clear_btn.clicked.connect(self._clear_workspace)
        workspace_row.addWidget(self.workspace_clear_btn)
        root.addLayout(workspace_row)

        split = QSplitter(Qt.Horizontal, self)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(6)
        root.addWidget(split, 1)

        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        self.compiler_tabs = QTabWidget(left)
        self.compiler_tabs.setDocumentMode(False)
        self.compiler_tabs.setTabsClosable(False)
        self.compiler_tabs.setMovable(False)
        self.compiler_tabs.currentChanged.connect(lambda *_: self._schedule_editor_sync())
        left_layout.addWidget(self.compiler_tabs, 1)

        self.save_config_btn = QPushButton("Save Config", left)
        self.save_config_btn.setMinimumHeight(34)
        self.save_config_btn.clicked.connect(self._save_current_engine_config)
        left_layout.addWidget(self.save_config_btn)
        split.addWidget(left)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        editor_title = QLabel("Engine Config JSON (real-time sync)", right)
        editor_title.setObjectName("prog_editor_title")
        right_layout.addWidget(editor_title)

        self.config_editor = QPlainTextEdit(right)
        self.config_editor.setObjectName("prog_config_editor")
        self.config_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.config_editor.textChanged.connect(self._on_editor_text_changed)
        right_layout.addWidget(self.config_editor, 1)

        self.editor_status = QLabel("Ready", right)
        self.editor_status.setObjectName("prog_editor_status")
        right_layout.addWidget(self.editor_status)
        split.addWidget(right)
        split.setSizes([760, 560])

        self.statusBar = QStatusBar(self)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        if _SimpleHighlighter is not None:
            try:
                _SimpleHighlighter(self.config_editor.document(), "json")
            except Exception:
                pass

    def _refresh_workspace_header(self) -> None:
        """Refresh header label with current workspace."""
        try:
            self.header_label.setText(
                f"Engine: {self.engine_id or 'all'} | Workspace: {self.workspace_dir or '(required)'}"
            )
        except Exception:
            pass

    def _select_workspace(self) -> None:
        """Open folder dialog and set workspace for the prog-engine session."""
        start = self.workspace_dir or self.workspace_edit.text().strip() or str(
            Path.home()
        )
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select workspace directory",
            start,
        )
        if not folder:
            return
        try:
            self.workspace_dir = os.path.abspath(folder)
        except Exception:
            self.workspace_dir = folder
        self.workspace_edit.setText(self.workspace_dir)
        self._refresh_workspace_header()
        self._load_workspace_config()
        self._sync_editor_from_tab()
        self._set_editor_status("Workspace updated", ok=True)

    def _clear_workspace(self) -> None:
        """Clear workspace selection in prog-engine GUI."""
        self.workspace_dir = None
        self.workspace_edit.clear()
        self._refresh_workspace_header()
        self._sync_editor_from_tab()
        self._set_editor_status("Workspace cleared", ok=False)

    def _apply_theme(self) -> None:
        if str(self.theme).lower() == "light":
            self.setStyleSheet(
                """
                QMainWindow, QWidget { background: #f7f7f7; color: #111; }
                QTabWidget::pane { border: 1px solid #d2d2d2; background: #fff; }
                QTabBar::tab { background: #efefef; border: 1px solid #d2d2d2; padding: 8px 12px; }
                QTabBar::tab:selected { background: #ffffff; border-bottom: 2px solid #1e88e5; }
                QPushButton { background: #1e88e5; color: #fff; border: 0; border-radius: 6px; padding: 8px 12px; font-weight: 700; }
                QPushButton:hover { background: #1565c0; }
                QPlainTextEdit { background: #ffffff; color: #111; border: 1px solid #d2d2d2; border-radius: 6px; font-family: Consolas, 'Courier New', monospace; font-size: 12px; }
                #prog_header { font-weight: 700; color: #333; }
                #prog_editor_title { font-weight: 700; color: #222; }
                #prog_editor_status { color: #555; }
                """
            )
            return
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #1d1f24; color: #e8e8e8; }
            QTabWidget::pane { border: 1px solid #363a43; background: #23262d; }
            QTabBar::tab { background: #2b3038; border: 1px solid #404652; padding: 8px 12px; color: #d9d9d9; }
            QTabBar::tab:selected { background: #343a45; border-bottom: 2px solid #35a0ff; }
            QPushButton { background: #1976d2; color: #fff; border: 0; border-radius: 6px; padding: 8px 12px; font-weight: 700; }
            QPushButton:hover { background: #1565c0; }
            QPlainTextEdit { background: #121417; color: #e6edf3; border: 1px solid #363a43; border-radius: 6px; font-family: Consolas, 'Courier New', monospace; font-size: 12px; }
            #prog_header { font-weight: 700; color: #b8d9ff; }
            #prog_editor_title { font-weight: 700; color: #8ac6ff; }
            #prog_editor_status { color: #9ca8b5; }
            """
        )

    def _load_engine_tabs(self) -> None:
        """Load one engine tab (targeted mode) or all engine tabs (global mode)."""
        self.compiler_tabs.clear()
        self._engines_by_id = {}
        self._tab_engine_map = {}
        try:
            engine_ids = [self.engine_id] if self.engine_id else list(available_engines())
            if not engine_ids:
                empty = QWidget(self)
                lay = QVBoxLayout(empty)
                lay.addWidget(QLabel("No engines available.", empty))
                self.compiler_tabs.addTab(empty, "No Engines")
                return

            for eid in engine_ids:
                if not eid:
                    continue
                try:
                    engine = create_engine(eid)
                    self._engines_by_id[str(eid)] = engine
                    pair = None
                    try:
                        make_tab = getattr(engine, "create_tab", None)
                        if callable(make_tab):
                            pair = make_tab(self)
                    except Exception as exc:
                        self._set_editor_status(
                            f"Tab creation failed for {eid}: {exc}", ok=False
                        )
                    if pair and isinstance(pair, tuple) and len(pair) == 2:
                        tab_widget, label = pair
                        idx = self.compiler_tabs.addTab(tab_widget, label)
                    else:
                        fallback_tab = QWidget(self)
                        fb = QVBoxLayout(fallback_tab)
                        fb.addWidget(
                            QLabel(
                                f"Engine tab unavailable for '{eid}'.\nUsing config editor only.",
                                fallback_tab,
                            )
                        )
                        idx = self.compiler_tabs.addTab(fallback_tab, str(eid))
                    self._tab_engine_map[int(idx)] = str(eid)
                except Exception as exc:
                    self._set_editor_status(f"Engine load failed for {eid}: {exc}", ok=False)

            self._attach_live_hooks()
        except Exception as exc:
            self.compiler_tabs.clear()
            failure_tab = QWidget(self)
            fl = QVBoxLayout(failure_tab)
            fl.addWidget(QLabel(f"Unable to load engines: {exc}"))
            self.compiler_tabs.addTab(failure_tab, "Error")
            self._set_editor_status(f"Engine load failed: {exc}", ok=False)

    def _current_engine_id(self) -> str | None:
        """Return engine id mapped to current tab."""
        try:
            idx = int(self.compiler_tabs.currentIndex())
        except Exception:
            return None
        if idx < 0:
            return None
        return self._tab_engine_map.get(idx)

    def _current_engine(self):
        """Return engine instance for current tab."""
        eid = self._current_engine_id()
        if not eid:
            return None
        return self._engines_by_id.get(eid)

    def _load_workspace_config(self) -> None:
        try:
            from Core.EngineConfigManager import (
                apply_engine_config,
                load_engine_config,
            )

            if not self._engines_by_id or not self.workspace_dir:
                return
            self._tab_push_guard = True
            try:
                for eid, engine in list(self._engines_by_id.items()):
                    data = load_engine_config(self.workspace_dir, eid)
                    if data:
                        apply_engine_config(self, engine, data)
            finally:
                self._tab_push_guard = False
        except Exception as exc:
            self._set_editor_status(f"Config load warning: {exc}", ok=False)

    def _attach_live_hooks(self) -> None:
        from PySide6.QtWidgets import (
            QCheckBox,
            QComboBox,
            QDoubleSpinBox,
            QLineEdit,
            QSpinBox,
            QTextEdit,
        )

        def _bind() -> None:
            if self._tab_push_guard:
                return
            self._schedule_editor_sync()

        roots = [self.compiler_tabs]
        for root in roots:
            for line in root.findChildren(QLineEdit):
                line.textChanged.connect(_bind)
            for check in root.findChildren(QCheckBox):
                check.toggled.connect(_bind)
            for combo in root.findChildren(QComboBox):
                combo.currentTextChanged.connect(_bind)
                combo.currentIndexChanged.connect(lambda *_: _bind())
            for spin in root.findChildren(QSpinBox):
                spin.valueChanged.connect(lambda *_: _bind())
            for dspin in root.findChildren(QDoubleSpinBox):
                dspin.valueChanged.connect(lambda *_: _bind())
            for txt in root.findChildren(QTextEdit):
                txt.textChanged.connect(_bind)
            for plain in root.findChildren(QPlainTextEdit):
                plain.textChanged.connect(_bind)

    def _schedule_editor_sync(self) -> None:
        if self._pending_tab_sync:
            return
        self._pending_tab_sync = True

        def _apply():
            self._pending_tab_sync = False
            self._sync_editor_from_tab()

        QTimer.singleShot(90, _apply)

    def _sync_editor_from_tab(self) -> None:
        if self._editor_push_guard or self._tab_push_guard:
            return
        engine = self._current_engine()
        if engine is None:
            return
        try:
            getter = getattr(engine, "get_config", None)
            if not callable(getter):
                return
            cfg = getter(self) or {}
            if not isinstance(cfg, dict):
                cfg = {}
            text = json.dumps(cfg, ensure_ascii=False, indent=2) + "\n"
            if self.config_editor.toPlainText() == text:
                self._set_editor_status("Synced from tab", ok=True)
                return
            self._tab_push_guard = True
            try:
                self.config_editor.setPlainText(text)
            finally:
                self._tab_push_guard = False
            self._set_editor_status("Synced from tab", ok=True)
        except Exception as exc:
            self._set_editor_status(f"Sync from tab failed: {exc}", ok=False)

    def _on_editor_text_changed(self) -> None:
        if self._tab_push_guard:
            return
        if self._pending_editor_apply:
            return
        self._pending_editor_apply = True

        def _apply():
            self._pending_editor_apply = False
            self._apply_editor_to_tab()

        QTimer.singleShot(90, _apply)

    def _apply_editor_to_tab(self) -> None:
        if self._editor_push_guard or self._tab_push_guard:
            return
        engine = self._current_engine()
        if engine is None:
            return
        raw = self.config_editor.toPlainText()
        try:
            data = json.loads(raw) if raw.strip() else {}
            if not isinstance(data, dict):
                self._set_editor_status("Config must be a JSON object", ok=False)
                return
        except Exception as exc:
            self._set_editor_status(f"Invalid JSON: {exc}", ok=False)
            return
        try:
            setter = getattr(engine, "set_config", None)
            if callable(setter):
                self._editor_push_guard = True
                try:
                    setter(self, data)
                finally:
                    self._editor_push_guard = False
            self._set_editor_status("Applied to tab", ok=True)
        except Exception as exc:
            self._set_editor_status(f"Apply failed: {exc}", ok=False)

    def _set_editor_status(self, message: str, *, ok: bool) -> None:
        self.editor_status.setText(message)
        if ok:
            self.editor_status.setStyleSheet("color: #4caf50;")
            self.statusBar.showMessage(message)
        else:
            self.editor_status.setStyleSheet("color: #f44336;")
            self.statusBar.showMessage(message)

    def _save_current_engine_config(self) -> None:
        try:
            manual_ws = self.workspace_edit.text().strip() if self.workspace_edit else ""
            if manual_ws and not self.workspace_dir:
                try:
                    self.workspace_dir = os.path.abspath(manual_ws)
                except Exception:
                    self.workspace_dir = manual_ws
                self._refresh_workspace_header()
            if not self.workspace_dir:
                QMessageBox.warning(
                    self,
                    "Workspace Required",
                    "Workspace is required to save engine config.",
                )
                self._set_editor_status("Workspace is required", ok=False)
                return
            if not Path(self.workspace_dir).is_dir():
                QMessageBox.warning(
                    self,
                    "Invalid Workspace",
                    "Workspace path is invalid or does not exist.",
                )
                self._set_editor_status("Invalid workspace path", ok=False)
                return
            from Core.EngineConfigManager import save_engine_config_for_gui

            self._apply_editor_to_tab()
            current_eid = self._current_engine_id()
            if not current_eid:
                self._set_editor_status("No engine tab selected", ok=False)
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    "No engine tab selected.",
                )
                return
            saved = save_engine_config_for_gui(self, current_eid)
            if saved:
                self._set_editor_status("Config saved", ok=True)
                QMessageBox.information(
                    self,
                    "Config Saved",
                    f"Configuration saved for engine: {current_eid}",
                )
            else:
                self._set_editor_status("Config save failed", ok=False)
                QMessageBox.warning(
                    self,
                    "Save Failed",
                    f"Unable to save configuration for engine: {current_eid}",
                )
        except Exception as exc:
            self._set_editor_status(f"Save failed: {exc}", ok=False)
            QMessageBox.warning(self, "Save Failed", str(exc))


def launch_prog_engine_gui(
    engine_id: str | None,
    workspace_dir: Optional[str] = None,
    language: str = "en",
    theme: str = "dark",
) -> int:
    """Launch dedicated programmatic engine config GUI."""
    if not workspace_dir:
        raise ValueError("workspace is required for prog-engine GUI")
    app = QApplication(sys.argv)
    app.setApplicationName("PyCompiler ARK Prog Engine")
    app.setOrganizationName("raidos23")

    window = ProgEngineConfigGui(
        engine_id=engine_id,
        workspace_dir=workspace_dir,
        language=language,
        theme=theme,
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_engines_gui())
