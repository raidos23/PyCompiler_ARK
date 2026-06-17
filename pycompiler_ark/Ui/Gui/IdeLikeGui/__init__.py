# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague

"""Couche de câblage IDE-like.

Ce package câble uniquement le fichier `Ui/Forms/ide_main_window.ui` aux méthodes
existantes de Core. Aucune logique métier ici.
"""

from .connections import init_ide_like_ui

__all__ = ["init_ide_like_ui"]
