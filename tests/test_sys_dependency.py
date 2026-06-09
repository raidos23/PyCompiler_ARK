# SPDX-License-Identifier: Apache-2.0
import platform
import shutil
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QProcess

from pycompiler_ark.Core.SysDependencyManager import SysDependencyManager
from pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI import SysDependencyUI


class TestSysDependencyManager:
    @patch("shutil.which")
    def test_detect_linux_package_manager(self, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/" + x if x == "apt" else None
        manager = SysDependencyManager()
        assert manager.detect_linux_package_manager() == "apt"

    @patch("platform.system", return_value="Linux")
    @patch.object(QProcess, "start")
    def test_run_elevated_shell_linux(self, mock_start, mock_system):
        manager = SysDependencyManager()
        # Mocking shell_run because QProcess start is tricky to mock directly with args
        with patch.object(manager, "shell_run") as mock_shell_run:
            manager.run_elevated_shell("apt-get update")
            mock_shell_run.assert_called_once()
            args = mock_shell_run.call_args[0]
            assert "pkexec bash -lc 'apt-get update'" in args[0]

    @patch("platform.system", return_value="Windows")
    def test_run_elevated_shell_windows(self, mock_system):
        manager = SysDependencyManager()
        with patch.object(manager, "shell_run") as mock_shell_run:
            manager.run_elevated_shell("winget install dummy")
            mock_shell_run.assert_called_once_with("winget install dummy", None, None, None)


class TestSysDependencyUI:
    @patch("pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI.ProgressDialog")
    @patch("platform.system", return_value="Linux")
    @patch.object(SysDependencyUI, "detect_linux_package_manager", return_value="apt")
    @patch.object(SysDependencyUI, "run_elevated_shell")
    def test_install_packages_linux(self, mock_elevated, mock_detect, mock_system, mock_dlg):
        ui = SysDependencyUI()
        ui.install_packages_linux(["gcc", "make"])
        
        mock_elevated.assert_called_once()
        cmd = mock_elevated.call_args[0][0]
        assert "apt install -y gcc make" in cmd

    @patch("pycompiler_ark.Ui.Gui.Dialogs.SysDependencyUI.ProgressDialog")
    @patch("shutil.which", return_value="/usr/bin/winget")
    @patch("platform.system", return_value="Windows")
    @patch.object(SysDependencyUI, "shell_run")
    def test_install_packages_windows(self, mock_shell_run, mock_system, mock_which, mock_dlg):
        ui = SysDependencyUI()
        ui.install_packages_windows([{"id": "Git.Git"}, {"id": "Python.Python.3"}])
        
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
