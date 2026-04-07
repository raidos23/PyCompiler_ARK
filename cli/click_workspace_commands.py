# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Click command registration for workspace-oriented actions."""

from typing import Any, Callable

from .contracts import EXIT_PRECHECK_FAILED, EXIT_WORKSPACE_INVALID
from .output import plain


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
) -> None:
    """Register workspace and workspace-bootstrap command groups on a Click root."""
    # Cette fonction isole un bloc volumineux de click_app pour améliorer la maintenabilité.
    @cli.group()
    def workspace():
        """Inspect workspace state and configuration."""

    @workspace.command("inspect")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--strict", is_flag=True, help="Exit non-zero when the workspace is invalid")
    def workspace_inspect(path, as_json, strict):
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
    @click.option("--strict", is_flag=True, help="Exit non-zero when no entrypoint is resolved")
    def workspace_entrypoint(path, as_json, strict):
        # Sortie volontairement compacte pour simplifier les scripts shell.
        payload = workspace_inspect_payload(resolve_workspace_path(path or "."))
        result = {"workspace": payload.get("workspace"), "entrypoint": payload.get("entrypoint")}
        if as_json:
            if strict and not result.get("entrypoint"):
                emit_and_exit(result, EXIT_PRECHECK_FAILED, True)
            echo_payload(result, True)
            return
        plain(result["entrypoint"] or "")
        if strict and not result.get("entrypoint"):
            raise click.exceptions.Exit(EXIT_PRECHECK_FAILED)

    @workspace.command("files")
    @click.argument("path", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    def workspace_files(path, as_json):
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

    @cli.command("init")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--with-venv", is_flag=True, help="Create or reuse a local workspace venv")
    def init_cmd(workspace, as_json, with_venv):
        # Les effets de bord (création fichiers/dossiers) sont encapsulés dans workspace_init_emit.
        workspace_dir = resolve_workspace_path(workspace or ".")
        workspace_init_emit(workspace_dir, as_json=as_json, with_venv=with_venv)

    @cli.command("config-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def config_auto_cmd(workspace, entrypoint, as_json):
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
    @click.option("--with-venv", is_flag=True, help="Create or reuse a local workspace venv")
    def ws_init_cmd(workspace, as_json, with_venv):
        # Alias strict de `init` pour garder une UX type "git-like".
        workspace_dir = resolve_workspace_path(workspace or ".")
        workspace_init_emit(workspace_dir, as_json=as_json, with_venv=with_venv)

    @ws.command("config-auto")
    @click.argument("workspace", required=False, type=click.Path(exists=False))
    @click.option("--entrypoint", type=str, help="Override detected entrypoint")
    @click.option("--json", "as_json", is_flag=True)
    def ws_config_auto_cmd(workspace, entrypoint, as_json):
        workspace_config_auto_emit(
            resolve_workspace_path(workspace or "."),
            entrypoint=entrypoint,
            as_json=as_json,
        )
