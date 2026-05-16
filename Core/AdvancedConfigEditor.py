# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

AdvancedConfigEditor (dialog Qt) a été déplacé dans Ui/Gui/Dialogs/AdvancedConfigEditor.py.
La logique métier (parsing, validation, diff) est dans Core/Services/ConfigEditorService.py.
"""

from Ui.Gui.Dialogs.AdvancedConfigEditor import AdvancedConfigEditor  # noqa: F401

__all__ = ["AdvancedConfigEditor"]
