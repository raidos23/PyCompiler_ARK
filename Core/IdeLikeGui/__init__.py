# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

IdeLikeGui a été déplacé dans Ui/Gui/IdeLikeGui/.
"""

from Ui.Gui.IdeLikeGui import init_ide_like_ui  # noqa: F401

__all__ = ["init_ide_like_ui"]
