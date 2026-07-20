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
GUI Compilation Helpers

Qt-coupled orchestration helpers for the compilation pipeline.
"""

from __future__ import annotations

from typing import Any, Optional

from pycompiler_ark.Ui import output
from .mainprocess import MainProcess

# Singleton MainProcess (initialised on first use)
_main_process: Optional[MainProcess] = None


def get_main_process() -> MainProcess:
    """Return the singleton `MainProcess` instance, creating it on demand."""
    global _main_process
    if _main_process is None:
        _main_process = MainProcess()
    return _main_process


def resolve_default_engine_id() -> str:
    """Resolve a default engine dynamically from the registered engines."""
    try:
        import pycompiler_ark.Core.engine as engines_loader

        engine_ids = list(engines_loader.available_engines())
        if engine_ids:
            return str(engine_ids[0])
    except Exception:
        pass
    return "engine"


def run_bcasl_before_compile(
    gui_instance,
    on_done,
    build_context: Optional[Any] = None,
    ark_config: Optional[dict] = None,
) -> None:
    """
    Run BCASL pre-compile stage, then invoke `on_done(report)`.
    Optimized: Checks activation state before launching the async thread.
    """
    try:
        from pathlib import Path

        from ....bcasl.Loader import BCASL_DISABLED_REPORT, _is_bcasl_enabled
        from ..Dialogs.BcaslDialog import run_pre_compile_async
    except Exception:
        if callable(on_done):
            on_done(None)
        return

    ws = getattr(gui_instance, "workspace_dir", None)
    if not ws:
        if callable(on_done):
            on_done(None)
        return

    # Optimization: Short-circuit if BCASL is disabled to avoid thread overhead
    enabled = True
    try:
        if ark_config:
            enabled = bool(ark_config.get("plugins", {}).get("bcasl_enabled", True))
        else:
            enabled = _is_bcasl_enabled(Path(ws))
    except Exception:
        pass

    if not enabled:
        try:
            output.info(
                (
                    "BCASL désactivé dans ark.yml. Exécution ignorée.",
                    "BCASL disabled in ark.yml. Skipping execution.",
                ),
                gui=gui_instance,
            )
        except Exception:
            pass
        if callable(on_done):
            on_done(dict(BCASL_DISABLED_REPORT))
        return

    try:
        output.info(
            ("Pré-compilation (BCASL)...", "Pre-compilation (BCASL)..."),
            gui=gui_instance,
        )
    except Exception:
        pass

    try:
        run_pre_compile_async(gui_instance, on_done, build_context=build_context)
    except Exception:
        if callable(on_done):
            on_done(None)


def bcasl_report_allows_compile(gui_instance, report) -> bool:
    """
    Return True when BCASL pre-compile report allows compilation to continue.
    Robustly handles dicts, objects, and lists.
    """
    try:
        if report is None:
            # Fallback check if the thread returned nothing
            try:
                from pathlib import Path

                from ....bcasl.Loader import _is_bcasl_enabled

                ws = getattr(gui_instance, "workspace_dir", None)
                if ws and not _is_bcasl_enabled(Path(ws).resolve()):
                    return True
            except Exception:
                pass
            return False

        # 1. Handle Disabled Report (Dict)
        if isinstance(report, dict):
            try:
                from ....bcasl.Loader import is_bcasl_disabled_report

                if is_bcasl_disabled_report(report):
                    return True
            except Exception:
                pass

            # Simple check for 'ok' key
            if "ok" in report:
                res = report.get("ok")
                return (
                    bool(res) if not isinstance(res, (list, tuple, set)) else all(res)
                )
            return True

        # 2. Handle ExecutionReport object
        if hasattr(report, "ok"):
            ok_val = getattr(report, "ok")
            # If it's a property returning bool, use it directly
            if isinstance(ok_val, bool):
                return ok_val
            # If it's a list (legacy/compat), check all
            try:
                return all(ok_val)
            except Exception:
                return bool(ok_val)

        # 3. Handle List of Results
        if isinstance(report, (list, tuple)):
            return all(getattr(item, "success", True) for item in report)

    except Exception:
        try:
            output.error(
                (
                    "Erreur lors de la validation du rapport BCASL. Compilation bloquée.",
                    "Error while validating BCASL report. Compilation blocked.",
                ),
                gui=gui_instance,
            )
        except Exception:
            pass
        return False

    return True
