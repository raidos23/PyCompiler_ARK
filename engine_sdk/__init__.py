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

# Re-export auto_plugins helpers for convenience
from .auto_build_command import (
    compute_auto_for_engine,
    compute_for_all,
    register_auto_builder,
)
from .ui_helpers import add_form_checkbox, add_icon_selector, add_output_dir

__version__ = "1.0.0"
# Re-export the base interface used by the host
from .base import CompilerEngine
from .utils import (
    atomic_write_text,
    clamp_text,
    ensure_dir,
    is_within_workspace,
    open_dir_candidates,
    open_path,
    redact_secrets,
    resolve_executable,  # executable resolution helper (SDK)
    safe_join,
    safe_log,
    tr,
)

# Re-export venv/pip helpers from mainprocess.py (moved from utils.py)
# These are maintained here for backward compatibility
# NOTE: Using lazy imports to avoid circular import issues during engine discovery
_lazy_imports_done = False
_lazy_mainprocess_imports = {}


def _do_lazy_imports():
    """Perform lazy imports from Core.Compiler.mainprocess to avoid circular imports."""
    global _lazy_imports_done, _lazy_mainprocess_imports
    if _lazy_imports_done:
        return
    try:
        from Core.Compiler.mainprocess import (
            pip_executable,
            pip_install,
            pip_show,
            resolve_project_venv,
        )

        _lazy_mainprocess_imports = {
            "pip_executable": pip_executable,
            "pip_install": pip_install,
            "pip_show": pip_show,
            "resolve_project_venv": resolve_project_venv,
        }
        _lazy_imports_done = True
    except ImportError:
        # Fallback: keep original imports if mainprocess.py is not available
        from .utils import (
            pip_executable,
            pip_install,
            pip_show,
            resolve_project_venv,
        )

        _lazy_mainprocess_imports = {
            "pip_executable": pip_executable,
            "pip_install": pip_install,
            "pip_show": pip_show,
            "resolve_project_venv": resolve_project_venv,
        }
        _lazy_imports_done = True


# Provide access to these functions via __getattr__ for lazy loading
def __getattr__(name: str):
    if name in ("pip_executable", "pip_install", "pip_show", "resolve_project_venv"):
        _do_lazy_imports()
        if name in _lazy_mainprocess_imports:
            return _lazy_mainprocess_imports[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


try:
    # Optional alias to host-level executable resolver for advanced cases
    from .utils import resolve_executable_path as host_resolve_executable_path  # type: ignore
except Exception:  # pragma: no cover
    host_resolve_executable_path = None  # type: ignore


# Re-export system dependency helpers
# Re-export i18n helpers
from .i18n import (
    resolve_language_code,
    load_engine_language_file,
)
from .Sys_Deps import SysDependencyManager  # type: ignore

# Re-export engines registry for self-registration from engine packages
try:
    from EngineLoader import registry as registry  # type: ignore
except Exception:  # pragma: no cover
    registry = None  # type: ignore

__version__ = "1.0.1"


# Lazy attribute resolver to reduce import overhead in plugin environments
def __getattr__(name: str):
    if name == "SysDependencyManager":
        import importlib

        mod = importlib.import_module(f"{__name__}.sysdep")
        attr = getattr(mod, "SysDependencyManager")
        globals()["SysDependencyManager"] = attr
        return attr
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    try:
        base = set(globals().keys()) | set(__all__)
        return sorted(base)
    except Exception:
        return sorted(globals().keys())


# Version helpers and capability report


def _parse_version(v: str) -> tuple:
    try:
        parts = v.strip().split("+")[0].split("-")[0].split(".")
        major = int(parts[0]) if len(parts) > 0 else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch = int(parts[2]) if len(parts) > 2 else 0
        return (major, minor, patch)
    except Exception:
        return (0, 0, 0)


def ensure_min_sdk(required: str) -> bool:
    """Return True if the current SDK version satisfies the minimal required semver (major.minor.patch).
    Example: ensure_min_sdk("3.2.2") -> True/False
    """
    try:
        cur = _parse_version(__version__)
        need = _parse_version(str(required))
        return cur >= need
    except Exception:
        return False


def get_capabilities() -> dict:
    """Return a dictionary of SDK runtime capabilities for feature detection."""
    caps = {
        "version": __version__,
        "process": {
            "on_stdout": True,
            "on_stderr": True,
        },
        "fs": {
            "atomic_write_text": True,
            "ensure_dir": True,
        },
        "exec_resolution": {
            "host_resolve_executable_path": bool(host_resolve_executable_path),
        },
    }
    return caps


def sdk_info() -> dict:
    """Return SDK metadata, exported symbols and capabilities."""
    return {
        "version": __version__,
        "exports": sorted(list(__all__)),
        "capabilities": get_capabilities(),
    }


def check_engine_compatibility(engine_class, required_sdk_version: str = None) -> bool:
    """Check if an engine is compatible with the current SDK version.

    Args:
        engine_class: The engine class to check
        required_sdk_version: Minimum required SDK version (defaults to engine's requirement)

    Returns:
        True if compatible, False otherwise
    """
    try:
        if required_sdk_version is None:
            required_sdk_version = getattr(
                engine_class, "required_sdk_version", "1.0.0"
            )
        return ensure_min_sdk(required_sdk_version)
    except Exception:
        return False


from EngineLoader.registry import engine_register

__all__ = [
    "CompilerEngine",
    "engine_register",
    "register",
    "compute_auto_for_engine",
    "compute_for_all",
    "register_auto_builder",
    "add_form_checkbox",
    "add_icon_selector",
    "add_output_dir",
    "registry",
    # Utilities for engine authors
    "redact_secrets",
    "is_within_workspace",
    "safe_join",
    "validate_args",
    "build_env",
    "clamp_text",
    "normalized_program_and_args",
    "tr",
    "safe_log",
    "open_path",
    "open_dir_candidates",
    "resolve_project_venv",
    "pip_executable",
    "pip_show",
    "pip_install",
    "resolve_executable",
    "ensure_dir",
    "atomic_write_text",
    "run_process",
    "resolve_executable_path",
    "host_resolve_executable_path",
    "SysDependencyManager",
    "resolve_language_code",
    "load_engine_language_file",
    "ensure_min_sdk",
    "get_capabilities",
    "sdk_info",
    "check_engine_compatibility",
    "__version__",
    # Config helpers
    "get_main_file_names",
]
