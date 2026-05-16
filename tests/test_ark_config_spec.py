# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path

from Core.Configs import (
    load_ark_config,
    new_workspace_config,
    validate_ark_config,
    write_ark_config,
)
from Core.Locking import build_context_from_ark_config


def test_new_workspace_config_uses_spec_shape() -> None:
    config = new_workspace_config(workspace_name="demo", entry="main.py")

    assert config["project"]["name"] == "demo"
    assert config["project"]["entry"] == "main.py"
    assert config["build"]["engine"] == "pyinstaller"
    assert config["workspace"]["exclude"]
    assert "*.spec" in config["workspace"]["exclude"]


def test_load_validate_and_convert_workspace_config(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")

    config = new_workspace_config(workspace_name="demo", entry="main.py", icon=None)
    write_ark_config(tmp_path, config)

    loaded = load_ark_config(tmp_path)
    result = validate_ark_config(tmp_path, loaded)

    assert result.ok is True
    assert result.config["project"]["entry"] == "main.py"

    context = build_context_from_ark_config(result.config)
    assert context.project_name == "demo"
    assert context.entry_point == "main.py"
    assert context.output_dir == "dist/"
