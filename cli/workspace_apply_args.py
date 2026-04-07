# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from typing import Optional


def build_workspace_apply_args(
    *,
    path: Optional[str],
    as_json: bool,
    with_venv: bool,
    entrypoint: Optional[str],
    no_auto_config: bool,
    no_inspect_files: bool,
    no_apply_venv_pref: bool,
    no_apply_engine_configs: bool,
    strict: bool,
    require_entrypoint: bool,
) -> list[str]:
    """Build argument list for workspace apply/select headless handlers."""
    args: list[str] = []
    if path:
        args.append(path)
    if as_json:
        args.append("--json")
    if with_venv:
        args.append("--with-venv")
    if entrypoint:
        args.extend(["--entrypoint", entrypoint])
    if no_auto_config:
        args.append("--no-auto-config")
    if no_inspect_files:
        args.append("--no-inspect-files")
    if no_apply_venv_pref:
        args.append("--no-apply-venv-pref")
    if no_apply_engine_configs:
        args.append("--no-apply-engine-configs")
    if strict:
        args.append("--strict")
    if require_entrypoint:
        args.append("--require-entrypoint")
    return args
