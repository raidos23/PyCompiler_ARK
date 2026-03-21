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

os.environ.setdefault("ARK_ENGINES_AUTO_DISCOVER", "0")

import EngineLoader.registry as engine_registry
from EngineLoader.base import CompilerEngine


def _snapshot_registry_state():
    return (
        dict(engine_registry._REGISTRY),
        list(engine_registry._ORDER),
        dict(engine_registry._TAB_INDEX),
        dict(engine_registry._INSTANCES),
        dict(engine_registry._ENGINE_TR),
        dict(engine_registry._GLOBAL_TR),
        engine_registry._GLOBAL_LANG,
    )


def _restore_registry_state(snapshot) -> None:
    reg, order, tab_index, instances, engine_tr, global_tr, global_lang = snapshot
    engine_registry._REGISTRY.clear()
    engine_registry._REGISTRY.update(reg)
    engine_registry._ORDER[:] = order
    engine_registry._TAB_INDEX.clear()
    engine_registry._TAB_INDEX.update(tab_index)
    engine_registry._INSTANCES.clear()
    engine_registry._INSTANCES.update(instances)
    engine_registry._ENGINE_TR.clear()
    engine_registry._ENGINE_TR.update(engine_tr)
    engine_registry._GLOBAL_TR.clear()
    engine_registry._GLOBAL_TR.update(global_tr)
    engine_registry._GLOBAL_LANG = global_lang


def test_engine_translate_uses_engine_cache_and_global_fallback(monkeypatch) -> None:
    snapshot = _snapshot_registry_state()

    class DummyEngine(CompilerEngine):
        id = "demo_engine"

        def __init__(self) -> None:
            self.events: list[str] = []

        def apply_i18n(self, gui, tr: dict) -> None:
            self.events.append(self.engine_translate("tab_title", "Default title"))
            self.events.append(self.engine_translate("shared_label", "Shared fallback"))

    DummyEngine.__module__ = "ENGINES.demo"

    class DummyGui:
        language_pref = "fr"

    try:
        engine_registry.unload_all()
        engine_registry.engine_register(DummyEngine)
        inst = DummyEngine()
        engine_registry._INSTANCES[DummyEngine.id] = inst

        monkeypatch.setattr(
            engine_registry,
            "load_engine_language_file",
            lambda engine_package, code: {
                "tab_title": f"{engine_package}:{code}"
            },
        )

        engine_registry.apply_translations(
            DummyGui(),
            {"_meta": {"code": "fr"}, "shared_label": "Global shared label"},
        )

        assert inst.events == [
            "ENGINES.demo:fr",
            "Global shared label",
        ]
        assert (
            engine_registry.engine_translate("demo_engine", "tab_title", "missing")
            == "ENGINES.demo:fr"
        )
        assert (
            engine_registry.engine_translate("demo_engine", "shared_label", "missing")
            == "Global shared label"
        )
    finally:
        _restore_registry_state(snapshot)
