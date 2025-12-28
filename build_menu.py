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
PyCompiler ARK++ — Build Menu
Interactive menu for selecting and running build scripts.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """Print the application header."""
    print("=" * 70)
    print("🚀 PyCompiler ARK++ Build System")
    print("=" * 70)
    print()


def print_menu():
    """Print the build menu."""
    print("📋 Available Build Tools:")
    print()
    print("  1. PyInstaller (Recommended)")
    print("     • Cross-platform")
    print("     • Fast compilation")
    print("     • Size: ~150-200 MB")
    print()
    print("  2. Nuitka (Best Performance)")
    print("     • Compiles to C")
    print("     • Faster execution")
    print("     • Size: ~100-150 MB")
    print()
    print("  3. cx_Freeze (Cross-platform)")
    print("     • Mature tool")
    print("     • Good compatibility")
    print("     • Size: ~150-200 MB")
    print()
    print("  4. Briefcase (Native Installers)")
    print("     • Native installers for each platform")
    print("     • Professional packaging")
    print("     • Size: Varies by platform")
    print()
    print("  5. pynsist (Windows Installer)")
    print("     • Windows-only")
    print("     • Includes Python")
    print("     • Size: ~200-300 MB")
    print()
    print("  6. Verify Build (Check dependencies)")
    print("     • Verify project is ready")
    print("     • Check all dependencies")
    print("     • Analyze project structure")
    print()
    print("  7. Test Build Config (Validate configurations)")
    print("     • Test all build scripts")
    print("     • Validate configurations")
    print("     • Generate report")
    print()
    print("  0. Exit")
    print()


def run_build_script(script_name: str) -> int:
    """Run a build script."""
    if not os.path.exists(script_name):
        print(f"\n❌ Error: {script_name} not found!")
        return 1
    
    print(f"\n🏗️  Running {script_name}...\n")
    try:
        result = subprocess.run([sys.executable, script_name], check=False)
        return result.returncode
    except Exception as e:
        print(f"\n❌ Error running {script_name}: {e}")
        return 1


def main():
    """Main menu function."""
    while True:
        clear_screen()
        print_header()
        
        # Display platform info
        print(f"📱 Platform: {platform.system()} {platform.machine()}")
        print(f"🐍 Python: {sys.version.split()[0]}")
        print()
        
        print_menu()
        
        choice = input("Select an option (0-7): ").strip()
        
        if choice == "0":
            print("\n👋 Goodbye!")
            return 0
        
        elif choice == "1":
            returncode = run_build_script("build_pyinstaller.py")
            if returncode == 0:
                print("\n✅ Build completed successfully!")
            else:
                print(f"\n❌ Build failed with code {returncode}")
        
        elif choice == "2":
            returncode = run_build_script("build_nuitka.py")
            if returncode == 0:
                print("\n✅ Build completed successfully!")
            else:
                print(f"\n❌ Build failed with code {returncode}")
        
        elif choice == "3":
            returncode = run_build_script("build_cxfreeze.py")
            if returncode == 0:
                print("\n✅ Build completed successfully!")
            else:
                print(f"\n❌ Build failed with code {returncode}")
        
        elif choice == "4":
            returncode = run_build_script("build_briefcase.py")
            if returncode == 0:
                print("\n✅ Build completed successfully!")
            else:
                print(f"\n❌ Build failed with code {returncode}")
        
        elif choice == "5":
            if platform.system() != "Windows":
                print("\n⚠️  Warning: pynsist is designed for Windows!")
                print("   You can still create the configuration.")
            returncode = run_build_script("build_pynsist.py")
            if returncode == 0:
                print("\n✅ Build completed successfully!")
            else:
                print(f"\n❌ Build failed with code {returncode}")
        
        elif choice == "6":
            returncode = run_build_script("verify_build.py")
            if returncode == 0:
                print("\n✅ Verification completed successfully!")
            else:
                print(f"\n❌ Verification failed with code {returncode}")
        
        elif choice == "7":
            returncode = run_build_script("test_build_config.py")
            if returncode == 0:
                print("\n✅ Tests completed successfully!")
            else:
                print(f"\n❌ Tests failed with code {returncode}")
        
        else:
            print("\n❌ Invalid option. Please try again.")
        
        input("\nPress Enter to continue...")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
