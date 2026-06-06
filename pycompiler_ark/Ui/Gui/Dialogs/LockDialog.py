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
LockDialog — Dialog pour gérer et reconstruire à partir de fichiers lock.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
)

from pycompiler_ark.Core.Locking import load_yaml_file


class LockDialog(QDialog):
    """Dialog pour lister les fichiers .lock.yml et relancer un build."""

    def __init__(self, gui):
        super().__init__(gui)
        self.gui = gui
        self.setWindowTitle(gui.tr("Gestion des Verrous (Locks)", "Lock Management"))
        self.resize(900, 600)

        layout = QVBoxLayout(self)

        ws = getattr(self.gui, "workspace_dir", None)
        ws_label = QLabel(gui.tr(f"Workspace: {ws}", f"Workspace: {ws}"))
        ws_label.setStyleSheet("color: #888;")
        layout.addWidget(ws_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Liste des verrous
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self.list_widget)

        # Détails du verrou
        self.details_view = QPlainTextEdit()
        self.details_view.setReadOnly(True)
        self.details_view.setFont(QFont("Consolas", 10))
        splitter.addWidget(self.details_view)

        splitter.setSizes([300, 600])
        layout.addWidget(splitter, 1)

        # Actions
        btn_layout = QHBoxLayout()
        self.btn_rebuild = QPushButton(gui.tr("Reconstruire (Rebuild)", "Rebuild"))
        self.btn_rebuild.setEnabled(False)
        self.btn_rebuild.clicked.connect(self._do_rebuild)

        self.btn_open_dir = QPushButton(gui.tr("Ouvrir dossier", "Open Directory"))
        self.btn_open_dir.clicked.connect(self._open_lock_dir)

        btn_close = QPushButton(gui.tr("Fermer", "Close"))
        btn_close.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_rebuild)
        btn_layout.addWidget(self.btn_open_dir)
        btn_layout.addStretch(1)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        self._refresh_list()

    def _get_lock_dir(self) -> Path | None:
        ws = getattr(self.gui, "workspace_dir", None)
        if not ws:
            return None
        return Path(ws) / ".ark" / "lock"

    def _refresh_list(self):
        self.list_widget.clear()
        lock_dir = self._get_lock_dir()
        if not lock_dir or not lock_dir.exists():
            return

        locks = sorted(
            lock_dir.glob("*.lock.yml"), key=lambda p: p.stat().st_mtime, reverse=True
        )
        for path in locks:
            item = QListWidgetItem(path.name)
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            self.list_widget.addItem(item)

    def _on_selection_changed(self):
        items = self.list_widget.selectedItems()
        if not items:
            self.details_view.clear()
            self.btn_rebuild.setEnabled(False)
            return

        path = items[0].data(Qt.ItemDataRole.UserRole)
        try:
            data = load_yaml_file(Path(path))
            # Formatage simplifié pour l'affichage
            display = yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            self.details_view.setPlainText(display)
            self.btn_rebuild.setEnabled(True)
        except Exception as e:
            self.details_view.setPlainText(f"Error loading lock: {e}")
            self.btn_rebuild.setEnabled(False)

    def _do_rebuild(self):
        items = self.list_widget.selectedItems()
        if not items:
            return

        path = items[0].data(Qt.ItemDataRole.UserRole)
        try:
            lock_payload = load_yaml_file(Path(path))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Impossible de lire le verrou : {e}")
            return

        # Vérification Alignement Git
        if not self._ensure_git_alignment(lock_payload):
            return

        answer = QMessageBox.question(
            self,
            self.gui.tr("Confirmer Rebuild", "Confirm Rebuild"),
            self.gui.tr(
                "Voulez-vous reconstruire le projet à partir de ce verrou ?",
                "Do you want to rebuild the project using this lock file?",
            ),
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.close()
        # On délègue le rebuild à la fenêtre principale
        if hasattr(self.gui, "rebuild_from_lock"):
            self.gui.rebuild_from_lock(Path(path))
        else:
            QMessageBox.critical(
                self, "Error", "rebuild_from_lock method not implemented in GUI"
            )

    def _ensure_git_alignment(self, lock_payload: dict) -> bool:
        project = lock_payload.get("project") or {}
        locked_commit = project.get("git_commit")
        locked_branch = project.get("git_branch")

        if not locked_commit and not locked_branch:
            return True

        from pycompiler_ark.Core.Locking import get_git_commit_hash, get_git_branch

        ws = getattr(self.gui, "workspace_dir", None)
        if not ws:
            return True

        current_commit = get_git_commit_hash(Path(ws))
        current_branch = get_git_branch(Path(ws))

        commit_match = (not locked_commit) or (current_commit == locked_commit)
        branch_match = (not locked_branch) or (current_branch == locked_branch)

        if commit_match and branch_match:
            return True

        import platform
        import subprocess

        is_linux = platform.system().lower() == "linux"

        lines = []
        if not branch_match:
            lines.append(
                self.gui.tr(
                    f"Branche : actuelle={current_branch}, verrou={locked_branch}",
                    f"Branch: current={current_branch}, lock={locked_branch}",
                )
            )
        if not commit_match:
            lines.append(
                self.gui.tr(
                    f"Commit : actuel={current_commit[:8] if current_commit else 'N/A'}, verrou={locked_commit[:8] if locked_commit else 'N/A'}",
                    f"Commit: current={current_commit[:8] if current_commit else 'N/A'}, lock={locked_commit[:8] if locked_commit else 'N/A'}",
                )
            )

        msg = (
            self.gui.tr("Désalignement Git détecté :\n", "Git mismatch detected:\n")
            + "\n".join(lines)
            + "\n\n"
        )

        if is_linux:
            msg += self.gui.tr(
                "Voulez-vous que ARK tente d'aligner automatiquement le code (git checkout) ?",
                "Do you want ARK to attempt automatic code alignment (git checkout)?",
            )
            ans = QMessageBox.question(
                self,
                "Git Mismatch",
                msg,
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if ans == QMessageBox.Yes:
                try:
                    if not branch_match and locked_branch:
                        subprocess.run(
                            ["git", "checkout", locked_branch], cwd=ws, check=True
                        )
                    if not commit_match and locked_commit:
                        subprocess.run(
                            ["git", "checkout", locked_commit], cwd=ws, check=True
                        )
                    return True
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Échec de l'alignement : {e}")
                    return False
            return ans == QMessageBox.No  # True si l'user ignore, False si Cancel
        else:
            cmd_hint = ""
            if not branch_match and locked_branch:
                cmd_hint += f"git checkout {locked_branch}\n"
            if not commit_match and locked_commit:
                cmd_hint += f"git checkout {locked_commit[:8]}\n"

            msg += self.gui.tr(
                f"Action manuelle recommandée :\n{cmd_hint}\nContinuer le build quand même ?",
                f"Recommended manual action:\n{cmd_hint}\nContinue build anyway?",
            )
            ans = QMessageBox.warning(
                self, "Git Mismatch", msg, QMessageBox.Yes | QMessageBox.No
            )
            return ans == QMessageBox.Yes

    def _open_lock_dir(self):
        lock_dir = self._get_lock_dir()
        if not lock_dir or not lock_dir.exists():
            return

        import platform
        import subprocess

        system = platform.system()
        if system == "Windows":
            os.startfile(str(lock_dir))
        elif system == "Darwin":
            subprocess.run(["open", str(lock_dir)])
        else:
            subprocess.run(["xdg-open", str(lock_dir)])


def open_lock_dialog(gui):
    """Helper pour ouvrir le dialog."""
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

    dlg = LockDialog(gui)
    dlg.exec()
