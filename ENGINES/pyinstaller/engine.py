# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Ague Samuel Amen
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
                    gui.log.append(
                        gui.tr(
                            f"✅ {package} déjà installé",
                            f"✅ {package} already installed",
                        )
                    )
                except Exception:
                    pass
                return True
            try:
                gui.log.append(
                    gui.tr(
                        f"📦 Installation de {package}…", f"📦 Installing {package}…"
                    )
                )
            except Exception:
                pass
            ok = pip_install(gui, pip, package) == 0
            try:
                if ok:
                    gui.log.append(
                        gui.tr("✅ Installation réussie", "✅ Installation successful")
                    )
                else:
                    gui.log.append(
                        gui.tr(
                            f"❌ Installation échouée ({package})",
                            f"❌ Installation failed ({package})",
                        )
                    )
            except Exception:
                pass
            return ok
        except Exception:
            return False

    def _check_linux_deps(self, gui) -> bool:
        """Check and install Linux system dependencies for PyInstaller."""
        import shutil as _shutil

        def _tr(fr, en):
            try:
                return gui.tr(fr, en)
            except Exception:
                return fr

        if platform.system() != "Linux":
            return True

        required = ["patchelf", "objdump (binutils)", "p7zip (7z/7za)"]
        missing = [r for r in required if not self._which_tool(r.split()[0])]

        if not missing:
            return True

        sdm = SysDependencyManager(parent_widget=gui)
        pm = sdm.detect_linux_package_manager()
        if not pm:
            self._show_error(gui, _tr(
                "Gestionnaire de paquets non détecté",
                "Package manager not detected",
            ), _tr(
                "Impossible d'installer automatiquement les dépendances système (patchelf, p7zip).",
                "Unable to auto-install system dependencies (patchelf, p7zip).",
            ))
            return False

        pkg_map = {
            "apt": ["binutils", "patchelf", "p7zip-full"],
            "dnf": ["binutils", "patchelf", "p7zip"],
            "pacman": ["binutils", "patchelf", "p7zip"],
        }
        packages = pkg_map.get(pm, ["binutils", "patchelf", "p7zip-full"])

        gui.log.append(_tr(
            "🔧 Dépendances système PyInstaller manquantes: ",
            "🔧 Missing PyInstaller system dependencies: ",
        ) + ", ".join(missing))

        if not sdm.install_packages_linux(packages, pm=pm):
            gui.log.append(_tr(
                "⛔ Installation des dépendances système annulée ou non démarrée.",
                "⛔ System dependencies installation cancelled or not started.",
            ))
            return False

        gui.log.append(_tr(
            "⏳ Installation des dépendances système en arrière‑plan… Relancez la compilation après l'installation.",
            "⏳ Installing system dependencies in background… Relaunch the build after installation.",
        ))
        return False

    def _which_tool(self, tool: str) -> bool:
        import shutil as _shutil
        if tool == "7z":
            return _shutil.which("7z") or _shutil.which("7za")
        return _shutil.which(tool)

    def _ensure_venv(self, gui) -> Optional[str]:
        vroot = self._resolve_venv_root(gui)
        if vroot:
            return vroot

        vm = getattr(gui, "venv_manager", None)
        if vm and getattr(gui, "workspace_dir", None):
            vm.create_venv_if_needed(gui.workspace_dir)
            return self._resolve_venv_root(gui)

        gui.log.append(gui.tr(
            "❌ Aucun venv détecté. Créez un venv dans le workspace.",
            "❌ No venv detected. Create a venv in the workspace.",
        ))
        return None

    def _check_pyinstaller_with_vm(self, gui, vroot, vm) -> bool:
        """Check/install PyInstaller using VenvManager (async flow)."""
        if vm.is_tool_installed(vroot, "pyinstaller"):
            return True

        def _on_check(ok: bool):
            if ok:
                gui.log.append(gui.tr(
                    "✅ PyInstaller déjà installé",
                    "✅ PyInstaller already installed",
                ))
            else:
                gui.log.append(gui.tr(
                    "📦 Installation de PyInstaller dans le venv (asynchrone)…",
                    "📦 Installing PyInstaller in venv (async)…",
                ))
                vm.ensure_tools_installed(vroot, ["pyinstaller"])

        gui.log.append(gui.tr(
            "🔎 Vérification de PyInstaller dans le venv (asynchrone)…",
            "🔎 Verifying PyInstaller in venv (async)…",
        ))

        try:
            vm.is_tool_installed_async(vroot, "pyinstaller", _on_check)
        except Exception:
            gui.log.append(gui.tr(
                "📦 Installation de PyInstaller dans le venv (asynchrone)…",
                "📦 Installing PyInstaller in venv (async)…",
            ))
            vm.ensure_tools_installed(vroot, ["pyinstaller"])

        return False

    def _show_error(self, gui, title: str, msg: str):
        try:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(gui, title, msg)
        except Exception:
            pass

    def preflight(self, gui, file: str) -> bool:
        """Ensure venv exists and PyInstaller is installed."""
        try:
            # Step 1: Check Linux system dependencies
            if platform.system() == "Linux":
                if not self._check_linux_deps(gui):
                    return False

            # Step 2: Ensure venv exists
            vroot = self._ensure_venv(gui)
            if not vroot:
                return False

            # Step 3: Check/install PyInstaller
            vm = getattr(gui, "venv_manager", None)
            if vm:
                return self._check_pyinstaller_with_vm(gui, vroot, vm)

            return self._ensure_tool_with_pip(gui, vroot, "pyinstaller")
        except Exception:
            return True

    def build_command(self, gui, file: str) -> list[str]:
        # Reuse existing logic from gui (compiler.py build_pyinstaller_command)
        return gui.build_pyinstaller_command(file)

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        cmd = self.build_command(gui, file)
        # Resolve pyinstaller binary from venv via VenvManager
        try:
            vm = getattr(gui, "venv_manager", None)
            vroot = vm.resolve_project_venv() if vm else None
            if not vroot:
                gui.log.append(
                    gui.tr(
                        "❌ Venv introuvable pour résoudre pyinstaller.",
                        "❌ Venv not found to resolve pyinstaller.",
                    )
                )
                gui.show_error_dialog(os.path.basename(file))
                return None
            vbin = os.path.join(
                vroot, "Scripts" if platform.system() == "Windows" else "bin"
            )
            pyinstaller_path = os.path.join(
                vbin,
                "pyinstaller" if platform.system() != "Windows" else "pyinstaller.exe",
            )
            if not os.path.isfile(pyinstaller_path):
                gui.log.append(
                    gui.tr(
                        "❌ pyinstaller non trouvé dans le venv : ",
                        "❌ pyinstaller not found in venv: ",
                    )
                    + str(pyinstaller_path)
                )
                gui.show_error_dialog(os.path.basename(file))
                return None
            return pyinstaller_path, cmd[1:]
        except Exception:
            return None

    def environment(self, gui, file: str) -> Optional[dict[str, str]]:
        return None

    def create_tab(self, gui):
        # Reuse existing tab if present (from UI file)
        try:
            from PySide6.QtWidgets import QWidget

            tab = getattr(gui, "tab_pyinstaller", None)
            if tab and isinstance(tab, QWidget):
                # Save UI state automatically when user toggles/edits widgets
                try:
                    from engine_sdk import save_engine_ui as _save

                    # Checkboxes to persist
                    for _name in (
                        "opt_onefile",
                        "opt_windowed",
                        "opt_noconfirm",
                        "opt_clean",
                        "opt_noupx",
                        "opt_debug",
                    ):
                        try:
                            _w = getattr(gui, _name, None)
                            if _w is not None and hasattr(_w, "toggled"):
                                _w.toggled.connect(
                                    lambda v, n=_name: _save(
                                        gui, "pyinstaller", {n: {"checked": bool(v)}}
                                    )
                                )
                        except Exception:
                            pass
                    # Text fields to persist
                    try:
                        _w = getattr(gui, "output_dir_input", None)
                        if _w is not None and hasattr(_w, "textChanged"):
                            _w.textChanged.connect(
                                lambda s: _save(
                                    gui,
                                    "pyinstaller",
                                    {"output_dir_input": {"text": str(s)}},
                                )
                            )
                    except Exception:
                        pass
                except Exception:
                    pass
                return tab, gui.tr("PyInstaller", "PyInstaller")
        except Exception:
            pass
        return None

    def on_success(self, gui, file: str) -> None:
        # Ouvre le dossier de sortie PyInstaller (dist ou --distpath)
        try:
            # 1) Essayer le champ global de l'UI s'il est présent et non vide
            out_dir = None
            try:
                if hasattr(gui, "output_dir_input") and gui.output_dir_input:
                    v = gui.output_dir_input.text().strip()
                    if v:
                        out_dir = v
            except Exception:
                out_dir = None
            # 2) Fallback: workspace/dist
            if not out_dir:
                base = getattr(gui, "workspace_dir", None) or os.getcwd()
                out_dir = os.path.join(base, "dist")
            # 3) Vérifier existence et ouvrir selon la plateforme
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
                    gui.log.append(
                        gui.tr(
                            f"⚠️ Dossier de sortie introuvable: {out_dir}",
                            f"⚠️ Output directory not found: {out_dir}",
                        )
                    )
                except Exception:
                    pass
        except Exception as e:
            try:
                gui.log.append(
                    (
                        gui.tr(
                            "⚠️ Impossible d'ouvrir le dossier dist automatiquement : {err}",
                            "⚠️ Unable to open dist folder automatically: {err}",
                        )
                    ).format(err=e)
                )
            except Exception:
                pass
