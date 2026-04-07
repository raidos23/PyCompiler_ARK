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
import sys

os.environ.setdefault("ARK_ENGINES_AUTO_DISCOVER", "0")

import EngineLoader.registry as engine_registry
import engine_sdk
from EngineLoader.Loader import EngineLoader as engine_loader
from EngineLoader.base import CompilerEngine


def _snapshot_registry_state():
    return (
        dict(engine_registry._REGISTRY),
        list(engine_registry._ORDER),
        dict(engine_registry._TAB_INDEX),
        dict(engine_registry._INSTANCES),
    )


def _restore_registry_state(snapshot) -> None:
    reg, order, tab_index, instances = snapshot
    engine_registry._REGISTRY.clear()
    engine_registry._REGISTRY.update(reg)
    engine_registry._ORDER[:] = order
    engine_registry._TAB_INDEX.clear()
    engine_registry._TAB_INDEX.update(tab_index)
    engine_registry._INSTANCES.clear()
    engine_registry._INSTANCES.update(instances)


def test_discovery_registers_namespaced_engine_classes(tmp_path, monkeypatch) -> None:
    snapshot = _snapshot_registry_state()
    engines_dir = tmp_path / "ENGINES"
    demo_pkg = engines_dir / "demo"
    demo_pkg.mkdir(parents=True)

    (demo_pkg / "__init__.py").write_text(
        "\n".join(
            [
                "from EngineLoader.base import CompilerEngine",
                "",
                "class DemoEngine(CompilerEngine):",
                "    id = 'demo_dynamic'",
                "    name = 'Demo Dynamic'",
            ]
        ),
        encoding="utf-8",
    )
    (demo_pkg / "extra.py").write_text(
        "\n".join(
            [
                "from EngineLoader.base import CompilerEngine",
                "",
                "class ExtraEngine(CompilerEngine):",
                "    id = 'demo_extra'",
                "    name = 'Demo Extra'",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.syspath_prepend(str(tmp_path))
    for mod_name in ("ENGINES.demo", "ENGINES.demo.extra"):
        sys.modules.pop(mod_name, None)

    try:
        engine_registry.unload_all()
        engine_loader._discover_external_plugins(
            str(engines_dir), namespace_package="ENGINES"
        )

        assert engine_registry.get_engine("demo_dynamic") is not None
        assert engine_registry.get_engine("demo_extra") is not None
        assert "ENGINES.demo" in sys.modules
        assert "ENGINES.demo.extra" in sys.modules
        assert engine_sdk.registry is engine_registry
    finally:
        _restore_registry_state(snapshot)


def test_sync_engine_sdk_registry_uses_active_engine_loader_registry() -> None:
    previous = engine_sdk.registry
    try:
        engine_sdk.registry = None
        synced = engine_loader._sync_engine_sdk_registry()
        assert engine_sdk.registry is engine_registry
        assert synced is None
    finally:
        engine_sdk.registry = previous


def test_bind_tabs_logs_explicit_failure_for_broken_engine() -> None:
    snapshot = _snapshot_registry_state()

    class BrokenTabEngine(CompilerEngine):
        id = "broken_tab_engine"

        def create_tab(self, gui):
            raise RuntimeError("boom")

    class DummyTabs:
        pass

    class DummyGui:
        def __init__(self) -> None:
            self.current_language = "fr"
            self.compiler_tabs = DummyTabs()
            self.tab_hello = None
            self.log: list[str] = []

    try:
        engine_registry.unload_all()
        engine_registry.engine_register(BrokenTabEngine)

        gui = DummyGui()
        engine_registry.bind_tabs(gui)

        assert any("broken_tab_engine" in msg for msg in gui.log)
        assert any("onglet moteur" in msg.lower() for msg in gui.log)
    finally:
        _restore_registry_state(snapshot)
