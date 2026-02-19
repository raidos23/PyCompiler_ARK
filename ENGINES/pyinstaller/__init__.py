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

import platform
import sys
from typing import Optional

from engine_sdk import (
    CompilerEngine,
    add_form_checkbox,
    add_icon_selector,
    add_output_dir,
    compute_auto_for_engine,
    engine_register,
)


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
    """

    id: str = "pyinstaller"
    name: str = "PyInstaller"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Return required tools for PyInstaller compilation."""
        return {"python": ["pyinstaller"], "system": []}

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

            # Auto-mapping args (mapping.json / auto builder)
            try:
                auto_args = compute_auto_for_engine(gui, self.id)
                if auto_args:
                    cmd.extend(auto_args)
            except Exception:
                pass

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

    def environment(self) -> Optional[dict[str, str]]:
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
            output_dir = (
                getattr(
                    self, "_output_dir_input", getattr(gui, "output_dir_input", None)
                )
                if hasattr(self, "_gui")
                else getattr(self, "_output_dir_input", None)
            )
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
            self._opt_onefile = add_form_checkbox(
                form_layout, "Mode:", "Onefile", "opt_onefile_dynamic"
            )

            # Windowed option
            self._opt_windowed = add_form_checkbox(
                form_layout, "Console:", "Windowed", "opt_windowed_dynamic"
            )

            layout.addLayout(form_layout)

            # Icon button + path input
            self._btn_select_icon, self._icon_path_input = add_icon_selector(
                layout,
                "🎨 Choisir une icône (.ico)",
                self.select_icon,
                "btn_select_icon_dynamic",
                "pyinstaller_icon_path_input_dynamic",
            )
            if self._icon_path_input is not None:
                self._icon_path_input.textChanged.connect(
                    self._on_icon_path_changed
                )

            # Output directory
            self._output_dir_input = add_output_dir(
                layout,
                "Dossier de sortie (--distpath). Laisser vide pour ./dist",
                "output_dir_input_dynamic",
            )

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

    def get_config(self, gui) -> dict:
        """Return a JSON-serializable snapshot of current PyInstaller UI options."""
        try:
            cfg = {}
            if hasattr(self, "_opt_onefile") and self._opt_onefile is not None:
                cfg["onefile"] = bool(self._opt_onefile.isChecked())
            if hasattr(self, "_opt_windowed") and self._opt_windowed is not None:
                cfg["windowed"] = bool(self._opt_windowed.isChecked())
            if (
                hasattr(self, "_output_dir_input")
                and self._output_dir_input is not None
            ):
                cfg["output_dir"] = self._output_dir_input.text().strip()
            icon_path = ""
            if (
                hasattr(self, "_icon_path_input")
                and self._icon_path_input is not None
            ):
                icon_path = self._icon_path_input.text().strip()
            if not icon_path and hasattr(self, "_selected_icon") and self._selected_icon:
                icon_path = str(self._selected_icon).strip()
            if icon_path:
                self._selected_icon = icon_path
                cfg["selected_icon"] = icon_path
            return cfg
        except Exception:
            return {}

    def set_config(self, gui, cfg: dict) -> None:
        """Apply a config dict to PyInstaller UI widgets."""
        if not isinstance(cfg, dict):
            return
        try:
            if (
                hasattr(self, "_opt_onefile")
                and self._opt_onefile is not None
                and "onefile" in cfg
            ):
                self._opt_onefile.setChecked(bool(cfg.get("onefile")))
            if (
                hasattr(self, "_opt_windowed")
                and self._opt_windowed is not None
                and "windowed" in cfg
            ):
                self._opt_windowed.setChecked(bool(cfg.get("windowed")))
            if (
                hasattr(self, "_output_dir_input")
                and self._output_dir_input is not None
                and "output_dir" in cfg
            ):
                val = cfg.get("output_dir") or ""
                self._output_dir_input.setText(str(val))
            if "selected_icon" in cfg:
                icon = cfg.get("selected_icon") or ""
                self._selected_icon = icon or None
                if (
                    hasattr(self, "_icon_path_input")
                    and self._icon_path_input is not None
                ):
                    self._icon_path_input.setText(str(icon))
        except Exception:
            pass

    def _get_opt(self, name: str):
        """Get option widget from engine instance or GUI."""
        # Try engine instance first (dynamic tabs)
        if hasattr(self, f"_opt_{name}"):
            return getattr(self, f"_opt_{name}")
        # Fallback to GUI widget (static UI)
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def _get_input(self, name: str):
        """Get input widget from engine instance or GUI."""
        if hasattr(self, f"_{name}"):
            return getattr(self, f"_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"PyInstaller ({self.version})"

    def apply_i18n(self, gui, tr: dict) -> None:
        """Apply internationalization translations to the engine UI."""
        try:
            from engine_sdk import resolve_language_code, load_engine_language_file

            # Resolve language code
            code = resolve_language_code(gui, tr)

            # Load engine-local translations
            lang_data = load_engine_language_file(__package__, code)

            # Apply translations to UI elements if they exist
            if hasattr(self, "_opt_onefile") and "onefile_checkbox" in lang_data:
                self._opt_onefile.setText(lang_data["onefile_checkbox"])
            if hasattr(self, "_opt_windowed") and "windowed_checkbox" in lang_data:
                self._opt_windowed.setText(lang_data["windowed_checkbox"])
            if hasattr(self, "_btn_select_icon") and "icon_button" in lang_data:
                self._btn_select_icon.setText(lang_data["icon_button"])
            if hasattr(self, "_output_dir_input") and "output_placeholder" in lang_data:
                self._output_dir_input.setPlaceholderText(
                    lang_data["output_placeholder"]
                )
        except Exception:
            pass

    def _on_icon_path_changed(self, text: str) -> None:
        """Keep the selected icon path in sync with manual edits."""
        icon = text.strip()
        self._selected_icon = icon or None

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
                if hasattr(self, "_icon_path_input") and self._icon_path_input is not None:
                    self._icon_path_input.setText(file_path)
                if hasattr(self._gui, "log"):
                    self._gui.log.append(
                        f"Icône sélectionnée pour PyInstaller : {file_path}"
                    )
        except Exception as e:
            if hasattr(self._gui, "log"):
                self._gui.log.append(f"❌ Erreur lors de la sélection de l'icône : {e}")
