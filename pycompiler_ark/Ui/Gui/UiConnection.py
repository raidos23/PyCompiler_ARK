# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

from PySide6.QtCore import QByteArray, QTimer, QRectF, QSize, Qt
from PySide6.QtGui import QAction, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QWidget,
)

try:
    from PySide6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None  # type: ignore[assignment]

from pycompiler_ark.Ui import output

from .mainwindow import Ui_MainWindow
from .Dialogs.WorkspaceDialog import show_language_dialog, translate


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
                if (
                    out.returncode == 0
                    and "dark" in out.stdout.strip().lower()
                ):
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
                    with open(
                        kdeglobals, encoding="utf-8", errors="ignore"
                    ) as f:
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


def _connect_dialogs_to_app(self) -> None:
    """Connect helper dialogs to the app for theme synchronization."""
    try:
        from .WidgetsCreator import connect_to_app

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
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "..",
            "data",
            "icons",
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

            for selector in ("QPushButton#btn_build_all", "#btn_build_all"):
                block = _block(selector)
                if block:
                    colors = _colors(block)
                    if colors:
                        return colors[0]

            match = re.search(
                r"--accent[^:]*:\\s*(#[0-9a-fA-F]{3,6})", css_text
            )
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
        return (
            "#FFFFFF"
            if _detect_system_color_scheme() == "sombre"
            else "#111111"
        )

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

    for name in (
        "btn_select_folder",
        "venv_button",
        "venv_label",
        "label_folder",
        "label_workspace_status",
        "label_workspace_section",
        "label_files_section",
        "label_tools",
        "label_options_section",
        "label_logs_section",
        "label_progress",
        "file_list",
        "file_filter_input",
        "btn_select_files",
        "btn_remove_file",
        "btn_clear_workspace",
        "compile_btn",
        "cancel_btn",
        "btn_help",
        "btn_suggest_deps",
        "activity_btn_deps",
        "btn_bc_loader",
        "btn_acasl_loader",
        "btn_lock_manager",
        "progress",
        "log",
        "btn_show_stats",
        "advanced_cfg_btn",
        "select_lang",
        "select_theme",
        "compiler_tabs",
        "tab_hello",
        "toolButton_more",
        "btn_select_icon",
        "btn_nuitka_icon",
        "statusbar",
        "status_hint",
    ):
        if not hasattr(self, name):
            setattr(self, name, None)

    self.btn_select_folder = _find(QPushButton, "btn_select_folder")
    self.venv_button = _find(QPushButton, "btn_venv_button")
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

    self.compile_btn = _find(QPushButton, "btn_build_all")
    self.cancel_btn = _find(QPushButton, "btn_cancel_all")
    self.btn_help = _find(QPushButton, "btn_help")

    self.btn_suggest_deps = _find(QPushButton, "btn_suggest_deps")
    self.btn_bc_loader = _find(QPushButton, "btn_bc_loader")
    self.btn_acasl_loader = _find(QPushButton, "btn_acasl_loader")
    self.btn_lock_manager = _find(QPushButton, "btn_lock_manager")
    self.activity_btn_deps = _find(QToolButton, "btn_activity_deps")
    self.btn_select_icon = _find(QPushButton, "btn_select_icon")
    self.btn_nuitka_icon = _find(QPushButton, "btn_nuitka_icon")
    self.toolButton_more = _find(QToolButton, "btn_more_actions")

    self.progress = _find(QProgressBar, "progress")
    self.log = _find(QTextEdit, "log")
    self.btn_show_stats = _find(QPushButton, "btn_show_stats")
    self.advanced_cfg_btn = _find(QPushButton, "btn_advanced_config")
    self.select_lang = _find(QPushButton, "btn_select_lang")
    self.select_theme = _find(QPushButton, "btn_select_theme")
    self.compiler_tabs = _find(QTabWidget, "compiler_tabs")
    self.tab_hello = _find(QWidget, "tab_hello")
    self.statusbar = self.findChild(QStatusBar, "statusbar")
    self.status_hint = None
    try:
        self.status_hint = (
            self.statusbar.findChild(QLabel, "status_ready")
            if self.statusbar
            else None
        )
    except Exception:
        self.status_hint = None

    # Set properties for dynamic i18n
    if self.select_lang:
        self.select_lang.setProperty(
            "i18n_text_system_key", "choose_language_system_button"
        )
        self.select_lang.setProperty("i18n_system_attr", "language_pref")
    if self.select_theme:
        self.select_theme.setProperty(
            "i18n_text_system_key", "choose_theme_system_button"
        )
        self.select_theme.setProperty("i18n_system_attr", "theme")
    if self.venv_label:
        self.venv_label.setProperty(
            "i18n_text_system_key", "venv_label_system"
        )
        self.venv_label.setProperty("i18n_system_attr", "use_system_python")
    if self.label_workspace_status:
        self.label_workspace_status.setProperty(
            "i18n_format_attr", "workspace_dir"
        )
        self.label_workspace_status.setProperty(
            "i18n_none_key", "label_workspace_status_none"
        )
    if self.file_filter_input:
        self.file_filter_input.setProperty(
            "i18n_placeholder_key", "file_filter_placeholder"
        )
    if self.btn_acasl_loader:
        self.btn_acasl_loader.setProperty("i18n_text_key", "bc_loader")
        self.btn_acasl_loader.setProperty("i18n_tooltip_key", "tt_bc_loader")
    if self.btn_select_icon:
        self.btn_select_icon.setProperty("i18n_tooltip_key", "tt_select_icon")
    if self.btn_nuitka_icon:
        self.btn_nuitka_icon.setProperty("i18n_tooltip_key", "tt_select_icon")
    if self.activity_btn_deps:
        self.activity_btn_deps.setProperty(
            "i18n_tooltip_key", "tt_suggest_deps"
        )

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
    _setup_status_bar(self)


def _prime_expected_attrs(self) -> None:
    """Backward-compatible helper for attribute bootstrapping."""
    for name in (
        "btn_select_folder",
        "venv_button",
        "venv_label",
        "label_folder",
        "label_workspace_status",
        "label_workspace_section",
        "label_files_section",
        "label_tools",
        "label_options_section",
        "label_logs_section",
        "label_progress",
        "file_list",
        "file_filter_input",
        "btn_select_files",
        "btn_remove_file",
        "btn_clear_workspace",
        "compile_btn",
        "cancel_btn",
        "btn_help",
        "btn_suggest_deps",
        "activity_btn_deps",
        "btn_bc_loader",
        "btn_acasl_loader",
        "btn_lock_manager",
        "progress",
        "log",
        "btn_show_stats",
        "advanced_cfg_btn",
        "select_lang",
        "select_theme",
        "compiler_tabs",
        "tab_hello",
        "toolButton_more",
        "btn_select_icon",
        "btn_nuitka_icon",
        "statusbar",
        "status_hint",
    ):
        if not hasattr(self, name):
            setattr(self, name, None)


def _map_ide_like_widgets(self) -> None:
    """Backward-compatible alias for widget mapping."""
    _setup_widgets(self)


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
            from .Dialogs.BcaslDialog import open_bc_loader_dialog

            self.btn_bc_loader.clicked.connect(
                lambda: open_bc_loader_dialog(self)
            )
        except Exception:
            pass

    if self.btn_lock_manager:
        _connect_clicked(self.btn_lock_manager, self.open_lock_dialog)

    _connect_clicked(self.btn_help, self.show_help_dialog)

    if self.btn_show_stats:
        _connect_clicked(self.btn_show_stats, self.show_statistics)

    if self.select_lang:
        _connect_clicked(self.select_lang, lambda: show_language_dialog(self))

    if self.select_theme:
        _connect_clicked(self.select_theme, lambda: show_theme_dialog(self))

    def update_compiler_options_enabled() -> None:
        if not self.compiler_tabs:
            return
        try:
            import pycompiler_ark.Core.engine as engines_loader

            idx = self.compiler_tabs.currentIndex()
            engines_loader.registry.get_engine_for_tab(idx)
        except Exception:
            pass

    if self.compiler_tabs:
        self.compiler_tabs.currentChanged.connect(
            update_compiler_options_enabled
        )
        update_compiler_options_enabled()

    if self.btn_suggest_deps:
        _connect_clicked(
            self.btn_suggest_deps, self.suggest_missing_dependencies
        )


def _show_initial_help_message(self) -> None:
    """Show help hint when no workspace is selected."""
    return


def init_ui(self) -> None:
    """Initialize UI and connect shared feature wiring."""
    _load_ui(self)
    _setup_widgets(self)
    _tune_layout(self)

    try:
        _connect_dialogs_to_app(self)
        _apply_initial_theme(self)
        _refresh_log_palette(self)
        _apply_button_icons(self)
        try:
            QTimer.singleShot(0, lambda: _auto_resize_for_screen(self))
        except Exception:
            _auto_resize_for_screen(self)
        _apply_activity_buttons_theme(self)
    except Exception:
        pass

    _setup_more_tools_menu(self)
    try:
        _connect_signals(self)
    except Exception:
        pass
    _connect_ui_specific_signals(self)
    try:
        if hasattr(self, "setup_entrypoint_selector"):
            self.setup_entrypoint_selector()
    except Exception:
        pass
    _schedule_async_init(self)
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
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "themes"
        )
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
                                    int(
                                        max(0.0, min(100.0, float(s[:-1])))
                                        * 2.55
                                    )
                                )
                            else:
                                vals.append(
                                    int(max(0.0, min(255.0, float(s))))
                                )
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
        avg = sum(
            0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in rgbs
        ) / len(rgbs)
        return avg < 128.0
    except Exception:
        return False


def _extract_accent_color_for_icons(css_text: str) -> str | None:
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

        for selector in ("QPushButton#btn_build_all", "#btn_build_all"):
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
    return "# FFFFFF" if _detect_system_color_scheme() == "dark" else "#111111"


def themed_svg_icon(
    path: str, size: int = 18, css: str | None = None
) -> QIcon | None:
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
            norm = (
                pref.lower().replace(" ", "").replace("-", "").replace("_", "")
            )
            for disp, path in candidates:
                stem = os.path.splitext(os.path.basename(path))[0]
                stem_n = (
                    stem.lower()
                    .replace(" ", "")
                    .replace("-", "")
                    .replace("_", "")
                )
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
                if self.theme == "System":
                    val = translate(
                        self.id,
                        "choose_theme_system_button",
                        translate(self.id, "choose_theme_button", "Theme"),
                    )
                else:
                    val = translate(self.id, "choose_theme_button", "Theme")
                if isinstance(val, str) and val:
                    self.select_theme.setText(val)
            except Exception:
                pass
        try:
            if chosen_path:
                output.info(
                    (
                        f"Thème appliqué : {chosen_name} ({os.path.basename(chosen_path)})",
                        f"Theme applied: {chosen_name} ({os.path.basename(chosen_path)})",
                    ),
                    gui=self,
                )
            else:
                output.warn(
                    (
                        "Aucun thème appliqué (aucun fichier .qss trouvé dans themes)",
                        "No theme applied (no .qss file found in themes)",
                    ),
                    gui=self,
                )
        except Exception:
            pass
    except Exception as e:
        try:
            if hasattr(self, "log") and self.log:
                try:
                    output.warn(
                        (
                            f"Échec d'application du thème: {e}",
                            f"Failed to apply theme: {e}",
                        ),
                        gui=self,
                    )
                except Exception:
                    output.warn(f"Échec d'application du thème: {e}", gui=self)
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
    title = translate(
        self.id,
        "choose_theme_title",
        getattr(self, "windowTitle", lambda: "")(),
    )
    label = translate(
        self.id,
        "choose_theme_label",
        getattr(getattr(self, "select_theme", None), "text", lambda: "")(),
    )
    choice, ok = QInputDialog.getItem(
        self, title, label, options, start_index, False
    )
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
            output.info(
                ("Sélection du thème annulée.", "Theme selection cancelled."),
                gui=self,
            )
        except Exception:
            pass


def _load_ui(self) -> None:
    """Load the generated Qt UI module and bind it to the main window."""
    ui = Ui_MainWindow()
    ui.setupUi(self)
    # Keep the main window as the lookup root; setupUi attaches children to it.
    self.ui = self

    _clear_inline_styles(self)
    try:
        central = self.centralWidget()
        if central is not None:
            _clear_inline_styles(central)
    except Exception:
        pass

    try:
        self.setStyleSheet("")
    except Exception:
        pass
    try:
        app = QApplication.instance()
        if app is not None and app.styleSheet():
            self.ui.style().unpolish(self.ui)
            self.ui.style().polish(self.ui)
    except Exception:
        pass


def _clear_inline_styles(root: QWidget) -> None:
    """Remove inline stylesheets so the app theme can apply cleanly."""
    try:
        if root.styleSheet():
            root.setStyleSheet("")
    except Exception:
        pass
    try:
        for widget in root.findChildren(QWidget):
            try:
                if widget.styleSheet():
                    widget.setStyleSheet("")
            except Exception:
                pass
    except Exception:
        pass


def _tune_layout(self) -> None:
    """Apply runtime splitter ratios; static constraints live in the .ui file."""
    main_splitter = self.ui.findChild(QSplitter, "mainSplitter")
    if main_splitter is not None:
        try:
            main_splitter.setStretchFactor(0, 0)
            main_splitter.setStretchFactor(1, 0)
            main_splitter.setStretchFactor(2, 1)
            main_splitter.setSizes([52, 300, 1013])
        except Exception:
            pass

    top_splitter = self.ui.findChild(QSplitter, "topSplitter")
    if top_splitter is not None:
        try:
            top_splitter.setStretchFactor(0, 1)
            top_splitter.setStretchFactor(1, 0)
            top_splitter.setSizes([820, 245])
        except Exception:
            pass

    right_splitter = self.ui.findChild(QSplitter, "rightSplitter")
    if right_splitter is not None:
        try:
            right_splitter.setStretchFactor(0, 1)
            right_splitter.setStretchFactor(1, 0)
            right_splitter.setSizes([470, 230])
        except Exception:
            pass


def _setup_compiler_tabs(self) -> None:
    """Bind compiler tabs using the existing engine registry."""
    tabs = getattr(self, "compiler_tabs", None)
    if tabs is None:
        return
    try:
        import pycompiler_ark.Core.engine as engines_loader

        engines_loader.bind_tabs(self)
    except Exception:
        pass


def _setup_more_tools_menu(self) -> None:
    """Attach a compact actions menu to the three-dots tool button."""
    more_btn = getattr(self, "toolButton_more", None)
    if more_btn is None:
        return

    try:
        more_btn.setToolTip(
            translate(self, "tt_more_actions", more_btn.toolTip())
        )
        menu = QMenu(more_btn)
        self._ide_more_tools_menu = menu

        act_workspace = QAction(
            translate(self, "action_select_workspace", "Select Workspace"),
            menu,
        )
        act_workspace.setObjectName("action_select_workspace")
        act_workspace.triggered.connect(
            lambda: getattr(self, "select_workspace", lambda: None)()
        )
        menu.addAction(act_workspace)

        act_init = QAction(
            translate(self, "action_init_project", "Initialise Project"), menu
        )
        act_init.setObjectName("action_init_project")
        act_init.triggered.connect(
            lambda: getattr(self, "open_init_workspace_dialog", lambda: None)()
        )
        menu.addAction(act_init)

        act_venv = QAction(
            translate(self, "action_select_venv", "Select Venv"), menu
        )
        act_venv.setObjectName("action_select_venv")
        act_venv.triggered.connect(
            lambda: getattr(self, "select_venv_manually", lambda: None)()
        )
        menu.addAction(act_venv)

        act_add_files = QAction(
            translate(self, "action_add_files", "Add Files"), menu
        )
        act_add_files.setObjectName("action_add_files")
        act_add_files.triggered.connect(
            lambda: getattr(self, "select_files_manually", lambda: None)()
        )
        menu.addAction(act_add_files)

        act_clear_workspace = QAction(
            translate(self, "btn_clear_workspace", "Clear Workspace"), menu
        )
        act_clear_workspace.setObjectName("btn_clear_workspace")
        act_clear_workspace.triggered.connect(
            lambda: getattr(self, "clear_workspace", lambda: None)()
        )
        menu.addAction(act_clear_workspace)

        act_stats = QAction(translate(self, "show_stats", "Show Stats"), menu)
        act_stats.setObjectName("show_stats")
        act_stats.triggered.connect(
            lambda: getattr(self, "show_statistics", lambda: None)()
        )
        menu.addAction(act_stats)

        menu.addSeparator()

        act_language = QAction(
            translate(self, "choose_language_button", "Language"), menu
        )
        act_language.setObjectName("btn_select_lang")
        act_language.triggered.connect(
            lambda: getattr(self, "show_language_dialog", lambda: None)()
        )
        menu.addAction(act_language)

        act_theme = QAction(
            translate(self, "choose_theme_button", "Theme"), menu
        )
        act_theme.setObjectName("btn_select_theme")
        act_theme.triggered.connect(lambda: _open_theme_dialog(self))
        menu.addAction(act_theme)

        menu.addSeparator()

        act_advanced = QAction(
            translate(self, "advanced_config", "Advanced Config"), menu
        )
        act_advanced.setObjectName("advanced_config")
        act_advanced.triggered.connect(
            lambda: getattr(
                self, "open_advanced_config_editor", lambda: None
            )()
        )
        menu.addAction(act_advanced)

        act_lock = QAction(
            translate(self, "lock_manager", "Lock Manager"), menu
        )
        act_lock.setObjectName("lock_manager")
        act_lock.triggered.connect(
            lambda: getattr(self, "open_lock_dialog", lambda: None)()
        )
        menu.addAction(act_lock)

        act_save_engines = QAction(
            translate(self, "save_engine_configs", "Save Engine Configs"), menu
        )
        act_save_engines.setObjectName("save_engine_configs")
        act_save_engines.triggered.connect(
            lambda: getattr(self, "save_all_engine_configs", lambda: None)()
        )
        menu.addAction(act_save_engines)

        act_help = QAction(translate(self, "help", "Help"), menu)
        act_help.setObjectName("help")
        act_help.triggered.connect(
            lambda: getattr(self, "show_help_dialog", lambda: None)()
        )
        menu.addAction(act_help)

        self._ide_more_menu_actions = {
            "workspace": act_workspace,
            "init": act_init,
            "venv": act_venv,
            "add_files": act_add_files,
            "clear_workspace": act_clear_workspace,
            "stats": act_stats,
            "language": act_language,
            "theme": act_theme,
            "advanced": act_advanced,
            "lock": act_lock,
            "save_engines": act_save_engines,
            "help": act_help,
        }

        more_btn.setMenu(menu)
        more_btn.setPopupMode(QToolButton.InstantPopup)
    except Exception:
        pass
    _retranslate_actions(self)
    _apply_activity_buttons_theme(self)

    for attr in (
        "btn_select_folder",
        "venv_button",
        "btn_select_files",
        "btn_clear_workspace",
        "btn_show_stats",
        "select_lang",
        "select_theme",
        "advanced_cfg_btn",
        "btn_help",
        "btn_suggest_deps",
    ):
        widget = getattr(self, attr, None)
        if widget is None:
            continue
        try:
            widget.setVisible(False)
        except Exception:
            pass


def _open_theme_dialog(self) -> None:
    """Bridge to existing theme dialog function without adding new core logic."""
    try:
        show_theme_dialog(self)
    except Exception:
        pass
    _apply_activity_buttons_theme(self)


def _apply_activity_buttons_theme(self) -> None:
    """Ensure activity-bar tool buttons follow current app theme."""
    try:
        app = QApplication.instance()
        css = app.styleSheet() if app else ""
        dark = _is_qss_dark(css or "")
    except Exception:
        dark = True

    if dark:
        base = "#1B1E23"
        hover = "#232831"
        pressed = "#20242C"
        border = "#2A2F37"
        fg = "#E6E8EB"
    else:
        base = "#FFFFFF"
        hover = "#F1F3F6"
        pressed = "#E7EAF0"
        border = "#D6D9DF"
        fg = "#1C1F26"

    style = (
        "QToolButton {"
        f"background: {base};"
        f"color: {fg};"
        f"border: 1px solid {border};"
        "border-radius: 8px;"
        "padding: 4px;"
        "}"
        f"QToolButton:hover {{ background: {hover}; }}"
        f"QToolButton:pressed, QToolButton:checked {{ background: {pressed}; }}"
        "QToolButton::menu-indicator { image: none; width: 0px; }"
    )

    try:
        base_path = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."
            )
        )
        icons_dir = os.path.join(base_path, "data", "icons")

        more_btn = getattr(self, "toolButton_more", None)
        if more_btn is not None:
            more_icon = themed_svg_icon(
                os.path.join(icons_dir, "more-horizontal.svg"), size=18
            )
            if more_icon is not None and not more_icon.isNull():
                more_btn.setIcon(more_icon)
                more_btn.setIconSize(more_btn.iconSize())
                more_btn.setText("")

        deps_btn = getattr(self, "activity_btn_deps", None)
        src_btn = getattr(self, "btn_suggest_deps", None)
        if deps_btn is not None:
            if (
                src_btn is not None
                and src_btn.icon() is not None
                and not src_btn.icon().isNull()
            ):
                deps_btn.setIcon(src_btn.icon())
                deps_btn.setIconSize(src_btn.iconSize())
                try:
                    deps_btn.setToolTip(src_btn.toolTip())
                except Exception:
                    pass
            else:
                deps_icon = themed_svg_icon(
                    os.path.join(icons_dir, "search.svg"), size=18
                )
                if deps_icon is not None and not deps_icon.isNull():
                    deps_btn.setIcon(deps_icon)
    except Exception:
        pass

    for attr in ("toolButton_more", "activity_btn_deps"):
        btn = getattr(self, attr, None)
        if btn is None:
            continue
        try:
            btn.setStyleSheet(style)
        except Exception:
            pass
    _apply_status_bar_theme(self, dark, fg, border)


def _retranslate_actions(self) -> None:
    """Refresh IDE-specific actions using the generic i18n traversal."""
    try:
        from ..i18n import (
            _apply_main_app_translations,
            get_active_translations,
        )

        _apply_main_app_translations(self, get_active_translations())
    except Exception:
        pass


def _retranslate_ide_like_actions(self) -> None:
    """Backward-compatible alias for older i18n call sites."""
    _retranslate_actions(self)


def _connect_ui_specific_signals(self) -> None:
    """Connect only UI-specific signals on top of the shared wiring."""

    def _connect_clicked(widget, handler) -> None:
        if widget is None or handler is None:
            return
        try:
            widget.clicked.connect(handler)
        except Exception:
            pass

    _connect_clicked(
        getattr(self, "activity_btn_deps", None),
        getattr(self, "suggest_missing_dependencies", None),
    )
    _bind_status_updates(self)


def _setup_status_bar(self) -> None:
    if self.statusbar is None:
        try:
            self.statusbar = QStatusBar(self)
            self.statusbar.setObjectName("statusbar")
            self.setStatusBar(self.statusbar)
        except Exception:
            return
    try:
        existing = getattr(self, "status_hint", None)
        if existing is None:
            existing = self.statusbar.findChild(QLabel, "status_ready")
        if existing is None:
            existing = QLabel("Ready")
            existing.setObjectName("status_ready")
            self.statusbar.addPermanentWidget(existing, 1)
        self.status_hint = existing
        self.status_hint.setText(translate(self, "status_ready", "Ready"))
    except Exception:
        pass


def _apply_status_bar_theme(self, dark: bool, fg: str, border: str) -> None:
    if not getattr(self, "statusbar", None):
        return
    bg = "#151A20" if dark else "#F7F7F9"
    style = (
        "QStatusBar {"
        f"background: {bg};"
        f"color: {fg};"
        f"border-top: 1px solid {border};"
        "}"
        "QStatusBar::item { border: none; }"
        "QLabel#status_ready { padding: 2px 8px; }"
    )
    try:
        self.statusbar.setStyleSheet(style)
    except Exception:
        pass


def _bind_status_updates(self) -> None:
    """Keep a lightweight status line without touching core logic."""
    statusbar = getattr(self, "statusbar", None)
    if statusbar is None:
        return

    def _queue_update() -> None:
        try:
            QTimer.singleShot(0, lambda: _update_status_line(self))
        except Exception:
            _update_status_line(self)

    _queue_update()

    for attr in (
        "btn_select_folder",
        "btn_select_files",
        "btn_remove_file",
        "btn_clear_workspace",
        "venv_button",
        "compile_btn",
        "cancel_btn",
    ):
        btn = getattr(self, attr, None)
        if btn is None:
            continue
        try:
            btn.clicked.connect(_queue_update)
        except Exception:
            pass

    file_list = getattr(self, "file_list", None)
    if file_list is not None:
        try:
            file_list.itemSelectionChanged.connect(_queue_update)
        except Exception:
            pass
        try:
            model = file_list.model()
            if model is not None:
                model.rowsInserted.connect(lambda *_: _queue_update())
                model.rowsRemoved.connect(lambda *_: _queue_update())
                model.modelReset.connect(lambda *_: _queue_update())
        except Exception:
            pass

    compiler_tabs = getattr(self, "compiler_tabs", None)
    if compiler_tabs is not None:
        try:
            compiler_tabs.currentChanged.connect(lambda *_: _queue_update())
        except Exception:
            pass

    progress = getattr(self, "progress", None)
    if progress is not None:
        try:
            progress.valueChanged.connect(lambda *_: _queue_update())
        except Exception:
            pass


def _update_status_line(self) -> None:
    statusbar = getattr(self, "statusbar", None)
    if statusbar is None:
        return

    def _workspace_label(path: str | None) -> str:
        if not path:
            return "-"
        try:
            p = os.path.normpath(path)
            name = os.path.basename(p)
            return name or p
        except Exception:
            return path

    ws = _workspace_label(getattr(self, "workspace_dir", None))
    files_total = 0
    files_sel = 0
    try:
        fl = getattr(self, "file_list", None)
        if fl is not None:
            files_total = fl.count()
            files_sel = len(fl.selectedItems())
    except Exception:
        pass

    engine_name = "None"
    try:
        tabs = getattr(self, "compiler_tabs", None)
        if tabs is not None and tabs.currentIndex() >= 0:
            engine_name = tabs.tabText(tabs.currentIndex())
    except Exception:
        pass

    prog = ""
    try:
        pb = getattr(self, "progress", None)
        if pb is not None and pb.value() > 0:
            prog = f"{pb.value()}%"
    except Exception:
        pass

    parts = [f"WS:{ws}", f"F:{files_sel}/{files_total}", f"E:{engine_name}"]
    if prog:
        parts.append(f"P:{prog}")

    msg = " | ".join(parts)
    try:
        if getattr(self, "status_hint", None):
            self.status_hint.setText(msg)
        statusbar.showMessage(msg)
    except Exception:
        pass


def _schedule_async_init(self) -> None:
    """Defer heavier setup steps to keep first paint responsive."""
    try:
        QTimer.singleShot(0, lambda: _setup_compiler_tabs(self))
    except Exception:
        _setup_compiler_tabs(self)


def _load_ide_like_ui(self) -> None:
    """Backward-compatible alias for older loader call sites."""
    _load_ui(self)


def _tune_ide_like_layout(self) -> None:
    """Backward-compatible alias for older layout call sites."""
    _tune_layout(self)


def _connect_ide_like_specific_signals(self) -> None:
    """Backward-compatible alias for older signal wiring call sites."""
    _connect_ui_specific_signals(self)


def _schedule_ide_like_async_init(self) -> None:
    """Backward-compatible alias for older async init call sites."""
    _schedule_async_init(self)


def _setup_ide_like_compiler_tabs(self) -> None:
    """Backward-compatible alias for older compiler tab init call sites."""
    _setup_compiler_tabs(self)


def _apply_classic_policies(self) -> None:
    """Backward-compatible alias for the old policy block."""
    try:
        _connect_dialogs_to_app(self)
        _apply_initial_theme(self)
        _refresh_log_palette(self)
        _apply_button_icons(self)
        try:
            QTimer.singleShot(0, lambda: _auto_resize_for_screen(self))
        except Exception:
            _auto_resize_for_screen(self)
        _apply_activity_buttons_theme(self)
    except Exception:
        pass

    try:
        if getattr(self, "btn_acasl_loader", None):
            self.btn_acasl_loader.hide()
            self.btn_acasl_loader.setEnabled(False)
    except Exception:
        pass

    for lbl_name in ("label_folder", "venv_label"):
        lbl = getattr(self, lbl_name, None)
        if lbl is None:
            continue
        try:
            lbl.setStyleSheet("border: none; background: transparent;")
        except Exception:
            pass

    try:
        if getattr(self, "activity_btn_deps", None):
            src = getattr(self, "btn_suggest_deps", None)
            if src is not None:
                self.activity_btn_deps.setIcon(src.icon())
                self.activity_btn_deps.setIconSize(src.iconSize())
                self.activity_btn_deps.setToolTip(src.toolTip())
    except Exception:
        pass
