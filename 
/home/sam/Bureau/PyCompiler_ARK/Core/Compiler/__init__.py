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

"""
PyCompiler ARK - Compiler Core Module

Module principal du compilateur pour PyCompiler ARK.
Gère l'exécution des processus de compilation avec support threading
et communication en temps réel avec l'interface utilisateur.

Classes principales:
- CompilerCore: Classe principale du compilateur
- CompilationThread: Thread pour exécution non-bloquante
- MainProcess: Processus principal de compilation
- ProcessKiller: Gestion des processus

Fonctions:
- compile_all: Compile tous les fichiers sélectionnés
- cancel_all_compilations: Annule toutes les compilations en cours
- kill_process: Tue un processus
- kill_process_tree: Tue un processus et ses enfants
- build_command: Construit une commande de compilation
- validate_command: Valide une commande de compilation
"""

from __future__ import annotations

# Instance globale du MainProcess (pour compatibilité avec l'UI)
_global_main_process = None


def _get_main_process():
    """Retourne l'instance globale du MainProcess."""
    global _global_main_process
    if _global_main_process is None:
        _global_main_process = MainProcess()
    return _global_main_process


# Importations de compiler.py
from Core.Compiler.compiler import (
    CompilationStatus,
    CompilationSignals,
    CompilationThread,
    CompilerCore,
)

# Importations de mainprocess.py
from Core.Compiler.mainprocess import (
    ProcessState,
    MainProcessSignals,
    MainProcess,
)

# Importations de command_helpers.py
from Core.Compiler.command_helpers import (
    build_command,
    validate_command,
    escape_arguments,
    sanitize_path,
    CommandBuilder,
    detect_python_executable,
    get_interpreter_version,
    check_module_available,
)

# Importations de process_killer.py
from Core.Compiler.process_killer import (
    ProcessInfo,
    ProcessKiller,
    kill_process,
    kill_process_tree,
    get_process_info,
)


def compile_all(gui_instance) -> bool:
    """
    Compile tous les fichiers sélectionnés en utilisant l'instance GUI.

    Args:
        gui_instance: Instance de l'interface graphique PyCompilerArkGui

    Returns:
        True si la compilation a démarrer, False sinon
    """
    mp = _get_main_process()

    # Synchroniser le workspace
    if hasattr(gui_instance, "workspace_dir") and gui_instance.workspace_dir:
        mp.set_workspace(gui_instance.workspace_dir)

    # Récupérer les fichiers à compiler
    files = []
    if hasattr(gui_instance, "python_files"):
        files = gui_instance.python_files

    if not files:
        if hasattr(gui_instance, "log") and gui_instance.log:
            gui_instance.log.append("⚠️ Aucun fichier à compiler")
        return False

    # Vérifier qu'un moteur est sélectionné
    if not hasattr(gui_instance, "compiler_tabs") or not gui_instance.compiler_tabs:
        if hasattr(gui_instance, "log") and gui_instance.log:
            gui_instance.log.append("⚠️ Aucun moteur de compilation disponible")
        return False

    try:
        import EngineLoader as engines_loader

        idx = gui_instance.compiler_tabs.currentIndex()
        engine_id = engines_loader.registry.get_engine_for_tab(idx)

        if not engine_id:
            if hasattr(gui_instance, "log") and gui_instance.log:
                gui_instance.log.append("⚠️ Aucun moteur sélectionné")
            return False

        mp.set_engine(engine_id)

    except Exception as e:
        if hasattr(gui_instance, "log") and gui_instance.log:
            gui_instance.log.append(f"⚠️ Erreur lors de la sélection du moteur: {e}")
        return False

    # Démarrer la compilation pour chaque fichier
    success_count = 0
    for file_path in files:
        try:
            mp.set_file(file_path)
            # La commande sera générée par le moteur
            # Pour l'instant, on retourne True si le MainProcess est prêt
            success_count += 1

        except Exception as e:
            if hasattr(gui_instance, "log") and gui_instance.log:
                gui_instance.log.append(f"❌ Erreur pour {file_path}: {e}")

    if hasattr(gui_instance, "log") and gui_instance.log:
        gui_instance.log.append(
            f"✅ {success_count} fichier(s) prêt(s) pour compilation"
        )

    return success_count > 0


def cancel_all_compilations() -> bool:
    """
    Annule toutes les compilations en cours.

    Returns:
        True si l'annulation a été demandée, False sinon
    """
    mp = _get_main_process()
    return mp.cancel()


def handle_finished(return_code: int) -> None:
    """
    Gère la fin d'une compilation.

    Args:
        return_code: Code de retour du processus
    """
    # La gestion est faite via les signaux du MainProcess


def handle_stderr(error: str) -> None:
    """
    Gère les erreurs stderr.

    Args:
        error: Message d'erreur
    """
    pass


def handle_stdout(output: str) -> None:
    """
    Gère la sortie stdout.

    Args:
        output: Sortie standard
    """
    pass


def show_error_dialog(parent, title: str, message: str) -> None:
    """
    Affiche une boîte de dialogue d'erreur.

    Args:
        parent: Widget parent
        title: Titre de la boîte de dialogue
        message: Message d'erreur
    """
    from PySide6.QtWidgets import QMessageBox

    QMessageBox.critical(parent, title, message)


def try_install_missing_modules(parent, missing: list) -> bool:
    """
    Tente d'installer les modules manquants.

    Args:
        parent: Widget parent
        missing: Liste des modules manquants

    Returns:
        True si l'installation a réussi, False sinon
    """
    # TODO: Implémenter l'installation des modules manquants
    return False


def try_start_processes(gui_instance) -> bool:
    """
    Tente de démarrer les processus de compilation.

    Args:
        gui_instance: Instance de l'interface graphique

    Returns:
        True si les processus ont démarrer, False sinon
    """
    return compile_all(gui_instance)


def start_compilation_process(gui_instance) -> bool:
    """
    Démarre un processus de compilation.

    Args:
        gui_instance: Instance de l'interface graphique

    Returns:
        True si le processus a démarrer, False sinon
    """
    return compile_all(gui_instance)


def _continue_compile_all(gui_instance) -> bool:
    """
    Continue la compilation de tous les fichiers.

    Args:
        gui_instance: Instance de l'interface graphique

    Returns:
        True si la compilation continue, False sinon
    """
    return compile_all(gui_instance)


__all__ = [
    # Classes de compiler.py
    "CompilationStatus",
    "CompilationSignals",
    "CompilationThread",
    "CompilerCore",
    # Classes de mainprocess.py
    "ProcessState",
    "MainProcessSignals",
    "MainProcess",
    # Fonctions de command_helpers.py
    "build_command",
    "validate_command",
    "escape_arguments",
    "sanitize_path",
    "CommandBuilder",
    "detect_python_executable",
    "get_interpreter_version",
    "check_module_available",
    # Classes et fonctions de process_killer.py
    "ProcessInfo",
    "ProcessKiller",
    "kill_process",
    "kill_process_tree",
    "get_process_info",
    # Fonctions de compatibilité UI
    "compile_all",
    "cancel_all_compilations",
    "handle_finished",
    "handle_stderr",
    "handle_stdout",
    "show_error_dialog",
    "try_install_missing_modules",
    "try_start_processes",
    "start_compilation_process",
    "_continue_compile_all",
]

__version__ = "1.0.0"
__author__ = "Ague Samuel Amen"
