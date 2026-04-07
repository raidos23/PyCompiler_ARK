# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Fallback CLI implementation used when Click is unavailable."""

import os
import sys

from .contracts import (
    EXIT_OK,
    EXIT_RUNTIME_ERROR,
    EXIT_USAGE_ERROR,
    first_positional,
    normalize_path,
)
from .dedicated import run_dedicated_cli
from .headless_commands import (
    run_check,
    run_config_auto,
    run_init,
    run_workspace_apply,
)
from .lazy_ops import (
    available_engine_ids,
    launch_bcasl_gui,
    launch_engines_gui,
    launch_main_gui,
    unload_all_engines,
)
from .output import error, info, plain
from .system_info import print_system_info

USAGE = """
PyCompiler ARK — CLI fallback mode (without click)

Usage:
    python -m pycompiler_ark                    # Launch main application (IDE by default)
    python -m pycompiler_ark --help             # Show help
    python -m pycompiler_ark --version          # Show version
    python -m pycompiler_ark --cli              # Open dedicated interactive CLI
    python -m pycompiler_ark --ide-gui          # Launch IDE-like main GUI
    python -m pycompiler_ark --classic-gui      # Launch classic main GUI
    python -m pycompiler_ark --verbose          # Enable verbose logging
    python -m pycompiler_ark --no-splash        # Disable splash screen
    python -m pycompiler_ark bcasl              # Launch BCASL standalone
    python -m pycompiler_ark bcasl /path/to/ws  # Launch BCASL with workspace
    python -m pycompiler_ark engines            # Launch Engines standalone GUI
    python -m pycompiler_ark engines --dry-run  # List available engines
    python -m pycompiler_ark unload             # Unload all engines
    python -m pycompiler_ark check [workspace]  # CI/CD strict checks
    python -m pycompiler_ark init [workspace]   # Init workspace config
    python -m pycompiler_ark config-auto [workspace]  # Auto configure workspace
    python -m pycompiler_ark ws apply [workspace]     # Full workspace apply workflow
"""


def _run_unload() -> int:
    """Unload all engines and return a standardized exit code."""
    result = unload_all_engines()
    if result["status"] == "success":
        info(str(result["message"]))
        unloaded = list(result.get("unloaded", []))
        if unloaded:
            plain("  Unloaded engines:")
            for eid in unloaded:
                plain(f"    - {eid}")
        return EXIT_OK
    error(str(result["message"]))
    return EXIT_RUNTIME_ERROR


def _run_engines(args: list[str]) -> int:
    """Handle the legacy `engines` fallback command path."""
    if any(flag in args for flag in ("--list-engines", "-l", "--dry-run", "-d")):
        engines = available_engine_ids()
        plain(f"Available engines ({len(engines)}):")
        for eid in engines:
            plain(f"  - {eid}")
        return EXIT_OK
    workspace = normalize_path(first_positional(args))
    return launch_engines_gui(workspace)


def run(argv: list[str] | None, app_version: str) -> int:
    """Execute the fallback CLI entrypoint and return a process exit code."""
    args = list(argv or sys.argv[1:])
    no_splash = False
    ide_gui = False
    classic_gui = False

    # Pré-traitement des options globales avant dispatch de commande.
    if "--verbose" in args:
        os.environ["PYCOMPILER_VERBOSE"] = "1"
        args = [a for a in args if a != "--verbose"]
    if "--no-splash" in args:
        no_splash = True
        args = [a for a in args if a != "--no-splash"]
    if "--ide-gui" in args:
        ide_gui = True
        args = [a for a in args if a != "--ide-gui"]
    if "--classic-gui" in args:
        classic_gui = True
        args = [a for a in args if a != "--classic-gui"]
    # `--cli` bascule vers le shell dédié uniquement s'il n'y a pas d'autre commande.
    if "--cli" in args:
        args = [a for a in args if a != "--cli"]
        if not args:
            return run_dedicated_cli(app_version)

    # Sans sous-commande explicite, on garde le comportement historique: ouvrir la GUI principale.
    if not args:
        return launch_main_gui(
            no_splash=no_splash,
            ide_gui=ide_gui,
            classic_gui=classic_gui,
        )

    # Split commande + reste des arguments.
    cmd = args[0]
    rest = args[1:]

    # Dispatch centralisé des commandes fallback.
    if cmd in ("--help", "-h", "help"):
        plain(USAGE)
        return EXIT_OK
    if cmd in ("--version", "-v", "version"):
        info(f"PyCompiler ARK v{app_version}")
        return EXIT_OK
    if cmd == "--info":
        print_system_info(app_version)
        return EXIT_OK
    if cmd in ("--unload", "unload"):
        return _run_unload()
    if cmd == "bcasl":
        return launch_bcasl_gui(normalize_path(first_positional(rest)))
    if cmd == "engines":
        return _run_engines(rest)
    if cmd == "check":
        return run_check(rest)
    if cmd == "init":
        return run_init(rest)
    if cmd in ("config-auto", "cfg-auto"):
        return run_config_auto(rest)
    if cmd == "workspace":
        if not rest:
            error("Usage: workspace <apply|select> [workspace]")
            return EXIT_USAGE_ERROR
        sub = rest[0]
        if sub in ("apply", "select"):
            return run_workspace_apply(rest[1:])
        error(f"Unknown workspace subcommand: {sub}")
        return EXIT_USAGE_ERROR
    # Alias workspace: garde les habitudes courtes (`ws ...`) en fallback.
    if cmd == "ws":
        if not rest:
            error("Usage: ws <init|config-auto|cfg-auto|apply|select> [workspace]")
            return EXIT_USAGE_ERROR
        ws_cmd = rest[0]
        ws_args = rest[1:]
        if ws_cmd == "init":
            return run_init(ws_args)
        if ws_cmd in ("config-auto", "cfg-auto"):
            return run_config_auto(ws_args)
        if ws_cmd in ("apply", "select"):
            return run_workspace_apply(ws_args)
        error(f"Unknown ws subcommand: {ws_cmd}")
        return EXIT_USAGE_ERROR

    error(f"Unknown command: {cmd}")
    plain(USAGE)
    return EXIT_USAGE_ERROR
