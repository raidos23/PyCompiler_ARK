from __future__ import annotations

import os

import pytest

from Core.process_security import (
    resolve_executable,
    sanitize_cli_args,
    sanitize_env_overrides,
    secure_command,
)


def test_sanitize_cli_args_rejects_null_byte() -> None:
    with pytest.raises(ValueError):
        sanitize_cli_args(["ok", "bad\x00arg"])


def test_sanitize_env_overrides_filters_invalid_keys() -> None:
    out = sanitize_env_overrides(
        {
            "GOOD_KEY": "1",
            "bad-key": "2",
            "ALSO_BAD\nKEY": "3",
            "NULL_VAL": "ok\x00bad",
        }
    )
    assert out == {"GOOD_KEY": "1"}


def test_resolve_executable_from_path() -> None:
    py = resolve_executable("python")
    assert py
    assert os.path.isabs(py)


def test_secure_command_normalizes_inputs() -> None:
    program, args, env = secure_command("python", ["-V"], {"ARK_WORKSPACE": "/tmp/ws"})
    assert os.path.isabs(program)
    assert args == ["-V"]
    assert env.get("ARK_WORKSPACE") == "/tmp/ws"
