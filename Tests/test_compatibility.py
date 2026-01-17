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
Tests for Core.compatibility module - System compatibility checks
"""

import os
import pytest
import platform
import sys
from unittest.mock import patch, MagicMock


class TestCompatibilityModule:
    """Test compatibility module functions"""

    def test_import_compatibility(self):
        """Test that compatibility module can be imported"""
        from Core import compatibility
        assert compatibility is not None


class TestPythonVersion:
    """Test Python version compatibility"""

    def test_python_version_check(self):
        """Test that Python version is 3.8 or higher"""
        from Core.compatibility import check_python_version, PYTHON_MIN_VERSION
        
        assert sys.version_info >= (3, 8)
        
        # check_python_version should return True for current version
        result = check_python_version()
        assert result is True

    def test_python_min_version_constant(self):
        """Test that PYTHON_MIN_VERSION is defined correctly"""
        from Core.compatibility import PYTHON_MIN_VERSION
        
        assert isinstance(PYTHON_MIN_VERSION, tuple)
        assert len(PYTHON_MIN_VERSION) == 2
        assert PYTHON_MIN_VERSION[0] == 3


class TestPlatformDetection:
    """Test platform detection functions"""

    def test_is_windows(self):
        """Test Windows detection"""
        from Core.compatibility import is_windows
        
        result = is_windows()
        assert isinstance(result, bool)
        assert result == (platform.system() == "Windows")

    def test_is_macos(self):
        """Test macOS detection"""
        from Core.compatibility import is_macos
        
        result = is_macos()
        assert isinstance(result, bool)
        assert result == (platform.system() == "Darwin")

    def test_is_linux(self):
        """Test Linux detection"""
        from Core.compatibility import is_linux
        
        result = is_linux()
        assert isinstance(result, bool)
        assert result == (platform.system() == "Linux")


class TestDependencyChecks:
    """Test dependency checking functions"""

    def test_check_pip_exists(self):
        """Test pip existence check"""
        from Core.compatibility import check_pip
        
        result = check_pip()
        assert isinstance(result, bool)
        # pip should exist in test environment

    def test_check_git_exists(self):
        """Test git existence check"""
        from Core.compatibility import check_git
        
        result = check_git()
        assert isinstance(result, bool)


class TestCompilerChecks:
    """Test compiler availability checks"""

    def test_check_pyinstaller(self):
        """Test PyInstaller availability check"""
        from Core.compatibility import check_pyinstaller
        
        result = check_pyinstaller()
        assert isinstance(result, bool)

    def test_check_nuitka(self):
        """Test Nuitka availability check"""
        from Core.compatibility import check_nuitka
        
        result = check_nuitka()
        assert isinstance(result, bool)

    def test_check_cx_freeze(self):
        """Test cx_Freeze availability check"""
        from Core.compatibility import check_cx_freeze
        
        result = check_cx_freeze()
        assert isinstance(result, bool)


class TestSystemInfo:
    """Test system information functions"""

    def test_get_system_info(self):
        """Test getting system information"""
        from Core.compatibility import get_system_info
        
        info = get_system_info()
        assert isinstance(info, dict)
        assert "platform" in info
        assert "python_version" in info

    def test_get_python_executable(self):
        """Test getting Python executable path"""
        from Core.compatibility import get_python_executable
        
        path = get_python_executable()
        assert isinstance(path, str)
        assert len(path) > 0
        assert os.path.exists(path) or "python" in path.lower()


class TestCompatibilityReport:
    """Test compatibility report generation"""

    def test_get_compatibility_report(self):
        """Test getting full compatibility report"""
        from Core.compatibility import get_compatibility_report
        
        report = get_compatibility_report()
        assert isinstance(report, dict)
        assert "python" in report
        assert "platform" in report
        assert "compilers" in report

    def test_compatibility_report_contains_all_checks(self):
        """Test that report contains all necessary checks"""
        from Core.compatibility import get_compatibility_report
        
        report = get_compatibility_report()
        
        # Check for expected keys
        expected_keys = ["python_version", "platform", "pip", "pyinstaller", "nuitka"]
        for key in expected_keys:
            assert key in report, f"Missing key: {key}"


class TestVersionComparison:
    """Test version comparison functions"""

    def test_version_parsing(self):
        """Test parsing version strings"""
        from Core.compatibility import parse_version
        
        version = parse_version("1.2.3")
        assert version == (1, 2, 3)
        
        version = parse_version("3.10.4")
        assert version == (3, 10, 4)

    def test_version_comparison(self):
        """Test comparing version strings"""
        from Core.compatibility import compare_versions
        
        assert compare_versions("1.0.0", "1.0.0") == 0
        assert compare_versions("2.0.0", "1.0.0") > 0
        assert compare_versions("1.0.0", "2.0.0") < 0

    def test_version_with_v_prefix(self):
        """Test parsing versions with 'v' prefix"""
        from Core.compatibility import parse_version
        
        version = parse_version("v1.2.3")
        assert version == (1, 2, 3)


class TestRequiredDependencies:
    """Test required dependency checking"""

    def test_get_required_dependencies(self):
        """Test getting list of required dependencies"""
        from Core.compatibility import get_required_dependencies
        
        deps = get_required_dependencies()
        assert isinstance(deps, list)
        assert len(deps) > 0

    def test_required_dependencies_format(self):
        """Test that required dependencies have correct format"""
        from Core.compatibility import get_required_dependencies
        
        deps = get_required_dependencies()
        for dep in deps:
            # Each dependency should have a name
            assert hasattr(dep, "name") or isinstance(dep, str)

    def test_required_compilers_list(self):
        """Test getting list of required compilers"""
        from Core.compatibility import get_required_compilers
        
        compilers = get_required_compilers()
        assert isinstance(compilers, list)
        # Should include at least pyinstaller and nuitka
        compiler_names = [c.lower() if isinstance(c, str) else c.__name__.lower() for c in compilers]
        assert "pyinstaller" in compiler_names or "pyinstaller" in str(compilers).lower()

