from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLineEdit, QPushButton


def add_icon_selector(layout, text: str, callback, object_name: str | None = None):
    """Add a standard icon selector button row to a layout."""
    row = QHBoxLayout()
    btn = QPushButton(text)
    if object_name:
        btn.setObjectName(object_name)
    if callback:
        btn.clicked.connect(callback)
    row.addWidget(btn)
    row.addStretch()
    layout.addLayout(row)
    return btn


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
    form, row_label: str, checkbox_label: str | None = None, object_name: str | None = None
) -> QCheckBox:
    """Add a labeled checkbox row to a QFormLayout."""
    cb = QCheckBox(checkbox_label or row_label)
    if object_name:
        cb.setObjectName(object_name)
    form.addRow(row_label, cb)
    return cb
