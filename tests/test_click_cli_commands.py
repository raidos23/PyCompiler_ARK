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

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest

click = pytest.importorskip("click")
from click.testing import CliRunner

from cli.click_app import build_cli


def test_help_lists_new_command_groups() -> None:
    runner = CliRunner()
    cli = build_cli("test")

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "gui" in result.output
    assert "engine" in result.output
    assert "workspace" in result.output
    assert "doctor" in result.output
    assert "scaffold" in result.output


def test_workspace_inspect_json(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (tmp_path / "ARK_Main_Config.yml").write_text(
        "build:\n  entrypoint: main.py\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["workspace", "inspect", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["exists"] is True
    assert payload["entrypoint"] == "main.py"
    assert payload["python_file_count"] >= 1


def test_scaffold_engine_json(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")

    result = runner.invoke(
        cli,
        ["scaffold", "engine", "demo_engine", "--root", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["created"] is True
    assert (tmp_path / "ENGINES" / "demo_engine" / "__init__.py").exists()


def test_workspace_entrypoint_strict_exits_non_zero(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")

    result = runner.invoke(
        cli,
        ["workspace", "entrypoint", str(tmp_path), "--json", "--strict"],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["entrypoint"] is None


def test_engine_config_path_json(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")

    result = runner.invoke(
        cli,
        ["engine", "config", "path", "nuitka", "--workspace", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["engine_id"] == "nuitka"
    assert payload["workspace"] == str(tmp_path.resolve())
    assert payload["path"].endswith(".ark/nuitka/config.json")


def test_bcasl_doctor_strict_json(monkeypatch) -> None:
    runner = CliRunner()
    cli = build_cli("test")

    monkeypatch.setattr(
        "cli.click_app.bcasl_doctor_payload",
        lambda workspace=None: {
            "workspace": workspace,
            "checks": [{"name": "plugin_discovery", "ok": False, "message": "boom"}],
        },
    )

    result = runner.invoke(cli, ["bcasl", "doctor", "--json", "--strict"])

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["checks"][0]["ok"] is False


def test_ci_smoke_strict_json(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")

    monkeypatch.setattr(
        "cli.click_app.ci_smoke_payload",
        lambda workspace=None, require_entrypoint=False: {
            "workspace": workspace,
            "require_entrypoint": require_entrypoint,
            "ok": False,
            "failed_count": 1,
            "checks": [
                {"name": "workspace_entrypoint", "ok": False, "message": "missing"}
            ],
        },
    )

    result = runner.invoke(
        cli,
        ["ci", "smoke", str(tmp_path), "--json", "--strict", "--require-entrypoint"],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["require_entrypoint"] is True
    assert payload["checks"][0]["name"] == "workspace_entrypoint"
