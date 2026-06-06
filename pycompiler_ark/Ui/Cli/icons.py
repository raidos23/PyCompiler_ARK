from __future__ import annotations

import os
from typing import Optional

from .runtime import ROOT_DIR


def _get_logo_path() -> Optional[str]:
    try:
        candidate = os.path.join(ROOT_DIR, "images", "logo.png")
        if os.path.isfile(candidate):
            return candidate
    except Exception:
        pass
    return None


def set_app_icon(target) -> None:
    try:
        from PySide6.QtGui import QIcon

        icon_path = _get_logo_path()
        if icon_path:
            target.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass


def set_window_icon(target) -> None:
    try:
        from PySide6.QtGui import QIcon

        icon_path = _get_logo_path()
        if icon_path:
            target.setWindowIcon(QIcon(icon_path))
    except Exception:
        pass
