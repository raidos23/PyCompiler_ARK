# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys

try:
    from rich.console import Console  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Console = None

try:
    import click  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    click = None

_CONSOLE = Console() if Console is not None else None
_CONSOLE_ERR = Console(stderr=True) if Console is not None else None


def _emit(message: str, err: bool = False, style: str | None = None) -> None:
    if _CONSOLE is not None:
        console = _CONSOLE_ERR if err else _CONSOLE
        console.print(message, style=style, markup=False)
        return
    if click is not None:
        click.echo(message, err=err)
        return
    stream = sys.stderr if err else sys.stdout
    print(message, file=stream)


def plain(message: str, err: bool = False) -> None:
    _emit(message, err=err)


def log(level: str, message: str, err: bool | None = None) -> None:
    lvl = level.upper().strip()
    prefix = f"[{lvl}]"
    out_err = err if err is not None else lvl in ("ERROR", "WARN", "WARNING")
    style = {
        "INFO": "cyan",
        "WARN": "yellow",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "SUCCESS": "bold green",
    }.get(lvl)
    _emit(f"{prefix} {message}", err=out_err, style=style)


def info(message: str) -> None:
    log("INFO", message, err=False)


def warn(message: str) -> None:
    log("WARN", message, err=True)


def error(message: str) -> None:
    log("ERROR", message, err=True)


def success(message: str) -> None:
    log("SUCCESS", message, err=False)
