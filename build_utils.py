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
PyCompiler ARK++ — Build Utilities
Shared utilities for build scripts including dependency analysis and validation.
"""

import os
import re
import sys
from pathlib import Path
from typing import Set, List, Dict


class DependencyAnalyzer:
    """Analyze Python dependencies from source code."""
    
    # Standard library modules (Python 3.10+)
    STDLIB_MODULES = {
        'abc', 'aifc', 'argparse', 'array', 'ast', 'asyncio', 'atexit', 'audioop',
        'base64', 'bdb', 'binascii', 'binhex', 'bisect', 'builtins', 'bz2',
        'calendar', 'cgi', 'cgitb', 'chunk', 'cmath', 'cmd', 'code', 'codecs',
        'codeop', 'collections', 'colorsys', 'compileall', 'concurrent', 'configparser',
        'contextlib', 'contextvars', 'copy', 'copyreg', 'cProfile', 'crypt', 'csv',
        'ctypes', 'curses', 'dataclasses', 'datetime', 'dbm', 'decimal', 'difflib',
        'dis', 'distutils', 'doctest', 'dummy_thread', 'dummy_threading', 'email',
        'encodings', 'ensurepip', 'enum', 'errno', 'faulthandler', 'fcntl', 'filecmp',
        'fileinput', 'fnmatch', 'fractions', 'ftplib', 'functools', 'gc', 'getopt',
        'getpass', 'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq', 'hmac',
        'html', 'http', 'idlelib', 'imaplib', 'imghdr', 'imp', 'importlib', 'inspect',
        'io', 'ipaddress', 'itertools', 'json', 'keyword', 'lib2to3', 'linecache',
        'locale', 'logging', 'lzma', 'mailbox', 'mailcap', 'marshal', 'math',
        'mimetypes', 'mmap', 'modulefinder', 'msilib', 'msvcrt', 'multiprocessing',
        'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse', 'os', 'ossaudiodev',
        'parser', 'pathlib', 'pdb', 'pickle', 'pickletools', 'pipes', 'pkgutil',
        'platform', 'plistlib', 'poplib', 'posix', 'posixpath', 'pprint', 'profile',
        'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue', 'quopri',
        'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter', 'runpy',
        'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex', 'shutil',
        'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket', 'socketserver',
        'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string', 'stringprep',
        'struct', 'subprocess', 'sunau', 'symbol', 'symtable', 'sys', 'sysconfig',
        'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile', 'termios', 'test',
        'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token', 'tokenize',
        'tomllib', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'types',
        'typing', 'typing_extensions', 'unicodedata', 'unittest', 'urllib', 'uu',
        'uuid', 'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'winreg',
        'winsound', 'wsgiref', 'xdrlib', 'xml', 'xmlrpc', 'zipapp', 'zipfile',
        'zipimport', 'zlib', 'zoneinfo',
    }
    
    # Third-party packages that should be included
    REQUIRED_PACKAGES = {
        'PySide6', 'shiboken6', 'psutil', 'yaml', 'PIL', 'jsonschema',
    }
    
    # Local packages to include
    LOCAL_PACKAGES = {
        'Core', 'engine_sdk', 'bcasl', 'Plugins_SDK',
    }
    
    # Directories to exclude from compilation (but included as data)
    EXCLUDE_DIRS = {
        '__pycache__', '.git', '.venv', 'build', 'dist',
        'Tests', 'tests', '.pytest_cache', '.mypy_cache', 'node_modules',
    }
    
    # Data directories to include (loaded dynamically at runtime)
    DATA_DIRS = {
        'Plugins', 'ENGINES', 'themes', 'languages', 'logo', 'ui',
    }
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.found_imports: Set[str] = set()
        self.missing_packages: Set[str] = set()
    
    def analyze_file(self, filepath: Path) -> Set[str]:
        """Extract import statements from a Python file."""
        imports = set()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Find all import statements
            import_patterns = [
                r'^\s*import\s+([\w.]+)',  # import x
                r'^\s*from\s+([\w.]+)\s+import',  # from x import
            ]
            
            for pattern in import_patterns:
                matches = re.finditer(pattern, content, re.MULTILINE)
                for match in matches:
                    module = match.group(1).split('.')[0]
                    imports.add(module)
        
        except Exception as e:
            print(f"⚠️  Error analyzing {filepath}: {e}")
        
        return imports
    
    def analyze_directory(self, directory: Path = None) -> Set[str]:
        """Recursively analyze all Python files in a directory."""
        if directory is None:
            directory = self.project_root
        
        all_imports = set()
        
        try:
            for py_file in directory.rglob('*.py'):
                # Skip excluded directories
                if any(excluded in py_file.parts for excluded in self.EXCLUDE_DIRS):
                    continue
                
                imports = self.analyze_file(py_file)
                all_imports.update(imports)
        
        except Exception as e:
            print(f"⚠️  Error analyzing directory {directory}: {e}")
        
        return all_imports
    
    def get_external_packages(self) -> Set[str]:
        """Get all external packages (non-stdlib, non-local)."""
        all_imports = self.analyze_directory()
        
        external = set()
        for module in all_imports:
            if module not in self.STDLIB_MODULES and module not in self.LOCAL_PACKAGES:
                external.add(module)
        
        return external
    
    def validate_dependencies(self) -> Dict[str, bool]:
        """Validate that all required dependencies are available."""
        validation = {}
        
        for package in self.REQUIRED_PACKAGES:
            try:
                __import__(package)
                validation[package] = True
            except ImportError:
                validation[package] = False
                self.missing_packages.add(package)
        
        return validation
    
    def get_missing_packages(self) -> Set[str]:
        """Get list of missing required packages."""
        self.validate_dependencies()
        return self.missing_packages
    
    def get_exclude_patterns(self) -> List[str]:
        """Get glob patterns for directories to exclude."""
        patterns = []
        for excluded_dir in self.EXCLUDE_DIRS:
            patterns.append(f"**/{excluded_dir}/**")
            patterns.append(f"{excluded_dir}/**")
        return patterns


def check_dependencies():
    """Check and report on project dependencies."""
    print("\n📊 Analyzing project dependencies...")
    
    analyzer = DependencyAnalyzer()
    
    # Analyze imports
    external_packages = analyzer.get_external_packages()
    print(f"\n✅ External packages found: {len(external_packages)}")
    for pkg in sorted(external_packages):
        print(f"   • {pkg}")
    
    # Validate required packages
    print(f"\n🔍 Validating required packages...")
    validation = analyzer.validate_dependencies()
    
    all_ok = True
    for package, available in validation.items():
        status = "✅" if available else "❌"
        print(f"   {status} {package}")
        if not available:
            all_ok = False
    
    if not all_ok:
        print(f"\n⚠️  Some required packages are missing!")
        print(f"   Install with: pip install -r requirements.txt")
        return False
    
    print(f"\n✅ All required packages are available!")
    return True


def get_build_config(tool_name: str) -> Dict:
    """Get build configuration for a specific tool."""
    
    analyzer = DependencyAnalyzer()
    exclude_patterns = analyzer.get_exclude_patterns()
    
    base_config = {
        "exclude_dirs": list(analyzer.EXCLUDE_DIRS),
        "exclude_patterns": exclude_patterns,
        "local_packages": list(analyzer.LOCAL_PACKAGES),
        "required_packages": list(analyzer.REQUIRED_PACKAGES),
        "data_dirs": [
            "themes",
            "languages",
            "logo",
            "ui",
        ],
    }
    
    if tool_name == "pyinstaller":
        return {
            **base_config,
            "hidden_imports": list(analyzer.REQUIRED_PACKAGES) + [
                "multiprocessing",
                "faulthandler",
                "traceback",
                "pathlib",
            ],
            "collect_all": ["PySide6", "shiboken6"],
            "collect_binaries": ["PySide6"],
            "collect_data": ["PySide6"],
        }
    
    elif tool_name == "nuitka":
        return {
            **base_config,
            "include_packages": list(analyzer.LOCAL_PACKAGES),
            "include_modules": list(analyzer.REQUIRED_PACKAGES) + [
                "multiprocessing",
                "faulthandler",
                "traceback",
                "pathlib",
            ],
        }
    
    elif tool_name == "cxfreeze":
        return {
            **base_config,
            "packages": list(analyzer.REQUIRED_PACKAGES) + list(analyzer.LOCAL_PACKAGES),
            "includes": list(analyzer.REQUIRED_PACKAGES),
        }
    
    elif tool_name == "pynsist":
        return {
            **base_config,
            "packages": list(analyzer.REQUIRED_PACKAGES),
            "files": list(analyzer.LOCAL_PACKAGES) + [
                "main.py",
                "pycompiler_ark.py",
            ] + base_config["data_dirs"],
        }
    
    return base_config


if __name__ == "__main__":
    check_dependencies()
