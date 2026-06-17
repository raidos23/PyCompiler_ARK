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

"""Headless helpers for system dependency checks and installation."""

from __future__ import annotations

import shutil
import subprocess

from pycompiler_ark.Core.Compiler.utils import check_internet_connection
from pycompiler_ark.Core.SystemDepsManager.detection import detect_linux_package_manager


def check_system_packages(packages: list[str]) -> bool:
    return all(shutil.which(pkg) for pkg in packages if pkg)


def install_system_packages(packages: list[str], gui=None) -> bool:
    """Headless/CI install entry point."""
    if not check_internet_connection():
        return False

    pkgs = [p.strip() for p in packages if p.strip()]
    if not pkgs:
        return True

    pm = detect_linux_package_manager()
    if not pm:
        return False

    cmd_prefix = ["sudo", "-n"]
    if pm == "apt":
        steps = [
            cmd_prefix + ["apt-get", "update"],
            cmd_prefix + ["apt-get", "install", "-y"] + pkgs,
        ]
    else:
        steps = [cmd_prefix + [pm, "install", "-y"] + pkgs]

    for cmd in steps:
        if subprocess.run(cmd).returncode != 0:
            return False
    return True
