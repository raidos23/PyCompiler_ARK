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

"""Internal system dependency management package."""

from pycompiler_ark.Core.SystemDepsManager.detection import (
    detect_linux_package_manager,
    detect_macos_package_manager,
    get_install_command,
    which,
)
from pycompiler_ark.Core.SystemDepsManager.headless import (
    check_system_packages,
    install_system_packages,
)
from pycompiler_ark.Core.SystemDepsManager.manager import SysDependencyManager

__all__ = [
    "SysDependencyManager",
    "check_system_packages",
    "install_system_packages",
    "detect_linux_package_manager",
    "detect_macos_package_manager",
    "get_install_command",
    "which",
]
