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

    def get_config(self, gui) -> dict:
        """Return a JSON-serializable dict of current engine UI options."""
        return {}

    def set_config(self, gui, cfg: dict) -> None:
        """Apply a config dict to engine UI widgets."""
        pass

    def environment(self) -> Optional[dict[str, str]]:
        """
        Optionally return a mapping of environment variables to inject for the engine process.
        Values here will override the current process environment. Return None for no changes.
        """
        return None

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """
        Return dict of required tools with installation modes.
        Keys: 'python' for pip-installable tools, 'system' for system packages.
        Used by VenvManager for Python tools and system installer for system tools.
        Example: {'python': ['pyinstaller'], 'system': ['build-essential']}
        """
        return {"python": [], "system": []}

    def ensure_tools_installed(self, gui) -> bool:
        """
        Check if all required tools are installed, and install missing ones.
        Uses direct SysDependencyManager integration for system packages with full GUI support.
        Returns True if all tools are available or installation started, False if system tool installation failed.
        """
        try:
            tools = self.required_tools
            python_tools = tools.get("python", [])
            system_tools = tools.get("system", [])

            # Check Python tools using venv_manager
            if hasattr(gui, "venv_manager") and gui.venv_manager:
                venv_path = gui.venv_manager.resolve_project_venv()
                if venv_path and python_tools:
                    missing_python = []
                    for tool in python_tools:
                        if not gui.venv_manager.is_tool_installed(venv_path, tool):
                            missing_python.append(tool)
                    if missing_python:
                        if hasattr(gui, "log") and gui.log:
                            gui.log.append(
                                gui.tr(
                                    f"📦 Installation des outils Python manquants: {missing_python}",
                                    f"📦 Installing missing Python tools: {missing_python}",
                                )
                            )
                        gui.venv_manager.ensure_tools_installed(
                            venv_path, missing_python
                        )

            # Check and install system tools using direct SysDependencyManager
            if system_tools:
                try:
                    # Import and use SysDependencyManager directly for full GUI support
                    from Core.sys_deps import (
                        SysDependencyManager,
                        check_system_packages,
                    )

                    # Get or create the system dependency manager with GUI parent
                    if hasattr(gui, "sys_deps_manager") and gui.sys_deps_manager:
                        sys_manager = gui.sys_deps_manager
                    else:
                        sys_manager = SysDependencyManager(gui)

                    # Check which system tools are missing
                    missing_system = []
                    for tool in system_tools:
                        if not check_system_packages([tool]):
                            missing_system.append(tool)

                    if missing_system:
                        if hasattr(gui, "log") and gui.log:
                            gui.log.append(
                                gui.tr(
                                    f"📦 Installation des outils système manquants: {missing_system}",
                                    f"📦 Installing missing system tools: {missing_system}",
                                )
                            )

                        # Detect platform and use appropriate installation method
                        import platform

                        system = platform.system().lower()

                        if system == "linux":
                            # Use Linux package installation with progress dialog
                            process = sys_manager.install_packages_linux(missing_system)
                            if process:
                                # Wait for completion with timeout
                                if process.waitForFinished(600000):  # 10 minutes
                                    if process.exitCode() == 0:
                                        if hasattr(gui, "log") and gui.log:
                                            gui.log.append(
                                                gui.tr(
                                                    f"✅ Outils système installés avec succès: {missing_system}",
                                                    f"✅ System tools installed successfully: {missing_system}",
                                                )
                                            )
                                    else:
                                        if hasattr(gui, "log") and gui.log:
                                            gui.log.append(
                                                gui.tr(
                                                    f"❌ Échec installation outils système: {missing_system} (code: {process.exitCode()})",
                                                    f"❌ System tools installation failed: {missing_system} (code: {process.exitCode()})",
                                                )
                                            )
                                        return False
                                else:
                                    if hasattr(gui, "log") and gui.log:
                                        gui.log.append(
                                            gui.tr(
                                                "⏱️ Timeout lors de l'installation des outils système",
                                                "⏱️ Timeout during system tools installation",
                                            )
                                        )
                                    return False
                            else:
                                if hasattr(gui, "log") and gui.log:
                                    gui.log.append(
                                        gui.tr(
                                            "❌ Impossible de démarrer l'installation des outils système",
                                            "❌ Unable to start system tools installation",
                                        )
                                    )
                                return False

                        elif system == "windows":
                            # Convert package names to winget format for Windows
                            winget_packages = []
                            for tool in missing_system:
                                # Map common Linux package names to Windows equivalents
                                winget_map = {
                                    "build-essential": [
                                        {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                                    ],
                                    "gcc": [
                                        {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                                    ],
                                    "g++": [
                                        {"id": "Microsoft.VisualStudio.2022.BuildTools"}
                                    ],
                                    "python3-dev": [{"id": "Python.Python.3"}],
                                    "libpython3-dev": [{"id": "Python.Python.3"}],
                                    "patchelf": [],  # Not available on Windows
                                }
                                if tool in winget_map:
                                    winget_packages.extend(winget_map[tool])
                                else:
                                    # Try as generic package
                                    winget_packages.append({"id": tool})

                            if winget_packages:
                                process = sys_manager.install_packages_windows(
                                    winget_packages
                                )
                                if process:
                                    if process.waitForFinished(600000):  # 10 minutes
                                        if process.exitCode() == 0:
                                            if hasattr(gui, "log") and gui.log:
                                                gui.log.append(
                                                    gui.tr(
                                                        f"✅ Outils Windows installés: {missing_system}",
                                                        f"✅ Windows tools installed: {missing_system}",
                                                    )
                                                )
                                        else:
                                            if hasattr(gui, "log") and gui.log:
                                                gui.log.append(
                                                    gui.tr(
                                                        f"❌ Échec installation Windows: {missing_system}",
                                                        f"❌ Windows installation failed: {missing_system}",
                                                    )
                                                )
                                            return False
                                    else:
                                        if hasattr(gui, "log") and gui.log:
                                            gui.log.append(
                                                gui.tr(
                                                    "⏱️ Timeout lors de l'installation Windows",
                                                    "⏱️ Timeout during Windows installation",
                                                )
                                            )
                                        return False
                                else:
                                    if hasattr(gui, "log") and gui.log:
                                        gui.log.append(
                                            gui.tr(
                                                "⚠️ winget non disponible, installation manuelle requise",
                                                "⚠️ winget not available, manual installation required",
                                            )
                                        )
                                    # Open documentation URL for manual installation
                                    sys_manager.open_urls(
                                        [
                                            "https://learn.microsoft.com/en-us/windows/package-manager/winget/"
                                        ]
                                    )
                                    return False
                            else:
                                if hasattr(gui, "log") and gui.log:
                                    gui.log.append(
                                        gui.tr(
                                            f"⚠️ Aucun équivalent Windows pour: {missing_system}",
                                            f"⚠️ No Windows equivalent for: {missing_system}",
                                        )
                                    )
                        else:
                            if hasattr(gui, "log") and gui.log:
                                gui.log.append(
                                    gui.tr(
                                        "⚠️ Plateforme non supportée pour l'installation automatique",
                                        "⚠️ Platform not supported for automatic installation",
                                    )
                                )
                                return False
                    else:
                        if hasattr(gui, "log") and gui.log:
                            gui.log.append(
                                gui.tr(
                                    f"✅ Tous les outils système sont déjà installés: {system_tools}",
                                    f"✅ All system tools are already installed: {system_tools}",
                                )
                            )

                except Exception as e:
                    if hasattr(gui, "log") and gui.log:
                        gui.log.append(
                            gui.tr(
                                f"⚠️ Erreur lors de la vérification/installation des outils système: {e}",
                                f"⚠️ Error checking/installing system tools: {e}",
                            )
                        )
                    return False

            return True
        except Exception as e:
            if hasattr(gui, "log") and gui.log:
                gui.log.append(
                    gui.tr(
                        f"⚠️ Erreur dans ensure_tools_installed: {e}",
                        f"⚠️ Error in ensure_tools_installed: {e}",
                    )
                )
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
