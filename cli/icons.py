# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from typing import Optional
import os

from .runtime import ROOT_DIR


def _get_app_icon_path() -> Optional[str]:
    try:
        candidates = [
            os.path.join(ROOT_DIR, "images", "logo.png"),
            os.path.join(ROOT_DIR, "images", "logo.png"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
    except Exception:
        pass
    return None


def _get_window_icon_path() -> Optional[str]:
    try:
        candidates = [
            os.path.join(ROOT_DIR, "images", "logo.png"),
            os.path.join(ROOT_DIR, "images", "logo.png"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
    except Exception:
        pass
    return None


def set_app_icon(target) -> None:
    try:
        from PySide6.QtGui import QIcon

        icon_path = _get_app_icon_path()
        if icon_path:
            target.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass


def set_window_icon(target) -> None:
    try:
        from PySide6.QtGui import QIcon

        icon_path = _get_window_icon_path()
        if icon_path:
            target.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass
