# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

from unittest.mock import patch

from pycompiler_ark.Core.Configs import load_ark_config
from pycompiler_ark.Core.deps_analyser import collect_internal_modules
from pycompiler_ark.Ui.Cli.helpers import init_workspace


def _make_internal_workspace(root):
    workspace = root / "workspace"
    package_dir = workspace / "src" / "pkg"
    package_dir.mkdir(parents=True)
    (package_dir / "__init__.py").write_text("", encoding="utf-8")
    (package_dir / "internal_mod.py").write_text(
        "VALUE = 1\n", encoding="utf-8"
    )
    (package_dir / "main.py").write_text(
        "from .internal_mod import VALUE\n", encoding="utf-8"
    )
    return workspace


def test_collect_internal_modules_uses_classification(tmp_path):
    workspace = _make_internal_workspace(tmp_path)

    def _classify(module_name, _workspace_dir):
        mapping = {
            "pkg": "internal",
            "requests": "third_party",
            "os": "stdlib",
        }
        return mapping.get(module_name, "unknown")

    with (
        patch(
            "pycompiler_ark.Core.deps_analyser.analyser._extract_imported_modules_from_file",
            return_value={"pkg", "requests", "os"},
        ),
        patch(
            "pycompiler_ark.Core.deps_analyser.analyser._classify_module_origin",
            side_effect=_classify,
        ),
    ):
        detected = collect_internal_modules(str(workspace))

    assert detected == {"pkg"}


@patch("pycompiler_ark.Ui.Cli.interactive.ask_yes_no", return_value=False)
def test_init_workspace_apply_internal_prompts_and_can_decline(
    mock_confirm, tmp_path
):
    workspace = _make_internal_workspace(tmp_path)

    payload = init_workspace(
        cwd=workspace,
        entry="src/pkg/main.py",
        apply_internal=True,
        auto_confirm=False,
    )

    assert payload["apply_internal"] is True
    assert payload["internal_modules"] == ["pkg"]
    assert payload["internal_modules_applied"] is False
    assert load_ark_config(workspace)["build"]["include"] == []
    mock_confirm.assert_called_once()


@patch("pycompiler_ark.Ui.Cli.interactive.ask_yes_no", return_value=True)
def test_init_workspace_apply_internal_prompts_and_can_accept(
    mock_confirm, tmp_path
):
    workspace = _make_internal_workspace(tmp_path)

    payload = init_workspace(
        cwd=workspace,
        entry="src/pkg/main.py",
        apply_internal=True,
        auto_confirm=False,
    )

    assert payload["apply_internal"] is True
    assert payload["internal_modules"] == ["pkg"]
    assert payload["internal_modules_applied"] is True
    assert load_ark_config(workspace)["build"]["include"] == ["pkg"]
    mock_confirm.assert_called_once()


@patch("pycompiler_ark.Ui.Cli.interactive.ask_yes_no")
def test_init_workspace_apply_internal_with_yes_flag(mock_confirm, tmp_path):
    workspace = _make_internal_workspace(tmp_path)

    payload = init_workspace(
        cwd=workspace,
        entry="src/pkg/main.py",
        apply_internal=True,
        auto_confirm=True,
    )

    assert payload["apply_internal"] is True
    assert payload["internal_modules"] == ["pkg"]
    assert payload["internal_modules_applied"] is True
    assert load_ark_config(workspace)["build"]["include"] == ["pkg"]
    mock_confirm.assert_not_called()
