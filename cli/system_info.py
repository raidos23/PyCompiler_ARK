# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import platform
from typing import Dict

from .output import plain


def print_system_info(app_version: str) -> None:
    info: Dict[str, str] = {
        "Application": "PyCompiler ARK",
        "Version": app_version,
        "Python": platform.python_version(),
        "Platform": platform.system(),
        "Architecture": platform.machine(),
    }

    plain("\nSystem Information:")
    for key, value in info.items():
        plain(f"  {key}: {value}")
