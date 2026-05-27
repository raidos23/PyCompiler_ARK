# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch, MagicMock
from Core.Venv_Manager.Manager import VenvManager

class TestVenvManagerInternet(unittest.TestCase):

    def setUp(self):
        # Create a mock parent
        self.mock_parent = MagicMock()
        self.manager = VenvManager(self.mock_parent)
        # Mock _safe_log and _call_ui to avoid side effects
        self.manager._safe_log = MagicMock()
        self.manager._call_ui = MagicMock()

    @patch("Core.Compiler.utils.check_internet_connection")
    def test_ensure_tools_installed_no_internet(self, mock_check):
        mock_check.return_value = False
        self.manager._reset_cancel_state = MagicMock()
        
        self.manager.ensure_tools_installed("/fake/venv", ["tool"])
        
        # Should log error and return early
        self.manager._safe_log.assert_called_with(
            "🛑 [ERROR] Pas de connexion internet. Installation des outils annulée.",
            "🛑 [ERROR] No internet connection. Tool installation cancelled.",
            level="error"
        )
        # Verify _reset_cancel_state was NOT called (it's the next line after the check)
        self.assertFalse(self.manager._reset_cancel_state.called)

    @patch("Core.Compiler.utils.check_internet_connection")
    def test_ensure_tools_installed_system_no_internet(self, mock_check):
        mock_check.return_value = False
        self.manager._reset_cancel_state = MagicMock()
        
        self.manager.ensure_tools_installed_system(["tool"])
        
        self.manager._safe_log.assert_called_with(
            "🛑 [ERROR] Pas de connexion internet. Installation système annulée.",
            "🛑 [ERROR] No internet connection. System installation cancelled.",
            level="error"
        )
        self.assertFalse(self.manager._reset_cancel_state.called)

if __name__ == "__main__":
    unittest.main()
