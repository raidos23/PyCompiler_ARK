#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
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
PyCompiler ARK++ — Cross-platform hardened bootstrap with Intelligent CLI Entry Point

Features:
    - OS-specific environment safety (UTF-8, DPI, Wayland/macOS)
    - Crash logging to platform-appropriate directories
    - Qt message handler and high-DPI attributes configured before QApplication
    - Global excepthook and faulthandler
    - Graceful signal handling (SIGINT/SIGTERM; SIGBREAK on Windows)
    - macOS PATH augmentation for GUI-launched app (Homebrew paths)
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
    python -m pycompiler_ark unload             # Unload all engines
"""

import faulthandler
import multiprocessing
import os
import platform
import signal
import sys
import traceback
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Ensure project root has priority on sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path[:1]:
    sys.path.insert(0, ROOT_DIR)

try:
    import click
    from click.shell_completion import get_completion
except ImportError:
    click = None

from Core import __version__ as APP_VERSION
from Core.engines_loader import unload_all
from Core import PyCompilerArkGui

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

IS_WINDOWS = os.name == "nt" or platform.system().lower().startswith("win")
IS_DARWIN = platform.system().lower().startswith("darwin")
IS_LINUX = platform.system().lower().startswith("linux")

# Reduce Qt startup noise unless explicitly verbose
if not os.environ.get("PYCOMPILER_VERBOSE"):
    os.environ.setdefault(
        "QT_LOGGING_RULES",
        "qt.qpa.*=false;qt.quick.*=false;qt.scenegraph.*=false;qt.*.debug=false;qt.*.info=false;qt.gui.*.warning=false;qt.widgets.*.warning=false",
    )

# UTF-8 everywhere
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# DPI/scaling hints
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
# Wayland fractional scaling workaround (Linux)
if IS_LINUX:
    os.environ.setdefault("QT_WAYLAND_DISABLE_FRACTIONAL_SCALE", "1")
# macOS: prefer layer-backed widgets for better rendering
if IS_DARWIN:
    os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
    # GUI-launched apps often have a reduced PATH; ensure common Homebrew paths are present
    try:
        path = os.environ.get("PATH", "")
        add = []
        for p in ("/opt/homebrew/bin", "/usr/local/bin"):
            if p not in path:
                add.append(p)
        if add:
            os.environ["PATH"] = (
                os.pathsep.join(add + [path]) if path else os.pathsep.join(add)
            )
    except Exception:
        pass
# Linux: ensure a UTF-8 locale if not set
if IS_LINUX:
    if not os.environ.get("LC_ALL") and not os.environ.get("LANG"):
        os.environ["LC_ALL"] = "C.UTF-8"


# Determine a platform-appropriate crash log directory
def _platform_log_dir() -> Path:
    # Toujours journaliser dans le dossier local du projet: ROOT_DIR/logs
    try:
        return Path(ROOT_DIR) / "logs"
    except Exception:
        return Path.cwd() / "logs"


# Enable faulthandler with persistent log file
crash_log = None
try:
    _log_dir = _platform_log_dir()
    _log_dir.mkdir(parents=True, exist_ok=True)
    crash_log = _log_dir / "crash.log"
    try:
        _crash_fp = open(crash_log, "a", encoding="utf-8", errors="ignore")
        faulthandler.enable(_crash_fp)  # type: ignore[arg-type]
    except Exception:
        faulthandler.enable()
except Exception:
    try:
        faulthandler.enable()
    except Exception:
        pass

# Import Qt after environment tuning
from PySide6.QtCore import (
    QCoreApplication,
    Qt,
    QTimer,
    QtMsgType,
    qInstallMessageHandler,
)
from PySide6.QtGui import QColor, QPixmap, QIcon
from PySide6.QtWidgets import QApplication, QSplashScreen

# Application metadata and high-DPI attributes BEFORE QApplication
try:
    QCoreApplication.setOrganizationName("PyCompiler")
    QCoreApplication.setOrganizationDomain("pycompiler.local")
    QCoreApplication.setApplicationName("PyCompiler ARK++")
    QCoreApplication.setApplicationVersion(APP_VERSION)
except Exception:
    pass


def _qt_message_handler(mode, context, message):
    # Écrit tous les messages Qt dans logs/crash.log. À l'écran, supprime warnings/info/debug si non-verbose.
    suppressed = (not os.environ.get("PYCOMPILER_VERBOSE")) and mode in (
        QtMsgType.QtWarningMsg,
        QtMsgType.QtInfoMsg,
        QtMsgType.QtDebugMsg,
    )
    # Toujours écrire en fichier
    try:
        _txt = (message or "") + "\n"
        if crash_log is not None:
            with open(crash_log, "a", encoding="utf-8", errors="ignore") as _f:
                _f.write(_txt)
    except Exception:
        pass
    if suppressed:
        return
    try:
        sys.__stderr__.write(_txt)
    except Exception:
        pass


def _excepthook(etype, value, tb):
    # Global last-chance handler: print to stderr and crash log
    try:
        msg = "\n".join(
            [
                "\n=== Unhandled exception ===",
                f"Platform: {platform.platform()} Python: {platform.python_version()}",
                "".join(traceback.format_exception(etype, value, tb)),
                "=== End exception ===\n",
            ]
        )
        try:
            sys.__stderr__.write(msg)
        except Exception:
            pass
        try:
            if crash_log is not None:
                with open(crash_log, "a", encoding="utf-8", errors="ignore") as f:
                    f.write(msg)
        except Exception:
            pass
    finally:
        try:
            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass
        os._exit(1)


# Install handlers early
qInstallMessageHandler(_qt_message_handler)
sys.excepthook = _excepthook


# Graceful termination on signals
def _handle_signal(signum, _frame):
    try:
        app = QApplication.instance()
        if app is not None:
            app.quit()
    except Exception:
        pass


for _sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
    try:
        if _sig is not None:
            signal.signal(_sig, _handle_signal)
    except Exception:
        pass
# Windows: also catch CTRL_BREAK_EVENT
if IS_WINDOWS and hasattr(signal, "SIGBREAK"):
    try:
        signal.signal(signal.SIGBREAK, _handle_signal)  # type: ignore[attr-defined]
    except Exception:
        pass


class WorkspaceManager:
    """Intelligent workspace management with discovery and validation."""

    WORKSPACE_MARKERS = [
        "bcasl.yml",
        ".bcasl.yml",
        "ARK_Main_Config.yml",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "main.py",
        "app.py",
    ]

    @staticmethod
    def discover_workspaces(
        start_path: Optional[str] = None, max_depth: int = 3
    ) -> List[Path]:
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
            has_marker = any(
                (path / marker).exists()
                for marker in WorkspaceManager.WORKSPACE_MARKERS
            )

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
                with open(config_file, "r") as f:
                    data = json.load(f)
                    return [Path(p) for p in data.get("recent", []) if Path(p).exists()]
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
                with open(config_file, "r") as f:
                    data = json.load(f)
                    recent = data.get("recent", [])

            # Add to front and remove duplicates
            workspace_str = str(Path(workspace_dir).resolve())
            if workspace_str in recent:
                recent.remove(workspace_str)
            recent.insert(0, workspace_str)

            # Keep only last 10
            recent = recent[:10]

            with open(config_file, "w") as f:
                json.dump({"recent": recent}, f, indent=2)
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
                return [".", str(Path.home())]

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
                            completions.append(str(item) + "/")
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
            click.echo(
                f"❌ Error: Failed to import BCASL standalone module: {e}", err=True
            )
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
    try:
        app = QApplication(sys.argv)
        # Use logo/logo2.png as application icon if available
        try:
            _icon_path = os.path.join(ROOT_DIR, "logo", "logo2.png")
            if os.path.isfile(_icon_path):
                app.setWindowIcon(QIcon(_icon_path))
        except Exception:
            pass

        # Splash screen: affiche l'image 'splash.*' depuis le dossier 'logo' si disponible
        splash = None
        try:
            logo_dir = os.path.join(ROOT_DIR, "logo")
            safe_ver = "".join(
                c for c in APP_VERSION if c.isalnum() or c in (".", "-", "_")
            )
            names = [
                f"splash_v{safe_ver}.png",
                "splash.png",
                "splash.jpg",
                "splash.jpeg",
                "splash.bmp",
            ]
            for _name in names:
                _path = os.path.join(logo_dir, _name)
                if os.path.isfile(_path):
                    _pix = QPixmap(_path)
                    if not _pix.isNull():
                        # Limiter la taille pour éviter tout affichage plein écran
                        try:
                            screen = app.primaryScreen()
                            geo = (
                                screen.availableGeometry()
                                if screen is not None
                                else None
                            )
                            max_side = 720
                            if geo is not None:
                                max_side = int(min(geo.width(), geo.height()) * 0.5)
                                max_side = max(240, min(max_side, 720))
                            if _pix.width() > max_side or _pix.height() > max_side:
                                _pix = _pix.scaled(
                                    max_side,
                                    max_side,
                                    Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation,
                                )
                        except Exception:
                            pass
                        splash = QSplashScreen(_pix)
                        splash.show()
                        try:
                            # Centrer le splash sur l'écran actif
                            if screen is not None:
                                sg = splash.frameGeometry()
                                center = (
                                    geo.center()
                                    if geo is not None
                                    else screen.geometry().center()
                                )
                                splash.move(
                                    center.x() - sg.width() // 2,
                                    center.y() - sg.height() // 2,
                                )
                        except Exception:
                            pass
                        app.processEvents()
                        # Messages d'étapes affichés sur le splash (FR/EN)
                        try:
                            align = Qt.AlignHCenter | Qt.AlignBottom
                            col = QColor(255, 255, 255)
                            splash.showMessage(
                                "Initialisation… / Initializing…", align, col
                            )
                            app.processEvents()
                            QTimer.singleShot(
                                700,
                                lambda: splash.showMessage(
                                    "Chargement du thème… / Loading theme…", align, col
                                ),
                            )
                            QTimer.singleShot(
                                1400,
                                lambda: splash.showMessage(
                                    "Découverte des moteurs… / Discovering engines…",
                                    align,
                                    col,
                                ),
                            )
                            QTimer.singleShot(
                                2300,
                                lambda: splash.showMessage(
                                    "Préparation de l'interface… / Preparing UI…",
                                    align,
                                    col,
                                ),
                            )
                        except Exception:
                            pass
                    break
        except Exception:
            splash = None
        if splash is not None:
            delay_ms = 3500
            try:
                delay_ms = int(os.environ.get("PYCOMPILER_SPLASH_DELAY_MS", "3500"))
            except Exception:
                delay_ms = 3500

            def _launch_main():
                try:
                    w = PyCompilerArkGui()
                    # ensure main window uses the same icon if available
                    try:
                        if os.path.isfile(_icon_path):
                            w.setWindowIcon(QIcon(_icon_path))
                    except Exception:
                        pass
                    w.show()

                    # Resserrement auto pour très petits écrans
                    try:
                        from PySide6.QtWidgets import QLabel, QLayout

                        screen2 = app.primaryScreen()
                        geo2 = (
                            screen2.availableGeometry() if screen2 is not None else None
                        )
                        if geo2 and (geo2.width() < 1000 or geo2.height() < 650):
                            try:
                                lays = (
                                    w.ui.findChildren(QLayout)
                                    if hasattr(w, "ui")
                                    else []
                                )
                                for _l in lays:
                                    try:
                                        _l.setContentsMargins(6, 6, 6, 6)
                                        _l.setSpacing(6)
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            try:
                                lbl = getattr(w, "sidebar_logo", None)
                                if lbl is None and hasattr(w, "ui"):
                                    lbl = w.ui.findChild(QLabel, "sidebar_logo")
                                if lbl is not None and lbl.pixmap() is not None:
                                    pm = lbl.pixmap()
                                    if pm is not None:
                                        lbl.setPixmap(
                                            pm.scaled(
                                                120,
                                                120,
                                                Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation,
                                            )
                                        )
                            except Exception:
                                pass
                    except Exception:
                        pass

                    try:
                        splash.finish(w)
                    except Exception:
                        pass
                except Exception:
                    _excepthook(*sys.exc_info())

            QTimer.singleShot(max(0, delay_ms), _launch_main)
        else:
            w = PyCompilerArkGui()
            # ensure main window uses the same icon if available
            try:
                if os.path.isfile(_icon_path):
                    w.setWindowIcon(QIcon(_icon_path))
            except Exception:
                pass
            w.show()
            # Resserrement auto pour très petits écrans
            try:
                from PySide6.QtWidgets import QLabel, QLayout

                screen3 = app.primaryScreen()
                geo3 = screen3.availableGeometry() if screen3 is not None else None
                if geo3 and (geo3.width() < 1000 or geo3.height() < 650):
                    try:
                        lays = w.ui.findChildren(QLayout) if hasattr(w, "ui") else []
                        for _l in lays:
                            try:
                                _l.setContentsMargins(6, 6, 6, 6)
                                _l.setSpacing(6)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        lbl = getattr(w, "sidebar_logo", None)
                        if lbl is None and hasattr(w, "ui"):
                            lbl = w.ui.findChild(QLabel, "sidebar_logo")
                        if lbl is not None and lbl.pixmap() is not None:
                            pm = lbl.pixmap()
                            if pm is not None:
                                lbl.setPixmap(
                                    pm.scaled(
                                        120,
                                        120,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation,
                                    )
                                )
                    except Exception:
                        pass
            except Exception:
                pass
        rc = app.exec()
        return int(rc) if isinstance(rc, int) else 0
    except Exception:
        _excepthook(*sys.exc_info())
        return 1


def print_system_info():
    """Print system information."""
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

    @click.group(
        invoke_without_command=True,
        context_settings=dict(help_option_names=["-h", "--help"]),
    )
    @click.option("--version", is_flag=True, help="Show version information")
    @click.option("--help-all", is_flag=True, help="Show detailed help with examples")
    @click.option("--info", is_flag=True, help="Show system and workspace information")
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

        if unload_engines_flag:
            result = unload_all()
            if result["status"] == "success":
                click.echo(f"✅ {result['message']}")
                if result["unloaded"]:
                    click.echo("  Unloaded engines:")
                    for eid in result["unloaded"]:
                        click.echo(f"    • {eid}")
            else:
                click.echo(f"❌ Error: {result['message']}", err=True)

        if help_all:
            click.echo(ctx.get_help())
            click.echo("\n📚 Available Commands:")
            click.echo("  bcasl       Launch BCASL standalone module")
            click.echo("  main        Launch main application (default)")
            click.echo("\n💡 Examples:")
            click.echo("  python -m pycompiler_ark                    # Main app")
            click.echo("  python -m pycompiler_ark bcasl              # BCASL")
            click.echo(
                "  python -m pycompiler_ark bcasl /path/to/ws  # BCASL with workspace"
            )
            click.echo("  python -m pycompiler_ark --info             # System info")
            ctx.exit(0)

        # If no subcommand provided, launch main application
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
    @click.option("--discover", is_flag=True, help="Discover workspaces automatically")
    @click.option("--recent", is_flag=True, help="Use most recent workspace")
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
                click.echo(
                    f"⚠️  Workspace directory does not exist: {workspace_dir}", err=True
                )
                click.echo("Creating directory...", err=True)
                try:
                    ws_path.mkdir(parents=True, exist_ok=True)
                    click.echo(f"✅ Directory created: {workspace_dir}")
                except Exception as e:
                    click.echo(f"❌ Failed to create directory: {e}", err=True)
                    sys.exit(1)

        sys.exit(launch_bcasl_standalone(workspace_dir))

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    def main_app():
        """Launch the main PyCompiler ARK++ application."""
        sys.exit(launch_main_application())

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]))
    def discover():
        """Discover available workspaces."""
        discovered = WorkspaceManager.discover_workspaces()

        if discovered:
            click.echo("🔍 Discovered workspaces:")
            for ws in discovered:
                click.echo(f"  • {ws}")
        else:
            click.echo("No workspaces discovered")

    @cli.command(context_settings=dict(help_option_names=["-h", "--help"]), name="unload")
    def unload_engines_cmd():
        """Unload all registered engines."""
        result = unload_all()
        if result["status"] == "success":
            click.echo(f"✅ {result['message']}")
            if result["unloaded"]:
                click.echo("  Unloaded engines:")
                for eid in result["unloaded"]:
                    click.echo(f"    • {eid}")
        else:
            click.echo(f"❌ Error: {result['message']}", err=True)
        sys.exit(0 if result["status"] == "success" else 1)


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
            if sys.argv[1] in ("--help", "-h", "help"):
                print(__doc__)
                sys.exit(0)
            elif sys.argv[1] in ("--version", "-v", "version"):
                print(f"PyCompiler ARK++ v{APP_VERSION}")
                sys.exit(0)
            elif sys.argv[1] == "--info":
                print_system_info()
                print_workspace_info()
                sys.exit(0)
            elif sys.argv[1] == "--unload":
                result = unload_all()
                if result["status"] == "success":
                    print(f"✅ {result['message']}")
                    if result["unloaded"]:
                        print("  Unloaded engines:")
                        for eid in result["unloaded"]:
                            print(f"    • {eid}")
                else:
                    print(f"❌ Error: {result['message']}")
            elif sys.argv[1] == "bcasl":
                workspace_dir = sys.argv[2] if len(sys.argv) > 2 else None
                sys.exit(launch_bcasl_standalone(workspace_dir))
            elif sys.argv[1] == "discover":
                discovered = WorkspaceManager.discover_workspaces()
                if discovered:
                    print("🔍 Discovered workspaces:")
                    for ws in discovered:
                        print(f"  • {ws}")
                else:
                    print("No workspaces discovered")
                sys.exit(0)
            elif sys.argv[1] == "unload":
                result = unload_all()
                if result["status"] == "success":
                    print(f"✅ {result['message']}")
                    if result["unloaded"]:
                        print("  Unloaded engines:")
                        for eid in result["unloaded"]:
                            print(f"    • {eid}")
                else:
                    print(f"❌ Error: {result['message']}")
                sys.exit(0 if result["status"] == "success" else 1)
            else:
                print(f"Unknown command: {sys.argv[1]}")
                print(__doc__)
                sys.exit(1)
        else:
            # No arguments: launch main application
            sys.exit(launch_main_application())

