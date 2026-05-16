# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

UiConnection a été déplacé dans Ui/Gui/UiConnection.py.
"""

from Ui.Gui.UiConnection import *  # noqa: F401, F403
from Ui.Gui.UiConnection import (  # noqa: F401
    init_ui,
    apply_theme,
    show_theme_dialog,
    themed_svg_icon,
    _is_qss_dark,
    _apply_button_icons,
    _apply_initial_theme,
    _auto_resize_for_screen,
    _connect_dialogs_to_app,
    _refresh_log_palette,
    _connect_signals,
    _detect_system_color_scheme,
)
