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
PyCompiler ARK++ — Briefcase Build Script
Automated build configuration for creating native installers with Briefcase.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

PROJECT_NAME = "PyCompiler ARK"
FORMAL_NAME = "PyCompiler-ARK"
APP_NAME = "pycompiler_ark"
BUNDLE_IDENTIFIER = "com.pycompiler.ark"


def check_briefcase_installed():
    """Check if Briefcase is installed."""
    try:
        subprocess.run(
            ["briefcase", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_briefcase():
    """Install Briefcase if not already installed."""
    print("📦 Installing Briefcase...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "briefcase"],
            check=True,
        )
        print("✅ Briefcase installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Briefcase: {e}")
        return False


def create_pyproject_toml():
    """Create pyproject.toml configuration for Briefcase."""
    pyproject_content = f'''[tool.briefcase]
project_name = "{PROJECT_NAME}"
bundle = "{BUNDLE_IDENTIFIER}"
version = "1.0.0"
url = "https://github.com/raidos23/PyCompiler-ARK-Professional"
license = "Apache-2.0"
author = "Ague Samuel Amen"
author_email = "your.email@example.com"

[tool.briefcase.app.{APP_NAME}]
formal_name = "{FORMAL_NAME}"
description = "Comprehensive Python compilation toolkit with modular architecture"
long_description = """PyCompiler ARK++ provides a modular, extensible platform for Python compilation with comprehensive tooling and security features."""
sources = [
    "pycompiler_ark.py",
    "main.py",
    "Core",
    "engine_sdk",
    "ENGINES",
    "bcasl",
    "Plugins_SDK",
]
requires = [
    "PySide6>=6.8.0",
    "shiboken6>=6.8.0",
    "psutil>=5.9.0",
    "PyYAML>=5.4.1",
    "jsonschema",
    "Pillow>=11.0.0",
]

[tool.briefcase.app.{APP_NAME}.macOS]
icon = "logo/logo"
installer_icon = "logo/logo"
requires = []

[tool.briefcase.app.{APP_NAME}.linux]
icon = "logo/logo"
requires = []
system_requires = [
    "libxcb-xinerama0",
    "libxcb-cursor0",
]

[tool.briefcase.app.{APP_NAME}.linux.system.debian]
system_requires = [
    "libxcb-xinerama0",
    "libxcb-cursor0",
    "libxcb-icccm4",
    "libxcb-image0",
    "libxcb-keysyms1",
    "libxcb-randr0",
    "libxcb-render-util0",
    "libxcb-render0",
    "libxcb-shape0",
    "libxcb-shm0",
    "libxcb-sync1",
    "libxcb-xfixes0",
]

[tool.briefcase.app.{APP_NAME}.windows]
icon = "logo/logo"
requires = []

# Support package configuration
[tool.briefcase.app.{APP_NAME}.support]
revision = "3.10"
'''
    
    with open("pyproject.toml", "w", encoding="utf-8") as f:
        f.write(pyproject_content)
    
    print("✅ Created pyproject.toml configuration")


def main():
    """Main build function."""
    print("=" * 70)
    print(f"🚀 Building {PROJECT_NAME} with Briefcase")
    print("=" * 70)
    
    # Check Briefcase installation
    if not check_briefcase_installed():
        print("⚠️  Briefcase is not installed")
        if not install_briefcase():
            return 1
    
    # Create pyproject.toml if it doesn't exist or ask to overwrite
    if os.path.exists("pyproject.toml"):
        print("\n⚠️  pyproject.toml already exists")
        response = input("Overwrite with Briefcase configuration? (y/N): ")
        if response.lower() == 'y':
            create_pyproject_toml()
    else:
        create_pyproject_toml()
    
    # Display build information
    print("\n📋 Build Configuration:")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  App Name: {APP_NAME}")
    print(f"  Bundle ID: {BUNDLE_IDENTIFIER}")
    
    # Build commands
    print("\n🏗️  Building application...\n")
    
    commands = [
        ("briefcase", "create"),    # Create scaffolding
        ("briefcase", "build"),     # Build the app
        ("briefcase", "package"),   # Create installer
    ]
    
    try:
        for cmd_name, cmd_action in commands:
            print(f"\n{'='*70}")
            print(f"📦 Running: {cmd_name} {cmd_action}")
            print(f"{'='*70}\n")
            
            result = subprocess.run(
                [cmd_name, cmd_action],
                check=True,
            )
        
        print("\n" + "=" * 70)
        print("✅ Build completed successfully!")
        print("=" * 70)
        
        # Display output location
        os_name = platform.system()
        if os_name == "Windows":
            print(f"\n📦 Installer created in: dist/")
            print(f"   Look for: {FORMAL_NAME}-1.0.0.msi")
        elif os_name == "Darwin":
            print(f"\n📦 App bundle created in: dist/")
            print(f"   Look for: {FORMAL_NAME}-1.0.0.dmg")
        elif os_name == "Linux":
            print(f"\n📦 Package created in: dist/")
            print(f"   Look for: {FORMAL_NAME}-1.0.0.AppImage")
        
        print("\nℹ️  You can also run the app without packaging:")
        print(f"   briefcase dev")
        print(f"   briefcase run")
        
        return 0
        
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 70)
        print(f"❌ Build failed with error code {e.returncode}")
        print("=" * 70)
        return e.returncode
    except KeyboardInterrupt:
        print("\n\n⛔ Build cancelled by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())