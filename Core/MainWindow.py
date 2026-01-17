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
import threading
from typing import Optional

from PySide6.QtCore import QObject, QProcess, Qt, QTimer, Signal
from PySide6.QtGui import QDropEvent, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QWidget
from .dialogs import ProgressDialog, CompilationProcessDialog
from .Venv_Manager import VenvManager

# Référence globale vers l'instance GUI pour récupération du workspace par l'API_SDK
_latest_gui_instance = None

# Non-blocking workspace cache for cross-thread access
_workspace_dir_cache = None
_workspace_dir_lock = threading.RLock()


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


class _UiInvoker(QObject):
    _sig = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sig.connect(self._exec, Qt.QueuedConnection)

    def post(self, fn):
        try:
            self._sig.emit(fn)
        except Exception:
            pass

    def _exec(self, fn):
        try:
            fn()
        except Exception:
            pass


def _run_coro_async(coro, on_result, ui_owner=None):
    invoker = None
    try:
        if ui_owner is not None and isinstance(ui_owner, QObject):
            invoker = getattr(ui_owner, "_ui_invoker", None)
            if invoker is None:
                invoker = _UiInvoker(ui_owner)
                setattr(ui_owner, "_ui_invoker", invoker)
    except Exception:
        invoker = None

    def _runner():
        try:
            res = asyncio.run(coro)
        except Exception as e:
            res = e
        try:
            if invoker is not None:
                invoker.post(lambda: on_result(res))
            else:
                QTimer.singleShot(0, lambda: on_result(res))
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True).start()


# Synchronous request from background threads to change workspace via GUI thread
# Ensures confirmation dialog is shown and result returned to caller
from PySide6.QtCore import QEventLoop as _QEventLoop


def request_workspace_change_from_BcPlugin(folder: str) -> bool:
    try:
        gui = _latest_gui_instance
        if gui is None:
            # Try active window
            app = QApplication.instance()
            w = app.activeWindow() if app else None
            if w and hasattr(w, "apply_workspace_selection"):
                gui = w
        if gui is None:
            # No GUI instance: accept request by contract
            return True
        invoker = getattr(gui, "_ui_invoker", None)
        if invoker is None or not isinstance(invoker, _UiInvoker):
            invoker = _UiInvoker(gui)
            setattr(gui, "_ui_invoker", invoker)
        result_holder = {"ok": False}
        loop = _QEventLoop()

        def _do():
            try:
                result_holder["ok"] = bool(
                    gui.apply_workspace_selection(str(folder), source="plugin")
                )
            except Exception:
                result_holder["ok"] = False
            finally:
                try:
                    loop.quit()
                except Exception:
                    pass

        try:
            invoker.post(_do)
        except Exception:
            # Fallback: direct call in case invoker posting fails
            try:
                return bool(gui.apply_workspace_selection(str(folder), source="plugin"))
            except Exception:
                return False
        loop.exec()
        return bool(result_holder.get("ok", False))
    except Exception:
        # Accept by contract even on unexpected errors
        return True


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

    from .init_ui import init_ui

    def add_pyinstaller_data(self):
        import os

        from PySide6.QtCore import QDir
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        choix, ok = QInputDialog.getItem(
            self,
            "Type d'inclusion",
            "Inclure un fichier ou un dossier ?",
            ["Fichier", "Dossier"],
            0,
            False,
        )
        if not ok:
            return
        if choix == "Fichier":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Sélectionner un fichier à inclure avec PyInstaller"
            )
            if file_path:
                dest, ok = QInputDialog.getText(
                    self,
                    "Chemin de destination",
                    "Chemin de destination dans l'exécutable :",
                    text=os.path.basename(file_path),
                )
                if ok and dest:
                    self.pyinstaller_data.append((file_path, dest))
                    if hasattr(self, "log"):
                        self.log_i18n(
                            f"Fichier ajouté à PyInstaller : {file_path} => {dest}",
                            f"File added to PyInstaller: {file_path} => {dest}",
                        )
        elif choix == "Dossier":
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Sélectionner un dossier à inclure avec PyInstaller",
                QDir.homePath(),
            )
            if dir_path:
                dest, ok = QInputDialog.getText(
                    self,
                    "Chemin de destination",
                    "Chemin de destination dans l'exécutable :",
                    text=os.path.basename(dir_path),
                )
                if ok and dest:
                    self.pyinstaller_data.append((dir_path, dest))
                    if hasattr(self, "log"):
                        self.log_i18n(
                            f"Dossier ajouté à PyInstaller : {dir_path} => {dest}",
                            f"Folder added to PyInstaller: {dir_path} => {dest}",
                        )

    def add_nuitka_data_file(self):
        import os

        from PySide6.QtCore import QDir
        from PySide6.QtWidgets import QFileDialog, QInputDialog

        choix, ok = QInputDialog.getItem(
            self,
            "Type d'inclusion",
            "Inclure un fichier ou un dossier ?",
            ["Fichier", "Dossier"],
            0,
            False,
        )
        if not ok:
            return
        if not hasattr(self, "nuitka_data_files"):
            self.nuitka_data_files = []
        if not hasattr(self, "nuitka_data_dirs"):
            self.nuitka_data_dirs = []
        if choix == "Fichier":
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Sélectionner un fichier à inclure avec Nuitka"
            )
            if file_path:
                dest, ok = QInputDialog.getText(
                    self,
                    "Chemin de destination",
                    "Chemin de destination dans l'exécutable :",
                    text=os.path.basename(file_path),
                )
                if ok and dest:
                    self.nuitka_data_files.append((file_path, dest))
                    if hasattr(self, "log"):
                        self.log_i18n(
                            f"Fichier ajouté à Nuitka : {file_path} => {dest}",
                            f"File added to Nuitka: {file_path} => {dest}",
                        )
        elif choix == "Dossier":
            dir_path = QFileDialog.getExistingDirectory(
                self, "Sélectionner un dossier à inclure avec Nuitka", QDir.homePath()
            )
            if dir_path:
                dest, ok = QInputDialog.getText(
                    self,
                    "Chemin de destination",
                    "Chemin de destination dans l'exécutable :",
                    text=os.path.basename(dir_path),
                )
                if ok and dest:
                    self.nuitka_data_dirs.append((dir_path, dest))
                    if hasattr(self, "log"):
                        self.log_i18n(
                            f"Dossier ajouté à Nuitka : {dir_path} => {dest}",
                            f"Folder added to Nuitka: {dir_path} => {dest}",
                        )

    def dragEnterEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        added = 0
        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                added += self.add_py_files_from_folder(path)
            elif path.endswith(".py"):
                # Vérifie que le fichier est dans workspace (si défini)
                if (
                    self.workspace_dir
                    and not os.path.commonpath([path, self.workspace_dir])
                    == self.workspace_dir
                ):
                    self.log_i18n(
                        f"⚠️ Ignoré (hors workspace): {path}",
                        f"⚠️ Ignored (outside workspace): {path}",
                    )
                    continue
                if path not in self.python_files:
                    self.python_files.append(path)
                    relative_path = (
                        os.path.relpath(path, self.workspace_dir)
                        if self.workspace_dir
                        else path
                    )
                    self.file_list.addItem(relative_path)
                    added += 1
        self.log_i18n(
            f"✅ {added} fichier(s) ajouté(s) via drag & drop.",
            f"✅ {added} file(s) added via drag & drop.",
        )
        self.update_command_preview()

    def add_py_files_from_folder(self, folder):
        from Core.ark_config_loader import load_ark_config, should_exclude_file

        count = 0
        excluded_count = 0
        # Charger la configuration ARK pour les patterns d'exclusion
        ark_config = load_ark_config(self.workspace_dir)
        exclusion_patterns = ark_config.get("exclusion_patterns", [])

        for root, _, files in os.walk(folder):
            for f in files:
                if f.endswith(".py"):
                    full_path = os.path.join(root, f)
                    if (
                        self.workspace_dir
                        and not os.path.commonpath([full_path, self.workspace_dir])
                        == self.workspace_dir
                    ):
                        continue

                    # Vérifier les patterns d'exclusion depuis ARK_Main_Config.yml
                    if should_exclude_file(
                        full_path, self.workspace_dir, exclusion_patterns
                    ):
                        excluded_count += 1
                        continue

                    if full_path not in self.python_files:
                        self.python_files.append(full_path)
                        relative_path = (
                            os.path.relpath(full_path, self.workspace_dir)
                            if self.workspace_dir
                            else full_path
                        )
                        self.file_list.addItem(relative_path)
                        count += 1

        # Afficher un message récapitulatif si des fichiers ont été exclus
        if excluded_count > 0:
            self.log_i18n(
                f"⏩ Exclusion appliquée : {excluded_count} fichier(s) exclu(s) selon ARK_Main_Config.yml",
                f"⏩ Exclusion applied: {excluded_count} file(s) excluded according to ARK_Main_Config.yml",
            )

        return count

    def select_workspace(self):
        folder = QFileDialog.getExistingDirectory(self, "Choisir le dossier du projet")
        if folder:
            self.apply_workspace_selection(folder, source="ui")

    def apply_workspace_selection(self, folder: str, source: str = "ui") -> bool:
        try:
            # Afficher le dialog de chargement du workspace
            try:
                loading_dialog = CompilationProcessDialog(
                    "Chargement de l'espace de travail", self
                )
                loading_dialog.set_status("📁 Chargement de l'espace de travail...")
                loading_dialog.btn_cancel.setEnabled(False)
                loading_dialog.show()
                QApplication.processEvents()
            except Exception:
                loading_dialog = None

            # Ensure target folder exists; auto-create if missing; never refuse
            if not folder:
                try:
                    self.log_i18n(
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
                        self.log_i18n(
                            f"📁 Dossier cré�� automatiquement: {folder}",
                            f"📁 Folder created automatically: {folder}",
                        )
                    except Exception:
                        pass
                except Exception:
                    try:
                        self.log_i18n(
                            f"⚠️ Impossible de créer le dossier, poursuite quand même: {folder}",
                            f"⚠️ Unable to create folder, continuing anyway: {folder}",
                        )
                    except Exception:
                        pass
            # Confirmation when API requests workspace change
            if str(source).lower() == "plugin":
                # Auto-approve API workspace switch; cancel running builds if any
                try:
                    if getattr(self, "processes", None) and self.processes:
                        try:
                            self.log_i18n(
                                "⛔ Arrêt des compilations en cours pour changer de workspace (API).",
                                "⛔ Stopping ongoing builds to switch workspace (API).",
                            )
                        except Exception:
                            pass
                        try:
                            self.cancel_all_compilations()
                        except Exception:
                            pass
                except Exception:
                    pass
            else:
                # Non-API requests: never refuse; cancel running builds if any
                if getattr(self, "processes", None) and self.processes:
                    try:
                        self.log_i18n(
                            "⛔ Arrêt des compilations en cours pour changer de workspace (UI).",
                            "⛔ Stopping ongoing builds to switch workspace (UI).",
                        )
                    except Exception:
                        pass
                    try:
                        self.cancel_all_compilations()
                    except Exception:
                        pass
            self.workspace_dir = folder
            try:
                global _workspace_dir_cache
                with _workspace_dir_lock:
                    _workspace_dir_cache = folder
            except Exception:
                pass
            self.label_folder.setText(f"Dossier sélectionné : {folder}")
            self.python_files.clear()
            self.file_list.clear()
            self.add_py_files_from_folder(folder)
            self.selected_files.clear()
            self.update_command_preview()
            try:
                self.save_preferences()
            except Exception:
                pass
            # -- Ajout automatique --
            try:
                self.venv_manager.create_venv_if_needed(folder)
                venv_path = None
                for name in (".venv", "venv"):
                    cand = os.path.join(folder, name)
                    if os.path.isdir(cand):
                        venv_path = cand
                        break
                if not venv_path:
                    self.log_i18n(
                        "Aucun dossier venv détecté dans ce workspace.",
                        "No venv folder detected in this workspace.",
                    )
                else:
                    self.log_i18n("Dossier venv détecté.", "Venv folder detected.")
            except Exception:
                pass

            # Créer le fichier ARK_Main_Config.yml s'il n'existe pas
            try:
                from Core.ark_config_loader import create_default_ark_config

                if create_default_ark_config(folder):
                    self.log_i18n(
                        "📋 Fichier ARK_Main_Config.yml créé dans le workspace.",
                        "📋 ARK_Main_Config.yml file created in workspace.",
                    )
            except Exception as e:
                self.log_i18n(
                    f"⚠️ Impossible de créer ARK_Main_Config.yml: {e}",
                    f"⚠️ Failed to create ARK_Main_Config.yml: {e}",
                )

            # Fermer le dialog de chargement
            try:
                if loading_dialog:
                    loading_dialog.close()
            except Exception:
                pass

            return True
        except Exception as _e:
            try:
                self.log_i18n(
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

    def _check_next_venv_pkg(self):
        if self._venv_check_index >= len(self._venv_check_pkgs):
            self.venv_check_progress.set_message("Vérification terminée.")
            self.venv_check_progress.set_progress(2, 2)
            self.venv_check_progress.close()
            # Installer les dépendances du projet si un requirements.txt est présent
            if self.workspace_dir:
                self.install_requirements_if_needed(self.workspace_dir)
            return
        pkg = self._venv_check_pkgs[self._venv_check_index]
        process = QProcess(self)
        self._venv_check_process = process
        process.setProgram(self._venv_check_pip_exe)
        process.setArguments(["show", pkg])
        process.setWorkingDirectory(self._venv_check_path)
        process.finished.connect(
            lambda code, status: self._on_venv_pkg_checked(process, code, status, pkg)
        )
        process.start()

    def _on_venv_pkg_checked(self, process, code, status, pkg):
        if code == 0:
            self.log_i18n(
                f"✅ {pkg} déjà installé dans le venv.",
                f"✅ {pkg} already installed in venv.",
            )
            self._venv_check_index += 1
            self.venv_check_progress.set_message(
                f"Vérification de {self._venv_check_pkgs[self._venv_check_index] if self._venv_check_index < len(self._venv_check_pkgs) else ''}..."
            )
            self.venv_check_progress.set_progress(self._venv_check_index, 2)
            self._check_next_venv_pkg()
        else:
            self.log_i18n(
                f"📦 Installation automatique de {pkg} dans le venv...",
                f"📦 Automatic installation of {pkg} in venv...",
            )
            self.venv_check_progress.set_message(f"Installation de {pkg}...")
            self.venv_check_progress.progress.setRange(0, 0)
            process2 = QProcess(self)
            self._venv_check_install_process = process2
            process2.setProgram(self._venv_check_pip_exe)
            process2.setArguments(["install", pkg])
            process2.setWorkingDirectory(self._venv_check_path)
            process2.readyReadStandardOutput.connect(
                lambda: self._on_venv_check_output(process2)
            )
            process2.readyReadStandardError.connect(
                lambda: self._on_venv_check_output(process2, error=True)
            )
            process2.finished.connect(
                lambda code2, status2: self._on_venv_pkg_installed(
                    process2, code2, status2, pkg
                )
            )
            process2.start()

    def _on_venv_check_output(self, process, error=False):
        if getattr(self, "_closing", False):
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        if hasattr(self, "venv_check_progress") and self.venv_check_progress:
            lines = data.strip().splitlines()
            if lines:
                self.venv_check_progress.set_message(lines[-1])
        self._safe_log(data)

    def _on_venv_pkg_installed(self, process, code, status, pkg):
        if getattr(self, "_closing", False):
            return
        if code == 0:
            self._safe_log(f"✅ {pkg} installé dans le venv.")
        else:
            self._safe_log(f"❌ Erreur installation {pkg} (code {code})")
        self._venv_check_index += 1
        self.venv_check_progress.progress.setRange(0, 2)
        self.venv_check_progress.set_progress(self._venv_check_index, 2)
        self._check_next_venv_pkg()

    def select_venv_manually(self):
        self.venv_manager.select_venv_manually()

    def create_venv_if_needed(self, path):
        # Support both '.venv' and 'venv'
        existing = None
        for name in (".venv", "venv"):
            cand = os.path.join(path, name)
            if os.path.exists(cand):
                existing = cand
                break
        venv_path = existing or os.path.join(path, "venv")
        if not existing:
            self._safe_log("🔧 Aucun venv trouvé, création automatique...")
            try:
                # Recherche d'un python embarqué à côté de l'exécutable
                python_candidate = None
                exe_dir = os.path.dirname(sys.executable)
                # Windows: python.exe, Linux/Mac: python3 ou python
                candidates = [
                    os.path.join(exe_dir, "python.exe"),
                    os.path.join(exe_dir, "python3"),
                    os.path.join(exe_dir, "python"),
                    os.path.join(exe_dir, "python_embedded", "python.exe"),
                    os.path.join(exe_dir, "python_embedded", "python3"),
                    os.path.join(exe_dir, "python_embedded", "python"),
                ]
                # Recherche également les interpréteurs système disponibles dans le PATH
                path_candidates = []
                try:
                    if platform.system() == "Windows":
                        w = shutil.which("py")
                        if w:
                            path_candidates.append(w)
                    for name in ("python3", "python"):
                        w = shutil.which(name)
                        if w:
                            path_candidates.append(w)
                except Exception:
                    pass
                for c in path_candidates:
                    if c not in candidates:
                        candidates.append(c)
                for c in candidates:
                    if os.path.isfile(c):
                        python_candidate = c
                        break
                if not python_candidate:
                    python_candidate = sys.executable
                # Journalisation du type d'interpréteur détecté
                base = os.path.basename(python_candidate).lower()
                if (
                    python_candidate.startswith(exe_dir)
                    or "python_embedded" in python_candidate
                ):
                    self.log_i18n(
                        f"➡️ Utilisation de l'interpréteur Python embarqué : {python_candidate}",
                        f"➡️ Using embedded Python interpreter: {python_candidate}",
                    )
                elif base in ("py", "py.exe") or shutil.which(base):
                    self.log_i18n(
                        f"➡️ Utilisation de l'interpréteur système : {python_candidate}",
                        f"➡️ Using system interpreter: {python_candidate}",
                    )
                else:
                    self.log_i18n(
                        f"➡️ Utilisation de sys.executable : {python_candidate}",
                        f"➡️ Using sys.executable: {python_candidate}",
                    )
                self.venv_progress_dialog = ProgressDialog(
                    "Création de l'environnement virtuel", self
                )
                self.venv_progress_dialog.set_message("Création du venv...")
                process = QProcess(self)
                self._venv_create_process = process
                process.setProgram(python_candidate)
                args = ["-m", "venv", venv_path]
                # Si l'on utilise le launcher Windows 'py', forcer Python 3 avec -3
                if base in ("py", "py.exe"):
                    args = ["-3"] + args
                process.setArguments(args)
                process.setWorkingDirectory(path)
                process.readyReadStandardOutput.connect(
                    lambda: self._on_venv_output(process)
                )
                process.readyReadStandardError.connect(
                    lambda: self._on_venv_output(process, error=True)
                )
                process.finished.connect(
                    lambda code, status: self._on_venv_created(
                        process, code, status, venv_path
                    )
                )
                self._venv_progress_lines = 0
                self.venv_progress_dialog.show()
                process.start()
            except Exception as e:
                self._safe_log(f"❌ Échec de création du venv : {e}")

    def _on_venv_output(self, process, error=False):
        if getattr(self, "_closing", False):
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        if hasattr(self, "venv_progress_dialog") and self.venv_progress_dialog:
            lines = data.strip().splitlines()
            if lines:
                self.venv_progress_dialog.set_message(lines[-1])
            self._venv_progress_lines += len(lines)
            self.venv_progress_dialog.set_progress(self._venv_progress_lines, 0)
        self._safe_log(data)

    def _on_venv_created(self, process, code, status, venv_path):
        if getattr(self, "_closing", False):
            return
        if code == 0:
            self._safe_log("✅ Environnement virtuel créé avec succès.")
            if hasattr(self, "venv_progress_dialog") and self.venv_progress_dialog:
                self.venv_progress_dialog.set_message("Environnement prêt.")
                self.venv_progress_dialog.set_progress(1, 1)
                self.venv_progress_dialog.close()
            # Installer les dépendances du projet à partir de requirements.txt si présent
            self.install_requirements_if_needed(os.path.dirname(venv_path))
        else:
            self._safe_log(f"❌ Échec de création du venv (code {code})")
            if hasattr(self, "venv_progress_dialog") and self.venv_progress_dialog:
                self.venv_progress_dialog.set_message(
                    "Erreur lors de la création du venv."
                )
                self.venv_progress_dialog.close()
        QApplication.processEvents()

    def install_requirements_if_needed(self, path):
        req_path = os.path.join(path, "requirements.txt")
        if os.path.exists(req_path):
            self._safe_log(
                "📦 Installation des dépendances à partir de requirements.txt..."
            )
            # Resolve pip inside '.venv' or 'venv'
            venv_root = None
            for name in (".venv", "venv"):
                cand = os.path.join(path, name)
                if os.path.isdir(cand):
                    venv_root = cand
                    break
            if not venv_root:
                self._safe_log("⚠️ Aucun venv détecté pour installer requirements.txt.")
                return
            pip_exe = os.path.join(
                venv_root, "Scripts" if platform.system() == "Windows" else "bin", "pip"
            )
            try:
                self.progress_dialog = ProgressDialog(
                    "Installation des dépendances", self
                )
                self.progress_dialog.set_message(
                    "Démarrage de l'installation des dépendances..."
                )
                process = QProcess(self)
                self._req_install_process = process
                process.setProgram(pip_exe)
                process.setArguments(["install", "-r", req_path])
                process.setWorkingDirectory(path)
                process.readyReadStandardOutput.connect(
                    lambda: self._on_pip_output(process)
                )
                process.readyReadStandardError.connect(
                    lambda: self._on_pip_output(process, error=True)
                )
                process.finished.connect(
                    lambda code, status: self._on_pip_finished(process, code, status)
                )
                self._pip_progress_lines = 0
                self.progress_dialog.show()
                process.start()
                # NE PAS bloquer ici, la fermeture se fait dans _on_pip_finished
            except Exception as e:
                self.log_i18n(
                    f"❌ Échec installation requirements.txt : {e}",
                    f"❌ Failed to install requirements.txt: {e}",
                )

    def _on_pip_output(self, process, error=False):
        if getattr(self, "_closing", False):
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            # Affiche la dernière ligne reçue
            lines = data.strip().splitlines()
            if lines:
                self.progress_dialog.set_message(lines[-1])
            self._pip_progress_lines += len(lines)
            # Simule une progression (pip ne donne pas de %)
            self.progress_dialog.set_progress(self._pip_progress_lines, 0)
        self._safe_log(data)

    def _on_pip_finished(self, process, code, status):
        if getattr(self, "_closing", False):
            return
        if code == 0:
            self._safe_log("✅ requirements.txt installé.")
            if hasattr(self, "progress_dialog") and self.progress_dialog:
                self.progress_dialog.set_message("Installation terminée.")
        else:
            self._safe_log(f"❌ Échec installation requirements.txt (code {code})")
            if hasattr(self, "progress_dialog") and self.progress_dialog:
                self.progress_dialog.set_message("Erreur lors de l'installation.")
        if hasattr(self, "progress_dialog") and self.progress_dialog:
            self.progress_dialog.close()
        QApplication.processEvents()

    def select_files_manually(self):
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                self.tr("Attention", "Warning"),
                self.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Sélectionner des fichiers Python",
            self.workspace_dir,
            "Python Files (*.py)",
        )
        if files:
            valid_files = []
            for f in files:
                if os.path.commonpath([f, self.workspace_dir]) == self.workspace_dir:
                    valid_files.append(f)
                else:
                    QMessageBox.warning(
                        self,
                        self.tr("Fichier hors workspace", "File outside workspace"),
                        self.tr(
                            f"Le fichier {f} est en dehors du workspace et sera ignoré.",
                            f"The file {f} is outside the workspace and will be ignored.",
                        ),
                    )
            if valid_files:
                self.selected_files = valid_files
                self.log_i18n(
                    f"✅ {len(valid_files)} fichier(s) sélectionné(s) manuellement.\n",
                    f"✅ {len(valid_files)} file(s) selected manually.\n",
                )
                self.update_command_preview()

    def open_ark_config(self):
        """Ouvre le fichier ARK_Main_Config.yml dans l'éditeur par défaut"""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                self.tr("Attention", "Warning"),
                self.tr(
                    "Veuillez d'abord sélectionner un dossier workspace.",
                    "Please select a workspace folder first.",
                ),
            )
            return

        config_path = os.path.join(self.workspace_dir, "ARK_Main_Config.yml")

        # Créer le fichier s'il n'existe pas
        if not os.path.exists(config_path):
            try:
                from Core.ark_config_loader import create_default_ark_config

                if create_default_ark_config(self.workspace_dir):
                    self.log_i18n(
                        "📋 Fichier ARK_Main_Config.yml créé.",
                        "📋 ARK_Main_Config.yml file created.",
                    )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    self.tr("Erreur", "Error"),
                    self.tr(
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

            self.log_i18n(
                f"📝 Ouverture de {config_path}",
                f"📝 Opening {config_path}",
            )
        except Exception as e:
            QMessageBox.warning(
                self,
                self.tr("Attention", "Warning"),
                self.tr(
                    f"Impossible d'ouvrir le fichier: {e}\nChemin: {config_path}",
                    f"Failed to open file: {e}\nPath: {config_path}",
                ),
            )

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
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            # Récupère le chemin relatif affiché
            rel_path = item.text()
            # Construit le chemin absolu si workspace_dir défini
            abs_path = (
                os.path.join(self.workspace_dir, rel_path)
                if self.workspace_dir
                else rel_path
            )
            # Supprime de python_files si présent
            if abs_path in self.python_files:
                self.python_files.remove(abs_path)
            # Supprime de selected_files si présent
            if abs_path in self.selected_files:
                self.selected_files.remove(abs_path)
            # Supprime l'item de la liste graphique
            self.file_list.takeItem(self.file_list.row(item))
        self.update_command_preview()

    def show_help_dialog(self):
        # Minimal help dialog with current license information
        if getattr(self, "current_language", "Français") == "English":
            help_text = (
                "<b>PyCompiler ARK++ — Quick Help</b><br>"
                "<ul>"
                "<li>1) Select the Workspace and add your .py files.</li>"
                "<li>2) Configure pre‑compile plugins via <b>API Loader</b> (BCASL).</li>"
                "<li>3) Configure options in the <b>PyInstaller</b>, <b>Nuitka</b> or <b>CX_Freeze</b> tab.</li>"
                "<li>4) Click <b>Build</b> and follow the logs.</li>"
                "</ul>"
                "<b>Notes</b><br>"
                "<ul>"
                "<li>When a build starts, all action controls are disabled (including API Loader) until it finishes or is canceled.</li>"
                "<li>Pre‑compilation (BCASL) completes before compilation.</li>"
                "<li>A <i>venv</i> can be created automatically; requirements.txt is installed if present; tools are installed into the venv as needed.</li>"
                "<li>API‑initiated workspace changes are auto‑applied; running builds are canceled before switching.</li>"
                "</ul>"
                "<b>License</b>: Apache-2.0 — <a href='https://www.apache.org/licenses/LICENSE-2.0'>apache.org/licenses/LICENSE-2.0</a>"
                "<br><b>Author</b>: Ague Samuel Amen"
                "<br>© 2026 Ague Samuel Amen"
            )
        else:
            help_text = (
                "<b>PyCompiler ARK++ — Aide rapide</b><br>"
                "<ul>"
                "<li>1) Sélectionnez le Workspace et ajoutez vos fichiers .py.</li>"
                "<li>2) Configurez les plugins de pré‑compilation via <b>API Loader</b> (BCASL).</li>"
                "<li>3) Réglez les options dans l’onglet <b>PyInstaller</b> ou <b>Nuitka</b>.</li>"
                "<li>4) Cliquez sur <b>Build</b> et suivez les logs.</li>"
                "</ul>"
                "<b>Notes</b><br>"
                "<ul>"
                "<li>Au démarrage d’un build, tous les contrôles d’action sont désactivés (y compris API Loader) jusqu’à la fin ou l’annulation.</li>"
                "<li>La pré‑compilation (BCASL) se termine avant la compilation.</li>"
                "<li>Un <i>venv</i> peut être créé automatiquement ; requirements.txt est installé s’il est présent ; les outils sont installés dans le venv si nécessaire.</li>"
                "<li>Les demandes de changement de workspace via l’API sont appliquées automatiquement ; les builds en cours sont annulés avant le changement.</li>"
                "</ul>"
                "<b>Licence</b> : Apache-2.0 — <a href='https://www.apache.org/licenses/LICENSE-2.0'>apache.org/licenses/LICENSE-2.0</a>"
                "<br><b>Auteur</b> : Ague Samuel Amen"
                "<br>© 2026 Ague Samuel Amen"
            )
        dlg = QMessageBox(self)
        dlg.setWindowTitle(self.tr("Aide", "Help"))
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
                        from .init_ui import apply_theme

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
        compute_for_all,
        _continue_compile_all,
    )

    def set_controls_enabled(self, enabled):
        self.btn_build_all.setEnabled(enabled)
        # Forcer une mise à jour visuelle pour refléter l'état grisé avec certains thèmes
        try:
            if self.btn_build_all and hasattr(self.btn_build_all, "style"):
                self.btn_build_all.style().unpolish(self.btn_build_all)
                self.btn_build_all.style().polish(self.btn_build_all)
                self.btn_build_all.update()
        except Exception:
            pass
        self.btn_cancel_all.setEnabled(not enabled)
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
        # API Loader button (BCASL)
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
                getattr(self, "btn_build_all", None),
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
            if hasattr(self, "btn_cancel_all") and self.btn_cancel_all:
                try:
                    self.btn_cancel_all.style().unpolish(self.btn_cancel_all)
                    self.btn_cancel_all.style().polish(self.btn_cancel_all)
                    self.btn_cancel_all.update()
                except Exception:
                    pass
        except Exception:
            pass

    from .preferences import load_preferences, save_preferences, update_ui_state

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

    def _apply_translations(self, tr: dict):
        # Utilitaires internes pour éviter les valeurs codées en dur
        def _set(attr: str, key: str, method: str = "setText"):
            try:
                widget = getattr(self, attr, None)
                value = tr.get(key)
                if widget is not None and value:
                    getattr(widget, method)(value)
            except Exception:
                pass

        # Sidebar & main buttons
        _set("btn_select_folder", "select_folder")
        _set("btn_select_files", "select_files")
        _set("btn_build_all", "build_all")
        _set("btn_export_config", "export_config")
        _set("btn_import_config", "import_config")
        _set("btn_cancel_all", "cancel_all")
        _set("btn_suggest_deps", "suggest_deps")
        _set("btn_help", "help")
        _set("btn_show_stats", "show_stats")

        # Bouton de langue (variante System vs simple), sans valeur de secours
        try:
            if getattr(self, "select_lang", None):
                if (
                    getattr(self, "language_pref", getattr(self, "language", "System"))
                    == "System"
                ):
                    val = tr.get("choose_language_system_button") or tr.get(
                        "choose_language_button"
                    )
                else:
                    val = tr.get("choose_language_button")
                if val:
                    self.select_lang.setText(val)
        except Exception:
            pass

        # Bouton de thème (variante System vs simple), sans valeur de secours
        try:
            if getattr(self, "select_theme", None):
                if getattr(self, "theme", "System") == "System":
                    val = tr.get("choose_theme_system_button") or tr.get(
                        "choose_theme_button"
                    )
                else:
                    val = tr.get("choose_theme_button")
                if val:
                    self.select_theme.setText(val)
        except Exception:
            pass

        # Workspace
        _set("venv_button", "venv_button")
        _set("label_workspace_section", "label_workspace_section")
        _set("venv_label", "venv_label")
        _set("label_folder", "label_folder")

        # Files
        _set("label_files_section", "label_files_section")
        _set("btn_remove_file", "btn_remove_file")

        # Logs
        _set("label_logs_section", "label_logs_section")

        # Note: Tabs are now dynamically created by engines, no static translation needed

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
            self._apply_translations(tr)
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
                    import Core.engines_loader as engines_loader

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
        from PySide6.QtWidgets import QInputDialog

        from .i18n import available_languages, get_translations, resolve_system_language

        async def _prepare():
            langs = await available_languages()
            name_to_code = {l.get("name", l.get("code")): l.get("code") for l in langs}
            display = ["System"] + list(name_to_code.keys())
            current = getattr(
                self, "language_pref", getattr(self, "language", "System")
            )
            try:
                start_index = display.index(current if current in display else "System")
            except Exception:
                start_index = 0
            return name_to_code, display, start_index

        def _after_prepared(res):
            if isinstance(res, Exception):
                try:
                    self.log_i18n(
                        "❌ Échec de chargement des langues disponibles.",
                        "❌ Failed to load available languages.",
                    )
                except Exception:
                    pass
                return
            name_to_code, display, start_index = res
            title = self.tr("Choisir la langue", "Choose language")
            label = self.tr("Langue :", "Language:")
            choice, ok = QInputDialog.getItem(
                self, title, label, display, start_index, False
            )
            if ok and choice:
                if choice == "System":
                    self.language_pref = "System"
                    # Apply resolved system language for UI strings, but keep pref as System
                    self.apply_language("System")
                    if self.select_lang:

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
                    code = name_to_code.get(choice) or choice
                    self.language_pref = code
                    self.apply_language(code)
                    if self.select_lang:
                        _run_coro_async(
                            get_translations(code),
                            lambda tr2: self.select_lang.setText(
                                tr2.get("choose_language_button")
                                or tr2.get("select_lang")
                                or ""
                            ),
                            ui_owner=self,
                        )
            else:
                try:
                    self.log_i18n(
                        "Sélection de la langue annulée.",
                        "Language selection canceled.",
                    )
                except Exception:
                    pass

        _run_coro_async(_prepare(), _after_prepared, ui_owner=self)

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
