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
BcaslOnlyMod GUI - Interface Graphique pour les Plugins BCASL

Interface complète pour exécuter et configurer les plugins BCASL
indépendamment de l'application principale PyCompiler ARK.

Fournit une interface utilisateur moderne permettant de:
- Découvrir et lister les plugins BCASL disponibles
- Activer/désactiver les plugins
- Réordonner l'exécution des plugins
- Exécuter les plugins de pré-compilation
- Afficher les rapports d'exécution
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt, QSize, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QProgressBar,
    QCheckBox,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
    QStatusBar,
    QMessageBox,
    QFrame,
    QSplitter,
    QSizePolicy,
    QFileDialog,
    QLineEdit,
)
from PySide6.QtGui import QFont, QIcon

# Importations BCASL
from bcasl import (
    BCASL,
    BcPluginBase,
    PluginMeta,
    PreCompileContext,
    ExecutionReport,
)
from bcasl.Loader import (
    _discover_bcasl_meta,
    _load_workspace_config,
)
from bcasl.tagging import (
    compute_tag_order,
    get_tag_phase_name,
)

# Importations Core
from Core.allversion import get_core_version, get_bcasl_version


def tr(en_text: str, fr_text: str) -> str:
    """Fonction de traduction simple pour BcaslOnlyMod.

    Utilise la variable globale _CURRENT_LANGUAGE pour déterminer la langue.
    """
    return fr_text if _CURRENT_LANGUAGE == "fr" else en_text


# Variable globale pour la langue (mise à jour par l'application)
_CURRENT_LANGUAGE = "en"


class BcaslExecutionThread(QThread):
    """Thread pour exécuter les plugins BCASL sans bloquer l'UI."""

    progress = Signal(int, int)  # current, total
    log_message = Signal(str)
    finished = Signal(object)  # ExecutionReport
    error = Signal(str)

    def __init__(
        self,
        workspace_root: Path,
        Plugins_dir: Path,
        plugin_order: List[str],
        enabled_plugins: Dict[str, bool],
        config: Dict[str, Any],
        plugin_timeout: float = 0.0,
        venv_path: Optional[str] = None,
    ):
        super().__init__()
        self.workspace_root = workspace_root
        self.Plugins_dir = Plugins_dir
        self.plugin_order = plugin_order
        self.enabled_plugins = enabled_plugins
        self.config = config
        self.plugin_timeout = plugin_timeout
        self.venv_path = venv_path

    def run(self):
        """Exécute les plugins BCASL dans un thread séparé."""
        try:
            # Log du venv utilisé
            if self.venv_path:
                self.log_message.emit(
                    f"🐍 Utilisation de l'environnement virtuel: {self.venv_path}"
                )
            
            # Créer le gestionnaire BCASL
            manager = BCASL(
                self.workspace_root,
                config=self.config,
                plugin_timeout_s=self.plugin_timeout,
            )

            # Charger les plugins
            loaded, errors = manager.load_plugins_from_directory(self.Plugins_dir)
            self.log_message.emit(
                f"🔌 BCASL: {loaded} plugin(s) chargé(s) depuis Plugins/"
            )

            for mod, msg in errors or []:
                self.log_message.emit(f"⚠️ Plugin '{mod}': {msg}")

            # Appliquer la configuration
            for pid, enabled in self.enabled_plugins.items():
                if not enabled:
                    manager.disable_plugin(pid)

            # Appliquer les priorités
            for idx, pid in enumerate(self.plugin_order):
                try:
                    manager.set_priority(pid, idx)
                except Exception:
                    pass

            # Préparer le contexte
            workspace_meta = {
                "workspace_name": self.workspace_root.name,
                "workspace_path": str(self.workspace_root),
                "file_patterns": self.config.get("file_patterns", []),
                "exclude_patterns": self.config.get("exclude_patterns", []),
                "required_files": self.config.get("required_files", []),
            }

            # Exécuter les plugins
            ctx = PreCompileContext(
                self.workspace_root,
                config=self.config,
                workspace_metadata=workspace_meta,
            )

            report = manager.run_pre_compile(ctx)
            self.finished.emit(report)

        except Exception as e:
            self.error.emit(str(e))


class BcaslStandaloneGui(QMainWindow):
    """
    Interface graphique principale pour gérer les plugins BCASL.

    Cette classe fournit une interface utilisateur complète pour:
    - Lister les plugins BCASL disponibles avec leurs métadonnées
    - Activer/désactiver les plugins individuellement
    - Réordonner l'exécution des plugins
    - Exécuter les plugins de pré-compilation
    - Afficher les rapports d'exécution détaillés
    """

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        language: str = "en",
        theme: str = "dark",
    ):
        """
        Initialise l'interface Bcasl Standalone GUI.

        Args:
            workspace_dir: Chemin du workspace (optionnel)
            language: Code de langue ('en' ou 'fr')
            theme: Nom du thème ('light' ou 'dark')
        """
        super().__init__()

        self.workspace_dir = workspace_dir
        self.language = language
        self.theme = theme
        
        # État du venv
        self.venv_path: Optional[str] = None
        self.venv_manager = None

        # État de l'application
        self.plugins_meta: Dict[str, Dict[str, Any]] = {}
        self.execution_thread: Optional[BcaslExecutionThread] = None

        # Configuration de la fenêtre
        self.setWindowTitle(
            tr(
                "BCASL Standalone - Plugin Manager",
                "BCASL Standalone - Gestionnaire de Plugins",
            )
        )
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        # Charger la configuration
        self._load_config()

        # Configuration de l'interface
        self._setup_ui()
        self._apply_theme(theme)
        self._apply_language(language)

        # Découvrir les plugins
        self._discover_plugins()

        # Centrer la fenêtre
        self._center_window()

    def _load_config(self):
        """Charge la configuration BCASL du workspace."""
        from bcasl.Loader import _load_workspace_config

        self.config: Dict[str, Any] = {}
        self.Plugins_dir: Optional[Path] = None
        self.repo_root: Optional[Path] = None

        if self.workspace_dir:
            workspace_root = Path(self.workspace_dir).resolve()
            self.config = _load_workspace_config(workspace_root)

        # Répertoire des plugins
        try:
            self.repo_root = Path(__file__).resolve().parents[2]
            self.Plugins_dir = self.repo_root / "Plugins"
        except Exception:
            pass

        # Initialiser le gestionnaire de venv
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
            best_venv = self.venv_manager.select_best_venv(self.workspace_dir)
            if best_venv:
                self.venv_path = best_venv
                if self._is_valid(self.venv_path_edit):
                    self.venv_path_edit.setText(best_venv)
                self._log(f"✅ Venv auto-détecté: {best_venv}")
            else:
                # Essayer de détecter un venv dans le workspace
                existing, default_path = self.venv_manager._detect_venv_in(self.workspace_dir)
                if existing:
                    self.venv_path = existing
                    if self._is_valid(self.venv_path_edit):
                        self.venv_path_edit.setText(existing)
                    self._log(f"✅ Venv existant trouvé: {existing}")
        except Exception as e:
            self._log(f"⚠️ Erreur détection venv: {e}")

    def _setup_ui(self):
        """Configure l'interface utilisateur."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # === En-tête ===
        header_layout = QHBoxLayout()

        title_label = QLabel(tr("BCASL Plugins", "Plugins BCASL"))
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #4da6ff;")
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # === Section Workspace ===
        workspace_layout = QHBoxLayout()
        workspace_layout.setSpacing(8)

        # Label workspace
        workspace_label = QLabel(tr("Workspace:", "Workspace :"))
        workspace_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        workspace_layout.addWidget(workspace_label)

        # Champ de显示 du chemin du workspace
        self.workspace_path_edit = QLineEdit()
        self.workspace_path_edit.setPlaceholderText(
            tr("Select a workspace folder...", "Sélectionner un dossier workspace...")
        )
        self.workspace_path_edit.setReadOnly(True)
        self.workspace_path_edit.setMinimumWidth(250)
        self.workspace_path_edit.setMaximumWidth(400)
        self.workspace_path_edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """
        )
        # Afficher le workspace actuel si défini
        if self.workspace_dir:
            self.workspace_path_edit.setText(str(Path(self.workspace_dir).resolve()))
        workspace_layout.addWidget(self.workspace_path_edit)

        # Bouton sélectionner workspace
        self.btn_select_workspace = QPushButton("📁")
        self.btn_select_workspace.setMinimumSize(32, 28)
        self.btn_select_workspace.setToolTip(
            tr("Select workspace folder", "Sélectionner le dossier workspace")
        )
        self.btn_select_workspace.setStyleSheet(
            """
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
        """
        )
        self.btn_select_workspace.clicked.connect(self._select_workspace)
        workspace_layout.addWidget(self.btn_select_workspace)

        # Bouton clear workspace
        self.btn_clear_workspace = QPushButton("✕")
        self.btn_clear_workspace.setMinimumSize(32, 28)
        self.btn_clear_workspace.setToolTip(
            tr("Clear workspace", "Effacer le workspace")
        )
        self.btn_clear_workspace.setStyleSheet(
            """
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
        """
        )
        self.btn_clear_workspace.clicked.connect(self._clear_workspace)
        workspace_layout.addWidget(self.btn_clear_workspace)

        header_layout.addLayout(workspace_layout)

        header_layout.addSpacing(20)

        # === Section Venv ===
        venv_layout = QHBoxLayout()
        venv_layout.setSpacing(8)

        # Label venv
        venv_label = QLabel(tr("Venv:", "Venv :"))
        venv_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        venv_layout.addWidget(venv_label)

        # Champ d'affichage du chemin du venv
        self.venv_path_edit = QLineEdit()
        self.venv_path_edit.setPlaceholderText(
            tr("Select a virtual environment...", "Sélectionner un environnement virtuel...")
        )
        self.venv_path_edit.setReadOnly(True)
        self.venv_path_edit.setMinimumWidth(200)
        self.venv_path_edit.setMaximumWidth(300)
        self.venv_path_edit.setStyleSheet(
            """
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #404040;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 11px;
            }
        """
        )
        venv_layout.addWidget(self.venv_path_edit)

        # Bouton sélectionner venv
        self.btn_select_venv = QPushButton("📁")
        self.btn_select_venv.setMinimumSize(32, 28)
        self.btn_select_venv.setToolTip(
            tr("Select virtual environment folder", "Sélectionner le dossier venv")
        )
        self.btn_select_venv.setStyleSheet(
            """
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
        """
        )
        self.btn_select_venv.clicked.connect(self._select_venv)
        venv_layout.addWidget(self.btn_select_venv)

        # Bouton auto-détecter venv
        self.btn_autodetect_venv = QPushButton("🔍")
        self.btn_autodetect_venv.setMinimumSize(32, 28)
        self.btn_autodetect_venv.setToolTip(
            tr("Auto-detect best virtual environment", "Auto-détecter le meilleur venv")
        )
        self.btn_autodetect_venv.setStyleSheet(
            """
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
        """
        )
        self.btn_autodetect_venv.clicked.connect(self._autodetect_venv)
        venv_layout.addWidget(self.btn_autodetect_venv)

        # Bouton clear venv
        self.btn_clear_venv = QPushButton("✕")
        self.btn_clear_venv.setMinimumSize(32, 28)
        self.btn_clear_venv.setToolTip(
            tr("Clear venv selection", "Effacer la sélection venv")
        )
        self.btn_clear_venv.setStyleSheet(
            """
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
        """
        )
        self.btn_clear_venv.clicked.connect(self._clear_venv)
        venv_layout.addWidget(self.btn_clear_venv)

        header_layout.addLayout(venv_layout)

        header_layout.addSpacing(20)

        # Version info
        version_text = tr(
            f"Core: {get_core_version()} | BCASL: {get_bcasl_version()}",
            f"Core: {get_core_version()} | BCASL: {get_bcasl_version()}",
        )
        version_label = QLabel(version_text)
        version_label.setStyleSheet("color: #888; font-size: 11px;")
        header_layout.addWidget(version_label)

        main_layout.addLayout(header_layout)

        # === Séparateur ===
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #404040; max-height: 2px;")
        main_layout.addWidget(separator)

        # === Splitter principal ===
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(main_splitter)

        # === Panneau supérieur ===
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # === Section Configuration des plugins (gauche) ===
        config_container = QWidget()
        config_layout = QVBoxLayout(config_container)
        config_layout.setSpacing(10)
        config_layout.setContentsMargins(3, 3, 3, 3)

        # Groupe activation globale
        global_group = QGroupBox(tr("Global Settings", "Paramètres Globaux"))
        global_layout = QVBoxLayout()
        global_layout.setSpacing(5)

        self.global_enable_check = QCheckBox(tr("Enable BCASL", "Activer BCASL"))
        self.global_enable_check.setChecked(True)
        self.global_enable_check.toggled.connect(self._on_global_toggle)
        global_layout.addWidget(self.global_enable_check)

        # Info label
        self.global_info_label = QLabel(
            tr(
                "BCASL executes plugins before compilation.\n"
                "Configure plugins and their execution order below.",
                "BCASL exécute les plugins avant la compilation.\n"
                "Configurez les plugins et leur ordre d'exécution ci-dessous.",
            )
        )
        self.global_info_label.setStyleSheet("color: #888; font-size: 11px;")
        global_layout.addWidget(self.global_info_label)

        global_group.setLayout(global_layout)
        config_layout.addWidget(global_group)

        # Groupe plugins
        plugins_group = QGroupBox(tr("Plugins", "Plugins"))
        plugins_group.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        plugins_layout = QVBoxLayout()
        plugins_layout.setSpacing(5)

        # Liste des plugins
        self.plugins_list = QListWidget()
        self.plugins_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.plugins_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.plugins_list.setAlternatingRowColors(True)
        self.plugins_list.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        plugins_layout.addWidget(self.plugins_list)

        # Boutons de navigation
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(5)

        self.btn_move_up = QPushButton("⬆️")
        self.btn_move_up.setMinimumSize(40, 30)
        self.btn_move_up.clicked.connect(self._move_plugin_up)
        nav_layout.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("⬇️")
        self.btn_move_down.setMinimumSize(40, 30)
        self.btn_move_down.clicked.connect(self._move_plugin_down)
        nav_layout.addWidget(self.btn_move_down)

        nav_layout.addStretch()

        # Bouton refresh
        self.btn_refresh = QPushButton("🔄")
        self.btn_refresh.setMinimumSize(40, 30)
        self.btn_refresh.setToolTip(
            tr("Refresh plugins list", "Rafraîchir la liste des plugins")
        )
        self.btn_refresh.clicked.connect(self._discover_plugins)
        nav_layout.addWidget(self.btn_refresh)

        plugins_layout.addLayout(nav_layout)
        plugins_group.setLayout(plugins_layout)
        config_layout.addWidget(plugins_group)

        top_splitter.addWidget(config_container)

        # === Section Log et rapport (droite) ===
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setSpacing(5)
        log_layout.setContentsMargins(3, 3, 3, 3)

        # Groupe exécution
        execution_group = QGroupBox(tr("Execution", "Exécution"))
        execution_layout = QVBoxLayout()
        execution_layout.setSpacing(8)

        # Boutons d'action
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)

        self.btn_run = QPushButton(tr("▶ Run Plugins", "▶ Exécuter les Plugins"))
        self.btn_run.setMinimumHeight(35)
        self.btn_run.setStyleSheet(
            """
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """
        )
        self.btn_run.clicked.connect(self._run_plugins)
        actions_layout.addWidget(self.btn_run)

        self.btn_cancel = QPushButton(tr("Cancel", "Annuler"))
        self.btn_cancel.setMinimumHeight(35)
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.setStyleSheet(
            """
            QPushButton {
                background-color: #f44336;
                color: white;
                font-size: 14px;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #666;
            }
        """
        )
        self.btn_cancel.clicked.connect(self._cancel_execution)
        actions_layout.addWidget(self.btn_cancel)

        actions_layout.addStretch()

        # Bouton effacer log
        self.btn_clear_log = QPushButton(tr("Clear Log", "Effacer Log"))
        self.btn_clear_log.setMinimumHeight(35)
        self.btn_clear_log.clicked.connect(self._clear_log)
        actions_layout.addWidget(self.btn_clear_log)

        execution_layout.addLayout(actions_layout)

        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimumHeight(16)
        self.progress_bar.setValue(0)
        execution_layout.addWidget(self.progress_bar)

        execution_group.setLayout(execution_layout)
        log_layout.addWidget(execution_group)

        # Groupe log
        log_group = QGroupBox(tr("Execution Log", "Journal d'Exécution"))
        log_layout_inner = QVBoxLayout()
        log_layout_inner.setSpacing(3)

        self.log_text = QTextEdit()
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setReadOnly(True)
        self.log_text.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
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

        log_group.setLayout(log_layout_inner)
        log_layout.addWidget(log_group)

        top_splitter.addWidget(log_container)

        # Définir les proportions (40% config, 60% log)
        top_splitter.setSizes([400, 600])

        main_splitter.addWidget(top_splitter)

        # === Barre de statut ===
        self.statusBar = QStatusBar()
        self.statusBar.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.statusBar.setMinimumHeight(20)
        if hasattr(self, "setStatusBar"):
            self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(tr("Ready", "Prêt"))

        # Définir les proportions du splitter vertical
        main_splitter.setSizes([500, 200])

    def _center_window(self):
        """Centre la fenêtre sur l'écran."""
        try:
            screen_geometry = QApplication.primaryScreen().geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)
        except Exception:
            pass

    def _select_workspace(self):
        """Ouvre une boîte de dialogue pour sélectionner le workspace."""
        current_path = self.workspace_dir or ""

        folder = QFileDialog.getExistingDirectory(
            self,
            tr("Select Workspace Folder", "Sélectionner le dossier Workspace"),
            current_path,
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            self.workspace_dir = folder
            self.workspace_path_edit.setText(str(Path(folder).resolve()))

            # Recharger la configuration et les plugins
            self._load_config()
            self._discover_plugins()

            self._log(
                tr(
                    f"Workspace selected: {folder}",
                    f"Workspace sélectionné : {folder}",
                )
            )
            self.statusBar.showMessage(tr("Workspace updated", "Workspace mis à jour"))

    def _clear_workspace(self):
        """Efface la sélection du workspace."""
        self.workspace_dir = None
        self.workspace_path_edit.clear()
        self.workspace_path_edit.setPlaceholderText(
            tr("Select a workspace folder...", "Sélectionner un dossier workspace...")
        )

        # Recharger avec workspace vide
        self._load_config()
        self.plugins_meta = {}
        self._discover_plugins()

        self._log(tr("Workspace cleared", "Workspace effacé"))
        self.statusBar.showMessage(tr("Workspace cleared", "Workspace effacé"))

    def _select_venv(self):
        """Ouvre une boîte de dialogue pour sélectionner le venv."""
        if not self.venv_manager:
            QMessageBox.warning(
                self,
                tr("Warning", "Avertissement"),
                tr(
                    "Venv manager not initialized.",
                    "Gestionnaire de venv non initialisé.",
                ),
            )
            return

        current_path = self.venv_path or ""

        folder = QFileDialog.getExistingDirectory(
            self,
            tr("Select Virtual Environment Folder", "Sélectionner le dossier Venv"),
            current_path,
            QFileDialog.Option.ShowDirsOnly,
        )

        if folder:
            # Valider que c'est un venv valide
            ok, reason = self.venv_manager.validate_venv_strict(folder)
            if ok:
                self.venv_path = folder
                self.venv_path_edit.setText(folder)
                self._log(
                    tr(
                        f"Virtual environment selected: {folder}",
                        f"Environnement virtuel sélectionné : {folder}",
                    )
                )
                self.statusBar.showMessage(tr("Venv updated", "Venv mis à jour"))
            else:
                QMessageBox.warning(
                    self,
                    tr("Invalid Venv", "Venv invalide"),
                    tr(
                        f"The selected folder is not a valid virtual environment:\n{reason}",
                        f"Le dossier sélectionné n'est pas un environnement virtuel valide :\n{reason}",
                    ),
                )
                self._log(
                    tr(
                        f"Invalid venv selected: {reason}",
                        f"Venv invalide sélectionné : {reason}",
                    )
                )

    def _autodetect_venv(self):
        """Auto-détecte le meilleur venv disponible."""
        if not self.venv_manager:
            QMessageBox.warning(
                self,
                tr("Warning", "Avertissement"),
                tr(
                    "Venv manager not initialized.",
                    "Gestionnaire de venv non initialisé.",
                ),
            )
            return

        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                tr("Warning", "Avertissement"),
                tr(
                    "Please select a workspace folder first.",
                    "Veuillez d'abord sélectionner un dossier workspace.",
                ),
            )
            return

        self._log(tr("Auto-detecting virtual environment...", "Auto-détection de l'environnement virtuel..."))

        # Chercher d'abord dans le workspace
        best_venv = self.venv_manager.select_best_venv(self.workspace_dir)
        
        if best_venv:
            self.venv_path = best_venv
            self.venv_path_edit.setText(best_venv)
            self._log(
                tr(
                    f"Best venv auto-detected: {best_venv}",
                    f"Meilleur venv auto-détecté : {best_venv}",
                )
            )
            self.statusBar.showMessage(tr("Venv auto-detected", "Venv auto-détecté"))
        else:
            # Essayer de trouver n'importe quel venv dans le workspace
            existing, default_path = self.venv_manager._detect_venv_in(self.workspace_dir)
            if existing:
                self.venv_path = existing
                self.venv_path_edit.setText(existing)
                self._log(
                    tr(
                        f"Existing venv found: {existing}",
                        f"Venv existant trouvé : {existing}",
                    )
                )
            else:
                self._log(
                    tr(
                        "No virtual environment found in workspace.",
                        "Aucun environnement virtuel trouvé dans le workspace.",
                    )
                )
                QMessageBox.information(
                    self,
                    tr("No Venv Found", "Aucun Venv Trouvé"),
                    tr(
                        "No valid virtual environment was found in the workspace.\n"
                        "Please select one manually or create a new venv.",
                        "Aucun environnement virtuel valide n'a été trouvé dans le workspace.\n"
                        "Veuillez en sélectionner un manuellement ou créer un nouveau venv.",
                    ),
                )

    def _clear_venv(self):
        """Efface la sélection du venv."""
        self.venv_path = None
        self.venv_path_edit.clear()
        self.venv_path_edit.setPlaceholderText(
            tr("Select a virtual environment...", "Sélectionner un environnement virtuel...")
        )

        self._log(tr("Venv selection cleared", "Sélection venv effacée"))
        self.statusBar.showMessage(tr("Venv selection cleared", "Sélection venv effacée"))

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
            self.setStyleSheet(
                """
                QWidget {
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
                QListWidget {
                    background-color: #2d2d2d;
                    color: #ffffff;
                    border: 1px solid #404040;
                    border-radius: 4px;
                    padding: 4px;
                }
                QListWidget::item:selected {
                    background-color: #4da6ff;
                    color: #ffffff;
                }
                QListWidget::item:alternate {
                    background-color: #2a2a2a;
                }
                QCheckBox {
                    color: #ffffff;
                    spacing: 5px;
                }
                QCheckBox::indicator {
                    width: 16px;
                    height: 16px;
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
                QWidget {
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
                QListWidget {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px;
                }
                QListWidget::item:selected {
                    background-color: #0066cc;
                    color: #ffffff;
                }
                QCheckBox {
                    color: #000000;
                    spacing: 5px;
                }
                QLineEdit {
                    background-color: #ffffff;
                    color: #000000;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 11px;
                }
                QPushButton {
                    background-color: #cccccc;
                    color: #000000;
                    border-radius: 4px;
                    padding: 4px 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #4da6ff;
                }
                QStatusBar {
                    background-color: #e0e0e0;
                    color: #666666;
                    font-size: 11px;
                }
            """
            )

    def _apply_language(self, lang_code: str):
        """Applique la langue de l'interface."""
        global _CURRENT_LANGUAGE
        self.language = lang_code
        _CURRENT_LANGUAGE = lang_code

        # Les traductions sont gérées via tr() dans setup_ui
        # Note: On utilise une vérification pour éviter l'erreur si log_text n'est pas encore initialisé
        if self._is_valid(self.log_text):
            try:
                self._log(tr("Language set to English", "Langue définie sur Français"))
            except (RuntimeError, AttributeError):
                pass  # Ignorer si le widget a été supprimé

    def _discover_plugins(self):
        """Découvre et affiche les plugins BCASL disponibles."""
        # Vérifier que les widgets sont initialisés et valides
        if not self._is_valid(self.plugins_list):
            return
        
        try:
            self.plugins_list.clear()
        except (RuntimeError, AttributeError):
            return  # Widget supprimé
        
        self.plugins_meta = {}

        if not self.Plugins_dir or not self.Plugins_dir.exists():
            self._log(
                tr("Plugins directory not found", "Répertoire Plugins non trouvé")
            )
            return

        # Découvrir les plugins
        self.plugins_meta = _discover_bcasl_meta(self.Plugins_dir)

        if not self.plugins_meta:
            self._log(
                tr(
                    "No plugins detected in Plugins/",
                    "Aucun plugin détecté dans Plugins/",
                )
            )
            # Créer un message dans la liste
            try:
                item = QListWidgetItem(
                    tr("No plugins available", "Aucun plugin disponible")
                )
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.plugins_list.addItem(item)
            except (RuntimeError, AttributeError):
                pass  # Widget supprimé
            return

        # Trier les plugins par ordre de priorité (tags)
        try:
            order = compute_tag_order(self.plugins_meta)
        except Exception:
            order = sorted(self.plugins_meta.keys())

        # Ajouter les plugins à la liste
        for pid in order:
            meta = self.plugins_meta.get(pid, {})
            self._add_plugin_item(pid, meta)

        # Nombre de plugins
        count = len(self.plugins_meta)
        self._log(
            tr(f"Discovered {count} plugin(s)", f"{count} plugin(s) découvert(s)")
        )

    def _add_plugin_item(self, plugin_id: str, meta: Dict[str, Any]):
        """Ajoute un plugin à la liste."""
        name = meta.get("name", plugin_id)
        version = meta.get("version", "")
        description = meta.get("description", "")
        author = meta.get("author", "")
        tags = meta.get("tags", [])

        # Déterminer la phase d'exécution
        phase_name = ""
        if tags:
            phase_name = get_tag_phase_name(tags[0])

        # Construire le texte de l'item
        text = f"{name}"
        if version:
            text += f" v{version}"
        if phase_name:
            text += f" [{phase_name}]"

        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, plugin_id)

        # Déterminer si activé par défaut
        enabled = True
        try:
            pentry = self.config.get("plugins", {}).get(plugin_id, {})
            if isinstance(pentry, dict):
                enabled = pentry.get("enabled", True)
            elif isinstance(pentry, bool):
                enabled = pentry
        except Exception:
            enabled = True

        # Configurer les flags
        item.setFlags(
            item.flags()
            | Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setCheckState(
            Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked
        )

        # Tooltip avec les détails
        tooltip_parts = [f"ID: {plugin_id}"]
        if description:
            tooltip_parts.append(f"{tr('Description:', 'Description :')} {description}")
        if author:
            tooltip_parts.append(f"{tr('Author:', 'Auteur :')} {author}")
        if tags:
            tooltip_parts.append(f"{tr('Tags:', 'Tags :')} {', '.join(tags)}")
        if phase_name:
            tooltip_parts.append(f"{tr('Phase:', 'Phase :')} {phase_name}")

        item.setToolTip("\n".join(tooltip_parts))

        self.plugins_list.addItem(item)

    def _on_global_toggle(self, checked: bool):
        """Gère l'activation/désactivation globale de BCASL."""
        # Vérifier que la liste des plugins est valide
        if not self._is_valid(self.plugins_list):
            return
        
        # Activer/désactiver tous les items
        try:
            for i in range(self.plugins_list.count()):
                item = self.plugins_list.item(i)
                plugin_id = item.data(Qt.ItemDataRole.UserRole)
                if plugin_id:
                    item.setCheckState(
                        Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
                    )
        except (RuntimeError, AttributeError):
            return  # Widget supprimé

        # Activer/désactiver les contrôles
        if self._is_valid(self.plugins_list):
            self.plugins_list.setEnabled(checked)
        self.btn_move_up.setEnabled(checked)
        self.btn_move_down.setEnabled(checked)
        self.btn_run.setEnabled(checked)

        if checked:
            self._log(tr("BCASL enabled", "BCASL activé"))
        else:
            self._log(tr("BCASL disabled", "BCASL désactivé"))

    def _move_plugin_up(self):
        """Déplace le plugin sélectionné vers le haut."""
        # Vérifier que la liste des plugins est valide
        if not self._is_valid(self.plugins_list):
            return
        
        row = self.plugins_list.currentRow()
        if row <= 0:
            return

        try:
            item = self.plugins_list.takeItem(row)
            self.plugins_list.insertItem(row - 1, item)
            self.plugins_list.setCurrentRow(row - 1)
        except (RuntimeError, AttributeError):
            pass  # Widget supprimé

    def _move_plugin_down(self):
        """Déplace le plugin sélectionné vers le bas."""
        # Vérifier que la liste des plugins est valide
        if not self._is_valid(self.plugins_list):
            return
        
        row = self.plugins_list.currentRow()
        if row < 0 or row >= self.plugins_list.count() - 1:
            return

        try:
            item = self.plugins_list.takeItem(row)
            self.plugins_list.insertItem(row + 1, item)
            self.plugins_list.setCurrentRow(row + 1)
        except (RuntimeError, AttributeError):
            pass  # Widget supprimé

    def _get_plugin_order(self) -> List[str]:
        """Récupère l'ordre actuel des plugins."""
        # Vérifier que la liste des plugins est valide
        if not self._is_valid(self.plugins_list):
            return []
        
        order = []
        try:
            for i in range(self.plugins_list.count()):
                item = self.plugins_list.item(i)
                plugin_id = item.data(Qt.ItemDataRole.UserRole)
                if plugin_id:
                    order.append(plugin_id)
        except (RuntimeError, AttributeError):
            return []  # Widget supprimé
        return order

    def _get_enabled_plugins(self) -> Dict[str, bool]:
        """Récupère l'état d'activation des plugins."""
        # Vérifier que la liste des plugins est valide
        if not self._is_valid(self.plugins_list):
            return {}
        
        enabled = {}
        try:
            for i in range(self.plugins_list.count()):
                item = self.plugins_list.item(i)
                plugin_id = item.data(Qt.ItemDataRole.UserRole)
                if plugin_id:
                    enabled[plugin_id] = item.checkState() == Qt.CheckState.Checked
        except (RuntimeError, AttributeError):
            return {}  # Widget supprimé
        return enabled

    def _run_plugins(self):
        """Exécute les plugins BCASL."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                tr("Warning", "Avertissement"),
                tr(
                    "Please select a workspace folder first.",
                    "Veuillez d'abord sélectionner un dossier workspace.",
                ),
            )
            return

        workspace_root = Path(self.workspace_dir).resolve()

        if not workspace_root.exists():
            QMessageBox.warning(
                self,
                tr("Warning", "Avertissement"),
                tr(
                    "Workspace folder does not exist.",
                    "Le dossier workspace n'existe pas.",
                ),
            )
            return

        # Récupérer la configuration
        plugin_order = self._get_plugin_order()
        enabled_plugins = self._get_enabled_plugins()

        if not any(enabled_plugins.values()):
            QMessageBox.warning(
                self,
                tr("Warning", "Avertissement"),
                tr(
                    "No plugins enabled. Please enable at least one plugin.",
                    "Aucun plugin activé. Veuillez activer au moins un plugin.",
                ),
            )
            return

        # Récupérer le timeout
        try:
            env_timeout = float(
                __import__("os").environ.get("PYCOMPILER_BCASL_PLUGIN_TIMEOUT", "0")
            )
        except Exception:
            env_timeout = 0.0

        try:
            opt = self.config.get("options", {}) or {}
            cfg_timeout = (
                float(opt.get("plugin_timeout_s", 0.0))
                if isinstance(opt, dict)
                else 0.0
            )
        except Exception:
            cfg_timeout = 0.0

        plugin_timeout = cfg_timeout if cfg_timeout != 0.0 else env_timeout

        # Récupérer le chemin du venv
        venv_path = None
        if self.venv_path:
            venv_path = self.venv_path
        elif self.venv_manager and self.workspace_dir:
            # Auto-détecter si pas de venv sélectionné
            best_venv = self.venv_manager.select_best_venv(self.workspace_dir)
            if best_venv:
                venv_path = best_venv
                self.venv_path = venv_path
                if self._is_valid(self.venv_path_edit):
                    self.venv_path_edit.setText(venv_path)

        if venv_path:
            self._log(
                tr(
                    f"Using virtual environment: {venv_path}",
                    f"Utilisation de l'environnement virtuel : {venv_path}",
                )
            )

        # Désactiver les contrôles pendant l'exécution
        self.btn_run.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        if self._is_valid(self.plugins_list):
            self.plugins_list.setEnabled(False)
        self.btn_move_up.setEnabled(False)
        self.btn_move_down.setEnabled(False)
        self.global_enable_check.setEnabled(False)

        # Afficher la progression
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.statusBar.showMessage(tr("Running plugins...", "Exécution des plugins..."))

        # Logger le début
        self._log("=" * 50)
        self._log(tr("Starting BCASL execution", "Début de l'exécution BCASL"))
        self._log(tr(f"Workspace: {workspace_root}", f"Workspace: {workspace_root}"))
        if venv_path:
            self._log(tr(f"Venv: {venv_path}", f"Venv: {venv_path}"))
        enabled_count = sum(1 for v in enabled_plugins.values() if v)
        self._log(
            tr(f"Enabled plugins: {enabled_count}", f"Plugins activés: {enabled_count}")
        )
        self._log("=" * 50)

        # Créer et démarrer le thread
        self.execution_thread = BcaslExecutionThread(
            workspace_root=workspace_root,
            Plugins_dir=self.Plugins_dir,
            plugin_order=plugin_order,
            enabled_plugins=enabled_plugins,
            config=self.config,
            plugin_timeout=plugin_timeout,
            venv_path=venv_path,
        )

        self.execution_thread.log_message.connect(self._log)
        self.execution_thread.progress.connect(self._on_progress)
        self.execution_thread.finished.connect(self._on_execution_finished)
        self.execution_thread.error.connect(self._on_execution_error)

        self.execution_thread.start()

    def _cancel_execution(self):
        """Annule l'exécution des plugins."""
        if self.execution_thread and self.execution_thread.isRunning():
            self._log(tr("Cancelling execution...", "Annulation de l'exécution..."))
            self.execution_thread.terminate()
            self.execution_thread.wait(3000)

        self._on_execution_finished(None, cancelled=True)

    def _on_progress(self, current: int, total: int):
        """Met à jour la progression."""
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)

    def _on_execution_finished(
        self, report: Optional[ExecutionReport], cancelled: bool = False
    ):
        """Appelé lorsque l'exécution est terminée."""
        # Réactiver les contrôles
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if self._is_valid(self.plugins_list):
            self.plugins_list.setEnabled(self.global_enable_check.isChecked())
        self.btn_move_up.setEnabled(self.global_enable_check.isChecked())
        self.btn_move_down.setEnabled(self.global_enable_check.isChecked())
        self.global_enable_check.setEnabled(True)

        self.progress_bar.setVisible(False)

        if cancelled:
            self._log(tr("Execution cancelled", "Exécution annulée"))
            self.statusBar.showMessage(tr("Cancelled", "Annulé"))
            return

        self._log("=" * 50)

        if report is None:
            self._log(tr("Execution failed", "Échec de l'exécution"))
            self.statusBar.showMessage(tr("Failed", "Échec"))
            return

        # Afficher le rapport
        self._log(tr("Execution Report", "Rapport d'Exécution"))
        self._log("-" * 30)

        for item in report:
            state = "✓ OK" if item.success else f"✗ FAIL: {item.error}"
            self._log(f"  - {item.name}: {state} ({item.duration_ms:.1f} ms)")

        self._log("-" * 30)
        self._log(report.summary())

        if report.ok:
            self._log(
                tr(
                    "All plugins executed successfully",
                    "Tous les plugins exécutés avec succès",
                )
            )
            self.statusBar.showMessage(tr("Completed", "Terminé"))
        else:
            self._log(tr("Some plugins failed", "Certains plugins ont échoué"))
            self.statusBar.showMessage(
                tr("Completed with errors", "Terminé avec erreurs")
            )

        self._log("=" * 50)

    def _on_execution_error(self, error: str):
        """Gère les erreurs d'exécution."""
        self._log(f"⚠️ {tr('Error:', 'Erreur :')} {error}")
        self.statusBar.showMessage(tr("Error", "Erreur"))

        # Réactiver les contrôles
        self.btn_run.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        if self._is_valid(self.plugins_list):
            self.plugins_list.setEnabled(self.global_enable_check.isChecked())
        self.btn_move_up.setEnabled(self.global_enable_check.isChecked())
        self.btn_move_down.setEnabled(self.global_enable_check.isChecked())
        self.global_enable_check.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _clear_log(self):
        """Efface le log."""
        if self._is_valid(self.log_text):
            try:
                self.log_text.clear()
            except (RuntimeError, AttributeError):
                pass  # Ignorer si le widget a été supprimé

    def _log(self, message: str):
        """Ajoute un message au log."""
        # Vérifier que le widget existe et n'a pas été supprimé
        if not self._is_valid(self.log_text):
            return
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.append(f"[{timestamp}] {message}")
            # Défiler automatiquement vers le bas
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        except (RuntimeError, AttributeError):
            pass  # Ignorer si le widget a été supprimé


def launch_bcasl_gui(
    workspace_dir: Optional[str] = None,
    language: str = "en",
    theme: str = "dark",
) -> int:
    """Lance l'application Bcasl Standalone GUI.

    Args:
        workspace_dir: Chemin du workspace (optionnel)
        language: Code de langue ('en' ou 'fr')
        theme: Nom du thème ('light' ou 'dark')

    Returns:
        Code de retour de l'application
    """
    app = QApplication(sys.argv)
    app.setApplicationName("PyCompiler ARK++ BCASL")
    app.setOrganizationName("raidos23")

    window = BcaslStandaloneGui(
        workspace_dir=workspace_dir, language=language, theme=theme
    )
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(launch_bcasl_gui())
