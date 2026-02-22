# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, Optional

from EngineLoader import unload_all

from .launchers import launch_bcasl_standalone, launch_engines_only_standalone, launch_main_application
from .output import echo
from .system_info import print_system_info


USAGE = """
PyCompiler ARK — Cross-platform hardened bootstrap with Intelligent CLI Entry Point

Usage:
    python -m pycompiler_ark                    # Launch main application
    python -m pycompiler_ark --help             # Show help
    python -m pycompiler_ark --version          # Show version
    python -m pycompiler_ark bcasl              # Launch BCASL standalone
    python -m pycompiler_ark bcasl /path/to/ws  # Launch BCASL with workspace
    python -m pycompiler_ark engines            # Launch Engines standalone GUI
    python -m pycompiler_ark engines /path/to/ws  # Launch Engines with workspace
    python -m pycompiler_ark engines --dry-run  # List available engines
    python -m pycompiler_ark --completion bash  # Generate bash completion
    python -m pycompiler_ark unload             # Unload all engines
"""


def _maybe_workspace(args: Iterable[str]) -> Optional[str]:
    for arg in args:
        if not arg.startswith("-"):
            return arg
    return None


def run(argv: Optional[list[str]], app_version: str) -> int:
    args = list(argv or sys.argv[1:])

    if args:
        if args[0] in ("--help", "-h", "help"):
            echo(USAGE)
            return 0
        if args[0] in ("--version", "-v", "version"):
            echo(f"PyCompiler ARK v{app_version}")
            return 0
        if args[0] == "--info":
            print_system_info(app_version)
            return 0
        if args[0] == "--unload":
            result = unload_all()
            if result["status"] == "success":
                echo(f"{result['message']}")
                if result["unloaded"]:
                    echo("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        echo(f"    • {eid}")
            else:
                echo(f"Error: {result['message']}")
            return 0 if result["status"] == "success" else 1
        if args[0] == "bcasl":
            workspace_dir = args[1] if len(args) > 1 else None
            return launch_bcasl_standalone(workspace_dir)
        if args[0] == "engines":
            sub_args = args[1:]
            if "--list-engines" in sub_args or "-l" in sub_args or "--dry-run" in sub_args or "-d" in sub_args:
                from EngineLoader import available_engines

                engines = available_engines()
                echo(f"Available engines ({len(engines)}):")
                for eid in engines:
                    echo(f"  - {eid}")
                return 0

            workspace_dir = _maybe_workspace(sub_args)
            return launch_engines_only_standalone(workspace_dir)
        if args[0] == "unload":
            result = unload_all()
            if result["status"] == "success":
                echo(f"{result['message']}")
                if result["unloaded"]:
                    echo("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        echo(f"    • {eid}")
            else:
                echo(f"Error: {result['message']}")
            return 0 if result["status"] == "success" else 1

        echo(f"Unknown command: {args[0]}")
        echo(USAGE)
        return 1

    return launch_main_application()
