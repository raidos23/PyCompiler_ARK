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

import functools
import configparser
import ast
import json
import os
import platform
import re
import subprocess
import yaml
from importlib.metadata import distribution, PackageNotFoundError

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication, QMessageBox

from Core.WidgetsCreator import ProgressDialog
from Core.i18n import log_with_level


def _log_append(gui, msg: str) -> None:
    try:
        text = str(msg)
    except Exception:
        text = msg
    level = "info"
    for emo, lvl in (
        ("❌", "error"),
        ("⚠️", "warning"),
        ("❗", "warning"),
        ("✅", "success"),
        ("ℹ️", "info"),
        ("⏩", "state"),
    ):
        if text.startswith(emo):
            level = lvl
            text = text[len(emo) :].lstrip()
            break
    log_with_level(gui, level, text)


# NOTE PRODUCTION-HARDENING:
# Les fonctionnalités non finalisées sont encapsulées dans des gardes afin de ne jamais
# faire échouer l'application. Les Plugins publiques restent stables; les chemins non
# implémentés renvoient silencieusement.


def _default_excluded_stdlib() -> set[str]:
    return {
        "sys",
        "os",
        "re",
        "subprocess",
        "json",
        "math",
        "time",
        "pathlib",
        "typing",
        "itertools",
        "functools",
        "collections",
        "asyncio",
        "importlib",
        "inspect",
        "logging",
        "argparse",
        "dataclasses",
        "unittest",
        "threading",
        "multiprocessing",
        "http",
        "urllib",
        "email",
        "socket",
        "ssl",
        "hashlib",
        "hmac",
        "gzip",
        "bz2",
        "lzma",
        "base64",
        "shutil",
        "tempfile",
        "glob",
        "fnmatch",
        "statistics",
        "pprint",
        "getpass",
        "uuid",
        "enum",
        "contextlib",
        "queue",
        "traceback",
        "warnings",
        "gc",
        "platform",
        "sysconfig",
        "pkgutil",
        "site",
        "venv",
        "sqlite3",
        "tkinter",
    }


def _load_excluded_stdlib() -> set[str]:
    default = _default_excluded_stdlib()
    mapping_path = os.path.join(os.path.dirname(__file__), "stblib.yml")
    if not os.path.isfile(mapping_path):
        return default
    try:
        with open(mapping_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        modules = None
        if isinstance(data, dict):
            modules = data.get("excluded_stdlib")
            if modules is None:
                modules = data.get("modules")
        elif isinstance(data, list):
            modules = data
        if not isinstance(modules, list):
            return default
        cleaned = [m.strip() for m in modules if isinstance(m, str) and m.strip()]
        return set(cleaned) or default
    except Exception:
        return default


# Liste explicite de modules de la bibliothèque standard à exclure (chargée du YAML)
EXCLUDED_STDLIB = _load_excluded_stdlib()


@functools.lru_cache(maxsize=256)
def _is_stdlib_module(module_name: str) -> bool:
    """
    Détermine si un module appartient à la bibliothèque standard Python.
    Combine une liste d'exclusion explicite et une détection basée sur importlib.util.find_spec.
    Résultats cachés pour éviter les appels répétés.
    """
    try:
        if module_name in EXCLUDED_STDLIB:
            return True
        import importlib.util
        import sys
        import sysconfig

        if module_name in sys.builtin_module_names:
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
                # os.path.commonpath peut lever si chemins sur volumes différents
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
def _discover_workspace_hints(workspace_dir: str | None) -> tuple[tuple[str, ...], tuple[str, ...]]:
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
    pyproject = _load_toml_file(pyproject_path) if os.path.isfile(pyproject_path) else {}
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
        setuptools = tool.get("setuptools", {}) if isinstance(tool, dict) else {}
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

    return tuple(sorted(source_roots)), tuple(sorted(m for m in module_roots if m))


def _should_skip_analysis_path(path: str, workspace_dir: str | None = None) -> bool:
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


def _relative_package_parts(file_path: str, workspace_dir: str | None) -> list[str]:
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
    except Exception:
        return modules

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = _top_level_module_name(alias.name)
                if top:
                    modules.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                rel_root = _resolve_relative_import_root(file_path, node.level, workspace_dir)
                if rel_root:
                    modules.add(rel_root)
            elif node.module:
                top = _top_level_module_name(node.module)
                if top:
                    modules.add(top)

    dynamic_imports = re.findall(r"__import__\(['\"]([\w\.]+)['\"]\)", source)
    modules.update(
        [top for top in (_top_level_module_name(mod) for mod in dynamic_imports) if top]
    )

    importlib_imports = re.findall(
        r"importlib\.import_module\(['\"]([\w\.]+)['\"]\)", source
    )
    modules.update(
        [top for top in (_top_level_module_name(mod) for mod in importlib_imports) if top]
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
        source_roots = _discover_workspace_hints(ws)[0]

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
    Vérifie si un module est installé via importlib.metadata (plus rPluginsde que subprocess pip show).
    """
    try:
        distribution(module)
        return True
    except PackageNotFoundError:
        return False
    except Exception:
        # Fallback: considérer comme non installé en cas d'erreur
        return False


def _find_pip_executable(venv_path: str = None, workspace_dir: str = None) -> tuple:
    """
    Localise l'exécutable pip avec plusieurs stratégies de fallback.
    Retourne un tuple (program, prefix_args) où:
    - program: chemin vers l'exécutable ou 'python'
    - prefix_args: arguments à préfixer ([] pour pip direct, ['-m', 'pip'] pour module)

    Stratégies (dans l'ordre):
    1. pip du venv (Scripts/pip.exe ou bin/pip)
    2. python -m pip du venv
    3. python -m pip du système
    """
    import sys

    # Déterminer le chemin du venv
    if venv_path:
        venv_dir = os.path.abspath(venv_path)
    elif workspace_dir:
        venv_dir = os.path.abspath(os.path.join(workspace_dir, "venv"))
    else:
        # Fallback: utiliser python -m pip du système
        return (sys.executable, ["-m", "pip"])

    is_windows = platform.system() == "Windows"
    bin_dir = os.path.join(venv_dir, "Scripts" if is_windows else "bin")
    pip_name = "pip.exe" if is_windows else "pip"
    pip_exe = os.path.join(bin_dir, pip_name)

    # Stratégie 1: pip exécutable du venv
    if os.path.isfile(pip_exe):
        try:
            # Vérifier que pip est exécutable
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

    # Stratégie 2: python -m pip du venv
    python_exe = os.path.join(bin_dir, "python.exe" if is_windows else "python")
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

    # Stratégie 3: python -m pip du système
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


def suggest_missing_dependencies(self):
    """
    Analyse les fichiers principaux à compiler, détecte les modules importés,
    vérifie leur présence dans le venv, et propose d'installer ceux qui manquent.
    """

    def _t(_key: str, fr: str, en: str) -> str:
        try:
            return self.tr(fr, en)
        except Exception:
            return en

    # Vérifie que le workspace ou le venv est bien sélectionné
    if not self.workspace_dir and not self.venv_path_manuel:
        _log_append(
            self,
            _t(
                "msg_no_workspace_or_venv_text",
                "❌ Workspace ou venv manquant. Sélectionnez-en un.",
                "❌ Workspace or venv missing. Please select one.",
            ),
        )
        try:
            box = QMessageBox(self)
            box.setWindowTitle(
                _t(
                    "msg_no_workspace_or_venv_title",
                    "Workspace ou venv manquant",
                    "Workspace or venv missing",
                )
            )
            box.setText(
                _t(
                    "msg_no_workspace_or_venv_text",
                    "Sélectionnez un Workspace ou un Venv pour analyser les dépendances.",
                    "Select a Workspace or a Venv to analyze dependencies.",
                )
            )
            btn_ws = box.addButton(
                _t("action_select_workspace", "Choisir Workspace", "Select Workspace"),
                QMessageBox.ActionRole,
            )
            btn_venv = box.addButton(
                _t("action_select_venv", "Choisir un Venv", "Select Venv"),
                QMessageBox.AcceptRole,
            )
            box.addButton(
                _t("action_cancel", "Annuler", "Cancel"), QMessageBox.RejectRole
            )
            box.exec()
            if box.clickedButton() == btn_ws:
                try:
                    self.select_workspace()
                except Exception:
                    pass
            elif box.clickedButton() == btn_venv:
                try:
                    self.select_venv_manually()
                except Exception:
                    pass
        except Exception:
            pass
        return
    modules = set()
    # Détermine la liste des fichiers à analyser (sélectionnés ou tous les fichiers du projet)
    files = self.selected_files if self.selected_files else self.python_files
    # Exclure les fichiers du venv et les dossiers cachés/__pycache__
    if self.venv_path_manuel:
        venv_dir = os.path.abspath(self.venv_path_manuel)
    else:
        venv_dir = os.path.abspath(os.path.join(self.workspace_dir, "venv"))
    filtered_files = []
    for f in files:
        abs_f = _normalize_realpath(f)
        try:
            if venv_dir and _is_path_under(abs_f, _normalize_realpath(venv_dir)):
                continue
        except Exception:
            pass
        if _should_skip_analysis_path(abs_f, getattr(self, "workspace_dir", None)):
            continue
        filtered_files.append(abs_f)

    # Créer une barre de progression pour l'analyse
    analysis_progress = None
    try:
        analysis_progress = ProgressDialog(
            self.tr("Analyse des dépendances", "Analyzing dependencies"), self
        )
        analysis_progress.set_message(
            self.tr("Analyse des fichiers Python...", "Analyzing Python files...")
        )
        analysis_progress.set_progress(0, len(filtered_files))
        analysis_progress.show()
    except Exception:
        pass

    # Analyse chaque fichier Python pour détecter les imports
    last_pump = 0
    for idx, file in enumerate(filtered_files):
        try:
            # Mettre à jour la progression
            if analysis_progress:
                file_name = os.path.basename(file)
                analysis_progress.set_message(
                    self.tr("Analyse de {file}...", "Analyzing {file}...").format(
                        file=file_name
                    )
                )
                analysis_progress.set_progress(idx, len(filtered_files))
            if idx - last_pump >= 50:
                QApplication.processEvents()
                last_pump = idx
            modules.update(
                _extract_imported_modules_from_file(
                    file,
                    workspace_dir=getattr(self, "workspace_dir", None),
                )
            )
        except Exception as e:
            _log_append(self, f"⚠️ Erreur analyse dépendances dans {file} : {e}")

    # Fermer la barre de progression d'analyse
    if analysis_progress:
        analysis_progress.set_message(self.tr("Analyse terminée", "Analysis completed"))
        analysis_progress.set_progress(len(filtered_files), len(filtered_files))
    # Classify imports as stdlib/internal/third-party/unknown.
    ws_root = _normalize_realpath(getattr(self, "workspace_dir", None) or "")
    internal_modules = _collect_workspace_module_roots(filtered_files, ws_root)
    # Mise à jour du message de progression
    if analysis_progress:
        analysis_progress.set_message(
            self.tr("Vérification des modules...", "Checking modules...")
        )

    suggestions = []
    category_stats = {"stdlib": 0, "internal": 0, "third_party": 0, "unknown": 0}
    for m in sorted(modules):
        if m in internal_modules:
            category = "internal"
        else:
            category = _classify_module_origin(m, ws_root)
            if category == "unknown" and m in internal_modules:
                category = "internal"
        category_stats[category] = category_stats.get(category, 0) + 1
        if category in ("third_party", "unknown"):
            suggestions.append(m)

    try:
        _log_append(
            self,
            "ℹ️ Imports classes: "
            f"stdlib={category_stats.get('stdlib', 0)}, "
            f"internal={category_stats.get('internal', 0)}, "
            f"third_party={category_stats.get('third_party', 0)}, "
            f"unknown={category_stats.get('unknown', 0)}",
        )
    except Exception:
        pass
    # Alerte spéciale pour tkinter (std lib optionnelle non installable via pip)
    try:
        import importlib.util as _il_util

        if "tkinter" in modules:
            if _il_util.find_spec("tkinter") is None:
                msg = (
                    "Le module tkinter n'est pas disponible dans votre environnement Python. "
                    "tkinter fait partie de la bibliothèque standard mais nécessite des paquets système et ne s'installe pas via pip.\n\n"
                    "Installez-le avec votre gestionnaire de paquets:\n"
                    "- Ubuntu/Debian: sudo apt install python3-tk\n"
                    "- Fedora: sudo dnf install python3-tkinter\n"
                    "- Arch: sudo pacman -S tk\n"
                    "- macOS: brew install tcl-tk (puis réinstallez Python avec le support Tk)\n"
                    "- Windows: réinstallez Python en incluant Tcl/Tk"
                )
                _log_append(self, f"ℹ️ {msg}")
                try:
                    QMessageBox.information(
                        self, self.tr("tkinter manquant", "Missing tkinter"), msg
                    )
                except Exception:
                    pass
    except Exception:
        pass
    if not suggestions:
        _log_append(self, "✅ Aucun module externe à installer détecté.")
        if analysis_progress:
            analysis_progress.close()
        return
    # Vérifie la présence des modules dans le venv (via pip show)
    # Utilise la fonction robuste de détection du pip
    if getattr(self, "use_system_python", False):
        pip_program, pip_prefix = _find_pip_executable(
            venv_path=None, workspace_dir=None
        )
    else:
        pip_program, pip_prefix = _find_pip_executable(
            venv_path=self.venv_path_manuel, workspace_dir=self.workspace_dir
        )
    try:
        _log_append(
            self, f"ℹ️ Utilisation de pip: {pip_program} {' '.join(pip_prefix)}"
        )
    except Exception:
        pass
    # Vérification des modules avec progression (préférer un seul pip list pour limiter le blocage UI)
    not_installed = []
    installed = set()
    try:
        cmd = [pip_program, *pip_prefix, "list", "--format=json"]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            try:
                data = json.loads(
                    result.stdout.decode("utf-8", errors="replace") or "[]"
                )
                for item in data:
                    name = str(item.get("name", "")).strip()
                    if name:
                        installed.add(name.lower().replace("_", "-"))
            except Exception:
                installed = set()
        else:
            installed = set()
    except Exception:
        installed = set()

    if installed:
        for idx, module in enumerate(suggestions):
            try:
                if analysis_progress:
                    analysis_progress.set_message(
                        self.tr(
                            "Vérification de {module}...", "Checking {module}..."
                        ).format(module=module)
                    )
                    analysis_progress.set_progress(idx, len(suggestions))
                if idx % 50 == 0:
                    QApplication.processEvents()
                key = module.lower().replace("_", "-")
                if key not in installed:
                    not_installed.append(module)
            except Exception as e:
                _log_append(
                    self, f"⚠️ Erreur lors de la vérification du module {module} : {e}"
                )
    else:
        for idx, module in enumerate(suggestions):
            try:
                if analysis_progress:
                    analysis_progress.set_message(
                        self.tr(
                            "Vérification de {module}...", "Checking {module}..."
                        ).format(module=module)
                    )
                    analysis_progress.set_progress(idx, len(suggestions))
                if idx % 20 == 0:
                    QApplication.processEvents()

                cmd = [pip_program, *pip_prefix, "show", module]
                result = subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                if result.returncode != 0:
                    not_installed.append(module)
            except Exception as e:
                _log_append(
                    self, f"⚠️ Erreur lors de la vérification du module {module} : {e}"
                )

    # Fermer la barre de progression d'analyse
    if analysis_progress:
        analysis_progress.close()
    # Si des modules sont manquants, propose l'installation automatique
    if not_installed:
        _log_append(
            self,
            "❗ Modules manquants dans le venv : " + ", ".join(sorted(not_installed)),
        )
        # Demande à l'utilisateur s'il souhaite installer automatiquement les modules manquants
        reply = QMessageBox.question(
            self,
            self.tr("Installer les dépendances", "Install dependencies"),
            self.tr(
                "Installer automatiquement les modules manquants ?\n{mods}",
                "Automatically install missing modules?\n{mods}",
            ).format(mods=", ".join(not_installed)),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self._dep_install_index = 0
            self._dep_install_list = not_installed
            # Programme pip pour QProcess: si pip du venv existe, l'utiliser; sinon python -m pip
            try:
                self._dep_pip_program = pip_program
                self._dep_pip_prefix = list(pip_prefix)
            except Exception:
                self._dep_pip_program = sys.executable
                self._dep_pip_prefix = ["-m", "pip"]
            self.dep_progress_dialog = ProgressDialog(
                self.tr("Installation des dépendances", "Installing dependencies"), self
            )
            self.dep_progress_dialog.set_message(
                self.tr("Installation de {m}...", "Installing {m}...").format(
                    m=not_installed[0]
                )
            )
            self.dep_progress_dialog.set_progress(0, len(not_installed))
            self.dep_progress_dialog.show()
            self._install_next_dependency()
    else:
        _log_append(
            self, "✅ Tous les modules nécessaires sont déjà installés dans le venv."
        )


# Installation automatique des dépendances manquantes (récursif)
def _install_next_dependency(self):
    # Si tous les modules ont été installés, termine le processus
    if self._dep_install_index >= len(self._dep_install_list):
        self.dep_progress_dialog.set_message(
            self.tr("Installation terminée.", "Installation completed.")
        )
        self.dep_progress_dialog.set_progress(
            len(self._dep_install_list), len(self._dep_install_list)
        )
        self.dep_progress_dialog.close()
        _log_append(self, "✅ Tous les modules manquants ont été installés.")
        return
    module = self._dep_install_list[self._dep_install_index]
    msg = f"Installation de {module}... ({self._dep_install_index+1}/{len(self._dep_install_list)})"
    self.dep_progress_dialog.set_message(msg)
    self.dep_progress_dialog.progress.setRange(
        0, 0
    )  # indéterminé pendant l'installation
    process = QProcess(self)
    # Utilise le programme et préfixe déterminés (pip du venv ou 'python -m pip')
    try:
        import sys as _sys

        default_prog = _sys.executable
    except Exception:
        default_prog = "python"
    program = getattr(self, "_dep_pip_program", None) or default_prog
    prefix = list(getattr(self, "_dep_pip_prefix", ["-m", "pip"]))
    process.setProgram(program)
    process.setArguments(prefix + ["install", module])
    process.readyReadStandardOutput.connect(lambda: self._on_dep_pip_output(process))
    process.readyReadStandardError.connect(
        lambda: self._on_dep_pip_output(process, error=True)
    )
    process.finished.connect(
        lambda code, status: self._on_dep_pip_finished(process, code, status)
    )
    process.start()


# Affiche la sortie de pip dans la ProgressDialog et les logs
def _on_dep_pip_output(self, process, error=False):
    data = (
        process.readAllStandardError().data().decode()
        if error
        else process.readAllStandardOutput().data().decode()
    )
    if hasattr(self, "dep_progress_dialog") and self.dep_progress_dialog:
        lines = data.strip().splitlines()
        if lines:
            self.dep_progress_dialog.set_message(lines[-1])
    _log_append(self, data)


# Callback après l'installation d'un module (pip)
def _on_dep_pip_finished(self, process, code, status):
    module = self._dep_install_list[self._dep_install_index]
    if code == 0:
        _log_append(self, f"✅ {module} installé.")
    else:
        _log_append(self, f"❌ Erreur installation {module} (code {code})")
    # Met à jour la progression globale
    self._dep_install_index += 1
    self.dep_progress_dialog.progress.setRange(0, len(self._dep_install_list))
    self.dep_progress_dialog.set_progress(
        self._dep_install_index, len(self._dep_install_list)
    )
    self._install_next_dependency()
