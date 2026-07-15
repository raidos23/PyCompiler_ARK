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

"""
engine_sdk.utils — Robust helpers for engine authors

"""

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
# Executable resolution helper
# -------------------------------
def resolve_executable(
    program: Pathish, base_dir: Optional[Pathish] = None, *, prefer_path: bool = True
) -> str:
    """Resolve an executable path according to a clear, cross-platform policy.

    - Absolute program path: returned as-is.
    - Bare command (no path separator) and prefer_path=True: use shutil.which to resolve real path if available;
      otherwise return the command name (so the OS can resolve it via PATH at runtime).
    - Otherwise: join relative to base_dir (or CWD) and return an absolute path.
    """
    prog = str(program)
    try:
        # Absolute path -> as is
        if os.path.isabs(prog):
            return prog
        bare = (os.path.sep not in prog) and (not prog.startswith("."))
        if prefer_path and bare:
            try:
                found = shutil.which(prog)
                if found:
                    return found
            except Exception:
                pass
            # Keep bare command to allow OS PATH resolution later
            return prog
        # Else, resolve relative to base_dir (or CWD)
        base = str(base_dir) if base_dir is not None else os.getcwd()
        return os.path.abspath(os.path.join(base, prog))
    except Exception:
        # Fallback: return the original string
        return prog


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
