# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Ague Samuel Amen
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
BCASL Standalone GUI Application

Interface minimale pour exécuter BCASL indépendamment du compilateur principal.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QApplication,
        QMainWindow,
        QWidget,
        QVBoxLayout,
        QHBoxLayout,
        QPushButton,
        QLabel,
        QTextEdit,
        QFileDialog,
        QMessageBox,
        QProgressBar,
        QCheckBox,
    )
    from PySide6.QtCore import Qt, QThread, Signal, Slot
except ImportError:
    print("Error: PySide6 is required. Install it with: pip install PySide6")
    sys.exit(1)

from bcasl import (
    run_pre_compile_async,
    run_pre_compile,
    ensure_bcasl_thread_stopped,
    open_bc_loader_dialog,
    resolve_bcasl_timeout,
)
from bcasl.Loader import _load_workspace_config


class BcaslStandaloneApp(QMainWindow):
    """Application autonome pour exécuter BCASL."""

    def __init__(self, workspace_dir: Optional[str] = None):
        super().__init__()
        self.workspace_dir = workspace_dir
        self.log = None
        self._bcasl_thread = None
        self._bcasl_worker = None
        self._bcasl_ui_bridge = None
        self._is_running = False

        self.setWindowTitle("BCASL Standalone - Before Compilation Actions System Loader")
        self.setGeometry(100, 100, 900, 700)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Workspace selection
        ws_layout = QHBoxLayout()
        ws_label = QLabel("Workspace:")
        self.ws_display = QLabel(workspace_dir or "No workspace selected")
        self.ws_display.setStyleSheet("color: #0066cc; font-weight: bold;")
        ws_btn = QPushButton("Browse...")
        ws_btn.clicked.connect(self._select_workspace)
        ws_layout.addWidget(ws_label)
        ws_layout.addWidget(self.ws_display)
        ws_layout.addStretch()
        ws_layout.addWidget(ws_btn)
        layout.addLayout(ws_layout)

        # Config info
        self.config_info = QLabel("No configuration loaded")
        self.config_info.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.config_info)

        # Log output
        log_label = QLabel("Execution Log:")
        layout.addWidget(log_label)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet("font-family: monospace; font-size: 9px;")
        layout.addWidget(self.log)

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Options
        options_layout = QHBoxLayout()
        self.chk_async = QCheckBox("Run asynchronously")
        self.chk_async.setChecked(True)
        options_layout.addWidget(self.chk_async)
        options_layout.addStretch()
        layout.addLayout(options_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_config = QPushButton("⚙️ Configure Plugins")
        self.btn_config.clicked.connect(self._open_config_dialog)
        self.btn_run = QPushButton("▶️ Run BCASL")
        self.btn_run.clicked.connect(self._run_bcasl)
        self.btn_clear = QPushButton("🗑️ Clear Log")
        self.btn_clear.clicked.connect(self.log.clear)
        self.btn_exit = QPushButton("Exit")
        self.btn_exit.clicked.connect(self.close)

        btn_layout.addWidget(self.btn_config)
        btn_layout.addWidget(self.btn_run)
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_exit)
        layout.addLayout(btn_layout)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Load initial config if workspace provided
        if workspace_dir:
            self._load_config_info()

    def _select_workspace(self):
        """Select workspace directory."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Workspace Directory",
            self.workspace_dir or os.path.expanduser("~"),
        )
        if folder:
            self.workspace_dir = folder
            self.ws_display.setText(folder)
            self._load_config_info()
            self.log.append(f"✅ Workspace selected: {folder}\n")

    def _load_config_info(self):
        """Load and display configuration info."""
        if not self.workspace_dir:
            self.config_info.setText("No workspace selected")
            return

        try:
            cfg = _load_workspace_config(Path(self.workspace_dir))
            plugins = cfg.get("plugins", {})
            enabled_count = sum(
                1
                for v in plugins.values()
                if isinstance(v, dict) and v.get("enabled", True)
                or isinstance(v, bool) and v
            )
            total_count = len(plugins)
            file_patterns = cfg.get("file_patterns", [])
            exclude_patterns = cfg.get("exclude_patterns", [])

            info = (
                f"Plugins: {enabled_count}/{total_count} enabled | "
                f"File patterns: {len(file_patterns)} | "
                f"Exclude patterns: {len(exclude_patterns)}"
            )
            self.config_info.setText(info)
        except Exception as e:
            self.config_info.setText(f"Error loading config: {e}")

    def _open_config_dialog(self):
        """Open plugin configuration dialog."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a workspace first.",
            )
            return
        try:
            open_bc_loader_dialog(self)
            self._load_config_info()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open config dialog: {e}")

    def _run_bcasl(self):
        """Run BCASL."""
        if not self.workspace_dir:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select a workspace first.",
            )
            return

        if self._is_running:
            QMessageBox.information(
                self,
                "Information",
                "BCASL is already running. Please wait for it to complete.",
            )
            return

        self._is_running = True
        self.btn_run.setEnabled(False)
        self.btn_config.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setMaximum(0)  # Indeterminate progress
        self.statusBar().showMessage("Running BCASL...")
        self.log.append("\n" + "=" * 60)
        self.log.append("Starting BCASL execution...")
        self.log.append("=" * 60 + "\n")

        def on_done(report):
            """Callback when BCASL completes."""
            self._is_running = False
            self.btn_run.setEnabled(True)
            self.btn_config.setEnabled(True)
            self.progress.setVisible(False)

            if report is None:
                self.log.append("\n❌ BCASL execution failed or was cancelled.\n")
                self.statusBar().showMessage("Failed")
            else:
                try:
                    self.log.append("\n" + "=" * 60)
                    self.log.append("BCASL Execution Report:")
                    self.log.append("=" * 60 + "\n")
                    for item in report:
                        status = "✅ OK" if item.success else f"❌ FAIL: {item.error}"
                        self.log.append(
                            f"  {item.plugin_id}: {status} ({item.duration_ms:.1f}ms)\n"
                        )
                    self.log.append("\n" + report.summary() + "\n")
                    self.statusBar().showMessage(
                        "Completed" if report.ok else "Completed with errors"
                    )
                except Exception as e:
                    self.log.append(f"\n⚠️ Error displaying report: {e}\n")
                    self.statusBar().showMessage("Completed")

        try:
            if self.chk_async.isChecked():
                run_pre_compile_async(self, on_done)
            else:
                report = run_pre_compile(self)
                on_done(report)
        except Exception as e:
            self.log.append(f"\n❌ Error: {e}\n")
            self._is_running = False
            self.btn_run.setEnabled(True)
            self.btn_config.setEnabled(True)
            self.progress.setVisible(False)
            self.statusBar().showMessage("Error")

    def closeEvent(self, event):
        """Handle window close."""
        try:
            ensure_bcasl_thread_stopped(self)
        except Exception:
            pass
        event.accept()


def main():
    """Main entry point for standalone BCASL application."""
    import argparse

    parser = argparse.ArgumentParser(
        description="BCASL Standalone - Before Compilation Actions System Loader"
    )
    parser.add_argument(
        "workspace",
        nargs="?",
        help="Path to workspace directory (optional)",
    )
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = BcaslStandaloneApp(workspace_dir=args.workspace)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
