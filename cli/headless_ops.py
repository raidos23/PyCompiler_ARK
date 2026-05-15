# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""Expose headless payload builders used by CLI commands and CI workflows."""

from __future__ import annotations

import json
import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any
import yaml


def emit_json(payload: Any) -> str:
    """Serialize a payload as stable pretty JSON."""
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def _project_root() -> Path:
    """Return repository root path."""
    return Path(__file__).resolve().parents[1]


def _plugins_root() -> Path:
    """Return plugins directory path."""
    return _project_root() / "Plugins"


def _new_engines_app(workspace_dir: str | None = None):
    """Instantiate the headless engines standalone app."""
    from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp

    return EnginesStandaloneApp(
        workspace_dir=workspace_dir,
        language="en",
        theme="dark",
        headless=True,
    )


class _HeadlessLog:
    """Minimal log collector for headless compatibility calls."""

    def __init__(self) -> None:
        """Initialize in-memory message buffer."""
        self.messages: list[str] = []

    def append(self, message: str) -> None:
        """Append a message to the headless log buffer."""
        self.messages.append(str(message))


class _HeadlessGui:
    """Minimal GUI-like adapter used by Core and engines in headless mode."""

    def __init__(self, workspace_dir: str | None = None):
        """Create a headless GUI context for a workspace."""
        self.workspace_dir = workspace_dir
        self.log = _HeadlessLog()
        self._tr: dict[str, Any] = {}
        self.language_pref = "en"
        self.current_language = "en"
        self.venv_manager = None
        self.venv_path_manuel = None
        self.venv_path = None
        self.use_system_python = False
        self._init_venv_context()

    def tr(self, fr_text: str, en_text: str) -> str:
        """Return the English message for deterministic CLI output."""
        return en_text

    def _init_venv_context(self) -> None:
        """Best-effort initialization of venv manager context."""
        try:
            from Core.Venv_Manager.Manager import VenvManager

            self.venv_manager = VenvManager(self)
            if self.workspace_dir:
                try:
                    self.venv_manager.apply_workspace_pref(self.workspace_dir)
                except Exception:
                    pass
                try:
                    detected = self.venv_manager.resolve_existing_venv(
                        self.workspace_dir
                    )
                    if detected:
                        self.venv_path = detected
                except Exception:
                    pass
        except Exception:
            self.venv_manager = None


def _read_version_from_init(rel_path: str) -> str:
    """Read __version__ from a module __init__.py file."""
    try:
        root = Path(__file__).resolve().parents[1]
        init_file = root / rel_path
        for line in init_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("__version__"):
                _, value = stripped.split("=", 1)
                return value.strip().strip("\"'")
    except Exception:
        pass
    return "unknown"


def _load_workspace_config(workspace_dir: str) -> dict[str, Any]:
    """Load workspace ARK config file with tolerant candidate fallback."""
    config_files = [
        Path(workspace_dir) / "ark.yaml",
        Path(workspace_dir) / "ark.yml",
        Path(workspace_dir) / ".ark.yaml",
        Path(workspace_dir) / ".ark.yml",
    ]
    for candidate in config_files:
        try:
            if candidate.exists():
                with open(candidate, encoding="utf-8") as handle:
                    data = yaml.safe_load(handle) or {}
                return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def _get_entrypoint(cfg: dict[str, Any]) -> str | None:
    """Extract build.entrypoint from a parsed ARK config payload."""
    try:
        build = cfg.get("build", {})
        if isinstance(build, dict):
            entry = build.get("entrypoint")
            if isinstance(entry, str) and entry.strip():
                return entry.strip()
    except Exception:
        pass
    return None


def _should_exclude(rel_path: str, patterns: list[str]) -> bool:
    """Check exclusion patterns against a relative file path."""
    import fnmatch

    rel_posix = rel_path.replace(os.sep, "/")
    for pattern in patterns:
        pat = str(pattern or "").replace("\\", "/").strip()
        if not pat:
            continue
        if fnmatch.fnmatch(rel_posix, pat):
            return True
        if "**" in pat and fnmatch.fnmatch(rel_posix, pat):
            return True
        if "/" not in pat and fnmatch.fnmatch(Path(rel_posix).name, pat):
            return True
    return False


def _normalize_workspace(workspace: str | None) -> str | None:
    """Normalize an optional workspace path to an absolute string."""
    if not workspace:
        return None
    try:
        return str(Path(workspace).expanduser().resolve())
    except Exception:
        return str(workspace)


def _scan_workspace_python_files(
    ws_path: Path,
    exclusion_patterns: list[str],
    should_exclude_file_fn=None,
) -> list[str]:
    """Scan workspace and return sorted relative Python files with exclusion logic."""
    python_files: list[str] = []
    for path in ws_path.rglob("*.py"):
        try:
            rel = str(path.relative_to(ws_path)).replace(os.sep, "/")
            if callable(should_exclude_file_fn):
                if should_exclude_file_fn(str(path), str(ws_path), exclusion_patterns):
                    continue
            elif _should_exclude(rel, exclusion_patterns):
                continue
            python_files.append(rel)
        except Exception:
            continue
    python_files.sort()
    return python_files


def _resolve_entrypoint_for_workspace(
    ws_path: Path,
    python_files: list[str],
    entrypoint: str | None = None,
) -> tuple[str | None, str | None]:
    """
    Resolve and validate entrypoint for a workspace.

    Returns:
        (resolved_entrypoint, error_message)
    """
    resolved_entrypoint = None
    if entrypoint:
        raw = str(entrypoint).strip()
        try:
            ep_path = Path(raw)
            if ep_path.is_absolute():
                ep_path = ep_path.resolve()
                try:
                    rel = ep_path.relative_to(ws_path.resolve())
                except Exception:
                    return None, "entrypoint must be inside workspace"
                resolved_entrypoint = str(rel).replace(os.sep, "/")
            else:
                resolved_entrypoint = raw.replace("\\", "/")
        except Exception:
            resolved_entrypoint = raw.replace("\\", "/")
    else:
        resolved_entrypoint = _detect_entrypoint(str(ws_path), python_files)

    if resolved_entrypoint and resolved_entrypoint not in python_files:
        return resolved_entrypoint, "entrypoint is not a Python file in workspace"
    return resolved_entrypoint, None


def _workspace_config_candidates(workspace_dir: str) -> list[Path]:
    """Return candidate ARK config file paths for a workspace."""
    ws = Path(workspace_dir)
    return [
        ws / "ark.yaml",
        ws / "ark.yml",
        ws / ".ark.yaml",
        ws / ".ark.yml",
    ]


def _is_probable_entrypoint(py_file: Path) -> bool:
    """Heuristically detect whether a Python file looks like an entrypoint."""
    name = py_file.name.lower()
    if name in {"main.py", "app.py", "__main__.py", "run.py"}:
        return True
    try:
        text = py_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return "__name__" in text and "__main__" in text


def _detect_entrypoint(workspace_dir: str, candidates: list[str]) -> str | None:
    """Auto-detect an entrypoint from discovered Python files."""
    ws = Path(workspace_dir)
    if not candidates:
        return None

    preferred = [
        "main.py",
        "app.py",
        "__main__.py",
        "run.py",
        "src/main.py",
        "src/app.py",
    ]
    candidate_set = set(candidates)
    for rel in preferred:
        if rel in candidate_set:
            return rel

    probable = []
    for rel in candidates:
        path = ws / rel
        if _is_probable_entrypoint(path):
            probable.append(rel)
    if probable:
        probable.sort()
        return probable[0]

    return candidates[0]


def _notify_progress(
    callback,
    step: str,
    status: str,
    message: str,
    steps: list[dict[str, str]],
) -> None:
    """Append and forward a normalized progress event."""
    entry = {"step": step, "status": status, "message": message}
    steps.append(entry)
    if callable(callback):
        try:
            callback(step, status, message)
        except Exception:
            pass


def _ensure_workspace_pref(workspace_dir: Path) -> tuple[bool, str]:
    """Ensure .ark/pref.json exists and return creation state with path."""
    pref_path = workspace_dir / ".ark" / "pref.json"
    if pref_path.exists():
        return False, str(pref_path)
    pref_path.parent.mkdir(parents=True, exist_ok=True)
    pref_payload = {"venv_mode": "system", "venv_path": None}
    pref_path.write_text(
        json.dumps(pref_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True, str(pref_path)


def _set_workspace_pref(
    workspace_dir: Path, venv_mode: str, venv_path: str | None
) -> bool:
    """Persist workspace Python mode preference in .ark/pref.json."""
    pref_path = workspace_dir / ".ark" / "pref.json"
    pref_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"venv_mode": str(venv_mode), "venv_path": venv_path}
    pref_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def _ensure_bcasl_config(workspace_dir: Path) -> tuple[bool, str | None]:
    """Ensure bcasl.yml exists and return creation state with path."""
    target = workspace_dir / "bcasl.yml"
    if target.exists():
        return False, str(target)
    try:
        from bcasl.Loader import _load_workspace_config  # type: ignore

        _load_workspace_config(workspace_dir)
    except Exception:
        return False, None
    return bool(target.exists()), str(target) if target.exists() else None


def _venv_python_path(venv_dir: Path) -> Path:
    """Return python executable path for a venv root."""
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _detect_existing_workspace_venv(workspace_dir: Path) -> Path | None:
    """Detect an existing local workspace venv."""
    for name in (".venv", "venv"):
        candidate = workspace_dir / name
        if candidate.is_dir() and _venv_python_path(candidate).exists():
            return candidate
    return None


def _ensure_workspace_venv(
    workspace_dir: Path,
) -> tuple[bool, bool, str | None, str | None]:
    """
    Returns (ok, created, venv_path, error_message)
    """
    existing = _detect_existing_workspace_venv(workspace_dir)
    if existing is not None:
        return True, False, str(existing), None

    target = workspace_dir / ".venv"
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "venv", str(target)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1800,
            check=False,
        )
    except Exception as exc:
        return False, False, None, str(exc)

    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "").strip()
        return (
            False,
            False,
            None,
            msg or f"venv creation failed with code {proc.returncode}",
        )

    py_path = _venv_python_path(target)
    if not py_path.exists():
        return False, False, None, "venv created but python executable not found"
    return True, True, str(target), None


def workspace_init_payload(
    workspace: str | None,
    progress_cb=None,
    *,
    with_venv: bool = False,
) -> dict[str, Any]:
    """Initialize workspace files and optionally venv, returning a structured payload."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "error": "workspace is required", "workspace": None}

    ws_path = Path(ws)
    steps: list[dict[str, str]] = []
    created_workspace = False
    created_bcasl_config = False
    created_pref = False
    created_venv = False
    venv_path: str | None = None

    _notify_progress(
        progress_cb,
        "workspace_dir",
        "running",
        f"Preparing workspace directory: {ws_path}",
        steps,
    )
    if ws_path.exists() and not ws_path.is_dir():
        _notify_progress(
            progress_cb,
            "workspace_dir",
            "failed",
            "workspace path is not a directory",
            steps,
        )
        return {
            "ok": False,
            "error": "workspace path is not a directory",
            "workspace": str(ws_path),
            "steps": steps,
        }
    if not ws_path.exists():
        try:
            ws_path.mkdir(parents=True, exist_ok=True)
            created_workspace = True
        except Exception as exc:
            return {
                "ok": False,
                "error": f"unable to create workspace directory: {exc}",
                "workspace": str(ws_path),
                "steps": steps,
            }
    _notify_progress(
        progress_cb,
        "workspace_dir",
        "done",
        "Workspace directory ready",
        steps,
    )

    _notify_progress(
        progress_cb,
        "ark_config",
        "running",
        "Ensuring ark.yml exists",
        steps,
    )
    config_candidates = _workspace_config_candidates(str(ws_path))
    existing = [p for p in config_candidates if p.exists()]
    created_config = False
    config_path = existing[0] if existing else ws_path / "ark.yml"
    if not existing:
        try:
            from Core.ArkConfigManager import create_default_ark_config

            created_config = bool(create_default_ark_config(str(ws_path)))
        except Exception as exc:
            return {
                "ok": False,
                "error": f"unable to create workspace config: {exc}",
                "workspace": str(ws_path),
                "steps": steps,
            }
    _notify_progress(
        progress_cb,
        "ark_config",
        "done",
        f"ARK config ready: {config_path}",
        steps,
    )

    _notify_progress(
        progress_cb,
        "bcasl_config",
        "running",
        "Ensuring bcasl.yml exists",
        steps,
    )
    created_bcasl_config, bcasl_path = _ensure_bcasl_config(ws_path)
    if bcasl_path:
        _notify_progress(
            progress_cb,
            "bcasl_config",
            "done",
            f"BCASL config ready: {bcasl_path}",
            steps,
        )
    else:
        _notify_progress(
            progress_cb,
            "bcasl_config",
            "warning",
            "Unable to create bcasl.yml automatically",
            steps,
        )

    _notify_progress(
        progress_cb,
        "workspace_pref",
        "running",
        "Ensuring .ark/pref.json exists",
        steps,
    )
    try:
        created_pref, pref_path = _ensure_workspace_pref(ws_path)
        _notify_progress(
            progress_cb,
            "workspace_pref",
            "done",
            f"Workspace pref ready: {pref_path}",
            steps,
        )
    except Exception as exc:
        _notify_progress(
            progress_cb,
            "workspace_pref",
            "warning",
            f"Unable to create workspace pref: {exc}",
            steps,
        )
        pref_path = str(ws_path / ".ark" / "pref.json")

    if with_venv:
        _notify_progress(
            progress_cb,
            "venv",
            "running",
            "Ensuring workspace virtual environment exists",
            steps,
        )
        ok_venv, created_venv, venv_path, venv_err = _ensure_workspace_venv(ws_path)
        if not ok_venv:
            _notify_progress(
                progress_cb,
                "venv",
                "failed",
                f"Unable to prepare venv: {venv_err}",
                steps,
            )
            return {
                "ok": False,
                "error": f"unable to prepare workspace venv: {venv_err}",
                "workspace": str(ws_path),
                "config_path": str(config_path),
                "bcasl_path": bcasl_path,
                "workspace_pref_path": pref_path,
                "steps": steps,
            }
        try:
            _set_workspace_pref(ws_path, "venv", venv_path)
            _notify_progress(
                progress_cb,
                "venv",
                "done",
                f"Workspace venv ready: {venv_path}",
                steps,
            )
        except Exception as exc:
            _notify_progress(
                progress_cb,
                "venv",
                "warning",
                f"Venv ready but pref update failed: {exc}",
                steps,
            )

    return {
        "ok": True,
        "workspace": str(ws_path),
        "created_workspace": created_workspace,
        "created_config": created_config,
        "created_bcasl_config": created_bcasl_config,
        "created_workspace_pref": created_pref,
        "with_venv": bool(with_venv),
        "created_venv": bool(created_venv),
        "venv_path": venv_path,
        "config_path": str(config_path),
        "bcasl_path": bcasl_path,
        "workspace_pref_path": pref_path,
        "steps": steps,
    }


def workspace_config_auto_payload(
    workspace: str | None,
    *,
    entrypoint: str | None = None,
) -> dict[str, Any]:
    """Auto-configure workspace entrypoint and dependency options."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "error": "workspace is required", "workspace": None}

    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "error": "workspace not found", "workspace": str(ws_path)}

    init_payload = workspace_init_payload(str(ws_path))
    if not init_payload.get("ok"):
        return init_payload

    try:
        from Core.ArkConfigManager import (
            load_ark_config,
            save_ark_config,
            set_entrypoint,
            should_exclude_file,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": f"unable to load ark config helpers: {exc}",
            "workspace": str(ws_path),
        }

    cfg = load_ark_config(str(ws_path))
    exclusion_patterns = (
        cfg.get("exclusion_patterns", []) if isinstance(cfg, dict) else []
    )

    python_files = _scan_workspace_python_files(
        ws_path,
        list(exclusion_patterns) if isinstance(exclusion_patterns, list) else [],
        should_exclude_file_fn=should_exclude_file,
    )

    deps = cfg.get("dependencies", {}) if isinstance(cfg, dict) else {}
    if not isinstance(deps, dict):
        deps = {}
    req_candidates = deps.get("requirements_files", [])
    if not isinstance(req_candidates, list):
        req_candidates = []
    req_candidates = [str(item) for item in req_candidates if str(item).strip()]
    if not req_candidates:
        req_candidates = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]

    found_req_files = []
    for rel in req_candidates:
        if (ws_path / rel).exists():
            found_req_files.append(rel)

    merged_requirements_files = found_req_files + [
        item for item in req_candidates if item not in found_req_files
    ]

    resolved_entrypoint, entrypoint_error = _resolve_entrypoint_for_workspace(
        ws_path,
        python_files,
        entrypoint=entrypoint,
    )
    if entrypoint_error:
        return {
            "ok": False,
            "error": entrypoint_error,
            "workspace": str(ws_path),
            "entrypoint": resolved_entrypoint,
        }
    if not set_entrypoint(str(ws_path), resolved_entrypoint):
        return {
            "ok": False,
            "error": "unable to persist workspace entrypoint",
            "workspace": str(ws_path),
            "entrypoint": resolved_entrypoint,
        }
    cfg = load_ark_config(str(ws_path))

    deps["requirements_files"] = merged_requirements_files
    deps["auto_generate_from_imports"] = True
    cfg["dependencies"] = deps

    if not save_ark_config(str(ws_path), cfg):
        return {
            "ok": False,
            "error": "unable to save workspace configuration",
            "workspace": str(ws_path),
        }

    return {
        "ok": True,
        "workspace": str(ws_path),
        "entrypoint": resolved_entrypoint,
        "python_file_count": len(python_files),
        "requirements_files_found": found_req_files,
        "requirements_files": merged_requirements_files,
        "config_path": str(ws_path / "ark.yml"),
        "created_workspace": bool(init_payload.get("created_workspace")),
        "created_config": bool(init_payload.get("created_config")),
    }


def _core_version() -> str:
    """Return Core package version."""
    return _read_version_from_init("Core/__init__.py")


def _engine_sdk_version() -> str:
    """Return engine SDK package version."""
    return _read_version_from_init("engine_sdk/__init__.py")


def _compatibility_result(engine_class) -> Any:
    """Compute compatibility status for an engine class."""
    from EngineLoader.validator import check_engine_compatibility

    return check_engine_compatibility(
        engine_class,
        _core_version(),
        _engine_sdk_version(),
    )


def _headless_engine_class(engine_id: str):
    """Resolve an engine class by identifier."""
    from EngineLoader import get_engine

    return get_engine(engine_id)


def _headless_engine_instance(engine_id: str):
    """Instantiate an engine from its identifier."""
    from EngineLoader import create as create_engine

    return create_engine(engine_id)


def _engine_required_tools(engine_id: str) -> dict[str, list[str]]:
    """Return normalized required tools declared by an engine."""
    try:
        engine = _headless_engine_instance(engine_id)
        required_tools = getattr(engine, "required_tools", {"python": [], "system": []})
        if not isinstance(required_tools, dict):
            return {"python": [], "system": []}
        return {
            "python": list(required_tools.get("python", []) or []),
            "system": list(required_tools.get("system", []) or []),
        }
    except Exception:
        return {"python": [], "system": []}


def _headless_engine_dry_run(
    engine_id: str,
    *,
    workspace: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Build an engine command without executing it."""
    if not file_path:
        return {"success": False, "error": "file path is required"}

    resolved_file = _normalize_workspace(file_path)
    if not resolved_file or not Path(resolved_file).is_file():
        return {"success": False, "error": "file not found"}

    try:
        engine = _headless_engine_instance(engine_id)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    gui = _HeadlessGui(workspace_dir=_normalize_workspace(workspace))
    prev_disable = os.environ.get("PYCOMPILER_DISABLE_AUTO_BUILDER")
    os.environ["PYCOMPILER_DISABLE_AUTO_BUILDER"] = "1"
    try:
        cmd = engine.build_command(gui, resolved_file)
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        if prev_disable is None:
            os.environ.pop("PYCOMPILER_DISABLE_AUTO_BUILDER", None)
        else:
            os.environ["PYCOMPILER_DISABLE_AUTO_BUILDER"] = prev_disable

    if not cmd:
        return {"success": False, "error": "empty command"}
    return {
        "success": True,
        "command": " ".join(shlex.quote(str(part)) for part in cmd),
        "argv": [str(part) for part in cmd],
        "log": list(gui.log.messages),
    }


def _plugin_candidates() -> list[dict[str, Any]]:
    """Discover plugin metadata from plugin packages."""
    plugins_root = _plugins_root()
    candidates: list[dict[str, Any]] = []
    if not plugins_root.exists():
        return candidates

    for pkg_dir in sorted(plugins_root.iterdir(), key=lambda p: p.name.lower()):
        init_file = pkg_dir / "__init__.py"
        if not pkg_dir.is_dir() or not init_file.exists():
            continue
        meta = _extract_plugin_meta(init_file, pkg_dir.name)
        candidates.append(meta)
    return candidates


def _extract_plugin_meta(init_file: Path, folder_name: str) -> dict[str, Any]:
    """Extract simple plugin metadata from source text."""
    text = ""
    try:
        text = init_file.read_text(encoding="utf-8")
    except Exception:
        pass

    def _match(field: str, default: str = "") -> str:
        """Extract a string field from plugin source text."""
        pattern = rf"{field}\s*=\s*['\"]([^'\"]+)['\"]"
        match = re.search(pattern, text)
        return match.group(1).strip() if match else default

    tags_match = re.search(r"tags\s*=\s*\[([^\]]*)\]", text, flags=re.S)
    tags: list[str] = []
    if tags_match:
        tags = [
            item.strip().strip("'\"")
            for item in tags_match.group(1).split(",")
            if item.strip().strip("'\"")
        ]

    plugin_id = _match("id", folder_name.lower())
    plugin_name = _match("name", folder_name)
    plugin_version = _match("version", "unknown")
    plugin_description = _match("description", "")
    plugin_author = _match("author", "")
    return {
        "id": plugin_id,
        "name": plugin_name,
        "version": plugin_version,
        "description": plugin_description,
        "author": plugin_author,
        "tags": tags,
        "active": True,
        "priority": 0,
        "source": str(init_file),
    }


def engine_list_payload(workspace: str | None = None) -> dict[str, Any]:
    """Return list and compatibility status for available engines."""
    from EngineLoader import available_engines

    engine_ids = list(available_engines())
    if not engine_ids:
        # In some test/automation paths, lazy discovery can be disabled globally.
        # For headless diagnostics we try one best-effort discovery pass.
        try:
            from EngineLoader.Loader.EngineLoader import _auto_discover

            _auto_discover()
            engine_ids = list(available_engines())
        except Exception:
            engine_ids = list(available_engines())

    engines = []
    for engine_id in engine_ids:
        engine_class = _headless_engine_class(engine_id)
        if engine_class is None:
            continue
        compat = _compatibility_result(engine_class)
        engines.append(
            {
                "id": getattr(engine_class, "id", engine_id),
                "name": getattr(engine_class, "name", engine_id),
                "version": getattr(engine_class, "version", "unknown"),
                "required_core": getattr(
                    engine_class, "required_core_version", "1.0.0"
                ),
                "required_sdk": getattr(engine_class, "required_sdk_version", "1.0.0"),
                "compatible": bool(getattr(compat, "is_compatible", False)),
                "message": getattr(compat, "error_message", ""),
            }
        )
    return {"engines": engines, "count": len(engines), "workspace": workspace}


def engine_info_payload(engine_id: str, workspace: str | None = None) -> dict[str, Any]:
    """Return detailed metadata for a single engine."""
    engine_class = _headless_engine_class(engine_id)
    if not engine_class:
        return {"found": False, "engine_id": engine_id}
    compat = _compatibility_result(engine_class)
    required_tools = _engine_required_tools(engine_id)
    return {
        "found": True,
        "engine": {
            "id": getattr(engine_class, "id", engine_id),
            "name": getattr(engine_class, "name", engine_id),
            "version": getattr(engine_class, "version", "unknown"),
            "required_core": getattr(engine_class, "required_core_version", "1.0.0"),
            "required_sdk": getattr(engine_class, "required_sdk_version", "1.0.0"),
            "compatible": bool(getattr(compat, "is_compatible", False)),
            "message": getattr(compat, "error_message", ""),
            "missing_requirements": list(
                getattr(compat, "missing_requirements", []) or []
            ),
            "required_tools": required_tools,
        },
    }


def engine_doctor_payload(
    engine_id: str,
    workspace: str | None = None,
    file_path: str | None = None,
) -> dict[str, Any]:
    """Return diagnostic checks for one engine."""
    payload = engine_info_payload(engine_id, workspace=workspace)
    if not payload.get("found"):
        return payload
    engine = payload["engine"]
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "compatibility",
            "ok": bool(engine.get("compatible")),
            "message": engine.get("message"),
        }
    )
    for stage in ("python", "system"):
        tools = (engine.get("required_tools") or {}).get(stage, [])
        checks.append(
            {
                "name": f"required_tools_{stage}",
                "ok": True,
                "message": ", ".join(tools) if tools else "none",
            }
        )

    if file_path:
        result = _headless_engine_dry_run(
            engine_id,
            workspace=workspace,
            file_path=file_path,
        )
        checks.append(
            {
                "name": "dry_run",
                "ok": bool(result.get("success")),
                "message": result.get("command") or result.get("error"),
            }
        )

    return {"engine_id": engine_id, "checks": checks, "engine": engine}


def engine_config_path_payload(engine_id: str, workspace: str | None) -> dict[str, Any]:
    """Return workspace engine config path details."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {
            "engine_id": engine_id,
            "workspace": None,
            "exists": False,
            "error": "workspace is required",
        }

    try:
        from Core.EngineConfigManager import _engine_config_path

        config_path = Path(_engine_config_path(ws, engine_id))
    except Exception as exc:
        return {
            "engine_id": engine_id,
            "workspace": ws,
            "exists": False,
            "error": f"unable to resolve config path: {exc}",
        }

    return {
        "engine_id": engine_id,
        "workspace": ws,
        "path": str(config_path),
        "exists": config_path.exists(),
    }


def engine_config_show_payload(engine_id: str, workspace: str | None) -> dict[str, Any]:
    """Load and return persisted workspace engine config."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {
            "engine_id": engine_id,
            "workspace": None,
            "exists": False,
            "error": "workspace is required",
        }

    info = engine_info_payload(engine_id, workspace=ws)
    if not info.get("found"):
        return {"found": False, "engine_id": engine_id, "workspace": ws}

    try:
        from Core.EngineConfigManager import load_engine_config

        config = load_engine_config(ws, engine_id)
    except Exception as exc:
        return {
            "found": True,
            "engine_id": engine_id,
            "workspace": ws,
            "exists": False,
            "error": f"unable to load engine config: {exc}",
        }

    path_payload = engine_config_path_payload(engine_id, ws)
    return {
        "found": True,
        "engine_id": engine_id,
        "workspace": ws,
        "path": path_payload.get("path"),
        "exists": bool(path_payload.get("exists")),
        "config": config,
    }


def engine_config_set_payload(
    engine_id: str,
    workspace: str | None,
    options: dict[str, Any],
    *,
    merge: bool = True,
) -> dict[str, Any]:
    """Persist workspace engine options in merge or replace mode."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {
            "saved": False,
            "engine_id": engine_id,
            "workspace": None,
            "error": "workspace is required",
        }
    if not isinstance(options, dict):
        return {
            "saved": False,
            "engine_id": engine_id,
            "workspace": ws,
            "error": "options must be an object",
        }
    info = engine_info_payload(engine_id, workspace=ws)
    if not info.get("found"):
        return {"saved": False, "found": False, "engine_id": engine_id, "workspace": ws}

    try:
        from Core.EngineConfigManager import load_engine_config, save_engine_config

        payload_options = dict(options)
        if merge:
            current = load_engine_config(ws, engine_id)
            base = current.get("options", current) if isinstance(current, dict) else {}
            if not isinstance(base, dict):
                base = {}
            merged = dict(base)
            merged.update(payload_options)
            payload_options = merged
        ok = bool(
            save_engine_config(
                ws,
                engine_id,
                payload_options,
                info.get("engine", {}).get("version"),
            )
        )
    except Exception as exc:
        return {
            "saved": False,
            "engine_id": engine_id,
            "workspace": ws,
            "error": f"unable to save engine config: {exc}",
        }

    show = engine_config_show_payload(engine_id, ws)
    return {
        "saved": ok,
        "engine_id": engine_id,
        "workspace": ws,
        "path": show.get("path"),
        "exists": bool(show.get("exists")),
        "config": show.get("config", {}),
    }


def engine_config_reset_payload(
    engine_id: str, workspace: str | None
) -> dict[str, Any]:
    """Delete persisted workspace engine configuration."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {
            "reset": False,
            "engine_id": engine_id,
            "workspace": None,
            "error": "workspace is required",
        }
    info = engine_info_payload(engine_id, workspace=ws)
    if not info.get("found"):
        return {"reset": False, "found": False, "engine_id": engine_id, "workspace": ws}
    try:
        from Core.EngineConfigManager import _engine_config_path

        path = Path(_engine_config_path(ws, engine_id))
        existed = path.exists()
        if existed:
            path.unlink()
    except Exception as exc:
        return {
            "reset": False,
            "engine_id": engine_id,
            "workspace": ws,
            "error": f"unable to reset engine config: {exc}",
        }
    return {
        "reset": True,
        "engine_id": engine_id,
        "workspace": ws,
        "path": str(path),
        "existed": bool(existed),
        "exists": bool(path.exists()),
    }


def workspace_inspect_payload(workspace: str | None) -> dict[str, Any]:
    """Inspect workspace config, entrypoint and discovered Python files."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"workspace": None, "exists": False, "error": "workspace is required"}

    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"workspace": ws, "exists": False, "error": "workspace not found"}

    should_exclude_file = None
    try:
        from Core.ArkConfigManager import (
            get_entrypoint,
            load_ark_config,
            should_exclude_file,
        )

        cfg = load_ark_config(str(ws_path))
        entrypoint = get_entrypoint(cfg)
    except Exception:
        cfg = _load_workspace_config(str(ws_path))
        entrypoint = _get_entrypoint(cfg)
        should_exclude_file = None  # type: ignore[assignment]

    dep_opts = cfg.get("dependencies", {}) if isinstance(cfg, dict) else {}
    req_candidates = (
        dep_opts.get("requirements_files", []) if isinstance(dep_opts, dict) else []
    )
    exclusion_patterns = (
        cfg.get("exclusion_patterns", []) if isinstance(cfg, dict) else []
    )

    python_files = _scan_workspace_python_files(
        ws_path,
        list(exclusion_patterns) if isinstance(exclusion_patterns, list) else [],
        should_exclude_file_fn=should_exclude_file,
    )

    detected_req_files = []
    for name in req_candidates:
        try:
            p = ws_path / str(name)
            if p.exists():
                detected_req_files.append(str(name))
        except Exception:
            continue

    return {
        "workspace": str(ws_path),
        "exists": True,
        "entrypoint": entrypoint,
        "python_file_count": len(python_files),
        "python_files_preview": python_files[:25],
        "requirements_files_found": detected_req_files,
        "config": cfg,
    }


def workspace_entrypoint_set_payload(
    workspace: str | None,
    entrypoint: str | None,
) -> dict[str, Any]:
    """Set explicit workspace entrypoint and return updated inspection."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "workspace": None, "error": "workspace is required"}
    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "workspace": ws, "error": "workspace not found"}

    raw = str(entrypoint or "").strip()
    if not raw:
        return {"ok": False, "workspace": ws, "error": "entrypoint is required"}

    should_exclude_file = None
    exclusion_patterns: list[str] = []
    try:
        from Core.ArkConfigManager import load_ark_config, should_exclude_file

        cfg = load_ark_config(str(ws_path))
        exclusion_patterns = (
            cfg.get("exclusion_patterns", []) if isinstance(cfg, dict) else []
        )
    except Exception:
        cfg = _load_workspace_config(str(ws_path))
        exclusion_patterns = (
            cfg.get("exclusion_patterns", []) if isinstance(cfg, dict) else []
        )
        should_exclude_file = None  # type: ignore[assignment]

    python_files = _scan_workspace_python_files(
        ws_path,
        list(exclusion_patterns) if isinstance(exclusion_patterns, list) else [],
        should_exclude_file_fn=should_exclude_file,
    )
    resolved, err = _resolve_entrypoint_for_workspace(ws_path, python_files, raw)
    if err:
        return {"ok": False, "workspace": ws, "entrypoint": resolved, "error": err}
    try:
        from Core.ArkConfigManager import set_entrypoint

        ok = bool(set_entrypoint(ws, resolved))
    except Exception as exc:
        return {
            "ok": False,
            "workspace": ws,
            "entrypoint": resolved,
            "error": f"unable to persist workspace entrypoint: {exc}",
        }
    inspect = workspace_inspect_payload(ws)
    return {
        "ok": ok,
        "workspace": ws,
        "entrypoint": inspect.get("entrypoint"),
        "inspect": inspect,
    }


def workspace_entrypoint_clear_payload(workspace: str | None) -> dict[str, Any]:
    """Clear explicit workspace entrypoint and return updated inspection."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "workspace": None, "error": "workspace is required"}
    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "workspace": ws, "error": "workspace not found"}
    try:
        from Core.ArkConfigManager import set_entrypoint

        ok = bool(set_entrypoint(ws, None))
    except Exception as exc:
        return {
            "ok": False,
            "workspace": ws,
            "error": f"unable to clear entrypoint: {exc}",
        }
    inspect = workspace_inspect_payload(ws)
    return {
        "ok": ok,
        "workspace": ws,
        "entrypoint": inspect.get("entrypoint"),
        "inspect": inspect,
    }


def venv_status_payload(workspace: str | None) -> dict[str, Any]:
    """Return workspace Python mode and persisted venv preference."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "workspace": None, "error": "workspace is required"}
    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "workspace": ws, "error": "workspace not found"}
    gui = _HeadlessGui(workspace_dir=ws)
    manager = getattr(gui, "venv_manager", None)
    if manager is None:
        return {"ok": False, "workspace": ws, "error": "venv manager unavailable"}

    mode = "system" if bool(getattr(gui, "use_system_python", False)) else "none"
    venv_path = None
    try:
        venv_path = manager.resolve_existing_venv(ws)
    except Exception:
        venv_path = getattr(gui, "venv_path_manuel", None)
    if mode != "system" and venv_path:
        mode = "venv"

    pref_path = Path(ws) / ".ark" / "pref.json"
    pref = None
    try:
        if pref_path.exists():
            pref = json.loads(pref_path.read_text(encoding="utf-8"))
    except Exception:
        pref = None
    return {
        "ok": True,
        "workspace": ws,
        "mode": mode,
        "venv_path": venv_path,
        "pref_path": str(pref_path),
        "pref_exists": pref_path.exists(),
        "pref": pref,
    }


def venv_use_system_payload(workspace: str | None) -> dict[str, Any]:
    """Persist system Python mode for workspace execution."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "workspace": None, "error": "workspace is required"}
    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "workspace": ws, "error": "workspace not found"}
    try:
        _set_workspace_pref(ws_path, "system", None)
    except Exception as exc:
        return {
            "ok": False,
            "workspace": ws,
            "error": f"unable to save workspace venv preference: {exc}",
        }
    return venv_status_payload(ws)


def venv_use_venv_payload(
    workspace: str | None,
    *,
    venv_path: str | None = None,
    create_if_missing: bool = False,
) -> dict[str, Any]:
    """Persist venv mode with optional local venv creation."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "workspace": None, "error": "workspace is required"}
    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "workspace": ws, "error": "workspace not found"}

    target = None
    if venv_path:
        raw = str(venv_path).strip()
        p = Path(raw)
        if not p.is_absolute():
            p = (ws_path / raw).resolve()
        target = p
    else:
        detected = _detect_existing_workspace_venv(ws_path)
        if detected is not None:
            target = detected
        elif create_if_missing:
            ok, _created, path, err = _ensure_workspace_venv(ws_path)
            if not ok or not path:
                return {
                    "ok": False,
                    "workspace": ws,
                    "error": f"unable to create workspace venv: {err}",
                }
            target = Path(path)
        else:
            return {
                "ok": False,
                "workspace": ws,
                "error": "venv path is required (or use --create)",
            }
    if not target or not target.is_dir():
        return {"ok": False, "workspace": ws, "error": "venv path not found"}
    py = _venv_python_path(target)
    if not py.exists():
        return {
            "ok": False,
            "workspace": ws,
            "error": "venv python executable not found",
        }
    try:
        _set_workspace_pref(ws_path, "venv", str(target))
    except Exception as exc:
        return {
            "ok": False,
            "workspace": ws,
            "error": f"unable to save workspace venv preference: {exc}",
        }
    return venv_status_payload(ws)


def venv_install_requirements_payload(
    workspace: str | None,
    *,
    force_pip: bool = False,
) -> dict[str, Any]:
    """Install workspace requirements in current Python mode."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "workspace": None, "error": "workspace is required"}
    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"ok": False, "workspace": ws, "error": "workspace not found"}

    gui = _HeadlessGui(workspace_dir=ws)
    manager = getattr(gui, "venv_manager", None)
    if manager is None:
        return {"ok": False, "workspace": ws, "error": "venv manager unavailable"}

    req_file = None
    try:
        req_file = manager._get_requirements_file(ws)  # noqa: SLF001
    except Exception:
        pass
    if not req_file:
        return {
            "ok": True,
            "workspace": ws,
            "installed": False,
            "reason": "no requirements file found",
        }

    use_system = bool(getattr(gui, "use_system_python", False))
    python_bin = sys.executable
    venv_path = None
    if not use_system:
        try:
            venv_path = manager.resolve_project_venv()
        except Exception:
            venv_path = None
        if not venv_path:
            return {"ok": False, "workspace": ws, "error": "no resolved project venv"}
        try:
            python_bin = manager.python_path(venv_path)
        except Exception:
            python_bin = sys.executable

    cmd = [python_bin, "-m", "pip", "install", "-r", str(req_file)]
    if use_system and platform.system() == "Linux":
        cmd = [
            python_bin,
            "-m",
            "pip",
            "install",
            "--break-system-packages",
            "-r",
            str(req_file),
        ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=ws,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=1800,
            check=False,
        )
    except Exception as exc:
        return {
            "ok": False,
            "workspace": ws,
            "error": f"requirements installation failed: {exc}",
        }

    return {
        "ok": proc.returncode == 0,
        "installed": proc.returncode == 0,
        "workspace": ws,
        "requirements_file": str(req_file),
        "mode": "system" if use_system else "venv",
        "venv_path": venv_path,
        "python": python_bin,
        "command": " ".join(shlex.quote(str(x)) for x in cmd),
        "return_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "force_pip": bool(force_pip),
    }


def workspace_apply_payload(
    workspace: str | None,
    *,
    with_venv: bool = False,
    entrypoint: str | None = None,
    auto_config: bool = True,
    inspect_files: bool = True,
    apply_venv_pref: bool = True,
    apply_engine_configs: bool = True,
    require_entrypoint: bool = False,
) -> dict[str, Any]:
    """Apply full workspace setup flow and return aggregated status payload."""
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"ok": False, "error": "workspace is required", "workspace": None}

    init_payload = workspace_init_payload(ws, with_venv=with_venv)
    if not init_payload.get("ok"):
        return {
            "ok": False,
            "workspace": ws,
            "init": init_payload,
            "error": init_payload.get("error", "workspace init failed"),
        }

    config_payload: dict[str, Any] | None = None
    if auto_config:
        config_payload = workspace_config_auto_payload(ws, entrypoint=entrypoint)
        if not config_payload.get("ok"):
            return {
                "ok": False,
                "workspace": ws,
                "init": init_payload,
                "config_auto": config_payload,
                "error": config_payload.get("error", "workspace auto-config failed"),
            }

    inspect_payload: dict[str, Any] = (
        workspace_inspect_payload(ws)
        if inspect_files
        else {"workspace": ws, "exists": True}
    )

    venv_state: dict[str, Any] = {
        "applied": False,
        "mode": "skipped",
        "venv_path": None,
    }
    if apply_venv_pref:
        try:
            gui = _HeadlessGui(workspace_dir=ws)
            manager = getattr(gui, "venv_manager", None)
            if manager is None:
                venv_state = {
                    "applied": False,
                    "mode": "unavailable",
                    "venv_path": None,
                }
            else:
                applied = bool(manager.apply_workspace_pref(ws))
                mode = (
                    "system"
                    if bool(getattr(gui, "use_system_python", False))
                    else (
                        "venv"
                        if bool(getattr(gui, "venv_path_manuel", None))
                        else "none"
                    )
                )
                try:
                    resolved = manager.resolve_existing_venv(ws)
                except Exception:
                    resolved = getattr(gui, "venv_path_manuel", None)
                venv_state = {
                    "applied": applied,
                    "mode": mode,
                    "venv_path": resolved,
                }
        except Exception as exc:
            venv_state = {
                "applied": False,
                "mode": "error",
                "venv_path": None,
                "error": str(exc),
            }

    engine_configs_state: dict[str, Any] = {
        "applied": False,
        "loaded_count": 0,
        "total_count": 0,
        "mode": "skipped",
    }
    if apply_engine_configs:
        try:
            import EngineLoader as engines_loader
            from Core.EngineConfigManager import (
                apply_engine_configs_for_workspace,
                load_engine_config,
            )

            gui = _HeadlessGui(workspace_dir=ws)
            engine_ids = list(engines_loader.available_engines())
            loaded = 0
            for eid in engine_ids:
                if load_engine_config(ws, eid):
                    loaded += 1
            apply_engine_configs_for_workspace(gui, ws)
            engine_configs_state = {
                "applied": True,
                "loaded_count": loaded,
                "total_count": len(engine_ids),
            }
        except Exception as exc:
            engine_configs_state = {
                "applied": False,
                "loaded_count": 0,
                "total_count": 0,
                "mode": "error",
                "error": str(exc),
            }

    entry = inspect_payload.get("entrypoint")
    precheck_failed = bool(require_entrypoint and not entry)
    return {
        "ok": not precheck_failed,
        "workspace": ws,
        "with_venv": bool(with_venv),
        "auto_config": bool(auto_config),
        "inspect_files": bool(inspect_files),
        "apply_venv_pref": bool(apply_venv_pref),
        "apply_engine_configs": bool(apply_engine_configs),
        "require_entrypoint": bool(require_entrypoint),
        "init": init_payload,
        "config_auto": config_payload,
        "inspect": inspect_payload,
        "venv": venv_state,
        "engine_configs": engine_configs_state,
    }


def doctor_payload(workspace: str | None = None) -> dict[str, Any]:
    """Return global environment and engine diagnostics."""
    versions = {
        "core": _read_version_from_init("Core/__init__.py"),
        "engine_sdk": _read_version_from_init("engine_sdk/__init__.py"),
        "bcasl": _read_version_from_init("bcasl/__init__.py"),
        "plugins_sdk": _read_version_from_init("Plugins_SDK/__init__.py"),
    }
    qt_available = False
    try:
        import importlib.util

        qt_available = importlib.util.find_spec("PySide6") is not None
    except Exception:
        qt_available = False

    engine_summary = engine_list_payload(workspace=workspace)
    compatible_count = sum(
        1 for item in engine_summary["engines"] if item.get("compatible")
    )
    payload = {
        "application": "PyCompiler ARK",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "versions": versions,
        "qt_available": qt_available,
        "engines": {
            "count": engine_summary["count"],
            "compatible_count": compatible_count,
            "ids": [item["id"] for item in engine_summary["engines"]],
        },
    }
    if workspace:
        payload["workspace"] = workspace_inspect_payload(workspace)
    workspace_payload = payload.get("workspace")
    has_workspace_issue = isinstance(
        workspace_payload, dict
    ) and not workspace_payload.get("exists", True)
    has_engine_issue = compatible_count != engine_summary["count"]
    has_qt_issue = not qt_available
    payload["ok"] = not (has_workspace_issue or has_engine_issue or has_qt_issue)
    return payload


def bcasl_list_payload(workspace: str | None = None) -> dict[str, Any]:
    """Return discovered BCASL plugins payload."""
    ws = _normalize_workspace(workspace) or str(Path.cwd())
    plugins_dir = _plugins_root()
    plugins = _plugin_candidates()
    return {
        "workspace": ws,
        "plugins_dir": str(plugins_dir),
        "count": len(plugins),
        "loaded_count": len(plugins),
        "plugins": plugins,
        "errors": [],
    }


def bcasl_doctor_payload(workspace: str | None = None) -> dict[str, Any]:
    """Return BCASL diagnostics checks."""
    ws = _normalize_workspace(workspace)
    plugins = bcasl_list_payload(workspace=ws)
    checks = [
        {
            "name": "plugins_dir",
            "ok": Path(plugins["plugins_dir"]).exists(),
            "message": plugins["plugins_dir"],
        },
        {
            "name": "plugin_discovery",
            "ok": not plugins.get("errors"),
            "message": (
                f"{plugins['count']} plugin(s) available"
                if not plugins.get("errors")
                else "; ".join(item["error"] for item in plugins.get("errors", []))
            ),
        },
    ]

    if ws:
        ws_path = Path(ws)
        checks.append(
            {
                "name": "workspace",
                "ok": ws_path.exists() and ws_path.is_dir(),
                "message": ws,
            }
        )

    return {
        "workspace": ws,
        "plugins": plugins,
        "checks": checks,
        "ok": all(bool(check.get("ok")) for check in checks),
    }


def ci_smoke_payload(
    workspace: str | None = None,
    *,
    require_entrypoint: bool = False,
) -> dict[str, Any]:
    """Build CI smoke checks payload with optional strict entrypoint requirement."""
    ws = _normalize_workspace(workspace)
    doctor = doctor_payload(workspace=ws if ws else None)
    bcasl = bcasl_doctor_payload(workspace=ws if ws else None)
    workspace_data = workspace_inspect_payload(ws) if ws else None

    checks: list[dict[str, Any]] = [
        {
            "name": "engine_inventory",
            "ok": doctor["engines"]["count"] > 0,
            "message": f"{doctor['engines']['count']} engine(s) detected",
        },
        {
            "name": "compatible_engines",
            "ok": doctor["engines"]["compatible_count"] > 0,
            "message": (
                f"{doctor['engines']['compatible_count']}/{doctor['engines']['count']} compatible"
            ),
        },
    ]

    for check in bcasl.get("checks", []):
        checks.append(
            {
                "name": f"bcasl_{check['name']}",
                "ok": bool(check.get("ok")),
                "message": check.get("message"),
            }
        )

    if workspace_data is not None:
        checks.append(
            {
                "name": "workspace_exists",
                "ok": bool(workspace_data.get("exists")),
                "message": workspace_data.get("workspace") or "workspace is required",
            }
        )
        entrypoint = workspace_data.get("entrypoint")
        checks.append(
            {
                "name": "workspace_entrypoint",
                "ok": bool(entrypoint) or not require_entrypoint,
                "message": entrypoint or "no entrypoint configured",
            }
        )

    failed = [check for check in checks if not check.get("ok")]
    return {
        "workspace": ws,
        "require_entrypoint": bool(require_entrypoint),
        "checks": checks,
        "failed_count": len(failed),
        "ok": not failed,
        "doctor": doctor,
        "bcasl": bcasl,
        "workspace_inspect": workspace_data,
    }


def scaffold_engine(target_name: str, root_dir: str | None = None) -> dict[str, Any]:
    """Create a starter engine package tree."""
    safe = str(target_name).strip().replace("-", "_").replace(" ", "_").lower()
    base_root = Path(root_dir or Path.cwd())
    engine_dir = base_root / "ENGINES" / safe
    lang_dir = engine_dir / "languages"
    created: list[str] = []
    if engine_dir.exists():
        return {"created": False, "path": str(engine_dir), "reason": "already exists"}

    lang_dir.mkdir(parents=True, exist_ok=True)
    created.extend([str(engine_dir), str(lang_dir)])
    (engine_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import sys",
                "from engine_sdk import CompilerEngine, engine_register",
                "",
                "",
                "@engine_register",
                f"class {safe.title().replace('_', '')}Engine(CompilerEngine):",
                f'    id = "{safe}"',
                f"    name = \"{safe.title().replace('_', ' ')}\"",
                '    version = "0.1.0"',
                '    required_core_version = "1.0.0"',
                '    required_sdk_version = "1.0.0"',
                "",
                "    def build_command(self, gui, file):",
                "        return [sys.executable, file]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (engine_dir / "languages" / "en.json").write_text(
        json.dumps({"tab_title": safe.title().replace("_", " ")}, indent=2) + "\n",
        encoding="utf-8",
    )
    (engine_dir / "mapping.json").write_text(
        '{\n  "imports": {}\n}\n', encoding="utf-8"
    )
    return {"created": True, "path": str(engine_dir)}


def scaffold_plugin(target_name: str, root_dir: str | None = None) -> dict[str, Any]:
    """Create a starter BCASL plugin package tree."""
    safe = str(target_name).strip().replace("-", "_").replace(" ", "_")
    base_root = Path(root_dir or Path.cwd())
    plugin_dir = base_root / "Plugins" / safe
    lang_dir = plugin_dir / "languages"
    if plugin_dir.exists():
        return {"created": False, "path": str(plugin_dir), "reason": "already exists"}

    lang_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from bcasl import bc_register",
                "from Plugins_SDK.BcPluginContext import BcPluginBase, PluginMeta",
                "",
                "PLUGIN_META = PluginMeta(",
                f'    id="{safe.lower()}",',
                f'    name="{safe}",',
                '    version="0.1.0",',
                '    description="BCASL plugin",',
                '    author="PyCompiler ARK",',
                '    tags=["prepare"],',
                ")",
                "",
                "",
                "@bc_register",
                f"class {safe.title().replace('_', '')}(BcPluginBase):",
                "    meta = PLUGIN_META",
                "",
                "    def __init__(self):",
                "        super().__init__(meta=PLUGIN_META)",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (plugin_dir / "languages" / "en.json").write_text(
        json.dumps({"ui_title": safe}, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"created": True, "path": str(plugin_dir)}
