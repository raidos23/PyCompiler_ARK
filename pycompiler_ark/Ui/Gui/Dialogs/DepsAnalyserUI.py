# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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
DepsAnalyserUI — GUI layer for dependency analysis.
"""

import json
import os
import sys
import subprocess

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QMessageBox, QApplication

from pycompiler_ark.Core.deps_analyser.analyser import (
    _normalize_realpath,
    _is_path_under,
    _should_skip_analysis_path,
    _extract_imported_modules_from_file,
    _collect_workspace_module_roots,
    _classify_module_origin,
    _find_pip_executable,
)
from pycompiler_ark.Ui.Gui.WidgetsCreator import ProgressDialog
from pycompiler_ark.Ui import output


def _log_append(gui, msg: str) -> None:
    try:
        text = str(msg)
    except Exception:
        text = msg
    level = "info"
    for emo, lvl in (
        ("❌", "error"),
        ("⚠️", "warning"),
        ("❗", "warning"),
        ("✅", "success"),
        ("ℹ️", "info"),
        ("⏩", "state"),
    ):
        if text.startswith(emo):
            level = lvl
            text = text[len(emo) :].lstrip()
            break
    output.log(level, text, gui=gui)


def suggest_missing_dependencies(self):
    """
    Analyze primary files to compile and detect imported modules,
    check leur présence dans le venv, et propose d'installer ceux qui manquent.
    """

    def _t(_key: str, fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    # Vérifie que le workspace ou le venv est bien sélectionné
    if not self.workspace_dir and not self.venv_path_manuel:
        _log_append(
            self,
            _t(
                "msg_no_workspace_or_venv_text",
                "❌ Workspace ou venv manquant. Sélectionnez-en un.",
                "❌ Workspace or venv missing. Please select one.",
            ),
        )
        try:
            box = QMessageBox(self)
            box.setWindowTitle(
                _t(
                    "msg_no_workspace_or_venv_title",
                    "Workspace ou venv manquant",
                    "Workspace or venv missing",
                )
            )
            box.setText(
                _t(
                    "msg_no_workspace_or_venv_text",
                    "Sélectionnez un Workspace ou un Venv pour analyser les dépendances.",
                    "Select a Workspace or a Venv to analyze dependencies.",
                )
            )
            btn_ws = box.addButton(
                _t("action_select_workspace", "Choisir Workspace", "Select Workspace"),
                QMessageBox.ActionRole,
            )
            btn_venv = box.addButton(
                _t("action_select_venv", "Choisir un Venv", "Select Venv"),
                QMessageBox.AcceptRole,
            )
            box.addButton(
                _t("action_cancel", "Annuler", "Cancel"), QMessageBox.RejectRole
            )
            box.exec()
            if box.clickedButton() == btn_ws:
                try:
                    self.select_workspace()
                except Exception:
                    pass
            elif box.clickedButton() == btn_venv:
                try:
                    self.select_venv_manually()
                except Exception:
                    pass
        except Exception:
            pass
        return
    modules = set()
    # Détermine la liste des fichiers à analyser (sélectionnés ou tous les fichiers du projet)
    files = self.selected_files if self.selected_files else self.python_files
    # Exclure les fichiers du venv et les dossiers cachés/__pycache__
    if self.venv_path_manuel:
        venv_dir = os.path.abspath(self.venv_path_manuel)
    else:
        venv_dir = os.path.abspath(os.path.join(self.workspace_dir, "venv"))
    filtered_files = []
    for f in files:
        abs_f = _normalize_realpath(f)
        try:
            if venv_dir and _is_path_under(abs_f, _normalize_realpath(venv_dir)):
                continue
        except Exception:
            pass
        if _should_skip_analysis_path(abs_f, getattr(self, "workspace_dir", None)):
            continue
        filtered_files.append(abs_f)

    # Créer une barre de progression pour l'analyse
    analysis_progress = None
    try:
        analysis_progress = ProgressDialog(
            self.tr("Analyse des dépendances", "Analyzing dependencies"), self
        )
        analysis_progress.set_message(
            self.tr("Analyse des fichiers Python...", "Analyzing Python files...")
        )
        analysis_progress.set_progress(0, len(filtered_files))
        analysis_progress.show()
    except Exception:
        pass

    # Analyse chaque fichier Python pour détecter les imports
    last_pump = 0
    for idx, file in enumerate(filtered_files):
        try:
            # Mettre à jour la progression
            if analysis_progress:
                file_name = os.path.basename(file)
                analysis_progress.set_message(
                    self.tr("Analyse de {file}...", "Analyzing {file}...").format(
                        file=file_name
                    )
                )
                analysis_progress.set_progress(idx, len(filtered_files))
            if idx - last_pump >= 50:
                QApplication.processEvents()
                last_pump = idx
            modules.update(
                _extract_imported_modules_from_file(
                    file,
                    workspace_dir=getattr(self, "workspace_dir", None),
                )
            )
        except Exception as e:
            _log_append(self, f"⚠️ Erreur analyse dépendances dans {file} : {e}")

    # Fermer la barre de progression d'analyse
    if analysis_progress:
        analysis_progress.set_message(self.tr("Analyse terminée", "Analysis completed"))
        analysis_progress.set_progress(len(filtered_files), len(filtered_files))
    # Classify imports as stdlib/internal/third-party/unknown.
    ws_root = _normalize_realpath(getattr(self, "workspace_dir", None) or "")
    internal_modules = _collect_workspace_module_roots(filtered_files, ws_root)
    # Mise à jour du message de progression
    if analysis_progress:
        analysis_progress.set_message(
            self.tr("Vérification des modules...", "Checking modules...")
        )

    suggestions = []
    category_stats = {"stdlib": 0, "internal": 0, "third_party": 0, "unknown": 0}
    for m in sorted(modules):
        if m in internal_modules:
            category = "internal"
        else:
            category = _classify_module_origin(m, ws_root)
            if category == "unknown" and m in internal_modules:
                category = "internal"
        category_stats[category] = category_stats.get(category, 0) + 1
        if category in ("third_party", "unknown"):
            suggestions.append(m)

    try:
        _log_append(
            self,
            "ℹ️ Imports classes: "
            f"stdlib={category_stats.get('stdlib', 0)}, "
            f"internal={category_stats.get('internal', 0)}, "
            f"third_party={category_stats.get('third_party', 0)}, "
            f"unknown={category_stats.get('unknown', 0)}",
        )
    except Exception:
        pass
    # Alerte spéciale pour tkinter (std lib optionnelle non installable via pip)
    try:
        import importlib.util as _il_util

        if "tkinter" in modules:
            if _il_util.find_spec("tkinter") is None:
                msg = (
                    "Le module tkinter n'est pas disponible dans votre environnement Python. "
                    "tkinter fait partie de la bibliothèque standard mais nécessite des paquets système et ne s'installe pas via pip.\n\n"
                    "Installez-le avec votre gestionnaire de paquets:\n"
                    "- Ubuntu/Debian: sudo apt install python3-tk\n"
                    "- Fedora: sudo dnf install python3-tkinter\n"
                    "- Arch: sudo pacman -S tk\n"
                    "- macOS: brew install tcl-tk (puis réinstallez Python avec le support Tk)\n"
                    "- Windows: réinstallez Python en incluant Tcl/Tk"
                )
                _log_append(self, f"ℹ️ {msg}")
                try:
                    QMessageBox.information(
                        self, self.tr("tkinter manquant", "Missing tkinter"), msg
                    )
                except Exception:
                    pass
    except Exception:
        pass
    if not suggestions:
        _log_append(self, "✅ Aucun module externe à installer détecté.")
        if analysis_progress:
            analysis_progress.close()
        return
    # Vérifie la présence des modules dans le venv (via pip show)
    # Utilise la fonction robuste de détection du pip
    if getattr(self, "use_system_python", False):
        pip_program, pip_prefix = _find_pip_executable(
            venv_path=None, workspace_dir=None
        )
    else:
        pip_program, pip_prefix = _find_pip_executable(
            venv_path=self.venv_path_manuel, workspace_dir=self.workspace_dir
        )
    try:
        _log_append(self, f"ℹ️ Utilisation de pip: {pip_program} {' '.join(pip_prefix)}")
    except Exception:
        pass
    # Vérification des modules avec progression (préférer un seul pip list pour limiter le blocage UI)
    not_installed = []
    installed = set()
    try:
        cmd = [pip_program, *pip_prefix, "list", "--format=json"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            try:
                data = json.loads(
                    result.stdout.decode("utf-8", errors="replace") or "[]"
                )
                for item in data:
                    name = str(item.get("name", "")).strip()
                    if name:
                        installed.add(name.lower().replace("_", "-"))
            except Exception:
                installed = set()
        else:
            installed = set()
    except Exception:
        installed = set()

    if installed:
        for idx, module in enumerate(suggestions):
            try:
                if analysis_progress:
                    analysis_progress.set_message(
                        self.tr(
                            "Vérification de {module}...", "Checking {module}..."
                        ).format(module=module)
                    )
                    analysis_progress.set_progress(idx, len(suggestions))
                if idx % 50 == 0:
                    QApplication.processEvents()
                key = module.lower().replace("_", "-")
                if key not in installed:
                    not_installed.append(module)
            except Exception as e:
                _log_append(
                    self, f"⚠️ Erreur lors de la vérification du module {module} : {e}"
                )
    else:
        for idx, module in enumerate(suggestions):
            try:
                if analysis_progress:
                    analysis_progress.set_message(
                        self.tr(
                            "Vérification de {module}...", "Checking {module}..."
                        ).format(module=module)
                    )
                    analysis_progress.set_progress(idx, len(suggestions))
                if idx % 20 == 0:
                    QApplication.processEvents()

                cmd = [pip_program, *pip_prefix, "show", module]
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                if result.returncode != 0:
                    not_installed.append(module)
            except Exception as e:
                _log_append(
                    self, f"⚠️ Erreur lors de la vérification du module {module} : {e}"
                )

    # Fermer la barre de progression d'analyse
    if analysis_progress:
        analysis_progress.close()
    # Si des modules sont manquants, propose l'installation automatique
    if not_installed:
        _log_append(
            self,
            "❗ Modules manquants dans le venv : " + ", ".join(sorted(not_installed)),
        )
        # Demande à l'utilisateur s'il souhaite installer automatiquement les modules manquants
        reply = QMessageBox.question(
            self,
            self.tr("Installer les dépendances", "Install dependencies"),
            self.tr(
                "Installer automatiquement les modules manquants ?\n{mods}",
                "Automatically install missing modules?\n{mods}",
            ).format(mods=", ".join(not_installed)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._dep_install_index = 0
            self._dep_install_list = not_installed
            # Programme pip pour QProcess: si pip du venv existe, l'utiliser; sinon python -m pip
            try:
                self._dep_pip_program = pip_program
                self._dep_pip_prefix = list(pip_prefix)
            except Exception:
                self._dep_pip_program = sys.executable
                self._dep_pip_prefix = ["-m", "pip"]
            self.dep_progress_dialog = ProgressDialog(
                self.tr("Installation des dépendances", "Installing dependencies"), self
            )
            self.dep_progress_dialog.set_message(
                self.tr("Installation de {m}...", "Installing {m}...").format(
                    m=not_installed[0]
                )
            )
            self.dep_progress_dialog.set_progress(0, len(not_installed))
            self.dep_progress_dialog.show()
            _install_next_dependency(self)
    else:
        _log_append(
            self, "✅ Tous les modules nécessaires sont déjà installés dans le venv."
        )


# Installation automatique des dépendances manquantes (récursif)
def _install_next_dependency(self):
    # Si tous les modules ont été installés, termine le processus
    if self._dep_install_index >= len(self._dep_install_list):
        self.dep_progress_dialog.set_message(
            self.tr("Installation terminée.", "Installation completed.")
        )
        self.dep_progress_dialog.set_progress(
            len(self._dep_install_list), len(self._dep_install_list)
        )
        self.dep_progress_dialog.close()
        _log_append(self, "✅ Tous les modules manquants ont été installés.")
        return
    module = self._dep_install_list[self._dep_install_index]
    msg = f"Installation de {module}... ({self._dep_install_index+1}/{len(self._dep_install_list)})"
    self.dep_progress_dialog.set_message(msg)
    self.dep_progress_dialog.progress.setRange(
        0, 0
    )  # indéterminé pendant l'installation
    process = QProcess(self)
    # Utilise le programme et préfixe déterminés (pip du venv ou 'python -m pip')
    try:
        import sys as _sys

        default_prog = _sys.executable
    except Exception:
        default_prog = "python"
    program = getattr(self, "_dep_pip_program", None) or default_prog
    prefix = list(getattr(self, "_dep_pip_prefix", ["-m", "pip"]))
    process.setProgram(program)
    process.setArguments(prefix + ["install", module])
    process.readyReadStandardOutput.connect(lambda: _on_dep_pip_output(self, process))
    process.readyReadStandardError.connect(
        lambda: _on_dep_pip_output(self, process, error=True)
    )
    process.finished.connect(
        lambda code, status: _on_dep_pip_finished(self, process, code, status)
    )
    process.start()


# Affiche la sortie de pip dans la ProgressDialog et les logs
def _on_dep_pip_output(self, process, error=False):
    data = (
        process.readAllStandardError().data().decode()
        if error
        else process.readAllStandardOutput().data().decode()
    )
    if hasattr(self, "dep_progress_dialog") and self.dep_progress_dialog:
        lines = data.strip().splitlines()
        if lines:
            self.dep_progress_dialog.set_message(lines[-1])
    _log_append(self, data)


# Callback après l'installation d'un module (pip)
def _on_dep_pip_finished(self, process, code, status):
    module = self._dep_install_list[self._dep_install_index]
    if code == 0:
        _log_append(self, f"✅ {module} installé.")
    else:
        _log_append(self, f"❌ Erreur installation {module} (code {code})")
    # Met à jour la progression globale
    self._dep_install_index += 1
    self.dep_progress_dialog.progress.setRange(0, len(self._dep_install_list))
    self.dep_progress_dialog.set_progress(
        self._dep_install_index, len(self._dep_install_list)
    )
    _install_next_dependency(self)
