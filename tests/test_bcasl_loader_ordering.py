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

"""Tests for BCASL Loader ordering helpers."""

from bcasl import Loader


def test_resolve_ordered_plugin_ids_uses_config_order() -> None:
    plugin_ids = ["a", "b", "c"]
    meta_map = {
        "a": {"tags": ["lint"]},
        "b": {"tags": ["clean"]},
        "c": {"tags": []},
    }
    cfg = {"plugin_order": ["b", "a"]}

    order = Loader._resolve_ordered_plugin_ids(plugin_ids, meta_map, cfg)
    assert order[:2] == ["b", "a"]
    assert "c" in order[2:]


def test_resolve_ordered_plugin_ids_falls_back_to_tags() -> None:
    plugin_ids = ["a", "b"]
    meta_map = {
        "a": {"tags": ["lint"]},
        "b": {"tags": ["clean"]},
    }
    cfg = {}

    order = Loader._resolve_ordered_plugin_ids(plugin_ids, meta_map, cfg)
    assert order == ["b", "a"]
