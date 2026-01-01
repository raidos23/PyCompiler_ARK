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

import os
import platform
from typing import Optional

from engine_sdk import (
    CompilerEngine,
    SysDependencyManager,
    pip_executable,
    pip_install,
    pip_show,
    resolve_project_venv,
)
from engine_sdk.auto_build_command import _tr


class PyInstallerEngine(CompilerEngine):
    id = "pyinstaller"
    name = "PyInstaller"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    def _resolve_venv_root(self, gui) -> Optional[str]:
        try:
            vroot = resolve_project_venv(gui)
            return vroot
        except Exception:
            return None

    def _pip_exe(self, vroot: str) -> str:
        return pip_executable(vroot)

    def _ensure_tool_with_pip(self, gui, vroot: str, package: str) -> bool:
        pip = self._pip_exe(vroot)
        try:
            if pip_show(gui, pip, package) == 0:
                try:
                    gui.log.append(_tr(f"✅ {package} déjà installé", f"✅ {package} already installed"))
                except Exception:
                    pass
                return True
            try:
                gui.log.append(_tr(f"📦 Installation de {package}…", f"📦 Installing {package}…"))
            except Exception:
                pass
            ok = pip_install(gui, pip, package) == 0
            try:
                gui.log.append(_tr("✅ Installation réussie", "✅ Installation successful") if ok else _tr(f"❌ Installation échouée ({package})", f"❌ Installation failed ({package})"))
            except Exception:
                pass
            return ok
        except Exception:
            return False

    def preflight(self, gui, file: str) -> bool:
        # Dépendances système minimales (Linux)
        try:
            import shutil as _shutil

            if platform.system() == "Linux":
                missing = []
                if not _shutil.which("patchelf"):
                    missing.append("patchelf")
                if not (_shutil.which("7z") or _shutil.which("7za")):
                    missing.append("p7zip (7z/7za)")
                if missing:
                    sdm = SysDependencyManager(parent_widget=gui)
                    pm = sdm.detect_linux_package_manager()
                    if pm:
                        if pm == "apt":
                            packages = ["patchelf", "p7zip-full"]
                        elif pm == "dnf":
                            packages = ["patchelf", "p7zip"]
                        elif pm == "pacman":
                            packages = ["patchelf", "p7zip"]
                        else:
                            packages = ["patchelf", "p7zip-full"]
                        try:
                            gui.log.append(
                                _tr(
                                    "🔧 Dépendances système PyInstaller manquantes: ",
                                    "🔧 Missing PyInstaller system dependencies: ",
                                )
                                + ", ".join(missing)
                            )
                        except Exception:
                            pass
                        proc = sdm.install_packages_linux(packages, pm=pm)
                        if proc:
                            try:
                                gui.log.append(
                                    _tr(
                                        "⏳ Installation des dépendances système en arrière‑plan… Relancez la compilation après l'installation.",
                                        "⏳ Installing system dependencies in background… Relaunch the build after installation.",
                                    )
                                )
                            except Exception:
                                pass
                            return False
                        else:
                            try:
                                gui.log.append(
                                    _tr(
                                        "⛔ Installation des dépendances système annulée ou non démarrée.",
                                        "⛔ System dependencies installation cancelled or not started.",
                                    )
                                )
                            except Exception:
                                pass
                            return False
                    else:
                        try:
                            from PySide6.QtWidgets import QMessageBox

                            QMessageBox.critical(
                                gui,
                                _tr("Gestionnaire de paquets non d��tecté", "Package manager not detected"),
                                _tr(
                                    "Impossible d'installer automatiquement les dépendances système (patchelf, p7zip).",
                                    "Unable to auto-install system dependencies (patchelf, p7zip).",
                                ),
                            )
                        except Exception:
                            pass
                        return False
        except Exception:
            pass

        # Venv + outil pyinstaller
        try:
            vroot = self._resolve_venv_root(gui)
            if not vroot:
                vm = getattr(gui, "venv_manager", None)
                if vm and getattr(gui, "workspace_dir", None):
                    vm.create_venv_if_needed(gui.workspace_dir)
                else:
                    try:
                        gui.log.append(
                            _tr(
                                "❌ Aucun venv détecté. Créez un venv dans le workspace.",
                                "❌ No venv detected. Create a venv in the workspace.",
                            )
                        )
                    except Exception:
                        pass
                return False

            vm = getattr(gui, "venv_manager", None)
            if vm:
                if vm.is_tool_installed(vroot, "pyinstaller"):
                    return True
                try:
                    gui.log.append(
                        _tr(
                            "🔎 Vérification de PyInstaller dans le venv (asynchrone)…",
                            "🔎 Verifying PyInstaller in venv (async)…",
                        )
                    )
                except Exception:
                    pass

                def _on_check(ok: bool):
                    try:
                        if ok:
                            gui.log.append(_tr("✅ PyInstaller déjà installé", "✅ PyInstaller already installed"))
                        else:
                            gui.log.append(_tr("📦 Installation de PyInstaller dans le venv (asynchrone)…", "📦 Installing PyInstaller in venv (async)…"))
                            vm.ensure_tools_installed(vroot, ["pyinstaller"])
                    except Exception:
                        pass

                try:
                    vm.is_tool_installed_async(vroot, "pyinstaller", _on_check)
                except Exception:
                    try:
                        gui.log.append(_tr("📦 Installation de PyInstaller dans le venv (asynchrone)…", "📦 Installing PyInstaller in venv (async)…"))
                    except Exception:
                        pass
                    vm.ensure_tools_installed(vroot, ["pyinstaller"])
                return False
            else:
                return self._ensure_tool_with_pip(gui, vroot, "pyinstaller")
        except Exception:
            pass
        return True

    def build_command(self, gui, file: str) -> list[str]:
        return gui.build_pyinstaller_command(file)

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        cmd = self.build_command(gui, file)
        try:
            vm = getattr(gui, "venv_manager", None)
            vroot = vm.resolve_project_venv() if vm else None
            if not vroot:
                gui.log.append(_tr("❌ Venv introuvable pour résoudre pyinstaller.", "❌ Venv not found to resolve pyinstaller."))
                gui.show_error_dialog(os.path.basename(file))
                return None
            vbin = os.path.join(vroot, "Scripts" if platform.system() == "Windows" else "bin")
            # Privilégier python -m PyInstaller pour robustesse cross-plateforme
            python_path = os.path.join(vbin, "python" if platform.system() != "Windows" else "python.exe")
            if os.path.isfile(python_path):
                return python_path, cmd[1:]
            # Fallback vers binaire pyinstaller
            pyinstaller_path = os.path.join(vbin, "pyinstaller" if platform.system() != "Windows" else "pyinstaller.exe")
            if os.path.isfile(pyinstaller_path):
                return pyinstaller_path, cmd[1:]
            gui.log.append(_tr("❌ Python/PyInstaller introuvable dans le venv.", "❌ Python/PyInstaller not found in venv."))
            gui.show_error_dialog(os.path.basename(file))
            return None
        except Exception:
            return None

    def environment(self, gui, file: str) -> Optional[dict[str, str]]:
        return None

    def create_tab(self, gui):
        try:
            from PySide6.QtWidgets import QWidget

            tab = getattr(gui, "tab_pyinstaller", None)
            if tab and isinstance(tab, QWidget):
                return tab, _tr("PyInstaller", "PyInstaller")
        except Exception:
            pass
        return None

    def on_success(self, gui, file: str) -> None:
        try:
            out_dir = None
            try:
                if hasattr(gui, "output_dir_input") and gui.output_dir_input:
                    v = gui.output_dir_input.text().strip()
                    if v:
                        out_dir = v
            except Exception:
                out_dir = None
            if not out_dir:
                base = getattr(gui, "workspace_dir", None) or os.getcwd()
                out_dir = os.path.join(base, "dist")
            if out_dir and os.path.isdir(out_dir):
                system = platform.system()
                if system == "Windows":
                    os.startfile(out_dir)
                elif system == "Linux":
                    import subprocess as _sp
                    _sp.run(["xdg-open", out_dir])
                else:
                    import subprocess as _sp
                    _sp.run(["open", out_dir])
            else:
                try:
                    gui.log.append(_tr(f"⚠️ Dossier de sortie introuvable: {out_dir}", f"⚠️ Output directory not found: {out_dir}"))
                except Exception:
                    pass
        except Exception as e:
            try:
                gui.log.append(_tr(
                    "⚠️ Impossible d'ouvrir le dossier dist automatiquement : {err}",
                    "⚠️ Unable to open dist folder automatically: {err}",
                ).format(err=e))
            except Exception:
                pass
