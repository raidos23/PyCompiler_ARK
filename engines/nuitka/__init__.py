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
    BuildContext,
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

    def build_command_from_context(self, context: BuildContext) -> list[str]:
        """Build a Nuitka command line from a normalized build context."""
        cfg = getattr(self, "_config_overrides", {})
        if not isinstance(cfg, dict):
            cfg = {}

        cmd = [sys.executable, "-m", "nuitka"]

        standalone_enabled = bool(cfg.get("standalone", False))
        if hasattr(self, "_nuitka_standalone"):
            standalone_enabled = bool(self._nuitka_standalone.isChecked())
        if standalone_enabled:
            cmd.append("--standalone")

        onefile_enabled = bool(cfg.get("onefile", False))
        if hasattr(self, "_nuitka_onefile"):
            onefile_enabled = bool(self._nuitka_onefile.isChecked())
        if onefile_enabled:
            cmd.append("--onefile")

        disable_console = bool(cfg.get("disable_console", False))
        if hasattr(self, "_nuitka_disable_console"):
            disable_console = bool(self._nuitka_disable_console.isChecked())
        if disable_console:
            cmd.append("--windows-disable-console")

        output_dir = str(context.output_dir or cfg.get("output_dir") or "").strip()
        if output_dir:
            cmd.append(f"--output-dir={output_dir}")

        output_name = str(context.project_name or "").strip()
        if output_name:
            cmd.append(f"--output-filename={output_name}")

        icon_path = str(context.icon or cfg.get("selected_icon") or "").strip()
        if not icon_path:
            icon_path = str(getattr(self, "_nuitka_selected_icon", "") or "").strip()
        if icon_path:
            cmd.append(f"--windows-icon-from-ico={icon_path}")

        for pattern in context.exclude_patterns:
            module = (
                str(pattern)
                .replace("/**/*", "")
                .replace("**/*", "")
                .replace("/**", "")
                .strip("/")
            )
            if module and "*" not in module:
                cmd.append(f"--nofollow-import-to={module.replace('/', '.')}")

        for mapping in context.data_mappings:
            source = str((mapping or {}).get("source") or "").strip()
            destination = str((mapping or {}).get("destination") or "").strip()
            if source and destination:
                cmd.append(f"--include-data-dir={source}={destination}")

        cmd.append(context.entry_point)
        return cmd

    def build_command(self, gui, file: str) -> list[str]:
        """Build the Nuitka command line."""
        try:
            cfg = getattr(self, "_config_overrides", {})
            if not isinstance(cfg, dict):
                cfg = {}

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
            standalone_enabled = bool(cfg.get("standalone", False))
            if hasattr(self, "_nuitka_standalone"):
                standalone_enabled = bool(self._nuitka_standalone.isChecked())
            if standalone_enabled:
                cmd.append("--standalone")

            # Onefile mode
            onefile_enabled = bool(cfg.get("onefile", False))
            if hasattr(self, "_nuitka_onefile"):
                onefile_enabled = bool(self._nuitka_onefile.isChecked())
            if onefile_enabled:
                cmd.append("--onefile")

            # Windowed (no console)
            disable_console = bool(cfg.get("disable_console", False))
            if hasattr(self, "_nuitka_disable_console"):
                disable_console = bool(self._nuitka_disable_console.isChecked())
            if disable_console:
                cmd.append("--windows-disable-console")

            # Output directory
            output_dir_value = str(cfg.get("output_dir") or "").strip()
            if (
                hasattr(self, "_nuitka_output_dir")
                and self._nuitka_output_dir.text().strip()
            ):
                output_dir_value = self._nuitka_output_dir.text().strip()
            if output_dir_value:
                cmd.append(f"--output-dir={output_dir_value}")

            # Icon
            selected_icon = getattr(self, "_nuitka_selected_icon", None)
            if not selected_icon:
                selected_icon = cfg.get("selected_icon")
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
                    log_with_level(
                        gui, "error", f"Erreur construction commande Nuitka: {e}"
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
                QLabel,
                QGroupBox,
                QSizePolicy,
                QVBoxLayout,
                QWidget,
            )

            # Create the tab widget
            tab = QWidget()
            tab.setObjectName("tab_nuitka_dynamic")

            # Create main layout
            layout = QVBoxLayout(tab)
            layout.setSpacing(8)
            layout.setContentsMargins(8, 8, 8, 8)

            build_group = QGroupBox("Build", tab)
            build_layout = QFormLayout()
            build_layout.setSpacing(6)

            # Onefile option
            self._nuitka_onefile = QCheckBox("Onefile (--onefile)")
            self._nuitka_onefile.setObjectName("nuitka_onefile_dynamic")
            build_layout.addRow("Mode:", self._nuitka_onefile)

            # Standalone option
            self._nuitka_standalone = QCheckBox("Standalone (--standalone)")
            self._nuitka_standalone.setObjectName("nuitka_standalone_dynamic")
            build_layout.addRow("Type:", self._nuitka_standalone)

            # Disable console option
            self._nuitka_disable_console = QCheckBox("Disable console")
            self._nuitka_disable_console.setObjectName("nuitka_disable_console_dynamic")
            self._nuitka_disable_console.setToolTip(
                "Disable console window for Windows builds."
            )
            build_layout.addRow("Console:", self._nuitka_disable_console)
            build_group.setLayout(build_layout)

            output_group = QGroupBox("Output", tab)
            output_layout = QVBoxLayout()
            output_layout.setSpacing(6)

            # Output directory
            self._nuitka_output_dir = add_output_dir(
                output_layout,
                "Dossier de sortie (--output-dir)",
                "nuitka_output_dir_dynamic",
            )
            output_group.setLayout(output_layout)

            assets_group = QGroupBox("Assets", tab)
            assets_layout = QVBoxLayout()
            assets_layout.setSpacing(6)

            # Icon button + path input
            self._btn_nuitka_icon, self._nuitka_icon_path_input = add_icon_selector(
                assets_layout,
                "🎨 Choisir une icône (.ico) Nuitka",
                self.select_icon,
                "btn_nuitka_icon_dynamic",
                "nuitka_icon_path_input_dynamic",
            )
            if self._nuitka_icon_path_input is not None:
                self._nuitka_icon_path_input.textChanged.connect(
                    self._on_icon_path_changed
                )
            assets_group.setLayout(assets_layout)

            hint = QLabel(
                "Tip: combine standalone or onefile modes carefully, then tune console visibility for desktop apps.",
                tab,
            )
            hint.setStyleSheet("color: #888; font-size: 11px;")
            hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            layout.addWidget(build_group)
            layout.addWidget(output_group)
            layout.addWidget(assets_group)
            layout.addWidget(hint)
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
            if (
                not icon_path
                and hasattr(self, "_selected_icon")
                and self._selected_icon
            ):
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
            self._config_overrides = dict(cfg)
        except Exception:
            self._config_overrides = {}
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
            # Apply translations to UI elements if they exist
            if hasattr(self, "_nuitka_onefile"):
                self._nuitka_onefile.setText(
                    self.engine_translate("onefile_checkbox", "Onefile")
                )
            if hasattr(self, "_nuitka_standalone"):
                self._nuitka_standalone.setText(
                    self.engine_translate("standalone_checkbox", "Standalone")
                )
            if hasattr(self, "_nuitka_disable_console"):
                self._nuitka_disable_console.setText(
                    self.engine_translate("disable_console_checkbox", "Disable console")
                )
            if hasattr(self, "_nuitka_disable_console"):
                self._nuitka_disable_console.setToolTip(
                    self.engine_translate("tt_disable_console", "")
                )
            if hasattr(self, "_nuitka_output_dir"):
                self._nuitka_output_dir.setPlaceholderText(
                    self.engine_translate("output_placeholder", "Output directory")
                )
            if hasattr(self, "_btn_nuitka_icon"):
                self._btn_nuitka_icon.setText(
                    self.engine_translate("icon_button", "Select icon")
                )
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
                log_with_level(
                    self._gui, "error", f"Erreur lors de la sélection de l'icône : {e}"
                )
