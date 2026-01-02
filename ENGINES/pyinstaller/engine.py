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

    def preflight(self, gui, file: str) -> bool:
        # Dépendances système (Linux/Windows)
        try:
            import shutil as _shutil
            import subprocess as _subprocess

            def _tr(fr, en):
                try:
                    return gui.tr(fr, en)
                except Exception:
                    return fr

            os_name = platform.system()
            if os_name == "Linux":
                required_cmds = {
                    "gcc": "gcc",
                    "g++": "g++",
                    "make": "make",
                    "pkg-config/pkgconf": "pkg-config",
                    "patchelf": "patchelf",
                }
                missing = []
                for label, cmd in required_cmds.items():
                    c = _shutil.which(cmd)
                    if not c:
                        if cmd == "pkg-config" and not (
                            _shutil.which("pkg-config") or _shutil.which("pkgconf")
                        ):
                            missing.append("pkg-config/pkgconf")
                        elif cmd != "pkg-config":
                            missing.append(label)
                if not (_shutil.which("7z") or _shutil.which("7za")):
                    missing.append("p7zip (7z/7za)")
                
                if missing:
                    sdm = SysDependencyManager(parent_widget=gui)
                    pm = sdm.detect_linux_package_manager()
                    if not pm:
                        try:
                            from PySide6.QtWidgets import QMessageBox

                            QMessageBox.critical(
                                gui,
                                _tr(
                                    "Gestionnaire de paquets non détecté",
                                    "Package manager not detected",
                                ),
                                _tr(
                                    "Impossible d'installer automatiquement les dépendances système (build tools, pkg-config, patchelf, p7zip).",
                                    "Unable to auto-install system dependencies (build tools, pkg-config, patchelf, p7zip).",
                                ),
                            )
                        except Exception:
                            pass
                        return False
                    if pm == "apt":
                        packages = ["build-essential", "pkg-config", "patchelf", "p7zip-full"]
                    elif pm == "dnf":
                        packages = ["gcc", "gcc-c++", "make", "pkgconf-pkg-config", "patchelf", "p7zip"]
                    elif pm == "pacman":
                        packages = ["base-devel", "pkgconf", "patchelf", "p7zip"]
                    else:
                        packages = ["gcc", "gcc-c++", "make", "pkg-config", "patchelf", "p7zip-full"]
                    
                    try:
                        gui.log.append("🔧 Dépendances système manquantes détectées (" + "; ".join(missing) + ").")
                    except Exception:
                        pass
                    proc = sdm.install_packages_linux(packages, pm=pm)
                    if not proc:
                        try:
                            gui.log.append("⛔ Installation des dépendances système annulée ou installation non démarrée.\n")
                        except Exception:
                            pass
                        return False
                    try:
                        gui.log.append("⏳ Installation des dépendances système en arrière‑plan… Relancez la compilation après l'installation.")
                    except Exception:
                        pass
                    return False
            elif os_name == "Windows":
                sdm = SysDependencyManager(parent_widget=gui)
                pkgs = [
                    {
                        "id": "Microsoft.VisualStudio.2022.BuildTools",
                        "override": "--add Microsoft.VisualStudio.Workload.VCTools --passive --norestart",
                    }
                ]
                p = sdm.install_packages_windows(pkgs)
                if p is not None:
                    try:
                        gui.log.append(_tr("⏳ Installation des dépendances Windows en arrière‑plan… Relancez la compilation après l'installation.", "⏳ Installing Windows dependencies in background… Relaunch the build after installation."))
                    except Exception:
                        pass
                    return False
                if p is None:
                    import webbrowser
                    from PySide6.QtWidgets import QMessageBox

                    msg = QMessageBox(gui)
                    msg.setIcon(QMessageBox.Question)
                    msg.setWindowTitle(_tr("Installer MinGW-w64 (mhw)", "Install MinGW-w64 (mhw)"))
                    msg.setText(_tr("Pour compiler avec PyInstaller sous Windows, il faut un compilateur C/C++.\n\nWinget indisponible. Voulez-vous ouvrir la page MinGW-w64 (winlibs.com) ?\n\nAprès installation, relancez la compilation.", "To build with PyInstaller on Windows, a C/C++ compiler is required.\n\nWinget unavailable. Do you want to open the MinGW-w64 page (winlibs.com)?\n\nAfter installation, restart the build."))
                    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                    msg.setDefaultButton(QMessageBox.Yes)
                    if msg.exec() == QMessageBox.Yes:
                        webbrowser.open("https://winlibs.com/")
                        QMessageBox.information(gui, _tr("Téléchargement lancé", "Download started"), _tr("La page officielle de MinGW-w64 a été ouverte. Installez puis relancez la compilation.", "The official MinGW-w64 page has been opened. Install and retry the build."))
                    return False
        except Exception:
            pass
        try:
            vroot = resolve_project_venv(gui)
            if not vroot:
                vm = getattr(gui, "venv_manager", None)
                if vm and getattr(gui, "workspace_dir", None):
                    vm.create_venv_if_needed(gui.workspace_dir)
                else:
                    try:
                        gui.log.append(gui.tr("❌ Aucun venv détecté. Créez un venv dans le workspace.", "❌ No venv detected. Create a venv in the workspace."))
                    except Exception:
                        pass
                return False
            vm = getattr(gui, "venv_manager", None)
            if vm:
                if vm.is_tool_installed(vroot, "pyinstaller"):
                    return True
                try:
                    gui.log.append(gui.tr("🔎 Vérification de PyInstaller dans le venv (asynchrone)…", "🔎 Verifying PyInstaller in venv (async)…"))
                except Exception:
                    pass

                def _on_check(ok: bool):
                    try:
                        if ok:
                            gui.log.append(gui.tr("✅ PyInstaller déjà installé", "✅ PyInstaller already installed"))
                        else:
                            gui.log.append(gui.tr("📦 Installation de PyInstaller dans le venv (asynchrone)…", "📦 Installing PyInstaller in venv (async)…"))
                            vm.ensure_tools_installed(vroot, ["pyinstaller"])
                    except Exception:
                        pass

                try:
                    vm.is_tool_installed_async(vroot, "pyinstaller", _on_check)
                except Exception:
                    try:
                        gui.log.append(gui.tr("📦 Installation de PyInstaller dans le venv (asynchrone)…", "📦 Installing PyInstaller in venv (async)…"))
                    except Exception:
                        pass
                    vm.ensure_tools_installed(vroot, ["pyinstaller"])
                return False
            else:
                pip = pip_executable(vroot)
                if pip_show(gui, pip, "pyinstaller") != 0:
                    try:
                        gui.log.append(gui.tr("📦 Installation de PyInstaller…", "📦 Installing PyInstaller…"))
                    except Exception:
                        pass
                    ok = pip_install(gui, pip, "pyinstaller") == 0
                    try:
                        if ok:
                            gui.log.append(gui.tr("✅ Installation réussie", "✅ Installation successful"))
                        else:
                            gui.log.append(gui.tr("❌ Installation échouée (pyinstaller)", "❌ Installation failed (pyinstaller)"))
                    except Exception:
                        pass
                    return ok
                else:
                    try:
                        gui.log.append(gui.tr("✅ PyInstaller déjà installé", "✅ PyInstaller already installed"))
                    except Exception:
                        pass
                    return True
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
            for arg in auto_args:
                if arg not in cmd:
                    cmd.append(arg)
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
        # PyInstaller s'exécute avec python -m pyinstaller dans le venv; resolve via VenvManager
        try:
            vm = getattr(gui, "venv_manager", None)
            vroot = vm.resolve_project_venv() if vm else None
            if not vroot:
                gui.log.append(
                    _tr(
                        "❌ Venv introuvable pour exécuter PyInstaller.",
                        "❌ Venv not found to run PyInstaller.",
                    )
                )
                gui.show_error_dialog(os.path.basename(file))
                return None
            vbin = os.path.join(
                vroot, "Scripts" if platform.system() == "Windows" else "bin"
            )
            python_path = os.path.join(
                vbin, "python" if platform.system() != "Windows" else "python.exe"
            )
            if not os.path.isfile(python_path):
                gui.log.append(
                    _tr(
                        "❌ python non trouvé dans le venv : ",
                        "❌ python not found in venv: ",
                    )
                    + str(python_path)
                )
                gui.show_error_dialog(os.path.basename(file))
                return None
            cmd = self.build_command(gui, file)
            return python_path, cmd[1:]
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
        """Action post-succès: ouvrir le dossier de sortie PyInstaller si identifiable."""
        try:
            # Priorité: champ UI dédié si présent (output_dir_input)
            out_dir = None
            try:
                if hasattr(gui, "output_dir_input") and gui.output_dir_input:
                    v = gui.output_dir_input.text().strip()
                    if v:
                        out_dir = v
            except Exception:
                out_dir = None
            # Fallback: workspace/dist
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
        except Exception as e:
            try:
                gui.log.append(
                    _tr(
                        "⚠️ Impossible d'ouvrir le dossier de sortie PyInstaller automatiquement : {err}",
                        "⚠️ Unable to open PyInstaller output folder automatically: {err}",
                    ).format(err=e)
                )
            except Exception:
                pass
