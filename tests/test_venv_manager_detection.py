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

"""Tests for VenvManager manager detection and preference handling."""

from __future__ import annotations

import os
import platform
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from Core.Venv_Manager.Manager import VenvManager


class DummyParent:
    def __init__(self):
        self.log = []
        self.workspace_dir = None
        self.venv_path_manuel = None
        self.use_system_python = False

    def tr(self, fr: str, en: str) -> str:
        return en


def _make_fake_venv(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    cfg = path / "pyvenv.cfg"
    cfg.write_text("include-system-site-packages = false\n", encoding="utf-8")
    bindir = "Scripts" if platform.system() == "Windows" else "bin"
    bin_path = path / bindir
    bin_path.mkdir(parents=True, exist_ok=True)
    py_name = "python.exe" if platform.system() == "Windows" else "python"
    (bin_path / py_name).write_text("", encoding="utf-8")
    return path


def test_resolve_existing_venv_prefers_local(monkeypatch, test_workspace: Path) -> None:
    parent = DummyParent()
    parent.workspace_dir = str(test_workspace)
    mgr = VenvManager(parent)

    called = {"select": False}

    def fake_select(_base: str) -> str | None:
        called["select"] = True
        return "/tmp/local-venv"

    monkeypatch.setattr(mgr, "select_best_venv", fake_select)

    result = mgr.resolve_existing_venv(str(test_workspace))

    assert result == "/tmp/local-venv"
    assert called["select"] is True


def test_pip_break_system_args_enabled_only_on_linux_system_python(monkeypatch) -> None:
    parent = DummyParent()
    parent.use_system_python = True
    mgr = VenvManager(parent)

    monkeypatch.setattr("platform.system", lambda: "Linux")
    assert mgr._pip_break_system_args() == ["--break-system-packages"]

    monkeypatch.setattr("platform.system", lambda: "Windows")
    assert mgr._pip_break_system_args() == []

    parent.use_system_python = False
    monkeypatch.setattr("platform.system", lambda: "Linux")
    assert mgr._pip_break_system_args() == []


def test_system_python_install_uses_break_system_packages_on_linux(
    monkeypatch, test_workspace: Path
) -> None:
    parent = DummyParent()
    parent.workspace_dir = str(test_workspace)
    parent.use_system_python = True
    mgr = VenvManager(parent)
    mgr._venv_check_use_python = True
    mgr._venv_check_pip_exe = "python"
    mgr._venv_check_path = str(test_workspace)
    mgr._venv_check_pkgs = ["requests"]
    mgr._venv_check_index = 0

    class _DummySignal:
        def connect(self, _cb) -> None:
            return None

    captured: dict[str, object] = {}

    class _DummyProgress:
        class _DummyBar:
            def setRange(self, *_args) -> None:
                return None

        def __init__(self) -> None:
            self.progress = self._DummyBar()

        def set_message(self, _msg: str) -> None:
            return None

    class _DummyProcess:
        def __init__(self, _parent) -> None:
            self.readyReadStandardOutput = _DummySignal()
            self.readyReadStandardError = _DummySignal()
            self.finished = _DummySignal()

        def setProgram(self, program: str) -> None:
            captured["program"] = program

        def setArguments(self, args: list[str]) -> None:
            captured["args"] = list(args)

        def setWorkingDirectory(self, cwd: str) -> None:
            captured["cwd"] = cwd

        def start(self) -> None:
            captured["started"] = True

    mgr.venv_check_progress = _DummyProgress()
    monkeypatch.setattr("Core.Venv_Manager.Manager.QProcess", _DummyProcess)
    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(mgr, "_arm_process_timeout", lambda *args, **kwargs: None)

    mgr._on_venv_pkg_checked(process=None, code=1, status=None, pkg="requests")

    assert captured["program"] == "python"
    assert captured["cwd"] == str(test_workspace)
    assert captured["started"] is True
    assert captured["args"] == [
        "-m",
        "pip",
        "install",
        "--break-system-packages",
        "requests",
    ]
