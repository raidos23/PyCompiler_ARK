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

import shutil
import sys
from pathlib import Path

import pytest

# Ensure project root imports (e.g. `import Core`) work regardless of pytest invocation path.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


@pytest.fixture()
def test_workspace(tmp_path: Path) -> Path:
    """Return a temporary workspace for file-operation tests.

    The fixture prefers copying `tests/workspace_for_test` when available.
    If that template folder is missing, it creates a minimal workspace in
    `tmp_path` so tests remain hermetic and portable.
    """
    src = Path(__file__).parent / "workspace_for_test"
    dest = tmp_path / "workspace"
    if src.exists():
        shutil.copytree(src, dest)
        return dest

    dest.mkdir(parents=True, exist_ok=True)
    (dest / "main.py").write_text(
        "print('hello from test workspace')\n", encoding="utf-8"
    )
    (dest / "requirements.txt").write_text("requests\n", encoding="utf-8")
    (dest / ".ark").mkdir(parents=True, exist_ok=True)
    return dest
