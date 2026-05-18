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
AdvancedConfigEditor — dialog Qt pour l'édition des fichiers de configuration avancés.

Toute la logique métier (parsing, validation, diff) est déléguée à
Core.Services.ConfigEditorService. Ce module ne contient que du code Qt.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
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
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
)

from Services.ConfigEditorService import (
    read_text,
    write_text,
    parse_text,
    format_text,
    render_colored_diff,
    flatten_keys,
    validate_payload,
    make_default_content,
)


# ---------------------------------------------------------------------------
# Highlighters Qt
# ---------------------------------------------------------------------------


class _SimpleHighlighter(QSyntaxHighlighter):
    """Colorisation syntaxique simple pour YAML et JSON."""

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

        self.rules.append((QRegularExpression(r"'[^']*'"), str_fmt))
        self.rules.append((QRegularExpression(r'"[^"]*"'), str_fmt))
        self.rules.append((QRegularExpression(r"\b\d+(?:\.\d+)?\b"), num_fmt))
        self.rules.append(
            (
                QRegularExpression(
                    r"\b(true|false|null|yes|no)\b",
                    QRegularExpression.CaseInsensitiveOption,
                ),
                bool_fmt,
            )
        )
        self.rules.append((QRegularExpression(r"[{}\[\]:,]"), sym_fmt))
        self.rules.append((QRegularExpression(r"#.*$"), com_fmt))

        if mode == "yaml":
            self.rules.append(
                (QRegularExpression(r"^\s*[A-Za-z0-9_\-\.]+(?=\s*:)"), key_fmt)
            )
        else:
            self.rules.append(
                (QRegularExpression(r'"[A-Za-z0-9_\-\.]+"(?=\s*:)'), key_fmt)
            )

    def highlightBlock(self, text: str) -> None:
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class _DiffHighlighter(QSyntaxHighlighter):
    """Colorisation visuelle pour les aperçus de diff."""

    _EDITOR_BG = "#111111"

    def __init__(self, doc: QTextDocument):
        super().__init__(doc)

        self._insert_fmt = QTextCharFormat()
        self._insert_fmt.setBackground(QColor("#123222"))

        self._delete_fmt = QTextCharFormat()
        self._delete_fmt.setBackground(QColor("#3a1717"))

        self._hint_fmt = QTextCharFormat()
        self._hint_fmt.setForeground(QColor("#8a8a8a"))
        self._hint_fmt.setFontItalic(True)

        self._equal_fmt = QTextCharFormat()
        self._equal_fmt.setForeground(QColor("#d8d8d8"))

        self._marker_fmt = QTextCharFormat()
        self._marker_fmt.setForeground(QColor(self._EDITOR_BG))
        self._marker_fmt.setBackground(QColor(self._EDITOR_BG))

    @staticmethod
    def _apply_content_format(
        highlighter: "_DiffHighlighter", text: str, fmt: QTextCharFormat
    ) -> None:
        if len(text) <= 2:
            return
        highlighter.setFormat(2, len(text) - 2, fmt)

    def highlightBlock(self, text: str) -> None:
        if text.startswith("A "):
            self._apply_content_format(self, text, self._insert_fmt)
            self.setFormat(0, 2, self._marker_fmt)
        elif text.startswith("D "):
            self._apply_content_format(self, text, self._delete_fmt)
            self.setFormat(0, 2, self._marker_fmt)
        elif text.startswith("= "):
            self._apply_content_format(self, text, self._equal_fmt)
            self.setFormat(0, 2, self._marker_fmt)
        elif text == "...":
            self.setFormat(0, len(text), self._hint_fmt)


# ---------------------------------------------------------------------------
# Dialog principal
# ---------------------------------------------------------------------------


class AdvancedConfigEditor(QDialog):
    """Dialog Qt d'édition avancée des fichiers de configuration ARK."""

    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self._tab_states: list[dict[str, Any]] = []
        self.setWindowTitle(
            gui.tr("Configurations avancées", "Advanced Configurations")
        )
        self.resize(1120, 760)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        ws = self._workspace_dir() or ""
        ws_label = QLabel(
            self.gui.tr(
                f"Workspace: {ws}" if ws else "Aucun workspace sélectionné",
                f"Workspace: {ws}" if ws else "No workspace selected",
            )
        )
        ws_label.setStyleSheet("color: #888;")
        layout.addWidget(ws_label)

        top_actions = QHBoxLayout()
        self.btn_validate_all = QPushButton(self.gui.tr("Valider tout", "Validate all"))
        self.btn_save_all = QPushButton(self.gui.tr("Tout enregistrer", "Save all"))
        self.btn_reload_all = QPushButton(self.gui.tr("Tout recharger", "Reload all"))
        self.btn_format_tab = QPushButton(self.gui.tr("Formater onglet", "Format tab"))
        top_actions.addWidget(self.btn_validate_all)
        top_actions.addWidget(self.btn_save_all)
        top_actions.addWidget(self.btn_reload_all)
        top_actions.addWidget(self.btn_format_tab)
        top_actions.addStretch(1)
        layout.addLayout(top_actions)

        self.tabs = QTabWidget(self)
        layout.addWidget(self.tabs)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #888;")
        layout.addWidget(self.status_label)

        self._setup_tab_ark()
        self._setup_tab_bcasl()
        self._setup_tab_pref()
        self._setup_engine_tabs()

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_close = QPushButton(gui.tr("Fermer", "Close"))
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

        self.btn_validate_all.clicked.connect(self._validate_all_tabs)
        self.btn_save_all.clicked.connect(self._save_all_tabs)
        self.btn_reload_all.clicked.connect(self._reload_all_tabs)
        self.btn_format_tab.clicked.connect(self._format_current_tab)
        self.tabs.currentChanged.connect(self._on_current_tab_changed)
        self._refresh_global_status()

    # -------------------------------------------------------------------------
    # Helpers UI
    # -------------------------------------------------------------------------

    def _workspace_dir(self) -> str | None:
        return getattr(self.gui, "workspace_dir", None)

    def _make_editor(self, parent) -> QPlainTextEdit:
        edit = QPlainTextEdit(parent)
        edit.setFont(QFont("Consolas", 10))
        edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return edit

    def _show_diff(self, title: str, before: str, after: str) -> None:
        diff = render_colored_diff(before, after)
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
        view.setStyleSheet(
            "QPlainTextEdit { background-color: #111111; color: #dddddd; }"
        )
        _DiffHighlighter(view.document())
        lay.addWidget(view)
        btn = QPushButton(self.gui.tr("Fermer", "Close"))
        btn.clicked.connect(dlg.close)
        lay.addWidget(btn)
        dlg.exec()

    # -------------------------------------------------------------------------
    # Gestion d'état des onglets
    # -------------------------------------------------------------------------

    def _set_tab_dirty(self, state: dict[str, Any], dirty: bool) -> None:
        if state.get("dirty") == dirty:
            return
        state["dirty"] = dirty
        idx = self.tabs.indexOf(state["tab"])
        base = state.get("tab_title", "")
        if idx >= 0:
            self.tabs.setTabText(idx, ("* " + base) if dirty else base)
        self._refresh_global_status()

    def _refresh_global_status(self) -> None:
        if not hasattr(self, "status_label") or self.status_label is None:
            return
        dirty_count = sum(1 for s in self._tab_states if s.get("dirty"))
        if dirty_count:
            self.status_label.setText(
                self.gui.tr(
                    f"{dirty_count} onglet(s) modifié(s).",
                    f"{dirty_count} modified tab(s).",
                )
            )
        else:
            self.status_label.setText(self.gui.tr("Tout est sauvegardé.", "All saved."))

    def _update_outline(self, state: dict[str, Any]) -> None:
        text = state["editor"].toPlainText()
        is_yaml = bool(state["is_yaml"])
        ok, data, err = parse_text(text, is_yaml)
        outline: QListWidget = state["outline"]
        diagnostics: QLabel = state["diagnostics"]
        outline.clear()

        if not ok:
            diagnostics.setText(
                self.gui.tr(f"Erreur de parsing: {err}", f"Parse error: {err}")
            )
            diagnostics.setStyleSheet("color: #d9534f;")
            return

        keys = flatten_keys(data)
        for key in keys:
            QListWidgetItem(key, outline)

        errs, warns = validate_payload(state["file_id"], data)
        if errs:
            diagnostics.setText(
                self.gui.tr(
                    "Erreurs:\n- " + "\n- ".join(errs),
                    "Errors:\n- " + "\n- ".join(errs),
                )
            )
            diagnostics.setStyleSheet("color: #d9534f;")
        elif warns:
            diagnostics.setText(
                self.gui.tr(
                    "Avertissements:\n- " + "\n- ".join(warns),
                    "Warnings:\n- " + "\n- ".join(warns),
                )
            )
            diagnostics.setStyleSheet("color: #f0ad4e;")
        else:
            diagnostics.setText(self.gui.tr("Validation OK.", "Validation OK."))
            diagnostics.setStyleSheet("color: #5cb85c;")

    def _validate_one_tab(self, state: dict[str, Any], popup: bool = False) -> bool:
        text = state["editor"].toPlainText()
        ok, data, err = parse_text(text, bool(state["is_yaml"]))
        if not ok:
            if popup:
                QMessageBox.warning(
                    self,
                    self.gui.tr("Erreur", "Error"),
                    self.gui.tr(f"Format invalide:\n{err}", f"Invalid format:\n{err}"),
                )
            self._update_outline(state)
            return False
        errs, warns = validate_payload(state["file_id"], data)
        self._update_outline(state)
        if errs and popup:
            QMessageBox.warning(
                self,
                self.gui.tr("Erreur", "Error"),
                self.gui.tr(
                    "Erreurs de validation:\n- " + "\n- ".join(errs),
                    "Validation errors:\n- " + "\n- ".join(errs),
                ),
            )
        elif warns and popup:
            QMessageBox.information(
                self,
                self.gui.tr("Avertissement", "Warning"),
                self.gui.tr(
                    "Validation avec avertissements:\n- " + "\n- ".join(warns),
                    "Validation with warnings:\n- " + "\n- ".join(warns),
                ),
            )
        return not errs

    def _jump_to_search(self, state: dict[str, Any], backward: bool = False) -> None:
        needle = state["search"].text().strip()
        if not needle:
            return
        editor = state["editor"]
        flags = (
            QTextDocument.FindFlag.FindBackward
            if backward
            else QTextDocument.FindFlag(0)
        )
        if editor.find(needle, flags):
            return
        cursor = editor.textCursor()
        cursor.movePosition(
            cursor.MoveOperation.End if backward else cursor.MoveOperation.Start
        )
        editor.setTextCursor(cursor)
        editor.find(needle, flags)

    def _on_current_tab_changed(self, _index: int) -> None:
        self._refresh_global_status()

    def _reload_all_tabs(self) -> None:
        for state in self._tab_states:
            state["reload"]()
        self._refresh_global_status()

    def _save_all_tabs(self) -> None:
        for state in self._tab_states:
            state["save"]()
        self._refresh_global_status()

    def _validate_all_tabs(self) -> None:
        all_ok = True
        for state in self._tab_states:
            if not self._validate_one_tab(state, popup=False):
                all_ok = False
        if all_ok:
            QMessageBox.information(
                self,
                self.gui.tr("Validation", "Validation"),
                self.gui.tr(
                    "Toutes les configurations sont valides.",
                    "All configurations are valid.",
                ),
            )
            return
        QMessageBox.warning(
            self,
            self.gui.tr("Validation", "Validation"),
            self.gui.tr(
                "Certaines configurations contiennent des erreurs.",
                "Some configurations contain errors.",
            ),
        )

    def _format_current_tab(self) -> None:
        idx = self.tabs.currentIndex()
        if idx < 0:
            return
        tab = self.tabs.widget(idx)
        for state in self._tab_states:
            if state["tab"] != tab:
                continue
            ok, formatted, err = format_text(
                state["editor"].toPlainText(), bool(state["is_yaml"])
            )
            if not ok:
                QMessageBox.warning(
                    self,
                    self.gui.tr("Erreur", "Error"),
                    self.gui.tr(
                        f"Format invalide, impossible de formater:\n{err}",
                        f"Invalid format, cannot format:\n{err}",
                    ),
                )
                return
            state["editor"].setPlainText(formatted)
            self._update_outline(state)
            return

    # -------------------------------------------------------------------------
    # Construction des onglets
    # -------------------------------------------------------------------------

    def _build_tab(
        self,
        file_id: str,
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

        actions = QHBoxLayout()
        search = QLineEdit(tab)
        search.setPlaceholderText(self.gui.tr("Rechercher...", "Search..."))
        btn_prev = QPushButton(self.gui.tr("Précédent", "Previous"))
        btn_next = QPushButton(self.gui.tr("Suivant", "Next"))
        btn_validate = QPushButton(self.gui.tr("Valider", "Validate"))
        btn_format = QPushButton(self.gui.tr("Formater", "Format"))
        btn_defaults = QPushButton(self.gui.tr("Valeurs par défaut", "Load defaults"))
        actions.addWidget(search, 1)
        actions.addWidget(btn_prev)
        actions.addWidget(btn_next)
        actions.addWidget(btn_validate)
        actions.addWidget(btn_format)
        actions.addWidget(btn_defaults)
        lay.addLayout(actions)

        splitter = QSplitter(Qt.Orientation.Horizontal, tab)
        editor = self._make_editor(splitter)
        splitter.addWidget(editor)

        side = QDialog(splitter)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(0, 0, 0, 0)
        side_lay.setSpacing(6)
        side_lay.addWidget(QLabel(self.gui.tr("Structure", "Structure")))
        outline = QListWidget(side)
        side_lay.addWidget(outline, 1)
        diagnostics = QLabel("")
        diagnostics.setWordWrap(True)
        diagnostics.setStyleSheet("color: #888;")
        side_lay.addWidget(diagnostics)
        splitter.addWidget(side)
        splitter.setSizes([760, 280])
        lay.addWidget(splitter, 1)

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

        # Initialisation anticipée pour que les closures puissent y accéder.
        state: dict[str, Any] = {}

        def _load():
            path = path_getter()
            if not path:
                editor.setPlainText("")
                path_label.setText("")
                self._update_outline(state)
                return
            path_label.setText(path)
            content = read_text(path)
            if not content.strip():
                content = make_default_content(file_id, is_yaml, self._workspace_dir())
            editor.setPlainText(content)
            state["last_saved"] = editor.toPlainText()
            self._set_tab_dirty(state, False)
            self._update_outline(state)

        def _save():
            path = path_getter()
            if not path:
                return
            text = editor.toPlainText()
            if text.strip() and not self._validate_one_tab(state, popup=True):
                return
            write_text(path, text)
            state["last_saved"] = text
            self._set_tab_dirty(state, False)
            self._update_outline(state)

        def _diff():
            path = path_getter()
            if not path:
                return
            before = read_text(path)
            after = editor.toPlainText()
            self._show_diff(self.gui.tr("Diff du fichier", "File diff"), before, after)

        def _open_any():
            path, _ = QFileDialog.getOpenFileName(
                self, self.gui.tr("Ouvrir un fichier", "Open file"), "", "*.*"
            )
            if not path:
                return
            editor.setPlainText(read_text(path))
            path_label.setText(path)
            self._update_outline(state)

        def _load_defaults():
            default_text = make_default_content(file_id, is_yaml, self._workspace_dir())
            if not default_text.strip():
                return
            answer = QMessageBox.question(
                self,
                self.gui.tr("Confirmer", "Confirm"),
                self.gui.tr(
                    "Remplacer le contenu courant par une configuration par défaut ?",
                    "Replace current content with default configuration?",
                ),
            )
            if answer == QMessageBox.StandardButton.Yes:
                editor.setPlainText(default_text)
                self._update_outline(state)

        btn_reload.clicked.connect(_load)
        btn_save.clicked.connect(_save)
        btn_diff.clicked.connect(_diff)
        btn_open.clicked.connect(_open_any)
        btn_validate.clicked.connect(lambda: self._validate_one_tab(state, popup=True))
        btn_format.clicked.connect(
            lambda: (
                (
                    lambda ok, content, err: (
                        editor.setPlainText(content)
                        if ok
                        else QMessageBox.warning(
                            self,
                            self.gui.tr("Erreur", "Error"),
                            self.gui.tr(
                                f"Format invalide, impossible de formater:\n{err}",
                                f"Invalid format, cannot format:\n{err}",
                            ),
                        )
                    )
                )(*format_text(editor.toPlainText(), is_yaml))
            )
        )
        btn_defaults.clicked.connect(_load_defaults)
        btn_prev.clicked.connect(lambda: self._jump_to_search(state, backward=True))
        btn_next.clicked.connect(lambda: self._jump_to_search(state, backward=False))
        search.returnPressed.connect(
            lambda: self._jump_to_search(state, backward=False)
        )

        self.tabs.addTab(tab, tab_title)
        state.update(
            {
                "file_id": file_id,
                "tab_title": tab_title,
                "tab": tab,
                "is_yaml": is_yaml,
                "editor": editor,
                "path_label": path_label,
                "outline": outline,
                "diagnostics": diagnostics,
                "search": search,
                "dirty": False,
                "last_saved": "",
                "reload": _load,
                "save": _save,
            }
        )
        self._tab_states.append(state)

        def _on_changed():
            self._set_tab_dirty(
                state, editor.toPlainText() != state.get("last_saved", "")
            )
            self._update_outline(state)

        editor.textChanged.connect(_on_changed)
        outline.itemDoubleClicked.connect(
            lambda item: search.setText(item.text())
            or self._jump_to_search(state, backward=False)
        )

        _load()
        return tab, editor, path_label

    # -------------------------------------------------------------------------
    # Configuration des onglets
    # -------------------------------------------------------------------------

    def _setup_tab_ark(self) -> None:
        ws = self._workspace_dir()
        self._build_tab(
            "ark",
            self.gui.tr("ark.yml", "ark.yml"),
            lambda: os.path.join(ws, "ark.yml") if ws else None,
            True,
            self.gui.tr("ARK Config", "ARK Config"),
        )

    def _setup_tab_bcasl(self) -> None:
        ws = self._workspace_dir()
        self._build_tab(
            "bcasl",
            self.gui.tr("bcasl.yml", "bcasl.yml"),
            lambda: os.path.join(ws, "bcasl.yml") if ws else None,
            True,
            self.gui.tr("BCASL Config", "BCASL Config"),
        )

    def _setup_tab_pref(self) -> None:
        ws = self._workspace_dir()
        self._build_tab(
            "pref",
            self.gui.tr(
                "Préférences Workspace (.ark/pref.json)",
                "Workspace Preferences (.ark/pref.json)",
            ),
            lambda: os.path.join(ws, ".ark", "pref.json") if ws else None,
            False,
            self.gui.tr("Workspace Pref", "Workspace Pref"),
        )

    def _setup_engine_tabs(self) -> None:
        ws = self._workspace_dir()
        if not ws:
            return
        root = Path(ws) / ".ark"
        root.mkdir(parents=True, exist_ok=True)

        engine_ids: list[str] = []
        try:
            import Core.engine as engines_loader

            if hasattr(engines_loader, "available_engines"):
                engine_ids = [str(e) for e in engines_loader.available_engines() if e]
        except Exception:
            engine_ids = []

        if not engine_ids:
            try:
                for p in sorted(root.iterdir()):
                    if not p.is_dir():
                        continue
                    if p.name in {"__pycache__"}:
                        continue
                    engine_ids.append(p.name)
            except Exception:
                pass

        for engine_id in sorted(set(engine_ids)):
            cfg = root / engine_id / "config.json"
            self._build_tab(
                f"engine:{engine_id}",
                self.gui.tr(
                    f"Engine config ({engine_id})",
                    f"Engine config ({engine_id})",
                ),
                lambda p=str(cfg): p,
                False,
                self.gui.tr(f"Engine: {engine_id}", f"Engine: {engine_id}"),
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        dirty = [s for s in self._tab_states if s.get("dirty")]
        if not dirty:
            event.accept()
            return
        answer = QMessageBox.question(
            self,
            self.gui.tr("Modifications non sauvegardées", "Unsaved changes"),
            self.gui.tr(
                "Des onglets contiennent des modifications non sauvegardées. Fermer quand même ?",
                "Some tabs contain unsaved changes. Close anyway?",
            ),
        )
        if answer == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
