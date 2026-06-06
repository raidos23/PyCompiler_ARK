# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""Connections for `Ui/Forms/ide_main_window.ui`.

Ce module contient uniquement le chargement UI, le mapping des widgets et les
connexions de signaux vers les méthodes existantes de la GUI principale.
"""

from __future__ import annotations

import os

from PySide6.QtCore import QFile, QTimer
from PySide6.QtGui import QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
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

from pycompiler_ark.Ui.Gui.UiConnection import (
    _apply_button_icons,
    _apply_initial_theme,
    _auto_resize_for_screen,
    _connect_dialogs_to_app,
)
from pycompiler_ark.Ui.Gui.UiConnection import _connect_signals as _connect_classic_signals
from pycompiler_ark.Ui.Gui.UiConnection import (
    _is_qss_dark,
    _refresh_log_palette,
    show_theme_dialog,
    themed_svg_icon,
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
        "btn_show_stats",
        "advanced_cfg_btn",
        "select_lang",
        "select_theme",
        "compiler_tabs",
        "tab_hello",
        "toolButton_more",
    ]
    for name in names:
        if not hasattr(self, name):
            setattr(self, name, None)


def _load_ide_like_ui(self) -> None:
    """Load the new ide-like UI file and set it as central widget."""
    from pycompiler_ark.Ui import ui_form_path

    loader = QUiLoader()
    ui_path = ui_form_path("ide_main_window.ui")
    ui_file = QFile(os.path.abspath(ui_path))
    if not ui_file.open(QFile.ReadOnly):
        raise RuntimeError(f"Impossible d'ouvrir le fichier UI : {ui_path}")
    loaded = loader.load(ui_file)
    ui_file.close()
    if loaded is None:
        raise RuntimeError(f"Échec du chargement du fichier UI : {ui_path}")

    if isinstance(loaded, QMainWindow):
        _clear_inline_styles(loaded)
        try:
            statusbar = loaded.statusBar()
            if statusbar is not None:
                statusbar.setParent(self)
                self.setStatusBar(statusbar)
        except Exception:
            pass
        central = loaded.takeCentralWidget()
        if central is None:
            central = loaded.findChild(QWidget, "centralwidget")
        if central is None:
            raise RuntimeError(
                "Le fichier UI IDE-like ne contient pas de centralwidget."
            )
        self.ui = central
    else:
        self.ui = loaded

    _clear_inline_styles(self.ui)

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
    self.select_lang = _find(QPushButton, "select_lang")
    self.select_theme = _find(QPushButton, "select_theme")
    self.advanced_cfg_btn = _find(QPushButton, "advanced_cfg_btn")
    self.btn_select_files = _find(QPushButton, "btn_select_files")
    self.btn_remove_file = _find(QPushButton, "btn_remove_file")
    self.btn_clear_workspace = _find(QPushButton, "btn_clear_workspace")
    self.btn_select_icon = None
    self.btn_nuitka_icon = None
    self.toolButton_more = _find(QToolButton, "toolButton_more")
    self.log = _find(QTextEdit, "log")
    self.progress = _find(QProgressBar, "progress")
    self.statusbar = self.findChild(QStatusBar, "statusbar")
    self.status_hint = None
    try:
        self.status_hint = (
            self.statusbar.findChild(QLabel, "status_hint") if self.statusbar else None
        )
    except Exception:
        self.status_hint = None
    _setup_status_bar(self)


def _tune_ide_like_layout(self) -> None:
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


def _setup_ide_like_compiler_tabs(self) -> None:
    """Bind engine tabs to compiler_tabs using existing EngineLoader registry."""
    tabs = getattr(self, "compiler_tabs", None)
    if tabs is None:
        return
    try:
        import pycompiler_ark.Core.engine as engines_loader

        engines_loader.bind_tabs(self)
    except Exception:
        pass


def _apply_classic_policies(self) -> None:
    """Reuse classic UI policies (prefs/theme/icons/palette/dialog binding)."""
    try:
        _connect_dialogs_to_app(self)
        _apply_initial_theme(self)
        _refresh_log_palette(self)
        _apply_button_icons(self)
        try:
            QTimer.singleShot(0, lambda: _auto_resize_for_screen(self))
        except Exception:
            _auto_resize_for_screen(self)
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
            else:
                self.activity_btn_deps.setToolTip(
                    self.tr("Analyser les dependances", "Analyze dependencies")
                )
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
        self._ide_more_tools_menu = menu

        act_workspace = QAction(menu)
        act_workspace.triggered.connect(
            lambda: getattr(self, "select_workspace", lambda: None)()
        )
        menu.addAction(act_workspace)

        act_init = QAction(menu)
        act_init.triggered.connect(
            lambda: getattr(self, "open_init_workspace_dialog", lambda: None)()
        )
        menu.addAction(act_init)

        act_venv = QAction(menu)
        act_venv.triggered.connect(
            lambda: getattr(self, "select_venv_manually", lambda: None)()
        )
        menu.addAction(act_venv)

        act_add_files = QAction(menu)
        act_add_files.triggered.connect(
            lambda: getattr(self, "select_files_manually", lambda: None)()
        )
        menu.addAction(act_add_files)

        act_clear_workspace = QAction(menu)
        act_clear_workspace.triggered.connect(
            lambda: getattr(self, "clear_workspace", lambda: None)()
        )
        menu.addAction(act_clear_workspace)

        act_stats = QAction(menu)
        act_stats.triggered.connect(
            lambda: getattr(self, "show_statistics", lambda: None)()
        )
        menu.addAction(act_stats)

        menu.addSeparator()

        act_language = QAction(menu)
        act_language.triggered.connect(
            lambda: getattr(self, "show_language_dialog", lambda: None)()
        )
        menu.addAction(act_language)

        act_theme = QAction(menu)
        act_theme.triggered.connect(lambda: _open_theme_dialog(self))
        menu.addAction(act_theme)

        menu.addSeparator()

        act_advanced = QAction(menu)
        act_advanced.triggered.connect(
            lambda: getattr(self, "open_advanced_config_editor", lambda: None)()
        )
        menu.addAction(act_advanced)

        act_lock = QAction(menu)
        act_lock.triggered.connect(
            lambda: getattr(self, "open_lock_dialog", lambda: None)()
        )
        menu.addAction(act_lock)

        act_save_engines = QAction(menu)
        act_save_engines.triggered.connect(
            lambda: getattr(self, "save_all_engine_configs", lambda: None)()
        )
        menu.addAction(act_save_engines)

        act_help = QAction(menu)
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

        try:
            menu.aboutToShow.connect(lambda: _retranslate_ide_like_actions(self))
        except Exception:
            pass

        more_btn.setMenu(menu)
        more_btn.setPopupMode(QToolButton.InstantPopup)
    except Exception:
        pass
    _retranslate_ide_like_actions(self)
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
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
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


def _retranslate_ide_like_actions(self) -> None:
    """Refresh IDE-specific actions using the active translation state."""
    try:
        trf = getattr(self, "tr", None)
        _tr = trf if callable(trf) else (lambda fr, en: en)
    except Exception:
        _tr = lambda fr, en: en

    current_tr = getattr(self, "_tr", {}) or {}

    def _label(key: str, fallback_fr: str, fallback_en: str) -> str:
        try:
            value = current_tr.get(key)
            if isinstance(value, str) and value.strip():
                return value
        except Exception:
            pass
        return _tr(fallback_fr, fallback_en)

    def _widget_text(attr: str) -> str:
        try:
            widget = getattr(self, attr, None)
            if widget is not None:
                text = widget.text()
                if isinstance(text, str) and text.strip():
                    return text
        except Exception:
            pass
        return ""

    lang_key = "choose_language_button"
    try:
        if (
            getattr(self, "language_pref", getattr(self, "language", "System"))
            == "System"
        ):
            lang_key = "choose_language_system_button"
    except Exception:
        pass

    theme_key = "choose_theme_button"
    try:
        if getattr(self, "theme", "System") == "System":
            theme_key = "choose_theme_system_button"
    except Exception:
        pass

    actions = getattr(self, "_ide_more_menu_actions", {}) or {}
    labels = {
        "workspace": _widget_text("btn_select_folder")
        or _label("action_select_workspace", "Choisir Workspace", "Select Workspace"),
        "init": _label("action_init_project", "Initialiser le projet", "Initialize Project"),
        "venv": _widget_text("venv_button")
        or _label("action_select_venv", "Choisir un Venv", "Select Venv"),
        "add_files": _widget_text("btn_select_files")
        or _label("action_add_files", "Ajouter des fichiers", "Add files"),
        "clear_workspace": _widget_text("btn_clear_workspace")
        or _label("btn_clear_workspace", "Vider le Workspace", "Clear workspace"),
        "stats": _widget_text("btn_show_stats")
        or _label("show_stats", "Statistiques", "Statistics"),
        "language": _widget_text("select_lang")
        or _label(lang_key, "Langue", "Language"),
        "theme": _widget_text("select_theme") or _label(theme_key, "Theme", "Theme"),
        "advanced": _widget_text("advanced_cfg_btn")
        or _label("advanced_config", "Configurations avancees", "Advanced config"),
        "lock": _label(
            "lock_manager", "Gestion des verrous (Locks)", "Lock management"
        ),
        "save_engines": _label(
            "save_engine_configs",
            "Enregistrer les configs engines",
            "Save engine configs",
        ),
        "help": _widget_text("btn_help") or _label("help", "Aide", "Help"),
    }
    for key, action in actions.items():
        if action is None:
            continue
        try:
            action.setText(labels.get(key, action.text()))
        except Exception:
            pass

    try:
        more_btn = getattr(self, "toolButton_more", None)
        if more_btn is not None:
            more_btn.setToolTip(
                _label("tt_more_actions", "Plus d'actions.", "More actions.")
            )
    except Exception:
        pass
    try:
        if hasattr(self, "register_language_refresh"):
            if not getattr(self, "_ide_menu_i18n_registered", False):

                def _refresh_menu_i18n() -> None:
                    _retranslate_ide_like_actions(self)
                    try:
                        QTimer.singleShot(
                            0, lambda: _retranslate_ide_like_actions(self)
                        )
                    except Exception:
                        pass

                self.register_language_refresh(_refresh_menu_i18n)
                self._ide_menu_i18n_registered = True
    except Exception:
        pass


def _connect_ide_like_specific_signals(self) -> None:
    """Connect only IDE-specific signals on top of the classic shared wiring."""

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


def init_ide_like_ui(self) -> None:
    """Initialize the ide-like UI and wire it to existing Core methods."""
    _load_ide_like_ui(self)
    _map_ide_like_widgets(self)
    _tune_ide_like_layout(self)
    _apply_classic_policies(self)
    _setup_more_tools_menu(self)
    try:
        _connect_classic_signals(self)
    except Exception:
        pass
    _connect_ide_like_specific_signals(self)
    try:
        if hasattr(self, "setup_entrypoint_selector"):
            self.setup_entrypoint_selector()
    except Exception:
        pass
    _schedule_ide_like_async_init(self)
    try:
        self.set_controls_enabled(True)
    except Exception:
        pass


def _setup_status_bar(self) -> None:
    if self.statusbar is None:
        try:
            self.statusbar = QStatusBar(self)
            self.statusbar.setObjectName("statusbar")
            self.setStatusBar(self.statusbar)
        except Exception:
            return
    try:
        self.status_hint = QLabel("Ready")
        self.status_hint.setObjectName("status_hint")
        self.statusbar.addPermanentWidget(self.status_hint, 1)
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
        "QLabel#status_hint { padding: 2px 8px; }"
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


def _schedule_ide_like_async_init(self) -> None:
    """Defer heavier IDE setup steps to keep first paint responsive."""
    try:
        QTimer.singleShot(0, lambda: _setup_ide_like_compiler_tabs(self))
    except Exception:
        _setup_ide_like_compiler_tabs(self)
