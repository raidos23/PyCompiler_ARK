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

"""
ConfigEditorService — logique métier pure pour l'éditeur de configuration avancé.

Ce module ne contient aucune dépendance Qt. Il est consommé par
Ui/Gui/Dialogs/AdvancedConfigEditor.py pour le parsing, la validation,
le diff et la sérialisation des fichiers YAML/JSON de configuration.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Lecture / écriture de fichiers
# ---------------------------------------------------------------------------


def read_text(path: str) -> str:
    """Lire le contenu textuel d'un fichier. Retourne '' en cas d'erreur."""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def write_text(path: str, content: str) -> None:
    """Écrire du texte dans un fichier, en créant les répertoires parents si nécessaire."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# Parsing YAML / JSON
# ---------------------------------------------------------------------------


def safe_parse_yaml(text: str) -> bool:
    """Retourne True si le texte est un YAML valide."""
    try:
        yaml.safe_load(text)
        return True
    except Exception:
        return False


def safe_parse_json(text: str) -> bool:
    """Retourne True si le texte est un JSON valide."""
    try:
        json.loads(text)
        return True
    except Exception:
        return False


def parse_text(text: str, is_yaml: bool) -> tuple[bool, Any, str]:
    """Parser le texte en une valeur structurée.

    Returns:
        (ok, data, error_message)
    """
    try:
        if is_yaml:
            data = yaml.safe_load(text) if text.strip() else {}
        else:
            data = json.loads(text) if text.strip() else {}
        return True, data, ""
    except Exception as exc:
        return False, None, str(exc)


def format_text(text: str, is_yaml: bool) -> tuple[bool, str, str]:
    """Formater le contenu YAML ou JSON.

    Returns:
        (ok, formatted_text, error_message)
    """
    ok, data, err = parse_text(text, is_yaml)
    if not ok:
        return False, text, err
    try:
        if is_yaml:
            return (
                True,
                yaml.safe_dump(data or {}, allow_unicode=True, sort_keys=False),
                "",
            )
        return True, json.dumps(data or {}, ensure_ascii=False, indent=2) + "\n", ""
    except Exception as exc:
        return False, text, str(exc)


# ---------------------------------------------------------------------------
# Moteur de diff interne (sans dépendances externes)
# ---------------------------------------------------------------------------


def _build_lcs_table(before: list[str], after: list[str]) -> list[list[int]]:
    """Construire la table LCS pour un diff ligne à ligne."""
    before_len = len(before)
    after_len = len(after)
    table = [[0] * (after_len + 1) for _ in range(before_len + 1)]
    for before_idx in range(before_len - 1, -1, -1):
        for after_idx in range(after_len - 1, -1, -1):
            if before[before_idx] == after[after_idx]:
                table[before_idx][after_idx] = table[before_idx + 1][after_idx + 1] + 1
            else:
                table[before_idx][after_idx] = max(
                    table[before_idx + 1][after_idx], table[before_idx][after_idx + 1]
                )
    return table


def _build_diff_ops(before: list[str], after: list[str]) -> list[tuple[str, str]]:
    """Générer les opérations de diff sans outil externe."""
    table = _build_lcs_table(before, after)
    ops: list[tuple[str, str]] = []
    before_idx = 0
    after_idx = 0

    while before_idx < len(before) and after_idx < len(after):
        if before[before_idx] == after[after_idx]:
            ops.append(("equal", before[before_idx]))
            before_idx += 1
            after_idx += 1
        elif table[before_idx + 1][after_idx] >= table[before_idx][after_idx + 1]:
            ops.append(("delete", before[before_idx]))
            before_idx += 1
        else:
            ops.append(("insert", after[after_idx]))
            after_idx += 1

    while before_idx < len(before):
        ops.append(("delete", before[before_idx]))
        before_idx += 1

    while after_idx < len(after):
        ops.append(("insert", after[after_idx]))
        after_idx += 1

    return ops


def _group_diff_ops(
    ops: list[tuple[str, str]], context: int = 3
) -> list[list[tuple[str, str]]]:
    """Regrouper les opérations en hunks de diff unifié avec contexte."""
    change_indexes = [
        idx for idx, (op, _) in enumerate(ops) if op in {"delete", "insert"}
    ]
    if not change_indexes:
        return []

    hunks: list[list[tuple[str, str]]] = []
    start = max(change_indexes[0] - context, 0)
    end = min(change_indexes[0] + context + 1, len(ops))

    for idx in change_indexes[1:]:
        next_start = max(idx - context, 0)
        next_end = min(idx + context + 1, len(ops))
        if next_start <= end:
            end = max(end, next_end)
            continue
        hunks.append(ops[start:end])
        start = next_start
        end = next_end

    hunks.append(ops[start:end])
    return hunks


def _format_unified_range(start: int, length: int) -> str:
    if length == 0:
        return f"{start},0"
    if length == 1:
        return str(start)
    return f"{start},{length}"


def render_unified_diff(
    before: str,
    after: str,
    fromfile: str = "original",
    tofile: str = "modified",
    context: int = 3,
) -> str:
    """Produire un diff unifié avec le moteur interne ARK."""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    ops = _build_diff_ops(before_lines, after_lines)
    hunks = _group_diff_ops(ops, context=context)

    if not hunks:
        return ""

    rendered: list[str] = [f"--- {fromfile}", f"+++ {tofile}"]
    before_line = 1
    after_line = 1

    for hunk in hunks:
        hunk_before_start = before_line
        hunk_after_start = after_line
        hunk_before_len = 0
        hunk_after_len = 0
        hunk_lines: list[str] = []

        for op, line in hunk:
            if op == "equal":
                hunk_lines.append(f" {line}")
                before_line += 1
                after_line += 1
                hunk_before_len += 1
                hunk_after_len += 1
            elif op == "delete":
                hunk_lines.append(f"-{line}")
                before_line += 1
                hunk_before_len += 1
            elif op == "insert":
                hunk_lines.append(f"+{line}")
                after_line += 1
                hunk_after_len += 1

        rendered.append(
            "@@ -"
            + _format_unified_range(hunk_before_start, hunk_before_len)
            + " +"
            + _format_unified_range(hunk_after_start, hunk_after_len)
            + " @@"
        )
        rendered.extend(hunk_lines)

    return "\n".join(rendered)


def render_colored_diff(before: str, after: str, context: int = 3) -> str:
    """Produire un diff compact lisible sans en-têtes git."""
    ops = _build_diff_ops(before.splitlines(), after.splitlines())
    if not any(op in {"delete", "insert"} for op, _ in ops):
        return ""

    rendered: list[str] = []
    equal_buffer: list[str] = []

    for op, line in ops:
        if op == "equal":
            equal_buffer.append(line)
            continue

        if equal_buffer:
            if rendered and len(equal_buffer) > context * 2:
                head = equal_buffer[:context]
                tail = equal_buffer[-context:]
                rendered.extend(f"= {item}" for item in head)
                rendered.append("...")
                rendered.extend(f"= {item}" for item in tail)
            else:
                rendered.extend(f"= {item}" for item in equal_buffer)
            equal_buffer.clear()

        if op == "delete":
            rendered.append(f"D {line}")
        elif op == "insert":
            rendered.append(f"A {line}")

    if equal_buffer:
        if rendered and len(equal_buffer) > context:
            rendered.extend(f"= {item}" for item in equal_buffer[:context])
            rendered.append("...")
        else:
            rendered.extend(f"= {item}" for item in equal_buffer)

    return "\n".join(rendered)


# ---------------------------------------------------------------------------
# Validation de contenu
# ---------------------------------------------------------------------------


def flatten_keys(data: Any, prefix: str = "") -> list[str]:
    """Aplatir récursivement les clés d'un dict/list en chemins pointés."""
    lines: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            k = str(key)
            path = f"{prefix}.{k}" if prefix else k
            lines.append(path)
            lines.extend(flatten_keys(value, path))
    elif isinstance(data, list):
        for idx, value in enumerate(data):
            path = f"{prefix}[{idx}]"
            lines.append(path)
            lines.extend(flatten_keys(value, path))
    return lines


def validate_payload(file_id: str, data: Any) -> tuple[list[str], list[str]]:
    """Valider les données selon le type de fichier de configuration.

    Returns:
        (errors, warnings)
    """
    errs: list[str] = []
    warns: list[str] = []

    if not isinstance(data, dict):
        errs.append("Root must be an object/map.")
        return errs, warns

    if file_id == "ark":
        allowed_top = {
            "project",
            "workspace",
            "dependencies",
            "environment_manager",
            "build",
            "plugins",
        }
        unknown = sorted(k for k in data.keys() if k not in allowed_top)
        if unknown:
            warns.append("Unknown top-level keys: " + ", ".join(unknown))

        # Validation de 'project'
        project = data.get("project")
        if project is not None:
            if not isinstance(project, dict):
                errs.append("project must be an object.")
            else:
                for k in ("name", "version", "entry"):
                    v = project.get(k)
                    if v is not None and not isinstance(v, str):
                        errs.append(f"project.{k} must be a string.")

        # Validation de 'workspace'
        workspace_cfg = data.get("workspace")
        if workspace_cfg is not None:
            if not isinstance(workspace_cfg, dict):
                errs.append("workspace must be an object.")
            else:
                exclude = workspace_cfg.get("exclude")
                if exclude is not None and (
                    not isinstance(exclude, list)
                    or not all(isinstance(item, str) for item in exclude)
                ):
                    errs.append("workspace.exclude must be a list of strings.")

        build = data.get("build")
        if build is not None and not isinstance(build, dict):
            errs.append("build must be an object.")
        if isinstance(build, dict):
            ep = build.get("entrypoint")
            if ep is not None and not isinstance(ep, str):
                errs.append("build.entrypoint must be a string or null.")
            if isinstance(ep, str) and not ep.strip():
                warns.append("build.entrypoint is empty.")
            exclude = build.get("exclude")
            if exclude is not None and (
                not isinstance(exclude, list)
                or not all(isinstance(item, str) for item in exclude)
            ):
                errs.append("build.exclude must be a list of strings.")

        deps = data.get("dependencies")
        if deps is not None and not isinstance(deps, dict):
            errs.append("dependencies must be an object.")
        if isinstance(deps, dict):
            req_files = deps.get("requirements_files")
            if req_files is not None and (
                not isinstance(req_files, list)
                or not all(isinstance(item, str) for item in req_files)
            ):
                errs.append(
                    "dependencies.requirements_files must be a list of strings."
                )
            autogen = deps.get("auto_generate_from_imports")
            if autogen is not None and not isinstance(autogen, bool):
                errs.append(
                    "dependencies.auto_generate_from_imports must be a boolean."
                )

        env = data.get("environment_manager")
        if env is not None and not isinstance(env, dict):
            errs.append("environment_manager must be an object.")
        if isinstance(env, dict):
            priority = env.get("priority")
            if priority is not None and (
                not isinstance(priority, list)
                or not all(isinstance(item, str) for item in priority)
            ):
                errs.append("environment_manager.priority must be a list of strings.")
            for flag in ("auto_detect", "fallback_to_pip"):
                if flag in env and not isinstance(env.get(flag), bool):
                    errs.append(f"environment_manager.{flag} must be a boolean.")

    elif file_id == "bcasl":
        file_patterns = data.get("file_patterns")
        if file_patterns is not None and (
            not isinstance(file_patterns, list)
            or not all(isinstance(item, str) for item in file_patterns)
        ):
            errs.append("file_patterns must be a list of strings.")

        exclude_patterns = data.get("exclude_patterns")
        if exclude_patterns is not None and (
            not isinstance(exclude_patterns, list)
            or not all(isinstance(item, str) for item in exclude_patterns)
        ):
            errs.append("exclude_patterns must be a list of strings.")

        options = data.get("options")
        if options is not None and not isinstance(options, dict):
            errs.append("options must be an object.")
        if isinstance(options, dict):
            if "enabled" in options and not isinstance(options.get("enabled"), bool):
                errs.append("options.enabled must be a boolean.")

        plugins = data.get("plugins")
        if plugins is not None and not isinstance(plugins, dict):
            errs.append("plugins must be an object.")
        if isinstance(plugins, dict):
            for pid, cfg in plugins.items():
                if not isinstance(cfg, dict):
                    errs.append(f"plugins.{pid} must be an object.")
                    continue
                if "enabled" in cfg and not isinstance(cfg.get("enabled"), bool):
                    errs.append(f"plugins.{pid}.enabled must be a boolean.")
                if "priority" in cfg and not isinstance(cfg.get("priority"), int):
                    errs.append(f"plugins.{pid}.priority must be an integer.")

        plugin_order = data.get("plugin_order")
        if plugin_order is not None and (
            not isinstance(plugin_order, list)
            or not all(isinstance(item, str) for item in plugin_order)
        ):
            errs.append("plugin_order must be a list of strings.")

    elif file_id == "pref":
        mode = data.get("venv_mode")
        if mode is not None and mode not in ("system", "venv"):
            errs.append("venv_mode must be 'system' or 'venv'.")
        venv_path = data.get("venv_path")
        if venv_path is not None and not isinstance(venv_path, str):
            errs.append("venv_path must be a string or null.")
        if mode == "venv" and not isinstance(venv_path, str):
            warns.append("venv_mode='venv' but venv_path is empty.")

    return errs, warns


def make_default_content(
    file_id: str, is_yaml: bool, workspace_dir: str | None = None
) -> str:
    """Construire le contenu par défaut pour un type de fichier donné."""
    if file_id == "ark":
        try:
            from Core.Configs import DEFAULT_CONFIG

            return yaml.safe_dump(DEFAULT_CONFIG, allow_unicode=True, sort_keys=False)
        except Exception:
            pass
    if file_id == "pref":
        payload = {"venv_mode": "system", "venv_path": None}
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if file_id == "bcasl":
        if workspace_dir:
            try:
                from bcasl.Loader import _load_workspace_config  # type: ignore

                data = _load_workspace_config(Path(workspace_dir))
                return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)
            except Exception:
                pass
        payload = {
            "file_patterns": ["**/*.py"],
            "exclude_patterns": ["**/__pycache__/**", ".venv/**", "venv/**"],
            "options": {
                "enabled": True,
                "sandbox": True,
                "iter_files_cache": True,
            },
            "plugins": {},
            "plugin_order": [],
        }
        return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)

    return "" if is_yaml else "{}\n"
