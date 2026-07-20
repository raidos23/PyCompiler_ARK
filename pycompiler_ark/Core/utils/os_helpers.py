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

import locale
import os
import platform
import re
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union

Pathish = Union[str, Path]

# -------------------------------
# OS helpers
# -------------------------------


def open_path(path: Pathish) -> bool:
    """Open a file or directory with the OS default handler. Returns True on attempt."""
    try:
        p = str(path)
        sysname = platform.system()
        if sysname == "Windows":
            os.startfile(p)  # type: ignore[attr-defined]
        elif sysname == "Linux":
            import subprocess

            subprocess.run(["xdg-open", p])
        else:
            import subprocess

            subprocess.run(["open", p])
        return True
    except Exception:
        return False
