# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Headless command handlers shared by multiple CLI frontends.

The goal is to keep behavior identical between fallback and dedicated modes by
reusing the same implementation for common commands.
"""

from .contracts import (
    EXIT_OK,
    EXIT_PRECHECK_FAILED,
    EXIT_USAGE_ERROR,
    EXIT_WORKSPACE_INVALID,
    first_positional,
    normalize_path,
    render_checks_text,
    render_workspace_init_result,
)
from .headless_ops import (
    ci_smoke_payload,
    emit_json,
    workspace_config_auto_payload,
    workspace_init_payload,
)
from .output import error, plain


def extract_option_value(args: list[str], option: str) -> tuple[str | None, list[str]]:
    """Extract an option value and return the remaining argument list."""
    # Parsing minimaliste mais déterministe: on garde la dernière occurrence si répétée.
    clean: list[str] = []
    value: str | None = None
    i = 0
    while i < len(args):
        token = args[i]
        if token == option:
            if i + 1 >= len(args):
                raise ValueError(f"Missing value after {option}")
            value = args[i + 1]
            i += 2
            continue
        clean.append(token)
        i += 1
    return value, clean


def run_check(args: list[str]) -> int:
    """Execute the strict CI/CD check command in headless mode."""
    # On garde les mêmes valeurs par défaut que la commande click `check`.
    workspace = normalize_path(first_positional(args))
    as_json = "--json" in args
    require_entrypoint = "--no-require-entrypoint" not in args
    fail_only = "--all-checks" not in args
    strict = "--no-strict" not in args
    # La payload reste la source de vérité: l'affichage n'en est qu'une projection.
    payload = ci_smoke_payload(
        workspace=workspace,
        require_entrypoint=require_entrypoint,
    )
    if as_json:
        plain(emit_json(payload))
    else:
        render_checks_text(
            "PyCompiler ARK Check",
            list(payload.get("checks", [])),
            fail_only=fail_only,
        )
    # En mode strict, un seul check en échec doit faire tomber la commande.
    if strict and not payload.get("ok"):
        return EXIT_PRECHECK_FAILED
    return EXIT_OK


def run_init(args: list[str]) -> int:
    """Initialize a workspace and return a standardized exit code."""
    # Le rendu texte suit le format partagé pour limiter les divergences d'UX.
    as_json = "--json" in args
    with_venv = "--with-venv" in args
    workspace = normalize_path(
        first_positional([token for token in args if not token.startswith("-")])
    ) or "."
    # L'initialisation unifie création dossier/config/bcasl/pref (et venv optionnel).
    payload = workspace_init_payload(workspace, with_venv=with_venv)
    if as_json:
        plain(emit_json(payload))
    else:
        for item in payload.get("steps", []):
            status = str(item.get("status", "")).upper() or "INFO"
            plain(f"[{status}] {item.get('message')}")
        if payload.get("ok"):
            render_workspace_init_result(payload)
    if not payload.get("ok"):
        error(str(payload.get("error", "Workspace init failed")))
        return EXIT_WORKSPACE_INVALID
    return EXIT_OK


def run_config_auto(args: list[str]) -> int:
    """Auto-configure workspace build settings and return an exit code."""
    as_json = "--json" in args
    try:
        entrypoint, clean_args = extract_option_value(args, "--entrypoint")
    except ValueError as exc:
        error(str(exc))
        return EXIT_USAGE_ERROR
    workspace = normalize_path(
        first_positional([token for token in clean_args if not token.startswith("-")])
    ) or "."
    # Détection auto de l'entrypoint + mise à jour config workspace.
    payload = workspace_config_auto_payload(workspace, entrypoint=entrypoint)
    if as_json:
        plain(emit_json(payload))
    else:
        if payload.get("ok"):
            plain(f"Workspace: {payload.get('workspace')}")
            plain(f"  Entrypoint: {payload.get('entrypoint') or '(none)'}")
            plain(
                "  Requirements found: "
                + (", ".join(payload.get("requirements_files_found", [])) or "none")
            )
            plain(f"  Config updated: {payload.get('config_path')}")
    if not payload.get("ok"):
        error(str(payload.get("error", "Workspace auto-config failed")))
        return EXIT_WORKSPACE_INVALID
    return EXIT_OK
