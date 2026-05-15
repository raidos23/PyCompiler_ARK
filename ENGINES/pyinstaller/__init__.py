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
    BuildContext,
    CompilerEngine,
    add_form_checkbox,
    add_icon_selector,
    add_output_dir,
    compute_auto_for_engine,
    engine_register,
)
from engine_sdk.utils import log_with_level


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

    def build_command_from_context(self, context: BuildContext) -> list[str]:
        """Build a PyInstaller command line from a normalized build context."""
        cfg = getattr(self, "_config_overrides", {})
        if not isinstance(cfg, dict):
            cfg = {}

        cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm"]

        onefile_enabled = bool(cfg.get("onefile", False))
        if hasattr(self, "_onefile") and self._onefile is not None:
            onefile_enabled = bool(self._onefile.isChecked())
        cmd.append("--onefile" if onefile_enabled else "--onedir")

        windowed_enabled = bool(cfg.get("windowed", False))
        if hasattr(self, "_windowed") and self._windowed is not None:
            windowed_enabled = bool(self._windowed.isChecked())
        if windowed_enabled and platform.system() in {"Windows", "Darwin"}:
            cmd.append("--windowed")

        output_dir = str(context.output_dir or cfg.get("output_dir") or "").strip()
        if output_dir:
            cmd.extend(["--distpath", output_dir])

        icon_path = str(context.icon or cfg.get("selected_icon") or "").strip()
        if not icon_path and hasattr(self, "_selected_icon") and self._selected_icon:
            icon_path = str(self._selected_icon).strip()
        if icon_path:
            cmd.extend(["--icon", icon_path])

        output_name = str(cfg.get("target_name") or context.project_name or "").strip()
        if output_name:
            cmd.extend(["--name", output_name])

        for pattern in context.exclude_patterns:
            module = (
                str(pattern)
                .replace("/**/*", "")
                .replace("**/*", "")
                .replace("/**", "")
                .strip("/")
            )
            if module and "*" not in module:
                cmd.extend(["--exclude-module", module.replace("/", ".")])

        separator = ";" if platform.system() == "Windows" else ":"
        for mapping in context.data_mappings:
            source = str((mapping or {}).get("source") or "").strip()
            destination = str((mapping or {}).get("destination") or "").strip()
            if source and destination:
                cmd.extend(["--add-data", f"{source}{separator}{destination}"])

        cmd.append(context.entry_point)
        return cmd

    def build_command(self, gui, file: str) -> list[str]:
        """Build the PyInstaller command line."""
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

            # Start with python -m PyInstaller
            cmd = [python_path, "-m", "PyInstaller", "--noconfirm"]

            # Get options from GUI - use dynamic widgets or fallback to UI widgets
            # Onefile vs Onedir
            onefile = self._get_opt("onefile")
            onefile_enabled = bool(cfg.get("onefile", False))
            if onefile and onefile.isChecked():
                onefile_enabled = True
            elif onefile is not None:
                onefile_enabled = False
            if onefile_enabled:
                cmd.append("--onefile")
            else:
                cmd.append("--onedir")

            # Windowed (no console) - only on Windows/macOS
            windowed = self._get_opt("windowed")
            windowed_enabled = bool(cfg.get("windowed", False))
            if windowed and windowed.isChecked():
                windowed_enabled = True
            elif windowed is not None:
                windowed_enabled = False
            if windowed_enabled:
                if platform.system() == "Windows":
                    cmd.append("--windowed")
                elif platform.system() == "Darwin":
                    cmd.append("--windowed")

            # Output directory
            output_dir = self._get_input("output_dir_input")
            output_dir_value = str(cfg.get("output_dir") or "").strip()
            if output_dir and output_dir.text().strip():
                output_dir_value = output_dir.text().strip()
            if output_dir_value:
                cmd.extend(["--distpath", output_dir_value])

            # Icon
            selected_icon = ""
            if hasattr(self, "_selected_icon") and self._selected_icon:
                selected_icon = str(self._selected_icon).strip()
            if not selected_icon:
                selected_icon = str(cfg.get("selected_icon") or "").strip()
            if selected_icon:
                cmd.extend(["--icon", selected_icon])

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
                    log_with_level(
                        gui, "error", f"Erreur construction commande PyInstaller: {e}"
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
                        log_with_level(
                            gui,
                            "success",
                            f"Sortie générée dans: {output_dir.text().strip()}",
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
                QLabel,
                QGroupBox,
                QSizePolicy,
                QVBoxLayout,
                QWidget,
            )

            # Create the tab widget
            tab = QWidget()
            tab.setObjectName("tab_pyinstaller_dynamic")

            # Create main layout
            layout = QVBoxLayout(tab)
            layout.setSpacing(8)
            layout.setContentsMargins(8, 8, 8, 8)

            build_group = QGroupBox("Build", tab)
            build_layout = QFormLayout()
            build_layout.setSpacing(6)

            # Onefile option
            self._opt_onefile = add_form_checkbox(
                build_layout, "Mode:", "Onefile", "opt_onefile_dynamic"
            )

            # Windowed option
            self._opt_windowed = add_form_checkbox(
                build_layout, "Console:", "Windowed", "opt_windowed_dynamic"
            )
            build_group.setLayout(build_layout)

            assets_group = QGroupBox("Assets", tab)
            assets_layout = QVBoxLayout()
            assets_layout.setSpacing(6)

            # Icon button + path input
            self._btn_select_icon, self._icon_path_input = add_icon_selector(
                assets_layout,
                "🎨 Choisir une icône (.ico)",
                self.select_icon,
                "btn_select_icon_dynamic",
                "pyinstaller_icon_path_input_dynamic",
            )
            if self._icon_path_input is not None:
                self._icon_path_input.textChanged.connect(self._on_icon_path_changed)
            assets_group.setLayout(assets_layout)

            output_group = QGroupBox("Output", tab)
            output_layout = QVBoxLayout()
            output_layout.setSpacing(6)

            # Output directory
            self._output_dir_input = add_output_dir(
                output_layout,
                "Dossier de sortie (--distpath). Laisser vide pour ./dist",
                "output_dir_input_dynamic",
            )
            output_group.setLayout(output_layout)

            hint = QLabel(
                "Tip: choose one packaging mode, then optionally add an icon and custom dist path.",
                tab,
            )
            hint.setStyleSheet("color: #888; font-size: 11px;")
            hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            layout.addWidget(build_group)
            layout.addWidget(assets_group)
            layout.addWidget(output_group)
            layout.addWidget(hint)
            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, "PyInstaller"

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    log_with_level(
                        gui, "error", f"Erreur création onglet PyInstaller: {e}"
                    )
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
            if hasattr(self, "_icon_path_input") and self._icon_path_input is not None:
                icon_path = self._icon_path_input.text().strip()
            if (
                not icon_path
                and hasattr(self, "_selected_icon")
                and self._selected_icon
            ):
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
            self._config_overrides = dict(cfg)
        except Exception:
            self._config_overrides = {}
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
            # Apply translations to UI elements if they exist
            if hasattr(self, "_opt_onefile"):
                self._opt_onefile.setText(
                    self.engine_translate("onefile_checkbox", "Onefile")
                )
            if hasattr(self, "_opt_windowed"):
                self._opt_windowed.setText(
                    self.engine_translate("windowed_checkbox", "Windowed")
                )
            if hasattr(self, "_btn_select_icon"):
                self._btn_select_icon.setText(
                    self.engine_translate("icon_button", "Select icon")
                )
            if hasattr(self, "_output_dir_input"):
                self._output_dir_input.setPlaceholderText(
                    self.engine_translate("output_placeholder", "Output directory")
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
                if (
                    hasattr(self, "_icon_path_input")
                    and self._icon_path_input is not None
                ):
                    self._icon_path_input.setText(file_path)
                if hasattr(self._gui, "log"):
                    self._gui.log.append(
                        f"Icône sélectionnée pour PyInstaller : {file_path}"
                    )
        except Exception as e:
            if hasattr(self._gui, "log"):
                log_with_level(
                    self._gui, "error", f"Erreur lors de la sélection de l'icône : {e}"
                )
