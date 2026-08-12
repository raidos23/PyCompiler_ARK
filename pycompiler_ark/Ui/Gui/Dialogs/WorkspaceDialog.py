# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

"""WorkspaceDialog — Qt interactions for workspace selection and initialization.

This module manages Qt dialogs (QFileDialog, QMessageBox, loading dialogs)
and delegates all business logic to Core.WorkSpaceManager.SetupWorkspace."""

from __future__ import annotations
import asyncio
import os
from typing import Optional
from pathlib import Path
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from pycompiler_ark.Ui import output

from ..WorkspaceManipulation import SetupWorkspace
from ..Globals import _workspace_dir_lock
from ..WidgetsCreator import CompilationProcessDialog
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from pycompiler_ark.Core.deps_analyser import collect_internal_modules

from ...Cli.helpers import init_workspace


class WorkspaceDialog:
    """Qt workspace management (selection, application, initialization)."""

    @staticmethod
    def confirm_workspace_change(gui, folder: str) -> bool:
        """
        Confirm workspace change with the user.
        """
        try:
            from ..WidgetsCreator import show_msgbox

            title = "Confirmation"
            message = (
                f"Un plugin demande de changer le workspace vers :\n{folder}\n\n"
                "Voulez-vous continuer ?"
            )
            try:
                if gui and hasattr(gui, "tr"):
                    title = gui.tr("Confirmation", "Confirmation")
                    message = gui.tr(
                        f"Un plugin demande de changer le workspace vers :\n{folder}\n\n"
                        "Voulez-vous continuer ?",
                        f"A plugin requests changing the workspace to:\n{folder}\n\n"
                        "Do you want to continue?",
                    )
            except Exception:
                pass

            res = show_msgbox(
                "question", title, message, parent=gui, default="Yes"
            )
            return bool(res)
        except Exception:
            # If confirmation UI fails, accept by contract
            return True

    @staticmethod
    def select_workspace(gui_instance) -> Optional[str]:
        """
        Open a folder picker to select a workspace directory.

        Args:
          gui_instance: Main GUI instance.

        Returns:
          Selected workspace path, or `None` if canceled.
        """

        def _t(_key: str, fr: str, en: str) -> str:
            try:
                return gui_instance.tr(fr, en)
            except Exception:
                return en

        folder = QFileDialog.getExistingDirectory(
            gui_instance,
            _t(
                "action_select_workspace",
                "Choisir Workspace",
                "Select Workspace",
            ),
        )
        if folder:
            return folder
        return None

    @staticmethod
    def apply_workspace_selection(
        gui_instance, folder: str, source: str = "ui"
    ) -> bool:
        """
        Apply workspace selection and refresh all dependent GUI state.

        Args:
          gui_instance: Main GUI instance.
          folder: Target workspace directory path.
          source: Request origin (`"ui"` or `"plugin"`).

        Returns:
          `True` on success, `False` otherwise.
        """
        try:
            # Étape 1: afficher un feedback utilisateur pendant le chargement.
            try:
                loading_dialog = CompilationProcessDialog(
                    gui_instance.tr(
                        "Chargement de l'espace de travail",
                        "Loading workspace",
                    ),
                    gui_instance,
                )
                loading_dialog.set_status(
                    gui_instance.tr(
                        "📁 Chargement de l'espace de travail...",
                        "📁 Loading workspace...",
                    )
                )
                loading_dialog.btn_cancel.setEnabled(False)
                loading_dialog.show()
                QApplication.processEvents()
            except Exception:
                loading_dialog = None

            # Étape 2: valider/préparer le dossier workspace (via Core).
            if not folder:
                try:
                    output.warn(
                        (
                            "⚠️ Chemin de workspace vide fourni; aucune modification appliquée (accepté).",
                            "⚠️ Empty workspace path provided; no changes applied (accepted).",
                        ),
                        gui=gui_instance,
                    )
                except Exception:
                    pass
                if loading_dialog:
                    loading_dialog.close()
                return True

            # Création du dossier si nécessaire via Core logic
            if not os.path.isdir(folder):
                try:
                    os.makedirs(folder, exist_ok=True)
                    output.info(
                        (
                            f"📁 Dossier créé automatiquement: {folder}",
                            f"📁 Folder created automatically: {folder}",
                        ),
                        gui=gui_instance,
                    )
                except Exception as e:
                    output.warn(
                        (
                            f"⚠️ Impossible de créer le dossier: {e}",
                            f"⚠️ Unable to create folder: {e}",
                        ),
                        gui=gui_instance,
                    )

            # Étape 3: stopper proprement les compilations actives.
            if hasattr(gui_instance, "processes") and gui_instance.processes:
                label = "Plugins" if str(source).lower() == "plugin" else "UI"
                output.warn(
                    (
                        f"⛔ Arrêt des compilations en cours pour changer de workspace ({label}).",
                        f"⛔ Stopping ongoing builds to switch workspace ({label}).",
                    ),
                    gui=gui_instance,
                )
                try:
                    gui_instance.cancel_all_compilations()
                except Exception:
                    pass

            # Étape 4: appliquer le workspace en mémoire.
            gui_instance.workspace_dir = folder

            # Étape 5: synchroniser le cache global thread-safe.
            try:
                from ..Globals import _workspace_dir_cache

                with _workspace_dir_lock:
                    _workspace_dir_cache = folder
            except Exception:
                pass

            # Étape 6: mettre à jour les widgets UI.
            if hasattr(gui_instance, "label_folder"):
                gui_instance.label_folder.setText(
                    gui_instance.tr(
                        f"Dossier sélectionné : {folder}",
                        f"Selected folder: {folder}",
                    )
                )
            if hasattr(gui_instance, "label_workspace_status"):
                try:
                    tr_map = getattr(gui_instance, "_tr", None)
                    if isinstance(tr_map, dict):
                        tmpl = (
                            tr_map.get("label_workspace_status")
                            or "Workspace: {path}"
                        )
                        gui_instance.label_workspace_status.setText(
                            str(tmpl).replace("{path}", str(folder))
                        )
                    else:
                        gui_instance.label_workspace_status.setText(
                            gui_instance.tr(
                                f"Workspace : {folder}", f"Workspace: {folder}"
                            )
                        )
                except Exception:
                    pass

            gui_instance.python_files.clear()
            if hasattr(gui_instance, "file_list"):
                gui_instance.file_list.clear()

            # Scanner les fichiers (via Core)
            files = SetupWorkspace.list_python_files(folder)

            # Filtrer et ajouter à l'UI
            from pycompiler_ark.Core.Configs import (
                load_ark_config,
                should_exclude_file,
            )

            ark_config = load_ark_config(folder)

            workspace_cfg = ark_config.get("workspace", {})
            exclusion_patterns = []
            if isinstance(workspace_cfg, dict):
                exclusion_patterns = workspace_cfg.get("exclude", [])

            added_count = 0
            excluded_count = 0

            # Optimization: collect items and add them in batches to avoid UI overhead
            to_add_relative = []
            to_add_absolute = []

            import time

            last_pump = time.monotonic()

            for full_path in files:
                if should_exclude_file(full_path, folder, exclusion_patterns):
                    excluded_count += 1
                    continue

                to_add_absolute.append(full_path)
                relative_path = os.path.relpath(full_path, folder)
                to_add_relative.append(relative_path)

                added_count += 1

                # Periodically process events to keep UI responsive during heavy filtering
                if added_count % 500 == 0:
                    if time.monotonic() - last_pump > 0.05:
                        QApplication.processEvents()
                        last_pump = time.monotonic()

            # Apply to GUI state
            gui_instance.python_files.extend(to_add_absolute)

            # Batch update the UI list widget
            if hasattr(gui_instance, "file_list"):
                # Disabling updates during batch addition for performance
                gui_instance.file_list.setUpdatesEnabled(False)
                try:
                    gui_instance.file_list.addItems(to_add_relative)
                finally:
                    gui_instance.file_list.setUpdatesEnabled(True)

            if excluded_count > 0:
                output.info(
                    (
                        f"⏩ Exclusion appliquée : {excluded_count} fichier(s) exclu(s) selon ark.yml",
                        f"⏩ Exclusion applied: {excluded_count} file(s) excluded according to ark.yml",
                    ),
                    gui=gui_instance,
                )

            # Rafraîchir les autres composants UI
            try:
                if hasattr(gui_instance, "apply_file_filter"):
                    gui_instance.apply_file_filter()
                if hasattr(gui_instance, "load_entrypoint_from_config"):
                    gui_instance.load_entrypoint_from_config()
                if hasattr(gui_instance, "update_command_preview"):
                    gui_instance.update_command_preview()
                gui_instance.save_preferences()
            except Exception:
                pass

            # Étape 7: gérer le Venv (interactions UI)
            if (
                hasattr(gui_instance, "venv_manager")
                and gui_instance.venv_manager
            ):
                if str(source).lower() == "plugin":
                    gui_instance.venv_manager.setup_workspace(
                        folder, check_tools=False
                    )
                else:
                    if not gui_instance.venv_manager.apply_workspace_pref(
                        folder
                    ):
                        # Proposer création ou sélection
                        def _t(fr, en):
                            return gui_instance.tr(fr, en)

                        title = _t("Configuration du Venv", "Venv setup")
                        msg = _t(
                            "Créer un venv automatiquement ou sélectionner un venv (Python système inclus).",
                            "Create a venv automatically or select a venv (System Python included).",
                        )
                        box = QMessageBox(gui_instance)
                        box.setWindowTitle(title)
                        box.setText(msg)
                        btn_auto = box.addButton(
                            _t("Créer un venv", "Create venv"),
                            QMessageBox.AcceptRole,
                        )
                        btn_manual = box.addButton(
                            _t("Sélectionner un Venv", "Select Venv"),
                            QMessageBox.ActionRole,
                        )
                        box.setDefaultButton(btn_auto)
                        box.exec()

                        if box.clickedButton() == btn_manual:
                            gui_instance.venv_manager.select_venv_manually()
                        else:
                            gui_instance.venv_manager.setup_workspace(
                                folder, check_tools=False
                            )

            # Étape 8: recharger les configs engines
            try:
                from ....Core.engine.ConfigManager import (
                    apply_engine_configs_for_workspace,
                )

                apply_engine_configs_for_workspace(gui_instance, folder)
            except Exception:
                pass

            if loading_dialog:
                loading_dialog.close()

            return True

        except Exception as e:
            output.error(
                (
                    f"❌ Échec application workspace: {e}",
                    f"❌ Failed to apply workspace: {e}",
                ),
                gui=gui_instance,
            )
            if loading_dialog:
                loading_dialog.close()
            return False

    @staticmethod
    def open_ark_config(gui_instance):
        """
        Open `ark.yml` with the system default editor.
        """
        workspace_dir = getattr(gui_instance, "workspace_dir", None)
        if not workspace_dir:
            QMessageBox.warning(
                gui_instance,
                gui_instance.tr("Attention", "Warning"),
                gui_instance.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return

        config_path = os.path.join(workspace_dir, "ark.yml")

        if not os.path.exists(config_path):
            try:
                from pycompiler_ark.Core.Configs import (
                    create_default_ark_config,
                )

                if create_default_ark_config(workspace_dir):
                    output.info(
                        (
                            "📋 Fichier ark.yml créé.",
                            "📋 ark.yml file created.",
                        ),
                        gui=gui_instance,
                    )
            except Exception as e:
                QMessageBox.critical(
                    gui_instance,
                    gui_instance.tr("Erreur", "Error"),
                    gui_instance.tr(
                        f"Impossible de créer ark.yml: {e}",
                        f"Failed to create ark.yml: {e}",
                    ),
                )
                return

        # Logique d'ouverture système (pure logic déléguée à Core si possible,
        # mais ici c'est du shell-out donc acceptable en UI helper)
        try:
            import platform
            import subprocess

            system = platform.system()
            if system == "Windows":
                os.startfile(config_path)
            elif system == "Darwin":
                subprocess.run(["open", config_path])
            else:
                subprocess.run(["xdg-open", config_path])
            output.info(
                (
                    f"📝 Ouverture de {config_path}",
                    f"📝 Opening {config_path}",
                ),
                gui=gui_instance,
            )
        except Exception as e:
            QMessageBox.warning(
                gui_instance,
                gui_instance.tr("Attention", "Warning"),
                gui_instance.tr(
                    f"Impossible d'ouvrir le fichier: {e}",
                    f"Failed to open file: {e}",
                ),
            )


class InitWorkspaceDialog(QDialog):
    """Dialog to initialize a new ARK workspace."""

    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self.setWindowTitle(
            gui.tr("Initialiser le projet", "init_project_title")
        )
        self.resize(500, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Form
        form = QFormLayout()

        # Entry Point
        self.edit_entry = QLineEdit()
        self.edit_entry.setPlaceholderText("main.py")
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self._browse_entry)

        row_entry = QHBoxLayout()
        row_entry.addWidget(self.edit_entry)
        row_entry.addWidget(btn_browse)

        form.addRow(
            self.gui.tr("Point d'entrée :", "init_project_entry"), row_entry
        )

        # Options
        self.chk_reqs = QCheckBox(
            self.gui.tr("Générer requirements.txt", "init_project_gen_reqs")
        )
        self.chk_reqs.setChecked(True)
        form.addRow("", self.chk_reqs)

        self.chk_venv = QCheckBox(
            self.gui.tr(
                "Créer un environnement virtuel (venv)",
                "init_project_create_venv",
            )
        )
        self.chk_venv.setChecked(False)
        form.addRow("", self.chk_venv)

        self.chk_install = QCheckBox(
            self.gui.tr(
                "Installer les dépendances", "init_project_install_reqs"
            )
        )
        self.chk_install.setChecked(False)
        self.chk_install.setEnabled(False)
        self.chk_venv.toggled.connect(self.chk_install.setEnabled)
        form.addRow("", self.chk_install)

        self.chk_apply_internal = QCheckBox(
            self.gui.tr(
                "Appliquer les modules internes",
                "Apply internal modules",
            )
        )
        self.chk_apply_internal.setChecked(False)
        form.addRow("", self.chk_apply_internal)

        layout.addLayout(form)

        # Note
        note = QLabel(
            self.gui.tr(
                "Note : Cela va créer un fichier ark.yml et configurer la structure du projet.",
                "init_project_note",
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(note)

        scan_note = QLabel(
            self.gui.tr(
                "Si activé, les modules internes seront proposés pour build.include avant écriture.",
                "If enabled, internal modules will be proposed for build.include before writing.",
            )
        )
        scan_note.setWordWrap(True)
        scan_note.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(scan_note)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(self.gui.tr("Annuler", "action_cancel"))
        btn_cancel.clicked.connect(self.reject)

        self.btn_init = QPushButton(
            self.gui.tr("Initialiser", "action_init_project")
        )
        self.btn_init.setDefault(True)
        self.btn_init.clicked.connect(self._on_init)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_init)
        layout.addLayout(btn_row)

    def _browse_entry(self):
        ws = getattr(self.gui, "workspace_dir", os.getcwd())
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.gui.tr("Choisir le point d'entrée", "Choose entrypoint"),
            ws,
            "Python Files (*.py)",
        )
        if path:
            try:
                rel = os.path.relpath(path, ws)
                if rel.startswith(".."):
                    self.edit_entry.setText(path)
                else:
                    self.edit_entry.setText(rel)
            except Exception:
                self.edit_entry.setText(path)

    def _on_init(self):
        ws = getattr(self.gui, "workspace_dir", None)
        if not ws:
            QMessageBox.warning(
                self,
                "Error",
                self.gui.tr(
                    "Aucun workspace sélectionné.", "msg_no_workspace_text"
                ),
            )
            return

        entry = self.edit_entry.text().strip()
        if not entry:
            QMessageBox.warning(
                self,
                "Error",
                self.gui.tr(
                    "Veuillez spécifier un point d'entrée.",
                    "Please specify an entry point.",
                ),
            )
            return

        self.btn_init.setEnabled(False)
        try:
            apply_internal = bool(self.chk_apply_internal.isChecked())
            effective_auto_confirm = False
            internal_modules = []
            if apply_internal:
                try:
                    internal_modules = sorted(
                        collect_internal_modules(str(Path(ws))),
                        key=lambda item: item.lower(),
                    )
                except Exception:
                    internal_modules = []

                if internal_modules:
                    title = self.gui.tr(
                        "Confirmer l'application interne",
                        "Confirm internal apply",
                    )
                    message = self.gui.tr(
                        "Modules internes à appliquer :\n{modules}\n\nLes ajouter à build.include ?",
                        "Internal modules to apply:\n{modules}\n\nAdd them to build.include?",
                    ).format(
                        modules="\n".join(
                            f"- {item}" for item in internal_modules
                        )
                    )
                    choice = QMessageBox.question(
                        self,
                        title,
                        message,
                        QMessageBox.StandardButton.Yes
                        | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if choice == QMessageBox.StandardButton.No:
                        apply_internal = False
                    else:
                        effective_auto_confirm = True
                else:
                    effective_auto_confirm = True

            payload = init_workspace(
                cwd=Path(ws),
                entry=entry,
                generate_requirements=self.chk_reqs.isChecked(),
                with_venv=self.chk_venv.isChecked(),
                install_requirements=self.chk_install.isChecked(),
                apply_internal=apply_internal,
                auto_confirm=effective_auto_confirm,
            )

            msg = self.gui.tr(
                "Projet initialisé avec succès !", "init_project_success"
            )
            QMessageBox.information(self, "Success", msg)

            # Refresh GUI
            if hasattr(self.gui, "apply_workspace_selection"):
                self.gui.apply_workspace_selection(ws)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Initialization failed: {e}")
            self.btn_init.setEnabled(True)


def open_init_workspace_dialog(gui):
    """Helper to open the init dialog."""
    workspace_dir = getattr(gui, "workspace_dir", None)
    if not workspace_dir:
        QMessageBox.warning(
            gui,
            gui.tr("Attention", "Warning"),
            gui.tr(
                "Veuillez d'abord sélectionner un dossier workspace.",
                "Please select a workspace folder first.",
            ),
        )
        return

    dlg = InitWorkspaceDialog(gui)
    dlg.exec()


from ... import output
from ...i18n import (
    available_languages,
    get_translations,
    i18n_synchro,
    translate,
)


def show_language_dialog(self):
    from PySide6.QtWidgets import QInputDialog

    langs = asyncio.run(available_languages())
    # Build options list with 'System' at top
    options = ["System"] + [
        str(x.get("name", x.get("code", ""))) for x in langs
    ]
    # Determine current index
    current_pref = getattr(self, "language", "System")
    if current_pref == "System":
        start_index = 0
    else:
        codes = [str(x.get("code", "")) for x in langs]
        start_index = (
            1 + codes.index(current_pref) if current_pref in codes else 0
        )
    title = translate(
        self.id,
        "choose_language_title",
        getattr(self, "windowTitle", lambda: "")(),
    )
    label = translate(
        self.id,
        "choose_language_label",
        getattr(getattr(self, "select_lang", None), "text", lambda: "")(),
    )
    choice, ok = QInputDialog.getItem(
        self, title, label, options, start_index, False
    )
    if ok and choice:
        lang_pref = (
            "System"
            if choice == "System"
            else next(
                (
                    str(x.get("code", "en"))
                    for x in langs
                    if str(x.get("name", "")) == choice
                ),
                "en",
            )
        )
        tr = asyncio.run(get_translations(lang_pref))
        i18n_synchro(self, lang_pref, tr)
    else:
        output.info(
            (
                "Sélection de la langue annulée.",
                "Language selection cancelled.",
            ),
            gui=self,
        )


class AdvancedAuthUI:
    """GUI implementations for AdvancedAuth service operations."""

    @staticmethod
    def handle_workspace_change_request(gui, folder: str) -> bool:
        """
        Interactively confirm and apply a workspace change request.
        """
        try:
            if not WorkspaceDialog.confirm_workspace_change(gui, str(folder)):
                return False

            if hasattr(gui, "apply_workspace_selection"):
                return bool(
                    gui.apply_workspace_selection(str(folder), source="plugin")
                )

            # Fallback if the GUI instance doesn't have the method directly
            return bool(
                WorkspaceDialog.apply_workspace_selection(
                    gui, str(folder), source="plugin"
                )
            )
        except Exception:
            return False
