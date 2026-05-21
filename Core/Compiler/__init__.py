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

Business-logic orchestration for the compilation pipeline.
This module exposes only pure business-logic types and helpers.
Qt-dependent classes have been moved to Ui/Gui/Compilation/.
"""

from __future__ import annotations

from Core.Compiler.engine_runner import (
    BuildContext,
    EngineRunnerError,
    resolve_engine_command,
    run_engine_compile,
    run_engine_compile_streaming,
)
from Core.Compiler.process_killer import (
    ProcessInfo,
    ProcessKiller,
    get_process_info,
    kill_process,
    kill_process_tree,
)
from Core.Compiler.utils import (
    CommandBuilder,
    build_command,
    check_module_available,
    detect_python_executable,
    escape_arguments,
    get_interpreter_version,
    sanitize_path,
    validate_command,
)
from Core.engine.registry import create, get_engine

# ============================================================================
# IMPORTS LOCAUX - Core.Compiler
# ============================================================================


__all__ = [
    # utils.py
    "build_command",
    "validate_command",
    "escape_arguments",
    "sanitize_path",
    "CommandBuilder",
    "detect_python_executable",
    "get_interpreter_version",
    "check_module_available",
    # process_killer.py
    "ProcessInfo",
    "ProcessKiller",
    "kill_process",
    "kill_process_tree",
    "get_process_info",
    # engine_runner.py — source of truth for compilation
    "BuildContext",
    "EngineRunnerError",
    "resolve_engine_command",
    "run_engine_compile",
    "run_engine_compile_streaming",
]

__version__ = "1.1.0"
__author__ = "Ague Samuel Amen"
