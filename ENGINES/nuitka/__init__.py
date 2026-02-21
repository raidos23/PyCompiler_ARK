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

import platform
import sys
from typing import Optional

from engine_sdk import (
    CompilerEngine,
    add_icon_selector,
    add_output_dir,
    compute_auto_for_engine,
    engine_register,
)
from engine_sdk.utils import log_with_level


@engine_register
class NuitkaEngine(CompilerEngine):
    """
    Nuitka compilation engine.

    Features:
    - Standalone and onefile modes
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
            system_tools = ["patchelf"]
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

            # Standalone mode
            if (
                hasattr(self, "_nuitka_standalone")
                and self._nuitka_standalone.isChecked()
            ):
                cmd.append("--standalone")

            # Onefile mode
            if hasattr(self, "_nuitka_onefile") and self._nuitka_onefile.isChecked():
                cmd.append("--onefile")

            # Windowed (no console)
            if (
                hasattr(self, "_nuitka_disable_console")
                and self._nuitka_disable_console.isChecked()
            ):
                cmd.append("--windows-disable-console")

            # Output directory
            if (
                hasattr(self, "_nuitka_output_dir")
                and self._nuitka_output_dir.text().strip()
            ):
                cmd.append(f"--output-dir={self._nuitka_output_dir.text().strip()}")

            # Icon
            selected_icon = getattr(self, "_nuitka_selected_icon", None)
            if selected_icon:
                cmd.extend(["--windows-icon", selected_icon])

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
                    log_with_level(gui, "error", f"Erreur construction commande Nuitka: {e}")
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
            if (
                hasattr(self, "_nuitka_output_dir")
                and self._nuitka_output_dir.text().strip()
            ):
                try:
                    if hasattr(gui, "log"):
                        log_with_level(
                            gui,
                            "success",
                            f"Compilation Nuitka terminée. Sortie dans: {self._nuitka_output_dir.text().strip()}",
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
            self._nuitka_disable_console = QCheckBox("Disable console")
            self._nuitka_disable_console.setObjectName("nuitka_disable_console_dynamic")
            self._nuitka_disable_console.setToolTip(
                "Disable console window for Windows builds."
            )
            form_layout.addRow("Console:", self._nuitka_disable_console)

            layout.addLayout(form_layout)

            # Output directory
            self._nuitka_output_dir = add_output_dir(
                layout, "Dossier de sortie (--output-dir)", "nuitka_output_dir_dynamic"
            )

            # Icon button + path input
            self._btn_nuitka_icon, self._nuitka_icon_path_input = add_icon_selector(
                layout,
                "🎨 Choisir une icône (.ico) Nuitka",
                self.select_icon,
                "btn_nuitka_icon_dynamic",
                "nuitka_icon_path_input_dynamic",
            )
            if self._nuitka_icon_path_input is not None:
                self._nuitka_icon_path_input.textChanged.connect(
                    self._on_icon_path_changed
                )

            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, "Nuitka"

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    log_with_level(gui, "error", f"Erreur création onglet Nuitka: {e}")
            except Exception:
                pass
            return None

    def get_config(self, gui) -> dict:
        """Return a JSON-serializable snapshot of current Nuitka UI options."""
        try:
            cfg = {}
            if hasattr(self, "_nuitka_onefile") and self._nuitka_onefile is not None:
                cfg["onefile"] = bool(self._nuitka_onefile.isChecked())
            if (
                hasattr(self, "_nuitka_standalone")
                and self._nuitka_standalone is not None
            ):
                cfg["standalone"] = bool(self._nuitka_standalone.isChecked())
            if (
                hasattr(self, "_nuitka_disable_console")
                and self._nuitka_disable_console is not None
            ):
                cfg["disable_console"] = bool(self._nuitka_disable_console.isChecked())
            if (
                hasattr(self, "_nuitka_output_dir")
                and self._nuitka_output_dir is not None
            ):
                cfg["output_dir"] = self._nuitka_output_dir.text().strip()
            icon_path = ""
            if (
                hasattr(self, "_nuitka_icon_path_input")
                and self._nuitka_icon_path_input is not None
            ):
                icon_path = self._nuitka_icon_path_input.text().strip()
            if (
                not icon_path
                and hasattr(self, "_nuitka_selected_icon")
                and self._nuitka_selected_icon
            ):
                icon_path = str(self._nuitka_selected_icon).strip()
            if not icon_path and hasattr(self, "_selected_icon") and self._selected_icon:
                icon_path = str(self._selected_icon).strip()
            if icon_path:
                self._nuitka_selected_icon = icon_path
                self._selected_icon = icon_path
                cfg["selected_icon"] = icon_path
            return cfg
        except Exception:
            return {}

    def set_config(self, gui, cfg: dict) -> None:
        """Apply a config dict to Nuitka UI widgets."""
        if not isinstance(cfg, dict):
            return
        try:
            if (
                hasattr(self, "_nuitka_onefile")
                and self._nuitka_onefile is not None
                and "onefile" in cfg
            ):
                self._nuitka_onefile.setChecked(bool(cfg.get("onefile")))
            if (
                hasattr(self, "_nuitka_standalone")
                and self._nuitka_standalone is not None
                and "standalone" in cfg
            ):
                self._nuitka_standalone.setChecked(bool(cfg.get("standalone")))
            if (
                hasattr(self, "_nuitka_disable_console")
                and self._nuitka_disable_console is not None
                and "disable_console" in cfg
            ):
                self._nuitka_disable_console.setChecked(
                    bool(cfg.get("disable_console"))
                )
            if (
                hasattr(self, "_nuitka_output_dir")
                and self._nuitka_output_dir is not None
                and "output_dir" in cfg
            ):
                val = cfg.get("output_dir") or ""
                self._nuitka_output_dir.setText(str(val))
            if "selected_icon" in cfg:
                icon = cfg.get("selected_icon") or ""
                self._nuitka_selected_icon = icon or None
                self._selected_icon = icon or None
                if (
                    hasattr(self, "_nuitka_icon_path_input")
                    and self._nuitka_icon_path_input is not None
                ):
                    self._nuitka_icon_path_input.setText(str(icon))
        except Exception:
            pass

    def _get_btn(self, name: str):
        """Get button widget from engine instance or GUI."""
        if hasattr(self, f"_btn_{name}"):
            return getattr(self, f"_btn_{name}")
        return getattr(self._gui, name, None) if hasattr(self, "_gui") else None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"Nuitka ({self.version})"

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
                hasattr(self, "_nuitka_disable_console")
                and "tt_disable_console" in lang_data
            ):
                self._nuitka_disable_console.setToolTip(lang_data["tt_disable_console"])
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

    def _on_icon_path_changed(self, text: str) -> None:
        """Keep the selected icon path in sync with manual edits."""
        icon = text.strip()
        self._nuitka_selected_icon = icon or None
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
                self._nuitka_selected_icon = file_path
                if (
                    hasattr(self, "_nuitka_icon_path_input")
                    and self._nuitka_icon_path_input is not None
                ):
                    self._nuitka_icon_path_input.setText(file_path)
                if hasattr(self._gui, "log"):
                    self._gui.log.append(
                        f"Icône sélectionnée pour Nuitka : {file_path}"
                    )
        except Exception as e:
            if hasattr(self._gui, "log"):
                log_with_level(self._gui, "error", f"Erreur lors de la sélection de l'icône : {e}")
