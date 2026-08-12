# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

from .Configs import normalize_ark_config
from .engine.build_context import BuildContext
from .globals import WORKSPACE_CONFIG_DIRNAME

LOCK_DIRNAME = "lock"
CACHE_DIRNAME = "cache"
BUILD_DIRNAME = "build"
LOGS_DIRNAME = "logs"
LOCK_FILE_SUFFIX = ".lock"
LATEST_LOCK_FILENAME = "latest.lock"
WORKSPACE_GITIGNORE = "pref.json\ncache/\nlogs/\nbuild/\nvenv/\n.venv/\n"


class LockingError(RuntimeError):
    """Raised when a lock file operation cannot satisfy the expected contract."""


def _ark_path(workspace: Path, *parts: str) -> Path:
    return workspace / WORKSPACE_CONFIG_DIRNAME / Path(*parts)


def _lock_dir(workspace: Path) -> Path:
    return _ark_path(workspace, LOCK_DIRNAME)


def _cache_dir(workspace: Path) -> Path:
    return _ark_path(workspace, CACHE_DIRNAME)


def _workspace_subdir_paths(workspace: Path) -> tuple[Path, ...]:
    return (
        _lock_dir(workspace),
        _cache_dir(workspace),
        _ark_path(workspace, BUILD_DIRNAME),
        _ark_path(workspace, LOGS_DIRNAME),
    )


def _as_list(value: Any) -> list[Any]:
    return list(value or [])


def _write_text_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _build_section(build: dict[str, Any]) -> dict[str, Any]:
    return {
        "output": build.get("output"),
        "data": _as_list(build.get("data")),
        "exclude": _as_list(build.get("exclude")),
        "include": _as_list(build.get("include")),
        **({"icon": build.get("icon")} if build.get("icon") else {}),
    }


def _project_section(
    project: dict[str, Any], git_commit: str | None, git_branch: str | None
) -> dict[str, Any]:
    return {
        "name": project.get("name"),
        "version": project.get("version"),
        "entry": project.get("entry"),
        "git_commit": git_commit,
        "git_branch": git_branch,
    }


def _engine_section(
    engine_id: str,
    engine_version: str,
    workspace: Path,
    resolved_command: dict[str, Any] | None,
) -> dict[str, Any]:
    section = {
        "name": engine_id,
        "version": engine_version,
        "config": read_engine_config(workspace, engine_id),
    }
    if resolved_command:
        section["resolved_command"] = resolved_command
    return section


def _platform_section(python_version: str | None = None) -> dict[str, Any]:
    return {
        "os": sys.platform,
        "arch": platform.machine(),
        "python_version": python_version or platform.python_version(),
    }


def _dependencies_section(
    dependencies: dict[str, str] | None,
) -> dict[str, str]:
    return dependencies or installed_distributions_snapshot()


def _payload_text(payload: dict[str, Any]) -> str:
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)


def ensure_workspace_layout(workspace: Path) -> None:
    for path in _workspace_subdir_paths(workspace):
        path.mkdir(parents=True, exist_ok=True)
    _write_text_if_missing(
        _ark_path(workspace, ".gitignore"), WORKSPACE_GITIGNORE
    )


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise LockingError(f"File not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise LockingError(f"Invalid YAML object in {path}")
    return data


def engine_config_path(workspace: Path, engine_id: str) -> Path:
    return _ark_path(workspace, engine_id, "config.json")


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
    prune_dirs = {
        ".git",
        WORKSPACE_CONFIG_DIRNAME,
        "__pycache__",
        "venv",
        ".venv",
        "build",
        "dist",
    }

    import os

    for root, dirs, files in os.walk(ws_str):
        # 1. Early pruning of common heavy/system directories
        dirs[:] = [d for d in dirs if d not in prune_dirs]

        # 2. Apply custom exclude patterns to directories
        rel_root = os.path.relpath(root, ws_str)
        if rel_root == ".":
            rel_root = ""

        if rel_root:
            if any(
                _matches_exclude_pattern(rel_root + "/", p)
                for p in exclude_patterns
            ):
                dirs[:] = []  # Stop recursion here
                continue

        # 3. Process files
        for f in files:
            rel_path = os.path.join(rel_root, f) if rel_root else f
            if any(
                _matches_exclude_pattern(rel_path, p) for p in exclude_patterns
            ):
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
            check=True,
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
            check=True,
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
        for path in lock_dir.glob(f"{prefix}*{LOCK_FILE_SUFFIX}"):
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
    resolved_command: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = normalize_ark_config(config)
    build = config.get("build") or {}
    workspace_cfg = config.get("workspace") or {}
    project = config.get("project") or {}
    ensure_workspace_layout(workspace)
    lock_dir = _lock_dir(workspace)
    build_id = next_build_id(lock_dir)
    git_commit = get_git_commit_hash(workspace)
    git_branch = get_git_branch(workspace)
    exclude_patterns = _as_list(workspace_cfg.get("exclude"))

    return {
        "build_id": build_id,
        "project": _project_section(project, git_commit, git_branch),
        "workspace": {"exclude_patterns": exclude_patterns},
        "build": _build_section(build),
        "engine": _engine_section(
            engine_id, engine_version, workspace, resolved_command
        ),
        "platform": _platform_section(python_version),
        "dependencies": _dependencies_section(dependencies),
    }


def write_lock_files(
    workspace: Path, payload: dict[str, Any]
) -> dict[str, str]:
    ensure_workspace_layout(workspace)
    build_id = str(payload.get("build_id") or "ARK_UNKNOWN")
    lock_dir = _lock_dir(workspace)
    text = _payload_text(payload)
    target = lock_dir / f"{build_id}{LOCK_FILE_SUFFIX}"
    latest = lock_dir / LATEST_LOCK_FILENAME
    target.write_text(text, encoding="utf-8")
    latest.write_text(text, encoding="utf-8")
    return {"lock": str(target), "latest": str(latest)}


def cache_rebuild_lock(workspace: Path, payload: dict[str, Any]) -> str:
    cache_dir = _cache_dir(workspace) / "rebuild.lock"
    cache_dir.mkdir(parents=True, exist_ok=True)
    build_id = str(payload.get("build_id") or "ARK_UNKNOWN")
    target = cache_dir / f"{build_id}{LOCK_FILE_SUFFIX}"
    target.write_text(_payload_text(payload), encoding="utf-8")
    return str(target)


def get_functional_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Extract critical metadata for functional equivalence check.
    Ignores non-functional fields like build_id, git_branch, or resolved_command.
    """
    if not isinstance(payload, dict):
        return {}

    project = payload.get("project") or {}
    build = payload.get("build") or {}
    engine = payload.get("engine") or {}
    platform_info = payload.get("platform") or {}
    dependencies = payload.get("dependencies") or {}

    return {
        "project": {
            "name": str(project.get("name") or ""),
            "version": str(project.get("version") or ""),
            "entry": str(project.get("entry") or ""),
            "git_commit": project.get("git_commit"),
        },
        "build": {
            "output": str(build.get("output") or ""),
            "data": list(build.get("data") or []),
            "exclude": list(build.get("exclude") or []),
            "icon": build.get("icon"),
        },
        "engine": {
            "name": str(engine.get("name") or ""),
            "version": str(engine.get("version") or ""),
            "config": engine.get("config") or {},
        },
        "platform": {
            "os": platform_info.get("os"),
            "arch": platform_info.get("arch"),
            "python_version": platform_info.get("python_version"),
        },
        "dependencies": dependencies,
    }


def compare_lock_payloads(
    left: dict[str, Any], right: dict[str, Any], return_diff: bool = False
) -> bool | tuple[bool, list[str]]:
    """
    Compare two build lock payloads for functional equivalence.
    If return_diff is True, returns (is_equal, diff_list).
    """
    snap_left = get_functional_snapshot(left)
    snap_right = get_functional_snapshot(right)

    if not return_diff:
        return snap_left == snap_right

    diffs = []

    def _diff_dict(a: dict, b: dict, path: str):
        keys = set(a.keys()) | set(b.keys())
        for k in sorted(keys):
            val_a = a.get(k)
            val_b = b.get(k)
            cur_path = f"{path}.{k}" if path else k

            if val_a != val_b:
                if isinstance(val_a, dict) and isinstance(val_b, dict):
                    _diff_dict(val_a, val_b, cur_path)
                else:
                    diffs.append(f"{cur_path}: {val_a} -> {val_b}")

    _diff_dict(snap_left, snap_right, "")
    return (len(diffs) == 0, diffs)


def default_lock_path(workspace: Path) -> Path:
    return _lock_dir(workspace) / LATEST_LOCK_FILENAME


def build_context_from_ark_config(config: dict[str, Any]) -> BuildContext:
    config = normalize_ark_config(config)
    project = config.get("project") or {}
    build = config.get("build") or {}
    return BuildContext(
        project_name=str(project.get("name") or ""),
        entry_point=str(project.get("entry") or ""),
        output_dir=str(build.get("output") or ""),
        exclude_packages=list(build.get("exclude") or []),
        include_packages=list(build.get("include") or []),
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
        exclude_packages=list(build.get("exclude") or []),
        include_packages=list(build.get("include") or []),
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
