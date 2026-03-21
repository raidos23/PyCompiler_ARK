# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

from .lazy_ops import (
    available_engine_ids,
    launch_bcasl_gui,
    launch_engines_gui,
    launch_main_gui,
    unload_all_engines,
)
from .dedicated import run_dedicated_cli
from .output import error, info, plain, warn
from .system_info import print_system_info

USAGE = """
PyCompiler ARK — Cross-platform hardened bootstrap with Intelligent CLI Entry Point

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
    python -m pycompiler_ark engines /path/to/ws  # Launch Engines with workspace
    python -m pycompiler_ark engines --dry-run  # List available engines
    python -m pycompiler_ark unload             # Unload all engines
"""


def _maybe_workspace(args: Iterable[str]) -> Optional[str]:
    for arg in args:
        if not arg.startswith("-"):
            return arg
    return None


def run(argv: Optional[list[str]], app_version: str) -> int:
    args = list(argv or sys.argv[1:])
    no_splash = False
    ide_gui = False
    classic_gui = False

    if "--verbose" in args:
        import os

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

    if "--cli" in args:
        args = [a for a in args if a != "--cli"]
        if not args:
            return run_dedicated_cli(app_version)

    if args:
        if args[0] in ("--help", "-h", "help"):
            plain(USAGE)
            return 0
        if args[0] in ("--version", "-v", "version"):
            info(f"PyCompiler ARK v{app_version}")
            return 0
        if args[0] == "--info":
            print_system_info(app_version)
            return 0
        if args[0] == "--unload":
            result = unload_all_engines()
            if result["status"] == "success":
                info(f"{result['message']}")
                if result["unloaded"]:
                    plain("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        plain(f"    • {eid}")
            else:
                error(f"{result['message']}")
            return 0 if result["status"] == "success" else 1
        if args[0] == "bcasl":
            workspace_dir = args[1] if len(args) > 1 else None
            return launch_bcasl_gui(workspace_dir)
        if args[0] == "engines":
            sub_args = args[1:]
            if (
                "--list-engines" in sub_args
                or "-l" in sub_args
                or "--dry-run" in sub_args
                or "-d" in sub_args
            ):
                engines = available_engine_ids()
                plain(f"Available engines ({len(engines)}):")
                for eid in engines:
                    plain(f"  - {eid}")
                return 0

            workspace_dir = _maybe_workspace(sub_args)
            return launch_engines_gui(workspace_dir)
        if args[0] == "unload":
            result = unload_all_engines()
            if result["status"] == "success":
                info(f"{result['message']}")
                if result["unloaded"]:
                    plain("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        plain(f"    • {eid}")
            else:
                error(f"{result['message']}")
            return 0 if result["status"] == "success" else 1

        error(f"Unknown command: {args[0]}")
        plain(USAGE)
        return 1

    return launch_main_gui(
        no_splash=no_splash, ide_gui=ide_gui, classic_gui=classic_gui
    )
