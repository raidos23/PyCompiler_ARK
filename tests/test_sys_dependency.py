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

import platform
import shutil
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QProcess

from pycompiler_ark.Core.SysDepsManager import SysDepsManager
from pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI import SysDependencyUI


class TestSysDepsManager:
    @patch("shutil.which")
    def test_detect_linux_package_manager(self, mock_which):
        mock_which.side_effect = lambda x: (
            "/usr/bin/" + x if x == "apt" else None
        )
        manager = SysDepsManager()
        assert manager.detect_linux_package_manager() == "apt"

    @patch("platform.system", return_value="Linux")
    @patch.object(QProcess, "start")
    def test_run_elevated_shell_linux(self, mock_start, mock_system):
        manager = SysDepsManager()
        # Mocking shell_run because QProcess start is tricky to mock directly with args
        with patch.object(manager, "shell_run") as mock_shell_run:
            manager.run_elevated_shell("apt-get update")
            mock_shell_run.assert_called_once()
            args = mock_shell_run.call_args[0]
            assert "pkexec bash -lc 'apt-get update'" in args[0]

    @patch("platform.system", return_value="Windows")
    def test_run_elevated_shell_windows(self, mock_system):
        manager = SysDepsManager()
        with patch.object(manager, "shell_run") as mock_shell_run:
            manager.run_elevated_shell("winget install dummy")
            mock_shell_run.assert_called_once_with(
                "winget install dummy", None, None, None
            )


class TestSysDependencyUI:
    @patch("pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI.ProgressDialog")
    @patch("platform.system", return_value="Linux")
    @patch(
        "pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI.SysDependencyUI.get_install_command",
        return_value="apt install -y gcc make",
    )
    @patch.object(SysDependencyUI, "run_elevated_shell")
    def test_install_packages_linux(
        self, mock_elevated, mock_get_cmd, mock_system, mock_dlg
    ):
        ui = SysDependencyUI()
        ui.install_packages_linux(["gcc", "make"])

        mock_elevated.assert_called_once()
        cmd = mock_elevated.call_args[0][0]
        assert "apt install -y gcc make" in cmd

    @patch("pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI.ProgressDialog")
    @patch("shutil.which", return_value="/usr/bin/winget")
    @patch("platform.system", return_value="Windows")
    @patch.object(SysDependencyUI, "shell_run")
    def test_install_packages_windows(
        self, mock_shell_run, mock_system, mock_which, mock_dlg
    ):
        ui = SysDependencyUI()
        ui.install_packages_windows(
            [{"id": "Git.Git"}, {"id": "Python.Python.3"}]
        )

        mock_shell_run.assert_called_once()
        cmd = mock_shell_run.call_args[0][0]
        assert "winget install --id Git.Git" in cmd
        assert "&&" in cmd
        assert "winget install --id Python.Python.3" in cmd

    @patch("shutil.which", return_value=None)
    @patch.object(SysDependencyUI, "msg_error")
    def test_install_packages_windows_no_winget(self, mock_error, mock_which):
        ui = SysDependencyUI()
        ui.install_packages_windows([{"id": "Git.Git"}])
        mock_error.assert_called_once()
