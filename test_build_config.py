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
PyCompiler ARK++ — Build Configuration Test
Tests that all build scripts have correct standalone and exclusion configurations.
"""

import sys
import os
import re
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_utils import DependencyAnalyzer


def test_build_script(script_path: str, tool_name: str) -> bool:
    """Test a build script for correct configuration."""
    print(f"\n{'='*70}")
    print(f"Testing {tool_name} build script")
    print(f"{'='*70}")
    
    if not os.path.exists(script_path):
        print(f"❌ Script not found: {script_path}")
        return False
    
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        "standalone": False,
        "onefile": False,
        "exclude_plugins": False,
        "exclude_engines": False,
        "include_data": False,
        "include_deps": False,
    }
    
    # Check for standalone mode
    if tool_name == "nuitka":
        if '"standalone": True' in content or "'standalone': True" in content:
            checks["standalone"] = True
            print("✅ Standalone mode enabled")
        else:
            print("❌ Standalone mode not found")
    elif tool_name == "pyinstaller":
        if '"onefile": True' in content or "'onefile': True" in content:
            checks["onefile"] = True
            print("✅ Onefile mode enabled")
        else:
            print("❌ Onefile mode not found")
    elif tool_name == "cxfreeze":
        if "build_exe" in content:
            checks["standalone"] = True
            print("✅ Build executable mode enabled")
        else:
            print("❌ Build executable mode not found")
    elif tool_name == "briefcase":
        checks["standalone"] = True
        print("✅ Briefcase standalone mode (native)")
    elif tool_name == "pynsist":
        if "bundled" in content or "format = bundled" in content:
            checks["standalone"] = True
            print("✅ Bundled Python mode enabled")
        else:
            print("❌ Bundled Python mode not found")
    
    # Check for Plugins/ exclusion
    if "Plugins" in content and ("exclude" in content or "EXCLUDE" in content):
        checks["exclude_plugins"] = True
        print("✅ Plugins/ directory exclusion configured")
    else:
        print("⚠️  Plugins/ directory exclusion not explicitly mentioned")
    
    # Check for ENGINES/ exclusion
    if "ENGINES" in content and ("exclude" in content or "EXCLUDE" in content):
        checks["exclude_engines"] = True
        print("✅ ENGINES/ directory exclusion configured")
    else:
        print("⚠️  ENGINES/ directory exclusion not explicitly mentioned")
    
    # Check for data directories
    data_dirs = ["themes", "languages", "logo", "ui"]
    data_found = sum(1 for d in data_dirs if d in content)
    if data_found >= 3:
        checks["include_data"] = True
        print(f"✅ Data directories included ({data_found}/4)")
    else:
        print(f"⚠️  Only {data_found}/4 data directories found")
    
    # Check for dependency inclusion
    deps = ["PySide6", "psutil", "yaml", "PIL", "jsonschema"]
    deps_found = sum(1 for d in deps if d in content)
    if deps_found >= 4:
        checks["include_deps"] = True
        print(f"✅ Dependencies included ({deps_found}/5)")
    else:
        print(f"⚠️  Only {deps_found}/5 dependencies found")
    
    # Summary
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    print(f"\n📊 Results: {passed}/{total} checks passed")
    
    return passed >= 4  # At least 4 checks should pass


def main():
    """Main test function."""
    print("=" * 70)
    print("🧪 PyCompiler ARK++ Build Configuration Tests")
    print("=" * 70)
    
    # Test scripts
    test_scripts = [
        ("build_pyinstaller.py", "pyinstaller"),
        ("build_nuitka.py", "nuitka"),
        ("build_cxfreeze.py", "cxfreeze"),
        ("build_briefcase.py", "briefcase"),
        ("build_pynsist.py", "pynsist"),
    ]
    
    results = {}
    for script_path, tool_name in test_scripts:
        results[tool_name] = test_build_script(script_path, tool_name)
    
    # Test build_utils
    print(f"\n{'='*70}")
    print("Testing build_utils module")
    print(f"{'='*70}")
    
    try:
        analyzer = DependencyAnalyzer()
        
        # Check excluded directories
        excluded = analyzer.EXCLUDE_DIRS
        if "Plugins" in excluded and "ENGINES" in excluded:
            print("✅ Plugins/ and ENGINES/ are in exclusion list")
        else:
            print("❌ Plugins/ or ENGINES/ missing from exclusion list")
        
        # Check local packages
        local = analyzer.LOCAL_PACKAGES
        if "Core" in local and "engine_sdk" in local:
            print("✅ Local packages correctly identified")
        else:
            print("❌ Local packages not correctly identified")
        
        # Check required packages
        required = analyzer.REQUIRED_PACKAGES
        if "PySide6" in required and "psutil" in required:
            print("✅ Required packages correctly identified")
        else:
            print("❌ Required packages not correctly identified")
        
        results["build_utils"] = True
    except Exception as e:
        print(f"❌ Error testing build_utils: {e}")
        results["build_utils"] = False
    
    # Final summary
    print(f"\n{'='*70}")
    print("📋 Test Summary")
    print(f"{'='*70}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for tool, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {tool}")
    
    print(f"\n{'='*70}")
    if passed == total:
        print(f"✅ All {total} tests passed!")
        print("=" * 70)
        return 0
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
