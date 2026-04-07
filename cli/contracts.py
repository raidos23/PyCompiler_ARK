# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .output import plain

EXIT_OK = 0
EXIT_RUNTIME_ERROR = 1
EXIT_USAGE_ERROR = 2
EXIT_PRECHECK_FAILED = 3
EXIT_WORKSPACE_INVALID = 4
EXIT_ENGINE_NOT_FOUND = 5


def normalize_path(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(Path(raw).expanduser().resolve(strict=False))
    except Exception:
        return raw


def first_positional(args: Iterable[str]) -> str | None:
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
    plain(f"Workspace: {payload.get('workspace')}")
    plain(f"  Config: {payload.get('config_path')}")
    plain(f"  BCASL: {payload.get('bcasl_path') or '(not created)'}")
    plain(f"  Pref: {payload.get('workspace_pref_path') or '(not created)'}")
    plain("  Created workspace: " + ("yes" if payload.get("created_workspace") else "no"))
    plain("  Created config: " + ("yes" if payload.get("created_config") else "no"))
    plain("  Created bcasl.yml: " + ("yes" if payload.get("created_bcasl_config") else "no"))
    plain(
        "  Created workspace pref: "
        + ("yes" if payload.get("created_workspace_pref") else "no")
    )
    if payload.get("with_venv"):
        plain(f"  Venv: {payload.get('venv_path') or '(not created)'}")
        plain("  Created venv: " + ("yes" if payload.get("created_venv") else "no"))
