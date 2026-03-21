# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations


def unload_all_engines():
    from EngineLoader import unload_all

    return unload_all()


def available_engine_ids() -> list[str]:
    from EngineLoader import available_engines

    return list(available_engines())


def launch_bcasl_gui(workspace_dir: str | None = None) -> int:
    from .launchers import launch_bcasl_standalone

    return launch_bcasl_standalone(workspace_dir)


def launch_engines_gui(workspace_dir: str | None = None) -> int:
    from .launchers import launch_engines_only_standalone

    return launch_engines_only_standalone(workspace_dir)


def launch_main_gui(
    no_splash: bool = False, ide_gui: bool = False, classic_gui: bool = False
) -> int:
    from .launchers import launch_main_application

    return launch_main_application(
        no_splash=no_splash,
        ide_gui=ide_gui,
        classic_gui=classic_gui,
    )
