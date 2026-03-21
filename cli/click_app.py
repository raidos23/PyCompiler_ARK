# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path
import sys

from .dedicated import _run_bcasl_headless, run_dedicated_cli
from .headless_ops import (
    doctor_payload,
    emit_json,
    engine_doctor_payload,
    engine_info_payload,
    engine_list_payload,
    scaffold_engine,
    scaffold_plugin,
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
        plain(emit_json(payload))
        return
    if isinstance(payload, str):
        plain(payload)
    else:
        plain(str(payload))


def _resolve_workspace_path(workspace: str | None) -> str | None:
    if not workspace:
        return None
    try:
        return str(Path(workspace).expanduser())
    except Exception:
        return workspace


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
    def engine_compat(engine_id, workspace, as_json):
        payload = engine_info_payload(engine_id, workspace=_resolve_workspace_path(workspace))
        if as_json:
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

    @engine.command("doctor")
    @click.argument("engine_id")
    @click.argument("file_path", required=False, type=click.Path(exists=False))
    @click.option("-w", "--workspace", type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def engine_doctor(engine_id, file_path, workspace, as_json):
        payload = engine_doctor_payload(
            engine_id,
            workspace=_resolve_workspace_path(workspace),
            file_path=_resolve_workspace_path(file_path),
        )
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        if "checks" not in payload:
            raise click.ClickException(f"Engine not found: {engine_id}")
        plain(f"Doctor for engine: {engine_id}")
        for check in payload["checks"]:
            status = "OK" if check["ok"] else "FAIL"
            plain(f"  [{status}] {check['name']}: {check.get('message') or ''}")

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
    def workspace_inspect(path, as_json):
        payload = workspace_inspect_payload(_resolve_workspace_path(path or "."))
        if as_json:
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
    def workspace_entrypoint(path, as_json):
        payload = workspace_inspect_payload(_resolve_workspace_path(path or "."))
        result = {"workspace": payload.get("workspace"), "entrypoint": payload.get("entrypoint")}
        if as_json:
            _echo_payload(result, as_json=True)
            return
        plain(result["entrypoint"] or "")

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

    @cli.command("doctor")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def doctor(workspace, as_json):
        payload = doctor_payload(workspace=_resolve_workspace_path(workspace))
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        plain("PyCompiler ARK Doctor")
        plain(f"  Python: {payload['platform']['python']}")
        plain(f"  Platform: {payload['platform']['system']} {payload['platform']['release']}")
        plain(f"  Qt available: {'yes' if payload['qt_available'] else 'no'}")
        plain(
            f"  Engines: {payload['engines']['compatible_count']}/{payload['engines']['count']} compatible"
        )

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
        code = _run_bcasl_headless(["list"])
        if as_json:
            # Fallback minimal JSON until BCASL headless metadata is fully exposed.
            _echo_payload({"status": "delegated", "command": "bcasl list", "exit_code": code}, as_json=True)
            return
        sys.exit(code)

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
    def bcasl_doctor(workspace, as_json):
        payload = {
            "workspace": _resolve_workspace_path(workspace),
            "available": True,
            "note": "BCASL doctor is currently delegated to the headless BCASL runner.",
        }
        if as_json:
            _echo_payload(payload, as_json=True)
            return
        plain(payload["note"])

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
