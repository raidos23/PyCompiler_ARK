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
from pathlib import Path
from typing import Any

from Core.process_security import hardened_popen_kwargs, secure_command

# BuildContext lives in engine_sdk; imported here so callers of this module
# only need to import from Core.Compiler.
from engine_sdk.build_context import BuildContext


class EngineRunnerError(RuntimeError):
    """Raised when an engine cannot be loaded or does not produce a command."""


def resolve_engine_command(
    engine_id: str,
    context: BuildContext,
    engine_config: dict[str, Any] | None = None,
) -> tuple[str, list[str]]:
    """
    Load *engine_id* and derive the (program, args) pair for *context*.

    Args:
        engine_id:     Registered engine identifier (e.g. ``"pyinstaller"``).
        context:       BuildContext describing the project.
        engine_config: Optional per-engine config overrides.

    Returns:
        A ``(program, args)`` tuple ready to be passed to subprocess.

    Raises:
        EngineRunnerError: When the engine cannot be loaded, does not support
                           BuildContext builds, or returns an empty command.
    """
    try:
        import EngineLoader as engines_loader
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
        resolved = engine.program_and_args_from_context(context)
    except NotImplementedError as exc:
        raise EngineRunnerError(
            f"Engine '{engine_id}' does not support BuildContext builds"
        ) from exc
    except Exception as exc:
        raise EngineRunnerError(
            f"Engine '{engine_id}' failed to build command: {exc}"
        ) from exc

    if not resolved:
        raise EngineRunnerError(f"Engine '{engine_id}' returned no command")

    program, args = resolved
    return str(program), list(args)


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
        A result dict with the following keys:

        ``success`` (bool)
            Whether ``returncode == 0``.
        ``return_code`` (int | None)
            Process return code, or ``None`` when the process never started.
        ``command`` (list[str] | None)
            The resolved, security-hardened command list, or ``None`` on early
            failure.
        ``stdout`` (str | None)
            Captured standard output.
        ``stderr`` (str | None)
            Captured standard error.
        ``error`` (str | None)
            Human-readable error message, or ``None`` on success.
    """
    # ── 1. Validate entry point ──────────────────────────────────────────────
    entry_path = workspace / Path(context.entry_point)
    if not context.entry_point or not entry_path.is_file():
        return _failure(
            f"Entrypoint missing or obsolete: {context.entry_point}"
        )

    # ── 2. Resolve (program, args) from engine ───────────────────────────────
    try:
        program, args = resolve_engine_command(engine_id, context, engine_config)
    except EngineRunnerError as exc:
        return _failure(str(exc))

    # ── 3. Security hardening ────────────────────────────────────────────────
    try:
        safe_program, safe_args, safe_env = secure_command(
            program, args, {"ARK_WORKSPACE": str(workspace)}
        )
    except Exception as exc:
        return _failure(f"Unsafe compile command blocked: {exc}")

    # ── 4. Run ───────────────────────────────────────────────────────────────
    command = [safe_program] + safe_args
    try:
        completed = subprocess.run(
            command,
            cwd=str(workspace),
            env=safe_env,
            capture_output=True,
            text=True,
            **hardened_popen_kwargs(),
        )
    except Exception as exc:
        return {
            "success": False,
            "return_code": None,
            "command": command,
            "stdout": None,
            "stderr": None,
            "error": f"Compilation failed to start: {exc}",
        }

    return {
        "success": completed.returncode == 0,
        "return_code": completed.returncode,
        "command": command,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "error": (
            None
            if completed.returncode == 0
            else (completed.stderr.strip() or "Build failed")
        ),
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
]
