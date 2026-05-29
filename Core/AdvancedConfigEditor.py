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
ConfigEditorService — business logic for the structured Project Config Editor.
"""

from __future__ import annotations

from typing import Any


def flatten_keys(data: Any, prefix: str = "") -> list[str]:
    """Recursively flatten dict/list keys into dotted paths."""
    lines: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            k = str(key)
            path = f"{prefix}.{k}" if prefix else k
            lines.append(path)
            lines.extend(flatten_keys(value, path))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            path = f"{prefix}[{idx}]"
            lines.append(path)
            lines.extend(flatten_keys(value, path))
    return lines


def validate_ark_payload(data: Any) -> tuple[list[str], list[str]]:
    """Validate ark.yml data structure.

    Returns:
        (errors, warnings)
    """
    errs: list[str] = []
    warns: list[str] = []

    if not isinstance(data, dict):
        errs.append("Root must be an object/map.")
        return errs, warns

    allowed_top = {
        "project",
        "workspace",
        "build",
        "plugins",
    }
    unknown = sorted(k for k in data.keys() if k not in allowed_top)
    if unknown:
        warns.append("Unknown top-level keys: " + ", ".join(unknown))

    # project
    project = data.get("project")
    if project is not None:
        if not isinstance(project, dict):
            errs.append("project must be an object.")
        else:
            for k in ("name", "version", "entry"):
                v = project.get(k)
                if v is not None and not isinstance(v, str):
                    errs.append(f"project.{k} must be a string.")

    # workspace
    workspace_cfg = data.get("workspace")
    if workspace_cfg is not None:
        if not isinstance(workspace_cfg, dict):
            errs.append("workspace must be an object.")
        else:
            exclude = workspace_cfg.get("exclude")
            if exclude is not None and (
                not isinstance(exclude, list)
                or not all(isinstance(item, str) for item in exclude)
            ):
                errs.append("workspace.exclude must be a list of strings.")

    # build
    build = data.get("build")
    if build is not None:
        if not isinstance(build, dict):
            errs.append("build must be an object.")
        else:
            for k in ("engine", "output", "icon", "entrypoint"):
                v = build.get(k)
                if v is not None and not isinstance(v, (str, type(None))):
                    errs.append(f"build.{k} must be a string or null.")

            exclude = build.get("exclude")
            if exclude is not None and (
                not isinstance(exclude, list)
                or not all(isinstance(item, str) for item in exclude)
            ):
                errs.append("build.exclude must be a list of strings.")

            data_map = build.get("data")
            if data_map is not None:
                if not isinstance(data_map, list):
                    errs.append("build.data must be a list.")
                else:
                    for idx, item in enumerate(data_map):
                        if not isinstance(item, dict):
                            errs.append(f"build.data[{idx}] must be an object.")
                        else:
                            if not item.get("source"):
                                errs.append(f"build.data[{idx}] missing 'source'.")

    # plugins
    plugins = data.get("plugins")
    if plugins is not None:
        if not isinstance(plugins, dict):
            errs.append("plugins must be an object.")
        else:
            bcasl_enabled = plugins.get("bcasl_enabled")
            if bcasl_enabled is not None and not isinstance(bcasl_enabled, bool):
                errs.append("plugins.bcasl_enabled must be a boolean.")

    return errs, warns
