# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

UiFeatures a été déplacé dans Ui/Gui/UiFeatures.py.
"""

from Ui.Gui.UiFeatures import UiFeatures  # noqa: F401

__all__ = ["UiFeatures"]
