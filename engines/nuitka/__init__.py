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

    def build_command(self, context: BuildContext) -> list[str]:
        """Build a Nuitka command line from a normalized build context."""
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

        cmd = [python_exe, "-m", "nuitka"]

        standalone_enabled = bool(cfg.get("standalone", False))
        if hasattr(self, "_nuitka_standalone") and self._nuitka_standalone is not None:
            standalone_enabled = bool(self._nuitka_standalone.isChecked())
        if standalone_enabled:
            cmd.append("--standalone")

        onefile_enabled = bool(cfg.get("onefile", False))
        if hasattr(self, "_nuitka_onefile") and self._nuitka_onefile is not None:
            onefile_enabled = bool(self._nuitka_onefile.isChecked())
        if onefile_enabled:
            cmd.append("--onefile")

        disable_console = bool(cfg.get("disable_console", False))
        if (
            hasattr(self, "_nuitka_disable_console")
            and self._nuitka_disable_console is not None
        ):
            disable_console = bool(self._nuitka_disable_console.isChecked())
        if disable_console:
            cmd.append("--windows-disable-console")

        output_dir = str(context.output_dir or "").strip()
        if output_dir:
            cmd.append(f"--output-dir={output_dir}")

        output_name = str(context.project_name or "").strip()
        if output_name:
            cmd.append(f"--output-filename={output_name}")

        icon_path = str(context.icon or "").strip()
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

        for module in context.include_packages:
            if module.strip():
                cmd.append(f"--include-package={module.strip()}")

        for mapping in context.data_mappings:
            source = str((mapping or {}).get("source") or "").strip()
            destination = str((mapping or {}).get("destination") or "").strip()
            mapping_type = str((mapping or {}).get("type") or "dir").strip().lower()

            if source and destination:
                if mapping_type == "file":
                    cmd.append(f"--include-data-files={source}={destination}")
                else:
                    # Default to dir for backward compatibility or explicit dir type
                    cmd.append(f"--include-data-dir={source}={destination}")

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
                    "Compilation Nuitka terminée avec succès.",
                )
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
                QGroupBox,
                QLabel,
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

            hint = QLabel(
                "Tip: combine standalone or onefile modes carefully. Global icon and output are managed in ark.yml.",
                tab,
            )
            hint.setStyleSheet("color: #888; font-size: 11px;")
            hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            layout.addWidget(build_group)
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
        except Exception:
            pass

    def select_icon(self) -> None:
        """Legacy select_icon method. Global icon is now managed in ark.yml."""
        pass
