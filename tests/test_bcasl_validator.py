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

"""Tests for BCASL plugin compatibility validator."""

from bcasl.validator import (
    parse_version,
    check_plugin_compatibility,
    validate_plugins_compatibility,
)


class DummyMeta:
    def __init__(
        self,
        plugin_id="dummy",
        name="Dummy",
        required_bcasl_version="2.0.0",
        required_core_version="1.0.0",
        required_plugins_sdk_version="1.0.0",
        required_bc_plugin_context_version="1.0.0",
        required_general_context_version="1.0.0",
    ):
        self.id = plugin_id
        self.name = name
        self.version = "0.1.0"
        self.required_bcasl_version = required_bcasl_version
        self.required_core_version = required_core_version
        self.required_plugins_sdk_version = required_plugins_sdk_version
        self.required_bc_plugin_context_version = required_bc_plugin_context_version
        self.required_general_context_version = required_general_context_version


class DummyPlugin:
    def __init__(self, meta: DummyMeta, ok_map: dict[str, bool]):
        self.meta = meta
        self._ok = ok_map

    def is_compatible_with_bcasl(self, _):
        return bool(self._ok.get("bcasl", True))

    def is_compatible_with_core(self, _):
        return bool(self._ok.get("core", True))

    def is_compatible_with_plugins_sdk(self, _):
        return bool(self._ok.get("plugins_sdk", True))

    def is_compatible_with_bc_plugin_context(self, _):
        return bool(self._ok.get("bc_context", True))

    def is_compatible_with_general_context(self, _):
        return bool(self._ok.get("general_context", True))


def test_parse_version_variants() -> None:
    assert parse_version("1.2.3") == (1, 2, 3)
    assert parse_version("2.0.0+") == (2, 0, 0)
    assert parse_version("3.4.5-beta") == (3, 4, 5)
    assert parse_version("bad") == (0, 0, 0)


def test_check_plugin_compatibility_missing_requirements() -> None:
    meta = DummyMeta(required_bcasl_version="2.0.0")
    plugin = DummyPlugin(meta, {"bcasl": False})

    result = check_plugin_compatibility(
        plugin,
        bcasl_version="1.0.0",
        core_version="1.0.0",
        plugins_sdk_version="1.0.0",
        bc_plugin_context_version="1.0.0",
        general_context_version="1.0.0",
    )

    assert result.is_compatible is False
    assert any("BCASL" in req for req in result.missing_requirements)
    assert result.plugin_id == "dummy"


def test_validate_plugins_compatibility_strict_mode() -> None:
    meta = DummyMeta(
        required_bcasl_version="1.0.0",
        required_core_version="1.0.0",
        required_plugins_sdk_version="1.0.0",
        required_bc_plugin_context_version="1.0.0",
        required_general_context_version="1.0.0",
    )
    plugin = DummyPlugin(meta, {"bcasl": True})

    compatible, incompatible = validate_plugins_compatibility(
        [plugin],
        bcasl_version="2.0.0",
        core_version="1.0.0",
        plugins_sdk_version="1.0.0",
        bc_plugin_context_version="1.0.0",
        general_context_version="1.0.0",
        strict_mode=True,
    )

    assert compatible == []
    assert len(incompatible) == 1
    assert "No explicit version requirements" in incompatible[0].error_message


def test_validate_plugins_compatibility_non_strict() -> None:
    meta = DummyMeta(
        required_bcasl_version="1.0.0",
        required_core_version="1.0.0",
        required_plugins_sdk_version="1.0.0",
        required_bc_plugin_context_version="1.0.0",
        required_general_context_version="1.0.0",
    )
    plugin = DummyPlugin(meta, {"bcasl": True})

    compatible, incompatible = validate_plugins_compatibility(
        [plugin],
        bcasl_version="2.0.0",
        core_version="1.0.0",
        plugins_sdk_version="1.0.0",
        bc_plugin_context_version="1.0.0",
        general_context_version="1.0.0",
        strict_mode=False,
    )

    assert len(compatible) == 1
    assert incompatible == []
