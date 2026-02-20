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

import os
import time
from typing import Optional

from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from Core.ArkConfigManager import load_ark_config, should_exclude_file
from Core.Globals import _workspace_dir_cache, _workspace_dir_lock
from Core.WidgetsCreator import CompilationProcessDialog


class SetupWorkspace:
    """Gestion de la sélection et de la configuration du workspace."""

    @staticmethod
    def select_workspace(gui_instance) -> Optional[str]:
        """
        Ouvre une boîte de dialogue pour sélectionner le dossier workspace.

        Args:
            gui_instance: Instance de l'interface GUI

        Returns:
            Le chemin du workspace sélectionné ou None si annulé
        """
        folder = QFileDialog.getExistingDirectory(
            gui_instance,
            gui_instance.tr("Choisir le dossier du projet", "Select project folder"),
        )
        if folder:
            return folder
        return None

    @staticmethod
    def apply_workspace_selection(
        gui_instance, folder: str, source: str = "ui"
    ) -> bool:
        """
        Applique la sélection du workspace et configure l'interface.

        Args:
            gui_instance: Instance de l'interface GUI
            folder: Chemin du dossier workspace
            source: Source de la requête ("ui" ou "plugin")

        Returns:
            True si succès, False sinon
        """
        try:
            # Afficher le dialog de chargement du workspace
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

            # Vérifier et créer le dossier si nécessaire
            if not folder:
                try:
                    gui_instance.log_i18n(
                        "⚠️ Chemin de workspace vide fourni; aucune modification appliquée (accepté).",
                        "⚠️ Empty workspace path provided; no changes applied (accepted).",
                    )
                except Exception:
                    pass
                try:
                    if loading_dialog:
                        loading_dialog.close()
                except Exception:
                    pass
                return True

            if not os.path.isdir(folder):
                try:
                    os.makedirs(folder, exist_ok=True)
                    try:
                        gui_instance.log_i18n(
                            f"📁 Dossier créé automatiquement: {folder}",
                            f"📁 Folder created automatically: {folder}",
                        )
                    except Exception:
                        pass
                except Exception:
                    try:
                        gui_instance.log_i18n(
                            f"⚠️ Impossible de créer le dossier, poursuite quand même: {folder}",
                            f"⚠️ Unable to create folder, continuing anyway: {folder}",
                        )
                    except Exception:
                        pass

            # Confirmation et arrêt des compilations en cours
            if str(source).lower() == "plugin":
                try:
                    if (
                        getattr(gui_instance, "processes", None)
                        and gui_instance.processes
                    ):
                        try:
                            gui_instance.log_i18n(
                                "⛔ Arrêt des compilations en cours pour changer de workspace (Plugins).",
                                "⛔ Stopping ongoing builds to switch workspace (Plugins).",
                            )
                        except Exception:
                            pass
                        try:
                            gui_instance.cancel_all_compilations()
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                if getattr(gui_instance, "processes", None) and gui_instance.processes:
                    try:
                        gui_instance.log_i18n(
                            "⛔ Arrêt des compilations en cours pour changer de workspace (UI).",
                            "⛔ Stopping ongoing builds to switch workspace (UI).",
                        )
                    except Exception:
                        pass
                    try:
                        gui_instance.cancel_all_compilations()
                    except Exception:
                        pass

            # Appliquer le workspace
            gui_instance.workspace_dir = folder

            # Mettre à jour le cache global
            try:
                global _workspace_dir_cache
                with _workspace_dir_lock:
                    _workspace_dir_cache = folder
            except Exception:
                pass

            # Mettre à jour l'interface
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
                        tmpl = (
                            tr_map.get("label_workspace_status") or "Workspace: {path}"
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

            SetupWorkspace.add_py_files_from_folder(gui_instance, folder)
            gui_instance.selected_files.clear()

            try:
                if hasattr(gui_instance, "apply_file_filter"):
                    gui_instance.apply_file_filter()
            except Exception:
                pass

            try:
                if hasattr(gui_instance, "load_entrypoint_from_config"):
                    gui_instance.load_entrypoint_from_config()
            except Exception:
                pass

            if hasattr(gui_instance, "update_command_preview"):
                gui_instance.update_command_preview()

            try:
                gui_instance.save_preferences()
            except Exception:
                pass

            # Configuration du venv
            try:
                if hasattr(gui_instance, "venv_manager") and gui_instance.venv_manager:
                    # Do not auto-install engine tools on workspace selection.
                    # Tools are installed only when compiling with the selected engine.
                    if str(source).lower() == "plugin":
                        gui_instance.venv_manager.setup_workspace(
                            folder, check_tools=False
                        )
                    else:
                        title = gui_instance.tr(
                            "Configuration du venv", "Venv setup"
                        )
                        msg = gui_instance.tr(
                            "Voulez-vous créer un venv automatiquement\n"
                            "ou sélectionner un venv manuellement (Python système inclus) ?",
                            "Do you want to create a venv automatically\n"
                            "or select a venv manually (System Python included)?",
                        )
                        box = QMessageBox(gui_instance)
                        box.setWindowTitle(title)
                        box.setText(msg)
                        btn_auto = box.addButton(
                            gui_instance.tr("Créer un venv", "Create venv"),
                            QMessageBox.AcceptRole,
                        )
                        btn_manual = box.addButton(
                            gui_instance.tr("Sélectionner un venv", "Select venv"),
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
            except Exception as e:
                gui_instance.log_i18n(
                    f"⚠️ Erreur lors de la configuration du workspace: {e}",
                    f"⚠️ Error during workspace setup: {e}",
                )

            # Appliquer la configuration des engines depuis .ark/<engine_id>/config.json
            try:
                from Core.EngineConfigManager import apply_engine_configs_for_workspace

                apply_engine_configs_for_workspace(gui_instance, folder)
            except Exception:
                pass

            # Fermer le dialog de chargement
            try:
                if loading_dialog:
                    loading_dialog.close()
            except Exception:
                pass

            return True

        except Exception as _e:
            try:
                gui_instance.log_i18n(
                    f"❌ Échec application workspace: {_e}",
                    f"❌ Failed to apply workspace: {_e}",
                )
            except Exception:
                pass
            try:
                if loading_dialog:
                    loading_dialog.close()
            except Exception:
                pass
            return False

    @staticmethod
    def add_py_files_from_folder(gui_instance, folder: str) -> int:
        """
        Ajoute récursivement tous les fichiers Python du dossier au projet.

        Args:
            gui_instance: Instance de l'interface GUI
            folder: Chemin du dossier à scanner

        Returns:
            Nombre de fichiers ajoutés
        """
        count = 0
        excluded_count = 0

        workspace_dir = getattr(gui_instance, "workspace_dir", None)

        # Charger la configuration ARK pour les patterns d'exclusion
        ark_config = load_ark_config(workspace_dir)
        exclusion_patterns = ark_config.get("exclusion_patterns", [])

        last_pump = time.monotonic()
        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith(".py"):
                    full_path = os.path.join(root, f)

                    # Vérifier si le fichier est dans le workspace
                    if (
                        workspace_dir
                        and not os.path.commonpath([full_path, workspace_dir])
                        == workspace_dir
                    ):
                        continue

                    # Vérifier les patterns d'exclusion depuis ARK_Main_Config.yml
                    if should_exclude_file(
                        full_path, workspace_dir, exclusion_patterns
                    ):
                        excluded_count += 1
                        continue

                    if full_path not in gui_instance.python_files:
                        gui_instance.python_files.append(full_path)

                        if hasattr(gui_instance, "file_list"):
                            relative_path = (
                                os.path.relpath(full_path, workspace_dir)
                                if workspace_dir
                                else full_path
                            )
                            gui_instance.file_list.addItem(relative_path)
                        count += 1
                        if count % 200 == 0:
                            now = time.monotonic()
                            if now - last_pump > 0.05:
                                QApplication.processEvents()
                                last_pump = now

        # Afficher un message récapitulatif si des fichiers ont été exclus
        if excluded_count > 0:
            gui_instance.log_i18n(
                f"⏩ Exclusion appliquée : {excluded_count} fichier(s) exclu(s) selon ARK_Main_Config.yml",
                f"⏩ Exclusion applied: {excluded_count} file(s) excluded according to ARK_Main_Config.yml",
            )

        try:
            if hasattr(gui_instance, "apply_file_filter"):
                gui_instance.apply_file_filter()
        except Exception:
            pass

        return count

    @staticmethod
    def open_ark_config(gui_instance):
        """
        Ouvre le fichier ARK_Main_Config.yml dans l'éditeur par défaut.

        Args:
            gui_instance: Instance de l'interface GUI
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

        config_path = os.path.join(workspace_dir, "ARK_Main_Config.yml")

        # Créer le fichier s'il n'existe pas
        if not os.path.exists(config_path):
            try:
                from Core.ArkConfigManager import create_default_ark_config

                if create_default_ark_config(workspace_dir):
                    gui_instance.log_i18n(
                        "📋 Fichier ARK_Main_Config.yml créé.",
                        "📋 ARK_Main_Config.yml file created.",
                    )
            except Exception as e:
                QMessageBox.critical(
                    gui_instance,
                    gui_instance.tr("Erreur", "Error"),
                    gui_instance.tr(
                        f"Impossible de créer ARK_Main_Config.yml: {e}",
                        f"Failed to create ARK_Main_Config.yml: {e}",
                    ),
                )
                return

        # Ouvrir le fichier dans l'éditeur par défaut
        try:
            import subprocess
            import platform

            system = platform.system()
            if system == "Windows":
                os.startfile(config_path)
            elif system == "Darwin":  # macOS
                subprocess.run(["open", config_path])
            else:  # Linux
                subprocess.run(["xdg-open", config_path])

            gui_instance.log_i18n(
                f"📝 Ouverture de {config_path}",
                f"📝 Opening {config_path}",
            )
        except Exception as e:
            QMessageBox.warning(
                gui_instance,
                gui_instance.tr("Attention", "Warning"),
                gui_instance.tr(
                    f"Impossible d'ouvrir le fichier: {e}\nChemin: {config_path}",
                    f"Failed to open file: {e}\nPath: {config_path}",
                ),
            )
