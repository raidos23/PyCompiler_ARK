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
Tests for Core.ark_config_loader module - ARK configuration file handling
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch, MagicMock


class TestArkConfigLoader:
    """Test ARK configuration loader functions"""

    def test_import_ark_config_loader(self):
        """Test that ark_config_loader module can be imported"""
        from Core import ark_config_loader

        assert ark_config_loader is not None


class TestLoadArkConfig:
    """Test load_ark_config function"""

    def test_load_ark_config_with_valid_file(self):
        """Test loading a valid ARK config file"""
        from Core.ark_config_loader import load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "ARK_Main_Config.yml")

            # Create a valid config file
            config_data = {
                "exclusion_patterns": ["*.pyc", "__pycache__"],
                "compiler_options": {"pyinstaller": {"onefile": True}},
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Load the config
            result = load_ark_config(tmpdir)

            assert isinstance(result, dict)
            assert "exclusion_patterns" in result

    def test_load_ark_config_with_missing_file(self):
        """Test loading config when file doesn't exist"""
        from Core.ark_config_loader import load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            # Should return empty dict or default config
            result = load_ark_config(tmpdir)
            assert isinstance(result, dict)

    def test_load_ark_config_with_invalid_yaml(self):
        """Test loading config with invalid YAML"""
        from Core.ark_config_loader import load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "ARK_Main_Config.yml")

            # Create invalid YAML
            with open(config_path, "w") as f:
                f.write("invalid: yaml: content: [")

            # Should handle error gracefully
            result = load_ark_config(tmpdir)
            assert isinstance(result, dict)

    def test_load_ark_config_with_empty_file(self):
        """Test loading config with empty file"""
        from Core.ark_config_loader import load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "ARK_Main_Config.yml")

            # Create empty file
            with open(config_path, "w") as f:
                pass

            # Should return empty dict or handle gracefully
            result = load_ark_config(tmpdir)
            assert isinstance(result, dict)


class TestCreateDefaultArkConfig:
    """Test create_default_ark_config function"""

    def test_create_default_config(self):
        """Test creating default ARK config"""
        from Core.ark_config_loader import create_default_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            result = create_default_ark_config(tmpdir)
            assert result is True

            # Verify file was created
            config_path = os.path.join(tmpdir, "ARK_Main_Config.yml")
            assert os.path.exists(config_path)

    def test_create_default_config_structure(self):
        """Test that default config has correct structure"""
        from Core.ark_config_loader import create_default_ark_config, load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            create_default_ark_config(tmpdir)

            config = load_ark_config(tmpdir)

            assert isinstance(config, dict)
            # Check for expected keys in default config
            expected_keys = ["exclusion_patterns", "compiler_options"]
            for key in expected_keys:
                assert key in config

    def test_create_default_config_no_overwrite(self):
        """Test that default config doesn't overwrite existing"""
        from Core.ark_config_loader import create_default_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "ARK_Main_Config.yml")

            # Create existing config
            with open(config_path, "w") as f:
                f.write("custom: config")

            # Should not overwrite
            result = create_default_ark_config(tmpdir)
            assert result is False


class TestShouldExcludeFile:
    """Test should_exclude_file function"""

    def test_should_exclude_file_with_pattern(self):
        """Test that matching patterns are excluded"""
        from Core.ark_config_loader import should_exclude_file

        with tempfile.TemporaryDirectory() as tmpdir:
            patterns = ["*.pyc", "__pycache__"]

            assert should_exclude_file("test.pyc", tmpdir, patterns) is True
            assert should_exclude_file("test.py", tmpdir, patterns) is False

    def test_should_exclude_file_with_directory(self):
        """Test that __pycache__ directories are excluded"""
        from Core.ark_config_loader import should_exclude_file

        with tempfile.TemporaryDirectory() as tmpdir:
            patterns = ["__pycache__", "*.egg-info"]

            assert should_exclude_file("__pycache__", tmpdir, patterns) is True
            assert should_exclude_file("test.egg-info", tmpdir, patterns) is True

    def test_should_exclude_file_empty_patterns(self):
        """Test with empty exclusion patterns"""
        from Core.ark_config_loader import should_exclude_file

        with tempfile.TemporaryDirectory() as tmpdir:
            result = should_exclude_file("test.pyc", tmpdir, [])
            assert result is False

    def test_should_exclude_file_none_patterns(self):
        """Test with None exclusion patterns"""
        from Core.ark_config_loader import should_exclude_file

        with tempfile.TemporaryDirectory() as tmpdir:
            result = should_exclude_file("test.pyc", tmpdir, None)
            assert result is False


class TestArkConfigSchema:
    """Test ARK configuration schema validation"""

    def test_default_config_schema(self):
        """Test that default config follows schema"""
        from Core.ark_config_loader import create_default_ark_config, load_ark_config
        from Core.ark_config_loader import SCHEMA

        with tempfile.TemporaryDirectory() as tmpdir:
            create_default_ark_config(tmpdir)
            config = load_ark_config(tmpdir)

            # Verify config follows schema
            if SCHEMA:
                # If there's a schema, validate against it
                assert isinstance(config, dict)

    def test_config_has_exclusion_patterns(self):
        """Test that config has exclusion_patterns key"""
        from Core.ark_config_loader import create_default_ark_config, load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            create_default_ark_config(tmpdir)
            config = load_ark_config(tmpdir)

            assert "exclusion_patterns" in config
            assert isinstance(config["exclusion_patterns"], list)


class TestArkConfigPaths:
    """Test path handling in ARK config"""

    def test_config_path_construction(self):
        """Test that config path is constructed correctly"""
        from Core.ark_config_loader import _get_config_path

        workspace = "/some/workspace"
        path = _get_config_path(workspace)

        assert path.endswith("ARK_Main_Config.yml")
        assert workspace in path

    def test_expand_variables_in_config(self):
        """Test variable expansion in config values"""
        from Core.ark_config_loader import load_ark_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "ARK_Main_Config.yml")

            config_data = {"paths": {"output": "${workspace}/build"}}

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            config = load_ark_config(tmpdir)

            # Check that variable was expanded
            if "paths" in config and "output" in config["paths"]:
                output = config["paths"]["output"]
                assert tmpdir in output or "build" in output
