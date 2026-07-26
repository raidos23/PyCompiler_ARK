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
from unittest.mock import MagicMock, patch

from pycompiler_ark.Core.utils.ensure_tools import (
    ToolsCheckResult,
    ensure_tools,
)


class TestEnsureToolsGui(unittest.TestCase):
    @patch("pycompiler_ark.Core.Compiler.utils.check_internet_connection")
    @patch("pycompiler_ark.Core.SystemDepsManager.check_system_packages")
    def test_ensure_tools_gui_system_success(
        self, mock_check_sys, mock_check_net
    ):
        # Setup mock GUI
        mock_gui = MagicMock()
        mock_sys_manager = MagicMock()
        mock_gui.sys_deps_manager = mock_sys_manager

        # Linux platform setup
        mock_process = MagicMock()
        mock_process.waitForFinished.return_value = True
        mock_process.exitCode.return_value = 0
        mock_sys_manager.install_packages_linux.return_value = mock_process

        mock_check_net.return_value = True
        mock_check_sys.side_effect = lambda tools: (
            False
        )  # package gcc is missing

        required = {"system": ["gcc"]}

        with patch("platform.system", return_value="Linux"):
            res = ensure_tools(required, gui=mock_gui)

            # Assert result ok, because installation succeeded
            self.assertTrue(res.ok)
            self.assertEqual(res.missing_system, [])
            mock_sys_manager.install_packages_linux.assert_called_once_with(
                ["gcc"]
            )

    @patch("pycompiler_ark.Core.Compiler.utils.check_internet_connection")
    def test_ensure_tools_gui_python_venv_success(self, mock_check_net):
        mock_gui = MagicMock()
        mock_venv_manager = MagicMock()
        mock_gui.venv_manager = mock_venv_manager
        mock_gui.use_system_python = False

        mock_venv_manager.resolve_project_venv.return_value = "/fake/venv"

        # First check returns False, second check (after wait loop) returns True
        mock_venv_manager.is_tool_installed.side_effect = [False, True]

        mock_check_net.return_value = True

        required = {"python": ["black"]}

        res = ensure_tools(required, gui=mock_gui)

        self.assertTrue(res.ok)
        mock_venv_manager.ensure_tools_installed.assert_called_once_with(
            "/fake/venv", ["black"]
        )

    @patch("pycompiler_ark.Core.Compiler.utils.check_internet_connection")
    def test_ensure_tools_gui_python_system_success(self, mock_check_net):
        mock_gui = MagicMock()
        mock_venv_manager = MagicMock()
        mock_gui.venv_manager = mock_venv_manager
        mock_gui.use_system_python = True

        mock_venv_manager.is_tool_installed_system.side_effect = [False, True]
        mock_check_net.return_value = True

        required = {"python": ["black"]}

        res = ensure_tools(required, gui=mock_gui)

        self.assertTrue(res.ok)
        mock_venv_manager.ensure_tools_installed_system.assert_called_once_with(
            ["black"]
        )


if __name__ == "__main__":
    unittest.main()
