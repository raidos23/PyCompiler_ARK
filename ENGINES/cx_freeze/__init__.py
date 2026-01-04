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
supporting onefile mode, windowed applications, and various customization options.
"""

from __future__ import annotations

import os
import platform
import sys
from typing import Optional

from Core.engines_loader.base import CompilerEngine
from Core.engines_loader.registry import register


@register
class CXFreezeEngine(CompilerEngine):
    """
    CX_Freeze compilation engine.
    
    Features:
    - Onefile and onedir modes
    - Windowed/console mode selection
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
    def required_tools(self) -> list[str]:
        return ["cx_freeze"]

    def preflight(self, gui, file: str) -> bool:
        """Check if CX_Freeze is available in the venv."""
        try:
            venv_manager = getattr(gui, "venv_manager", None)
            if not venv_manager:
                return True  # Let build_command fail instead
            
            venv_path = venv_manager.resolve_project_venv()
            if not venv_path:
                return True  # Let build_command fail instead
            
            if not venv_manager.has_tool_binary(venv_path, "cx_freeze"):
                # Try to install cx_freeze
                venv_manager.ensure_tools_installed(venv_path, ["cx_freeze"])
                return False  # Will be retried after installation
            
            return True
        except Exception:
            return True  # Let build_command handle errors

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
            
            # Get options from GUI - use existing UI widgets from .ui file
            # Onefile vs Onedir (CX_Freeze uses --onefile)
            onefile = getattr(gui, "opt_onefile", None)
            if onefile and onefile.isChecked():
                cmd.append("--onefile")
            else:
                # CX_Freeze defaults to onedir (build-exe directory)
                cmd.append("--build-exe")
            
            # Windowed (no console) - CX_Freeze uses --console or implies GUI
            windowed = getattr(gui, "opt_windowed", None)
            if windowed and windowed.isChecked():
                # CX_Freeze uses --gui-name for windowed apps
                cmd.append("--gui-name=pythonw")
            
            # Clean build
            clean = getattr(gui, "opt_clean", None)
            if clean and clean.isChecked():
                cmd.append("--clean")
            
            # Output directory - CX_Freeze uses --build-dir
            output_dir = getattr(gui, "output_dir_input", None)
            if output_dir and output_dir.text().strip():
                cmd.extend(["--build-dir", output_dir.text().strip()])
            
            # Name - CX_Freeze uses --name
            name_input = getattr(gui, "output_name_input", None)
            if name_input and name_input.text().strip():
                cmd.extend(["--name", name_input.text().strip()])
            
            # Add the target file
            cmd.append(file)
            
            return cmd
            
        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(f"❌ Erreur construction commande CX_Freeze: {e}\n")
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
                        gui.log.append(f"📁 Compilation CX_Freeze terminée. Sortie dans: {output_dir.text().strip()}\n")
                except Exception:
                    pass
        except Exception:
            pass

    def create_tab(self, gui):
        """
        Return None to use existing UI widgets from the .ui file.
        The CX_Freeze tab is already defined in the UI with opt_onefile, 
        opt_windowed, opt_clean, output_dir_input, etc.
        """
        return None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"CX_Freeze ({self.version})"

    def should_compile_file(self, gui, file: str, selected_files: list[str], python_files: list[str]) -> bool:
        """Determine if a file should be included in the compilation queue."""
        # Skip non-Python files
        if not file.endswith(".py"):
            return False
        return True

    def apply_i18n(self, gui, tr: dict) -> None:
        """Apply internationalization translations to the engine UI."""
        pass

