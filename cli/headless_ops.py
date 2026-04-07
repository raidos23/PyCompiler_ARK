# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import json
import os
import platform
import fnmatch
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any
import yaml


def emit_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _plugins_root() -> Path:
    return _project_root() / "Plugins"


def _new_engines_app(workspace_dir: str | None = None):
    from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp

    return EnginesStandaloneApp(
        workspace_dir=workspace_dir,
        language="en",
        theme="dark",
        headless=True,
    )


class _HeadlessLog:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def append(self, message: str) -> None:
        self.messages.append(str(message))


class _HeadlessGui:
    def __init__(self, workspace_dir: str | None = None):
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
        return en_text

    def _init_venv_context(self) -> None:
        try:
            from Core.Venv_Manager.Manager import VenvManager

            self.venv_manager = VenvManager(self)
            if self.workspace_dir:
                try:
                    self.venv_manager.apply_workspace_pref(self.workspace_dir)
                except Exception:
                    pass
                try:
                    detected = self.venv_manager.resolve_existing_venv(self.workspace_dir)
                    if detected:
                        self.venv_path = detected
                except Exception:
                    pass
        except Exception:
            self.venv_manager = None


def _read_version_from_init(rel_path: str) -> str:
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
    config_files = [
        Path(workspace_dir) / "ARK_Main_Config.yaml",
        Path(workspace_dir) / "ARK_Main_Config.yml",
        Path(workspace_dir) / ".ARK_Main_Config.yaml",
        Path(workspace_dir) / ".ARK_Main_Config.yml",
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
    if not workspace:
        return None
    try:
        return str(Path(workspace).expanduser().resolve())
    except Exception:
        return str(workspace)


def _workspace_config_candidates(workspace_dir: str) -> list[Path]:
    ws = Path(workspace_dir)
    return [
        ws / "ARK_Main_Config.yaml",
        ws / "ARK_Main_Config.yml",
        ws / ".ARK_Main_Config.yaml",
        ws / ".ARK_Main_Config.yml",
    ]


def _is_probable_entrypoint(py_file: Path) -> bool:
    name = py_file.name.lower()
    if name in {"main.py", "app.py", "__main__.py", "run.py"}:
        return True
    try:
        text = py_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return "__name__" in text and "__main__" in text


def _detect_entrypoint(workspace_dir: str, candidates: list[str]) -> str | None:
    ws = Path(workspace_dir)
    if not candidates:
        return None

    preferred = ["main.py", "app.py", "__main__.py", "run.py", "src/main.py", "src/app.py"]
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
    entry = {"step": step, "status": status, "message": message}
    steps.append(entry)
    if callable(callback):
        try:
            callback(step, status, message)
        except Exception:
            pass


def _ensure_workspace_pref(workspace_dir: Path) -> tuple[bool, str]:
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


def _set_workspace_pref(workspace_dir: Path, venv_mode: str, venv_path: str | None) -> bool:
    pref_path = workspace_dir / ".ark" / "pref.json"
    pref_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"venv_mode": str(venv_mode), "venv_path": venv_path}
    pref_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return True


def _ensure_bcasl_config(workspace_dir: Path) -> tuple[bool, str | None]:
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
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _detect_existing_workspace_venv(workspace_dir: Path) -> Path | None:
    for name in (".venv", "venv"):
        candidate = workspace_dir / name
        if candidate.is_dir() and _venv_python_path(candidate).exists():
            return candidate
    return None


def _ensure_workspace_venv(workspace_dir: Path) -> tuple[bool, bool, str | None, str | None]:
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
        return False, False, None, msg or f"venv creation failed with code {proc.returncode}"

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
        "Ensuring ARK_Main_Config.yml exists",
        steps,
    )
    config_candidates = _workspace_config_candidates(str(ws_path))
    existing = [p for p in config_candidates if p.exists()]
    created_config = False
    config_path = existing[0] if existing else ws_path / "ARK_Main_Config.yml"
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
        from Core.ArkConfigManager import load_ark_config, save_ark_config
    except Exception as exc:
        return {
            "ok": False,
            "error": f"unable to load ark config helpers: {exc}",
            "workspace": str(ws_path),
        }

    cfg = load_ark_config(str(ws_path))
    exclusion_patterns = cfg.get("exclusion_patterns", []) if isinstance(cfg, dict) else []

    python_files: list[str] = []
    for path in ws_path.rglob("*.py"):
        try:
            rel = str(path.relative_to(ws_path)).replace(os.sep, "/")
            if _should_exclude(rel, exclusion_patterns):
                continue
            python_files.append(rel)
        except Exception:
            continue
    python_files.sort()

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
                    return {
                        "ok": False,
                        "error": "entrypoint must be inside workspace",
                        "workspace": str(ws_path),
                    }
                resolved_entrypoint = str(rel).replace(os.sep, "/")
            else:
                resolved_entrypoint = raw.replace("\\", "/")
        except Exception:
            resolved_entrypoint = raw.replace("\\", "/")
    else:
        resolved_entrypoint = _detect_entrypoint(str(ws_path), python_files)

    build = cfg.get("build", {}) if isinstance(cfg, dict) else {}
    if not isinstance(build, dict):
        build = {}
    if resolved_entrypoint and resolved_entrypoint not in python_files:
        return {
            "ok": False,
            "error": "entrypoint is not a Python file in workspace",
            "workspace": str(ws_path),
            "entrypoint": resolved_entrypoint,
        }
    build["entrypoint"] = resolved_entrypoint
    cfg["build"] = build

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
        "config_path": str(ws_path / "ARK_Main_Config.yml"),
        "created_workspace": bool(init_payload.get("created_workspace")),
        "created_config": bool(init_payload.get("created_config")),
    }


def _core_version() -> str:
    return _read_version_from_init("Core/__init__.py")


def _engine_sdk_version() -> str:
    return _read_version_from_init("engine_sdk/__init__.py")


def _compatibility_result(engine_class) -> Any:
    from EngineLoader.validator import check_engine_compatibility

    return check_engine_compatibility(
        engine_class,
        _core_version(),
        _engine_sdk_version(),
    )


def _headless_engine_class(engine_id: str):
    from EngineLoader import get_engine

    return get_engine(engine_id)


def _headless_engine_instance(engine_id: str):
    from EngineLoader import create as create_engine

    return create_engine(engine_id)


def _engine_required_tools(engine_id: str) -> dict[str, list[str]]:
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
    text = ""
    try:
        text = init_file.read_text(encoding="utf-8")
    except Exception:
        pass

    def _match(field: str, default: str = "") -> str:
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
                "required_core": getattr(engine_class, "required_core_version", "1.0.0"),
                "required_sdk": getattr(engine_class, "required_sdk_version", "1.0.0"),
                "compatible": bool(getattr(compat, "is_compatible", False)),
                "message": getattr(compat, "error_message", ""),
            }
        )
    return {"engines": engines, "count": len(engines), "workspace": workspace}


def engine_info_payload(engine_id: str, workspace: str | None = None) -> dict[str, Any]:
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


def workspace_inspect_payload(workspace: str | None) -> dict[str, Any]:
    ws = _normalize_workspace(workspace)
    if not ws:
        return {"workspace": None, "exists": False, "error": "workspace is required"}

    ws_path = Path(ws)
    if not ws_path.exists() or not ws_path.is_dir():
        return {"workspace": ws, "exists": False, "error": "workspace not found"}

    cfg = _load_workspace_config(str(ws_path))
    entrypoint = _get_entrypoint(cfg)
    dep_opts = cfg.get("dependencies", {}) if isinstance(cfg, dict) else {}
    req_candidates = (
        dep_opts.get("requirements_files", []) if isinstance(dep_opts, dict) else []
    )
    exclusion_patterns = cfg.get("exclusion_patterns", []) if isinstance(cfg, dict) else []

    python_files: list[str] = []
    for path in ws_path.rglob("*.py"):
        try:
            rel = str(path.relative_to(ws_path)).replace(os.sep, "/")
            if _should_exclude(rel, exclusion_patterns):
                continue
            python_files.append(rel)
        except Exception:
            continue
    python_files.sort()

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


def doctor_payload(workspace: str | None = None) -> dict[str, Any]:
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
    compatible_count = sum(1 for item in engine_summary["engines"] if item.get("compatible"))
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
    return payload


def bcasl_list_payload(workspace: str | None = None) -> dict[str, Any]:
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
    }


def ci_smoke_payload(
    workspace: str | None = None,
    *,
    require_entrypoint: bool = False,
) -> dict[str, Any]:
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
                f"    id = \"{safe}\"",
                f"    name = \"{safe.title().replace('_', ' ')}\"",
                "    version = \"0.1.0\"",
                "    required_core_version = \"1.0.0\"",
                "    required_sdk_version = \"1.0.0\"",
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
    (engine_dir / "mapping.json").write_text("{\n  \"imports\": {}\n}\n", encoding="utf-8")
    return {"created": True, "path": str(engine_dir)}


def scaffold_plugin(target_name: str, root_dir: str | None = None) -> dict[str, Any]:
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
                f"    id=\"{safe.lower()}\",",
                f"    name=\"{safe}\",",
                "    version=\"0.1.0\",",
                "    description=\"BCASL plugin\",",
                "    author=\"PyCompiler ARK\",",
                "    tags=[\"prepare\"],",
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
