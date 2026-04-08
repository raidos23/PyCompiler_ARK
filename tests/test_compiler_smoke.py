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

import pytest

pytest.importorskip("PySide6")

from Core.ArkConfigManager import set_entrypoint
import Core.Compiler as compiler_module
from Core.Compiler.compiler import CompilationThread


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
        self.log: list[str] = []
        self._controls_enabled = True
        self.current_language = "fr"

    def log_i18n(self, fr: str, en: str) -> None:
        self.log.append(fr)

    def set_controls_enabled(self, enabled: bool) -> None:
        self._controls_enabled = enabled


def test_compile_all_no_files(tmp_path) -> None:
    gui = DummyGUI()
    gui.workspace_dir = str(tmp_path)

    compiler_module.compile_all(gui)

    assert any("Aucun fichier" in msg for msg in gui.log)


def test_compile_all_no_workspace(tmp_path) -> None:
    gui = DummyGUI()
    gui.python_files = [str(tmp_path / "main.py")]

    compiler_module.compile_all(gui)

    assert any("Aucun workspace" in msg for msg in gui.log)


def test_compile_all_uses_entrypoint(test_workspace, monkeypatch) -> None:
    entry = test_workspace / "main.py"
    other = test_workspace / "other.py"
    other.write_text("print('y')", encoding="utf-8")

    assert set_entrypoint(str(test_workspace), "main.py") is True

    gui = DummyGUI()
    gui.workspace_dir = str(test_workspace)
    gui.python_files = [str(other)]
    gui.selected_files = [str(other)]

    captured: dict[str, list[str]] = {}

    def fake_start(_self, _engine, files):
        captured["files"] = files

    monkeypatch.setattr(compiler_module, "_start_compilation_queue", fake_start)
    monkeypatch.setattr(compiler_module, "create", lambda _eid: DummyEngine())
    monkeypatch.setattr(
        compiler_module, "_get_main_process", lambda: DummyMainProcess()
    )
    monkeypatch.setattr(
        compiler_module,
        "_run_bcasl_before_compile",
        lambda _self, cb: cb({"status": "disabled"}),
    )

    compiler_module.compile_all(gui)

    assert captured.get("files") == [str(entry)]


def test_compile_all_stops_when_bcasl_report_is_failure(test_workspace, monkeypatch) -> None:
    entry = test_workspace / "main.py"
    assert set_entrypoint(str(test_workspace), "main.py") is True

    gui = DummyGUI()
    gui.workspace_dir = str(test_workspace)
    gui.python_files = [str(entry)]
    gui.selected_files = [str(entry)]

    captured = {"started": False}

    def fake_start(_self, _engine, _files):
        captured["started"] = True

    monkeypatch.setattr(compiler_module, "_start_compilation_queue", fake_start)
    monkeypatch.setattr(compiler_module, "create", lambda _eid: DummyEngine())
    monkeypatch.setattr(
        compiler_module, "_get_main_process", lambda: DummyMainProcess()
    )
    monkeypatch.setattr(
        compiler_module,
        "_run_bcasl_before_compile",
        lambda _self, cb: cb({"ok": False, "error": "bcasl failed"}),
    )

    compiler_module.compile_all(gui)

    assert captured["started"] is False
    assert gui._controls_enabled is True


def test_compilation_thread_warns_when_live_streams_are_unavailable() -> None:
    thread = CompilationThread(program="python", args=["-V"])
    warnings: list[str] = []
    outputs: list[str] = []

    thread.error_ready.connect(warnings.append)
    thread.output_ready.connect(outputs.append)

    class DummyProcess:
        stdout = None
        stderr = None

        def poll(self):
            return None

    thread.process = DummyProcess()

    thread._read_output()
    thread._read_remaining()

    assert thread._live_output_disabled is True
    assert any("stdout/stderr unavailable" in msg for msg in warnings)
    assert outputs == []
