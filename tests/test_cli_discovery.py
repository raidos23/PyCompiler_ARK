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

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pycompiler_ark.Ui.Cli import discovery


class TestCliDiscovery(unittest.TestCase):
    def test_plugin_roots_includes_user_and_dev_dirs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            user_dir = temp_path / "user_plugins"
            dev_dir = temp_path / "dev_plugins"
            user_dir.mkdir(parents=True)
            dev_dir.mkdir(parents=True)

            def fake_resolve_config_value(
                key: str, create_default: bool = True
            ):
                if key == "user-plugin-dir":
                    return str(user_dir)
                if key == "dev-plugin-dir":
                    return str(dev_dir)
                return None

            with patch.object(
                discovery,
                "resolve_config_value",
                side_effect=fake_resolve_config_value,
            ):
                roots = discovery._plugin_roots()

            self.assertEqual(len(roots), 3)
            self.assertEqual(
                [label for _, label in roots], ["internal", "user", "dev"]
            )
            self.assertEqual(
                [path for path, _ in roots][1:], [user_dir, dev_dir]
            )

    def test_plugin_candidates_accepts_package_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            package_root = Path(temp_dir) / "my_plugin"
            package_root.mkdir(parents=True)
            init_file = package_root / "__init__.py"
            init_file.write_text(
                """
                id = 'example_plugin'
                name = 'Example Plugin'
                version = '0.1.0'
                description = 'Test plugin package root'
                author = 'ark'
                tags = ['test', 'plugin']
                """,
                encoding="utf-8",
            )

            with patch.object(
                discovery,
                "_plugin_roots",
                return_value=[(package_root, "user")],
            ):
                candidates = discovery._plugin_candidates()

            self.assertEqual(len(candidates), 1)
            candidate = candidates[0]
            self.assertEqual(candidate["id"], "example_plugin")
            self.assertEqual(candidate["name"], "Example Plugin")
            self.assertEqual(candidate["version"], "0.1.0")
            self.assertEqual(
                candidate["description"], "Test plugin package root"
            )
            self.assertEqual(candidate["author"], "ark")
            self.assertEqual(candidate["tags"], ["test", "plugin"])
            self.assertEqual(candidate["source"], "user")
            self.assertTrue(candidate["path"].endswith("__init__.py"))

    def test_scaffold_engine_creates_expected_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_name = "test-engine"
            payload = discovery.scaffold_engine(target_name, root_dir=temp_dir)
            self.assertTrue(payload["created"])

            engine_dir = Path(payload["path"])
            self.assertTrue((engine_dir / "__init__.py").exists())
            self.assertTrue((engine_dir / "mapping.json").exists())
            self.assertTrue((engine_dir / "languages").exists())
            self.assertTrue((engine_dir / "languages" / "en.yml").exists())

            content = (engine_dir / "__init__.py").read_text(encoding="utf-8")
            self.assertIn("class TestEngine", content)
            self.assertIn('id = "test_engine"', content)

    def test_scaffold_plugin_creates_expected_structure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target_name = "test plugin"
            payload = discovery.scaffold_plugin(target_name, root_dir=temp_dir)
            self.assertTrue(payload["created"])

            plugin_dir = Path(payload["path"])
            self.assertTrue((plugin_dir / "__init__.py").exists())
            self.assertTrue((plugin_dir / "languages").exists())
            self.assertTrue((plugin_dir / "languages" / "en.yml").exists())

            content = (plugin_dir / "__init__.py").read_text(encoding="utf-8")
            self.assertIn("class TestPlugin", content)
            self.assertIn('id="test_plugin"', content)


if __name__ == "__main__":
    unittest.main()
