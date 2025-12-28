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
PyCompiler ARK++ — cx_Freeze Build Script
Automated build configuration for creating standalone executables with cx_Freeze.
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
PROJECT_NAME = "PyCompiler-ARK"
MAIN_SCRIPT = "pycompiler_ark.py"
VERSION = "1.0.0"
DESCRIPTION = "Python Compilation Toolkit"

# Build configuration
BUILD_CONFIG = {
    # Basic options
    "build_exe": "build/cxfreeze",
    
    # Include files (source:destination)
    "include_files": [
        ("themes", "themes"),
        ("languages", "languages"),
        ("logo", "logo"),
        ("ui", "ui"),
        ("Plugins", "Plugins"),
        ("ENGINES", "ENGINES"),
    ],
    
    # Packages to include
    "packages": [
        "PySide6",
        "shiboken6",
        "psutil",
        "yaml",
        "PIL",
        "jsonschema",
        "multiprocessing",
        "faulthandler",
        "Core",
        "engine_sdk",
        "ENGINES",
        "bcasl",
        "Plugins_SDK",
    ],
    
    # Modules to include
    "includes": [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtUiTools",
    ],
    
    # Modules to exclude
    "excludes": [
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "IPython",
        "notebook",
        "jupyter",
        "pytest",
        "unittest",
        "test",
    ],
    
    # Optimization level (0, 1, or 2)
    "optimize": 2,
    
    # Silent mode
    "silent": False,
}


def check_cxfreeze_installed():
    """Check if cx_Freeze is installed."""
    try:
        import cx_Freeze
        return True
    except ImportError:
        return False


def install_cxfreeze():
    """Install cx_Freeze if not already installed."""
    print("📦 Installing cx_Freeze...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "cx_Freeze"],
            check=True,
        )
        print("✅ cx_Freeze installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install cx_Freeze: {e}")
        return False


def create_setup_script():
    """Create setup.py for cx_Freeze."""
    
    # Build include_files list
    include_files_str = ",\n        ".join(
        [f'("{src}", "{dest}")' for src, dest in BUILD_CONFIG["include_files"]]
    )
    
    # Build packages list
    packages_str = ",\n        ".join([f'"{pkg}"' for pkg in BUILD_CONFIG["packages"]])
    
    # Build includes list
    includes_str = ",\n        ".join([f'"{mod}"' for mod in BUILD_CONFIG["includes"]])
    
    # Build excludes list
    excludes_str = ",\n        ".join([f'"{mod}"' for mod in BUILD_CONFIG["excludes"]])
    
    setup_content = f'''# SPDX-License-Identifier: Apache-2.0
# PyCompiler ARK++ - cx_Freeze Setup Script

import sys
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {{
    "build_exe": "{BUILD_CONFIG["build_exe"]}",
    "packages": [
        {packages_str}
    ],
    "includes": [
        {includes_str}
    ],
    "excludes": [
        {excludes_str}
    ],
    "include_files": [
        {include_files_str}
    ],
    "optimize": {BUILD_CONFIG["optimize"]},
}}

# GUI applications require a different base on Windows
base = None
if sys.platform == "win32":
    # Use "Win32GUI" to hide console, None to show console
    base = None  # Change to "Win32GUI" for GUI-only mode

setup(
    name="{PROJECT_NAME}",
    version="{VERSION}",
    description="{DESCRIPTION}",
    options={{"build_exe": build_exe_options}},
    executables=[
        Executable(
            "{MAIN_SCRIPT}",
            base=base,
            target_name="{PROJECT_NAME}",
            icon="logo/logo.png" if sys.platform == "win32" else None,
        )
    ],
)
'''
    
    with open("setup_cxfreeze.py", "w", encoding="utf-8") as f:
        f.write(setup_content)
    
    print("✅ Created setup_cxfreeze.py")
    return "setup_cxfreeze.py"


def main():
    """Main build function."""
    print("=" * 70)
    print(f"🚀 Building {PROJECT_NAME} with cx_Freeze")
    print("=" * 70)
    
    # Check if main script exists
    if not os.path.exists(MAIN_SCRIPT):
        print(f"❌ Error: Main script '{MAIN_SCRIPT}' not found!")
        return 1
    
    # Check cx_Freeze installation
    if not check_cxfreeze_installed():
        print("⚠️  cx_Freeze is not installed")
        if not install_cxfreeze():
            return 1
    
    # Create setup script
    setup_script = create_setup_script()
    
    # Display build configuration
    print("\n📋 Build Configuration:")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Main script: {MAIN_SCRIPT}")
    print(f"  Output directory: {BUILD_CONFIG['build_exe']}")
    print(f"  Optimization level: {BUILD_CONFIG['optimize']}")
    
    # Build command
    cmd = [sys.executable, setup_script, "build_exe"]
    if BUILD_CONFIG.get("silent"):
        cmd.append("--silent")
    
    print("\n🔧 Build Command:")
    print(" ".join(cmd))
    
    # Run build
    print("\n🏗️  Starting build process...\n")
    try:
        result = subprocess.run(cmd, check=True)
        
        print("\n" + "=" * 70)
        print("✅ Build completed successfully!")
        print("=" * 70)
        
        # Display output location
        print(f"\n📦 Application created in: {BUILD_CONFIG['build_exe']}/")
        
        os_name = platform.system()
        if os_name == "Windows":
            exe_name = f"{PROJECT_NAME}.exe"
        else:
            exe_name = PROJECT_NAME
        
        exe_path = os.path.join(BUILD_CONFIG['build_exe'], exe_name)
        if os.path.exists(exe_path):
            print(f"   Executable: {exe_path}")
        
        print("\n💡 To run the application:")
        print(f"   cd {BUILD_CONFIG['build_exe']}")
        print(f"   ./{exe_name}")
        
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