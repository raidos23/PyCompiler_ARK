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

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from Core.engine.build_context import BuildContext


def log_i18n_level(gui, level: str, fr: str, en: str) -> None:
    """Minimal i18n log helper to avoid EngineLoader <-> engine_sdk circular imports."""
    try:
        if hasattr(gui, "tr") and callable(getattr(gui, "tr")):
            msg = gui.tr(fr, en)
        else:
            cur = getattr(gui, "current_language", "")
            if isinstance(cur, str) and cur.lower().startswith("fr"):
                msg = fr
            else:
                msg = en
    except Exception:
        msg = en

    labels = {
        "info": "INFO",
        "warning": "WARN",
        "error": "ERROR",
        "success": "SUCCESS",
        "state": "STATE",
    }
    try:
        lvl = str(level).lower()
    except Exception:
        lvl = "info"
    label = labels.get(lvl, str(level).upper())
    line = f"[{label}] {msg}"
    try:
        if hasattr(gui, "log"):
            log_obj = getattr(gui, "log")
            if hasattr(log_obj, "append"):
                log_obj.append(line)
                return
    except Exception:
        pass
    try:
        print(line)
    except Exception:
        pass


def _tools_stage_message(stage: str, fr: str, en: str) -> tuple[str, str]:
    prefix = f"[tools:{stage}] "
    return prefix + fr, prefix + en


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

    def build_command(self, context: "BuildContext") -> list[str]:
        """
        Return the full command list for a normalized build context.

        This is the primary entry point for command generation. Engines should
        use the provided `context` for project settings and `self._config_overrides`
        for engine-specific options.
        """
        raise NotImplementedError

    def program_and_args(self, context: "BuildContext") -> Optional[tuple[str, list[str]]]:
        """
        Resolve the program and arguments for a normalized build context.
        Default implementation splits `build_command`.
        """
        cmd = self.build_command(context)
        if not cmd:
            return None
        return cmd[0], cmd[1:]

    def on_success(self, gui, file: str) -> None:
        """Hook called when a build is successful."""
        pass

    def engine_translate(self, key: str, default: Optional[str] = None) -> str:
        """Translate an engine-local key using the shared engine i18n registry."""
        try:
            from .registry import engine_translate as _engine_translate

            return _engine_translate(self, key, default)
        except Exception:
            return default if default is not None else str(key)

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

    def config_policy(self, gui) -> dict:
        """
        Define how the engine wants its config to be handled.

        Return a dict with any of:
        - read (bool): allow Core to read/apply config
        - write (bool): allow Core to persist config
        - ui_edit (bool): allow UI-driven save of config
        """
        return {"read": True, "write": True, "ui_edit": True}

    def load_config(self, gui, workspace_dir: str) -> Optional[dict]:
        """
        Optional custom config loader for special engines.
        Return a dict (payload or options). Return None to use default storage.
        """
        return None

    def save_config(self, gui, workspace_dir: str, options: dict) -> Optional[bool]:
        """
        Optional custom config saver for special engines.
        Return True/False to override default save, or None to use default storage.
        """
        return None

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
        Example: {'python': ['<tool_name>'], 'system': ['<system_package>']}
        """
        return {"python": [], "system": []}

    def ensure_tools_installed(self, gui, stop_signal: Optional[Callable[[], bool]] = None) -> bool:
        """
        Check if all required tools are installed, and install missing ones.
        Uses direct SysDependencyManager integration for system packages with full GUI support.
        Returns True if all tools are available or installation started, False if system tool installation failed.
        """
        try:
            tools = self.required_tools
            python_tools = tools.get("python", [])
            system_tools = tools.get("system", [])
            system_install_ok = True

            # Check and install system tools first to avoid overlapping system/Python installs.
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
                        log_i18n_level(
                            gui,
                            "info",
                            *_tools_stage_message(
                                "system",
                                f"Installation des outils système manquants: {missing_system}",
                                f"Installing missing system tools: {missing_system}",
                            ),
                        )

                        # Detect platform and use appropriate installation method
                        import platform

                        system = platform.system().lower()

                        if system == "linux":
                            # Use Linux package installation with progress dialog
                            process = sys_manager.install_packages_linux(missing_system)
                            if process:
                                # Wait for completion with timeout, but check stop_signal
                                timeout_total = 600000 # 10 minutes
                                elapsed = 0
                                interval = 500 # 0.5s
                                while not process.waitForFinished(interval):
                                    if stop_signal and stop_signal():
                                        process.terminate()
                                        process.waitForFinished(1000)
                                        process.kill()
                                        return False
                                    elapsed += interval
                                    if elapsed >= timeout_total:
                                        log_i18n_level(
                                            gui,
                                            "warning",
                                            *_tools_stage_message(
                                                "system",
                                                "Timeout lors de l'installation des outils système",
                                                "Timeout during system tools installation",
                                            ),
                                        )
                                        system_install_ok = False
                                        break
                                
                                if system_install_ok:
                                    if process.exitCode() == 0:
                                        log_i18n_level(
                                            gui,
                                            "success",
                                            *_tools_stage_message(
                                                "system",
                                                f"Outils système installés avec succès: {missing_system}",
                                                f"System tools installed successfully: {missing_system}",
                                            ),
                                        )
                                    else:
                                        log_i18n_level(
                                            gui,
                                            "error",
                                            *_tools_stage_message(
                                                "system",
                                                f"Échec installation outils système: {missing_system} (code: {process.exitCode()})",
                                                f"System tools installation failed: {missing_system} (code: {process.exitCode()})",
                                            ),
                                        )
                                        system_install_ok = False
                            else:
                                log_i18n_level(
                                    gui,
                                    "error",
                                    *_tools_stage_message(
                                        "system",
                                        "Impossible de démarrer l'installation des outils système",
                                        "Unable to start system tools installation",
                                    ),
                                )
                                system_install_ok = False

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
                                    timeout_total = 600000 # 10 minutes
                                    elapsed = 0
                                    interval = 500 # 0.5s
                                    while not process.waitForFinished(interval):
                                        if stop_signal and stop_signal():
                                            process.terminate()
                                            process.waitForFinished(1000)
                                            process.kill()
                                            return False
                                        elapsed += interval
                                        if elapsed >= timeout_total:
                                            log_i18n_level(
                                                gui,
                                                "warning",
                                                *_tools_stage_message(
                                                    "system",
                                                    "Timeout lors de l'installation Windows",
                                                    "Timeout during Windows installation",
                                                ),
                                            )
                                            system_install_ok = False
                                            break

                                    if system_install_ok:
                                        if process.exitCode() == 0:
                                            log_i18n_level(
                                                gui,
                                                "success",
                                                *_tools_stage_message(
                                                    "system",
                                                    f"Outils Windows installés: {missing_system}",
                                                    f"Windows tools installed: {missing_system}",
                                                ),
                                            )
                                        else:
                                            log_i18n_level(
                                                gui,
                                                "error",
                                                *_tools_stage_message(
                                                    "system",
                                                    f"Échec installation Windows: {missing_system}",
                                                    f"Windows installation failed: {missing_system}",
                                                ),
                                            )
                                            system_install_ok = False
                                else:
                                    log_i18n_level(
                                        gui,
                                        "warning",
                                        *_tools_stage_message(
                                            "system",
                                            "winget non disponible, installation manuelle requise",
                                            "winget not available, manual installation required",
                                        ),
                                    )
                                    # Open documentation URL for manual installation
                                    sys_manager.open_urls(
                                        [
                                            "https://learn.microsoft.com/en-us/windows/package-manager/winget/"
                                        ]
                                    )
                                    system_install_ok = False
                            else:
                                log_i18n_level(
                                    gui,
                                    "warning",
                                    *_tools_stage_message(
                                        "system",
                                        f"Aucun équivalent Windows pour: {missing_system}",
                                        f"No Windows equivalent for: {missing_system}",
                                    ),
                                )
                        else:
                            log_i18n_level(
                                gui,
                                "warning",
                                *_tools_stage_message(
                                    "system",
                                    "Plateforme non supportée pour l'installation automatique",
                                    "Platform not supported for automatic installation",
                                ),
                            )
                            system_install_ok = False
                    else:
                        log_i18n_level(
                            gui,
                            "success",
                            *_tools_stage_message(
                                "system",
                                f"Tous les outils système sont déjà installés: {system_tools}",
                                f"All system tools are already installed: {system_tools}",
                            ),
                        )

                except Exception as e:
                    log_i18n_level(
                        gui,
                        "warning",
                        *_tools_stage_message(
                            "system",
                            f"Erreur lors de la vérification/installation des outils système: {e}",
                            f"Error checking/installing system tools: {e}",
                        ),
                    )
                    system_install_ok = False

            if stop_signal and stop_signal():
                return False

            # Check Python tools after the system phase, even if the system phase failed.
            if hasattr(gui, "venv_manager") and gui.venv_manager and python_tools:
                use_system = bool(getattr(gui, "use_system_python", False))
                if use_system:
                    missing_python = []
                    for tool in python_tools:
                        if not gui.venv_manager.is_tool_installed_system(tool):
                            missing_python.append(tool)
                    if missing_python:
                        log_i18n_level(
                            gui,
                            "info",
                            *_tools_stage_message(
                                "python",
                                f"Installation des outils Python manquants: {missing_python}",
                                f"Installing missing Python tools: {missing_python}",
                            ),
                        )
                        gui.venv_manager.ensure_tools_installed_system(missing_python)
                else:
                    venv_path = gui.venv_manager.resolve_project_venv()
                    if venv_path:
                        missing_python = []
                        for tool in python_tools:
                            if not gui.venv_manager.is_tool_installed(venv_path, tool):
                                missing_python.append(tool)
                        if missing_python:
                            log_i18n_level(
                                gui,
                                "info",
                                *_tools_stage_message(
                                    "python",
                                    f"Installation des outils Python manquants: {missing_python}",
                                    f"Installing missing Python tools: {missing_python}",
                                ),
                            )
                            gui.venv_manager.ensure_tools_installed(
                                venv_path, missing_python
                            )

            return system_install_ok and not (stop_signal and stop_signal())
        except Exception as e:
            log_i18n_level(
                gui,
                "warning",
                f"Erreur dans ensure_tools_installed: {e}",
                f"Error in ensure_tools_installed: {e}",
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
