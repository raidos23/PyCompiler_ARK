# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import os
from typing import Optional

from .runtime import ROOT_DIR


def _get_logo_path() -> Optional[str]:
    try:
        candidate = os.path.join(ROOT_DIR, "images", "logo3.png")
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
