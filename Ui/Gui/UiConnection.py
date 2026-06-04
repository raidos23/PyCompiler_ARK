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

from PySide6.QtCore import QByteArray, QFile, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QFrame,
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

from Ui.i18n import show_language_dialog


def _detect_system_color_scheme() -> str:
    """Detect the OS color scheme and return ``"sombre"`` or ``"clair"``."""
    try:
        import os as _os
        import platform
        import subprocess

        sysname = platform.system()
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
                    val = out.stdout.lower()
                    if "0x0" in val or " 0x0\n" in val:
                        return "sombre"
                    return "clair"
            except Exception:
                pass
            return "clair"
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
        if sysname == "Linux":
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
            try:
                kdeglobals = _os.path.expanduser("~/.config/kdeglobals")
                if _os.path.isfile(kdeglobals):
                    with open(kdeglobals, encoding="utf-8", errors="ignore") as f:
                        txt = f.read().lower()
                    if "colorscheme" in txt and "dark" in txt:
                        return "sombre"
            except Exception:
                pass
            try:
                gtk_theme = _os.environ.get("GTK_THEME", "").lower()
                if gtk_theme and "dark" in gtk_theme:
                    return "sombre"
            except Exception:
                pass
            return "clair"
        return "clair"
    except Exception:
        return "clair"


# =========================================================================
# INITIALISATION UI
# =========================================================================


def _load_ui_file(self) -> None:
    """Load the classic `.ui` file and install its central widget."""
    from Ui import ui_form_path

    loader = QUiLoader()
    ui_path = ui_form_path("classic_main_window.ui")
    ui_file = QFile(os.path.abspath(ui_path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Impossible d'ouvrir le fichier UI : {ui_path}")
    self.ui = loader.load(ui_file, self)
    ui_file.close()
    if self.ui is None:
        raise RuntimeError(f"Échec du chargement du fichier UI : {ui_path}")
    self.setCentralWidget(self.ui)


def _clear_inline_styles(self) -> None:
    """Remove inline styles so the global theme can apply consistently."""
    from PySide6.QtWidgets import QWidget

    widgets = [self.ui] + self.ui.findChildren(QWidget)
    for widget in widgets:
        if widget.styleSheet():
            widget.setStyleSheet("")


def _connect_dialogs_to_app(self) -> None:
    """Connect helper dialogs to the app for theme synchronization."""
    try:
        from Ui.Gui.WidgetsCreator import connect_to_app

        connect_to_app(self)
    except Exception:
        pass


def _apply_initial_theme(self) -> None:
    """Apply the initial theme from persisted user preferences."""
    pref = getattr(self, "theme", "System")
    apply_theme(self, pref)
    try:
        if hasattr(self, "save_preferences"):
            self.save_preferences()
    except Exception:
        pass


def _setup_sidebar_logo(self) -> None:
    """Configure the sidebar logo when a dedicated label is available."""
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
    logo_path = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "images",
            "logo2.png",
        )
    )
    if not os.path.isfile(logo_path):
        return
    pixmap = QPixmap(logo_path)
    if pixmap.isNull():
        return
    logo_label.setPixmap(pixmap)
    logo_label.setAlignment(Qt.AlignCenter)
    logo_label.setScaledContents(True)


def _auto_resize_for_screen(self) -> None:
    """Resize and center the window to fit the current screen safely."""
    try:
        from PySide6.QtWidgets import QApplication

        screen = None
        try:
            screen = self.screen()
        except Exception:
            screen = None
        if screen is None:
            screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        aw, ah = geo.width(), geo.height()
        if aw <= 0 or ah <= 0:
            return

        try:
            if self.isMaximized() or self.isFullScreen():
                return
        except Exception:
            pass

        min_w = max(800, int(aw * 0.55))
        min_h = max(600, int(ah * 0.55))
        try:
            self.setMinimumSize(min_w, min_h)
        except Exception:
            pass
        try:
            self.setMaximumSize(aw, ah)
        except Exception:
            pass

        try:
            hint = self.sizeHint()
            base_w = max(self.width(), hint.width())
            base_h = max(self.height(), hint.height())
        except Exception:
            base_w, base_h = self.width(), self.height()

        target_w = min(max(base_w, int(aw * 0.6)), int(aw * 0.92))
        target_h = min(max(base_h, int(ah * 0.6)), int(ah * 0.92))

        try:
            self.resize(target_w, target_h)
        except Exception:
            pass

        try:
            x = geo.x() + max(0, (aw - target_w) // 2)
            y = geo.y() + max(0, (ah - target_h) // 2)
            self.move(x, y)
        except Exception:
            pass
    except Exception:
        pass


def _apply_button_icons(self) -> None:
    """Apply SVG icons to primary controls when icon assets are available."""
    if not getattr(self, "ui", None):
        return
    icons_dir = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "icons"
        )
    )
    if not os.path.isdir(icons_dir):
        return

    def _extract_accent_color(css_text: str) -> str | None:
        try:
            import re

            def _block(selector: str) -> str | None:
                pattern = re.compile(
                    rf"{re.escape(selector)}\\s*\\{{([^}}]+)\\}}", re.S
                )
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
            svg = svg.replace("<svg ", f'<svg color="{color}" ', 1)
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
    _set(getattr(self, "btn_lock_manager", None), "lock.svg")
    _set(getattr(self, "btn_show_stats", None), "bar-chart-2.svg")
    _set(getattr(self, "btn_help", None), "help-circle.svg")

    _set(getattr(self, "btn_select_icon", None), "image.svg")
    _set(getattr(self, "btn_nuitka_icon", None), "image.svg")


def _setup_widgets(self) -> None:
    """Resolve UI widgets and initialize expected attributes."""
    if not getattr(self, "ui", None):
        return

    def _find(cls, name: str):
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
    self.btn_lock_manager = _find(QPushButton, "btn_lock_manager")

    self.progress = _find(QProgressBar, "progress")
    self.log = _find(QTextEdit, "log")
    self.btn_show_stats = _find(QPushButton, "btn_show_stats")
    self.advanced_cfg_btn = _find(QPushButton, "advanced_cfg_btn")
    self.select_lang = _find(QPushButton, "select_lang")
    self.select_theme = _find(QPushButton, "select_theme")

    for _lbl in (self.label_folder, self.venv_label):
        if _lbl is None:
            continue
        try:
            _lbl.setFrameShape(QFrame.NoFrame)
        except Exception:
            pass
        try:
            _lbl.setStyleSheet("border: none; background: transparent;")
        except Exception:
            pass

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
    """Initialize compiler tabs and bind available engines."""
    from PySide6.QtWidgets import QTabWidget, QWidget

    if not getattr(self, "ui", None):
        return

    self.compiler_tabs = self.ui.findChild(QTabWidget, "compiler_tabs")
    self.tab_hello = self.ui.findChild(QWidget, "tab_hello")

    if self.compiler_tabs:
        try:
            import Core.engine as engines_loader

            engines_loader.bind_tabs(self)
        except Exception:
            pass


def _connect_signals(self) -> None:
    """Connect widget signals when corresponding controls are available."""

    def _connect_clicked(widget, handler) -> None:
        if widget is None:
            return
        try:
            widget.clicked.connect(handler)
        except Exception:
            pass

    def _connect_text(widget, handler) -> None:
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
    _connect_clicked(self.advanced_cfg_btn, self.open_advanced_config_editor)

    if self.btn_clear_workspace:
        _connect_clicked(self.btn_clear_workspace, self.clear_workspace)

    _connect_text(self.file_filter_input, self.apply_file_filter)

    if self.btn_bc_loader:
        try:
            from Ui.Gui.Dialogs.BcaslDialog import open_bc_loader_dialog

            self.btn_bc_loader.clicked.connect(lambda: open_bc_loader_dialog(self))
        except Exception:
            pass

    if self.btn_lock_manager:
        _connect_clicked(self.btn_lock_manager, self.open_lock_dialog)

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
        if not self.compiler_tabs:
            return
        try:
            import Core.engine as engines_loader

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
    """Show help hint when no workspace is selected."""
    return


def init_ui(self) -> None:
    """Initialize UI and connect shared feature wiring."""
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
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, lambda: _auto_resize_for_screen(self))
    except Exception:
        _auto_resize_for_screen(self)
    try:
        if hasattr(self, "setup_entrypoint_selector"):
            self.setup_entrypoint_selector()
    except Exception:
        pass
    _show_initial_help_message(self)
    try:
        self.set_controls_enabled(True)
    except Exception:
        pass


# =========================================================================
# THÈMES
# =========================================================================


def _themes_dir() -> str:
    """Return absolute path to the `themes` directory."""
    return os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "themes")
    )


def _list_available_themes() -> list[tuple[str, str]]:
    """Return `(display_name, absolute_path)` pairs for `.qss` theme files."""
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
    """Heuristic to determine whether a QSS theme is dark or light."""
    try:
        import re

        if not css or not isinstance(css, str):
            return False
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


def _extract_accent_color_for_icons(css_text: str) -> str | None:
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
    except Exception:
        return None
    return None


def _resolve_theme_icon_color(css: str | None = None) -> str:
    if not css:
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            css = app.styleSheet() if app else ""
        except Exception:
            css = ""
    if css:
        accent = _extract_accent_color_for_icons(css)
        if accent:
            return accent
        return "#FFFFFF" if _is_qss_dark(css) else "#111111"
    return "#FFFFFF" if _detect_system_color_scheme() == "sombre" else "#111111"


def themed_svg_icon(path: str, size: int = 18, css: str | None = None) -> QIcon | None:
    """Render an SVG icon tinted according to current app theme."""
    if not os.path.isfile(path):
        return None
    if QSvgRenderer is None:
        return QIcon(path)
    try:
        with open(path, encoding="utf-8") as f:
            svg = f.read()
    except Exception:
        return None

    color = _resolve_theme_icon_color(css)
    if "currentColor" in svg:
        svg = svg.replace("currentColor", color)
    else:
        svg = svg.replace("<svg ", f'<svg color="{color}" ', 1)
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        return None
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return QIcon(pixmap)


def _refresh_log_palette(self, css: str | None = None) -> None:
    """Ensure readable log text color according to active theme."""
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
    """Apply a theme from themes directory."""
    try:
        from PySide6.QtWidgets import QApplication

        candidates = _list_available_themes()
        chosen_path = None
        chosen_name = None

        if not pref or pref == "System":
            mode = _detect_system_color_scheme()
            key = "dark" if mode == "sombre" else "light"
            for disp, path in candidates:
                if key in os.path.basename(path).lower():
                    chosen_path = path
                    chosen_name = disp
                    break
            if not chosen_path and candidates:
                chosen_name, chosen_path = candidates[0]
        else:
            norm = pref.lower().replace(" ", "").replace("-", "").replace("_", "")
            for disp, path in candidates:
                stem = os.path.splitext(os.path.basename(path))[0]
                stem_n = stem.lower().replace(" ", "").replace("-", "").replace("_", "")
                if stem_n == norm:
                    chosen_name = disp
                    chosen_path = path
                    break
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
        try:
            from Ui.Gui.IdeLikeGui.connections import _apply_activity_buttons_theme

            _apply_activity_buttons_theme(self)
        except Exception:
            pass
        try:
            if hasattr(self, "_refresh_entrypoint_marker"):
                self._refresh_entrypoint_marker()
        except Exception:
            pass
        self.theme = pref or "System"
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
        try:
            from Ui.i18n import log_i18n_level

            if chosen_path:
                log_i18n_level(
                    self,
                    "info",
                    f"Thème appliqué : {chosen_name} ({os.path.basename(chosen_path)})",
                    f"Theme applied: {chosen_name} ({os.path.basename(chosen_path)})",
                )
            else:
                log_i18n_level(
                    self,
                    "warning",
                    "Aucun thème appliqué (aucun fichier .qss trouvé dans themes)",
                    "No theme applied (no .qss file found in themes)",
                )
        except Exception:
            pass
    except Exception as e:
        try:
            if hasattr(self, "log") and self.log:
                try:
                    from Ui.i18n import log_i18n_level

                    log_i18n_level(
                        self,
                        "warning",
                        f"Échec d'application du thème: {e}",
                        f"Failed to apply theme: {e}",
                    )
                except Exception:
                    from Ui.i18n import log_with_level

                    log_with_level(
                        self, "warning", f"Échec d'application du thème: {e}"
                    )
        except Exception:
            pass


def show_theme_dialog(self) -> None:
    """Open theme selection dialog."""
    from PySide6.QtWidgets import QInputDialog

    themes = _list_available_themes()
    options = ["System"] + [name for name, _ in themes]
    current = getattr(self, "theme", "System")
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
        try:
            if hasattr(self, "save_preferences"):
                self.save_preferences()
        except Exception:
            pass
    else:
        try:
            from Ui.i18n import log_i18n_level

            log_i18n_level(
                self,
                "info",
                "Sélection du thème annulée.",
                "Theme selection cancelled.",
            )
        except Exception:
            pass
