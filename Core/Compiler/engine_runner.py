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
Engine Runner - pure-Python, Qt-free compilation executor.

Source of truth for how ARK loads an engine and runs a compilation
against a BuildContext.  Both the CLI (Ui/Cli/spec_helpers.py) and the
Qt async path (MainProcess.compile_from_context) delegate to this module.

Provides:
- `resolve_engine_command` - load an engine and derive (program, args)
- `run_engine_compile`     - full synchronous compilation pipeline
"""

from __future__ import annotations

import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

# BuildContext lives in engine_sdk; imported here so callers of this module
# only need to import from Core.Compiler.
from Core.engine.build_context import BuildContext
from Core.process_security import hardened_popen_kwargs, secure_command


class EngineRunnerError(RuntimeError):
    """Raised when an engine cannot be loaded or does not produce a command."""


def resolve_engine_command(
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
    gui: Any = None,
) -> tuple[str, list[str], dict[str, str]]:
    """
    Load *engine_id* and derive (program, args, env) for *context*.

    Args:
        engine_id:     Registered engine identifier (e.g. ``"pyinstaller"``).
        context:       BuildContext describing the project.
        engine_config: Optional per-engine config overrides.
        gui:           Optional GUI or Bridge object for logging and auto-mapping.

    Returns:
        A ``(program, args, env)`` tuple ready to be passed to subprocess.

    Raises:
        EngineRunnerError: When the engine cannot be loaded, does not support
                           BuildContext builds, or returns an empty command.
    """
    try:
        import Core.engine as engines_loader

        engine = engines_loader.create(engine_id)
        if gui:
            try:
                engine._gui = gui
            except Exception:
                pass
    except Exception as exc:
        raise EngineRunnerError(f"Unable to load engine '{engine_id}': {exc}") from exc

    try:
        setattr(engine, "_config_overrides", dict(engine_config or {}))
    except Exception:
        pass

    try:
        resolved = engine.program_and_args(context)
    except NotImplementedError:
        raise EngineRunnerError(
            f"Engine '{engine_id}' does not implement build_command"
        )
    except Exception as exc:
        raise EngineRunnerError(
            f"Engine '{engine_id}' failed to build command: {exc}"
        ) from exc

    if not resolved:
        raise EngineRunnerError(f"Engine '{engine_id}' returned no command")

    program, args = resolved

    # Integrated Auto-mapping: apply engine-specific flags from detected imports
    if gui and str(
        os.environ.get("PYCOMPILER_DISABLE_AUTO_BUILDER", "0")
    ).lower() not in (
        "1",
        "true",
        "yes",
    ):
        try:
            from Core.Auto_Command_Builder import compute_auto_for_engine

            auto_args = compute_auto_for_engine(gui, engine_id)
            if auto_args:
                # Try to insert auto-args before the entry point to ensure they are
                # interpreted as compiler flags, not script arguments.
                try:
                    # Exact match or end-match for the entry point
                    target_idx = -1
                    if context.entry_point in args:
                        target_idx = args.index(context.entry_point)
                    else:
                        for i, arg in enumerate(args):
                            if str(arg).endswith(context.entry_point):
                                target_idx = i
                                break

                    if target_idx != -1:
                        # Insert before target_idx
                        # We don't check "if a not in args" because some flags like
                        # --collect-all or --hidden-import can be repeated with different values.
                        # However, we avoid adding the EXACT same pair twice if possible.

                        # To be safe and simple, we just insert all auto_args at target_idx
                        # and rely on the engine or auto-builder to have filtered exact duplicates.
                        for a in reversed(auto_args):
                            args.insert(target_idx, a)
                    else:
                        # Fallback: append at the end
                        for a in auto_args:
                            args.append(a)
                except Exception:
                    pass
        except Exception:
            pass

    # Retrieve engine-specific environment
    try:
        env = engine.environment() if hasattr(engine, "environment") else {}
        if env is None:
            env = {}
    except Exception:
        env = {}

    return str(program), list(args), dict(env)


def run_engine_compile(
    *,
    workspace: Path,
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
    gui: Any = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Execute a compilation synchronously.

    This is the **source of truth** for ARK's compilation pipeline.
    It validates the entry point, resolves the command via the engine,
    applies security hardening, and runs the subprocess.

    Args:
        workspace:     Absolute path to the project workspace.
        engine_id:     Registered engine identifier.
        context:       BuildContext describing the project.
        engine_config: Optional per-engine config overrides (forwarded to
                       ``engine._config_overrides``).
        gui:           Optional GUI object.
        verbose:       Whether to enable verbose logging.

    Returns:
        A result dict with success status, return code, command, stdout, stderr, and error message.
    """
    captured_stdout = []
    captured_stderr = []

    def _on_stdout(line: str):
        captured_stdout.append(line)

    def _on_stderr(line: str):
        captured_stderr.append(line)

    result = run_engine_compile_streaming(
        workspace=workspace,
        engine_id=engine_id,
        context=context,
        engine_config=engine_config,
        on_stdout=_on_stdout,
        on_stderr=_on_stderr,
        gui=gui,
        verbose=verbose,
    )

    result["stdout"] = "\n".join(captured_stdout)
    result["stderr"] = "\n".join(captured_stderr)

    if not result["success"] and not result.get("error"):
        result["error"] = result["stderr"].strip() or "Build failed"

    return result


def run_engine_compile_streaming(
    *,
    workspace: Path,
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
    on_stdout: Optional[Callable[[str], None]] = None,
    on_stderr: Optional[Callable[[str], None]] = None,
    stop_signal: Optional[Callable[[], bool]] = None,
    gui: Any = None,
    verbose: bool = False,
    is_rebuild: bool = False,
) -> dict[str, Any]:
    """
    Execute a compilation with real-time output streaming.

    Args:
        workspace:     Absolute path to the project workspace.
        engine_id:     Registered engine identifier.
        context:       BuildContext describing the project.
        engine_config: Optional per-engine config overrides.
        on_stdout:     Callback for each line of stdout.
        on_stderr:     Callback for each line of stderr.
        stop_signal:   Optional callback that returns True if cancellation is requested.
        gui:           Optional GUI object to use instead of creating a bridge.
        verbose:       Whether to enable verbose logging.
        is_rebuild:     Whether this is a rebuild from a lock file (disables auto-mapping).

    Returns:
        A result dict.
    """
    # -- 1. Validate entry point ----------------------------------------------
    entry_path = workspace / Path(context.entry_point)
    if not context.entry_point or not entry_path.is_file():
        return _failure(f"Entrypoint missing or obsolete: {context.entry_point}")

    # -- 2. Resolve (program, args, env) from engine --------------------------
    try:
        if on_stdout:
            on_stdout("Etape 1/3 : Verification et installation des outils requis...")

        import Core.engine as engines_loader

        engine_instance = engines_loader.create(engine_id)

        # Ensure tools are installed (this may take time, so we do it in the thread)
        def _log(fr, en):
            if on_stdout:
                on_stdout(f"  -> {en}")

        if gui:
            bridge = gui
        else:
            from PySide6.QtCore import QObject

            # We pass a dummy 'gui' object that supports log_i18n_level-like logging
            class LogBridge(QObject):
                def __init__(self, log_cb, workspace_path: Path, verbose: bool = False):
                    super().__init__()
                    self.log_cb = log_cb
                    self.workspace_dir = str(workspace_path)
                    self.verbose = verbose
                    self.log = self  # So gui.log.append works
                    self.use_system_python = False  # Default for CLI
                    self.venv_path_manuel = None
                    self._venv_manager = None
                    self._sys_deps_manager = None

                def append(self, message: str):
                    # message is already formatted by log_i18n_level
                    self.log_cb("", message)

                def _safe_log(self, text, text_en=None, level=None):
                    # Fallback for VenvManager
                    msg = text_en if text_en else text
                    self.log_cb("", msg)

                def tr(self, fr, en):
                    return en  # Simple fallback

                @property
                def venv_manager(self):
                    if self._venv_manager is None:
                        from Core.Venv_Manager.Manager import VenvManager

                        self._venv_manager = VenvManager(self)
                        # Automatically load workspace preferences if available
                        if hasattr(self, "workspace_dir") and self.workspace_dir:
                            try:
                                self._venv_manager.apply_workspace_pref(
                                    self.workspace_dir
                                )
                            except Exception:
                                pass
                    return self._venv_manager

                @property
                def sys_deps_manager(self):
                    if self._sys_deps_manager is None:
                        from Core.SysDependencyManager import SysDependencyManager

                        self._sys_deps_manager = SysDependencyManager(self)
                    return self._sys_deps_manager

            bridge = LogBridge(_log, workspace, verbose=verbose)

        # Link bridge to engine for venv/tool resolution in build_command
        try:
            engine_instance._gui = bridge
        except Exception:
            pass

        # Log the environment used for this compilation
        env_display = "System"
        if bridge and hasattr(bridge, "venv_manager"):
            try:
                vpath = bridge.venv_manager.resolve_project_venv()
                if vpath:
                    # Make path relative if it's inside workspace
                    try:
                        rel_path = Path(vpath).relative_to(workspace)
                        env_display = f"Venv ({rel_path})"
                    except ValueError:
                        env_display = f"Venv ({vpath})"
            except Exception:
                pass

        if on_stdout:
            on_stdout(f"⚙️ Environnement : {env_display}")

        if hasattr(engine_instance, "ensure_tools_installed"):
            if not engine_instance.ensure_tools_installed(
                bridge, stop_signal=stop_signal
            ):
                if stop_signal and stop_signal():
                    return _failure("Compilation annulee par l'utilisateur.")
                return _failure(
                    f"Echec de l'installation des outils pour '{engine_id}'"
                )

        if stop_signal and stop_signal():
            return _failure("Compilation annulee.")

        if on_stdout:
            on_stdout("Etape 2/3 : Generation de la commande de compilation...")

        # Check if we have a pre-resolved command in the engine_config (from lock)
        resolved_cmd = (engine_config or {}).get("_resolved_command")
        if resolved_cmd and isinstance(resolved_cmd, dict):
            program = str(resolved_cmd.get("program") or "")
            args = list(resolved_cmd.get("args") or [])
            engine_env = dict(resolved_cmd.get("env") or {})
            if not program:
                return _failure("Verrou invalide : commande résolue manquante.")
        elif is_rebuild:
            return _failure(
                "Mode Rebuild : Aucune commande pré-résolue trouvée dans le verrou. "
                "L'auto-mapping est désactivé lors d'un rebuild pour garantir l'intégrité."
            )
        else:
            program, args, engine_env = resolve_engine_command(
                engine_id, context, engine_config, gui=bridge
            )
    except EngineRunnerError as exc:
        return _failure(str(exc))
    except Exception as exc:
        return _failure(f"Echec de la preparation de l'engine '{engine_id}': {exc}")

    if stop_signal and stop_signal():
        return _failure("Compilation annulee.")

    # -- 3. Security hardening ------------------------------------------------
    try:
        full_env = dict(engine_env)
        full_env["ARK_WORKSPACE"] = str(workspace)
        safe_program, safe_args, safe_env = secure_command(program, args, full_env)
    except Exception as exc:
        return _failure(f"Commande de compilation non securisee bloquee : {exc}")

    # -- 4. Run with streaming ------------------------------------------------
    command = [safe_program] + safe_args

    if on_stdout:
        on_stdout("Etape 3/3 : Execution du processus de compilation...")
        on_stdout(f"  Commande : {' '.join(command)}")
        on_stdout("-" * 40)

    try:
        process = subprocess.Popen(
            command,
            cwd=str(workspace),
            env=safe_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            **hardened_popen_kwargs(),
        )
    except Exception as exc:
        return {
            "success": False,
            "return_code": None,
            "command": command,
            "error": f"Compilation failed to start: {exc}",
        }

    def _read_stream(stream, callback):
        if not stream or not callback:
            return
        for line in iter(stream.readline, ""):
            callback(line.rstrip())
        stream.close()

    stdout_thread = threading.Thread(
        target=_read_stream, args=(process.stdout, on_stdout)
    )
    stderr_thread = threading.Thread(
        target=_read_stream, args=(process.stderr, on_stderr)
    )

    stdout_thread.start()
    stderr_thread.start()

    try:
        while process.poll() is None:
            if stop_signal and stop_signal():
                from Core.process_killer import kill_process_tree

                kill_process_tree(process.pid)
                break
            time.sleep(0.05)
    finally:
        process.wait()
        stdout_thread.join()
        stderr_thread.join()

        # Compilation success hooks
        if process.returncode == 0:
            # 1. ARK opens the output directory by default
            try:
                if hasattr(engine_instance, "open_output_dir"):
                    engine_instance.open_output_dir(context.output_dir)
            except Exception:
                pass

            # 2. Call engine-specific on_success hook
            try:
                if hasattr(engine_instance, "on_success"):
                    engine_instance.on_success(bridge, str(entry_path))
            except Exception:
                pass

        return {
            "success": process.returncode == 0,
            "return_code": process.returncode,
            "command": command,
            "error": None if process.returncode == 0 else "Build failed",
        }


# -- helpers ------------------------------------------------------------------


def _failure(error: str) -> dict[str, Any]:
    return {
        "success": False,
        "return_code": None,
        "command": None,
        "stdout": None,
        "stderr": None,
        "error": error,
    }


__all__ = [
    "BuildContext",
    "EngineRunnerError",
    "resolve_engine_command",
    "run_engine_compile",
    "run_engine_compile_streaming",
]
