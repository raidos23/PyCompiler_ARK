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
Engine Runner — pure-Python, Qt-free compilation executor.

Source of truth for how ARK loads an engine and runs a compilation
against a BuildContext.  Both the CLI (Ui/Cli/spec_helpers.py) and the
Qt async path (MainProcess.compile_from_context) delegate to this module.

Provides:
- `resolve_engine_command` — load an engine and derive (program, args)
- `run_engine_compile`     — full synchronous compilation pipeline
"""

from __future__ import annotations

import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from Core.process_security import hardened_popen_kwargs, secure_command

# BuildContext lives in engine_sdk; imported here so callers of this module
# only need to import from Core.Compiler.
from Core.engine.build_context import BuildContext


class EngineRunnerError(RuntimeError):
    """Raised when an engine cannot be loaded or does not produce a command."""


def resolve_engine_command(
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
) -> tuple[str, list[str], dict[str, str]]:
    """
    Load *engine_id* and derive (program, args, env) for *context*.

    Args:
        engine_id:     Registered engine identifier (e.g. ``"pyinstaller"``).
        context:       BuildContext describing the project.
        engine_config: Optional per-engine config overrides.

    Returns:
        A ``(program, args, env)`` tuple ready to be passed to subprocess.

    Raises:
        EngineRunnerError: When the engine cannot be loaded, does not support
                           BuildContext builds, or returns an empty command.
    """
    try:
        import Core.engine as engines_loader
        engine = engines_loader.create(engine_id)
    except Exception as exc:
        raise EngineRunnerError(
            f"Unable to load engine '{engine_id}': {exc}"
        ) from exc

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

    Returns:
        A result dict.
    """
    # ── 1. Validate entry point ──────────────────────────────────────────────
    entry_path = workspace / Path(context.entry_point)
    if not context.entry_point or not entry_path.is_file():
        return _failure(f"Entrypoint missing or obsolete: {context.entry_point}")

    # ── 2. Resolve (program, args, env) from engine ──────────────────────────
    try:
        if on_stdout:
            on_stdout("🔨 Étape 1/3 : Vérification et installation des outils requis...")
            
        import Core.engine as engines_loader
        engine_instance = engines_loader.create(engine_id)
        
        # Ensure tools are installed (this may take time, so we do it in the thread)
        def _log(fr, en):
            if on_stdout:
                on_stdout(f"  ➡️ {en}")

        # We pass a dummy 'gui' object that supports log_i18n_level-like logging
        class LogBridge:
            def __init__(self, log_cb):
                self.log_cb = log_cb
            def tr(self, fr, en): return en # Simple fallback

        if hasattr(engine_instance, "ensure_tools_installed"):
            if not engine_instance.ensure_tools_installed(LogBridge(_log), stop_signal=stop_signal):
                if stop_signal and stop_signal():
                    return _failure("Compilation annulée par l'utilisateur.")
                return _failure(f"Échec de l'installation des outils pour '{engine_id}'")

        if stop_signal and stop_signal():
            return _failure("Compilation annulée.")

        if on_stdout:
            on_stdout("⚙️ Étape 2/3 : Génération de la commande de compilation...")

        program, args, engine_env = resolve_engine_command(engine_id, context, engine_config)
    except EngineRunnerError as exc:
        return _failure(str(exc))
    except Exception as exc:
        return _failure(f"Échec de la préparation de l'engine '{engine_id}': {exc}")

    if stop_signal and stop_signal():
        return _failure("Compilation annulée.")

    # ── 3. Security hardening ────────────────────────────────────────────────
    try:
        full_env = dict(engine_env)
        full_env["ARK_WORKSPACE"] = str(workspace)
        safe_program, safe_args, safe_env = secure_command(program, args, full_env)
    except Exception as exc:
        return _failure(f"Commande de compilation non sécurisée bloquée : {exc}")

    # ── 4. Run with streaming ────────────────────────────────────────────────
    command = [safe_program] + safe_args
    
    if on_stdout:
        on_stdout(f"🚀 Étape 3/3 : Exécution du processus de compilation...")
        on_stdout(f"  💻 Commande : {' '.join(command)}")
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

    stdout_thread = threading.Thread(target=_read_stream, args=(process.stdout, on_stdout))
    stderr_thread = threading.Thread(target=_read_stream, args=(process.stderr, on_stderr))
    
    stdout_thread.start()
    stderr_thread.start()

    try:
        while process.poll() is None:
            if stop_signal and stop_signal():
                from Core.Compiler.process_killer import kill_process_tree
                kill_process_tree(process.pid)
                break
            time.sleep(0.05)
    finally:
        process.wait()
        stdout_thread.join()
        stderr_thread.join()

    return {
        "success": process.returncode == 0,
        "return_code": process.returncode,
        "command": command,
        "error": None if process.returncode == 0 else "Build failed",
    }



# ── helpers ──────────────────────────────────────────────────────────────────

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
