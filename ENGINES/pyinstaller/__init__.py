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
PyInstaller Engine for PyCompiler_ARK.

This engine handles compilation of Python scripts using PyInstaller,
supporting onefile and directory (onedir) modes, windowed applications,
and various customization options.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Optional

from PySide6.QtCore import QDir
from PySide6.QtWidgets import QFileDialog, QInputDialog

from engine_sdk.base import CompilerEngine
from engine_sdk import engine_register


@engine_register
class PyInstallerEngine(CompilerEngine):
    """
    PyInstaller compilation engine.

    Features:
    - Onefile and onedir modes
    - Windowed/console mode selection
    - Custom output directory
    - Automatic venv detection and use
    - Icon specification
    - Version file support
    - Clean build option
    """

    id: str = "pyinstaller"
    name: str = "PyInstaller"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Return required tools for PyInstaller compilation."""
        return {
            'python': ['pyinstaller'],
            'system': []
        }

    def preflight(self, gui, file: str) -> bool:
        """Preflight check - dependencies are handled automatically by required_tools."""
        return True

    def build_command(self, gui, file: str) -> list[str]:
        """Build the PyInstaller command line."""
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

            # Start with python -m PyInstaller
            cmd = [python_path, "-m", "PyInstaller"]

            # Get options from GUI - use dynamic widgets or fallback to UI widgets
            # Onefile vs Onedir
            onefile = self._get_opt("onefile")
            if onefile and onefile.isChecked():
                cmd.append("--onefile")
            else:
                cmd.append("--onedir")

            # Windowed (no console) - only on Windows/macOS
            windowed = self._get_opt("windowed")
            if windowed and windowed.isChecked():
                if platform.system() == "Windows":
                    cmd.append("--windowed")
                elif platform.system() == "Darwin":
                    cmd.append("--windowed")

            # Clean build
            clean = self._get_opt("clean")
            if clean and clean.isChecked():
                cmd.append("--clean")

            # No UPX
            noupx = self._get_opt("noupx")
            if noupx and noupx.isChecked():
                cmd.append("--noupx")

            # Output directory
            output_dir = self._get_input("output_dir_input")
            if output_dir and output_dir.text().strip():
                cmd.extend(["--distpath", output_dir.text().strip()])

            # Icon
            if hasattr(self, "_selected_icon") and self._selected_icon:
                cmd.extend(["--icon", self._selected_icon])

            # Name
            name_input = self._get_input("output_name_input")
            if name_input and name_input.text().strip():
                cmd.extend(["--name", name_input.text().strip()])

            # Add the target file
            cmd.append(file)

            return cmd

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(
                        f"❌ Erreur construction commande PyInstaller: {e}\n"
                    )
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
            output_dir = self._get_input("output_dir_input")
            if output_dir and output_dir.text().strip():
                try:
                    if hasattr(gui, "log"):
                        gui.log.append(
                            f"📁 Sortie générée dans: {output_dir.text().strip()}\n"
                        )
                except Exception:
                    pass
        except Exception:
            pass

    def create_tab(self, gui):
        """
        Create the PyInstaller tab widget with all options.
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
            from PySide6.QtCore import Qt

            # Create the tab widget
            tab = QWidget()
            tab.setObjectName("tab_pyinstaller_dynamic")

            # Create main layout
            layout = QVBoxLayout(tab)
            layout.setSpacing(10)

            # Create form layout for options
            form_layout = QFormLayout()
            form_layout.setSpacing(8)

            # Onefile option
            self._opt_onefile = QCheckBox("Onefile")
            self._opt_onefile.setObjectName("opt_onefile_dynamic")
            form_layout.addRow("Mode:", self._opt_onefile)

            # Windowed option
            self._opt_windowed = QCheckBox("Windowed")
            self._opt_windowed.setObjectName("opt_windowed_dynamic")
            form_layout.addRow("Console:", self._opt_windowed)

            # Noconfirm option
            self._opt_noconfirm = QCheckBox("Noconfirm")
            self._opt_noconfirm.setObjectName("opt_noconfirm_dynamic")
            form_layout.addRow("Confirmation:", self._opt_noconfirm)

            # Clean option
            self._opt_clean = QCheckBox("Clean")
            self._opt_clean.setObjectName("opt_clean_dynamic")
            form_layout.addRow("Nettoyage:", self._opt_clean)

            # No UPX option
            self._opt_noupx = QCheckBox("No UPX")
            self._opt_noupx.setObjectName("opt_noupx_dynamic")
            form_layout.addRow("Compression:", self._opt_noupx)

            # Main only option
            self._opt_main_only = QCheckBox("Compiler uniquement main.py ou app.py")
            self._opt_main_only.setObjectName("opt_main_only_dynamic")
            form_layout.addRow("Fichiers:", self._opt_main_only)

            layout.addLayout(form_layout)

            # Icon button
            icon_layout = QHBoxLayout()
            self._btn_select_icon = QPushButton("🎨 Choisir une icône (.ico)")
            self._btn_select_icon.setObjectName("btn_select_icon_dynamic")
            self._btn_select_icon.clicked.connect(self.select_icon)
            icon_layout.addWidget(self._btn_select_icon)
            icon_layout.addStretch()
            layout.addLayout(icon_layout)

            # Debug option
            self._opt_debug = QCheckBox("Mode debug (--debug)")
            self._opt_debug.setObjectName("opt_debug_dynamic")
            layout.addWidget(self._opt_debug)

            # Add data button
            self._pyinstaller_add_data = QPushButton("add_data")
            self._pyinstaller_add_data.setObjectName("pyinstaller_add_data_dynamic")
            self._pyinstaller_add_data.clicked.connect(self.add_data)
            layout.addWidget(self._pyinstaller_add_data)

            # Output directory
            output_layout = QHBoxLayout()
            self._output_dir_input = QLineEdit()
            self._output_dir_input.setObjectName("output_dir_input_dynamic")
            self._output_dir_input.setPlaceholderText(
                "Dossier de sortie (--distpath). Laisser vide pour ./dist"
            )
            output_layout.addWidget(self._output_dir_input)
            layout.addLayout(output_layout)

            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, "PyInstaller"

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(f"❌ Erreur création onglet PyInstaller: {e}\n")
            except Exception:
                pass
            return None

    def _get_opt(self, name: str):
        """Get option widget from engine instance or GUI."""
        # Try engine instance first (dynamic tabs)
        if hasattr(self, f"_opt_{name}"):
            return getattr(self, f"_opt_{name}")
        # Fallback to GUI widget (static UI)
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def _get_btn(self, name: str):
        """Get button widget from engine instance or GUI."""
        if hasattr(self, f"_btn_{name}"):
            return getattr(self, f"_btn_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def _get_input(self, name: str):
        """Get input widget from engine instance or GUI."""
        if hasattr(self, f"_{name}"):
            return getattr(self, f"_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"PyInstaller ({self.version})"

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
            from Core.engines_loader.registry import resolve_language_code, load_engine_language_file

            # Resolve language code
            code = resolve_language_code(gui, tr)

            # Load engine-local translations
            lang_data = load_engine_language_file(__package__, code)

            # Apply translations to UI elements if they exist
            if hasattr(self, "_opt_onefile") and "onefile_checkbox" in lang_data:
                self._opt_onefile.setText(lang_data["onefile_checkbox"])
            if hasattr(self, "_opt_windowed") and "windowed_checkbox" in lang_data:
                self._opt_windowed.setText(lang_data["windowed_checkbox"])
            if hasattr(self, "_opt_noconfirm") and "noconfirm_checkbox" in lang_data:
                self._opt_noconfirm.setText(lang_data["noconfirm_checkbox"])
            if hasattr(self, "_opt_clean") and "clean_checkbox" in lang_data:
                self._opt_clean.setText(lang_data["clean_checkbox"])
            if hasattr(self, "_opt_noupx") and "noupx_checkbox" in lang_data:
                self._opt_noupx.setText(lang_data["noupx_checkbox"])
            if hasattr(self, "_opt_main_only") and "main_only_checkbox" in lang_data:
                self._opt_main_only.setText(lang_data["main_only_checkbox"])
            if hasattr(self, "_btn_select_icon") and "icon_button" in lang_data:
                self._btn_select_icon.setText(lang_data["icon_button"])
            if hasattr(self, "_opt_debug") and "debug_checkbox" in lang_data:
                self._opt_debug.setText(lang_data["debug_checkbox"])
            if (
                hasattr(self, "_pyinstaller_add_data")
                and "add_data_button" in lang_data
            ):
                self._pyinstaller_add_data.setText(lang_data["add_data_button"])
            if hasattr(self, "_output_dir_input") and "output_placeholder" in lang_data:
                self._output_dir_input.setPlaceholderText(
                    lang_data["output_placeholder"]
                )
        except Exception:
            pass

    def add_data(self) -> None:
        """Add data files or directories to be included with PyInstaller."""
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
        if choix == "Fichier":
            file_path, _ = QFileDialog.getOpenFileName(
                self._gui, "Sélectionner un fichier à inclure avec PyInstaller"
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
                            f"Fichier ajouté à PyInstaller : {file_path} => {dest}"
                        )
        elif choix == "Dossier":
            dir_path = QFileDialog.getExistingDirectory(
                self._gui,
                "Sélectionner un dossier à inclure avec PyInstaller",
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
                    self._data_files.append((dir_path, dest))
                    if hasattr(self._gui, "log"):
                        self._gui.log.append(
                            f"Dossier ajouté à PyInstaller : {dir_path} => {dest}"
                        )

    def select_icon(self) -> None:
        """Select an icon file for the executable."""
        try:
            from PySide6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getOpenFileName(
                self._gui,
                "Sélectionner une icône",
                "",
                "Fichiers icône (*.ico);;Tous les fichiers (*)"
            )
            if file_path:
                self._selected_icon = file_path
                if hasattr(self._gui, "log"):
                    self._gui.log.append(f"Icône sélectionnée pour PyInstaller : {file_path}")
        except Exception as e:
            if hasattr(self._gui, "log"):
                self._gui.log.append(f"❌ Erreur lors de la sélection de l'icône : {e}")
