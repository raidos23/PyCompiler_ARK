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
EngineConfigManager

Persists engine UI configuration per workspace at:
    <workspace>/.ark/<engine_id>/config.json
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

ENGINE_CONFIG_DIRNAME = ".ark"
ENGINE_CONFIG_BASENAME = "config.json"
ENGINE_CONFIG_VERSION = 1


def _safe_engine_id(engine_id: str) -> str:
    try:
        raw = str(engine_id or "").strip()
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_", raw)
        return safe or "engine"
    except Exception:
        return "engine"


def _engine_config_dir(workspace_dir: str, engine_id: str) -> str:
    return os.path.join(workspace_dir, ENGINE_CONFIG_DIRNAME, _safe_engine_id(engine_id))


def _engine_config_path(workspace_dir: str, engine_id: str) -> str:
    return os.path.join(_engine_config_dir(workspace_dir, engine_id), ENGINE_CONFIG_BASENAME)


def _atomic_write_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    os.replace(tmp, path)


def load_engine_config(workspace_dir: str, engine_id: str) -> dict[str, Any]:
    if not workspace_dir or not engine_id:
        return {}
    path = _engine_config_path(workspace_dir, engine_id)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_engine_config(
    workspace_dir: str,
    engine_id: str,
    options: Optional[dict],
    engine_version: Optional[str] = None,
) -> bool:
    if not workspace_dir or not engine_id:
        return False
    try:
        cfg_dir = _engine_config_dir(workspace_dir, engine_id)
        os.makedirs(cfg_dir, exist_ok=True)
        payload = {
            "meta": {
                "engine_id": str(engine_id),
                "version": ENGINE_CONFIG_VERSION,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "options": options if isinstance(options, dict) else {},
        }
        if engine_version:
            payload["meta"]["engine_version"] = str(engine_version)
        _atomic_write_json(_engine_config_path(workspace_dir, engine_id), payload)
        return True
    except Exception:
        return False


def apply_engine_config(gui, engine, data: dict) -> None:
    if not isinstance(data, dict):
        return
    opts = data.get("options") if isinstance(data, dict) else None
    if not isinstance(opts, dict):
        opts = data if isinstance(data, dict) else {}
    try:
        fn = getattr(engine, "set_config", None)
        if callable(fn):
            fn(gui, opts)
    except Exception:
        pass


def apply_engine_configs_for_workspace(gui, workspace_dir: str) -> None:
    if not workspace_dir:
        return
    try:
        import EngineLoader as engines_loader

        for eid in engines_loader.registry.available_engines():
            try:
                engine = engines_loader.registry.get_instance(eid)
                if not engine:
                    continue
                data = load_engine_config(workspace_dir, eid)
                if data:
                    apply_engine_config(gui, engine, data)
            except Exception:
                continue
    except Exception:
        pass

    try:
        if hasattr(gui, "update_command_preview"):
            gui.update_command_preview()
    except Exception:
        pass


def save_engine_config_for_gui(gui, engine_id: str) -> bool:
    try:
        workspace_dir = getattr(gui, "workspace_dir", None)
        if not workspace_dir or not engine_id:
            return False
        import EngineLoader as engines_loader

        engine = engines_loader.registry.get_instance(engine_id)
        if not engine:
            return False
        options = {}
        try:
            fn = getattr(engine, "get_config", None)
            if callable(fn):
                options = fn(gui) or {}
        except Exception:
            options = {}
        return save_engine_config(
            workspace_dir,
            engine_id,
            options,
            getattr(engine, "version", None),
        )
    except Exception:
        return False
