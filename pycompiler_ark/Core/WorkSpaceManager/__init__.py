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

"""WorkSpaceManagerModule

This module manages all operations related to the workspace:
- Initial configuration of the workspace
- Advanced manipulation (drag & drop, file selection)
- Management of Python files in the workspace"""

from .SetupWorkspace import SetupWorkspace
from .WorkspaceManipulation import get_workspace_status

__all__ = ["SetupWorkspace", "get_workspace_status"]
