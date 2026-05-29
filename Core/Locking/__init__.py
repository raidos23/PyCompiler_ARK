# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import fnmatch
import json
import platform
import sys
from datetime import datetime
from hashlib import sha256
from importlib.metadata import distributions
from pathlib import Path
from typing import Any

import yaml

from Core.Configs import normalize_ark_config
from Core.engine.build_context import BuildContext


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
    return workspace / ".ark" / engine_id / "config.json"


def read_engine_config(workspace: Path, engine_id: str) -> dict[str, Any]:
    path = engine_config_path(workspace, engine_id)
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and "options" in data and "meta" in data:
            # Format saved by Core.engine.ConfigManager
            opts = data.get("options")
            return opts if isinstance(opts, dict) else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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


def included_workspace_files(
    workspace: Path, exclude_patterns: list[str]
) -> list[Path]:
    """
    Return a list of files to be included in the workspace snapshot.
    Optimized to skip excluded directories early.
    """
    included: list[Path] = []
    ws_str = str(workspace.resolve())
    
    # Prune list for os.walk
    prune_dirs = {".git", ".ark", "__pycache__", "venv", ".venv", "build", "dist"}
    
    import os
    for root, dirs, files in os.walk(ws_str):
        # 1. Early pruning of common heavy/system directories
        dirs[:] = [d for d in dirs if d not in prune_dirs]
        
        # 2. Apply custom exclude patterns to directories
        rel_root = os.path.relpath(root, ws_str)
        if rel_root == ".":
            rel_root = ""
            
        if rel_root:
            if any(_matches_exclude_pattern(rel_root + "/", p) for p in exclude_patterns):
                dirs[:] = [] # Stop recursion here
                continue

        # 3. Process files
        for f in files:
            rel_path = os.path.join(rel_root, f) if rel_root else f
            if any(_matches_exclude_pattern(rel_path, p) for p in exclude_patterns):
                continue
            included.append(Path(root) / f)
            
    return sorted(included)


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


def get_git_commit_hash(workspace: Path) -> str | None:
    """Return the current Git commit hash of the workspace if available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return None


def get_git_branch(workspace: Path) -> str | None:
    """Return the current Git branch of the workspace if available."""
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=5,
            check=True
        )
        return result.stdout.strip()
    except Exception:
        return None


def next_build_id(lock_dir: Path) -> str:
    from datetime import UTC
    today = datetime.now(UTC).strftime("%Y_%m_%d")
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
    python_version: str | None = None,
) -> dict[str, Any]:
    config = normalize_ark_config(config)
    build = config.get("build") or {}
    exclude_patterns = list(build.get("exclude") or [])
    project = config.get("project") or {}
    ensure_workspace_layout(workspace)
    lock_dir = workspace / ".ark" / "lock"
    build_id = next_build_id(lock_dir)
    git_commit = get_git_commit_hash(workspace)
    git_branch = get_git_branch(workspace)
    
    return {
        "build_id": build_id,
        "project": {
            "name": project.get("name"),
            "version": project.get("version"),
            "entry": project.get("entry"),
            "git_commit": git_commit,
            "git_branch": git_branch,
        },
        "workspace": {"exclude_patterns": exclude_patterns},
        "build": {
            "output": build.get("output"),
            "data": list(build.get("data") or []),
            "exclude": exclude_patterns,
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
            "python_version": python_version or platform.python_version(),
        },
        "dependencies": dependencies or installed_distributions_snapshot(),
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
    return BuildContext(
        project_name=str(project.get("name") or ""),
        entry_point=str(project.get("entry") or ""),
        output_dir=str(build.get("output") or ""),
        exclude_patterns=list(build.get("exclude") or []),
        data_mappings=list(build.get("data") or []),
        icon=str(build.get("icon")) if build.get("icon") else None,
    )


def build_context_from_lock(lock_payload: dict[str, Any]) -> BuildContext:
    project = lock_payload.get("project") or {}
    build = lock_payload.get("build") or {}
    workspace_cfg = lock_payload.get("workspace") or {}
    
    # Check build.exclude (new) then workspace.exclude_patterns (legacy)
    exclude_patterns = list(build.get("exclude") or [])
    if not exclude_patterns:
        exclude_patterns = list(workspace_cfg.get("exclude_patterns") or [])

    return BuildContext(
        project_name=str(project.get("name") or ""),
        entry_point=str(project.get("entry") or ""),
        output_dir=str(build.get("output") or ""),
        exclude_patterns=exclude_patterns,
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
    "default_lock_path",
    "engine_config_path",
    "ensure_workspace_layout",
    "get_git_branch",
    "get_git_commit_hash",
    "included_workspace_files",
    "installed_distributions_snapshot",
    "load_yaml_file",
    "next_build_id",
    "read_engine_config",
    "write_lock_files",
]
