# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
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

"""Theme coverage tests for rarely visible Qt widgets."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from Core.UiConnection import apply_theme, _list_available_themes


REQUIRED_SELECTORS = [
    "QToolButton",
    "QCommandLinkButton",
    "QToolBox",
    "QDockWidget",
    "QCalendarWidget",
    "QDateEdit",
    "QTimeEdit",
    "QDateTimeEdit",
    "QSlider",
    "QDial",
    "QLCDNumber",
    "QToolBar",
    "QSplitter",
    "QStatusBar",
]


def test_theme_files_cover_hidden_widgets() -> None:
    themes_dir = Path("themes")
    assert themes_dir.is_dir(), "themes/ directory missing"
    missing: dict[str, list[str]] = {}
    for path in themes_dir.glob("*.qss"):
        text = path.read_text(encoding="utf-8")
        missing_selectors = [s for s in REQUIRED_SELECTORS if s not in text]
        if missing_selectors:
            missing[path.name] = missing_selectors
    assert not missing, f"Missing selectors: {missing}"


def test_apply_theme_loads_stylesheet() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])

    class Dummy:
        def __init__(self) -> None:
            self.log = []
            self.theme = "System"
            self.ui = None
            self.select_theme = None

    dummy = Dummy()
    themes = _list_available_themes()
    assert themes, "No .qss themes found"

    for name, _path in themes:
        apply_theme(dummy, name)
        css = app.styleSheet()
        assert isinstance(css, str)
        assert css.strip() != ""
