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

from __future__ import annotations

import re
import sys
from typing import Any, Callable, Optional

try:
    from rich.console import Console  # type: ignore
    from rich.theme import Theme
except Exception:  # pragma: no cover
    Console = None
    Theme = None
# Import translation once (lazy)
try:
    from .i18n import tr
except Exception:
    tr = None
try:
    import click  # type: ignore
except ImportError:
    click = None

_THEME = (
    Theme(
        {
            "info": "cyan",
            "warning": "bold yellow",
            "error": "bold red",
            "success": "bold green",
            "prefix": "bold",
        }
    )
    if Theme is not None
    else None
)

_CONSOLE = Console(theme=_THEME) if Console is not None else None
_CONSOLE_ERR = (
    Console(stderr=True, theme=_THEME) if Console is not None else None
)

# Common emojis to strip for a cleaner CLI look
_EMOJI_RE = re.compile(
    r"[\U0001f000-\U0001f9ff]|[\U00002600-\U000026ff]|[\U00002700-\U000027bf]",
    re.UNICODE,
)

_LOG_COLORS = {
    "info": "#00aaff",
    "warning": "#ffaa00",
    "error": "#ff4444",
    "success": "#00cc66",
}

# Global widget cache
_log_widget = None


def strip_emojis(text: str) -> str:
    """Remove emojis from a string for cleaner terminal output."""
    return _EMOJI_RE.sub("", text).strip()


def get_console() -> Optional[Console]:
    return _CONSOLE


def _emit(message: str, err: bool = False, style: str | None = None) -> None:
    # Always strip emojis in CLI mode for a modern look
    clean_message = strip_emojis(message)

    if _CONSOLE is not None:
        console = _CONSOLE_ERR if err else _CONSOLE
        # Use markup=True to support Rich tags in log messages if provided
        console.print(clean_message, style=style, markup=True)
        return

    if click is not None:
        click.echo(clean_message, err=err)
        return

    stream = sys.stderr if err else sys.stdout
    print(clean_message, file=stream)


def plain(message: str, err: bool = False) -> None:
    _emit(message, err=err)


def get_log_widget():
    global _log_widget
    if _log_widget is not None:
        return _log_widget

    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            for window in app.topLevelWidgets():
                if hasattr(window, "log") and window.log is not None:
                    _log_widget = window.log
                    return _log_widget
    except Exception:
        pass
    return None


def _is_on_gui_thread() -> bool:
    """Return True when there is no Qt app, or we are on the app's thread."""
    try:
        from PySide6.QtCore import QThread
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return True
        return QThread.currentThread() == app.thread()
    except Exception:
        return True


def _append_html_to_widget(widget: Any, html: str, plain_text: str) -> None:
    """Mutate the log widget. Must only run on the Qt GUI thread."""
    try:
        from PySide6.QtGui import QTextCursor

        widget.moveCursor(QTextCursor.MoveOperation.End)
        widget.insertHtml(html)
        widget.ensureCursorVisible()
    except Exception:
        try:
            widget.append(plain_text)
        except Exception:
            pass


def _post_to_gui_thread(fn: Callable[[], None]) -> bool:
    """Queue *fn* on the Qt GUI thread. Returns False if posting is impossible."""
    try:
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            return False
        # Context=app → functor runs on the application (GUI) thread.
        QTimer.singleShot(0, app, fn)
        return True
    except Exception:
        return False


def _safe_append_to_widget(widget: Any, html: str, plain_text: str) -> None:
    """Append to a Qt log widget from any thread without segfaulting."""
    if widget is None:
        return

    # Bridge / non-QTextEdit objects expose a thread-safe append via signals.
    try:
        from PySide6.QtWidgets import QTextEdit

        if not isinstance(widget, QTextEdit):
            if callable(getattr(widget, "append", None)):
                widget.append(plain_text)
            return
    except Exception:
        # Qt unavailable: best-effort append
        try:
            if callable(getattr(widget, "append", None)):
                widget.append(plain_text)
        except Exception:
            pass
        return

    if _is_on_gui_thread():
        _append_html_to_widget(widget, html, plain_text)
        return

    # Off GUI thread: never touch QTextEdit directly (segfault).
    posted = _post_to_gui_thread(
        lambda w=widget, h=html, p=plain_text: _append_html_to_widget(w, h, p)
    )
    if not posted:
        # No event loop / posting failed — skip widget; console _emit still runs.
        return


def _try_bridge_log(gui: object | None, level: str, message: str) -> bool:
    """Route through SafeGuiBridge-style API when available (already thread-safe)."""
    if gui is None:
        return False
    log_message_level = getattr(gui, "log_message_level", None)
    if not callable(log_message_level):
        return False
    try:
        # Message is already translated; pass twice for (fr, en).
        log_message_level(level, message, message)
        return True
    except Exception:
        return False


def log(
    level: str,
    message: str | tuple | list | Any,
    err: bool | None = None,
    gui: object | None = None,
) -> None:
    """Main log with automatic append (thread-safe for GUI widget)."""

    lvl = level.upper().strip()

    style_map = {
        "INFO": "info",
        "WARN": "warning",
        "WARNING": "warning",
        "ERROR": "error",
        "SUCCESS": "success",
    }

    style = style_map.get(lvl, "info")
    prefix = f"[{lvl}]"

    # Translation (fr, en) — works with or without gui (CLI uses prefs/system lang)
    if isinstance(message, (tuple, list)) and len(message) >= 2:
        fr, en = str(message[0]), str(message[1])
        if tr is not None:
            try:
                message = tr(gui, fr, en)
            except Exception:
                message = en
        else:
            message = en
    else:
        message = str(message)

    out_err = err if err is not None else lvl in ("ERROR", "WARN", "WARNING")
    plain_line = f"{prefix} {message}"

    # Prefer SafeGuiBridge (signals) when the caller passes one — avoids
    # touching QTextEdit from a worker thread and prevents double-writes.
    bridged = _try_bridge_log(gui, style, str(message))

    if not bridged:
        widget = get_log_widget()
        if widget is None and gui is not None and hasattr(gui, "log"):
            widget = gui.log

        if widget is not None:
            color = _LOG_COLORS.get(style, "#ffffff")
            html = f'<span style="color:{color};">{plain_line}</span><br>'
            _safe_append_to_widget(widget, html, plain_line)

    # Safe call to _emit (without exc_info)
    try:
        _emit(plain_line, err=out_err, style=style)
    except TypeError:
        # If _emit has another signature
        try:
            _emit(plain_line, err=out_err)
        except Exception:
            pass  # last resort


def info(message: str | tuple | list | Any, gui: object | None = None):
    log("INFO", message, err=False, gui=gui)


def warn(message: str | tuple | list | Any, gui: object | None = None):
    log("WARN", message, err=True, gui=gui)


def error(message: str | tuple | list | Any, gui: object | None = None):
    log("ERROR", message, err=True, gui=gui)


def success(message: str | tuple | list | Any, gui: object | None = None):
    log("SUCCESS", message, err=False, gui=gui)
