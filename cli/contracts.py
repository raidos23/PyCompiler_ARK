# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Shared CLI contracts and rendering helpers.

This module centralizes stable exit codes and lightweight text rendering helpers
used by multiple CLI entry paths (click, fallback, dedicated).
"""

from pathlib import Path
from typing import Iterable

from .output import plain

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_PRECHECK_FAILED = 3
EXIT_WORKSPACE_INVALID = 4
EXIT_ENGINE_NOT_FOUND = 5

# Convention de codes de sortie CLI:
# 0  : succès
# 1  : erreur runtime non prévue
# 2  : erreur d'usage/arguments
# 3  : échec d'un garde-fou (precheck/strict)
# 4  : workspace invalide
# 5  : moteur introuvable
# Le fait de centraliser ici évite les divergences entre click/fallback/dedicated.


def normalize_path(raw: str | None) -> str | None:
    """Return a normalized absolute path, or ``None`` when input is empty."""
    # Normalisation défensive pour aligner les sorties entre les différents frontends CLI.
    if not raw:
        return None
    try:
        return str(Path(raw).expanduser().resolve(strict=False))
    except Exception:
        return raw


def first_positional(args: Iterable[str]) -> str | None:
    """Return the first non-option token from an argument sequence."""
    for token in args:
        if not token.startswith("-"):
            return token
    return None


def render_checks_text(
    title: str,
    checks: list[dict[str, object]],
    *,
    fail_only: bool = False,
) -> None:
    """Render check results in the canonical human-readable text format."""
    # Format texte volontairement stable pour:
    # 1) lisibilité humaine dans le terminal
    # 2) docs/screenshots cohérents
    # 3) éviter les régressions UX entre frontends CLI
    plain(title)
    shown = 0
    for check in checks:
        ok = bool(check.get("ok"))
        if fail_only and ok:
            continue
        status = "OK" if ok else "FAIL"
        plain(f"  [{status}] {check.get('name')}: {check.get('message') or ''}")
        shown += 1
    if fail_only and shown == 0:
        plain("  [OK] no failing checks")


def render_workspace_init_result(payload: dict[str, object]) -> None:
    """Render the canonical workspace initialization summary."""
    # Rendu détaillé conservé pour faciliter le diagnostic des bootstraps workspace en CI/CD.
    plain(f"Workspace: {payload.get('workspace')}")
    plain(f"  Config: {payload.get('config_path')}")
    plain(f"  BCASL: {payload.get('bcasl_path') or '(not created)'}")
    plain(f"  Pref: {payload.get('workspace_pref_path') or '(not created)'}")
    plain(
        "  Created workspace: " + ("yes" if payload.get("created_workspace") else "no")
    )
    plain("  Created config: " + ("yes" if payload.get("created_config") else "no"))
    plain(
        "  Created bcasl.yml: "
        + ("yes" if payload.get("created_bcasl_config") else "no")
    )
    plain(
        "  Created workspace pref: "
        + ("yes" if payload.get("created_workspace_pref") else "no")
    )
    if payload.get("with_venv"):
        plain(f"  Venv: {payload.get('venv_path') or '(not created)'}")
        plain("  Created venv: " + ("yes" if payload.get("created_venv") else "no"))
