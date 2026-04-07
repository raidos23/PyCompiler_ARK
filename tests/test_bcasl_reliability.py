from __future__ import annotations

from pathlib import Path

from bcasl.Base import BcPluginBase, PluginMeta
from bcasl.executor import BCASL


class _FailPlugin(BcPluginBase):
    def __init__(self) -> None:
        super().__init__(
            meta=PluginMeta(id="fail", name="Fail", version="1.0.0"),
            requires=(),
            priority=1,
        )

    def on_pre_compile(
        self, ctx
    ) -> None:  # pragma: no cover - behavior tested by side effects
        raise RuntimeError("boom")


class _DependentPlugin(BcPluginBase):
    def __init__(self, marker: dict) -> None:
        self._marker = marker
        super().__init__(
            meta=PluginMeta(id="dep", name="Dep", version="1.0.0"),
            requires=("fail",),
            priority=2,
        )

    def on_pre_compile(
        self, ctx
    ) -> None:  # pragma: no cover - behavior tested by marker
        self._marker["ran"] = True


class _OkPlugin(BcPluginBase):
    def __init__(self, marker: dict) -> None:
        self._marker = marker
        super().__init__(
            meta=PluginMeta(id="ok", name="Ok", version="1.0.0"),
            requires=(),
            priority=2,
        )

    def on_pre_compile(
        self, ctx
    ) -> None:  # pragma: no cover - behavior tested by marker
        self._marker["ran"] = True


def test_skip_dependents_on_failure_default_true(tmp_path: Path) -> None:
    marker = {"ran": False}
    mgr = BCASL(tmp_path, config={"options": {"sandbox": False}}, sandbox=False)
    mgr.add_plugin(_FailPlugin())
    mgr.add_plugin(_DependentPlugin(marker))

    rep = mgr.run_pre_compile()
    by_id = {it.plugin_id: it for it in rep}

    assert by_id["fail"].success is False
    assert by_id["dep"].success is False
    assert "dépendance échouée" in by_id["dep"].error
    assert marker["ran"] is False


def test_fail_fast_stops_remaining_plugins(tmp_path: Path) -> None:
    ok_marker = {"ran": False}
    mgr = BCASL(
        tmp_path,
        config={"options": {"sandbox": False, "fail_fast": True}},
        sandbox=False,
    )
    mgr.add_plugin(_FailPlugin())
    mgr.add_plugin(_OkPlugin(ok_marker))

    rep = mgr.run_pre_compile()
    ids = [it.plugin_id for it in rep]

    assert ids == ["fail"]
    assert ok_marker["ran"] is False


def test_invalid_timeout_is_normalized(tmp_path: Path) -> None:
    mgr = BCASL(tmp_path, config={}, sandbox=False, plugin_timeout_s=float("nan"))
    assert mgr.plugin_timeout_s == 0.0
