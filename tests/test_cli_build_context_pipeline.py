# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import sys
from pathlib import Path

from Core.Locking import compare_lock_payloads, included_workspace_files
from engine_sdk import BuildContext
from Ui.Cli import helpers


def test_run_engine_compile_uses_build_context(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class FakeEngine:
        def program_and_args(self, context: BuildContext):
            captured["context"] = context
            captured["config"] = getattr(self, "_config_overrides", {})
            return sys.executable, ["-c", "print('built')"]

    class Completed:
        returncode = 0
        stdout = "built\n"
        stderr = ""

    monkeypatch.setattr("Core.engine.create", lambda _engine_id: FakeEngine())
    monkeypatch.setattr(
        helpers.subprocess, "run", lambda *_args, **_kwargs: Completed()
    )

    context = BuildContext(
        project_name="demo",
        entry_point="main.py",
        output_dir="dist/",
        exclude_patterns=[],
        data_mappings=[],
        icon=None,
    )

    result = helpers.run_engine_compile(
        workspace=tmp_path,
        engine_id="fake",
        context=context,
        engine_config={"standalone": True},
    )

    assert result["success"] is True
    assert captured["context"] is context
    assert captured["config"] == {"standalone": True}


def test_run_engine_compile_rejects_obsolete_entrypoint(tmp_path: Path) -> None:
    context = BuildContext(
        project_name="demo",
        entry_point="missing.py",
        output_dir="dist/",
        exclude_patterns=[],
        data_mappings=[],
        icon=None,
    )

    result = helpers.run_engine_compile(
        workspace=tmp_path,
        engine_id="fake",
        context=context,
    )

    assert result["success"] is False
    assert "obsolete" in result["error"]


def test_compare_lock_payloads_ignores_build_id() -> None:
    base = {
        "build_id": "ARK_2026_05_15_001",
        "project": {"name": "demo", "version": "1.0.0", "entry": "main.py"},
        "workspace_hash": "sha256:abc",
    }
    regenerated = dict(base)
    regenerated["build_id"] = "ARK_2026_05_15_002"

    assert compare_lock_payloads(base, regenerated) is True


def test_workspace_file_inclusion_respects_recursive_excludes(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print('ok')\n", encoding="utf-8")
    nested_build = tmp_path / "build" / "app"
    nested_build.mkdir(parents=True)
    (nested_build / "generated.txt").write_text("generated\n", encoding="utf-8")
    nested_dist = tmp_path / "dist" / "app"
    nested_dist.mkdir(parents=True)
    (nested_dist / "generated.txt").write_text("generated\n", encoding="utf-8")
    nested_venv = tmp_path / ".venv" / "bin"
    nested_venv.mkdir(parents=True)
    (nested_venv / "python").write_text("python\n", encoding="utf-8")

    files = {
        path.relative_to(tmp_path).as_posix()
        for path in included_workspace_files(
            tmp_path,
            ["build/**", "dist/**", ".venv/**"],
        )
    }

    assert files == {"main.py"}
