# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import json
import os
import platform
import fnmatch
from pathlib import Path
from typing import Any
import yaml


def emit_json(payload: Any) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)


def _new_engines_app(workspace_dir: str | None = None):
    from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp

    return EnginesStandaloneApp(
        workspace_dir=workspace_dir,
        language="en",
        theme="dark",
        headless=True,
    )


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


def engine_list_payload(workspace: str | None = None) -> dict[str, Any]:
    app = _new_engines_app(workspace_dir=_normalize_workspace(workspace))
    engines = []
    for eng in app.load_engines():
        compat = app.check_engine_compatibility(eng["id"])
        engines.append(
            {
                "id": eng["id"],
                "name": eng["name"],
                "version": eng["version"],
                "required_core": eng["required_core"],
                "required_sdk": eng["required_sdk"],
                "compatible": bool(compat.get("compatible")),
                "message": compat.get("message"),
            }
        )
    return {"engines": engines, "count": len(engines), "workspace": workspace}


def engine_info_payload(engine_id: str, workspace: str | None = None) -> dict[str, Any]:
    app = _new_engines_app(workspace_dir=_normalize_workspace(workspace))
    info = app.get_engine_info(engine_id)
    if not info:
        return {"found": False, "engine_id": engine_id}
    compat = app.check_engine_compatibility(engine_id)
    try:
        from EngineLoader import create as create_engine

        engine = create_engine(engine_id)
        required_tools = getattr(engine, "required_tools", {"python": [], "system": []})
    except Exception:
        required_tools = {"python": [], "system": []}
    return {
        "found": True,
        "engine": {
            "id": info["id"],
            "name": info["name"],
            "version": info["version"],
            "required_core": info["required_core"],
            "required_sdk": info["required_sdk"],
            "compatible": bool(compat.get("compatible")),
            "message": compat.get("message"),
            "missing_requirements": compat.get("missing_requirements", []),
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
        app = _new_engines_app(workspace_dir=_normalize_workspace(workspace))
        result = app.run_compilation(engine_id, file_path, dry_run=True)
        checks.append(
            {
                "name": "dry_run",
                "ok": bool(result.get("success")),
                "message": result.get("command") or result.get("error"),
            }
        )

    return {"engine_id": engine_id, "checks": checks, "engine": engine}


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
