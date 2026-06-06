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

from pycompiler_ark.engine_sdk import (
    BuildContext,
    CompilerEngine,
    add_form_checkbox,
    add_output_dir,
    engine_register,
)
from pycompiler_ark.engine_sdk.utils import log_with_level


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
    version: str = "1.1.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Return required tools for CX_Freeze compilation."""
        return {"python": ["cx_freeze"], "system": []}

    def preflight(self, gui, file: str) -> bool:
        """Preflight check - dependencies are handled automatically by required_tools."""
        return True

    def build_command(self, context: BuildContext) -> list[str]:
        """Build a cx_Freeze command line from a normalized build context."""
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

        cmd = [python_exe, "-m", "cx_Freeze"]

        windowed_enabled = bool(cfg.get("windowed", False))
        if hasattr(self, "_cx_windowed") and self._cx_windowed is not None:
            windowed_enabled = bool(self._cx_windowed.isChecked())
        if windowed_enabled and platform.system() == "Windows":
            cmd.extend(["--base", "Win32GUI"])

        output_dir = str(context.output_dir or "").strip()
        if output_dir:
            cmd.extend(["--target-dir", output_dir])

        icon_path = str(context.icon or "").strip()
        if icon_path:
            cmd.extend(["--icon", icon_path])

        target_name = str(context.project_name or "").strip()
        if target_name:
            cmd.extend(["--target-name", target_name])

        debug_enabled = bool(cfg.get("debug", False))
        if hasattr(self, "_cx_debug") and self._cx_debug is not None:
            debug_enabled = bool(self._cx_debug.isChecked())
        if debug_enabled:
            cmd.append("--debug")

        verbose_enabled = bool(cfg.get("verbose", False))
        if hasattr(self, "_cx_verbose") and self._cx_verbose is not None:
            verbose_enabled = bool(self._cx_verbose.isChecked())
        if verbose_enabled:
            cmd.append("--verbose")

        # cx_Freeze CLI can be finicky with repeated flags vs comma-separated.
        # Repeating with --opt=val is generally the most robust for distutils parsers.
        for module in context.include_packages:
            m = str(module).strip()
            if m:
                cmd.append(f"--includes={m}")

        for mapping in context.data_mappings:
            source = str((mapping or {}).get("source") or "").strip()
            # CX_FREEZE CLI HACK: 
            # 1. Remove trailing slashes which confuse path resolution
            # 2. Avoid ':' destination mapping in CLI as it is often misinterpreted
            #    as part of the filename. Default behavior preserves the name.
            source = source.rstrip("/").rstrip("\\")
            if source:
                cmd.append(f"--include-files={source}")

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
                    "Compilation CX_Freeze terminée avec succès.",
                )
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
                QGroupBox,
                QLabel,
                QSizePolicy,
                QVBoxLayout,
                QWidget,
            )

            # Create the tab widget
            tab = QWidget()
            tab.setObjectName("tab_cx_freeze_dynamic")

            # Create main layout
            layout = QVBoxLayout(tab)
            layout.setSpacing(8)
            layout.setContentsMargins(8, 8, 8, 8)

            build_group = QGroupBox("Build", tab)
            build_layout = QFormLayout()
            build_layout.setSpacing(6)

            # Windowed option
            self._cx_windowed = add_form_checkbox(
                build_layout, "Console:", "No console", "cx_windowed_dynamic"
            )
            self._cx_windowed.setToolTip("Disable the console window.")
            build_group.setLayout(build_layout)

            diagnostics_group = QGroupBox("Diagnostics", tab)
            diagnostics_layout = QVBoxLayout()
            diagnostics_layout.setSpacing(4)

            self._cx_debug = QCheckBox("Debug")
            self._cx_debug.setObjectName("cx_debug_dynamic")
            self._cx_debug.setToolTip("Enable debug output.")
            diagnostics_layout.addWidget(self._cx_debug)

            self._cx_verbose = QCheckBox("Verbose")
            self._cx_verbose.setObjectName("cx_verbose_dynamic")
            self._cx_verbose.setToolTip("Enable verbose output.")
            diagnostics_layout.addWidget(self._cx_verbose)
            diagnostics_group.setLayout(diagnostics_layout)

            hint = QLabel(
                "Tip: use the console visibility option. Global icon and output are managed in ark.yml.",
                tab,
            )
            hint.setStyleSheet("color: #888; font-size: 11px;")
            hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

            layout.addWidget(build_group)
            layout.addWidget(diagnostics_group)
            layout.addWidget(hint)
            layout.addStretch()

            # Store references in the engine instance for build_command access
            self._gui = gui

            return tab, "CX_Freeze"

        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    log_with_level(
                        gui, "error", f"Erreur création onglet CX_Freeze: {e}"
                    )
            except Exception:
                pass
            return None

    def get_config(self, gui) -> dict:
        """Return a JSON-serializable snapshot of current CX_Freeze UI options."""
        try:
            cfg = {}
            if hasattr(self, "_cx_windowed") and self._cx_windowed is not None:
                cfg["windowed"] = bool(self._cx_windowed.isChecked())
            if hasattr(self, "_cx_debug") and self._cx_debug is not None:
                cfg["debug"] = bool(self._cx_debug.isChecked())
            if hasattr(self, "_cx_verbose") and self._cx_verbose is not None:
                cfg["verbose"] = bool(self._cx_verbose.isChecked())
            return cfg
        except Exception:
            return {}

    def set_config(self, gui, cfg: dict) -> None:
        """Apply a config dict to CX_Freeze UI widgets."""
        if not isinstance(cfg, dict):
            return
        try:
            self._config_overrides = dict(cfg)
        except Exception:
            self._config_overrides = {}
        try:
            if (
                hasattr(self, "_cx_windowed")
                and self._cx_windowed is not None
                and "windowed" in cfg
            ):
                self._cx_windowed.setChecked(bool(cfg.get("windowed")))
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
            # Apply translations to UI elements if they exist
            if hasattr(self, "_cx_windowed"):
                self._cx_windowed.setText(
                    self.engine_translate("windowed_checkbox", "Windowed")
                )
            if hasattr(self, "_cx_windowed"):
                self._cx_windowed.setToolTip(self.engine_translate("tt_windowed", ""))
            if hasattr(self, "_cx_debug"):
                self._cx_debug.setText(
                    self.engine_translate("debug_checkbox", "Debug mode")
                )
            if hasattr(self, "_cx_debug"):
                self._cx_debug.setToolTip(self.engine_translate("tt_debug", ""))
            if hasattr(self, "_cx_verbose"):
                self._cx_verbose.setText(
                    self.engine_translate("verbose_checkbox", "Verbose output")
                )
            if hasattr(self, "_cx_verbose"):
                self._cx_verbose.setToolTip(self.engine_translate("tt_verbose", ""))
        except Exception:
            pass

    def select_icon(self) -> None:
        """Legacy select_icon method. Global icon is now managed in ark.yml."""
        pass
