# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch, MagicMock
from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager


class TestVenvManagerInternet(unittest.TestCase):

    def setUp(self):
        # Create a mock parent
        self.mock_parent = MagicMock()
        self.manager = VenvManager(self.mock_parent)
        # Mock log_i18n and _call_ui to avoid side effects
        self.manager.log_i18n = MagicMock()
        self.manager._call_ui = MagicMock()

    @patch("pycompiler_ark.Core.Compiler.utils.check_internet_connection")
    def test_ensure_tools_installed_no_internet(self, mock_check):
        mock_check.return_value = False
        self.manager._reset_cancel_state = MagicMock()

        self.manager.ensure_tools_installed("/fake/venv", ["tool"])

        # Should log error and return early
        self.manager.log_i18n.assert_called_with(
            "🛑 [ERROR] Pas de connexion internet. Installation des outils annulée.",
            "🛑 [ERROR] No internet connection. Tool installation cancelled.",
            level="error",
        )
        # Verify _reset_cancel_state was NOT called (it's the next line after the check)
        self.assertFalse(self.manager._reset_cancel_state.called)

    @patch("pycompiler_ark.Core.Compiler.utils.check_internet_connection")
    def test_ensure_tools_installed_system_no_internet(self, mock_check):
        mock_check.return_value = False
        self.manager._reset_cancel_state = MagicMock()

        self.manager.ensure_tools_installed_system(["tool"])

        self.manager.log_i18n.assert_called_with(
            "🛑 [ERROR] Pas de connexion internet. Installation système annulée.",
            "🛑 [ERROR] No internet connection. System installation cancelled.",
            level="error",
        )
        self.assertFalse(self.manager._reset_cancel_state.called)


if __name__ == "__main__":
    unittest.main()
