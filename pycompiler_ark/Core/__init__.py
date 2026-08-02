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
PyCompiler ARK - Compiler Core Module

Main compiler core module for PyCompiler ARK.
This module now exposes only pure business-logic types and helpers.
Qt-dependent classes have been moved to Ui/Gui/Compilation/.
"""

from __future__ import annotations

# Imports of allversion.py
from .allversion import (
    get_bcasl_version,
    get_core_version,
    get_engine_sdk_version,
)

# Imports of utils.py
from .Compiler.utils import (
    CommandBuilder,
    build_command,
    escape_arguments,
    sanitize_path,
    validate_command,
)

# Process_killer.py imports
from .process_killer import (
    ProcessInfo,
    ProcessKiller,
    get_process_info,
    kill_process,
    kill_process_tree,
)

# Venv_Manager/Manager.py imports
from .Venv_Manager.Manager import VenvManager

__all__ = [
    "build_command",
    "validate_command",
    "escape_arguments",
    "sanitize_path",
    "CommandBuilder",
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
__author__ = "Samuel Amen Ague"
