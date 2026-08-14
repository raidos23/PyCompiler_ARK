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

import tempfile
import unittest
import importlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pycompiler_ark.Plugins_SDK.GeneralContext import i18n as gc_i18n

gc_dialog = importlib.import_module(
    "pycompiler_ark.Plugins_SDK.GeneralContext.Dialog"
)


class TestGeneralContextSdk(unittest.TestCase):
    def setUp(self) -> None:
        gc_i18n._PLUGIN_TR.clear()

    def test_load_all_plugin_languages_scans_all_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            internal_root = base / "internal_plugins"
            user_root = base / "user_plugins"
            for root, plugin_name, label in (
                (internal_root, "alpha", "Alpha"),
                (user_root, "beta", "Beta"),
            ):
                plugin_dir = root / plugin_name
                lang_dir = plugin_dir / "languages"
                lang_dir.mkdir(parents=True, exist_ok=True)
                (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
                (lang_dir / "en.yml").write_text(
                    f"tab_title: {label}\n", encoding="utf-8"
                )

            with patch.object(
                gc_i18n,
                "_plugin_roots",
                return_value=[
                    (internal_root, "internal"),
                    (user_root, "user"),
                ],
            ):
                gc_i18n._load_all_plugin_languages("en")

            self.assertEqual(gc_i18n._PLUGIN_TR["alpha"]["tab_title"], "Alpha")
            self.assertEqual(gc_i18n._PLUGIN_TR["beta"]["tab_title"], "Beta")

    def test_resolve_plugin_id_uses_discovered_plugin_roots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "external_plugins"
            plugin_dir = root / "gamma"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            (plugin_dir / "__init__.py").write_text("", encoding="utf-8")
            plugin_file = plugin_dir / "module.py"
            plugin_file.write_text("", encoding="utf-8")

            fake_stack = [
                SimpleNamespace(filename="/tmp/bootstrap.py"),
                SimpleNamespace(filename="/tmp/bootstrap2.py"),
                SimpleNamespace(filename=str(plugin_file)),
            ]

            with (
                patch.object(
                    gc_dialog,
                    "_plugin_roots",
                    return_value=[(root, "user")],
                ),
                patch.object(
                    gc_dialog.inspect, "stack", return_value=fake_stack
                ),
            ):
                dialog = gc_dialog.Dialog.__new__(gc_dialog.Dialog)
                dialog.plugin_id = None
                self.assertEqual(dialog._resolve_plugin_id(), "gamma")


if __name__ == "__main__":
    unittest.main()
