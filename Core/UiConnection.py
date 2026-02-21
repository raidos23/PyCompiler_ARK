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

from PySide6.QtCore import QFile, Qt, QSize, QByteArray, QRectF
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QProgressBar,
    QPushButton,
    QTextEdit,
)
try:
    from PySide6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None  # type: ignore[assignment]

from .i18n import show_language_dialog


def _detect_system_color_scheme() -> str:
    """
    Retourne "sombre" ou "clair" selon le thème système détecté.
    - Windows : registre AppsUseLightTheme (0 = sombre, 1 = clair)
    - macOS : defaults read -g AppleInterfaceStyle (Dark = sombre)
    - Linux (GNOME/KDE) : gsettings ou kdeglobals, repli sur GTK_THEME
    En cas d'échec, renvoie "clair".
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
                    # Valeur comme : REG_DWORD    0x1 (clair) ou 0x0 (sombre)
                    val = out.stdout.lower()
                    if "0x0" in val or " 0x0\n" in val:
                        return "sombre"
                    return "clair"
            except Exception:
                pass
            return "clair"
        # macOS
        if sysname == "Darwin":
            try:
                out = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "dark" in out.stdout.strip().lower():
                    return "sombre"
            except Exception:
                pass
            return "clair"
        # Linux (GNOME/KDE)
        if sysname == "Linux":
            # GNOME 42+ : color-scheme
            try:
                out = subprocess.run(
                    [
                        "gsettings",
                        "get",
                        "org.gnome.desktop.interface",
                        "color-scheme",
                    ],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "prefer-dark" in out.stdout:
                    return "sombre"
            except Exception:
                pass
            # GNOME : gtk-theme contient "dark"
            try:
                out = subprocess.run(
                    [
                        "gsettings",
                        "get",
                        "org.gnome.desktop.interface",
                        "gtk-theme",
                    ],
                    capture_output=True,
                    text=True,
                )
                if out.returncode == 0 and "dark" in out.stdout.lower():
                    return "sombre"
            except Exception:
                pass
            # KDE : kdeglobals
            try:
                kdeglobals = _os.path.expanduser("~/.config/kdeglobals")
                if _os.path.isfile(kdeglobals):
                    with open(kdeglobals, encoding="utf-8", errors="ignore") as f:
                        txt = f.read().lower()
                    if "colorscheme" in txt and "dark" in txt:
                        return "sombre"
            except Exception:
                pass
            # Variable d'environnement GTK_THEME
            try:
                gtk_theme = _os.environ.get("GTK_THEME", "").lower()
                if gtk_theme and "dark" in gtk_theme:
                    return "sombre"
            except Exception:
                pass
            return "clair"
        # Autres systèmes
        return "clair"
    except Exception:
        return "clair"


# =========================================================================
# INITIALISATION UI
# =========================================================================


def _load_ui_file(self) -> None:
    """Charge le fichier .ui et installe le widget central."""
    loader = QUiLoader()
    ui_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "ui", "ui_design.ui"
    )
    ui_file = QFile(os.path.abspath(ui_path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Impossible d'ouvrir le fichier UI : {ui_path}")
    self.ui = loader.load(ui_file, self)
    ui_file.close()
    if self.ui is None:
        raise RuntimeError(f"Échec du chargement du fichier UI : {ui_path}")
    self.setCentralWidget(self.ui)


def _clear_inline_styles(self) -> None:
    """Supprime les styles inline pour laisser le style global s'appliquer."""
    from PySide6.QtWidgets import QWidget

    widgets = [self.ui] + self.ui.findChildren(QWidget)
    for widget in widgets:
        if widget.styleSheet():
            widget.setStyleSheet("")


def _connect_dialogs_to_app(self) -> None:
    """Connecte les dialogues à l'application pour synchroniser le thème."""
    try:
        from Core.WidgetsCreator import connect_to_app

        connect_to_app(self)
    except Exception:
        pass


def _apply_initial_theme(self) -> None:
    """Applique le thème initial selon les préférences utilisateur."""
    pref = getattr(self, "theme", "System")
    apply_theme(self, pref)
    try:
        if hasattr(self, "save_preferences"):
            self.save_preferences()
    except Exception:
        pass


def _setup_sidebar_logo(self) -> None:
    """Configure le logo latéral si un QLabel dédié est présent dans l'UI."""
    if not getattr(self, "ui", None):
        return
    candidates = [
        "sidebar_logo",
        "label_logo",
        "label_app_logo",
        "logo_label",
    ]
    logo_label = None
    for name in candidates:
        logo_label = self.ui.findChild(QLabel, name)
        if logo_label is not None:
            break
    if logo_label is None:
        return
    logo_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "logo", "logo2.png"
    )
    if not os.path.isfile(logo_path):
        return
    pixmap = QPixmap(logo_path)
    if pixmap.isNull():
        return
    logo_label.setPixmap(pixmap)
    logo_label.setAlignment(Qt.AlignCenter)
    logo_label.setScaledContents(True)


def _apply_button_icons(self) -> None:
    """Applique des icônes SVG aux boutons principaux si disponibles."""
    if not getattr(self, "ui", None):
        return
    icons_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "icons"
    )
    if not os.path.isdir(icons_dir):
        return

    def _extract_accent_color(css_text: str) -> str | None:
        try:
            import re

            def _block(selector: str) -> str | None:
                pattern = re.compile(rf"{re.escape(selector)}\\s*\\{{([^}}]+)\\}}", re.S)
                match = pattern.search(css_text)
                return match.group(1) if match else None

            def _colors(text: str) -> list[str]:
                return re.findall(r"#[0-9a-fA-F]{3,6}", text)

            for selector in ("QPushButton#compile_btn", "#compile_btn"):
                block = _block(selector)
                if block:
                    colors = _colors(block)
                    if colors:
                        return colors[0]

            match = re.search(r"--accent[^:]*:\\s*(#[0-9a-fA-F]{3,6})", css_text)
            if match:
                return match.group(1)

            match = re.search(
                r":focus[^\\{]*\\{[^}]*border[^#]*?(#[0-9a-fA-F]{3,6})",
                css_text,
                re.S,
            )
            if match:
                return match.group(1)

            match = re.search(
                r"QProgressBar::chunk[^\\{]*\\{[^}]*?(#[0-9a-fA-F]{3,6})",
                css_text,
                re.S,
            )
            if match:
                return match.group(1)
        except Exception:
            return None
        return None

    def _resolve_icon_color(css: str | None = None) -> str:
        if not css:
            try:
                from PySide6.QtWidgets import QApplication

                app = QApplication.instance()
                css = app.styleSheet() if app else ""
            except Exception:
                css = ""
        if css:
            accent = _extract_accent_color(css)
            if accent:
                return accent
            return "#FFFFFF" if _is_qss_dark(css) else "#111111"
        return "#FFFFFF" if _detect_system_color_scheme() == "sombre" else "#111111"

    def _render_svg_icon(path: str, color: str, size: int) -> QIcon | None:
        if not os.path.isfile(path):
            return None
        if QSvgRenderer is None:
            return QIcon(path)
        try:
            with open(path, encoding="utf-8") as f:
                svg = f.read()
        except Exception:
            return None
        if "currentColor" in svg:
            svg = svg.replace("currentColor", color)
        else:
            svg = svg.replace("<svg ", f"<svg color=\"{color}\" ", 1)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            return None
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter, QRectF(0, 0, size, size))
        painter.end()
        return QIcon(pixmap)

    icon_color = _resolve_icon_color()

    def _icon(name: str, size: int) -> QIcon | None:
        path = os.path.join(icons_dir, name)
        icon = _render_svg_icon(path, icon_color, size)
        if not icon or icon.isNull():
            return None
        return icon

    def _set(widget, icon_name: str, size: int = 18) -> None:
        if widget is None:
            return
        icon = _icon(icon_name, size)
        if icon is None:
            return
        widget.setIcon(icon)
        widget.setIconSize(QSize(size, size))

    _set(getattr(self, "select_lang", None), "globe.svg")
    _set(getattr(self, "select_theme", None), "sun.svg")
    _set(getattr(self, "compile_btn", None), "play.svg", size=20)
    _set(getattr(self, "cancel_btn", None), "stop-circle.svg", size=20)

    _set(getattr(self, "btn_select_folder", None), "folder.svg")
    _set(getattr(self, "venv_button", None), "package.svg")
    _set(getattr(self, "btn_select_files", None), "file.svg")
    _set(getattr(self, "btn_clear_workspace", None), "trash-2.svg")
    _set(getattr(self, "btn_remove_file", None), "minus-circle.svg")
    _set(getattr(self, "btn_suggest_deps", None), "search.svg")
    _set(getattr(self, "btn_bc_loader", None), "sliders.svg")
    _set(getattr(self, "btn_show_stats", None), "bar-chart-2.svg")
    _set(getattr(self, "btn_help", None), "help-circle.svg")

    _set(getattr(self, "btn_export_config", None), "upload-cloud.svg")
    _set(getattr(self, "btn_import_config", None), "download-cloud.svg")
    _set(getattr(self, "btn_select_icon", None), "image.svg")
    _set(getattr(self, "btn_nuitka_icon", None), "image.svg")


def _setup_widgets(self) -> None:
    """Récupère les widgets depuis l'UI et initialise les attributs."""
    if not getattr(self, "ui", None):
        return

    def _find(cls, name: str):
        """Raccourci pour trouver un widget par nom."""
        return self.ui.findChild(cls, name)

    self.btn_select_folder = _find(QPushButton, "btn_select_folder")
    self.venv_button = _find(QPushButton, "venv_button")
    self.venv_label = _find(QLabel, "venv_label")
    self.label_folder = _find(QLabel, "label_folder")
    self.label_workspace_status = _find(QLabel, "label_workspace_status")
    self.label_workspace_section = _find(QLabel, "label_workspace_section")
    self.label_files_section = _find(QLabel, "label_files_section")
    self.label_tools = _find(QLabel, "label_tools")
    self.label_options_section = _find(QLabel, "label_options_section")
    self.label_logs_section = _find(QLabel, "label_logs_section")
    self.label_progress = _find(QLabel, "label_progress")

    self.file_list = _find(QListWidget, "file_list")
    self.file_filter_input = _find(QLineEdit, "file_filter_input")

    self.btn_select_files = _find(QPushButton, "btn_select_files")
    self.btn_remove_file = _find(QPushButton, "btn_remove_file")
    self.btn_clear_workspace = _find(QPushButton, "btn_clear_workspace")

    self.compile_btn = _find(QPushButton, "compile_btn")
    self.cancel_btn = _find(QPushButton, "cancel_btn")
    self.btn_help = _find(QPushButton, "btn_help")

    self.btn_suggest_deps = _find(QPushButton, "btn_suggest_deps")
    self.btn_bc_loader = _find(QPushButton, "btn_bc_loader")
    self.btn_acasl_loader = _find(QPushButton, "btn_acasl_loader")

    self.progress = _find(QProgressBar, "progress")
    self.log = _find(QTextEdit, "log")
    self.btn_export_config = _find(QPushButton, "btn_export_config")
    self.btn_import_config = _find(QPushButton, "btn_import_config")
    self.btn_show_stats = _find(QPushButton, "btn_show_stats")
    self.select_lang = _find(QPushButton, "select_lang")
    self.select_theme = _find(QPushButton, "select_theme")

    if self.btn_acasl_loader:
        self.btn_acasl_loader.hide()
        self.btn_acasl_loader.setEnabled(False)

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


def _setup_compiler_tabs(self) -> None:
    """Configure les onglets de compilation et charge les moteurs."""
    from PySide6.QtWidgets import QTabWidget, QWidget

    if not getattr(self, "ui", None):
        return

    self.compiler_tabs = self.ui.findChild(QTabWidget, "compiler_tabs")
    self.tab_hello = self.ui.findChild(QWidget, "tab_hello")

    if self.compiler_tabs:
        try:
            import EngineLoader as engines_loader

            engines_loader.registry.bind_tabs(self)
        except Exception:
            pass


def _connect_signals(self) -> None:
    """Connecte les signaux des widgets lorsque disponibles."""

    def _connect_clicked(widget, handler) -> None:
        """Connecte le signal clicked d'un bouton si possible."""
        if widget is None:
            return
        try:
            widget.clicked.connect(handler)
        except Exception:
            pass

    def _connect_text(widget, handler) -> None:
        """Connecte le signal textChanged d'un champ si possible."""
        if widget is None:
            return
        try:
            widget.textChanged.connect(handler)
        except Exception:
            pass

    _connect_clicked(self.btn_select_folder, self.select_workspace)
    _connect_clicked(self.venv_button, self.select_venv_manually)
    _connect_clicked(self.btn_select_files, self.select_files_manually)
    _connect_clicked(self.btn_remove_file, self.remove_selected_file)
    _connect_clicked(self.compile_btn, self.compile_all)
    _connect_clicked(self.cancel_btn, self.cancel_all_compilations)

    if self.btn_clear_workspace:
        _connect_clicked(self.btn_clear_workspace, self.clear_workspace)

    _connect_text(self.file_filter_input, self.apply_file_filter)

    if self.btn_bc_loader:
        try:
            from bcasl import open_bc_loader_dialog

            self.btn_bc_loader.clicked.connect(lambda: open_bc_loader_dialog(self))
        except Exception:
            pass

    _connect_clicked(self.btn_help, self.show_help_dialog)

    if self.btn_show_stats:
        self.btn_show_stats.setToolTip(
            "Afficher les statistiques de compilation (temps, nombre de fichiers, mémoire)"
        )
        _connect_clicked(self.btn_show_stats, self.show_statistics)

    if self.select_lang:
        self.select_lang.setToolTip("Choisir la langue de l'interface utilisateur.")
        _connect_clicked(self.select_lang, lambda: show_language_dialog(self))

    if self.select_theme:
        _connect_clicked(self.select_theme, lambda: show_theme_dialog(self))

    def update_compiler_options_enabled() -> None:
        """Met à jour l'état des options selon l'onglet actif."""
        if not self.compiler_tabs:
            return
        try:
            import EngineLoader as engines_loader

            idx = self.compiler_tabs.currentIndex()
            engines_loader.registry.get_engine_for_tab(idx)
        except Exception:
            pass

    if self.compiler_tabs:
        self.compiler_tabs.currentChanged.connect(update_compiler_options_enabled)
        update_compiler_options_enabled()

    if self.btn_suggest_deps:
        _connect_clicked(self.btn_suggest_deps, self.suggest_missing_dependencies)


def _show_initial_help_message(self) -> None:
    """Affiche un message d'aide si aucun workspace n'est sélectionné."""
    # Désactivé à la demande : pas de message d'astuce par défaut dans le log.
    return


def init_ui(self) -> None:
    """Initialise l'interface utilisateur et branche les fonctionnalités."""
    _load_ui_file(self)
    _clear_inline_styles(self)
    _apply_initial_theme(self)
    _connect_dialogs_to_app(self)
    _setup_widgets(self)
    _refresh_log_palette(self)
    _apply_button_icons(self)
    _setup_sidebar_logo(self)
    _setup_compiler_tabs(self)
    _connect_signals(self)
    try:
        if hasattr(self, "setup_entrypoint_selector"):
            self.setup_entrypoint_selector()
    except Exception:
        pass
    _show_initial_help_message(self)


# =========================================================================
# THÈMES
# =========================================================================


def _themes_dir() -> str:
    """Retourne le chemin absolu du dossier themes."""
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
    """Heuristique pour déterminer si un QSS est sombre ou clair."""
    try:
        import re

        if not css or not isinstance(css, str):
            return False
        # Collecter d'abord les couleurs de fond les plus probables
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
            """Convertit une couleur CSS en tuple RGB."""
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
                    # Supporte rgb/rgba avec pourcentages optionnels
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


def _refresh_log_palette(self, css: str | None = None) -> None:
    """Assure une couleur de texte lisible pour le journal, selon le thème."""
    if not getattr(self, "log", None):
        return
    try:
        from PySide6.QtGui import QColor, QPalette
        from PySide6.QtWidgets import QApplication
    except Exception:
        return
    try:
        if css is None:
            app = QApplication.instance()
            css = app.styleSheet() if app else ""
        dark = _is_qss_dark(css or "")
        color = "#E6E8EB" if dark else "#1F2A3C"
        pal = self.log.palette()
        pal.setColor(QPalette.Text, QColor(color))
        pal.setColor(QPalette.PlaceholderText, QColor(color))
        self.log.setPalette(pal)
    except Exception:
        pass


def apply_theme(self, pref: str) -> None:
    """
    Applique un thème depuis themes.
    - "System" : détection (sombre/clair) et sélection d'un .qss correspondant
    - Sinon : appliquer le .qss dont le nom correspond (insensible à la casse/espaces)
    - Repli : pas de stylesheet si aucun thème trouvé
    """
    try:
        from PySide6.QtWidgets import QApplication

        candidates = _list_available_themes()
        chosen_path = None
        chosen_name = None

        if not pref or pref == "System":
            mode = _detect_system_color_scheme()  # "sombre" / "clair"
            # Préférer un fichier contenant le mot-clé
            key = "dark" if mode == "sombre" else "light"
            for disp, path in candidates:
                if key in os.path.basename(path).lower():
                    chosen_path = path
                    chosen_name = disp
                    break
            # Repli : premier disponible
            if not chosen_path and candidates:
                chosen_name, chosen_path = candidates[0]
        else:
            norm = pref.lower().replace(" ", "").replace("-", "").replace("_", "")
            # Correspondance exacte sur le nom de fichier
            for disp, path in candidates:
                stem = os.path.splitext(os.path.basename(path))[0]
                stem_n = stem.lower().replace(" ", "").replace("-", "").replace("_", "")
                if stem_n == norm:
                    chosen_name = disp
                    chosen_path = path
                    break
            # Sinon, correspondance partielle
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
        _refresh_log_palette(self, css)
        try:
            _apply_button_icons(self)
        except Exception:
            pass
        self.theme = pref or "System"
        # Met à jour le texte du bouton (ne pas recharger i18n)
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
        # Journalisation
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


def show_theme_dialog(self) -> None:
    """Affiche la boîte de dialogue de sélection de thème."""
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
