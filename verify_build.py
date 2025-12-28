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
PyCompiler ARK++ — Build Verification Script
Verifies that all dependencies are available and the project is ready for building.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_utils import DependencyAnalyzer, check_dependencies


def main():
    """Main verification function."""
    print("=" * 70)
    print("🔍 PyCompiler ARK++ Build Verification")
    print("=" * 70)
    
    # Check dependencies
    if not check_dependencies():
        print("\n❌ Build verification failed!")
        print("   Please install missing dependencies:")
        print("   pip install -r requirements.txt")
        return 1
    
    # Analyze project structure
    print("\n📁 Project Structure Analysis:")
    analyzer = DependencyAnalyzer()
    
    # Check for excluded directories
    excluded_dirs = analyzer.EXCLUDE_DIRS
    print(f"\n✅ Directories to exclude from compilation:")
    for excluded_dir in sorted(excluded_dirs):
        print(f"   • {excluded_dir}/")
    
    # Check for data directories
    data_dirs = analyzer.DATA_DIRS
    print(f"\n✅ Data directories to include (loaded dynamically):")
    for data_dir in sorted(data_dirs):
        print(f"   • {data_dir}/")
    
    # Check for local packages
    print(f"\n✅ Local packages to include:")
    for local_pkg in sorted(analyzer.LOCAL_PACKAGES):
        pkg_path = os.path.join(".", local_pkg)
        if os.path.isdir(pkg_path):
            print(f"   ✓ {local_pkg}/")
        else:
            print(f"   ✗ {local_pkg}/ (NOT FOUND)")
    
    # Check for data directories
    print(f"\n✅ Data directories to include:")
    data_dirs = ["themes", "languages", "logo", "ui"]
    for data_dir in data_dirs:
        if os.path.isdir(data_dir):
            print(f"   ✓ {data_dir}/")
        else:
            print(f"   ✗ {data_dir}/ (NOT FOUND)")
    
    # Check main scripts
    print(f"\n✅ Main entry points:")
    main_scripts = ["pycompiler_ark.py", "main.py"]
    for script in main_scripts:
        if os.path.isfile(script):
            print(f"   ✓ {script}")
        else:
            print(f"   ✗ {script} (NOT FOUND)")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Build verification completed successfully!")
    print("=" * 70)
    print("\n📝 Next steps:")
    print("   1. Choose a build tool:")
    print("      • PyInstaller: python build_pyinstaller.py")
    print("      • Nuitka:      python build_nuitka.py")
    print("      • cx_Freeze:   python build_cxfreeze.py")
    print("      • Briefcase:   python build_briefcase.py")
    print("      • pynsist:     python build_pynsist.py (Windows only)")
    print("\n   2. All builds will create standalone executables")
    print("   3. Plugins/ and ENGINES/ directories are excluded from compilation")
    print("   4. All dependencies are automatically included")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
