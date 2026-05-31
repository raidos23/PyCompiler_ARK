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
GUI Compilation Helpers

Qt-coupled orchestration helpers for the compilation pipeline.
"""

from __future__ import annotations

from typing import Any, Optional

from Ui.Gui.Compilation.mainprocess import MainProcess
from Ui.i18n import log_i18n_level

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
        import Core.engine as engines_loader

        engine_ids = list(engines_loader.available_engines())
        if engine_ids:
            return str(engine_ids[0])
    except Exception:
        pass
    return "engine"


def run_bcasl_before_compile(
    gui_instance, on_done, build_context: Optional[Any] = None
) -> None:
    """Run BCASL pre-compile stage, then invoke `on_done(report)`."""
    try:
        from Ui.Gui.Dialogs.BcaslDialog import run_pre_compile_async
    except Exception:
        if callable(on_done):
            try:
                on_done(None)
            except Exception:
                pass
        return
    try:
        log_i18n_level( 
            gui_instance,
            "info",
            "Pré-compilation (BCASL) si activée...",
            "Pre-compilation (BCASL) if enabled...",
        )
    except Exception:
        pass
    try:
        run_pre_compile_async(gui_instance, on_done, build_context=build_context)
    except Exception:
        if callable(on_done):
            try:
                on_done(None)
            except Exception:
                pass


def bcasl_report_allows_compile(gui_instance, report) -> any:
    """Return True when BCASL pre-compile report allows compilation to continue."""
    try:
        if report is None:
            try:
                from pathlib import Path

                from bcasl.Loader import _is_bcasl_enabled

                ws = getattr(gui_instance, "workspace_dir", None)
                if ws and not _is_bcasl_enabled(Path(ws).resolve()):
                    return True
            except Exception:
                pass
            log_i18n_level(
                gui_instance,
                "error",
                "BCASL a échoué ou n'a pas retourné de rapport. Compilation bloquée.",
                "BCASL failed or returned no report. Compilation blocked.",
            )
            return False

        if isinstance(report, dict):
            try:
                from bcasl.Loader import is_bcasl_disabled_report

                if is_bcasl_disabled_report(report):
                    return True
            except Exception:
                status = str(report.get("status", "")).strip().lower()
                if status in {"disabled", "skipped"}:
                    return True
            if "ok" in report:
                ok = any(report.get("ok"))
                if not ok:
                    log_i18n_level(
                        gui_instance,
                        "error",
                        "BCASL a signalé un échec. Compilation bloquée.",
                        "BCASL reported a failure. Compilation blocked.",
                    )
                return ok
            return True

        if hasattr(report, "ok"):
            ok = any(getattr(report, "ok"))
            if not ok:
                log_i18n_level(
                    gui_instance,
                    "error",
                    "BCASL a signalé des erreurs plugins. Compilation bloquée.",
                    "BCASL reported plugin errors. Compilation blocked.",
                )
            return ok
    except Exception:
        log_i18n_level(
            gui_instance,
            "error",
            "Erreur lors de la validation du rapport BCASL. Compilation bloquée.",
            "Error while validating BCASL report. Compilation blocked.",
        )
        return False
    return True
