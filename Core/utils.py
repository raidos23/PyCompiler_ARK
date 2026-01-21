import asyncio
import threading
from PySide6.QtCore import QObject, QTimer, Qt, Signal


class _UiInvoker(QObject):
    _sig = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sig.connect(self._exec, Qt.QueuedConnection)

    def post(self, fn):
        try:
            self._sig.emit(fn)
        except Exception:
            pass

    def _exec(self, fn):
        try:
            fn()
        except Exception:
            pass


def _run_coro_async(coro, on_result, ui_owner=None):
    invoker = None
    try:
        if ui_owner is not None and isinstance(ui_owner, QObject):
            invoker = getattr(ui_owner, "_ui_invoker", None)
            if invoker is None:
                invoker = _UiInvoker(ui_owner)
                setattr(ui_owner, "_ui_invoker", invoker)
    except Exception:
        invoker = None

    def _runner():
        try:
            res = asyncio.run(coro)
        except Exception as e:
            res = e
        try:
            if invoker is not None:
                invoker.post(lambda: on_result(res))
            else:
                QTimer.singleShot(0, lambda: on_result(res))
        except Exception:
            pass

    threading.Thread(target=_runner, daemon=True).start()