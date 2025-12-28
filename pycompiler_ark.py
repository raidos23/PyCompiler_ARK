#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Ague Samuel Amen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
PyCompiler ARK++ — Alternative entry point with Click CLI support

Provides multiple entry points:
    - Main application (default)
    - BCASL standalone module
    - Help and version information

Usage:
    python pycompiler_ark.py                    # Launch main application
    python pycompiler_ark.py --help             # Show help
    python pycompiler_ark.py --version          # Show version
    python pycompiler_ark.py bcasl              # Launch BCASL standalone
    python pycompiler_ark.py bcasl /path/to/ws  # Launch BCASL with workspace
"""

import multiprocessing
import sys
from pathlib import Path

try:
    import click
except ImportError:
    click = None

from main import main
from Core import __version__ as APP_VERSION


def launch_bcasl_standalone(workspace_dir=None):
    """Launch the BCASL standalone module.
    
    Args:
        workspace_dir: Optional path to workspace directory
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        from bcasl.only_mod import BcaslStandaloneApp
        from PySide6.QtWidgets import QApplication
        
        app = QApplication(sys.argv)
        window = BcaslStandaloneApp(workspace_dir=workspace_dir)
        window.show()
        return app.exec()
    except ImportError as e:
        if click:
            click.echo(f"Error: Failed to import BCASL standalone module: {e}", err=True)
            click.echo("Make sure bcasl.only_mod is properly installed.", err=True)
        else:
            print(f"Error: Failed to import BCASL standalone module: {e}")
            print("Make sure bcasl.only_mod is properly installed.")
        return 1
    except Exception as e:
        if click:
            click.echo(f"Error: Failed to launch BCASL standalone: {e}", err=True)
        else:
            print(f"Error: Failed to launch BCASL standalone: {e}")
        return 1


def launch_main_application():
    """Launch the main PyCompiler ARK++ application.
    
    Returns:
        Exit code from main application
    """
    return main(sys.argv)


# Click CLI setup (if available)
if click:
    @click.group(invoke_without_command=True)
    @click.option('--version', is_flag=True, help='Show version information')
    @click.option('--help-all', is_flag=True, help='Show detailed help')
    @click.pass_context
    def cli(ctx, version, help_all):
        """PyCompiler ARK++ — Cross-platform Python compiler with BCASL integration.
        
        Launch the main application by default, or use subcommands for specific modes.
        """
        if version:
            click.echo(f"PyCompiler ARK++ v{APP_VERSION}")
            ctx.exit(0)
        
        if help_all:
            click.echo(ctx.get_help())
            click.echo("\nAvailable Commands:")
            click.echo("  bcasl    Launch BCASL standalone module")
            click.echo("  main     Launch main application (default)")
            ctx.exit(0)
        
        # If no subcommand provided, launch main application
        if ctx.invoked_subcommand is None:
            ctx.exit(launch_main_application())
    
    @cli.command()
    @click.argument('workspace', required=False, type=click.Path(exists=False))
    def bcasl(workspace):
        """Launch BCASL standalone module for plugin management.
        
        WORKSPACE: Optional path to workspace directory
        
        Examples:
            python pycompiler_ark.py bcasl
            python pycompiler_ark.py bcasl /path/to/project
            python pycompiler_ark.py bcasl .
        """
        workspace_dir = workspace if workspace else None
        
        # Validate workspace if provided
        if workspace_dir:
            ws_path = Path(workspace_dir)
            if not ws_path.exists():
                click.echo(f"Warning: Workspace directory does not exist: {workspace_dir}", err=True)
                click.echo("Creating directory...", err=True)
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    click.echo(f"✅ Directory created: {workspace_dir}")
                except Exception as e:
                    click.echo(f"❌ Failed to create directory: {e}", err=True)
                    sys.exit(1)
        
        sys.exit(launch_bcasl_standalone(workspace_dir))
    
    @cli.command()
    def main_app():
        """Launch the main PyCompiler ARK++ application."""
        sys.exit(launch_main_application())


if __name__ == "__main__":
    if click:
        # Use Click CLI
        try:
            cli()
        except click.exceptions.Exit as e:
            sys.exit(e.exit_code)
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)
    else:
        # Fallback to simple argument parsing if Click is not available
        if len(sys.argv) > 1:
            if sys.argv[1] in ('--help', '-h', 'help'):
                print(__doc__)
                sys.exit(0)
            elif sys.argv[1] in ('--version', '-v', 'version'):
                print(f"PyCompiler ARK++ v{APP_VERSION}")
                sys.exit(0)
            elif sys.argv[1] == 'bcasl':
                workspace_dir = sys.argv[2] if len(sys.argv) > 2 else None
                sys.exit(launch_bcasl_standalone(workspace_dir))
            else:
                print(f"Unknown command: {sys.argv[1]}")
                print(__doc__)
                sys.exit(1)
        else:
            # No arguments: launch main application
            sys.exit(launch_main_application())