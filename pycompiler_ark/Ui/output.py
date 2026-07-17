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

import sys
import re
from typing import Optional, Any

try:
    from rich.console import Console  # type: ignore
    from rich.theme import Theme
except Exception:  # pragma: no cover
    Console = None
    Theme = None
# Import translation once (lazy)
try:
    from pycompiler_ark.Ui.i18n import tr
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
_CONSOLE_ERR = Console(stderr=True, theme=_THEME) if Console is not None else None

# Common emojis to strip for a cleaner CLI look
_EMOJI_RE = re.compile(
    r"[\U0001f000-\U0001f9ff]|[\U00002600-\U000026ff]|[\U00002700-\U000027bf]",
    re.UNICODE,
)


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


# Global widget cache
_log_widget = None


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


def log(
    level: str,
    message: str | tuple | list | Any,
    err: bool | None = None,
    gui: object | None = None,
) -> None:
    """Log principal avec append automatique"""

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

    # === Append AUTOMATIQUE dans le widget 'log' ===
    widget = get_log_widget()
    if widget is None and gui is not None and hasattr(gui, "log"):
        widget = gui.log

    if widget is not None:
        try:
            from PySide6.QtGui import QTextCursor

            colors = {
                "info": "#00aaff",
                "warning": "#ffaa00",
                "error": "#ff4444",
                "success": "#00cc66",
            }
            color = colors.get(style, "#ffffff")

            html = f'<span style="color:{color};">{prefix} {message}</span><br>'

            widget.moveCursor(QTextCursor.MoveOperation.End)
            widget.insertHtml(html)
            widget.ensureCursorVisible()

        except Exception:
            try:
                widget.append(f"{prefix} {message}")
            except Exception:
                pass

    # Appel sûr à _emit (sans exc_info)
    try:
        _emit(f"{prefix} {message}", err=out_err, style=style)
    except TypeError:
        # Si _emit a une autre signature
        try:
            _emit(f"{prefix} {message}", err=out_err)
        except Exception:
            pass  # dernier recours


def info(message: str | tuple | list | Any, gui: object | None = None):
    log("INFO", message, err=False, gui=gui)


def warn(message: str | tuple | list | Any, gui: object | None = None):
    log("WARN", message, err=True, gui=gui)


def error(message: str | tuple | list | Any, gui: object | None = None):
    log("ERROR", message, err=True, gui=gui)


def success(message: str | tuple | list | Any, gui: object | None = None):
    log("SUCCESS", message, err=False, gui=gui)
