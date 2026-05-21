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
Plugin Compatibility Validator - Validates plugin compatibility with system components.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CompatibilityCheckResult:
    """Result of a plugin compatibility check."""

    plugin_id: str
    plugin_name: str
    is_compatible: bool
    missing_requirements: List[str]
    error_message: str = ""


def parse_version(version_string: str) -> Tuple[int, int, int]:
    """Parse a version string into (major, minor, patch)."""
    try:
        s = version_string.strip()
        if s.endswith("+"):
            s = s[:-1].strip()
        s = s.split("+")[0].split("-")[0]
        parts = s.split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception:
        return (0, 0, 0)


def check_plugin_compatibility(
    plugin,
    bcasl_version: str,
    core_version: str,
    plugins_sdk_version: str,
    bc_plugin_context_version: str,
    general_context_version: str,
) -> CompatibilityCheckResult:
    """Check if a plugin is compatible with the current system versions."""
    meta = plugin.meta
    plugin_id = meta.id
    plugin_name = meta.name
    missing_requirements = []

    def _check(label, current, required):
        if parse_version(current) < parse_version(required):
            missing_requirements.append(f"{label} >= {required} (current: {current})")

    _check("BCASL", bcasl_version, meta.required_bcasl_version)
    _check("Core", core_version, meta.required_core_version)
    _check("Plugins SDK", plugins_sdk_version, meta.required_plugins_sdk_version)
    _check("BcPluginContext", bc_plugin_context_version, meta.required_bc_plugin_context_version)
    _check("GeneralContext", general_context_version, meta.required_general_context_version)

    is_compatible = len(missing_requirements) == 0
    error_message = ""
    if not is_compatible:
        error_message = f"Plugin '{plugin_name}' ({plugin_id}) is incompatible. Missing: {', '.join(missing_requirements)}"

    return CompatibilityCheckResult(
        plugin_id=plugin_id,
        plugin_name=plugin_name,
        is_compatible=is_compatible,
        missing_requirements=missing_requirements,
        error_message=error_message,
    )


def validate_plugins_compatibility(
    plugins: List,
    bcasl_version: str,
    core_version: str,
    plugins_sdk_version: str,
    bc_plugin_context_version: str,
    general_context_version: str,
    strict_mode: bool = True,
) -> Tuple[List, List]:
    """Validate a list of plugins for compatibility."""
    compatible_plugins = []
    incompatible_results = []

    for plugin in plugins:
        try:
            meta = plugin.meta
            if strict_mode:
                has_explicit = any(
                    v != "1.0.0" for v in [
                        meta.required_bcasl_version,
                        meta.required_core_version,
                        meta.required_plugins_sdk_version,
                        meta.required_bc_plugin_context_version,
                        meta.required_general_context_version
                    ]
                )

                if not has_explicit:
                    result = CompatibilityCheckResult(
                        plugin_id=meta.id,
                        plugin_name=meta.name,
                        is_compatible=False,
                        missing_requirements=["No explicit version requirements specified"],
                        error_message=f"No explicit version requirements specified. Plugin '{meta.name}' ({meta.id}) does not specify version requirements.",
                    )
                    incompatible_results.append(result)
                    continue

            result = check_plugin_compatibility(
                plugin, bcasl_version, core_version, plugins_sdk_version,
                bc_plugin_context_version, general_context_version,
            )

            if result.is_compatible:
                compatible_plugins.append(plugin)
            else:
                incompatible_results.append(result)

        except Exception as e:
            incompatible_results.append(CompatibilityCheckResult(
                plugin_id=getattr(getattr(plugin, "meta", None), "id", "unknown"),
                plugin_name=getattr(getattr(plugin, "meta", None), "name", "Unknown"),
                is_compatible=False,
                missing_requirements=[],
                error_message=f"Error validating plugin: {str(e)}",
            ))

    return compatible_plugins, incompatible_results


def print_compatibility_report(
    compatible_plugins: List,
    incompatible_results: List,
) -> None:
    """Print a formatted compatibility report."""
    print("=" * 70)
    print("Plugin Compatibility Report")
    print("=" * 70)
    print(f"\n✓ Compatible: {len(compatible_plugins)}")
    for plugin in compatible_plugins:
        print(f"  - {plugin.meta.name} ({plugin.meta.id}) v{plugin.meta.version}")
    print(f"\n✗ Incompatible: {len(incompatible_results)}")
    for result in incompatible_results:
        print(f"  - {result.plugin_name} ({result.plugin_id})")
        for req in result.missing_requirements:
            print(f"    • {req}")
        if result.error_message:
            print(f"    Error: {result.error_message}")
    print("\n" + "=" * 70)


__all__ = [
    "CompatibilityCheckResult",
    "parse_version",
    "check_plugin_compatibility",
    "validate_plugins_compatibility",
    "print_compatibility_report",
]
