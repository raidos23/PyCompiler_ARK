"""Provide core utilities and workflows for this module."""

import hashlib
import os
import platform
import shutil
import sys

from PySide6.QtCore import QProcess, QTimer

import Core.deps_analyser.analyser as deps_analyser
import Core.SysDependencyManager as sys_deps


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

        # UI delegate callbacks — registered by VenvManagerUI (Ui layer)
        self._ui_callbacks: dict = {}

        # Internal timers to enforce timeouts on background processes
        self._proc_timers: list[QTimer] = []

        # Retry counters for resilience
        self._venv_check_retries = {}
        self._max_retries = 2

        # Encoding detection for subprocess output
        self._output_encoding = "utf-8"
        self._fallback_encodings = ["utf-8", "latin-1", "cp1252", "ascii"]

        # Environment manager detection (Simplified to PIP only)
        self._detected_manager = "pip"
        self._manager_commands = self._get_pip_commands()
        # Cache for auto-selected venv per workspace
        self._auto_venv_cache: dict[str, str] = {}
        # User-driven cancellation flag for long-running async flows
        self._cancel_requested = False

    # ---------- PIP-only Manager mapping ----------
    def _get_pip_commands(self) -> dict[str, dict[str, list[str]]]:
        """Return the standard PIP/VENV commands."""
        return {
            "pip": {
                "create_venv": ["python", "-m", "venv"],
                "install": ["pip", "install", "-r"],
                "add": ["pip", "install"],
                "show": ["pip", "show"],
                "check": ["pip", "check"],
            }
        }

    def _call_ui(self, method: str, *args, **kwargs):
        """Invoke a registered UI callback by name. Returns None if no delegate registered."""
        fn = self._ui_callbacks.get(method)
        if callable(fn):
            try:
                return fn(*args, **kwargs)
            except Exception:
                pass
        return None

    def tr(self, fr: str, en: str) -> str:
        """Translation helper using UI callback or fallback to English."""
        res = self._call_ui("tr", fr, en)
        if res is not None:
            return str(res)
        return en

    # ---------- Workspace pref stubs (Overridden in VenvManagerUI) ----------
    def apply_workspace_pref(self, workspace_dir: str) -> bool:
        """Stub for applying workspace preferences. Overridden in UI layer."""
        return False

    def save_workspace_pref(self, workspace_dir: str | None) -> None:
        """Stub for saving workspace preferences. Overridden in UI layer."""
        pass

    # ---------- Public helpers for engines ----------
    def resolve_existing_venv(self, workspace_dir: str | None = None) -> str | None:
        """Resolve an existing venv path (manual/local/manager).

        Returns only if a real, existing environment is found.
        Does not return a default path when no venv exists.
        """
        try:
            if getattr(self.parent, "use_system_python", False):
                return None

            manual = getattr(self.parent, "venv_path_manuel", None)
            if manual:
                return os.path.abspath(manual)

            base = None
            if workspace_dir:
                base = os.path.abspath(workspace_dir)
            elif getattr(self.parent, "workspace_dir", None):
                base = os.path.abspath(self.parent.workspace_dir)

            if not base:
                return None

            # Apply saved workspace preference first (.ark/pref.json)
            try:
                if self.apply_workspace_pref(base):
                    if getattr(self.parent, "use_system_python", False):
                        return None
                    manual = getattr(self.parent, "venv_path_manuel", None)
                    if manual:
                        return os.path.abspath(manual)
            except Exception:
                pass

            # Prefer local venv if available
            try:
                cached = self._auto_venv_cache.get(base)
                if cached and os.path.isdir(cached):
                    ok, _ = self.validate_venv_strict(cached)
                    if ok:
                        return cached
            except Exception:
                pass

            # Auto-detect best local venv among common names in workspace
            best = self.select_best_venv(base)
            if best:
                try:
                    self._auto_venv_cache[base] = best
                except Exception:
                    pass
                return best

        except Exception:
            return None
        return None

    def resolve_project_venv(self) -> str | None:
        """Resolve the venv root to use based on manual selection or workspace.
        Prefers an existing .venv over venv; if none exists, returns the default path (.venv).
        """
        try:
            if getattr(self.parent, "use_system_python", False):
                return None
            manual = getattr(self.parent, "venv_path_manuel", None)
            if manual:
                return os.path.abspath(manual)
            if getattr(self.parent, "workspace_dir", None):
                base = os.path.abspath(self.parent.workspace_dir)

                # First, use an existing environment if available
                existing = self.resolve_existing_venv(base)
                if existing:
                    return existing

                # Fallback to default detection (.venv / venv)
                existing2, default_path = self._detect_venv_in(base)
                return existing2 or default_path
        except Exception:
            return None
        return None

    def pip_path(self, venv_root: str) -> str:
        """Get the absolute path to the pip executable using deps_analyser."""
        pip_exe, _ = deps_analyser._find_pip_executable(venv_path=venv_root)
        return pip_exe

    def python_path(self, venv_root: str) -> str:
        """Get the absolute path to the python executable using deps_analyser."""
        pip_exe, pip_args = deps_analyser._find_pip_executable(venv_path=venv_root)
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
                venv_root, "Scripts" if platform.system() == "Windows" else "bin"
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
            import Core.engine as engines_loader

            for engine_id in list(engines_loader.available_engines()):
                try:
                    engine = engines_loader.create(engine_id)
                except Exception:
                    engine = None
                if engine is None:
                    continue
                req = getattr(engine, "required_tools", {"python": [], "system": []})
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

    def is_tool_installed_async(self, venv_root: str, tool: str, callback) -> None:
        """Asynchronous check using 'pip show <tool>' via QProcess, then callback(bool).
        Safe for UI: does not block. On any error, returns False.
        """
        try:
            pip_exe, pip_args = deps_analyser._find_pip_executable(venv_path=venv_root)
            if not pip_exe or not os.path.isfile(pip_exe):
                callback(False)
                return
            proc = QProcess(self.parent)

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
            self._reset_cancel_state()
            self._venv_check_pkgs = list(tools)
            self._venv_check_index = 0
            
            pip_exe, pip_args = deps_analyser._find_pip_executable(venv_path=venv_root)
            self._venv_check_pip_exe = pip_exe
            self._venv_check_pip_args = pip_args
            self._venv_check_path = venv_root
            self._venv_check_use_python = False

            self._call_ui(
                "show_progress",
                "tools_check",
                "Verification du venv",
                "Verification du venv",
            )
            self._bind_cancel_for_progress("tools_check", "verification des outils")
            self._call_ui(
                "update_progress_message",
                "tools_check",
                f"Verification de {tools[0]}...",
            )
            self._call_ui("update_progress_progress", "tools_check", 0, len(tools))
            self._check_next_venv_pkg()
        except Exception as e:
            self._safe_log(
                f"[ERROR] {self._tools_stage_prefix()}Erreur ensure_tools_installed: {e}"
            )

    def ensure_tools_installed_system(self, tools: list[str]) -> None:
        """Asynchronously check/install tools in system Python using pip."""
        try:
            self._reset_cancel_state()
            self._venv_check_pkgs = list(tools)
            self._venv_check_index = 0
            
            pip_exe, pip_args = deps_analyser._find_pip_executable(venv_path=None, workspace_dir=None)
            self._venv_check_pip_exe = pip_exe
            self._venv_check_pip_args = pip_args
            self._venv_check_path = (
                getattr(self.parent, "workspace_dir", None) or os.getcwd()
            )
            self._venv_check_use_python = True

            self._call_ui(
                "show_progress",
                "tools_check",
                "Verification du Python systeme",
                "Verification du Python systeme",
            )
            self._bind_cancel_for_progress(
                "tools_check", "verification des outils systeme"
            )
            self._call_ui(
                "update_progress_message",
                "tools_check",
                f"Verification de {tools[0]}...",
            )
            self._call_ui("update_progress_progress", "tools_check", 0, len(tools))
            self._check_next_venv_pkg()
        except Exception as e:
            self._safe_log(
                f"[ERROR] {self._tools_stage_prefix()}Erreur ensure_tools_installed_system: {e}"
            )

    # ---------- Utility ----------
    def _safe_decode(self, data: bytes, error_handling: str = "replace") -> str:
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

    def _infer_log_level(self, text: str | None) -> str:
        """Execute _infer_log_level logic for this component."""
        try:
            s = str(text or "").strip()
        except Exception:
            s = ""
        if not s:
            return "info"
        emoji_levels = {
            "[ERROR]": "error",
            "[WARNING]": "warning",
            "[OK]": "success",
            "[SUCCESS]": "success",
            "[INFO]": "info",
            "[STATE]": "state",
            "[SEARCH]": "state",
            "[CONFIG]": "state",
            "[BUILD]": "state",
            "[INSTALL]": "state",
            "[DELETE]": "state",
            "[CANCEL]": "state",
            "[TIMEOUT]": "error",
        }
        for tag, lvl in emoji_levels.items():
            if s.startswith(tag):
                return lvl
        low = s.lower()
        if any(
            tok in low
            for tok in (
                "error",
                "erreur",
                "echec",
                "failed",
                "invalid",
                "refus",
            )
        ):
            return "error"
        if any(tok in low for tok in ("warning", "avert", "warn", "attention")):
            return "warning"
        if any(tok in low for tok in ("success", "succes", "reussi")):
            return "success"
        if any(tok in low for tok in ("state", "status", "etat")):
            return "state"
        return "info"

    def _safe_log(
        self, text: str, text_en: str | None = None, level: str | None = None
    ):
        """Execute _safe_log logic for this component via UI callback."""
        lvl = level or self._infer_log_level(text_en if text_en is not None else text)

        # Try primary UI callback for i18n logging
        if text_en is not None:
            res = self._call_ui("log_i18n", lvl, text, text_en)
            if res is not None:
                return
        else:
            res = self._call_ui("log", lvl, text)
            if res is not None:
                return

        # Fallback to parent methods if available
        try:
            if text_en is not None:
                text = self.tr(text, text_en)
            if hasattr(self.parent, "_safe_log"):
                self.parent._safe_log(text)
                return
        except Exception:
            pass

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
        self._safe_log(
            f"[CANCEL] Annulation demandee par l'utilisateur{suffix}.",
            f"[CANCEL] Cancellation requested by user{suffix}.",
            level="warning",
        )
        self.terminate_tasks()

    def _bind_cancel_for_progress(self, progress_id: str, action_label: str) -> None:
        """Bind cancellation logic for a named progress dialog via UI callback."""
        self._call_ui(
            "bind_cancel", progress_id, lambda: self._request_cancel(action_label)
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
                    self._safe_log(
                        f"[WARNING] Failed to remove {path} after {max_retries} attempts: {e}"
                    )
                    return False
        return False

    def _safe_mkdir(self, path: str) -> bool:
        """Safely create a directory with error handling."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            self._safe_log(f"[WARNING] Failed to create directory {path}: {e}")
            return False

    def _prompt_recreate_invalid_venv(self, venv_root: str, reason: str) -> bool:
        """Ask the UI delegate whether to delete and recreate an invalid venv.
        If the user confirms, performs deletion then triggers recreation (business logic).
        Returns True if recreation was initiated, False otherwise.
        """
        confirmed = self._call_ui("ask_recreate_invalid_venv", venv_root, reason)
        if not confirmed:
            return False
        # Business logic: delete the bad venv
        try:
            shutil.rmtree(venv_root)
            self._safe_log(f"[DELETE] Deleted invalid venv: {venv_root}")
        except Exception as e:
            self._call_ui(
                "show_error_dialog",
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
            self._call_ui(
                "show_error_dialog",
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
        Return (ok, raison_si_ko).
        Règles:
         - Dossier existant
         - pyvenv.cfg présent
         - Scripts/python.exe (Windows) ou bin/python[3] (POSIX) présent
         - include-system-site-packages=false (refus si true)
         - pyvenv.cfg, folder Scripts/bin et executable Python doivent rester confinés dans le venv (pas de liens sortants)
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
            # Politique pyvenv.cfg: include-system-site-packages doit être false
            try:
                with open(cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                for line in text.splitlines():
                    if "include-system-site-packages" in line.lower():
                        _, _, v = line.partition("=")
                        if str(v).strip().lower() in ("1", "true", "yes"):
                            return False, "include-system-site-packages=true (refusé)"
                        break
            except Exception:
                pass
            # Confinement: pyvenv.cfg et le dossier bin/Scripts doivent rester dans le venv.
            # L'exécutable Python peut être un lien symbolique hors venv selon la plateforme;
            # la vérification de liaison (verify_venv_binding) garantira l'isolation effective.
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
                self._safe_log(f"[ERROR] Invalid venv: {reason}")
                # Offer to delete and recreate
                self._prompt_recreate_invalid_venv(venv_path, reason)
                return

            # Verification asynchrone de la liaison python/pip -> venv
            def _after_binding(ok_bind: bool):
                """Execute _after_binding logic for this component."""
                if not ok_bind:
                    self._safe_log(
                        "[ERROR] Invalid venv binding: python/pip do not point to the selected venv."
                    )
                    self._prompt_recreate_invalid_venv(
                        venv_path, "Python/pip do not point to the selected venv"
                    )
                    return
                
                reqs = self._discover_engine_requirements()
                python_tools = reqs.get("python", [])
                system_tools = reqs.get("system", [])

                # 1. Check system tools first (fast, usually non-blocking)
                if system_tools:
                    missing_sys = [t for t in system_tools if not sys_deps.check_system_packages([t])]
                    if missing_sys:
                        self._safe_log(
                            f"[WARNING] Outils systeme manquants : {', '.join(missing_sys)}",
                            f"[WARNING] Missing system tools: {', '.join(missing_sys)}",
                        )
                        # On pourrait proposer l'installation, mais on laisse les engines gérer 
                        # ou on affiche juste l'avertissement.
                    else:
                        self._safe_log("[OK] Outils systeme verifies.")

                # 2. Proceed with python tools in venv
                if not python_tools:
                    self._safe_log(
                        "[INFO] Aucun outil Python requis detecte depuis les engines.",
                        "[INFO] No required Python tools detected from engines.",
                    )
                    return
                
                pip_exe, pip_args = deps_analyser._find_pip_executable(venv_path=venv_path)
                self._venv_check_pkgs = python_tools
                self._venv_check_index = 0
                self._venv_check_pip_exe = pip_exe
                self._venv_check_pip_args = pip_args
                self._venv_check_path = venv_path
                self._venv_check_use_python = False

                self._call_ui(
                    "show_progress",
                    "tools_check",
                    "Verification du venv",
                    "Verification du venv",
                )
                self._bind_cancel_for_progress(
                    "tools_check", "verification des outils du venv"
                )
                self._call_ui(
                    "update_progress_message",
                    "tools_check",
                    f"Verification de {self._venv_check_pkgs[0]}...",
                )
                self._call_ui(
                    "update_progress_progress",
                    "tools_check",
                    0,
                    len(self._venv_check_pkgs),
                )
                self._check_next_venv_pkg()

            self._verify_venv_binding_async(venv_path, _after_binding)
        except Exception as e:
            self._safe_log(f"[ERROR] Erreur lors de la verification du venv: {e}")

    def _check_next_venv_pkg(self):
        """Execute _check_next_venv_pkg logic for this component."""
        if self._is_cancel_requested():
            self._call_ui("close_progress", "tools_check")
            return
        if self._venv_check_index >= len(self._venv_check_pkgs):
            self._call_ui(
                "update_progress_message", "tools_check", "Verification terminee."
            )
            total = (
                len(self._venv_check_pkgs)
                if hasattr(self, "_venv_check_pkgs") and self._venv_check_pkgs
                else 0
            )
            self._call_ui("update_progress_progress", "tools_check", total, total)
            self._call_ui("close_progress", "tools_check")

            # Installer les dependances du projet si un requirements.txt est present
            try:
                if getattr(self.parent, "workspace_dir", None):
                    self.install_requirements_if_needed(self.parent.workspace_dir)
            except Exception:
                pass
            return
        pkg = self._venv_check_pkgs[self._venv_check_index]
        process = QProcess(self.parent)
        self._venv_check_process = process
        process.setProgram(self._venv_check_pip_exe)
        # Use stored pip args (e.g. ['-m', 'pip']) if available
        args = list(getattr(self, "_venv_check_pip_args", []))
        process.setArguments(args + ["show", pkg])
        process.setWorkingDirectory(self._venv_check_path)
        process.finished.connect(
            lambda code, status: self._on_venv_pkg_checked(process, code, status, pkg)
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
                self._safe_log(
                    f"[OK] {self._tools_stage_prefix()}{pkg} deja installe (Python systeme)."
                )
            else:
                self._safe_log(
                    f"[OK] {self._tools_stage_prefix()}{pkg} deja installe dans le venv."
                )
            self._venv_check_index += 1
            next_label = (
                self._venv_check_pkgs[self._venv_check_index]
                if self._venv_check_index < len(self._venv_check_pkgs)
                else ""
            )
            self._call_ui(
                "update_progress_message",
                "tools_check",
                f"Verification de {next_label}...",
            )
            self._call_ui(
                "update_progress_progress",
                "tools_check",
                self._venv_check_index,
                len(self._venv_check_pkgs),
            )
            self._check_next_venv_pkg()
        else:
            from Core.Compiler.utils import check_internet_connection

            if not check_internet_connection():
                self._safe_log(
                    f"🛑 [ERROR] Pas de connexion internet. Impossible d'installer {pkg}.",
                    f"🛑 [ERROR] No internet connection. Unable to install {pkg}.",
                    level="error",
                )
                self._call_ui("close_progress", "tools_check")
                return

            self._safe_log(
                f"[INSTALL] {self._tools_stage_prefix()}Installation automatique de {pkg}..."
            )
            self._call_ui(
                "update_progress_message", "tools_check", f"Installation de {pkg}..."
            )
            self._call_ui(
                "update_progress_progress", "tools_check", 0, 0
            )  # indeterminate

            process2 = QProcess(self.parent)
            self._venv_check_install_process = process2
            process2.setProgram(self._venv_check_pip_exe)
            
            # Use stored pip args (e.g. ['-m', 'pip']) if available
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
            self._call_ui("update_progress_message", "tools_check", lines[-1][:200])
        self._safe_log(data)

    def verify_venv_binding(self, venv_root: str) -> bool:
        """Keep synchronous verification path for internal compatibility."""
        try:
            import subprocess

            vpython = self.python_path(venv_root)
            if not os.path.isfile(vpython):
                return False
            cp = subprocess.run(
                [vpython, "-c", "import sys, os; print(os.path.realpath(sys.prefix))"],
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
            cp2 = subprocess.run([vpip, "--version"], capture_output=True, text=True)
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
            # Étape 1: vérifier sys.prefix
            p1 = QProcess(self.parent)

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
                    # Étape 2: vérifier pip --version et site-path
                    vpip = self.pip_path(venv_root)
                    if not os.path.isfile(vpip):
                        callback(False)
                        return
                    p2 = QProcess(self.parent)

                    def _p2_finished(code2, _status2):
                        """Execute _p2_finished logic for this component."""
                        try:
                            if code2 != 0:
                                callback(False)
                                return
                            text = p2.readAllStandardOutput().data().decode().strip()
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

    def _arm_process_timeout(self, process: QProcess, timeout_ms: int, label: str):
        """Arm a one-shot timer to kill a long-running process and keep UI responsive."""
        try:
            if timeout_ms and timeout_ms > 0:
                t = QTimer(self.parent)
                t.setSingleShot(True)

                def _on_timeout():
                    """Handle the related event callback."""
                    try:
                        if process.state() != QProcess.NotRunning:
                            self._safe_log(
                                f"[TIMEOUT] Timeout exceeded for {label} ({timeout_ms} ms). Killing process..."
                            )
                            from Core.process_killer import kill_process_tree
                            kill_process_tree(process.processId())
                    except Exception:
                        pass

                t.timeout.connect(_on_timeout)
                t.start(timeout_ms)
                # keep reference to avoid GC
                self._proc_timers.append(t)

                # also attach to process so timer can be cleared if process finishes earlier
                def _clear_timer(*_args):
                    """Clear the related cached state or UI values."""
                    try:
                        if t.isActive():
                            t.stop()
                    except Exception:
                        pass

                process.finished.connect(_clear_timer)
        except Exception:
            pass

    def _detect_venv_in(self, base: str) -> tuple[str | None, str]:
        """Return (existing_venv_path_or_None, default_venv_path). Prefers .venv if present, otherwise venv. Default path is .venv."""
        try:
            base = os.path.abspath(base)
        except Exception:
            pass
        p_dot = os.path.join(base, ".venv")
        p_std = os.path.join(base, "venv")
        existing = (
            p_dot if os.path.isdir(p_dot) else (p_std if os.path.isdir(p_std) else None)
        )
        default = p_dot
        return existing, default

    def _find_all_venvs_in(self, base: str) -> list[str]:
        """Find all potential venv directories in the base path.
        Returns a list of valid venv paths, sorted by preference.
        """
        try:
            base = os.path.abspath(base)
        except Exception:
            return []

        venvs = []
        common_names = [".venv", "venv", ".env", "env", "virtualenv"]

        for name in common_names:
            venv_path = os.path.join(base, name)
            if os.path.isdir(venv_path):
                ok, _ = self.validate_venv_strict(venv_path)
                if ok:
                    venvs.append(venv_path)

        return venvs

    def _score_venv(self, venv_path: str, workspace_dir: str) -> tuple[int, str]:
        """Score a venv based on its completeness and requirements satisfaction.
        Returns (score, reason) where higher score = better venv.

        Scoring criteria:
        - Has requirements.txt satisfied: +100
        - Has required engine python tools: +50 each
        - Has pip/setuptools/wheel: +30
        - Is valid venv: +10
        - Has binding verified: +20
        """
        score = 0
        reasons = []

        try:
            # Check if venv is valid
            ok, _ = self.validate_venv_strict(venv_path)
            if not ok:
                return 0, "Invalid venv structure"
            score += 10
            reasons.append("valid_structure")

            # Check binding
            if self.verify_venv_binding(venv_path):
                score += 20
                reasons.append("verified_binding")
            else:
                return score, "Invalid binding (python/pip don't point to venv)"

            # Check for requirements.txt (lightweight marker only to avoid blocking UI)
            req_path = os.path.join(workspace_dir, "requirements.txt")
            if os.path.isfile(req_path):
                marker = os.path.join(venv_path, ".requirements.sha256")
                if os.path.isfile(marker):
                    score += 100
                    reasons.append("requirements_marker")
                else:
                    reasons.append("requirements_unknown")

            # Check for key tools
            tools_to_check = self._discover_engine_required_python_tools()
            for tool in tools_to_check:
                if self.has_tool_binary(venv_path, tool):
                    score += 50
                    reasons.append(f"has_{tool}")

            # Check for pip/setuptools/wheel
            pip_exe = self.pip_path(venv_path)
            if os.path.isfile(pip_exe):
                score += 30
                reasons.append("has_pip")

            return score, ", ".join(reasons)
        except Exception as e:
            return 0, f"Scoring error: {e}"

    def select_best_venv(self, workspace_dir: str) -> str | None:
        """Select the best venv from multiple candidates.

        Strategy:
        1. Find all valid venvs in workspace
        2. Score each based on completeness and requirements satisfaction
        3. Return the highest-scoring venv
        4. If no valid venv found, return None
        """
        try:
            venvs = self._find_all_venvs_in(workspace_dir)

            if not venvs:
                self._safe_log("[INFO] Aucun venv valide trouve dans le workspace.")
                return None

            if len(venvs) == 1:
                self._safe_log(f"[OK] Un seul venv trouve: {venvs[0]}")
                return venvs[0]

            # Multiple venvs found - score and select the best
            self._safe_log(
                f"[INFO] {len(venvs)} venv(s) trouve(s), selection du meilleur..."
            )

            scored_venvs = []
            for venv_path in venvs:
                score, reason = self._score_venv(venv_path, workspace_dir)
                scored_venvs.append((score, venv_path, reason))
                self._safe_log(
                    f"  - {os.path.basename(venv_path)}: score={score} ({reason})"
                )

            # Sort by score (descending)
            scored_venvs.sort(key=lambda x: x[0], reverse=True)

            best_score, best_venv, best_reason = scored_venvs[0]

            if best_score == 0:
                self._safe_log("[ERROR] Aucun venv valide avec une bonne liaison.")
                return None

            self._safe_log(
                f"[OK] Meilleur venv selectionne: {os.path.basename(best_venv)} (score={best_score})"
            )
            return best_venv
        except Exception as e:
            self._safe_log(f"[WARNING] Erreur lors de la selection du meilleur venv: {e}")
            return None

    def _on_venv_pkg_installed(self, process, code, status, pkg):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            return
        if code == 0:
            self._safe_log(f"[OK] {pkg} installe dans le venv.")
        else:
            self._safe_log(f"[ERROR] Erreur installation {pkg} (code {code})")
        self._venv_check_index += 1
        self._call_ui(
            "update_progress_progress",
            "tools_check",
            self._venv_check_index,
            len(self._venv_check_pkgs),
        )
        self._check_next_venv_pkg()

    # ---------- Create venv if needed ----------
    def create_venv_if_needed(self, path: str):
        """Execute create_venv_if_needed logic for this component."""
        existing, default_path = self._detect_venv_in(path)
        venv_path = existing or default_path
        if existing:
            # Validate existing venv; if invalid, propose deletion/recreation
            ok, reason = self.validate_venv_strict(venv_path)
            if not ok:
                self._safe_log(f"[ERROR] Invalid venv detected: {reason}")
                recreated = self._prompt_recreate_invalid_venv(venv_path, reason)
                if not recreated:
                    return
            else:
                return

        self._safe_log("[CONFIG] Aucun venv trouve, creation automatique...")
        try:
            self._reset_cancel_state()
            # Recherche d'un python embarque a cote de l'executable
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
            # Recherche egalement les interpreteurs systeme disponibles dans le PATH
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
            # Journalisation du type d'interpreteur detecte
            base = os.path.basename(python_candidate).lower()
            if (
                python_candidate.startswith(exe_dir)
                or "python_embedded" in python_candidate
            ):
                self._safe_log(
                    f"[STATE] Utilisation de l'interpreteur Python embarque : {python_candidate}"
                )
            elif base in ("py", "py.exe") or shutil.which(base):
                self._safe_log(
                    f"[STATE] Utilisation de l'interpreteur systeme : {python_candidate}"
                )
            else:
                self._safe_log(f"[STATE] Utilisation de sys.executable : {python_candidate}")

            self._call_ui(
                "show_progress",
                "venv_creation",
                "Creation de l'environnement virtuel",
                "creation de l'environnement virtuel",
            )
            self._bind_cancel_for_progress(
                "venv_creation", "creation de l'environnement virtuel"
            )
            self._call_ui(
                "update_progress_message", "venv_creation", "Creation du venv..."
            )

            process = QProcess(self.parent)
            self._venv_create_process = process
            process.setProgram(python_candidate)
            args = ["-m", "venv", venv_path]
            # Si l'on utilise le launcher Windows 'py', forcer Python 3 avec -3
            if base in ("py", "py.exe"):
                args = ["-3"] + args
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
                    process, code, status, venv_path
                )
            )
            self._venv_progress_lines = 0
            process.start()
            # Safety timeout for venv creation (10 min)
            self._arm_process_timeout(process, 600_000, "venv creation")
        except Exception as e:
            self._safe_log(
                f"[ERROR] Echec de creation du venv ou installation des outils : {e}"
            )

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
            self._call_ui("update_progress_message", "venv_creation", lines[-1][:200])
            self._venv_progress_lines += len(lines)
            self._call_ui(
                "update_progress_progress",
                "venv_creation",
                self._venv_progress_lines,
                0,
            )
        self._safe_log(data)

    def _on_venv_created(self, process, code, status, venv_path):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            self._safe_log("[INFO] Creation du venv annulee.")
            self._call_ui("close_progress", "venv_creation")
            return
        if code == 0:
            self._safe_log("[OK] Environnement virtuel cree avec succes.")
            self._call_ui("update_progress_message", "venv_creation", "Venv cree.")
            self._call_ui("close_progress", "venv_creation")

            # Installer les dependances du projet a partir de requirements.txt si present
            try:
                self.install_requirements_if_needed(os.path.dirname(venv_path))
            except Exception:
                pass
        else:
            self._safe_log(f"[ERROR] Echec de creation du venv (code {code})")
            self._call_ui(
                "update_progress_message",
                "venv_creation",
                "Erreur lors de la creation du venv.",
            )
            self._call_ui("close_progress", "venv_creation")

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
            self._safe_log("[SEARCH] Analyse des dependances du projet via DepsAnalyser...")
            generated = deps_analyser.write_requirements_txt(workspace_dir)
            if generated and os.path.isfile(generated):
                self._safe_log("[OK] requirements.txt genere via DepsAnalyser.")
                return generated

            return None
        except Exception as e:
            self._safe_log(f"[WARNING] Erreur lors de la detection des requirements: {e}")
            return None

    # ---------- Install requirements.txt ----------
    def install_requirements_if_needed(self, path: str, force_pip: bool = False):
        """Execute install_requirements_if_needed logic for this component."""
        # Get or generate requirements file
        req_path = self._get_requirements_file(path)
        if not req_path:
            self._safe_log("[INFO] Aucun fichier de dependances trouve ou genere.")
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
            existing, default_path = self._detect_venv_in(path)
            venv_root = existing or default_path
            if not existing:
                # Create default .venv if none exists
                self.create_venv_if_needed(path)
                existing2, _ = self._detect_venv_in(path)
                venv_root = existing2 or venv_root
        ok, reason = self.validate_venv_strict(venv_root)
        if not ok:
            self._safe_log(f"[WARNING] Invalid venv for requirements: {reason}")
            # Offer to delete and recreate, then retry installation
            if self._prompt_recreate_invalid_venv(venv_root, reason):
                # if recreated, try install again
                self._start_requirements_install(path, venv_root, req_path)
            return

        # Verifier la liaison de maniere asynchrone, puis demarrer l'installation
        def _after_binding(ok_bind: bool):
            """Execute _after_binding logic for this component."""
            if not ok_bind:
                self._safe_log(
                    "[WARNING] Liaison venv invalide (python/pip ne pointent pas vers le venv); installation ignoree."
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
        from Core.Compiler.utils import check_internet_connection

        if not check_internet_connection():
            self._safe_log(
                "🛑 [ERROR] Pas de connexion internet. Installation des dépendances annulée.",
                "🛑 [ERROR] No internet connection. Dependencies installation cancelled.",
                level="error",
            )
            return

        self._reset_cancel_state()
        py_exe = sys.executable if use_system_python else self.python_path(venv_root)
        if not os.path.isfile(py_exe):
            self._safe_log(
                "[WARNING] python introuvable dans le venv; installation requirements ignoree."
            )
            return
        # Compute checksum and skip install if unchanged
        try:
            with open(req_path, "rb") as f:
                data = f.read()
            req_hash = hashlib.sha256(data).hexdigest()
        except Exception as e:
            self._safe_log(
                f"[WARNING] Impossible de calculer le hash de requirements.txt: {e}"
            )
            req_hash = None
        marker_base = venv_root
        if use_system_python:
            try:
                marker_base = os.path.join(path, ".ark", "system_python")
                os.makedirs(marker_base, exist_ok=True)
            except Exception:
                marker_base = path
        marker_path = os.path.join(marker_base, ".requirements.sha256")
        if req_hash and os.path.isfile(marker_path):
            try:
                with open(marker_path, encoding="utf-8") as mf:
                    current = mf.read().strip()
                if current == req_hash:
                    self._safe_log(
                        "[OK] requirements.txt deja installe (aucun changement detecte)."
                    )
                    return
            except Exception:
                pass
        self._safe_log(
            "[INSTALL] Installation des dependances a partir de requirements.txt..."
        )
        try:
            # remember marker info to write after success
            self._req_marker_path = marker_path
            self._req_marker_hash = req_hash
            self._req_path = req_path
            self._venv_python_exe = py_exe
            self._req_use_system_python = bool(use_system_python)
            self._pip_phase = "ensurepip"

            self._call_ui(
                "show_progress",
                "reqs_install",
                "Installation des dependances",
                "installation des dependances",
            )
            self._bind_cancel_for_progress(
                "reqs_install", "installation des dependances"
            )
            self._call_ui(
                "update_progress_message",
                "reqs_install",
                "Activation de pip (ensurepip)...",
            )

            process = QProcess(self.parent)
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
                lambda code, status: self._on_pip_finished(process, code, status)
            )
            self._pip_progress_lines = 0
            process.start()
            # Safety timeout for ensurepip (3 min)
            self._arm_process_timeout(process, 180_000, "ensurepip")
        except Exception as e:
            self._safe_log(f"[ERROR] Echec installation requirements.txt : {e}")

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
        # Affiche la dernière ligne reçue
        lines = data.strip().splitlines()
        if lines:
            self._call_ui("update_progress_message", "reqs_install", lines[-1][:200])
            self._pip_progress_lines += len(lines)
            # Simule une progression (pip ne donne pas de %)
            self._call_ui(
                "update_progress_progress", "reqs_install", self._pip_progress_lines, 0
            )
        self._safe_log(data)

    def _on_pip_finished(self, process, code, status):
        """Handle the related event callback."""
        if getattr(self.parent, "_closing", False):
            return
        if self._is_cancel_requested():
            self._safe_log("[INFO] Installation des dependances annulee.")
            self._call_ui("close_progress", "reqs_install")
            return
        phase = self._pip_phase
        if phase == "ensurepip":
            # Proceed to upgrade pip/setuptools/wheel regardless of ensurepip result
            self._call_ui(
                "update_progress_message",
                "reqs_install",
                "Mise a niveau de pip/setuptools/wheel...",
            )
            p2 = QProcess(self.parent)
            self._req_install_process = p2
            p2.setProgram(self._venv_python_exe)
            p2.setArguments(
                [
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "pip",
                    "setuptools",
                    "wheel",
                ]
                + (
                    self._pip_break_system_args()
                    if getattr(self, "_req_use_system_python", False)
                    else []
                )
            )
            p2.setWorkingDirectory(os.path.dirname(self._req_path))
            p2.readyReadStandardOutput.connect(lambda: self._on_pip_output(p2))
            p2.readyReadStandardError.connect(
                lambda: self._on_pip_output(p2, error=True)
            )
            self._pip_phase = "upgrade"
            p2.finished.connect(
                lambda code2, status2: self._on_pip_finished(p2, code2, status2)
            )
            p2.start()
            # Safety timeout for upgrade (5 min)
            self._arm_process_timeout(p2, 300_000, "pip upgrade core")
            return
        elif phase == "upgrade":
            if code == 0:
                # now install requirements.txt
                self._call_ui(
                    "update_progress_message",
                    "reqs_install",
                    "Installation des dependances (requirements.txt)...",
                )
                p2 = QProcess(self.parent)
                self._req_install_process = p2
                p2.setProgram(self._venv_python_exe)
                p2.setArguments(
                    ["-m", "pip", "install", "-r", self._req_path]
                    + (
                        self._pip_break_system_args()
                        if getattr(self, "_req_use_system_python", False)
                        else []
                    )
                )
                p2.setWorkingDirectory(os.path.dirname(self._req_path))
                p2.readyReadStandardOutput.connect(lambda: self._on_pip_output(p2))
                p2.readyReadStandardError.connect(
                    lambda: self._on_pip_output(p2, error=True)
                )
                self._pip_phase = "install"
                p2.finished.connect(
                    lambda code2, status2: self._on_pip_finished(p2, code2, status2)
                )
                p2.start()
                # Safety timeout for requirements install (15 min)
                self._arm_process_timeout(
                    p2, 900_000, "pip install -r requirements.txt"
                )
                return
            else:
                self._safe_log(
                    f"[ERROR] Echec mise a niveau pip/setuptools/wheel (code {code})"
                )
                self._call_ui(
                    "update_progress_message",
                    "reqs_install",
                    "Echec upgrade pip/setuptools/wheel.",
                )
        else:
            if code == 0:
                self._safe_log("[OK] requirements.txt installe.")
                # Write/update marker if we computed it
                try:
                    if getattr(self, "_req_marker_path", None) and getattr(
                        self, "_req_marker_hash", None
                    ):
                        with open(self._req_marker_path, "w", encoding="utf-8") as mf:
                            mf.write(self._req_marker_hash)
                except Exception:
                    pass
                finally:
                    self._req_marker_path = None
                    self._req_marker_hash = None
                self._call_ui(
                    "update_progress_message", "reqs_install", "Installation terminee."
                )
            else:
                self._safe_log(f"[ERROR] Echec installation requirements.txt (code {code})")
                self._call_ui(
                    "update_progress_message",
                    "reqs_install",
                    "Erreur lors de l'installation.",
                )
        self._call_ui("close_progress", "reqs_install")
        self._call_ui("process_events")

    # ---------- Background tasks status/control ----------
    def has_active_tasks(self) -> bool:
        """Return whether any venv-related tasks are active."""
        for task_id in ["venv_creation", "reqs_install", "tools_check"]:
            if self._call_ui("is_progress_visible", task_id):
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
                    from Core.process_killer import kill_process_tree
                    kill_process_tree(proc.processId())
            except Exception:
                pass

        if had_active:
            self._safe_log(
                "[CANCEL] Operations venv interrompues.",
                "[CANCEL] Venv operations interrupted.",
                level="warning",
            )

        # Close dialogs via UI callbacks
        for task_id in ["venv_creation", "reqs_install", "tools_check"]:
            self._call_ui("close_progress", task_id)


    # ---------- Environment Manager Detection & Handling ----------
    def _detect_environment_manager(self, workspace_dir: str) -> str:
        """Detect which environment manager is used in the project (Simplified to PIP)."""
        return "pip"

    def _is_tool_available(self, tool: str) -> bool:
        """Check if a tool is available in the system PATH."""
        try:
            return shutil.which(tool) is not None
        except Exception:
            return False

    def _get_manager_command(self, manager: str, action: str) -> list[str] | None:
        """Get the command for a specific manager and action."""
        try:
            if manager in self._manager_commands:
                if action in self._manager_commands[manager]:
                    return self._manager_commands[manager][action]
        except Exception:
            pass
        return None

    def setup_workspace(self, workspace_dir: str, check_tools: bool = True) -> bool:
        """Setup a workspace with venv and dependencies."""
        try:
            workspace_dir = os.path.abspath(workspace_dir)

            # Resolve an existing environment first
            existing_env = self.resolve_existing_venv(workspace_dir)

            # Create venv if needed
            if not existing_env:
                self.create_venv_if_needed(workspace_dir)
            else:
                self._safe_log(f"[OK] Venv existant detecte: {existing_env}")

            # Check and install tools if requested
            if check_tools:
                existing_check, _ = self._detect_venv_in(workspace_dir)
                if existing_check:
                    ok, reason = self.validate_venv_strict(existing_check)
                    if ok:

                        def _after_binding(ok_bind: bool):
                            if ok_bind:
                                self._safe_log(
                                    "[SEARCH] Verification des outils de compilation..."
                                )
                                self.check_tools_in_venv(existing_check)
                            else:
                                self._safe_log(
                                    "[WARNING] Liaison venv invalide, verification des outils ignoree."
                                )

                        self._verify_venv_binding_async(existing_check, _after_binding)
                    else:
                        self._safe_log(
                            f"[WARNING] Venv invalide, verification des outils ignoree: {reason}"
                        )

            # Create ARK config if it doesn't exist
            try:
                from Core.Configs import create_default_ark_config

                if create_default_ark_config(workspace_dir):
                    self._safe_log("[STATE] Fichier ark.yml cree dans le workspace.")
            except Exception as e:
                self._safe_log(f"[WARNING] Impossible de creer ark.yml: {e}")

            return True
        except Exception as e:
            self._safe_log(f"[ERROR] Erreur lors de la configuration du workspace: {e}")
            return False

    def get_manager_info(self, workspace_dir: str) -> dict:
        """Get detailed information about the detected environment manager."""
        return {
            "manager": "pip",
            "available": True,
            "commands": self._manager_commands.get("pip", {}),
            "config_file": "requirements.txt",
            "lock_file": None,
        }
