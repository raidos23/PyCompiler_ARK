from Core.Globals import _UiInvoker, _latest_gui_instance


from PySide6.QtCore import QEventLoop as _QEventLoop
from PySide6.QtWidgets import QApplication


def request_workspace_change_from_BcPlugin(folder: str) -> bool:
    try:
        gui = _latest_gui_instance
        if gui is None:
            # Try active window
            app = QApplication.instance()
            w = app.activeWindow() if app else None
            if w and hasattr(w, "apply_workspace_selection"):
                gui = w
        if gui is None:
            # No GUI instance: accept request by contract
            return True
        invoker = getattr(gui, "_ui_invoker", None)
        if invoker is None or not isinstance(invoker, _UiInvoker):
            invoker = _UiInvoker(gui)
            setattr(gui, "_ui_invoker", invoker)
        result_holder = {"ok": False}
        loop = _QEventLoop()

        def _do():
            try:
                result_holder["ok"] = bool(
                    gui.apply_workspace_selection(str(folder), source="plugin")
                )
            except Exception:
                result_holder["ok"] = False
            finally:
                try:
                    loop.quit()
                except Exception:
                    pass

        try:
            invoker.post(_do)
        except Exception:
            # Fallback: direct call in case invoker posting fails
            try:
                return bool(gui.apply_workspace_selection(str(folder), source="plugin"))
            except Exception:
                return False
        loop.exec()
        return bool(result_holder.get("ok", False))
    except Exception:
        # Accept by contract even on unexpected errors
        return True