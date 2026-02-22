# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from typing import Iterable, List

try:
    from rich.console import Console
    from rich.table import Table
except Exception:  # pragma: no cover - optional dependency
    Console = None
    Table = None


COMMANDS: List[str] = ["bcasl", "engines", "main", "unload"]
GLOBAL_FLAGS: List[str] = ["--help", "-h", "--version", "--info", "--completion", "--unload"]
ENGINE_FLAGS: List[str] = ["--dry-run", "-l", "--language", "-t", "--theme"]


def command_suggestions() -> List[str]:
    return sorted(set(COMMANDS + GLOBAL_FLAGS))


def print_command_completion(shell: str) -> None:
    lines = [f"# {shell.upper()} completion for PyCompiler ARK", "# Commands:"]
    lines.extend(f"  {cmd}" for cmd in COMMANDS)
    lines.append("# Global flags:")
    lines.extend(f"  {flag}" for flag in GLOBAL_FLAGS)
    lines.append("# Engine flags:")
    lines.extend(f"  {flag}" for flag in ENGINE_FLAGS)

    if Console is None or Table is None:
        print("\n".join(lines))
        return

    console = Console()
    table = Table(title="PyCompiler ARK Completion")
    table.add_column("Type", style="bold")
    table.add_column("Values")
    table.add_row("Commands", ", ".join(COMMANDS))
    table.add_row("Global flags", ", ".join(GLOBAL_FLAGS))
    table.add_row("Engine flags", ", ".join(ENGINE_FLAGS))
    console.print(table)
