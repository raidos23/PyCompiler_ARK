from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import venv
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, distributions, version
from pathlib import Path
from typing import Any

import yaml

CONFIG_KEYS = {
    "user-engine-dir": "user_engine_dir",
    "user-plugin-dir": "user_plugin_dir",
    "dev-engine-dir": "dev_engine_dir",
    "dev-plugin-dir": "dev_plugin_dir",
}

DEFAULT_USER_DIRS = {
    "user-engine-dir": ("ark_user", "engines"),
    "user-plugin-dir": ("ark_user", "plugins"),
}

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class CliSpecError(RuntimeError):
    """Raised when a spec-level CLI rule is violated."""


@dataclass(slots=True)
class ArkValidationResult:
    config: dict[str, Any]
    warnings: list[str]


def config_home() -> Path:
    override = os.environ.get("ARK_CONFIG_HOME")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".arkconf"


def ensure_config_home(*, create: bool = True) -> Path:
    root = config_home()
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return root


def config_file_for(key: str, *, create_root: bool = True) -> Path:
    if key not in CONFIG_KEYS:
        raise CliSpecError(f"Unknown config key: {key}")
    return ensure_config_home(create=create_root) / CONFIG_KEYS[key]


def resolve_config_value(key: str, *, create_default: bool = True) -> str | None:
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
    path = config_file_for(key, create_root=True)
    target = str(Path(value).expanduser().resolve())
    path.write_text(target + "\n", encoding="utf-8")
    return target


def unset_config_value(key: str) -> bool:
    path = config_file_for(key)
    if not path.exists():
        return False
    path.unlink()
    return True


def workspace_ark_dirs(workspace: Path) -> list[Path]:
    return [
        workspace / ".ark" / "lock",
        workspace / ".ark" / "cache",
        workspace / ".ark" / "build",
        workspace / ".ark" / "logs",
    ]


def ensure_workspace_layout(workspace: Path) -> None:
    for path in workspace_ark_dirs(workspace):
        path.mkdir(parents=True, exist_ok=True)


def relative_to_workspace(workspace: Path, target: Path) -> str:
    return target.resolve().relative_to(workspace.resolve()).as_posix()


def python_in_venv(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def init_workspace(
    *,
    cwd: Path,
    entry: str,
    icon: str | None = None,
    with_venv: bool = False,
    generate_requirements: bool = False,
    install_requirements: bool = False,
) -> dict[str, Any]:
    workspace = cwd.resolve()
    if not workspace.exists():
        raise CliSpecError("Current directory does not exist.")

    entry_path = Path(entry).expanduser()
    if not entry_path.is_absolute():
        entry_path = workspace / entry_path
    if entry_path.is_dir():
        raise CliSpecError("Entry point must be a file, not a directory.")
    if not entry_path.is_file():
        raise CliSpecError(f"Entry file '{entry}' not found.")

    icon_value = None
    if icon:
        icon_path = Path(icon).expanduser()
        if not icon_path.is_absolute():
            icon_path = workspace / icon_path
        if not icon_path.is_file():
            raise CliSpecError(f"Icon file '{icon}' not found.")
        icon_value = relative_to_workspace(workspace, icon_path)

    ensure_workspace_layout(workspace)

    config = {
        "project": {
            "name": workspace.name,
            "version": "1.0.0",
            "entry": relative_to_workspace(workspace, entry_path),
        },
        "workspace": {"exclude": []},
        "build": {"engine": "pyinstaller", "output": "dist/", "data": []},
    }
    if icon_value:
        config["build"]["icon"] = icon_value

    ark_yml = workspace / "ark.yml"
    ark_yml.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8"
    )

    requirements_path = workspace / "requirements.txt"
    if generate_requirements:
        if requirements_path.exists():
            raise CliSpecError(
                "requirements.txt already exists. (--generate-requirements)"
            )
        requirements_path.write_text(
            "# Add your runtime dependencies here.\n", encoding="utf-8"
        )

    venv_path = workspace / ".ark" / "venv"
    if with_venv and not venv_path.exists():
        builder = venv.EnvBuilder(with_pip=True)
        builder.create(str(venv_path))

    if install_requirements:
        if not requirements_path.exists():
            raise CliSpecError(
                "requirements.txt not found. Run 'ark init --generate-requirements' first."
            )
        if not venv_path.exists():
            builder = venv.EnvBuilder(with_pip=True)
            builder.create(str(venv_path))
        python_exe = python_in_venv(venv_path)
        result = subprocess.run(
            [str(python_exe), "-m", "pip", "install", "-r", str(requirements_path)],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CliSpecError(result.stderr.strip() or "requirements installation failed")

    return {
        "workspace": str(workspace),
        "ark_yml": str(ark_yml),
        "venv": str(venv_path) if venv_path.exists() else None,
        "requirements": str(requirements_path) if requirements_path.exists() else None,
        "config": config,
    }


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise CliSpecError(f"File not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise CliSpecError(f"Invalid YAML object in {path}")
    return data


def load_ark_config(workspace: Path) -> dict[str, Any]:
    path = workspace / "ark.yml"
    if not path.is_file():
        raise CliSpecError("ark.yml not found in current directory.")
    return load_yaml_file(path)


def validate_ark_config(workspace: Path, config: dict[str, Any]) -> ArkValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    project = config.get("project")
    build = config.get("build")
    workspace_cfg = config.get("workspace", {})

    if not isinstance(project, dict):
        project = {}
    if not isinstance(build, dict):
        build = {}
    if not isinstance(workspace_cfg, dict):
        workspace_cfg = {}

    name = str(project.get("name") or "").strip()
    version_value = str(project.get("version") or "").strip()
    entry = str(project.get("entry") or "").strip()
    engine = str(build.get("engine") or "").strip()
    output = str(build.get("output") or "").strip()
    icon = str(build.get("icon") or "").strip()

    if not name:
        errors.append("project.name is required")
    if not version_value or not SEMVER_RE.match(version_value):
        errors.append("project.version must use X.Y.Z format")
    if not entry:
        errors.append("project.entry is required")
    else:
        entry_path = workspace / Path(entry)
        if not entry_path.is_file():
            errors.append(f"project.entry: file '{entry}' not found")

    if not engine:
        errors.append("build.engine is required")
    else:
        try:
            from cli.headless_ops import engine_info_payload

            info = engine_info_payload(engine)
            if not info.get("found"):
                errors.append(f"build.engine: unknown engine '{engine}'")
        except Exception:
            pass

    if not output:
        errors.append("build.output is required")

    if icon:
        icon_path = workspace / Path(icon)
        if not icon_path.is_file():
            warnings.append(f"Icon file '{icon}' not found (ignored)")

    normalized = {
        "project": {"name": name, "version": version_value, "entry": entry},
        "workspace": {"exclude": list(workspace_cfg.get("exclude") or [])},
        "build": {
            "engine": engine,
            "output": output,
            "data": list(build.get("data") or []),
        },
    }
    if icon:
        normalized["build"]["icon"] = icon

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise CliSpecError(f"Invalid ark.yml\n{joined}")

    return ArkValidationResult(config=normalized, warnings=warnings)


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


def engine_version(engine_id: str) -> str:
    try:
        from cli.headless_ops import engine_info_payload

        payload = engine_info_payload(engine_id)
        return str(((payload.get("engine") or {}) if payload.get("found") else {}).get("version") or "unknown")
    except Exception:
        return "unknown"


def included_workspace_files(workspace: Path, exclude_patterns: list[str]) -> list[Path]:
    included: list[Path] = []
    for path in sorted(workspace.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(workspace).as_posix()
        if rel.startswith(".ark/"):
            continue
        if any(Path(rel).match(pattern) for pattern in exclude_patterns):
            continue
        included.append(path)
    return included


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
) -> dict[str, Any]:
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
            "version": engine_version(engine_id),
            "config": read_engine_config(workspace, engine_id),
        },
        "platform": {
            "os": sys.platform,
            "arch": platform.machine(),
            "python_version": platform.python_version(),
        },
        "dependencies": installed_distributions_snapshot(),
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
    return left == right


def default_lock_path(workspace: Path) -> Path:
    return workspace / ".ark" / "lock" / "latest.lock.yml"


def build_context_from_ark_config(config: dict[str, Any]) -> dict[str, Any]:
    project = config.get("project") or {}
    build = config.get("build") or {}
    workspace_cfg = config.get("workspace") or {}
    return {
        "project_name": project.get("name"),
        "entry_point": project.get("entry"),
        "output_dir": build.get("output"),
        "exclude_patterns": list(workspace_cfg.get("exclude") or []),
        "data_mappings": list(build.get("data") or []),
        "icon": build.get("icon"),
    }


def build_context_from_lock(lock_payload: dict[str, Any]) -> dict[str, Any]:
    project = lock_payload.get("project") or {}
    build = lock_payload.get("build") or {}
    workspace_cfg = lock_payload.get("workspace") or {}
    return {
        "project_name": project.get("name"),
        "entry_point": project.get("entry"),
        "output_dir": build.get("output"),
        "exclude_patterns": list(workspace_cfg.get("exclude_patterns") or []),
        "data_mappings": list(build.get("data") or []),
        "icon": build.get("icon"),
    }


def run_engine_compile(
    *,
    workspace: Path,
    engine_id: str,
    entry_file: str,
) -> dict[str, Any]:
    from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp

    app = EnginesStandaloneApp(
        workspace_dir=str(workspace),
        language="en",
        theme="dark",
        headless=True,
        quiet_logs=True,
    )
    return app.run_compilation(engine_id, str(workspace / entry_file), dry_run=False)


def list_engines_payload() -> dict[str, Any]:
    from cli.headless_ops import engine_list_payload

    return engine_list_payload()


def list_plugins_payload() -> dict[str, Any]:
    from cli.headless_ops import bcasl_list_payload

    return bcasl_list_payload()


def scaffold_engine_payload(name: str, root_dir: str | None = None) -> dict[str, Any]:
    from cli.headless_ops import scaffold_engine

    return scaffold_engine(name, root_dir=root_dir)


def scaffold_plugin_payload(name: str, root_dir: str | None = None) -> dict[str, Any]:
    from cli.headless_ops import scaffold_plugin

    return scaffold_plugin(name, root_dir=root_dir)


def run_bcasl_headless(args: list[str]) -> int:
    if not args or args[0] in ("help", "-h", "--help"):
        print("Usage: ark run bcasl [--timeout SECONDS] [--list-plugins]")
        return 0

    sub = str(args[0]).lower()
    if sub == "list":
        payload = list_plugins_payload()
        plugins = list(payload.get("plugins", []))
        print(f"Available BCASL plugins ({len(plugins)}):")
        for plugin in plugins:
            print(f"  - {plugin['id']} ({plugin['name']}) v{plugin['version']}")
        return 0

    if sub != "run":
        print(f"Unknown BCASL subcommand: {sub}")
        return 2

    workspace: str | None = None
    timeout = 0.0
    i = 1
    while i < len(args):
        tok = args[i]
        if tok in ("-w", "--workspace"):
            if i + 1 >= len(args):
                print("Missing workspace path after --workspace")
                return 2
            workspace = str(Path(args[i + 1]).expanduser())
            i += 2
            continue
        if tok == "--timeout":
            if i + 1 >= len(args):
                print("Missing value after --timeout")
                return 2
            try:
                timeout = float(args[i + 1])
            except ValueError:
                print("Timeout must be a number.")
                return 2
            i += 2
            continue
        if workspace is None and not tok.startswith("-"):
            workspace = str(Path(tok).expanduser())
            i += 1
            continue
        print(f"Unknown option for bcasl run: {tok}")
        return 2

    if not workspace:
        print("Usage: bcasl run <workspace> [--timeout SECONDS]")
        return 2

    ws_path = Path(workspace)
    if not ws_path.exists() or not ws_path.is_dir():
        print(f"Invalid workspace: {workspace}")
        return 1

    try:
        from OnlyMod.BcaslOnlyMod.app import BcaslOnlyModApp
    except Exception as exc:
        print(f"Unable to load BCASL module: {exc}")
        return 1

    try:
        app = BcaslOnlyModApp(
            workspace_dir=str(ws_path),
            language="en",
            theme="dark",
            headless=True,
        )
    except Exception as exc:
        print(f"Failed to initialize BCASL mode: {exc}")
        return 1

    report = app.run_plugins(
        workspace_dir=str(ws_path),
        timeout=timeout,
        log_callback=lambda msg: print(f"[BCASL] {msg}"),
    )
    if report is None:
        print("BCASL execution failed to start.")
        return 1
    if report.ok:
        print("BCASL run completed successfully.")
        return 0
    failed = sum(1 for item in report if not item.success)
    print(f"BCASL run finished with failures: {failed} plugin(s) failed.")
    return 1


def launch_gui(*, legacy: bool = False) -> int:
    from cli.lazy_ops import launch_main_gui

    return launch_main_gui(no_splash=False, ide_gui=not legacy, classic_gui=legacy)
