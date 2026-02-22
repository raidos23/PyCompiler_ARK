# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path
import sys

from EngineLoader import unload_all

from .completion import PathCompleter
from .launchers import (
    launch_bcasl_standalone,
    launch_engines_only_standalone,
    launch_main_application,
)
from .output import echo
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
    def cli(ctx, version, help_all, info, completion, unload_engines_flag):
        """PyCompiler ARK — Cross-platform Python compiler with BCASL integration.

        Launch the main application by default, or use subcommands for specific modes.

        Examples:
            python -m pycompiler_ark                    # Launch main app
            python -m pycompiler_ark bcasl              # Launch BCASL
            python -m pycompiler_ark bcasl .            # BCASL in current dir
            python -m pycompiler_ark --info             # Show system info
        """
        if version:
            echo(f"PyCompiler ARK v{app_version}")
            ctx.exit(0)

        if info:
            print_system_info(app_version)
            ctx.exit(0)

        if completion:
            echo(f"# {completion.upper()} completion for PyCompiler ARK")
            echo("# Add this to your shell configuration file")
            ctx.exit(0)

        if unload_engines_flag:
            result = unload_all()
            if result["status"] == "success":
                echo(f"{result['message']}")
                if result["unloaded"]:
                    echo("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        echo(f"    • {eid}")
            else:
                echo(f"Error: {result['message']}", err=True)

        if help_all:
            echo(ctx.get_help())
            echo("\nAvailable Commands:")
            echo("  bcasl       Launch BCASL standalone module")
            echo("  main        Launch main application (default)")
            echo("\nExamples:")
            echo("  python -m pycompiler_ark                    # Main app")
            echo("  python -m pycompiler_ark bcasl              # BCASL")
            echo("  python -m pycompiler_ark bcasl /path/to/ws  # BCASL with workspace")
            echo("  python -m pycompiler_ark --info             # System info")
            ctx.exit(0)

        if ctx.invoked_subcommand is None:
            ctx.exit(launch_main_application())

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.argument(
        "workspace",
        required=False,
        type=click.Path(exists=False),
        shell_complete=lambda ctx, args, incomplete: PathCompleter.complete_paths(
            incomplete
        ),
    )
    def bcasl(workspace):
        """Launch BCASL standalone module for plugin management."""
        workspace_dir = None
        if workspace:
            workspace_dir = workspace

        if workspace_dir:
            ws_path = Path(workspace_dir)
            if not ws_path.exists():
                echo(
                    f"Warning: Workspace directory does not exist: {workspace_dir}",
                    err=True,
                )
                echo("Creating directory...", err=True)
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    echo(f"Directory created: {workspace_dir}")
                except Exception as exc:
                    echo(f"Failed to create directory: {exc}", err=True)
                    sys.exit(1)

        sys.exit(launch_bcasl_standalone(workspace_dir))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    @click.argument(
        "workspace",
        required=False,
        type=click.Path(exists=False),
        shell_complete=lambda ctx, args, incomplete: PathCompleter.complete_paths(
            incomplete
        ),
    )
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
                echo(
                    f"Warning: Workspace directory does not exist: {workspace_dir}",
                    err=True,
                )
                echo("Creating directory...", err=True)
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    echo(f"Directory created: {workspace_dir}")
                except Exception as exc:
                    echo(f"Failed to create directory: {exc}", err=True)
                    sys.exit(1)

        if dry_run:
            from EngineLoader import available_engines

            engines = available_engines()
            echo(f"Available engines ({len(engines)}):")
            for eid in engines:
                echo(f"  • {eid}")
            sys.exit(0)

        sys.exit(launch_engines_only_standalone(workspace_dir))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    def main_app():
        """Launch the main PyCompiler ARK application."""
        sys.exit(launch_main_application())

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]), name="unload")
    def unload_engines_cmd():
        """Unload all registered engines."""
        result = unload_all()
        if result["status"] == "success":
            echo(f"{result['message']}")
            if result["unloaded"]:
                echo("  Unloaded engines:")
                for eid in result["unloaded"]:
                    echo(f"    • {eid}")
        else:
            echo(f"Error: {result['message']}", err=True)
        sys.exit(0 if result["status"] == "success" else 1)

    return cli
