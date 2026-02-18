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

"""
Tests for Core.ArkConfigManager - ARK_Main_Config.yml handling
"""

import copy
from pathlib import Path

import yaml

from Core.ArkConfigManager import (
    DEFAULT_CONFIG,
    get_entrypoint,
    load_ark_config,
    save_ark_config,
    set_entrypoint,
)


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_load_defaults_when_missing(tmp_path: Path) -> None:
    """Load should return defaults when config is missing."""
    cfg = load_ark_config(str(tmp_path))
    assert isinstance(cfg, dict)
    assert "build" in cfg
    assert cfg["build"].get("entrypoint") is None


def test_set_entrypoint_writes_file(tmp_path: Path) -> None:
    """Setting entrypoint should persist it to ARK_Main_Config.yml."""
    ok = set_entrypoint(str(tmp_path), "main.py")
    assert ok is True
    cfg = load_ark_config(str(tmp_path))
    assert get_entrypoint(cfg) == "main.py"


def test_set_entrypoint_trims_value(tmp_path: Path) -> None:
    """Entrypoint should be trimmed when saved and reloaded."""
    ok = set_entrypoint(str(tmp_path), "  app.py  ")
    assert ok is True
    cfg = load_ark_config(str(tmp_path))
    assert get_entrypoint(cfg) == "app.py"


def test_clear_entrypoint(tmp_path: Path) -> None:
    """Clearing entrypoint should store null in config."""
    assert set_entrypoint(str(tmp_path), "main.py") is True
    assert set_entrypoint(str(tmp_path), None) is True
    cfg = load_ark_config(str(tmp_path))
    assert get_entrypoint(cfg) is None


def test_save_ark_config_normalizes_build(tmp_path: Path) -> None:
    """Loading should normalize build section even if malformed."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["build"] = "bad"
    assert save_ark_config(str(tmp_path), cfg) is True
    loaded = load_ark_config(str(tmp_path))
    assert isinstance(loaded.get("build"), dict)
    assert loaded["build"].get("entrypoint") is None


def test_load_config_strips_entrypoint(tmp_path: Path) -> None:
    """load_ark_config should strip entrypoint from raw YAML content."""
    raw = {
        "build": {
            "entrypoint": "  src/main.py  ",
        }
    }
    cfg_path = Path(tmp_path) / "ARK_Main_Config.yml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(raw, f, sort_keys=False, allow_unicode=True)

    loaded = load_ark_config(str(tmp_path))
    assert loaded["build"]["entrypoint"] == "src/main.py"
