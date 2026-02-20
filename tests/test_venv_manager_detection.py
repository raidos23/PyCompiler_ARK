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
