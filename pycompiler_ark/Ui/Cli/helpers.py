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

import json
import logging
import os
import signal
import subprocess
import sys
import threading
import venv
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

# Global event for CLI cancellation
_CLI_CANCEL_EVENT = threading.Event()


@contextmanager
def _redirect_output(enabled: bool):
    """Redirect stdout and stderr to devnull if enabled is True."""
    if not enabled:
        yield
        return

    # Set env var for child processes (e.g. BCASL sandbox workers)
    os.environ["PYCOMPILER_QUIET"] = "1"

    # Silence 'bcasl' logger
    bcasl_logger = logging.getLogger("bcasl")
    old_level = bcasl_logger.level
    # If not verbose, only show CRITICAL/ERROR if they happen during compilation
    # but the user wants it really clean, so let's go with ERROR.
    bcasl_logger.setLevel(logging.ERROR)

    # Some handlers might be bound to the original sys.stderr/stdout.
    # We don't remove them to avoid side effects, but setting the level should be enough.

    with open(os.devnull, "w") as fnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.stdout = fnull
            sys.stderr = fnull
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            bcasl_logger.setLevel(old_level)
            os.environ.pop("PYCOMPILER_QUIET", None)


def _cli_sigint_handler(signum, frame):
    """Handle SIGINT (Ctrl+C) by setting the cancellation event."""
    _CLI_CANCEL_EVENT.set()


def run_engine_compile(
    *,
    workspace: Path,
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
    verbose: bool = False,
    is_rebuild: bool = False,
) -> dict[str, Any]:
    """Execute a compilation with real-time output streaming to the CLI."""
    from ...Core.Compiler.engine_runner import run_engine_compile_streaming
    from .output import error, get_console, plain

    captured_stdout = []
    captured_stderr = []

    from .interactive import register_cli_status, unregister_cli_status

    console = get_console()
    status = None
    if not verbose and console:
        status = console.status(
            "[cyan]Initializing compilation...[/cyan]", spinner="dots"
        )
        register_cli_status(status)
        status.start()

    def _on_stdout(line: str):
        captured_stdout.append(line)
        from .output import strip_emojis

        clean_line = strip_emojis(line)
        if verbose:
            # plain() already strips emojis via _emit()
            plain(line)
        elif status:
            if clean_line:
                # Update status message for high-level steps
                # We check the original line for emojis/markers to identify steps,
                # but we display the clean version.
                if any(
                    x in line
                    for x in (
                        "Step",
                        "Etape",
                        "Étape",
                        "->",
                        "Execution",
                        "Command",
                        "Commande",
                        "➡️",
                        "🚀",
                        "⚙️",
                        "🔨",
                        "📦",
                        "✅",
                    )
                ):
                    status.update(f"[cyan]{clean_line}[/cyan]")

    def _on_stderr(line: str):
        captured_stderr.append(line)
        if verbose:
            plain(line, err=True)
        # In non-verbose mode, we keep stderr for the final result if it fails

    # Register SIGINT handler
    _CLI_CANCEL_EVENT.clear()
    old_handler = signal.signal(signal.SIGINT, _cli_sigint_handler)

    try:
        # Use redirection to catch any direct print() calls from ...engines or their dependencies
        with _redirect_output(not verbose):
            result = run_engine_compile_streaming(
                workspace=workspace,
                engine_id=engine_id,
                context=context,
                engine_config=engine_config,
                on_stdout=_on_stdout,
                on_stderr=_on_stderr,
                stop_signal=lambda: _CLI_CANCEL_EVENT.is_set(),
                verbose=verbose,
                is_rebuild=is_rebuild,
            )
    except Exception as exc:
        result = {
            "success": False,
            "return_code": None,
            "error": f"Internal error during compilation: {exc}",
        }
    finally:
        # Restore old handler
        signal.signal(signal.SIGINT, old_handler)
        if status:
            status.stop()
            unregister_cli_status(status)

    if _CLI_CANCEL_EVENT.is_set():
        error(
            (
                "Compilation annulée par l'utilisateur (Ctrl+C).",
                "Compilation cancelled by user (Ctrl+C).",
            )
        )
        result["success"] = False
        result["error"] = "Cancelled by user"

    result["stdout"] = "\n".join(captured_stdout)
    result["stderr"] = "\n".join(captured_stderr)

    if not result["success"] and not result.get("error"):
        result["error"] = result["stderr"].strip() or "Build failed"

    return result


from ...Core.Configs import (
    CONFIG_KEYS,
    DEFAULT_USER_DIRS,
    ArkConfigError,
    ArkConfigValidationResult,
    UserConfigError,
    new_workspace_config,
    resolve_config_value,
    set_config_value,
    unset_config_value,
    write_ark_config,
)
from ...Core.Configs import config_file_for as _config_file_for
from ...Core.Configs import config_home as _config_home
from ...Core.Configs import ensure_config_home as _ensure_config_home
from ...Core.Configs import load_ark_config as _load_ark_config
from ...Core.Configs import validate_ark_config as _validate_ark_config
from ...Core.Locking import (
    BuildContext,
    ensure_workspace_layout,
    load_yaml_file,
)
from ...Core.Locking import (
    build_context_from_ark_config as _build_context_from_ark_config,
)
from ...Core.Locking import (
    build_context_from_lock as _build_context_from_lock,
)
from ...Core.Locking import build_lock_payload as _build_lock_payload
from ...Core.Locking import cache_rebuild_lock as _cache_rebuild_lock
from ...Core.Locking import compare_lock_payloads as _compare_lock_payloads
from ...Core.Locking import default_lock_path as _default_lock_path
from ...Core.Locking import write_lock_files as _write_lock_files
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
class PyCompilerArkValidationResult:
    config: dict[str, Any]
    warnings: list[str]


# ── Thin CLI wrappers around Core.Configs (user config) ──────────────────────
# resolve_config_value / set_config_value / unset_config_value are imported
# directly from ...Core.Configs above and re-exported as-is.


def config_home() -> Path:
    """Return the PyCompiler ARK user config root (delegates to Core.Configs)."""
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
    apply_internal: bool = False,
    auto_confirm: bool = False,
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

    internal_modules: list[str] = []
    internal_modules_applied = False
    if apply_internal:
        from ...Core.deps_analyser.analyser import collect_internal_modules

        internal_modules = sorted(
            collect_internal_modules(str(workspace)),
            key=lambda item: item.lower(),
        )
        if internal_modules:
            if auto_confirm:
                config["build"]["include"] = internal_modules
                internal_modules_applied = True
            else:
                from .interactive import ask_yes_no, cli_pause_for_user_input
                from .output import info

                with cli_pause_for_user_input():
                    detected = ", ".join(internal_modules)
                    info(
                        (
                            f"Modules internes à appliquer : {detected}",
                            f"Internal modules to apply: {detected}",
                        )
                    )
                    if ask_yes_no(
                        "Apply these internal modules to build.include?",
                        default_yes=False,
                    ):
                        config["build"]["include"] = internal_modules
                        internal_modules_applied = True

    ark_yml = write_ark_config(workspace, config)

    requirements_path = workspace / "requirements.txt"
    if generate_requirements:
        if requirements_path.exists():
            raise CliSpecError(
                "requirements.txt already exists. (--generate-requirements)"
            )
        from ...Core.deps_analyser.analyser import write_requirements_txt

        if not write_requirements_txt(str(workspace), str(requirements_path)):
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
                "requirements.txt not found. Run 'pycompiler_ark init --generate-requirements' first."
            )
        if not venv_path.exists():
            builder = venv.EnvBuilder(with_pip=True)
            builder.create(str(venv_path))
        python_exe = python_in_venv(venv_path)
        result = subprocess.run(
            [
                str(python_exe),
                "-m",
                "pip",
                "install",
                "-r",
                str(requirements_path),
            ],
            cwd=str(workspace),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise CliSpecError(
                result.stderr.strip() or "requirements installation failed"
            )

    # Initialize workspace preferences
    from .output import info

    pref_path = workspace / ".ark" / "pref.json"
    pref_data = {"venv_mode": "system", "venv_path": None}

    if venv_path.exists():
        pref_data["venv_mode"] = "manual"
        pref_data["venv_path"] = str(venv_path)
    else:
        info(
            (
                "Aucun environnement virtuel créé, utilisation de Python système par défaut.",
                "No virtual environment created, using system Python by default.",
            )
        )

    pref_path.write_text(json.dumps(pref_data, indent=2), encoding="utf-8")

    return {
        "workspace": str(workspace),
        "ark_yml": str(ark_yml),
        "venv": str(venv_path) if venv_path.exists() else None,
        "requirements": str(requirements_path)
        if requirements_path.exists()
        else None,
        "config": config,
        "apply_internal": apply_internal,
        "internal_modules": internal_modules,
        "internal_modules_applied": internal_modules_applied,
    }


def load_ark_config(workspace: Path) -> dict[str, Any]:
    try:
        return _load_ark_config(workspace, require_exists=True)
    except ArkConfigError as exc:
        raise CliSpecError(str(exc)) from exc


def validate_ark_config(
    workspace: Path, config: dict[str, Any]
) -> PyCompilerArkValidationResult:
    result: ArkConfigValidationResult = _validate_ark_config(workspace, config)
    errors = list(result.errors)
    warnings = list(result.warnings)

    engine = str(
        ((result.config.get("build") or {}).get("engine")) or ""
    ).strip()
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

    return PyCompilerArkValidationResult(
        config=result.config, warnings=warnings
    )


def engine_version(engine_id: str) -> str:
    try:
        payload = engine_info_payload(engine_id)
        return str(
            (
                (payload.get("engine") or {}) if payload.get("found") else {}
            ).get("version")
            or "unknown"
        )
    except Exception:
        return "unknown"


def build_lock_payload(
    workspace: Path,
    config: dict[str, Any],
    *,
    engine_id: str,
    python_version: str | None = None,
    resolved_command: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_lock_payload(
        workspace,
        config,
        engine_id=engine_id,
        engine_version=engine_version(engine_id),
        python_version=python_version,
        resolved_command=resolved_command,
    )


def write_lock_files(
    workspace: Path, payload: dict[str, Any]
) -> dict[str, str]:
    return _write_lock_files(workspace, payload)


def cache_rebuild_lock(workspace: Path, payload: dict[str, Any]) -> str:
    return _cache_rebuild_lock(workspace, payload)


def compare_lock_payloads(
    left: dict[str, Any], right: dict[str, Any], return_diff: bool = False
) -> bool | tuple[bool, list[str]]:
    return _compare_lock_payloads(left, right, return_diff=return_diff)


def default_lock_path(workspace: Path) -> Path:
    return _default_lock_path(workspace)


def build_context_from_ark_config(config: dict[str, Any]) -> dict[str, Any]:
    return _build_context_from_ark_config(config).to_dict()


def build_context_from_lock(lock_payload: dict[str, Any]) -> dict[str, Any]:
    return _build_context_from_lock(lock_payload).to_dict()


def build_context_object_from_ark_config(
    config: dict[str, Any],
) -> BuildContext:
    return _build_context_from_ark_config(config)


def build_context_object_from_lock(
    lock_payload: dict[str, Any],
) -> BuildContext:
    return _build_context_from_lock(lock_payload)


def engine_config_from_lock(lock_payload: dict[str, Any]) -> dict[str, Any]:
    engine_data = lock_payload.get("engine") or {}
    config = engine_data.get("config") or {}

    final_config = {}
    if not isinstance(config, dict):
        final_config = {}
    elif "options" in config and "meta" in config:
        opts = config.get("options")
        final_config = dict(opts) if isinstance(opts, dict) else {}
    else:
        final_config = dict(config)

    if "resolved_command" in engine_data:
        final_config["_resolved_command"] = engine_data["resolved_command"]

    return final_config


def ensure_correct_git_commit(
    workspace: Path,
    lock_payload: dict[str, Any],
    confirm_cb: Callable[[str], bool] | None = None,
) -> bool:
    """Checks if the current commit and Git branch match those of the lock."""
    project = lock_payload.get("project") or {}
    locked_commit = project.get("git_commit")
    locked_branch = project.get("git_branch")

    if not locked_commit and not locked_branch:
        return True

    from ...Core.Locking import get_git_branch, get_git_commit_hash

    current_commit = get_git_commit_hash(workspace)
    current_branch = get_git_branch(workspace)

    commit_match = (not locked_commit) or (current_commit == locked_commit)
    branch_match = (not locked_branch) or (current_branch == locked_branch)

    if commit_match and branch_match:
        return True

    import platform
    import subprocess

    from .output import error, info, success, warn

    is_linux = platform.system().lower() == "linux"

    warn(
        (
            "Désynchronisation Git détectée.",
            "Git mismatch detected.",
        )
    )
    if not branch_match:
        info(
            (
                f" - Branche verrouillée : {locked_branch}",
                f" - Locked Branch : {locked_branch}",
            )
        )
        info(
            (
                f" - Branche actuelle : {current_branch}",
                f" - Current Branch : {current_branch}",
            )
        )
    if not commit_match:
        info(
            (
                f" - Commit verrouillé : {locked_commit[:8] if locked_commit else 'N/A'}",
                f" - Locked Commit : {locked_commit[:8] if locked_commit else 'N/A'}",
            )
        )
        info(
            (
                f" - Commit actuel : {current_commit[:8] if current_commit else 'N/A'}",
                f" - Current Commit : {current_commit[:8] if current_commit else 'N/A'}",
            )
        )

    if is_linux:
        try:

            def _confirm(msg: str) -> bool:
                if confirm_cb:
                    return confirm_cb(msg)
                from .interactive import ask_yes_no

                return ask_yes_no(msg, default_yes=True)

            if not branch_match and locked_branch:
                if _confirm(
                    f"Perform automatic 'git checkout {locked_branch}'?"
                ):
                    info(
                        (
                            "Changement de branche...",
                            "Switching branch...",
                        )
                    )
                    subprocess.run(
                        ["git", "checkout", locked_branch],
                        cwd=str(workspace),
                        check=True,
                    )
                    # Re-verify commit after branch change
                    current_commit = get_git_commit_hash(workspace)
                    commit_match = (not locked_commit) or (
                        current_commit == locked_commit
                    )

            if not commit_match and locked_commit:
                if _confirm(
                    f"Perform automatic 'git checkout {locked_commit[:8]}'?"
                ):
                    info(
                        (
                            "Alignement du commit...",
                            "Aligning commit...",
                        )
                    )
                    subprocess.run(
                        ["git", "checkout", locked_commit],
                        cwd=str(workspace),
                        check=True,
                    )
                    success(
                        (
                            "Espace de travail aligné.",
                            "Workspace aligned.",
                        )
                    )
                    return True

            if commit_match and branch_match:
                success(
                    (
                        "Espace de travail aligné.",
                        "Workspace aligned.",
                    )
                )
                return True
            else:
                warn(
                    (
                        "Build avec désynchronisation (non recommandé).",
                        "Build with mismatch (not recommended).",
                    )
                )
                return True
        except Exception as e:
            error(
                (
                    f"Échec de l'alignement Git : {e}",
                    f"Git alignment failed: {e}",
                )
            )
            return False
    else:
        warn(
            (
                "Alignement automatique non pris en charge sur cette plateforme.",
                "Automatic alignment not supported on this platform.",
            )
        )
        if not branch_match and locked_branch:
            info(
                (
                    f"Action manuelle requise : git checkout {locked_branch}",
                    f"Manual action required: git checkout {locked_branch}",
                )
            )
        if not commit_match and locked_commit:
            info(
                (
                    f"Action manuelle requise : git checkout {locked_commit}",
                    f"Manual action required: git checkout {locked_commit}",
                )
            )
        from .interactive import ask_yes_no

        return ask_yes_no("Continue anyway?", default_yes=False)


def list_engines_payload() -> dict[str, Any]:
    return engine_list_payload()


def list_plugins_payload() -> dict[str, Any]:
    return bcasl_list_payload()


def scaffold_engine_payload(
    name: str, root_dir: str | None = None
) -> dict[str, Any]:
    from ...Core.Configs import config_file_for, resolve_config_value
    from .interactive import ask_path

    if not root_dir:
        conf_path = config_file_for("dev-engine-dir", create_root=False)
        if conf_path.exists():
            root_dir = resolve_config_value(
                "dev-engine-dir", create_default=False
            )

    if not root_dir:
        root_dir = ask_path("Path for the new engine")
        if not root_dir:
            return {"created": False, "reason": "No destination path provided"}

    return scaffold_engine(name, root_dir=root_dir)


def scaffold_plugin_payload(
    name: str, root_dir: str | None = None
) -> dict[str, Any]:
    from ...Core.Configs import config_file_for, resolve_config_value
    from .interactive import ask_path

    if not root_dir:
        conf_path = config_file_for("dev-plugin-dir", create_root=False)
        if conf_path.exists():
            root_dir = resolve_config_value(
                "dev-plugin-dir", create_default=False
            )

    if not root_dir:
        root_dir = ask_path("Path for the new plugin")
        if not root_dir:
            return {"created": False, "reason": "No destination path provided"}

    return scaffold_plugin(name, root_dir=root_dir)


def run_bcasl_before_compile_sync(
    workspace: Path, verbose: bool = False, build_context: Optional[Any] = None
) -> bool:
    """Run BCASL pre-compile stage synchronously for the CLI.

    Returns:
        True if compilation can proceed (success or BCASL disabled), False otherwise.
    """
    from ...bcasl.Loader import _is_bcasl_enabled, run_pre_compile

    # Quick check to avoid "blablabla inutile" when disabled
    if not _is_bcasl_enabled(workspace):
        return True

    from .interactive import register_cli_status, unregister_cli_status
    from .output import error, get_console, info, log, success

    console = get_console()
    status = None
    if not verbose and console:
        status = console.status(
            "[cyan]Running BCASL...[/cyan]", spinner="dots"
        )
        register_cli_status(status)
        status.start()

    class CliBcaslHost:
        def __init__(self, ws_dir: Path, status_obj):
            self.workspace_dir = str(ws_dir)
            self.status_obj = status_obj

            class Logger:
                def __init__(self, host_ptr):
                    self.host_ptr = host_ptr

                def append(self, msg: str):
                    if verbose:
                        # Strip trailing newline as our log() adds one
                        log("BCASL", msg.rstrip())
                    elif self.host_ptr.status_obj:
                        clean = msg.strip()
                        if clean and not clean.startswith("["):
                            display = clean
                            if clean.startswith("Plugin: "):
                                # Using Rich markup instead of icons
                                plugin_name = clean[8:].strip()
                                display = f"Plugin: [bold white]{plugin_name}[/bold white]"
                            elif clean.startswith("Phase: "):
                                phase_name = clean[7:].strip()
                                display = f"Phase: [bold yellow]{phase_name}[/bold yellow]"

                            if len(display) < 120:
                                self.host_ptr.status_obj.update(
                                    f"[cyan]BCASL[/cyan] [white]»[/white] {display}"
                                )

            self.log = Logger(self)

    host = CliBcaslHost(workspace, status)

    info(
        (
            "Exécution des contrôles BCASL pré-compilation...",
            "Running BCASL pre-compile checks...",
        )
    )

    # Register SIGINT handler
    _CLI_CANCEL_EVENT.clear()
    old_handler = signal.signal(signal.SIGINT, _cli_sigint_handler)

    try:
        # Catch direct prints from BCASL plugins or loader
        with _redirect_output(not verbose):
            report = run_pre_compile(host, build_context=build_context)
    except Exception as exc:
        if status:
            status.stop()
            unregister_cli_status(status)
        error(
            (
                f"Échec de l'exécution BCASL : {exc}",
                f"BCASL execution failed: {exc}",
            )
        )
        return False
    finally:
        # Restore old handler
        signal.signal(signal.SIGINT, old_handler)
        if status:
            status.stop()
            unregister_cli_status(status)

    if _CLI_CANCEL_EVENT.is_set():
        error(
            (
                "BCASL annulé par l'utilisateur (Ctrl+C).",
                "BCASL cancelled by user (Ctrl+C).",
            )
        )
        return False

    if report is None:
        # report is None if BCASL is disabled or failed silently
        return True

    if isinstance(report, dict):
        try:
            from ...bcasl.Loader import is_bcasl_disabled_report

            if is_bcasl_disabled_report(report):
                return True
        except Exception:
            pass
        if "ok" in report:
            return bool(report.get("ok"))

    if hasattr(report, "ok"):
        if not getattr(report, "ok"):
            error(
                (
                    "BCASL a signalé des échecs de sécurité ou de validation.",
                    "BCASL reported security or validation failures.",
                )
            )
            return False
        if verbose:
            success(
                (
                    "Contrôles BCASL réussis.",
                    "BCASL checks passed.",
                )
            )
        return True

    return True


def run_bcasl_headless(args: list[str], verbose: bool = False) -> int:
    """Run BCASL in headless mode for the current workspace."""
    from ...bcasl.Loader import run_pre_compile
    from .output import error, get_console, info, log, success

    if "list" in args:
        payload = list_plugins_payload()
        for plugin in payload.get("plugins", []):
            print(f"{plugin['id']} {plugin['version']} {plugin['name']}")
        return 0

    workspace = Path.cwd()
    if "run" in args:
        # If workspace path is provided in args, use it
        for i, arg in enumerate(args):
            if arg == "run" and i + 1 < len(args):
                candidate = Path(args[i + 1])
                if candidate.is_dir():
                    workspace = candidate.resolve()
                break

    from .interactive import register_cli_status, unregister_cli_status

    console = get_console()
    status = None
    if not verbose and console:
        status = console.status(
            "[cyan]Running BCASL (headless)...[/cyan]", spinner="dots"
        )
        register_cli_status(status)
        status.start()

    class CliBcaslHost:
        def __init__(self, ws_dir: Path, status_obj):
            self.workspace_dir = str(ws_dir)
            self.status_obj = status_obj

            class Logger:
                def __init__(self, host_ptr):
                    self.host_ptr = host_ptr

                def append(self, msg: str):
                    if verbose:
                        log("BCASL", msg.rstrip())
                    elif self.host_ptr.status_obj:
                        clean = msg.strip()
                        if clean and not clean.startswith("["):
                            display = clean
                            if clean.startswith("Plugin: "):
                                # Using Rich markup instead of icons
                                plugin_name = clean[8:].strip()
                                display = f"Plugin: [bold white]{plugin_name}[/bold white]"
                            elif clean.startswith("Phase: "):
                                phase_name = clean[7:].strip()
                                display = f"Phase: [bold yellow]{phase_name}[/bold yellow]"

                            if len(display) < 120:
                                self.host_ptr.status_obj.update(
                                    f"[cyan]BCASL[/cyan] [white]»[/white] {display}"
                                )

            self.log = Logger(self)

    host = CliBcaslHost(workspace, status)

    info(
        (
            f"Exécution BCASL headless dans {workspace}...",
            f"Running BCASL headless in {workspace}...",
        )
    )

    # Register SIGINT handler
    _CLI_CANCEL_EVENT.clear()
    old_handler = signal.signal(signal.SIGINT, _cli_sigint_handler)

    try:
        with _redirect_output(not verbose):
            report = run_pre_compile(host)

        if _CLI_CANCEL_EVENT.is_set():
            if status:
                status.stop()
                unregister_cli_status(status)
            error(
                (
                    "BCASL annulé par l'utilisateur (Ctrl+C).",
                    "BCASL cancelled by user (Ctrl+C).",
                )
            )
            return 1

        if report and hasattr(report, "ok") and not getattr(report, "ok"):
            if status:
                status.stop()
                unregister_cli_status(status)
            error(
                (
                    "\nBCASL a trouvé des problèmes.",
                    "\nBCASL found issues.",
                )
            )
            return 1

        if status:
            status.stop()
            unregister_cli_status(status)
        success(
            (
                "\nBCASL terminé avec succès.",
                "\nBCASL completed successfully.",
            )
        )
        return 0
    except Exception as exc:
        if status:
            status.stop()
            unregister_cli_status(status)
        error(
            (
                f"Échec BCASL : {exc}",
                f"BCASL failed: {exc}",
            )
        )
        return 1
    finally:
        signal.signal(signal.SIGINT, old_handler)
        if status:
            try:
                status.stop()
            except Exception:
                pass
            unregister_cli_status(status)


def launch_gui(*, legacy: bool = False) -> int:
    return launch_main_application(
        no_splash=False,
        ide_gui=not legacy,
        classic_gui=legacy,
    )
