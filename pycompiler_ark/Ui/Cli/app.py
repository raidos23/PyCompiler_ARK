# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .helpers import (
    CliSpecError,
    build_context_object_from_ark_config,
    build_context_object_from_lock,
    build_lock_payload,
    cache_rebuild_lock,
    compare_lock_payloads,
    default_lock_path,
    engine_config_from_lock,
    init_workspace,
    launch_gui,
    list_engines_payload,
    list_plugins_payload,
    load_ark_config,
    load_yaml_file,
    resolve_config_value,
    run_bcasl_headless,
    run_engine_compile,
    scaffold_engine_payload,
    scaffold_plugin_payload,
    set_config_value,
    unset_config_value,
    validate_ark_config,
    write_lock_files,
)
from .output import info, success
from .runtime import install_runtime, should_enable_qt

try:
    import click  # type: ignore
except Exception:  # pragma: no cover
    click = None


def has_click() -> bool:
    return click is not None


def _echo_json(payload: Any) -> None:
    click.echo(json.dumps(payload, indent=2, ensure_ascii=False))


def _format_warning(message: str) -> str:
    from .output import strip_emojis

    return f"[warning]Warning:[/warning] {strip_emojis(message)}"


def _resolve_version() -> str:
    root = Path(__file__).resolve().parents[2]
    core_init = root / "Core" / "__init__.py"
    try:
        for line in core_init.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("__version__"):
                return line.split("=", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    return "unknown"


def _ensure_engine_known(engine_id: str) -> None:
    payload = list_engines_payload()
    known_ids = {
        str(item.get("id") or "").strip()
        for item in payload.get("engines", [])
        if isinstance(item, dict)
    }
    if engine_id not in known_ids:
        raise CliSpecError(f"build.engine: unknown engine '{engine_id}'")


def _build_impl(
    *,
    workspace: Path,
    engine_override: str | None,
    lock_file: str | None,
    as_json: bool,
    verbose: bool = False,
    auto_confirm: bool = False,
) -> int:
    if auto_confirm:
        os.environ["PYCOMPILER_NONINTERACTIVE"] = "1"
        os.environ["PYCOMPILER_YES"] = "1"

    if lock_file and engine_override:
        raise CliSpecError(
            "--engine cannot be used with --lock\nIf you need a different engine, create a new lock with: pycompiler_ark build --engine <engine_id>"
        )

    if not as_json and verbose:
        info((f"Espace de travail : {workspace}", f"Workspace: {workspace}"))

    # Shared Python version resolution for locking/comparison
    python_version = None
    try:
        from ...Core.utils.internet import get_interpreter_version_str
        from ...Core.Venv_Manager.Manager import VenvManager

        # We create a dummy bridge for VenvManager
        class DummyBridge:
            def __init__(self, ws):
                self.workspace_dir = ws
                self.use_system_python = False

        vm = VenvManager(DummyBridge(str(workspace)))
        vpython = vm.resolve_existing_venv()
        if vpython:
            vpath = vm.python_path(vpython)
            python_version = get_interpreter_version_str(vpath)
        else:
            python_version = get_interpreter_version_str()
    except Exception:
        pass

    if lock_file is None:
        if not as_json and verbose:
            info(("Chargement de ark.yml...", "Loading ark.yml..."))
        config = load_ark_config(workspace)
        if not as_json and verbose:
            info(
                (
                    "Validation de la configuration...",
                    "Validating configuration...",
                )
            )
        validated = validate_ark_config(workspace, config)
        engine_id = engine_override or str(validated.config["build"]["engine"])
        _ensure_engine_known(engine_id)

        if not as_json and verbose:
            info(
                (
                    f"Génération du payload de lock pour le moteur '{engine_id}'...",
                    f"Generating lock payload for engine '{engine_id}'...",
                )
            )

        context = build_context_object_from_ark_config(validated.config)

        # Pre-resolve command for auto-mapping persistence (Phase 3)
        resolved_command = None
        try:
            from ...Core.Compiler.engine_runner import (
                resolve_engine_command,
            )
            from ...Core.Locking import read_engine_config

            # Create a minimal bridge for resolution
            class ResolutionBridge:
                def __init__(self, ws):
                    self.workspace_dir = str(ws)
                    self.use_system_python = False

                def tr(self, fr, en):
                    return en

            # We use the current engine config from disk for resolution
            current_engine_config = read_engine_config(workspace, engine_id)

            prog, args, env = resolve_engine_command(
                engine_id,
                context,
                current_engine_config,
                gui=ResolutionBridge(workspace),
            )
            resolved_command = {"program": prog, "args": args, "env": env}
        except Exception as e:
            if verbose:
                info(
                    (
                        f"Résolution auto-mapping ignorée pour le lock : {e}",
                        f"Auto-mapping resolution skipped for lock: {e}",
                    )
                )

        # Point 3 alignment: build_lock_payload now correctly loads engine config via fixed path
        lock_payload = build_lock_payload(
            workspace,
            validated.config,
            engine_id=engine_id,
            python_version=python_version,
            resolved_command=resolved_command,
        )
        if not as_json and verbose:
            info(("Écriture des fichiers de lock...", "Writing lock files..."))
        lock_paths = write_lock_files(workspace, lock_payload)

        # 1. BCASL Pre-compile check (Point 1 of mutation plan)
        from .helpers import run_bcasl_before_compile_sync

        if not run_bcasl_before_compile_sync(
            workspace, verbose=verbose, build_context=context
        ):
            return 1

        if not as_json and verbose:
            info(
                (
                    "Démarrage de la compilation du moteur...",
                    "Starting engine compilation...",
                )
            )
        result = run_engine_compile(
            workspace=workspace,
            engine_id=engine_id,
            context=context,
            engine_config=engine_config_from_lock(lock_payload),
            verbose=verbose,
        )
        payload = {
            "mode": "build",
            "engine": engine_id,
            "warnings": validated.warnings,
            "lock": lock_paths,
            "build_context": context.to_dict(),
            "result": result,
        }
        if as_json:
            _echo_json(payload)
        else:
            from .output import success

            for warning in validated.warnings:
                click.echo(_format_warning(warning))
            if verbose:
                info((f"Moteur : {engine_id}", f"Engine: {engine_id}"))
                info(
                    (
                        f"Lock : {lock_paths['lock']}",
                        f"Lock: {lock_paths['lock']}",
                    )
                )
            if result.get("success"):
                success(
                    (
                        "Build terminé avec succès.",
                        "Build completed successfully.",
                    )
                )
            else:
                raise CliSpecError(result.get("error") or "Build failed")
        return 0 if result.get("success") else 1

    # Rebuild from lock
    if lock_file == "__default__":
        raise CliSpecError(
            "Usage: pycompiler_ark build --lock <FILE_OR_LATEST>\n"
            "Exemple: pycompiler_ark build --lock latest"
        )

    if lock_file == "latest":
        lock_path = default_lock_path(workspace)
    else:
        lock_path = Path(lock_file).expanduser()
        if not lock_path.is_absolute():
            lock_path = workspace / lock_path

    if not lock_path.exists():
        raise CliSpecError(f"Lock file not found: {lock_path}")

    if not as_json:
        info(
            (
                f"Reconstruction depuis le lock : {lock_path.name}",
                f"Rebuilding from lock: {lock_path.name}",
            )
        )

    lock_payload = load_yaml_file(lock_path)
    engine_id = str(
        ((lock_payload.get("engine") or {}).get("name")) or ""
    ).strip()
    entry_file = str(
        ((lock_payload.get("project") or {}).get("entry")) or ""
    ).strip()
    if not engine_id or not entry_file:
        raise CliSpecError(
            "Invalid lock file: missing engine.name or project.entry"
        )

    entry_path = workspace / Path(entry_file)
    if not entry_path.is_file():
        raise CliSpecError(
            f"Invalid lock file: project.entry '{entry_file}' is missing or obsolete"
        )

    if not as_json and verbose:
        info((f"Moteur cible : {engine_id}", f"Target engine: {engine_id}"))

    # Alignement Git
    from .helpers import ensure_correct_git_commit

    if not ensure_correct_git_commit(workspace, lock_payload):
        return 1

    context = build_context_object_from_lock(lock_payload)

    # BCASL Pre-compile check for lock branch
    from .helpers import run_bcasl_before_compile_sync

    if not run_bcasl_before_compile_sync(
        workspace, verbose=verbose, build_context=context
    ):
        return 1

    if not as_json:
        info(
            (
                "Démarrage de la reconstruction du moteur...",
                "Starting engine rebuild...",
            )
        )

    result = run_engine_compile(
        workspace=workspace,
        engine_id=engine_id,
        context=context,
        engine_config=engine_config_from_lock(lock_payload),
        verbose=verbose,
        is_rebuild=True,
    )

    comparison = None
    rebuild_cache = None
    warnings: list[str] = []
    try:
        if not as_json and verbose:
            info(
                (
                    "Vérification d'intégrité du lock...",
                    "Performing lock integrity check...",
                )
            )
        current_config = load_ark_config(workspace)
        validated = validate_ark_config(workspace, current_config)
        regenerated = build_lock_payload(
            workspace,
            validated.config,
            engine_id=str(validated.config["build"]["engine"]),
            python_version=python_version,
        )
        rebuild_cache = cache_rebuild_lock(workspace, regenerated)
        comparison_ok, diffs = compare_lock_payloads(
            lock_payload, regenerated, return_diff=True
        )
        comparison = comparison_ok
        if not comparison_ok:
            warnings.append("Lock mismatch")
            if not as_json and verbose:
                from .output import warn

                warn(
                    (
                        "Désynchronisation fonctionnelle détectée :",
                        "Functional mismatch detected:",
                    )
                )
                for d in diffs:
                    info((f"  - {d}", f"  - {d}"))
        elif not as_json and verbose:
            from .output import success

            success(
                (
                    "Intégrité du lock confirmée (équivalence fonctionnelle).",
                    "Lock integrity confirmed (Functional Equivalence).",
                )
            )
    except Exception as exc:
        warnings.append(f"Unable to regenerate comparison lock: {exc}")

    payload = {
        "mode": "lock",
        "lock_file": str(lock_path),
        "engine": engine_id,
        "warnings": warnings,
        "comparison_ok": comparison,
        "comparison_lock": rebuild_cache,
        "build_context": context.to_dict(),
        "result": result,
    }
    if as_json:
        _echo_json(payload)
    else:
        for warning in warnings:
            click.echo(_format_warning(warning))
        if verbose:
            info((f"Lock : {lock_path}", f"Lock: {lock_path}"))
            if rebuild_cache:
                info(
                    (
                        f"Lock de comparaison : {rebuild_cache}",
                        f"Comparison lock: {rebuild_cache}",
                    )
                )
        if result.get("success"):
            success(
                (
                    "Reconstruction terminée avec succès.",
                    "Rebuild completed successfully.",
                )
            )
        else:
            raise CliSpecError(result.get("error") or "Build failed")
    return 0 if result.get("success") else 1


def build_cli():
    if click is None:
        raise RuntimeError("Click is not available")

    @click.group(context_settings={"help_option_names": ["-h", "--help"]})
    @click.version_option(
        version=_resolve_version(), prog_name="pycompiler_ark"
    )
    def cli():
        """PyCompiler ARK command line interface."""

    @cli.command("init")
    @click.option("--entry", required=True, type=str)
    @click.option("--icon", type=str)
    @click.option("--with-venv", is_flag=True)
    @click.option("--install-requirements", is_flag=True)
    @click.option("--generate-requirements", is_flag=True)
    @click.option(
        "--apply-internal",
        is_flag=True,
        help="Detect internal project modules and propose them for build.include.",
    )
    @click.option(
        "--yes",
        "-y",
        "auto_confirm",
        is_flag=True,
        help="Auto-confirm all prompts.",
    )
    @click.option("--json", "as_json", is_flag=True)
    def init_cmd(
        entry,
        icon,
        with_venv,
        install_requirements,
        generate_requirements,
        apply_internal,
        auto_confirm,
        as_json,
    ):
        """Initialize the current directory as a PyCompiler ARK workspace."""
        try:
            payload = init_workspace(
                cwd=Path.cwd(),
                entry=entry,
                icon=icon,
                with_venv=with_venv,
                generate_requirements=generate_requirements,
                install_requirements=install_requirements,
                apply_internal=apply_internal,
                auto_confirm=auto_confirm,
            )
        except CliSpecError as exc:
            raise click.ClickException(str(exc))
        if as_json:
            _echo_json(payload)
            return

        from .output import info, success

        success(
            (
                f"Espace de travail initialisé : {payload['workspace']}",
                f"Workspace initialized: {payload['workspace']}",
            )
        )
        info(
            (
                f"ark.yml : {payload['ark_yml']}",
                f"ark.yml: {payload['ark_yml']}",
            )
        )
        if payload.get("apply_internal"):
            detected = payload.get("internal_modules", [])
            if detected:
                joined = ", ".join(str(item) for item in detected)
                info(
                    (
                        f"Modules internes à appliquer : {joined}",
                        f"Internal modules to apply: {joined}",
                    )
                )
                if payload.get("internal_modules_applied"):
                    info(
                        (
                            "build.include mis à jour automatiquement.",
                            "build.include updated automatically.",
                        )
                    )
                else:
                    info(
                        (
                            "Passez -y pour les écrire dans build.include.",
                            "Pass -y to write them into build.include.",
                        )
                    )
        if payload.get("venv"):
            info((f"Venv : {payload['venv']}", f"Venv: {payload['venv']}"))
        if payload.get("requirements"):
            info(
                (
                    f"Requirements : {payload['requirements']}",
                    f"Requirements: {payload['requirements']}",
                )
            )

    @cli.command("build")
    @click.option("--engine", "engine_override", type=str)
    @click.option(
        "--lock",
        "lock_file",
        flag_value="__default__",
        default=None,
        type=str,
        required=False,
    )
    @click.argument("lock_arg", required=False)
    @click.option("--json", "as_json", is_flag=True)
    @click.option("--verbose", "-v", is_flag=True)
    @click.option(
        "--yes",
        "-y",
        "auto_confirm",
        is_flag=True,
        help="Auto-confirm all prompts.",
    )
    def build_cmd(
        engine_override, lock_file, lock_arg, as_json, verbose, auto_confirm
    ):
        """Build from ark.yml or rebuild from a lock file."""
        effective_lock = (
            lock_arg if lock_arg and lock_file == "__default__" else lock_file
        )
        try:
            code = _build_impl(
                workspace=Path.cwd(),
                engine_override=engine_override,
                lock_file=effective_lock,
                as_json=as_json,
                verbose=verbose,
                auto_confirm=auto_confirm,
            )
        except CliSpecError as exc:
            raise click.ClickException(str(exc))
        raise click.exceptions.Exit(code)

    @cli.group("run")
    def run_group():
        """Run developer-facing commands."""

    @run_group.command("bcasl")
    @click.option("--list-plugins", is_flag=True)
    @click.option("--verbose", "-v", is_flag=True)
    @click.option(
        "--yes",
        "-y",
        "auto_confirm",
        is_flag=True,
        help="Auto-confirm all prompts.",
    )
    def run_bcasl_cmd(list_plugins, verbose, auto_confirm):
        """Run BCASL in headless mode for the current workspace."""
        if auto_confirm:
            os.environ["PYCOMPILER_NONINTERACTIVE"] = "1"
            os.environ["PYCOMPILER_YES"] = "1"

        args: list[str]
        if list_plugins:
            args = ["list"]
        else:
            args = ["run", str(Path.cwd())]
        raise click.exceptions.Exit(run_bcasl_headless(args, verbose=verbose))

    @cli.command("gui")
    @click.option("--legacy", is_flag=True)
    def gui_cmd(legacy):
        """Launch the PyCompiler ARK GUI."""
        if legacy:
            click.echo(
                "LIMITATION: The classic GUI does not support full UI feature integration.\nFor full functionality, use 'pycompiler_ark gui'."
            )
        raise click.exceptions.Exit(launch_gui(legacy=legacy))

    @cli.group("set")
    def set_group():
        """Set user-level PyCompiler ARK paths."""

    @cli.group("get")
    def get_group():
        """Get user-level PyCompiler ARK paths."""

    @cli.group("unset")
    def unset_group():
        """Unset user-level PyCompiler ARK paths."""

    for key in (
        "user-engine-dir",
        "user-plugin-dir",
        "dev-engine-dir",
        "dev-plugin-dir",
    ):

        def _make_set(spec_key: str):
            @set_group.command(spec_key)
            @click.argument("path")
            def _cmd(path):
                click.echo(set_config_value(spec_key, path))

        def _make_get(spec_key: str):
            @get_group.command(spec_key)
            def _cmd():
                value = resolve_config_value(spec_key)
                if value:
                    click.echo(value)

        def _make_unset(spec_key: str):
            @unset_group.command(spec_key)
            def _cmd():
                unset_config_value(spec_key)

        _make_set(key)
        _make_get(key)
        _make_unset(key)

    @cli.group("list")
    def list_group():
        """List engines and plugins."""

    @list_group.command("engines")
    @click.option("--json", "as_json", is_flag=True)
    def list_engines_cmd(as_json):
        payload = list_engines_payload()
        if as_json:
            _echo_json(payload)
            return

        from rich.table import Table

        from .output import get_console

        console = get_console()
        if console:
            from collections import defaultdict

            groups = defaultdict(list)
            for engine in payload.get("engines", []):
                groups[engine.get("source", "embedded")].append(engine)

            # Print sections in preferred order
            for section_key, title in (
                ("user", "User Engines"),
                ("dev", "Dev Engines"),
                ("internal", "Internal Engines"),
                ("embedded", "Other Engines"),
            ):
                items = groups.get(section_key, [])
                if not items:
                    continue
                table = Table(title=title, box=None, header_style="bold cyan")
                table.add_column("ID", style="bright_blue")
                table.add_column("Version", style="green")
                table.add_column("Name")
                for engine in items:
                    table.add_row(
                        engine["id"], engine["version"], engine["name"]
                    )
                console.print(table)
        else:
            for section_key, title in (
                ("user", "User Engines"),
                ("dev", "Dev Engines"),
                ("internal", "Internal Engines"),
                ("embedded", "Other Engines"),
            ):
                items = [
                    e
                    for e in payload.get("engines", [])
                    if e.get("source", "embedded") == section_key
                ]
                if not items:
                    continue
                click.echo(title + ":")
                for engine in items:
                    click.echo(
                        f"  {engine['id']} {engine['version']} {engine['name']}"
                    )

    @list_group.command("plugins")
    @click.option("--json", "as_json", is_flag=True)
    def list_plugins_cmd(as_json):
        payload = list_plugins_payload()
        if as_json:
            _echo_json(payload)
            return

        from rich.table import Table

        from .output import get_console

        console = get_console()
        if console:
            table = Table(
                title="Available Plugins", box=None, header_style="bold cyan"
            )
            table.add_column("ID", style="bright_blue")
            table.add_column("Version", style="green")
            table.add_column("Name")

            for plugin in payload.get("plugins", []):
                table.add_row(plugin["id"], plugin["version"], plugin["name"])
            console.print(table)
        else:
            for plugin in payload.get("plugins", []):
                click.echo(
                    f"{plugin['id']} {plugin['version']} {plugin['name']}"
                )

    @cli.group("scaffold")
    def scaffold_group():
        """Generate starter templates."""

    @scaffold_group.command("engine")
    @click.argument("name")
    @click.option(
        "--path", "root_dir", type=click.Path(exists=True, file_okay=False)
    )
    @click.option("--json", "as_json", is_flag=True)
    def scaffold_engine_cmd(name, root_dir, as_json):
        payload = scaffold_engine_payload(name, root_dir=root_dir)
        if as_json:
            _echo_json(payload)
            return
        if not payload.get("created"):
            raise click.ClickException(
                payload.get("reason", "Unable to create scaffold")
            )
        click.echo(payload["path"])

    @scaffold_group.command("plugin-bcasl")
    @click.argument("name")
    @click.option(
        "--path", "root_dir", type=click.Path(exists=True, file_okay=False)
    )
    @click.option("--json", "as_json", is_flag=True)
    def scaffold_plugin_cmd(name, root_dir, as_json):
        payload = scaffold_plugin_payload(name, root_dir=root_dir)
        if as_json:
            _echo_json(payload)
            return
        if not payload.get("created"):
            raise click.ClickException(
                payload.get("reason", "Unable to create scaffold")
            )
        click.echo(payload["path"])

    return cli


def main(argv: list[str] | None = None) -> int:
    args = list(argv) if argv is not None else list(sys.argv[1:])
    install_runtime(_resolve_version(), enable_qt=should_enable_qt(args))
    try:
        cli = build_cli()
        result = cli.main(
            args=args, prog_name="pycompiler_ark", standalone_mode=False
        )
        return int(result) if isinstance(result, int) else 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0
    except Exception as exc:
        if click is not None and isinstance(
            exc, click.exceptions.ClickException
        ):
            exc.show()
            return int(getattr(exc, "exit_code", 2))
        raise
