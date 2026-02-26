# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""Connections for `ui/ui_ide_design2.ui`.

This module intentionally contains only UI loading, widget mapping and signal
connections to existing methods on the main GUI object.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QFile, QTimer
from PySide6.QtGui import QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QApplication,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QMenu,
    QTabWidget,
    QTextEdit,
    QToolButton,
    QWidget,
)


def _prime_expected_attrs(self) -> None:
    """Create expected UI attributes with safe defaults."""
    names = [
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
        "progress",
        "log",
        "btn_export_config",
        "btn_import_config",
        "btn_show_stats",
        "advanced_cfg_btn",
        "select_lang",
        "select_theme",
        "compiler_tabs",
        "tab_hello",
        "btn_select_icon",
        "btn_nuitka_icon",
        "toolButton_more",
    ]
    for name in names:
        if not hasattr(self, name):
            setattr(self, name, None)


def _load_ide_like_ui(self) -> None:
    """Load the new ide-like UI file and set it as central widget."""
    loader = QUiLoader()
    ui_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "ui", "ui_ide_design2.ui"
    )
    ui_file = QFile(os.path.abspath(ui_path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Impossible d'ouvrir le fichier UI : {ui_path}")
    loaded = loader.load(ui_file)
    ui_file.close()
    if loaded is None:
        raise RuntimeError(f"Échec du chargement du fichier UI : {ui_path}")

    # ui_ide_design2.ui uses QMainWindow as root. Reuse its central widget.
    if isinstance(loaded, QMainWindow):
        _clear_inline_styles(loaded)
        central = loaded.takeCentralWidget()
        if central is None:
            central = loaded.findChild(QWidget, "centralwidget")
        if central is None:
            raise RuntimeError("Le fichier UI IDE-like ne contient pas de centralwidget.")
        self.ui = central
    else:
        self.ui = loaded

    _clear_inline_styles(self.ui)

    # Keep styling source of truth at app level.
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

    self.setCentralWidget(self.ui)


def _clear_inline_styles(root: QWidget) -> None:
    """Remove stylesheets embedded in the loaded IDE UI to inherit app theme."""
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


def _map_ide_like_widgets(self) -> None:
    """Map design2 widget names to existing Core attribute names."""
    _prime_expected_attrs(self)

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
    self.file_filter_input = _find(QLineEdit, "file_filter_input")
    self.compiler_tabs = _find(QTabWidget, "compiler_tabs")
    self.tab_hello = _find(QWidget, "tab_hello")
    self.file_list = _find(QListWidget, "file_list")
    self.compile_btn = _find(QPushButton, "compile_btn")
    self.cancel_btn = _find(QPushButton, "cancel_btn")
    self.btn_help = _find(QPushButton, "btn_help")
    self.btn_suggest_deps = _find(QPushButton, "btn_suggest_deps")
    self.activity_btn_deps = _find(QToolButton, "activity_btn_deps")
    self.btn_bc_loader = _find(QPushButton, "btn_bc_loader")
    self.btn_acasl_loader = _find(QPushButton, "btn_acasl_loader")
    self.btn_show_stats = _find(QPushButton, "btn_show_stats")
    self.btn_export_config = _find(QPushButton, "btn_export_config")
    self.btn_import_config = _find(QPushButton, "btn_import_config")
    self.select_lang = _find(QPushButton, "select_lang")
    self.select_theme = _find(QPushButton, "select_theme")
    self.advanced_cfg_btn = _find(QPushButton, "advanced_cfg_btn")
    self.btn_select_files = _find(QPushButton, "btn_select_files")
    self.btn_remove_file = _find(QPushButton, "btn_remove_file")
    self.btn_clear_workspace = _find(QPushButton, "btn_clear_workspace")
    self.btn_select_icon = _find(QPushButton, "btn_select_icon")
    self.btn_nuitka_icon = _find(QPushButton, "btn_nuitka_icon")
    self.toolButton_more = _find(QToolButton, "toolButton_more")
    self.log = _find(QTextEdit, "log")
    self.progress = _find(QProgressBar, "progress")
    try:
        if self.log is not None:
            self.log.setReadOnly(True)
            self.log.setAcceptRichText(False)
    except Exception:
        pass


def _setup_ide_like_compiler_tabs(self) -> None:
    """Bind engine tabs to compiler_tabs using existing EngineLoader registry."""
    tabs = getattr(self, "compiler_tabs", None)
    if tabs is None:
        return
    try:
        import EngineLoader as engines_loader

        engines_loader.registry.bind_tabs(self)
    except Exception:
        pass


def _apply_classic_policies(self) -> None:
    """Reuse classic UI policies (prefs/theme/icons/palette/dialog binding)."""
    try:
        from ..UiConnection import (
            _apply_button_icons,
            _apply_initial_theme,
            _connect_dialogs_to_app,
            _refresh_log_palette,
        )

        _connect_dialogs_to_app(self)
        _apply_initial_theme(self)
        _refresh_log_palette(self)
        _apply_button_icons(self)
    except Exception:
        pass

    # Keep parity with classic UI for deprecated/removed entries.
    try:
        if getattr(self, "btn_acasl_loader", None):
            self.btn_acasl_loader.hide()
            self.btn_acasl_loader.setEnabled(False)
    except Exception:
        pass

    # Keep workspace labels clean like the classic UI.
    for lbl_name in ("label_folder", "venv_label"):
        lbl = getattr(self, lbl_name, None)
        if lbl is None:
            continue
        try:
            lbl.setStyleSheet("border: none; background: transparent;")
        except Exception:
            pass

    # Mirror dependencies action as an activity-bar icon button.
    try:
        if getattr(self, "activity_btn_deps", None):
            self.activity_btn_deps.setToolTip(
                self.tr("Analyser dépendances", "Analyze dependencies")
            )
            src = getattr(self, "btn_suggest_deps", None)
            if src is not None:
                self.activity_btn_deps.setIcon(src.icon())
                self.activity_btn_deps.setIconSize(src.iconSize())
    except Exception:
        pass
    _apply_activity_buttons_theme(self)


def _setup_more_tools_menu(self) -> None:
    """Attach a compact actions menu to the three-dots tool button."""
    more_btn = getattr(self, "toolButton_more", None)
    if more_btn is None:
        return

    try:
        menu = QMenu(more_btn)

        act_language = QAction("Language", menu)
        act_language.triggered.connect(lambda: getattr(self, "show_language_dialog", lambda: None)())
        menu.addAction(act_language)

        act_theme = QAction("Theme", menu)
        act_theme.triggered.connect(lambda: _open_theme_dialog(self))
        menu.addAction(act_theme)

        menu.addSeparator()

        act_advanced = QAction("Advanced config", menu)
        act_advanced.triggered.connect(
            lambda: getattr(self, "open_advanced_config_editor", lambda: None)()
        )
        menu.addAction(act_advanced)

        act_export = QAction("Export config", menu)
        act_export.triggered.connect(lambda: getattr(self, "export_config", lambda: None)())
        menu.addAction(act_export)

        act_import = QAction("Import config", menu)
        act_import.triggered.connect(lambda: getattr(self, "import_config", lambda: None)())
        menu.addAction(act_import)

        act_help = QAction("Help", menu)
        act_help.triggered.connect(lambda: getattr(self, "show_help_dialog", lambda: None)())
        menu.addAction(act_help)

        more_btn.setMenu(menu)
        more_btn.setPopupMode(QToolButton.InstantPopup)
    except Exception:
        pass
    _apply_activity_buttons_theme(self)

    # Avoid duplicated controls in the side panel.
    for attr in (
        "select_lang",
        "select_theme",
        "advanced_cfg_btn",
        "btn_export_config",
        "btn_import_config",
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
        from ..UiConnection import show_theme_dialog

        show_theme_dialog(self)
    except Exception:
        pass
    _apply_activity_buttons_theme(self)


def _apply_activity_buttons_theme(self) -> None:
    """Ensure activity-bar tool buttons follow current app theme."""
    try:
        from ..UiConnection import _is_qss_dark

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

    for attr in ("toolButton_more", "activity_btn_deps"):
        btn = getattr(self, attr, None)
        if btn is None:
            continue
        try:
            btn.setStyleSheet(style)
        except Exception:
            pass


def _connect_ide_like_signals(self) -> None:
    """Connect UI signals to existing methods implemented in Core."""

    def _connect_clicked(widget, handler) -> None:
        if widget is None or handler is None:
            return
        try:
            widget.clicked.connect(handler)
        except Exception:
            pass

    def _connect_text(widget, handler) -> None:
        if widget is None or handler is None:
            return
        try:
            widget.textChanged.connect(handler)
        except Exception:
            pass

    _connect_clicked(getattr(self, "btn_select_folder", None), getattr(self, "select_workspace", None))
    _connect_clicked(getattr(self, "venv_button", None), getattr(self, "select_venv_manually", None))
    _connect_clicked(getattr(self, "btn_select_files", None), getattr(self, "select_files_manually", None))
    _connect_clicked(getattr(self, "btn_remove_file", None), getattr(self, "remove_selected_file", None))
    _connect_clicked(getattr(self, "btn_clear_workspace", None), getattr(self, "clear_workspace", None))
    _connect_clicked(getattr(self, "compile_btn", None), getattr(self, "compile_all", None))
    _connect_clicked(
        getattr(self, "cancel_btn", None),
        getattr(self, "cancel_all_compilations", None),
    )
    _connect_clicked(getattr(self, "advanced_cfg_btn", None), getattr(self, "open_advanced_config_editor", None))
    _connect_clicked(getattr(self, "btn_help", None), getattr(self, "show_help_dialog", None))
    _connect_clicked(getattr(self, "btn_suggest_deps", None), getattr(self, "suggest_missing_dependencies", None))
    _connect_clicked(
        getattr(self, "activity_btn_deps", None),
        getattr(self, "suggest_missing_dependencies", None),
    )
    _connect_clicked(getattr(self, "btn_show_stats", None), getattr(self, "show_statistics", None))
    _connect_clicked(getattr(self, "btn_export_config", None), getattr(self, "export_config", None))
    _connect_clicked(getattr(self, "btn_import_config", None), getattr(self, "import_config", None))
    _connect_clicked(getattr(self, "select_lang", None), getattr(self, "show_language_dialog", None))
    _connect_clicked(getattr(self, "select_theme", None), lambda: _open_theme_dialog(self))
    _connect_text(getattr(self, "file_filter_input", None), getattr(self, "apply_file_filter", None))

    if getattr(self, "btn_bc_loader", None):
        try:
            from bcasl import open_bc_loader_dialog

            self.btn_bc_loader.clicked.connect(lambda: open_bc_loader_dialog(self))
        except Exception:
            pass

def init_ide_like_ui(self) -> None:
    """Initialize the ide-like UI and wire it to existing Core methods."""
    _load_ide_like_ui(self)
    _map_ide_like_widgets(self)
    _apply_classic_policies(self)
    _setup_more_tools_menu(self)
    _connect_ide_like_signals(self)
    _schedule_ide_like_async_init(self)


def _schedule_ide_like_async_init(self) -> None:
    """Defer heavier IDE setup steps to keep first paint responsive."""
    try:
        QTimer.singleShot(0, lambda: _setup_ide_like_compiler_tabs(self))
    except Exception:
        _setup_ide_like_compiler_tabs(self)
