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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class HelloTab(QWidget):
    def __init__(self, gui, parent=None):
        super().__init__(parent)
        self.gui = gui
        self.setObjectName("tab_hello")
        self.init_ui()
        if hasattr(self.gui, "register_language_refresh"):
            try:
                self.gui.register_language_refresh(self.retranslate_ui)
            except Exception:
                pass

    def init_ui(self):
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Title Label
        self.title_label = QLabel()
        self.title_label.setObjectName("welcome_title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setStyleSheet(
            "font-size: 16pt; font-weight: bold; color: #ffffff;"
        )

        # Description Label
        self.desc_label = QLabel()
        self.desc_label.setObjectName("welcome_desc")
        self.desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(
            "font-size: 9.5pt; color: #a0a0a0; max-width: 500px;"
        )

        # Guide Box (Frame)
        self.guide_box = QFrame()
        self.guide_box.setStyleSheet(
            "QFrame {"
            "  background-color: #2b2b2b;"
            "  border: 1px solid #3d3d3d;"
            "  border-radius: 6px;"
            "  margin-top: 10px;"
            "}"
        )
        guide_layout = QVBoxLayout(self.guide_box)
        guide_layout.setContentsMargins(15, 15, 15, 15)
        guide_layout.setSpacing(6)

        self.guide_title = QLabel()
        self.guide_title.setObjectName("welcome_guide_title")
        self.guide_title.setStyleSheet(
            "font-size: 10pt; font-weight: bold; color: #ffcc00; border: none;"
        )
        self.guide_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.guide_desc = QLabel()
        self.guide_desc.setObjectName("welcome_guide")
        self.guide_desc.setStyleSheet(
            "font-size: 9pt; color: #d4d4d4; border: none;"
        )
        self.guide_desc.setWordWrap(True)
        self.guide_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)

        guide_layout.addWidget(self.guide_title)
        guide_layout.addWidget(self.guide_desc)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Spacer to push elements into center-top vertical layout
        layout.addSpacing(10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.desc_label)
        layout.addWidget(self.guide_box)
        layout.addSpacing(10)
        layout.addLayout(btn_layout)
        layout.addStretch()

        self.retranslate_ui()

    def retranslate_ui(self):
        from ...Ui.i18n import translate

        ctx = self.gui.id if hasattr(self.gui, "id") else "ui"

        t_title = translate(
            ctx, "welcome_title", "Bienvenue dans PyCompiler ARK"
        )
        t_desc = translate(
            ctx,
            "welcome_desc",
            "Un outil de compilation et d'empaquetage universel pour vos applications Python.",
        )
        t_guide_title = translate(
            ctx,
            "welcome_guide_title",
            "Aucun moteur de compilation disponible",
        )
        t_guide_desc = translate(
            ctx,
            "welcome_guide",
            "Veuillez installer un moteur de compilation pour commencer.",
        )

        self.title_label.setText(t_title)
        self.desc_label.setText(t_desc)
        self.guide_title.setText(t_guide_title)
        self.guide_desc.setText(t_guide_desc)

    def destroy(self, destroyWindow=True, destroySubWindows=True):
        if hasattr(self.gui, "unregister_language_refresh"):
            try:
                self.gui.unregister_language_refresh(self.retranslate_ui)
            except Exception:
                pass
        super().destroy(destroyWindow, destroySubWindows)


def create_hello_tab(gui) -> HelloTab:
    """Create a new HelloTab widget for the GUI."""
    return HelloTab(gui)
