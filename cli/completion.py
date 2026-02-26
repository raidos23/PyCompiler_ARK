# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from typing import List

COMMANDS: List[str] = ["bcasl", "engines", "main", "unload"]
GLOBAL_FLAGS: List[str] = [
    "--help",
    "-h",
    "--version",
    "--info",
    "--cli",
    "--ide-gui",
    "--completion",
    "--unload",
    "--verbose",
    "--no-splash",
]
ENGINE_FLAGS: List[str] = ["--dry-run", "-l", "--language", "-t", "--theme"]


def _bash_script() -> str:
    cmds = " ".join(COMMANDS)
    gflags = " ".join(GLOBAL_FLAGS)
    eflags = " ".join(ENGINE_FLAGS)
    return f"""
_pycompiler_ark_complete() {{
    local cur prev
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"

    if [[ $COMP_CWORD -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "{cmds} {gflags}" -- "$cur") )
        return 0
    fi

    case "${{COMP_WORDS[1]}}" in
        engines)
            COMPREPLY=( $(compgen -W "{eflags}" -- "$cur") )
            return 0
            ;;
        bcasl|main|unload)
            COMPREPLY=( $(compgen -W "" -- "$cur") )
            return 0
            ;;
        *)
            COMPREPLY=( $(compgen -W "{gflags}" -- "$cur") )
            return 0
            ;;
    esac
}}

complete -F _pycompiler_ark_complete pycompiler_ark
""".strip()


def _zsh_script() -> str:
    cmds = " ".join(COMMANDS)
    gflags = " ".join(GLOBAL_FLAGS)
    eflags = " ".join(ENGINE_FLAGS)
    return f"""
#compdef pycompiler_ark

_pycompiler_ark() {{
  local -a commands global_flags engine_flags
  commands=({cmds})
  global_flags=({gflags})
  engine_flags=({eflags})

  if (( CURRENT == 2 )); then
    _describe -t commands 'commands' commands
    _describe -t options 'options' global_flags
    return
  fi

  case $words[2] in
    engines)
      _describe -t options 'engine options' engine_flags
      return
      ;;
    *)
      _describe -t options 'options' global_flags
      return
      ;;
  esac
}}

_pycompiler_ark "$@"
""".strip()


def _fish_script() -> str:
    lines = [
        "complete -c pycompiler_ark -f",
    ]
    cmd_list = " ".join(COMMANDS)
    for cmd in COMMANDS:
        lines.append(
            f"complete -c pycompiler_ark -n 'not __fish_seen_subcommand_from {cmd_list}' -a {cmd}"
        )
    for flag in GLOBAL_FLAGS:
        if flag.startswith("--"):
            lines.append(f"complete -c pycompiler_ark -l {flag.lstrip('-')}")
        elif flag.startswith("-"):
            lines.append(f"complete -c pycompiler_ark -s {flag.lstrip('-')}")
    for flag in ENGINE_FLAGS:
        if flag.startswith("--"):
            lines.append(
                f"complete -c pycompiler_ark -n '__fish_seen_subcommand_from engines' -l {flag.lstrip('-')}"
            )
        else:
            lines.append(
                f"complete -c pycompiler_ark -n '__fish_seen_subcommand_from engines' -s {flag.lstrip('-')}"
            )
    return "\n".join(lines)


def generate_completion(shell: str) -> str:
    shell = shell.lower().strip()
    if shell == "bash":
        return _bash_script()
    if shell == "zsh":
        return _zsh_script()
    if shell == "fish":
        return _fish_script()
    raise ValueError(f"Unsupported shell: {shell}")


def print_command_completion(shell: str) -> None:
    print(generate_completion(shell))
