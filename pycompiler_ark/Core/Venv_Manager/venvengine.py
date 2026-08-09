"""VenvEngine: Pure, deterministic Python core for virtual environment inspection,
resolution, command building, creation, dependency analysis, and filesystem operations without UI/Qt dependencies.
"""

import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

import pycompiler_ark.Core.deps_analyser.analyser as deps_analyser
from ..globals import WORKSPACE_CONFIG_DIRNAME
from .config import VenvManagerConfig
from .executor import ExecutorFactory


class VenvEngine:
    """Pure Python engine for virtual environment operations.

    This engine operates synchronously without any dependence on Qt event loops,
    UI dialogs, or signal connections, making it usable in both CLI and GUI contexts.
    """

    def __init__(self, config: VenvManagerConfig | None = None):
        self.config = config or VenvManagerConfig()
        self._fallback_encodings = ["utf-8", "latin-1", "cp1252", "ascii"]

    # ---------- Path & Containment Utilities ----------
    def is_within(self, path: str, root: str) -> bool:
        """Check if path is contained within root directory."""
        try:
            rp = os.path.realpath(path)
            rr = os.path.realpath(root)
            return os.path.commonpath([rp, rr]) == rr
        except Exception:
            return False

    def validate_venv_strict(self, venv_root: str) -> tuple[bool, str]:
        """Strict validation of a virtual environment structure.

        Return (ok, reason_if_failed).
        """
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

            # Containment: pyvenv.cfg and the bin/Scripts folder must remain in the venv
            for p in (cfg, bpath):
                if not self.is_within(p, venv_root):
                    return (
                        False,
                        f"Lien/symlink sortant du venv: {os.path.relpath(p, venv_root)}",
                    )
            return True, ""
        except Exception as e:
            return False, f"Erreur validation venv: {e}"

    # ---------- Workspace Preferences ----------
    def workspace_pref_path(self, workspace_dir: str) -> str:
        """Return the preference file path for a workspace."""
        return os.path.join(
            os.path.abspath(workspace_dir),
            WORKSPACE_CONFIG_DIRNAME,
            "pref.json",
        )

    def read_workspace_pref(self, workspace_dir: str) -> dict | None:
        """Read and parse workspace preferences file if present."""
        try:
            path = self.workspace_pref_path(workspace_dir)
            if not os.path.isfile(path):
                return None
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def write_workspace_pref(self, workspace_dir: str, data: dict) -> bool:
        """Write workspace preferences safely using a temp file swap."""
        try:
            path = self.workspace_pref_path(workspace_dir)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
            return True
        except Exception:
            return False

    def clear_workspace_pref(self, workspace_dir: str) -> bool:
        """Remove workspace preferences file."""
        try:
            path = self.workspace_pref_path(workspace_dir)
            if os.path.isfile(path):
                os.remove(path)
                return True
        except Exception:
            pass
        return False

    # ---------- Manager & Venv Resolution ----------
    def resolve_workspace_manager(self, workspace_dir: str) -> str:
        """Resolve environment manager for a workspace (Pref -> Auto Detect -> YAML default)."""
        if workspace_dir:
            pref_data = self.read_workspace_pref(workspace_dir)
            if pref_data and isinstance(pref_data, dict):
                saved_mgr = pref_data.get("manager")
                if (
                    isinstance(saved_mgr, str)
                    and saved_mgr in self.config.get_available_managers()
                ):
                    return saved_mgr

            detected = self.config.detect_manager_for_workspace(workspace_dir)
            if detected:
                return detected

        default_mgr = self.config.get_default_manager()
        if not default_mgr:
            raise ValueError("No environment manager configured in YAML")
        return default_mgr

    def resolve_manager_venv_path(
        self,
        workspace_dir: str | None = None,
        python_exe: str | None = None,
    ) -> str | None:
        """Resolve expected venv path from the active manager YAML definition."""
        try:
            if not workspace_dir:
                return None
            base = os.path.abspath(workspace_dir)
            manager = self.resolve_workspace_manager(base)
            if not manager:
                return None
            return self.config.resolve_venv_path(
                manager,
                base,
                python_interpreter=python_exe or sys.executable,
            )
        except Exception:
            return None

    def resolve_existing_venv(
        self,
        workspace_dir: str | None = None,
        use_system_python: bool = False,
        venv_path_manuel: str | None = None,
    ) -> str | None:
        """Resolve an existing, valid venv path for a workspace."""
        try:
            if use_system_python:
                return None

            if venv_path_manuel:
                manual = os.path.abspath(venv_path_manuel)
                if (
                    os.path.isdir(manual)
                    and self.validate_venv_strict(manual)[0]
                ):
                    return manual
                return None

            if not workspace_dir:
                return None
            base = os.path.abspath(workspace_dir)

            # Check saved workspace pref
            pref_data = self.read_workspace_pref(base)
            if pref_data and isinstance(pref_data, dict):
                mode = str(pref_data.get("venv_mode", "")).strip().lower()
                saved_venv = pref_data.get("venv_path")
                if mode == "system":
                    return None
                elif (
                    mode == "venv"
                    and isinstance(saved_venv, str)
                    and saved_venv
                ):
                    saved_venv = os.path.abspath(saved_venv)
                    if (
                        os.path.isdir(saved_venv)
                        and self.validate_venv_strict(saved_venv)[0]
                    ):
                        return saved_venv

            resolved = self.resolve_manager_venv_path(base)
            if resolved and os.path.isdir(resolved):
                ok, _ = self.validate_venv_strict(resolved)
                if ok:
                    return resolved
        except Exception:
            return None
        return None

    def resolve_project_venv(
        self,
        workspace_dir: str | None = None,
        use_system_python: bool = False,
        venv_path_manuel: str | None = None,
    ) -> str | None:
        """Resolve target project venv path (even if not yet created)."""
        try:
            if use_system_python:
                return None
            if venv_path_manuel:
                return os.path.abspath(venv_path_manuel)
            if workspace_dir:
                base = os.path.abspath(workspace_dir)
                return self.resolve_manager_venv_path(base)
        except Exception:
            return None
        return None

    # ---------- System Python Viability & Dependency Inspection ----------
    def collect_declared_dependencies(
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

    def missing_in_system_python(self, packages: list[str]) -> list[str]:
        """Check for missing packages in system Python using deps_analyser."""
        missing = []
        for pkg in packages:
            if not pkg:
                continue
            if not deps_analyser._check_module_installed(str(pkg)):
                missing.append(str(pkg))
        return missing

    def can_use_system_python(
        self, workspace_dir: str | None
    ) -> tuple[bool, list[str], bool]:
        """Return (can_use: bool, missing_packages: list[str], has_source: bool)."""
        if not workspace_dir:
            return False, [], False
        deps, has_source = self.collect_declared_dependencies(workspace_dir)
        if not deps:
            if has_source:
                return True, [], True
            return True, [], False
        missing = self.missing_in_system_python(sorted(set(deps)))
        return (len(missing) == 0), missing, has_source

    def is_tool_installed_system(self, tool: str) -> bool:
        """Check if a tool is installed in system Python via deps_analyser."""
        try:
            return deps_analyser._check_module_installed(tool)
        except Exception:
            return False

    # ---------- Requirements Checksums & Markers ----------
    def compute_file_hash(self, file_path: str) -> str | None:
        """Compute SHA-256 hash of a file."""
        try:
            if not os.path.isfile(file_path):
                return None
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return None

    def is_requirements_up_to_date(
        self, marker_dir: str, req_path: str
    ) -> bool:
        """Check if requirements.txt hash matches recorded marker file."""
        try:
            current_hash = self.compute_file_hash(req_path)
            if not current_hash:
                return False
            marker_path = os.path.join(marker_dir, ".requirements.sha256")
            if not os.path.isfile(marker_path):
                return False
            with open(marker_path, "r", encoding="utf-8") as f:
                saved_hash = f.read().strip()
            return current_hash == saved_hash
        except Exception:
            return False

    def update_requirements_marker(
        self, marker_dir: str, req_path: str
    ) -> bool:
        """Write current requirements.txt hash to marker file."""
        try:
            current_hash = self.compute_file_hash(req_path)
            if not current_hash:
                return False
            os.makedirs(marker_dir, exist_ok=True)
            marker_path = os.path.join(marker_dir, ".requirements.sha256")
            with open(marker_path, "w", encoding="utf-8") as f:
                f.write(current_hash)
            return True
        except Exception:
            return False

    # ---------- Manager Command Building & Execution ----------
    def prepare_manager_command(
        self,
        action: str,
        manager_name: str | None = None,
        extra_args: list[str] | None = None,
        python_exe: str | None = None,
        kwargs: dict[str, str] | None = None,
    ) -> tuple[str, list[str]]:
        """Build (program, arguments) tuple for a manager action from YAML config."""
        extra_args = list(extra_args or [])
        manager = manager_name or self.config.get_default_manager()
        if not manager:
            raise ValueError("No environment manager configured")

        cmd_args = self.config.get_command(manager, action)
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

        executor_cfg = self.config.get_executor(manager, action=action)
        python_interpreter = python_exe or sys.executable

        executor = ExecutorFactory.create(executor_cfg, python_interpreter)
        return executor.build_command(resolved_args)

    def find_python_candidate(self) -> str:
        """Find candidate Python interpreter (embedded or system PATH)."""
        exe_dir = os.path.dirname(sys.executable)
        candidates = [
            os.path.join(exe_dir, "python.exe"),
            os.path.join(exe_dir, "python3"),
            os.path.join(exe_dir, "python"),
            os.path.join(exe_dir, "python_embedded", "python.exe"),
            os.path.join(exe_dir, "python_embedded", "python3"),
            os.path.join(exe_dir, "python_embedded", "python"),
        ]
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
                return c
        return sys.executable

    def create_venv_sync(
        self,
        workspace_dir: str,
        venv_path: str | None = None,
        manager_name: str | None = None,
        python_candidate: str | None = None,
    ) -> tuple[bool, str]:
        """Synchronously create virtual environment via subprocess."""
        try:
            ws_dir = os.path.abspath(workspace_dir)
            mgr = manager_name or self.resolve_workspace_manager(ws_dir)
            target_venv = venv_path or self.resolve_project_venv(
                workspace_dir=ws_dir
            )
            if not target_venv:
                return False, "Impossible de déterminer le chemin du venv"

            py_cand = python_candidate or self.find_python_candidate()
            program, args = self.prepare_manager_command(
                "create_venv",
                manager_name=mgr,
                kwargs={"venv_path": target_venv, "python": py_cand},
                python_exe=py_cand,
            )

            base = os.path.basename(py_cand).lower()
            if base in ("py", "py.exe") and program == py_cand:
                args = ["-3"] + args

            completed = subprocess.run(
                [program, *args],
                cwd=ws_dir,
                capture_output=True,
                text=True,
            )

            if completed.returncode != 0:
                err = (completed.stderr or completed.stdout or "").strip()
                return False, err or "Échec de création du venv"

            valid, reason = self.validate_venv_strict(target_venv)
            if not valid:
                return False, f"Venv créé mais invalide: {reason}"

            return True, target_venv
        except Exception as e:
            return False, f"Erreur lors de la création du venv: {e}"

    # ---------- Binary & Tool Executable Discovery ----------
    def pip_path(self, venv_root: str) -> str:
        """Get absolute path to pip executable for a venv."""
        pip_exe, _ = deps_analyser._find_pip_executable(venv_path=venv_root)
        return pip_exe

    def python_path(self, venv_root: str) -> str:
        """Get absolute path to python executable for a venv."""
        pip_exe, pip_args = deps_analyser._find_pip_executable(
            venv_path=venv_root
        )
        if "-m" in pip_args and "pip" in pip_args:
            return pip_exe

        base = os.path.join(
            venv_root, "Scripts" if platform.system() == "Windows" else "bin"
        )
        if platform.system() == "Windows":
            return os.path.join(base, "python.exe")
        cand1 = os.path.join(base, "python")
        cand2 = os.path.join(base, "python3")
        return cand1 if os.path.isfile(cand1) else cand2

    def has_tool_binary(self, venv_root: str, tool: str) -> bool:
        """Non-blocking check: detect console script/binary inside the venv bin folder."""
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

    def is_tool_installed(self, venv_root: str, tool: str) -> bool:
        """Synchronous check for tool presence in venv."""
        return self.has_tool_binary(venv_root, tool)

    def discover_engine_requirements(self) -> dict[str, list[str]]:
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

    # ---------- Resilient File Operations ----------
    def safe_decode(
        self, data: bytes | str, error_handling: str = "replace"
    ) -> str:
        """Safely decode bytes with fallback encodings."""
        if isinstance(data, str):
            return data
        for encoding in self._fallback_encodings:
            try:
                return data.decode(encoding, errors=error_handling)
            except Exception:
                continue
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return "[Decode Error]"

    def safe_rmtree(self, path: str, max_retries: int = 3) -> bool:
        """Safely remove a directory tree with retries for file locks."""
        if not path or not os.path.exists(path):
            return True
        for attempt in range(max_retries):
            try:
                shutil.rmtree(path)
                return True
            except Exception:
                if attempt < max_retries - 1:
                    time.sleep(0.2)
        return not os.path.exists(path)

    def safe_mkdir(self, path: str) -> bool:
        """Safely create a directory path."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception:
            return False
