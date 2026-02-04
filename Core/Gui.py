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

import asyncio
import json
import os
import platform
import shutil
import sys
from typing import Optional

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QDropEvent, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget

from Core.Globals import _workspace_dir_lock, _latest_gui_instance, _workspace_dir_cache

from .Globals import _UiInvoker, _run_coro_async
from .WidgetsCreator import ProgressDialog, CompilationProcessDialog
from .Venv_Manager import VenvManager
from .i18n import (
    _apply_main_app_translations as _i18n_apply_translations,
    show_language_dialog as _i18n_show_dialog,
)

# Import des classes de gestion du workspace
from Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace
from Core.WorkSpaceManager.WorkspaceAdvancedManipulation import WorkspaceAdvancedManipulation


def get_selected_workspace() -> Optional[str]:
    """Retourne le workspace sélectionné d'une manière non bloquante et thread-safe."""
    # Fast path: cached value with lock, no UI access
    try:
        with _workspace_dir_lock:
            val = _workspace_dir_cache
        if val:
            return str(val)
    except Exception:
        pass
    # Fallback to last known GUI instance without touching QApplication/activeWindow
    try:
        gui = _latest_gui_instance
        if gui and getattr(gui, "workspace_dir", None):
            return str(gui.workspace_dir)
    except Exception:
        pass
    return None


from PySide6.QtCore import QEventLoop as _QEventLoop


class PyCompilerArkGui(QWidget):
    def __init__(self):
        super().__init__()
        global _latest_gui_instance
        _latest_gui_instance = self
        self.setWindowTitle("PyCompiler ARK++")
        self.setGeometry(100, 100, 1280, 720)
        self.setAcceptDrops(True)

        self.workspace_dir = None
        self.python_files = []
        self.icon_path = None
        self.selected_files = []
        self.venv_path_manuel = None

        self.processes = []
        self.queue = []
        self.current_compiling = set()
        self._closing = False
        # Callbacks de rafraîchissement i18n enregistrés par les moteurs
        self._language_refresh_callbacks = []
        # Gestion du venv via VenvManager
        self.venv_manager = VenvManager(self)

        self.load_preferences()
        self.init_ui()

        # Détection langue système si préférence = "System"
        import locale

        sys_lang = None
        try:
            loc = locale.getdefaultlocale()[0] or ""
            sys_lang = (
                "Français" if loc.lower().startswith(("fr", "fr_")) else "English"
            )
        except Exception:
            sys_lang = "English"
        # Utiliser la préférence persistée (System ou code)
        pref_lang = getattr(self, "language_pref", getattr(self, "language", "System"))
        chosen_lang = sys_lang if pref_lang == "System" else pref_lang
        self.apply_language(chosen_lang)
        # Conserver language_pref pour les futurs enregistrements
        self.language_pref = pref_lang
        # Afficher le mode de langue sur le bouton
        try:
            if self.select_lang:
                from .i18n import get_translations, resolve_system_language

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

    from .UiConnection import init_ui

    def dragEnterEvent(self, event: QDropEvent):
        """Gère l'événement dragEnter en déléguant à WorkspaceAdvancedManipulation."""
        WorkspaceAdvancedManipulation.handle_drag_enter_event(self, event)

    def dropEvent(self, event: QDropEvent):
        """Gère l'événement drop en déléguant à WorkspaceAdvancedManipulation."""
        WorkspaceAdvancedManipulation.handle_drop_event(self, event)

    def add_py_files_from_folder(self, folder):
        """Ajoute les fichiers Python du dossier en déléguant à SetupWorkspace."""
        return SetupWorkspace.add_py_files_from_folder(self, folder)

    def select_workspace(self):
        """Ouvre une boîte de dialogue pour sélectionner le workspace."""
        folder = SetupWorkspace.select_workspace(self)
        if folder:
            self.apply_workspace_selection(folder, source="ui")

    def apply_workspace_selection(self, folder: str, source: str = "ui") -> bool:
        """Applique la sélection du workspace en déléguant à SetupWorkspace."""
        return SetupWorkspace.apply_workspace_selection(self, folder, source)

    def select_venv_manually(self):
        self.venv_manager.select_venv_manually()

    def create_venv_if_needed(self, path):
        self.venv_manager.create_venv_if_needed(path)

    def install_requirements_if_needed(self, path):
        self.venv_manager.install_requirements_if_needed(path)

    def select_files_manually(self):
        """Ouvre une boîte de dialogue pour sélectionner des fichiers en déléguant à WorkspaceAdvancedManipulation."""
        WorkspaceAdvancedManipulation.select_files_manually(self)

    def open_ark_config(self):
        """Ouvre le fichier ARK_Main_Config.yml dans l'éditeur par défaut en déléguant à SetupWorkspace."""
        SetupWorkspace.open_ark_config(self)

    def on_main_only_changed(self):
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

    def select_icon(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier .ico", "", "Icon Files (*.ico)"
        )
        if file:
            self.icon_path = file
            self.log_i18n(
                f"🎨 Icône sélectionnée : {file}", f"🎨 Icon selected: {file}"
            )
            pixmap = QPixmap(file)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.icon_preview.setPixmap(scaled_pixmap)
                self.icon_preview.show()
            else:
                self.icon_preview.hide()
        else:
            # Annulation: supprimer l'icône sélectionnée et masquer l'aperçu
            self.icon_path = None
            self.icon_preview.hide()
        # Persistance et mise à jour en temps réel
        self.update_command_preview()
        try:
            self.save_preferences()
        except Exception:
            pass

    def select_nuitka_icon(self):
        import platform

        from PySide6.QtWidgets import QFileDialog

        if platform.system() != "Windows":
            return
        file, _ = QFileDialog.getOpenFileName(
            self, "Choisir une icône .ico pour Nuitka", "", "Icon Files (*.ico)"
        )
        if file:
            self.nuitka_icon_path = file
            self.log_i18n(
                f"🎨 Icône Nuitka sélectionnée : {file}",
                f"🎨 Nuitka icon selected: {file}",
            )
        else:
            self.nuitka_icon_path = None
        self.update_command_preview()

    def add_remove_file_button(self):
        # Cette méthode n'est plus nécessaire car le bouton est déjà dans le .ui
        pass

    def remove_selected_file(self):
        """Supprime les fichiers sélectionnés en déléguant à WorkspaceAdvancedManipulation."""
        WorkspaceAdvancedManipulation.remove_selected_file(self)

    def show_help_dialog(self):
        # Minimal help dialog with current license information
        try:
            tr = getattr(self, "_tr", None)
            if tr and isinstance(tr, dict):
                help_title = tr.get("help_title", "Help")
                help_text = tr.get("help_text", "")
            else:
                help_title = "Help"
                help_text = ""
        except Exception:
            help_title = "Help"
            help_text = ""
        dlg = QMessageBox(self)
        dlg.setWindowTitle(help_title)
        dlg.setTextFormat(Qt.TextFormat.RichText)
        dlg.setText(help_text)
        dlg.setIcon(QMessageBox.Icon.Information)
        dlg.setStandardButtons(QMessageBox.StandardButton.Ok)
        dlg.exec()

    def export_config(self):
        file, _ = QFileDialog.getSaveFileName(
            self, "Exporter la configuration", "", "JSON Files (*.json)"
        )
        if file:
            if not file.endswith(".json"):
                file += ".json"
            # Normaliser la préférence de langue pour qu'elle soit soit 'System' soit un code i18n (ex: 'fr','en')
            try:
                from .i18n import normalize_lang_pref

                base_lang_pref = getattr(
                    self,
                    "language_pref",
                    getattr(
                        self, "language", getattr(self, "current_language", "System")
                    ),
                )
                lang_pref_out = (
                    base_lang_pref
                    if base_lang_pref == "System"
                    else asyncio.run(normalize_lang_pref(base_lang_pref))
                )
            except Exception:
                lang_pref_out = getattr(self, "language_pref", "System")
            # Export minimal: uniquement les préférences globales pertinentes
            prefs = {
                "language_pref": lang_pref_out,
                "theme": getattr(self, "theme", "System"),
            }
            try:
                with open(file, "w", encoding="utf-8") as f:
                    json.dump(prefs, f, indent=4)
                self.log_i18n(
                    f"✅ Configuration exportée : {file}",
                    f"✅ Configuration exported: {file}",
                )
            except Exception as e:
                self.log_i18n(
                    f"❌ Erreur export configuration : {e}",
                    f"❌ Error exporting configuration: {e}",
                )

    def import_config(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "Importer la configuration", "", "JSON Files (*.json)"
        )
        if file:
            try:
                with open(file, encoding="utf-8") as f:
                    prefs = json.load(f)
                # Appliquer la préférence de langue si présente
                try:
                    lang_pref_in = prefs.get(
                        "language_pref", prefs.get("language", None)
                    )
                    if lang_pref_in is not None:
                        from .i18n import (
                            get_translations,
                            normalize_lang_pref,
                            resolve_system_language,
                        )

                        if lang_pref_in == "System":
                            self.language_pref = "System"
                            # Applique la langue système pour les chaînes
                            self.apply_language("System")
                            if getattr(self, "select_lang", None):

                                async def _fetch_sys():
                                    code = await resolve_system_language()
                                    return await get_translations(code)

                                _run_coro_async(
                                    _fetch_sys(),
                                    lambda tr: self.select_lang.setText(
                                        tr.get("choose_language_system_button")
                                        or tr.get("select_lang")
                                        or ""
                                    ),
                                    ui_owner=self,
                                )
                        else:
                            code = asyncio.run(normalize_lang_pref(lang_pref_in))
                            self.language_pref = code
                            self.apply_language(code)
                            if getattr(self, "select_lang", None):
                                _run_coro_async(
                                    get_translations(code),
                                    lambda tr2: self.select_lang.setText(
                                        tr2.get("choose_language_button")
                                        or tr2.get("select_lang")
                                        or ""
                                    ),
                                    ui_owner=self,
                                )
                except Exception:
                    pass
                # Appliquer la préférence de thème si présente
                try:
                    theme_pref = prefs.get("theme", None)
                    if theme_pref is not None:
                        from .UiConnection import apply_theme

                        self.theme = theme_pref
                        apply_theme(self, theme_pref)
                except Exception:
                    pass
                self.log_i18n(
                    f"✅ Configuration importée : {file}",
                    f"✅ Configuration imported: {file}",
                )
                self.update_command_preview()
                # Persister les préférences mises à jour
                try:
                    self.save_preferences()
                except Exception:
                    pass
            except Exception as e:
                self.log_i18n(
                    f"❌ Erreur import configuration : {e}",
                    f"❌ Error importing configuration: {e}",
                )

    def update_command_preview(self):
        # Aperçu de commande désactivé: widget label_cmd retiré
        # Cette méthode est maintenant vide car les options sont gérées dynamiquement par les moteurs
        pass

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

    def set_controls_enabled(self, enabled):
        self.compile_btn.setEnabled(enabled)
        # Forcer une mise à jour visuelle pour refléter l'état grisé avec certains thèmes
        try:
            if self.compile_btn and hasattr(self.compile_btn, "style"):
                self.compile_btn.style().unpolish(self.compile_btn)
                self.compile_btn.style().polish(self.compile_btn)
                self.compile_btn.update()
        except Exception:
            pass
        self.cancel_btn.setEnabled(not enabled)
        self.btn_select_folder.setEnabled(enabled)
        self.btn_select_files.setEnabled(enabled)
        self.btn_remove_file.setEnabled(enabled)
        # Check if buttons exist before calling setEnabled
        try:
            if hasattr(self, "btn_export_config") and self.btn_export_config:
                self.btn_export_config.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_import_config") and self.btn_import_config:
                self.btn_import_config.setEnabled(enabled)
        except Exception:
            pass
        # Désactiver aussi le bouton d'analyse des dépendances
        try:
            if hasattr(self, "btn_suggest_deps") and self.btn_suggest_deps:
                self.btn_suggest_deps.setEnabled(enabled)
        except Exception:
            pass
        # Bc Plugins Loader button (BCASL)
        try:
            if hasattr(self, "btn_bc_loader") and self.btn_bc_loader:
                self.btn_bc_loader.setEnabled(enabled)
        except Exception:
            pass
        # Désactiver aussi options de langue/thème et stats (sensibles en cours de build)
        try:
            if hasattr(self, "select_lang") and self.select_lang:
                self.select_lang.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "select_theme") and self.select_theme:
                self.select_theme.setEnabled(enabled)
        except Exception:
            pass
        try:
            if hasattr(self, "btn_show_stats") and self.btn_show_stats:
                self.btn_show_stats.setEnabled(enabled)
        except Exception:
            pass
        self.venv_button.setEnabled(enabled)
        # Rafraîchir visuellement l'état grisé de tous les contrôles sensibles
        try:
            grey_targets = [
                getattr(self, "compile_btn", None),
                getattr(self, "btn_select_folder", None),
                getattr(self, "btn_select_files", None),
                getattr(self, "btn_remove_file", None),
                getattr(self, "btn_export_config", None),
                getattr(self, "btn_import_config", None),
                getattr(self, "btn_bc_loader", None),
                getattr(self, "btn_suggest_deps", None),
                getattr(self, "select_lang", None),
                getattr(self, "select_theme", None),
                getattr(self, "btn_show_stats", None),
                getattr(self, "venv_button", None),
            ]
            for w in grey_targets:
                try:
                    if w and hasattr(w, "style"):
                        w.style().unpolish(w)
                        w.style().polish(w)
                        w.update()
                except Exception:
                    pass
            # S'assurer que Cancel reflète visuellement son état inverse
            if hasattr(self, "cancel_btn") and self.cancel_btn:
                try:
                    self.cancel_btn.style().unpolish(self.cancel_btn)
                    self.cancel_btn.style().polish(self.cancel_btn)
                    self.cancel_btn.update()
                except Exception:
                    pass
        except Exception:
            pass

    from .PreferencesManager import load_preferences, save_preferences, update_ui_state

    def show_statistics(self):
        import psutil

        # Statistiques de compilation
        if not hasattr(self, "_compilation_times") or not self._compilation_times:
            QMessageBox.information(
                self,
                self.tr("Statistiques", "Statistics"),
                self.tr(
                    "Aucune compilation récente à analyser.",
                    "No recent builds to analyze.",
                ),
            )
            return
        total_files = len(self._compilation_times)
        total_time = sum(self._compilation_times.values())
        avg_time = total_time / total_files if total_files else 0
        try:
            mem_info = psutil.Process().memory_info().rss / (1024 * 1024)
        except Exception:
            mem_info = None
        msg = "<b>Statistiques de compilation</b><br>"
        msg += f"Fichiers compilés : {total_files}<br>"
        msg += f"Temps total : {total_time:.2f} secondes<br>"
        msg += f"Temps moyen par fichier : {avg_time:.2f} secondes<br>"
        if mem_info:
            msg += f"Mémoire utilisée (processus GUI) : {mem_info:.1f} Mo<br>"
        QMessageBox.information(
            self, self.tr("Statistiques de compilation", "Build statistics"), msg
        )

    # Internationalization using JSON language files
    current_language = "English"

    def _apply_main_app_translations(self, tr: dict):
        """Apply translations to UI elements - uses centralized i18n module version."""
        _i18n_apply_translations(self, tr)

    def apply_language(self, lang_display: str):
        # Launch non-blocking translation loading and apply when ready
        from .i18n import get_translations, normalize_lang_pref, resolve_system_language

        async def _do():
            code = (
                await resolve_system_language()
                if lang_display == "System"
                else await normalize_lang_pref(lang_display)
            )
            tr = await get_translations(code)
            return code, tr

        def _on_result(res):
            if isinstance(res, Exception):
                return
            code, tr = res
            self._apply_main_app_translations(tr)
            # Notifier les moteurs pour rafraîchir leurs libellés (i18n)
            try:
                # Callback-based refresh (legacy)
                for cb in getattr(self, "_language_refresh_callbacks", []) or []:
                    try:
                        cb()
                    except Exception:
                        pass
                # Registry-based propagation to engine instances
                try:
                    import EngineLoader as engines_loader

                    engines_loader.registry.apply_translations(self, tr)
                except Exception:
                    pass
            except Exception:
                pass
            # Update markers
            meta = tr.get("_meta", {})
            self.current_language = meta.get("name", lang_display)
            self.language = lang_display  # preserve chosen preference (may be 'System')
            try:
                self.save_preferences()
            except Exception:
                pass
            try:
                self.log_i18n(
                    f"🌐 Langue appliquée : {self.current_language}",
                    f"🌐 Language applied: {self.current_language}",
                )
            except Exception:
                pass

        _run_coro_async(_do(), _on_result, ui_owner=self)

    def register_language_refresh(self, callback):
        try:
            if not hasattr(self, "_language_refresh_callbacks"):
                self._language_refresh_callbacks = []
            if callable(callback):
                self._language_refresh_callbacks.append(callback)
        except Exception:
            pass

    def tr(self, fr: str, en: str) -> str:
        """Return FR text only when UI language is French; otherwise default to EN.
        This ensures all non-French locales get English by default.
        """
        try:
            lang = str(
                getattr(self, "current_language", "English") or "English"
            ).lower()
        except Exception:
            lang = "english"
        return fr if lang.startswith("fr") else en

    def log_i18n(self, fr: str, en: str) -> None:
        """Append a localized message to the log (EN by default, FR if UI language is French)."""
        try:
            msg = self.tr(fr, en)
        except Exception:
            msg = en
        try:
            if hasattr(self, "log") and self.log:
                self.log.append(msg)
            else:
                print(msg)
        except Exception:
            try:
                print(msg)
            except Exception:
                pass

    def set_compilation_ui_enabled(self, enabled):
        self.set_controls_enabled(enabled)

    def show_language_dialog(self):
        """Show language selection dialog - uses centralized i18n module version."""
        _i18n_show_dialog(self)

    from .deps_analyser import (
        _install_next_dependency,
        _on_dep_pip_finished,
        _on_dep_pip_output,
        suggest_missing_dependencies,
    )

    def _safe_log(self, text):
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

    def _has_active_background_tasks(self):
        # Compilation en cours
        if self.processes:
            return True
        # Tâches liées au venv via le gestionnaire
        if (
            hasattr(self, "venv_manager")
            and self.venv_manager
            and self.venv_manager.has_active_tasks()
        ):
            return True
        # BCASL (pré-compilation) en cours
        try:
            bcasl_thread = getattr(self, "_bcasl_thread", None)
            if bcasl_thread is not None and bcasl_thread.is_alive():
                return True
        except Exception:
            pass
        return False

    def _terminate_background_tasks(self):
        # Stoppe les tâches en arrière-plan liées au venv via le gestionnaire
        try:
            if hasattr(self, "venv_manager") and self.venv_manager:
                self.venv_manager.terminate_tasks()
        except Exception:
            pass

    def closeEvent(self, event):
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

                # Construire le message détaillé
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

                # Construire le message détaillé
                title = "⚠️ Processus en cours"
                msg = "Un processus est actuellement en cours :\n\n"
                if details_disp:
                    for detail in details_disp:
                        msg += f"  • {detail}\n"
                    msg += "\n"
                msg += "Si vous quittez maintenant, le processus sera arrêté et tout travail non sauvegardé sera perdu.\n\n"
                msg += "Voulez-vous vraiment quitter ?"

                yes_text = "Oui, Quitter"
                no_text = "Non, Continuer"

            # Créer la boîte de dialogue avec des boutons personnalisés
            msgbox = QMessageBox(self)
            msgbox.setWindowTitle(title)
            msgbox.setText(msg)
            msgbox.setIcon(QMessageBox.Warning)
            msgbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msgbox.setDefaultButton(QMessageBox.No)

            # Personnaliser les textes des boutons
            msgbox.button(QMessageBox.Yes).setText(yes_text)
            msgbox.button(QMessageBox.No).setText(no_text)

            reply = msgbox.exec()

            if reply == QMessageBox.Yes:
                self._closing = True
                # Annule les compilations en cours si nécessaire
                if self.processes:
                    self.cancel_all_compilations()
                # Stoppe les processus/boîtes de progression en arrière-plan
                self._terminate_background_tasks()
                # Arrêt propre des threads BCASL si actifs
                try:
                    from bcasl.Loader import ensure_bcasl_thread_stopped

                    ensure_bcasl_thread_stopped(self)
                except Exception:
                    pass
                event.accept()
            else:
                event.ignore()
        else:
            # Arrêt propre des threads BCASL si actifs
            try:
                from bcasl.Loader import ensure_bcasl_thread_stopped

                ensure_bcasl_thread_stopped(self)
            except Exception:
                pass
            event.accept()

