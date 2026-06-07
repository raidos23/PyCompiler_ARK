"""Pause CLI spinners and output redirection for interactive Rich prompts."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Any, Iterator, Optional, TextIO, Tuple

_REAL_STDOUT = sys.__stdout__
_REAL_STDERR = sys.__stderr__
_active_statuses: list[Any] = []


def _is_noninteractive_env() -> bool:
    try:
        from pycompiler_ark.Ui.Cli.runtime import is_noninteractive

        return is_noninteractive()
    except Exception:
        return False


def _open_tty_stream() -> Tuple[Optional[TextIO], bool]:
    """Return a readable TTY stream for prompts, even when stdin is piped."""
    try:
        if sys.stdin.isatty():
            return sys.stdin, False
    except Exception:
        pass
    if os.name != "nt":
        try:
            tty = open("/dev/tty", "r", encoding="utf-8", errors="replace")
            return tty, True
        except OSError:
            pass
    return None, False


def ask_yes_no(prompt: str, *, default_yes: bool = True) -> bool:
    """Blocking yes/no prompt; never auto-accept on EOF or missing TTY."""
    if os.environ.get("PYCOMPILER_YES") == "1":
        return True

    try:
        from pycompiler_ark.Ui.i18n import is_french_language

        french = bool(is_french_language(None))
    except Exception:
        french = False

    stream, close_stream = _open_tty_stream()
    if stream is None:
        if _is_noninteractive_env():
            return default_yes
        try:
            from pycompiler_ark.Ui.i18n import log_with_level

            log_with_level(
                None,
                "warning",
                "[PROMPT] Terminal non interactif — action refusee (reponse: non).",
            )
        except Exception:
            pass
        return False

    try:
        from rich.prompt import Confirm
    except Exception:
        Confirm = None

    try:
        if Confirm is not None:
            with cli_pause_for_user_input() as console:
                try:
                    return bool(Confirm.ask(prompt, default=default_yes, console=console))
                except EOFError:
                    return False

        hint = "o/n" if french else "y/n"
        default_label = "o" if default_yes else "n"
        out = _REAL_STDOUT
        while True:
            out.write(f"{prompt} [{hint}] ({default_label}): ")
            out.flush()
            line = stream.readline()
            if line == "":
                # EOF: do not treat as implicit consent.
                out.write("\n")
                out.flush()
                return False
            answer = line.strip().lower()
            if answer == "":
                out.write("\n")
                out.flush()
                return default_yes
            if answer in ("y", "yes", "o", "oui"):
                out.write("\n")
                out.flush()
                return True
            if answer in ("n", "no", "non"):
                out.write("\n")
                out.flush()
                return False
            invalid = (
                "Reponse invalide. Tapez o ou n."
                if french
                else "Invalid answer. Type y or n."
            )
            out.write(invalid + "\n")
            out.flush()
    finally:
        if close_stream and stream is not None:
            try:
                stream.close()
            except Exception:
                pass


def register_cli_status(status: Any) -> None:
    """Register a Rich status spinner that must pause during user prompts."""
    if status is not None and status not in _active_statuses:
        _active_statuses.append(status)


def unregister_cli_status(status: Any) -> None:
    try:
        _active_statuses.remove(status)
    except ValueError:
        pass


def _stop_active_statuses() -> list[Any]:
    stopped: list[Any] = []
    for status in list(_active_statuses):
        try:
            status.stop()
            stopped.append(status)
        except Exception:
            pass
    return stopped


def _restart_statuses(statuses: list[Any]) -> None:
    for status in statuses:
        try:
            status.start()
        except Exception:
            pass


@contextmanager
def cli_pause_for_user_input() -> Iterator[Optional[Any]]:
    """Stop spinners and restore the real terminal for prompts."""
    stopped = _stop_active_statuses()
    prev_out, prev_err = sys.stdout, sys.stderr
    sys.stdout = _REAL_STDOUT
    sys.stderr = _REAL_STDERR
    try:
        console = None
        try:
            from pycompiler_ark.Ui.Cli.output import get_console

            console = get_console()
        except Exception:
            pass
        if console is None:
            try:
                from rich.console import Console

                console = Console()
            except Exception:
                console = None
        yield console
    finally:
        sys.stdout = prev_out
        sys.stderr = prev_err
        _restart_statuses(stopped)
