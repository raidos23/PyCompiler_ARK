# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import MagicMock, patch

from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager
from pycompiler_ark.Ui import output


class TestVenvManagerInternet(unittest.TestCase):
    def setUp(self):
        # Create a mock parent
        self.mock_parent = MagicMock()
        self.manager = VenvManager(self.mock_parent)
        # Avoid rendering side effects
        self.output_error = patch.object(output, "error").start()
        self.addCleanup(patch.stopall)

    @patch("pycompiler_ark.Core.utils.check_internet_connection")
    def test_ensure_tools_installed_no_internet(self, mock_check):
        mock_check.return_value = False
        self.manager._reset_cancel_state = MagicMock()

        self.manager.ensure_tools_installed("/fake/venv", ["tool"])

        # Should emit a localized error and return early
        self.output_error.assert_called_with(
            "Pas de connexion internet. Installation des outils annulée.",
            "No internet connection. Tool installation cancelled.",
        )
        # Verify _reset_cancel_state was NOT called (it's the next line after the check)
        self.assertFalse(self.manager._reset_cancel_state.called)

    @patch("pycompiler_ark.Core.utils.check_internet_connection")
    def test_ensure_tools_installed_system_no_internet(self, mock_check):
        mock_check.return_value = False
        self.manager._reset_cancel_state = MagicMock()

        self.manager.ensure_tools_installed_system(["tool"])

        self.output_error.assert_called_with(
            "Pas de connexion internet. Installation système annulée.",
            "No internet connection. System installation cancelled.",
        )
        self.assertFalse(self.manager._reset_cancel_state.called)


if __name__ == "__main__":
    unittest.main()
