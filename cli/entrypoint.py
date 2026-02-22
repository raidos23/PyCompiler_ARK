# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys

from Core import __version__ as APP_VERSION

from .click_app import build_cli, has_click
from .fallback import run as run_fallback
from .runtime import install_runtime, handle_fatal


def main(argv: list[str] | None = None) -> int:
    install_runtime(APP_VERSION)

    if has_click():
        try:
            cli = build_cli(APP_VERSION)
            cli.main(args=argv, prog_name="pycompiler_ark", standalone_mode=False)
            return 0
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 0
        except Exception:
            handle_fatal(sys.exc_info())
            return 1

    return run_fallback(argv, APP_VERSION)
