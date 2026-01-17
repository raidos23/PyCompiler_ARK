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

from __future__ import annotations

from typing import Optional


class CompilerEngine:
    """
    Base class for a pluggable compilation engine.

    An engine is responsible for:
    - building the command (program, args) for a given file and GUI state
    - performing preflight checks (venv tools, system dependencies)
    - post-success hooks (e.g., open output folder)

    Engines must be stateless or keep minimal transient state; GUI state is
    provided via the `gui` object.
    """

    id: str = "base"
    name: str = "BaseEngine"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    def preflight(self, gui, file: str) -> bool:
        """Perform preflight checks and setup. Return True if OK, False to abort."""
        return True

    def build_command(self, gui, file: str) -> list[str]:
        """Return the full command list including the program at index 0."""
        raise NotImplementedError

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        """
        Resolve the program (executable path) and its arguments for QProcess.
        Default implementation splits build_command into program and args.
        Return None to abort.
        """
        cmd = self.build_command(gui, file)
        if not cmd:
            return None
        return cmd[0], cmd[1:]

    def on_success(self, gui, file: str) -> None:
        """Hook called when a build is successful."""
        pass

    def create_tab(self, gui):
        """
        Optionally create and return a QWidget tab and its label for the GUI.
        Return value: (widget, label: str) or None if the engine does not add a tab.
        The engine is responsible for creating its own controls and wiring signals.
        """
        return None

    def environment(self, gui, file: str) -> Optional[dict[str, str]]:
        """
        Optionally return a mapping of environment variables to inject for the engine process.
        Values here will override the current process environment. Return None for no changes.
        """
        return None

    def should_compile_file(
        self, gui, file: str, selected_files: list[str], python_files: list[str]
    ) -> bool:
        """
        Determine if a file should be included in the compilation queue.
        Called by the compiler to filter files based on engine-specific criteria.
        Default implementation returns True for all files.
        Override to implement custom filtering logic.
        """
        return True

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """
        Return dict of required tools with installation modes.
        Keys: 'python' for pip-installable tools, 'system' for system packages.
        Used by VenvManager for Python tools and system installer for system tools.
        Example: {'python': ['pyinstaller'], 'system': ['build-essential']}
        """
        return {'python': [], 'system': []}

    def ensure_tools_installed(self, gui) -> bool:
        """
        Ensure all required tools are installed.
        Returns True if all tools are ready, False if installation failed or was cancelled.
        Handles both Python (pip) and system packages.
        """
        try:
            tools = self.required_tools
            python_tools = tools.get('python', [])
            system_tools = tools.get('system', [])

            # Check if VenvManager is available
            if hasattr(gui, 'venv_manager') and gui.venv_manager:
                venv_root = gui.venv_manager.resolve_project_venv()
                if venv_root:
                    # Install Python tools via VenvManager
                    if python_tools:
                        try:
                            gui.venv_manager.ensure_tools_installed(venv_root, python_tools)
                            # Wait for completion (simplified - in practice would need async handling)
                        except Exception as e:
                            if hasattr(gui, 'log') and gui.log:
                                gui.log.append(f"⚠️ Failed to install Python tools {python_tools}: {e}")
                            return False

            # Install system tools
            if system_tools:
                try:
                    from Core.sys_deps import install_system_packages
                    success = install_system_packages(system_tools, gui)
                    if not success:
                        if hasattr(gui, 'log') and gui.log:
                            gui.log.append(f"⚠️ Failed to install system tools {system_tools}")
                        return False
                except Exception as e:
                    if hasattr(gui, 'log') and gui.log:
                        gui.log.append(f"⚠️ Failed to install system tools {system_tools}: {e}")
                    return False

            return True
        except Exception as e:
            if hasattr(gui, 'log') and gui.log:
                gui.log.append(f"⚠️ Error ensuring tools installed: {e}")
            return False

    def apply_i18n(self, gui, tr: dict) -> None:
        """
        Apply internationalization translations to the engine UI.
        Default implementation does nothing - engines should override this.
        """
        pass

    def get_log_prefix(self, file_basename: str) -> str:
        """
        Return a log prefix string for the engine's compilation messages.
        Default includes engine name and version.
        """
        return f"{self.name} ({self.version})"
