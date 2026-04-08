# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

from pathlib import Path

from OnlyMod.EngineOnlyMod.app import EnginesStandaloneApp, MockLog


class _DummyEngine:
    def __init__(self, required_tools: dict[str, list[str]] | None = None):
        self.required_tools = required_tools or {"python": [], "system": []}


def test_headless_tools_preflight_fails_on_missing_system_tools(monkeypatch) -> None:
    app = EnginesStandaloneApp(headless=True, workspace_dir=str(Path.cwd()))
    engine = _DummyEngine(required_tools={"python": [], "system": ["patchelf"]})

    monkeypatch.setattr(app, "_missing_system_tools", lambda tools: ["patchelf"])

    ok, error = app._ensure_engine_tools_headless(engine)

    assert ok is False
    assert "Missing system tools" in error
    assert "ARK_AUTO_INSTALL_SYSTEM_TOOLS=1" in error


def test_headless_tools_preflight_installs_missing_python_tools(monkeypatch) -> None:
    app = EnginesStandaloneApp(headless=True, workspace_dir=str(Path.cwd()))
    engine = _DummyEngine(required_tools={"python": ["pyinstaller"], "system": []})

    state = {"calls": 0}

    def _missing_python(*_args, **_kwargs):
        state["calls"] += 1
        return ["pyinstaller"] if state["calls"] == 1 else []

    install_called = {"ok": False}

    def _install_python(*_args, **_kwargs):
        install_called["ok"] = True
        return True, ""

    monkeypatch.setattr(app, "_missing_system_tools", lambda tools: [])
    monkeypatch.setattr(app, "_missing_python_tools", _missing_python)
    monkeypatch.setattr(app, "_install_python_tools_headless", _install_python)

    ok, error = app._ensure_engine_tools_headless(engine)

    assert ok is True
    assert error == ""
    assert install_called["ok"] is True
    assert state["calls"] >= 2


def test_run_compilation_headless_returns_preflight_error(monkeypatch) -> None:
    app = EnginesStandaloneApp(headless=True, workspace_dir=str(Path.cwd()))

    monkeypatch.setattr(
        app,
        "check_engine_compatibility",
        lambda engine_id: {
            "compatible": True,
            "message": None,
            "missing_requirements": [],
        },
    )
    monkeypatch.setattr(app, "_create_engine_for_run", lambda engine_id: _DummyEngine())
    monkeypatch.setattr(
        app, "_ensure_engine_tools_headless", lambda engine: (False, "preflight failed")
    )

    result = app.run_compilation(
        "pyinstaller", str(Path.cwd() / "main.py"), dry_run=False
    )

    assert result["success"] is False
    assert result["return_code"] == -1
    assert "preflight failed" in result["error"]


def test_mock_log_can_disable_stdout_echo(monkeypatch) -> None:
    called = {"n": 0}

    def _fake_print(*_args, **_kwargs):
        called["n"] += 1

    monkeypatch.setattr("builtins.print", _fake_print)

    silent_log = MockLog(echo=False)
    silent_log.append("hello")

    loud_log = MockLog(echo=True)
    loud_log.append("world")

    assert called["n"] == 1
