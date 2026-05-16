# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""
Shim de compatibilité ascendante.

La classe PyCompilerArkGui a été déplacée dans Ui/Gui/Gui.py.
Ce fichier re-exporte pour ne pas casser les imports existants.
"""

from Ui.Gui.Gui import PyCompilerArkGui, get_selected_workspace  # noqa: F401

__all__ = ["PyCompilerArkGui", "get_selected_workspace"]
