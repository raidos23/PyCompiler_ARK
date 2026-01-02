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


class NuitkaEngine(CompilerEngine):
    id = "nuitka"
    name = "Nuitka"
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
                    "python3-dev/python3-devel (headers)": "python3-config",
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
                                    "Impossible d'installer automatiquement les dépendances système (build tools, python3-dev, pkg-config, patchelf, p7zip).",
                                    "Unable to auto-install system dependencies (build tools, python3-dev, pkg-config, patchelf, p7zip).",
                                ),
                            )
                        except Exception:
                            pass
                        return False
                    if pm == "apt":
                        packages = ["build-essential", "python3-dev", "pkg-config", "patchelf", "p7zip-full"]
                    elif pm == "dnf":
                        packages = ["gcc", "gcc-c++", "make", "python3-devel", "pkgconf-pkg-config", "patchelf", "p7zip"]
                    elif pm == "pacman":
                        packages = ["base-devel", "pkgconf", "patchelf", "p7zip"]
                    else:
                        packages = ["gcc", "gcc-c++", "make", "python3-devel", "pkg-config", "patchelf", "p7zip-full"]
                    
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
                    msg.setText(_tr("Pour compiler avec Nuitka sous Windows, il faut un compilateur C/C++.\n\nWinget indisponible. Voulez-vous ouvrir la page MinGW-w64 (winlibs.com) ?\n\nAprès installation, relancez la compilation.", "To build with Nuitka on Windows, a C/C++ compiler is required.\n\nWinget unavailable. Do you want to open the MinGW-w64 page (winlibs.com)?\n\nAfter installation, restart the build."))
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
                if vm.is_tool_installed(vroot, "nuitka"):
                    return True
                try:
                    gui.log.append(gui.tr("🔎 Vérification de Nuitka dans le venv (asynchrone)…", "🔎 Verifying Nuitka in venv (async)…"))
                except Exception:
                    pass

                def _on_check(ok: bool):
                    try:
                        if ok:
                            gui.log.append(gui.tr("✅ Nuitka déjà installé", "✅ Nuitka already installed"))
                        else:
                            gui.log.append(gui.tr("📦 Installation de Nuitka dans le venv (asynchrone)…", "📦 Installing Nuitka in venv (async)…"))
                            vm.ensure_tools_installed(vroot, ["nuitka"])
                    except Exception:
                        pass

                try:
                    vm.is_tool_installed_async(vroot, "nuitka", _on_check)
                except Exception:
                    try:
                        gui.log.append(gui.tr("📦 Installation de Nuitka dans le venv (asynchrone)…", "📦 Installing Nuitka in venv (async)…"))
                    except Exception:
                        pass
                    vm.ensure_tools_installed(vroot, ["nuitka"])
                return False
            else:
                pip = pip_executable(vroot)
                if pip_show(gui, pip, "nuitka") != 0:
                    try:
                        gui.log.append(gui.tr("📦 Installation de Nuitka…", "📦 Installing Nuitka…"))
                    except Exception:
                        pass
                    ok = pip_install(gui, pip, "nuitka") == 0
                    try:
                        if ok:
                            gui.log.append(gui.tr("✅ Installation réussie", "✅ Installation successful"))
                        else:
                            gui.log.append(gui.tr("❌ Installation échouée (nuitka)", "❌ Installation failed (nuitka)"))
                    except Exception:
                        pass
                    return ok
                else:
                    try:
                        gui.log.append(gui.tr("✅ Nuitka déjà installé", "✅ Nuitka already installed"))
                    except Exception:
                        pass
                    return True
        except Exception:
            return True

    def build_command(self, gui, file: str) -> list[str]:
        import sys
        cmd = [sys.executable, "-m", "nuitka"]
        
        # Options checkboxes
        try:
            if hasattr(self, "_nuitka_onefile") and self._nuitka_onefile.isChecked():
                cmd.append("--onefile")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_nuitka_standalone") and self._nuitka_standalone.isChecked():
                cmd.append("--standalone")
        except Exception:
            pass
        
        try:
            if (
                hasattr(self, "_nuitka_disable_console")
                and self._nuitka_disable_console.isChecked()
                and platform.system() == "Windows"
            ):
                cmd.append("--windows-disable-console")
        except Exception:
            pass
        
        try:
            if hasattr(self, "_nuitka_show_progress") and self._nuitka_show_progress.isChecked():
                cmd.append("--show-progress")
        except Exception:
            pass
        
        # Auto-detect Qt plugins (PySide6 or PyQt6, but not both)
        plugins = []
        found_pyside6 = False
        found_pyqt6 = False
        
        try:
            with open(file, encoding="utf-8") as f:
                content = f.read()
                if "import PySide6" in content or "from PySide6" in content:
                    found_pyside6 = True
                if "import PyQt6" in content or "from PyQt6" in content:
                    found_pyqt6 = True
        except Exception:
            pass
        
        # Never enable both Qt plugins at the same time
        if found_pyside6:
            if "pyqt6" in plugins:
                plugins.remove("pyqt6")
            if "pyside6" not in plugins:
                plugins.append("pyside6")
        elif found_pyqt6:
            if "pyside6" in plugins:
                plugins.remove("pyside6")
            if "pyqt6" not in plugins:
                plugins.append("pyqt6")
        
        # If both are in the list, keep only one (priority to pyside6)
        if "pyside6" in plugins and "pyqt6" in plugins:
            plugins.remove("pyqt6")
        
        for plugin in plugins:
            cmd.append(f"--plugin-enable={plugin}")
        
        # Auto-detection of plugins/hooks
        try:
            from engine_sdk.auto_build_command import compute_auto_for_engine
            auto_args = compute_auto_for_engine(gui, "nuitka") or []
            for arg in auto_args:
                if arg not in cmd:
                    cmd.append(arg)
        except Exception as e:
            try:
                gui.log.append(gui.tr(
                    f"⚠️ Auto-détection Nuitka: {e}",
                    f"⚠️ Nuitka auto-detection: {e}"
                ))
            except Exception:
                pass
        
        # Icon (Windows only)
        try:
            if platform.system() == "Windows":
                icon_path = None
                if hasattr(self, "_nuitka_icon_path") and self._nuitka_icon_path:
                    icon_path = self._nuitka_icon_path
                elif hasattr(self, "_icon_path") and self._icon_path:
                    icon_path = self._icon_path
                
                if icon_path:
                    cmd.append(f"--windows-icon-from-ico={icon_path}")
        except Exception:
            pass
        
        # Output directory
        try:
            if hasattr(self, "_nuitka_output_dir") and self._nuitka_output_dir:
                output_dir = self._nuitka_output_dir.text().strip()
                if output_dir:
                    cmd.append(f"--output-dir={output_dir}")
        except Exception:
            pass
        
        # Data files
        try:
            if hasattr(self, "_nuitka_data_files"):
                for src, dest in self._nuitka_data_files:
                    cmd.append(f"--include-data-files={src}={dest}")
        except Exception:
            pass
        
        # Data directories
        try:
            if hasattr(self, "_nuitka_data_dirs"):
                for src, dest in self._nuitka_data_dirs:
                    cmd.append(f"--include-data-dir={src}={dest}")
        except Exception:
            pass
        
        # Script file
        cmd.append(file)
        
        return cmd

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        # Nuitka s'exécute avec python -m nuitka dans le venv; resolve via VenvManager
        try:
            vm = getattr(gui, "venv_manager", None)
            vroot = vm.resolve_project_venv() if vm else None
            if not vroot:
                gui.log.append(
                    _tr(
                        "❌ Venv introuvable pour exécuter Nuitka.",
                        "❌ Venv not found to run Nuitka.",
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

            tab = getattr(gui, "tab_nuitka", None)
            if tab and isinstance(tab, QWidget):
                return tab, _tr("Nuitka", "Nuitka")
        except Exception:
            pass
        return None

    def on_success(self, gui, file: str) -> None:
        """Action post-succès: ouvrir le dossier de sortie Nuitka si identifiable."""
        try:
            # Priorité: champ UI dédié si présent (nuitka_output_dir)
            out_dir = None
            try:
                if hasattr(gui, "nuitka_output_dir") and gui.nuitka_output_dir:
                    v = gui.nuitka_output_dir.text().strip()
                    if v:
                        out_dir = v
            except Exception:
                out_dir = None
            # Fallback: dossier global de sortie de l'app
            if not out_dir:
                try:
                    if hasattr(gui, "output_dir_input") and gui.output_dir_input:
                        v = gui.output_dir_input.text().strip()
                        if v:
                            out_dir = v
                except Exception:
                    out_dir = None
            # Dernier recours: workspace/dist
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
                        "⚠️ Impossible d'ouvrir le dossier de sortie Nuitka automatiquement : {err}",
                        "⚠️ Unable to open Nuitka output folder automatically: {err}",
                    ).format(err=e)
                )
            except Exception:
                pass
