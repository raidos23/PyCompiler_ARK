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

from cli import click_app, dedicated, fallback
from cli.runtime import should_enable_qt


def test_should_enable_qt_for_headless_commands() -> None:
    assert should_enable_qt(["--help"]) is False
    assert should_enable_qt(["--version"]) is False
    assert should_enable_qt(["--info"]) is False
    assert should_enable_qt(["--cli"]) is False
    assert should_enable_qt(["--unload"]) is False
    assert should_enable_qt(["engines", "--dry-run"]) is False
    assert should_enable_qt(["engine", "list"]) is False
    assert should_enable_qt(["bcasl", "list"]) is False


def test_should_enable_qt_for_gui_commands() -> None:
    assert should_enable_qt([]) is True
    assert should_enable_qt(["main"]) is True
    assert should_enable_qt(["--ide-gui"]) is True
    assert should_enable_qt(["engines"]) is True


def test_cli_modules_import_without_qt_bootstrap_side_effects() -> None:
    assert callable(click_app.build_cli)
    assert callable(fallback.run)
    assert callable(dedicated.run_dedicated_cli)
