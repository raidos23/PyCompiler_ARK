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
PyCompiler ARK GUI Module

Module principal de l'interface utilisateur pour PyCompiler ARK.
Délègue les fonctionnalités UI à UiFeatures et gère la fenêtre principale.

Ce module est simplifié et délègue les fonctionnalités UI à Core/UiFeatures.py
pour une meilleure modularité.
"""

import asyncio
import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QMainWindow, QMessageBox

from Core.Globals import _latest_gui_instance, _workspace_dir_cache, _workspace_dir_lock

from .Globals import _run_coro_async
from .WidgetsCreator import ProgressDialog, CompilationProcessDialog
from .Venv_Manager import VenvManager
from .i18n import resolve_system_language, get_translations

# Import des fonctionnalités UI depuis UiFeatures
from .UiFeatures import UiFeatures

# Import des classes de gestion du workspace
from Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace
from Core.WorkSpaceManager.WorkspaceAdvancedManipulation import (
    WorkspaceAdvancedManipulation,
)


def get_selected_workspace() -> Optional[str]:
    """Retourne le workspace sélectionné de manière thread-safe."""
    try:
        with _workspace_dir_lock:
            val = _workspace_dir_cache
        if val:
            return str(val)
    except Exception:
        pass
    try:
        gui = _latest_gui_instance
        if gui and getattr(gui, "workspace_dir", None):
            return str(gui.workspace_dir)
    except Exception:
        pass
    return None


class PyCompilerArkGui(QMainWindow, UiFeatures):
    """
    Classe principale de la fenêtre GUI pour PyCompiler ARK.

    Hérité de UiFeatures pour les fonctionnalités UI déléguées.
    """

    def __init__(self):
        super().__init__()
        global _latest_gui_instance
        _latest_gui_instance = self

        self.setWindowTitle("PyCompiler ARK")
        self.setGeometry(100, 100, 1280, 720)
        self.setAcceptDrops(True)

        # Initialisation des attributs d'état
        self.workspace_dir = None
        self.python_files = []
        self.icon_path = None
        self.selected_files = []
        self.venv_path_manuel = None
        self.use_system_python = False
        self.processes = []
        self.queue = []
        self.current_compiling = set()
        self._closing = False
        self._language_refresh_callbacks = []

        # Gestion du venv via VenvManager
        self.venv_manager = VenvManager(self)

        # Charger les préférences et initialiser l'UI
        self.load_preferences()
        self.init_ui()

        # Détection et application de la langue système
        import locale

        sys_lang = None
        try:
            loc = locale.getdefaultlocale()[0] or ""
            sys_lang = (
                "Français" if loc.lower().startswith(("fr", "fr_")) else "English"
            )
        except Exception:
            sys_lang = "English"

        pref_lang = getattr(self, "language_pref", getattr(self, "language", "System"))
        chosen_lang = sys_lang if pref_lang == "System" else pref_lang
        self.apply_language(chosen_lang)
        self.language_pref = pref_lang

        # Afficher le mode de langue sur le bouton
        try:
            if self.select_lang:

                async def _fetch_tr():
                    effective_code = (
                        await resolve_system_language()
                        if pref_lang == "System"
                        else pref_lang
                    )
                    return await get_translations(effective_code)

                def _apply_label(tr):
                    try:
                        key = (
                            "choose_language_system_button"
                            if pref_lang == "System"
                            else "choose_language_button"
                        )
                        self.select_lang.setText(
                            (tr.get(key) if isinstance(tr, dict) else "")
                            or (tr.get("select_lang") if isinstance(tr, dict) else "")
                            or ""
                        )
                    except Exception:
                        pass

                _run_coro_async(_fetch_tr(), _apply_label, ui_owner=self)
        except Exception:
            pass

        self.update_ui_state()

    # =========================================================================
    # DÉLÉGATION UI À UiFeatures
    # =========================================================================
    # Les méthodes suivantes sont déléguées à UiFeatures via l'héritage multiple

    select_icon = UiFeatures.select_icon
    select_nuitka_icon = UiFeatures.select_nuitka_icon
    show_help_dialog = UiFeatures.show_help_dialog
    export_config = UiFeatures.export_config
    import_config = UiFeatures.import_config
    update_command_preview = UiFeatures.update_command_preview
    set_controls_enabled = UiFeatures.set_controls_enabled
    set_compilation_ui_enabled = UiFeatures.set_compilation_ui_enabled
    show_statistics = UiFeatures.show_statistics
    apply_language = UiFeatures.apply_language
    register_language_refresh = UiFeatures.register_language_refresh
    log_i18n = UiFeatures.log_i18n
    show_language_dialog = UiFeatures.show_language_dialog
    _apply_main_app_translations = UiFeatures._apply_main_app_translations

    # =========================================================================
    # INITIALISATION UI
    # =========================================================================

    from .UiConnection import init_ui

    # =========================================================================
    # GESTION DU WORKSPACE (délégation à SetupWorkspace)
    # =========================================================================

    def dragEnterEvent(self, event: QDropEvent):
        """Gère l'événement dragEnter."""
        WorkspaceAdvancedManipulation.handle_drag_enter_event(self, event)

    def dropEvent(self, event: QDropEvent):
        """Gère l'événement drop."""
        WorkspaceAdvancedManipulation.handle_drop_event(self, event)

    def add_py_files_from_folder(self, folder):
        """Ajoute les fichiers Python du dossier."""
        return SetupWorkspace.add_py_files_from_folder(self, folder)

    def select_workspace(self):
        """Ouvre une boîte de dialogue pour sélectionner le workspace."""
        folder = SetupWorkspace.select_workspace(self)
        if folder:
            self.apply_workspace_selection(folder, source="ui")

    def apply_workspace_selection(self, folder: str, source: str = "ui") -> bool:
        """Applique la sélection du workspace."""
        return SetupWorkspace.apply_workspace_selection(self, folder, source)

    def select_venv_manually(self):
        """Sélectionne un venv manuellement."""
        self.venv_manager.select_venv_manually()

    def create_venv_if_needed(self, path):
        """Crée un venv si nécessaire."""
        self.venv_manager.create_venv_if_needed(path)

    def install_requirements_if_needed(self, path):
        """Installe les requirements si nécessaire."""
        self.venv_manager.install_requirements_if_needed(path)

    def select_files_manually(self):
        """Ouvre une boîte de dialogue pour sélectionner des fichiers."""
        WorkspaceAdvancedManipulation.select_files_manually(self)

    def open_ark_config(self):
        """Ouvre le fichier ARK_Main_Config.yml."""
        SetupWorkspace.open_ark_config(self)

    def on_main_only_changed(self):
        """Gestion du changement de l'option main uniquement."""
        if self.opt_main_only.isChecked():
            mains = [
                f
                for f in self.python_files
                if os.path.basename(f) in ("main.py", "app.py")
            ]
            if len(mains) > 1:
                QMessageBox.information(
                    self,
                    self.tr("Info", "Info"),
                    self.tr(
                        f"{len(mains)} fichiers main.py ou app.py détectés dans le workspace.",
                        f"{len(mains)} main.py or app.py files detected in the workspace.",
                    ),
                )
        self.update_command_preview()

    def add_remove_file_button(self):
        """Cette méthode n'est plus nécessaire."""
        pass

    def remove_selected_file(self):
        """Supprime les fichiers sélectionnés."""
        WorkspaceAdvancedManipulation.remove_selected_file(self)

    def clear_workspace(self):
        """Vide la liste des fichiers du workspace sans changer le dossier."""
        WorkspaceAdvancedManipulation.clear_workspace(self, keep_dir=True)

    def apply_file_filter(self, text: Optional[str] = None) -> None:
        """Filtre la liste des fichiers affichés selon un texte."""
        try:
            if text is None:
                try:
                    if getattr(self, "file_filter_input", None):
                        text = self.file_filter_input.text()
                except Exception:
                    text = ""
            needle = (text or "").strip().lower()
            if not getattr(self, "file_list", None):
                return
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if item is None:
                    continue
                hay = item.text().lower()
                item.setHidden(bool(needle) and needle not in hay)
        except Exception:
            pass

    # =========================================================================
    # COMPILATION (délégation à Compiler)
    # =========================================================================

    from .Compiler import (
        cancel_all_compilations,
        handle_finished,
        handle_stderr,
        handle_stdout,
        show_error_dialog,
        try_install_missing_modules,
        try_start_processes,
        compile_all,
        start_compilation_process,
        _continue_compile_all,
    )

    # =========================================================================
    # PRÉFÉRENCES
    # =========================================================================

    from .PreferencesManager import load_preferences, save_preferences, update_ui_state

    # =========================================================================
    # DÉPENDANCES
    # =========================================================================

    from .deps_analyser import (
        _install_next_dependency,
        _on_dep_pip_finished,
        _on_dep_pip_output,
        suggest_missing_dependencies,
    )

    # =========================================================================
    # INTERNATIONALISATION
    # =========================================================================

    current_language = "English"

    def tr(self, fr: str, en: str) -> str:
        """Retourne le texte FR si la langue est Français, sinon EN."""
        try:
            lang = str(
                getattr(self, "current_language", "English") or "English"
            ).lower()
        except Exception:
            lang = "english"
        return fr if lang.startswith("fr") else en

    # =========================================================================
    # JOURNALISATION
    # =========================================================================

    def _safe_log(self, text):
        """Journalise de manière sécurisée."""
        try:
            if hasattr(self, "log") and self.log:
                self.log.append(text)
            else:
                print(text)
        except Exception:
            try:
                print(text)
            except Exception:
                pass

    # =========================================================================
    # TÂCHES EN ARRIÈRE-PLAN
    # =========================================================================

    def _has_active_background_tasks(self) -> bool:
        """Vérifie s'il y a des tâches en arrière-plan actives."""
        if self.processes:
            return True
        if (
            hasattr(self, "venv_manager")
            and self.venv_manager
            and self.venv_manager.has_active_tasks()
        ):
            return True
        try:
            bcasl_thread = getattr(self, "_bcasl_thread", None)
            if bcasl_thread is not None and bcasl_thread.is_alive():
                return True
        except Exception:
            pass
        return False

    def _terminate_background_tasks(self):
        """Arrête les tâches en arrière-plan."""
        try:
            if hasattr(self, "venv_manager") and self.venv_manager:
                self.venv_manager.terminate_tasks()
        except Exception:
            pass

    # =========================================================================
    # ÉVÉNEMENT DE FERMETURE
    # =========================================================================

    def closeEvent(self, event):
        """Gère l'événement de fermeture de la fenêtre."""
        if self._has_active_background_tasks():
            details = []
            if self.processes:
                details.append("compilation")
            if hasattr(self, "venv_manager") and self.venv_manager:
                details.extend(self.venv_manager.get_active_task_labels("Français"))

            is_english = getattr(self, "current_language", "Français") == "English"

            if is_english:
                mapping = {
                    "compilation": "build",
                    "création du venv": "venv creation",
                    "installation des dépendances": "dependencies installation",
                    "vérification/installation du venv": "venv check/installation",
                }
                details_disp = [mapping.get(d, d) for d in details]
                title = "⚠️ Process Running"
                msg = "A process is currently running:\n\n"
                if details_disp:
                    for detail in details_disp:
                        msg += f"  • {detail}\n"
                    msg += "\n"
                msg += "If you quit now, the process will be stopped and any unsaved work will be lost.\n\n"
                msg += "Do you really want to quit?"
                yes_text = "Yes, Quit"
                no_text = "No, Continue"
            else:
                details_disp = details
                title = "⚠️ Processus en cours"
                msg = "Un processus est actuellement en cours :\n\n"
                if details_disp:
                    for detail in details_disp:
                        msg += f"  • {detail}\n"
                    msg += "\n"
                msg += "Si vous quittez maintenant, le processus sera arrêté et tout travail non sauvegardé sera perdu.\n\n"
                msg += "Voulez-vous vraiment quitter ?"
                yes_text = "Oui, Quitter"
                no_text = "Non, continuer"

            msgbox = QMessageBox(self)
            msgbox.setWindowTitle(title)
            msgbox.setText(msg)
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)
            msgbox.button(QMessageBox.Yes).setText(yes_text)
            msgbox.button(QMessageBox.No).setText(no_text)
            reply = msgbox.exec()

            if reply == QMessageBox.Yes:
                self._closing = True
                if self.processes:
                    self.cancel_all_compilations()
                self._terminate_background_tasks()
                try:
                    from bcasl.Loader import ensure_bcasl_thread_stopped

                    ensure_bcasl_thread_stopped(self)
                except Exception:
                    pass
                event.accept()
            else:
                event.ignore()
        else:
            try:
                from bcasl.Loader import ensure_bcasl_thread_stopped

                ensure_bcasl_thread_stopped(self)
            except Exception:
                pass
            event.accept()
