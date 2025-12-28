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
PyCompiler ARK++ — Nuitka Build Script
Automated build configuration for creating standalone executables with Nuitka.
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

# Project configuration
PROJECT_NAME = "PyCompiler-ARK"
MAIN_SCRIPT = "pycompiler_ark.py"
OUTPUT_DIR = "build/nuitka"
DIST_DIR = "dist"

# Build configuration
BUILD_CONFIG = {
    # Main compilation options
    "standalone": True,
    "onefile": True,
    "follow_imports": True,
    
    # Qt/PySide6 configuration
    "enable_plugins": ["pyside6"],
    
    # Output configuration
    "output_dir": OUTPUT_DIR,
    "output_filename": PROJECT_NAME,
    
    # Performance options
    "show_progress": True,
    "show_memory": True,
    "lto": "yes",  # Link Time Optimization
    "jobs": os.cpu_count() or 4,
    
    # Windows-specific
    "windows_disable_console": True if platform.system() == "Windows" else None,
    "windows_icon": "logo/logo.png" if os.path.exists("logo/logo.png") else None,
    "windows_company_name": "PyCompiler",
    "windows_product_name": "PyCompiler ARK++",
    "windows_product_version": "1.0.0",
    "windows_file_description": "Python Compilation Toolkit",
    
    # Linux-specific
    "linux_icon": "logo/logo.png" if os.path.exists("logo/logo.png") else None,
    
    # macOS-specific
    "macos_app_name": "PyCompiler ARK++",
    "macos_app_icon": "logo/logo.png" if os.path.exists("logo/logo.png") else None,
    
    # Include data files and directories
    "include_data_dir": [
        "themes=themes",
        "languages=languages",
        "logo=logo",
        "ui=ui",
    ],
    
    # Include packages (ensure all modules are bundled)
    "include_package": [
        "Core",
        "engine_sdk",
        "ENGINES",
        "bcasl",
        "Plugins_SDK",
    ],
    
    # Include modules explicitly
    "include_module": [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtUiTools",
        "psutil",
        "yaml",
        "PIL",
        "jsonschema",
    ],
    
    # Optimization flags
    "remove_output": True,  # Clean build directory before building
    "assume_yes_for_downloads": True,
    
    # Debugging options (disable for production)
    "debug": False,
    "debugger": False,
}


def build_command():
    """Build the Nuitka command from configuration."""
    cmd = [sys.executable, "-m", "nuitka"]
    
    # Main options
    if BUILD_CONFIG.get("standalone"):
        cmd.append("--standalone")
    if BUILD_CONFIG.get("onefile"):
        cmd.append("--onefile")
    if BUILD_CONFIG.get("follow_imports"):
        cmd.append("--follow-imports")
    
    # Enable plugins
    for plugin in BUILD_CONFIG.get("enable_plugins", []):
        cmd.append(f"--enable-plugin={plugin}")
    
    # Output configuration
    if BUILD_CONFIG.get("output_dir"):
        cmd.append(f"--output-dir={BUILD_CONFIG['output_dir']}")
    if BUILD_CONFIG.get("output_filename"):
        cmd.append(f"--output-filename={BUILD_CONFIG['output_filename']}")
    
    # Performance options
    if BUILD_CONFIG.get("show_progress"):
        cmd.append("--show-progress")
    if BUILD_CONFIG.get("show_memory"):
        cmd.append("--show-memory")
    if BUILD_CONFIG.get("lto"):
        cmd.append(f"--lto={BUILD_CONFIG['lto']}")
    if BUILD_CONFIG.get("jobs"):
        cmd.append(f"--jobs={BUILD_CONFIG['jobs']}")
    
    # Platform-specific options
    os_name = platform.system()
    
    if os_name == "Windows":
        if BUILD_CONFIG.get("windows_disable_console"):
            cmd.append("--windows-disable-console")
        if BUILD_CONFIG.get("windows_icon"):
            cmd.append(f"--windows-icon-from-ico={BUILD_CONFIG['windows_icon']}")
        if BUILD_CONFIG.get("windows_company_name"):
            cmd.append(f"--windows-company-name={BUILD_CONFIG['windows_company_name']}")
        if BUILD_CONFIG.get("windows_product_name"):
            cmd.append(f"--windows-product-name={BUILD_CONFIG['windows_product_name']}")
        if BUILD_CONFIG.get("windows_product_version"):
            cmd.append(f"--windows-product-version={BUILD_CONFIG['windows_product_version']}")
        if BUILD_CONFIG.get("windows_file_description"):
            cmd.append(f"--windows-file-description={BUILD_CONFIG['windows_file_description']}")
    
    elif os_name == "Linux":
        if BUILD_CONFIG.get("linux_icon"):
            cmd.append(f"--linux-icon={BUILD_CONFIG['linux_icon']}")
    
    elif os_name == "Darwin":
        if BUILD_CONFIG.get("macos_app_name"):
            cmd.append(f"--macos-app-name={BUILD_CONFIG['macos_app_name']}")
        if BUILD_CONFIG.get("macos_app_icon"):
            cmd.append(f"--macos-app-icon={BUILD_CONFIG['macos_app_icon']}")
    
    # Include data directories
    for data_dir in BUILD_CONFIG.get("include_data_dir", []):
        cmd.append(f"--include-data-dir={data_dir}")
    
    # Include packages
    for package in BUILD_CONFIG.get("include_package", []):
        cmd.append(f"--include-package={package}")
    
    # Include modules
    for module in BUILD_CONFIG.get("include_module", []):
        cmd.append(f"--include-module={module}")
    
    # Optimization flags
    if BUILD_CONFIG.get("remove_output"):
        cmd.append("--remove-output")
    if BUILD_CONFIG.get("assume_yes_for_downloads"):
        cmd.append("--assume-yes-for-downloads")
    
    # Debugging options
    if BUILD_CONFIG.get("debug"):
        cmd.append("--debug")
    if BUILD_CONFIG.get("debugger"):
        cmd.append("--debugger")
    
    # Main script
    cmd.append(MAIN_SCRIPT)
    
    return cmd


def check_nuitka_installed():
    """Check if Nuitka is installed."""
    try:
        subprocess.run(
            [sys.executable, "-m", "nuitka", "--version"],
            check=True,
            capture_output=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_nuitka():
    """Install Nuitka if not already installed."""
    print("📦 Installing Nuitka...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "nuitka"],
            check=True,
        )
        print("✅ Nuitka installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install Nuitka: {e}")
        return False


def main():
    """Main build function."""
    print("=" * 70)
    print(f"🚀 Building {PROJECT_NAME} with Nuitka")
    print("=" * 70)
    
    # Check if main script exists
    if not os.path.exists(MAIN_SCRIPT):
        print(f"❌ Error: Main script '{MAIN_SCRIPT}' not found!")
        return 1
    
    # Check Nuitka installation
    if not check_nuitka_installed():
        print("⚠️  Nuitka is not installed")
        if not install_nuitka():
            return 1
    
    # Build command
    cmd = build_command()
    
    # Display build configuration
    print("\n📋 Build Configuration:")
    print(f"  Platform: {platform.system()} {platform.machine()}")
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Main script: {MAIN_SCRIPT}")
    print(f"  Output mode: {'Onefile' if BUILD_CONFIG.get('onefile') else 'Standalone'}")
    print(f"  Output directory: {BUILD_CONFIG.get('output_dir')}")
    print(f"  Optimization: LTO {BUILD_CONFIG.get('lto')}, {BUILD_CONFIG.get('jobs')} jobs")
    
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
                exe_name = f"{BUILD_CONFIG['output_filename']}.exe"
            else:
                exe_name = BUILD_CONFIG['output_filename']
            output_path = os.path.join(BUILD_CONFIG['output_dir'], exe_name)
            print(f"\n📦 Executable created: {output_path}")
        else:
            print(f"\n📦 Distribution created in: {BUILD_CONFIG['output_dir']}")
        
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