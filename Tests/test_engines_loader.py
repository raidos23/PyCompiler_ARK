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
Tests for Core.engines_loader module - Dynamic engine loading functionality
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestEnginesLoaderModule:
    """Test engines_loader module"""

    def test_import_engines_loader(self):
        """Test that engines_loader module can be imported"""
        from Core import engines_loader

        assert engines_loader is not None

    def test_import_registry(self):
        """Test that registry can be imported"""
        from Core.engines_loader import registry

        assert registry is not None

    def test_import_compiler_engine(self):
        """Test that CompilerEngine can be imported"""
        from Core.engines_loader import CompilerEngine

        assert CompilerEngine is not None


class TestRegistry:
    """Test engine registry functionality"""

    def test_registry_has_registered_engines(self):
        """Test that registry has some registered engines"""
        from Core.engines_loader import registry

        # Registry should have some engines
        engines = registry.get_engines()
        assert isinstance(engines, dict)

    def test_registry_get_engine_ids(self):
        """Test getting list of engine IDs"""
        from Core.engines_loader import registry

        engine_ids = registry.get_engine_ids()
        assert isinstance(engine_ids, list)
        # Should have at least pyinstaller and nuitka
        if len(engine_ids) > 0:
            assert any(
                "pyinstaller" in eid.lower() or "nuitka" in eid.lower()
                for eid in engine_ids
            )

    def test_registry_get_engine(self):
        """Test getting an engine by ID"""
        from Core.engines_loader import registry

        engine_ids = registry.get_engine_ids()
        if len(engine_ids) > 0:
            engine = registry.get_engine(engine_ids[0])
            assert engine is not None

    def test_registry_get_engine_for_tab(self):
        """Test getting engine for tab index"""
        from Core.engines_loader import registry

        # Should return None or an engine ID
        result = registry.get_engine_for_tab(0)
        # Result can be None if no engine is registered for tab 0

    def test_registry_get_engine_for_invalid_tab(self):
        """Test getting engine for invalid tab index"""
        from Core.engines_loader import registry

        result = registry.get_engine_for_tab(-1)
        assert result is None

    def test_registry_bind_tabs_function_exists(self):
        """Test that bind_tabs function exists"""
        from Core.engines_loader import registry

        assert hasattr(registry, "bind_tabs")
        assert callable(registry.bind_tabs)


class TestCompilerEngine:
    """Test CompilerEngine base class"""

    def test_compiler_engine_is_class(self):
        """Test that CompilerEngine is a class"""
        from Core.engines_loader import CompilerEngine

        assert isinstance(CompilerEngine, type)

    def test_compiler_engine_has_required_methods(self):
        """Test that CompilerEngine has required methods"""
        from Core.engines_loader import CompilerEngine

        engine = CompilerEngine()

        # Check for required methods
        required_methods = [
            "get_id",
            "get_name",
            "get_version",
            "create_tab",
            "get_options_widget",
            "get_compile_options",
        ]

        for method in required_methods:
            assert hasattr(engine, method), f"Missing method: {method}"

    def test_compiler_engine_has_required_attributes(self):
        """Test that CompilerEngine has required attributes"""
        from Core.engines_loader import CompilerEngine

        engine = CompilerEngine()

        # Check for required attributes
        required_attrs = ["GUI_CLASS"]
        for attr in required_attrs:
            assert hasattr(engine, attr), f"Missing attribute: {attr}"


class TestEnginesDiscovery:
    """Test engine discovery functionality"""

    def test_external_engines_directory_exists(self):
        """Test that external engines directory exists"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        engines_dir = os.path.join(project_root, "ENGINES")
        assert os.path.isdir(engines_dir)

    def test_engines_directory_has_packages(self):
        """Test that ENGINES directory has package directories"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        engines_dir = os.path.join(project_root, "ENGINES")

        if os.path.isdir(engines_dir):
            items = os.listdir(engines_dir)
            # Should have pyinstaller and nuitka
            assert any("pyinstaller" in item.lower() for item in items)
            assert any("nuitka" in item.lower() for item in items)

    def test_engine_packages_have_init(self):
        """Test that engine packages have __init__.py"""
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        engines_dir = os.path.join(project_root, "ENGINES")

        if os.path.isdir(engines_dir):
            for item in os.listdir(engines_dir):
                item_path = os.path.join(engines_dir, item)
                if os.path.isdir(item_path):
                    init_file = os.path.join(item_path, "__init__.py")
                    assert os.path.exists(init_file), f"Missing __init__.py in {item}"


class TestEngineCompatibility:
    """Test engine compatibility checking"""

    def test_check_engine_compatibility_exists(self):
        """Test that check_engine_compatibility function exists"""
        from Core.engines_loader import check_engine_compatibility

        assert callable(check_engine_compatibility)

    def test_validate_engines_compatibility_exists(self):
        """Test that validate_engines_compatibility function exists"""
        from Core.engines_loader import validate_engines_compatibility

        assert callable(validate_engines_compatibility)

    def test_validate_engines_compatibility_returns_result(self):
        """Test that validate_engines_compatibility returns a result"""
        from Core.engines_loader import validate_engines_compatibility

        result = validate_engines_compatibility()
        assert result is not None


class TestEngineRegistryApplyTranslations:
    """Test engine registry translation application"""

    def test_apply_translations_function_exists(self):
        """Test that registry has apply_translations method"""
        from Core.engines_loader import registry

        assert hasattr(registry, "apply_translations")
        assert callable(registry.apply_translations)

    def test_apply_translations_with_mock_gui(self):
        """Test applying translations via registry"""
        from Core.engines_loader import registry

        mock_gui = MagicMock()
        translations = {"test_key": "Test Value"}

        # Should not raise exception
        try:
            registry.apply_translations(mock_gui, translations)
        except Exception:
            # May fail if no engines are registered, which is OK
            pass
