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

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class BuildContext:
    """Generic build payload passed from ARK to compilation engines."""

    project_name: str
    entry_point: str
    output_dir: str
    exclude_packages: list[str]
    include_packages: list[str]
    data_mappings: list[
        dict[str, Any]
    ]  # Each dict: {"source": str, "destination": str, "type": "file" | "dir"}
    icon: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON/YAML-friendly representation of the build context."""
        return asdict(self)


__all__ = ["BuildContext"]
