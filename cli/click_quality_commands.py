# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Click command registration for quality gates (doctor/check)."""

from typing import Any, Callable

from .contracts import EXIT_PRECHECK_FAILED
from .output import plain


def register_quality_commands(
    *,
    cli: Any,
    click: Any,
    resolve_workspace_path: Callable[[str | None], str | None],
    emit_and_exit: Callable[[object, int, bool], None],
    echo_payload: Callable[[object, bool], None],
    doctor_payload: Callable[..., dict[str, object]],
    ci_smoke_payload: Callable[..., dict[str, object]],
    render_checks_text: Callable[..., None],
) -> None:
    """Register quality-focused commands on a Click root command group."""

    # On sépare ces commandes pour garder click_app concentré sur l'orchestration.
    @cli.command("doctor")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--strict", is_flag=True, help="Exit non-zero when diagnostics detect issues"
    )
    def doctor(workspace, as_json, strict):
        # `doctor` agrège un état global plateforme + Qt + inventory engines.
        payload = doctor_payload(workspace=resolve_workspace_path(workspace))
        strict_failed = bool(strict and not payload.get("ok", True))
        if as_json:
            if strict_failed:
                emit_and_exit(payload, EXIT_PRECHECK_FAILED, True)
            echo_payload(payload, True)
            return
        plain("PyCompiler ARK Doctor")
        plain(f"  Python: {payload['platform']['python']}")
        plain(
            f"  Platform: {payload['platform']['system']} {payload['platform']['release']}"
        )
        plain(f"  Qt available: {'yes' if payload['qt_available'] else 'no'}")
        plain(
            f"  Engines: {payload['engines']['compatible_count']}/{payload['engines']['count']} compatible"
        )
        if strict_failed:
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @cli.command("check")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--strict/--no-strict",
        default=True,
        show_default=True,
        help="Exit non-zero when checks fail",
    )
    @click.option(
        "--require-entrypoint/--no-require-entrypoint",
        default=True,
        show_default=True,
        help="Require workspace entrypoint in checks",
    )
    @click.option(
        "--fail-only/--all-checks",
        default=True,
        show_default=True,
        help="Display only failing checks in text output",
    )
    def check_cmd(workspace, as_json, strict, require_entrypoint, fail_only):
        """Single-command CI/CD gate with strict defaults."""
        # `check` est conçu pour les pipelines: sortie stable + code de retour exploitable.
        payload = ci_smoke_payload(
            workspace=resolve_workspace_path(workspace),
            require_entrypoint=require_entrypoint,
        )
        if as_json:
            if strict and not payload.get("ok"):
                emit_and_exit(payload, EXIT_PRECHECK_FAILED, True)
            echo_payload(payload, True)
            return
        render_checks_text(
            "PyCompiler ARK Check",
            list(payload.get("checks", [])),
            fail_only=fail_only,
        )
        if strict and not payload.get("ok"):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)
