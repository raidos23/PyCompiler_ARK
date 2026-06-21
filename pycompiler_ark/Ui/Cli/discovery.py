from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - la génération peut échouer proprement
    yaml = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _plugins_root() -> Path:
    path = _project_root() / "Plugins"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return path


def _read_version_from_init(rel_path: str) -> str:
    try:
        init_file = _project_root() / rel_path
        for line in init_file.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("__version__"):
                _, value = stripped.split("=", 1)
                return value.strip().strip("\"'")
    except Exception:
        pass
    return "unknown"


def _core_version() -> str:
    return _read_version_from_init("Core/__init__.py")


def _engine_sdk_version() -> str:
    return _read_version_from_init("engine_sdk/__init__.py")


def _compatibility_result(engine_class) -> Any:
    from pycompiler_ark.Core.engine.validator import check_engine_compatibility

    return check_engine_compatibility(
        engine_class,
        _core_version(),
        _engine_sdk_version(),
    )


def _headless_engine_class(engine_id: str):
    from pycompiler_ark.Core.engine import get_engine

    return get_engine(engine_id)


def _headless_engine_instance(engine_id: str):
    from pycompiler_ark.Core.engine import create as create_engine

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

    return {
        "id": _match("id", folder_name.lower()),
        "name": _match("name", folder_name),
        "version": _match("version", "unknown"),
        "description": _match("description", ""),
        "author": _match("author", ""),
        "tags": tags,
        "active": True,
        "priority": 0,
        "source": str(init_file),
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
        candidates.append(_extract_plugin_meta(init_file, pkg_dir.name))
    return candidates


def engine_list_payload(workspace: str | None = None) -> dict[str, Any]:
    from pycompiler_ark.Core.engine import available_engines

    engine_ids = list(available_engines())
    if not engine_ids:
        try:
            from pycompiler_ark.Core.engine.loader import _auto_discover

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


def bcasl_list_payload(workspace: str | None = None) -> dict[str, Any]:
    ws = str(Path(workspace).expanduser().resolve()) if workspace else str(Path.cwd())
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
    ws = str(Path(workspace).expanduser().resolve()) if workspace else None
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


def scaffold_engine(
    target_name: str, root_dir: str | None = None
) -> dict[str, Any]:
    safe = str(target_name).strip().replace("-", "_").replace(" ", "_").lower()
    base_root = Path(root_dir or Path.cwd())
    engine_dir = base_root / safe

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
                "from pycompiler_ark.engine_sdk import BuildContext, CompilerEngine, engine_register",
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
                "    def build_command(self, context: BuildContext) -> list[str]:",
                "        return [sys.executable, context.entry_point]",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if yaml is not None:
        (engine_dir / "languages" / "en.yml").write_text(
            yaml.safe_dump(
                {"tab_title": safe.title().replace("_", " ")},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    (engine_dir / "mapping.json").write_text(
        '{\n  "imports": {}\n}\n', encoding="utf-8"
    )
    return {"created": True, "path": str(engine_dir)}


def scaffold_plugin(
    target_name: str, root_dir: str | None = None
) -> dict[str, Any]:
    safe = str(target_name).strip().replace("-", "_").replace(" ", "_")
    base_root = Path(root_dir or Path.cwd())
    plugin_dir = base_root / safe

    lang_dir = plugin_dir / "languages"
    if plugin_dir.exists():
        return {"created": False, "path": str(plugin_dir), "reason": "already exists"}

    lang_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "__init__.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                'id = "' + safe.lower() + '"',
                'name = "' + safe + '"',
                'version = "0.1.0"',
                'description = ""',
                'author = ""',
                "",
                "def bc_register(registry):",
                "    return None",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    if yaml is not None:
        (plugin_dir / "languages" / "en.yml").write_text(
            yaml.safe_dump(
                {"plugin_name": safe},
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )
    return {"created": True, "path": str(plugin_dir)}
