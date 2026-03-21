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


def test_create_venv_prefers_manager_mapping(test_workspace: Path, monkeypatch) -> None:
    # Simulate a Poetry-managed project
    pyproject = test_workspace / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'demo'\n", encoding="utf-8")

    parent = DummyParent()
    parent.workspace_dir = str(test_workspace)
    mgr = VenvManager(parent)

    called: dict[str, str] = {}

    def fake_create(workspace_dir: str, venv_path: str | None = None) -> None:
        called["workspace"] = workspace_dir
        called["venv_path"] = venv_path or ""

    monkeypatch.setattr(mgr, "create_venv_with_manager", fake_create)
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: True)

    mgr.create_venv_if_needed(str(test_workspace))

    assert called.get("workspace") == str(test_workspace)
    assert called.get("venv_path", "").endswith(os.path.join("", ".venv"))


def test_resolve_existing_venv_prefers_manager(
    monkeypatch, test_workspace: Path
) -> None:
    parent = DummyParent()
    parent.workspace_dir = str(test_workspace)
    mgr = VenvManager(parent)

    monkeypatch.setattr(
        mgr, "_detect_manager_existing_venv", lambda base: "/tmp/manager-venv"
    )
    called = {"select": False}

    def fake_select(_base: str) -> str | None:
        called["select"] = True
        return "/tmp/local-venv"

    monkeypatch.setattr(mgr, "select_best_venv", fake_select)

    result = mgr.resolve_existing_venv(str(test_workspace))

    assert result == "/tmp/manager-venv"
    assert called["select"] is False


def test_install_requirements_prefers_manager(
    monkeypatch, test_workspace: Path
) -> None:
    parent = DummyParent()
    mgr = VenvManager(parent)

    called: dict[str, str] = {}

    def fake_install(workspace_dir: str, venv_path: str | None = None) -> None:
        called["workspace"] = workspace_dir

    monkeypatch.setattr(mgr, "install_dependencies_with_manager", fake_install)
    monkeypatch.setattr(mgr, "_detect_environment_manager", lambda path: "poetry")
    monkeypatch.setattr(
        mgr,
        "_get_requirements_file",
        lambda _path: (_ for _ in ()).throw(AssertionError("should not call")),
    )

    mgr.install_requirements_if_needed(str(test_workspace))

    assert called.get("workspace") == str(test_workspace)


def test_detect_manager_existing_venv_poetry(test_workspace: Path, monkeypatch) -> None:
    pyproject = test_workspace / "pyproject.toml"
    pyproject.write_text("[tool.poetry]\nname = 'demo'\n", encoding="utf-8")
    venv_path = _make_fake_venv(test_workspace / "poetry-venv")

    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: True)
    monkeypatch.setattr(
        mgr, "_run_cmd_capture", lambda cmd, cwd, timeout=5: str(venv_path)
    )

    result = mgr._detect_manager_existing_venv(str(test_workspace))
    assert result == str(venv_path)


def test_detect_manager_existing_venv_pipenv(test_workspace: Path, monkeypatch) -> None:
    pipfile = test_workspace / "Pipfile"
    pipfile.write_text("[packages]\n", encoding="utf-8")
    venv_path = _make_fake_venv(test_workspace / "pipenv-venv")

    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: True)
    monkeypatch.setattr(
        mgr, "_run_cmd_capture", lambda cmd, cwd, timeout=5: str(venv_path)
    )

    result = mgr._detect_manager_existing_venv(str(test_workspace))
    assert result == str(venv_path)


def test_detect_manager_existing_venv_pdm(test_workspace: Path, monkeypatch) -> None:
    pyproject = test_workspace / "pyproject.toml"
    pyproject.write_text("[tool.pdm]\n", encoding="utf-8")
    venv_path = _make_fake_venv(test_workspace / "pdm-venv")

    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: True)
    monkeypatch.setattr(
        mgr, "_run_cmd_capture", lambda cmd, cwd, timeout=5: str(venv_path)
    )

    result = mgr._detect_manager_existing_venv(str(test_workspace))
    assert result == str(venv_path)


def test_detect_manager_existing_venv_conda_prefix(
    test_workspace: Path, monkeypatch
) -> None:
    venv_path = _make_fake_venv(test_workspace / "conda-env")
    env_file = test_workspace / "environment.yml"
    env_file.write_text(f"name: demo\nprefix: {venv_path}\n", encoding="utf-8")

    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: True)

    result = mgr._detect_manager_existing_venv(str(test_workspace))
    assert result == str(venv_path)


def test_detect_manager_existing_venv_conda_name(
    test_workspace: Path, monkeypatch
) -> None:
    venv_path = _make_fake_venv(test_workspace / "conda-name-env")
    env_file = test_workspace / "environment.yml"
    env_name = venv_path.name
    env_file.write_text(f"name: {env_name}\n", encoding="utf-8")

    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: True)

    class _FakeResult:
        returncode = 0
        stdout = f'{{"envs": ["{venv_path}"]}}'
        stderr = ""

    monkeypatch.setattr(
        "Core.Venv_Manager.Manager.subprocess.run", lambda *a, **k: _FakeResult()
    )

    result = mgr._detect_manager_existing_venv(str(test_workspace))
    assert result == str(venv_path)


def test_create_venv_with_manager_fallback(monkeypatch, test_workspace: Path) -> None:
    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_detect_environment_manager", lambda path: "poetry")
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: False)
    called: dict[str, bool] = {}

    def fake_create(path: str, prefer_manager: bool = True):
        called["prefer_manager"] = prefer_manager

    monkeypatch.setattr(mgr, "create_venv_if_needed", fake_create)

    mgr.create_venv_with_manager(str(test_workspace))
    assert called.get("prefer_manager") is False


def test_install_dependencies_with_manager_fallback(
    monkeypatch, test_workspace: Path
) -> None:
    mgr = VenvManager(DummyParent())
    monkeypatch.setattr(mgr, "_detect_environment_manager", lambda path: "poetry")
    monkeypatch.setattr(mgr, "_is_tool_available", lambda tool: False)
    called: dict[str, bool] = {}

    def fake_install(path: str, force_pip: bool = False):
        called["force_pip"] = force_pip
        called["path"] = path

    monkeypatch.setattr(mgr, "install_requirements_if_needed", fake_install)

    mgr.install_dependencies_with_manager(str(test_workspace))
    assert called.get("force_pip") is True
    assert called.get("path") == str(test_workspace)


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
