# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import os
import sys

from .contracts import (
    EXIT_OK,
    EXIT_PRECHECK_FAILED,
    EXIT_RUNTIME_ERROR,
    EXIT_USAGE_ERROR,
    EXIT_WORKSPACE_INVALID,
    first_positional,
    normalize_path,
    render_checks_text,
    render_workspace_init_result,
)
from .dedicated import run_dedicated_cli
from .headless_ops import (
    ci_smoke_payload,
    emit_json,
    workspace_config_auto_payload,
    workspace_init_payload,
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
"""


def _extract_option_value(args: list[str], option: str) -> tuple[str | None, list[str]]:
    clean: list[str] = []
    value: str | None = None
    i = 0
    while i < len(args):
        token = args[i]
        if token == option:
            if i + 1 >= len(args):
                raise ValueError(f"Missing value after {option}")
            value = args[i + 1]
            i += 2
            continue
        clean.append(token)
        i += 1
    return value, clean


def _run_unload() -> int:
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
    if any(flag in args for flag in ("--list-engines", "-l", "--dry-run", "-d")):
        engines = available_engine_ids()
        plain(f"Available engines ({len(engines)}):")
        for eid in engines:
            plain(f"  - {eid}")
        return EXIT_OK
    workspace = normalize_path(first_positional(args))
    return launch_engines_gui(workspace)


def _run_check(args: list[str]) -> int:
    workspace = normalize_path(first_positional(args))
    as_json = "--json" in args
    require_entrypoint = "--no-require-entrypoint" not in args
    fail_only = "--all-checks" not in args
    strict = "--no-strict" not in args
    payload = ci_smoke_payload(
        workspace=workspace,
        require_entrypoint=require_entrypoint,
    )
    if as_json:
        plain(emit_json(payload))
    else:
        render_checks_text(
            "PyCompiler ARK Check",
            list(payload.get("checks", [])),
            fail_only=fail_only,
        )
    if strict and not payload.get("ok"):
        return EXIT_PRECHECK_FAILED
    return EXIT_OK


def _run_init(args: list[str]) -> int:
    as_json = "--json" in args
    with_venv = "--with-venv" in args
    workspace = normalize_path(first_positional([a for a in args if not a.startswith("-")])) or "."
    payload = workspace_init_payload(workspace, with_venv=with_venv)
    if as_json:
        plain(emit_json(payload))
    else:
        for item in payload.get("steps", []):
            status = str(item.get("status", "")).upper() or "INFO"
            plain(f"[{status}] {item.get('message')}")
        if payload.get("ok"):
            render_workspace_init_result(payload)
    if not payload.get("ok"):
        error(str(payload.get("error", "Workspace init failed")))
        return EXIT_WORKSPACE_INVALID
    return EXIT_OK


def _run_config_auto(args: list[str]) -> int:
    as_json = "--json" in args
    try:
        entrypoint, clean_args = _extract_option_value(args, "--entrypoint")
    except ValueError as exc:
        error(str(exc))
        return EXIT_USAGE_ERROR
    workspace = normalize_path(first_positional([a for a in clean_args if not a.startswith("-")])) or "."
    payload = workspace_config_auto_payload(workspace, entrypoint=entrypoint)
    if as_json:
        plain(emit_json(payload))
    else:
        if payload.get("ok"):
            plain(f"Workspace: {payload.get('workspace')}")
            plain(f"  Entrypoint: {payload.get('entrypoint') or '(none)'}")
            plain(
                "  Requirements found: "
                + (", ".join(payload.get("requirements_files_found", [])) or "none")
            )
            plain(f"  Config updated: {payload.get('config_path')}")
    if not payload.get("ok"):
        error(str(payload.get("error", "Workspace auto-config failed")))
        return EXIT_WORKSPACE_INVALID
    return EXIT_OK


def run(argv: list[str] | None, app_version: str) -> int:
    args = list(argv or sys.argv[1:])
    no_splash = False
    ide_gui = False
    classic_gui = False

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
    if "--cli" in args:
        args = [a for a in args if a != "--cli"]
        if not args:
            return run_dedicated_cli(app_version)

    if not args:
        return launch_main_gui(
            no_splash=no_splash,
            ide_gui=ide_gui,
            classic_gui=classic_gui,
        )

    cmd = args[0]
    rest = args[1:]

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
        return _run_check(rest)
    if cmd == "init":
        return _run_init(rest)
    if cmd in ("config-auto", "cfg-auto"):
        return _run_config_auto(rest)
    if cmd == "ws":
        if not rest:
            error("Usage: ws <init|config-auto|cfg-auto> [workspace]")
            return EXIT_USAGE_ERROR
        ws_cmd = rest[0]
        ws_args = rest[1:]
        if ws_cmd == "init":
            return _run_init(ws_args)
        if ws_cmd in ("config-auto", "cfg-auto"):
            return _run_config_auto(ws_args)
        error(f"Unknown ws subcommand: {ws_cmd}")
        return EXIT_USAGE_ERROR

    error(f"Unknown command: {cmd}")
    plain(USAGE)
    return EXIT_USAGE_ERROR
