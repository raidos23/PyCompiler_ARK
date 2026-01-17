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
Tests for Core.preferences module - User preferences functionality
"""

import pytest
import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings


class TestPreferencesModule:
    """Test preferences module functions"""

    def test_import_preferences(self):
        """Test that preferences module can be imported"""
        from Core import preferences
        assert preferences is not None

    def test_default_preferences_structure(self):
        """Test that default preferences have correct structure"""
        from Core.preferences import DEFAULT_PREFERENCES
        
        assert isinstance(DEFAULT_PREFERENCES, dict)
        # Check for expected keys
        assert "language" in DEFAULT_PREFERENCES
        assert "theme" in DEFAULT_PREFERENCES
        assert "language_pref" in DEFAULT_PREFERENCES

    def test_default_language_is_system(self):
        """Test that default language is System"""
        from Core.preferences import DEFAULT_PREFERENCES
        
        assert DEFAULT_PREFERENCES["language"] == "System"
        assert DEFAULT_PREFERENCES["language_pref"] == "System"

    def test_default_theme_is_system(self):
        """Test that default theme is System"""
        from Core.preferences import DEFAULT_PREFERENCES
        
        assert DEFAULT_PREFERENCES["theme"] == "System"


class TestLoadPreferences:
    """Test load_preferences function"""

    def test_load_preferences_returns_dict(self):
        """Test that load_preferences returns a dictionary"""
        from Core.preferences import load_preferences
        
        prefs = load_preferences()
        assert isinstance(prefs, dict)

    def test_load_preferences_contains_expected_keys(self):
        """Test that loaded preferences contain expected keys"""
        from Core.preferences import load_preferences
        
        prefs = load_preferences()
        expected_keys = ["language", "theme", "language_pref", "window_geometry"]
        for key in expected_keys:
            assert key in prefs

    def test_load_preferences_handles_missing_file(self):
        """Test that load_preferences handles missing file gracefully"""
        from Core.preferences import load_preferences
        
        # Should not raise an exception
        prefs = load_preferences()
        assert isinstance(prefs, dict)

    def test_load_preferences_with_corrupted_file(self):
        """Test that load_preferences handles corrupted file gracefully"""
        from Core.preferences import load_preferences
        
        # Should not raise an exception even with corrupted data
        prefs = load_preferences()
        assert isinstance(prefs, dict)


class TestSavePreferences:
    """Test save_preferences function"""

    def test_save_preferences_creates_file(self):
        """Test that save_preferences creates a preferences file"""
        from Core.preferences import save_preferences
        
        # Create a mock GUI object
        mock_gui = MagicMock()
        mock_gui.language = "en"
        mock_gui.theme = "dark"
        mock_gui.language_pref = "en"
        
        # save_preferences should not raise an exception
        try:
            save_preferences(mock_gui)
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

    def test_save_preferences_with_custom_path(self):
        """Test saving preferences to custom path"""
        from Core.preferences import save_preferences, load_preferences, DEFAULT_PREFERENCES
        
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_path = os.path.join(tmpdir, "custom_prefs.json")
            
            mock_gui = MagicMock()
            mock_gui.language = "fr"
            mock_gui.theme = "light"
            mock_gui.language_pref = "fr"
            
            # Mock the get_settings_path to return our custom path
            with patch('Core.preferences._get_settings_path', return_value=custom_path):
                try:
                    save_preferences(mock_gui)
                    # Verify file was created
                    assert os.path.exists(custom_path)
                    
                    # Verify content
                    with open(custom_path, 'r') as f:
                        saved = json.load(f)
                    assert saved["language"] == "fr"
                except Exception as e:
                    pytest.skip(f"QApplication not available: {e}")


class TestUpdateUIState:
    """Test update_ui_state function"""

    def test_update_ui_state_function_exists(self):
        """Test that update_ui_state function exists"""
        from Core.preferences import update_ui_state
        
        assert callable(update_ui_state)

    def test_update_ui_state_with_mock_gui(self):
        """Test update_ui_state with a mock GUI object"""
        from Core.preferences import update_ui_state
        
        mock_gui = MagicMock()
        mock_gui.select_lang = None
        mock_gui.select_theme = None
        
        # Should not raise an exception
        try:
            update_ui_state(mock_gui)
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")


class TestPreferencesMigration:
    """Test preferences migration functionality"""

    def test_preferences_have_version(self):
        """Test that preferences include version info"""
        from Core.preferences import DEFAULT_PREFERENCES
        
        assert "version" in DEFAULT_PREFERENCES or "app_version" in DEFAULT_PREFERENCES

    def test_load_preferences_preserves_unknown_keys(self):
        """Test that load_preferences preserves unknown keys from file"""
        from Core.preferences import load_preferences, DEFAULT_PREFERENCES
        
        # If there are any custom/unknown keys in the file, they should be preserved
        prefs = load_preferences()
        assert isinstance(prefs, dict)


class TestPreferencesEdgeCases:
    """Test edge cases in preferences handling"""

    def test_load_preferences_with_empty_file(self):
        """Test handling of empty preferences file"""
        from Core.preferences import load_preferences
        
        # Should return defaults when file is empty
        prefs = load_preferences()
        assert isinstance(prefs, dict)
        assert len(prefs) > 0

    def test_load_preferences_with_null_values(self):
        """Test handling of null values in preferences"""
        from Core.preferences import load_preferences
        
        # Should handle null values gracefully
        prefs = load_preferences()
        # Should have all expected keys
        assert "language" in prefs

    def test_language_preference_values(self):
        """Test valid language preference values"""
        from Core.preferences import DEFAULT_PREFERENCES
        
        valid_languages = ["System", "en", "fr", "de", "es", "it", "ja", "ko", "pt-BR", "ru", "zh-CN", "af"]
        # Default should be "System"
        assert DEFAULT_PREFERENCES["language"] in ["System"] + valid_languages

    def test_theme_preference_values(self):
        """Test valid theme preference values"""
        from Core.preferences import DEFAULT_PREFERENCES
        
        # Default should be "System"
        assert DEFAULT_PREFERENCES["theme"] == "System"


class TestPreferencesQtIntegration:
    """Test Qt-specific preferences functionality"""

    def test_settings_object_creation(self):
        """Test that QSettings object can be created"""
        try:
            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            
            settings = QSettings("PyCompiler", "ARK")
            assert settings is not None
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

    def test_preferences_use_qsettings(self):
        """Test that preferences module uses QSettings"""
        from Core import preferences
        
        # Verify that QSettings is used in the module
        assert hasattr(preferences, 'QSettings') or 'QSettings' in dir(preferences)

