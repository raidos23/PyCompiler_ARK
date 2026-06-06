from __future__ import annotations

import faulthandler
import logging
import os
import platform
import signal
import sys
import traceback
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parents[2]

IS_WINDOWS = os.name == "nt" or platform.system().lower().startswith("win")
IS_DARWIN = platform.system().lower().startswith("darwin")
IS_LINUX = platform.system().lower().startswith("linux")

_crash_log: Optional[Path] = None


def ensure_sys_path() -> None:
    root = str(ROOT_DIR)
    if root not in sys.path[:1]:
        sys.path.insert(0, root)


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def configure_env() -> None:
    if not os.environ.get("PYCOMPILER_VERBOSE"):
        os.environ.setdefault(
            "QT_LOGGING_RULES",
            "qt.qpa.*=false;qt.quick.*=false;qt.scenegraph.*=false;qt.*.debug=false;qt.*.info=false;qt.gui.*.warning=false;qt.widgets.*.warning=false",
        )

    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    if IS_LINUX:
        os.environ.setdefault("QT_WAYLAND_DISABLE_FRACTIONAL_SCALE", "1")
        if not os.environ.get("LC_ALL") and not os.environ.get("LANG"):
            os.environ["LC_ALL"] = "C.UTF-8"

    if IS_DARWIN:
        os.environ.setdefault("QT_MAC_WANTS_LAYER", "1")
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


def _platform_log_dir() -> Path:
    """
    Return the log directory.
    Aligned with the global config directory dit in Ui/PreferencesManager.py.
    """
    try:
        # Try to use the global config directory defined in PreferencesManager
        from pycompiler_ark.Ui.PreferencesManager import _user_config_dir

        return Path(_user_config_dir()) / "logs"
    except Exception:
        # Robust fallback to ~/.PyCompiler_ARK/logs
        try:
            return Path("~/.PyCompiler_ARK/logs").expanduser()
        except Exception:
            # Last resort fallbacks
            try:
                return ROOT_DIR / "logs"
            except Exception:
                return Path.cwd() / "logs"


def enable_faulthandler() -> Optional[Path]:
    global _crash_log
    try:
        log_dir = _platform_log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_log = log_dir / "crash.log"
        try:
            fp = open(crash_log, "a", encoding="utf-8", errors="ignore")
            faulthandler.enable(fp)  # type: ignore[arg-type]
        except Exception:
            faulthandler.enable()
        _crash_log = crash_log
        return crash_log
    except Exception:
        try:
            faulthandler.enable()
        except Exception:
            pass
    return None


def install_qt_metadata(app_version: str) -> None:
    try:
        from PySide6.QtCore import QCoreApplication

        QCoreApplication.setOrganizationName("raidos23")
        QCoreApplication.setOrganizationDomain("pycompiler.local")
        QCoreApplication.setApplicationName("PyCompiler ARK")
        QCoreApplication.setApplicationVersion(app_version)
    except Exception:
        pass


def _qt_message_handler(mode, _context, message) -> None:
    from PySide6.QtCore import QtMsgType

    suppressed = (not os.environ.get("PYCOMPILER_VERBOSE")) and mode in (
        QtMsgType.QtWarningMsg,
        QtMsgType.QtInfoMsg,
        QtMsgType.QtDebugMsg,
    )
    try:
        txt = (message or "") + "\n"
        if _crash_log is not None:
            with open(_crash_log, "a", encoding="utf-8", errors="ignore") as f:
                f.write(txt)
    except Exception:
        pass
    if suppressed:
        return
    try:
        sys.__stderr__.write(txt)
    except Exception:
        pass


def _excepthook(etype, value, tb) -> None:
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
            if _crash_log is not None:
                with open(_crash_log, "a", encoding="utf-8", errors="ignore") as f:
                    f.write(msg)
        except Exception:
            pass
    finally:
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass
        os._exit(1)


def install_qt_handlers() -> None:
    try:
        from PySide6.QtCore import qInstallMessageHandler

        qInstallMessageHandler(_qt_message_handler)
    except Exception:
        pass
    sys.excepthook = _excepthook


def install_signal_handlers() -> None:
    def _handle_signal(_signum, _frame) -> None:
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception:
            pass

    for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
        try:
            if sig is not None:
                signal.signal(sig, _handle_signal)
        except Exception:
            pass

    if IS_WINDOWS and hasattr(signal, "SIGBREAK"):
        try:
            signal.signal(signal.SIGBREAK, _handle_signal)  # type: ignore[attr-defined]
        except Exception:
            pass


def handle_fatal(exc_info) -> None:
    _excepthook(*exc_info)


def should_enable_qt(argv: list[str] | None) -> bool:
    args = list(argv or [])
    if not args:
        return True

    if any(flag in args for flag in ("--help", "-h", "--version", "-v")):
        return False

    cmd = None
    for token in args:
        if not token.startswith("-"):
            cmd = token
            break

    if cmd is None:
        return True

    headless_commands = {"build", "init", "list", "set", "get", "unset", "scaffold"}
    if cmd == "run":
        return False
    if cmd == "gui":
        return True
    if cmd in headless_commands:
        return False
    return False


def is_cli_mode() -> bool:
    """True when PyCompiler ARK runs as a terminal CLI (no Qt UI for plugins/dialogs)."""
    try:
        v = os.environ.get("PYCOMPILER_CLI")
        if v is None:
            return False
        return str(v).strip().lower() not in ("", "0", "false", "no")
    except Exception:
        return False


def is_noninteractive() -> bool:
    """True when prompts must not block (CI, headless plugin workers, etc.)."""
    try:
        v = os.environ.get("PYCOMPILER_NONINTERACTIVE")
        if v is None:
            return False
        return str(v).strip().lower() not in ("", "0", "false", "no")
    except Exception:
        return False


def use_rich_dialogs() -> bool:
    """Use Rich console dialogs instead of Qt message boxes (for PyCompiler ARK)."""
    return is_cli_mode() or is_noninteractive()


def install_runtime(app_version: str, enable_qt: bool = True) -> None:
    ensure_sys_path()
    configure_logging()
    configure_env()
    enable_faulthandler()
    if enable_qt:
        os.environ.pop("PYCOMPILER_CLI", None)
        install_qt_metadata(app_version)
        install_qt_handlers()
    else:
        os.environ["PYCOMPILER_CLI"] = "1"
    install_signal_handlers()
