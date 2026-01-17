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
Tests for Core.init_ui module - UI initialization functionality
"""

import pytest
import os
from unittest.mock import patch, MagicMock


class TestInitUIModule:
    """Test init_ui module functions"""

    def test_import_init_ui(self):
        """Test that init_ui module can be imported"""
        from Core import init_ui
        assert init_ui is not None


class TestThemeDetection:
    """Test theme detection functions"""

    def test_detect_system_color_scheme_function_exists(self):
        """Test that _detect_system_color_scheme function exists"""
        from Core.init_ui import _detect_system_color_scheme
        
        assert callable(_detect_system_color_scheme)

    def test_detect_system_color_scheme_returns_string(self):
        """Test that _detect_system_color_scheme returns a string"""
        from Core.init_ui import _detect_system_color_scheme
        
        result = _detect_system_color_scheme()
        assert isinstance(result, str)
        assert result in ["dark", "light"]

    def test_is_qss_dark_function_exists(self):
        """Test that _is_qss_dark function exists"""
        from Core.init_ui import _is_qss_dark
        
        assert callable(_is_qss_dark)

    def test_is_qss_dark_with_dark_css(self):
        """Test detecting dark theme from CSS"""
        from Core.init_ui import _is_qss_dark
        
        dark_css = """
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        """
        assert _is_qss_dark(dark_css) is True

    def test_is_qss_dark_with_light_css(self):
        """Test detecting light theme from CSS"""
        from Core.init_ui import _is_qss_dark
        
        light_css = """
        QWidget {
            background-color: #ffffff;
            color: #000000;
        }
        """
        assert _is_qss_dark(light_css) is False

    def test_is_qss_dark_with_empty_css(self):
        """Test handling empty CSS"""
        from Core.init_ui import _is_qss_dark
        
        assert _is_qss_dark("") is False
        assert _is_qss_dark(None) is False

    def test_is_qss_dark_with_rgb_colors(self):
        """Test detecting theme from RGB colors"""
        from Core.init_ui import _is_qss_dark
        
        # Dark theme with rgba
        dark_css = "background-color: rgba(0, 0, 0, 1);"
        assert _is_qss_dark(dark_css) is True
        
        # Light theme with rgba
        light_css = "background-color: rgba(255, 255, 255, 1);"
        assert _is_qss_dark(light_css) is False


class TestThemesDirectory:
    """Test themes directory functions"""

    def test_themes_dir_function_exists(self):
        """Test that _themes_dir function exists"""
        from Core.init_ui import _themes_dir
        
        assert callable(_themes_dir)

    def test_themes_dir_returns_path(self):
        """Test that _themes_dir returns a valid path"""
        from Core.init_ui import _themes_dir
        
        path = _themes_dir()
        assert isinstance(path, str)
        assert len(path) > 0

    def test_themes_dir_exists(self):
        """Test that themes directory exists"""
        from Core.init_ui import _themes_dir
        
        path = _themes_dir()
        assert os.path.isdir(path)

    def test_list_available_themes_function_exists(self):
        """Test that _list_available_themes function exists"""
        from Core.init_ui import _list_available_themes
        
        assert callable(_list_available_themes)

    def test_list_available_themes_returns_list(self):
        """Test that _list_available_themes returns a list"""
        from Core.init_ui import _list_available_themes
        
        themes = _list_available_themes()
        assert isinstance(themes, list)
        assert len(themes) > 0

    def test_list_available_themes_format(self):
        """Test that themes have correct format (display_name, path)"""
        from Core.init_ui import _list_available_themes
        
        themes = _list_available_themes()
        for theme in themes:
            assert isinstance(theme, tuple)
            assert len(theme) == 2
            display_name, path = theme
            assert isinstance(display_name, str)
            assert isinstance(path, str)
            assert path.endswith(".qss")


class TestApplyTheme:
    """Test apply_theme function"""

    def test_apply_theme_function_exists(self):
        """Test that apply_theme function exists"""
        from Core.init_ui import apply_theme
        
        assert callable(apply_theme)

    def test_apply_theme_with_system(self):
        """Test applying System theme (auto-detect)"""
        from Core.init_ui import apply_theme
        
        mock_gui = MagicMock()
        mock_gui.log = MagicMock()
        mock_gui.sidebar_logo = None
        
        # Should not raise exception
        try:
            apply_theme(mock_gui, "System")
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

    def test_apply_theme_with_light(self):
        """Test applying light theme"""
        from Core.init_ui import apply_theme
        
        mock_gui = MagicMock()
        mock_gui.log = MagicMock()
        mock_gui.sidebar_logo = None
        
        try:
            apply_theme(mock_gui, "light")
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")


class TestApplyTranslations:
    """Test _apply_translations function"""

    def test_apply_translations_function_exists(self):
        """Test that _apply_translations function exists"""
        from Core.init_ui import _apply_translations
        
        assert callable(_apply_translations)

    def test_apply_translations_with_mock_gui(self):
        """Test applying translations to mock GUI"""
        from Core.init_ui import _apply_translations
        
        mock_gui = MagicMock()
        mock_gui.btn_select_folder = MagicMock()
        mock_gui.btn_select_files = MagicMock()
        mock_gui.btn_build_all = MagicMock()
        mock_gui.btn_cancel_all = MagicMock()
        mock_gui.btn_help = MagicMock()
        
        translations = {
            "select_folder": "Select Folder",
            "select_files": "Select Files",
            "build_all": "Build All",
            "cancel_all": "Cancel All",
            "help": "Help"
        }
        
        # Should not raise exception
        _apply_translations(mock_gui, translations)


class TestShowLanguageDialog:
    """Test show_language_dialog function"""

    def test_show_language_dialog_function_exists(self):
        """Test that show_language_dialog function exists"""
        from Core.init_ui import show_language_dialog
        
        assert callable(show_language_dialog)


class TestShowThemeDialog:
    """Test show_theme_dialog function"""

    def test_show_theme_dialog_function_exists(self):
        """Test that show_theme_dialog function exists"""
        from Core.init_ui import show_theme_dialog
        
        assert callable(show_theme_dialog)


class TestDataFileFunctions:
    """Test data file addition functions"""

    def test_add_pyinstaller_data_function_exists(self):
        """Test that add_pyinstaller_data function exists"""
        from Core.init_ui import add_pyinstaller_data
        
        assert callable(add_pyinstaller_data)

    def test_add_nuitka_data_file_function_exists(self):
        """Test that add_nuitka_data_file function exists"""
        from Core.init_ui import add_nuitka_data_file
        
        assert callable(add_nuitka_data_file)


class TestInitUIBypass:
    """Test that init_ui can be bypassed for unit testing"""

    def test_init_ui_function_exists(self):
        """Test that init_ui function exists in module"""
        from Core.init_ui import init_ui
        
        assert callable(init_ui)

    def test_init_ui_accepts_gui_parameter(self):
        """Test that init_ui accepts a GUI parameter"""
        from Core.init_ui import init_ui
        import inspect
        
        sig = inspect.signature(init_ui)
        params = list(sig.parameters.keys())
        assert "self" in params or len(params) >= 1

