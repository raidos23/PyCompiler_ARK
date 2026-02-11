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
import os
import sys

from PySide6.QtCore import QFile, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from Core import i18n as _i18n
from .i18n import _apply_main_app_translations, show_language_dialog

# Import du module Compiler
from Core.Compiler import (
    MainProcess,
    ProcessState,
    CompilationStatus,
    kill_process_tree,
    get_process_info,
)


def _detect_system_color_scheme() -> str:
    """
    Retourne "dark" ou "light" selon le thème système détecté.
    - Windows: registre AppsUseLightTheme (0 = dark, 1 = light)
    - macOS: defaults read -g AppleInterfaceStyle (Dark = dark)
    - Linux (GNOME/KDE): gsettings ou kdeglobals, repli sur GTK_THEME
    En cas d'échec, renvoie "light".
    """
    try:
        import os as _os
        import platform
        import subprocess

        sysname = platform.system()
        # Windows
        if sysname == "Windows":
            try:
                out = subprocess.run(
                    [
                        "reg",
                        "query",
                        r"HKCU\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                        "/v",
                        "AppsUseLightTheme",
                    ],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and out.stdout:
                    # Value like: REG_DWORD    0x1 (light) or 0x0 (dark)
                    val = out.stdout.lower()
                    if "0x0" in val or " 0x0\n" in val:
                        return "dark"
                    return "light"
            except Exception:
                pass
            return "light"
        # macOS
        if sysname == "Darwin":
            try:
                out = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "dark" in out.stdout.strip().lower():
                    return "dark"
            except Exception:
                pass
            return "light"
        # Linux (GNOME/KDE)
        if sysname == "Linux":
            # GNOME 42+: color-scheme
            try:
                out = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "prefer-dark" in out.stdout:
                    return "dark"
            except Exception:
                pass
            # GNOME: gtk-theme contains "dark"
            try:
                out = subprocess.run(
                    ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "dark" in out.stdout.lower():
                    return "dark"
            except Exception:
                pass
            # KDE: kdeglobals
            try:
                kdeglobals = _os.path.expanduser("~/.config/kdeglobals")
                if _os.path.isfile(kdeglobals):
                    with open(kdeglobals, encoding="utf-8", errors="ignore") as f:
                        txt = f.read().lower()
                    if "colorscheme" in txt and "dark" in txt:
                        return "dark"
            except Exception:
                pass
            # Env GTK_THEME
            try:
                gtk_theme = _os.environ.get("GTK_THEME", "").lower()
                if gtk_theme and "dark" in gtk_theme:
                    return "dark"
            except Exception:
                pass
            return "light"
        # Autres systèmes
        return "light"
    except Exception:
        return "light"


def init_ui(self):
    loader = QUiLoader()
    ui_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ui", "ui_design.ui"
    )
    ui_file = QFile(os.path.abspath(ui_path))
    ui_file.open(QFile.ReadOnly)
    self.ui = loader.load(ui_file, self)
    ui_file.close()

    # Supprimer tous les styles inline du .ui pour laisser le style global s'appliquer
    try:
        from PySide6.QtWidgets import QWidget

        widgets = [self.ui] + self.ui.findChildren(QWidget)
        for w in widgets:
            if hasattr(w, "styleSheet") and w.styleSheet():
                w.setStyleSheet("")
    except Exception:
        pass

    # Charger le thème (light/dark) selon préférence ou système, avec repli
    try:
        pref = getattr(self, "theme", "System")
        apply_theme(self, pref)
        # Après application, sauvegarder la préférence pour persistance immédiate
        try:
            if hasattr(self, "save_preferences"):
                self.save_preferences()
        except Exception:
            pass
    except Exception as _e:
        # En cas d'échec de chargement du style, on loggue sans casser l'UI
        try:
            if hasattr(self, "log") and self.log:
                self.log.append(f"⚠️ Échec application du thème: {_e}")
        except Exception:
            pass

    # Connecter les dialogs à l'application pour synchronisation du thème
    try:
        from Core.WidgetsCreator import connect_to_app

        connect_to_app(self)
    except Exception:
        pass

    # Définir l'UI chargée comme widget central de QMainWindow
    self.setCentralWidget(self.ui)

    # Récupérer les widgets depuis l'UI chargée
    self.btn_select_folder = self.ui.findChild(QPushButton, "btn_select_folder")
    self.venv_button = self.ui.findChild(QPushButton, "venv_button")
    self.venv_label = self.ui.findChild(QLabel, "venv_label")
    self.label_folder = self.ui.findChild(QLabel, "label_folder")
    self.label_workspace_status = self.ui.findChild(QLabel, "label_workspace_status")
    self.label_workspace_section = self.ui.findChild(QLabel, "label_workspace_section")
    self.label_files_section = self.ui.findChild(QLabel, "label_files_section")
    self.label_logs_section = self.ui.findChild(QLabel, "label_logs_section")
    self.file_list = self.ui.findChild(QListWidget, "file_list")
    self.file_filter_input = self.ui.findChild(QLineEdit, "file_filter_input")
    self.btn_select_files = self.ui.findChild(QPushButton, "btn_select_files")
    self.btn_remove_file = self.ui.findChild(QPushButton, "btn_remove_file")
    self.btn_clear_workspace = self.ui.findChild(QPushButton, "btn_clear_workspace")
    self.compile_btn = self.ui.findChild(QPushButton, "compile_btn")
    self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
    self.btn_help = self.ui.findChild(QPushButton, "btn_help")

    # Statut workspace dans l'en-tête
    if self.label_workspace_status:
        try:
            ws = getattr(self, "workspace_dir", None)
            if ws:
                self.label_workspace_status.setText(
                    self.tr(f"Workspace : {ws}", f"Workspace: {ws}")
                )
            else:
                self.label_workspace_status.setText(
                    self.tr("Workspace : Aucun", "Workspace: None")
                )
        except Exception:
            pass
    self.btn_suggest_deps = self.ui.findChild(QPushButton, "btn_suggest_deps")
    self.btn_bc_loader = self.ui.findChild(QPushButton, "btn_bc_loader")
    self.btn_acasl_loader = self.ui.findChild(QPushButton, "btn_acasl_loader")
    if self.btn_acasl_loader:
        try:
            self.btn_acasl_loader.hide()
            self.btn_acasl_loader.setEnabled(False)
        except Exception:
            pass
    # Onglets compilateur (correction robuste)
    from PySide6.QtWidgets import QTabWidget, QWidget

    # Ensure engines package is imported to register engines dynamically
    try:
        pass  # triggers discovery
    except Exception:
        pass
    self.compiler_tabs = self.ui.findChild(QTabWidget, "compiler_tabs")
    # Hello tab is now the default tab - it's defined in the UI
    self.tab_hello = self.ui.findChild(QWidget, "tab_hello")
    # Lier dynamiquement les onglets des moteurs plug-and-play (only if compiler_tabs exists)
    if self.compiler_tabs:
        try:
            import EngineLoader as engines_loader

            engines_loader.registry.bind_tabs(self)
        except Exception:
            pass

    self.compile_btn = self.ui.findChild(QPushButton, "compile_btn")
    self.cancel_btn = self.ui.findChild(QPushButton, "cancel_btn")
    self.progress = self.ui.findChild(QProgressBar, "progress")
    self.log = self.ui.findChild(QTextEdit, "log")
    self.btn_export_config = self.ui.findChild(QPushButton, "btn_export_config")
    self.btn_import_config = self.ui.findChild(QPushButton, "btn_import_config")
    self.btn_help = self.ui.findChild(QPushButton, "btn_help")

    # Connecter les signaux (only for widgets that exist in the UI)
    self.btn_select_folder.clicked.connect(self.select_workspace)
    self.venv_button.clicked.connect(self.select_venv_manually)
    self.btn_select_files.clicked.connect(self.select_files_manually)
    self.btn_remove_file.clicked.connect(self.remove_selected_file)
    self.compile_btn.clicked.connect(self.compile_all)
    self.cancel_btn.clicked.connect(self.cancel_all_compilations)
    if self.btn_clear_workspace:
        try:
            self.btn_clear_workspace.clicked.connect(self.clear_workspace)
        except Exception:
            pass

    # Filtre de fichiers
    if self.file_filter_input:
        try:
            self.file_filter_input.textChanged.connect(self.apply_file_filter)
        except Exception:
            pass

    from bcasl import open_bc_loader_dialog

    self.btn_bc_loader.clicked.connect(lambda: open_bc_loader_dialog(self))

    if self.btn_help:
        self.btn_help.clicked.connect(self.show_help_dialog)
    # Find btn_show_stats widget if it exists in the UI
    self.btn_show_stats = self.ui.findChild(QPushButton, "btn_show_stats")
    if getattr(self, "btn_show_stats", None):
        self.btn_show_stats.setToolTip(
            "Afficher les statistiques de compilation (temps, nombre de fichiers, mémoire)"
        )
        self.btn_show_stats.clicked.connect(self.show_statistics)
    # Static checkbox widgets are None - options are now in dynamic tabs
    # No signal connections needed for static widgets
    # self.custom_args supprimé (widget inutilisé)
    # Find select_lang widget if it exists in the UI
    self.select_lang = self.ui.findChild(QPushButton, "select_lang")
    if getattr(self, "select_lang", None):
        self.select_lang.setToolTip("Choisir la langue de l'interface utilisateur.")
        try:
            self.select_lang.clicked.connect(lambda: show_language_dialog(self))
        except Exception:
            pass

    # Find select_theme widget if it exists in the UI and connect it
    self.select_theme = self.ui.findChild(QPushButton, "select_theme")
    if getattr(self, "select_theme", None):
        try:
            self.select_theme.clicked.connect(lambda: show_theme_dialog(self))
        except Exception:
            pass

    # Désactivation croisée des options selon le moteur actif
    import platform

    def update_compiler_options_enabled():
        if not self.compiler_tabs:
            return
        try:
            import EngineLoader as engines_loader

            idx = self.compiler_tabs.currentIndex()
            engine_id = engines_loader.registry.get_engine_for_tab(idx)
        except Exception:
            engine_id = None

        # Helper to enable/disable widgets safely
        def set_enabled_safe(widget, enabled):
            if widget is None:
                return
            try:
                if enabled:
                    widget.setEnabled(True)
                else:
                    widget.setEnabled(False)
            except Exception:
                pass

        # Helper to set checkbox checked state safely
        def set_checked_safe(widget, checked):
            if widget is None:
                return
            try:
                widget.setChecked(checked)
            except Exception:
                pass

    self.compiler_tabs.currentChanged.connect(update_compiler_options_enabled)
    if self.compiler_tabs:
        update_compiler_options_enabled()

    # Message d'aide contextuel à la première utilisation
    if not self.workspace_dir:
        self.log.append(
            "Astuce : Commencez par sélectionner un dossier workspace, puis ajoutez vos fichiers Python à compiler. Configurez les options selon vos besoins et cliquez sur Compiler."
        )

    self.btn_suggest_deps = self.ui.findChild(QPushButton, "btn_suggest_deps")
    if self.btn_suggest_deps:
        self.btn_suggest_deps.clicked.connect(self.suggest_missing_dependencies)


def _themes_dir() -> str:
    return os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "themes")
    )


def _list_available_themes() -> list[tuple[str, str]]:
    """
    Retourne une liste (display_name, absolute_path) pour tous les fichiers .qss
    présents dans themes. display_name est dérivé du nom de fichier.
    """
    themes: list[tuple[str, str]] = []
    try:
        tdir = _themes_dir()
        if os.path.isdir(tdir):
            for fname in sorted(os.listdir(tdir)):
                if not fname.lower().endswith(".qss"):
                    continue
                name = os.path.splitext(fname)[0]
                disp = name.replace("_", " ").replace("-", " ").strip().title()
                themes.append((disp, os.path.join(tdir, fname)))
    except Exception:
        pass
    return themes


def _is_qss_dark(css: str) -> bool:
    """Heuristic to determine if a QSS stylesheet is dark or light.
    - Prefer background/background-color/window/base declarations when present
    - Fallback to all color tokens found
    - Compute average luminance; return True if dark
    """
    try:
        import re

        if not css or not isinstance(css, str):
            return False
        # Collect likely background colors first
        bg_matches = [
            m.group(2).strip()
            for m in re.finditer(
                r"(?i)(background(?:-color)?|window|base)\s*:\s*([^;]+);", css
            )
        ]
        tokens = (
            bg_matches
            if bg_matches
            else re.findall(r"#[0-9a-fA-F]{3,6}|rgba?\([^\)]+\)", css)
        )
        if not tokens:
            return False

        def _to_rgb(val: str):
            try:
                v = val.strip()
                if v.startswith("#"):
                    h = v[1:]
                    if len(h) == 3:
                        r = int(h[0] * 2, 16)
                        g = int(h[1] * 2, 16)
                        b = int(h[2] * 2, 16)
                    elif len(h) >= 6:
                        r = int(h[0:2], 16)
                        g = int(h[2:4], 16)
                        b = int(h[4:6], 16)
                    else:
                        return None
                    return (r, g, b)
                if v.lower().startswith("rgb"):
                    # Support rgb/rgba with optional percentages
                    nums_str = re.findall(r"([0-9.]+%?)", v)[:3]
                    if any(s.endswith("%") for s in nums_str):
                        vals = []
                        for s in nums_str:
                            if s.endswith("%"):
                                vals.append(
                                    int(max(0.0, min(100.0, float(s[:-1]))) * 2.55)
                                )
                            else:
                                vals.append(int(max(0.0, min(255.0, float(s)))))
                        return tuple(vals)
                    nums = [
                        int(max(0.0, min(255.0, float(x))))
                        for x in re.findall(r"([0-9.]+)", v)[:3]
                    ]
                    if len(nums) == 3:
                        return tuple(nums)
            except Exception:
                return None
            return None

        rgbs = []
        for t in tokens:
            rgb = _to_rgb(t)
            if rgb:
                rgbs.append(rgb)
        if not rgbs:
            return False
        avg = sum(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in rgbs) / len(rgbs)
        return avg < 128.0
    except Exception:
        return False


def apply_theme(self, pref: str):
    """Applique un thème depuis themes.
    - 'System': détection (dark/light) et sélection d'un .qss correspondant si possible
    - Sinon: appliquer le .qss dont le nom correspond (insensible à la casse/espaces)
    - Repli: pas de stylesheet si aucun thème trouvé
    """
    try:
        from PySide6.QtWidgets import QApplication

        candidates = _list_available_themes()
        chosen_path = None
        chosen_name = None

        if not pref or pref == "System":
            mode = _detect_system_color_scheme()  # 'dark'/'light'
            # préférer un fichier contenant le mot-clé
            key = "dark" if mode == "dark" else "light"
            for disp, path in candidates:
                if key in os.path.basename(path).lower():
                    chosen_path = path
                    chosen_name = disp
                    break
            # repli: premier disponible
            if not chosen_path and candidates:
                chosen_name, chosen_path = candidates[0]
        else:
            norm = pref.lower().replace(" ", "").replace("-", "").replace("_", "")
            # correspondance exacte sur le stem
            for disp, path in candidates:
                stem = os.path.splitext(os.path.basename(path))[0]
                stem_n = stem.lower().replace(" ", "").replace("-", "").replace("_", "")
                if stem_n == norm:
                    chosen_name = disp
                    chosen_path = path
                    break
            # sinon, contient
            if not chosen_path:
                for disp, path in candidates:
                    if norm in os.path.basename(path).lower().replace(" ", ""):
                        chosen_name = disp
                        chosen_path = path
                        break

        css = ""
        if chosen_path and os.path.isfile(chosen_path):
            with open(chosen_path, encoding="utf-8") as f:
                css = f.read()
        app = QApplication.instance()
        if app:
            app.setStyleSheet(css)
        self.theme = pref or "System"
        # Met à jour le texte du bouton (ne pas recharger i18n; utiliser la traduction active)
        if hasattr(self, "select_theme") and self.select_theme:
            try:
                tr = getattr(self, "_tr", None)
                if isinstance(tr, dict):
                    if self.theme == "System":
                        val = (
                            tr.get("choose_theme_system_button")
                            or tr.get("choose_theme_button")
                            or tr.get("select_theme")
                        )
                    else:
                        val = tr.get("choose_theme_button") or tr.get("select_theme")
                    if isinstance(val, str) and val:
                        self.select_theme.setText(val)
            except Exception:
                pass
        # Log
        if hasattr(self, "log") and self.log:
            if chosen_path:
                self.log.append(
                    f"🎨 Thème appliqué : {chosen_name} ({os.path.basename(chosen_path)})"
                )
            else:
                self.log.append(
                    "🎨 Aucun thème appliqué (aucun fichier .qss trouvé dans themes)"
                )
    except Exception as e:
        try:
            if hasattr(self, "log") and self.log:
                self.log.append(f"⚠️ Échec d'application du thème: {e}")
        except Exception:
            pass


def show_theme_dialog(self):
    from PySide6.QtWidgets import QInputDialog

    themes = _list_available_themes()
    options = ["System"] + [name for name, _ in themes]
    current = getattr(self, "theme", "System")
    # Trouver l'index initial
    try:
        start_index = options.index(current) if current in options else 0
    except Exception:
        start_index = 0
    title = self.tr("Choisir un thème", "Choose theme")
    label = self.tr("Thème :", "Theme:")
    choice, ok = QInputDialog.getItem(self, title, label, options, start_index, False)
    if ok and choice:
        self.theme = choice
        apply_theme(self, choice)
        # Sauvegarde si possible
        try:
            if hasattr(self, "save_preferences"):
                self.save_preferences()
        except Exception:
            pass
    else:
        if hasattr(self, "log") and self.log:
            self.log.append("Sélection du thème annulée.")
