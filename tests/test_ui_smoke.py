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

"""Smoke tests for GUI initialization."""

import os

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication

from Core.Gui import PyCompilerArkGui


def test_ui_init_smoke() -> None:
    """Ensure GUI can initialize in offscreen mode without crashing."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    gui = PyCompilerArkGui()
    assert gui is not None
    gui.close()
    app.quit()
