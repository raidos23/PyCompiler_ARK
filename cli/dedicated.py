# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

"""Dedicated interactive CLI frontend for PyCompiler ARK."""

import shlex
from pathlib import Path

from .lazy_ops import (
    available_engine_ids,
    launch_bcasl_gui,
    launch_engines_gui,
    launch_main_gui,
    unload_all_engines,
)
from .headless_commands import run_check, run_config_auto, run_init, run_workspace_apply
from .output import error, info, plain, success, warn
from .system_info import print_system_info

try:
    from rich.console import Console  # type: ignore
    from rich.panel import Panel  # type: ignore
    from rich.table import Table  # type: ignore
    from rich.text import Text  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Console = None
    Panel = None
    Table = None
    Text = None

try:
    from pyfiglet import Figlet  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Figlet = None

try:
    from prompt_toolkit import PromptSession  # type: ignore
    from prompt_toolkit.completion import WordCompleter  # type: ignore
    from prompt_toolkit.history import InMemoryHistory  # type: ignore
    from prompt_toolkit.lexers import Lexer  # type: ignore
    from prompt_toolkit.styles import Style  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    PromptSession = None
    WordCompleter = None
    InMemoryHistory = None
    Lexer = object
    Style = None

_RICH_CONSOLE = Console() if Console is not None else None


def _rprint(message: str, style: str | None = None) -> None:
    """Print with Rich when available, fallback to plain output otherwise."""
    if _RICH_CONSOLE is not None:
        _RICH_CONSOLE.print(message, style=style)
        return
    plain(message)


def _styled_parts(command: str) -> list[tuple[str, str]]:
    """Tokenize and style a command line for prompt-toolkit rendering."""
    try:
        parts = shlex.split(command)
    except Exception:
        parts = command.split()
    styled: list[tuple[str, str]] = []
    for idx, tok in enumerate(parts):
        if idx > 0:
            styled.append(("class:plain", " "))
        if idx == 0:
            styled.append(("class:cmd", tok))
        elif tok.startswith("--"):
            styled.append(("class:flag_long", tok))
        elif tok.startswith("-"):
            styled.append(("class:flag_short", tok))
        elif tok.startswith(("/", "./", "../", "~/")) or tok.endswith(
            (".py", ".yml", ".yaml", ".json")
        ):
            styled.append(("class:path", tok))
        else:
            styled.append(("class:arg", tok))
    return styled


class ArkCommandLexer(Lexer):
    def lex_document(self, document):
        lines = document.lines or [""]

        def get_line(lineno: int):
            if lineno >= len(lines):
                return []
            return _styled_parts(lines[lineno])

        return get_line


def _command_text(command: str):
    """Build a Rich ``Text`` object for command preview output."""
    if Text is None:
        return command
    try:
        parts = shlex.split(command)
    except Exception:
        parts = command.split()
    out = Text()
    for idx, tok in enumerate(parts):
        if idx > 0:
            out.append(" ")
        if idx == 0:
            out.append(tok, style="bold bright_cyan")
        elif tok.startswith("--"):
            out.append(tok, style="bold yellow")
        elif tok.startswith("-"):
            out.append(tok, style="yellow")
        elif tok.startswith(("/", "./", "../", "~/")) or tok.endswith(
            (".py", ".yml", ".yaml", ".json")
        ):
            out.append(tok, style="green")
        else:
            out.append(tok, style="white")
    return out


def _print_cmdline(command: str) -> None:
    """Render a shell-like command preview line."""
    if _RICH_CONSOLE is None:
        plain(command)
        return
    prefix = Text("$ ", style="dim")
    prefix.append_text(_command_text(command))
    _RICH_CONSOLE.print(prefix)


def _print_banner(app_version: str) -> None:
    """Render the dedicated CLI startup banner."""
    if _RICH_CONSOLE is None:
        plain("PyCompiler ARK - dedicated CLI")
        plain(f"Version {app_version}")
        plain("Type `help` for commands and `exit` to quit.")
        return

    ascii_title = None
    if Figlet is not None:
        try:
            fig = Figlet(font="slant", width=140)
            ascii_title = fig.renderText("PyCompiler ARK").rstrip("\n")
        except Exception:
            ascii_title = None

    if ascii_title:
        body = Text(ascii_title, style="bold bright_cyan")
    else:
        body = Text("PyCompiler ARK", style="bold bright_cyan")

    panel = Panel.fit(
        body,
        title=f"[bold white]v{app_version}[/bold white]",
        subtitle="[bold green]Dedicated CLI[/bold green]",
        border_style="bright_blue",
        padding=(0, 1),
    )
    _RICH_CONSOLE.print(panel)
    _RICH_CONSOLE.print(
        "[dim]Type [bold]help[/bold] for commands and [bold]exit[/bold] to quit.[/dim]"
    )


def _print_help() -> None:
    """Render help for the dedicated interactive command set."""
    if _RICH_CONSOLE is None or Table is None:
        plain("")
        plain("Available commands")
        plain("  help                  Show this help")
        plain("  info                  Show system information")
        plain("  version               Show app version")
        plain("  main                  Launch main app (GUI)")
        plain("  main --ide-gui        Launch main app (IDE GUI)")
        plain("  bcasl [workspace]     Launch BCASL standalone (GUI)")
        plain("  bcasl help            BCASL command help")
        plain("  bcasl list            List BCASL plugins (headless)")
        plain("  bcasl run <workspace> Run BCASL without GUI")
        plain("  engines [workspace]   Launch Engines standalone (GUI)")
        plain("  engine help           Engine command help")
        plain("  engine list           List engines with compatibility")
        plain("  engine compat <id>    Check engine compatibility")
        plain("  engine info <id>      Show engine metadata")
        plain("  engine dry-run <id> <file>  Preview compile command")
        plain("  engine compile <id> <file>  Run compilation")
        plain("  check [workspace]     Run strict CI/CD check")
        plain("  init [workspace] [--with-venv]  Initialize workspace")
        plain("  config-auto [workspace]  Auto-configure workspace")
        plain("  cfg-auto [workspace]     Alias for config-auto")
        plain("  ws init [workspace]      Alias for init")
        plain("  ws config-auto [workspace] Alias for config-auto")
        plain("  ws apply [workspace]     Full workspace apply workflow")
        plain("  engines --dry-run     List available engines")
        plain("  unload                Unload all registered engines")
        plain("  exit | quit           Close dedicated CLI")
        plain("")
        return

    table = Table(title="Command Center", header_style="bold magenta")
    table.add_column("Command", style="bold cyan")
    table.add_column("Action", style="white")
    table.add_row("help", "Show this help")
    table.add_row("info", "Show system information")
    table.add_row("version", "Show app version")
    table.add_row("main", "Launch main GUI")
    table.add_row("main --ide-gui", "Launch IDE-like main GUI")
    table.add_row("bcasl [workspace]", "Launch BCASL GUI")
    table.add_row("bcasl list", "List BCASL plugins (headless)")
    table.add_row("bcasl run <workspace>", "Run BCASL without GUI")
    table.add_row("engines [workspace]", "Launch Engines GUI")
    table.add_row("engine list", "List engines + compatibility")
    table.add_row("engine compat <id>", "Check one engine compatibility")
    table.add_row("engine info <id>", "Show engine metadata")
    table.add_row("engine dry-run <id> <file>", "Preview compile command")
    table.add_row("engine compile <id> <file>", "Run compilation")
    table.add_row("check [workspace]", "Run strict CI/CD checks")
    table.add_row("init [workspace] [--with-venv]", "Initialize workspace config")
    table.add_row("config-auto [workspace]", "Auto-configure workspace")
    table.add_row("cfg-auto [workspace]", "Alias for config-auto")
    table.add_row("ws init [workspace]", "Alias for init")
    table.add_row("ws config-auto [workspace]", "Alias for config-auto")
    table.add_row("ws apply [workspace]", "Apply full workspace workflow")
    table.add_row("unload", "Unload all registered engines")
    table.add_row("exit | quit", "Close dedicated CLI")
    _RICH_CONSOLE.print(table)
    _RICH_CONSOLE.print("[bold]Quick examples[/bold]")
    _print_cmdline("engine dry-run <engine_id> src/main.py")
    _print_cmdline("engine compile <engine_id> app.py")
    _print_cmdline("bcasl run -w ~/workspace --timeout 30")


def _resolve_workspace(raw: str | None) -> str | None:
    """Normalize an optional workspace path."""
    if not raw:
        return None
    try:
        return str(Path(raw).expanduser())
    except Exception:
        return raw


def _run_engines(args: list[str]) -> int:
    """Handle legacy `engines` command behavior in dedicated mode."""
    if "--dry-run" in args or "-d" in args:
        engines = available_engine_ids()
        if _RICH_CONSOLE is not None and Table is not None:
            table = Table(
                title=f"Available engines ({len(engines)})", header_style="bold magenta"
            )
            table.add_column("#", style="dim")
            table.add_column("Engine ID", style="cyan")
            for idx, eid in enumerate(engines, start=1):
                table.add_row(str(idx), eid)
            _RICH_CONSOLE.print(table)
        else:
            plain(f"Available engines ({len(engines)})")
            for eid in engines:
                plain(f"  - {eid}")
        return 0
    workspace = _resolve_workspace(args[0]) if args else None
    return launch_engines_gui(workspace)


def _run_bcasl(args: list[str]) -> int:
    """Launch BCASL GUI mode from the dedicated shell."""
    workspace = _resolve_workspace(args[0]) if args else None
    return launch_bcasl_gui(workspace)


def _new_bcasl_app(workspace: str | None = None):
    """Create a headless BCASL app instance."""
    try:
        from OnlyMod.BcaslOnlyMod.app import BcaslOnlyModApp
    except Exception as exc:
        error(f"Unable to load BCASL module: {exc}")
        return None

    try:
        return BcaslOnlyModApp(
            workspace_dir=workspace,
            language="en",
            theme="dark",
            headless=True,
        )
    except Exception as exc:
        error(f"Failed to initialize BCASL mode: {exc}")
        return None


def _print_bcasl_help() -> None:
    """Render BCASL subcommand help."""
    if _RICH_CONSOLE is None or Table is None:
        plain("")
        plain("BCASL commands")
        plain("  bcasl [workspace]")
        plain("  bcasl list")
        plain("  bcasl run <workspace> [--timeout SECONDS]")
        plain("  bcasl run -w <workspace> [--timeout SECONDS]")
        plain("  bcasl doctor [workspace] [--strict]")
        plain("  bcasl doctor -w <workspace> [--strict]")
        plain("")
        plain("Examples:")
        plain("  bcasl")
        plain("  bcasl /path/to/workspace")
        plain("  bcasl list")
        plain("  bcasl run /path/to/workspace")
        plain("  bcasl run /path/to/workspace --timeout 30")
        plain("  bcasl doctor /path/to/workspace --strict")
        plain("")
        return

    table = Table(title="BCASL Commands", header_style="bold magenta")
    table.add_column("Command", style="bold cyan")
    table.add_column("Action", style="white")
    table.add_row("bcasl [workspace]", "Launch BCASL GUI")
    table.add_row("bcasl list", "List BCASL plugins")
    table.add_row("bcasl run <workspace>", "Run plugins headless")
    table.add_row("bcasl run -w <workspace>", "Run plugins headless")
    table.add_row("bcasl doctor [workspace]", "Run BCASL diagnostics")
    _RICH_CONSOLE.print(table)
    _RICH_CONSOLE.print("[bold]Examples[/bold]")
    _print_cmdline("bcasl list")
    _print_cmdline("bcasl run /path/to/workspace --timeout 30")
    _print_cmdline("bcasl doctor /path/to/workspace --strict")


def _run_bcasl_headless(args: list[str]) -> int:
    """Run BCASL subcommands in headless mode from the dedicated shell."""
    if not args or args[0] in ("help", "-h", "--help"):
        _print_bcasl_help()
        return 0

    sub = args[0].lower()
    if sub == "list":
        app = _new_bcasl_app(workspace=None)
        if app is None:
            return 1
        plugins = app.get_plugins_info()
        if _RICH_CONSOLE is not None and Table is not None:
            table = Table(
                title=f"BCASL plugins ({len(plugins)})", header_style="bold magenta"
            )
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Version", style="green")
            for plugin in plugins:
                table.add_row(plugin["id"], plugin["name"], str(plugin["version"]))
            _RICH_CONSOLE.print(table)
        else:
            plain(f"Available BCASL plugins ({len(plugins)}):")
            for plugin in plugins:
                plain(f"  - {plugin['id']} ({plugin['name']}) v{plugin['version']}")
        return 0

    if sub == "run":
        workspace: str | None = None
        timeout = 0.0
        i = 1
        while i < len(args):
            tok = args[i]
            if tok in ("-w", "--workspace"):
                if i + 1 >= len(args):
                    error("Missing workspace path after --workspace")
                    return 2
                workspace = _resolve_workspace(args[i + 1])
                i += 2
                continue
            if tok == "--timeout":
                if i + 1 >= len(args):
                    error("Missing value after --timeout")
                    return 2
                try:
                    timeout = float(args[i + 1])
                except ValueError:
                    error("Timeout must be a number.")
                    return 2
                i += 2
                continue
            if workspace is None and not tok.startswith("-"):
                workspace = _resolve_workspace(tok)
                i += 1
                continue
            error(f"Unknown option for bcasl run: {tok}")
            return 2

        if not workspace:
            error("Usage: bcasl run <workspace> [--timeout SECONDS]")
            _print_cmdline("bcasl run -w /path/to/workspace --timeout 30")
            return 2
        ws_path = Path(workspace)
        if not ws_path.exists() or not ws_path.is_dir():
            error(f"Invalid workspace: {workspace}")
            return 1

        app = _new_bcasl_app(workspace=str(ws_path))
        if app is None:
            return 1

        def _log(msg: str) -> None:
            _rprint(f"[BCASL] {msg}", style="bright_blue")

        report = app.run_plugins(
            workspace_dir=str(ws_path),
            timeout=timeout,
            log_callback=_log,
        )
        if report is None:
            error("BCASL execution failed to start.")
            return 1
        if report.ok:
            success("BCASL run completed successfully.")
            return 0
        failed = sum(1 for item in report if not item.success)
        error(f"BCASL run finished with failures: {failed} plugin(s) failed.")
        return 1

    if sub == "doctor":
        workspace: str | None = None
        strict = False
        i = 1
        while i < len(args):
            tok = args[i]
            if tok in ("-w", "--workspace"):
                if i + 1 >= len(args):
                    error("Missing workspace path after --workspace")
                    return 2
                workspace = _resolve_workspace(args[i + 1])
                i += 2
                continue
            if tok == "--strict":
                strict = True
                i += 1
                continue
            if workspace is None and not tok.startswith("-"):
                workspace = _resolve_workspace(tok)
                i += 1
                continue
            error(f"Unknown option for bcasl doctor: {tok}")
            return 2

        from .headless_ops import bcasl_doctor_payload

        payload = bcasl_doctor_payload(workspace=workspace)
        plain("BCASL Doctor")
        for check in payload.get("checks", []):
            status = "OK" if check.get("ok") else "FAIL"
            plain(f"  [{status}] {check.get('name')}: {check.get('message') or ''}")
        if strict and not payload.get("ok", False):
            return 1
        return 0

    error(f"Unknown bcasl subcommand: {sub}")
    _print_bcasl_help()
    return 2


def _parse_workspace_option(args: list[str]) -> tuple[str | None, list[str]]:
    """Extract ``-w/--workspace`` from arguments."""
    ws = None
    kept: list[str] = []
    i = 0
    while i < len(args):
        token = args[i]
        if token in ("-w", "--workspace"):
            if i + 1 >= len(args):
                raise ValueError("Missing workspace path after --workspace")
            ws = _resolve_workspace(args[i + 1])
            i += 2
            continue
        kept.append(token)
        i += 1
    return ws, kept


def _new_engines_app(workspace: str | None = None):
    """Create a headless Engines app instance."""
    try:
        from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp
    except Exception as exc:
        error(f"Unable to load engines module: {exc}")
        return None

    try:
        return EnginesStandaloneApp(
            workspace_dir=workspace,
            language="en",
            theme="dark",
            dry_run=False,
            headless=True,
        )
    except Exception as exc:
        error(f"Failed to initialize engines mode: {exc}")
        return None


def _print_engine_help() -> None:
    """Render engine subcommand help."""
    if _RICH_CONSOLE is None or Table is None:
        plain("")
        plain("Engine commands")
        plain("  engine list [-w|--workspace PATH]")
        plain("  engine compat <engine_id> [-w|--workspace PATH]")
        plain("  engine info <engine_id> [-w|--workspace PATH]")
        plain("  engine dry-run <engine_id> <file.py> [-w|--workspace PATH]")
        plain("  engine compile <engine_id> <file.py> [-w|--workspace PATH]")
        plain("")
        plain("Examples:")
        plain("  engine list")
        plain("  engine compat <engine_id>")
        plain("  engine info <engine_id>")
        plain("  engine dry-run <engine_id> src/main.py")
        plain("  engine compile <engine_id> app.py")
        plain("")
        return

    table = Table(title="Engine Commands", header_style="bold magenta")
    table.add_column("Command", style="bold cyan")
    table.add_column("Action", style="white")
    table.add_row("engine list", "List engines")
    table.add_row("engine compat <engine_id>", "Check compatibility")
    table.add_row("engine info <engine_id>", "Show details")
    table.add_row("engine dry-run <engine_id> <file.py>", "Preview command")
    table.add_row("engine compile <engine_id> <file.py>", "Run compile")
    _RICH_CONSOLE.print(table)
    _RICH_CONSOLE.print("[bold]Examples[/bold]")
    _print_cmdline("engine list")
    _print_cmdline("engine compat <engine_id>")
    _print_cmdline("engine dry-run <engine_id> src/main.py")


def _run_engine_command(args: list[str]) -> int:
    """Execute an `engine ...` command from the dedicated shell."""
    # Cette fonction garde la compatibilité des usages interactifs historiques.
    if not args or args[0] in ("help", "-h", "--help"):
        _print_engine_help()
        return 0

    try:
        workspace, clean_args = _parse_workspace_option(args)
    except ValueError as exc:
        error(str(exc))
        return 2

    if not clean_args:
        _print_engine_help()
        return 0

    sub = clean_args[0].lower()
    app = _new_engines_app(workspace=workspace)
    if app is None:
        return 1

    if sub == "list":
        engines = app.load_engines()
        if _RICH_CONSOLE is not None and Table is not None:
            table = Table(
                title=f"Engines ({len(engines)})", header_style="bold magenta"
            )
            table.add_column("Status", style="bold")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Version", style="green")
            for eng in engines:
                compat = app.check_engine_compatibility(eng["id"])
                ok = bool(compat.get("compatible"))
                status = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
                table.add_row(status, eng["id"], eng["name"], str(eng["version"]))
            _RICH_CONSOLE.print(table)
        else:
            plain(f"Available engines ({len(engines)}):")
            for eng in engines:
                compat = app.check_engine_compatibility(eng["id"])
                status = "OK" if compat.get("compatible") else "FAIL"
                plain(f"  [{status}] {eng['id']} - {eng['name']} v{eng['version']}")
        return 0

    if sub == "compat":
        if len(clean_args) < 2:
            error("Usage: engine compat <engine_id>")
            _print_cmdline("engine compat <engine_id>")
            return 2
        engine_id = clean_args[1]
        result = app.check_engine_compatibility(engine_id)
        if result.get("compatible"):
            success(f"Engine compatible: {engine_id}")
            return 0
        error(f"Engine not compatible: {engine_id}")
        if result.get("message"):
            warn(f"Reason: {result['message']}")
        missing = result.get("missing_requirements") or []
        for req in missing:
            warn(f"Missing: {req}")
        return 1

    if sub == "info":
        if len(clean_args) < 2:
            error("Usage: engine info <engine_id>")
            _print_cmdline("engine info <engine_id>")
            return 2
        engine_id = clean_args[1]
        eng = app.get_engine_info(engine_id)
        if not eng:
            error(f"Engine not found: {engine_id}")
            return 1
        compat = app.check_engine_compatibility(engine_id)
        plain(f"Engine: {eng['name']}")
        plain(f"  ID: {eng['id']}")
        plain(f"  Version: {eng['version']}")
        plain(f"  Required core: {eng['required_core']}")
        plain(f"  Compatible: {'yes' if compat.get('compatible') else 'no'}")
        if compat.get("message"):
            plain(f"  Message: {compat['message']}")
        return 0

    if sub in ("dry-run", "compile"):
        if len(clean_args) < 3:
            error(f"Usage: engine {sub} <engine_id> <file.py>")
            _print_cmdline(f"engine {sub} <engine_id> src/main.py")
            return 2
        engine_id = clean_args[1]
        file_path = _resolve_workspace(clean_args[2])
        if not file_path:
            error("File path is required.")
            return 2
        file_obj = Path(file_path)
        if not file_obj.exists():
            error(f"File not found: {file_path}")
            return 1
        if not file_obj.is_file():
            error(f"Not a file: {file_path}")
            return 1

        dry_run = sub == "dry-run"
        result = app.run_compilation(engine_id, str(file_obj), dry_run=dry_run)
        if result.get("success"):
            if dry_run:
                success("Dry-run successful.")
                _rprint("Command preview:", style="bold")
                _print_cmdline(result.get("command", ""))
            else:
                success("Compilation successful.")
                out = (result.get("stdout") or "").strip()
                if out:
                    plain("Output:")
                    plain(out)
            return 0

        error("Compilation failed.")
        if result.get("error"):
            warn(f"Error: {result['error']}")
        err_out = (result.get("stderr") or "").strip()
        if err_out:
            plain("Stderr:")
            plain(err_out, err=True)
        return 1

    error(f"Unknown engine subcommand: {sub}")
    _print_engine_help()
    return 2


def _run_unload() -> int:
    """Unload all engines from the dedicated shell."""
    result = unload_all_engines()
    if result["status"] == "success":
        success(result["message"])
        if result["unloaded"]:
            plain("  Unloaded engines:")
            for eid in result["unloaded"]:
                plain(f"    - {eid}")
    else:
        error(result["message"])
    return 0 if result["status"] == "success" else 1


def run_dedicated_cli(app_version: str) -> int:
    """Run the interactive dedicated CLI loop."""
    try:
        from rich.prompt import Prompt  # type: ignore
    except Exception:
        Prompt = None

    # Session interactive avancée (completion, style) si prompt_toolkit est dispo.
    session = None
    if (
        PromptSession is not None
        and WordCompleter is not None
        and InMemoryHistory is not None
        and Style is not None
    ):
        commands = [
            "help",
            "version",
            "info",
            "main",
            "main --ide-gui",
            "main ide",
            "bcasl",
            "bcasl list",
            "bcasl run",
            "bcasl run -w",
            "bcasl run --timeout",
            "engines",
            "engines --dry-run",
            "engine",
            "engine list",
            "engine compat",
            "engine info",
            "engine dry-run",
            "engine compile",
            "check",
            "init",
            "config-auto",
            "cfg-auto",
            "ws",
            "ws init",
            "ws config-auto",
            "ws apply",
            "workspace apply",
            "workspace select",
            "unload",
            "exit",
            "quit",
            "--help",
            "--ide-gui",
            "--timeout",
            "--workspace",
            "-w",
            "-d",
        ]
        completer = WordCompleter(commands, ignore_case=True, sentence=True)
        style = Style.from_dict(
            {
                "cmd": "bold ansicyan",
                "flag_long": "bold ansiyellow",
                "flag_short": "ansiyellow",
                "path": "ansigreen",
                "arg": "ansiwhite",
                "plain": "ansiwhite",
                "prompt": "bold ansibrightblue",
            }
        )
        session = PromptSession(
            lexer=ArkCommandLexer(),
            completer=completer,
            complete_while_typing=True,
            style=style,
            history=InMemoryHistory(),
        )

    # Affichage initial.
    _print_banner(app_version)
    _print_help()

    while True:
        try:
            # Lecture de ligne compatible avec plusieurs backends (prompt_toolkit/rich/input).
            if session is not None:
                line = session.prompt([("class:prompt", "ark-cli> ")]).strip()
            elif Prompt is not None:
                line = Prompt.ask(
                    "[bold bright_blue]ark-cli[/bold bright_blue]"
                ).strip()
            else:
                line = input("ark-cli> ").strip()
        except (EOFError, KeyboardInterrupt):
            plain("")
            info("Closing dedicated CLI.")
            return 0

        if not line:
            continue

        try:
            parts = shlex.split(line)
        except Exception as exc:
            error(f"Invalid command: {exc}")
            continue

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            # Dispatch impératif simple: lisible et facile à maintenir pour un shell interactif.
            if cmd in ("exit", "quit"):
                info("Dedicated CLI closed.")
                return 0
            if cmd in ("help", "h", "?"):
                _print_help()
                continue
            if cmd == "version":
                info(f"PyCompiler ARK v{app_version}")
                continue
            if cmd == "info":
                print_system_info(app_version)
                continue
            if cmd == "main":
                ide_gui = False
                for tok in args:
                    low = tok.lower()
                    if low in ("--ide-gui", "ide", "idelike", "ide-like"):
                        ide_gui = True
                    else:
                        warn(f"Unknown option for main: {tok}")
                        plain("Usage: main [--ide-gui]")
                        ide_gui = False
                        break
                launch_main_gui(no_splash=False, ide_gui=ide_gui)
                continue
            if cmd == "bcasl":
                # Les sous-commandes `list/run` passent en mode headless.
                if args and args[0].lower() in ("help", "list", "run"):
                    _run_bcasl_headless(args)
                    continue
                _run_bcasl(args)
                continue
            if cmd == "engine":
                _run_engine_command(args)
                continue
            if cmd == "engines":
                # Compat: `engines <subcommand>` redirige vers le parser `engine`.
                if args and args[0].lower() in (
                    "help",
                    "list",
                    "compat",
                    "info",
                    "dry-run",
                    "compile",
                ):
                    _run_engine_command(args)
                    continue
                _run_engines(args)
                continue
            if cmd == "check":
                run_check(args)
                continue
            if cmd == "init":
                run_init(args)
                continue
            if cmd == "config-auto":
                run_config_auto(args)
                continue
            if cmd == "cfg-auto":
                run_config_auto(args)
                continue
            if cmd == "ws":
                if not args:
                    warn(
                        "Usage: ws <init|config-auto|cfg-auto|apply|select> [workspace]"
                    )
                    continue
                sub = args[0].lower()
                ws_args = args[1:]
                if sub == "init":
                    run_init(ws_args)
                    continue
                if sub in ("config-auto", "cfg-auto"):
                    run_config_auto(ws_args)
                    continue
                if sub in ("apply", "select"):
                    run_workspace_apply(ws_args)
                    continue
                warn(f"Unknown ws subcommand: {sub}")
                continue
            if cmd == "workspace":
                if not args:
                    warn("Usage: workspace <apply|select> [workspace]")
                    continue
                sub = args[0].lower()
                if sub in ("apply", "select"):
                    run_workspace_apply(args[1:])
                    continue
                warn(f"Unknown workspace subcommand: {sub}")
                continue
            if cmd == "unload":
                _run_unload()
                continue
            warn(f"Unknown command: {cmd}")
            plain("Type `help` to list commands.")
        except Exception as exc:
            error(f"Internal error: {exc}")
