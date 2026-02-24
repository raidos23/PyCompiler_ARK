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

import json
import os
from pathlib import Path

import yaml
from PySide6.QtWidgets import (
    QDialog,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
)


def _read_text(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _write_text(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _safe_parse_yaml(text: str) -> bool:
    try:
        yaml.safe_load(text)
        return True
    except Exception:
        return False


def _safe_parse_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except Exception:
        return False


class AdvancedConfigEditor(QDialog):
    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self.setWindowTitle(gui.tr("Configurations avancées", "Advanced Configurations"))
        self.resize(980, 720)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        self._setup_tab_ark()
        self._setup_tab_bcasl()
        self._setup_tab_pref()

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton(gui.tr("Fermer", "Close"))
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _workspace_dir(self) -> str | None:
        return getattr(self.gui, "workspace_dir", None)

    def _setup_tab_ark(self) -> None:
        tab = QDialog(self)
        lay = QVBoxLayout(tab)
        lay.setSpacing(6)
        title = QLabel(self.gui.tr("ARK_Main_Config.yml", "ARK_Main_Config.yml"))
        lay.addWidget(title)

        self.ark_edit = QPlainTextEdit(tab)
        self.ark_edit.setPlaceholderText(
            self.gui.tr("Sélectionnez un workspace pour éditer ARK_Main_Config.yml", "Select a workspace to edit ARK_Main_Config.yml")
        )
        lay.addWidget(self.ark_edit, 1)

        btns = QHBoxLayout()
        btn_reload = QPushButton(self.gui.tr("Recharger", "Reload"))
        btn_save = QPushButton(self.gui.tr("Enregistrer", "Save"))
        btn_open = QPushButton(self.gui.tr("Ouvrir fichier…", "Open file…"))
        btns.addWidget(btn_reload)
        btns.addWidget(btn_save)
        btns.addStretch(1)
        btns.addWidget(btn_open)
        lay.addLayout(btns)

        btn_reload.clicked.connect(self._load_ark_config)
        btn_save.clicked.connect(self._save_ark_config)
        btn_open.clicked.connect(lambda: self._open_any_file(self.ark_edit))

        self.tabs.addTab(tab, self.gui.tr("ARK Config", "ARK Config"))
        self._load_ark_config()

    def _setup_tab_bcasl(self) -> None:
        tab = QDialog(self)
        lay = QVBoxLayout(tab)
        lay.setSpacing(6)
        title = QLabel(self.gui.tr("bcasl.yml", "bcasl.yml"))
        lay.addWidget(title)

        self.bcasl_edit = QPlainTextEdit(tab)
        self.bcasl_edit.setPlaceholderText(
            self.gui.tr("Sélectionnez un workspace pour éditer bcasl.yml", "Select a workspace to edit bcasl.yml")
        )
        lay.addWidget(self.bcasl_edit, 1)

        btns = QHBoxLayout()
        btn_reload = QPushButton(self.gui.tr("Recharger", "Reload"))
        btn_save = QPushButton(self.gui.tr("Enregistrer", "Save"))
        btn_open = QPushButton(self.gui.tr("Ouvrir fichier…", "Open file…"))
        btns.addWidget(btn_reload)
        btns.addWidget(btn_save)
        btns.addStretch(1)
        btns.addWidget(btn_open)
        lay.addLayout(btns)

        btn_reload.clicked.connect(self._load_bcasl_config)
        btn_save.clicked.connect(self._save_bcasl_config)
        btn_open.clicked.connect(lambda: self._open_any_file(self.bcasl_edit))

        self.tabs.addTab(tab, self.gui.tr("BCASL Config", "BCASL Config"))
        self._load_bcasl_config()

    def _setup_tab_pref(self) -> None:
        tab = QDialog(self)
        lay = QVBoxLayout(tab)
        lay.setSpacing(6)
        title = QLabel(self.gui.tr("Préférences Workspace (.ark/pref.json)", "Workspace Preferences (.ark/pref.json)"))
        lay.addWidget(title)

        self.pref_edit = QPlainTextEdit(tab)
        self.pref_edit.setPlaceholderText(
            self.gui.tr("Sélectionnez un workspace pour éditer .ark/pref.json", "Select a workspace to edit .ark/pref.json")
        )
        lay.addWidget(self.pref_edit, 1)

        btns = QHBoxLayout()
        btn_reload = QPushButton(self.gui.tr("Recharger", "Reload"))
        btn_save = QPushButton(self.gui.tr("Enregistrer", "Save"))
        btn_open = QPushButton(self.gui.tr("Ouvrir fichier…", "Open file…"))
        btns.addWidget(btn_reload)
        btns.addWidget(btn_save)
        btns.addStretch(1)
        btns.addWidget(btn_open)
        lay.addLayout(btns)

        btn_reload.clicked.connect(self._load_pref)
        btn_save.clicked.connect(self._save_pref)
        btn_open.clicked.connect(lambda: self._open_any_file(self.pref_edit))

        self.tabs.addTab(tab, self.gui.tr("Workspace Pref", "Workspace Pref"))
        self._load_pref()

    def _open_any_file(self, editor: QPlainTextEdit) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.gui.tr("Ouvrir un fichier", "Open file"), "", "*.*")
        if not path:
            return
        editor.setPlainText(_read_text(path))

    def _load_ark_config(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        path = os.path.join(ws, "ARK_Main_Config.yml")
        self.ark_edit.setPlainText(_read_text(path))

    def _save_ark_config(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        text = self.ark_edit.toPlainText()
        if text.strip() and not _safe_parse_yaml(text):
            QMessageBox.warning(self, self.gui.tr("Erreur", "Error"), self.gui.tr("YAML invalide.", "Invalid YAML."))
            return
        path = os.path.join(ws, "ARK_Main_Config.yml")
        _write_text(path, text)

    def _load_bcasl_config(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        path = os.path.join(ws, "bcasl.yml")
        self.bcasl_edit.setPlainText(_read_text(path))

    def _save_bcasl_config(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        text = self.bcasl_edit.toPlainText()
        if text.strip() and not _safe_parse_yaml(text):
            QMessageBox.warning(self, self.gui.tr("Erreur", "Error"), self.gui.tr("YAML invalide.", "Invalid YAML."))
            return
        path = os.path.join(ws, "bcasl.yml")
        _write_text(path, text)

    def _load_pref(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        path = os.path.join(ws, ".ark", "pref.json")
        self.pref_edit.setPlainText(_read_text(path))

    def _save_pref(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        text = self.pref_edit.toPlainText()
        if text.strip() and not _safe_parse_json(text):
            QMessageBox.warning(self, self.gui.tr("Erreur", "Error"), self.gui.tr("JSON invalide.", "Invalid JSON."))
            return
        path = os.path.join(ws, ".ark", "pref.json")
        _write_text(path, text)
