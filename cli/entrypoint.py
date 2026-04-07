# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Primary CLI entrypoint with automatic Click/fallback selection."""

import sys
from pathlib import Path

from .click_app import build_cli, has_click, click as click_module
from .fallback import run as run_fallback
from .runtime import install_runtime, handle_fatal, should_enable_qt


def _resolve_app_version() -> str:
    """Resolve application version from ``Core/__init__.py``."""
    try:
        # Lecture directe de la version côté Core pour éviter une dépendance circulaire.
        root = Path(__file__).resolve().parents[1]
        core_init = root / "Core" / "__init__.py"
        for line in core_init.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("__version__"):
                _, value = stripped.split("=", 1)
                return value.strip().strip("\"'")
    except Exception:
        pass
    return "unknown"


def main(argv: list[str] | None = None) -> int:
    """Run the CLI entrypoint and return a shell-compatible exit code."""
    app_version = _resolve_app_version()
    args = list(argv) if argv is not None else list(sys.argv[1:])
    # Activation du verbose le plus tôt possible pour couvrir les logs bootstrap.
    if args and "--verbose" in args:
        import os

        os.environ["PYCOMPILER_VERBOSE"] = "1"
    # Initialisation runtime commune avant le parsing de commandes.
    install_runtime(app_version, enable_qt=should_enable_qt(args))

    # Chemin principal: Click; chemin de secours: parser fallback.
    if has_click():
        try:
            # `standalone_mode=False` permet de récupérer les codes de retour proprement.
            cli = build_cli(app_version)
            result = cli.main(args=args, prog_name="pycompiler_ark", standalone_mode=False)
            return int(result) if isinstance(result, int) else 0
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 0
        except Exception as exc:
            if click_module is not None and isinstance(
                exc, click_module.exceptions.ClickException
            ):
                try:
                    exc.show()
                except Exception:
                    pass
                return int(getattr(exc, "exit_code", 2))
            handle_fatal(sys.exc_info())
            return 1

    return run_fallback(args, app_version)
