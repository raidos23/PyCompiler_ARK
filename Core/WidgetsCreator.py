# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

WidgetsCreator a été déplacé dans Ui/Gui/WidgetsCreator.py.
"""

from Ui.Gui.WidgetsCreator import (  # noqa: F401
    ProgressDialog,
    CompilationProcessDialog,
    InstallAuth,
    show_msgbox,
    sys_msgbox_for_installing,
    connect_to_app,
    _invoke_in_main_thread,
    _redact_secrets,
)

__all__ = [
    "ProgressDialog",
    "CompilationProcessDialog",
    "InstallAuth",
    "show_msgbox",
    "sys_msgbox_for_installing",
    "connect_to_app",
]
