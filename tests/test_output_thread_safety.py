# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Samuel Amen Ague
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

"""Thread-safety of Ui.output log widget appends (GUI segfault guard)."""

from __future__ import annotations

import os
import threading
import time

import pytest

# Must be set before QApplication is created.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["test_output_thread_safety"])
    return app


def test_output_info_from_worker_thread_does_not_segfault(qapp, monkeypatch):
    from pycompiler_ark.Ui import output

    window = QMainWindow()
    log_widget = QTextEdit()
    window.setCentralWidget(log_widget)
    window.log = log_widget
    window.show()
    qapp.processEvents()

    monkeypatch.setattr(output, "_log_widget", log_widget)

    errors: list[BaseException] = []

    def _worker():
        try:
            for i in range(20):
                output.info(f"worker-line-{i}")
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    thread = threading.Thread(target=_worker)
    thread.start()

    deadline = time.time() + 3.0
    while thread.is_alive() and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.01)

    thread.join(timeout=2.0)
    for _ in range(50):
        qapp.processEvents()
        time.sleep(0.01)

    assert not thread.is_alive()
    assert errors == []
    text = log_widget.toPlainText()
    assert "worker-line-0" in text
    assert "worker-line-19" in text

    window.close()


def test_output_info_on_gui_thread_still_works(qapp, monkeypatch):
    from pycompiler_ark.Ui import output

    window = QMainWindow()
    log_widget = QTextEdit()
    window.setCentralWidget(log_widget)
    window.log = log_widget

    monkeypatch.setattr(output, "_log_widget", log_widget)

    output.info("main-thread-line")
    qapp.processEvents()

    assert "main-thread-line" in log_widget.toPlainText()
    window.close()


def test_bridge_log_message_level_preferred(qapp, monkeypatch):
    from pycompiler_ark.Ui import output

    calls: list[tuple] = []

    class Bridge:
        def log_message_level(self, level, fr, en):
            calls.append((level, fr, en))

    # Even with a cached QTextEdit, bridge must win to avoid double-write.
    fake_widget = QTextEdit()
    monkeypatch.setattr(output, "_log_widget", fake_widget)

    output.info("bridged-msg", gui=Bridge())
    qapp.processEvents()

    assert calls == [("info", "bridged-msg", "bridged-msg")]
    assert "bridged-msg" not in fake_widget.toPlainText()
