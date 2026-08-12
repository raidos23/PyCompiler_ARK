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

import ast
import configparser
import functools
import os
import platform
import re
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution


@functools.lru_cache(maxsize=256)
def _is_stdlib_module(module_name: str) -> bool:
    """Determine whether module belongs to Python standard library."""
    try:
        import importlib.util
        import sys
        import sysconfig

        top_level = (module_name or "").split(".")[0]
        if top_level in sys.builtin_module_names:
            return True
        stdlib_names = getattr(sys, "stdlib_module_names", None)
        if stdlib_names and top_level in stdlib_names:
            return True
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return False
        if getattr(spec, "origin", None) in ("built-in", "frozen"):
            return True
        stdlib_path = sysconfig.get_path("stdlib") or ""
        stdlib_path = os.path.realpath(stdlib_path)
        candidates = []
        if getattr(spec, "origin", None):
            candidates.append(os.path.realpath(spec.origin))
        for loc in spec.submodule_search_locations or []:
            candidates.append(os.path.realpath(loc))
        for c in candidates:
            try:
                if os.path.commonpath([c, stdlib_path]) == stdlib_path:
                    return True
            except Exception:
                # os.path.commonpath may raise if paths on different volumes
                pass
        return False
    except Exception:
        return False


def _normalize_realpath(path: str | None) -> str:
    if not path:
        return ""
    try:
        return os.path.normcase(os.path.realpath(path))
    except Exception:
        return path


def _is_path_under(path: str, root: str) -> bool:
    if not path or not root:
        return False
    try:
        return os.path.commonpath([path, root]) == root
    except Exception:
        return False


def _normalize_module_name(name: str | None) -> str:
    if not name:
        return ""
    try:
        cleaned = re.sub(r"[^A-Za-z0-9_\.]+", "_", str(name).strip())
        return cleaned.replace("-", "_").strip("._")
    except Exception:
        return ""


def _top_level_module_name(name: str | None) -> str:
    normalized = _normalize_module_name(name)
    if not normalized:
        return ""
    return normalized.split(".")[0]


def _load_toml_file(path: str) -> dict:
    try:
        import tomllib  # type: ignore
    except Exception:
        try:
            import tomli as tomllib  # type: ignore
        except Exception:
            tomllib = None  # type: ignore
    if tomllib is None:
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@functools.lru_cache(maxsize=64)
def _discover_workspace_hints(
    workspace_dir: str | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    ws = _normalize_realpath(workspace_dir)
    if not ws or not os.path.isdir(ws):
        return tuple(), tuple()

    source_roots: set[str] = {ws}
    module_roots: set[str] = set()

    def _add_source_root(*parts: str) -> None:
        candidate = _normalize_realpath(os.path.join(ws, *parts))
        if candidate and os.path.isdir(candidate):
            source_roots.add(candidate)

    for rel_parts in (
        ("src",),
        ("lib",),
        ("python",),
        ("lib", "python"),
        ("src", "python"),
    ):
        _add_source_root(*rel_parts)

    pyproject_path = os.path.join(ws, "pyproject.toml")
    pyproject = (
        _load_toml_file(pyproject_path)
        if os.path.isfile(pyproject_path)
        else {}
    )
    try:
        project = pyproject.get("project", {})
        if isinstance(project, dict):
            top = _top_level_module_name(project.get("name"))
            if top:
                module_roots.add(top)
    except Exception:
        pass
    try:
        tool = pyproject.get("tool", {})
        poetry = tool.get("poetry", {}) if isinstance(tool, dict) else {}
        if isinstance(poetry, dict):
            top = _top_level_module_name(poetry.get("name"))
            if top:
                module_roots.add(top)
            packages = poetry.get("packages", [])
            if isinstance(packages, list):
                for pkg in packages:
                    if not isinstance(pkg, dict):
                        continue
                    include = _top_level_module_name(pkg.get("include"))
                    if include:
                        module_roots.add(include)
                    from_dir = pkg.get("from")
                    if isinstance(from_dir, str) and from_dir.strip():
                        _add_source_root(from_dir.strip())
        setuptools = (
            tool.get("setuptools", {}) if isinstance(tool, dict) else {}
        )
        if isinstance(setuptools, dict):
            package_dir = setuptools.get("package-dir", {})
            if isinstance(package_dir, dict):
                root_dir = package_dir.get("") or package_dir.get(".")
                if isinstance(root_dir, str) and root_dir.strip():
                    _add_source_root(root_dir.strip())
            packages = setuptools.get("packages", {})
            if isinstance(packages, dict):
                find_cfg = packages.get("find", {})
                if isinstance(find_cfg, dict):
                    where = find_cfg.get("where", [])
                    if isinstance(where, str):
                        where = [where]
                    if isinstance(where, list):
                        for item in where:
                            if isinstance(item, str) and item.strip():
                                _add_source_root(item.strip())
    except Exception:
        pass

    setup_cfg_path = os.path.join(ws, "setup.cfg")
    if os.path.isfile(setup_cfg_path):
        try:
            cfg = configparser.ConfigParser()
            cfg.read(setup_cfg_path, encoding="utf-8")
            if cfg.has_option("metadata", "name"):
                top = _top_level_module_name(cfg.get("metadata", "name"))
                if top:
                    module_roots.add(top)
            if cfg.has_option("options", "package_dir"):
                package_dir_raw = cfg.get("options", "package_dir")
                for line in package_dir_raw.splitlines():
                    if "=" not in line:
                        continue
                    _, value = line.split("=", 1)
                    value = value.strip()
                    if value:
                        _add_source_root(value)
            if cfg.has_option("options.packages.find", "where"):
                where_raw = cfg.get("options.packages.find", "where")
                for line in where_raw.splitlines():
                    value = line.strip().strip(",")
                    if value:
                        _add_source_root(value)
        except Exception:
            pass

    return tuple(sorted(source_roots)), tuple(
        sorted(m for m in module_roots if m)
    )


def _should_skip_analysis_path(
    path: str, workspace_dir: str | None = None
) -> bool:
    abs_path = _normalize_realpath(path)
    if not abs_path:
        return True
    if not abs_path.endswith(".py"):
        return True

    base = os.path.basename(abs_path)
    if base.endswith((".pyc", ".pyo", ".pyd")):
        return True

    skip_dirs = {
        "__pycache__",
        ".git",
        ".svn",
        ".hg",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".nox",
        "node_modules",
        "build",
        "dist",
        "site-packages",
        "dist-packages",
        "tests",
        "test",
    }
    skip_prefixes = ("venv", ".venv", "env", ".env")
    skip_suffixes = (".egg-info", ".dist-info")
    parts = [p for p in abs_path.split(os.sep) if p]
    for part in parts:
        low = part.lower()
        if low in skip_dirs:
            return True
        if low.startswith(skip_prefixes):
            return True
        if low.endswith(skip_suffixes):
            return True

    ws = _normalize_realpath(workspace_dir)
    if ws:
        for source_root in _discover_workspace_hints(ws)[0]:
            if _is_path_under(abs_path, source_root):
                return False
        if _is_path_under(abs_path, ws):
            return False
    return False


def _relative_package_parts(
    file_path: str, workspace_dir: str | None
) -> list[str]:
    abs_file = _normalize_realpath(file_path)
    ws = _normalize_realpath(workspace_dir)
    if not abs_file or not ws:
        return []

    source_roots, _ = _discover_workspace_hints(ws)
    chosen_root = ""
    for root in source_roots:
        if _is_path_under(abs_file, root):
            if not chosen_root or len(root) > len(chosen_root):
                chosen_root = root
    if not chosen_root:
        chosen_root = ws

    try:
        rel = os.path.relpath(abs_file, chosen_root)
    except Exception:
        return []

    parts = [p for p in rel.split(os.sep) if p]
    if not parts:
        return []
    if parts[-1] == "__init__.py":
        candidate_parts = parts[:-1]
    else:
        candidate_parts = parts[:-1]

    package_parts: list[str] = []
    current_dir = chosen_root
    for part in candidate_parts:
        current_dir = os.path.join(current_dir, part)
        if os.path.isfile(os.path.join(current_dir, "__init__.py")):
            package_parts.append(_normalize_module_name(part))
        else:
            break
    return [p for p in package_parts if p]


def _resolve_relative_import_root(
    file_path: str, level: int, workspace_dir: str | None
) -> str:
    package_parts = _relative_package_parts(file_path, workspace_dir)
    if not package_parts:
        return ""
    anchor_parts = list(package_parts)
    if os.path.basename(file_path) != "__init__.py" and anchor_parts:
        # For a regular module file, level=1 refers to its containing package.
        steps_up = max(level - 1, 0)
    else:
        # For __init__.py, level=1 refers to the package itself.
        steps_up = max(level - 1, 0)
    if steps_up:
        anchor_parts = anchor_parts[: max(len(anchor_parts) - steps_up, 0)]
    return anchor_parts[0] if anchor_parts else ""


def _extract_imported_modules_from_source(
    source: str, file_path: str = "", workspace_dir: str | None = None
) -> set[str]:
    """Parse Python source and return normalized top-level imported modules."""
    modules: set[str] = set()
    try:
        tree = ast.parse(source, filename=file_path or "<memory>")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = _top_level_module_name(alias.name)
                    if top:
                        modules.add(top)
            elif isinstance(node, ast.ImportFrom):
                if node.level and node.level > 0:
                    rel_root = _resolve_relative_import_root(
                        file_path, node.level, workspace_dir
                    )
                    if rel_root:
                        modules.add(rel_root)
                elif node.module:
                    top = _top_level_module_name(node.module)
                    if top:
                        modules.add(top)
    except Exception:
        # Robust regex-based fallback if AST parsing fails (e.g. syntax error or newer Python version)
        # Handle 'import module1, module2 as alias'
        import_matches = re.findall(
            r"^\s*import\s+([\w\.,\s]+)", source, re.MULTILINE
        )
        for match in import_matches:
            for part in match.split(","):
                # Extract 'module1' from 'module1 as alias'
                mod = part.strip().split(" ")[0].strip()
                top = _top_level_module_name(mod)
                if top:
                    modules.add(top)

        # Handle 'from module import something'
        from_matches = re.findall(
            r"^\s*from\s+([\w\.]+)\s+import", source, re.MULTILINE
        )
        for mod in from_matches:
            top = _top_level_module_name(mod)
            if top:
                modules.add(top)

    dynamic_imports = re.findall(r"__import__\(['\"]([\w\.]+)['\"]\)", source)
    modules.update(
        [
            top
            for top in (_top_level_module_name(mod) for mod in dynamic_imports)
            if top
        ]
    )

    importlib_imports = re.findall(
        r"importlib\.import_module\(['\"]([\w\.]+)['\"]\)", source
    )
    modules.update(
        [
            top
            for top in (
                _top_level_module_name(mod) for mod in importlib_imports
            )
            if top
        ]
    )
    return modules


def _extract_imported_modules_from_file(
    file_path: str, workspace_dir: str | None = None
) -> set[str]:
    """Read a Python file and return normalized imported modules."""
    try:
        with open(file_path, encoding="utf-8") as f:
            source = f.read()
    except Exception:
        return set()
    return _extract_imported_modules_from_source(
        source,
        file_path=file_path,
        workspace_dir=workspace_dir,
    )


def _collect_workspace_module_roots(
    filtered_files: list[str], workspace_dir: str | None
) -> set[str]:
    """
    Build a conservative set of internal module roots from workspace files.
    Handles common src-layout aliases (src/, lib/, python/).
    """
    roots: set[str] = set()
    ws = _normalize_realpath(workspace_dir)
    source_roots, hinted_modules = _discover_workspace_hints(ws)
    roots.update(hinted_modules)
    for f in filtered_files:
        try:
            abs_f = _normalize_realpath(f)
            base = os.path.splitext(os.path.basename(abs_f))[0]
            if base and base != "__init__":
                roots.add(base)
            if not ws or not _is_path_under(abs_f, ws):
                continue
            package_parts = _relative_package_parts(abs_f, ws)
            if package_parts:
                roots.add(package_parts[0])

            candidate_roots = source_roots or (ws,)
            for root in candidate_roots:
                if not _is_path_under(abs_f, root):
                    continue
                rel = os.path.relpath(abs_f, root)
                parts = [p for p in rel.split(os.sep) if p]
                if not parts:
                    continue
                first = _normalize_module_name(parts[0])
                if first and first != "__pycache__":
                    roots.add(first)
                break
        except Exception:
            pass
    return {r for r in roots if r}


@functools.lru_cache(maxsize=1024)
def _classify_module_origin(module_name: str, workspace_dir: str) -> str:
    """
    Classify module origin:
    - stdlib: Python standard library / builtins
    - internal: module resolved under workspace_dir
    - third_party: resolved in site-packages/purelib/platlib/dist-packages
    - unknown: cannot resolve safely
    """
    if not module_name:
        return "unknown"
    if _is_stdlib_module(module_name):
        return "stdlib"
    try:
        import importlib.util
        import sysconfig

        ws = _normalize_realpath(workspace_dir)
        hinted_roots = set(_discover_workspace_hints(ws)[1])
        normalized_module = _top_level_module_name(module_name)
        if normalized_module and normalized_module in hinted_roots:
            return "internal"
        # Fast filesystem-based detection for local workspace modules that are not
        # importable from sys.path yet (common in src/ and lib/python layouts).
        source_roots = _discover_workspace_hints(ws)[0]
        if normalized_module:
            for root in source_roots:
                try:
                    pkg_init = os.path.join(
                        root, normalized_module, "__init__.py"
                    )
                    mod_file = os.path.join(root, f"{normalized_module}.py")
                    if os.path.isfile(pkg_init) or os.path.isfile(mod_file):
                        return "internal"
                except Exception:
                    continue
        spec = importlib.util.find_spec(module_name)
        if spec is None:
            return "unknown"
        origin = getattr(spec, "origin", None)
        if origin in ("built-in", "frozen"):
            return "stdlib"

        candidates: list[str] = []
        if origin:
            candidates.append(_normalize_realpath(origin))
        for loc in spec.submodule_search_locations or []:
            candidates.append(_normalize_realpath(loc))

        stdlib_path = _normalize_realpath(sysconfig.get_path("stdlib") or "")
        purelib_path = _normalize_realpath(sysconfig.get_path("purelib") or "")
        platlib_path = _normalize_realpath(sysconfig.get_path("platlib") or "")
        for c in candidates:
            if ws and _is_path_under(c, ws):
                return "internal"
            for root in source_roots:
                if root and _is_path_under(c, root):
                    return "internal"
            if stdlib_path and _is_path_under(c, stdlib_path):
                return "stdlib"
            if purelib_path and _is_path_under(c, purelib_path):
                return "third_party"
            if platlib_path and _is_path_under(c, platlib_path):
                return "third_party"
            if "site-packages" in c or "dist-packages" in c:
                return "third_party"

        return "unknown"
    except Exception:
        return "unknown"


def _check_module_installed(module: str) -> bool:
    """
    Check whether module is installed.
    Tries importlib.metadata (package name) and then importlib.util.find_spec (module name).
    """
    try:
        distribution(module)
        return True
    except (PackageNotFoundError, Exception):
        pass

    try:
        import importlib.util

        if importlib.util.find_spec(module) is not None:
            return True
    except Exception:
        pass

    return False


def _find_pip_executable(
    venv_path: str = None, workspace_dir: str = None
) -> tuple:
    """Locate pip executable with multiple fallback strategies.
    Return a tuple (program, prefix_args) where:
    - program: path to executable or 'python'
    - prefix_args: arguments to prefix ([] for direct pip, ['-m', 'pip'] for module)

    Strategies (in order):
    1. venv pip (Scripts/pip.exe or bin/pip)
    2. python -m pip from venv
    3. python -m system pip"""

    # Determine the path of the venv
    if venv_path:
        venv_dir = os.path.abspath(venv_path)
    elif workspace_dir:
        venv_dir = os.path.abspath(os.path.join(workspace_dir, "venv"))
    else:
        # Fallback: use python -m system pip
        return (sys.executable, ["-m", "pip"])

    is_windows = platform.system() == "Windows"
    bin_dir = os.path.join(venv_dir, "Scripts" if is_windows else "bin")
    pip_name = "pip.exe" if is_windows else "pip"
    pip_exe = os.path.join(bin_dir, pip_name)

    # Strategy 1: executable pip from venv
    if os.path.isfile(pip_exe):
        try:
            # Check that pip is executable
            result = subprocess.run(
                [pip_exe, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            if result.returncode == 0:
                return (pip_exe, [])
        except Exception:
            pass

    # Strategy 2: python -m pip from venv
    python_exe = os.path.join(
        bin_dir, "python.exe" if is_windows else "python"
    )
    if os.path.isfile(python_exe):
        try:
            result = subprocess.run(
                [python_exe, "-m", "pip", "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
            )
            if result.returncode == 0:
                return (python_exe, ["-m", "pip"])
        except Exception:
            pass

    # Strategy 3: python -m system pip
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        if result.returncode == 0:
            return (sys.executable, ["-m", "pip"])
    except Exception:
        pass

    # Fallback ultime
    return (sys.executable, ["-m", "pip"])


# --- Project-wide Dependency Collection & Requirements Generation ---


def collect_project_dependencies(
    workspace_dir: str, include_dev: bool = False
) -> set[str]:
    """
    Collect all third-party dependencies by scanning project files and imports.
    This is the core logic to replace VenvManager's fragmented detection.
    """
    workspace_dir = _normalize_realpath(workspace_dir)
    if not workspace_dir or not os.path.isdir(workspace_dir):
        return set()

    all_deps: set[str] = set()

    # 1. Scan configuration files (high priority, more accurate than imports)

    # requirements.txt / requirements.in (Very high priority, can skip full scan if found)
    reqs_found = False
    for req_file in ["requirements.txt", "requirements.in"]:
        path = os.path.join(workspace_dir, req_file)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith(("#", "-")):
                            # Basic parsing of requirement line
                            name = re.split(r"[<>=!~\s]", line)[0].strip()
                            if name:
                                all_deps.add(name)
                                reqs_found = True
            except Exception:
                pass

    # If we found explicit requirements, we can potentially skip the expensive scan
    # unless specific validation is requested. For now, we continue but mark it.

    # pyproject.toml
    pyproject_path = os.path.join(workspace_dir, "pyproject.toml")
    if os.path.isfile(pyproject_path):
        data = _load_toml_file(pyproject_path)
        # Standard [project] dependencies
        project = data.get("project", {})
        if isinstance(project, dict):
            deps = project.get("dependencies", [])
            if isinstance(deps, list):
                for d in deps:
                    name = re.split(r"[<>=!~\s]", str(d))[0].strip()
                    if name:
                        all_deps.add(name)
            if include_dev:
                opt_deps = project.get("optional-dependencies", {})
                if isinstance(opt_deps, dict):
                    for group in opt_deps.values():
                        if isinstance(group, list):
                            for d in group:
                                name = re.split(r"[<>=!~\s]", str(d))[
                                    0
                                ].strip()
                                if name:
                                    all_deps.add(name)

        # Poetry [tool.poetry.dependencies]
        tool = data.get("tool", {})
        if isinstance(tool, dict):
            poetry = tool.get("poetry", {})
            if isinstance(poetry, dict):
                p_deps = poetry.get("dependencies", {})
                if isinstance(p_deps, dict):
                    for name in p_deps.keys():
                        if name.lower() != "python":
                            all_deps.add(name)
                if include_dev:
                    d_deps = (
                        poetry.get("group", {})
                        .get("dev", {})
                        .get("dependencies", {})
                    )
                    if isinstance(d_deps, dict):
                        for name in d_deps.keys():
                            all_deps.add(name)
                    # Legacy poetry dev-dependencies
                    legacy_dev = poetry.get("dev-dependencies", {})
                    if isinstance(legacy_dev, dict):
                        for name in legacy_dev.keys():
                            all_deps.add(name)

    # setup.py (very basic regex as we shouldn't execute it)
    setup_py = os.path.join(workspace_dir, "setup.py")
    if os.path.isfile(setup_py):
        try:
            with open(setup_py, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Simple match for install_requires=[...]
            matches = re.findall(
                r"install_requires\s*=\s*\[(.*?)\]", content, re.DOTALL
            )
            for m in matches:
                for line in m.split(","):
                    line = line.strip().strip("\"'")
                    if line:
                        name = re.split(r"[<>=!~\s]", line)[0].strip()
                        if name:
                            all_deps.add(name)
        except Exception:
            pass

    # Pipfile
    pipfile_path = os.path.join(workspace_dir, "Pipfile")
    if os.path.isfile(pipfile_path):
        try:
            with open(
                pipfile_path, "r", encoding="utf-8", errors="ignore"
            ) as f:
                content = f.read()
            match = re.search(r"\[packages\](.*?)(?=\[|$)", content, re.DOTALL)
            if match:
                for line in match.group(1).splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        name = line.split("=")[0].strip().strip("\"'")
                        if name:
                            all_deps.add(name)
        except Exception:
            pass

    # 2. Scan imports in all Python files (fallback/validation)
    # OPTIMIZATION: If we already found dependencies in config files, we skip the slow full scan
    if reqs_found and all_deps:
        return all_deps

    modules_from_imports = set()
    workspace_python_files = []
    for root, dirs, files in os.walk(workspace_dir):
        # Skip common non-source directories
        dirs[:] = [
            d
            for d in dirs
            if d
            not in (
                ".venv",
                "venv",
                ".env",
                "env",
                "__pycache__",
                ".git",
                "build",
                "dist",
            )
        ]
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                workspace_python_files.append(file_path)
                try:
                    modules_from_imports.update(
                        _extract_imported_modules_from_file(
                            file_path, workspace_dir
                        )
                    )
                except Exception:
                    pass

    # Identify internal module roots to avoid misclassifying them as third-party
    internal_roots = _collect_workspace_module_roots(
        workspace_python_files, workspace_dir
    )

    # Filter and classify modules from imports
    for m in modules_from_imports:
        if m in internal_roots:
            continue
        origin = _classify_module_origin(m, workspace_dir)
        if origin in ("third_party", "unknown"):
            all_deps.add(m)

    return all_deps


def collect_internal_modules(workspace_dir: str) -> set[str]:
    """
    Collect internal project modules/packages referenced by imports.

    This is intended for build.include prefill during workspace initialization.
    It intentionally ignores third-party modules because auto-mapping already
    handles them elsewhere in the build pipeline.
    """
    workspace_dir = _normalize_realpath(workspace_dir)
    if not workspace_dir or not os.path.isdir(workspace_dir):
        return set()

    internal_modules: set[str] = set()
    workspace_python_files: list[str] = []

    for root, dirs, files in os.walk(workspace_dir):
        dirs[:] = [
            d
            for d in dirs
            if d
            not in (
                ".venv",
                "venv",
                ".env",
                "env",
                "__pycache__",
                ".git",
                "build",
                "dist",
                "tests",
                "test",
            )
        ]
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = os.path.join(root, file)
            workspace_python_files.append(file_path)
            try:
                imported = _extract_imported_modules_from_file(
                    file_path, workspace_dir
                )
            except Exception:
                continue
            for module_name in imported:
                if (
                    _classify_module_origin(module_name, workspace_dir)
                    == "internal"
                ):
                    top = _top_level_module_name(module_name)
                    if top:
                        internal_modules.add(top)

    return set(sorted(internal_modules))


def write_requirements_txt(
    workspace_dir: str,
    output_path: str | None = None,
    include_dev: bool = False,
) -> str | None:
    """
    Generate a requirements.txt file based on project analysis.
    Returns the path to the written file, or None on failure.
    """
    try:
        deps = collect_project_dependencies(
            workspace_dir, include_dev=include_dev
        )
        if not deps:
            return None

        if not output_path:
            output_path = os.path.join(workspace_dir, "requirements.txt")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("# Auto-generated by PyCompiler ARK DepsAnalyser\n")
            f.write(
                "# Generated from project imports and configuration files\n\n"
            )
            for dep in sorted(deps):
                f.write(f"{dep}\n")

        return output_path
    except Exception:
        return None
