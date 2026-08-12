from __future__ import annotations

import locale
import os
import platform
import re
import shutil
from collections.abc import Sequence
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

from ..Ui import output as output
import importlib.util
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Pathish = Union[str, Path]


# =================
# internet
# ================
def check_internet_connection(timeout: float = 3.0, retries: int = 0) -> bool:
    """
    Check if internet connection is available with high certainty.
    Prioritizes checking connectivity to essential services like PyPI.
    """
    import http.client
    import socket
    import time

    # Essential hosts to verify connectivity for tool installation
    # pypi.org is the most important one for pip installs
    hosts = ["pypi.org", "www.google.com", "www.cloudflare.com", "1.1.1.1"]

    for attempt in range(retries + 1):
        # Try each host
        for host in hosts:
            try:
                # If it looks like an IP, use direct connection
                if host[0].isdigit():
                    with socket.create_connection((host, 53), timeout=timeout):
                        return True
                else:
                    # For domains, try both resolution and a quick HTTP HEAD request
                    # This handles environments with DNS but no real internet egress
                    socket.gethostbyname(host)
                    conn = http.client.HTTPSConnection(host, timeout=timeout)
                    conn.request("HEAD", "/")
                    res = conn.getresponse()
                    conn.close()
                    if 200 <= res.status < 400:
                        return True
            except Exception:
                continue

        if attempt < retries:
            time.sleep(1.0)

    return False


@dataclass
class ToolsCheckResult:
    """Result of verification/installation of required tools."""

    ok: bool
    missing_system: list[str] = field(default_factory=list)
    missing_python: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _tools_stage_message(stage: str, fr: str, en: str) -> tuple[str, str]:
    prefix = f"[tools:{stage}] "
    return prefix + fr, prefix + en


# ===============
# install tools
# ================
def ensure_tools(
    required_tools: dict,
    stop_signal: Callable[[], bool] | None = None,
    log_cb: Callable[[str], None] | None = None,
    timeout_s: int = 300,
    gui: Any | None = None,
) -> ToolsCheckResult:
    """Checks and installs the required tools (system + Python).

    Args:
        required_tools: Dictionary ``{"python": [...], "system": [...]}``
        stop_signal: Callable without argument returning True to cancel
        log_cb: Callable(str) to emit progress messages (used if gui is absent)
        timeout_s: Global timeout in seconds (not used for pip, future guardrail)
        gui: Optional GUI or Bridge object for full UI support (VenvManager, SysDepsManager, etc.)

    Returns:
        ToolsCheckResult with ok=True if everything is available after installation."""

    missing_system: list[str] = []
    missing_python: list[str] = []
    errors: list[str] = []

    system_tools = [t for t in (required_tools.get("system") or []) if t]
    python_tools = [t for t in (required_tools.get("python") or []) if t]
    use_qt_gui_helpers = False
    if gui is not None:
        try:
            from PySide6.QtCore import QCoreApplication, QThread

            app = QCoreApplication.instance()
            use_qt_gui_helpers = (
                app is None or QThread.currentThread() == app.thread()
            )
        except Exception:
            use_qt_gui_helpers = False

    # ------------------------------------------------------------------ #
    # 1. System Tools #
    # ------------------------------------------------------------------ #
    if system_tools:
        if gui is not None and use_qt_gui_helpers:
            # GUI/Bridge system tools flow
            try:
                from pycompiler_ark.Core.SysDepsManager import (
                    SysDepsManager,
                    check_system_packages,
                )

                if hasattr(gui, "sys_deps_manager") and gui.sys_deps_manager:
                    sys_manager = gui.sys_deps_manager
                else:
                    sys_manager = SysDepsManager(gui)

                for tool in system_tools:
                    if stop_signal and stop_signal():
                        errors.append(
                            "Annulé par stop_signal (outils système)"
                        )
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=missing_python,
                            errors=errors,
                        )
                    if not check_system_packages([tool]):
                        missing_system.append(tool)

                if missing_system:
                    output.info(
                        *_tools_stage_message(
                            "system",
                            "Vérification de la connexion Internet...",
                            "Checking Internet connection...",
                        ),
                    )

                    if not check_internet_connection(timeout=4.0):
                        err_fr = "Pas de connexion Internet. Impossible d'installer les outils systeme manquants."
                        err_en = "No Internet connection. Cannot install missing system tools."
                        output.error(
                            *_tools_stage_message("system", err_fr, err_en),
                        )
                        errors.append(f"[ensure_tools:system] {err_en}")
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=missing_python,
                            errors=errors,
                        )

                    output.info(
                        *_tools_stage_message(
                            "system",
                            f"Installation des outils systeme manquants: {missing_system}",
                            f"Installing missing system tools: {missing_system}",
                        ),
                    )

                    import platform

                    system = platform.system().lower()

                    system_install_ok = True
                    if system == "linux":
                        process = sys_manager.install_packages_linux(
                            missing_system
                        )
                        if process:
                            timeout_total = 600000  # 10 minutes
                            elapsed = 0
                            interval = 500  # 0.5s
                            while not process.waitForFinished(interval):
                                if stop_signal and stop_signal():
                                    from .process_killer import (
                                        kill_process_tree,
                                    )

                                    try:
                                        kill_process_tree(process.processId())
                                    except Exception:
                                        pass
                                    errors.append(
                                        "Annulé par stop_signal pendant l'installation Linux"
                                    )
                                    return ToolsCheckResult(
                                        ok=False,
                                        missing_system=missing_system,
                                        missing_python=missing_python,
                                        errors=errors,
                                    )
                                elapsed += interval
                                if elapsed >= timeout_total:
                                    output.warn(
                                        *_tools_stage_message(
                                            "system",
                                            "Timeout lors de l'installation des outils systeme",
                                            "Timeout during system tools installation",
                                        ),
                                    )
                                    system_install_ok = False
                                    break

                            if system_install_ok:
                                if process.exitCode() == 0:
                                    output.success(
                                        *_tools_stage_message(
                                            "system",
                                            f"Outils systeme installes avec succes: {missing_system}",
                                            f"System tools installed successfully: {missing_system}",
                                        ),
                                    )
                                    missing_system = []
                                else:
                                    output.error(
                                        *_tools_stage_message(
                                            "system",
                                            f"Echec installation outils systeme: {missing_system} (code: {process.exitCode()})",
                                            f"System tools installation failed: {missing_system} (code: {process.exitCode()})",
                                        ),
                                    )
                                    system_install_ok = False
                        else:
                            # Fallback to headless
                            from pycompiler_ark.Core.SysDepsManager import (
                                install_system_packages,
                            )

                            output.info(
                                *_tools_stage_message(
                                    "system",
                                    "Tentative d'installation systeme en mode headless...",
                                    "Attempting headless system installation...",
                                ),
                            )
                            if install_system_packages(missing_system):
                                output.success(
                                    *_tools_stage_message(
                                        "system",
                                        "Installation systeme headless reussie.",
                                        "Headless system installation successful.",
                                    ),
                                )
                                missing_system = []
                            else:
                                output.error(
                                    *_tools_stage_message(
                                        "system",
                                        "Echec de l'installation systeme headless.",
                                        "Headless system installation failed.",
                                    ),
                                )
                                system_install_ok = False

                    elif system == "windows":
                        winget_packages = []
                        for tool in missing_system:
                            winget_map = {
                                "build-essential": [
                                    {
                                        "id": "Microsoft.VisualStudio.2022.BuildTools"
                                    }
                                ],
                                "gcc": [
                                    {
                                        "id": "Microsoft.VisualStudio.2022.BuildTools"
                                    }
                                ],
                                "g++": [
                                    {
                                        "id": "Microsoft.VisualStudio.2022.BuildTools"
                                    }
                                ],
                                "python3-dev": [{"id": "Python.Python.3"}],
                                "libpython3-dev": [{"id": "Python.Python.3"}],
                                "patchelf": [],
                            }
                            if tool in winget_map:
                                winget_packages.extend(winget_map[tool])
                            else:
                                winget_packages.append({"id": tool})

                        if winget_packages:
                            process = sys_manager.install_packages_windows(
                                winget_packages
                            )
                            if process:
                                timeout_total = 600000  # 10 minutes
                                elapsed = 0
                                interval = 500  # 0.5s
                                while not process.waitForFinished(interval):
                                    if stop_signal and stop_signal():
                                        from .process_killer import (
                                            kill_process_tree,
                                        )

                                        try:
                                            kill_process_tree(
                                                process.processId()
                                            )
                                        except Exception:
                                            pass
                                        errors.append(
                                            "Annulé par stop_signal pendant l'installation Windows"
                                        )
                                        return ToolsCheckResult(
                                            ok=False,
                                            missing_system=missing_system,
                                            missing_python=missing_python,
                                            errors=errors,
                                        )
                                    elapsed += interval
                                    if elapsed >= timeout_total:
                                        output.warn(
                                            *_tools_stage_message(
                                                "system",
                                                "Timeout lors de l'installation Windows",
                                                "Timeout during Windows installation",
                                            ),
                                        )
                                        system_install_ok = False
                                        break

                                if system_install_ok:
                                    if process.exitCode() == 0:
                                        output.success(
                                            *_tools_stage_message(
                                                "system",
                                                f"Outils Windows installes: {missing_system}",
                                                f"Windows tools installed: {missing_system}",
                                            ),
                                        )
                                        missing_system = []
                                    else:
                                        output.error(
                                            *_tools_stage_message(
                                                "system",
                                                f"Echec installation Windows: {missing_system}",
                                                f"Windows installation failed: {missing_system}",
                                            ),
                                        )
                                        system_install_ok = False
                            else:
                                output.warn(
                                    *_tools_stage_message(
                                        "system",
                                        "winget non disponible, installation manuelle requise",
                                        "winget not available, manual installation required",
                                    ),
                                )
                                try:
                                    sys_manager.open_urls(
                                        [
                                            "https://learn.microsoft.com/en-us/windows/package-manager/winget/"
                                        ]
                                    )
                                except Exception:
                                    pass
                                system_install_ok = False
                        else:
                            output.warn(
                                *_tools_stage_message(
                                    "system",
                                    f"Aucun equivalent Windows pour: {missing_system}",
                                    f"No Windows equivalent for: {missing_system}",
                                ),
                            )
                            system_install_ok = False
                    else:
                        output.warn(
                            *_tools_stage_message(
                                "system",
                                "Plateforme non supportee pour l'installation automatique",
                                "Platform not supported for automatic installation",
                            ),
                        )
                        system_install_ok = False

                    if not system_install_ok:
                        errors.append(
                            f"Échec installation outils système: {missing_system}"
                        )

                else:
                    output.success(
                        *_tools_stage_message(
                            "system",
                            f"Tous les outils systeme sont deja installes: {system_tools}",
                            f"All system tools are already installed: {system_tools}",
                        ),
                    )

            except Exception as e:
                err_msg = f"Erreur lors de la verification/installation des outils systeme: {e}"
                output.warn(
                    *_tools_stage_message(
                        "system",
                        err_msg,
                        f"Error checking/installing system tools: {e}",
                    ),
                )
                errors.append(err_msg)

        else:
            # Original headless system tools check & installation flow
            try:
                from .SysDepsManager import (
                    check_system_packages,
                    install_system_packages,
                )
            except ImportError as exc:
                err = f"[ensure_tools] Import headless impossible : {exc}"
                errors.append(err)
                output.error("error", err, err)
                return ToolsCheckResult(ok=False, errors=errors)

            for tool in system_tools:
                if stop_signal and stop_signal():
                    errors.append("Annulé par stop_signal (outils système)")
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=missing_python,
                        errors=errors,
                    )
                if not check_system_packages([tool]):
                    missing_system.append(tool)

            if missing_system:
                output.info(
                    f"[ensure_tools:system] Outils manquants : {missing_system}",
                    f"[ensure_tools:system] Missing tools: {missing_system}",
                )
                output.info(
                    "[ensure_tools:system] Vérification de la connexion Internet…",
                    "[ensure_tools:system] Checking Internet connection...",
                )

                if not check_internet_connection(timeout=4.0):
                    err = "[ensure_tools:system] Pas de connexion Internet — installation impossible."
                    errors.append(err)
                    output.error("error", err, err)
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=missing_python,
                        errors=errors,
                    )

                output.info(
                    f"[ensure_tools:system] Installation de {missing_system}…",
                    f"[ensure_tools:system] Installing {missing_system}...",
                )
                if install_system_packages(missing_system):
                    output.success(
                        "[ensure_tools:system] Installation réussie.",
                        "[ensure_tools:system] Installation successful.",
                    )
                    missing_system = []
                else:
                    err = f"[ensure_tools:system] Échec installation : {missing_system}"
                    errors.append(err)
                    output.error("error", err, err)
            else:
                output.success(
                    f"[ensure_tools:system] Tous présents : {system_tools}",
                    f"[ensure_tools:system] All present: {system_tools}",
                )

    # ------------------------------------------------------------------ #
    # 2. Outils Python                                                     #
    # ------------------------------------------------------------------ #
    if python_tools:
        if (
            gui is not None
            and hasattr(gui, "venv_manager")
            and gui.venv_manager
        ):
            try:
                use_system = bool(getattr(gui, "use_system_python", False))

                if use_system:
                    for tool in python_tools:
                        if not gui.venv_manager.is_tool_installed_system(tool):
                            missing_python.append(tool)

                    if missing_python:
                        output.info(
                            *_tools_stage_message(
                                "python",
                                "Vérification de la connexion Internet...",
                                "Checking Internet connection...",
                            ),
                        )

                        if not check_internet_connection(timeout=4.0):
                            output.error(
                                *_tools_stage_message(
                                    "python",
                                    "Pas de connexion Internet. Impossible d'installer les outils Python manquants.",
                                    "No Internet connection. Cannot install missing Python tools.",
                                ),
                            )
                            errors.append(
                                "Pas de connexion Internet (outils Python système)"
                            )
                            return ToolsCheckResult(
                                ok=False,
                                missing_system=missing_system,
                                missing_python=missing_python,
                                errors=errors,
                            )

                        output.info(
                            *_tools_stage_message(
                                "python",
                                f"Installation des outils Python manquants: {missing_python}",
                                f"Installing missing Python tools: {missing_python}",
                            ),
                        )
                        gui.venv_manager.ensure_tools_installed_system(
                            missing_python
                        )

                        # Wait for Python tools to be installed on system
                        timeout_total = 600000  # 10 minutes
                        elapsed = 0
                        interval = 1000  # 1s
                        all_done = False
                        while elapsed < timeout_total:
                            if stop_signal and stop_signal():
                                errors.append(
                                    "Annulé par stop_signal pendant l'installation Python (système)"
                                )
                                return ToolsCheckResult(
                                    ok=False,
                                    missing_system=missing_system,
                                    missing_python=missing_python,
                                    errors=errors,
                                )

                            # Check if all are installed
                            all_done = True
                            for tool in missing_python:
                                if not gui.venv_manager.is_tool_installed_system(
                                    tool
                                ):
                                    all_done = False
                                    break
                            if all_done:
                                break

                            time.sleep(interval / 1000.0)
                            elapsed += interval

                        if not all_done:
                            output.warn(
                                *_tools_stage_message(
                                    "python",
                                    "Timeout ou echec de l'installation des outils Python (systeme)",
                                    "Timeout or failure installing system Python tools",
                                ),
                            )
                            errors.append(
                                "Timeout ou échec de l'installation des outils Python (système)"
                            )
                            missing_python = [
                                t
                                for t in missing_python
                                if not gui.venv_manager.is_tool_installed_system(
                                    t
                                )
                            ]
                        else:
                            missing_python = []
                else:
                    venv_path = gui.venv_manager.resolve_project_venv()
                    if venv_path:
                        for tool in python_tools:
                            if not gui.venv_manager.is_tool_installed(
                                venv_path, tool
                            ):
                                missing_python.append(tool)

                        if missing_python:
                            output.info(
                                *_tools_stage_message(
                                    "python",
                                    "Vérification de la connexion Internet...",
                                    "Checking Internet connection...",
                                ),
                            )

                            if not check_internet_connection(timeout=4.0):
                                output.error(
                                    *_tools_stage_message(
                                        "python",
                                        "Pas de connexion Internet. Impossible d'installer les outils Python manquants.",
                                        "No Internet connection. Cannot install missing Python tools.",
                                    ),
                                )
                                errors.append(
                                    "Pas de connexion Internet (outils Python venv)"
                                )
                                return ToolsCheckResult(
                                    ok=False,
                                    missing_system=missing_system,
                                    missing_python=missing_python,
                                    errors=errors,
                                )

                            output.info(
                                *_tools_stage_message(
                                    "python",
                                    f"Installation des outils Python manquants: {missing_python}",
                                    f"Installing missing Python tools: {missing_python}",
                                ),
                            )
                            gui.venv_manager.ensure_tools_installed(
                                venv_path, missing_python
                            )

                            # Wait for Python tools to be installed
                            timeout_total = 600000  # 10 minutes
                            elapsed = 0
                            interval = 1000  # 1s
                            all_done = False
                            while elapsed < timeout_total:
                                if stop_signal and stop_signal():
                                    errors.append(
                                        "Annulé par stop_signal pendant l'installation Python (venv)"
                                    )
                                    return ToolsCheckResult(
                                        ok=False,
                                        missing_system=missing_system,
                                        missing_python=missing_python,
                                        errors=errors,
                                    )

                                # Check if all are installed
                                all_done = True
                                for tool in missing_python:
                                    if not gui.venv_manager.is_tool_installed(
                                        venv_path, tool
                                    ):
                                        all_done = False
                                        break
                                if all_done:
                                    break

                                time.sleep(interval / 1000.0)
                                elapsed += interval

                            if not all_done:
                                output.warn(
                                    *_tools_stage_message(
                                        "python",
                                        "Timeout ou echec de l'installation des outils Python",
                                        "Timeout or failure installing Python tools",
                                    ),
                                )
                                errors.append(
                                    "Timeout ou échec de l'installation des outils Python (venv)"
                                )
                                missing_python = [
                                    t
                                    for t in missing_python
                                    if not gui.venv_manager.is_tool_installed(
                                        venv_path, t
                                    )
                                ]
                            else:
                                missing_python = []
            except Exception as e:
                err_msg = f"Erreur lors de la verification/installation des outils Python: {e}"
                output.warn(
                    *_tools_stage_message(
                        "python",
                        err_msg,
                        f"Error checking/installing Python tools: {e}",
                    ),
                )
                errors.append(err_msg)
        else:
            # Original headless Python tools check & installation flow
            for tool in python_tools:
                if stop_signal and stop_signal():
                    errors.append("Annulé par stop_signal (outils Python)")
                    return ToolsCheckResult(
                        ok=False,
                        missing_system=missing_system,
                        missing_python=missing_python,
                        errors=errors,
                    )
                spec_name = tool.replace("-", "_").split("[")[0]
                if importlib.util.find_spec(spec_name) is None:
                    missing_python.append(tool)

            if missing_python:
                output.info(
                    f"[ensure_tools:python] Paquets manquants : {missing_python}",
                    f"[ensure_tools:python] Missing packages: {missing_python}",
                )

                try:
                    output.info(
                        "[ensure_tools:python] Vérification de la connexion Internet…",
                        "[ensure_tools:python] Checking Internet connection...",
                    )
                    if not check_internet_connection(timeout=4.0):
                        err = "[ensure_tools:python] Pas de connexion Internet — installation impossible."
                        errors.append(err)
                        output.error("error", err, err)
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=missing_python,
                            errors=errors,
                        )
                except ImportError:
                    pass

                still_missing: list[str] = []
                for pkg in missing_python:
                    if stop_signal and stop_signal():
                        errors.append("Annulé par stop_signal (pip install)")
                        return ToolsCheckResult(
                            ok=False,
                            missing_system=missing_system,
                            missing_python=still_missing
                            + missing_python[len(still_missing) :],
                            errors=errors,
                        )
                    output.info(
                        f"[ensure_tools:python] pip install {pkg}…",
                        f"[ensure_tools:python] pip install {pkg}...",
                    )
                    try:
                        result = subprocess.run(
                            [sys.executable, "-m", "pip", "install", pkg],
                            capture_output=True,
                            text=True,
                            timeout=timeout_s,
                        )
                        if result.returncode == 0:
                            output.success(
                                f"[ensure_tools:python] {pkg} installé avec succès.",
                                f"[ensure_tools:python] {pkg} installed successfully.",
                            )
                        else:
                            err = f"[ensure_tools:python] Échec pip install {pkg} : {result.stderr.strip()}"
                            errors.append(err)
                            output.error("error", err, err)
                            still_missing.append(pkg)
                    except subprocess.TimeoutExpired:
                        err = (
                            f"[ensure_tools:python] Timeout pip install {pkg}"
                        )
                        errors.append(err)
                        output.error("error", err, err)
                        still_missing.append(pkg)
                    except Exception as exc:
                        err = f"[ensure_tools:python] Erreur pip install {pkg} : {exc}"
                        errors.append(err)
                        output.error("error", err, err)
                        still_missing.append(pkg)

                missing_python = still_missing
            else:
                output.success(
                    f"[ensure_tools:python] Tous présents : {python_tools}",
                    f"[ensure_tools:python] All present: {python_tools}",
                )

    ok = not missing_system and not missing_python and not errors
    return ToolsCheckResult(
        ok=ok,
        missing_system=missing_system,
        missing_python=missing_python,
        errors=errors,
    )


# ======================
#
# Executor
#
# =======================


@dataclass
class ExecutionResult:
    """Structured result of a function execution."""

    success: bool
    value: Any | None = None
    error: str = ""
    duration_ms: float = 0.0
    name: str = ""


def _emit_log(
    log_callback: Optional[Callable[[str], None]], message: str
) -> None:
    """Emit a log line via callback if one was provided."""
    if log_callback is None:
        return
    try:
        log_callback(message)
    except Exception:
        pass


def _check_stop(stop_requested: Optional[Callable[[], bool]]) -> bool:
    """Return True if the caller requested a stop."""
    if stop_requested is None:
        return False
    try:
        return bool(stop_requested())
    except Exception:
        return False


def executor(
    func: Callable,
    *args,
    name: Optional[str] = None,
    stop_requested: Optional[Callable[[], bool]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    catch_exceptions: bool = True,
    **kwargs,
) -> ExecutionResult:
    """Execute ``func(*args, **kwargs)`` and return a structured result.
    It can be used to run any callable with uniform error handling, timing and
    logging.

    Args:
        func: The callable to execute.
        *args: Positional arguments passed to ``func``.
        name: Optional display name used in logs and in the returned result.
              Defaults to ``func.__name__``.
        stop_requested: Optional callable returning ``True`` when execution
            should be cancelled. Checked before starting and can be polled
            inside long-running ``func`` implementations if they accept it.
        log_callback: Optional callable receiving log lines.
        catch_exceptions: If ``True`` (default), exceptions are caught and
            returned as a failed ``ExecutionResult``. If ``False``, exceptions
            propagate normally.
        **kwargs: Keyword arguments passed to ``func``.

    Returns:
        ``ExecutionResult`` describing the outcome of the call.
    """
    task_name = name or getattr(func, "__name__", repr(func))

    if _check_stop(stop_requested):
        msg = f"Cancelled before start: {task_name}"
        _emit_log(log_callback, msg)
        output.info(msg)
        return ExecutionResult(
            success=False,
            error="Execution cancelled before start",
            name=task_name,
        )

    msg = f"Start: {task_name}"
    _emit_log(log_callback, msg)
    output.info(msg)
    start = time.perf_counter()

    try:
        value = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000.0
        _emit_log(
            log_callback,
            f"Success: {task_name} ({duration_ms:.1f} ms)",
        )
        output.success(
            f" {task_name} ({duration_ms:.1f} ms)",
        )
        return ExecutionResult(
            success=True,
            value=value,
            duration_ms=duration_ms,
            name=task_name,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000.0
        error_message = str(exc)
        _emit_log(
            log_callback,
            f"Failure: {task_name} - {error_message}",
        )
        output.error(
            f" {task_name} - {error_message}",
        )
        if not catch_exceptions:
            raise
        return ExecutionResult(
            success=False,
            error=error_message,
            duration_ms=duration_ms,
            name=task_name,
        )


def open_path(path: Pathish) -> bool:
    """Open a file or directory with the OS default handler. Returns True on attempt."""
    try:
        p = str(path)
        sysname = platform.system()
        if sysname == "Windows":
            os.startfile(p)  # type: ignore[attr-defined]
        elif sysname == "Linux":
            import subprocess

            subprocess.run(["xdg-open", p])
        else:
            import subprocess

            subprocess.run(["open", p])
        return True
    except Exception:
        return False


def get_interpreter_version(
    python_path: Optional[str] = None,
) -> Tuple[int, int, int]:
    """Return Python interpreter version (major, minor, patch)"""
    if python_path is None:
        python_path = sys.executable

    try:
        result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version_str = result.stdout or result.stderr
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
    except Exception:
        pass

    return (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )


def get_interpreter_version_str(python_path: Optional[str] = None) -> str:
    """Return Python interpreter version as a string."""
    v = get_interpreter_version(python_path)
    return f"{v[0]}.{v[1]}.{v[2]}"


def check_module_available(
    module_name: str, python_path: Optional[str] = None
) -> bool:
    """Check whether a Python module is available.

    Args:
     module_name: Module name
     python_path: Path of the interpreter

    Returns:
     True if the module is available"""
    try:
        if python_path:
            result = subprocess.run(
                [python_path, "-c", f"import {module_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        else:
            import importlib

            importlib.import_module(module_name)
            return True
    except Exception:
        return False
