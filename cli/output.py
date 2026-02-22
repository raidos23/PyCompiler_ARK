# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys

try:
    import click  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    click = None


def _emit(message: str, err: bool = False) -> None:
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
    _emit(f"{prefix} {message}", err=out_err)


def info(message: str) -> None:
    log("INFO", message, err=False)


def warn(message: str) -> None:
    log("WARN", message, err=True)


def error(message: str) -> None:
    log("ERROR", message, err=True)
