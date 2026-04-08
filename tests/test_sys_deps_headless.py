# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Headless system dependency installation tests."""

from __future__ import annotations


def test_install_system_packages_headless_linux_uses_noninteractive_sudo(
    monkeypatch,
) -> None:
    """Headless mode should run package install commands without Qt widgets."""
    import Core.sys_deps as sys_deps

    executed: list[list[str]] = []

    class _Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(
        sys_deps.shutil, "which", lambda name: "/usr/bin/apt" if name == "apt" else None
    )
    monkeypatch.setattr(sys_deps.os, "geteuid", lambda: 1000, raising=False)

    def _fake_run(cmd, **_kwargs):
        executed.append(list(cmd))
        return _Result(0)

    monkeypatch.setattr(sys_deps.subprocess, "run", _fake_run)

    assert sys_deps.install_system_packages(["cloc"], gui=None) is True
    assert executed == [
        ["sudo", "-n", "apt-get", "-o", "Acquire::Retries=3", "update"],
        [
            "sudo",
            "-n",
            "apt-get",
            "-o",
            "Dpkg::Options::=--force-confdef",
            "-o",
            "Dpkg::Options::=--force-confnew",
            "-o",
            "Acquire::Retries=3",
            "install",
            "-y",
            "--no-install-recommends",
            "cloc",
        ],
    ]


def test_install_system_packages_headless_does_not_use_qt_manager(monkeypatch) -> None:
    """Headless mode must bypass the Qt-based SysDependencyManager path."""
    import Core.sys_deps as sys_deps

    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(
        sys_deps.shutil, "which", lambda name: "/usr/bin/dnf" if name == "dnf" else None
    )
    monkeypatch.setattr(sys_deps.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(
        sys_deps,
        "SysDependencyManager",
        lambda _gui: (_ for _ in ()).throw(
            AssertionError("Qt manager should not be used in headless mode")
        ),
    )

    class _Result:
        def __init__(self, returncode: int = 0) -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    monkeypatch.setattr(sys_deps.subprocess, "run", lambda *_a, **_k: _Result(0))

    assert sys_deps.install_system_packages(["cloc"], gui=None) is True


def test_install_system_packages_headless_retries_transient_failures(
    monkeypatch,
) -> None:
    """Headless install should retry command steps before failing."""
    import Core.sys_deps as sys_deps

    attempts = {"count": 0}

    class _Result:
        def __init__(self, returncode: int) -> None:
            self.returncode = returncode
            self.stdout = ""
            self.stderr = ""

    monkeypatch.setattr("platform.system", lambda: "Linux")
    monkeypatch.setattr(
        sys_deps.shutil,
        "which",
        lambda name: "/usr/bin/dnf" if name == "dnf" else None,
    )
    monkeypatch.setattr(sys_deps.os, "geteuid", lambda: 0, raising=False)
    monkeypatch.setattr(sys_deps.time, "sleep", lambda *_a, **_k: None)

    def _fake_run(_cmd, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            return _Result(1)
        return _Result(0)

    monkeypatch.setattr(sys_deps.subprocess, "run", _fake_run)

    assert sys_deps.install_system_packages(["cloc"], gui=None) is True
    assert attempts["count"] == 2
