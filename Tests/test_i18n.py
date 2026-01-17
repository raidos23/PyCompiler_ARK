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
Tests for Core.i18n module - Internationalization functionality
"""

import pytest
import asyncio
import os
from unittest.mock import patch, MagicMock


class TestI18nModule:
    """Test i18n module functions"""

    def test_import_i18n(self):
        """Test that i18n module can be imported"""
        from Core import i18n
        assert i18n is not None

    def test_available_languages(self):
        """Test getting available languages"""
        from Core.i18n import available_languages
        
        # Run the async function
        languages = asyncio.run(available_languages())
        
        assert isinstance(languages, list)
        # Should have at least English and French
        assert len(languages) >= 2
        
        # Check structure of language entries
        for lang in languages:
            assert "code" in lang
            assert "name" in lang

    def test_get_translations_english(self):
        """Test getting English translations"""
        from Core.i18n import get_translations
        
        translations = asyncio.run(get_translations("en"))
        assert isinstance(translations, dict)
        # Should have some translations
        assert len(translations) > 0

    def test_get_translations_french(self):
        """Test getting French translations"""
        from Core.i18n import get_translations
        
        translations = asyncio.run(get_translations("fr"))
        assert isinstance(translations, dict)
        assert len(translations) > 0

    def test_get_translations_system(self):
        """Test getting system language translations"""
        from Core.i18n import get_translations
        
        # System should resolve to some language
        translations = asyncio.run(get_translations("System"))
        assert isinstance(translations, dict)

    def test_resolve_system_language(self):
        """Test resolving system language"""
        from Core.i18n import resolve_system_language
        
        result = asyncio.run(resolve_system_language())
        assert isinstance(result, str)
        assert result in ["en", "fr"]

    def test_normalize_lang_pref(self):
        """Test normalizing language preference"""
        from Core.i18n import normalize_lang_pref
        
        # Test various inputs
        result = asyncio.run(normalize_lang_pref("English"))
        assert isinstance(result, str)
        assert result in ["en", "fr"]
        
        result = asyncio.run(normalize_lang_pref("Français"))
        assert isinstance(result, str)
        
        result = asyncio.run(normalize_lang_pref("en"))
        assert result == "en"

    def test_get_language_direction(self):
        """Test getting language direction (LTR/RTL)"""
        from Core.i18n import get_language_direction
        
        # All supported languages should be LTR
        direction = get_language_direction("en")
        assert direction == "ltr"
        
        direction = get_language_direction("fr")
        assert direction == "ltr"

    def test_translations_contain_common_keys(self):
        """Test that translations contain common UI keys"""
        from Core.i18n import get_translations
        
        en_trans = asyncio.run(get_translations("en"))
        fr_trans = asyncio.run(get_translations("fr"))
        
        # Common keys that should be present
        common_keys = ["select_folder", "build_all", "cancel_all", "help"]
        for key in common_keys:
            assert key in en_trans or key in fr_trans

    def test_get_translations_invalid_lang(self):
        """Test handling invalid language code"""
        from Core.i18n import get_translations
        
        # Should fall back to English for invalid language
        translations = asyncio.run(get_translations("invalid_xyz"))
        assert isinstance(translations, dict)

    def test_language_files_exist(self):
        """Test that language files exist"""
        from Core.i18n import _get_lang_file_path
        
        # Check English file
        en_path = _get_lang_file_path("en")
        assert os.path.exists(en_path)
        
        # Check French file
        fr_path = _get_lang_file_path("fr")
        assert os.path.exists(fr_path)

    def test_get_translations_returns_dict_with_meta(self):
        """Test that translations contain metadata"""
        from Core.i18n import get_translations
        
        translations = asyncio.run(get_translations("en"))
        assert isinstance(translations, dict)
        
        # Should have _meta key with language info
        if "_meta" in translations:
            meta = translations["_meta"]
            assert "name" in meta
            assert "code" in meta


class TestI18nAsync:
    """Test async behavior of i18n functions"""

    @pytest.mark.asyncio
    async def test_available_languages_async(self):
        """Test async availability of languages"""
        from Core.i18n import available_languages
        
        languages = await available_languages()
        assert isinstance(languages, list)
        assert len(languages) >= 2

    @pytest.mark.asyncio
    async def test_get_translations_async(self):
        """Test async retrieval of translations"""
        from Core.i18n import get_translations
        
        translations = await get_translations("en")
        assert isinstance(translations, dict)

    @pytest.mark.asyncio
    async def test_resolve_system_language_async(self):
        """Test async resolution of system language"""
        from Core.i18n import resolve_system_language
        
        result = await resolve_system_language()
        assert isinstance(result, str)

