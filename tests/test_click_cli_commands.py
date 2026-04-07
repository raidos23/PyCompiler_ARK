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


def test_workspace_apply_json(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")

    result = runner.invoke(cli, ["workspace", "apply", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["workspace"] == str(tmp_path.resolve())
    assert payload["inspect"]["python_file_count"] >= 1


def test_workspace_apply_strict_fails_without_entrypoint(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")

    result = runner.invoke(
        cli,
        ["workspace", "apply", str(tmp_path), "--no-auto-config", "--strict", "--json"],
    )

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["require_entrypoint"] is True


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


def test_check_strict_json(monkeypatch, tmp_path) -> None:
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

    result = runner.invoke(cli, ["check", str(tmp_path), "--json", "--strict", "--require-entrypoint"])

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["require_entrypoint"] is True
    assert payload["checks"][0]["name"] == "workspace_entrypoint"


def test_check_command_is_strict_by_default(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    calls: list[dict[str, object]] = []

    def _fake_payload(workspace=None, require_entrypoint=False):
        calls.append(
            {
                "workspace": workspace,
                "require_entrypoint": require_entrypoint,
            }
        )
        return {
            "workspace": workspace,
            "require_entrypoint": require_entrypoint,
            "ok": False,
            "failed_count": 1,
            "checks": [{"name": "workspace_entrypoint", "ok": False, "message": "missing"}],
        }

    monkeypatch.setattr("cli.click_app.ci_smoke_payload", _fake_payload)

    result = runner.invoke(cli, ["check", str(tmp_path), "--json"])

    assert result.exit_code == 3
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["require_entrypoint"] is True
    assert calls and calls[0]["require_entrypoint"] is True


def test_check_fail_only_filters_ok_checks(monkeypatch) -> None:
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
                {"name": "engine_inventory", "ok": True, "message": "2 engine(s) detected"},
                {"name": "workspace_entrypoint", "ok": False, "message": "missing"},
            ],
        },
    )

    result = runner.invoke(cli, ["check", "--fail-only", "--no-strict"])

    assert result.exit_code == 0
    assert "workspace_entrypoint" in result.output
    assert "engine_inventory" not in result.output


def test_init_command_creates_workspace_and_config(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    workspace = tmp_path / "new_ws"

    result = runner.invoke(cli, ["init", str(workspace), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["created_workspace"] is True
    assert payload["created_config"] is True
    assert payload["created_bcasl_config"] is True
    assert payload["created_workspace_pref"] is True
    assert (workspace / "ARK_Main_Config.yml").exists()
    assert (workspace / "bcasl.yml").exists()
    assert (workspace / ".ark" / "pref.json").exists()


def test_config_auto_detects_entrypoint_and_updates_config(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    (tmp_path / "main.py").write_text("if __name__ == '__main__':\n    print('ok')\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("click\n", encoding="utf-8")

    result = runner.invoke(cli, ["config-auto", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["entrypoint"] == "main.py"
    assert "requirements.txt" in payload["requirements_files_found"]


def test_cfg_auto_alias_behaves_like_config_auto(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")

    result = runner.invoke(cli, ["cfg-auto", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["entrypoint"] == "main.py"


def test_ws_init_alias_creates_workspace(tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    workspace = tmp_path / "via_ws_alias"

    result = runner.invoke(cli, ["ws", "init", str(workspace), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert (workspace / "ARK_Main_Config.yml").exists()
    assert (workspace / "bcasl.yml").exists()
    assert (workspace / ".ark" / "pref.json").exists()


def test_init_with_venv_option_is_forwarded(monkeypatch, tmp_path) -> None:
    runner = CliRunner()
    cli = build_cli("test")
    calls: list[dict[str, object]] = []

    def _fake_init(workspace=None, progress_cb=None, with_venv=False):
        calls.append({"workspace": workspace, "with_venv": with_venv})
        return {
            "ok": True,
            "workspace": workspace,
            "config_path": str(tmp_path / "ARK_Main_Config.yml"),
            "bcasl_path": str(tmp_path / "bcasl.yml"),
            "workspace_pref_path": str(tmp_path / ".ark" / "pref.json"),
            "created_workspace": False,
            "created_config": False,
            "created_bcasl_config": False,
            "created_workspace_pref": False,
            "with_venv": bool(with_venv),
            "created_venv": bool(with_venv),
            "venv_path": str(tmp_path / ".venv") if with_venv else None,
            "steps": [],
        }

    monkeypatch.setattr("cli.click_app.workspace_init_payload", _fake_init)

    result = runner.invoke(cli, ["init", str(tmp_path), "--with-venv", "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["with_venv"] is True
    assert calls and calls[0]["with_venv"] is True
