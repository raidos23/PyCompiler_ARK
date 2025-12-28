#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2025 Ague Samuel Amen
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
PyCompiler ARK++ — Pynsist Build Script
Automated build configuration for creating Windows standalone installers with pynsist.
Note: pynsist is Windows-only and creates installers that include Python itself.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

# Import build utilities
try:
    from build_utils import DependencyAnalyzer, check_dependencies
except ImportError:
    print("⚠️  build_utils.py not found. Creating minimal configuration...")
    DependencyAnalyzer = None
    check_dependencies = None

# Project configuration
PROJECT_NAME = "PyCompiler ARK++"
APP_NAME = "PyCompiler-ARK"
VERSION = "1.0.0"
PUBLISHER = "PyCompiler"
INSTALLER_NAME = "PyCompiler-ARK-Setup"

# Build configuration
BUILD_CONFIG = {
    # Python version to bundle (must be 3.x)
    "python_version": "3.10.11",
    
    # Application entry point
    "entry_point": "pycompiler_ark:main",
    
    # Console or GUI application
    "console": True,  # Set to False to hide console
    
    # Icon file (must be .ico for Windows)
    "icon": "logo/logo.ico" if os.path.exists("logo/logo.ico") else None,
    
    # License file
    "license": "LICENSE" if os.path.exists("LICENSE") else None,
    
    # Python packages to include
    "packages": [
        "PySide6",
        "shiboken6",
        "psutil",
        "yaml",
        "PIL",
        "jsonschema",
    ],
    
    # Additional files to include
    "files": [
        "main.py",
        "pycompiler_ark.py",
        "Core",
        "engine_sdk",
        "bcasl",
        "Plugins_SDK",
        "themes",
        "languages",
        "logo",
        "ui",
        "Plugins",
        "ENGINES",
    ],
    
    # Exclude patterns (pynsist will skip these)
    "exclude": [
        "*.pyc",
        "__pycache__",
        "*.git*",
        ".venv",
        "build",
        "dist",
        "*.egg-info",
        "tests",
        "Tests",
    ],
}


def check_platform():
    """Check if running on Windows."""
    if platform.system() != "Windows":
        print("⚠️  Warning: pynsist is designed for Windows installers.")
        print("   You can create the configuration, but building will fail.")
        print("   Consider using Briefcase or cx_Freeze for cross-platform builds.")
        response = input("\nContinue anyway to create configuration? (y/N): ")
        if response.lower() != 'y':
            return False
    return True


def check_pynsist_installed():
    """Check if pynsist is installed."""
    try:
        subprocess.run(
            ["pynsist", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_pynsist():
    """Install pynsist if not already installed."""
    print("📦 Installing pynsist...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pynsist"],
            check=True,
        )
        print("✅ pynsist installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install pynsist: {e}")
        return False


def check_nsis_installed():
    """Check if NSIS is installed (required for pynsist)."""
    try:
        result = subprocess.run(
            ["makensis", "/VERSION"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_installer_cfg():
    """Create installer.cfg configuration file for pynsist."""
    
    # Build packages list
    packages_list = "\n    ".join(BUILD_CONFIG["packages"])
    
    # Build files list
    files_list = "\n    ".join(BUILD_CONFIG["files"])
    
    # Build exclude patterns
    exclude_list = "\n    ".join(BUILD_CONFIG["exclude"])
    
    cfg_content = f'''# PyCompiler ARK++ - Pynsist Configuration File
# This file configures the Windows installer created by pynsist

[Application]
name = {PROJECT_NAME}
version = {VERSION}
entry_point = {BUILD_CONFIG["entry_point"]}
console = {'true' if BUILD_CONFIG["console"] else 'false'}
icon = {BUILD_CONFIG["icon"] if BUILD_CONFIG["icon"] else ""}

[Python]
version = {BUILD_CONFIG["python_version"]}
format = bundled

# Include bitness if needed (32 or 64)
# bitness = 64

[Include]
# Python packages from PyPI
packages = 
    {packages_list}

# Local files and directories
files = 
    {files_list}

# Exclude patterns
exclude = 
    {exclude_list}

[Build]
# Output directory
installer_name = {INSTALLER_NAME}-{VERSION}.exe
'''
    
    # Add optional fields
    if BUILD_CONFIG.get("license"):
        cfg_content += f'''
[Installer]
license_file = {BUILD_CONFIG["license"]}
publisher = {PUBLISHER}
'''
    
    with open("installer.cfg", "w", encoding="utf-8") as f:
        f.write(cfg_content)
    
    print("✅ Created installer.cfg")


def main():
    """Main build function."""
    print("=" * 70)
    print(f"🚀 Building {PROJECT_NAME} Windows Installer with pynsist")
    print("=" * 70)
    
    # Check platform
    if not check_platform():
        return 1
    
    # Check pynsist installation
    if not check_pynsist_installed():
        print("⚠️  pynsist is not installed")
        if not install_pynsist():
            return 1
    
    # Check NSIS installation
    if not check_nsis_installed():
        print("\n⚠️  NSIS (Nullsoft Scriptable Install System) is not installed!")
        print("   pynsist requires NSIS to create Windows installers.")
        print("\n📥 Download NSIS from: https://nsis.sourceforge.io/Download")
        print("   Or install via chocolatey: choco install nsis")
        print("   Or via winget: winget install NSIS.NSIS")
        print("\nAfter installing NSIS, run this script again.")
        return 1
    
    # Create installer configuration
    create_installer_cfg()
    
    # Display build configuration
    print("\n📋 Build Configuration:")
    print(f"  Platform: Windows")
    print(f"  Python version: {BUILD_CONFIG['python_version']}")
    print(f"  Entry point: {BUILD_CONFIG['entry_point']}")
    print(f"  Console: {BUILD_CONFIG['console']}")
    print(f"  Output: {INSTALLER_NAME}-{VERSION}.exe")
    
    # Build command
    cmd = ["pynsist", "installer.cfg"]
    
    print("\n🔧 Build Command:")
    print(" ".join(cmd))
    
    # Run build
    print("\n🏗️  Starting build process...\n")
    print("⏳ This may take several minutes as pynsist downloads Python and dependencies...")
    
    try:
        result = subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 70)
        print("✅ Build completed successfully!")
        print("=" * 70)
        
        # Display output location
        installer_path = f"build/nsis/{INSTALLER_NAME}-{VERSION}.exe"
        print(f"\n📦 Windows Installer created: {installer_path}")
        print(f"\n💡 The installer includes:")
        print(f"   • Python {BUILD_CONFIG['python_version']}")
        print(f"   • All required packages")
        print(f"   • Your application files")
        print(f"\n🎯 Users can run the installer on any Windows machine")
        print(f"   No Python installation required!")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 70)
        print(f"❌ Build failed with error code {e.returncode}")
        print("=" * 70)
        print("\n💡 Common issues:")
        print("   • NSIS not installed or not in PATH")
        print("   • Missing icon file (must be .ico)")
        print("   • Invalid Python version specified")
        print("   • Network issues downloading Python/packages")
        return e.returncode
    except KeyboardInterrupt:
        print("\n\n⛔ Build cancelled by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())