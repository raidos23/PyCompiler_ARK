#!/usr/bin/env python3
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

"""
PyCompiler ARK — Cross-platform hardened bootstrap with Intelligent CLI Entry Point

Usage:
    python -m pycompiler_ark                    # Launch main application
    python -m pycompiler_ark --help             # Show help
    python -m pycompiler_ark --version          # Show version
    python -m pycompiler_ark --cli              # Open dedicated interactive CLI
    python -m pycompiler_ark --ide-gui          # Launch IDE-like main GUI
    python -m pycompiler_ark --verbose          # Enable verbose logging
    python -m pycompiler_ark --no-splash        # Disable splash screen
    python -m pycompiler_ark bcasl              # Launch BCASL standalone
    python -m pycompiler_ark bcasl /path/to/ws  # Launch BCASL with workspace
    python -m pycompiler_ark engines            # Launch Engines standalone GUI
    python -m pycompiler_ark engines /path/to/ws  # Launch Engines with workspace
    python -m pycompiler_ark prog-engine nuitka /path/to/ws  # Launch GUI focused on one engine
    python -m pycompiler_ark engines --dry-run  # List available engines
    python -m pycompiler_ark unload             # Unload all engines
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

_ONLYMOD_LOG_HISTORY: list[str] = []


def onlymod_log(message: str, gui: Optional[object] = None) -> str:
    """Centralized logging for OnlyMod GUIs."""
    try:
        if not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
    except Exception:
        pass

    logger = logging.getLogger(__name__)

    try:
        ts = datetime.now().strftime("%H:%M:%S")
    except Exception:
        ts = ""

    def _strip_emoji_prefix(s: str) -> str:
        try:
            val = str(s)
        except Exception:
            return s
        for emo in (
            "✅",
            "⚠️",
            "❌",
            "ℹ️",
            "❗",
            "⏩",
            "📝",
            "📋",
            "🔍",
            "🔧",
            "🔨",
            "➡️",
            "📦",
            "🗑️",
            "🧩",
            "🔌",
            "⏹️",
            "⏱️",
        ):
            if val.startswith(emo):
                val = val[len(emo) :]
                break
        return val.lstrip()

    clean_message = _strip_emoji_prefix(message)
    line = f"[{ts}] {clean_message}" if ts else str(clean_message)

    try:
        _ONLYMOD_LOG_HISTORY.append(line)
    except Exception:
        pass

    try:
        logger.info("[OnlyMod] %s", clean_message)
    except Exception:
        pass

    if gui is not None:
        try:
            log_text = getattr(gui, "log_text", None)
            is_valid = getattr(gui, "_is_valid", None)
            if callable(is_valid) and not is_valid(log_text):
                return line
            if log_text is not None:
                log_text.append(line)
                scrollbar = log_text.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
        except Exception:
            pass

    return line


if __name__ == "__main__":
    from cli.entrypoint import main

    raise SystemExit(main())
