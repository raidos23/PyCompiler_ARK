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

import difflib
import json
import os
from pathlib import Path
from typing import Callable

import yaml
from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor
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


class _SimpleHighlighter(QSyntaxHighlighter):
    def __init__(self, doc, mode: str = "yaml"):
        super().__init__(doc)
        self.mode = mode
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        def _fmt(color: str, bold: bool = False) -> QTextCharFormat:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            return fmt

        key_fmt = _fmt("#9cdcfe", bold=True)
        str_fmt = _fmt("#ce9178")
        num_fmt = _fmt("#b5cea8")
        bool_fmt = _fmt("#569cd6", bold=True)
        sym_fmt = _fmt("#d4d4d4")
        com_fmt = _fmt("#6a9955")

        # Strings
        self.rules.append((QRegularExpression(r"'[^']*'"), str_fmt))
        self.rules.append((QRegularExpression(r'"[^"]*"'), str_fmt))
        # Numbers
        self.rules.append((QRegularExpression(r"\b\d+(?:\.\d+)?\b"), num_fmt))
        # Booleans/null
        self.rules.append(
            (
                QRegularExpression(
                    r"\b(true|false|null|yes|no)\b",
                    QRegularExpression.CaseInsensitiveOption,
                ),
                bool_fmt,
            )
        )
        # Symbols
        self.rules.append((QRegularExpression(r"[{}\[\]:,]"), sym_fmt))
        # Comments
        self.rules.append((QRegularExpression(r"#.*$"), com_fmt))

        if mode == "yaml":
            # YAML keys (simple: key:)
            self.rules.append(
                (QRegularExpression(r"^\s*[A-Za-z0-9_\-\.]+(?=\s*:)"), key_fmt)
            )
        else:
            # JSON keys ("key":)
            self.rules.append(
                (QRegularExpression(r'"[A-Za-z0-9_\-\.]+"(?=\s*:)'), key_fmt)
            )

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class AdvancedConfigEditor(QDialog):
    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self.setWindowTitle(
            gui.tr("Configurations avancées", "Advanced Configurations")
        )
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

    def _make_editor(self, parent) -> QPlainTextEdit:
        edit = QPlainTextEdit(parent)
        edit.setFont(QFont("Consolas", 10))
        edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return edit

    def _show_diff(self, title: str, before: str, after: str) -> None:
        diff = "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="original",
                tofile="modifié",
                lineterm="",
            )
        )
        if not diff.strip():
            QMessageBox.information(
                self, title, self.gui.tr("Aucune différence.", "No differences.")
            )
            return
        dlg = QDialog(self)
        dlg.setWindowTitle(title)
        dlg.resize(900, 600)
        lay = QVBoxLayout(dlg)
        view = QPlainTextEdit(dlg)
        view.setReadOnly(True)
        view.setFont(QFont("Consolas", 10))
        view.setPlainText(diff)
        lay.addWidget(view)
        btn = QPushButton(self.gui.tr("Fermer", "Close"))
        btn.clicked.connect(dlg.close)
        lay.addWidget(btn)
        dlg.exec()

    def _build_tab(
        self,
        label: str,
        path_getter: Callable[[], str | None],
        is_yaml: bool,
        tab_title: str,
    ) -> tuple[QDialog, QPlainTextEdit, QLabel]:
        tab = QDialog(self)
        lay = QVBoxLayout(tab)
        lay.setSpacing(6)

        title = QLabel(label)
        lay.addWidget(title)

        path_label = QLabel("")
        path_label.setStyleSheet("color: #888;")
        lay.addWidget(path_label)

        editor = self._make_editor(tab)
        lay.addWidget(editor, 1)

        _SimpleHighlighter(editor.document(), "yaml" if is_yaml else "json")

        btns = QHBoxLayout()
        btn_reload = QPushButton(self.gui.tr("Recharger", "Reload"))
        btn_save = QPushButton(self.gui.tr("Enregistrer", "Save"))
        btn_diff = QPushButton(self.gui.tr("Voir diff", "View diff"))
        btn_open = QPushButton(self.gui.tr("Ouvrir fichier…", "Open file…"))
        btns.addWidget(btn_reload)
        btns.addWidget(btn_save)
        btns.addWidget(btn_diff)
        btns.addStretch(1)
        btns.addWidget(btn_open)
        lay.addLayout(btns)

        def _load():
            path = path_getter()
            if not path:
                editor.setPlainText("")
                path_label.setText("")
                return
            path_label.setText(path)
            editor.setPlainText(_read_text(path))

        def _save():
            path = path_getter()
            if not path:
                return
            text = editor.toPlainText()
            if text.strip():
                if is_yaml and not _safe_parse_yaml(text):
                    QMessageBox.warning(
                        self,
                        self.gui.tr("Erreur", "Error"),
                        self.gui.tr("YAML invalide.", "Invalid YAML."),
                    )
                    return
                if not is_yaml and not _safe_parse_json(text):
                    QMessageBox.warning(
                        self,
                        self.gui.tr("Erreur", "Error"),
                        self.gui.tr("JSON invalide.", "Invalid JSON."),
                    )
                    return
            _write_text(path, text)

        def _diff():
            path = path_getter()
            if not path:
                return
            before = _read_text(path)
            after = editor.toPlainText()
            self._show_diff(self.gui.tr("Diff du fichier", "File diff"), before, after)

        def _open_any():
            path, _ = QFileDialog.getOpenFileName(
                self, self.gui.tr("Ouvrir un fichier", "Open file"), "", "*.*"
            )
            if not path:
                return
            editor.setPlainText(_read_text(path))
            path_label.setText(path)

        btn_reload.clicked.connect(_load)
        btn_save.clicked.connect(_save)
        btn_diff.clicked.connect(_diff)
        btn_open.clicked.connect(_open_any)

        self.tabs.addTab(tab, tab_title)
        _load()
        return tab, editor, path_label

    def _setup_tab_ark(self) -> None:
        ws = self._workspace_dir()
        self._build_tab(
            self.gui.tr("ARK_Main_Config.yml", "ARK_Main_Config.yml"),
            lambda: os.path.join(ws, "ARK_Main_Config.yml") if ws else None,
            True,
            self.gui.tr("ARK Config", "ARK Config"),
        )

    def _setup_tab_bcasl(self) -> None:
        ws = self._workspace_dir()
        self._build_tab(
            self.gui.tr("bcasl.yml", "bcasl.yml"),
            lambda: os.path.join(ws, "bcasl.yml") if ws else None,
            True,
            self.gui.tr("BCASL Config", "BCASL Config"),
        )

    def _setup_tab_pref(self) -> None:
        ws = self._workspace_dir()
        self._build_tab(
            self.gui.tr(
                "Préférences Workspace (.ark/pref.json)",
                "Workspace Preferences (.ark/pref.json)",
            ),
            lambda: os.path.join(ws, ".ark", "pref.json") if ws else None,
            False,
            self.gui.tr("Workspace Pref", "Workspace Pref"),
        )
