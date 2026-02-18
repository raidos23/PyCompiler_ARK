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

"""Tests for BCASL tagging order utilities."""

from bcasl.tagging import compute_tag_order, describe_plugin_priority


def test_compute_tag_order_respects_priority() -> None:
    meta_map = {
        "plugin_lint": {"tags": ["lint"]},
        "plugin_clean": {"tags": ["clean"]},
        "plugin_none": {"tags": []},
    }

    order = compute_tag_order(meta_map)
    assert order[0] == "plugin_clean"
    assert order[1] == "plugin_lint"
    assert order[2] == "plugin_none"


def test_describe_plugin_priority_includes_phase() -> None:
    desc = describe_plugin_priority("plugin_lint", ["lint", "format"])
    assert "plugin_lint" in desc
    assert "Phase 40" in desc
