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
PyCompiler ARK++ — PyInstaller Build Script
Automated build configuration for creating standalone executables with PyInstaller.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

# Project configuration
PROJECT_NAME = "PyCompiler-ARK"
MAIN_SCRIPT = "pycompiler_ark.py"
OUTPUT_DIR = "dist"
BUILD_DIR = "build"

# Build configuration
BUILD_CONFIG = {
    # Main compilation options
    "onefile": True,
    "windowed": False,  # Set to True to hide console (GUI only)
    "noconfirm": True,  # Replace output directory without confirmation
    "clean": True,  # Clean PyInstaller cache before building
    
    # Output configuration
    "name": PROJECT_NAME,
    "distpath": OUTPUT_DIR,
    "workpath": BUILD_DIR,
    "specpath": ".",
    
    # Icon configuration
    "icon": "logo/logo.png" if os.path.exists("logo/logo.png") else None,
    
    # UPX compression
    "noupx": True,  # Disable UPX (can cause issues)
    
    # Add data files (source:destination)
    "add_data": [
        ("themes", "themes"),
        ("languages", "languages"),
        ("logo", "logo"),
        ("ui", "ui"),
    ],
    
    # Hidden imports (modules not automatically detected)
    "hidden_import": [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtUiTools",
        "psutil",
        "yaml",
        "PIL",
        "PIL.Image",
        "jsonschema",
        "multiprocessing",
        "faulthandler",
        "traceback",
        "pathlib",
    ],
    
    # Collect all submodules for these packages
    "collect_all": [
        "PySide6",
        "shiboken6",
    ],
    
    # Collect binary files for these packages
    "collect_binaries": [
        "PySide6",
    ],
    
    # Collect data files for these packages
    "collect_data": [
        "PySide6",
    ],
    
    # Runtime hooks
    "runtime_hook": [],
    
    # Exclude modules (reduce size)
    "exclude_module": [
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
    
    # Debugging options
    "debug": False,
    "console": True,  # Show console for debugging
    
    # Version info (Windows only)
    "version_file": None,  # Path to version file
}


def build_command():
    """Build the PyInstaller command from configuration."""
    cmd = ["pyinstaller"]
    
    # Main options
    if BUILD_CONFIG.get("onefile"):
        cmd.append("--onefile")
    if BUILD_CONFIG.get("windowed"):
        cmd.append("--windowed")
    if BUILD_CONFIG.get("noconfirm"):
        cmd.append("--noconfirm")
    if BUILD_CONFIG.get("clean"):
        cmd.append("--clean")
    if BUILD_CONFIG.get("noupx"):
        cmd.append("--noupx")
    
    # Output configuration
    if BUILD_CONFIG.get("name"):
        cmd.append(f"--name={BUILD_CONFIG['name']}")
    if BUILD_CONFIG.get("distpath"):
        cmd.append(f"--distpath={BUILD_CONFIG['distpath']}")
    if BUILD_CONFIG.get("workpath"):
        cmd.append(f"--workpath={BUILD_CONFIG['workpath']}")
    if BUILD_CONFIG.get("specpath"):
        cmd.append(f"--specpath={BUILD_CONFIG['specpath']}")
    
    # Icon
    if BUILD_CONFIG.get("icon"):
        cmd.append(f"--icon={BUILD_CONFIG['icon']}")
    
    # Add data files
    separator = ";" if platform.system() == "Windows" else ":"
    for src, dest in BUILD_CONFIG.get("add_data", []):
        if os.path.exists(src):
            cmd.append(f"--add-data={src}{separator}{dest}")
    
    # Hidden imports
    for module in BUILD_CONFIG.get("hidden_import", []):
        cmd.append(f"--hidden-import={module}")
    
    # Collect all
    for package in BUILD_CONFIG.get("collect_all", []):
        cmd.append(f"--collect-all={package}")
    
    # Collect binaries
    for package in BUILD_CONFIG.get("collect_binaries", []):
        cmd.append(f"--collect-binaries={package}")
    
    # Collect data
    for package in BUILD_CONFIG.get("collect_data", []):
        cmd.append(f"--collect-data={package}")
    
    # Runtime hooks
    for hook in BUILD_CONFIG.get("runtime_hook", []):
        if os.path.exists(hook):
            cmd.append(f"--runtime-hook={hook}")
    
    # Exclude modules
    for module in BUILD_CONFIG.get("exclude_module", []):
        cmd.append(f"--exclude-module={module}")
    
    # Debugging
    if BUILD_CONFIG.get("debug"):
        cmd.append("--debug=all")
    if not BUILD_CONFIG.get("console"):
        cmd.append("--noconsole")
    
    # Version file (Windows)
    if BUILD_CONFIG.get("version_file") and os.path.exists(BUILD_CONFIG["version_file"]):
        cmd.append(f"--version-file={BUILD_CONFIG['version_file']}")
    
    # Main script
    cmd.append(MAIN_SCRIPT)
    
    return cmd


def check_pyinstaller_installed():
    """Check if PyInstaller is installed."""
    try:
        subprocess.run(
            ["pyinstaller", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_pyinstaller():
    """Install PyInstaller if not already installed."""
    print("📦 Installing PyInstaller...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "pyinstaller"],
            check=True,
        )
        print("✅ PyInstaller installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyInstaller: {e}")
        return False


def main():
    """Main build function."""
    print("=" * 70)
    print(f"🚀 Building {PROJECT_NAME} with PyInstaller")
    print("=" * 70)
    
    # Check if main script exists
    if not os.path.exists(MAIN_SCRIPT):
        print(f"❌ Error: Main script '{MAIN_SCRIPT}' not found!")
        return 1
    
    # Check PyInstaller installation
    if not check_pyinstaller_installed():
        print("⚠️  PyInstaller is not installed")
        if not install_pyinstaller():
            return 1
    
    # Build command
    cmd = build_command()
    
    # Display build configuration
    print("\n📋 Build Configuration:")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Main script: {MAIN_SCRIPT}")
    print(f"  Output mode: {'Onefile' if BUILD_CONFIG.get('onefile') else 'Directory'}")
    print(f"  Output directory: {BUILD_CONFIG.get('distpath')}")
    print(f"  Console: {'Enabled' if BUILD_CONFIG.get('console') else 'Disabled'}")
    
    # Display command (for debugging)
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
        if BUILD_CONFIG.get("onefile"):
            if platform.system() == "Windows":
                exe_name = f"{BUILD_CONFIG['name']}.exe"
            else:
                exe_name = BUILD_CONFIG['name']
            output_path = os.path.join(BUILD_CONFIG['distpath'], exe_name)
            print(f"\n📦 Executable created: {output_path}")
        else:
            print(f"\n📦 Distribution created in: {BUILD_CONFIG['distpath']}/{BUILD_CONFIG['name']}")
        
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