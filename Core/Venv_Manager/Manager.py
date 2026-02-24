import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import yaml

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

from ..WidgetsCreator import ProgressDialog
from ..i18n import log_i18n_level, log_with_level


class VenvManager:
    """
    Encapsulates all virtual environment (venv) related operations for the GUI.

    Responsibilities:
    - Manual venv selection (updates parent UI label and internal path)
    - Create venv if missing
    - Check/install tools in an existing venv
    - Install project requirements.txt
    - Report/terminate active background tasks related to venv operations

    The class uses the parent QWidget to own QProcess instances and for logging/UI.
    """

    def __init__(self, parent_widget):
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
        self._venv_check_index = 0
        self._venv_check_pip_exe = None
        self._venv_check_path = None
        self._venv_check_use_python = False

        # For fresh venv install flow (no longer used for tool installs)

        # Progress dialogs
        self.venv_progress_dialog = None
        self.venv_check_progress = None
        self.progress_dialog = None

        # Internal timers to enforce timeouts on background processes
        self._proc_timers: list[QTimer] = []

        # Retry counters for resilience
        self._venv_check_retries = {}
        self._max_retries = 2

        # Encoding detection for subprocess output
        self._output_encoding = "utf-8"
        self._fallback_encodings = ["utf-8", "latin-1", "cp1252", "ascii"]

        # Environment manager detection
        self._detected_manager = None  # 'pip', 'poetry', 'conda', 'pipenv', 'uv', 'pdm'
        self._manager_commands = self._load_manager_mapping()
        # Cache for auto-selected venv per workspace
        self._auto_venv_cache: dict[str, str] = {}
        # Cache for manager-provided venv per workspace (None if not found)
        self._manager_venv_cache: dict[str, str | None] = {}

    # ---------- Workspace pref (.ark/pref.json) ----------
    def _workspace_pref_path(self, workspace_dir: str) -> str:
        return os.path.join(os.path.abspath(workspace_dir), ".ark", "pref.json")

    def _read_workspace_pref(self, workspace_dir: str) -> dict | None:
        try:
            path = self._workspace_pref_path(workspace_dir)
            if not os.path.isfile(path):
                return None
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else None
        except Exception:
            return None

    def _write_workspace_pref(self, workspace_dir: str, data: dict) -> None:
        try:
            path = self._workspace_pref_path(workspace_dir)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            pass

    def _clear_workspace_pref(self, workspace_dir: str) -> None:
        try:
            path = self._workspace_pref_path(workspace_dir)
            if os.path.isfile(path):
                os.remove(path)
        except Exception:
            pass

    def _pref_label_system(self) -> str:
        try:
            return self.parent.tr(
                "Venv sélectionné : Python système",
                "Venv selected: System Python",
            )
        except Exception:
            return "Venv selected: System Python"

    def _pref_label_none(self) -> str:
        try:
            return self.parent.tr("Venv sélectionné : Aucun", "Venv selected: None")
        except Exception:
            return "Venv selected: None"

    def apply_workspace_pref(self, workspace_dir: str) -> bool:
        """Apply saved venv/system selection from .ark/pref.json if available."""
        try:
            data = self._read_workspace_pref(workspace_dir)
            if not data:
                return False
            mode = str(data.get("venv_mode", "")).strip().lower()
            venv_path = data.get("venv_path")
            if mode == "system":
                try:
                    setattr(self.parent, "use_system_python", True)
                except Exception:
                    pass
                try:
                    self.parent.venv_path_manuel = None
                except Exception:
                    pass
                try:
                    if hasattr(self.parent, "venv_path"):
                        setattr(self.parent, "venv_path", None)
                except Exception:
                    pass
                try:
                    if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                        self.parent.venv_label.setText(self._pref_label_system())
                except Exception:
                    pass
                try:
                    if hasattr(self.parent, "venv_path_edit") and self.parent.venv_path_edit:
                        self.parent.venv_path_edit.setText(self._pref_label_system())
                except Exception:
                    pass
                return True
            if mode == "venv" and isinstance(venv_path, str) and venv_path:
                venv_path = os.path.abspath(venv_path)
                ok, _ = self.validate_venv_strict(venv_path)
                if ok:
                    try:
                        setattr(self.parent, "use_system_python", False)
                    except Exception:
                        pass
                    try:
                        self.parent.venv_path_manuel = venv_path
                    except Exception:
                        pass
                    try:
                        if hasattr(self.parent, "venv_path"):
                            setattr(self.parent, "venv_path", venv_path)
                    except Exception:
                        pass
                    try:
                        if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                            self.parent.venv_label.setText(f"Venv sélectionné : {venv_path}")
                    except Exception:
                        pass
                    try:
                        if hasattr(self.parent, "venv_path_edit") and self.parent.venv_path_edit:
                            self.parent.venv_path_edit.setText(venv_path)
                    except Exception:
                        pass
                    return True
                self._clear_workspace_pref(workspace_dir)
            return False
        except Exception:
            return False

    def save_workspace_pref(self, workspace_dir: str | None) -> None:
        """Persist current venv/system selection for a workspace."""
        if not workspace_dir:
            return
        try:
            if getattr(self.parent, "use_system_python", False):
                self._write_workspace_pref(
                    workspace_dir,
                    {"venv_mode": "system", "venv_path": None},
                )
                return
            venv_path = getattr(self.parent, "venv_path_manuel", None)
            if not venv_path:
                venv_path = getattr(self.parent, "venv_path", None)
            if venv_path:
                self._write_workspace_pref(
                    workspace_dir,
                    {"venv_mode": "venv", "venv_path": os.path.abspath(venv_path)},
                )
                return
        except Exception:
            pass
        self._clear_workspace_pref(workspace_dir)

    # ---------- Manager mapping ----------
    def _default_manager_commands(self) -> dict[str, dict[str, list[str]]]:
        return {
            "poetry": {
                "create_venv": ["poetry", "env", "use", "python"],
                "install": ["poetry", "install"],
                "add": ["poetry", "add"],
                "show": ["poetry", "show"],
                "check": ["poetry", "check"],
                "lock": ["poetry", "lock"],
            },
            "conda": {
                "create_venv": ["conda", "create", "-y", "-n"],
                "install": ["conda", "install", "-y"],
                "activate": ["conda", "activate"],
                "list": ["conda", "list"],
                "check": ["conda", "list"],
            },
            "pipenv": {
                "create_venv": ["pipenv", "--python"],
                "install": ["pipenv", "install"],
                "add": ["pipenv", "install"],
                "show": ["pipenv", "graph"],
                "check": ["pipenv", "check"],
                "lock": ["pipenv", "lock"],
            },
            "uv": {
                "create_venv": ["uv", "venv"],
                "install": ["uv", "pip", "install", "-r"],
                "add": ["uv", "pip", "install"],
                "show": ["uv", "pip", "show"],
                "check": ["uv", "pip", "check"],
            },
            "pdm": {
                "create_venv": ["pdm", "venv", "create"],
                "install": ["pdm", "install"],
                "add": ["pdm", "add"],
                "show": ["pdm", "show"],
                "check": ["pdm", "check"],
                "lock": ["pdm", "lock"],
            },
            "pip": {
                "create_venv": ["python", "-m", "venv"],
                "install": ["pip", "install", "-r"],
                "add": ["pip", "install"],
                "show": ["pip", "show"],
                "check": ["pip", "check"],
            },
        }

    def _validate_manager_mapping(
        self,
        data: object,
        allowed_actions: dict[str, set[str]] | None = None,
    ) -> tuple[dict[str, dict[str, list[str]]], list[str]]:
        errors: list[str] = []
        if not isinstance(data, dict):
            errors.append("Le fichier YAML doit contenir un objet racine (mapping).")
            return {}, errors
        managers = data.get("managers")
        if managers is None:
            errors.append("Clé 'managers' manquante.")
            return {}, errors
        if not isinstance(managers, dict):
            errors.append("La clé 'managers' doit être un mapping.")
            return {}, errors

        cleaned: dict[str, dict[str, list[str]]] = {}
        for manager, actions in managers.items():
            if not isinstance(manager, str) or not manager.strip():
                errors.append("Nom de gestionnaire invalide (doit être une chaîne).")
                continue
            if not isinstance(actions, dict):
                errors.append(
                    f"'{manager}': la section doit être un mapping d'actions."
                )
                continue
            action_map: dict[str, list[str]] = {}
            for action, cmd in actions.items():
                if not isinstance(action, str) or not action.strip():
                    errors.append(f"'{manager}': nom d'action invalide.")
                    continue
                if allowed_actions and manager in allowed_actions:
                    if action not in allowed_actions[manager]:
                        allowed = ", ".join(sorted(allowed_actions[manager]))
                        errors.append(
                            f"'{manager}.{action}': action non autorisee. "
                            f"Actions autorisees: {allowed}."
                        )
                        continue
                if not isinstance(cmd, list):
                    errors.append(
                        f"'{manager}.{action}': la commande doit être une liste."
                    )
                    continue
                if not all(isinstance(item, str) and item for item in cmd):
                    errors.append(
                        f"'{manager}.{action}': chaque argument doit être une chaîne."
                    )
                    continue
                action_map[action] = cmd
            if not action_map:
                errors.append(f"'{manager}': aucune action valide trouvée.")
                continue
            cleaned[manager] = action_map

        return cleaned, errors

    def _load_manager_mapping(self) -> dict[str, dict[str, list[str]]]:
        default = self._default_manager_commands()
        mapping_path = os.path.join(os.path.dirname(__file__), "ManagerMapping.yml")
        if not os.path.isfile(mapping_path):
            return default
        try:
            with open(mapping_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            allowed_actions = {
                manager: set(actions.keys()) for manager, actions in default.items()
            }
            cleaned, errors = self._validate_manager_mapping(
                data, allowed_actions=allowed_actions
            )
            if errors:
                for err in errors:
                    self._safe_log(f"⚠️ ManagerMapping.yml: {err}")
            if not cleaned:
                self._safe_log(
                    "⚠️ ManagerMapping.yml invalide, utilisation de la configuration par défaut."
                )
                return default
            return cleaned
        except Exception as e:
            self._safe_log(f"⚠️ Erreur chargement ManagerMapping.yml: {e}")
            return default

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

            # Prefer manager-provided venv (poetry/pipenv/pdm/...) when available
            mgr_venv = self._detect_manager_existing_venv(base)
            if mgr_venv:
                return mgr_venv

            # Try cached auto-selection next
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
        return os.path.join(
            venv_root, "Scripts" if platform.system() == "Windows" else "bin", "pip"
        )

    def python_path(self, venv_root: str) -> str:
        base = os.path.join(
            venv_root, "Scripts" if platform.system() == "Windows" else "bin"
        )
        if platform.system() == "Windows":
            cand = os.path.join(base, "python.exe")
            return cand
        # Linux/macOS: prefer 'python', fallback to 'python3'
        cand1 = os.path.join(base, "python")
        cand2 = os.path.join(base, "python3")
        return cand1 if os.path.isfile(cand1) else cand2

    def _using_system_python(self) -> bool:
        try:
            return bool(getattr(self.parent, "use_system_python", False))
        except Exception:
            return False

    def _pip_break_system_args(self) -> list[str]:
        if self._using_system_python() and platform.system() == "Linux":
            return ["--break-system-packages"]
        return []

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
            names: list[str] = []
            t = tool.strip().lower()
            if t == "pyinstaller":
                names = ["pyinstaller", "pyinstaller.exe", "pyinstaller-script.py"]
            elif t == "nuitka":
                names = ["nuitka", "nuitka3", "nuitka.exe", "nuitka-script.py"]
            elif t == "cx_freeze":
                names = ["cxfreeze", "cxfreeze.exe", "cxfreeze-script.py"]
            else:
                # generic: try tool, tool.exe, and tool-script.py
                names = [t, f"{t}.exe", f"{t}-script.py"]
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
        """Non-blocking check for tool presence in venv.
        Uses has_tool_binary() only (no subprocess run). If uncertain, returns False
        so that callers can trigger the asynchronous ensure_tools_installed() flow.
        """
        return self.has_tool_binary(venv_root, tool)

    def is_tool_installed_system(self, tool: str) -> bool:
        try:
            missing = self._missing_in_system_python([tool])
            return len(missing) == 0
        except Exception:
            return False

    def is_tool_installed_async(self, venv_root: str, tool: str, callback) -> None:
        """Asynchronous check using 'pip show <tool>' via QProcess, then callback(bool).
        Safe for UI: does not block. On any error, returns False.
        """
        try:
            pip_exe = self.pip_path(venv_root)
            if not pip_exe or not os.path.isfile(pip_exe):
                callback(False)
                return
            proc = QProcess(self.parent)

            def _done(code, _status):
                try:
                    callback(code == 0)
                except Exception:
                    pass

            proc.finished.connect(_done)
            proc.setProgram(pip_exe)
            proc.setArguments(["show", tool])
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
            self._venv_check_pkgs = list(tools)
            self._venv_check_index = 0
            self._venv_check_pip_exe = self.pip_path(venv_root)
            self._venv_check_path = venv_root
            self._venv_check_use_python = False
            self.venv_check_progress = ProgressDialog(
                "Vérification du venv", self.parent
            )
            self.venv_check_progress.set_message(f"Vérification de {tools[0]}...")
            self.venv_check_progress.set_progress(0, len(tools))
            self.venv_check_progress.show()
            self._check_next_venv_pkg()
        except Exception as e:
            self._safe_log(f"❌ Erreur ensure_tools_installed: {e}")

    def ensure_tools_installed_system(self, tools: list[str]) -> None:
        """Asynchronously check/install tools in system Python using pip."""
        try:
            self._venv_check_pkgs = list(tools)
            self._venv_check_index = 0
            self._venv_check_pip_exe = sys.executable
            self._venv_check_path = (
                getattr(self.parent, "workspace_dir", None) or os.getcwd()
            )
            self._venv_check_use_python = True
            self.venv_check_progress = ProgressDialog(
                "Vérification du Python système", self.parent
            )
            self.venv_check_progress.set_message(f"Vérification de {tools[0]}...")
            self.venv_check_progress.set_progress(0, len(tools))
            self.venv_check_progress.show()
            self._check_next_venv_pkg()
        except Exception as e:
            self._safe_log(f"❌ Erreur ensure_tools_installed_system: {e}")

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
        try:
            s = str(text or "").strip()
        except Exception:
            s = ""
        if not s:
            return "info"
        emoji_levels = {
            "❌": "error",
            "⚠️": "warning",
            "✅": "success",
            "ℹ️": "info",
            "📝": "state",
            "📋": "state",
            "🔍": "state",
            "🔧": "state",
            "🔨": "state",
            "➡️": "state",
            "📦": "state",
            "🗑️": "state",
        }
        for emoji, lvl in emoji_levels.items():
            if s.startswith(emoji):
                return lvl
        low = s.lower()
        if any(tok in low for tok in ("error", "erreur", "échec", "echec", "failed", "invalid", "refus")):
            return "error"
        if any(tok in low for tok in ("warning", "avert", "warn", "attention")):
            return "warning"
        if any(tok in low for tok in ("success", "succès", "reussi", "réussi")):
            return "success"
        if any(tok in low for tok in ("state", "status", "état", "etat")):
            return "state"
        return "info"

    def _safe_log(self, text: str, text_en: str | None = None, level: str | None = None):
        gui = getattr(self, "parent", None) or self
        lvl = level or self._infer_log_level(text_en if text_en is not None else text)
        try:
            if text_en is not None:
                log_i18n_level(gui, lvl, text, text_en)
            else:
                log_with_level(gui, lvl, text)
            return
        except Exception:
            pass
        try:
            # Fallback: If both FR/EN provided and parent has translator, resolve first.
            if text_en is not None and hasattr(self.parent, "tr"):
                try:
                    text = self.parent.tr(text, text_en)
                except Exception:
                    pass
            if hasattr(self.parent, "_safe_log"):
                self.parent._safe_log(text)
                return
        except Exception:
            pass
        try:
            if hasattr(self.parent, "log") and self.parent.log:
                self.parent.log.append(text)
            else:
                print(text)
        except Exception:
            try:
                print(text)
            except Exception:
                pass

    def _is_stdlib_module(self, module_name: str) -> bool:
        """Check if a module is part of Python's standard library."""
        try:
            import sys
            import sysconfig
            import importlib.util

            # Check if it's a built-in module
            if module_name in sys.builtin_module_names:
                return True

            # Try to find the module spec
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                return False

            # Check if it's a built-in or frozen module
            if getattr(spec, "origin", None) in ("built-in", "frozen"):
                return True

            # Check if it's in the stdlib path
            stdlib_path = sysconfig.get_path("stdlib") or ""
            stdlib_path = os.path.realpath(stdlib_path)

            if getattr(spec, "origin", None):
                origin_path = os.path.realpath(spec.origin)
                if os.path.commonpath([origin_path, stdlib_path]) == stdlib_path:
                    return True

            for loc in spec.submodule_search_locations or []:
                loc_path = os.path.realpath(loc)
                try:
                    if os.path.commonpath([loc_path, stdlib_path]) == stdlib_path:
                        return True
                except Exception:
                    pass

            return False
        except Exception:
            return False

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
                        f"⚠️ Failed to remove {path} after {max_retries} attempts: {e}"
                    )
                    return False
        return False

    def _safe_mkdir(self, path: str) -> bool:
        """Safely create a directory with error handling."""
        try:
            os.makedirs(path, exist_ok=True)
            return True
        except Exception as e:
            self._safe_log(f"⚠️ Failed to create directory {path}: {e}")
            return False

    def _prompt_recreate_invalid_venv(self, venv_root: str, reason: str) -> bool:
        """Show an English message box explaining the invalid venv and propose deletion/recreation.
        Returns True if user accepted to recreate, False otherwise.
        """
        try:
            title = "Environnement virtuel invalide / Invalid virtual environment"
            folder = os.path.basename(os.path.normpath(venv_root))
            msg = (
                "L'environnement virtuel du workspace est invalide :\n"
                f"- {reason}\n\n"
                f"Voulez-vous supprimer le dossier '{folder}' et le recréer ?\n\n"
                "The workspace virtual environment is invalid:\n"
                f"- {reason}\n\n"
                f"Do you want to delete the '{folder}' folder and recreate it?"
            )
            reply = QMessageBox.question(
                self.parent,
                title,
                msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                try:
                    shutil.rmtree(venv_root)
                    self._safe_log(f"🗑️ Deleted invalid venv: {venv_root}")
                except Exception as e:
                    try:
                        QMessageBox.critical(
                            self.parent,
                            title,
                            f"Échec suppression venv / Failed to delete venv: {e}",
                        )
                    except Exception:
                        pass
                    return False
                # Recreate fresh venv under the workspace
                try:
                    workspace_dir = os.path.dirname(venv_root)
                    self.create_venv_if_needed(workspace_dir)
                    return True
                except Exception as e:
                    try:
                        QMessageBox.critical(
                            self.parent,
                            title,
                            f"Échec de recréation du venv / Failed to recreate venv: {e}",
                        )
                    except Exception:
                        pass
                    return False
            return False
        except Exception:
            return False

    # ---------- Venv validation ----------
    def _is_within(self, path: str, root: str) -> bool:
        try:
            rp = os.path.realpath(path)
            rr = os.path.realpath(root)
            return os.path.commonpath([rp, rr]) == rr
        except Exception:
            return False

    def validate_venv_strict(self, venv_root: str) -> tuple[bool, str]:
        """Validation stricte d'un venv.
        Retourne (ok, raison_si_ko).
        Règles:
          - Dossier existant
          - pyvenv.cfg présent
          - Scripts/python.exe (Windows) ou bin/python[3] (POSIX) présent
          - include-system-site-packages=false (refus si true)
          - pyvenv.cfg, dossier Scripts/bin et exécutable Python doivent rester confinés dans le venv (pas de liens sortants)
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
        ok, _ = self.validate_venv_strict(venv_root)
        return ok

    # ---------- System Python suggestion ----------
    def _normalize_dist_name(self, name: str) -> str:
        try:
            return name.strip().lower().replace("_", "-")
        except Exception:
            return str(name).strip().lower()

    def _parse_requirements_file(self, req_path: str, seen: set | None = None) -> list[str]:
        seen = seen or set()
        try:
            req_path = os.path.abspath(req_path)
        except Exception:
            return []
        if req_path in seen:
            return []
        seen.add(req_path)

        deps: list[str] = []
        try:
            with open(req_path, encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return []

        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # Include other requirements files
            if line.startswith("-r ") or line.startswith("--requirement"):
                try:
                    parts = line.split(maxsplit=1)
                    if len(parts) == 2:
                        inc = parts[1].strip()
                        inc_path = os.path.join(os.path.dirname(req_path), inc)
                        deps.extend(self._parse_requirements_file(inc_path, seen))
                except Exception:
                    pass
                continue

            # Editable installs
            if line.startswith("-e ") or line.startswith("--editable"):
                try:
                    parts = line.split(maxsplit=1)
                    line = parts[1].strip() if len(parts) == 2 else ""
                except Exception:
                    line = ""

            if not line or line.startswith("-"):
                # Skip other pip options (-f, --index-url, etc.)
                continue

            # Git URL with egg name
            if "#egg=" in line:
                try:
                    name = line.split("#egg=", 1)[1].strip()
                    if name:
                        deps.append(name)
                except Exception:
                    pass
                continue

            # PEP 508 direct reference: name @ url
            if " @ " in line:
                try:
                    name = line.split(" @ ", 1)[0].strip()
                    if name:
                        deps.append(name)
                except Exception:
                    pass
                continue

            # Strip environment markers
            if ";" in line:
                line = line.split(";", 1)[0].strip()

            # Strip extras
            if "[" in line:
                line = line.split("[", 1)[0].strip()

            # Strip version specifiers
            try:
                import re as _re

                base = _re.split(r"(===|==|~=|!=|<=|>=|<|>)", line, maxsplit=1)[0]
                base = base.strip()
            except Exception:
                base = line.strip()

            if base:
                deps.append(base)

        # Deduplicate while preserving order
        seen_names = set()
        ordered = []
        for d in deps:
            if d not in seen_names:
                seen_names.add(d)
                ordered.append(d)
        return ordered

    def _collect_declared_dependencies(self, workspace_dir: str) -> tuple[list[str], bool]:
        try:
            workspace_dir = os.path.abspath(workspace_dir)
        except Exception:
            return [], False

        try:
            req_files = self._find_requirements_files(workspace_dir, workspace_dir)
        except Exception:
            req_files = []

        if not req_files:
            return [], False

        # Rebuild patterns to prioritize
        try:
            from Core.ArkConfigManager import load_ark_config, get_dependency_options

            ark_config = load_ark_config(workspace_dir)
            dep_opts = get_dependency_options(ark_config)
            patterns = dep_opts.get(
                "requirements_files",
                [
                    "requirements.txt",
                    "requirements-prod.txt",
                    "requirements-dev.txt",
                    "Pipfile",
                    "Pipfile.lock",
                    "pyproject.toml",
                    "setup.py",
                    "setup.cfg",
                    "poetry.lock",
                    "conda.yml",
                    "environment.yml",
                ],
            )
        except Exception:
            patterns = [
                "requirements.txt",
                "requirements-prod.txt",
                "requirements-dev.txt",
                "Pipfile",
                "Pipfile.lock",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "poetry.lock",
                "conda.yml",
                "environment.yml",
            ]

        pattern_index = {p: i for i, p in enumerate(patterns)}

        def _prio(path: str) -> int:
            base = os.path.basename(path)
            if base in pattern_index:
                return pattern_index[base]
            if base.startswith("requirements-") and base.endswith(".txt"):
                return pattern_index.get("requirements.txt", 0) + 1
            return len(patterns) + 10

        req_files.sort(key=_prio)
        chosen = req_files[0]
        base = os.path.basename(chosen)

        deps: list[str] = []
        if base.endswith(".txt"):
            deps = self._parse_requirements_file(chosen)
        elif base == "Pipfile":
            deps = self._extract_requirements_from_pipfile(chosen)
        elif base == "pyproject.toml":
            deps = self._extract_requirements_from_pyproject(chosen)
        elif base in ("setup.py", "setup.cfg"):
            deps = self._extract_requirements_from_setup(chosen)
        else:
            # Unsupported source for now
            deps = []

        return deps, True

    def _missing_in_system_python(self, packages: list[str]) -> list[str]:
        try:
            from importlib.metadata import PackageNotFoundError, distribution

            missing = []
            for pkg in packages:
                if not pkg:
                    continue
                name = str(pkg).strip()
                if not name:
                    continue
                normalized = self._normalize_dist_name(name)
                try:
                    distribution(name)
                    continue
                except PackageNotFoundError:
                    pass
                except Exception:
                    pass
                if normalized != name:
                    try:
                        distribution(normalized)
                        continue
                    except PackageNotFoundError:
                        pass
                    except Exception:
                        pass
                missing.append(name)
            return missing
        except Exception:
            return packages

    def _can_use_system_python(self) -> tuple[bool, list[str], bool]:
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

    def _apply_system_python(self) -> None:
        try:
            setattr(self.parent, "use_system_python", True)
        except Exception:
            pass
        try:
            self.parent.venv_path_manuel = None
        except Exception:
            pass
        try:
            if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                label = None
                try:
                    tr = getattr(self.parent, "_tr", {}) if hasattr(self.parent, "_tr") else {}
                    label = tr.get("venv_label_system") if isinstance(tr, dict) else None
                except Exception:
                    label = None
                if not label:
                    label = self.parent.tr(
                        "Venv sélectionné : Python système",
                        "Venv selected: System Python",
                    )
                self.parent.venv_label.setText(label)
        except Exception:
            pass
        try:
            self._safe_log("✅ Utilisation de Python système pour la compilation.")
        except Exception:
            pass
        try:
            workspace_dir = getattr(self.parent, "workspace_dir", None)
            self.save_workspace_pref(workspace_dir)
        except Exception:
            pass

    # ---------- Manual selection ----------
    def select_venv_manually(self):
        try:
            ok_sys, missing, has_source = self._can_use_system_python()
            if ok_sys:
                title = self.parent.tr("Suggestion de venv", "Venv suggestion")
                if has_source:
                    msg = self.parent.tr(
                        "Python système contient les dépendances nécessaires.\n"
                        "Souhaitez-vous l'utiliser ?",
                        "System Python has the required dependencies.\n"
                        "Do you want to use it?",
                    )
                else:
                    msg = self.parent.tr(
                        "Aucun fichier de dépendances détecté.\n"
                        "Souhaitez-vous utiliser Python système ?",
                        "No dependency file detected.\n"
                        "Do you want to use System Python?",
                    )
                reply = QMessageBox.question(
                    self.parent, title, msg, QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._apply_system_python()
                    return
            else:
                if missing:
                    try:
                        self._safe_log(
                            "ℹ️ Python système incomplet: "
                            + ", ".join(sorted(set(missing)))
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        folder = QFileDialog.getExistingDirectory(
            self.parent,
            self.parent.tr("Choisir un dossier venv", "Choose a venv folder"),
            "",
        )
        if folder:
            path = os.path.abspath(folder)
            ok, reason = self.validate_venv_strict(path)
            if ok:
                try:
                    setattr(self.parent, "use_system_python", False)
                except Exception:
                    pass
                self.parent.venv_path_manuel = path
                if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                    self.parent.venv_label.setText(f"Venv sélectionné : {path}")
                self._safe_log(f"✅ Venv valide sélectionné: {path}")
                try:
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    self.save_workspace_pref(workspace_dir)
                except Exception:
                    pass
            else:
                self._safe_log(f"❌ Venv refusé: {reason}")
                self.parent.venv_path_manuel = None
                try:
                    setattr(self.parent, "use_system_python", False)
                except Exception:
                    pass
                if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                    self.parent.venv_label.setText("Venv sélectionné : Aucun")
                try:
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    self.save_workspace_pref(workspace_dir)
                except Exception:
                    pass
                # Message concis avec actions proposées
                try:
                    def _t(_key: str, fr: str, en: str) -> str:
                        try:
                            return self.parent.tr(fr, en)
                        except Exception:
                            return en

                    box = QMessageBox(self.parent)
                    box.setWindowTitle(
                        _t("msg_invalid_venv_title", "Venv invalide", "Invalid Venv")
                    )
                    box.setText(
                        _t(
                            "msg_invalid_venv_text",
                            "Le dossier sélectionné n'est pas un venv valide. Réessayer ou créer un venv ?",
                            "The selected folder is not a valid venv. Retry or create a venv?",
                        )
                    )
                    if reason:
                        try:
                            box.setInformativeText(str(reason))
                        except Exception:
                            pass
                    btn_retry = box.addButton(
                        _t("action_retry", "Réessayer", "Retry"),
                        QMessageBox.AcceptRole,
                    )
                    btn_create = None
                    workspace_dir = getattr(self.parent, "workspace_dir", None)
                    if workspace_dir:
                        btn_create = box.addButton(
                            _t("action_create_venv", "Créer un venv", "Create venv"),
                            QMessageBox.ActionRole,
                        )
                    box.addButton(
                        _t("action_cancel", "Annuler", "Cancel"),
                        QMessageBox.RejectRole,
                    )
                    box.exec()
                    if box.clickedButton() == btn_retry:
                        self.select_venv_manually()
                        return
                    if btn_create and box.clickedButton() == btn_create:
                        try:
                            self.create_venv_if_needed(workspace_dir)
                        except Exception:
                            pass
                        return
                except Exception:
                    pass
        else:
            self.parent.venv_path_manuel = None
            try:
                setattr(self.parent, "use_system_python", False)
            except Exception:
                pass
            if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                self.parent.venv_label.setText("Venv sélectionné : Aucun")
            try:
                workspace_dir = getattr(self.parent, "workspace_dir", None)
                self.save_workspace_pref(workspace_dir)
            except Exception:
                pass

    # ---------- Existing venv: check and install tools ----------
    def check_tools_in_venv(self, venv_path: str):
        try:
            ok, reason = self.validate_venv_strict(venv_path)
            if not ok:
                self._safe_log(f"❌ Invalid venv: {reason}")
                # Offer to delete and recreate
                self._prompt_recreate_invalid_venv(venv_path, reason)
                return

            # Vérification asynchrone de la liaison python/pip → venv
            def _after_binding(ok_bind: bool):
                if not ok_bind:
                    self._safe_log(
                        "❌ Invalid venv binding: python/pip do not point to the selected venv."
                    )
                    self._prompt_recreate_invalid_venv(
                        venv_path, "Python/pip do not point to the selected venv"
                    )
                    return
                pip_exe = os.path.join(
                    venv_path,
                    "Scripts" if platform.system() == "Windows" else "bin",
                    "pip",
                )
                self._venv_check_pkgs = ["pyinstaller", "nuitka", "cx_freeze"]
                self._venv_check_index = 0
                self._venv_check_pip_exe = pip_exe
                self._venv_check_path = venv_path
                self.venv_check_progress = ProgressDialog(
                    "Vérification du venv", self.parent
                )
                self.venv_check_progress.set_message("Vérification de PyInstaller...")
                self.venv_check_progress.set_progress(0, len(self._venv_check_pkgs))
                self.venv_check_progress.show()
                self._check_next_venv_pkg()

            self._verify_venv_binding_async(venv_path, _after_binding)
        except Exception as e:
            self._safe_log(f"❌ Erreur lors de la vérification du venv: {e}")

    def _check_next_venv_pkg(self):
        if self._venv_check_index >= len(self._venv_check_pkgs):
            try:
                self.venv_check_progress.set_message("Vérification terminée.")
                total = (
                    len(self._venv_check_pkgs)
                    if hasattr(self, "_venv_check_pkgs") and self._venv_check_pkgs
                    else 0
                )
                self.venv_check_progress.set_progress(total, total)
                self.venv_check_progress.close()
            except Exception:
                pass
            # Installer les dépendances du projet si un requirements.txt est présent
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
        if self._venv_check_use_python:
            process.setArguments(["-m", "pip", "show", pkg])
        else:
            process.setArguments(["show", pkg])
        process.setWorkingDirectory(self._venv_check_path)
        process.finished.connect(
            lambda code, status: self._on_venv_pkg_checked(process, code, status, pkg)
        )
        process.start()
        # Safety timeout for pip show (30s)
        self._arm_process_timeout(process, 30_000, f"pip show {pkg}")

    def _on_venv_pkg_checked(self, process, code, status, pkg):
        if getattr(self.parent, "_closing", False):
            return
        if code == 0:
            if self._venv_check_use_python:
                self._safe_log(f"✅ {pkg} déjà installé (Python système).")
            else:
                self._safe_log(f"✅ {pkg} déjà installé dans le venv.")
            self._venv_check_index += 1
            try:
                next_label = (
                    self._venv_check_pkgs[self._venv_check_index]
                    if self._venv_check_index < len(self._venv_check_pkgs)
                    else ""
                )
                self.venv_check_progress.set_message(f"Vérification de {next_label}...")
                self.venv_check_progress.set_progress(
                    self._venv_check_index, len(self._venv_check_pkgs)
                )
            except Exception:
                pass
            self._check_next_venv_pkg()
        else:
            self._safe_log(f"📦 Installation automatique de {pkg}...")
            try:
                self.venv_check_progress.set_message(f"Installation de {pkg}...")
                self.venv_check_progress.progress.setRange(0, 0)
            except Exception:
                pass
            process2 = QProcess(self.parent)
            self._venv_check_install_process = process2
            process2.setProgram(self._venv_check_pip_exe)
            if self._venv_check_use_python:
                process2.setArguments(
                    ["-m", "pip", "install"] + self._pip_break_system_args() + [pkg]
                )
            else:
                process2.setArguments(
                    ["install"] + self._pip_break_system_args() + [pkg]
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
        if getattr(self.parent, "_closing", False):
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        try:
            if self.venv_check_progress:
                lines = data.strip().splitlines()
                if lines:
                    self.venv_check_progress.set_message(lines[-1])
        except Exception:
            pass
        self._safe_log(data)

    def verify_venv_binding(self, venv_root: str) -> bool:
        """Conservation de la version synchrone pour compat interne (éviter blocages ailleurs)."""
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
        """Vérifie de manière asynchrone que python et pip du venv pointent bien vers ce venv, puis appelle callback(bool)."""
        try:
            vpython = self.python_path(venv_root)
            if not os.path.isfile(vpython):
                callback(False)
                return
            # Étape 1: vérifier sys.prefix
            p1 = QProcess(self.parent)

            def _p1_finished(code, _status):
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
                    try:
                        if process.state() != QProcess.NotRunning:
                            self._safe_log(
                                f"⏱️ Timeout exceeded for {label} ({timeout_ms} ms). Killing process…"
                            )
                            process.kill()
                    except Exception:
                        pass

                t.timeout.connect(_on_timeout)
                t.start(timeout_ms)
                # keep reference to avoid GC
                self._proc_timers.append(t)

                # also attach to process so timer can be cleared if process finishes earlier
                def _clear_timer(*_args):
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
        - Has pyinstaller: +50
        - Has nuitka: +50
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
            tools_to_check = [
                ("pyinstaller", 50),
                ("nuitka", 50),
                ("cx_freeze", 50),
            ]
            for tool, tool_score in tools_to_check:
                if self.has_tool_binary(venv_path, tool):
                    score += tool_score
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
                self._safe_log("ℹ️ Aucun venv valide trouvé dans le workspace.")
                return None

            if len(venvs) == 1:
                self._safe_log(f"✅ Un seul venv trouvé: {venvs[0]}")
                return venvs[0]

            # Multiple venvs found - score and select the best
            self._safe_log(
                f"ℹ️ {len(venvs)} venv(s) trouvé(s), sélection du meilleur..."
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
                self._safe_log("❌ Aucun venv valide avec une bonne liaison.")
                return None

            self._safe_log(
                f"✅ Meilleur venv sélectionné: {os.path.basename(best_venv)} (score={best_score})"
            )
            return best_venv
        except Exception as e:
            self._safe_log(f"⚠️ Erreur lors de la sélection du meilleur venv: {e}")
            return None

    def _on_venv_pkg_installed(self, process, code, status, pkg):
        if getattr(self.parent, "_closing", False):
            return
        if code == 0:
            self._safe_log(f"✅ {pkg} installé dans le venv.")
        else:
            self._safe_log(f"❌ Erreur installation {pkg} (code {code})")
        self._venv_check_index += 1
        try:
            self.venv_check_progress.progress.setRange(0, len(self._venv_check_pkgs))
            self.venv_check_progress.set_progress(
                self._venv_check_index, len(self._venv_check_pkgs)
            )
        except Exception:
            pass
        self._check_next_venv_pkg()

    # ---------- Create venv if needed ----------
    def create_venv_if_needed(self, path: str, prefer_manager: bool = True):
        existing, default_path = self._detect_venv_in(path)
        venv_path = existing or default_path
        if existing:
            # Validate existing venv; if invalid, propose deletion/recreation
            ok, reason = self.validate_venv_strict(venv_path)
            if not ok:
                self._safe_log(f"❌ Invalid venv detected: {reason}")
                recreated = self._prompt_recreate_invalid_venv(venv_path, reason)
                if not recreated:
                    return
            else:
                return
        # Manager-aware creation when possible
        if prefer_manager:
            try:
                manager = self._detect_environment_manager(path)
            except Exception:
                manager = "pip"
            try:
                cmd = self._get_manager_command(manager, "create_venv")
            except Exception:
                cmd = None
            if manager and manager != "pip" and cmd and self._is_tool_available(manager):
                self._safe_log(
                    f"🔧 Aucun venv trouvé, création avec {manager} (ManagerMapping.yml)..."
                )
                self.create_venv_with_manager(path, venv_path)
                return

        self._safe_log("🔧 Aucun venv trouvé, création automatique...")
        try:
            # Recherche d'un python embarqué à côté de l'exécutable
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
            # Recherche également les interpréteurs système disponibles dans le PATH
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
            # Journalisation du type d'interpréteur détecté
            base = os.path.basename(python_candidate).lower()
            if (
                python_candidate.startswith(exe_dir)
                or "python_embedded" in python_candidate
            ):
                self._safe_log(
                    f"➡️ Utilisation de l'interpréteur Python embarqué : {python_candidate}"
                )
            elif base in ("py", "py.exe") or shutil.which(base):
                self._safe_log(
                    f"➡️ Utilisation de l'interpréteur système : {python_candidate}"
                )
            else:
                self._safe_log(f"➡️ Utilisation de sys.executable : {python_candidate}")

            self.venv_progress_dialog = ProgressDialog(
                "Création de l'environnement virtuel", self.parent
            )
            self.venv_progress_dialog.set_message("Création du venv...")

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
            self.venv_progress_dialog.show()
            process.start()
            # Safety timeout for venv creation (10 min)
            self._arm_process_timeout(process, 600_000, "venv creation")
        except Exception as e:
            self._safe_log(
                f"❌ Échec de création du venv ou installation de PyInstaller : {e}"
            )

    def _on_venv_output(self, process, error=False):
        if getattr(self.parent, "_closing", False):
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        try:
            if self.venv_progress_dialog:
                lines = data.strip().splitlines()
                if lines:
                    self.venv_progress_dialog.set_message(lines[-1])
                self._venv_progress_lines += len(lines)
                self.venv_progress_dialog.set_progress(self._venv_progress_lines, 0)
        except Exception:
            pass
        self._safe_log(data)

    def _on_venv_created(self, process, code, status, venv_path):
        if getattr(self.parent, "_closing", False):
            return
        if code == 0:
            self._safe_log("✅ Environnement virtuel créé avec succès.")
            try:
                if self.venv_progress_dialog:
                    self.venv_progress_dialog.set_message("Venv créé.")
                    self.venv_progress_dialog.close()
            except Exception:
                pass
            try:
                if not getattr(self.parent, "use_system_python", False):
                    if not getattr(self.parent, "venv_path_manuel", None):
                        self.parent.venv_path_manuel = venv_path
                        if hasattr(self.parent, "venv_label") and self.parent.venv_label:
                            self.parent.venv_label.setText(f"Venv sélectionné : {venv_path}")
                self.save_workspace_pref(os.path.dirname(venv_path))
            except Exception:
                pass
            # Installer les dépendances du projet à partir de requirements.txt si présent
            try:
                self.install_requirements_if_needed(os.path.dirname(venv_path))
            except Exception:
                pass
        else:
            self._safe_log(f"❌ Échec de création du venv (code {code})")
            try:
                if self.venv_progress_dialog:
                    self.venv_progress_dialog.set_message(
                        "Erreur lors de la création du venv."
                    )
                    self.venv_progress_dialog.close()
            except Exception:
                pass
        QApplication.processEvents()

    # ---------- Requirements detection and generation ----------
    def _find_requirements_files(
        self, path: str, workspace_dir: str | None = None
    ) -> list[str]:
        """Find all potential requirements files in the project.
        Supports: requirements.txt, requirements-*.txt, Pipfile, Pipfile.lock,
                  pyproject.toml, setup.py, setup.cfg, poetry.lock, etc.

        Uses ARK config to determine priority order if available.
        """
        try:
            path = os.path.abspath(path)
        except Exception:
            return []

        requirements_files = []

        # Load ARK config to get requirements file patterns
        try:
            from Core.ArkConfigManager import load_ark_config, get_dependency_options

            if workspace_dir:
                ark_config = load_ark_config(workspace_dir)
                dep_opts = get_dependency_options(ark_config)
                patterns = dep_opts.get(
                    "requirements_files",
                    [
                        "requirements.txt",
                        "requirements-prod.txt",
                        "requirements-dev.txt",
                        "Pipfile",
                        "Pipfile.lock",
                        "pyproject.toml",
                        "setup.py",
                        "setup.cfg",
                        "poetry.lock",
                        "conda.yml",
                        "environment.yml",
                    ],
                )
            else:
                patterns = [
                    "requirements.txt",
                    "requirements-prod.txt",
                    "requirements-dev.txt",
                    "Pipfile",
                    "Pipfile.lock",
                    "pyproject.toml",
                    "setup.py",
                    "setup.cfg",
                    "poetry.lock",
                    "conda.yml",
                    "environment.yml",
                ]
        except Exception:
            patterns = [
                "requirements.txt",
                "requirements-prod.txt",
                "requirements-dev.txt",
                "Pipfile",
                "Pipfile.lock",
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "poetry.lock",
                "conda.yml",
                "environment.yml",
            ]

        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if not os.path.isfile(item_path):
                    continue

                # Check exact matches
                if item in patterns:
                    requirements_files.append(item_path)
                # Check wildcard patterns
                elif item.startswith("requirements-") and item.endswith(".txt"):
                    requirements_files.append(item_path)
        except Exception:
            pass

        return requirements_files

    def _generate_requirements_from_imports(self, workspace_dir: str) -> str | None:
        """Generate requirements.txt by analyzing Python imports in the project.
        Returns the path to the generated requirements.txt, or None if failed.
        """
        try:
            import ast
            import re as _re

            self._safe_log(
                "🔍 Génération de requirements.txt à partir des imports du projet..."
            )

            modules = set()
            python_files = []

            # Find all Python files
            for root, dirs, files in os.walk(workspace_dir):
                # Skip venv directories
                dirs[:] = [
                    d
                    for d in dirs
                    if d not in (".venv", "venv", ".env", "env", "__pycache__")
                ]
                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

            # Analyze imports
            for py_file in python_files:
                try:
                    with open(py_file, encoding="utf-8", errors="ignore") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=py_file)

                    # Standard imports
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                modules.add(alias.name.split(".")[0])
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                modules.add(node.module.split(".")[0])

                    # Dynamic imports
                    dynamic_imports = _re.findall(
                        r"__import__\(['\"]([\w\.]+)['\"]\)", source
                    )
                    modules.update([mod.split(".")[0] for mod in dynamic_imports])
                    importlib_imports = _re.findall(
                        r"importlib\.import_module\(['\"]([\w\.]+)['\"]\)", source
                    )
                    modules.update([mod.split(".")[0] for mod in importlib_imports])
                except Exception:
                    pass

            # Filter out stdlib modules
            external_modules = []
            for mod in sorted(modules):
                if not self._is_stdlib_module(mod):
                    external_modules.append(mod)

            if not external_modules:
                self._safe_log("ℹ️ Aucun module externe détecté dans le projet.")
                return None

            # Generate requirements.txt
            req_path = os.path.join(workspace_dir, "requirements.txt")
            try:
                with open(req_path, "w", encoding="utf-8") as f:
                    f.write("# Auto-generated requirements.txt\n")
                    f.write("# Generated from project imports\n\n")
                    for mod in external_modules:
                        f.write(f"{mod}\n")

                self._safe_log(
                    f"✅ requirements.txt généré avec {len(external_modules)} dépendances"
                )
                return req_path
            except Exception as e:
                self._safe_log(
                    f"❌ Erreur lors de la génération de requirements.txt: {e}"
                )
                return None
        except Exception as e:
            self._safe_log(f"⚠️ Erreur lors de l'analyse des imports: {e}")
            return None

    def _extract_requirements_from_pyproject(self, pyproject_path: str) -> list[str]:
        """Extract dependencies from pyproject.toml (Poetry, Flit, etc.)"""
        try:
            import re as _re

            with open(pyproject_path, encoding="utf-8") as f:
                content = f.read()

            # Simple regex-based extraction (not a full TOML parser)
            # Look for dependencies sections
            deps = []

            # Poetry format: [tool.poetry.dependencies]
            poetry_match = _re.search(
                r"\[tool\.poetry\.dependencies\](.*?)(?=\[|$)", content, _re.DOTALL
            )
            if poetry_match:
                section = poetry_match.group(1)
                # Extract package names (simple format: package = "version")
                for line in section.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        pkg_name = line.split("=")[0].strip().strip("\"'")
                        if pkg_name and pkg_name != "python":
                            deps.append(pkg_name)

            # Flit format: [project] dependencies
            flit_match = _re.search(r"\[project\](.*?)(?=\[|$)", content, _re.DOTALL)
            if flit_match:
                section = flit_match.group(1)
                deps_match = _re.search(
                    r"dependencies\s*=\s*\[(.*?)\]", section, _re.DOTALL
                )
                if deps_match:
                    deps_str = deps_match.group(1)
                    for line in deps_str.split(","):
                        line = line.strip().strip("\"'")
                        if line:
                            # Extract package name from "package>=1.0" format
                            pkg_name = _re.split(r"[<>=!]", line)[0].strip()
                            if pkg_name:
                                deps.append(pkg_name)

            return list(set(deps))
        except Exception:
            return []

    def _extract_requirements_from_setup(self, setup_path: str) -> list[str]:
        """Extract dependencies from setup.py or setup.cfg"""
        try:
            import re as _re

            with open(setup_path, encoding="utf-8") as f:
                content = f.read()

            deps = []

            # Look for install_requires
            match = _re.search(r"install_requires\s*=\s*\[(.*?)\]", content, _re.DOTALL)
            if match:
                deps_str = match.group(1)
                for line in deps_str.split(","):
                    line = line.strip().strip("\"'")
                    if line:
                        pkg_name = _re.split(r"[<>=!]", line)[0].strip()
                        if pkg_name:
                            deps.append(pkg_name)

            return list(set(deps))
        except Exception:
            return []

    def _extract_requirements_from_pipfile(self, pipfile_path: str) -> list[str]:
        """Extract dependencies from Pipfile"""
        try:
            import re as _re

            with open(pipfile_path, encoding="utf-8") as f:
                content = f.read()

            deps = []

            # Look for [packages] section
            match = _re.search(r"\[packages\](.*?)(?=\[|$)", content, _re.DOTALL)
            if match:
                section = match.group(1)
                for line in section.split("\n"):
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        pkg_name = line.split("=")[0].strip().strip("\"'")
                        if pkg_name:
                            deps.append(pkg_name)

            return list(set(deps))
        except Exception:
            return []

    def _get_requirements_file(self, workspace_dir: str) -> str | None:
        """Get or generate a requirements file for the project.

        Strategy:
        1. Load ARK config to get requirements file preferences
        2. Look for existing requirements files (requirements.txt, Pipfile, pyproject.toml, etc.)
        3. If found, convert to requirements.txt if needed
        4. If not found, generate from project imports (if enabled in ARK config)
        5. Return path to requirements.txt
        """
        try:
            workspace_dir = os.path.abspath(workspace_dir)

            # Load ARK config to get requirements file preferences
            try:
                from Core.ArkConfigManager import (
                    load_ark_config,
                    get_dependency_options,
                )

                ark_config = load_ark_config(workspace_dir)
                dep_opts = get_dependency_options(ark_config)
                auto_generate = dep_opts.get("auto_generate_from_imports", True)
                output_file = dep_opts.get("generate_output_file", "requirements.txt")
            except Exception:
                auto_generate = True
                output_file = "requirements.txt"

            # Check for existing requirements files
            req_files = self._find_requirements_files(workspace_dir, workspace_dir)

            if req_files:
                self._safe_log(
                    f"ℹ️ Fichiers de dépendances trouvés: {[os.path.basename(f) for f in req_files]}"
                )

                # If requirements.txt exists, use it
                req_txt = os.path.join(workspace_dir, output_file)
                if os.path.isfile(req_txt):
                    return req_txt

                # Try to convert other formats to requirements.txt
                for req_file in req_files:
                    basename = os.path.basename(req_file)
                    deps = []

                    if basename == "Pipfile":
                        deps = self._extract_requirements_from_pipfile(req_file)
                    elif basename == "pyproject.toml":
                        deps = self._extract_requirements_from_pyproject(req_file)
                    elif basename in ("setup.py", "setup.cfg"):
                        deps = self._extract_requirements_from_setup(req_file)
                    elif basename.startswith("requirements-"):
                        # Use requirements-*.txt files
                        try:
                            with open(req_file, encoding="utf-8") as f:
                                deps = [
                                    line.strip()
                                    for line in f
                                    if line.strip() and not line.startswith("#")
                                ]
                        except Exception:
                            pass

                    if deps:
                        # Generate requirements.txt from extracted deps
                        try:
                            with open(req_txt, "w", encoding="utf-8") as f:
                                f.write(f"# Converted from {basename}\n")
                                f.write(
                                    f"# ARK Config: generate_output_file = {output_file}\n\n"
                                )
                                for dep in deps:
                                    f.write(f"{dep}\n")
                            self._safe_log(
                                f"✅ {output_file} généré à partir de {basename}"
                            )
                            return req_txt
                        except Exception as e:
                            self._safe_log(
                                f"⚠️ Erreur lors de la conversion de {basename}: {e}"
                            )

            # No requirements file found
            if not auto_generate:
                self._safe_log(
                    "ℹ️ Auto-génération des requirements désactivée dans ARK config"
                )
                return None

            # Generate from imports
            return self._generate_requirements_from_imports(workspace_dir)
        except Exception as e:
            self._safe_log(f"⚠️ Erreur lors de la détection des requirements: {e}")
            return None

    # ---------- Install requirements.txt ----------
    def install_requirements_if_needed(self, path: str, force_pip: bool = False):
        # Prefer manager-based installation when a manager is detected and no manual venv is set.
        if not force_pip:
            try:
                manual = getattr(self.parent, "venv_path_manuel", None)
                manager = self._detect_environment_manager(path)
                if not manual and manager and manager != "pip":
                    self.install_dependencies_with_manager(path)
                    return
            except Exception:
                pass

        # Get or generate requirements file
        req_path = self._get_requirements_file(path)
        if not req_path:
            self._safe_log("ℹ️ Aucun fichier de dépendances trouvé ou généré.")
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
            self._safe_log(f"⚠️ Invalid venv for requirements: {reason}")
            # Offer to delete and recreate, then retry installation
            if self._prompt_recreate_invalid_venv(venv_root, reason):
                # if recreated, try install again
                self._start_requirements_install(path, venv_root, req_path)
            return

        # Vérifier la liaison de manière asynchrone, puis démarrer l'installation
        def _after_binding(ok_bind: bool):
            if not ok_bind:
                self._safe_log(
                    "⚠️ Liaison venv invalide (python/pip ne pointent pas vers le venv); installation ignorée."
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
        py_exe = sys.executable if use_system_python else self.python_path(venv_root)
        if not os.path.isfile(py_exe):
            self._safe_log(
                "⚠️ python introuvable dans le venv; installation requirements ignorée."
            )
            return
        # Compute checksum and skip install if unchanged
        try:
            with open(req_path, "rb") as f:
                data = f.read()
            req_hash = hashlib.sha256(data).hexdigest()
        except Exception as e:
            self._safe_log(f"⚠️ Impossible de calculer le hash de requirements.txt: {e}")
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
                        "✅ requirements.txt déjà installé (aucun changement détecté)."
                    )
                    return
            except Exception:
                pass
        self._safe_log(
            "📦 Installation des dépendances à partir de requirements.txt..."
        )
        try:
            # remember marker info to write after success
            self._req_marker_path = marker_path
            self._req_marker_hash = req_hash
            self._req_path = req_path
            self._venv_python_exe = py_exe
            self._req_use_system_python = bool(use_system_python)
            self._pip_phase = "ensurepip"
            self.progress_dialog = ProgressDialog(
                "Installation des dépendances", self.parent
            )
            self.progress_dialog.set_message("Activation de pip (ensurepip)...")
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
            self.progress_dialog.show()
            process.start()
            # Safety timeout for ensurepip (3 min)
            self._arm_process_timeout(process, 180_000, "ensurepip")
        except Exception as e:
            self._safe_log(f"❌ Échec installation requirements.txt : {e}")

    def _on_pip_output(self, process, error=False):
        if getattr(self.parent, "_closing", False):
            return
        data = (
            process.readAllStandardError().data().decode()
            if error
            else process.readAllStandardOutput().data().decode()
        )
        try:
            if self.progress_dialog:
                # Affiche la dernière ligne reçue
                lines = data.strip().splitlines()
                if lines:
                    self.progress_dialog.set_message(lines[-1])
                self._pip_progress_lines += len(lines)
                # Simule une progression (pip ne donne pas de %)
                self.progress_dialog.set_progress(self._pip_progress_lines, 0)
        except Exception:
            pass
        self._safe_log(data)

    def _on_pip_finished(self, process, code, status):
        if getattr(self.parent, "_closing", False):
            return
        phase = self._pip_phase
        if phase == "ensurepip":
            # Proceed to upgrade pip/setuptools/wheel regardless of ensurepip result
            try:
                if self.progress_dialog:
                    self.progress_dialog.set_message(
                        "Mise à niveau de pip/setuptools/wheel..."
                    )
            except Exception:
                pass
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
                + (self._pip_break_system_args() if getattr(self, "_req_use_system_python", False) else [])
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
                try:
                    if self.progress_dialog:
                        self.progress_dialog.set_message(
                            "Installation des dépendances (requirements.txt)..."
                        )
                except Exception:
                    pass
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
                    f"❌ Échec mise à niveau pip/setuptools/wheel (code {code})"
                )
                try:
                    if self.progress_dialog:
                        self.progress_dialog.set_message(
                            "Échec upgrade pip/setuptools/wheel."
                        )
                except Exception:
                    pass
        else:
            if code == 0:
                self._safe_log("✅ requirements.txt installé.")
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
                try:
                    if self.progress_dialog:
                        self.progress_dialog.set_message("Installation terminée.")
                except Exception:
                    pass
            else:
                self._safe_log(f"❌ Échec installation requirements.txt (code {code})")
                try:
                    if self.progress_dialog:
                        self.progress_dialog.set_message(
                            "Erreur lors de l'installation."
                        )
                except Exception:
                    pass
        try:
            if self.progress_dialog:
                self.progress_dialog.close()
        except Exception:
            pass
        QApplication.processEvents()

    # ---------- Background tasks status/control ----------
    def has_active_tasks(self) -> bool:
        try:
            if self.venv_progress_dialog and self.venv_progress_dialog.isVisible():
                return True
        except Exception:
            pass
        try:
            if self.progress_dialog and self.progress_dialog.isVisible():
                return True
        except Exception:
            pass
        try:
            if self.venv_check_progress and self.venv_check_progress.isVisible():
                return True
        except Exception:
            pass
        return False

    def terminate_tasks(self):
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
                    proc.kill()
            except Exception:
                pass
            setattr(self, attr, None)
        # Close dialogs
        for dlg_attr in [
            "venv_progress_dialog",
            "progress_dialog",
            "venv_check_progress",
        ]:
            dlg = getattr(self, dlg_attr, None)
            try:
                if dlg:
                    dlg.close()
            except Exception:
                pass

    def get_active_task_labels(self, lang: str) -> list[str]:
        """Return active venv task labels in requested language ('English' or 'Français')."""
        labels_fr = {
            "create": "création du venv",
            "reqs": "installation des dépendances",
            "check": "vérification/installation du venv",
        }
        labels_en = {
            "create": "venv creation",
            "reqs": "dependencies installation",
            "check": "venv check/installation",
        }
        L = labels_en if lang == "English" else labels_fr
        out = []
        try:
            if self.venv_progress_dialog and self.venv_progress_dialog.isVisible():
                out.append(L["create"])
        except Exception:
            pass
        try:
            if self.progress_dialog and self.progress_dialog.isVisible():
                out.append(L["reqs"])
        except Exception:
            pass
        try:
            if self.venv_check_progress and self.venv_check_progress.isVisible():
                out.append(L["check"])
        except Exception:
            pass
        return out

    # ---------- Environment Manager Detection & Handling ----------
    def _detect_environment_manager(self, workspace_dir: str) -> str:
        """Detect which environment manager is used in the project.

        Uses ARK configuration to determine priority order if available.
        Falls back to default priority if not configured.

        Default priority order:
        1. Poetry (pyproject.toml with [tool.poetry])
        2. Pipenv (Pipfile)
        3. Conda (environment.yml, conda.yml)
        4. PDM (pyproject.toml with [tool.pdm])
        5. UV (pyproject.toml with [tool.uv])
        6. Pip (requirements.txt, setup.py)
        """
        try:
            workspace_dir = os.path.abspath(workspace_dir)

            # Load ARK configuration to get manager priorities
            try:
                from Core.ArkConfigManager import (
                    load_ark_config,
                    get_environment_manager_options,
                )

                ark_config = load_ark_config(workspace_dir)
                env_manager_opts = get_environment_manager_options(ark_config)
                priority_list = env_manager_opts.get(
                    "priority", ["poetry", "pipenv", "conda", "pdm", "uv", "pip"]
                )
                auto_detect = env_manager_opts.get("auto_detect", True)
                fallback_to_pip = env_manager_opts.get("fallback_to_pip", True)
                self._safe_log(f"📋 Priorités des gestionnaires (ARK): {priority_list}")
            except Exception:
                priority_list = ["poetry", "pipenv", "conda", "pdm", "uv", "pip"]
                auto_detect = True
                fallback_to_pip = True

            if not auto_detect:
                self._safe_log(
                    "ℹ️ Auto-détection des gestionnaires désactivée dans ARK config"
                )
                self._detected_manager = "pip"
                return "pip"

            # Detect available managers
            detected_managers = {}

            # Check for Poetry
            pyproject = os.path.join(workspace_dir, "pyproject.toml")
            if os.path.isfile(pyproject):
                try:
                    with open(pyproject, encoding="utf-8") as f:
                        content = f.read()
                    if "[tool.poetry]" in content:
                        detected_managers["poetry"] = "🎵"
                    if "[tool.pdm]" in content:
                        detected_managers["pdm"] = "📦"
                    if "[tool.uv]" in content:
                        detected_managers["uv"] = "⚡"
                except Exception:
                    pass

            # Check for Pipenv
            if os.path.isfile(os.path.join(workspace_dir, "Pipfile")):
                detected_managers["pipenv"] = "🔧"

            # Check for Conda
            for conda_file in ["environment.yml", "conda.yml", "environment.yaml"]:
                if os.path.isfile(os.path.join(workspace_dir, conda_file)):
                    detected_managers["conda"] = "🐍"
                    break

            # Always consider pip as available
            detected_managers["pip"] = "📝"

            if detected_managers:
                self._safe_log(
                    f"ℹ️ Gestionnaires détectés: {', '.join(detected_managers.keys())}"
                )

            # Select the first available manager from the priority list
            for manager in priority_list:
                if manager in detected_managers:
                    self._detected_manager = manager
                    emoji = detected_managers[manager]
                    self._safe_log(f"{emoji} Gestionnaire sélectionné: {manager}")
                    return manager

            # Fallback to pip if no preferred manager found
            if fallback_to_pip:
                self._detected_manager = "pip"
                self._safe_log("📝 Fallback vers Pip")
                return "pip"

            # If fallback disabled and no manager found, still use pip
            self._detected_manager = "pip"
            return "pip"
        except Exception as e:
            self._safe_log(f"⚠️ Erreur détection gestionnaire: {e}")
            self._detected_manager = "pip"
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

    def _run_cmd_capture(
        self, cmd: list[str], cwd: str, timeout: int = 5
    ) -> str | None:
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=timeout,
            )
            out = (result.stdout or "").strip()
            if out:
                return out
            err = (result.stderr or "").strip()
            if err:
                return err
        except Exception:
            pass
        return None

    def _extract_existing_dir(self, output: str | None) -> str | None:
        if not output:
            return None
        for line in output.splitlines():
            cand = line.strip()
            if not cand:
                continue
            for prefix in ("*", "-", ">", "•"):
                if cand.startswith(prefix):
                    cand = cand[len(prefix) :].strip()
            if cand.startswith(("'", "\"")) and cand.endswith(("'", "\"")):
                cand = cand[1:-1].strip()
            if cand and os.path.isdir(cand):
                return cand
            # Handle "Label: /path" style outputs
            if ":" in cand:
                try:
                    after = cand.split(":", 1)[1].strip()
                    if after and os.path.isdir(after):
                        return after
                except Exception:
                    pass
            # Try to extract a path-like token from the line
            try:
                tokens = cand.replace("'", " ").replace('"', " ").split()
                for tok in tokens:
                    if os.path.isdir(tok):
                        return tok
            except Exception:
                pass
        return None

    def _validate_conda_env(self, env_root: str) -> tuple[bool, str]:
        try:
            if not env_root or not os.path.isdir(env_root):
                return False, "Chemin invalide (dossier manquant)"
            conda_meta = os.path.join(env_root, "conda-meta")
            if not os.path.isdir(conda_meta):
                return False, "conda-meta introuvable"
            bindir = "Scripts" if platform.system() == "Windows" else "bin"
            bpath = os.path.join(env_root, bindir)
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
            return True, ""
        except Exception as e:
            return False, f"Erreur validation conda: {e}"

    def _validate_manager_venv(self, manager: str, venv_root: str) -> tuple[bool, str]:
        if manager == "conda":
            return self._validate_conda_env(venv_root)
        return self.validate_venv_strict(venv_root)

    def _parse_conda_env_spec(self, workspace_dir: str) -> tuple[str | None, str | None]:
        for fname in ("environment.yml", "conda.yml", "environment.yaml"):
            path = os.path.join(workspace_dir, fname)
            if not os.path.isfile(path):
                continue
            try:
                name = None
                prefix = None
                with open(path, encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        lower = s.lower()
                        if lower.startswith("name:"):
                            name = s.split(":", 1)[1].strip().strip("'\"")
                        elif lower.startswith("prefix:"):
                            prefix = s.split(":", 1)[1].strip().strip("'\"")
                return prefix, name
            except Exception:
                pass
        return None, None

    def _find_conda_env_path(self, env_name: str, cwd: str) -> str | None:
        try:
            result = subprocess.run(
                ["conda", "env", "list", "--json"],
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=6,
            )
            if result.returncode != 0:
                return None
            data = json.loads(result.stdout or "{}")
            envs = data.get("envs", []) if isinstance(data, dict) else []
            for p in envs:
                try:
                    if os.path.basename(p) == env_name:
                        return p
                except Exception:
                    pass
        except Exception:
            return None
        return None

    def _detect_manager_existing_venv(self, workspace_dir: str) -> str | None:
        try:
            base = os.path.abspath(workspace_dir)
        except Exception:
            base = workspace_dir

        if base in self._manager_venv_cache:
            return self._manager_venv_cache.get(base)

        manager = self._detect_environment_manager(base)
        if not manager or manager == "pip":
            self._manager_venv_cache[base] = None
            return None

        if not self._is_tool_available(manager):
            self._manager_venv_cache[base] = None
            return None

        path = None
        if manager == "poetry":
            out = self._run_cmd_capture(["poetry", "env", "info", "-p"], base)
            path = self._extract_existing_dir(out)
        elif manager == "pipenv":
            out = self._run_cmd_capture(["pipenv", "--venv"], base)
            path = self._extract_existing_dir(out)
        elif manager == "pdm":
            out = self._run_cmd_capture(["pdm", "venv", "--path"], base)
            path = self._extract_existing_dir(out)
            if not path:
                out = self._run_cmd_capture(["pdm", "venv", "list"], base)
                path = self._extract_existing_dir(out)
        elif manager == "conda":
            prefix, name = self._parse_conda_env_spec(base)
            if prefix and os.path.isdir(prefix):
                path = prefix
            elif name:
                path = self._find_conda_env_path(name, base)
        elif manager == "uv":
            path = None

        if path and os.path.isdir(path):
            ok, reason = self._validate_manager_venv(manager, path)
            if ok:
                self._manager_venv_cache[base] = path
                self._safe_log(f"✅ Venv détecté via {manager}: {path}")
                return path
            self._safe_log(
                f"⚠️ Venv détecté via {manager} mais invalide: {reason}"
            )

        self._manager_venv_cache[base] = None
        return None

    def create_venv_with_manager(
        self, workspace_dir: str, venv_path: str | None = None
    ):
        """Create venv using the detected environment manager."""
        try:
            manager = self._detect_environment_manager(workspace_dir)

            if not venv_path:
                venv_path = os.path.join(workspace_dir, ".venv")

            self._safe_log(f"🔨 Création du venv avec {manager}...")

            # Check if manager is available
            if not self._is_tool_available(manager):
                self._safe_log(
                    f"⚠️ {manager} n'est pas disponible, utilisation de pip..."
                )
                self.create_venv_if_needed(workspace_dir, prefer_manager=False)
                return

            # Get the appropriate command
            cmd = self._get_manager_command(manager, "create_venv")
            if not cmd:
                self._safe_log(f"⚠️ Commande de création non disponible pour {manager}")
                self.create_venv_if_needed(workspace_dir, prefer_manager=False)
                return

            # Build full command
            if manager == "poetry":
                full_cmd = cmd + [sys.executable]
            elif manager == "conda":
                _, env_name = self._parse_conda_env_spec(workspace_dir)
                env_name = env_name or os.path.basename(venv_path) or "env"
                full_cmd = cmd + [env_name]
            elif manager == "pipenv":
                full_cmd = cmd + [sys.executable]
            elif manager == "pdm":
                full_cmd = cmd + [sys.executable]
            elif manager == "uv":
                full_cmd = cmd + [venv_path]
            else:
                full_cmd = cmd + [venv_path]

            self._safe_log(f"📋 Commande: {' '.join(full_cmd)}")

            # Execute command
            self.venv_progress_dialog = ProgressDialog(
                f"Création du venv avec {manager}", self.parent
            )
            self.venv_progress_dialog.set_message(f"Création du venv avec {manager}...")

            process = QProcess(self.parent)
            self._venv_create_process = process
            process.setProgram(full_cmd[0])
            process.setArguments(full_cmd[1:])
            process.setWorkingDirectory(workspace_dir)
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
            self.venv_progress_dialog.show()
            process.start()
            # Safety timeout (15 min for manager-based creation)
            self._arm_process_timeout(process, 900_000, f"{manager} venv creation")
        except Exception as e:
            self._safe_log(f"❌ Erreur création venv avec manager: {e}")
            self.create_venv_if_needed(workspace_dir, prefer_manager=False)

    def install_dependencies_with_manager(
        self, workspace_dir: str, venv_path: str | None = None
    ):
        """Install dependencies using the detected environment manager."""
        try:
            manager = self._detect_environment_manager(workspace_dir)

            if not venv_path:
                venv_path = os.path.join(workspace_dir, ".venv")

            self._safe_log(f"📦 Installation des dépendances avec {manager}...")

            # Check if manager is available
            if not self._is_tool_available(manager):
                self._safe_log(
                    f"⚠️ {manager} n'est pas disponible, utilisation de pip..."
                )
                self.install_requirements_if_needed(workspace_dir, force_pip=True)
                return

            # Get the appropriate command
            cmd = self._get_manager_command(manager, "install")
            if not cmd:
                self._safe_log(
                    f"⚠️ Commande d'installation non disponible pour {manager}"
                )
                self.install_requirements_if_needed(workspace_dir, force_pip=True)
                return

            # Build full command
            if manager == "poetry":
                full_cmd = cmd  # poetry install
            elif manager == "conda":
                # conda install -y -r <env_file>
                env_file = None
                for fname in ("environment.yml", "conda.yml", "environment.yaml"):
                    p = os.path.join(workspace_dir, fname)
                    if os.path.isfile(p):
                        env_file = p
                        break
                if env_file:
                    full_cmd = cmd + ["-r", env_file]
                else:
                    full_cmd = cmd
            elif manager == "pipenv":
                full_cmd = cmd  # pipenv install
            elif manager == "pdm":
                full_cmd = cmd  # pdm install
            elif manager == "uv":
                req_file = os.path.join(workspace_dir, "requirements.txt")
                full_cmd = cmd + [req_file]
            else:
                req_file = os.path.join(workspace_dir, "requirements.txt")
                full_cmd = cmd + [req_file]

            self._safe_log(f"📋 Commande: {' '.join(full_cmd)}")

            # Execute command
            self.progress_dialog = ProgressDialog(
                f"Installation avec {manager}", self.parent
            )
            self.progress_dialog.set_message(
                f"Installation des dépendances avec {manager}..."
            )

            process = QProcess(self.parent)
            self._req_install_process = process
            process.setProgram(full_cmd[0])
            process.setArguments(full_cmd[1:])
            process.setWorkingDirectory(workspace_dir)
            process.readyReadStandardOutput.connect(
                lambda: self._on_pip_output(process)
            )
            process.readyReadStandardError.connect(
                lambda: self._on_pip_output(process, error=True)
            )
            process.finished.connect(
                lambda code, status: self._on_manager_install_finished(
                    process, code, status, manager
                )
            )
            self._pip_progress_lines = 0
            self.progress_dialog.show()
            process.start()
            # Safety timeout (20 min for dependency installation)
            self._arm_process_timeout(process, 1200_000, f"{manager} install")
        except Exception as e:
            self._safe_log(f"❌ Erreur installation avec manager: {e}")
            self.install_requirements_if_needed(workspace_dir, force_pip=True)

    def _on_manager_install_finished(self, process, code, status, manager):
        """Callback after manager-based installation."""
        if getattr(self.parent, "_closing", False):
            return

        if code == 0:
            self._safe_log(f"✅ Installation avec {manager} réussie.")
        else:
            self._safe_log(f"❌ Erreur installation avec {manager} (code {code})")

        try:
            if self.progress_dialog:
                self.progress_dialog.set_message("Installation terminée.")
                self.progress_dialog.close()
        except Exception:
            pass

        QApplication.processEvents()

    def setup_workspace(self, workspace_dir: str, check_tools: bool = True) -> bool:
        """Setup a workspace with venv and dependencies.

        This centralizes the workspace setup logic that was previously
        scattered in PyCompilerArkGui.apply_workspace_selection().

        Args:
            workspace_dir: Path to the workspace directory
            check_tools: Whether to check and install tools (pyinstaller, nuitka, cx_freeze)
                        after venv creation. Defaults to True.

        Returns:
            bool: True if setup successful, False otherwise
        """
        try:
            workspace_dir = os.path.abspath(workspace_dir)

            # Resolve an existing environment first (local or manager-provided)
            existing_env = self.resolve_existing_venv(workspace_dir)

            # Create venv if needed
            if not existing_env:
                self.create_venv_if_needed(workspace_dir)
            else:
                self._safe_log(f"✅ Venv existant détecté: {existing_env}")

            # Check and install tools if requested
            if check_tools:
                # Verify venv exists and is valid before checking tools
                existing_check, _ = self._detect_venv_in(workspace_dir)
                if existing_check:
                    ok, reason = self.validate_venv_strict(existing_check)
                    if ok:
                        # Verify binding and then check tools
                        def _after_binding(ok_bind: bool):
                            if ok_bind:
                                self._safe_log(
                                    "🔍 Vérification des outils de compilation..."
                                )
                                self.check_tools_in_venv(existing_check)
                            else:
                                self._safe_log(
                                    "⚠️ Liaison venv invalide, vérification des outils ignorée."
                                )

                        self._verify_venv_binding_async(existing_check, _after_binding)
                    else:
                        self._safe_log(
                            f"⚠️ Venv invalide, vérification des outils ignorée: {reason}"
                        )

            # Create ARK config if it doesn't exist
            try:
                from Core.ArkConfigManager import create_default_ark_config

                if create_default_ark_config(workspace_dir):
                    self._safe_log(
                        "📋 Fichier ARK_Main_Config.yml créé dans le workspace.",
                        "📋 ARK_Main_Config.yml file created in workspace.",
                    )
            except Exception as e:
                self._safe_log(
                    f"⚠️ Impossible de créer ARK_Main_Config.yml: {e}",
                    f"⚠️ Failed to create ARK_Main_Config.yml: {e}",
                )

            return True
        except Exception as e:
            self._safe_log(f"❌ Erreur lors de la configuration du workspace: {e}")
            return False

    def get_manager_info(self, workspace_dir: str) -> dict:
        """Get detailed information about the detected environment manager."""
        try:
            manager = self._detect_environment_manager(workspace_dir)

            info = {
                "manager": manager,
                "available": self._is_tool_available(manager),
                "commands": self._manager_commands.get(manager, {}),
            }

            # Add manager-specific info
            if manager == "poetry":
                info["config_file"] = "pyproject.toml"
                info["lock_file"] = "poetry.lock"
            elif manager == "conda":
                info["config_file"] = "environment.yml"
                info["lock_file"] = "conda.lock"
            elif manager == "pipenv":
                info["config_file"] = "Pipfile"
                info["lock_file"] = "Pipfile.lock"
            elif manager == "pdm":
                info["config_file"] = "pyproject.toml"
                info["lock_file"] = "pdm.lock"
            elif manager == "uv":
                info["config_file"] = "pyproject.toml"
                info["lock_file"] = "uv.lock"
            else:
                info["config_file"] = "requirements.txt"
                info["lock_file"] = None

            return info
        except Exception as e:
            self._safe_log(f"⚠️ Erreur récupération info manager: {e}")
            return {"manager": "pip", "available": True, "commands": {}}
