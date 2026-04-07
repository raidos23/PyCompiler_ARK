# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

"""Register Click commands related to workspace operations."""

from __future__ import annotations

from typing import Any, Callable

from .contracts import EXIT_PRECHECK_FAILED, EXIT_WORKSPACE_INVALID
from .headless_commands import run_workspace_apply
from .output import plain
from .workspace_apply_args import build_workspace_apply_args


def register_workspace_commands(
    *,
    cli: Any,
    click: Any,
    resolve_workspace_path: Callable[[str | None], str | None],
    emit_and_exit: Callable[[object, int, bool], None],
    echo_payload: Callable[[object, bool], None],
    workspace_init_emit: Callable[[str, bool, bool], None],
    workspace_config_auto_emit: Callable[[str, str | None, bool], None],
    workspace_inspect_payload: Callable[[str], dict[str, object]],
    workspace_entrypoint_set_payload: Callable[[str, str | None], dict[str, object]],
    workspace_entrypoint_clear_payload: Callable[[str], dict[str, object]],
) -> None:
    """Register workspace and workspace-bootstrap command groups on a Click root."""

    # Cette fonction isole un bloc volumineux de click_app pour améliorer la maintenabilité.
    @cli.group()
    def workspace():
        """Inspect workspace state and configuration."""

    @workspace.command("inspect")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--strict", is_flag=True, help="Exit non-zero when the workspace is invalid"
    )
    def workspace_inspect(path, as_json, strict):
        """Inspect workspace state and optionally enforce strict existence checks."""
        # Inspection non destructive: lit l'état workspace sans rien modifier.
        payload = workspace_inspect_payload(resolve_workspace_path(path or "."))
        if as_json:
            if strict and not payload.get("exists"):
                emit_and_exit(payload, EXIT_WORKSPACE_INVALID, True)
            echo_payload(payload, True)
            return
        if not payload.get("exists"):
            raise click.ClickException(payload.get("error", "Workspace not found"))
        plain(f"Workspace: {payload['workspace']}")
        plain(f"  Entrypoint: {payload.get('entrypoint') or '(none)'}")
        plain(f"  Python files: {payload['python_file_count']}")
        plain(
            "  Requirements files: "
            + (", ".join(payload["requirements_files_found"]) or "none")
        )

    @workspace.command("entrypoint")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--strict", is_flag=True, help="Exit non-zero when no entrypoint is resolved"
    )
    def workspace_entrypoint(path, as_json, strict):
        """Return the current workspace entrypoint in compact text or JSON form."""
        # Sortie volontairement compacte pour simplifier les scripts shell.
        payload = workspace_inspect_payload(resolve_workspace_path(path or "."))
        result = {
            "workspace": payload.get("workspace"),
            "entrypoint": payload.get("entrypoint"),
        }
        if as_json:
            if strict and not result.get("entrypoint"):
                emit_and_exit(result, EXIT_PRECHECK_FAILED, True)
            echo_payload(result, True)
            return
        plain(result["entrypoint"] or "")
        if strict and not result.get("entrypoint"):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @workspace.command("entrypoint-set")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.argument("entrypoint", required=True, type=str)
    @click.option("--json", "as_json", is_flag=True)
    def workspace_entrypoint_set(path, entrypoint, as_json):
        """Set and persist an explicit workspace entrypoint."""
        payload = workspace_entrypoint_set_payload(
            resolve_workspace_path(path or "."),
            entrypoint,
        )
        if as_json:
            if not payload.get("ok"):
                code = (
                    EXIT_WORKSPACE_INVALID
                    if payload.get("error")
                    in {"workspace is required", "workspace not found"}
                    else EXIT_PRECHECK_FAILED
                )
                emit_and_exit(payload, code, True)
            echo_payload(payload, True)
            return
        if not payload.get("ok"):
            raise click.ClickException(payload.get("error", "Unable to set entrypoint"))
        plain(payload.get("entrypoint") or "")

    @workspace.command("entrypoint-clear")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def workspace_entrypoint_clear(path, as_json):
        """Clear the persisted workspace entrypoint."""
        payload = workspace_entrypoint_clear_payload(
            resolve_workspace_path(path or ".")
        )
        if as_json:
            if not payload.get("ok"):
                code = (
                    EXIT_WORKSPACE_INVALID
                    if payload.get("error")
                    in {"workspace is required", "workspace not found"}
                    else EXIT_PRECHECK_FAILED
                )
                emit_and_exit(payload, code, True)
            echo_payload(payload, True)
            return
        if not payload.get("ok"):
            raise click.ClickException(
                payload.get("error", "Unable to clear entrypoint")
            )
        plain("")

    @workspace.command("files")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def workspace_files(path, as_json):
        """Show a preview list of Python files discovered in the workspace."""
        # Preview partielle: on ne dump pas toute l'arborescence pour rester lisible.
        payload = workspace_inspect_payload(resolve_workspace_path(path or "."))
        result = {
            "workspace": payload.get("workspace"),
            "python_file_count": payload.get("python_file_count", 0),
            "python_files_preview": payload.get("python_files_preview", []),
        }
        if as_json:
            echo_payload(result, True)
            return
        plain(f"Python files: {result['python_file_count']}")
        for item in result["python_files_preview"]:
            plain(f"  - {item}")

    @workspace.command("apply")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--with-venv", is_flag=True, help="Create or reuse a local workspace venv"
    )
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--no-auto-config", is_flag=True, help="Skip auto configuration pass")
    @click.option(
        "--no-inspect-files", is_flag=True, help="Skip recursive python file scan"
    )
    @click.option(
        "--no-apply-venv-pref",
        is_flag=True,
        help="Skip workspace venv preference application",
    )
    @click.option(
        "--no-apply-engine-configs",
        is_flag=True,
        help="Skip loading workspace engine configs",
    )
    @click.option(
        "--strict", is_flag=True, help="Fail when required checks are missing"
    )
    @click.option(
        "--require-entrypoint", is_flag=True, help="Require a resolved entrypoint"
    )
    def workspace_apply(
        path,
        as_json,
        with_venv,
        entrypoint,
        no_auto_config,
        no_inspect_files,
        no_apply_venv_pref,
        no_apply_engine_configs,
        strict,
        require_entrypoint,
    ):
        """Apply the full workspace workflow in a single command."""
        args = build_workspace_apply_args(
            path=path,
            as_json=bool(as_json),
            with_venv=bool(with_venv),
            entrypoint=entrypoint,
            no_auto_config=bool(no_auto_config),
            no_inspect_files=bool(no_inspect_files),
            no_apply_venv_pref=bool(no_apply_venv_pref),
            no_apply_engine_configs=bool(no_apply_engine_configs),
            strict=bool(strict),
            require_entrypoint=bool(require_entrypoint),
        )
        code = run_workspace_apply(args)
        if code:
            raise click.exceptions.Exit(code)

    @workspace.command("select")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--with-venv", is_flag=True, help="Create or reuse a local workspace venv"
    )
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--no-auto-config", is_flag=True, help="Skip auto configuration pass")
    @click.option(
        "--no-inspect-files", is_flag=True, help="Skip recursive python file scan"
    )
    @click.option(
        "--no-apply-venv-pref",
        is_flag=True,
        help="Skip workspace venv preference application",
    )
    @click.option(
        "--no-apply-engine-configs",
        is_flag=True,
        help="Skip loading workspace engine configs",
    )
    @click.option(
        "--strict", is_flag=True, help="Fail when required checks are missing"
    )
    @click.option(
        "--require-entrypoint", is_flag=True, help="Require a resolved entrypoint"
    )
    def workspace_select(
        path,
        as_json,
        with_venv,
        entrypoint,
        no_auto_config,
        no_inspect_files,
        no_apply_venv_pref,
        no_apply_engine_configs,
        strict,
        require_entrypoint,
    ):
        """Alias of workspace apply that keeps GUI wording familiarity."""
        args = build_workspace_apply_args(
            path=path,
            as_json=bool(as_json),
            with_venv=bool(with_venv),
            entrypoint=entrypoint,
            no_auto_config=bool(no_auto_config),
            no_inspect_files=bool(no_inspect_files),
            no_apply_venv_pref=bool(no_apply_venv_pref),
            no_apply_engine_configs=bool(no_apply_engine_configs),
            strict=bool(strict),
            require_entrypoint=bool(require_entrypoint),
        )
        code = run_workspace_apply(args)
        if code:
            raise click.exceptions.Exit(code)

    @cli.command("init")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--with-venv", is_flag=True, help="Create or reuse a local workspace venv"
    )
    def init_cmd(workspace, as_json, with_venv):
        """Initialize workspace structure and baseline configuration files."""
        # Les effets de bord (création fichiers/dossiers) sont encapsulés dans workspace_init_emit.
        workspace_dir = resolve_workspace_path(workspace or ".")
        workspace_init_emit(workspace_dir, as_json=as_json, with_venv=with_venv)

    @cli.command("config-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def config_auto_cmd(workspace, entrypoint, as_json):
        """Auto-configure workspace entrypoint and dependency settings."""
        # Support d'override explicite via --entrypoint pour bypasser l'auto-détection.
        workspace_config_auto_emit(
            resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )

    @cli.command("cfg-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def cfg_auto_cmd(workspace, entrypoint, as_json):
        """Short alias for config-auto."""
        workspace_config_auto_emit(
            resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )

    @cli.group("ws")
    def ws():
        """Alias for workspace bootstrap commands."""

    @ws.command("init")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--with-venv", is_flag=True, help="Create or reuse a local workspace venv"
    )
    def ws_init_cmd(workspace, as_json, with_venv):
        """Initialize workspace using the short ws namespace."""
        # Alias strict de `init` pour garder une UX type "git-like".
        workspace_dir = resolve_workspace_path(workspace or ".")
        workspace_init_emit(workspace_dir, as_json=as_json, with_venv=with_venv)

    @ws.command("config-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def ws_config_auto_cmd(workspace, entrypoint, as_json):
        """Auto-configure workspace using the short ws namespace."""
        workspace_config_auto_emit(
            resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )

    @ws.command("entrypoint-set")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.argument("entrypoint", required=True, type=str)
    @click.option("--json", "as_json", is_flag=True)
    def ws_entrypoint_set_cmd(workspace, entrypoint, as_json):
        """Set workspace entrypoint through the short ws namespace."""
        payload = workspace_entrypoint_set_payload(
            resolve_workspace_path(workspace or "."),
            entrypoint,
        )
        if as_json:
            if not payload.get("ok"):
                code = (
                    EXIT_WORKSPACE_INVALID
                    if payload.get("error")
                    in {"workspace is required", "workspace not found"}
                    else EXIT_PRECHECK_FAILED
                )
                emit_and_exit(payload, code, True)
            echo_payload(payload, True)
            return
        if not payload.get("ok"):
            raise click.ClickException(payload.get("error", "Unable to set entrypoint"))
        plain(payload.get("entrypoint") or "")

    @ws.command("entrypoint-clear")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def ws_entrypoint_clear_cmd(workspace, as_json):
        """Clear workspace entrypoint through the short ws namespace."""
        payload = workspace_entrypoint_clear_payload(
            resolve_workspace_path(workspace or ".")
        )
        if as_json:
            if not payload.get("ok"):
                code = (
                    EXIT_WORKSPACE_INVALID
                    if payload.get("error")
                    in {"workspace is required", "workspace not found"}
                    else EXIT_PRECHECK_FAILED
                )
                emit_and_exit(payload, code, True)
            echo_payload(payload, True)
            return
        if not payload.get("ok"):
            raise click.ClickException(
                payload.get("error", "Unable to clear entrypoint")
            )
        plain("")

    @ws.command("apply")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--with-venv", is_flag=True, help="Create or reuse a local workspace venv"
    )
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--no-auto-config", is_flag=True, help="Skip auto configuration pass")
    @click.option(
        "--no-inspect-files", is_flag=True, help="Skip recursive python file scan"
    )
    @click.option(
        "--no-apply-venv-pref",
        is_flag=True,
        help="Skip workspace venv preference application",
    )
    @click.option(
        "--no-apply-engine-configs",
        is_flag=True,
        help="Skip loading workspace engine configs",
    )
    @click.option(
        "--strict", is_flag=True, help="Fail when required checks are missing"
    )
    @click.option(
        "--require-entrypoint", is_flag=True, help="Require a resolved entrypoint"
    )
    def ws_apply_cmd(
        workspace,
        as_json,
        with_venv,
        entrypoint,
        no_auto_config,
        no_inspect_files,
        no_apply_venv_pref,
        no_apply_engine_configs,
        strict,
        require_entrypoint,
    ):
        """Apply workspace workflow using the short ws namespace."""
        args = build_workspace_apply_args(
            path=workspace,
            as_json=bool(as_json),
            with_venv=bool(with_venv),
            entrypoint=entrypoint,
            no_auto_config=bool(no_auto_config),
            no_inspect_files=bool(no_inspect_files),
            no_apply_venv_pref=bool(no_apply_venv_pref),
            no_apply_engine_configs=bool(no_apply_engine_configs),
            strict=bool(strict),
            require_entrypoint=bool(require_entrypoint),
        )
        code = run_workspace_apply(args)
        if code:
            raise click.exceptions.Exit(code)

    @ws.command("select")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option(
        "--with-venv", is_flag=True, help="Create or reuse a local workspace venv"
    )
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--no-auto-config", is_flag=True, help="Skip auto configuration pass")
    @click.option(
        "--no-inspect-files", is_flag=True, help="Skip recursive python file scan"
    )
    @click.option(
        "--no-apply-venv-pref",
        is_flag=True,
        help="Skip workspace venv preference application",
    )
    @click.option(
        "--no-apply-engine-configs",
        is_flag=True,
        help="Skip loading workspace engine configs",
    )
    @click.option(
        "--strict", is_flag=True, help="Fail when required checks are missing"
    )
    @click.option(
        "--require-entrypoint", is_flag=True, help="Require a resolved entrypoint"
    )
    def ws_select_cmd(
        workspace,
        as_json,
        with_venv,
        entrypoint,
        no_auto_config,
        no_inspect_files,
        no_apply_venv_pref,
        no_apply_engine_configs,
        strict,
        require_entrypoint,
    ):
        """Select/apply workspace using the short ws namespace."""
        args = build_workspace_apply_args(
            path=workspace,
            as_json=bool(as_json),
            with_venv=bool(with_venv),
            entrypoint=entrypoint,
            no_auto_config=bool(no_auto_config),
            no_inspect_files=bool(no_inspect_files),
            no_apply_venv_pref=bool(no_apply_venv_pref),
            no_apply_engine_configs=bool(no_apply_engine_configs),
            strict=bool(strict),
            require_entrypoint=bool(require_entrypoint),
        )
        code = run_workspace_apply(args)
        if code:
            raise click.exceptions.Exit(code)
