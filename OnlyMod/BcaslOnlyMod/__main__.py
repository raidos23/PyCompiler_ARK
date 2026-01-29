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

"""
BCASL Standalone Module Entry Point

Allows running BCASL as a standalone application:
    python -m bcasl.only_mod [workspace_path]

Examples:
    # Launch with no workspace
    python -m bcasl.only_mod

    # Launch with a specific workspace
    python -m bcasl.only_mod /path/to/workspace

    # Launch from current directory
    python -m bcasl.only_mod .
"""

from .app import main

if __name__ == "__main__":
    main()
