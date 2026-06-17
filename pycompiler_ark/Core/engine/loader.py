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

from __future__ import annotations

import importlib
import inspect
import logging
import os
import pkgutil
import sys
from types import ModuleType

from pycompiler_ark.Core.engine import registry as engine_registry
from pycompiler_ark.Core.engine.base import CompilerEngine

logger = logging.getLogger(__name__)


def _iter_engine_module_names(base_path: str, namespace_package: str) -> list[str]:
    """Return top-level engine package names under the configured namespace."""
    if not os.path.isdir(base_path):
        return []
    prefix = f"{namespace_package.rstrip('.') }."
    return [
        name
        for _finder, name, ispkg in pkgutil.iter_modules([base_path], prefix=prefix)
        if ispkg
    ]


def _register_engine_classes(module: ModuleType) -> list[str]:
    """Register CompilerEngine subclasses declared by an imported module."""
    registered: list[str] = []
    for _name, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, CompilerEngine) or obj is CompilerEngine:
            continue
        try:
            if not str(getattr(obj, "__module__", "")).startswith(module.__name__):
                continue
            engine_registry.engine_register(obj)
            registered.append(getattr(obj, "id", obj.__name__))
        except Exception:
            logger.exception(
                "Failed to register engine class %s from module %s",
                getattr(obj, "__name__", repr(obj)),
                module.__name__,
            )
    return registered


def _import_module_tree(module_name: str) -> list[ModuleType]:
    """Import a package and its submodules, returning successfully loaded modules."""
    imported: list[ModuleType] = []
    root_module = importlib.import_module(module_name)
    imported.append(root_module)

    module_path = getattr(root_module, "__path__", None)
    if not module_path:
        return imported

    for _finder, subname, _ispkg in pkgutil.walk_packages(
        module_path, prefix=f"{module_name}."
    ):
        try:
            imported.append(importlib.import_module(subname))
        except Exception:
            logger.exception("Failed to import engine submodule %s", subname)
    return imported


def _sync_engine_sdk_registry() -> None:
    """Keep engine_sdk.registry aligned with the active engine registry module."""
    try:
        import pycompiler_ark.engine_sdk as engine_sdk

        engine_sdk.registry = engine_registry
    except Exception:
        logger.exception(
            "Failed to synchronize engine_sdk.registry with Core.engine.registry"
        )


def _discover_external_plugins(
    base_path: str, namespace_package: str = "engines"
) -> None:
    """Import namespaced engine packages and register CompilerEngine classes dynamically."""
    try:
        if not os.path.isdir(base_path):
            return

        parent_dir = os.path.abspath(os.path.dirname(base_path))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

        for module_name in _iter_engine_module_names(base_path, namespace_package):
            try:
                imported_modules = _import_module_tree(module_name)
            except Exception:
                logger.exception("Failed to import engine package %s", module_name)
                continue

            registered_any = False
            for module in imported_modules:
                try:
                    if _register_engine_classes(module):
                        registered_any = True
                except Exception:
                    logger.exception(
                        "Failed while introspecting engine module %s",
                        getattr(module, "__name__", module_name),
                    )
            if not registered_any:
                logger.warning(
                    "No CompilerEngine subclasses were discovered in engine package %s",
                    module_name,
                )
    except Exception:
        logger.exception("Engine discovery failed for base path %s", base_path)
    finally:
        _sync_engine_sdk_registry()


def _auto_discover() -> None:
    """Discover and register external engine plugins from multiple locations."""
    # 1. Project local engines folder
    try:
        project_root = os.path.abspath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), os.pardir, os.pardir
            )
        )
        external_dir = os.path.join(project_root, "engines")
        # Ensure directory exists for auto-discovery
        os.makedirs(external_dir, exist_ok=True)
        _discover_external_plugins(external_dir, namespace_package="engines")
    except Exception:
        logger.exception("Automatic engine discovery failed for project engines folder")

    # 2. User-level and Dev-level engines folders (from pycompiler_ark.Core.Configs)
    try:
        from pycompiler_ark.Core.Configs import resolve_config_value

        for key in ("user-engine-dir", "dev-engine-dir"):
            try:
                dir_path = resolve_config_value(key, create_default=False)
                if dir_path and os.path.isdir(dir_path):
                    # We discover plugins in these external folders using 'engines' namespace
                    _discover_external_plugins(dir_path, namespace_package="engines")
            except Exception:
                logger.warning("Failed to discover engines from config key: %s", key)
    except Exception:
        logger.exception("External engine discovery from user config failed")
    finally:
        _sync_engine_sdk_registry()
