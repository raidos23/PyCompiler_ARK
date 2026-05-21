# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
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

"""
Core.Configs — unified configuration module for PyCompiler ARK.

Merges the former ``Core.ArkConfig`` (workspace / project configuration) and
``Core.UserConfig`` (user-level persistent settings) into a single canonical
package.

Backward-compatible shims are preserved in ``Core/ArkConfig/__init__.py`` and
``Core/UserConfig/__init__.py`` so existing external code keeps working.

Workspace / project config (previously Core.ArkConfig)
-------------------------------------------------------
- ``load_ark_config``        — load ``ark.yml`` for a workspace
- ``validate_ark_config``    — validate and normalise a raw config dict
- ``write_ark_config``       — write ``ark.yml`` to disk
- ``save_ark_config``        — convenience wrapper around write_ark_config
- ``new_workspace_config``   — build a fresh config dict
- ``normalize_ark_config``   — normalise a raw config dict (no I/O)
- ``get_entrypoint``         — extract the entry-point path from config
- ``set_entrypoint``         — persist a new entry-point in ark.yml
- ``get_build_options``      — extract build section from config
- ``get_dependency_options`` — extract dependency section from config
- ``get_environment_manager_options``
- ``should_exclude_file``    — test a file path against exclusion patterns
- ``create_default_ark_config``

User-level config (previously Core.UserConfig)
----------------------------------------------
- ``config_home``            — resolve ``~/.arkconf`` (or $ARK_CONFIG_HOME)
- ``resolve_config_value``   — read a persisted user setting
- ``set_config_value``       — persist a user setting
- ``unset_config_value``     — remove a persisted user setting
- ``CONFIG_KEYS``            — mapping of public key names → file names
- ``DEFAULT_USER_DIRS``      — default directory layout
"""

from __future__ import annotations

import fnmatch
import os
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import yaml

# =============================================================================
# WORKSPACE / PROJECT CONFIGURATION  (was Core.ArkConfig)
# =============================================================================


# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    ".ark/**",
    "**/__pycache__/**",
    "**/*.pyc",
    "**/*.pyo",
    "**/*.pyd",
    ".git/**",
    ".svn/**",
    ".hg/**",
    "venv/**",
    ".venv/**",
    "env/**",
    ".env/**",
    "node_modules/**",
    "build/**",
    "dist/**",
    "*.spec",
    "*.egg-info/**",
    ".pytest_cache/**",
    ".mypy_cache/**",
    ".tox/**",
    "site-packages/**",
]

DEFAULT_ARK_CONFIG: dict[str, Any] = {
    "project": {
        "name": "",
        "version": "1.0.0",
        "entry": "",
    },
    "workspace": {
        "exclude": list(DEFAULT_EXCLUDE_PATTERNS),
    },
    "build": {
        "engine": "pyinstaller",
        "output": "dist/",
        "data": [],
    },
}

DEFAULT_DEPENDENCY_OPTIONS: dict[str, Any] = {
    "requirements_files": [
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
    "auto_generate_from_imports": True,
}

DEFAULT_ENVIRONMENT_MANAGER_OPTIONS: dict[str, Any] = {
    "priority": ["poetry", "pipenv", "conda", "pdm", "uv", "pip"],
    "auto_detect": True,
    "fallback_to_pip": True,
}

DEFAULT_CONFIG: dict[str, Any] = {
    **deepcopy(DEFAULT_ARK_CONFIG),
    "dependencies": deepcopy(DEFAULT_DEPENDENCY_OPTIONS),
    "environment_manager": deepcopy(DEFAULT_ENVIRONMENT_MANAGER_OPTIONS),
    "build": {
        **deepcopy(DEFAULT_ARK_CONFIG["build"]),
        "entrypoint": None,
    },
}


# ── Errors ────────────────────────────────────────────────────────────────────


class ArkConfigError(RuntimeError):
    """Raised when an ARK workspace config is missing or malformed."""


@dataclass(slots=True)
class ArkConfigValidationResult:
    config: dict[str, Any]
    warnings: list[str]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


# ── Internal helpers ──────────────────────────────────────────────────────────


def _deep_merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(result.get(key), dict) and isinstance(value, dict):
            result[key] = _deep_merge_dict(result[key], value)
        else:
            result[key] = value
    return result


def _normalize_list(values: Any) -> list[Any]:
    if not isinstance(values, list):
        return []
    return [item for item in values if item is not None and str(item).strip()]


def _normalize_workspace_exclude(values: Any) -> list[str]:
    merged: list[str] = []
    for item in DEFAULT_EXCLUDE_PATTERNS:
        merged.append(str(item))
    for item in _normalize_list(values):
        merged.append(str(item).strip())
    return list(dict.fromkeys(pattern for pattern in merged if pattern))


def _config_candidates(workspace: Path) -> list[Path]:
    return [
        workspace / "ark.yml",
        workspace / "ark.yaml",
        workspace / ".ark.yml",
        workspace / ".ark.yaml",
    ]


def _looks_like_semver(value: str) -> bool:
    parts = value.split(".")
    if len(parts) != 3:
        return False
    return all(part.isdigit() for part in parts)


def _compatibility_view(config: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_ark_config(config)
    view = deepcopy(normalized)
    view["dependencies"] = _deep_merge_dict(
        DEFAULT_DEPENDENCY_OPTIONS,
        (
            config.get("dependencies")
            if isinstance(config.get("dependencies"), dict)
            else {}
        ),
    )
    view["environment_manager"] = _deep_merge_dict(
        DEFAULT_ENVIRONMENT_MANAGER_OPTIONS,
        (
            config.get("environment_manager")
            if isinstance(config.get("environment_manager"), dict)
            else {}
        ),
    )
    build = view.get("build")
    if not isinstance(build, dict):
        build = {}
    entry = get_entrypoint(view)
    build["entrypoint"] = entry
    view["build"] = build
    return view


# ── Public API — workspace config ─────────────────────────────────────────────


def normalize_ark_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalise une configuration brute en un dictionnaire canonique.

    Cette version ne gère plus la rétro-compatibilité avec 'exclusion_patterns'
    et 'inclusion_patterns' au niveau racine. Ces réglages doivent désormais
    être exclusivement gérés dans 'workspace: exclude'.
    """
    if not isinstance(config, dict):
        config = {}

    # Fusion avec les valeurs par défaut
    merged = _deep_merge_dict(DEFAULT_ARK_CONFIG, config)

    # Nettoyage explicite des clés obsolètes si présentes
    merged.pop("exclusion_patterns", None)
    merged.pop("inclusion_patterns", None)

    # Normalisation de la section 'project'
    project = merged.get("project")
    if not isinstance(project, dict):
        project = {}
    project_name = str(project.get("name") or "").strip()
    project_version = str(project.get("version") or "").strip() or "1.0.0"

    # Récupération de l'entrypoint (support build.entrypoint comme legacy interne)
    build_for_entry = merged.get("build")
    if not isinstance(build_for_entry, dict):
        build_for_entry = {}
    legacy_entry = build_for_entry.get("entrypoint")
    project_entry = str(project.get("entry") or legacy_entry or "").strip()

    merged["project"] = {
        "name": project_name,
        "version": project_version,
        "entry": project_entry,
    }

    # Normalisation de la section 'workspace'
    workspace_cfg = merged.get("workspace")
    if not isinstance(workspace_cfg, dict):
        workspace_cfg = {}
    merged["workspace"] = {
        "exclude": _normalize_workspace_exclude(workspace_cfg.get("exclude")),
    }

    # Normalisation de la section 'build'
    build = merged.get("build")
    if not isinstance(build, dict):
        build = {}
    normalized_build: dict[str, Any] = {
        "engine": str(build.get("engine") or "").strip() or "pyinstaller",
        "output": str(build.get("output") or "").strip() or "dist/",
        "data": [
            item
            for item in _normalize_list(build.get("data"))
            if isinstance(item, dict)
        ],
    }
    icon_value = build.get("icon")
    if isinstance(icon_value, str) and icon_value.strip():
        normalized_build["icon"] = icon_value.strip()
    merged["build"] = normalized_build

    return merged


def load_ark_config(
    workspace: Path | str, *, require_exists: bool = False
) -> dict[str, Any]:
    workspace_path = Path(workspace)
    path = next((c for c in _config_candidates(workspace_path) if c.is_file()), None)
    if path is None:
        if require_exists:
            raise ArkConfigError("ark.yml not found in current directory.")
        return _compatibility_view({})
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise ArkConfigError(f"Unable to read ark.yml: {exc}") from exc
    if not isinstance(data, dict):
        raise ArkConfigError("ark.yml must contain a YAML mapping at the root.")
    return _compatibility_view(data)


def validate_ark_config(
    workspace: Path, config: dict[str, Any]
) -> ArkConfigValidationResult:
    normalized = normalize_ark_config(config)
    warnings: list[str] = []
    errors: list[str] = []

    project = normalized["project"]
    build = normalized["build"]
    workspace_cfg = normalized["workspace"]

    name = str(project.get("name") or "").strip()
    version = str(project.get("version") or "").strip()
    entry = str(project.get("entry") or "").strip()
    engine = str(build.get("engine") or "").strip()
    output = str(build.get("output") or "").strip()

    if not name:
        errors.append("project.name is required")
    if not version:
        errors.append("project.version is required")
    elif not _looks_like_semver(version):
        errors.append("project.version must use X.Y.Z format")

    if not entry:
        errors.append("project.entry is required")
    else:
        entry_path = workspace / Path(entry)
        if not entry_path.is_file():
            errors.append(f"project.entry: file '{entry}' not found")

    if not engine:
        errors.append("build.engine is required")

    if not output:
        errors.append("build.output is required")
    else:
        output_path = workspace / Path(output)
        if output_path.exists() and output_path.is_file():
            errors.append(f"build.output: path '{output}' is a file")

    icon = build.get("icon")
    if isinstance(icon, str) and icon.strip():
        icon_path = workspace / Path(icon)
        if not icon_path.is_file():
            warnings.append(f"build.icon: file '{icon}' not found (ignored)")

    exclude_patterns = workspace_cfg.get("exclude")
    if not isinstance(exclude_patterns, list):
        errors.append("workspace.exclude must be a list")

    return ArkConfigValidationResult(
        config=normalized, warnings=warnings, errors=errors
    )


def write_ark_config(workspace: Path | str, config: dict[str, Any]) -> Path:
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "ark.yml"
    normalized = normalize_ark_config(config)
    path.write_text(
        yaml.safe_dump(normalized, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return path


def save_ark_config(workspace_dir: str, config: dict[str, Any]) -> bool:
    if not workspace_dir or not isinstance(config, dict):
        return False
    try:
        write_ark_config(Path(workspace_dir), config)
        return True
    except Exception:
        return False


def new_workspace_config(
    *,
    workspace_name: str,
    entry: str,
    version: str = "1.0.0",
    engine: str = "pyinstaller",
    output: str = "dist/",
    icon: str | None = None,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "project": {
            "name": str(workspace_name).strip(),
            "version": str(version).strip() or "1.0.0",
            "entry": str(entry).strip(),
        },
        "workspace": {"exclude": list(DEFAULT_EXCLUDE_PATTERNS)},
        "build": {
            "engine": str(engine).strip() or "pyinstaller",
            "output": str(output).strip() or "dist/",
            "data": [],
        },
    }
    if icon:
        config["build"]["icon"] = str(icon).strip()
    return normalize_ark_config(config)


def get_entrypoint(config: dict[str, Any]) -> Optional[str]:
    project = config.get("project")
    if isinstance(project, dict):
        entry = project.get("entry")
        if isinstance(entry, str) and entry.strip():
            return entry.strip()
    build = get_build_options(config)
    entry = build.get("entrypoint")
    return entry.strip() if isinstance(entry, str) and entry.strip() else None


def set_entrypoint(workspace_dir: str, entrypoint: Optional[str]) -> bool:
    if not workspace_dir:
        return False
    try:
        config = load_ark_config(workspace_dir)
        if isinstance(entrypoint, str):
            entrypoint = entrypoint.strip() or None
        else:
            entrypoint = None
        project = config.get("project")
        if not isinstance(project, dict):
            project = {}
        project["entry"] = entrypoint or ""
        config["project"] = project
        build = config.get("build")
        if not isinstance(build, dict):
            build = {}
        build["entrypoint"] = entrypoint
        config["build"] = build
        return save_ark_config(workspace_dir, config)
    except Exception:
        return False


def get_build_options(config: dict[str, Any]) -> dict[str, Any]:
    build = config.get("build")
    return dict(build) if isinstance(build, dict) else {}


def get_dependency_options(config: dict[str, Any]) -> dict[str, Any]:
    options = config.get("dependencies")
    return (
        dict(options)
        if isinstance(options, dict)
        else deepcopy(DEFAULT_DEPENDENCY_OPTIONS)
    )


def get_environment_manager_options(config: dict[str, Any]) -> dict[str, Any]:
    options = config.get("environment_manager")
    return (
        dict(options)
        if isinstance(options, dict)
        else deepcopy(DEFAULT_ENVIRONMENT_MANAGER_OPTIONS)
    )


def _normalize_exclusion_pattern(pattern: str) -> str:
    value = str(pattern).strip().replace("\\", "/")
    if value.startswith("./"):
        value = value[2:]
    if value.endswith("/"):
        value = value.rstrip("/") + "/**"
    return value


def should_exclude_file(
    file_path: str,
    workspace_dir: str,
    exclusion_patterns: Optional[list[str]],
) -> bool:
    try:
        if not file_path or not workspace_dir:
            return False
        file_abs = Path(file_path).resolve()
        workspace_abs = Path(workspace_dir).resolve()
        try:
            relative_path = file_abs.relative_to(workspace_abs).as_posix()
        except ValueError:
            return True
        patterns = exclusion_patterns or []
        for pattern in patterns:
            pat = _normalize_exclusion_pattern(pattern)
            if not pat:
                continue
            if pat.endswith("/**"):
                prefix = pat[:-3].rstrip("/")
                if relative_path == prefix or relative_path.startswith(prefix + "/"):
                    return True
            if fnmatch.fnmatch(relative_path, pat) or Path(relative_path).match(pat):
                return True
            if "/" not in pat and Path(file_abs.name).match(pat):
                return True
        return False
    except Exception:
        return False


def create_default_ark_config(workspace_dir: str) -> bool:
    if not workspace_dir:
        return False
    workspace = Path(workspace_dir)
    path = workspace / "ark.yml"
    if path.exists():
        return False
    try:
        config = new_workspace_config(workspace_name=workspace.name, entry="")
        write_ark_config(workspace, config)
        return True
    except Exception:
        return False


# =============================================================================
# USER-LEVEL CONFIGURATION  (was Core.UserConfig)
# =============================================================================

#: Maps public CLI/API key names to the filename used inside ``config_home()``.
CONFIG_KEYS: dict[str, str] = {
    "user-engine-dir": "user_engine_dir",
    "user-plugin-dir": "user_plugin_dir",
    "dev-engine-dir": "dev_engine_dir",
    "dev-plugin-dir": "dev_plugin_dir",
}

#: Default sub-directory paths (relative to ``Path.home()``) created on first
#: access for keys that have no explicit override.
DEFAULT_USER_DIRS: dict[str, tuple[str, ...]] = {
    "user-engine-dir": ("ark_user", "engines"),
    "user-plugin-dir": ("ark_user", "plugins"),
}


class UserConfigError(RuntimeError):
    """Raised when a user-config operation violates a spec rule."""


def config_home() -> Path:
    """Return the root directory for user-level ARK config files.

    Respects the ``ARK_CONFIG_HOME`` environment variable; falls back to
    ``~/.arkconf``.
    """
    override = os.environ.get("ARK_CONFIG_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arkconf"


def ensure_config_home(*, create: bool = True) -> Path:
    """Return ``config_home()``, optionally creating it."""
    root = config_home()
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def config_file_for(key: str, *, create_root: bool = True) -> Path:
    """Return the ``Path`` of the config file for *key*.

    Raises:
        UserConfigError: When *key* is not in :data:`CONFIG_KEYS`.
    """
    if key not in CONFIG_KEYS:
        raise UserConfigError(f"Unknown config key: {key!r}")
    return ensure_config_home(create=create_root) / CONFIG_KEYS[key]


def resolve_config_value(key: str, *, create_default: bool = True) -> str | None:
    """Read a user config value.

    Returns the persisted override when present, otherwise falls back to the
    default directory path defined in :data:`DEFAULT_USER_DIRS`.  Returns
    ``None`` when neither exists.
    """
    path = config_file_for(key, create_root=False)
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        return value or None

    default_parts = DEFAULT_USER_DIRS.get(key)
    if not default_parts:
        return None

    default_path = Path.home().joinpath(*default_parts)
    if create_default:
        try:
            default_path.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    return str(default_path)


def set_config_value(key: str, value: str) -> str:
    """Persist a user config *value* for *key*.  Returns the stored absolute path."""
    path = config_file_for(key, create_root=True)
    target = str(Path(value).expanduser().resolve())
    path.write_text(target + "\n", encoding="utf-8")
    return target


def unset_config_value(key: str) -> bool:
    """Remove the persisted override for *key*.  Returns ``True`` if it existed."""
    path = config_file_for(key)
    if not path.exists():
        return False
    path.unlink()
    return True


# =============================================================================
# __all__
# =============================================================================

__all__ = [
    # ── Workspace config ──────────────────────────────────────────────────────
    "ArkConfigError",
    "ArkConfigValidationResult",
    "DEFAULT_ARK_CONFIG",
    "DEFAULT_CONFIG",
    "DEFAULT_EXCLUDE_PATTERNS",
    "DEFAULT_DEPENDENCY_OPTIONS",
    "DEFAULT_ENVIRONMENT_MANAGER_OPTIONS",
    "create_default_ark_config",
    "get_build_options",
    "get_dependency_options",
    "get_entrypoint",
    "get_environment_manager_options",
    "load_ark_config",
    "new_workspace_config",
    "normalize_ark_config",
    "save_ark_config",
    "set_entrypoint",
    "should_exclude_file",
    "validate_ark_config",
    "write_ark_config",
    # ── User config ───────────────────────────────────────────────────────────
    "CONFIG_KEYS",
    "DEFAULT_USER_DIRS",
    "UserConfigError",
    "config_file_for",
    "config_home",
    "ensure_config_home",
    "resolve_config_value",
    "set_config_value",
    "unset_config_value",
]
