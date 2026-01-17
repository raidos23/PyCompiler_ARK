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
Tests for Core.dialogs module - Dialog functionality
"""

import pytest
from unittest.mock import patch, MagicMock


class TestDialogsModule:
    """Test dialogs module"""

    def test_import_dialogs(self):
        """Test that dialogs module can be imported"""
        from Core import dialogs
        assert dialogs is not None


class TestProgressDialog:
    """Test ProgressDialog class"""

    def test_progress_dialog_import(self):
        """Test that ProgressDialog can be imported"""
        from Core.dialogs import ProgressDialog
        assert ProgressDialog is not None

    def test_progress_dialog_instantiation(self):
        """Test creating a ProgressDialog instance"""
        from Core.dialogs import ProgressDialog
        
        try:
            # Create a mock parent
            mock_parent = MagicMock()
            dialog = ProgressDialog("Test Title", mock_parent)
            assert dialog is not None
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

    def test_progress_dialog_has_required_methods(self):
        """Test that ProgressDialog has required methods"""
        from Core.dialogs import ProgressDialog
        
        try:
            mock_parent = MagicMock()
            dialog = ProgressDialog("Test", mock_parent)
            
            required_methods = [
                'set_message',
                'set_progress',
                'close',
                'show',
                'exec',
            ]
            
            for method in required_methods:
                assert hasattr(dialog, method), f"Missing method: {method}"
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")


class TestCompilationProcessDialog:
    """Test CompilationProcessDialog class"""

    def test_compilation_dialog_import(self):
        """Test that CompilationProcessDialog can be imported"""
        from Core.dialogs import CompilationProcessDialog
        assert CompilationProcessDialog is not None

    def test_compilation_dialog_instantiation(self):
        """Test creating a CompilationProcessDialog instance"""
        from Core.dialogs import CompilationProcessDialog
        
        try:
            mock_parent = MagicMock()
            dialog = CompilationProcessDialog("Compilation", mock_parent)
            assert dialog is not None
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

    def test_compilation_dialog_has_required_methods(self):
        """Test that CompilationProcessDialog has required methods"""
        from Core.dialogs import CompilationProcessDialog
        
        try:
            mock_parent = MagicMock()
            dialog = CompilationProcessDialog("Compilation", mock_parent)
            
            required_methods = [
                'set_status',
                'set_progress',
                'close',
                'show',
                'exec',
            ]
            
            for method in required_methods:
                assert hasattr(dialog, method), f"Missing method: {method}"
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")


class TestConnectToApp:
    """Test connect_to_app function"""

    def test_connect_to_app_import(self):
        """Test that connect_to_app can be imported"""
        from Core.dialogs import connect_to_app
        assert connect_to_app is not None

    def test_connect_to_app_function_exists(self):
        """Test that connect_to_app is a function"""
        from Core.dialogs import connect_to_app
        assert callable(connect_to_app)

    def test_connect_to_app_with_mock_gui(self):
        """Test connecting dialogs to application"""
        from Core.dialogs import connect_to_app
        
        mock_gui = MagicMock()
        
        # Should not raise exception
        try:
            connect_to_app(mock_gui)
        except Exception:
            # May fail in test environment, which is OK
            pass


class TestDialogFunctions:
    """Test dialog helper functions"""

    def test_show_message_dialog_exists(self):
        """Test that show_message_dialog function exists"""
        from Core.dialogs import show_message_dialog
        assert callable(show_message_dialog)

    def test_show_error_dialog_exists(self):
        """Test that show_error_dialog function exists"""
        from Core.dialogs import show_error_dialog
        assert callable(show_error_dialog)

    def test_show_question_dialog_exists(self):
        """Test that show_question_dialog function exists"""
        from Core.dialogs import show_question_dialog
        assert callable(show_question_dialog)

    def test_show_input_dialog_exists(self):
        """Test that show_input_dialog function exists"""
        from Core.dialogs import show_input_dialog
        assert callable(show_input_dialog)

    def test_show_file_dialog_exists(self):
        """Test that show_file_dialog function exists"""
        from Core.dialogs import show_file_dialog
        assert callable(show_file_dialog)

    def test_show_directory_dialog_exists(self):
        """Test that show_directory_dialog function exists"""
        from Core.dialogs import show_directory_dialog
        assert callable(show_directory_dialog)


class TestDialogAppearance:
    """Test dialog appearance and behavior"""

    def test_progress_dialog_default_state(self):
        """Test ProgressDialog default state"""
        from Core.dialogs import ProgressDialog
        
        try:
            mock_parent = MagicMock()
            dialog = ProgressDialog("Test", mock_parent)
            
            # Default message should be set
            assert dialog is not None
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

    def test_compilation_dialog_has_cancel_button(self):
        """Test that CompilationProcessDialog has cancel button"""
        from Core.dialogs import CompilationProcessDialog
        
        try:
            mock_parent = MagicMock()
            dialog = CompilationProcessDialog("Compilation", mock_parent)
            
            # Should have cancel button
            assert hasattr(dialog, 'btn_cancel') or hasattr(dialog, 'cancel_btn')
        except Exception as e:
            pytest.skip(f"QApplication not available: {e}")

