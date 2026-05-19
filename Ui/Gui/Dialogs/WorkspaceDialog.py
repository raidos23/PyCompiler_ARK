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
WorkspaceDialog — interactions Qt pour la sélection et l'initialisation du workspace.

Ce module gère les dialogues Qt (QFileDialog, QMessageBox, loading dialogs)
et délègue toute la logique métier à Core.WorkSpaceManager.SetupWorkspace.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace
from Core.Globals import _workspace_dir_lock
from Ui.Gui.WidgetsCreator import CompilationProcessDialog


class WorkspaceDialog:
    """Gestion Qt du workspace (sélection, application, initialisation)."""

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
            _t("action_select_workspace", "Choisir Workspace", "Select Workspace"),
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
                        "Chargement de l'espace de travail", "Loading workspace"
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
                    gui_instance.log_i18n(
                        "⚠️ Chemin de workspace vide fourni; aucune modification appliquée (accepté).",
                        "⚠️ Empty workspace path provided; no changes applied (accepted).",
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
                    gui_instance.log_i18n(
                        f"📁 Dossier créé automatiquement: {folder}",
                        f"📁 Folder created automatically: {folder}",
                    )
                except Exception as e:
                    gui_instance.log_i18n(
                        f"⚠️ Impossible de créer le dossier: {e}",
                        f"⚠️ Unable to create folder: {e}",
                    )

            # Étape 3: stopper proprement les compilations actives.
            if hasattr(gui_instance, "processes") and gui_instance.processes:
                label = "Plugins" if str(source).lower() == "plugin" else "UI"
                gui_instance.log_i18n(
                    f"⛔ Arrêt des compilations en cours pour changer de workspace ({label}).",
                    f"⛔ Stopping ongoing builds to switch workspace ({label}).",
                )
                try:
                    gui_instance.cancel_all_compilations()
                except Exception:
                    pass

            # Étape 4: appliquer le workspace en mémoire.
            gui_instance.workspace_dir = folder

            # Étape 5: synchroniser le cache global thread-safe.
            try:
                from Core.Globals import _workspace_dir_cache
                global _workspace_dir_cache
                with _workspace_dir_lock:
                    _workspace_dir_cache = folder
            except Exception:
                pass

            # Étape 6: mettre à jour les widgets UI.
            if hasattr(gui_instance, "label_folder"):
                gui_instance.label_folder.setText(
                    gui_instance.tr(
                        f"Dossier sélectionné : {folder}", f"Selected folder: {folder}"
                    )
                )
            if hasattr(gui_instance, "label_workspace_status"):
                try:
                    tr_map = getattr(gui_instance, "_tr", None)
                    if isinstance(tr_map, dict):
                        tmpl = tr_map.get("label_workspace_status") or "Workspace: {path}"
                        gui_instance.label_workspace_status.setText(
                            str(tmpl).replace("{path}", str(folder))
                        )
                    else:
                        gui_instance.label_workspace_status.setText(
                            gui_instance.tr(f"Workspace : {folder}", f"Workspace: {folder}")
                        )
                except Exception:
                    pass

            gui_instance.python_files.clear()
            if hasattr(gui_instance, "file_list"):
                gui_instance.file_list.clear()

            # Scanner les fichiers (via Core)
            files = SetupWorkspace.list_python_files(folder)
            
            # Filtrer et ajouter à l'UI
            from Core.Configs import load_ark_config, should_exclude_file
            ark_config = load_ark_config(folder)

            workspace_cfg = ark_config.get("workspace", {})
            exclusion_patterns = []
            if isinstance(workspace_cfg, dict):
                exclusion_patterns = workspace_cfg.get("exclude", [])

            # Suppression de la rétro-compatibilité avec exclusion_patterns racine
            # exclusion_patterns = ark_config.get("exclusion_patterns", [])

            for f in files:

            excluded_count = 0
            
            import time
            last_pump = time.monotonic()
            
            for full_path in files:
                if should_exclude_file(full_path, folder, exclusion_patterns):
                    excluded_count += 1
                    continue
                    
                gui_instance.python_files.append(full_path)
                if hasattr(gui_instance, "file_list"):
                    relative_path = os.path.relpath(full_path, folder)
                    gui_instance.file_list.addItem(relative_path)
                
                added_count += 1
                if added_count % 200 == 0:
                    if time.monotonic() - last_pump > 0.05:
                        QApplication.processEvents()
                        last_pump = time.monotonic()

            if excluded_count > 0:
                gui_instance.log_i18n(
                    f"⏩ Exclusion appliquée : {excluded_count} fichier(s) exclu(s) selon ark.yml",
                    f"⏩ Exclusion applied: {excluded_count} file(s) excluded according to ark.yml",
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
            if hasattr(gui_instance, "venv_manager") and gui_instance.venv_manager:
                if str(source).lower() == "plugin":
                    gui_instance.venv_manager.setup_workspace(folder, check_tools=False)
                else:
                    if not gui_instance.venv_manager.apply_workspace_pref(folder):
                        # Proposer création ou sélection
                        def _t(fr, en): return gui_instance.tr(fr, en)
                        title = _t("Configuration du Venv", "Venv setup")
                        msg = _t("Créer un venv automatiquement ou sélectionner un venv (Python système inclus).",
                                 "Create a venv automatically or select a venv (System Python included).")
                        box = QMessageBox(gui_instance)
                        box.setWindowTitle(title)
                        box.setText(msg)
                        btn_auto = box.addButton(_t("Créer un venv", "Create venv"), QMessageBox.AcceptRole)
                        btn_manual = box.addButton(_t("Sélectionner un Venv", "Select Venv"), QMessageBox.ActionRole)
                        box.setDefaultButton(btn_auto)
                        box.exec()

                        if box.clickedButton() == btn_manual:
                            gui_instance.venv_manager.select_venv_manually()
                        else:
                            gui_instance.venv_manager.setup_workspace(folder, check_tools=False)

            # Étape 8: recharger les configs engines
            try:
                from Core.EngineConfigManager import apply_engine_configs_for_workspace
                apply_engine_configs_for_workspace(gui_instance, folder)
            except Exception:
                pass

            if loading_dialog:
                loading_dialog.close()

            return True

        except Exception as e:
            gui_instance.log_i18n(f"❌ Échec application workspace: {e}", f"❌ Failed to apply workspace: {e}")
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
            QMessageBox.warning(gui_instance, gui_instance.tr("Attention", "Warning"),
                                gui_instance.tr("Veuillez d'abord sélectionner un dossier workspace.",
                                              "Please select a workspace folder first."))
            return

        config_path = os.path.join(workspace_dir, "ark.yml")

        if not os.path.exists(config_path):
            try:
                from Core.Configs import create_default_ark_config
                if create_default_ark_config(workspace_dir):
                    gui_instance.log_i18n("📋 Fichier ark.yml créé.", "📋 ark.yml file created.")
            except Exception as e:
                QMessageBox.critical(gui_instance, gui_instance.tr("Erreur", "Error"),
                                     gui_instance.tr(f"Impossible de créer ark.yml: {e}",
                                                   f"Failed to create ark.yml: {e}"))
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
            gui_instance.log_i18n(f"📝 Ouverture de {config_path}", f"📝 Opening {config_path}")
        except Exception as e:
            QMessageBox.warning(gui_instance, gui_instance.tr("Attention", "Warning"),
                                gui_instance.tr(f"Impossible d'ouvrir le fichier: {e}",
                                              f"Failed to open file: {e}"))
