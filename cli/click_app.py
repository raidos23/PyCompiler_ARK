# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path
import sys

from .contracts import (
    EXIT_ENGINE_NOT_FOUND,
    EXIT_PRECHECK_FAILED,
    EXIT_WORKSPACE_INVALID,
    normalize_path,
    render_checks_text,
    render_workspace_init_result,
)
from .dedicated import _run_bcasl_headless, run_dedicated_cli
from .headless_ops import (
    bcasl_doctor_payload,
    bcasl_list_payload,
    ci_smoke_payload,
    doctor_payload,
    emit_json,
    engine_config_path_payload,
    engine_config_show_payload,
    engine_doctor_payload,
    engine_info_payload,
    engine_list_payload,
    scaffold_engine,
    scaffold_plugin,
    workspace_config_auto_payload,
    workspace_init_payload,
    workspace_inspect_payload,
)
from .lazy_ops import (
    available_engine_ids,
    launch_bcasl_gui,
    launch_engines_gui,
    launch_main_gui,
    unload_all_engines,
)
from .output import error, info, plain, success, warn
from .system_info import print_system_info

try:
    import click  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    click = None


def has_click() -> bool:
    return click is not None


def _echo_payload(payload, as_json: bool = False) -> None:
    if as_json:
        text = emit_json(payload)
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()
        return
    if isinstance(payload, str):
        plain(payload)
    else:
        plain(str(payload))


def _emit_and_exit(payload, code: int, as_json: bool = False) -> None:
    _echo_payload(payload, as_json=as_json)
    raise click.exceptions.Exit(code)


def _run_workspace_init_with_progress(workspace_dir: str, with_venv: bool = False):
    try:
        from rich.console import Console  # type: ignore
        from rich.status import Status  # type: ignore
    except Exception:
        Console = None
        Status = None

    if Console is None or Status is None:
        payload = workspace_init_payload(workspace_dir, with_venv=with_venv)
        for item in payload.get("steps", []):
            status = str(item.get("status", "")).upper() or "INFO"
            plain(f"[{status}] {item.get('message')}")
        return payload

    console = Console()
    current = {"text": "Initializing workspace..."}

    def _cb(_step: str, _status: str, message: str) -> None:
        current["text"] = message

    with console.status("[bold cyan]Initializing workspace...", spinner="dots") as status:
        payload = workspace_init_payload(workspace_dir, progress_cb=_cb, with_venv=with_venv)
        try:
            status.update(f"[bold cyan]{current['text']}")
        except Exception:
            pass
    for item in payload.get("steps", []):
        status_txt = str(item.get("status", "")).lower()
        if status_txt == "done":
            prefix = "[OK]"
        elif status_txt == "warning":
            prefix = "[WARN]"
        elif status_txt == "failed":
            prefix = "[FAIL]"
        else:
            prefix = "[INFO]"
        plain(f"{prefix} {item.get('message')}")
    return payload


def _resolve_workspace_path(workspace: str | None) -> str | None:
    return normalize_path(workspace)


def _workspace_init_emit(workspace_dir: str, as_json: bool, with_venv: bool) -> None:
    if as_json:
        payload = workspace_init_payload(workspace_dir, with_venv=with_venv)
        if not payload.get("ok"):
            _emit_and_exit(payload, EXIT_WORKSPACE_INVALID, as_json=True)
        _echo_payload(payload, as_json=True)
        return
    payload = _run_workspace_init_with_progress(workspace_dir, with_venv=with_venv)
    if not payload.get("ok"):
        raise click.ClickException(payload.get("error", "Workspace init failed"))
    render_workspace_init_result(payload)


def _workspace_config_auto_emit(
    workspace_dir: str, entrypoint: str | None, as_json: bool
) -> None:
    payload = workspace_config_auto_payload(workspace_dir, entrypoint=entrypoint)
    if as_json:
        if not payload.get("ok"):
            _emit_and_exit(payload, EXIT_WORKSPACE_INVALID, as_json=True)
        _echo_payload(payload, as_json=True)
        return
    if not payload.get("ok"):
        raise click.ClickException(payload.get("error", "Workspace auto-config failed"))
    plain(f"Workspace: {payload.get('workspace')}")
    plain(f"  Entrypoint: {payload.get('entrypoint') or '(none)'}")
    plain(
        "  Requirements found: "
        + (", ".join(payload.get("requirements_files_found", [])) or "none")
    )
    plain(f"  Config updated: {payload.get('config_path')}")


def _ensure_workspace_exists(workspace_dir: str | None) -> str | None:
    if not workspace_dir:
        return None
    ws_path = Path(workspace_dir)
    if ws_path.exists():
        return str(ws_path)
    warn(f"Warning: Workspace directory does not exist: {workspace_dir}")
    warn("Creating directory...")
    try:
        ws_path.mkdir(parents=True, exist_ok=True)
        info(f"Directory created: {workspace_dir}")
        return str(ws_path)
    except Exception as exc:
        raise click.ClickException(f"Failed to create directory: {exc}")


def build_cli(app_version: str):
    if click is None:
        raise RuntimeError("Click is not available")

    @click.group(
        invoke_without_command=True,
        context_settings=dict(help_option_names=["-h", "--help"]),
    )
    @click.option("--version", is_flag=True, help="Show version information")
    @click.option("--help-all", is_flag=True, help="Show detailed help with examples")
    @click.option("--info", "show_info", is_flag=True, help="Show system information")
    @click.option(
        "--cli", "dedicated_cli", is_flag=True, help="Open dedicated interactive CLI"
    )
    @click.option("--verbose", is_flag=True, help="Enable verbose logging")
    @click.option("--no-splash", is_flag=True, help="Disable splash screen")
    @click.option(
        "--ide-gui",
        "ide_gui",
        is_flag=True,
        help="Launch the new IDE-like main GUI layout",
    )
    @click.option(
        "--classic-gui",
        "classic_gui",
        is_flag=True,
        help="Launch the classic main GUI layout",
    )
    @click.option(
        "--unload",
        "unload_engines_flag",
        is_flag=True,
        help="Unload all registered engines before launching the application",
    )
    @click.pass_context
    def cli(
        ctx,
        version,
        help_all,
        show_info,
        dedicated_cli,
        verbose,
        no_splash,
        ide_gui,
        classic_gui,
        unload_engines_flag,
    ):
        """PyCompiler ARK command line interface."""
        ctx.obj = ctx.obj or {}
        ctx.obj["no_splash"] = bool(no_splash)
        ctx.obj["verbose"] = bool(verbose)
        ctx.obj["ide_gui"] = bool(ide_gui)
        ctx.obj["classic_gui"] = bool(classic_gui)

        if verbose:
            import os

            os.environ["PYCOMPILER_VERBOSE"] = "1"

        if version:
            info(f"PyCompiler ARK v{app_version}")
            ctx.exit(0)

        if show_info:
            print_system_info(app_version)
            ctx.exit(0)

        if dedicated_cli and ctx.invoked_subcommand is None:
            ctx.exit(run_dedicated_cli(app_version))

        if unload_engines_flag:
            result = unload_all_engines()
            if result["status"] == "success":
                info(result["message"])
            else:
                error(result["message"])

        if help_all:
            plain(ctx.get_help())
            plain("\nCommand Groups:")
            plain("  gui         Launch graphical interfaces")
            plain("  engine      Inspect and run engines headlessly")
            plain("  bcasl       BCASL plugin actions")
            plain("  workspace   Inspect workspace state")
            plain("  doctor      Global diagnostics")
            plain("  scaffold    Generate starter templates")
            ctx.exit(0)

        if ctx.invoked_subcommand is None:
            ctx.exit(
                launch_main_gui(
                    no_splash=ctx.obj.get("no_splash", False),
                    ide_gui=ctx.obj.get("ide_gui", False),
                    classic_gui=ctx.obj.get("classic_gui", False),
                )
            )

    @cli.group()
    def gui():
        """Launch graphical interfaces."""

    @gui.command("main")
    @click.option("--ide", "ide_gui", is_flag=True, help="Use IDE-like layout")
    @click.option("--classic", "classic_gui", is_flag=True, help="Use classic layout")
    @click.option("--no-splash", is_flag=True, help="Disable splash screen")
    def gui_main(ide_gui, classic_gui, no_splash):
        sys.exit(
            launch_main_gui(
                no_splash=no_splash,
                ide_gui=ide_gui,
                classic_gui=classic_gui,
            )
        )

    @gui.command("bcasl")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    def gui_bcasl(workspace):
        sys.exit(launch_bcasl_gui(_ensure_workspace_exists(_resolve_workspace_path(workspace))))

    @gui.command("engines")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    def gui_engines(workspace):
        sys.exit(launch_engines_gui(_ensure_workspace_exists(_resolve_workspace_path(workspace))))

    @cli.group()
    def engine():
        """Inspect and run compilation engines."""

    @engine.command("list")
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True, help="Emit machine-readable JSON")
    def engine_list(workspace, as_json):
        payload = engine_list_payload(workspace=_resolve_workspace_path(workspace))
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        plain(f"Available engines ({payload['count']}):")
        for eng in payload["engines"]:
            status = "OK" if eng["compatible"] else "FAIL"
            plain(f"  [{status}] {eng['id']} - {eng['name']} v{eng['version']}")

    @engine.command("info")
    @click.argument("engine_id")
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def engine_info(engine_id, workspace, as_json):
        payload = engine_info_payload(engine_id, workspace=_resolve_workspace_path(workspace))
        if as_json:
            if not payload.get("found"):
                _emit_and_exit(payload, EXIT_ENGINE_NOT_FOUND, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        if not payload.get("found"):
            raise click.ClickException(f"Engine not found: {engine_id}")
        eng = payload["engine"]
        plain(f"Engine: {eng['name']}")
        plain(f"  ID: {eng['id']}")
        plain(f"  Version: {eng['version']}")
        plain(f"  Required core: {eng['required_core']}")
        plain(f"  Required SDK: {eng['required_sdk']}")
        plain(f"  Compatible: {'yes' if eng['compatible'] else 'no'}")
        plain(f"  Python tools: {', '.join(eng['required_tools'].get('python', [])) or 'none'}")
        plain(f"  System tools: {', '.join(eng['required_tools'].get('system', [])) or 'none'}")

    @engine.command("compat")
    @click.argument("engine_id")
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when compatibility checks fail")
    def engine_compat(engine_id, workspace, as_json, strict):
        payload = engine_info_payload(engine_id, workspace=_resolve_workspace_path(workspace))
        if as_json:
            if not payload.get("found"):
                _emit_and_exit(payload, EXIT_ENGINE_NOT_FOUND, as_json=True)
            if strict and not payload["engine"]["compatible"]:
                _emit_and_exit(payload, EXIT_PRECHECK_FAILED, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        if not payload.get("found"):
            raise click.ClickException(f"Engine not found: {engine_id}")
        eng = payload["engine"]
        if eng["compatible"]:
            success(f"Engine compatible: {engine_id}")
        else:
            error(f"Engine not compatible: {engine_id}")
            if eng.get("message"):
                warn(f"Reason: {eng['message']}")
            if strict:
                raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @engine.command("doctor")
    @click.argument("engine_id")
    @click.argument("file_path", required=False, type=click.Path(exists=False))
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when doctor checks fail")
    def engine_doctor(engine_id, file_path, workspace, as_json, strict):
        payload = engine_doctor_payload(
            engine_id,
            workspace=_resolve_workspace_path(workspace),
            file_path=_resolve_workspace_path(file_path),
        )
        if as_json:
            if "checks" not in payload:
                _emit_and_exit(payload, EXIT_ENGINE_NOT_FOUND, as_json=True)
            if strict and any(not check["ok"] for check in payload["checks"]):
                _emit_and_exit(payload, EXIT_PRECHECK_FAILED, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        if "checks" not in payload:
            raise click.ClickException(f"Engine not found: {engine_id}")
        plain(f"Doctor for engine: {engine_id}")
        for check in payload["checks"]:
            status = "OK" if check["ok"] else "FAIL"
            plain(f"  [{status}] {check['name']}: {check.get('message') or ''}")
        if strict and any(not check["ok"] for check in payload["checks"]):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @engine.group("config")
    def engine_config():
        """Inspect persisted per-workspace engine configuration."""

    @engine_config.command("show")
    @click.argument("engine_id")
    @click.option("-w", "--workspace", required=True, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def engine_config_show(engine_id, workspace, as_json):
        payload = engine_config_show_payload(
            engine_id, workspace=_resolve_workspace_path(workspace)
        )
        if as_json:
            if not payload.get("found", True):
                _emit_and_exit(payload, EXIT_ENGINE_NOT_FOUND, as_json=True)
            if payload.get("error") == "workspace is required":
                _emit_and_exit(payload, EXIT_WORKSPACE_INVALID, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        if payload.get("error") == "workspace is required":
            raise click.ClickException("Workspace is required")
        if not payload.get("found", True):
            raise click.ClickException(f"Engine not found: {engine_id}")
        plain(f"Engine config: {engine_id}")
        plain(f"  Workspace: {payload.get('workspace')}")
        plain(f"  Path: {payload.get('path')}")
        plain(f"  Exists: {'yes' if payload.get('exists') else 'no'}")
        plain(emit_json(payload.get("config", {})))

    @engine_config.command("path")
    @click.argument("engine_id")
    @click.option("-w", "--workspace", required=True, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def engine_config_path(engine_id, workspace, as_json):
        payload = engine_config_path_payload(
            engine_id, workspace=_resolve_workspace_path(workspace)
        )
        if as_json:
            if payload.get("error") == "workspace is required":
                _emit_and_exit(payload, EXIT_WORKSPACE_INVALID, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        if payload.get("error") == "workspace is required":
            raise click.ClickException("Workspace is required")
        plain(payload.get("path", ""))

    @engine.command("dry-run")
    @click.argument("engine_id")
    @click.argument("file_path", type=click.Path(exists=True))
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def engine_dry_run(engine_id, file_path, workspace, as_json):
        from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp

        app = EnginesStandaloneApp(
            workspace_dir=_resolve_workspace_path(workspace),
            language="en",
            theme="dark",
            headless=True,
            dry_run=True,
        )
        result = app.run_compilation(engine_id, str(Path(file_path)), dry_run=True)
        if as_json:
            _echo_payload(result, as_json=True)
            return
        if result.get("success"):
            success("Dry-run successful.")
            plain(result.get("command", ""))
        else:
            raise click.ClickException(result.get("error", "Dry-run failed"))

    @engine.command("compile")
    @click.argument("engine_id")
    @click.argument("file_path", type=click.Path(exists=True))
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def engine_compile(engine_id, file_path, workspace, as_json):
        from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp

        app = EnginesStandaloneApp(
            workspace_dir=_resolve_workspace_path(workspace),
            language="en",
            theme="dark",
            headless=True,
        )
        result = app.run_compilation(engine_id, str(Path(file_path)), dry_run=False)
        if as_json:
            _echo_payload(result, as_json=True)
            return
        if result.get("success"):
            success("Compilation successful.")
            if result.get("stdout"):
                plain(result["stdout"])
        else:
            raise click.ClickException(result.get("error", "Compilation failed"))

    @cli.group()
    def workspace():
        """Inspect workspace state and configuration."""

    @workspace.command("inspect")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when the workspace is invalid")
    def workspace_inspect(path, as_json, strict):
        payload = workspace_inspect_payload(_resolve_workspace_path(path or "."))
        if as_json:
            if strict and not payload.get("exists"):
                _emit_and_exit(payload, EXIT_WORKSPACE_INVALID, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        if not payload.get("exists"):
            raise click.ClickException(payload.get("error", "Workspace not found"))
        plain(f"Workspace: {payload['workspace']}")
        plain(f"  Entrypoint: {payload.get('entrypoint') or '(none)'}")
        plain(f"  Python files: {payload['python_file_count']}")
        plain(
            "  Requirements files: "
            + (", ".join(payload["requirements_files_found"]) or "none")
        )

    @workspace.command("entrypoint")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when no entrypoint is resolved")
    def workspace_entrypoint(path, as_json, strict):
        payload = workspace_inspect_payload(_resolve_workspace_path(path or "."))
        result = {"workspace": payload.get("workspace"), "entrypoint": payload.get("entrypoint")}
        if as_json:
            if strict and not result.get("entrypoint"):
                _emit_and_exit(result, EXIT_PRECHECK_FAILED, as_json=True)
            _echo_payload(result, as_json=True)
            return
        plain(result["entrypoint"] or "")
        if strict and not result.get("entrypoint"):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @workspace.command("files")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def workspace_files(path, as_json):
        payload = workspace_inspect_payload(_resolve_workspace_path(path or "."))
        result = {
            "workspace": payload.get("workspace"),
            "python_file_count": payload.get("python_file_count", 0),
            "python_files_preview": payload.get("python_files_preview", []),
        }
        if as_json:
            _echo_payload(result, as_json=True)
            return
        plain(f"Python files: {result['python_file_count']}")
        for item in result["python_files_preview"]:
            plain(f"  - {item}")

    @cli.command("init")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--with-venv", is_flag=True, help="Create or reuse a local workspace venv")
    def init_cmd(workspace, as_json, with_venv):
        workspace_dir = _resolve_workspace_path(workspace or ".")
        _workspace_init_emit(workspace_dir, as_json=as_json, with_venv=with_venv)

    @cli.command("config-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def config_auto_cmd(workspace, entrypoint, as_json):
        _workspace_config_auto_emit(
            _resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )

    @cli.command("cfg-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def cfg_auto_cmd(workspace, entrypoint, as_json):
        _workspace_config_auto_emit(
            _resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )

    @cli.group("ws")
    def ws():
        """Alias for workspace bootstrap commands."""

    @ws.command("init")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--with-venv", is_flag=True, help="Create or reuse a local workspace venv")
    def ws_init_cmd(workspace, as_json, with_venv):
        workspace_dir = _resolve_workspace_path(workspace or ".")
        _workspace_init_emit(workspace_dir, as_json=as_json, with_venv=with_venv)

    @ws.command("config-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def ws_config_auto_cmd(workspace, entrypoint, as_json):
        _workspace_config_auto_emit(
            _resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )

    @cli.command("doctor")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when diagnostics detect issues")
    def doctor(workspace, as_json, strict):
        payload = doctor_payload(workspace=_resolve_workspace_path(workspace))
        if strict:
            workspace_payload = payload.get("workspace")
            has_workspace_issue = isinstance(workspace_payload, dict) and not workspace_payload.get("exists", True)
            has_engine_issue = payload["engines"]["compatible_count"] != payload["engines"]["count"]
            has_qt_issue = not payload.get("qt_available", False)
            strict_failed = bool(has_workspace_issue or has_engine_issue or has_qt_issue)
        else:
            strict_failed = False
        if as_json:
            if strict_failed:
                _emit_and_exit(payload, EXIT_PRECHECK_FAILED, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        plain("PyCompiler ARK Doctor")
        plain(f"  Python: {payload['platform']['python']}")
        plain(f"  Platform: {payload['platform']['system']} {payload['platform']['release']}")
        plain(f"  Qt available: {'yes' if payload['qt_available'] else 'no'}")
        plain(
            f"  Engines: {payload['engines']['compatible_count']}/{payload['engines']['count']} compatible"
        )
        if strict_failed:
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @cli.command("check")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--strict/--no-strict",
        default=True,
        show_default=True,
        help="Exit non-zero when checks fail",
    )
    @click.option(
        "--require-entrypoint/--no-require-entrypoint",
        default=True,
        show_default=True,
        help="Require workspace entrypoint in checks",
    )
    @click.option(
        "--fail-only/--all-checks",
        default=True,
        show_default=True,
        help="Display only failing checks in text output",
    )
    def check_cmd(workspace, as_json, strict, require_entrypoint, fail_only):
        """Single-command CI/CD gate with strict defaults."""
        payload = ci_smoke_payload(
            workspace=_resolve_workspace_path(workspace),
            require_entrypoint=require_entrypoint,
        )
        if as_json:
            if strict and not payload.get("ok"):
                _emit_and_exit(payload, EXIT_PRECHECK_FAILED, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        render_checks_text(
            "PyCompiler ARK Check",
            list(payload.get("checks", [])),
            fail_only=fail_only,
        )
        if strict and not payload.get("ok"):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @cli.group()
    def scaffold():
        """Generate starter templates."""

    @scaffold.command("engine")
    @click.argument("name")
    @click.option("--root", type=click.Path(exists=True, file_okay=False))
    @click.option("--json", "as_json", is_flag=True)
    def scaffold_engine_cmd(name, root, as_json):
        payload = scaffold_engine(name, root_dir=root)
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        if payload.get("created"):
            success(f"Engine scaffold created in {payload['path']}")
        else:
            raise click.ClickException(payload.get("reason", "Unable to create scaffold"))

    @scaffold.command("plugin")
    @click.argument("name")
    @click.option("--root", type=click.Path(exists=True, file_okay=False))
    @click.option("--json", "as_json", is_flag=True)
    def scaffold_plugin_cmd(name, root, as_json):
        payload = scaffold_plugin(name, root_dir=root)
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        if payload.get("created"):
            success(f"Plugin scaffold created in {payload['path']}")
        else:
            raise click.ClickException(payload.get("reason", "Unable to create scaffold"))

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def bcasl(ctx):
        """BCASL plugin actions."""
        if ctx.invoked_subcommand is None:
            ctx.exit(launch_bcasl_gui(None))

    @bcasl.command("gui")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    def bcasl_gui_cmd(workspace):
        sys.exit(launch_bcasl_gui(_ensure_workspace_exists(_resolve_workspace_path(workspace))))

    @bcasl.command("list")
    @click.option("--json", "as_json", is_flag=True)
    def bcasl_list(as_json):
        if as_json:
            _echo_payload(bcasl_list_payload(), as_json=True)
            return
        sys.exit(_run_bcasl_headless(["list"]))

    @bcasl.command("run")
    @click.argument("workspace", type=click.Path(exists=False))
    @click.option("--timeout", type=float, default=0.0)
    def bcasl_run(workspace, timeout):
        args = ["run", _resolve_workspace_path(workspace) or workspace]
        if timeout:
            args.extend(["--timeout", str(timeout)])
        sys.exit(_run_bcasl_headless(args))

    @bcasl.command("doctor")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when BCASL checks fail")
    def bcasl_doctor(workspace, as_json, strict):
        payload = bcasl_doctor_payload(workspace=_resolve_workspace_path(workspace))
        if as_json:
            if strict and any(not check["ok"] for check in payload.get("checks", [])):
                _emit_and_exit(payload, EXIT_PRECHECK_FAILED, as_json=True)
            _echo_payload(payload, as_json=True)
            return
        plain("BCASL Doctor")
        for check in payload.get("checks", []):
            status = "OK" if check["ok"] else "FAIL"
            plain(f"  [{status}] {check['name']}: {check.get('message') or ''}")
        if strict and any(not check["ok"] for check in payload.get("checks", [])):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @cli.command("info")
    @click.option("--json", "as_json", is_flag=True)
    def info_cmd(as_json):
        payload = doctor_payload()
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        print_system_info(app_version)

    @cli.command(name="unload")
    @click.option("--json", "as_json", is_flag=True)
    def unload_cmd(as_json):
        result = unload_all_engines()
        if as_json:
            _echo_payload(result, as_json=True)
            return
        if result["status"] == "success":
            success(result["message"])
        else:
            raise click.ClickException(result["message"])

    # Backward-compatible aliases
    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    def engines(workspace):
        """Backward-compatible alias for `gui engines`."""
        sys.exit(launch_engines_gui(_ensure_workspace_exists(_resolve_workspace_path(workspace))))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    def main_app():
        """Backward-compatible alias for `gui main`."""
        ctx = click.get_current_context(silent=True)
        ctx_obj = ctx.obj if ctx is not None else {}
        sys.exit(
            launch_main_gui(
                no_splash=bool(ctx_obj.get("no_splash", False)),
                ide_gui=bool(ctx_obj.get("ide_gui", False)),
                classic_gui=bool(ctx_obj.get("classic_gui", False)),
            )
        )

    return cli
