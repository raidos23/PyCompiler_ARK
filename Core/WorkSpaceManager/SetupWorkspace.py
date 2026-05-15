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

from Core.ArkConfig import load_ark_config, should_exclude_file
from Core.Globals import _workspace_dir_lock
from Core.WidgetsCreator import CompilationProcessDialog


class SetupWorkspace:
    """Workspace selection and initialization helpers for the main GUI."""

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

            # Étape 2: valider/préparer le dossier workspace.
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

            # Étape 3: stopper proprement les compilations actives si nécessaire.
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

            # Étape 4: appliquer le workspace en mémoire.
            gui_instance.workspace_dir = folder

            # Étape 5: synchroniser le cache global thread-safe.
            try:
                global _workspace_dir_cache
                with _workspace_dir_lock:
                    _workspace_dir_cache = folder
            except Exception:
                pass

            # Étape 6: mettre à jour les widgets dépendants du workspace.
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

            # Étape 7: appliquer la stratégie venv du workspace.
            try:
                if hasattr(gui_instance, "venv_manager") and gui_instance.venv_manager:
                    # Do not auto-install engine tools on workspace selection.
                    # Tools are installed only when compiling with the selected engine.
                    if str(source).lower() == "plugin":
                        gui_instance.venv_manager.setup_workspace(
                            folder, check_tools=False
                        )
                    else:
                        if gui_instance.venv_manager.apply_workspace_pref(folder):
                            # Pref applied, nothing more to do
                            pass
                        else:

                            def _t(_key: str, fr: str, en: str) -> str:
                                try:
                                    return gui_instance.tr(fr, en)
                                except Exception:
                                    return en

                            title = _t(
                                "msg_venv_choice_title",
                                "Configuration du Venv",
                                "Venv setup",
                            )
                            msg = _t(
                                "msg_venv_choice_text",
                                "Créer un venv automatiquement ou sélectionner un venv (Python système inclus).",
                                "Create a venv automatically or select a venv (System Python included).",
                            )
                            box = QMessageBox(gui_instance)
                            box.setWindowTitle(title)
                            box.setText(msg)
                            btn_auto = box.addButton(
                                _t(
                                    "action_create_venv", "Créer un venv", "Create venv"
                                ),
                                QMessageBox.AcceptRole,
                            )
                            btn_manual = box.addButton(
                                _t(
                                    "action_select_venv",
                                    "Sélectionner un Venv",
                                    "Select Venv",
                                ),
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

            # Étape 8: recharger les configs engines persistées dans le workspace.
            try:
                from Core.EngineConfigManager import apply_engine_configs_for_workspace

                apply_engine_configs_for_workspace(gui_instance, folder)
            except Exception:
                pass

            # Étape 9: fermer le feedback de chargement.
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
        Recursively add Python files from a folder into the GUI file list.

        Args:
          gui_instance: Main GUI instance.
          folder: Folder path to scan.

        Returns:
          Number of files effectively added.
        """
        count = 0
        excluded_count = 0

        workspace_dir = getattr(gui_instance, "workspace_dir", None)

        # Étape 1: charger les règles d'exclusion workspace.
        ark_config = load_ark_config(workspace_dir)
        exclusion_patterns = ark_config.get("exclusion_patterns", [])

        last_pump = time.monotonic()
        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith(".py"):
                    full_path = os.path.join(root, f)

                    # Étape 2: ignorer les fichiers hors workspace.
                    if (
                        workspace_dir
                        and not os.path.commonpath([full_path, workspace_dir])
                        == workspace_dir
                    ):
                        continue

                    # Étape 3: appliquer les exclusions ark.yml.
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

        # Étape 4: journaliser le résumé d'exclusion.
        if excluded_count > 0:
            gui_instance.log_i18n(
                f"⏩ Exclusion appliquée : {excluded_count} fichier(s) exclu(s) selon ark.yml",
                f"⏩ Exclusion applied: {excluded_count} file(s) excluded according to ark.yml",
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
        Open `ark.yml` with the system default editor.

        Args:
          gui_instance: Main GUI instance.
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

        # Étape 1: créer le fichier config si absent.
        if not os.path.exists(config_path):
            try:
                from Core.ArkConfig import create_default_ark_config

                if create_default_ark_config(workspace_dir):
                    gui_instance.log_i18n(
                        "📋 Fichier ark.yml créé.",
                        "📋 ark.yml file created.",
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

        # Étape 2: ouvrir le fichier dans l'éditeur système.
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
