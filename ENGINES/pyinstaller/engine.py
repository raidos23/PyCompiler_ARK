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

    def preflight(self, gui, file: str) -> bool:
        # Ensure venv exists and PyInstaller is installed; trigger install if needed
        try:
            # System dependencies (Linux)
            try:
                import shutil as _shutil

                def _tr(fr, en):
                    try:
                        return gui.tr(fr, en)
                    except Exception:
                        return fr

                if platform.system() == "Linux":
                    missing = []
                    if not _shutil.which("patchelf"):
                        missing.append("patchelf")
                    if not _shutil.which("objdump"):
                        missing.append("objdump (binutils)")
                    if not (_shutil.which("7z") or _shutil.which("7za")):
                        missing.append("p7zip (7z/7za)")
                    if missing:
                        sdm = SysDependencyManager(parent_widget=gui)
                        pm = sdm.detect_linux_package_manager()
                        if pm:
                            if pm == "apt":
                                packages = ["binutils", "patchelf", "p7zip-full"]
                            elif pm == "dnf":
                                packages = ["binutils", "patchelf", "p7zip"]
                            elif pm == "pacman":
                                packages = ["binutils", "patchelf", "p7zip"]
                            else:
                                packages = ["binutils", "patchelf", "p7zip-full"]
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
                                # Ne pas bloquer l'UI: arrêter le préflight et relancer plus tard
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
                                    _tr(
                                        "Gestionnaire de paquets non détecté",
                                        "Package manager not detected",
                                    ),
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

            vroot = self._resolve_venv_root(gui)
            if not vroot:
                # Demander à la GUI de créer le venv si VenvManager dispo
                vm = getattr(gui, "venv_manager", None)
                if vm and getattr(gui, "workspace_dir", None):
                    vm.create_venv_if_needed(gui.workspace_dir)
                else:
                    try:
                        gui.log.append(
                            gui.tr(
                                "❌ Aucun venv détecté. Créez un venv dans le workspace.",
                                "❌ No venv detected. Create a venv in the workspace.",
                            )
                        )
                    except Exception:
                        pass
                return False
            # Utiliser VenvManager s'il est là, sinon fallback pip
            vm = getattr(gui, "venv_manager", None)
            if vm:
                # Check if already installed
                if vm.is_tool_installed(vroot, "pyinstaller"):
                    try:
                        gui.log.append(
                            gui.tr(
                                "✅ PyInstaller déjà installé",
                                "✅ PyInstaller already installed",
                            )
                        )
                    except Exception:
                        pass
                    return True
                
                # Install synchronously (blocking) to ensure it's ready before build
                try:
                    gui.log.append(
                        gui.tr(
                            "📦 Installation de PyInstaller dans le venv…",
                            "📦 Installing PyInstaller in venv…",
                        )
                    )
                except Exception:
                    pass
                
                vm.ensure_tools_installed(vroot, ["pyinstaller"])
                
                # Verify installation
                if vm.is_tool_installed(vroot, "pyinstaller"):
                    try:
                        gui.log.append(
                            gui.tr(
                                "✅ PyInstaller installé avec succès",
                                "✅ PyInstaller installed successfully",
                            )
                        )
                    except Exception:
                        pass
                    return True
                else:
                    try:
                        gui.log.append(
                            gui.tr(
                                "❌ Échec de l'installation de PyInstaller",
                                "❌ Failed to install PyInstaller",
                            )
                        )
                    except Exception:
                        pass
                    return False
            else:
                return self._ensure_tool_with_pip(gui, vroot, "pyinstaller")
        except Exception:
            return True

    def build_command(self, gui, file: str) -> list[str]:
        import sys
        
        cmd = [sys.executable, "-m", "pyinstaller"]
        
        # Options checkboxes
        try:
            if hasattr(self, "_opt_onefile") and self._opt_onefile.isChecked():
                cmd.append("--onefile")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_opt_windowed") and self._opt_windowed.isChecked():
                cmd.append("--windowed")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_opt_noconfirm") and self._opt_noconfirm.isChecked():
                cmd.append("--noconfirm")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_opt_clean") and self._opt_clean.isChecked():
                cmd.append("--clean")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_opt_noupx") and self._opt_noupx.isChecked():
                cmd.append("--noupx")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_opt_debug") and self._opt_debug.isChecked():
                cmd.append("--debug")
        except Exception:
            pass
        
        # Icon
        try:
            if hasattr(self, "_icon_path") and self._icon_path:
                cmd.append(f"--icon={self._icon_path}")
        except Exception:
            pass
        
        # Data files
        try:
            if hasattr(self, "_pyinstaller_data"):
                for src, dest in self._pyinstaller_data:
                    cmd.append(f"--add-data={src}:{dest}")
        except Exception:
            pass
        
        # Auto-detection of plugins/hooks
        try:
            from engine_sdk.auto_build_command import compute_auto_for_engine
            auto_args = compute_auto_for_engine(gui, "pyinstaller") or []
            if auto_args:
                cmd.extend(auto_args)
        except Exception as e:
            try:
                gui.log.append(gui.tr(
                    f"⚠️ Auto-détection PyInstaller: {e}",
                    f"⚠️ PyInstaller auto-detection: {e}"
                ))
            except Exception:
                pass
        
        # Output name
        try:
            custom_name = ""
            if hasattr(self, "_output_name_input") and self._output_name_input:
                custom_name = self._output_name_input.text().strip()
            
            if custom_name:
                output_name = (
                    custom_name + ".exe" if platform.system() == "Windows" else custom_name
                )
            else:
                base_name = os.path.splitext(os.path.basename(file))[0]
                output_name = (
                    base_name + ".exe" if platform.system() == "Windows" else base_name
                )
            cmd.extend(["--name", output_name])
        except Exception:
            pass
        
        # Output directory
        try:
            output_dir = ""
            if hasattr(self, "_output_dir_input") and self._output_dir_input:
                output_dir = self._output_dir_input.text().strip()
            
            if output_dir:
                cmd.extend(["--distpath", output_dir])
        except Exception:
            pass
        
        # Script file
        cmd.append(file)
        
        return cmd

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        cmd = self.build_command(gui, file)
        # Resolve python from venv via VenvManager
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
            python_path = os.path.join(
                vbin,
                "python.exe" if platform.system() == "Windows" else "python",
            )
            if not os.path.isfile(python_path):
                gui.log.append(
                    gui.tr(
                        "❌ python non trouvé dans le venv : ",
                        "❌ python not found in venv: ",
                    )
                    + str(python_path)
                )
                gui.show_error_dialog(os.path.basename(file))
                return None
            return python_path, cmd[1:]
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
