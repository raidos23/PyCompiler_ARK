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

import os
import platform
import sys
from typing import Optional

from engine_sdk.base import CompilerEngine
from engine_sdk import register



@register
class NuitkaEngine(CompilerEngine):
    """
    Nuitka compilation engine.
    
    Features:
    - Standalone and onefile modes
    - Python include options
    - Plugin support
    - MSVC/Clang/LLVM backend selection
    - Data files inclusion
    - Icon specification
    """

    id: str = "nuitka"
    name: str = "Nuitka"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    @property
    def required_tools(self) -> list[str]:
        return ["nuitka"]

    def preflight(self, gui, file: str) -> bool:
        """Check if Nuitka is available in the venv."""
        try:
            venv_manager = getattr(gui, "venv_manager", None)
            if not venv_manager:
                return True  # Let build_command fail instead
            
            venv_path = venv_manager.resolve_project_venv()
            if not venv_path:
                return True  # Let build_command fail instead
            
            if not venv_manager.has_tool_binary(venv_path, "nuitka"):
                # Try to install nuitka
                venv_manager.ensure_tools_installed(venv_path, ["nuitka"])
                return False  # Will be retried after installation
            
            return True
        except Exception:
            return True  # Let build_command handle errors

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
            
            # Use existing UI widgets from .ui file
            # Standalone mode
            standalone = getattr(gui, "nuitka_standalone", None)
            if standalone and standalone.isChecked():
                cmd.append("--standalone")
            
            # Onefile mode
            onefile = getattr(gui, "nuitka_onefile", None)
            if onefile and onefile.isChecked():
                cmd.append("--onefile")
            
            # Windowed (no console)
            disable_console = getattr(gui, "nuitka_disable_console", None)
            if disable_console and disable_console.isChecked():
                cmd.append("--windows-disable-console")
            
            # Show progress
            show_progress = getattr(gui, "nuitka_show_progress", None)
            if show_progress and show_progress.isChecked():
                cmd.append("--show-progress")
            
            # Output directory
            output_dir = getattr(gui, "nuitka_output_dir", None)
            if output_dir and output_dir.text().strip():
                cmd.extend(["--output-dir", output_dir.text().strip()])
            
            # Add the target file
            cmd.append(file)
            
            return cmd
            
        except Exception as e:
            try:
                if hasattr(gui, "log"):
                    gui.log.append(f"❌ Erreur construction commande Nuitka: {e}\n")
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
            output_dir = getattr(gui, "nuitka_output_dir", None)
            if output_dir and output_dir.text().strip():
                try:
                    if hasattr(gui, "log"):
                        gui.log.append(f"📁 Compilation Nuitka terminée. Sortie dans: {output_dir.text().strip()}\n")
                except Exception:
                    pass
        except Exception:
            pass

    def create_tab(self, gui):
        """
        Return None to use existing UI widgets from the .ui file.
        The Nuitka tab is already defined in the UI with nuitka_onefile,
        nuitka_standalone, nuitka_disable_console, nuitka_show_progress,
        nuitka_output_dir, etc.
        """
        return None

    def get_log_prefix(self, file_basename: str) -> str:
        return f"Nuitka ({self.version})"

    def should_compile_file(self, gui, file: str, selected_files: list[str], python_files: list[str]) -> bool:
        """Determine if a file should be included in the compilation queue."""
        # Skip non-Python files
        if not file.endswith(".py"):
            return False
        return True

    def apply_i18n(self, gui, tr: dict) -> None:
        """Apply internationalization translations to the engine UI."""
        pass

