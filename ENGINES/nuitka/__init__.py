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
Nuitka Engine for PyCompiler_ARK.

This engine handles compilation of Python scripts using Nuitka,
supporting standalone mode, onefile mode, and various optimization options.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Optional

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QFileDialog, QInputDialog

from engine_sdk.base import CompilerEngine
from engine_sdk import engine_register, compute_for_all


@engine_register
class NuitkaEngine(CompilerEngine):
    """
    Nuitka compilation engine.

    Features:
    - Standalone and onefile modes
    - Python include options
    - Plugin support
    - MSVC/Clang/LLVM backend selection
    - Data files inclusion
    - Icon specification
    """

    id: str = "nuitka"
    name: str = "Nuitka"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Return required tools for Nuitka compilation."""
        system_tools = []
        if platform.system() == "Linux":
            # patchelf is needed for Linux binary manipulation
            # gcc is needed for compilation
            system_tools = ["patchelf", "gcc"]
        elif platform.system() == "Windows":
            # On Windows, Visual Studio Build Tools or similar might be needed
            # but we'll keep it minimal for now
            system_tools = []

        return {"python": ["nuitka"], "system": system_tools}

    def preflight(self, gui, file: str) -> bool:
        """Preflight check - dependencies are handled automatically by required_tools."""
        return True

    def build_command(self, gui, file: str) -> list[str]:
        """Build the Nuitka command line."""
        try:
            venv_manager = getattr(gui, "venv_manager", None)

            # Resolve venv python
            if venv_manager:
                venv_path = venv_manager.resolve_project_venv()
                if venv_path:
                    python_path = venv_manager.python_path(venv_path)
                else:
                    python_path = sys.executable
            else:
                python_path = sys.executable

            # Start with python -m nuitka
            cmd = [python_path, "-m", "nuitka"]

            # Use dynamic widgets or fallback to UI widgets
            # Standalone mode
            if self._nuitka_standalone.isChecked():
                cmd.append("--standalone")

            # Onefile mode
            if self._nuitka_onefile.isChecked():
                cmd.append("--onefile")

            # Windowed (no console)
            if self._nuitka_disable_console.isChecked():
                cmd.append("--windows-disable-console")

            # Show progress
            if self._nuitka_show_progress.isChecked():
                cmd.append("--show-progress")

            # Output directory
            if self._nuitka_output_dir.text().strip():
                cmd.extend(["--output-dir", self._nuitka_output_dir.text().strip()])

            # Auto ajout des plugins Nuitka via détection
            try:
                auto_map = compute_for_all(self) or {}
                auto_nuitka_args = auto_map.get("nuitka", [])
                for a in auto_nuitka_args:
                    if a not in cmd:
                        cmd.append(a)
            except Exception as e:
                try:
                    self.log.append(f"⚠️ Auto-détection Nuitka: {e}")
                except Exception:
                    pass

            # Add the target file
            cmd.append(file)

            return cmd

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(f"❌ Erreur construction commande Nuitka: {e}\n")
            except Exception:
                pass
            return []

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        """Return the program and args for QProcess."""
        cmd = self.build_command(gui, file)
        if not cmd:
            return None
        return cmd[0], cmd[1:]

    def environment(self, gui, file: str) -> Optional[dict[str, str]]:
        """Return environment variables for the compilation process."""
        try:
            env = {}

            # Set PYTHONIOENCODING for proper output handling
            env["PYTHONIOENCODING"] = "utf-8"

            # Disable PYTHONUTF8 mode to avoid conflicts
            env["PYTHONUTF8"] = "0"

            # Set LC_ALL for consistent output
            env["LC_ALL"] = "C"

            return env if env else None
        except Exception:
            return None

    def on_success(self, gui, file: str) -> None:
        """Handle successful compilation."""
        try:
            # Log success message with output location
            if self._nuitka_output_dir.text().strip():
                try:
                    if hasattr(gui, "log"):
                        gui.log.append(
                            f"📁 Compilation Nuitka terminée. Sortie dans: {self._nuitka_output_dir.text().strip()}\n"
                        )
                except Exception:
                    pass
        except Exception:
            pass

    def create_tab(self, gui):
        """
        Create the Nuitka tab widget with all options.
        Returns (widget, label) tuple or None if tab creation fails.
        """
        try:
            from PySide6.QtWidgets import (
                QCheckBox,
                QFormLayout,
                QHBoxLayout,
                QLineEdit,
                QPushButton,
                QVBoxLayout,
                QWidget,
            )

            # Create the tab widget
            tab = QWidget()
            tab.setObjectName("tab_nuitka_dynamic")

            # Create main layout
            layout = QVBoxLayout(tab)
            layout.setSpacing(10)

            # Create form layout for options
            form_layout = QFormLayout()
            form_layout.setSpacing(8)

            # Onefile option
            self._nuitka_onefile = QCheckBox("Onefile (--onefile)")
            self._nuitka_onefile.setObjectName("nuitka_onefile_dynamic")
            form_layout.addRow("Mode:", self._nuitka_onefile)

            # Standalone option
            self._nuitka_standalone = QCheckBox("Standalone (--standalone)")
            self._nuitka_standalone.setObjectName("nuitka_standalone_dynamic")
            form_layout.addRow("Type:", self._nuitka_standalone)

            # Disable console option
            self._nuitka_disable_console = QCheckBox(
                "Désactiver la console Windows (--windows-disable-console)"
            )
            self._nuitka_disable_console.setObjectName("nuitka_disable_console_dynamic")
            form_layout.addRow("Console:", self._nuitka_disable_console)

            # Show progress option
            self._nuitka_show_progress = QCheckBox(
                "Afficher la progression (--show-progress)"
            )
            self._nuitka_show_progress.setObjectName("nuitka_show_progress_dynamic")
            self._nuitka_show_progress.setChecked(True)
            form_layout.addRow("Progression:", self._nuitka_show_progress)

            layout.addLayout(form_layout)

            # Add data button
            self._nuitka_add_data = QPushButton("add_data")
            self._nuitka_add_data.setObjectName("nuitka_add_data_dynamic")
            self._nuitka_add_data.clicked.connect(self.add_data)
            layout.addWidget(self._nuitka_add_data)

            # Output directory
            output_layout = QHBoxLayout()
            self._nuitka_output_dir = QLineEdit()
            self._nuitka_output_dir.setObjectName("nuitka_output_dir_dynamic")
            self._nuitka_output_dir.setPlaceholderText(
                "Dossier de sortie (--output-dir)"
            )
            output_layout.addWidget(self._nuitka_output_dir)
            layout.addLayout(output_layout)

            # Icon button
            icon_layout = QHBoxLayout()
            self._btn_nuitka_icon = QPushButton("🎨 Choisir une icône (.ico) Nuitka")
            self._btn_nuitka_icon.setObjectName("btn_nuitka_icon_dynamic")
            self._btn_nuitka_icon.clicked.connect(self.select_icon)
            icon_layout.addWidget(self._btn_nuitka_icon)
            icon_layout.addStretch()
            layout.addLayout(icon_layout)

            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, "Nuitka"

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(f"❌ Erreur création onglet Nuitka: {e}\n")
            except Exception:
                pass
            return None



    def _get_btn(self, name: str):
        """Get button widget from engine instance or GUI."""
        if hasattr(self, f"_btn_{name}"):
            return getattr(self, f"_btn_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None



    def get_log_prefix(self, file_basename: str) -> str:
        return f"Nuitka ({self.version})"

    def should_compile_file(
        self, gui, file: str, selected_files: list[str], python_files: list[str]
    ) -> bool:
        """Determine if a file should be included in the compilation queue."""
        # Skip non-Python files
        if not file.endswith(".py"):
            return False
        return True

    def apply_i18n(self, gui, tr: dict) -> None:
        """Apply internationalization translations to the engine UI."""
        try:
            from engine_sdk import resolve_language_code, load_engine_language_file

            # Resolve language code
            code = resolve_language_code(gui, tr)

            # Load engine-local translations
            lang_data = load_engine_language_file(__package__, code)

            # Apply translations to UI elements if they exist
            if hasattr(self, "_nuitka_onefile") and "onefile_checkbox" in lang_data:
                self._nuitka_onefile.setText(lang_data["onefile_checkbox"])
            if (
                hasattr(self, "_nuitka_standalone")
                and "standalone_checkbox" in lang_data
            ):
                self._nuitka_standalone.setText(lang_data["standalone_checkbox"])
            if (
                hasattr(self, "_nuitka_disable_console")
                and "disable_console_checkbox" in lang_data
            ):
                self._nuitka_disable_console.setText(
                    lang_data["disable_console_checkbox"]
                )
            if (
                hasattr(self, "_nuitka_show_progress")
                and "show_progress_checkbox" in lang_data
            ):
                self._nuitka_show_progress.setText(lang_data["show_progress_checkbox"])
            if hasattr(self, "_nuitka_add_data") and "add_data_button" in lang_data:
                self._nuitka_add_data.setText(lang_data["add_data_button"])
            if (
                hasattr(self, "_nuitka_output_dir")
                and "output_placeholder" in lang_data
            ):
                self._nuitka_output_dir.setPlaceholderText(
                    lang_data["output_placeholder"]
                )
            if hasattr(self, "_btn_nuitka_icon") and "icon_button" in lang_data:
                self._btn_nuitka_icon.setText(lang_data["icon_button"])
        except Exception:
            pass

    def add_data(self) -> None:
        """Add data files or directories to be included with Nuitka."""
        choix, ok = QInputDialog.getItem(
            self._gui,
            "Type d'inclusion",
            "Inclure un fichier ou un dossier ?",
            ["Fichier", "Dossier"],
            0,
            False,
        )
        if not ok:
            return
        if not hasattr(self, "_data_files"):
            self._data_files = []
        if not hasattr(self, "_data_dirs"):
            self._data_dirs = []
        if choix == "Fichier":
            file_path, _ = QFileDialog.getOpenFileName(
                self._gui, "Sélectionner un fichier à inclure avec Nuitka"
            )
            if file_path:
                dest, ok = QInputDialog.getText(
                    self._gui,
                    "Chemin de destination",
                    "Chemin de destination dans l'exécutable :",
                    text=os.path.basename(file_path),
                )
                if ok and dest:
                    self._data_files.append((file_path, dest))
                    if hasattr(self._gui, "log"):
                        self._gui.log.append(
                            f"Fichier ajouté à Nuitka : {file_path} => {dest}"
                        )
        elif choix == "Dossier":
            dir_path = QFileDialog.getExistingDirectory(
                self._gui,
                "Sélectionner un dossier à inclure avec Nuitka",
                QDir.homePath(),
            )
            if dir_path:
                dest, ok = QInputDialog.getText(
                    self._gui,
                    "Chemin de destination",
                    "Chemin de destination dans l'exécutable :",
                    text=os.path.basename(dir_path),
                )
                if ok and dest:
                    self._data_dirs.append((dir_path, dest))
                    if hasattr(self._gui, "log"):
                        self._gui.log.append(
                            f"Dossier ajouté à Nuitka : {dir_path} => {dest}"
                        )

    def select_icon(self) -> None:
        """Select an icon file for the executable."""
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getOpenFileName(
                self._gui,
                "Sélectionner une icône",
                "",
                "Fichiers icône (*.ico);;Tous les fichiers (*)",
            )
            if file_path:
                self._selected_icon = file_path
                if hasattr(self._gui, "log"):
                    self._gui.log.append(
                        f"Icône sélectionnée pour Nuitka : {file_path}"
                    )
        except Exception as e:
            if hasattr(self._gui, "log"):
                self._gui.log.append(f"❌ Erreur lors de la sélection de l'icône : {e}")
