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

"""Smoke tests for compile entrypoint selection."""

from __future__ import annotations

from Core.ArkConfigManager import set_entrypoint
import Core.Compiler as compiler_module


class DummyMainProcess:
    def __init__(self) -> None:
        self.workspace = None
        self.engine = None

    def set_workspace(self, value: str) -> None:
        self.workspace = value

    def set_engine(self, value: str) -> None:
        self.engine = value


class DummyEngine:
    name = "Dummy"


class DummyGUI:
    def __init__(self) -> None:
        self.python_files: list[str] = []
        self.selected_files: list[str] = []
        self.workspace_dir: str | None = None
        self.compiler_tabs = None
        self._logs: list[tuple[str, str]] = []
        self._controls_enabled = True

    def log_i18n(self, fr: str, en: str) -> None:
        self._logs.append((fr, en))

    def set_controls_enabled(self, enabled: bool) -> None:
        self._controls_enabled = enabled


def test_compile_all_no_files(tmp_path) -> None:
    gui = DummyGUI()
    gui.workspace_dir = str(tmp_path)

    compiler_module.compile_all(gui)

    assert any("Aucun fichier" in fr for fr, _ in gui._logs)


def test_compile_all_no_workspace(tmp_path) -> None:
    gui = DummyGUI()
    gui.python_files = [str(tmp_path / "main.py")]

    compiler_module.compile_all(gui)

    assert any("Aucun workspace" in fr for fr, _ in gui._logs)


def test_compile_all_uses_entrypoint(tmp_path, monkeypatch) -> None:
    entry = tmp_path / "main.py"
    other = tmp_path / "other.py"
    entry.write_text("print('x')", encoding="utf-8")
    other.write_text("print('y')", encoding="utf-8")

    assert set_entrypoint(str(tmp_path), "main.py") is True

    gui = DummyGUI()
    gui.workspace_dir = str(tmp_path)
    gui.python_files = [str(other)]
    gui.selected_files = [str(other)]

    captured: dict[str, list[str]] = {}

    def fake_start(_self, _engine, files):
        captured["files"] = files

    monkeypatch.setattr(compiler_module, "_start_compilation_queue", fake_start)
    monkeypatch.setattr(compiler_module, "create", lambda _eid: DummyEngine())
    monkeypatch.setattr(compiler_module, "_get_main_process", lambda: DummyMainProcess())

    compiler_module.compile_all(gui)

    assert captured.get("files") == [str(entry)]
