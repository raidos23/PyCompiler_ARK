# Copyright (C) 2025

"""
Détection automatique des modules sensibles et application des hooks/plugins
pour les moteurs, basée sur un mapping JSON piloté par les moteurs (ENGINES).

Règles clés:
- La détection est automatique et non désactivable par l'utilisateur.
- Priorité à requirements.txt s'il existe dans le workspace, sinon scan des imports.
- Les actions sont dérivées du JSON (clé = id du moteur).
- Rapport optionnel pouvant être écrit dans le workspace.
"""
from __future__ import annotations

import ast
import importlib
import importlib.resources as ilr
import json
import os
import re
from typing import Optional

from engine_sdk.utils import log_with_level, log_i18n_level

# Optional access to registered engines for discovery
try:
    from ..engines_loader import registry as engines_registry  # type: ignore
except Exception:  # pragma: no cover
    engines_registry = None  # type: ignore

# Validation optionnelle via JSON Schema (si disponible)
try:
    import jsonschema  # type: ignore
except Exception:
    jsonschema = None

# Import utilitaire d'exclusion stdlib
try:
    from ..deps_analyser import _is_stdlib_module
except Exception:  # fallback au cas où

    def _is_stdlib_module(name: str) -> bool:
        try:
            import importlib.util
            import sys
            import sysconfig

            if name in sys.builtin_module_names:
                return True
            spec = importlib.util.find_spec(name)
            if not spec:
                return False
            if getattr(spec, "origin", None) in ("built-in", "frozen"):
                return True
            stdlib_path = os.path.realpath(sysconfig.get_path("stdlib") or "")
            if getattr(spec, "origin", None):
                p = os.path.realpath(spec.origin)
                try:
                    return os.path.commonpath([p, stdlib_path]) == stdlib_path
                except Exception:
                    return False
            return False
        except Exception:
            return False


# Cache mapping (path -> data)
_MAPPING_CACHE: dict[str, dict[str, dict[str, Optional[str]]]] = {}
# Collect validation warnings to surface them later in compute_auto_for_engine
_VALIDATION_WARNINGS: list[str] = []

# Aliases import_name -> package_name (mapping keys potentiels). Extensible à l'exécution.
ALIASES_IMPORT_TO_PACKAGE: dict[str, str] = {}

# Aliases package_name -> import_name canonique utilisé pour PyInstaller --collect-all. Extensible à l'exécution.
PACKAGE_TO_IMPORT_NAME: dict[str, str] = {}


# Fonctions d'extension d'alias (plug-and-play)
def register_import_alias(import_name: str, package_name: str) -> None:
    try:
        if (
            isinstance(import_name, str)
            and isinstance(package_name, str)
            and import_name
        ):
            ALIASES_IMPORT_TO_PACKAGE[import_name.lower()] = package_name
    except Exception:
        pass


def register_package_import_name(package_name: str, import_name: str) -> None:
    try:
        if (
            isinstance(package_name, str)
            and isinstance(import_name, str)
            and package_name
        ):
            PACKAGE_TO_IMPORT_NAME[package_name] = import_name
    except Exception:
        pass


def register_aliases(
    *,
    import_to_package: Optional[dict[str, str]] = None,
    package_to_import: Optional[dict[str, str]] = None,
) -> None:
    try:
        if import_to_package:
            for k, v in import_to_package.items():
                register_import_alias(k, v)
        if package_to_import:
            for k, v in package_to_import.items():
                register_package_import_name(k, v)
    except Exception:
        pass


# Bilingual translation helper (fallback to English if self.tr is unavailable)
def _tr(self, fr: str, en: str) -> str:
    try:
        tr = getattr(self, "tr", None)
        if callable(tr):
            return tr(fr, en)
    except Exception:
        pass
    return en


# Normalisation des noms (pour matcher mapping keys insensibles à la casse/aux tirets)
def _norm(s: str) -> str:
    return s.replace("_", "-").lower().strip()


def _read_json_file(path: str) -> dict[str, dict[str, Optional[str]]]:
    with open(path, encoding="utf-8-sig") as f:  # support BOM
        data = json.load(f)
    # Validation JSON Schema optionnelle (si schéma disponible)
    if jsonschema is not None:
        try:
            repo_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
            )
            schema_path = os.path.join(
                repo_root, "Core", "Auto_Builder", "schemas", "mapping.schema.json"
            )
            if os.path.isfile(schema_path):
                with open(schema_path, encoding="utf-8") as sf:
                    schema = json.load(sf)
                jsonschema.validate(instance=data, schema=schema)
        except Exception as e:
            # Schema errors are downgraded to warnings to preserve plug-and-play
            _VALIDATION_WARNINGS.append(f"Invalid mapping file '{path}': {e}")
    # Normalize and validate structure: dict[str, dict]
    normed: dict[str, dict[str, Optional[str]]] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            if not isinstance(k, str):
                _VALIDATION_WARNINGS.append(
                    f"Mapping key is not a string in '{path}': {k!r}"
                )
                continue
            if isinstance(v, dict):
                normed[k] = v
            else:
                # Accept simple forms by coercion where possible
                # e.g., {"numpy": {"pyinstaller": ["--collect-all numpy"]}} is expected
                _VALIDATION_WARNINGS.append(
                    f"Mapping entry for '{k}' should be an object; got {type(v).__name__} in '{path}'"
                )
    else:
        _VALIDATION_WARNINGS.append(f"Top-level mapping is not an object in '{path}'")
    return normed


def _load_mapping(
    base_dir: str, workspace_dir: Optional[str] = None
) -> tuple[dict[str, dict[str, Optional[str]]], Optional[str]]:
    """Charge le mapping via la variable d'environnement uniquement.
    Retourne (mapping, chemin_utilisé) ou ({}, None) si non défini.
    """
    # ENV-only mapping loader; legacy locations disabled
    try:
        env_path = os.environ.get("PYCOMPILER_MAPPING")
        if env_path and os.path.isfile(env_path):
            cached = _MAPPING_CACHE.get(env_path)
            if cached is not None:
                return cached, env_path
            mapping = _read_json_file(env_path)
            _MAPPING_CACHE[env_path] = mapping
            return mapping, env_path
    except Exception:
        pass
    return {}, None


def _parse_requirements(requirements_path: str) -> set[str]:
    """Extract package names from requirements.txt, handling URLs, VCS, and extras.
    - Supports lines like 'package==1.2', 'package[extra]', 'name @ https://...', 'git+https://...#egg=name'
    - Ignores comments, markers, and includes (-r ...)
    """
    found: set[str] = set()
    if not os.path.isfile(requirements_path):
        return found
    rx_egg = re.compile(r"[#&]egg=([A-Za-z0-9_.\-]+)")
    rx_name = re.compile(r"^([A-Za-z0-9_.\-]+)")
    try:
        with open(requirements_path, encoding="utf-8", errors="ignore") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("-r ") or line.startswith("--requirement "):
                    # Do not process nested files here; keep it simple and robust
                    continue
                # Strip markers
                if ";" in line:
                    line = line.split(";", 1)[0].strip()
                # VCS/URL with egg
                m = rx_egg.search(line)
                if m:
                    found.add(m.group(1))
                    continue
                # Name @ URL
                if "@" in line:
                    name = line.split("@", 1)[0].strip()
                    m2 = rx_name.match(name)
                    if m2:
                        found.add(m2.group(1))
                        continue
                # Wheel/archives
                if line.endswith((".whl", ".zip", ".tar.gz", ".tgz")):
                    base = os.path.basename(line)
                    # Try to extract distribution name prefix
                    part = base.split("-", 1)[0]
                    if part:
                        found.add(part)
                        continue
                # Strip versions
                for sep in ("===", "==", ">=", "<=", "~=", ">", "<"):
                    if sep in line:
                        line = line.split(sep, 1)[0].strip()
                        break
                # Extras
                if "[" in line and "]" in line:
                    base = line.split("[", 1)[0]
                    found.add(base)
                    found.add(line)  # keep original as hint
                else:
                    m3 = rx_name.match(line)
                    if m3:
                        found.add(m3.group(1))
    except Exception:
        return found
    return found


def _scan_imports(py_files: list[str], workspace_dir: str) -> set[str]:
    """Analyse les fichiers .py et retourne les noms de modules importés (top-level).
    - Ignore venv/, __pycache__/ et dossiers cachés
    - Ignore fichiers trop volumineux (>1.5 Mo) pour robustesse
    - Tolérant aux erreurs d'encodage/syntaxe
    """
    found: set[str] = set()
    # Exclure venv interne
    venv_dir = os.path.abspath(os.path.join(workspace_dir, "venv"))
    size_cap = 1_500_000
    for file in py_files:
        af = os.path.abspath(file)
        try:
            if af.startswith(venv_dir):
                continue
            parts = af.split(os.sep)
            if any(part.startswith(".") or part == "__pycache__" for part in parts):
                continue
            try:
                if os.path.getsize(af) > size_cap:
                    continue
            except Exception:
                pass
            with open(af, encoding="utf-8", errors="ignore") as f:
                src = f.read()
            try:
                tree = ast.parse(src, filename=af)
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        found.add(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        found.add(node.module.split(".")[0])
            # Imports dynamiques
            for m in re.findall(r"__import__\(['\"]([\w\.]+)['\"]\)", src):
                found.add(m.split(".")[0])
            for m in re.findall(
                r"importlib\.import_module\(['\"]([\w\.]+)['\"]\)", src
            ):
                found.add(m.split(".")[0])
        except Exception:
            continue
    # Filtre stdlib et modules internes (fichiers du projet)
    internal_names = {os.path.splitext(os.path.basename(p))[0] for p in py_files}
    result = {m for m in found if not _is_stdlib_module(m) and m not in internal_names}
    return result


def _match_modules_to_mapping(
    modules: set[str], mapping: dict[str, dict[str, Optional[str]]]
) -> tuple[dict[str, dict[str, Optional[str]]], dict[str, str]]:
    """Retourne deux dicts:
    - matched: {package_key_in_mapping: mapping_entry}
    - package_to_import_name: {package_key_in_mapping: import_name}
    """
    # Build lookup index insensible à la casse et aux tirets
    index = {_norm(name): name for name in mapping.keys()}

    matched: dict[str, dict[str, Optional[str]]] = {}
    pkg_to_import: dict[str, str] = {}

    # 1) modules peuvent être des noms d'import (e.g. cv2, PIL, sklearn)
    for mod in modules:
        norm_mod = _norm(mod)
        # map import alias -> package key attendu
        pkg_guess = ALIASES_IMPORT_TO_PACKAGE.get(mod.lower())
        if pkg_guess and _norm(pkg_guess) in index:
            key = index[_norm(pkg_guess)]
            matched[key] = mapping[key]
            import_name = PACKAGE_TO_IMPORT_NAME.get(key, mod)
            pkg_to_import[key] = import_name
            continue
        # direct match si le même nom est référencé comme package (ex: numpy, scipy, lxml)
        if norm_mod in index:
            key = index[norm_mod]
            matched[key] = mapping[key]
            import_name = PACKAGE_TO_IMPORT_NAME.get(key, mod)
            pkg_to_import[key] = import_name

    return matched, pkg_to_import


# Default builder for unknown engines: interpret mapping values as final CLI args
# Supported value types per package entry and engine_id key:
# - str: a single CLI argument (e.g., "--enable-feature=foo")
# - list[str]: multiple CLI arguments
# - dict: expects keys like "args" or "flags" mapping to str | list[str]
# - True: ignored by default (requires engine-specific semantics); provide a custom builder
# The default builder performs simple de-duplication while preserving order.
from typing import Optional as _Optional  # local alias to avoid confusion


def _default_builder_for_engine(engine_id: str):
    def _builder(
        matched: dict[str, dict[str, _Optional[str]]], pkg_to_import: dict[str, str]
    ) -> list[str]:
        out: list[str] = []
        for pkg, entry in matched.items():
            val = entry.get(engine_id)
            if val is None:
                continue
            tmpl_import = pkg_to_import.get(pkg, pkg)
            if isinstance(val, str):
                out.append(val.replace("{import_name}", tmpl_import))
            elif isinstance(val, list):
                out.extend([str(x).replace("{import_name}", tmpl_import) for x in val])
            elif isinstance(val, dict):
                a = val.get("args") or val.get("flags")
                if isinstance(a, list):
                    out.extend(
                        [str(x).replace("{import_name}", tmpl_import) for x in a]
                    )
                elif isinstance(a, str):
                    out.append(str(a).replace("{import_name}", tmpl_import))
            elif val is True:
                # No generic meaning; skip unless a specific builder is registered
                pass
        # de-dup while preserving order
        seen = set()
        dedup: list[str] = []
        for a in out:
            if a not in seen:
                seen.add(a)
                dedup.append(a)
        return dedup

    return _builder


# --------- Engine builders registry (plug-and-play) ---------
_ENGINE_BUILDERS: dict[str, callable] = {}


def register_auto_builder(engine_id: str, builder) -> None:
    """Register a builder function for a given engine_id.
    The builder signature must be (matched: dict, pkg_to_import: dict) -> List[str].
    """
    if not engine_id or not callable(builder):
        return
    _ENGINE_BUILDERS[engine_id] = builder


def _maybe_load_plugin_auto_builder(engine_id: str) -> None:
    """Optionally load a plugin-provided auto builder for engine_id.
    Tries to import '<engine_id>.auto_plugins' without failing app logic.
    """
    try:
        mod = importlib.import_module(f"{engine_id}.auto_plugins")
        auto_builder = getattr(mod, "AUTO_BUILDER", None)
        if callable(auto_builder):
            register_auto_builder(engine_id, auto_builder)
            return
        get_fn = getattr(mod, "get_auto_builder", None)
        if callable(get_fn):
            cb = get_fn()
            if callable(cb):
                register_auto_builder(engine_id, cb)
                return
        reg_fn = getattr(mod, "register_auto_builder", None)
        if callable(reg_fn):
            reg_fn(register_auto_builder)
            return
    except Exception:
        return


def _write_report_if_enabled(self, report: dict):
    """Ecrit un rapport JSON si activé via attribut ou variable d'env (écriture atomique)."""
    try:
        should = (
            bool(getattr(self, "generate_auto_detection_report", False))
            or os.environ.get("PYCOMPILER_AUTO_REPORT") == "1"
        )
        if not should:
            return
        out_path = os.path.join(
            self.workspace_dir, ".pycompiler_auto_modules_report.json"
        )
        # Atomic write
        import tempfile

        d = os.path.dirname(out_path)
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass
        fd, tmp = tempfile.mkstemp(prefix=".auto_report_", dir=d)
        try:
            with open(fd, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            try:
                os.replace(tmp, out_path)
            except Exception:
                with open(out_path, "w", encoding="utf-8") as f2:
                    json.dump(report, f2, indent=2, ensure_ascii=False)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
        try:
            log_i18n_level(
                self,
                "info",
                f"Rapport auto-modules écrit: {out_path}",
                f"Auto-modules report written: {out_path}",
            )
        except Exception:
            pass
    except Exception as e:
        try:
            log_i18n_level(
                self,
                "warning",
                f"Échec écriture rapport auto-modules: {e}",
                f"Failed to write auto-modules report: {e}",
            )
        except Exception:
            pass


def _detect_modules_preferring_requirements(self) -> tuple[set[str], str]:
    """Retourne (modules_detectés, source: 'requirements'|'pyproject'|'imports')."""
    # 1) requirements.{txt|in} dans le workspace (configurable via env PYCOMPILER_REQ_FILES)
    req_names = os.environ.get(
        "PYCOMPILER_REQ_FILES", "requirements.txt,requirements.in"
    ).split(",")
    for name in [n.strip() for n in req_names if n.strip()]:
        req_path = os.path.join(self.workspace_dir, name)
        if os.path.isfile(req_path):
            mods = _parse_requirements(req_path)
            if mods:
                return mods, "requirements"
    # 2) pyproject.toml dependencies (PEP 621) / poetry
    try:
        import tomllib as _tomllib  # Python 3.11+
    except Exception:
        try:
            import tomli as _tomllib  # pyright: ignore[reportMissingImports] # backport
        except Exception:
            _tomllib = None
    try:
        pyproj = os.path.join(self.workspace_dir, "pyproject.toml")
        if _tomllib is not None and os.path.isfile(pyproj):
            with open(pyproj, "rb") as f:
                data = _tomllib.load(f)
            mods: set[str] = set()
            # PEP 621
            proj = data.get("project") or {}
            deps = proj.get("dependencies") or []
            if isinstance(deps, list):
                for d in deps:
                    if isinstance(d, str) and d:
                        mods.add(
                            d.split(";", 1)[0]
                            .split("[", 1)[0]
                            .split("==", 1)[0]
                            .split(">=", 1)[0]
                            .split("<=", 1)[0]
                            .split("~=", 1)[0]
                            .split(">", 1)[0]
                            .split("<", 1)[0]
                            .strip()
                        )
            # poetry
            tool = data.get("tool") or {}
            poetry = tool.get("poetry") or {}
            deps2 = poetry.get("dependencies") or {}
            if isinstance(deps2, dict):
                for k in deps2.keys():
                    if isinstance(k, str) and k and k != "python":
                        mods.add(k)
            if mods:
                return mods, "pyproject"
    except Exception:
        pass
    # 3) fallback: scan imports
    py_files = (
        self.selected_files
        if getattr(self, "selected_files", None)
        else getattr(self, "python_files", [])
    )
    mods = _scan_imports(py_files, self.workspace_dir)
    return mods, "imports"


def _match_with_requirements_aware(
    modules: set[str], mapping: dict[str, dict[str, Optional[str]]]
) -> tuple[dict[str, dict[str, Optional[str]]], dict[str, str]]:
    """Essaye de matcher d'abord sur package names (requirements), sinon via alias import."""
    # D'abord, essayer correspondance directe sur package (utile pour Pillow, opencv, scikit-learn)
    index = {_norm(name): name for name in mapping.keys()}
    matched: dict[str, dict[str, Optional[str]]] = {}
    pkg_to_import: dict[str, str] = {}

    for mod in modules:
        # Le set 'modules' peut contenir des noms de package (requirements) avec ou sans extras
        base = mod
        if "[" in base and "]" in base:
            base = base.split("[", 1)[0]
        norm = _norm(base)
        if norm in index:
            k = index[norm]
            matched[k] = mapping[k]
            import_name = PACKAGE_TO_IMPORT_NAME.get(k, base)
            pkg_to_import[k] = import_name

    # Compléter via alias d'import pour ceux non trouvés
    rem_imports = {m for m in modules if m not in matched}
    add, add_imp = _match_modules_to_mapping(rem_imports, mapping)
    matched.update(add)
    pkg_to_import.update(add_imp)
    return matched, pkg_to_import


def compute_for_all(
    self, engine_ids: Optional[list[str]] = None
) -> dict[str, list[str]]:
    """
    Calcule les arguments auto pour tous les moteurs (plug-and-play).
    - engine_ids: liste optionnelle d'identifiants de moteurs à traiter. Si None,
      on détecte automatiquement:
        * moteurs enregistrés dans _ENGINE_BUILDERS
        * moteurs avec un mapping engine_plugins/<engine_id>/mapping.json
        * moteurs embarqués utils/engines/<engine_id>/mapping.json
    Retourne un dict: { engine_id: List[str] }.
    """
    # Construire la liste ordonnée des moteurs à traiter
    ordered: list[str] = []
    if engine_ids:
        # préserve l'ordre fourni et déduplique
        seen: set[str] = set()
        for e in engine_ids:
            if e and e not in seen:
                seen.add(e)
                ordered.append(e)
    else:
        # 0) moteurs enregistrés via le registry central s'ils existent
        try:
            if engines_registry is not None:
                for e in engines_registry.available_engines():
                    if e and e not in ordered:
                        ordered.append(e)
                        _maybe_load_plugin_auto_builder(e)
        except Exception:
            pass
        # 1) moteurs déjà enregistrés dans _ENGINE_BUILDERS
        try:
            for e in _ENGINE_BUILDERS.keys():
                if e and e not in ordered:
                    ordered.append(e)
        except Exception:
            pass
        # 2) moteurs sous ENGINES/<engine_id>/mapping.json (plug-and-play)
        try:
            project_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
            )
            engines_root = os.path.join(project_root, "ENGINES")
            if os.path.isdir(engines_root):
                for name in sorted(os.listdir(engines_root)):
                    d = os.path.join(engines_root, name)
                    if os.path.isdir(d) and os.path.isfile(
                        os.path.join(d, "mapping.json")
                    ):
                        if name not in ordered:
                            ordered.append(name)
                            _maybe_load_plugin_auto_builder(name)
        except Exception:
            pass
    # Calculer pour chaque moteur
    results: dict[str, list[str]] = {}
    for e in ordered:
        try:
            args = compute_auto_for_engine(self, e) or []
        except Exception:
            args = []
        results[e] = args
    return results


def _load_engine_package_mapping(
    engine_id: str,
) -> tuple[dict[str, dict[str, Optional[str]]], Optional[str]]:
    """Charge le mapping spécifique au moteur depuis plusieurs emplacements, avec priorités:
    1) mapping.json embarqué dans le package du moteur importé (engine_id)
    2) ENGINES/<engine_id>/mapping.json (fichiers du projet)
    3) (optionnel) chemin défini par l'env PYCOMPILER_MAPPING (fusionné)
    Retourne (mapping_combiné, chemin_principal_utilisé)
    """
    combined: dict[str, dict[str, Optional[str]]] = {}
    used: Optional[str] = None

    # 1) mapping intégré dans le package du moteur (importé par engines_loader)
    try:
        pkg = importlib.import_module(engine_id)
        with ilr.as_file(ilr.files(pkg).joinpath("mapping.json")) as p:
            p2 = str(p)
            if os.path.isfile(p2):
                try:
                    data_pkg = _read_json_file(p2)
                    combined.update(data_pkg)
                    used = used or p2
                except Exception as e:
                    _VALIDATION_WARNINGS.append(
                        f"Invalid embedded mapping for engine '{engine_id}' at {p2}: {e}"
                    )
    except Exception:
        pass

    # 2) mapping dans ENGINES/<engine_id>/mapping.json (filesystem projet)
    try:
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
        )
        engines_dir = os.path.join(project_root, "ENGINES", engine_id, "mapping.json")
        if os.path.isfile(engines_dir):
            try:
                data_ext = _read_json_file(engines_dir)
                for k, v in data_ext.items():
                    if k not in combined:
                        combined[k] = v
                used = used or engines_dir
            except Exception as e:
                _VALIDATION_WARNINGS.append(
                    f"Invalid mapping for engine '{engine_id}' at {engines_dir}: {e}"
                )
    except Exception:
        pass

    # 3) mapping via variable d'environnement (fusion, priorité la plus faible)
    try:
        env_path = os.environ.get("PYCOMPILER_MAPPING")
        if env_path and os.path.isfile(env_path):
            try:
                data_env = _read_json_file(env_path)
                for k, v in data_env.items():
                    if k not in combined:
                        combined[k] = v
                used = used or env_path
            except Exception as e:
                _VALIDATION_WARNINGS.append(
                    f"Invalid mapping from PYCOMPILER_MAPPING for engine '{engine_id}' at {env_path}: {e}"
                )
    except Exception:
        pass

    # Fusion optionnelle d'alias déclarés via "__aliases__"
    try:
        aliases = combined.get("__aliases__")  # type: ignore[index]
        if isinstance(aliases, dict):
            itp = aliases.get("import_to_package") or aliases.get("import2package")
            if isinstance(itp, dict):
                for k, v in itp.items():
                    if isinstance(k, str) and isinstance(v, str):
                        register_import_alias(k, v)
            pti = aliases.get("package_to_import_name") or aliases.get("package2import")
            if isinstance(pti, dict):
                for k, v in pti.items():
                    if isinstance(k, str) and isinstance(v, str):
                        register_package_import_name(k, v)
            try:
                del combined["__aliases__"]
            except Exception:
                pass
    except Exception:
        pass

    return combined, used


def compute_auto_for_engine(self, engine_id: str) -> list[str]:
    """Calcule les arguments auto pour un moteur donné (plug-and-play)."""
    try:
        os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir))
        getattr(self, "workspace_dir", None)
        # Charge uniquement le mapping spécifique moteur (package)
        eng_mapping, eng_used_path = _load_engine_package_mapping(engine_id)
        mapping = dict(eng_mapping)
        try:
            if eng_used_path:
                log_i18n_level(
                    self,
                    "info",
                    f"Mapping spécifique moteur ({engine_id}): {eng_used_path}",
                    f"Engine-specific mapping ({engine_id}): {eng_used_path}",
                )
            # Emit any validation warnings collected during mapping load
            while _VALIDATION_WARNINGS:
                w = _VALIDATION_WARNINGS.pop(0)
                try:
                    log_with_level(self, "warning", w)
                except Exception:
                    pass
        except Exception:
            pass
    except Exception as e:
        try:
            log_i18n_level(
                self,
                "warning",
                f"Mapping hooks/plugins introuvable: {e}",
                f"Mapping hooks/plugins not found: {e}",
            )
        except Exception:
            pass
        return []

    detected, source = _detect_modules_preferring_requirements(self)
    matched, pkg_to_import = _match_with_requirements_aware(detected, mapping)
    builder = _ENGINE_BUILDERS.get(engine_id) or _default_builder_for_engine(engine_id)
    try:
        if engine_id not in _ENGINE_BUILDERS:
            log_i18n_level(
                self,
                "info",
                f"Builder générique utilisé pour le moteur '{engine_id}'.",
                f"Generic builder used for engine '{engine_id}'.",
            )
    except Exception:
        pass

    try:
        args = builder(matched, pkg_to_import)
    except Exception as e:
        args = []
        try:
            log_i18n_level(
                self,
                "warning",
                f"Erreur constructeur auto-args pour '{engine_id}': {e}",
                f"Auto-args builder error for '{engine_id}': {e}",
            )
        except Exception:
            pass

    # Logging
    try:
        log_i18n_level(
            self,
            "info",
            f"Auto-détection des modules sensibles ({engine_id}) activée.",
            f"Auto-detection of sensitive modules ({engine_id}) enabled.",
        )
        log_i18n_level(
            self, "info", f"   Source détection: {source}", f"   Detection source: {source}"
        )
        if detected:
            log_i18n_level(
                self,
                "info",
                "   Modules détectés: " + ", ".join(sorted(detected)),
                "   Detected modules: " + ", ".join(sorted(detected)),
            )
        else:
            log_i18n_level(
                self,
                "info",
                "   Aucun module externe détecté.",
                "   No external modules detected.",
            )
        if args:
            log_i18n_level(
                self,
                "info",
                f"   Options {engine_id} ajoutées: " + " ".join(args),
                f"   {engine_id} options added: " + " ".join(args),
            )
        else:
            log_i18n_level(
                self,
                "info",
                f"   Aucune option {engine_id} supplémentaire requise d'après le mapping.",
                f"   No additional {engine_id} options required from mapping.",
            )
    except Exception:
        pass

    # Rapport optionnel
    report = {
        "source": source,
        "detected_modules": sorted(detected),
        "applied": {
            engine_id: args,
        },
    }
    _write_report_if_enabled(self, report)

    return args
