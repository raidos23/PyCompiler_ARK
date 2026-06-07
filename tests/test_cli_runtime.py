# SPDX-License-Identifier: Apache-2.0
import unittest
from unittest.mock import patch
from pathlib import Path

from pycompiler_ark.Ui.Cli.runtime import _platform_log_dir


class TestCliRuntime(unittest.TestCase):

    @patch("pycompiler_ark.Ui.PreferencesManager._user_config_dir")
    def test_platform_log_dir_from_prefs(self, mock_user_dir):
        mock_user_dir.return_value = "/tmp/fake_ark_home"
        log_dir = _platform_log_dir()
        self.assertEqual(log_dir, Path("/tmp/fake_ark_home/logs"))

    @patch("pycompiler_ark.Ui.PreferencesManager._user_config_dir")
    def test_platform_log_dir_fallback(self, mock_user_dir):
        # Simulate import error or exception
        mock_user_dir.side_effect = Exception("Import fail")

        # We expect it to fallback to ~/.PyCompiler_ARK/logs
        log_dir = _platform_log_dir()
        expected = Path("~/.PyCompiler_ARK/logs").expanduser()
        self.assertEqual(log_dir, expected)


if __name__ == "__main__":
    unittest.main()
