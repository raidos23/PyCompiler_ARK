# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

from pycompiler_ark.engine_sdk import (
    BuildContext,
    CompilerEngine,
    engine_register,
    translate,
)
from pycompiler_ark.engine_sdk.utils import log_with_level


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
    version: str = "1.1.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Return required tools for PyInstaller compilation."""
        return {"python": ["pyinstaller"], "system": []}

    def preflight(self, gui, file: str) -> bool:
        """Preflight check - dependencies are handled automatically by required_tools."""
        return True

    def build_command(self, context: BuildContext) -> list[str]:
        """Build a PyInstaller command line from a normalized build context."""
        cfg = getattr(self, "_config_overrides", {})
        if not isinstance(cfg, dict):
            cfg = {}

        # Resolve executable (prefer venv if available)
        python_exe = sys.executable
        if hasattr(self, "_gui") and self._gui:
            venv_manager = getattr(self._gui, "venv_manager", None)
            if venv_manager:
                venv_path = venv_manager.resolve_project_venv()
                if venv_path:
                    python_exe = venv_manager.python_path(venv_path)

        cmd = [python_exe, "-m", "PyInstaller", "--noconfirm"]

        onefile_enabled = bool(cfg.get("onefile", False))
        if hasattr(self, "_opt_onefile") and self._opt_onefile is not None:
            onefile_enabled = bool(self._opt_onefile.isChecked())
        cmd.append("--onefile" if onefile_enabled else "--onedir")

        windowed_enabled = bool(cfg.get("windowed", False))
        if hasattr(self, "_opt_windowed") and self._opt_windowed is not None:
            windowed_enabled = bool(self._opt_windowed.isChecked())
        if windowed_enabled and platform.system() in {"Windows", "Darwin"}:
            cmd.append("--windowed")

        output_dir = str(context.output_dir or "").strip()
        if output_dir:
            cmd.extend(["--distpath", output_dir])

        icon_path = str(context.icon or "").strip()
        if icon_path:
            cmd.extend(["--icon", icon_path])

        output_name = str(context.project_name or "").strip()
        if output_name:
            cmd.extend(["--name", output_name])

        for pattern in context.exclude_packages:
            module = (
                str(pattern)
                .replace("/**/*", "")
                .replace("**/*", "")
                .replace("/**", "")
                .strip("/")
            )
            if module and "*" not in module:
                cmd.extend(["--exclude-module", module.replace("/", ".")])

        for module in context.include_packages:
            if module.strip():
                cmd.extend(["--collect-all", module.strip()])

        separator = ";" if platform.system() == "Windows" else ":"
        for mapping in context.data_mappings:
            source = str((mapping or {}).get("source") or "").strip()
            destination = str((mapping or {}).get("destination") or "").strip()
            # mapping_type = str((mapping or {}).get("type") or "dir").strip().lower()

            if source and destination:
                cmd.extend(["--add-data", f"{source}{separator}{destination}"])

        cmd.append(context.entry_point)
        return cmd

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
            if hasattr(gui, "log"):
                log_with_level(
                    gui,
                    "success",
                    "Compilation PyInstaller terminée avec succès.",
                )
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
                QGroupBox,
                QLabel,
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

            build_group = QGroupBox(translate(self.id, "build_group", "Build"), tab)
            build_layout = QFormLayout()
            build_layout.setSpacing(6)

            # Onefile option
            self._opt_onefile = QCheckBox(
                translate(self.id, "onefile_checkbox", "Onefile")
            )
            self._opt_onefile.setObjectName("opt_onefile_dynamic")
            build_layout.addRow(translate(self.id, "mode_label", "Mode:"), self._opt_onefile)

            # Windowed option
            self._opt_windowed = QCheckBox(
                translate(self.id, "windowed_checkbox", "Windowed")
            )
            self._opt_windowed.setObjectName("opt_windowed_dynamic")
            build_layout.addRow(self._opt_windowed)

            build_group.setLayout(build_layout)

            hint = QLabel(
                translate(
                    self.id,
                    "hint_text",
                    "Tip: choose one packaging mode and console visibility. Global icon and output are managed in ark.yml.",
                ),
                tab,
            )
            hint.setStyleSheet("color: #888; font-size: 11px;")
            hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            layout.addWidget(build_group)
            layout.addWidget(hint)
            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, translate(self.id, "tab_label", "PyInstaller")

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

    def select_icon(self) -> None:
        """Legacy select_icon method. Global icon is now managed in ark.yml."""
        pass
