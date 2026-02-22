# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys

try:
    import click  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    click = None


def echo(message: str, err: bool = False) -> None:
    if click is not None:
        click.echo(message, err=err)
        return
    stream = sys.stderr if err else sys.stdout
    print(message, file=stream)
