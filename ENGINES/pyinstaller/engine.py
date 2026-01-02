from __future__ import annotations

import os
import platform
import sys
from typing import Optional

from engine_sdk import CompilerEngine
from Core.engines_loader.registry import register


class PyInstallerEngine(CompilerEngine):
    id = "pyinstaller"
    name = "PyInstaller"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    def _dedupe_args(self, seq: list[str]) -> list[str]:
        seen = set()
        out: list[str] = []
        for x in seq:
            if x not in seen:
                out.append(x)
                seen.add(x)
        return out

    def preflight(self, gui, file: str) -> bool:
        try:
            import shutil
            import subprocess

            # Vérifie pyinstaller dans le venv courant
            py = sys.executable
            ok = False
            try:
                r = subprocess.run([py, "-m", "PyInstaller", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                ok = r.returncode == 0
            except Exception:
                ok = False

            if not ok:
                # Fallback: binaire pyinstaller dans PATH
                if shutil.which("pyinstaller") is None:
                    try:
                        gui.log.append(gui.tr("❌ PyInstaller introuvable. Installez-le dans le venv.", "❌ PyInstaller not found. Install it in the venv."))
                    except Exception:
                        pass
                    return False
            return True
        except Exception:
            return True

    def build_command(self, gui, file: str) -> list[str]:
        cmd = [sys.executable, "-m", "PyInstaller"]

        # Options depuis l'UI
        try:
            if hasattr(gui, "opt_onefile") and gui.opt_onefile.isChecked():
                cmd.append("--onefile")
        except Exception:
            pass
        try:
            if hasattr(gui, "opt_windowed") and gui.opt_windowed.isChecked():
                cmd.append("--noconsole")
        except Exception:
            pass
        try:
            if hasattr(gui, "opt_noconfirm") and gui.opt_noconfirm.isChecked():
                cmd.append("--noconfirm")
        except Exception:
            pass
        try:
            if hasattr(gui, "opt_clean") and gui.opt_clean.isChecked():
                cmd.append("--clean")
        except Exception:
            pass
        try:
            if hasattr(gui, "opt_noupx") and gui.opt_noupx.isChecked():
                cmd.append("--noupx")
        except Exception:
            pass
        try:
            if hasattr(gui, "opt_debug") and gui.opt_debug.isChecked():
                cmd.append("--debug")
        except Exception:
            pass

        # Icone
        try:
            icon = getattr(gui, "_pyinstaller_icon_path", None)
            if icon:
                cmd.extend(["--icon", icon])
        except Exception:
            pass

        # Dossier de sortie
        try:
            if hasattr(gui, "output_dir_input") and gui.output_dir_input:
                out = gui.output_dir_input.text().strip()
                if out:
                    cmd.extend(["--distpath", out])
        except Exception:
            pass

        # Données additionnelles
        try:
            if hasattr(gui, "_pyinstaller_add_data"):
                for src, dest in getattr(gui, "_pyinstaller_add_data", []):
                    cmd.extend(["--add-data", f"{src}{os.pathsep}{dest}"])
        except Exception:
            pass

        # Fichier cible
        cmd.append(file)

        # Auto-plugins mapping for PyInstaller
        try:
            from engine_sdk import auto_build_command as _ap  # type: ignore

            auto_args = _ap.compute_auto_for_engine(gui, "pyinstaller") or []
        except Exception:
            auto_args = []
        try:
            cmd = self._dedupe_args(cmd)
        except Exception:
            pass
        return cmd + auto_args

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        # Utilise le python du venv résolu par le VenvManager si disponible
        try:
            vm = getattr(gui, "venv_manager", None)
            vroot = vm.resolve_project_venv() if vm else None
            if not vroot:
                return None
            vbin = os.path.join(vroot, "Scripts" if platform.system() == "Windows" else "bin")
            python_path = os.path.join(vbin, "python.exe" if platform.system() == "Windows" else "python")
            if not os.path.isfile(python_path):
                return None
            cmd = self.build_command(gui, file)
            return python_path, cmd[1:]
        except Exception:
            # Fallback sur l'interpréteur courant
            cmd = self.build_command(gui, file)
            return (cmd[0], cmd[1:]) if cmd else None

    def environment(self, gui, file: str) -> Optional[dict[str, str]]:
        return None

    def create_tab(self, gui):
        # L’UI intègre déjà l’onglet PyInstaller (ui_design.ui)
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
                import subprocess as _sp
                sysname = platform.system()
                if sysname == "Windows":
                    os.startfile(out_dir)  # type: ignore[attr-defined]
                elif sysname == "Linux":
                    _sp.run(["xdg-open", out_dir])
                else:
                    _sp.run(["open", out_dir])
        except Exception:
            pass


# Enregistrement
register(PyInstallerEngine)
