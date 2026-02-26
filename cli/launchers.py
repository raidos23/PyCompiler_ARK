# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from .icons import set_app_icon, set_window_icon
from .output import error, warn
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
                lays = window.ui.findChildren(QLayout) if hasattr(window, "ui") else []
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


def launch_bcasl_standalone(workspace_dir: Optional[str] = None) -> int:
    try:
        from OnlyMod.BcaslOnlyMod import BcaslStandaloneGui

        if workspace_dir:
            try:
                workspace_dir = str(Path(workspace_dir).expanduser())
            except Exception:
                pass

        app = _get_or_create_qapp()
        app.setApplicationName("PyCompiler ARK BCASL")
        app.setOrganizationName("raidos23")
        set_app_icon(app)
        window = BcaslStandaloneGui(workspace_dir=workspace_dir)
        set_window_icon(window)
        window.show()
        return app.exec()
    except ImportError as exc:
        error(f"Failed to import BCASL standalone module: {exc}")
        warn("Make sure OnlyMod.BcaslOnlyMod is properly installed.")
        return 1
    except Exception as exc:
        error(f"Failed to launch BCASL standalone: {exc}")
        return 1


def launch_engines_only_standalone(workspace_dir: Optional[str] = None) -> int:
    try:
        from OnlyMod.EngineOnlyMod.gui import EnginesStandaloneGui

        if workspace_dir:
            try:
                workspace_dir = str(Path(workspace_dir).expanduser())
            except Exception:
                pass

        app = _get_or_create_qapp()
        app.setApplicationName("PyCompiler ARK Engines")
        app.setOrganizationName("raidos23")
        set_app_icon(app)
        window = EnginesStandaloneGui(workspace_dir=workspace_dir)
        set_window_icon(window)

        window.show()
        return app.exec()
    except ImportError as exc:
        error(f"Failed to import Engines standalone module: {exc}")
        warn("Make sure OnlyMod.EngineOnlyMod is properly installed.")
        return 1
    except Exception as exc:
        error(f"Failed to launch Engines standalone: {exc}")
        return 1


def launch_main_application(no_splash: bool = False, ide_gui: bool = False) -> int:
    try:
        from Core import PyCompilerArkGui
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QColor, QPixmap
        from PySide6.QtWidgets import QSplashScreen

        app = _get_or_create_qapp()
        set_app_icon(app)
        app_version = _get_app_version()

        splash = None
        if not no_splash:
            try:
                logo_dir = os.path.join(ROOT_DIR, "images")
                safe_ver = "".join(
                    c for c in app_version if c.isalnum() or c in (".", "-", "_")
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
                            try:
                                screen = app.primaryScreen()
                                geo = (
                                    screen.availableGeometry()
                                    if screen is not None
                                    else None
                                )
                                max_side = 720
                                if geo is not None:
                                    max_side = int(min(geo.width(), geo.height()) * 0.5)
                                    max_side = max(240, min(max_side, 720))
                                if pix.width() > max_side or pix.height() > max_side:
                                    pix = pix.scaled(
                                        max_side,
                                        max_side,
                                        Qt.AspectRatioMode.KeepAspectRatio,
                                        Qt.TransformationMode.SmoothTransformation,
                                    )
                            except Exception:
                                pass
                            splash = QSplashScreen(pix)
                            splash.show()
                            try:
                                if screen is not None:
                                    sg = splash.frameGeometry()
                                    center = (
                                        geo.center()
                                        if geo is not None
                                        else screen.geometry().center()
                                    )
                                    splash.move(
                                        center.x() - sg.width() // 2,
                                        center.y() - sg.height() // 2,
                                    )
                            except Exception:
                                pass
                            app.processEvents()
                            try:
                                align = Qt.AlignHCenter | Qt.AlignBottom
                                col = QColor(255, 255, 255)
                                splash.showMessage(
                                    "Initialisation… / Initializing…", align, col
                                )
                                app.processEvents()
                                QTimer.singleShot(
                                    700,
                                    lambda: splash.showMessage(
                                        "Chargement du thème… / Loading theme…",
                                        align,
                                        col,
                                    ),
                                )
                                QTimer.singleShot(
                                    1400,
                                    lambda: splash.showMessage(
                                        "Découverte des moteurs… / Discovering engines…",
                                        align,
                                        col,
                                    ),
                                )
                                QTimer.singleShot(
                                    2300,
                                    lambda: splash.showMessage(
                                        "Préparation de l'interface… / Preparing UI…",
                                        align,
                                        col,
                                    ),
                                )
                            except Exception:
                                pass
                        break
            except Exception:
                splash = None

        if splash is not None:
            delay_ms = 4000
            try:
                delay_ms = int(os.environ.get("PYCOMPILER_SPLASH_DELAY_MS", "4000"))
            except Exception:
                delay_ms = 4000

            def _launch_main():
                try:
                    if ide_gui:
                        os.environ["PYCOMPILER_UI_VARIANT"] = "ide2"
                    else:
                        os.environ.pop("PYCOMPILER_UI_VARIANT", None)
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
            if ide_gui:
                os.environ["PYCOMPILER_UI_VARIANT"] = "ide2"
            else:
                os.environ.pop("PYCOMPILER_UI_VARIANT", None)
            window = PyCompilerArkGui()
            set_window_icon(window)
            window.show()
            _apply_small_screen_compaction(app, window)

        rc = app.exec()
        return int(rc) if isinstance(rc, int) else 0
    except Exception:
        handle_fatal(sys.exc_info())
        return 1
