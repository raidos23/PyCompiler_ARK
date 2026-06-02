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

"""
AdvancedConfigEditor — Structured GUI for project configuration (ark.yml).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from Core.AdvancedConfigEditor import validate_ark_payload
from Core.Configs import load_ark_config, write_ark_config
from Core.engine.registry import available_engines


def _apply_themed_icon(widget: QPushButton, icon_name: str, size: int = 16) -> None:
    """Applique une icône SVG thémée au widget."""
    try:
        from Ui.Gui.UiConnection import themed_svg_icon

        # icons/ is at project root, which is 4 levels up from this file
        icon_path = str(
            Path(__file__).parent.parent.parent.parent / "icons" / icon_name
        )
        icon = themed_svg_icon(icon_path, size=size)
        if icon:
            widget.setIcon(icon)
            widget.setIconSize(QSize(size, size))
    except Exception:
        pass


class AdvancedConfigEditor(QDialog):
    """Structured editor for ark.yml configuration."""

    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self.setWindowTitle(gui.tr("Configuration du projet", "Project Configuration"))
        self.resize(800, 800)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Info Header
        ws = self._workspace_dir() or ""
        ws_label = QLabel(
            self.gui.tr(
                f"Workspace: {ws}" if ws else "Aucun workspace sélectionné",
                f"Workspace: {ws}" if ws else "No workspace selected",
            )
        )
        ws_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(ws_label)

        # Scroll Area for the form
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        container = QWidget()
        scroll.setWidget(container)
        self.form_layout = QVBoxLayout(container)
        self.form_layout.setSpacing(15)
        layout.addWidget(scroll)

        # --- Section: Project ---
        group_project = QGroupBox(self.gui.tr("Projet", "Project"))
        form_project = QFormLayout(group_project)
        self.edit_name = QLineEdit()
        self.edit_version = QLineEdit()
        self.edit_entry = QLineEdit()
        btn_browse_entry = QPushButton()
        _apply_themed_icon(btn_browse_entry, "play.svg")
        btn_browse_entry.setFixedWidth(35)
        btn_browse_entry.clicked.connect(self._browse_entry)

        row_entry = QHBoxLayout()
        row_entry.addWidget(self.edit_entry)
        row_entry.addWidget(btn_browse_entry)

        form_project.addRow(
            self.gui.tr("Nom du projet:", "Project Name:"), self.edit_name
        )
        form_project.addRow(self.gui.tr("Version:", "Version:"), self.edit_version)
        form_project.addRow(self.gui.tr("Point d'entrée:", "Entry Point:"), row_entry)
        self.form_layout.addWidget(group_project)

        # --- Section: Build ---
        group_build = QGroupBox(self.gui.tr("Compilation", "Build"))
        form_build = QFormLayout(group_build)
        self.combo_engine = QComboBox()
        self.combo_engine.addItems(available_engines())

        self.edit_output = QLineEdit()
        btn_browse_output = QPushButton()
        _apply_themed_icon(btn_browse_output, "folder.svg")
        btn_browse_output.setFixedWidth(35)
        btn_browse_output.clicked.connect(self._browse_output)
        row_output = QHBoxLayout()
        row_output.addWidget(self.edit_output)
        row_output.addWidget(btn_browse_output)

        self.edit_icon = QLineEdit()
        btn_browse_icon = QPushButton()
        _apply_themed_icon(btn_browse_icon, "image.svg")
        btn_browse_icon.setFixedWidth(35)
        btn_browse_icon.clicked.connect(self._browse_icon)
        row_icon = QHBoxLayout()
        row_icon.addWidget(self.edit_icon)
        row_icon.addWidget(btn_browse_icon)

        form_build.addRow(self.gui.tr("Moteur (Engine):", "Engine:"), self.combo_engine)
        form_build.addRow(
            self.gui.tr("Dossier de sortie:", "Output Directory:"), row_output
        )
        form_build.addRow(self.gui.tr("Icône (.ico):", "Icon:"), row_icon)
        self.form_layout.addWidget(group_build)

        # --- Section: Data Mappings ---
        group_data = QGroupBox(self.gui.tr("Données (Assets)", "Data Mappings"))
        lay_data = QVBoxLayout(group_data)
        self.table_data = QTableWidget(0, 3)
        self.table_data.setHorizontalHeaderLabels(
            [
                self.gui.tr("Source (relatif)", "Source (relative)"),
                self.gui.tr("Destination (bundle)", "Destination (in bundle)"),
                self.gui.tr("Type", "Type"),
            ]
        )
        self.table_data.horizontalHeader().setStretchLastSection(False)
        self.table_data.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.table_data.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table_data.setMinimumHeight(180)
        lay_data.addWidget(self.table_data)

        row_btns_data = QHBoxLayout()
        btn_add_file = QPushButton(self.gui.tr("Fichier", "File"))
        _apply_themed_icon(btn_add_file, "file-plus.svg")
        btn_add_dir = QPushButton(self.gui.tr("Dossier", "Dir"))
        _apply_themed_icon(btn_add_dir, "folder-plus.svg")
        btn_del_data = QPushButton(self.gui.tr("Supprimer", "Remove"))
        _apply_themed_icon(btn_del_data, "trash-2.svg")

        btn_add_file.clicked.connect(self._on_add_file_data)
        btn_add_dir.clicked.connect(self._on_add_dir_data)
        btn_del_data.clicked.connect(self._remove_data_row)

        row_btns_data.addWidget(btn_add_file)
        row_btns_data.addWidget(btn_add_dir)
        row_btns_data.addWidget(btn_del_data)
        row_btns_data.addStretch()
        lay_data.addLayout(row_btns_data)
        self.form_layout.addWidget(group_data)

        # --- Section: Exclusions ---
        group_exclude = QGroupBox(self.gui.tr("Exclusions", "Exclusions"))
        lay_exclude = QVBoxLayout(group_exclude)

        lay_exclude.addWidget(
            QLabel(
                self.gui.tr(
                    "Exclusions Build (Packages Python à ignorer par le compilateur) :",
                    "Build Exclusions (Python packages to ignore by the compiler):",
                )
            )
        )
        self.edit_build_exclude = QPlainTextEdit()
        self.edit_build_exclude.setPlaceholderText("tkinter\nunittest\nrequests")
        self.edit_build_exclude.setMaximumHeight(80)
        lay_exclude.addWidget(self.edit_build_exclude)

        lay_exclude.addWidget(
            QLabel(
                self.gui.tr(
                    "Inclusions Build (Packages Python à forcer dans le bundle) :",
                    "Build Inclusions (Python packages to force into the bundle):",
                )
            )
        )
        self.edit_build_include = QPlainTextEdit()
        self.edit_build_include.setPlaceholderText("my_custom_lib\nrare_package")
        self.edit_build_include.setMaximumHeight(80)
        lay_exclude.addWidget(self.edit_build_include)

        lay_exclude.addWidget(
            QLabel(
                self.gui.tr(
                    "Exclusions Workspace (filtre GUI) :",
                    "Workspace Exclusions (GUI filter):",
                )
            )
        )
        self.edit_ws_exclude = QPlainTextEdit()
        self.edit_ws_exclude.setPlaceholderText(".git/**\nvenv/**\n__pycache__/**")
        self.edit_ws_exclude.setMaximumHeight(80)
        lay_exclude.addWidget(self.edit_ws_exclude)
        self.form_layout.addWidget(group_exclude)

        # --- Section: Plugins ---
        group_plugins = QGroupBox(self.gui.tr("Plugins", "Plugins"))
        lay_plugins = QVBoxLayout(group_plugins)
        self.check_bcasl = QCheckBox(
            self.gui.tr("Activer le pipeline BCASL", "Enable BCASL Pipeline")
        )
        lay_plugins.addWidget(self.check_bcasl)
        self.form_layout.addWidget(group_plugins)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(self.gui.tr("Annuler", "Cancel"))
        _apply_themed_icon(btn_cancel, "x.svg")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton(self.gui.tr("Enregistrer", "Save"))
        _apply_themed_icon(btn_save, "save.svg")
        btn_save.clicked.connect(self._on_save)
        btn_save.setDefault(True)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_save)
        layout.addLayout(btn_row)

        self._load_config()

    def _workspace_dir(self) -> str | None:
        return getattr(self.gui, "workspace_dir", None)

    def _load_config(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return

        try:
            config = load_ark_config(Path(ws))

            project = config.get("project", {})
            self.edit_name.setText(str(project.get("name", "")))
            self.edit_version.setText(str(project.get("version", "1.0.0")))
            self.edit_entry.setText(str(project.get("entry", "")))

            build = config.get("build", {})
            engine = build.get("engine", "pyinstaller")
            idx = self.combo_engine.findText(engine)
            if idx >= 0:
                self.combo_engine.setCurrentIndex(idx)
            else:
                # Add engine to combo if missing (e.g. custom engine not loaded yet)
                self.combo_engine.addItem(engine)
                self.combo_engine.setCurrentText(engine)

            self.edit_output.setText(str(build.get("output", "dist/")))
            self.edit_icon.setText(str(build.get("icon", "")))

            build_exclude = build.get("exclude", [])
            if isinstance(build_exclude, list):
                self.edit_build_exclude.setPlainText("\n".join(build_exclude))

            build_include = build.get("include", [])
            if isinstance(build_include, list):
                self.edit_build_include.setPlainText("\n".join(build_include))

            workspace = config.get("workspace", {})
            ws_exclude = workspace.get("exclude", [])
            if isinstance(ws_exclude, list):
                self.edit_ws_exclude.setPlainText("\n".join(ws_exclude))

            data_map = build.get("data", [])
            self.table_data.setRowCount(0)
            if isinstance(data_map, list):
                for item in data_map:
                    if isinstance(item, dict):
                        self._add_data_row(
                            item.get("source", ""),
                            item.get("destination", ""),
                            item.get("type", "dir"),
                        )

            plugins = config.get("plugins", {})
            self.check_bcasl.setChecked(bool(plugins.get("bcasl_enabled", True)))

        except Exception as e:
            QMessageBox.critical(
                self,
                self.gui.tr("Erreur", "Error"),
                self.gui.tr(
                    f"Impossible de charger ark.yml : {e}",
                    f"Failed to load ark.yml: {e}",
                ),
            )

    def _on_save(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            self.reject()
            return

        # Prepare payload
        data_map = []
        for row in range(self.table_data.rowCount()):
            src_item = self.table_data.item(row, 0)
            dst_item = self.table_data.item(row, 1)
            src = src_item.text().strip() if src_item else ""
            dst = dst_item.text().strip() if dst_item else ""

            combo = self.table_data.cellWidget(row, 2)
            m_type = "dir"
            if isinstance(combo, QComboBox):
                m_type = combo.currentText()

            if src:
                data_map.append({"source": src, "destination": dst, "type": m_type})

        config = {
            "project": {
                "name": self.edit_name.text().strip(),
                "version": self.edit_version.text().strip(),
                "entry": self.edit_entry.text().strip(),
            },
            "workspace": {
                "exclude": [
                    line.strip()
                    for line in self.edit_ws_exclude.toPlainText().splitlines()
                    if line.strip()
                ],
            },
            "build": {
                "engine": self.combo_engine.currentText(),
                "output": self.edit_output.text().strip(),
                "icon": self.edit_icon.text().strip() or None,
                "exclude": [
                    line.strip()
                    for line in self.edit_build_exclude.toPlainText().splitlines()
                    if line.strip()
                ],
                "include": [
                    line.strip()
                    for line in self.edit_build_include.toPlainText().splitlines()
                    if line.strip()
                ],
                "data": data_map,
            },
            "plugins": {
                "bcasl_enabled": self.check_bcasl.isChecked(),
            },
        }

        # Validate
        errs, warns = validate_ark_payload(config)
        if errs:
            QMessageBox.warning(
                self,
                self.gui.tr("Erreur de validation", "Validation Error"),
                "\n".join(errs),
            )
            return

        if warns:
            ans = QMessageBox.question(
                self,
                self.gui.tr("Avertissement", "Warning"),
                "\n".join(warns)
                + "\n\n"
                + self.gui.tr("Enregistrer quand même ?", "Save anyway?"),
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        try:
            write_ark_config(Path(ws), config)
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self,
                self.gui.tr("Erreur", "Error"),
                self.gui.tr(
                    f"Impossible d'enregistrer ark.yml : {e}",
                    f"Failed to save ark.yml: {e}",
                ),
            )

    def _add_data_row(
        self, source: str = "", dest: str = "", m_type: str = "dir"
    ) -> None:
        row = self.table_data.rowCount()
        self.table_data.insertRow(row)
        self.table_data.setItem(row, 0, QTableWidgetItem(source))
        self.table_data.setItem(row, 1, QTableWidgetItem(dest))

        combo = QComboBox()
        combo.addItems(["dir", "file"])
        combo.setCurrentText(m_type)
        self.table_data.setCellWidget(row, 2, combo)

    def _on_add_file_data(self) -> None:
        ws = self._workspace_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.gui.tr("Sélectionner un fichier", "Select File"),
            ws or "",
            "All Files (*)",
        )
        if path:
            rel = os.path.relpath(path, ws) if ws and path.startswith(ws) else path
            self._add_data_row(rel, rel, "file")

    def _on_add_dir_data(self) -> None:
        ws = self._workspace_dir()
        path = QFileDialog.getExistingDirectory(
            self, self.gui.tr("Sélectionner un dossier", "Select Directory"), ws or ""
        )
        if path:
            rel = os.path.relpath(path, ws) if ws and path.startswith(ws) else path
            self._add_data_row(rel, rel, "dir")

    def _remove_data_row(self) -> None:
        curr = self.table_data.currentRow()
        if curr >= 0:
            self.table_data.removeRow(curr)

    def _browse_entry(self) -> None:
        ws = self._workspace_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.gui.tr("Sélectionner le point d'entrée", "Select Entry Point"),
            ws or "",
            "Python Files (*.py *.pyw);;All Files (*)",
        )
        if path:
            if ws and path.startswith(ws):
                path = os.path.relpath(path, ws)
            self.edit_entry.setText(path)

    def _browse_output(self) -> None:
        ws = self._workspace_dir()
        path = QFileDialog.getExistingDirectory(
            self, self.gui.tr("Dossier de sortie", "Output Directory"), ws or ""
        )
        if path:
            if ws and path.startswith(ws):
                path = os.path.relpath(path, ws)
            self.edit_output.setText(path)

    def _browse_icon(self) -> None:
        ws = self._workspace_dir()
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.gui.tr("Sélectionner une icône", "Select Icon"),
            ws or "",
            "Icon Files (*.ico);;All Files (*)",
        )
        if path:
            if ws and path.startswith(ws):
                path = os.path.relpath(path, ws)
            self.edit_icon.setText(path)
