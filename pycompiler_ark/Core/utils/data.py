# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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
Data classes for structured information

"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import http.client
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Pattern,
    Set,
    Tuple,
    Union,
)


@dataclass
class DependencyInfo:
    """Information about project dependencies."""

    requirements_txt: List[str] = field(default_factory=list)
    pyproject_toml: Dict[str, Any] = field(default_factory=dict)
    setup_py: Dict[str, Any] = field(default_factory=dict)
    pipfile: Dict[str, Any] = field(default_factory=dict)
    conda_yaml: Dict[str, Any] = field(default_factory=dict)
    all_dependencies: Set[str] = field(default_factory=set)


@dataclass
class PythonFileInfo:
    """Information extracted from a Python file."""

    path: Path
    imports: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    classes: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    line_count: int = 0
    is_valid_syntax: bool = True
    syntax_error: Optional[str] = None


@dataclass
class VenvInfo:
    """Information about a virtual environment."""

    path: Path
    exists: bool = False
    python_version: Optional[str] = None
    pip_version: Optional[str] = None
    installed_packages: Dict[str, str] = field(default_factory=dict)
    is_active: bool = False


@dataclass
class GitInfo:
    """Git repository information."""

    is_repo: bool = False
    branch: Optional[str] = None
    has_uncommitted: bool = False
    staged_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    last_commit: Optional[str] = None
