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
from typing import Optional

try:
    from rich.console import Console  # type: ignore
    from rich.theme import Theme
except Exception:  # pragma: no cover
    Console = None
    Theme = None

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


def log(level: str, message: str | tuple, err: bool | None = None, gui: object | None = None) -> None:
    """Emit a log line.

    `message` may be a plain string or a (fr, en) tuple. When a tuple is
    provided and a GUI is available, attempt translation via `pycompiler_ark.Ui.i18n.tr`.
    """
    lvl = level.upper().strip()

    # Map level to theme styles
    style_map = {
        "INFO": "info",
        "WARN": "warning",
        "WARNING": "warning",
        "ERROR": "error",
        "SUCCESS": "success",
    }

    style = style_map.get(lvl, "info")
    prefix = f"[prefix][{lvl}][/prefix]"

    # Support optional translation: message can be (fr, en)
    try:
        if isinstance(message, (tuple, list)) and len(message) >= 2:
            fr = str(message[0])
            en = str(message[1])
            try:
                from pycompiler_ark.Ui.i18n import tr

                message = tr(gui, fr, en)
            except Exception:
                message = en
        else:
            message = str(message)
    except Exception:
        try:
            message = str(message)
        except Exception:
            message = ""

    out_err = err if err is not None else lvl in ("ERROR", "WARN", "WARNING")
    _emit(f"{prefix} {message}", err=out_err, style=style)


def info(message: str | tuple, gui: object | None = None) -> None:
    log("INFO", message, err=False, gui=gui)


def warn(message: str | tuple, gui: object | None = None) -> None:
    log("WARN", message, err=True, gui=gui)


def error(message: str | tuple, gui: object | None = None) -> None:
    log("ERROR", message, err=True, gui=gui)


def success(message: str | tuple, gui: object | None = None) -> None:
    log("SUCCESS", message, err=False, gui=gui)
