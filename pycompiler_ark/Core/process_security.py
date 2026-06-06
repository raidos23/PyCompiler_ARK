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

import os
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

_ENV_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _is_safe_text(value: str) -> bool:
    return ("\x00" not in value) and ("\r" not in value) and ("\n" not in value)


def resolve_executable(program: str) -> str:
    """Resolve and validate an executable path/name."""
    prog = str(program or "").strip()
    if not prog:
        raise ValueError("Executable is empty")
    if not _is_safe_text(prog):
        raise ValueError("Executable contains invalid control characters")

    if os.path.sep in prog or (os.path.altsep and os.path.altsep in prog):
        abs_prog = os.path.abspath(prog)
        if not os.path.isfile(abs_prog):
            raise FileNotFoundError(f"Executable not found: {abs_prog}")
        if not os.access(abs_prog, os.X_OK):
            raise PermissionError(f"Executable is not executable: {abs_prog}")
        return abs_prog

    found = shutil.which(prog)
    if not found:
        raise FileNotFoundError(f"Executable not found in PATH: {prog}")
    return found


def sanitize_cli_args(args: List[str]) -> List[str]:
    """Validate CLI arguments for subprocess launch."""
    out: List[str] = []
    total = 0
    for raw in list(args or []):
        s = str(raw)
        if not _is_safe_text(s):
            raise ValueError("Argument contains invalid control characters")
        total += len(s)
        if total > 262144:
            raise ValueError("Command line arguments are too large")
        out.append(s)
    return out


def sanitize_env_overrides(env: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Validate environment override keys/values."""
    clean: Dict[str, str] = {}
    if not isinstance(env, dict):
        return clean
    for key, val in env.items():
        k = str(key or "")
        v = str(val if val is not None else "")
        if not _ENV_KEY_RE.match(k):
            continue
        if not _is_safe_text(k):
            continue
        if "\x00" in v:
            continue
        clean[k] = v
    return clean


def build_secure_env(env: Optional[Dict[str, str]]) -> Dict[str, str]:
    base = dict(os.environ)
    base.update(sanitize_env_overrides(env))
    return base


def hardened_popen_kwargs() -> Dict[str, object]:
    """Subprocess kwargs that reduce process/FD inheritance risks."""
    kw: Dict[str, object] = {"stdin": subprocess.DEVNULL}
    if os.name != "nt":
        kw["close_fds"] = True
        kw["start_new_session"] = True
    return kw


def secure_command(
    program: str, args: List[str], env: Optional[Dict[str, str]]
) -> Tuple[str, List[str], Dict[str, str]]:
    return resolve_executable(program), sanitize_cli_args(args), build_secure_env(env)
