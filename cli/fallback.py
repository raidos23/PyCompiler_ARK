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
from .headless_ops import (
    ci_smoke_payload,
    emit_json,
    workspace_config_auto_payload,
    workspace_init_payload,
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
    python -m pycompiler_ark check [workspace]  # CI/CD strict checks
    python -m pycompiler_ark init [workspace]   # Init workspace config
    python -m pycompiler_ark config-auto [workspace]  # Auto configure workspace
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
        if args[0] == "check":
            workspace = args[1] if len(args) > 1 and not args[1].startswith("-") else None
            as_json = "--json" in args
            require_entrypoint = "--no-require-entrypoint" not in args
            fail_only = "--all-checks" not in args
            strict = "--no-strict" not in args
            payload = ci_smoke_payload(
                workspace=workspace,
                require_entrypoint=require_entrypoint,
            )
            checks = list(payload.get("checks", []))
            if as_json:
                text = emit_json(payload)
                plain(text)
            else:
                plain("PyCompiler ARK Check")
                shown = 0
                for check in checks:
                    ok = bool(check.get("ok"))
                    if fail_only and ok:
                        continue
                    status = "OK" if ok else "FAIL"
                    plain(f"  [{status}] {check.get('name')}: {check.get('message') or ''}")
                    shown += 1
                if fail_only and shown == 0:
                    plain("  [OK] no failing checks")
            if strict and not payload.get("ok"):
                return 3
            return 0
        if args[0] == "init":
            workspace = args[1] if len(args) > 1 and not args[1].startswith("-") else "."
            as_json = "--json" in args
            with_venv = "--with-venv" in args
            payload = workspace_init_payload(workspace, with_venv=with_venv)
            if as_json:
                plain(emit_json(payload))
            else:
                for item in payload.get("steps", []):
                    status = str(item.get("status", "")).upper() or "INFO"
                    plain(f"[{status}] {item.get('message')}")
                if not payload.get("ok"):
                    error(str(payload.get("error", "Workspace init failed")))
                    return 4
                plain(f"Workspace: {payload.get('workspace')}")
                plain(f"  Config: {payload.get('config_path')}")
                plain(f"  BCASL: {payload.get('bcasl_path') or '(not created)'}")
                plain(
                    f"  Pref: {payload.get('workspace_pref_path') or '(not created)'}"
                )
                plain(
                    "  Created workspace: "
                    + ("yes" if payload.get("created_workspace") else "no")
                )
                plain(
                    "  Created config: "
                    + ("yes" if payload.get("created_config") else "no")
                )
                plain(
                    "  Created bcasl.yml: "
                    + ("yes" if payload.get("created_bcasl_config") else "no")
                )
                plain(
                    "  Created workspace pref: "
                    + ("yes" if payload.get("created_workspace_pref") else "no")
                )
                if payload.get("with_venv"):
                    plain(f"  Venv: {payload.get('venv_path') or '(not created)'}")
                    plain(
                        "  Created venv: "
                        + ("yes" if payload.get("created_venv") else "no")
                    )
            return 0 if payload.get("ok") else 4
        if args[0] in ("config-auto", "cfg-auto"):
            workspace = args[1] if len(args) > 1 and not args[1].startswith("-") else "."
            as_json = "--json" in args
            entrypoint = None
            if "--entrypoint" in args:
                idx = args.index("--entrypoint")
                if idx + 1 < len(args):
                    entrypoint = args[idx + 1]
            payload = workspace_config_auto_payload(workspace, entrypoint=entrypoint)
            if as_json:
                plain(emit_json(payload))
            else:
                if not payload.get("ok"):
                    error(str(payload.get("error", "Workspace auto-config failed")))
                    return 4
                plain(f"Workspace: {payload.get('workspace')}")
                plain(f"  Entrypoint: {payload.get('entrypoint') or '(none)'}")
                plain(
                    "  Requirements found: "
                    + (
                        ", ".join(payload.get("requirements_files_found", []))
                        or "none"
                    )
                )
                plain(f"  Config updated: {payload.get('config_path')}")
            return 0 if payload.get("ok") else 4
        if args[0] == "ws":
            if len(args) < 2:
                error("Usage: ws <init|config-auto|cfg-auto> [workspace]")
                return 2
            sub = args[1]
            rest = args[2:]
            if sub == "init":
                ws_args = ["init"] + rest
                return run(ws_args, app_version)
            if sub in ("config-auto", "cfg-auto"):
                ws_args = ["config-auto"] + rest
                return run(ws_args, app_version)
            error(f"Unknown ws subcommand: {sub}")
            return 2

        error(f"Unknown command: {args[0]}")
        plain(USAGE)
        return 1

    return launch_main_gui(
        no_splash=no_splash, ide_gui=ide_gui, classic_gui=classic_gui
    )
