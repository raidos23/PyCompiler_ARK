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

from engine_sdk.base import CompilerEngine
from engine_sdk import register


@register
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
    def required_tools(self) -> list[str]:
        return ["pyinstaller"]

    def preflight(self, gui, file: str) -> bool:
        """Check if PyInstaller is available in the venv."""
        try:
            venv_manager = getattr(gui, "venv_manager", None)
            if not venv_manager:
                return True  # Let build_command fail instead
            
            venv_path = venv_manager.resolve_project_venv()
            if not venv_path:
                return True  # Let build_command fail instead
            
            if not venv_manager.has_tool_binary(venv_path, "pyinstaller"):
                # Try to install pyinstaller
                venv_manager.ensure_tools_installed(venv_path, ["pyinstaller"])
                return False  # Will be retried after installation
            
            return True
        except Exception:
            return True  # Let build_command handle errors

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
            
            # Get options from GUI - use existing UI widgets from .ui file
            # Onefile vs Onedir
            onefile = getattr(gui, "opt_onefile", None)
            if onefile and onefile.isChecked():
                cmd.append("--onefile")
            else:
                cmd.append("--onedir")
            
            # Windowed (no console) - only on Windows/macOS
            windowed = getattr(gui, "opt_windowed", None)
            if windowed and windowed.isChecked():
                if platform.system() == "Windows":
                    cmd.append("--windowed")
                elif platform.system() == "Darwin":
                    cmd.append("--windowed")
            
            # Clean build
            clean = getattr(gui, "opt_clean", None)  # UI uses opt_clean, not opt_clean_build
            if clean and clean.isChecked():
                cmd.append("--clean")
            
            # No UPX
            noupx = getattr(gui, "opt_noupx", None)
            if noupx and noupx.isChecked():
                cmd.append("--noupx")
            
            # Output directory - use output_dir_input from UI
            output_dir = getattr(gui, "output_dir_input", None)
            if output_dir and output_dir.text().strip():
                cmd.extend(["--distpath", output_dir.text().strip()])
            
            # Icon
            if platform.system() == "Windows":
                # Try btn_select_icon callback for icon path
                btn_icon = getattr(gui, "btn_select_icon", None)
                if btn_icon and hasattr(self, "_selected_icon"):
                    cmd.extend(["--icon", self._selected_icon])
            
            # Name
            # Check if there's a name input in the UI
            name_input = getattr(gui, "output_name_input", None)
            if name_input and name_input.text().strip():
                cmd.extend(["--name", name_input.text().strip()])
            
            # Add the target file
            cmd.append(file)
            
            return cmd
            
        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(f"❌ Erreur construction commande PyInstaller: {e}\n")
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
            output_dir = getattr(gui, "output_dir_input", None)
            if output_dir and output_dir.text().strip():
                try:
                    if hasattr(gui, "log"):
                        gui.log.append(f"📁 Sortie générée dans: {output_dir.text().strip()}\n")
                except Exception:
                    pass
        except Exception:
            pass

    def create_tab(self, gui):
        """
        Return None to use existing UI widgets from the .ui file.
        The PyInstaller tab is already defined in the UI with opt_onefile, 
        opt_windowed, opt_clean, output_dir_input, etc.
        """
        return None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"PyInstaller ({self.version})"

    def should_compile_file(self, gui, file: str, selected_files: list[str], python_files: list[str]) -> bool:
        """Determine if a file should be included in the compilation queue."""
        # Skip non-Python files
        if not file.endswith(".py"):
            return False
        return True

    def apply_i18n(self, gui, tr: dict) -> None:
        """Apply internationalization translations to the engine UI."""
        pass

