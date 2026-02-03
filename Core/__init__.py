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


__all__ = [
    "CompilationStatus",
    "CompilationSignals",
    "CompilationThread",
    "CompilerCore",
    "ProcessState",
    "MainProcessSignals",
    "MainProcess",
    "build_command",
    "validate_command",
    "escape_arguments",
    "sanitize_path",
    "CommandBuilder",
    "detect_python_executable",
    "get_interpreter_version",
    "check_module_available",
    "ProcessInfo",
    "ProcessKiller",
    "kill_process",
    "kill_process_tree",
    "get_process_info",
]
__version__ = "1.0.0"
__author__ = "Ague Samuel Amen"
