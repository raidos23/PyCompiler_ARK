"""Provide core utilities and workflows for this module."""

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
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml
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


def _read_text(path: str) -> str:
    """Execute _read_text logic for this component."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def _write_text(path: str, content: str) -> None:
    """Execute _write_text logic for this component."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _safe_parse_yaml(text: str) -> bool:
    """Execute _safe_parse_yaml logic for this component."""
    try:
        yaml.safe_load(text)
        return True
    except Exception:
        return False


def _safe_parse_json(text: str) -> bool:
    """Execute _safe_parse_json logic for this component."""
    try:
        json.loads(text)
        return True
    except Exception:
        return False


class _SimpleHighlighter(QSyntaxHighlighter):
    """Implement the _SimpleHighlighter component behavior."""

    def __init__(self, doc, mode: str = "yaml"):
        """Initialize instance state and runtime dependencies."""
        super().__init__(doc)
        self.mode = mode
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        def _fmt(color: str, bold: bool = False) -> QTextCharFormat:
            """Execute _fmt logic for this component."""
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
        """Execute highlightBlock logic for this component."""
        for pattern, fmt in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class AdvancedConfigEditor(QDialog):
    """Implement the AdvancedConfigEditor component behavior."""

    def __init__(self, gui):
        """Initialize instance state and runtime dependencies."""
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

        # Must exist before tab setup: editors emit textChanged during initial load.
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

    def _workspace_dir(self) -> str | None:
        """Return the resolved workspace path information."""
        return getattr(self.gui, "workspace_dir", None)

    def _make_editor(self, parent) -> QPlainTextEdit:
        """Execute _make_editor logic for this component."""
        edit = QPlainTextEdit(parent)
        edit.setFont(QFont("Consolas", 10))
        edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        return edit

    def _parse_text(self, text: str, is_yaml: bool) -> tuple[bool, Any, str]:
        """Parse the provided input into a structured value."""
        try:
            if is_yaml:
                data = yaml.safe_load(text) if text.strip() else {}
            else:
                data = json.loads(text) if text.strip() else {}
            return True, data, ""
        except Exception as exc:
            return False, None, str(exc)

    def _format_text(self, text: str, is_yaml: bool) -> tuple[bool, str, str]:
        """Format the related content for display or storage."""
        ok, data, err = self._parse_text(text, is_yaml)
        if not ok:
            return False, text, err
        try:
            if is_yaml:
                return (
                    True,
                    yaml.safe_dump(data or {}, allow_unicode=True, sort_keys=False),
                    "",
                )
            return True, json.dumps(data or {}, ensure_ascii=False, indent=2) + "\n", ""
        except Exception as exc:
            return False, text, str(exc)

    def _show_diff(self, title: str, before: str, after: str) -> None:
        """Execute _show_diff logic for this component."""
        diff = self._compute_diff(before, after)
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

    def _compute_diff(self, before: str, after: str) -> str:
        """Compute a git-like diff first, then fallback to Python unified diff."""
        git = shutil.which("git")
        if git:
            try:
                with tempfile.TemporaryDirectory(prefix="ark_diff_") as tmp:
                    old_path = os.path.join(tmp, "before.txt")
                    new_path = os.path.join(tmp, "after.txt")
                    with open(old_path, "w", encoding="utf-8") as f_old:
                        f_old.write(before)
                    with open(new_path, "w", encoding="utf-8") as f_new:
                        f_new.write(after)
                    proc = subprocess.run(
                        [
                            git,
                            "--no-pager",
                            "diff",
                            "--no-index",
                            "--minimal",
                            "--patience",
                            "--",
                            old_path,
                            new_path,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                    out = proc.stdout or ""
                    # git diff returns 1 when changes are found; this is expected.
                    if out.strip():
                        return out
            except Exception:
                pass
        return "\n".join(
            difflib.unified_diff(
                before.splitlines(),
                after.splitlines(),
                fromfile="original",
                tofile="modified",
                lineterm="",
            )
        )

    def _flatten_keys(self, data: Any, prefix: str = "") -> list[str]:
        """Execute _flatten_keys logic for this component."""
        lines: list[str] = []
        if isinstance(data, dict):
            for key, value in data.items():
                k = str(key)
                path = f"{prefix}.{k}" if prefix else k
                lines.append(path)
                lines.extend(self._flatten_keys(value, path))
        elif isinstance(data, list):
            for idx, value in enumerate(data):
                path = f"{prefix}[{idx}]"
                lines.append(path)
                lines.extend(self._flatten_keys(value, path))
        return lines

    def _validate_payload(self, file_id: str, data: Any) -> tuple[list[str], list[str]]:
        """Validate the related data and constraints."""
        errs: list[str] = []
        warns: list[str] = []

        if not isinstance(data, dict):
            errs.append("Root must be an object/map.")
            return errs, warns

        if file_id == "ark":
            allowed_top = {
                "exclusion_patterns",
                "inclusion_patterns",
                "dependencies",
                "environment_manager",
                "build",
                "plugins",
            }
            unknown = sorted(k for k in data.keys() if k not in allowed_top)
            if unknown:
                warns.append("Unknown top-level keys: " + ", ".join(unknown))

            for key in ("exclusion_patterns", "inclusion_patterns"):
                v = data.get(key)
                if v is not None and (
                    not isinstance(v, list)
                    or not all(isinstance(item, str) for item in v)
                ):
                    errs.append(f"{key} must be a list of strings.")

            build = data.get("build")
            if build is not None and not isinstance(build, dict):
                errs.append("build must be an object.")
            if isinstance(build, dict):
                ep = build.get("entrypoint")
                if ep is not None and not isinstance(ep, str):
                    errs.append("build.entrypoint must be a string or null.")
                if isinstance(ep, str) and not ep.strip():
                    warns.append("build.entrypoint is empty.")

            deps = data.get("dependencies")
            if deps is not None and not isinstance(deps, dict):
                errs.append("dependencies must be an object.")
            if isinstance(deps, dict):
                req_files = deps.get("requirements_files")
                if req_files is not None and (
                    not isinstance(req_files, list)
                    or not all(isinstance(item, str) for item in req_files)
                ):
                    errs.append(
                        "dependencies.requirements_files must be a list of strings."
                    )
                autogen = deps.get("auto_generate_from_imports")
                if autogen is not None and not isinstance(autogen, bool):
                    errs.append(
                        "dependencies.auto_generate_from_imports must be a boolean."
                    )

            env = data.get("environment_manager")
            if env is not None and not isinstance(env, dict):
                errs.append("environment_manager must be an object.")
            if isinstance(env, dict):
                priority = env.get("priority")
                if priority is not None and (
                    not isinstance(priority, list)
                    or not all(isinstance(item, str) for item in priority)
                ):
                    errs.append(
                        "environment_manager.priority must be a list of strings."
                    )
                for flag in ("auto_detect", "fallback_to_pip"):
                    if flag in env and not isinstance(env.get(flag), bool):
                        errs.append(f"environment_manager.{flag} must be a boolean.")

        elif file_id == "bcasl":
            file_patterns = data.get("file_patterns")
            if file_patterns is not None and (
                not isinstance(file_patterns, list)
                or not all(isinstance(item, str) for item in file_patterns)
            ):
                errs.append("file_patterns must be a list of strings.")

            exclude_patterns = data.get("exclude_patterns")
            if exclude_patterns is not None and (
                not isinstance(exclude_patterns, list)
                or not all(isinstance(item, str) for item in exclude_patterns)
            ):
                errs.append("exclude_patterns must be a list of strings.")

            options = data.get("options")
            if options is not None and not isinstance(options, dict):
                errs.append("options must be an object.")
            if isinstance(options, dict):
                if "enabled" in options and not isinstance(
                    options.get("enabled"), bool
                ):
                    errs.append("options.enabled must be a boolean.")
                if "plugin_timeout_s" in options and not isinstance(
                    options.get("plugin_timeout_s"), (int, float)
                ):
                    errs.append("options.plugin_timeout_s must be numeric.")
                if "plugin_parallelism" in options and not isinstance(
                    options.get("plugin_parallelism"), int
                ):
                    errs.append("options.plugin_parallelism must be an integer.")

            plugins = data.get("plugins")
            if plugins is not None and not isinstance(plugins, dict):
                errs.append("plugins must be an object.")
            if isinstance(plugins, dict):
                for pid, cfg in plugins.items():
                    if not isinstance(cfg, dict):
                        errs.append(f"plugins.{pid} must be an object.")
                        continue
                    if "enabled" in cfg and not isinstance(cfg.get("enabled"), bool):
                        errs.append(f"plugins.{pid}.enabled must be a boolean.")
                    if "priority" in cfg and not isinstance(cfg.get("priority"), int):
                        errs.append(f"plugins.{pid}.priority must be an integer.")

            plugin_order = data.get("plugin_order")
            if plugin_order is not None and (
                not isinstance(plugin_order, list)
                or not all(isinstance(item, str) for item in plugin_order)
            ):
                errs.append("plugin_order must be a list of strings.")

        elif file_id == "pref":
            mode = data.get("venv_mode")
            if mode is not None and mode not in ("system", "venv"):
                errs.append("venv_mode must be 'system' or 'venv'.")
            venv_path = data.get("venv_path")
            if venv_path is not None and not isinstance(venv_path, str):
                errs.append("venv_path must be a string or null.")
            if mode == "venv" and not isinstance(venv_path, str):
                warns.append("venv_mode='venv' but venv_path is empty.")

        return errs, warns

    def _mk_default_content(self, file_id: str, is_yaml: bool) -> str:
        """Build and return the default content structure."""
        if file_id == "ark":
            try:
                from Core.ArkConfigManager import DEFAULT_CONFIG

                return yaml.safe_dump(
                    DEFAULT_CONFIG, allow_unicode=True, sort_keys=False
                )
            except Exception:
                pass
        if file_id == "pref":
            payload = {"venv_mode": "system", "venv_path": None}
            return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if file_id == "bcasl":
            ws = self._workspace_dir()
            if ws:
                try:
                    from bcasl.Loader import _load_workspace_config  # type: ignore

                    data = _load_workspace_config(Path(ws))
                    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
                except Exception:
                    pass
            payload = {
                "file_patterns": ["**/*.py"],
                "exclude_patterns": ["**/__pycache__/**", ".venv/**", "venv/**"],
                "options": {
                    "enabled": True,
                    "plugin_timeout_s": 0.0,
                    "sandbox": True,
                    "plugin_parallelism": 0,
                    "iter_files_cache": True,
                },
                "plugins": {},
                "plugin_order": [],
            }
            return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

        return "" if is_yaml else "{}\n"

    def _set_tab_dirty(self, state: dict[str, Any], dirty: bool) -> None:
        """Execute _set_tab_dirty logic for this component."""
        if state.get("dirty") == dirty:
            return
        state["dirty"] = dirty
        idx = self.tabs.indexOf(state["tab"])
        base = state.get("tab_title", "")
        if idx >= 0:
            self.tabs.setTabText(idx, ("* " + base) if dirty else base)
        self._refresh_global_status()

    def _refresh_global_status(self) -> None:
        """Refresh the related state and UI feedback."""
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
        """Update the related state based on current data."""
        text = state["editor"].toPlainText()
        is_yaml = bool(state["is_yaml"])
        ok, data, err = self._parse_text(text, is_yaml)
        outline: QListWidget = state["outline"]
        diagnostics: QLabel = state["diagnostics"]
        outline.clear()

        if not ok:
            diagnostics.setText(
                self.gui.tr(
                    f"Erreur de parsing: {err}",
                    f"Parse error: {err}",
                )
            )
            diagnostics.setStyleSheet("color: #d9534f;")
            return

        keys = self._flatten_keys(data)
        for key in keys:
            QListWidgetItem(key, outline)

        errs, warns = self._validate_payload(state["file_id"], data)
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
        """Validate the related data and constraints."""
        text = state["editor"].toPlainText()
        ok, data, err = self._parse_text(text, bool(state["is_yaml"]))
        if not ok:
            if popup:
                QMessageBox.warning(
                    self,
                    self.gui.tr("Erreur", "Error"),
                    self.gui.tr(f"Format invalide:\n{err}", f"Invalid format:\n{err}"),
                )
            self._update_outline(state)
            return False
        errs, warns = self._validate_payload(state["file_id"], data)
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
        """Execute _jump_to_search logic for this component."""
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
        """Handle the related event callback."""
        self._refresh_global_status()

    def _reload_all_tabs(self) -> None:
        """Execute _reload_all_tabs logic for this component."""
        for state in self._tab_states:
            state["reload"]()
        self._refresh_global_status()

    def _save_all_tabs(self) -> None:
        """Persist data to the related destination."""
        for state in self._tab_states:
            state["save"]()
        self._refresh_global_status()

    def _validate_all_tabs(self) -> None:
        """Validate the related data and constraints."""
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
        """Format the related content for display or storage."""
        idx = self.tabs.currentIndex()
        if idx < 0:
            return
        tab = self.tabs.widget(idx)
        for state in self._tab_states:
            if state["tab"] != tab:
                continue
            ok, formatted, err = self._format_text(
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

    def _build_tab(
        self,
        file_id: str,
        label: str,
        path_getter: Callable[[], str | None],
        is_yaml: bool,
        tab_title: str,
    ) -> tuple[QDialog, QPlainTextEdit, QLabel]:
        """Execute _build_tab logic for this component."""
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

        def _load():
            """Load data from the related source."""
            path = path_getter()
            if not path:
                editor.setPlainText("")
                path_label.setText("")
                self._update_outline(state)
                return
            path_label.setText(path)
            content = _read_text(path)
            if not content.strip():
                content = self._mk_default_content(file_id, is_yaml)
            editor.setPlainText(content)
            state["last_saved"] = editor.toPlainText()
            self._set_tab_dirty(state, False)
            self._update_outline(state)

        def _save():
            """Persist data to the related destination."""
            path = path_getter()
            if not path:
                return
            text = editor.toPlainText()
            if text.strip() and not self._validate_one_tab(state, popup=True):
                return
            _write_text(path, text)
            state["last_saved"] = text
            self._set_tab_dirty(state, False)
            self._update_outline(state)

        def _diff():
            """Execute _diff logic for this component."""
            path = path_getter()
            if not path:
                return
            before = _read_text(path)
            after = editor.toPlainText()
            self._show_diff(self.gui.tr("Diff du fichier", "File diff"), before, after)

        def _open_any():
            """Execute _open_any logic for this component."""
            path, _ = QFileDialog.getOpenFileName(
                self, self.gui.tr("Ouvrir un fichier", "Open file"), "", "*.*"
            )
            if not path:
                return
            editor.setPlainText(_read_text(path))
            path_label.setText(path)
            self._update_outline(state)

        def _load_defaults():
            """Load data from the related source."""
            default_text = self._mk_default_content(file_id, is_yaml)
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
                )(*self._format_text(editor.toPlainText(), is_yaml))
            )
        )
        btn_defaults.clicked.connect(_load_defaults)
        btn_prev.clicked.connect(lambda: self._jump_to_search(state, backward=True))
        btn_next.clicked.connect(lambda: self._jump_to_search(state, backward=False))
        search.returnPressed.connect(
            lambda: self._jump_to_search(state, backward=False)
        )

        self.tabs.addTab(tab, tab_title)
        state = {
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
        self._tab_states.append(state)

        def _on_changed():
            """Handle the related event callback."""
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

    def _setup_tab_ark(self) -> None:
        """Set up the related UI or runtime section."""
        ws = self._workspace_dir()
        self._build_tab(
            "ark",
            self.gui.tr("ARK_Main_Config.yml", "ARK_Main_Config.yml"),
            lambda: os.path.join(ws, "ARK_Main_Config.yml") if ws else None,
            True,
            self.gui.tr("ARK Config", "ARK Config"),
        )

    def _setup_tab_bcasl(self) -> None:
        """Set up the related UI or runtime section."""
        ws = self._workspace_dir()
        self._build_tab(
            "bcasl",
            self.gui.tr("bcasl.yml", "bcasl.yml"),
            lambda: os.path.join(ws, "bcasl.yml") if ws else None,
            True,
            self.gui.tr("BCASL Config", "BCASL Config"),
        )

    def _setup_tab_pref(self) -> None:
        """Set up the related UI or runtime section."""
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
        """Set up the related UI or runtime section."""
        ws = self._workspace_dir()
        if not ws:
            return
        root = Path(ws) / ".ark"
        root.mkdir(parents=True, exist_ok=True)

        engine_ids: list[str] = []
        try:
            import EngineLoader as engines_loader

            if hasattr(engines_loader, "available_engines"):
                engine_ids = [str(e) for e in engines_loader.available_engines() if e]
        except Exception:
            engine_ids = []

        # Fallback to existing engine config folders in workspace.
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
        """Handle window close behavior and cleanup."""
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
