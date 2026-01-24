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

from PySide6.QtWidgets import QMessageBox
import os
import traceback
from Core.ark_config_loader import (
    load_ark_config,
    should_exclude_file,
    get_compiler_options,
    get_output_options,
    get_dependency_options,
)


def _kill_all_processes(self) -> None:
    """Tue tous les processus de compilation en cours et réinitialise l'état.

    Cette fonction doit être appelée en cas d'erreur pour nettoyer proprement
    tous les processus lancés et réinitialiser l'interface utilisateur.
    """
    try:
        # Arrêter tous les processus en cours
        if hasattr(self, "processes") and self.processes:
            for pid, proc in list(self.processes.items()):
                try:
                    if proc is not None and proc.state() == proc.Running:
                        proc.terminate()
                        proc.waitForFinished(2000)  # Attendre max 2s
                        if proc.state() == proc.Running:
                            proc.kill()
                            proc.waitForFinished(1000)
                except Exception:
                    pass
            # Vider le dictionnaire des processus
            self.processes.clear()
    except Exception:
        pass

    try:
        # Vider la file d'attente
        if hasattr(self, "queue"):
            self.queue.clear()
    except Exception:
        pass

    try:
        # Réinitialiser les compteurs
        if hasattr(self, "current_compiling"):
            self.current_compiling.clear()
    except Exception:
        pass

    # Réactiver les contrôles UI
    try:
        self.set_controls_enabled(True)
    except Exception:
        pass

    try:
        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            self.compiler_tabs.setEnabled(True)
    except Exception:
        pass

    try:
        if hasattr(self, "progress"):
            self.progress.setRange(0, 1)
            self.progress.setValue(0)
    except Exception:
        pass

    try:
        if hasattr(self, "_compile_continued"):
            self._compile_continued = False
    except Exception:
        pass


# Nouvelle version de try_start_processes pour gérer les fichiers ignorés dynamiquement
def _continue_compile_all(self):
    # Charger la configuration ARK complète
    ark_config = load_ark_config(self.workspace_dir)
    exclusion_patterns = ark_config.get("exclusion_patterns", [])
    inclusion_patterns = ark_config.get("inclusion_patterns", ["**/*.py"])
    auto_detect_entry_points = ark_config.get("auto_detect_entry_points", True)
    compile_only_main_ark = ark_config.get("compile_only_main", False)
    main_file_names_ark = ark_config.get("main_file_names", ["main.py", "app.py"])

    # Déplacé depuis compile_all pour poursuivre après BCASL sans bloquer l'UI
    # Compteurs pour les exclusions
    exclusion_counts = {
        "site_packages": 0,
        "ark_patterns": 0,
        "no_entry_point": 0,
        "read_error": 0,
        "not_exists": 0,
    }

    def is_executable_script(path):
        # Vérifie que le fichier existe, n'est pas dans site-packages, et contient un point d'entrée
        if not os.path.exists(path):
            exclusion_counts["not_exists"] += 1
            return False

        # Vérifier les patterns d'exclusion depuis ARK_Main_Config.yml
        if should_exclude_file(path, self.workspace_dir, exclusion_patterns):
            exclusion_counts["ark_patterns"] += 1
            return False

        if "site-packages" in path:
            exclusion_counts["site_packages"] += 1
            return False

        # Si auto_detect_entry_points est désactivé, accepter tous les fichiers
        if not auto_detect_entry_points:
            return True

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
                if (
                    "if __name__ == '__main__'" in content
                    or 'if __name__ == "__main__"' in content
                ):
                    return True
                else:
                    exclusion_counts["no_entry_point"] += 1
                    return False
        except Exception as e:
            exclusion_counts["read_error"] += 1
            return False

    # Détection du compilateur actif
    use_nuitka = False
    if hasattr(self, "compiler_tabs") and self.compiler_tabs:
        self.compiler_tabs.setEnabled(
            False
        )  # Désactive les onglets au début de la compilation
        if self.compiler_tabs.currentIndex() == 1:  # 0 = PyInstaller, 1 = Nuitka
            use_nuitka = True

    # L'option UI a priorité sur la config ARK
    compile_only_main = (
        self.opt_main_only.isChecked()
        if hasattr(self, "opt_main_only") and self.opt_main_only is not None
        else compile_only_main_ark
    )

    # Sélection des fichiers à compiler selon le compilateur
    if use_nuitka:
        # Nuitka : compile tous les fichiers sélectionnés ou tous les fichiers du workspace
        if self.selected_files:
            files_ok = [f for f in self.selected_files if is_executable_script(f)]
        else:
            files_ok = [f for f in self.python_files if is_executable_script(f)]
        self.queue = [(f, True) for f in files_ok]
    else:
        # PyInstaller : applique la logique main.py/app.py uniquement si l'option est cochée
        if self.selected_files:
            files_ok = [f for f in self.selected_files if is_executable_script(f)]
            self.queue = [(f, True) for f in files_ok]
        elif compile_only_main:
            # Utiliser les noms de fichiers depuis la config ARK
            files = [
                f
                for f in self.python_files
                if os.path.basename(f) in main_file_names_ark
            ]
            files_ok = [f for f in files if is_executable_script(f)]
            self.queue = [(f, True) for f in files_ok]
            if not files_ok:
                main_names_str = ", ".join(main_file_names_ark)
                self.log.append(
                    f"❌ Aucun fichier exécutable trouvé parmi : {main_names_str}\n"
                    f"   Raison : Les fichiers spécifiés n'ont pas de point d'entrée (if __name__ == '__main__') ou n'existent pas.\n"
                )
                self.set_controls_enabled(True)
                if hasattr(self, "compiler_tabs") and self.compiler_tabs:
                    self.compiler_tabs.setEnabled(True)
                return
        else:
            files_ok = [f for f in self.python_files if is_executable_script(f)]
            self.queue = [(f, True) for f in files_ok]

    # Vérifier s'il y a des fichiers à compiler
    if not files_ok:
        try:
            self.log.append(
                f"❌ Aucun fichier exécutable à compiler.\n"
                f"   Raisons possibles :\n"
                f"   • Aucun fichier Python sélectionné ou dans le workspace\n"
                f"   • Les fichiers n'ont pas de point d'entrée (if __name__ == '__main__')\n"
                f"   • Les fichiers sont dans site-packages ou correspondent à des patterns d'exclusion\n"
                f"   • Les fichiers n'existent pas ou ne sont pas accessibles\n"
            )
        except Exception:
            pass
        try:
            self.set_controls_enabled(True)
        except Exception:
            pass
        try:
            if hasattr(self, "compiler_tabs") and self.compiler_tabs:
                self.compiler_tabs.setEnabled(True)
        except Exception:
            pass
        return

    try:
        self.current_compiling.clear()
    except Exception:
        pass
    try:
        self.processes.clear()
    except Exception:
        pass
    try:
        self.progress.setRange(0, 0)  # Mode indéterminé pendant toute la compilation
    except Exception:
        pass

    # Afficher les informations de configuration ARK
    if ark_config:
        try:
            self.log.append("📋 Configuration ARK chargée depuis ARK_Main_Config.yml\n")
        except Exception:
            pass
        # Afficher les paramètres de compilation utilisés
        try:
            self.log.append(
                f"   • Patterns d'inclusion : {', '.join(inclusion_patterns)}\n"
            )
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Patterns d'exclusion : {len(exclusion_patterns)} pattern(s)\n"
            )
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Détection point d'entrée : {'Activée' if auto_detect_entry_points else 'Désactivée'}\n"
            )
        except Exception:
            pass
        try:
            self.log.append(
                f"   • Compiler uniquement main : {'Oui' if compile_only_main else 'Non'}\n"
            )
        except Exception:
            pass

    try:
        self.log.append(
            f"🔨 Compilation parallèle démarrée ({len(files_ok)} fichier(s))...\n"
        )
    except Exception:
        pass

    try:
        self.set_controls_enabled(False)
    except Exception:
        pass
    try:
        self.try_start_processes()
    except Exception:
        pass


def compile_all(self):
    import os

    # Garde-fous avant toute opération
    if self.processes:
        try:
            QMessageBox.warning(
                self,
                self.tr("Attention", "Warning"),
                self.tr(
                    "Des compilations sont déjà en cours.",
                    "Builds are already running.",
                ),
            )
        except Exception:
            pass
        return
    if not self.workspace_dir or (not self.python_files and not self.selected_files):
        try:
            self.log.append("❌ Aucun fichier à compiler.\n")
        except Exception:
            pass
        return

    # Réinitialise les statistiques de compilation pour ce run
    try:
        self._compilation_times = {}
    except Exception:
        pass

    # Désactiver immédiatement les contrôles sensibles (sauf Annuler) et les onglets pendant toute la (pré)compilation
    try:
        self.set_controls_enabled(False)
    except Exception:
        pass
    try:
        if hasattr(self, "compiler_tabs") and self.compiler_tabs:
            self.compiler_tabs.setEnabled(False)
    except Exception:
        pass

    # BCASL: exécution des plugins API avant compilation, sans bloquer l'UI
    try:
        from bcasl.Loader import run_pre_compile_async as _run_bcasl_async

        # Drapeau de poursuite pour éviter le double déclenchement
        try:
            self._compile_continued = False
        except Exception:
            pass

        # Gating strict: pas de fallback; la compilation ne démarre qu'après la fin de BCASL
        # Continuer la préparation de la compilation une fois BCASL terminé
        def _after_bcasl(_report):
            try:
                # Stop fallback timer if any
                try:
                    tmr2 = getattr(self, "_compile_phase_timer", None)
                    if tmr2:
                        tmr2.stop()
                except Exception:
                    pass

                # Vérifier si BCASL a eu des erreurs
                if _report is not None:
                    if isinstance(_report, dict):
                        # Cas spécial: BCASL désactivé
                        if _report.get("status") == "disabled":
                            # BCASL désactivé, continuer normalement
                            pass
                        else:
                            # Autre dict inattendu, traiter comme erreur
                            try:
                                self.log.append(f"❌ Erreur BCASL: rapport inattendu {_report}\n")
                            except Exception:
                                pass
                            _kill_all_processes(self)
                            return
                    elif hasattr(_report, 'ok') and not _report.ok:
                        error_items = [item for item in _report.items if not item.success]
                        error_msg = ", ".join(
                            [f"{item.plugin_id}: {item.error}" for item in error_items]
                        )
                        try:
                            self.log.append(f"❌ Erreur BCASL: {error_msg}\n")
                        except Exception:
                            pass
                        # Nettoyer tout et réactiver l'UI
                        _kill_all_processes(self)
                        return

                if not getattr(self, "_compile_continued", False):
                    self._compile_continued = True
                    try:
                        self.log.append("⏭️ Démarrage compilation après BCASL.\n")
                    except Exception:
                        pass
                    try:
                        _continue_compile_all(self)
                    except Exception as _e:
                        try:
                            self.log.append(
                                f"❌ Erreur fatale dans _continue_compile_all: {_e}\n{traceback.format_exc()}\n"
                            )
                        except Exception:
                            pass
                        # En cas d'erreur: tout tuer et réinitialiser
                        _kill_all_processes(self)
            except Exception as _e:
                try:
                    self.log.append(
                        f"❌ Erreur critique dans _after_bcasl: {_e}\n{traceback.format_exc()}\n"
                    )
                except Exception:
                    pass
                # En cas d'erreur: tout tuer et réinitialiser
                _kill_all_processes(self)

        _run_bcasl_async(self, _after_bcasl)
        return  # différer la suite dans le callback pour ne pas bloquer
    except Exception as e:
        try:
            self.log.append(
                f"❌ BCASL non exécuté: {e}\nLa compilation est annulée car les API BCASL doivent terminer avant de compiler.\n"
            )
        except Exception:
            pass
        # Réactiver l'UI et sortir
        try:
            if hasattr(self, "compiler_tabs") and self.compiler_tabs:
                self.compiler_tabs.setEnabled(True)
        except Exception:
            pass
        try:
            self.set_controls_enabled(True)
        except Exception:
            pass
        return
