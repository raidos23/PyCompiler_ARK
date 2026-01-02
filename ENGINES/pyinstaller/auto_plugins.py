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

# Engine-controlled auto builder for PyInstaller
# Signature required by host: (matched: dict, pkg_to_import: dict) -> list[str]
from engine_sdk import register_auto_builder  # type: ignore


def AUTO_BUILDER(
    matched: dict[str, dict[str, object]], pkg_to_import: dict[str, str]
) -> list[str]:
    """
    Build PyInstaller arguments from the engine-owned mapping.

    Mapping conventions supported for an entry value under key "pyinstaller":
      - str: a single CLI argument (e.g., "--collect-all=numpy")
      - list[str]: multiple CLI arguments
      - dict: expects 'args' or 'flags' -> str | list[str]
      - True: ignored by default (no generic meaning)
    """
    out: list[str] = []
    seen = set()

    for pkg, entry in matched.items():
        if not isinstance(entry, dict):
            continue
        val = entry.get("pyinstaller")
        if val is None:
            continue
        args: list[str] = []
        if isinstance(val, str):
            tmpl_import = pkg_to_import.get(pkg, pkg)
            args = [val.replace("{import_name}", tmpl_import)]
        elif isinstance(val, list):
            tmpl_import = pkg_to_import.get(pkg, pkg)
            args = [str(x).replace("{import_name}", tmpl_import) for x in val]
        elif isinstance(val, dict):
            tmpl_import = pkg_to_import.get(pkg, pkg)
            a = val.get("args") or val.get("flags")
            if isinstance(a, list):
                args = [str(x).replace("{import_name}", tmpl_import) for x in a]
            elif isinstance(a, str):
                args = [str(a).replace("{import_name}", tmpl_import)]
        for a in args:
            if a not in seen:
                out.append(a)
                seen.add(a)

    return out


# Register at import time via the SDK facade
try:
    register_auto_builder("pyinstaller", AUTO_BUILDER)
except Exception:
    pass
