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

from EngineLoader.base import CompilerEngine


class DummyProcess:
    def __init__(self, wait_result: bool, exit_code: int) -> None:
        self._wait_result = wait_result
        self._exit_code = exit_code

    def waitForFinished(self, _timeout: int) -> bool:
        return self._wait_result

    def exitCode(self) -> int:
        return self._exit_code


class DummySysDepsManager:
    def __init__(self, events: list[str], process: DummyProcess) -> None:
        self._events = events
        self._process = process

    def install_packages_linux(self, packages: list[str]):
        self._events.append(f"system-install:{','.join(packages)}")
        return self._process

    def open_urls(self, _urls: list[str]) -> None:
        self._events.append("open-urls")


class DummyVenvManager:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def resolve_project_venv(self) -> str:
        return "/tmp/project/.venv"

    def is_tool_installed(self, _venv_path: str, _tool: str) -> bool:
        return False

    def ensure_tools_installed(self, venv_path: str, tools: list[str]) -> None:
        self._events.append(f"python-install:{venv_path}:{','.join(tools)}")


class DummyGui:
    def __init__(self, events: list[str]) -> None:
        self.current_language = "fr"
        self.log: list[str] = []
        self.venv_manager = DummyVenvManager(events)
        self.use_system_python = False


class DummyEngine(CompilerEngine):
    @property
    def required_tools(self) -> dict[str, list[str]]:
        return {"system": ["patchelf"], "python": ["nuitka"]}


def test_ensure_tools_installed_runs_system_before_python(monkeypatch) -> None:
    events: list[str] = []
    process = DummyProcess(wait_result=True, exit_code=0)

    import Core.sys_deps as sys_deps

    monkeypatch.setattr(sys_deps, "check_system_packages", lambda _packages: False)
    monkeypatch.setattr(
        sys_deps,
        "SysDependencyManager",
        lambda gui: DummySysDepsManager(events, process),
    )
    monkeypatch.setattr("platform.system", lambda: "Linux")

    gui = DummyGui(events)
    engine = DummyEngine()

    assert engine.ensure_tools_installed(gui) is True
    assert events == [
        "system-install:patchelf",
        "python-install:/tmp/project/.venv:nuitka",
    ]


def test_ensure_tools_installed_continues_python_after_system_timeout(
    monkeypatch,
) -> None:
    events: list[str] = []
    process = DummyProcess(wait_result=False, exit_code=1)

    import Core.sys_deps as sys_deps

    monkeypatch.setattr(sys_deps, "check_system_packages", lambda _packages: False)
    monkeypatch.setattr(
        sys_deps,
        "SysDependencyManager",
        lambda gui: DummySysDepsManager(events, process),
    )
    monkeypatch.setattr("platform.system", lambda: "Linux")

    gui = DummyGui(events)
    engine = DummyEngine()

    assert engine.ensure_tools_installed(gui) is False
    assert events == [
        "system-install:patchelf",
        "python-install:/tmp/project/.venv:nuitka",
    ]
    assert any("Timeout" in msg or "timeout" in msg for msg in gui.log)
