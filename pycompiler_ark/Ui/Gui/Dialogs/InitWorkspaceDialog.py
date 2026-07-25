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

"""
InitWorkspaceDialog — GUI layer for project initialization.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from pycompiler_ark.Core.deps_analyser import collect_internal_modules

from ...Cli.helpers import init_workspace


class InitWorkspaceDialog(QDialog):
    """Dialog to initialize a new ARK workspace."""

    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self.setWindowTitle(gui.tr("Initialiser le projet", "init_project_title"))
        self.resize(500, 300)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Form
        form = QFormLayout()

        # Entry Point
        self.edit_entry = QLineEdit()
        self.edit_entry.setPlaceholderText("main.py")
        btn_browse = QPushButton("...")
        btn_browse.setFixedWidth(40)
        btn_browse.clicked.connect(self._browse_entry)

        row_entry = QHBoxLayout()
        row_entry.addWidget(self.edit_entry)
        row_entry.addWidget(btn_browse)

        form.addRow(self.gui.tr("Point d'entrée :", "init_project_entry"), row_entry)

        # Options
        self.chk_reqs = QCheckBox(
            self.gui.tr("Générer requirements.txt", "init_project_gen_reqs")
        )
        self.chk_reqs.setChecked(True)
        form.addRow("", self.chk_reqs)

        self.chk_venv = QCheckBox(
            self.gui.tr(
                "Créer un environnement virtuel (venv)", "init_project_create_venv"
            )
        )
        self.chk_venv.setChecked(False)
        form.addRow("", self.chk_venv)

        self.chk_install = QCheckBox(
            self.gui.tr("Installer les dépendances", "init_project_install_reqs")
        )
        self.chk_install.setChecked(False)
        self.chk_install.setEnabled(False)
        self.chk_venv.toggled.connect(self.chk_install.setEnabled)
        form.addRow("", self.chk_install)

        self.chk_apply_internal = QCheckBox(
            self.gui.tr(
                "Appliquer les modules internes",
                "Apply internal modules",
            )
        )
        self.chk_apply_internal.setChecked(False)
        form.addRow("", self.chk_apply_internal)

        layout.addLayout(form)

        # Note
        note = QLabel(
            self.gui.tr(
                "Note : Cela va créer un fichier ark.yml et configurer la structure du projet.",
                "init_project_note",
            )
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(note)

        scan_note = QLabel(
            self.gui.tr(
                "Si activé, les modules internes seront proposés pour build.include avant écriture.",
                "If enabled, internal modules will be proposed for build.include before writing.",
            )
        )
        scan_note.setWordWrap(True)
        scan_note.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(scan_note)

        layout.addStretch()

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton(self.gui.tr("Annuler", "action_cancel"))
        btn_cancel.clicked.connect(self.reject)

        self.btn_init = QPushButton(self.gui.tr("Initialiser", "action_init_project"))
        self.btn_init.setDefault(True)
        self.btn_init.clicked.connect(self._on_init)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(self.btn_init)
        layout.addLayout(btn_row)

    def _browse_entry(self):
        ws = getattr(self.gui, "workspace_dir", os.getcwd())
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.gui.tr("Choisir le point d'entrée", "Choose entrypoint"),
            ws,
            "Python Files (*.py)",
        )
        if path:
            try:
                rel = os.path.relpath(path, ws)
                if rel.startswith(".."):
                    self.edit_entry.setText(path)
                else:
                    self.edit_entry.setText(rel)
            except Exception:
                self.edit_entry.setText(path)

    def _on_init(self):
        ws = getattr(self.gui, "workspace_dir", None)
        if not ws:
            QMessageBox.warning(
                self,
                "Error",
                self.gui.tr("Aucun workspace sélectionné.", "msg_no_workspace_text"),
            )
            return

        entry = self.edit_entry.text().strip()
        if not entry:
            QMessageBox.warning(
                self,
                "Error",
                self.gui.tr(
                    "Veuillez spécifier un point d'entrée.",
                    "Please specify an entry point.",
                ),
            )
            return

        self.btn_init.setEnabled(False)
        try:
            apply_internal = bool(self.chk_apply_internal.isChecked())
            effective_auto_confirm = False
            internal_modules = []
            if apply_internal:
                try:
                    internal_modules = sorted(
                        collect_internal_modules(str(Path(ws))),
                        key=lambda item: item.lower(),
                    )
                except Exception:
                    internal_modules = []

                if internal_modules:
                    title = self.gui.tr(
                        "Confirmer l'application interne",
                        "Confirm internal apply",
                    )
                    message = self.gui.tr(
                        "Modules internes à appliquer :\n{modules}\n\nLes ajouter à build.include ?",
                        "Internal modules to apply:\n{modules}\n\nAdd them to build.include?",
                    ).format(
                        modules="\n".join(f"- {item}" for item in internal_modules)
                    )
                    choice = QMessageBox.question(
                        self,
                        title,
                        message,
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No,
                    )
                    if choice == QMessageBox.StandardButton.No:
                        apply_internal = False
                    else:
                        effective_auto_confirm = True
                else:
                    effective_auto_confirm = True

            payload = init_workspace(
                cwd=Path(ws),
                entry=entry,
                generate_requirements=self.chk_reqs.isChecked(),
                with_venv=self.chk_venv.isChecked(),
                install_requirements=self.chk_install.isChecked(),
                apply_internal=apply_internal,
                auto_confirm=effective_auto_confirm,
            )

            msg = self.gui.tr("Projet initialisé avec succès !", "init_project_success")
            QMessageBox.information(self, "Success", msg)

            # Refresh GUI
            if hasattr(self.gui, "apply_workspace_selection"):
                self.gui.apply_workspace_selection(ws)

            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Initialization failed: {e}")
            self.btn_init.setEnabled(True)


def open_init_workspace_dialog(gui):
    """Helper to open the init dialog."""
    workspace_dir = getattr(gui, "workspace_dir", None)
    if not workspace_dir:
        QMessageBox.warning(
            gui,
            gui.tr("Attention", "Warning"),
            gui.tr(
                "Veuillez d'abord sélectionner un dossier workspace.",
                "Please select a workspace folder first.",
            ),
        )
        return

    dlg = InitWorkspaceDialog(gui)
    dlg.exec()
