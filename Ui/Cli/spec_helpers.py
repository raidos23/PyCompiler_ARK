from __future__ import annotations

import subprocess
import venv
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from Core.Configs import (
    ArkConfigError,
    ArkConfigValidationResult,
    load_ark_config as _load_ark_config,
    new_workspace_config,
    validate_ark_config as _validate_ark_config,
    write_ark_config,
)
from Core.Locking import (
    BuildContext,
    build_context_from_ark_config as _build_context_from_ark_config,
    build_context_from_lock as _build_context_from_lock,
    build_lock_payload as _build_lock_payload,
    cache_rebuild_lock as _cache_rebuild_lock,
    compare_lock_payloads as _compare_lock_payloads,
    default_lock_path as _default_lock_path,
    ensure_workspace_layout,
    load_yaml_file,
    write_lock_files as _write_lock_files,
)
from Core.Compiler.engine_runner import run_engine_compile as _core_run_engine_compile
from Core.Configs import (
    CONFIG_KEYS,
    DEFAULT_USER_DIRS,
    UserConfigError,
    config_home as _config_home,
    ensure_config_home as _ensure_config_home,
    config_file_for as _config_file_for,
    resolve_config_value,
    set_config_value,
    unset_config_value,
)
from .discovery import (
    bcasl_list_payload,
    engine_info_payload,
    engine_list_payload,
    scaffold_engine,
    scaffold_plugin,
)
from .launchers import launch_main_application


class CliSpecError(RuntimeError):
    """Raised when a spec-level CLI rule is violated."""


@dataclass(slots=True)
class ArkValidationResult:
    config: dict[str, Any]
    warnings: list[str]


# ── Thin CLI wrappers around Core.Configs (user config) ──────────────────────
# resolve_config_value / set_config_value / unset_config_value are imported
# directly from Core.Configs above and re-exported as-is.

def config_home() -> Path:
    """Return the ARK user config root (delegates to Core.Configs)."""
    return _config_home()


def ensure_config_home(*, create: bool = True) -> Path:
    return _ensure_config_home(create=create)


def config_file_for(key: str, *, create_root: bool = True) -> Path:
    try:
        return _config_file_for(key, create_root=create_root)
    except UserConfigError as exc:
        raise CliSpecError(str(exc)) from exc


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

    config = new_workspace_config(
        workspace_name=workspace.name,
        version="1.0.0",
        entry=relative_to_workspace(workspace, entry_path),
        engine="pyinstaller",
        output="dist/",
        icon=icon_value,
    )
    ark_yml = write_ark_config(workspace, config)

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


def load_ark_config(workspace: Path) -> dict[str, Any]:
    try:
        return _load_ark_config(workspace, require_exists=True)
    except ArkConfigError as exc:
        raise CliSpecError(str(exc)) from exc


def validate_ark_config(workspace: Path, config: dict[str, Any]) -> ArkValidationResult:
    result: ArkConfigValidationResult = _validate_ark_config(workspace, config)
    errors = list(result.errors)
    warnings = list(result.warnings)

    engine = str(((result.config.get("build") or {}).get("engine")) or "").strip()
    if engine:
        try:
            info = engine_info_payload(engine)
            if not info.get("found"):
                errors.append(f"build.engine: unknown engine '{engine}'")
        except Exception:
            pass

    if errors:
        joined = "\n".join(f"- {item}" for item in errors)
        raise CliSpecError(f"Invalid ark.yml\n{joined}")

    return ArkValidationResult(config=result.config, warnings=warnings)


def engine_version(engine_id: str) -> str:
    try:
        payload = engine_info_payload(engine_id)
        return str(((payload.get("engine") or {}) if payload.get("found") else {}).get("version") or "unknown")
    except Exception:
        return "unknown"


def build_lock_payload(
    workspace: Path,
    config: dict[str, Any],
    *,
    engine_id: str,
) -> dict[str, Any]:
    return _build_lock_payload(
        workspace,
        config,
        engine_id=engine_id,
        engine_version=engine_version(engine_id),
    )


def write_lock_files(workspace: Path, payload: dict[str, Any]) -> dict[str, str]:
    return _write_lock_files(workspace, payload)


def cache_rebuild_lock(workspace: Path, payload: dict[str, Any]) -> str:
    return _cache_rebuild_lock(workspace, payload)


def compare_lock_payloads(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return _compare_lock_payloads(left, right)


def default_lock_path(workspace: Path) -> Path:
    return _default_lock_path(workspace)


def build_context_from_ark_config(config: dict[str, Any]) -> dict[str, Any]:
    return _build_context_from_ark_config(config).to_dict()


def build_context_from_lock(lock_payload: dict[str, Any]) -> dict[str, Any]:
    return _build_context_from_lock(lock_payload).to_dict()


def build_context_object_from_ark_config(config: dict[str, Any]) -> BuildContext:
    return _build_context_from_ark_config(config)


def build_context_object_from_lock(lock_payload: dict[str, Any]) -> BuildContext:
    return _build_context_from_lock(lock_payload)


def run_engine_compile(
    *,
    workspace: Path,
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Delegate to :func:`Core.Compiler.engine_runner.run_engine_compile`.

    The Core implementation is the single source of truth for compilation.
    """
    return _core_run_engine_compile(
        workspace=workspace,
        engine_id=engine_id,
        context=context,
        engine_config=engine_config,
    )


def engine_config_from_lock(lock_payload: dict[str, Any]) -> dict[str, Any]:
    config = ((lock_payload.get("engine") or {}).get("config")) or {}
    return dict(config) if isinstance(config, dict) else {}


def list_engines_payload() -> dict[str, Any]:
    return engine_list_payload()


def list_plugins_payload() -> dict[str, Any]:
    return bcasl_list_payload()


def scaffold_engine_payload(name: str, root_dir: str | None = None) -> dict[str, Any]:
    return scaffold_engine(name, root_dir=root_dir)


def scaffold_plugin_payload(name: str, root_dir: str | None = None) -> dict[str, Any]:
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
    return launch_main_application(
        no_splash=False,
        ide_gui=not legacy,
        classic_gui=legacy,
    )
