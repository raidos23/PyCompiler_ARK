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

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QPushButton


def add_icon_selector(
    layout,
    text: str,
    callback,
    object_name: str | None = None,
    path_object_name: str | None = None,
    path_placeholder: str | None = None,
):
    """Add a standard icon selector button row to a layout."""
    row = QHBoxLayout()
    btn = QPushButton(text)
    if object_name:
        btn.setObjectName(object_name)
    if callback:
        btn.clicked.connect(callback)
    path_input = QLineEdit()
    if path_object_name:
        path_input.setObjectName(path_object_name)
    if path_placeholder:
        path_input.setPlaceholderText(path_placeholder)
    path_input.setClearButtonEnabled(True)
    row.addWidget(btn)
    row.addWidget(path_input, 1)
    layout.addLayout(row)
    return btn, path_input


def add_output_dir(
    layout, placeholder: str = "", object_name: str | None = None
) -> QLineEdit:
    """Add a standard output directory input row to a layout."""
    row = QHBoxLayout()
    line = QLineEdit()
    if object_name:
        line.setObjectName(object_name)
    if placeholder:
        line.setPlaceholderText(placeholder)
    row.addWidget(line)
    layout.addLayout(row)
    return line


def add_form_checkbox(
    form,
    row_label: str,
    checkbox_label: str | None = None,
    object_name: str | None = None,
) -> QCheckBox:
    """Add a labeled checkbox row to a QFormLayout."""
    cb = QCheckBox(checkbox_label or row_label)
    if object_name:
        cb.setObjectName(object_name)
    form.addRow(row_label, cb)
    return cb
