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
CX_Freeze Engine for PyCompiler_ARK.

This engine handles compilation of Python scripts using CX_Freeze,
supporting windowed applications and minimal essential options.
"""

from __future__ import annotations

import os
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
from engine_sdk.utils import log_with_level


@engine_register
class CXFreezeEngine(CompilerEngine):
    """
    CX_Freeze compilation engine.

    Features:
    - Windowed/console mode selection (Windows)
    - Custom output directory
    - Automatic venv detection and use
    - Icon specification
    """

    id: str = "cx_freeze"
    name: str = "CX_Freeze"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Return required tools for CX_Freeze compilation."""
        return {"python": ["cx_freeze"], "system": []}

    def preflight(self, gui, file: str) -> bool:
        """Preflight check - dependencies are handled automatically by required_tools."""
        return True

    def build_command(self, gui, file: str) -> list[str]:
        """Build the CX_Freeze command line."""
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

            # Start with python -m cx_Freeze
            cmd = [python_path, "-m", "cx_Freeze"]

            # Add options from UI
            # Windowed mode (Windows only)
            windowed = self._get_opt("windowed")
            if windowed and windowed.isChecked() and platform.system() == "Windows":
                cmd.extend(["--base", "Win32GUI"])

            # Output directory
            output_dir = self._get_input("output_dir")
            if output_dir and output_dir.text().strip():
                cmd.extend(["--target-dir", output_dir.text().strip()])

            # Icon
            if hasattr(self, "_selected_icon") and self._selected_icon:
                cmd.extend(["--icon", self._selected_icon])

            # Target name
            target_name = self._get_input("target_name")
            if target_name and target_name.text().strip():
                cmd.extend(["--target-name", target_name.text().strip()])

            # Debug / verbose
            debug = self._get_opt("debug")
            if debug and debug.isChecked():
                cmd.append("--debug")
            verbose = self._get_opt("verbose")
            if verbose and verbose.isChecked():
                cmd.append("--verbose")

            # Auto-mapping args (mapping.json / auto builder)
            try:
                auto_args = compute_auto_for_engine(gui, self.id)
                if auto_args:
                    cmd.extend(auto_args)
            except Exception:
                pass

            # Add the target script
            cmd.extend(["--script", file])

            return cmd

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    log_with_level(gui, "error", f"Erreur construction commande CX_Freeze: {e}")
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
                getattr(self, "_cx_output_dir", getattr(gui, "output_dir_input", None))
                if hasattr(self, "_gui")
                else getattr(self, "_cx_output_dir", None)
            )
            if output_dir and output_dir.text().strip():
                try:
                    if hasattr(gui, "log"):
                        log_with_level(
                            gui,
                            "success",
                            f"Compilation CX_Freeze terminée. Sortie dans: {output_dir.text().strip()}",
                        )
                except Exception:
                    pass
        except Exception:
            pass

    def create_tab(self, gui):
        """
        Create the CX_Freeze tab widget with all options.
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
            tab.setObjectName("tab_cx_freeze_dynamic")

            # Create main layout
            layout = QVBoxLayout(tab)
            layout.setSpacing(10)

            # Create form layout for options
            form_layout = QFormLayout()
            form_layout.setSpacing(8)

            # Windowed option
            self._cx_windowed = add_form_checkbox(
                form_layout, "Console:", "No console", "cx_windowed_dynamic"
            )
            self._cx_windowed.setToolTip("Disable the console window.")

            layout.addLayout(form_layout)

            # Icon button + path input
            self._cx_btn_select_icon, self._cx_icon_path_input = add_icon_selector(
                layout,
                "Choisir une icône (.ico)",
                self.select_icon,
                "cx_btn_select_icon_dynamic",
                "cx_icon_path_input_dynamic",
            )
            if self._cx_icon_path_input is not None:
                self._cx_icon_path_input.textChanged.connect(
                    self._on_icon_path_changed
                )

            # Debug / verbose
            self._cx_debug = QCheckBox("Debug")
            self._cx_debug.setObjectName("cx_debug_dynamic")
            self._cx_debug.setToolTip("Enable debug output.")
            layout.addWidget(self._cx_debug)

            self._cx_verbose = QCheckBox("Verbose")
            self._cx_verbose.setObjectName("cx_verbose_dynamic")
            self._cx_verbose.setToolTip("Enable verbose output.")
            layout.addWidget(self._cx_verbose)

            # Target name
            self._cx_target_name = add_output_dir(
                layout,
                "Nom de sortie (--target-name)",
                "cx_target_name_dynamic",
            )

            # Output directory
            self._cx_output_dir = add_output_dir(
                layout, "Dossier de sortie", "cx_output_dir_dynamic"
            )

            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, "CX_Freeze"

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    log_with_level(gui, "error", f"Erreur création onglet CX_Freeze: {e}")
            except Exception:
                pass
            return None

    def get_config(self, gui) -> dict:
        """Return a JSON-serializable snapshot of current CX_Freeze UI options."""
        try:
            cfg = {}
            if hasattr(self, "_cx_windowed") and self._cx_windowed is not None:
                cfg["windowed"] = bool(self._cx_windowed.isChecked())
            if hasattr(self, "_cx_output_dir") and self._cx_output_dir is not None:
                cfg["output_dir"] = self._cx_output_dir.text().strip()
            if (
                hasattr(self, "_cx_target_name")
                and self._cx_target_name is not None
            ):
                cfg["target_name"] = self._cx_target_name.text().strip()
            if hasattr(self, "_cx_debug") and self._cx_debug is not None:
                cfg["debug"] = bool(self._cx_debug.isChecked())
            if hasattr(self, "_cx_verbose") and self._cx_verbose is not None:
                cfg["verbose"] = bool(self._cx_verbose.isChecked())
            icon_path = ""
            if (
                hasattr(self, "_cx_icon_path_input")
                and self._cx_icon_path_input is not None
            ):
                icon_path = self._cx_icon_path_input.text().strip()
            if not icon_path and hasattr(self, "_selected_icon") and self._selected_icon:
                icon_path = str(self._selected_icon).strip()
            if icon_path:
                self._selected_icon = icon_path
                cfg["selected_icon"] = icon_path
            return cfg
        except Exception:
            return {}

    def set_config(self, gui, cfg: dict) -> None:
        """Apply a config dict to CX_Freeze UI widgets."""
        if not isinstance(cfg, dict):
            return
        try:
            if (
                hasattr(self, "_cx_windowed")
                and self._cx_windowed is not None
                and "windowed" in cfg
            ):
                self._cx_windowed.setChecked(bool(cfg.get("windowed")))
            if (
                hasattr(self, "_cx_output_dir")
                and self._cx_output_dir is not None
                and "output_dir" in cfg
            ):
                val = cfg.get("output_dir") or ""
                self._cx_output_dir.setText(str(val))
            if (
                hasattr(self, "_cx_target_name")
                and self._cx_target_name is not None
                and "target_name" in cfg
            ):
                val = cfg.get("target_name") or ""
                self._cx_target_name.setText(str(val))
            if (
                hasattr(self, "_cx_debug")
                and self._cx_debug is not None
                and "debug" in cfg
            ):
                self._cx_debug.setChecked(bool(cfg.get("debug")))
            if (
                hasattr(self, "_cx_verbose")
                and self._cx_verbose is not None
                and "verbose" in cfg
            ):
                self._cx_verbose.setChecked(bool(cfg.get("verbose")))
            if "selected_icon" in cfg:
                icon = cfg.get("selected_icon") or ""
                self._selected_icon = icon or None
                if (
                    hasattr(self, "_cx_icon_path_input")
                    and self._cx_icon_path_input is not None
                ):
                    self._cx_icon_path_input.setText(str(icon))
        except Exception:
            pass

    def _get_opt(self, name: str):
        """Get option widget from engine instance or GUI."""
        # Try engine instance first (dynamic tabs)
        if hasattr(self, f"_cx_{name}"):
            return getattr(self, f"_cx_{name}")
        # Fallback to GUI widget (static UI)
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def _get_input(self, name: str):
        """Get input widget from engine instance or GUI."""
        if hasattr(self, f"_cx_{name}"):
            return getattr(self, f"_cx_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def _get_btn(self, name: str):
        """Get button widget from engine instance or GUI."""
        if hasattr(self, f"_cx_btn_{name}"):
            return getattr(self, f"_cx_btn_{name}")
        if hasattr(self, f"_btn_{name}"):
            return getattr(self, f"_btn_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"CX_Freeze ({self.version})"

    def apply_i18n(self, gui, tr: dict) -> None:
        """Apply internationalization translations to the engine UI."""
        try:
            from engine_sdk import resolve_language_code, load_engine_language_file

            # Resolve language code
            code = resolve_language_code(gui, tr)

            # Load engine-local translations
            lang_data = load_engine_language_file(__package__, code)

            # Apply translations to UI elements if they exist
            if hasattr(self, "_cx_windowed") and "windowed_checkbox" in lang_data:
                self._cx_windowed.setText(lang_data["windowed_checkbox"])
            if hasattr(self, "_cx_windowed") and "tt_windowed" in lang_data:
                self._cx_windowed.setToolTip(lang_data["tt_windowed"])
            if hasattr(self, "_cx_btn_select_icon") and "icon_button" in lang_data:
                self._cx_btn_select_icon.setText(lang_data["icon_button"])
            if hasattr(self, "_cx_debug") and "debug_checkbox" in lang_data:
                self._cx_debug.setText(lang_data["debug_checkbox"])
            if hasattr(self, "_cx_debug") and "tt_debug" in lang_data:
                self._cx_debug.setToolTip(lang_data["tt_debug"])
            if hasattr(self, "_cx_verbose") and "verbose_checkbox" in lang_data:
                self._cx_verbose.setText(lang_data["verbose_checkbox"])
            if hasattr(self, "_cx_verbose") and "tt_verbose" in lang_data:
                self._cx_verbose.setToolTip(lang_data["tt_verbose"])
            if (
                hasattr(self, "_cx_target_name")
                and "target_name_placeholder" in lang_data
            ):
                self._cx_target_name.setPlaceholderText(
                    lang_data["target_name_placeholder"]
                )
            if hasattr(self, "_cx_output_dir") and "output_placeholder" in lang_data:
                self._cx_output_dir.setPlaceholderText(lang_data["output_placeholder"])
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
                if (
                    hasattr(self, "_cx_icon_path_input")
                    and self._cx_icon_path_input is not None
                ):
                    self._cx_icon_path_input.setText(file_path)
                if hasattr(self._gui, "log"):
                    self._gui.log.append(
                        f"Icône sélectionnée pour Cx_Freeze : {file_path}"
                    )
        except Exception as e:
            if hasattr(self._gui, "log"):
                log_with_level(self._gui, "error", f"Erreur lors de la sélection de l'icône : {e}")
