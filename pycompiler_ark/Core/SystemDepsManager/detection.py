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

"""Package manager detection and install command helpers."""

from __future__ import annotations

import platform
import shutil
from typing import Optional


def detect_linux_package_manager() -> Optional[str]:
    for pm in ("apt", "dnf", "yum", "pacman", "zypper"):
        if shutil.which(pm):
            return pm
    return None


def detect_macos_package_manager() -> Optional[str]:
    if shutil.which("brew"):
        return "brew"
    return None


def which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def get_install_command(packages: list[str]) -> Optional[str]:
    """Generate a platform-specific install command string."""
    if not packages:
        return None

    system = platform.system()
    if system == "Linux":
        pm = detect_linux_package_manager()
        if not pm:
            return None
        pkgs = " ".join(packages)
        return f"{pm} install -y {pkgs}"

    if system == "Windows":
        if not shutil.which("winget"):
            return None
        parts = [
            f"winget install --id {p} --silent --accept-source-agreements --accept-package-agreements"
            for p in packages
        ]
        return " && ".join(parts)

    if system == "Darwin":
        pm = detect_macos_package_manager()
        if pm == "brew":
            pkgs = " ".join(packages)
            return f"brew install {pkgs}"

    return None
