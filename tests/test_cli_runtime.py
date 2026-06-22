# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

        # We expect it to fallback to ~/.pycompiler_ark/logs
        log_dir = _platform_log_dir()
        expected = Path("~/.pycompiler_ark/logs").expanduser()
        self.assertEqual(log_dir, expected)


if __name__ == "__main__":
    unittest.main()
