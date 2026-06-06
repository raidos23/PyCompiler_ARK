# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
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
from typing import Any, Dict, Iterator, List, Optional, Pattern, Set, Tuple, Union

# -----------------------------
# Plugin base (BCASL) and decorator
# -----------------------------
# Reuse BCASL types to guarantee compatibility with the host
try:
    from pycompiler_ark.bcasl import BCASL as BCASL
    from pycompiler_ark.bcasl import BCASL_PLUGIN_REGISTER_FUNC as BCASL_PLUGIN_REGISTER_FUNC
    from pycompiler_ark.bcasl import BcPluginBase as BcPluginBase
    from pycompiler_ark.bcasl import ExecutionReport as ExecutionReport
    from pycompiler_ark.bcasl import PluginMeta as PluginMeta
    from pycompiler_ark.bcasl import PreCompileContext as PreCompileContext
    from pycompiler_ark.bcasl import bc_register as _bc_register
    from pycompiler_ark.bcasl import register_plugin as register_plugin
except ImportError:
    # Dev fallback when BCASL is not importable (e.g. standalone SDK testing)
    class BcPluginBase:
        pass

    class PluginMeta:
        pass

    @dataclass
    class PreCompileContext:
        root: Path
        config: dict[str, Any] = field(default_factory=dict)
        metadata: dict[str, Any] = field(default_factory=dict)
        build_context: Optional[Any] = None

    def register_plugin(cls: Any) -> Any:
        setattr(cls, "__bcasl_plugin__", True)
        return cls

    BCASL_PLUGIN_REGISTER_FUNC = "bcasl_register"

    def _bc_register(cls=None, **kwargs):
        def inner(c):
            setattr(c, "__bcasl_plugin__", True)
            return c

        return inner(cls) if cls else inner


def bc_register(cls=None, **kwargs):
    """SDK-level wrapper for bc_register."""
    return _bc_register(cls, **kwargs)


# -----------------------------
# Version information
# -----------------------------
__version__ = "1.0.0"


# -----------------------------
# Type aliases
# -----------------------------
Pathish = Union[str, Path]


# -----------------------------
# Data classes for structured information
# -----------------------------


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





# -----------------------------
# Workspace management utilities
# -----------------------------


def set_selected_workspace(path: Pathish) -> bool:
    """Request workspace change from BC plugin.

    This function allows BC plugins to request a workspace directory change.
    The request is always accepted at the SDK level, with best-effort directory creation.

    Args:
        path: Target workspace directory path (str or Path object)

    Returns:
        bool: Always returns True (acceptance guaranteed by SDK contract)

    Behavior:
        - Auto-creates the target directory if missing
        - Invokes the GUI-side bridge when available (non-blocking)
        - Works in both GUI and headless environments

    Example:
        >>> from pycompiler_ark.Plugins_SDK.BcPluginContext import set_selected_workspace
        >>> set_selected_workspace("/path/to/new/workspace")
        True
    """
    # Best-effort ensure the path exists
    try:
        p = Path(path)
        if not p.exists():
            try:
                p.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
    except Exception:
        pass
    # Try to inform the GUI when running with UI; ignore result and accept by contract
    try:
        from pycompiler_ark.Services.AdvancedAuth import (
            request_workspace_change_from_BcPlugin,
        )  # type: ignore

        try:
            request_workspace_change_from_BcPlugin(str(path))
        except Exception:
            pass
    except Exception:
        # No GUI or bridge available — still accept
        pass
    return True




# -----------------------------
# Template generation
# -----------------------------


def Generate_Bc_Plugin_Template() -> str:
    """Generate a ready-to-use BC plugin template.

    The template is compatible with the BCASL loader:
    - Exposes a plugin class with proper metadata
    - Provides the global PLUGIN variable for execution
    - Provides the bcasl_register(manager) function for direct registration
    - Includes Dialog Plugins for user interaction and logging
    - Includes proper version requirements

    Returns:
        str: Complete BC plugin template code

    Example:
        >>> template = Generate_Bc_Plugin_Template()
        >>> with open("Plugins/my_plugin/__init__.py", "w") as f:
        ...     f.write(template)
    """

    template = '''from __future__ import annotations

from pathlib import Path
from pycompiler_ark.Plugins_SDK.BcPluginContext import BcPluginBase, PluginMeta, PreCompileContext
from pycompiler_ark.Plugins_SDK.GeneralContext import Dialog

# Create Dialog instances for user interaction and logging
log = Dialog()
dialog = Dialog()

META = PluginMeta(
    id="my.plugin.id",
    name="My BC Plugin",
    version="1.0.0",
    description="Describe what this BC plugin does before compilation.",
    author="Your Name",
    tags=("check",),   # e.g., ("clean", "check", "optimize", "prepare", ...)
    required_bcasl_version="2.0.0",
    required_core_version="1.0.0",
    required_plugins_sdk_version="1.0.0",
    required_bc_plugin_context_version="1.0.0",
    required_general_context_version="1.0.0",
)


class MyPlugin(BcPluginBase):
    def __init__(self) -> None:
        super().__init__(META)

    def on_pre_compile(self, ctx: PreCompileContext) -> None:
        """Execute pre-compilation actions.
        
        Args:
            ctx: PreCompileContext with workspace information and utilities
        """
        try:
            # Example: Ask user for confirmation
            response = dialog.msg_question(
                title="My Plugin",
                text="Proceed with pre-build checks?",
                default_yes=True,
            )
            
            if not response:
                log.log_info("Plugin cancelled by user")
                return
            
            # Example: Check for Python files
            files = list(ctx.iter_files(["*.py"], []))
            if not files:
                log.log_warn("No Python files found in workspace")
                raise RuntimeError("No Python files found in workspace")
            
            log.log_info(f"Found {len(files)} Python files")
            # Perform additional preparation...
            
        except Exception as e:
            log.log_error(f"Plugin error: {e}")
            raise


# Create plugin instance
PLUGIN = MyPlugin()


def bcasl_register(manager):
    """Register the plugin with the BCASL manager."""
    manager.add_plugin(PLUGIN)
'''

    return template


# -----------------------------
# Public APIs exports
# -----------------------------

__all__ = [
    # Version
    "__version__",
    # Base classes and types
    "BcPluginBase",
    "PluginMeta",
    "PreCompileContext",
    "register_plugin",
    "BCASL_PLUGIN_REGISTER_FUNC",
    "bc_register",
    # Type aliases
    "Pathish",
    # Data classes
    "DependencyInfo",
    "PythonFileInfo",
    "VenvInfo",
    "GitInfo",
    # Workspace management
    "set_selected_workspace",
    # Template generation
    "Generate_Bc_Plugin_Template",
]
