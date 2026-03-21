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

import importlib
import sys

import pytest

pytest.importorskip("PySide6")

from Core.deps_analyser.analyser import (
    _classify_module_origin,
    _collect_workspace_module_roots,
    _discover_workspace_hints,
    _extract_imported_modules_from_file,
    _extract_imported_modules_from_source,
    _resolve_relative_import_root,
    _should_skip_analysis_path,
)

_STUB_PREFIX = "deps_stub_"


@pytest.fixture(autouse=True)
def _isolate_deps_analyser_test_state():
    before = {name for name in sys.modules if name.startswith(_STUB_PREFIX)}
    _discover_workspace_hints.cache_clear()
    _classify_module_origin.cache_clear()
    yield
    for name in list(sys.modules):
        if name.startswith(_STUB_PREFIX) and name not in before:
            sys.modules.pop(name, None)
    _discover_workspace_hints.cache_clear()
    _classify_module_origin.cache_clear()


def test_discover_workspace_hints_reads_pyproject_and_setup_cfg(tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "demo-app"

[tool.poetry]
name = "demo_poetry"

[[tool.poetry.packages]]
include = "demo_pkg"
from = "src"
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "setup.cfg").write_text(
        """
[metadata]
name = demo_cfg

[options]
package_dir =
    = lib/python

[options.packages.find]
where =
    lib/python
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "src" / "demo_pkg").mkdir(parents=True)
    (tmp_path / "lib" / "python" / "demo_cfg").mkdir(parents=True)

    _discover_workspace_hints.cache_clear()
    source_roots, module_roots = _discover_workspace_hints(str(tmp_path))

    assert any(root.endswith("src") for root in source_roots)
    assert any(root.endswith("lib/python") for root in source_roots)
    assert "demo_pkg" in module_roots
    assert "demo_app" in module_roots
    assert "demo_poetry" in module_roots
    assert "demo_cfg" in module_roots


def test_collect_workspace_module_roots_supports_src_and_lib_python_layouts(
    tmp_path,
) -> None:
    src_pkg = tmp_path / "src" / "appcore"
    src_pkg.mkdir(parents=True)
    (src_pkg / "__init__.py").write_text("", encoding="utf-8")
    (src_pkg / "service.py").write_text("import requests\n", encoding="utf-8")

    lib_pkg = tmp_path / "lib" / "python" / "helpers"
    lib_pkg.mkdir(parents=True)
    (lib_pkg / "__init__.py").write_text("", encoding="utf-8")
    (lib_pkg / "tools.py").write_text("import rich\n", encoding="utf-8")

    _discover_workspace_hints.cache_clear()
    roots = _collect_workspace_module_roots(
        [str(src_pkg / "service.py"), str(lib_pkg / "tools.py")],
        str(tmp_path),
    )

    assert "appcore" in roots
    assert "helpers" in roots


def test_should_skip_analysis_path_filters_venv_caches_and_artifacts(tmp_path) -> None:
    cases = [
        tmp_path / ".venv" / "lib" / "python3.11" / "site-packages" / "pkg" / "x.py",
        tmp_path / "build" / "generated.py",
        tmp_path / "__pycache__" / "x.py",
        tmp_path / ".pytest_cache" / "x.py",
    ]

    for path in cases:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        assert _should_skip_analysis_path(str(path), str(tmp_path)) is True

    normal_file = tmp_path / "src" / "demo" / "main.py"
    normal_file.parent.mkdir(parents=True, exist_ok=True)
    normal_file.write_text("", encoding="utf-8")
    assert _should_skip_analysis_path(str(normal_file), str(tmp_path)) is False


def test_resolve_relative_import_root_handles_nested_package_chain(tmp_path) -> None:
    pkg = tmp_path / "src" / "demo_pkg" / "subpkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "demo_pkg" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    module = pkg / "module.py"
    module.write_text("from ..utils import helper\nfrom . import local\n", encoding="utf-8")

    _discover_workspace_hints.cache_clear()
    assert _resolve_relative_import_root(str(module), 1, str(tmp_path)) == "demo_pkg"
    assert _resolve_relative_import_root(str(module), 2, str(tmp_path)) == "demo_pkg"


def test_classify_module_origin_marks_workspace_package_as_internal(tmp_path) -> None:
    pkg = tmp_path / "src" / "localpkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")

    _discover_workspace_hints.cache_clear()
    _classify_module_origin.cache_clear()

    assert _classify_module_origin("localpkg", str(tmp_path)) == "internal"
    assert _classify_module_origin("json", str(tmp_path)) == "stdlib"


def test_extract_imported_modules_from_source_handles_relative_and_dynamic_imports(
    tmp_path,
) -> None:
    pkg = tmp_path / "src" / "demo_pkg" / "subpkg"
    pkg.mkdir(parents=True)
    (tmp_path / "src" / "demo_pkg" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    file_path = pkg / "module.py"

    source = """
import requests
from rich.console import Console
from . import local_helpers
from ..utils import helper

mod = __import__("yaml")
other = importlib.import_module("httpx._main")
""".strip()

    _discover_workspace_hints.cache_clear()
    modules = _extract_imported_modules_from_source(
        source,
        file_path=str(file_path),
        workspace_dir=str(tmp_path),
    )

    assert {"requests", "rich", "demo_pkg", "yaml", "httpx"} <= modules


def test_extract_imported_modules_from_file_uses_workspace_context(tmp_path) -> None:
    pkg = tmp_path / "lib" / "python" / "mypkg" / "sub"
    pkg.mkdir(parents=True)
    (tmp_path / "lib" / "python" / "mypkg" / "__init__.py").write_text(
        "", encoding="utf-8"
    )
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    module = pkg / "feature.py"
    module.write_text(
        """
from ..core import service
import importlib
plugin = importlib.import_module("pluggy")
""".strip(),
        encoding="utf-8",
    )

    _discover_workspace_hints.cache_clear()
    modules = _extract_imported_modules_from_file(str(module), workspace_dir=str(tmp_path))

    assert "mypkg" in modules
    assert "pluggy" in modules


def test_deps_analyser_stub_modules_are_isolated_from_sys_modules(
    tmp_path, monkeypatch
) -> None:
    pkg = tmp_path / f"{_STUB_PREFIX}pkg"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.import_module(f"{_STUB_PREFIX}pkg")

    assert f"{_STUB_PREFIX}pkg" in sys.modules
