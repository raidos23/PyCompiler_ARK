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

Main compiler core module for PyCompiler ARK.
Handles compilation process execution with threading support and
real-time communication with the user interface.

Main classes:
- CompilerCore: Main compiler class
- CompilationThread: Non-blocking execution thread
- MainProcess: Main compilation process
- ProcessKiller: Process management helpers

Functions:
- compile_all: Compile all selected files
- cancel_all_compilations: Cancel all running compilations
- kill_process: Terminate one process
- kill_process_tree: Terminate one process and its children
- build_command: Build a compilation command
- validate_command: Validate a compilation command
"""

from __future__ import annotations

# Instance globale du MainProcess (pour compatibilité avec l'UI)
_global_main_process = None


def _get_main_process():
    """Return the global `MainProcess` instance."""
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

# Importations de mainprocess.py (fonctions intégrées depuis command_helpers.py)
# Note: command_helpers.py a été supprimé et ses fonctions ont été
# intégrées dans mainprocess.py avec la gestion ArkConfig
from Core.Compiler.mainprocess import (
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

# Importations de Venv_Manager/Manager.py
from Core.Venv_Manager.Manager import (
    VenvManager,
)

# Importations de allversion.py
from Core.allversion import (
    get_core_version,
    get_bcasl_version,
    get_engine_sdk_version,
)

# Importations de Gui.py
from Core.Gui import PyCompilerArkGui

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
    "VenvManager",
    "get_core_version",
    "get_bcasl_version",
    "get_engine_sdk_version",
    "PyCompilerArkGui",
]
__version__ = "1.0.0"
__author__ = "Ague Samuel Amen"
