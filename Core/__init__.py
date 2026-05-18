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
This module now exposes only pure business-logic types and helpers.
Qt-dependent classes have been moved to Ui/Gui/Compilation/.
"""

from __future__ import annotations

# Importations de utils.py
from Core.Compiler.utils import (
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

__all__ = [
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
]
__version__ = "1.1.0"
__author__ = "Ague Samuel Amen"
