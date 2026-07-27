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
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple, Union

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


def get_interpreter_version(
    python_path: Optional[str] = None,
) -> Tuple[int, int, int]:
    """
    Return Python interpreter version.

    Args:
     python_path: Path de l'interpréteur (défaut: sys.executable)

    Returns:
     Tuple (major, minor, patch)
    """
    if python_path is None:
        python_path = sys.executable

    try:
        result = subprocess.run(
            [python_path, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version_str = result.stdout or result.stderr
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if match:
            return (
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
    except Exception:
        pass

    return (
        sys.version_info.major,
        sys.version_info.minor,
        sys.version_info.micro,
    )


def get_interpreter_version_str(python_path: Optional[str] = None) -> str:
    """
    Return Python interpreter version as a string.

    Args:
     python_path: Path de l'interpréteur (défaut: sys.executable)

    Returns:
     Version string (ex: "3.10.12")
    """
    v = get_interpreter_version(python_path)
    return f"{v[0]}.{v[1]}.{v[2]}"


def check_module_available(
    module_name: str, python_path: Optional[str] = None
) -> bool:
    """
    Check whether a Python module is available.

    Args:
     module_name: Nom du module
     python_path: Path de l'interpréteur

    Returns:
     True si le module est disponible
    """
    try:
        if python_path:
            result = subprocess.run(
                [python_path, "-c", f"import {module_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        else:
            import importlib

            importlib.import_module(module_name)
            return True
    except Exception:
        return False
