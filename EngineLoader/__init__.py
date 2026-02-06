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

from EngineLoader.Loader.EngineLoader import _auto_discover

from . import registry as registry  # re-export registry module
from .base import CompilerEngine  # re-export base type
from .registry import unload_all  # re-export unload_all function
from .registry import get_engine  # re-export get_engine function
from .registry import available_engines  # re-export available_engines function
from .registry import create  # re-export create function

__version__ = "1.0.0"


# Perform discovery at import-time so engines are ready for UI/compile usage (packages under ENGINES/ only)
try:
    if str(os.environ.get("ARK_ENGINES_AUTO_DISCOVER", "1")).lower() not in (
        "0",
        "false",
        "no",
    ):
        _auto_discover()
except Exception:
    pass

__all__ = [
    "CompilerEngine",
    "registry",
    "unload_all",
    "get_engine",
    "available_engines",
    "create",
]
