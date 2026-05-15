# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""Ide-like GUI wiring layer.

This package only wires the new `Ui/Forms/ide_main_window.ui` to existing Core methods.
No business logic is implemented here.
"""

from .connections import init_ide_like_ui

__all__ = ["init_ide_like_ui"]
