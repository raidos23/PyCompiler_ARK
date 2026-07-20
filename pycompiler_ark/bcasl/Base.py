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

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ..bcasl.PreCompileContext import PreCompileContext

__all__ = [
    "BcPluginBase",
    "PluginMeta",
    "ExecutionReport",
    "bc_register",
]

_logger = logging.getLogger("bcasl")
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(levelname)s] %(message)s")
    _handler.setFormatter(_formatter)
    _logger.addHandler(_handler)
    _logger.setLevel(logging.INFO)

BCASL_PLUGIN_REGISTER_FUNC = "bcasl_register"


@dataclass(frozen=True)
class PluginMeta:
    """Métadonnées d'un plugin."""

    id: str
    name: str
    version: str
    description: str = ""
    author: str = ""
    tags: tuple[str, ...] = ()

    # Versions minimales requises
    required_bcasl_version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_plugins_sdk_version: str = "1.0.0"
    required_bc_plugin_context_version: str = "1.0.0"
    required_general_context_version: str = "1.0.0"

    def __post_init__(self) -> None:
        nid = (self.id or "").strip()
        if not nid:
            raise ValueError("PluginMeta invalide: 'id' requis")
        object.__setattr__(self, "id", nid)

        try:
            if isinstance(self.tags, str):
                normalized = tuple(
                    t.strip().lower() for t in str(self.tags).split(",") if t.strip()
                )
            elif isinstance(self.tags, (list, tuple)):
                normalized = tuple(
                    str(t).strip().lower() for t in self.tags if str(t).strip()
                )
            else:
                normalized = ()
            object.__setattr__(self, "tags", normalized)
        except Exception:
            object.__setattr__(self, "tags", ())


class BcPluginBase:
    """Classe de base pour les plugins BCASL."""

    meta: PluginMeta
    requires: tuple[str, ...]
    priority: int

    def __init__(
        self, meta: PluginMeta, requires: Iterable[str] = (), priority: int = 100
    ) -> None:
        if not meta or not meta.id:
            raise ValueError("PluginMeta invalide: 'id' requis")
        self.meta = meta
        self.requires = tuple(str(r).strip() for r in requires if str(r).strip())
        self.priority = int(priority)

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """Outils requis par ce plugin.

        Structure identique à CompilerEngine.required_tools :
          {"python": ["black", "mypy"], "system": ["gcc"]}
        Les plugins n'ayant pas besoin d'outils supplémentaires
        n'ont pas besoin de surcharger cette propriété.
        """
        return {"python": [], "system": []}

    def on_pre_compile(self, ctx: PreCompileContext) -> None:
        """Méthode à surcharger par le plugin."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Plugin {self.meta.id} v{self.meta.version} prio={self.priority}>"


@dataclass
class ExecutionItem:
    plugin_id: str
    name: str
    success: bool
    duration_ms: float
    error: str = ""


@dataclass
class ExecutionReport:
    """Rapport d'exécution agrégé."""

    items: list[ExecutionItem] = field(default_factory=list)

    def add(self, item: ExecutionItem) -> None:
        self.items.append(item)

    @property
    def ok(self) -> bool:
        return all(i.success for i in self.items)

    def summary(self) -> str:
        total = len(self.items)
        ok = sum(1 for i in self.items if i.success)
        dur = sum(i.duration_ms for i in self.items)
        return f"Plugins: {ok}/{total} ok, temps total {dur:.1f} ms"

    def __iter__(self):
        return iter(self.items)


class _PluginRecord:
    __slots__ = (
        "plugin",
        "active",
        "requires",
        "priority",
        "order",
        "insert_idx",
        "module_path",
        "module_name",
    )

    def __init__(self, plugin: BcPluginBase, insert_idx: int) -> None:
        self.plugin = plugin
        self.active = True
        self.requires = tuple(plugin.requires)
        self.priority = plugin.priority
        self.order = 0
        self.insert_idx = insert_idx
        self.module_path: Optional[Path] = None
        self.module_name: Optional[str] = None


def bc_register(
    cls: Optional[type] = None,
    *,
    manager: Any = None,
    auto_instantiate: bool = True,
    priority: Optional[int] = None,
) -> Any:
    """Décorateur pour enregistrer un plugin BCASL."""

    def decorator_inner(cls_to_decorate: type) -> Any:
        if not isinstance(cls_to_decorate, type):
            raise TypeError("bc_register doit être appliqué à une classe")

        setattr(cls_to_decorate, "__bcasl_plugin__", True)
        meta = getattr(cls_to_decorate, "meta", None)

        if meta is None and cls_to_decorate.__init__ is not BcPluginBase.__init__:
            try:
                temp = cls_to_decorate()
                meta = getattr(temp, "meta", None)
            except Exception:
                pass

        if meta is None:
            raise ValueError(f"Attribut 'meta' requis pour {cls_to_decorate.__name__}")

        def _create_instance() -> BcPluginBase:
            try:
                return cls_to_decorate()
            except TypeError:
                return cls_to_decorate(meta=meta)

        plugin_instance = None
        if auto_instantiate:
            plugin_instance = _create_instance()
            setattr(cls_to_decorate, "_bcasl_instance_", plugin_instance)

        if manager is not None:
            if plugin_instance is None:
                plugin_instance = _create_instance()
            if priority is not None:
                plugin_instance.priority = priority
            manager.add_plugin(plugin_instance)

        return cls_to_decorate

    return decorator_inner(cls) if cls else decorator_inner


def register_plugin(cls: Any) -> Any:
    """Legacy alias for bc_register."""
    setattr(cls, "__bcasl_plugin__", True)
    return cls
