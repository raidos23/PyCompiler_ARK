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

"""
Universal function executor.

Provides a thin, reusable wrapper around any callable:
- structured result (success / value / error / timing)
- optional cancellation check
- optional log callback
- optional exception catching

This module intentionally knows nothing about BCASL or any other subsystem so
that it can be imported and used anywhere in PyCompiler ARK.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ExecutionResult:
    """Structured result of a function execution."""

    success: bool
    value: Any | None = None
    error: str = ""
    duration_ms: float = 0.0
    name: str = ""


def _emit_log(
    log_callback: Optional[Callable[[str], None]], message: str
) -> None:
    """Emit a log line via callback if one was provided."""
    if log_callback is None:
        return
    try:
        log_callback(message)
    except Exception:
        pass


def _check_stop(stop_requested: Optional[Callable[[], bool]]) -> bool:
    """Return True if the caller requested a stop."""
    if stop_requested is None:
        return False
    try:
        return bool(stop_requested())
    except Exception:
        return False


def executor(
    func: Callable,
    *args,
    name: Optional[str] = None,
    stop_requested: Optional[Callable[[], bool]] = None,
    log_callback: Optional[Callable[[str], None]] = None,
    catch_exceptions: bool = True,
    **kwargs,
) -> ExecutionResult:
    """Execute ``func(*args, **kwargs)`` and return a structured result.

    The executor is completely independent from BCASL or any other subsystem.
    It can be used to run any callable with uniform error handling, timing and
    logging.

    Args:
        func: The callable to execute.
        *args: Positional arguments passed to ``func``.
        name: Optional display name used in logs and in the returned result.
              Defaults to ``func.__name__``.
        stop_requested: Optional callable returning ``True`` when execution
            should be cancelled. Checked before starting and can be polled
            inside long-running ``func`` implementations if they accept it.
        log_callback: Optional callable receiving log lines.
        catch_exceptions: If ``True`` (default), exceptions are caught and
            returned as a failed ``ExecutionResult``. If ``False``, exceptions
            propagate normally.
        **kwargs: Keyword arguments passed to ``func``.

    Returns:
        ``ExecutionResult`` describing the outcome of the call.
    """
    task_name = name or getattr(func, "__name__", repr(func))

    if _check_stop(stop_requested):
        _emit_log(log_callback, f"Cancelled before start: {task_name}")
        return ExecutionResult(
            success=False,
            error="Execution cancelled before start",
            name=task_name,
        )

    _emit_log(log_callback, f"Start: {task_name}")
    start = time.perf_counter()

    try:
        value = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - start) * 1000.0
        _emit_log(
            log_callback,
            f"Success: {task_name} ({duration_ms:.1f} ms)",
        )
        return ExecutionResult(
            success=True,
            value=value,
            duration_ms=duration_ms,
            name=task_name,
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - start) * 1000.0
        error_message = str(exc)
        _emit_log(
            log_callback,
            f"Failure: {task_name} - {error_message}",
        )
        if not catch_exceptions:
            raise
        return ExecutionResult(
            success=False,
            error=error_message,
            duration_ms=duration_ms,
            name=task_name,
        )
