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

from __future__ import annotations

import os
import sys
from pathlib import Path

from .icons import set_app_icon, set_window_icon
from .output import error
from .runtime import ROOT_DIR, handle_fatal


def _get_or_create_qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def _get_app_version() -> str:
    try:
        core_init = Path(ROOT_DIR) / "Core" / "__init__.py"
        for line in core_init.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("__version__"):
                _, value = stripped.split("=", 1)
                return value.strip().strip("\"'")
    except Exception:
        pass
    return "unknown"


def _apply_small_screen_compaction(app, window) -> None:
    try:
        from PySide6.QtWidgets import QLayout

        screen = app.primaryScreen()
        geo = screen.availableGeometry() if screen is not None else None
        if geo and (geo.width() < 1000 or geo.height() < 650):
            try:
                lays = (
                    window.ui.findChildren(QLayout)
                    if hasattr(window, "ui")
                    else []
                )
                for layout in lays:
                    try:
                        layout.setContentsMargins(6, 6, 6, 6)
                        layout.setSpacing(6)
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass


def launch_main_application(
    no_splash: bool = False, ide_gui: bool = False, classic_gui: bool = False
) -> int:
    try:
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QPixmap
        from PySide6.QtWidgets import QSplashScreen

        from ..Gui.Gui import PyCompilerArkGui

        app = _get_or_create_qapp()
        set_app_icon(app)
        app_version = _get_app_version()
        splash = None
        if not no_splash:
            try:
                logo_dir = os.path.join(ROOT_DIR, "images")
                safe_ver = "".join(
                    c
                    for c in app_version
                    if c.isalnum() or c in (".", "-", "_")
                )
                names = [
                    f"splash_v{safe_ver}.png",
                    "splash.png",
                    "splash.jpg",
                    "splash.jpeg",
                    "splash.bmp",
                ]
                for name in names:
                    path = os.path.join(logo_dir, name)
                    if os.path.isfile(path):
                        pix = QPixmap(path)
                        if not pix.isNull():
                            # Framing adjustment: limit the size to 80% of the screen
                            screen = app.primaryScreen()
                            if screen:
                                sgeo = screen.availableGeometry()
                                max_w, max_h = (
                                    int(sgeo.width() * 0.5),
                                    int(sgeo.height() * 0.5),
                                )
                                if pix.width() > max_w or pix.height() > max_h:
                                    pix = pix.scaled(
                                        max_w,
                                        max_h,
                                        Qt.KeepAspectRatio,
                                        Qt.SmoothTransformation,
                                    )

                            splash = QSplashScreen(
                                pix, Qt.WindowStaysOnTopHint
                            )

                            # Explicit centering
                            if screen:
                                sgeo = screen.availableGeometry()
                                splash.move(
                                    sgeo.x()
                                    + (sgeo.width() - pix.width()) // 2,
                                    sgeo.y()
                                    + (sgeo.height() - pix.height()) // 2,
                                )

                            splash.show()
                            app.processEvents()
                        break
            except Exception:
                splash = None

        if splash is not None:
            delay_ms = 4000
            try:
                delay_ms = int(
                    os.environ.get("PYCOMPILER_SPLASH_DELAY_MS", "4000")
                )
            except Exception:
                delay_ms = 4000

            def _launch_main():
                try:
                    if classic_gui:
                        os.environ["PYCOMPILER_UI_VARIANT"] = "classic"
                    elif ide_gui:
                        os.environ["PYCOMPILER_UI_VARIANT"] = "ide2"
                    window = PyCompilerArkGui()
                    set_window_icon(window)
                    window.show()
                    _apply_small_screen_compaction(app, window)
                    try:
                        splash.finish(window)
                    except Exception:
                        pass
                except Exception:
                    handle_fatal(sys.exc_info())

            QTimer.singleShot(max(0, delay_ms), _launch_main)
        else:
            if classic_gui:
                os.environ["PYCOMPILER_UI_VARIANT"] = "classic"
            elif ide_gui:
                os.environ["PYCOMPILER_UI_VARIANT"] = "ide2"
            window = PyCompilerArkGui()
            set_window_icon(window)
            window.show()
            _apply_small_screen_compaction(app, window)

        return app.exec()
    except Exception as exc:
        error(
            (
                f"Échec du lancement de l'application principale : {exc}",
                f"Failed to launch main application: {exc}",
            )
        )
        return 1
