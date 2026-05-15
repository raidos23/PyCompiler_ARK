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

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from Ui.Cli.app import build_cli
from Ui.Cli.discovery import bcasl_doctor_payload, engine_list_payload
from Ui.Cli.entrypoint import main as entrypoint_main
from Ui.Cli.runtime import should_enable_qt


def test_should_enable_qt_for_headless_commands() -> None:
    assert should_enable_qt(["--help"]) is False
    assert should_enable_qt(["--version"]) is False
    assert should_enable_qt(["init", "--entry", "main.py"]) is False
    assert should_enable_qt(["build"]) is False
    assert should_enable_qt(["list", "engines"]) is False
    assert should_enable_qt(["run", "bcasl"]) is False


def test_should_enable_qt_for_gui_commands() -> None:
    assert should_enable_qt([]) is True
    assert should_enable_qt(["gui"]) is True
    assert should_enable_qt(["gui", "--legacy"]) is True


def test_cli_modules_import_without_qt_bootstrap_side_effects() -> None:
    assert callable(build_cli)


def test_engine_list_payload_is_available_headlessly() -> None:
    payload = engine_list_payload()

    assert payload["count"] >= 1
    assert any(item["id"] == "pyinstaller" for item in payload["engines"])


def test_bcasl_doctor_payload_discovers_plugin_candidates_headlessly() -> None:
    payload = bcasl_doctor_payload()

    assert payload["checks"]
    assert payload["plugins"]["count"] >= 1
    assert any(item["id"] == "cleaner" for item in payload["plugins"]["plugins"])


def test_entrypoint_preserves_click_return_codes() -> None:
    code = entrypoint_main(["--help"])

    assert code == 0


def test_entrypoint_returns_usage_error_for_unknown_command() -> None:
    code = entrypoint_main(["ci", "smoke"])

    assert code == 2
