from __future__ import annotations

import json
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
    return f"Warning: {message}"


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
) -> int:
    if lock_file and engine_override:
        raise CliSpecError(
            "--engine cannot be used with --lock\nIf you need a different engine, create a new lock with: ark build --engine <engine_id>"
        )

    # 1. BCASL Pre-compile check (Point 1 of mutation plan)
    from .helpers import run_bcasl_before_compile_sync

    if not run_bcasl_before_compile_sync(workspace):
        return 1

    if lock_file is None:
        config = load_ark_config(workspace)
        validated = validate_ark_config(workspace, config)
        engine_id = engine_override or str(validated.config["build"]["engine"])
        _ensure_engine_known(engine_id)
        # Point 3 alignment: build_lock_payload now correctly loads engine config via fixed path
        lock_payload = build_lock_payload(
            workspace, validated.config, engine_id=engine_id
        )
        lock_paths = write_lock_files(workspace, lock_payload)
        context = build_context_object_from_ark_config(validated.config)
        result = run_engine_compile(
            workspace=workspace,
            engine_id=engine_id,
            context=context,
            engine_config=engine_config_from_lock(lock_payload),
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
            for warning in validated.warnings:
                click.echo(_format_warning(warning))
            click.echo(f"Engine: {engine_id}")
            click.echo(f"Lock: {lock_paths['lock']}")
            if result.get("success"):
                click.echo("Build completed.")
            else:
                raise CliSpecError(result.get("error") or "Build failed")
        return 0 if result.get("success") else 1

    lock_path = Path(lock_file).expanduser()
    if not lock_path.is_absolute():
        lock_path = workspace / lock_path
    if not lock_path.exists():
        if lock_file == "__default__":
            lock_path = default_lock_path(workspace)
        if not lock_path.exists():
            raise CliSpecError(f"Lock file not found: {lock_path}")

    lock_payload = load_yaml_file(lock_path)
    engine_id = str(((lock_payload.get("engine") or {}).get("name")) or "").strip()
    entry_file = str(((lock_payload.get("project") or {}).get("entry")) or "").strip()
    if not engine_id or not entry_file:
        raise CliSpecError("Invalid lock file: missing engine.name or project.entry")
    entry_path = workspace / Path(entry_file)
    if not entry_path.is_file():
        raise CliSpecError(
            f"Invalid lock file: project.entry '{entry_file}' is missing or obsolete"
        )

    context = build_context_object_from_lock(lock_payload)
    result = run_engine_compile(
        workspace=workspace,
        engine_id=engine_id,
        context=context,
        engine_config=engine_config_from_lock(lock_payload),
    )

    comparison = None
    rebuild_cache = None
    warnings: list[str] = []
    try:
        current_config = load_ark_config(workspace)
        validated = validate_ark_config(workspace, current_config)
        regenerated = build_lock_payload(
            workspace,
            validated.config,
            engine_id=str(validated.config["build"]["engine"]),
        )
        rebuild_cache = cache_rebuild_lock(workspace, regenerated)
        comparison = compare_lock_payloads(lock_payload, regenerated)
        if not comparison:
            warnings.append("Lock mismatch")
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
        click.echo(f"Lock: {lock_path}")
        if rebuild_cache:
            click.echo(f"Comparison lock: {rebuild_cache}")
        if result.get("success"):
            click.echo("Rebuild completed.")
        else:
            raise CliSpecError(result.get("error") or "Build failed")
    return 0 if result.get("success") else 1


def build_cli():
    if click is None:
        raise RuntimeError("Click is not available")

    @click.group(context_settings={"help_option_names": ["-h", "--help"]})
    @click.version_option(version=_resolve_version(), prog_name="ark")
    def cli():
        """ARK command line interface."""

    @cli.command("init")
    @click.option("--entry", required=True, type=str)
    @click.option("--icon", type=str)
    @click.option("--with-venv", is_flag=True)
    @click.option("--install-requirements", is_flag=True)
    @click.option("--generate-requirements", is_flag=True)
    @click.option("--json", "as_json", is_flag=True)
    def init_cmd(
        entry, icon, with_venv, install_requirements, generate_requirements, as_json
    ):
        """Initialize the current directory as an ARK workspace."""
        try:
            payload = init_workspace(
                cwd=Path.cwd(),
                entry=entry,
                icon=icon,
                with_venv=with_venv,
                generate_requirements=generate_requirements,
                install_requirements=install_requirements,
            )
        except CliSpecError as exc:
            raise click.ClickException(str(exc))
        if as_json:
            _echo_json(payload)
            return
        click.echo(f"Workspace initialized: {payload['workspace']}")
        click.echo(f"ark.yml: {payload['ark_yml']}")
        if payload.get("venv"):
            click.echo(f"Venv: {payload['venv']}")
        if payload.get("requirements"):
            click.echo(f"Requirements: {payload['requirements']}")

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
    def build_cmd(engine_override, lock_file, lock_arg, as_json):
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
            )
        except CliSpecError as exc:
            raise click.ClickException(str(exc))
        raise click.exceptions.Exit(code)

    @cli.group("run")
    def run_group():
        """Run developer-facing commands."""

    @run_group.command("bcasl")
    @click.option("--timeout", type=float)
    @click.option("--parallel", type=int)
    @click.option("--list-plugins", is_flag=True)
    def run_bcasl_cmd(timeout, parallel, list_plugins):
        """Run BCASL in headless mode for the current workspace."""
        args: list[str]
        if list_plugins:
            args = ["list"]
        else:
            args = ["run", str(Path.cwd())]
            if timeout is not None:
                args.extend(["--timeout", str(timeout)])
        del parallel
        raise click.exceptions.Exit(run_bcasl_headless(args))

    @cli.command("gui")
    @click.option("--legacy", is_flag=True)
    def gui_cmd(legacy):
        """Launch the ARK GUI."""
        if legacy:
            click.echo(
                "LIMITATION: The classic GUI does not support full UI feature integration.\nFor full functionality, use 'ark gui'."
            )
        raise click.exceptions.Exit(launch_gui(legacy=legacy))

    @cli.group("set")
    def set_group():
        """Set user-level ARK paths."""

    @cli.group("get")
    def get_group():
        """Get user-level ARK paths."""

    @cli.group("unset")
    def unset_group():
        """Unset user-level ARK paths."""

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
        for engine in payload.get("engines", []):
            click.echo(f"{engine['id']} {engine['version']} {engine['name']}")

    @list_group.command("plugins")
    @click.option("--json", "as_json", is_flag=True)
    def list_plugins_cmd(as_json):
        payload = list_plugins_payload()
        if as_json:
            _echo_json(payload)
            return
        for plugin in payload.get("plugins", []):
            click.echo(f"{plugin['id']} {plugin['version']} {plugin['name']}")

    @cli.group("scaffold")
    def scaffold_group():
        """Generate starter templates."""

    @scaffold_group.command("engine")
    @click.argument("name")
    @click.option("--path", "root_dir", type=click.Path(exists=True, file_okay=False))
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
    @click.option("--path", "root_dir", type=click.Path(exists=True, file_okay=False))
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
        result = cli.main(args=args, prog_name="ark", standalone_mode=False)
        return int(result) if isinstance(result, int) else 0
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 0
    except Exception as exc:
        if click is not None and isinstance(exc, click.exceptions.ClickException):
            exc.show()
            return int(getattr(exc, "exit_code", 2))
        raise
