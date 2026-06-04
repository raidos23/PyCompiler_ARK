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
PyCompiler ARK — Fenêtre principale Qt.

Ce module ne contient que du code Qt (cycle de vie de la fenêtre, slots,
délégation vers les services Core). Aucune logique métier ici.
"""

import os
from typing import Optional

from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QMainWindow, QMessageBox

from Core.Globals import (
    _latest_gui_instance,
    _run_coro_async,
    _workspace_dir_cache,
    _workspace_dir_lock,
)
from Ui.Gui.Dialogs.VenvDialog import VenvManagerUI
from Ui.Gui.Dialogs.WorkspaceDialog import WorkspaceDialog
from Ui.Gui.UiFeatures import UiFeatures
from Ui.Gui.WorkspaceManipulation import WorkspaceAdvancedManipulation
from Ui.i18n import (
    get_translations,
    is_french_language,
    log_i18n_level,
    log_with_level,
    resolve_system_language,
    tr_fr_en,
)


def get_selected_workspace() -> Optional[str]:
    """Return the currently selected workspace in a thread-safe way."""
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
    Fenêtre principale PyCompiler ARK.

    Cette classe hérite de `UiFeatures` et orchestre uniquement le cycle de vie
    de la fenêtre Qt. Toute la logique métier est déléguée à Core/.
    """

    def __init__(self):
        super().__init__()
        global _latest_gui_instance
        _latest_gui_instance = self

        self.setWindowTitle("PyCompiler ARK")
        self.setGeometry(100, 100, 1280, 720)
        self.setAcceptDrops(True)

        # Étape 1: initialiser l'état runtime de la fenêtre.
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

        # Étape 2: brancher les services partagés (venv manager, sys deps).
        self.venv_manager = VenvManagerUI(self)
        try:
            from Ui.Gui.Dialogs.SysDependencyUI import SysDependencyUI

            self.sys_deps_manager = SysDependencyUI(self)
        except Exception:
            self.sys_deps_manager = None

        # Enregistrement du handler AdvancedAuth pour les requêtes de plugins
        try:
            from Services.AdvancedAuth import Api as AuthApi
            from Ui.Gui.Dialogs.AdvancedAuthUI import AdvancedAuthUI

            AuthApi.register_workspace_change_handler(
                lambda folder: AdvancedAuthUI.handle_workspace_change_request(
                    self, folder
                )
            )
        except Exception:
            pass

        # Étape 3: charger les préférences puis choisir la variante UI.
        self.load_preferences()
        ui_variant = str(os.environ.get("PYCOMPILER_UI_VARIANT", "")).strip().lower()
        if not ui_variant:
            ui_variant = "ide2"
        if ui_variant in {"classic", "classic-gui", "legacy"}:
            ui_variant = "classic"
        if ui_variant in {"ide2", "design2", "ide-like", "idelike", "vscode"}:
            try:
                self.init_ide_like_ui()
                self._ui_variant_active = "ide2"
            except Exception:
                self._ui_variant_active = "classic"
                log_i18n_level(
                    self,
                    "warning",
                    "UI IDE-like indisponible, bascule vers l'interface classique.",
                    "IDE-like UI unavailable, falling back to classic UI.",
                )
                self.init_ui()
        else:
            self._ui_variant_active = "classic"
            self.init_ui()

        # Étape 4: résoudre la langue effective et appliquer l'i18n.
        import locale

        sys_lang = None
        try:
            loc = locale.getlocale()[0] or ""
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

    # =========================================================================
    # DÉLÉGATION UI À UiFeatures
    # =========================================================================

    select_icon = UiFeatures.select_icon
    select_nuitka_icon = UiFeatures.select_nuitka_icon
    show_help_dialog = UiFeatures.show_help_dialog

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

    from Ui.Gui.IdeLikeGui import init_ide_like_ui
    from Ui.Gui.UiConnection import init_ui

    # =========================================================================
    # GESTION DU WORKSPACE
    # =========================================================================

    def dragEnterEvent(self, event: QDropEvent):
        """Handle drag-enter events."""
        WorkspaceAdvancedManipulation.handle_drag_enter_event(self, event)

    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        WorkspaceAdvancedManipulation.handle_drop_event(self, event)

    def add_py_files_from_folder(self, folder):
        """Add Python files from a folder into the workspace list."""
        from Core.WorkSpaceManager.SetupWorkspace import SetupWorkspace

        files = SetupWorkspace.list_python_files(folder)

        # Logique UI pour ajouter les fichiers
        from Core.Configs import load_ark_config, should_exclude_file

        ark_config = load_ark_config(self.workspace_dir) if self.workspace_dir else {}

        workspace_cfg = ark_config.get("workspace", {})
        exclusion_patterns = []
        if isinstance(workspace_cfg, dict):
            exclusion_patterns = workspace_cfg.get("exclude", [])

        added = 0
        for f in files:
            if (
                self.workspace_dir
                and not os.path.commonpath([f, self.workspace_dir])
                == self.workspace_dir
            ):
                continue
            if should_exclude_file(f, self.workspace_dir, exclusion_patterns):
                continue
            if f not in self.python_files:
                self.python_files.append(f)
                if hasattr(self, "file_list"):
                    rel = (
                        os.path.relpath(f, self.workspace_dir)
                        if self.workspace_dir
                        else f
                    )
                    self.file_list.addItem(rel)
                added += 1
        return added

    def select_workspace(self):
        """Open a dialog to select the workspace directory."""
        folder = WorkspaceDialog.select_workspace(self)
        if folder:
            self.apply_workspace_selection(folder, source="ui")

    def apply_workspace_selection(self, folder: str, source: str = "ui") -> bool:
        """Apply workspace selection and refresh GUI state."""
        return WorkspaceDialog.apply_workspace_selection(self, folder, source)

    def select_venv_manually(self):
        """Open manual virtual environment selection."""
        self.venv_manager.select_venv_manually()

    def create_venv_if_needed(self, path):
        """Create a virtual environment when required."""
        self.venv_manager.create_venv_if_needed(path)

    def install_requirements_if_needed(self, path):
        """Install requirements when needed."""
        self.venv_manager.install_requirements_if_needed(path)

    def select_files_manually(self):
        """Open a dialog to add files manually."""
        WorkspaceAdvancedManipulation.select_files_manually(self)

    def open_ark_config(self):
        """Open `ark.yml` from the current workspace."""
        WorkspaceDialog.open_ark_config(self)

    def open_init_workspace_dialog(self):
        """Open the project initialization dialog."""
        from Ui.Gui.Dialogs.InitWorkspaceDialog import open_init_workspace_dialog
        open_init_workspace_dialog(self)

    def on_main_only_changed(self):
        """Handle the `main-only` option toggle."""
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
        """Deprecated compatibility shim."""
        pass

    def remove_selected_file(self):
        """Remove selected files from the workspace list."""
        WorkspaceAdvancedManipulation.remove_selected_file(self)

    def clear_workspace(self):
        """Clear workspace file list without changing the folder."""
        WorkspaceAdvancedManipulation.clear_workspace(self, keep_dir=True)

    def apply_file_filter(self, text: Optional[str] = None) -> None:
        """Filter visible files using the provided text input."""
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
    # COMPILATION (délégation à Ui/Gui/Compilation)
    # =========================================================================

    from Ui.Gui.Dialogs.DepsAnalyserUI import (
        _install_next_dependency,
        _on_dep_pip_finished,
        _on_dep_pip_output,
        suggest_missing_dependencies,
    )

    def open_lock_dialog(self):
        """Open the build lock management dialog."""
        from Ui.Gui.Dialogs.LockDialog import open_lock_dialog

        open_lock_dialog(self)

    from Ui.Gui.Dialogs.CompilerDialog import (
        _continue_compile_all,
        cancel_all_compilations,
        compile_all,
        handle_finished,
        handle_stderr,
        handle_stdout,
        rebuild_from_lock,
        show_error_dialog,
        start_compilation_process,
        try_install_missing_modules,
        try_start_processes,
    )
    from Ui.PreferencesManager import load_preferences, save_preferences

    # =========================================================================
    # PRÉFÉRENCES (délégation à Core/PreferencesManager)
    # =========================================================================

    # =========================================================================
    # DÉPENDANCES (délégation à Core/deps_analyser)
    # =========================================================================

    # =========================================================================
    # INTERNATIONALISATION
    # =========================================================================

    current_language = "English"

    def tr(self, fr: str, en: str) -> str:
        """Return FR text for French UI, otherwise EN text."""
        return tr_fr_en(self, fr, en)

    # =========================================================================
    # JOURNALISATION
    # =========================================================================

    def _infer_log_level(self, text) -> str:
        try:
            s = str(text or "").strip()
        except Exception:
            s = ""
        if not s:
            return "info"
        emoji_levels = {
            "❌": "error",
            "⚠️": "warning",
            "✅": "success",
            "ℹ️": "info",
            "📝": "state",
            "📋": "state",
            "🔍": "state",
            "🔧": "state",
            "🔨": "state",
            "➡️": "state",
            "📦": "state",
            "🗑️": "state",
        }
        for emoji, lvl in emoji_levels.items():
            if s.startswith(emoji):
                return lvl
        low = s.lower()
        if any(
            tok in low
            for tok in (
                "error",
                "erreur",
                "échec",
                "echec",
                "failed",
                "invalid",
                "refus",
            )
        ):
            return "error"
        if any(tok in low for tok in ("warning", "avert", "warn", "attention")):
            return "warning"
        if any(tok in low for tok in ("success", "succès", "reussi", "réussi")):
            return "success"
        if any(tok in low for tok in ("state", "status", "état", "etat")):
            return "state"
        return "info"

    def _safe_log(self, text):
        """Write a log line with safe fallback behavior."""
        try:
            level = self._infer_log_level(text)
            log_with_level(self, level, text)
            return
        except Exception:
            pass

    # =========================================================================
    # TÂCHES EN ARRIÈRE-PLAN
    # =========================================================================

    def _has_active_background_tasks(self) -> bool:
        """Check whether any background task is still active."""
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
            if bcasl_thread is not None and bcasl_thread.isRunning():
                return True
        except Exception:
            pass
        try:
            tasks = getattr(self, "_sysdep_tasks", None) or []
            for task in list(tasks):
                proc = task.get("process") if isinstance(task, dict) else None
                if proc is not None and proc.state() != proc.NotRunning:
                    return True
        except Exception:
            pass
        return False

    def _terminate_background_tasks(self):
        """Terminate running background tasks safely."""
        try:
            if hasattr(self, "venv_manager") and self.venv_manager:
                self.venv_manager.terminate_tasks()
        except Exception:
            pass
        try:
            tasks = getattr(self, "_sysdep_tasks", None) or []
            for task in list(tasks):
                proc = task.get("process") if isinstance(task, dict) else None
                dlg = task.get("dialog") if isinstance(task, dict) else None
                try:
                    if proc is not None and proc.state() != proc.NotRunning:
                        from Core.process_killer import kill_process_tree

                        kill_process_tree(proc.processId())
                except Exception:
                    pass
                try:
                    if dlg is not None:
                        dlg.close()
                except Exception:
                    pass
            if isinstance(tasks, list):
                tasks.clear()
        except Exception:
            pass

    # =========================================================================
    # ÉVÉNEMENT DE FERMETURE
    # =========================================================================

    def closeEvent(self, event):
        """Handle application close and guard against active background tasks."""
        if self._has_active_background_tasks():
            details = []
            if self.processes:
                details.append("compilation")
            is_french = is_french_language(self)
            if hasattr(self, "venv_manager") and self.venv_manager:
                try:
                    details.extend(
                        self.venv_manager.get_active_task_labels(
                            "Français" if is_french else "English"
                        )
                    )
                except Exception:
                    pass
            try:
                tasks = getattr(self, "_sysdep_tasks", None) or []
                for task in list(tasks):
                    if not isinstance(task, dict):
                        continue
                    proc = task.get("process")
                    if proc is None or proc.state() == proc.NotRunning:
                        continue
                    if is_french:
                        details.append(task.get("label_fr") or "dépendances système")
                    else:
                        details.append(task.get("label_en") or "system dependencies")
            except Exception:
                pass

            if not is_french:
                mapping = {"compilation": "build"}
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
                    from Ui.Gui.Dialogs.BcaslDialog import ensure_bcasl_thread_stopped

                    ensure_bcasl_thread_stopped(self)
                except Exception:
                    pass
                event.accept()
            else:
                event.ignore()
        else:
            try:
                from Ui.Gui.Dialogs.BcaslDialog import ensure_bcasl_thread_stopped

                ensure_bcasl_thread_stopped(self)
            except Exception:
                pass
            event.accept()
