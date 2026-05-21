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

from Loaders.EngineLoader.loader import _auto_discover

from . import registry as registry  # re-export registry module
from .base import CompilerEngine  # re-export base type
from .registry import available_engines as _registry_available_engines
from .registry import bind_tabs as _registry_bind_tabs
from .registry import create as _registry_create
from .registry import get_engine as _registry_get_engine
from .registry import unload_all as _registry_unload_all

__version__ = "1.0.0"

_DISCOVERY_DONE = False


def _ensure_discovered() -> None:
    """Load project engines on first real registry access.

    Keeping discovery lazy avoids importing every engine package during harmless
    module imports such as CLI headless bootstrap or SDK helper loading.
    """
    global _DISCOVERY_DONE
    if _DISCOVERY_DONE:
        return
    try:
        if str(os.environ.get("ARK_ENGINES_AUTO_DISCOVER", "1")).lower() not in (
            "0",
            "false",
            "no",
        ):
            _auto_discover()
    except Exception:
        pass
    finally:
        _DISCOVERY_DONE = True


def get_engine(eid: str):
    _ensure_discovered()
    return _registry_get_engine(eid)


def available_engines() -> list[str]:
    _ensure_discovered()
    return _registry_available_engines()


def create(eid: str):
    _ensure_discovered()
    return _registry_create(eid)


def bind_tabs(gui) -> None:
    _ensure_discovered()
    return _registry_bind_tabs(gui)


def unload_all():
    global _DISCOVERY_DONE
    result = _registry_unload_all()
    _DISCOVERY_DONE = False
    return result


__all__ = [
    "CompilerEngine",
    "registry",
    "unload_all",
    "get_engine",
    "available_engines",
    "create",
    "bind_tabs",
]
