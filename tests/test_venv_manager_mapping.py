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

"""Tests for VenvManager manager mapping loading and validation."""

from __future__ import annotations

import io
import os
import builtins

import pytest

pytest.importorskip("PySide6")

from Core.Venv_Manager.Manager import VenvManager


class DummyParent:
    def __init__(self):
        self.log = []

    def _safe_log(self, text: str) -> None:
        self.log.append(text)


def test_validate_manager_mapping_rejects_unknown_action() -> None:
    mgr = VenvManager(DummyParent())
    data = {"managers": {"pip": {"installx": ["pip", "install"]}}}
    cleaned, errors = mgr._validate_manager_mapping(
        data, allowed_actions={"pip": {"install"}}
    )
    assert cleaned == {}
    assert any("action non autorisee" in e.lower() for e in errors)


def test_load_manager_mapping_invalid_uses_default(monkeypatch) -> None:
    original_isfile = os.path.isfile
    original_open = builtins.open

    def fake_isfile(path: str) -> bool:
        if path.endswith("ManagerMapping.yml"):
            return True
        return original_isfile(path)

    def fake_open(path, *args, **kwargs):
        if str(path).endswith("ManagerMapping.yml"):
            return io.StringIO("managers: []")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(os.path, "isfile", fake_isfile)
    monkeypatch.setattr(builtins, "open", fake_open)

    mgr = VenvManager(DummyParent())
    default = mgr._default_manager_commands()
    assert mgr._manager_commands == default


def test_load_manager_mapping_missing_uses_default(monkeypatch) -> None:
    original_isfile = os.path.isfile

    def fake_isfile(path: str) -> bool:
        if path.endswith("ManagerMapping.yml"):
            return False
        return original_isfile(path)

    monkeypatch.setattr(os.path, "isfile", fake_isfile)

    mgr = VenvManager(DummyParent())
    default = mgr._default_manager_commands()
    assert mgr._manager_commands == default
