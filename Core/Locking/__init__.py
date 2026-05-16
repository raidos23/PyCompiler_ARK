# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import json
import platform
import sys
import fnmatch
from datetime import datetime
from hashlib import sha256
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

import yaml
from Core.Configs import normalize_ark_config
from engine_sdk.build_context import BuildContext


class LockingError(RuntimeError):
    """Raised when a lock file operation cannot satisfy the expected contract."""


def ensure_workspace_layout(workspace: Path) -> None:
    for path in (
        workspace / ".ark" / "lock",
        workspace / ".ark" / "cache",
        workspace / ".ark" / "build",
        workspace / ".ark" / "logs",
    ):
        path.mkdir(parents=True, exist_ok=True)


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LockingError(f"File not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise LockingError(f"Invalid YAML object in {path}")
    return data


def engine_config_path(workspace: Path, engine_id: str) -> Path:
    return workspace / ".ark" / "config" / engine_id / "config.json"


def read_engine_config(workspace: Path, engine_id: str) -> dict[str, Any]:
    path = engine_config_path(workspace, engine_id)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def installed_distributions_snapshot() -> dict[str, str]:
    items: dict[str, str] = {}
    for dist in distributions():
        try:
            name = str(dist.metadata["Name"] or "").strip()
        except Exception:
            name = ""
        if not name:
            continue
        items[name] = str(dist.version)
    return dict(sorted(items.items()))


def included_workspace_files(workspace: Path, exclude_patterns: list[str]) -> list[Path]:
    included: list[Path] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace).as_posix()
        if rel.startswith(".ark/"):
            continue
        if any(_matches_exclude_pattern(rel, pattern) for pattern in exclude_patterns):
            continue
        included.append(path)
    return included


def _matches_exclude_pattern(relative_path: str, pattern: str) -> bool:
    pat = str(pattern or "").strip().replace("\\", "/")
    if not pat:
        return False
    rel = relative_path.replace("\\", "/")
    if pat.startswith("./"):
        pat = pat[2:]
    if pat.endswith("/"):
        pat = pat.rstrip("/") + "/**"
    if pat.endswith("/**"):
        prefix = pat[:-3].rstrip("/")
        return rel == prefix or rel.startswith(prefix + "/")
    return fnmatch.fnmatch(rel, pat) or Path(rel).match(pat)


def compute_workspace_hash(workspace: Path, exclude_patterns: list[str]) -> str:
    digest = sha256()
    for path in included_workspace_files(workspace, exclude_patterns):
        rel = path.relative_to(workspace).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def next_build_id(lock_dir: Path) -> str:
    today = datetime.utcnow().strftime("%Y_%m_%d")
    prefix = f"ARK_{today}_"
    seq = 1
    if lock_dir.exists():
        for path in lock_dir.glob(f"{prefix}*.lock.yml"):
            suffix = path.stem.replace(prefix, "").replace(".lock", "")
            if suffix.isdigit():
                seq = max(seq, int(suffix) + 1)
    return f"{prefix}{seq:03d}"


def build_lock_payload(
    workspace: Path,
    config: dict[str, Any],
    *,
    engine_id: str,
    engine_version: str = "unknown",
    dependencies: dict[str, str] | None = None,
) -> dict[str, Any]:
    config = normalize_ark_config(config)
    exclude_patterns = list(((config.get("workspace") or {}).get("exclude")) or [])
    build = config.get("build") or {}
    project = config.get("project") or {}
    ensure_workspace_layout(workspace)
    lock_dir = workspace / ".ark" / "lock"
    build_id = next_build_id(lock_dir)
    return {
        "build_id": build_id,
        "project": {
            "name": project.get("name"),
            "version": project.get("version"),
            "entry": project.get("entry"),
        },
        "workspace": {"exclude_patterns": exclude_patterns},
        "build": {
            "output": build.get("output"),
            "data": list(build.get("data") or []),
            **({"icon": build.get("icon")} if build.get("icon") else {}),
        },
        "engine": {
            "name": engine_id,
            "version": engine_version,
            "config": read_engine_config(workspace, engine_id),
        },
        "platform": {
            "os": sys.platform,
            "arch": platform.machine(),
            "python_version": platform.python_version(),
        },
        "dependencies": dependencies or installed_distributions_snapshot(),
        "workspace_hash": compute_workspace_hash(workspace, exclude_patterns),
    }


def write_lock_files(workspace: Path, payload: dict[str, Any]) -> dict[str, str]:
    lock_dir = workspace / ".ark" / "lock"
    ensure_workspace_layout(workspace)
    build_id = str(payload.get("build_id") or "ARK_UNKNOWN")
    target = lock_dir / f"{build_id}.lock.yml"
    latest = lock_dir / "latest.lock.yml"
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    target.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return {"lock": str(target), "latest": str(latest)}


def cache_rebuild_lock(workspace: Path, payload: dict[str, Any]) -> str:
    cache_dir = workspace / ".ark" / "cache" / "rebuild.lock"
    cache_dir.mkdir(parents=True, exist_ok=True)
    build_id = str(payload.get("build_id") or "ARK_UNKNOWN")
    target = cache_dir / f"{build_id}.lock.yml"
    target.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )
    return str(target)


def compare_lock_payloads(left: dict[str, Any], right: dict[str, Any]) -> bool:
    def comparable(payload: dict[str, Any]) -> dict[str, Any]:
        data = dict(payload)
        data.pop("build_id", None)
        return data

    return comparable(left) == comparable(right)


def default_lock_path(workspace: Path) -> Path:
    return workspace / ".ark" / "lock" / "latest.lock.yml"


def build_context_from_ark_config(config: dict[str, Any]) -> BuildContext:
    config = normalize_ark_config(config)
    project = config.get("project") or {}
    build = config.get("build") or {}
    workspace_cfg = config.get("workspace") or {}
    return BuildContext(
        project_name=str(project.get("name") or ""),
        entry_point=str(project.get("entry") or ""),
        output_dir=str(build.get("output") or ""),
        exclude_patterns=list(workspace_cfg.get("exclude") or []),
        data_mappings=list(build.get("data") or []),
        icon=str(build.get("icon")) if build.get("icon") else None,
    )


def build_context_from_lock(lock_payload: dict[str, Any]) -> BuildContext:
    project = lock_payload.get("project") or {}
    build = lock_payload.get("build") or {}
    workspace_cfg = lock_payload.get("workspace") or {}
    return BuildContext(
        project_name=str(project.get("name") or ""),
        entry_point=str(project.get("entry") or ""),
        output_dir=str(build.get("output") or ""),
        exclude_patterns=list(workspace_cfg.get("exclude_patterns") or []),
        data_mappings=list(build.get("data") or []),
        icon=str(build.get("icon")) if build.get("icon") else None,
    )


__all__ = [
    "BuildContext",
    "LockingError",
    "build_context_from_ark_config",
    "build_context_from_lock",
    "build_lock_payload",
    "cache_rebuild_lock",
    "compare_lock_payloads",
    "compute_workspace_hash",
    "default_lock_path",
    "engine_config_path",
    "ensure_workspace_layout",
    "included_workspace_files",
    "installed_distributions_snapshot",
    "load_yaml_file",
    "next_build_id",
    "read_engine_config",
    "write_lock_files",
]
