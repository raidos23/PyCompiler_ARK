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