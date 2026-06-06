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
Custom dialogs for PyCompiler ARK.
Inclut ProgressDialog, dialogs de message, et autres dialogues spécifiques.

IMPORTANT: Tous les dialogs ici executent les opérations Qt dans le thread main
via le système d'invoker de Plugins_SDK.GeneralContext.Dialog pour assurer:
- L'héritage du theme de l'application
- L'intégration visuelle avec l'application maine
- La sécurité des threads
"""

import getpass
import platform
import re
from typing import NamedTuple, Optional

from PySide6 import QtCore as _QtC
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)
from rich.console import Console
from rich.panel import Panel


def _get_linux_display_server() -> str:
    """Detect the Linux display server being used. Returns 'wayland', 'x11', or 'unknown'."""
    try:
        import os

        session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
        if session_type in ("wayland", "x11"):
            return session_type
        if os.environ.get("WAYLAND_DISPLAY"):
            return "wayland"
        if os.environ.get("DISPLAY"):
            return "x11"
        return "unknown"
    except Exception:
        return "unknown"


def _invoke_in_main_thread(fn, *args, **kwargs):
    """Invoke a function in the main Qt thread (thread-safe)."""
    try:
        app = QApplication.instance()
        if app is None:
            return fn(*args, **kwargs)

        if _QtC.QThread.currentThread() == app.thread():
            return fn(*args, **kwargs)

        result = []
        exception = []

        def _wrapper():
            try:
                result.append(fn(*args, **kwargs))
            except Exception as e:
                exception.append(e)

        try:
            import platform

            system = platform.system().lower()
            if system == "linux":
                _QtC.QMetaObject.invokeMethod(
                    app, _wrapper, _QtC.Qt.BlockingQueuedConnection
                )
            else:
                _QtC.QMetaObject.invokeMethod(
                    app, _wrapper, _QtC.Qt.BlockingQueuedConnection
                )
        except Exception:
            _QtC.QMetaObject.invokeMethod(
                app, _wrapper, _QtC.Qt.BlockingQueuedConnection
            )

        if exception:
            raise exception[0]

        return result[0] if result else None

    except Exception:
        return fn(*args, **kwargs)


_REDACT_PATTERNS = [
    re.compile(r"(password\s*[:=]\s*)([^\s]+)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:]\s*bearer\s+)([A-Za-z0-9\-_.]+)", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)([A-Za-z0-9\-_.]{12,})", re.IGNORECASE),
]


def _redact_secrets(text: str) -> str:
    """Redact obvious secrets from text for logging."""
    if not text:
        return text
    redacted = str(text)
    try:
        for pat in _REDACT_PATTERNS:
            redacted = pat.sub(lambda m: m.group(1) + "<redacted>", redacted)
    except Exception:
        pass
    return redacted


def _is_noninteractive() -> bool:
    """Check if running in non-interactive mode."""
    from pycompiler_ark.Ui.Cli.runtime import is_noninteractive

    return is_noninteractive()


def _is_cli_mode() -> bool:
    """True when ARK CLI is active: plugins/dialogs must use Rich, not Qt."""
    from pycompiler_ark.Ui.Cli.runtime import is_cli_mode

    return is_cli_mode()


def _use_rich_dialogs() -> bool:
    """Use Rich console dialogs instead of Qt message boxes."""
    from pycompiler_ark.Ui.Cli.runtime import use_rich_dialogs

    return use_rich_dialogs()


def _qt_active_parent():
    """Get the active Qt parent window."""
    try:
        app = QApplication.instance()
        if app is None:
            return None
        w = app.activeWindow()
        if w:
            return w
        try:
            tls = app.topLevelWidgets()
            if tls:
                return tls[0]
        except Exception:
            pass
        return None
    except Exception:
        return None


class InstallAuth(NamedTuple):
    """Authentication info for system installation."""

    method: str  # 'sudo' (POSIX) | 'uac' (Windows)
    secret: Optional[str] = None  # password for 'sudo', None for 'uac'


def show_msgbox(
    kind: str, title: str, text: str, *, parent=None, buttons=None, default=None
) -> Optional[bool]:
    """
    Show a message box if a Qt toolkit is available; fallback to console output otherwise.
    Executes in the main Qt thread to ensure theme inheritance and proper UI integration.
    """
    if _use_rich_dialogs() or QApplication.instance() is None:
        if str(kind or "").lower() != "question":
            try:
                from pycompiler_ark.Ui.i18n import log_with_level

                lvl = "warning" if kind in ("warning", "error") else "info"
                log_with_level(None, lvl, f"[MSGBOX:{kind}] {title}: {text}")
            except Exception:
                pass
        return _show_rich_msgbox(kind, title, text, default=default)

    def _show_in_main_thread():
        try:
            parent_widget = parent or _qt_active_parent()
            mb = QMessageBox(parent_widget)
            mb.setWindowTitle(str(title))
            mb.setText(str(text))
            if kind == "warning":
                mb.setIcon(QMessageBox.Warning)
            elif kind == "error":
                mb.setIcon(QMessageBox.Critical)
            elif kind == "question":
                mb.setIcon(QMessageBox.Question)
            else:
                mb.setIcon(QMessageBox.Information)

            if kind == "question":
                yes = QMessageBox.Yes
                no = QMessageBox.No
                mb.setStandardButtons(yes | no)
                if default and str(default).lower() == "no":
                    mb.setDefaultButton(no)
                else:
                    mb.setDefaultButton(yes)
                res = mb.exec_() if hasattr(mb, "exec_") else mb.exec()
                return res == yes
            else:
                ok = QMessageBox.Ok
                mb.setStandardButtons(ok)
                mb.setDefaultButton(ok)
                _ = mb.exec_() if hasattr(mb, "exec_") else mb.exec()
                return None
        except Exception:
            try:
                from pycompiler_ark.Ui.i18n import log_with_level

                lvl = "warning" if kind in ("warning", "error") else "info"
                log_with_level(None, lvl, f"[MSGBOX:{kind}] {title}: {text}")
            except Exception:
                pass
            return _show_rich_msgbox(kind, title, text, default=default)

    return _invoke_in_main_thread(_show_in_main_thread)


def _show_rich_msgbox(
    kind: str, title: str, text: str, *, default: Optional[str] = None
) -> Optional[bool]:
    """Render a Rich message-box-style panel in CLI environments."""
    from pycompiler_ark.Ui.Cli.interactive import cli_pause_for_user_input

    kind_key = str(kind or "info").lower()
    icon = "ℹ"
    border_style = "cyan"

    if kind_key == "warning":
        icon = "⚠"
        border_style = "yellow"
    elif kind_key == "error":
        icon = "✖"
        border_style = "red"
    elif kind_key == "question":
        icon = "?"
        border_style = "magenta"

    panel_title = f"{icon} {str(title)}" if title else icon
    body = str(text or "")
    if kind_key == "question":
        body = f"{body}\n\n[bold]Yes[/bold]/No"

    with cli_pause_for_user_input() as console:
        if console is None:
            console = Console()
        console.print(
            Panel(
                body,
                title=panel_title,
                border_style=border_style,
                expand=False,
            )
        )

        if kind_key == "question":
            default_yes = bool(
                default and str(default).lower() in ("yes", "ok", "true", "1")
            )
            try:
                from pycompiler_ark.Ui.i18n import is_french_language

                prompt = "Confirmer" if is_french_language(None) else "Confirm"
            except Exception:
                prompt = "Confirm"
            from pycompiler_ark.Ui.Cli.interactive import ask_yes_no

            return ask_yes_no(prompt, default_yes=default_yes)

    return None


def sys_msgbox_for_installing(
    subject: str, explanation: Optional[str] = None, title: str = "Installation requise"
) -> Optional[InstallAuth]:
    """Interactive prompt for multi-OS installation authorization."""
    is_windows = platform.system().lower().startswith("win")
    try:
        from pycompiler_ark.Ui.i18n import is_french_language, tr_fr_en

        if title == "Installation requise":
            title = tr_fr_en(None, "Installation requise", "Installation required")
        is_fr = is_french_language(None)
    except Exception:
        is_fr = True

    if is_fr:
        msg = (
            f"L'installation de '{subject}' nécessite des privilèges administrateur.\n"
            + (f"\n{explanation}\n" if explanation else "")
            + (
                "\nSur Windows, une élévation UAC sera demandée."
                if is_windows
                else "\nSur Linux/macOS, votre mot de passe sudo est requis."
            )
        )
    else:
        msg = (
            f"Installing '{subject}' requires administrator privileges.\n"
            + (f"\n{explanation}\n" if explanation else "")
            + (
                "\nOn Windows, a UAC elevation will be requested."
                if is_windows
                else "\nOn Linux/macOS, your sudo password is required."
            )
        )
    if QApplication.instance() is not None and not _use_rich_dialogs():
        try:
            parent = _qt_active_parent()
            proceed = show_msgbox("question", title, msg, default="Yes")
            if not proceed:
                return None
            if is_windows:
                return InstallAuth("uac", None)
            pwd, ok = QInputDialog.getText(
                parent,
                title,
                (
                    "Entrez votre mot de passe (sudo):"
                    if is_fr
                    else "Enter your password (sudo):"
                ),
                QLineEdit.Password,
            )
            if not ok:
                return None
            pwd = str(pwd)
            return InstallAuth("sudo", pwd) if pwd else None
        except Exception:
            pass
    try:
        try:
            from pycompiler_ark.Ui.i18n import log_with_level

            log_with_level(None, "info", f"[INSTALL] {title}: {msg}")
        except Exception:
            pass
        ans = (
            input("Continuer ? [y/N] " if is_fr else "Continue? [y/N] ").strip().lower()
        )
        if ans not in ("y", "yes", "o", "oui"):
            return None
    except Exception:
        pass
    if is_windows:
        return InstallAuth("uac", None)
    try:
        pwd = getpass.getpass("Mot de passe (sudo): " if is_fr else "Password (sudo): ")
        return InstallAuth("sudo", pwd) if pwd else None
    except Exception:
        return None


class ProgressDialog(QDialog):
    """Progress dialog tightly integrated with application."""

    def __init__(
        self,
        title="Progression",
        parent=None,
        cancelable=False,
        closeable=False,
        cancel_text="Annuler",
        close_text="Fermer",
    ):
        super().__init__(parent or _qt_active_parent())
        self.setWindowTitle(title)
        self.setModal(False)
        self.setMinimumWidth(400)
        self._canceled = False
        self.btn_cancel = None
        self.btn_close = None

        layout = QVBoxLayout(self)
        self.label = QLabel("Préparation...", self)
        self.progress = QProgressBar(self)
        self.progress.setRange(0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.progress)

        if cancelable or closeable:
            btn_row = QHBoxLayout()
            btn_row.addStretch(1)
            if cancelable:
                self.btn_cancel = QPushButton(cancel_text, self)
                self.btn_cancel.clicked.connect(self._on_cancel)
                btn_row.addWidget(self.btn_cancel)
            if closeable:
                self.btn_close = QPushButton(close_text, self)
                self.btn_close.setEnabled(False)
                self.btn_close.clicked.connect(self.close)
                btn_row.addWidget(self.btn_close)
            layout.addLayout(btn_row)

        self.setLayout(layout)

    def set_message(self, msg):
        def _set():
            self.label.setText(msg)
            QApplication.processEvents()

        _invoke_in_main_thread(_set)

    def set_status(self, msg):
        self.set_message(msg)

    def set_progress(self, value, maximum=None):
        def _set():
            if maximum is not None:
                self.progress.setMaximum(maximum)
            self.progress.setValue(value)
            QApplication.processEvents()

        _invoke_in_main_thread(_set)

    def show(self):
        def _show():
            super(ProgressDialog, self).show()

        _invoke_in_main_thread(_show)

    def close(self):
        def _close():
            try:
                super(ProgressDialog, self).close()
            except Exception:
                pass

        _invoke_in_main_thread(_close)

    def _on_cancel(self):
        self._canceled = True
        try:
            self.close()
        except Exception:
            pass

    def is_canceled(self):
        return self._canceled


class CompilationProcessDialog(ProgressDialog):
    """Dialog integrated with application to display workspace loading."""

    def __init__(self, title="Chargement", parent=None):
        super().__init__(title=title, parent=parent, cancelable=True, closeable=True)
        self.setMinimumHeight(150)


_app_main_window = None


def connect_to_app(main_window):
    """Connect dialogs to the main application window for theme synchronization."""
    global _app_main_window
    _app_main_window = main_window
    try:
        app = QApplication.instance()
        if app and hasattr(main_window, "styleSheet"):
            pass
    except Exception:
        pass
