# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Headless command handlers shared by multiple CLI frontends.

The goal is to keep behavior identical between fallback and dedicated modes by
reusing the same implementation for common commands.
"""

import sys

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
    workspace_apply_payload,
    workspace_config_auto_payload,
    workspace_init_payload,
)
from .output import error, plain


def _emit_json_raw(payload: object) -> None:
    """Write JSON payload directly to stdout without rich/click formatting layers."""
    text = emit_json(payload)
    sys.stdout.write(text)
    if not text.endswith("\n"):
        sys.stdout.write("\n")
    sys.stdout.flush()


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
        _emit_json_raw(payload)
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
    workspace = (
        normalize_path(
            first_positional([token for token in args if not token.startswith("-")])
        )
        or "."
    )
    # L'initialisation unifie création dossier/config/bcasl/pref (et venv optionnel).
    payload = workspace_init_payload(workspace, with_venv=with_venv)
    if as_json:
        _emit_json_raw(payload)
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
    workspace = (
        normalize_path(
            first_positional(
                [token for token in clean_args if not token.startswith("-")]
            )
        )
        or "."
    )
    # Détection auto de l'entrypoint + mise à jour config workspace.
    payload = workspace_config_auto_payload(workspace, entrypoint=entrypoint)
    if as_json:
        _emit_json_raw(payload)
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


def run_workspace_apply(args: list[str]) -> int:
    """Apply a complete workspace setup flow in a single command."""
    as_json = "--json" in args
    with_venv = "--with-venv" in args
    auto_config = "--no-auto-config" not in args
    inspect_files = "--no-inspect-files" not in args
    apply_venv_pref = "--no-apply-venv-pref" not in args
    apply_engine_configs = "--no-apply-engine-configs" not in args
    strict = "--strict" in args
    require_entrypoint = "--require-entrypoint" in args or strict

    try:
        entrypoint, clean_args = extract_option_value(args, "--entrypoint")
    except ValueError as exc:
        error(str(exc))
        return EXIT_USAGE_ERROR

    workspace = (
        normalize_path(
            first_positional(
                [token for token in clean_args if not token.startswith("-")]
            )
        )
        or "."
    )

    payload = workspace_apply_payload(
        workspace,
        with_venv=with_venv,
        entrypoint=entrypoint,
        auto_config=auto_config,
        inspect_files=inspect_files,
        apply_venv_pref=apply_venv_pref,
        apply_engine_configs=apply_engine_configs,
        require_entrypoint=require_entrypoint,
    )
    inspect_payload = payload.get("inspect", {}) if isinstance(payload, dict) else {}
    entrypoint_value = (
        inspect_payload.get("entrypoint") if isinstance(inspect_payload, dict) else None
    )
    venv_state = payload.get("venv", {}) if isinstance(payload, dict) else {}
    engine_config_state = (
        payload.get("engine_configs", {}) if isinstance(payload, dict) else {}
    )
    precheck_failed = bool(payload.get("require_entrypoint") and not entrypoint_value)
    has_workspace_error = bool(payload.get("error")) and not precheck_failed

    if as_json:
        _emit_json_raw(payload)
    else:
        if has_workspace_error:
            error(str(payload.get("error")))
        plain(f"Workspace: {workspace}")
        plain("  Init: OK")
        plain(f"  Auto-config: {'yes' if auto_config else 'no'}")
        plain(f"  Entrypoint: {entrypoint_value or '(none)'}")
        plain(f"  Python files: {inspect_payload.get('python_file_count', 0)}")
        plain(f"  Venv pref applied: {'yes' if venv_state.get('applied') else 'no'}")
        plain(
            "  Engine configs loaded: "
            + f"{engine_config_state.get('loaded_count', 0)}/{engine_config_state.get('total_count', 0)}"
        )
        if with_venv:
            plain(
                "  Venv: "
                + str(
                    (
                        (payload.get("init", {}) if isinstance(payload, dict) else {})
                        or {}
                    ).get("venv_path")
                    or "(not created)"
                )
            )
        if precheck_failed:
            error("Workspace entrypoint is required but missing.")

    if has_workspace_error:
        return EXIT_WORKSPACE_INVALID
    if precheck_failed:
        return EXIT_PRECHECK_FAILED
    return EXIT_OK
