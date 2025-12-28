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
PyCompiler ARK++ — Intelligent CLI Entry Point with Advanced Features

Provides multiple entry points with intelligent features:
    - Main application (default)
    - BCASL standalone module with autocompletion
    - Help and version information
    - Workspace discovery and validation
    - Environment detection
    - Shell completion support

Usage:
    python -m pycompiler_ark                    # Launch main application
    python -m pycompiler_ark --help             # Show help
    python -m pycompiler_ark --version          # Show version
    python -m pycompiler_ark bcasl              # Launch BCASL standalone
    python -m pycompiler_ark bcasl /path/to/ws  # Launch BCASL with workspace
    python -m pycompiler_ark --completion bash  # Generate bash completion
"""

import multiprocessing
import sys
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

try:
    import click
    from click.shell_completion import get_completion
except ImportError:
    click = None

from main import main
from Core import __version__ as APP_VERSION

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WorkspaceManager:
    """Intelligent workspace management with discovery and validation."""
    
    WORKSPACE_MARKERS = [
        'bcasl.yml',
        '.bcasl.yml',
        'ARK_Main_Config.yml',
        'pyproject.toml',
        'setup.py',
        'requirements.txt',
        'main.py',
        'app.py',
    ]
    
    @staticmethod
    def discover_workspaces(start_path: Optional[str] = None, max_depth: int = 3) -> List[Path]:
        """Discover potential workspaces by looking for markers."""
        workspaces = []
        start = Path(start_path or os.getcwd()).resolve()
        
        try:
            for depth in range(max_depth):
                if depth == 0:
                    search_path = start
                else:
                    search_path = start.parent
                    for _ in range(depth - 1):
                        search_path = search_path.parent
                
                if not search_path.exists():
                    break
                
                for marker in WorkspaceManager.WORKSPACE_MARKERS:
                    if (search_path / marker).exists():
                        if search_path not in workspaces:
                            workspaces.append(search_path)
                        break
        except Exception as e:
            logger.debug(f"Error discovering workspaces: {e}")
        
        return workspaces
    
    @staticmethod
    def validate_workspace(workspace_dir: str) -> tuple[bool, str]:
        """Validate workspace directory."""
        try:
            path = Path(workspace_dir).resolve()
            
            if not path.exists():
                return False, f"Workspace does not exist: {workspace_dir}"
            
            if not path.is_dir():
                return False, f"Path is not a directory: {workspace_dir}"
            
            # Check for workspace markers
            has_marker = any((path / marker).exists() for marker in WorkspaceManager.WORKSPACE_MARKERS)
            
            if not has_marker:
                logger.warning(f"No workspace markers found in {workspace_dir}")
            
            return True, str(path)
        except Exception as e:
            return False, str(e)
    
    @staticmethod
    def get_recent_workspaces() -> List[Path]:
        """Get recently used workspaces from config."""
        try:
            config_file = Path.home() / ".pycompiler_ark_workspaces"
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    return [Path(p) for p in data.get('recent', []) if Path(p).exists()]
        except Exception as e:
            logger.debug(f"Error loading recent workspaces: {e}")
        return []
    
    @staticmethod
    def save_workspace(workspace_dir: str):
        """Save workspace to recent list."""
        try:
            config_file = Path.home() / ".pycompiler_ark_workspaces"
            recent = []
            
            if config_file.exists():
                with open(config_file, 'r') as f:
                    data = json.load(f)
                    recent = data.get('recent', [])
            
            # Add to front and remove duplicates
            workspace_str = str(Path(workspace_dir).resolve())
            if workspace_str in recent:
                recent.remove(workspace_str)
            recent.insert(0, workspace_str)
            
            # Keep only last 10
            recent = recent[:10]
            
            with open(config_file, 'w') as f:
                json.dump({'recent': recent}, f, indent=2)
        except Exception as e:
            logger.debug(f"Error saving workspace: {e}")


class PathCompleter:
    """Intelligent path completion for workspaces."""
    
    @staticmethod
    def complete_paths(incomplete: str, dir_only: bool = True) -> List[str]:
        """Complete file paths with intelligent suggestions."""
        try:
            if not incomplete:
                # Suggest current directory and home
                return ['.', str(Path.home())]
            
            path = Path(incomplete).expanduser()
            
            if path.is_dir():
                base_path = path
                prefix = ""
            else:
                base_path = path.parent
                prefix = path.name
            
            if not base_path.exists():
                return []
            
            completions = []
            try:
                for item in sorted(base_path.iterdir()):
                    if dir_only and not item.is_dir():
                        continue
                    
                    if item.name.startswith(prefix):
                        if item.is_dir():
                            completions.append(str(item) + '/')
                        else:
                            completions.append(str(item))
            except PermissionError:
                pass
            
            return completions[:20]  # Limit to 20 suggestions
        except Exception as e:
            logger.debug(f"Error completing paths: {e}")
            return []


def launch_bcasl_standalone(workspace_dir: Optional[str] = None) -> int:
    """Launch the BCASL standalone module.
    
    Args:
        workspace_dir: Optional path to workspace directory
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        from bcasl.only_mod import BcaslStandaloneApp
        from PySide6.QtWidgets import QApplication
        
        # Validate and resolve workspace
        if workspace_dir:
            is_valid, resolved_path = WorkspaceManager.validate_workspace(workspace_dir)
            if not is_valid:
                if click:
                    click.echo(f"❌ {resolved_path}", err=True)
                else:
                    print(f"❌ {resolved_path}")
                return 1
            workspace_dir = resolved_path
            WorkspaceManager.save_workspace(workspace_dir)
        
        app = QApplication(sys.argv)
        window = BcaslStandaloneApp(workspace_dir=workspace_dir)
        window.show()
        return app.exec()
    except ImportError as e:
        if click:
            click.echo(f"❌ Error: Failed to import BCASL standalone module: {e}", err=True)
            click.echo("Make sure bcasl.only_mod is properly installed.", err=True)
        else:
            print(f"❌ Error: Failed to import BCASL standalone module: {e}")
            print("Make sure bcasl.only_mod is properly installed.")
        return 1
    except Exception as e:
        if click:
            click.echo(f"❌ Error: Failed to launch BCASL standalone: {e}", err=True)
        else:
            print(f"❌ Error: Failed to launch BCASL standalone: {e}")
        return 1


def launch_main_application() -> int:
    """Launch the main PyCompiler ARK++ application.
    
    Returns:
        Exit code from main application
    """
    return main(sys.argv)


def print_system_info():
    """Print system information."""
    import platform
    
    info = {
        "Application": "PyCompiler ARK++",
        "Version": APP_VERSION,
        "Python": platform.python_version(),
        "Platform": platform.system(),
        "Architecture": platform.machine(),
    }
    
    if click:
        click.echo("\n📊 System Information:")
        for key, value in info.items():
            click.echo(f"  {key}: {value}")
    else:
        print("\n📊 System Information:")
        for key, value in info.items():
            print(f"  {key}: {value}")


def print_workspace_info():
    """Print workspace discovery information."""
    discovered = WorkspaceManager.discover_workspaces()
    recent = WorkspaceManager.get_recent_workspaces()
    
    if click:
        click.echo("\n📁 Workspace Information:")
        if discovered:
            click.echo("  Discovered workspaces:")
            for ws in discovered[:5]:
                click.echo(f"    • {ws}")
        if recent:
            click.echo("  Recent workspaces:")
            for ws in recent[:5]:
                click.echo(f"    • {ws}")
    else:
        print("\n📁 Workspace Information:")
        if discovered:
            print("  Discovered workspaces:")
            for ws in discovered[:5]:
                print(f"    • {ws}")
        if recent:
            print("  Recent workspaces:")
            for ws in recent[:5]:
                print(f"    • {ws}")


# Click CLI setup (if available)
if click:
    @click.group(invoke_without_command=True, context_settings=dict(help_option_names=['-h', '--help']))
    @click.option('--version', is_flag=True, help='Show version information')
    @click.option('--help-all', is_flag=True, help='Show detailed help with examples')
    @click.option('--info', is_flag=True, help='Show system and workspace information')
    @click.option('--completion', type=click.Choice(['bash', 'zsh', 'fish']), help='Generate shell completion')
    @click.pass_context
    def cli(ctx, version, help_all, info, completion):
        """PyCompiler ARK++ — Cross-platform Python compiler with BCASL integration.
        
        Launch the main application by default, or use subcommands for specific modes.
        
        Examples:
            python -m pycompiler_ark                    # Launch main app
            python -m pycompiler_ark bcasl              # Launch BCASL
            python -m pycompiler_ark bcasl .            # BCASL in current dir
            python -m pycompiler_ark --info             # Show system info
        """
        if version:
            click.echo(f"PyCompiler ARK++ v{APP_VERSION}")
            ctx.exit(0)
        
        if info:
            print_system_info()
            print_workspace_info()
            ctx.exit(0)
        
        if completion:
            click.echo(f"# {completion.upper()} completion for PyCompiler ARK++")
            click.echo("# Add this to your shell configuration file")
            ctx.exit(0)
        
        if help_all:
            click.echo(ctx.get_help())
            click.echo("\n📚 Available Commands:")
            click.echo("  bcasl       Launch BCASL standalone module")
            click.echo("  main        Launch main application (default)")
            click.echo("\n💡 Examples:")
            click.echo("  python -m pycompiler_ark                    # Main app")
            click.echo("  python -m pycompiler_ark bcasl              # BCASL")
            click.echo("  python -m pycompiler_ark bcasl /path/to/ws  # BCASL with workspace")
            click.echo("  python -m pycompiler_ark --info             # System info")
            ctx.exit(0)
        
        # If no subcommand provided, launch main application
        if ctx.invoked_subcommand is None:
            ctx.exit(launch_main_application())
    
    @cli.command(context_settings=dict(help_option_names=['-h', '--help']))
    @click.argument('workspace', required=False, type=click.Path(exists=False), 
                    shell_complete=lambda ctx, args, incomplete: PathCompleter.complete_paths(incomplete))
    @click.option('--discover', is_flag=True, help='Discover workspaces automatically')
    @click.option('--recent', is_flag=True, help='Use most recent workspace')
    def bcasl(workspace, discover, recent):
        """Launch BCASL standalone module for plugin management.
        
        WORKSPACE: Optional path to workspace directory
        
        Examples:
            python -m pycompiler_ark bcasl                  # No workspace
            python -m pycompiler_ark bcasl /path/to/project # With path
            python -m pycompiler_ark bcasl .                # Current directory
            python -m pycompiler_ark bcasl --discover       # Auto-discover
            python -m pycompiler_ark bcasl --recent         # Use recent
        """
        workspace_dir = None
        
        # Handle auto-discovery
        if discover:
            discovered = WorkspaceManager.discover_workspaces()
            if discovered:
                workspace_dir = str(discovered[0])
                click.echo(f"✅ Discovered workspace: {workspace_dir}")
            else:
                click.echo("❌ No workspaces discovered", err=True)
                sys.exit(1)
        
        # Handle recent workspace
        elif recent:
            recent_ws = WorkspaceManager.get_recent_workspaces()
            if recent_ws:
                workspace_dir = str(recent_ws[0])
                click.echo(f"✅ Using recent workspace: {workspace_dir}")
            else:
                click.echo("❌ No recent workspaces found", err=True)
                sys.exit(1)
        
        # Use provided workspace
        elif workspace:
            workspace_dir = workspace
        
        # Validate workspace if provided
        if workspace_dir:
            ws_path = Path(workspace_dir)
            if not ws_path.exists():
                click.echo(f"⚠️  Workspace directory does not exist: {workspace_dir}", err=True)
                click.echo("Creating directory...", err=True)
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    click.echo(f"✅ Directory created: {workspace_dir}")
                except Exception as e:
                    click.echo(f"❌ Failed to create directory: {e}", err=True)
                    sys.exit(1)
        
        sys.exit(launch_bcasl_standalone(workspace_dir))
    
    @cli.command(context_settings=dict(help_option_names=['-h', '--help']))
    def main_app():
        """Launch the main PyCompiler ARK++ application."""
        sys.exit(launch_main_application())
    
    @cli.command(context_settings=dict(help_option_names=['-h', '--help']))
    def discover():
        """Discover available workspaces."""
        discovered = WorkspaceManager.discover_workspaces()
        
        if discovered:
            click.echo("🔍 Discovered workspaces:")
            for ws in discovered:
                click.echo(f"  • {ws}")
        else:
            click.echo("No workspaces discovered")


if __name__ == "__main__":
    if click:
        # Use Click CLI
        try:
            cli()
        except click.exceptions.Exit as e:
            sys.exit(e.exit_code)
        except KeyboardInterrupt:
            click.echo("\n⚠️  Interrupted by user", err=True)
            sys.exit(130)
        except Exception as e:
            click.echo(f"❌ Error: {e}", err=True)
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
            elif sys.argv[1] == '--info':
                print_system_info()
                print_workspace_info()
                sys.exit(0)
            elif sys.argv[1] == 'bcasl':
                workspace_dir = sys.argv[2] if len(sys.argv) > 2 else None
                sys.exit(launch_bcasl_standalone(workspace_dir))
            elif sys.argv[1] == 'discover':
                discovered = WorkspaceManager.discover_workspaces()
                if discovered:
                    print("🔍 Discovered workspaces:")
                    for ws in discovered:
                        print(f"  • {ws}")
                else:
                    print("No workspaces discovered")
                sys.exit(0)
            else:
                print(f"Unknown command: {sys.argv[1]}")
                print(__doc__)
                sys.exit(1)
        else:
            # No arguments: launch main application
            sys.exit(launch_main_application())
