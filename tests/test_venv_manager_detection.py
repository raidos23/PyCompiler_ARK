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


def test_resolve_existing_venv_prefers_manager(monkeypatch, test_workspace: Path) -> None:
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


def test_install_requirements_prefers_manager(monkeypatch, test_workspace: Path) -> None:
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
