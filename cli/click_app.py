# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path
import sys

from EngineLoader import unload_all

from .completion import print_command_completion
from .launchers import (
    launch_bcasl_standalone,
    launch_engines_only_standalone,
    launch_main_application,
)
from .output import error, info, plain, warn
from .system_info import print_system_info


try:
    import click  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    click = None


def has_click() -> bool:
    return click is not None


def build_cli(app_version: str):
    if click is None:
        raise RuntimeError("Click is not available")

    @click.group(
        invoke_without_command=True,
        context_settings=dict(help_option_names=["-h", "--help"]),
    )
    @click.option("--version", is_flag=True, help="Show version information")
    @click.option("--help-all", is_flag=True, help="Show detailed help with examples")
    @click.option("--info", is_flag=True, help="Show system information")
    @click.option("--verbose", is_flag=True, help="Enable verbose logging")
    @click.option("--no-splash", is_flag=True, help="Disable splash screen")
    @click.option(
        "--completion",
        type=click.Choice(["bash", "zsh", "fish"]),
        help="Generate shell completion",
    )
    @click.option(
        "--unload",
        "unload_engines_flag",
        is_flag=True,
        help="Unload all registered engines before launching the application",
    )
    @click.pass_context
    def cli(ctx, version, help_all, info, verbose, no_splash, completion, unload_engines_flag):
        """PyCompiler ARK — Cross-platform Python compiler with BCASL integration.

        Launch the main application by default, or use subcommands for specific modes.

        Examples:
            python -m pycompiler_ark                    # Launch main app
            python -m pycompiler_ark bcasl              # Launch BCASL
            python -m pycompiler_ark bcasl .            # BCASL in current dir
            python -m pycompiler_ark --info             # Show system info
        """
        ctx.obj = ctx.obj or {}
        ctx.obj["no_splash"] = bool(no_splash)
        ctx.obj["verbose"] = bool(verbose)

        if verbose:
            import os

            os.environ["PYCOMPILER_VERBOSE"] = "1"

        if version:
            info_msg = f"PyCompiler ARK v{app_version}"
            info(info_msg)
            ctx.exit(0)

        if info:
            print_system_info(app_version)
            ctx.exit(0)

        if completion:
            print_command_completion(completion)
            ctx.exit(0)

        if unload_engines_flag:
            result = unload_all()
            if result["status"] == "success":
                info(f"{result['message']}")
                if result["unloaded"]:
                    plain("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        plain(f"    • {eid}")
            else:
                error(f"{result['message']}")

        if help_all:
            plain(ctx.get_help())
            plain("\nAvailable Commands:")
            plain("  bcasl       Launch BCASL standalone module")
            plain("  main        Launch main application (default)")
            plain("\nExamples:")
            plain("  python -m pycompiler_ark                    # Main app")
            plain("  python -m pycompiler_ark bcasl              # BCASL")
            plain("  python -m pycompiler_ark bcasl /path/to/ws  # BCASL with workspace")
            plain("  python -m pycompiler_ark --info             # System info")
            ctx.exit(0)

        if ctx.invoked_subcommand is None:
            ctx.exit(launch_main_application(no_splash=ctx.obj.get("no_splash", False)))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    def bcasl(workspace):
        """Launch BCASL standalone module for plugin management."""
        workspace_dir = None
        if workspace:
            workspace_dir = workspace

        if workspace_dir:
            ws_path = Path(workspace_dir)
            if not ws_path.exists():
                warn(
                    f"Warning: Workspace directory does not exist: {workspace_dir}",
                )
                warn("Creating directory...")
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    info(f"Directory created: {workspace_dir}")
                except Exception as exc:
                    error(f"Failed to create directory: {exc}")
                    sys.exit(1)

        sys.exit(launch_bcasl_standalone(workspace_dir))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--dry-run", is_flag=True, help="Show command without executing")
    @click.option(
        "-l",
        "--language",
        type=click.Choice(["en", "fr"]),
        default="en",
        help="Interface language",
    )
    @click.option(
        "-t",
        "--theme",
        type=click.Choice(["light", "dark"]),
        default="dark",
        help="UI theme",
    )
    def engines(workspace, dry_run, language, theme):
        """Launch Engines standalone module for compilation engine management."""
        workspace_dir = None
        if workspace:
            workspace_dir = workspace

        if workspace_dir:
            ws_path = Path(workspace_dir)
            if not ws_path.exists():
                warn(
                    f"Warning: Workspace directory does not exist: {workspace_dir}",
                )
                warn("Creating directory...")
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    info(f"Directory created: {workspace_dir}")
                except Exception as exc:
                    error(f"Failed to create directory: {exc}")
                    sys.exit(1)

        if dry_run:
            from EngineLoader import available_engines

            engines = available_engines()
            plain(f"Available engines ({len(engines)}):")
            for eid in engines:
                plain(f"  • {eid}")
            sys.exit(0)

        sys.exit(launch_engines_only_standalone(workspace_dir))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    def main_app():
        """Launch the main PyCompiler ARK application."""
        ctx = click.get_current_context(silent=True)
        ctx_obj = ctx.obj if ctx is not None else {}
        sys.exit(launch_main_application(no_splash=bool(ctx_obj.get("no_splash", False))))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]), name="unload")
    def unload_engines_cmd():
        """Unload all registered engines."""
        result = unload_all()
        if result["status"] == "success":
            info(f"{result['message']}")
            if result["unloaded"]:
                plain("  Unloaded engines:")
                for eid in result["unloaded"]:
                    plain(f"    • {eid}")
        else:
            error(f"{result['message']}")
        sys.exit(0 if result["status"] == "success" else 1)

    return cli
