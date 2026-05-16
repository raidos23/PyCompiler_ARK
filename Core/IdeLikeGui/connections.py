# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

IdeLikeGui/connections a été déplacé dans Ui/Gui/IdeLikeGui/connections.py.
"""

from Ui.Gui.IdeLikeGui.connections import *  # noqa: F401, F403
from Ui.Gui.IdeLikeGui.connections import (  # noqa: F401
    init_ide_like_ui,
    _apply_activity_buttons_theme,
    _retranslate_ide_like_actions,
)
