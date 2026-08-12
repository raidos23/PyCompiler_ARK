"""Provide core utilities and workflows for this module."""

import hashlib
import os
import platform
import shutil
import subprocess
import sys
from typing import Any

import pycompiler_ark.Core.deps_analyser as deps_analyser
import pycompiler_ark.Core.SysDepsManager as sys_deps

from ...Ui import output as output
from ..globals import WORKSPACE_CONFIG_DIRNAME
from .config import VenvManagerConfig
from .executor import ExecutorFactory, PythonModuleExecutor, ExecutableExecutor


class VenvManager:
    """
    Encapsulates all virtual environment (venv) related operations.

    Responsibilities:
    - Manual venv selection
    - Create venv if missing
    - Check/install tools in an existing venv
    - Install project requirements.txt
    - Report/terminate active background tasks related to venv operations
    """

    def __init__(self, parent_widget):
        """Initialize instance state and runtime dependencies."""
        self.parent = parent_widget
        # QProcess references for graceful termination
        self._venv_create_process = None
        self._venv_check_process = None
        self._venv_check_install_process = None
        self._req_install_process = None
        # Marker for requirements checksum to avoid redundant installs
        self._req_marker_path = None
        self._req_marker_hash = None
        # State for pip three-phase (ensurepip -> upgrade -> install)
        self._pip_phase = None  # 'ensurepip' | 'upgrade' | 'install'
        self._venv_python_exe = None
        self._req_path = None

        # State for ongoing operations
        self._venv_progress_lines = 0
        self._pip_progress_lines = 0

        # For tool check/installation
        self._venv_check_pkgs = []
        self._venv_check_sys_pkgs = []
        self._venv_check_index = 0
        self._venv_check_pip_exe = None
        self._venv_check_pip_args = []
        self._venv_check_path = None
        self._venv_check_use_python = False

        # Progress state management handled via UI callbacks
        # (venv_progress_dialog, venv_check_progress, progress_dialog removed)

        # Internal timers to enforce timeouts on background processes
        self._proc_timers: list = []

        # Retry counters for resilience
        self._venv_check_retries = {}
        self._max_retries = 2

        # Encoding detection for subprocess output
        self._output_encoding = "utf-8"
        self._fallback_encodings = ["utf-8", "latin-1", "cp1252", "ascii"]

        # Environment manager detection is driven by YAML configuration.
        self._config = VenvManagerConfig()
        self._detected_manager = self._config.get_default_manager()
        self._manager_commands = self._get_manager_commands()
        # Cache for auto-selected venv per workspace
        self._auto_venv_cache: dict[str, str] = {}
        # User-driven cancellation flag for long-running async flows
        self._cancel_requested = False

    # ---------- Manager mapping from YAML ----------
    def _get_manager_commands(self) -> dict[str, dict[str, list[str]]]:
        """Return commands from the YAML configuration for all available managers."""
        commands: dict[str, dict[str, list[str]]] = {}
        for manager_name in self._config.get_available_managers():
            commands[manager_name] = self._config.get_commands(manager_name)
        return commands

    def _get_executor_config(
        self, manager: str, action: str | None = None
    ) -> dict:
        """Get executor config (type / module / executable) from VenvManagerConfig."""
        try:
            cfg = self._config.get_executor(manager, action=action)
            if isinstance(cfg, dict) and cfg:
                return cfg
        except Exception:
            pass
        raise ValueError(f"Missing executor config for manager '{manager}'")

    def _resolve_manager_venv_path(
        self, workspace_dir: str | None = None
    ) -> str | None:
        """Resolve the venv path from the active manager YAML definition."""
        try:
            base = workspace_dir or getattr(self.parent, "workspace_dir", None)
            if not base:
                return None
            base = os.path.abspath(base)
            manager = self.resolve_workspace_manager(base)
            if not manager:
                return None
            return self._config.resolve_venv_path(
                manager,
                base,
                python_interpreter=self._venv_python_exe or sys.executable,
            )
        except Exception:
            return None

    def _prepare_manager_command(
        self,
        action: str,
        extra_args: list[str] | None = None,
        python_exe: str | None = None,
        kwargs: dict[str, str] | None = None,
    ) -> tuple[str, list[str]]:
        """
        build (program, arguments) from executor + commands of YAML file using ExecutorFactory.

        - executor.type == "python_module"  ->  <python> -m <module> <args...>
        - executor.type == "executable"     ->  <executable> <args...>
        """
        extra_args = list(extra_args or [])
        manager = (
            self._detected_manager
            if isinstance(getattr(self, "_detected_manager", None), str)
            and self._detected_manager
            else self._config.get_default_manager()
        )
        if not manager:
            raise ValueError("No environment manager configured")

        cmd_args = self._get_manager_command(manager, action)
        if not cmd_args:
            raise ValueError(
                f"Missing command config for manager '{manager}' and action '{action}'"
            )

        resolved_args = []
        fmt_vars = kwargs or {}
        for arg in cmd_args:
            formatted_arg = str(arg)
            for k, v in fmt_vars.items():
                formatted_arg = formatted_arg.replace(f"{{{k}}}", str(v))
            resolved_args.append(formatted_arg)

        if extra_args:
            resolved_args.extend(extra_args)

        executor_cfg = self._get_executor_config(manager, action=action)
        python_interpreter = (
            python_exe
            or getattr(self, "_venv_python_exe", None)
            or sys.executable
        )

        executor = ExecutorFactory.create(executor_cfg, python_interpreter)
        return executor.build_command(resolved_args)

    # ---------- UI / Event Hooks (Overridden by UI Layer) ----------
    def _tr(self, fr: str, en: str) -> str:
        """Translation helper (overridden by UI layer)."""
        return en

    def tr(self, fr: str, en: str) -> str:
        """Translation helper using UI hook or fallback to English."""
        return self._tr(fr, en)

    def _on_pref_applied(self, mode: str, venv_path: str | None) -> None:
        """Hook called when preference is applied (overridden by UI layer)."""
        pass

    def _show_progress(self, id: str, title: str, cancel_label: str) -> None:
        """Hook to display progress (overridden by UI layer)."""
        pass

    def _update_progress_message(self, id: str, message: str) -> None:
        """Hook to update progress message (overridden by UI layer)."""
        pass

    def _update_progress_progress(
        self, id: str, value: int, total: int
    ) -> None:
        """Hook to update progress bar value (overridden by UI layer)."""
        pass

    def _close_progress(self, id: str) -> None:
        """Hook to close progress indicator (overridden by UI layer)."""
        pass

    def _is_progress_visible(self, id: str) -> bool:
        """Hook to check if progress is visible (overridden by UI layer)."""
        return False

    def _bind_cancel(self, id: str, callback) -> None:
        """Hook to bind cancel action (overridden by UI layer)."""
        pass

    def _process_events(self) -> None:
        """Hook to process UI events (overridden by UI layer)."""
        pass

    def _ask_recreate_invalid_venv(self, venv_root: str, reason: str) -> bool:
        """Hook to prompt user for venv recreation (overridden by UI layer)."""
        return False

    def _show_error_dialog(self, title: str, text: str) -> None:
        """Hook to display error dialog (overridden by UI layer)."""
        pass

    def _create_process(self):
        """Create a process instance (overridden by UI layer or fallback)."""
        try:
            from PySide6.QtCore import QProcess

            return QProcess(self.parent)
        except Exception:
            return None

    # ---------- Workspace pref management ----------
    def _workspace_pref_path(self, workspace_dir: str) -> str:
        """Return the resolved workspace path information."""
        return os.path.join(
            os.path.abspath(workspace_dir),
            WORKSPACE_CONFIG_DIRNAME,
            "pref.json",
        )

    def _read_workspace_pref(self, workspace_dir: str) -> dict | None:
        """Execute _read_workspace_pref logic for this component."""
        try:
            path = self._workspace_pref_path(workspace_dir)
            if not os.path.isfile(path):
                return None
            with open(path, encoding="utf-8") as f:
                import json

                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _write_workspace_pref(self, workspace_dir: str, data: dict) -> None:
        """Execute _write_workspace_pref logic for this component."""
        try:
            path = self._workspace_pref_path(workspace_dir)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            import json

            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    def resolve_workspace_manager(self, workspace_dir: str) -> str:
        """Resolve environment manager for workspace (User Pref -> Dynamic Detection -> YAML default)."""
        if workspace_dir:
            pref_data = self._read_workspace_pref(workspace_dir)
            if pref_data and isinstance(pref_data, dict):
                saved_mgr = pref_data.get("manager")
                if (
                    isinstance(saved_mgr, str)
                    and saved_mgr in self._config.get_available_managers()
                ):
                    self._detected_manager = saved_mgr
                    return saved_mgr

            detected = self._config.detect_manager_for_workspace(workspace_dir)
            if detected:
                self._detected_manager = detected
                return detected

        default_mgr = self._config.get_default_manager()
        if not default_mgr:
            raise ValueError("No environment manager configured in YAML")
        self._detected_manager = default_mgr
        return default_mgr

    def apply_workspace_pref(self, workspace_dir: str) -> bool:
        """Apply saved venv/system selection from .ark/pref.json if available."""
        try:
            self.resolve_workspace_manager(workspace_dir)
            data = self._read_workspace_pref(workspace_dir)
            if not data:
                return False
            mode = str(data.get("venv_mode", "")).strip().lower()
            venv_path = data.get("venv_path")

            applied = False
            if mode == "system":
                try:
                    setattr(self.parent, "use_system_python", True)
                    applied = True
                except Exception:
                    pass
                try:
                    self.parent.venv_path_manuel = None
                except Exception:
                    pass
            elif mode == "venv" and isinstance(venv_path, str) and venv_path:
                venv_path = os.path.abspath(venv_path)
                ok, _ = self.validate_venv_strict(venv_path)
                if ok:
                    try:
                        setattr(self.parent, "use_system_python", False)
                        applied = True
                    except Exception:
                        pass
                    try:
                        self.parent.venv_path_manuel = venv_path
                    except Exception:
                        pass
                else:
                    self._clear_workspace_pref(workspace_dir)

            if applied:
                self._on_pref_applied(mode, venv_path)
                return True
            return False
        except Exception:
            return False

    def save_workspace_pref(self, workspace_dir: str | None) -> None:
        """Persist current venv/system selection for a workspace."""
        if not workspace_dir:
            return
        try:
            pref_data = self._read_workspace_pref(workspace_dir) or {}
            pref_data["manager"] = self._detected_manager
            if getattr(self.parent, "use_system_python", False):
                pref_data.update({"venv_mode": "system", "venv_path": None})
                self._write_workspace_pref(workspace_dir, pref_data)
                return
            venv_path = getattr(self.parent, "venv_path_manuel", None)
            if not venv_path and hasattr(self.parent, "venv_path"):
                venv_path = getattr(self.parent, "venv_path", None)

            if venv_path:
                pref_data.update(
                    {
                        "venv_mode": "venv",
                        "venv_path": os.path.abspath(venv_path),
                    }
                )
                self._write_workspace_pref(workspace_dir, pref_data)
                return
        except Exception:
            pass
        self._clear_workspace_pref(workspace_dir)

    def _clear_workspace_pref(self, workspace_dir: str) -> None:
        """Clear the related cached state or UI values."""
        try:
            path = self._workspace_pref_path(workspace_dir)
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass

    # ---------- Public helpers for engines ----------
    def resolve_existing_venv(
        self, workspace_dir: str | None = None
    ) -> str | None:
        """Resolve an existing venv path from the manager definition."""
        try:
            if getattr(self.parent, "use_system_python", False):
                return None

            manual = getattr(self.parent, "venv_path_manuel", None)
            if manual:
                manual = os.path.abspath(manual)
                if (
                    os.path.isdir(manual)
                    and self.validate_venv_strict(manual)[0]
                ):
                    return manual
                return None

            base = workspace_dir or getattr(self.parent, "workspace_dir", None)
            if not base:
                return None
            base = os.path.abspath(base)

            try:
                if self.apply_workspace_pref(base):
                    if getattr(self.parent, "use_system_python", False):
                        return None
                    manual = getattr(self.parent, "venv_path_manuel", None)
                    if manual:
                        manual = os.path.abspath(manual)
                        if (
                            os.path.isdir(manual)
                            and self.validate_venv_strict(manual)[0]
                        ):
                            return manual
            except Exception:
                pass

            resolved = self._resolve_manager_venv_path(base)
            if resolved and os.path.isdir(resolved):
                ok, _ = self.validate_venv_strict(resolved)
                if ok:
                    return resolved
        except Exception:
            return None
        return None

    def resolve_project_venv(self) -> str | None:
        """Resolve the manager-defined venv path for the active workspace."""
        try:
            if getattr(self.parent, "use_system_python", False):
                return None
            manual = getattr(self.parent, "venv_path_manuel", None)
            if manual:
                return os.path.abspath(manual)
            if getattr(self.parent, "workspace_dir", None):
                base = os.path.abspath(self.parent.workspace_dir)
                return self._resolve_manager_venv_path(base)
        except Exception:
            return None
        return None

    def pip_path(self, venv_root: str) -> str:
        """Get the absolute path to the pip executable using deps_analyser."""
        pip_exe, _ = deps_analyser._find_pip_executable(venv_path=venv_root)
        return pip_exe

    def python_path(self, venv_root: str) -> str:
        """Get the absolute path to the python executable using deps_analyser."""
        pip_exe, pip_args = deps_analyser._find_pip_executable(
            venv_path=venv_root
        )
        if "-m" in pip_args and "pip" in pip_args:
            return pip_exe
        # Fallback to internal detection if pip_exe is directly the pip binary
        base = os.path.join(
            venv_root, "Scripts" if platform.system() == "Windows" else "bin"
        )
        if platform.system() == "Windows":
            return os.path.join(base, "python.exe")
        cand1 = os.path.join(base, "python")
        cand2 = os.path.join(base, "python3")
        return cand1 if os.path.isfile(cand1) else cand2

    def _using_system_python(self) -> bool:
        """Execute _using_system_python logic for this component."""
        try:
            return bool(getattr(self.parent, "use_system_python", False))
        except Exception:
            return False

    def _is_cli_mode(self) -> bool:
        """Return whether the manager runs in CLI/synchronous mode."""
        try:
            if bool(getattr(self.parent, "_cli_mode", False)):
                return True
        except Exception:
            pass
        try:
            return os.environ.get("PYCOMPILER_CLI") == "1"
        except Exception:
            return False

    def _pip_break_system_args(self) -> list[str]:
        """Execute _pip_break_system_args logic for this component."""
        if self._using_system_python() and platform.system() == "Linux":
            return ["--break-system-packages"]
        return []

    def _tools_stage_prefix(self) -> str:
        """Execute _tools_stage_prefix logic for this component."""
        return "[tools:python] "

    def has_tool_binary(self, venv_root: str, tool: str) -> bool:
        """Non-blocking heuristic check: detect console script/binary inside the venv.
        This avoids spawning subprocesses and keeps UI fully responsive.
        """
        try:
            bindir = os.path.join(
                venv_root,
                "Scripts" if platform.system() == "Windows" else "bin",
            )
            if not os.path.isdir(bindir):
                return False
            raw = str(tool or "").strip()
            if not raw:
                return False
            lower = raw.lower()
            variants = {lower}
            if "_" in lower:
                variants.add(lower.replace("_", "-"))
                variants.add(lower.replace("_", ""))
            if "-" in lower:
                variants.add(lower.replace("-", "_"))
                variants.add(lower.replace("-", ""))
            variants.add(f"{lower}3")

            names: list[str] = []
            for name in sorted(variants):
                names.extend([name, f"{name}.exe", f"{name}-script.py"])
            for n in names:
                p = os.path.join(bindir, n)
                if os.path.isfile(p):
                    try:
                        return os.access(p, os.X_OK) or p.endswith(".py")
                    except Exception:
                        return True
            return False
        except Exception:
            return False

    def _discover_engine_requirements(self) -> dict[str, list[str]]:
        """Discover tools required by available engines dynamically."""
        python_tools: list[str] = []
        system_tools: list[str] = []
        try:
            import pycompiler_ark.Core.engine as engines_loader

            for engine_id in list(engines_loader.available_engines()):
                try:
                    engine = engines_loader.create(engine_id)
                except Exception:
                    engine = None
                if engine is None:
                    continue
                req = getattr(
                    engine, "required_tools", {"python": [], "system": []}
                )
                if not isinstance(req, dict):
                    continue
                for item in req.get("python", []) or []:
                    name = str(item or "").strip()
                    if name:
                        python_tools.append(name)
                for item in req.get("system", []) or []:
                    name = str(item or "").strip()
                    if name:
                        system_tools.append(name)
        except Exception:
            pass

        return {
            "python": sorted(set(python_tools), key=str.lower),
            "system": sorted(set(system_tools), key=str.lower),
        }

    def _discover_engine_required_python_tools(self) -> list[str]:
        """Discover python tools required by available engines dynamically (legacy helper)."""
        return self._discover_engine_requirements().get("python", [])

    def is_tool_installed(self, venv_root: str, tool: str) -> bool:
        """Non-blocking check for tool presence in venv.
        Uses has_tool_binary() only (no subprocess run). If uncertain, returns False
        so that callers can trigger the asynchronous ensure_tools_installed() flow.
        """
        return self.has_tool_binary(venv_root, tool)

    def is_tool_installed_async(
        self, venv_root: str, tool: str, callback
    ) -> None:
        """Asynchronous check using 'pip show <tool>' via QProcess, then callback(bool).
        Safe for UI: does not block. On any error, returns False.
        """
        try:
            pip_exe, pip_args = deps_analyser._find_pip_executable(
                venv_path=venv_root
            )
            if not pip_exe or not os.path.isfile(pip_exe):
                callback(False)
                return
            proc = self._create_process()

            def _done(code, _status):
                """Execute _done logic for this component."""
                try:
                    callback(code == 0)
                except Exception:
                    pass

            proc.finished.connect(_done)
            proc.setProgram(pip_exe)
            proc.setArguments(pip_args + ["show", tool])
            proc.setWorkingDirectory(venv_root)
            proc.start()
        except Exception:
            try:
                callback(False)
            except Exception:
                pass

    def ensure_tools_installed(self, venv_root: str, tools: list[str]) -> None:
        """Asynchronously check/install the provided tools list with progress dialog."""
        try:
            from ..utils import check_internet_connection

            if not check_internet_connection():
                output.error(
                    "Pas de connexion internet. Installation des outils annulée.",
                    "No internet connection. Tool installation cancelled.",
                )
                return

            self._reset_cancel_state()
            self._venv_check_pkgs = list(tools)
            self._venv_check_index = 0

            pip_exe, pip_args = deps_analyser._find_pip_executable(
                venv_path=venv_root
            )
            self._venv_check_pip_exe = pip_exe
            self._venv_check_pip_args = pip_args
            self._venv_check_path = venv_root
            self._venv_check_use_python = False

            self._show_progress(
                "tools_check",
                "Verification du venv",
                "Verification du venv",
            )
            self._bind_cancel_for_progress(
                "tools_check", "verification des outils"
            )
            self._update_progress_message(
                "tools_check",
                f"Verification de {tools[0]}...",
            )
            self._update_progress_progress("tools_check", 0, len(tools))

            # We need a local event loop if we are in a background thread or CLI mode
            # to process QProcess signals and QTimer events.
            from PySide6.QtCore import QCoreApplication, QEventLoop, QThread

            must_wait = (
                getattr(self.parent, "verbose", False)
                or os.environ.get("PYCOMPILER_CLI") == "1"
                or (
                    QCoreApplication.instance()
                    and QThread.currentThread()
                    != QCoreApplication.instance().thread()
                )
            )

            loop = None
            if must_wait:
                if not QCoreApplication.instance():
                    self._app_ref = QCoreApplication([])  # Keep alive

                loop = QEventLoop()
                # We need a way to stop the loop when all tools are checked
                self._venv_check_loop = loop

            self._check_next_venv_pkg()

            if loop:
                loop.exec()
                self._venv_check_loop = None
        except Exception as e:
            output.error(
                f"{self._tools_stage_prefix()}Erreur ensure_tools_installed: {e}"
            )

    def ensure_tools_installed_system(self, tools: list[str]) -> None:
        """Asynchronously check/install tools in system Python using pip."""
        try:
            from ..utils import check_internet_connection

            if not check_internet_connection():
                output.error(
                    "Pas de connexion internet. Installation système annulée.",
                    "No internet connection. System installation cancelled.",
                )
                return

            self._reset_cancel_state()
            self._venv_check_pkgs = list(tools)
            self._venv_check_index = 0

            pip_exe, pip_args = deps_analyser._find_pip_executable(
                venv_path=None, workspace_dir=None
            )
            self._venv_check_pip_exe = pip_exe
            self._venv_check_pip_args = pip_args
            self._venv_check_path = (
                getattr(self.parent, "workspace_dir", None) or os.getcwd()
            )
            self._venv_check_use_python = True

            self._show_progress(
                "tools_check",
                "Verification du Python systeme",
                "Verification du Python systeme",
            )
            self._bind_cancel_for_progress(
                "tools_check", "verification des outils systeme"
            )
            self._update_progress_message(
                "tools_check",
                f"Verification de {tools[0]}...",
            )
            self._update_progress_progress("tools_check", 0, len(tools))

            # We need a local event loop if we are in a background thread or CLI mode
            from PySide6.QtCore import QCoreApplication, QEventLoop, QThread

            must_wait = (
                getattr(self.parent, "verbose", False)
                or os.environ.get("PYCOMPILER_CLI") == "1"
                or (
                    QCoreApplication.instance()
                    and QThread.currentThread()
                    != QCoreApplication.instance().thread()
                )
            )

            loop = None
            if must_wait:
                if not QCoreApplication.instance():
                    self._app_ref = QCoreApplication([])  # Keep alive

                loop = QEventLoop()
                self._venv_check_loop = loop

            self._check_next_venv_pkg()

            if loop:
                loop.exec()
                self._venv_check_loop = None
        except Exception as e:
            output.error(
                f"{self._tools_stage_prefix()}Erreur ensure_tools_installed_system: {e}"
            )

    # ---------- Utility ----------
    def _safe_decode(
        self, data: bytes, error_handling: str = "replace"
    ) -> str:
        """Safely decode bytes with fallback encodings."""
        if isinstance(data, str):
            return data
        for encoding in self._fallback_encodings:
            try:
                return data.decode(encoding, errors=error_handling)
            except Exception:
                continue
        # Last resort: decode with errors ignored
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return "[Decode Error]"

    def _reset_cancel_state(self) -> None:
        """Execute _reset_cancel_state logic for this component."""
        try:
            self._cancel_requested = False
        except Exception:
            pass

    def _is_cancel_requested(self) -> bool:
        """Return whether the related condition is satisfied."""
        try:
            return bool(getattr(self, "_cancel_requested", False))
        except Exception:
            return False

    def _request_cancel(self, action_label: str | None = None) -> None:
        """Request the related operation or state transition."""
        if self._is_cancel_requested():
            return
        self._cancel_requested = True
        suffix = f" ({action_label})" if action_label else ""
        try:
            from pycompiler_ark.Ui import output

            output.warn(
                (
                    f"Annulation demandee par l'utilisateur{suffix}.",
                    f"Cancellation requested by user{suffix}.",
                ),
            )
        except Exception:
            pass
        self.terminate_tasks()

    def _bind_cancel_for_progress(
        self, progress_id: str, action_label: str
    ) -> None:
        """Bind cancellation logic for a named progress dialog via UI callback."""
        self._bind_cancel(
            progress_id,
            lambda: self._request_cancel(action_label),
        )

    def _safe_rmtree(self, path: str, max_retries: int = 3) -> bool:
        """Safely remove a directory tree with retries for locked files."""
        if not os.path.exists(path):
            return True
        for attempt in range(max_retries):
            try:
                shutil.rmtree(path)
                return True
            except Exception as e:
                if attempt < max_retries - 1:
                    try:
                        import time

                        time.sleep(0.5)  # Brief pause before retry
                    except Exception:
                        pass
                else:
                    try:
                        from pycompiler_ark.Ui import output

                        output.warn(
                            f"Failed to remove {path} after {max_retries} attempts: {e}",
                        )
                    except Exception:
                        pass
                    return False
        return False

    def _safe_mkdir(self, path: str) -> bool:
        """Safely create a directory with error handling."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            try:
                from pycompiler_ark.Ui import output

                output.warn(
                    f"Failed to create directory {path}: {e}",
                )
            except Exception:
                pass
            return False

    def _prompt_recreate_invalid_venv(
        self, venv_root: str, reason: str
    ) -> bool:
        """Ask the UI delegate whether to delete and recreate an invalid venv.
        If the user confirms, performs deletion then triggers recreation (business logic).
        Returns True if recreation was initiated, False otherwise.
        """
        confirmed = self._ask_recreate_invalid_venv(venv_root, reason)
        if not confirmed:
            return False
        # Business logic: delete the bad venv
        try:
            shutil.rmtree(venv_root)
            try:
                from pycompiler_ark.Ui import output

                output.info(f"Deleted invalid venv: {venv_root}")
            except Exception:
                pass
        except Exception as e:
            self._show_error_dialog(
                "Environnement virtuel invalide / Invalid virtual environment",
                f"Echec suppression venv / Failed to delete venv: {e}",
            )
            return False
        # Business logic: recreate
        try:
            workspace_dir = os.path.dirname(venv_root)
            self.create_venv_if_needed(workspace_dir)
            return True
        except Exception as e:
            self._show_error_dialog(
                "Environnement virtuel invalide / Invalid virtual environment",
                f"Echec de recreation du venv / Failed to recreate venv: {e}",
            )
            return False

    # ---------- Venv validation ----------
    def _is_within(self, path: str, root: str) -> bool:
        """Return whether the related condition is satisfied."""
        try:
            rp = os.path.realpath(path)
            rr = os.path.realpath(root)
            return os.path.commonpath([rp, rr]) == rr
        except Exception:
            return False

    def validate_venv_strict(self, venv_root: str) -> tuple[bool, str]:
        """Strict validation of a venv.
        Return (ok, reason_si_ko).
        Rules:
         - Existing file
         - pyvenv.cfg present
         - Scripts/python.exe (Windows) or bin/python[3] (POSIX) present
         - include-system-site-packages=false (refused if true)
         - pyvenv.cfg, Scripts/bin folder and Python executable must remain contained in the venv (no outgoing links)"""
        try:
            if not venv_root or not os.path.isdir(venv_root):
                return False, "Chemin invalide (dossier manquant)"
            cfg = os.path.join(venv_root, "pyvenv.cfg")
            if not os.path.isfile(cfg):
                return False, "pyvenv.cfg introuvable"
            bindir = "Scripts" if platform.system() == "Windows" else "bin"
            bpath = os.path.join(venv_root, bindir)
            if not os.path.isdir(bpath):
                return False, f"Dossier {bindir}/ introuvable"
            if platform.system() == "Windows":
                pyexe = os.path.join(bpath, "python.exe")
                if not os.path.isfile(pyexe):
                    return False, "python.exe introuvable dans Scripts/"
            else:
                cand1 = os.path.join(bpath, "python")
                cand2 = os.path.join(bpath, "python3")
                if not (os.path.isfile(cand1) or os.path.isfile(cand2)):
                    return False, "python ou python3 introuvable dans bin/"
                pyexe = cand1 if os.path.isfile(cand1) else cand2
            # pyvenv.cfg policy: include-system-site-packages must be false
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                for line in text.splitlines():
                    if "include-system-site-packages" in line.lower():
                        _, _, v = line.partition("=")
                        if str(v).strip().lower() in ("1", "true", "yes"):
                            return (
                                False,
                                "include-system-site-packages=true (refusé)",
                            )
                        break
            except Exception:
                pass
            # Containment: pyvenv.cfg and the bin/Scripts folder must remain in the venv.
            # The Python executable may be a non-venv symlink depending on the platform;
            # binding verification (verify_venv_binding) will ensure effective isolation.
            for p in (cfg, bpath):
                if not self._is_within(p, venv_root):
                    return (
                        False,
                        f"Lien/symlink sortant du venv: {os.path.relpath(p, venv_root)}",
                    )
            return True, ""
        except Exception as e:
            return False, f"Erreur validation venv: {e}"

    def is_valid_venv(self, venv_root: str) -> bool:
        """Return whether the related condition is satisfied."""
        ok, _ = self.validate_venv_strict(venv_root)
        return ok

    # ---------- System Python suggestion ----------
    def _collect_declared_dependencies(
        self, workspace_dir: str
    ) -> tuple[list[str], bool]:
        """Collect project dependencies using DepsAnalyser."""
        try:
            deps = deps_analyser.collect_project_dependencies(workspace_dir)
            if deps:
                return list(deps), True
            return [], False
        except Exception:
            return [], False

    def _missing_in_system_python(self, packages: list[str]) -> list[str]:
        """Check for missing packages in system Python using deps_analyser."""
        missing = []
        for pkg in packages:
            if not pkg:
                continue
            if not deps_analyser._check_module_installed(str(pkg)):
                missing.append(str(pkg))
        return missing

    def _can_use_system_python(self) -> tuple[bool, list[str], bool]:
        """Return whether this operation can run safely using system Python."""
        workspace_dir = getattr(self.parent, "workspace_dir", None)
        if not workspace_dir:
            return False, [], False
        deps, has_source = self._collect_declared_dependencies(workspace_dir)
        if not deps:
            # If we have a source but no deps, allow system python (no external deps)
            if has_source:
                return True, [], True
            return True, [], False
        missing = self._missing_in_system_python(sorted(set(deps)))
        return (len(missing) == 0), missing, has_source

    def is_tool_installed_system(self, tool: str) -> bool:
        """Check if a tool is installed in system Python via deps_analyser."""
        return deps_analyser._check_module_installed(tool)

    def check_tools_in_venv(self, venv_path: str):
        """Check both python and system requirements for the current workspace."""
        try:
            self._reset_cancel_state()
            ok, reason = self.validate_venv_strict(venv_path)
            if not ok:
                try:
                    from pycompiler_ark.Ui import output

                    output.error(f"Invalid venv: {reason}")
                except Exception:
                    pass
                # Offer to delete and recreate
                self._prompt_recreate_invalid_venv(venv_path, reason)
                return

            # Asynchronous verification of the python/pip -> venv connection
            def _after_binding(ok_bind: bool):
                """Execute _after_binding logic for this component."""
                if not ok_bind:
                    try:
                        from pycompiler_ark.Ui import output

                        output.error(
                            "Invalid venv binding: python/pip do not point to the selected venv.",
                        )
                    except Exception:
                        pass
                    self._prompt_recreate_invalid_venv(
                        venv_path,
                        "Python/pip do not point to the selected venv",
                    )
                    return

                reqs = self._discover_engine_requirements()
                python_tools = reqs.get("python", [])
                system_tools = reqs.get("system", [])

                # 1. Check system tools first (fast, usually non-blocking)
                if system_tools:
                    missing_sys = [
                        t
                        for t in system_tools
                        if not sys_deps.check_system_packages([t])
                    ]
                    if missing_sys:
                        try:
                            from pycompiler_ark.Ui import output

                            output.warn(
                                (
                                    f"Outils systeme manquants : {', '.join(missing_sys)}",
                                    f"Missing system tools: {', '.join(missing_sys)}",
                                ),
                            )
                        except Exception:
                            pass
                        # We could offer the installation, but we let the engines manage
                        # or we just display the warning.
                    else:
                        try:
                            from pycompiler_ark.Ui import output

                            output.success("Outils systeme verifies.")
                        except Exception:
                            pass

                # 2. Proceed with python tools in venv
                if not python_tools:
                    try:
                        from pycompiler_ark.Ui import output

                        output.info(
                            (
                                "Aucun outil Python requis detecte depuis les engines.",
                                "No required Python tools detected from engines.",
                            ),
                        )
                    except Exception:
                        pass
                    return

                pip_exe, pip_args = deps_analyser._find_pip_executable(
                    venv_path=venv_path
                )
                self._venv_check_pkgs = python_tools
                self._venv_check_index = 0
                self._venv_check_pip_exe = pip_exe
                self._venv_check_pip_args = pip_args
                self._venv_check_path = venv_path
                self._venv_check_use_python = False

                self._show_progress(
                    "tools_check",
                    "Verification du venv",
                    "Verification du venv",
                )
                self._bind_cancel_for_progress(
                    "tools_check", "verification des outils du venv"
                )
                self._update_progress_message(
                    "tools_check",
                    f"Verification de {self._venv_check_pkgs[0]}...",
                )
                self._update_progress_progress(
                    "tools_check",
                    0,
                    len(self._venv_check_pkgs),
                )
                self._check_next_venv_pkg()

            self._verify_venv_binding_async(venv_path, _after_binding)
        except Exception as e:
            try:
                from pycompiler_ark.Ui import output

                output.error(
                    f"Erreur lors de la verification du venv: {e}",
                )
            except Exception:
                pass

    def _check_next_venv_pkg(self):
        """Execute _check_next_venv_pkg logic for this component."""
        if self._is_cancel_requested():
            self._close_progress("tools_check")
            # Exit local loop if any
            loop = getattr(self, "_venv_check_loop", None)
            if loop:
                loop.quit()
            return
        if self._venv_check_index >= len(self._venv_check_pkgs):
            self._update_progress_message(
                "tools_check",
                "Verification terminee.",
            )
            total = (
                len(self._venv_check_pkgs)
                if hasattr(self, "_venv_check_pkgs") and self._venv_check_pkgs
                else 0
            )
            self._update_progress_progress("tools_check", total, total)
            self._close_progress("tools_check")

            # Exit local loop if any
            loop = getattr(self, "_venv_check_loop", None)
            if loop:
                loop.quit()

            # Install project dependencies if a requirements.txt is present
            try:
                if getattr(self.parent, "workspace_dir", None):
                    self.install_requirements_if_needed(
                        self.parent.workspace_dir
                    )
            except Exception:
                pass
            return
        pkg = self._venv_check_pkgs[self._venv_check_index]
        process = self._create_process()
        self._venv_check_process = process
        process.setProgram(self._venv_check_pip_exe)
        # Use stored pip args (e.g. ['-m', 'pip']) if available
        args = list(getattr(self, "_venv_check_pip_args", []))
        process.setArguments(args + ["show", pkg])
        process.setWorkingDirectory(self._venv_check_path)
        process.finished.connect(
            lambda code, status: self._on_venv_pkg_checked(
                process, code, status, pkg
            )
        )
        process.start()
        # Safety timeout for pip show (30s)
        self._arm_process_timeout(process, 30_000, f"pip show {pkg}")

    def _on_venv_pkg_checked(self, process, code, status, pkg):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            return
        if code == 0:
            if self._venv_check_use_python:
                output.success(
                    f"{self._tools_stage_prefix()}{pkg} deja installe (Python systeme)."
                )
            else:
                output.success(
                    f"{self._tools_stage_prefix()}{pkg} deja installe dans le venv."
                )
            self._venv_check_index += 1
            next_label = (
                self._venv_check_pkgs[self._venv_check_index]
                if self._venv_check_index < len(self._venv_check_pkgs)
                else ""
            )
            self._update_progress_message(
                "tools_check",
                f"Verification de {next_label}...",
            )
            self._update_progress_progress(
                "tools_check",
                self._venv_check_index,
                len(self._venv_check_pkgs),
            )
            self._check_next_venv_pkg()
        else:
            from ..utils import check_internet_connection

            if not check_internet_connection():
                output.error(
                    f"Pas de connexion internet. Impossible d'installer {pkg}.",
                    f"No internet connection. Unable to install {pkg}.",
                )
                self._close_progress("tools_check")

                # Exit local loop if any
                loop = getattr(self, "_venv_check_loop", None)
                if loop:
                    loop.quit()
                return

            output.info(
                f"{self._tools_stage_prefix()}Installation automatique de {pkg}..."
            )
            self._update_progress_message(
                "tools_check",
                f"Installation de {pkg}...",
            )
            self._update_progress_progress(
                "tools_check", 0, 0
            )  # indeterminate

            process2 = self._create_process()
            self._venv_check_install_process = process2
            # --- Executor system ---
            try:
                program, args = self._prepare_manager_command(
                    "add",  # "add" == install d'un paquet
                    extra_args=self._pip_break_system_args() + [pkg],
                    python_exe=self._venv_check_pip_exe
                    if self._venv_check_use_python
                    else None,
                )
                # if in venv, force venv's python using
                if not self._venv_check_use_python and self._venv_check_path:
                    program = self.python_path(self._venv_check_path)
                process2.setProgram(program)
                process2.setArguments(args)
            except Exception:
                process2.setProgram(self._venv_check_pip_exe)
                args = list(getattr(self, "_venv_check_pip_args", []))
                process2.setArguments(
                    args + ["install"] + self._pip_break_system_args() + [pkg]
                )

            process2.setWorkingDirectory(self._venv_check_path)
            process2.readyReadStandardOutput.connect(
                lambda: self._on_venv_check_output(process2)
            )
            process2.readyReadStandardError.connect(
                lambda: self._on_venv_check_output(process2, error=True)
            )
            process2.finished.connect(
                lambda code2, status2: self._on_venv_pkg_installed(
                    process2, code2, status2, pkg
                )
            )
            process2.start()
            # Safety timeout for pip install of single tool (10 min)
            self._arm_process_timeout(process2, 600_000, f"pip install {pkg}")

    def _on_venv_check_output(self, process, error=False):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        lines = data.strip().splitlines()
        if lines:
            self._update_progress_message("tools_check", lines[-1][:200])

            # Detailed logging for verbose mode or errors
            is_verbose = getattr(self.parent, "verbose", False)
            if is_verbose or error:
                for line in lines:
                    lvl = "WARNING" if error else "INFO"
                    # We use a slight indentation to make it clear it's sub-output
                    output.log(f"  [pip] {line}", level=lvl)

    def verify_venv_binding(self, venv_root: str) -> bool:
        """Keep synchronous verification path for internal compatibility."""
        try:
            import subprocess

            vpython = self.python_path(venv_root)
            if not os.path.isfile(vpython):
                return False
            cp = subprocess.run(
                [
                    vpython,
                    "-c",
                    "import sys, os; print(os.path.realpath(sys.prefix))",
                ],
                capture_output=True,
                text=True,
            )
            if cp.returncode != 0:
                return False
            sys_prefix = os.path.realpath(cp.stdout.strip())
            if not self._is_within(sys_prefix, venv_root):
                return False
            vpip = self.pip_path(venv_root)
            if not os.path.isfile(vpip):
                return False
            cp2 = subprocess.run(
                [vpip, "--version"], capture_output=True, text=True
            )
            if cp2.returncode != 0:
                return False
            import re as _re

            m = _re.search(r" from (.+?) \(python ", cp2.stdout.strip())
            if not m:
                return False
            site_path = os.path.realpath(m.group(1))
            if not self._is_within(site_path, venv_root):
                return False
            return True
        except Exception:
            return False

    def _verify_venv_binding_async(self, venv_root: str, callback):
        """Asynchronously verify that venv Python and pip bind to the same venv."""
        try:
            vpython = self.python_path(venv_root)
            if not os.path.isfile(vpython):
                callback(False)
                return
            # Step 1: Check sys.prefix
            p1 = self._create_process()

            def _p1_finished(code, _status):
                """Execute _p1_finished logic for this component."""
                try:
                    if code != 0:
                        callback(False)
                        return
                    out = p1.readAllStandardOutput().data().decode().strip()
                    sys_prefix = os.path.realpath(out)
                    if not self._is_within(sys_prefix, venv_root):
                        callback(False)
                        return
                    # Step 2: check pip --version and site-path
                    vpip = self.pip_path(venv_root)
                    if not os.path.isfile(vpip):
                        callback(False)
                        return
                    p2 = self._create_process()

                    def _p2_finished(code2, _status2):
                        """Execute _p2_finished logic for this component."""
                        try:
                            if code2 != 0:
                                callback(False)
                                return
                            text = (
                                p2.readAllStandardOutput()
                                .data()
                                .decode()
                                .strip()
                            )
                            import re as _re

                            m = _re.search(r" from (.+?) \(python ", text)
                            if not m:
                                callback(False)
                                return
                            site_path = os.path.realpath(m.group(1))
                            callback(self._is_within(site_path, venv_root))
                        except Exception:
                            callback(False)

                    p2.finished.connect(_p2_finished)
                    p2.setProgram(vpip)
                    p2.setArguments(["--version"])
                    p2.setWorkingDirectory(venv_root)
                    p2.start()
                except Exception:
                    callback(False)

            p1.finished.connect(_p1_finished)
            p1.setProgram(vpython)
            p1.setArguments(
                ["-c", "import sys, os; print(os.path.realpath(sys.prefix))"]
            )
            p1.setWorkingDirectory(venv_root)
            p1.start()
        except Exception:
            callback(False)

    def _arm_process_timeout(self, process: Any, timeout_ms: int, label: str):
        """Arm a one-shot timeout for a background process (overridden by UI layer)."""
        try:
            if hasattr(self.parent, "_arm_process_timeout"):
                self.parent._arm_process_timeout(process, timeout_ms, label)
        except Exception:
            pass

    def _query_manager_venv_path(self, base_dir: str) -> str | None:
        """Query active manager dynamically for environment path via YAML get_venv_path command."""
        try:
            manager = self.resolve_workspace_manager(base_dir)
            if not manager:
                return None
            return self._config.resolve_venv_path(
                manager,
                base_dir,
                python_interpreter=self._venv_python_exe or sys.executable,
            )
        except Exception:
            pass
        return None

    def _on_venv_pkg_installed(self, process, code, status, pkg):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            return
        if code == 0:
            try:
                from pycompiler_ark.Ui import output

                output.success(f"{pkg} installe dans le venv.")
            except Exception:
                pass
        else:
            try:
                from pycompiler_ark.Ui import output

                output.error(
                    f"Erreur installation {pkg} (code {code})",
                )
            except Exception:
                pass
        self._venv_check_index += 1
        self._update_progress_progress(
            "tools_check",
            self._venv_check_index,
            len(self._venv_check_pkgs),
        )
        self._check_next_venv_pkg()

    # ---------- Create venv if needed ----------
    def create_venv_if_needed(self, path: str):
        """Execute create_venv_if_needed logic for this component."""
        existing = self.resolve_existing_venv(path)
        venv_path = existing or self.resolve_project_venv()
        if existing:
            return
        if venv_path and os.path.isdir(venv_path):
            ok, reason = self.validate_venv_strict(venv_path)
            if ok:
                return
            try:
                from pycompiler_ark.Ui import output

                output.error(
                    f"Invalid venv detected: {reason}",
                )
            except Exception:
                pass
            recreated = self._prompt_recreate_invalid_venv(venv_path, reason)
            if not recreated:
                return

        try:
            from pycompiler_ark.Ui import output

            output.info("Aucun venv trouve, creation automatique...")
        except Exception:
            pass
        try:
            self._reset_cancel_state()
            # Search for a python embedded next to the executable
            python_candidate = None
            exe_dir = os.path.dirname(sys.executable)
            # Windows: python.exe, Linux/Mac: python3 ou python
            candidates = [
                os.path.join(exe_dir, "python.exe"),
                os.path.join(exe_dir, "python3"),
                os.path.join(exe_dir, "python"),
                os.path.join(exe_dir, "python_embedded", "python.exe"),
                os.path.join(exe_dir, "python_embedded", "python3"),
                os.path.join(exe_dir, "python_embedded", "python"),
            ]
            # Also searches for system interpreters available in the PATH
            path_candidates = []
            try:
                if platform.system() == "Windows":
                    w = shutil.which("py")
                    if w:
                        path_candidates.append(w)
                for name in ("python3", "python"):
                    w = shutil.which(name)
                    if w:
                        path_candidates.append(w)
            except Exception:
                pass
            for c in path_candidates:
                if c not in candidates:
                    candidates.append(c)
            for c in candidates:
                if os.path.isfile(c):
                    python_candidate = c
                    break
            if not python_candidate:
                python_candidate = sys.executable
            # Logging the type of interpreter detected
            base = os.path.basename(python_candidate).lower()
            if (
                python_candidate.startswith(exe_dir)
                or "python_embedded" in python_candidate
            ):
                try:
                    from pycompiler_ark.Ui import output

                    output.info(
                        f"Utilisation de l'interpreteur Python embarque : {python_candidate}",
                    )
                except Exception:
                    pass
            elif base in ("py", "py.exe") or shutil.which(base):
                try:
                    from pycompiler_ark.Ui import output

                    output.info(
                        f"Utilisation de l'interpreteur systeme : {python_candidate}",
                    )
                except Exception:
                    pass
            else:
                try:
                    from pycompiler_ark.Ui import output

                    output.info(
                        f"Utilisation de sys.executable : {python_candidate}",
                    )
                except Exception:
                    pass

            if self._is_cli_mode():
                try:
                    program, args = self._prepare_manager_command(
                        "create_venv",
                        kwargs={
                            "venv_path": venv_path,
                            "python": python_candidate,
                        },
                        python_exe=python_candidate,
                    )
                    if (
                        base in ("py", "py.exe")
                        and program == python_candidate
                    ):
                        args = ["-3"] + args
                    completed = subprocess.run(
                        [program, *args],
                        cwd=path,
                        capture_output=True,
                        text=True,
                    )
                    if completed.returncode != 0:
                        err = (
                            completed.stderr or completed.stdout or ""
                        ).strip()
                        raise RuntimeError(err or "venv creation failed")
                    try:
                        from pycompiler_ark.Ui import output

                        output.success(
                            "Environnement virtuel cree avec succes."
                        )
                    except Exception:
                        pass
                    resolved_venv = self.resolve_existing_venv(path)
                    if not resolved_venv:
                        resolved_venv = self.resolve_project_venv()
                    if resolved_venv:
                        try:
                            setattr(self.parent, "venv_path", resolved_venv)
                        except Exception:
                            pass
                        ws_dir = (
                            path
                            or getattr(self.parent, "workspace_dir", None)
                            or os.path.dirname(resolved_venv)
                        )
                        if ws_dir:
                            self.save_workspace_pref(ws_dir)
                            try:
                                self.install_requirements_if_needed(ws_dir)
                            except Exception:
                                pass
                    return
                except Exception as e:
                    try:
                        from pycompiler_ark.Ui import output

                        output.error(
                            f"Echec de creation du venv ou installation des outils : {e}",
                        )
                    except Exception:
                        pass
                    return

            self._show_progress(
                "venv_creation",
                "Creation de l'environnement virtuel",
                "creation de l'environnement virtuel",
            )
            self._bind_cancel_for_progress(
                "venv_creation", "creation de l'environnement virtuel"
            )
            self._update_progress_message(
                "venv_creation",
                "Creation du venv...",
            )

            process = self._create_process()
            self._venv_create_process = process
            # --- Dynamic Executor System for venv creation ---
            program, args = self._prepare_manager_command(
                "create_venv",
                kwargs={"venv_path": venv_path, "python": python_candidate},
                python_exe=python_candidate,
            )
            if base in ("py", "py.exe") and program == python_candidate:
                args = ["-3"] + args
            process.setProgram(program)
            process.setArguments(args)
            process.setWorkingDirectory(path)
            process.readyReadStandardOutput.connect(
                lambda: self._on_venv_output(process)
            )
            process.readyReadStandardError.connect(
                lambda: self._on_venv_output(process, error=True)
            )
            process.finished.connect(
                lambda code, status: self._on_venv_created(
                    process, code, status, path
                )
            )
            self._venv_progress_lines = 0
            process.start()
            # Safety timeout for venv creation (10 min)
            self._arm_process_timeout(process, 600_000, "venv creation")
        except Exception as e:
            try:
                from pycompiler_ark.Ui import output

                output.error(
                    f"Echec de creation du venv ou installation des outils : {e}",
                )
            except Exception:
                pass

    def _on_venv_output(self, process, error=False):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        lines = data.strip().splitlines()
        if lines:
            self._update_progress_message("venv_creation", lines[-1][:200])
            self._venv_progress_lines += len(lines)
            self._update_progress_progress(
                "venv_creation",
                self._venv_progress_lines,
                0,
            )

            # Detailed logging for verbose mode or errors
            is_verbose = getattr(self.parent, "verbose", False)
            if is_verbose or error:
                for line in lines:
                    lvl = "warning" if error else "info"
                    try:
                        from pycompiler_ark.Ui import output

                        output.log(lvl, f"  [venv] {line}")
                    except Exception:
                        pass

    def _on_venv_created(self, process, code, status, workspace_dir):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            try:
                from pycompiler_ark.Ui import output

                output.info("Creation du venv annulee.")
            except Exception:
                pass
            self._close_progress("venv_creation")
            return
        if code == 0:
            try:
                from pycompiler_ark.Ui import output

                output.success("Environnement virtuel cree avec succes.")
            except Exception:
                pass
            self._update_progress_message("venv_creation", "Venv cree.")
            self._close_progress("venv_creation")

            resolved_venv = self.resolve_existing_venv(workspace_dir)
            if not resolved_venv:
                resolved_venv = self.resolve_project_venv()
            ws_dir = (
                workspace_dir
                or getattr(self.parent, "workspace_dir", None)
                or (
                    os.path.dirname(resolved_venv)
                    if isinstance(resolved_venv, str) and resolved_venv
                    else None
                )
            )
            if not ws_dir or not resolved_venv:
                try:
                    from pycompiler_ark.Ui import output

                    output.warn("can't resolve venv path.")
                except Exception:
                    pass
                return
            try:
                setattr(self.parent, "venv_path", resolved_venv)
            except Exception:
                pass
            self.save_workspace_pref(ws_dir)

            # Install project dependencies from requirements.txt if present
            try:
                self.install_requirements_if_needed(ws_dir)
            except Exception:
                pass
        else:
            try:
                from pycompiler_ark.Ui import output

                output.error(
                    f"Echec de creation du venv (code {code})",
                )
            except Exception:
                pass
            self._update_progress_message(
                "venv_creation",
                "Erreur lors de la creation du venv.",
            )
            self._close_progress("venv_creation")

    # ---------- Requirements detection and generation ----------
    def _find_requirements_files(
        self, path: str, workspace_dir: str | None = None
    ) -> list[str]:
        """Find all potential requirements files in the project."""
        try:
            path = os.path.abspath(path)
        except Exception:
            return []

        requirements_files = []
        patterns = [
            "requirements.txt",
            "requirements-prod.txt",
            "requirements-dev.txt",
        ]

        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if not os.path.isfile(item_path):
                    continue
                if item in patterns or (
                    item.startswith("requirements-") and item.endswith(".txt")
                ):
                    requirements_files.append(item_path)
        except Exception:
            pass

        return requirements_files

    def _get_requirements_file(self, workspace_dir: str) -> str | None:
        """Get or generate a requirements file for the project via DepsAnalyser."""
        try:
            workspace_dir = os.path.abspath(workspace_dir)

            # 1. Look for existing requirements.txt
            req_txt = os.path.join(workspace_dir, "requirements.txt")
            if os.path.isfile(req_txt):
                return req_txt

            # 2. Try other requirements-*.txt files
            others = self._find_requirements_files(workspace_dir)
            if others:
                return others[0]

            # 3. Use DepsAnalyser to generate requirements.txt from project analysis
            output.info(
                "Analyse des dependances du projet via DepsAnalyser..."
            )
            generated = deps_analyser.write_requirements_txt(workspace_dir)
            if generated and os.path.isfile(generated):
                output.success("requirements.txt genere via DepsAnalyser.")
                return generated

            return None
        except Exception as e:
            output.warn(f"Erreur lors de la detection des requirements: {e}")
            return None

    # ---------- Install requirements.txt ----------
    def install_requirements_if_needed(
        self, path: str, force_pip: bool = False
    ):
        """Execute install_requirements_if_needed logic for this component."""
        # Get or generate requirements file
        req_path = self._get_requirements_file(path)
        if not req_path:
            output.info("Aucun fichier de dependances trouve ou genere.")
            return

        if self._using_system_python():
            self._start_requirements_install(
                path, path, req_path, use_system_python=True
            )
            return

        manual = getattr(self.parent, "venv_path_manuel", None)
        if manual:
            venv_root = os.path.abspath(manual)
        else:
            existing = self.resolve_existing_venv(path)
            if not existing:
                self.create_venv_if_needed(path)
                return
            venv_root = existing
        ok, reason = self.validate_venv_strict(venv_root)
        if not ok:
            output.warn(f"Invalid venv for requirements: {reason}")
            # Offer to delete and recreate, then retry installation
            if self._prompt_recreate_invalid_venv(venv_root, reason):
                # if recreated, try install again
                self._start_requirements_install(path, venv_root, req_path)
            return

        # Verify the link asynchronously, then start the installation
        def _after_binding(ok_bind: bool):
            """Execute _after_binding logic for this component."""
            if not ok_bind:
                output.warn(
                    "Liaison venv invalide (python/pip ne pointent pas vers le venv); installation ignoree."
                )
                return
            self._start_requirements_install(path, venv_root, req_path)

        self._verify_venv_binding_async(venv_root, _after_binding)

    def _start_requirements_install(
        self,
        path: str,
        venv_root: str,
        req_path: str,
        use_system_python: bool = False,
    ):
        """Start the related asynchronous operation."""
        from ..utils import check_internet_connection

        if not check_internet_connection():
            output.error(
                "Pas de connexion internet. Installation des dépendances annulée.",
                "No internet connection. Dependencies installation cancelled.",
            )
            return

        self._reset_cancel_state()
        py_exe = (
            sys.executable
            if use_system_python
            else self.python_path(venv_root)
        )
        if not os.path.isfile(py_exe):
            output.warn(
                "python introuvable dans le venv; installation requirements ignoree."
            )
            return
        # Compute checksum and skip install if unchanged
        try:
            with open(req_path, "rb") as f:
                data = f.read()
            req_hash = hashlib.sha256(data).hexdigest()
        except Exception as e:
            output.warn(
                f"Impossible de calculer le hash de requirements.txt: {e}"
            )
            req_hash = None
        marker_base = venv_root
        if use_system_python:
            try:
                marker_base = os.path.join(
                    path, WORKSPACE_CONFIG_DIRNAME, "system_python"
                )
                os.makedirs(marker_base, exist_ok=True)
            except Exception:
                marker_base = path
        marker_path = os.path.join(marker_base, ".requirements.sha256")
        if req_hash and os.path.isfile(marker_path):
            try:
                with open(marker_path, encoding="utf-8") as mf:
                    current = mf.read().strip()
                if current == req_hash:
                    output.success(
                        "requirements.txt deja installe (aucun changement detecte)."
                    )
                    return
            except Exception:
                pass
        output.info(
            "Installation des dependances a partir de requirements.txt..."
        )
        try:
            # remember marker info to write after success
            self._req_marker_path = marker_path
            self._req_marker_hash = req_hash
            self._req_path = req_path
            self._venv_python_exe = py_exe
            self._req_use_system_python = bool(use_system_python)
            self._pip_phase = "ensurepip"

            self._show_progress(
                "reqs_install",
                "Installation des dependances",
                "installation des dependances",
            )
            self._bind_cancel_for_progress(
                "reqs_install", "installation des dependances"
            )
            self._update_progress_message(
                "reqs_install",
                "Activation de pip (ensurepip)...",
            )

            process = self._create_process()
            self._req_install_process = process
            process.setProgram(py_exe)
            process.setArguments(["-m", "ensurepip", "--upgrade"])
            process.setWorkingDirectory(path)
            process.readyReadStandardOutput.connect(
                lambda: self._on_pip_output(process)
            )
            process.readyReadStandardError.connect(
                lambda: self._on_pip_output(process, error=True)
            )
            process.finished.connect(
                lambda code, status: self._on_pip_finished(
                    process, code, status
                )
            )
            self._pip_progress_lines = 0
            process.start()
            # Safety timeout for ensurepip (3 min)
            self._arm_process_timeout(process, 180_000, "ensurepip")
        except Exception as e:
            output.error(f"Echec installation requirements.txt : {e}")

    def _on_pip_output(self, process, error=False):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        # Shows the last line received
        lines = data.strip().splitlines()
        if lines:
            self._update_progress_message("reqs_install", lines[-1][:200])
            self._pip_progress_lines += len(lines)
            # Simulates progress (pip does not give %)
            self._update_progress_progress(
                "reqs_install",
                self._pip_progress_lines,
                0,
            )

            # Detailed logging for verbose mode or errors
            is_verbose = getattr(self.parent, "verbose", False)
            if is_verbose or error:
                for line in lines:
                    lvl = "WARNING" if error else "INFO"
                    output.log(f" [pip] {line}", level=lvl)

    def _on_pip_finished(self, process, code, status):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            output.info("Installation des dependances annulee.")
            self._close_progress("reqs_install")
            return
        phase = self._pip_phase
        if phase == "ensurepip":
            # Proceed to upgrade pip/setuptools/wheel regardless of ensurepip result
            self._update_progress_message(
                "reqs_install",
                "Mise a niveau de pip/setuptools/wheel...",
            )
            p2 = self._create_process()
            self._req_install_process = p2
            # --- Executor system ---
            program, args = self._prepare_manager_command(
                "add",
                extra_args=["--upgrade", "pip", "setuptools", "wheel"]
                + (
                    self._pip_break_system_args()
                    if getattr(self, "_req_use_system_python", False)
                    else []
                ),
                python_exe=self._venv_python_exe,
            )
            p2.setProgram(program)
            p2.setArguments(args)
            p2.setWorkingDirectory(os.path.dirname(self._req_path))
            p2.readyReadStandardOutput.connect(lambda: self._on_pip_output(p2))
            p2.readyReadStandardError.connect(
                lambda: self._on_pip_output(p2, error=True)
            )
            self._pip_phase = "upgrade"
            p2.finished.connect(
                lambda code2, status2: self._on_pip_finished(
                    p2, code2, status2
                )
            )
            p2.start()
            # Safety timeout for upgrade (5 min)
            self._arm_process_timeout(p2, 300_000, "pip upgrade core")
            return
        elif phase == "upgrade":
            if code == 0:
                # now install requirements.txt
                self._update_progress_message(
                    "reqs_install",
                    "Installation des dependances (requirements.txt)...",
                )
                p2 = self._create_process()
                self._req_install_process = p2
                # --- Executor system ---
                program, args = self._prepare_manager_command(
                    "install",
                    extra_args=[self._req_path]
                    + (
                        self._pip_break_system_args()
                        if getattr(self, "_req_use_system_python", False)
                        else []
                    ),
                    python_exe=self._venv_python_exe,
                )
                p2.setProgram(program)
                p2.setArguments(args)
                p2.setWorkingDirectory(os.path.dirname(self._req_path))
                p2.readyReadStandardOutput.connect(
                    lambda: self._on_pip_output(p2)
                )
                p2.readyReadStandardError.connect(
                    lambda: self._on_pip_output(p2, error=True)
                )
                self._pip_phase = "install"
                p2.finished.connect(
                    lambda code2, status2: self._on_pip_finished(
                        p2, code2, status2
                    )
                )
                p2.start()
                # Safety timeout for requirements install (15 min)
                self._arm_process_timeout(
                    p2, 900_000, "pip install -r requirements.txt"
                )
                return
            else:
                output.error(
                    f"Echec mise a niveau pip/setuptools/wheel (code {code})"
                )
                self._update_progress_message(
                    "reqs_install",
                    "Echec upgrade pip/setuptools/wheel.",
                )
        else:
            if code == 0:
                output.success("requirements.txt installe.")
                # Write/update marker if we computed it
                try:
                    if getattr(self, "_req_marker_path", None) and getattr(
                        self, "_req_marker_hash", None
                    ):
                        with open(
                            self._req_marker_path, "w", encoding="utf-8"
                        ) as mf:
                            mf.write(self._req_marker_hash)
                except Exception:
                    pass
                finally:
                    self._req_marker_path = None
                    self._req_marker_hash = None
                self._update_progress_message(
                    "reqs_install",
                    "Installation terminee.",
                )
            else:
                output.error(
                    f"Echec installation requirements.txt (code {code})"
                )
                self._update_progress_message(
                    "reqs_install",
                    "Erreur lors de l'installation.",
                )
        self._close_progress("reqs_install")
        self._process_events()

    # ---------- Background tasks status/control ----------
    def has_active_tasks(self) -> bool:
        """Return whether any venv-related tasks are active."""
        for task_id in ["venv_creation", "reqs_install", "tools_check"]:
            if self._is_progress_visible(task_id):
                return True
        return False

    def terminate_tasks(self):
        """Execute terminate_tasks logic for this component."""
        had_active = self.has_active_tasks()
        if had_active:
            self._cancel_requested = True
        # Kill processes
        for attr in [
            "_venv_create_process",
            "_venv_check_process",
            "_venv_check_install_process",
            "_req_install_process",
        ]:
            proc = getattr(self, attr, None)
            try:
                if proc:
                    from ..process_killer import kill_process_tree

                    kill_process_tree(proc.processId())
            except Exception:
                pass

        if had_active:
            output.warn(
                "Operations venv interrompues.",
                "Venv operations interrupted.",
            )

        # Close dialogs via UI callbacks
        for task_id in ["venv_creation", "reqs_install", "tools_check"]:
            self._close_progress(task_id)

    # ---------- Environment Manager Detection & Handling ----------
    def _detect_environment_manager(self, workspace_dir: str) -> str:
        """Detect which environment manager is used in the project."""
        detected = self._config.detect_manager_for_workspace(workspace_dir)
        if detected:
            return detected
        default_mgr = self._config.get_default_manager()
        if default_mgr:
            return default_mgr
        raise ValueError("No environment manager configured in YAML")

    def _is_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in the system PATH."""
        try:
            return shutil.which(tool) is not None
        except Exception:
            return False

    def _get_manager_command(
        self, manager: str, action: str
    ) -> list[str] | None:
        """Get the command for a specific manager and action."""
        try:
            cmd = self._config.get_command(manager, action)
            if cmd:
                return cmd
            if manager in self._manager_commands:
                if action in self._manager_commands[manager]:
                    return self._manager_commands[manager][action]
        except Exception:
            pass
        return None

    def setup_workspace(
        self, workspace_dir: str, check_tools: bool = True
    ) -> bool:
        """Setup a workspace with venv and dependencies."""
        try:
            workspace_dir = os.path.abspath(workspace_dir)

            # Dynamically resolve manager for workspace
            self.resolve_workspace_manager(workspace_dir)

            # Resolve an existing environment first
            existing_env = self.resolve_existing_venv(workspace_dir)

            # Create venv if needed
            if not existing_env:
                self.create_venv_if_needed(workspace_dir)
            else:
                output.success(f"Venv existant detecte: {existing_env}")
                try:
                    setattr(self.parent, "venv_path", existing_env)
                except Exception:
                    pass
                self.save_workspace_pref(workspace_dir)

            # Check and install tools if requested
            if check_tools:
                existing_check = self.resolve_existing_venv(workspace_dir)
                if existing_check:
                    ok, reason = self.validate_venv_strict(existing_check)
                    if ok:

                        def _after_binding(ok_bind: bool):
                            if ok_bind:
                                output.info(
                                    "Verification des outils de compilation..."
                                )
                                self.check_tools_in_venv(existing_check)
                            else:
                                output.warn(
                                    "Liaison venv invalide, verification des outils ignoree."
                                )

                        self._verify_venv_binding_async(
                            existing_check, _after_binding
                        )
                    else:
                        output.warn(
                            f"Venv invalide, verification des outils ignoree: {reason}"
                        )

            # Create ARK config if it doesn't exist
            try:
                from ..configs import (
                    create_default_ark_config,
                )

                if create_default_ark_config(workspace_dir):
                    output.success("Fichier ark.yml cree dans le workspace.")
            except Exception as e:
                output.warn(f"erreur lors de la creation de ark.yml: {e}")

            return True
        except Exception as e:
            output.error(f"Erreur lors de la configuration du workspace: {e}")
            return False

    def get_manager_info(self, workspace_dir: str) -> dict:
        """Get detailed information about the detected environment manager."""
        return {
            "manager": self._detected_manager,
            "available": bool(
                self._manager_commands.get(self._detected_manager)
            ),
            "commands": self._manager_commands.get(self._detected_manager, {}),
            "config_file": "requirements.txt",
            "lock_file": None,
        }
