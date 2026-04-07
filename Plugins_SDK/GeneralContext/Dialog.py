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

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Optional
import colorama
from rich.console import Console
from .i18n import translate

# Import des classes et fonctions de Core.dialogs
from Core.WidgetsCreator import (
    show_msgbox,
    sys_msgbox_for_installing,
    ProgressDialog,
    CompilationProcessDialog,
    InstallAuth,
    _redact_secrets,
    _invoke_in_main_thread,
)


class Dialog:
    """Dialog class for plugins - uses Core.dialogs classes for all UI operations."""

    def __init__(self):
        colorama.init()
        self.console = Console()
        self.plugin_id: Optional[str] = None

    def _resolve_plugin_id(self) -> str:
        """Resolve plugin id for i18n lookup.

        Priority:
        1) Explicit `self.plugin_id` when provided by caller/plugin.
        2) Infer from call stack path containing `.../Plugins/<plugin_dir>/...`.
        """
        if isinstance(self.plugin_id, str) and self.plugin_id.strip():
            return self.plugin_id.strip()
        try:
            for frame_info in inspect.stack()[2:]:
                filename = str(getattr(frame_info, "filename", "") or "")
                if not filename:
                    continue
                parts = Path(filename).parts
                if "Plugins" in parts:
                    idx = parts.index("Plugins")
                    if idx + 1 < len(parts):
                        return str(parts[idx + 1])
        except Exception:
            pass
        return ""

    def _tr_text(self, text: str) -> str:
        """Translate a potential i18n key while keeping literals intact."""
        raw = str(text or "")
        if not raw:
            return raw
        plugin_id = self._resolve_plugin_id()
        try:
            return translate(plugin_id, raw, raw)
        except Exception:
            return raw

    def show_msgbox(
        self, kind: str, title: str, text: str, *, default: Optional[str] = None
    ) -> Optional[bool]:
        """Show a message box using Core.dialogs.show_msgbox."""
        return show_msgbox(
            kind,
            self._tr_text(title),
            self._tr_text(text),
            default=default,
        )

    def msg_info(self, title: str, text: str) -> None:
        """Show an info message box."""
        show_msgbox("info", self._tr_text(title), self._tr_text(text))

    def msg_warn(self, title: str, text: str) -> None:
        """Show a warning message box."""
        show_msgbox("warning", self._tr_text(title), self._tr_text(text))

    def msg_error(self, title: str, text: str) -> None:
        """Show an error message box."""
        show_msgbox("error", self._tr_text(title), self._tr_text(text))

    def msg_question(self, title: str, text: str, default_yes: bool = True) -> bool:
        """Show a question message box and return True if Yes, False otherwise."""
        return bool(
            show_msgbox(
                "question",
                self._tr_text(title),
                self._tr_text(text),
                default="Yes" if default_yes else "No",
            )
        )

    def log(self, message: str) -> None:
        """Log a message with optional redaction of secrets."""
        msg = (
            _redact_secrets(message) if getattr(self, "redact_logs", True) else message
        )
        if hasattr(self, "log_fn") and self.log_fn:
            try:
                self.log_fn(msg)
                return
            except Exception:
                pass
        print(msg)

    def log_info(self, message: str) -> None:
        """Log an info message."""
        self.console.print(f"[bold green][INFO][/bold green] {message}")

    def log_warn(self, message: str) -> None:
        """Log a warning message."""
        self.console.print(f"[bold yellow][WARN][/bold yellow] {message}")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        self.console.print(f"[bold red][ERROR][/bold red] {message}")

    def sys_msgbox_for_installing(
        self,
        subject: str,
        explanation: Optional[str] = None,
        title: str = "Installation requise",
    ) -> Optional[InstallAuth]:
        """Show a system installation authorization dialog using Core.dialogs."""
        return sys_msgbox_for_installing(subject, explanation=explanation, title=title)

    def progress(
        self, title: str, text: str = "", maximum: int = 0, cancelable: bool = False
    ) -> ProgressDialog:
        """Create and return a ProgressDialog from Core.dialogs.

        Uses Core.dialogs.ProgressDialog to ensure:
        - Theme inheritance from the application
        - Visual integration with the main application
        - Thread safety

        Args:
            title: Dialog title
            text: Initial dialog text
            maximum: Maximum value (0 = indeterminate)
            cancelable: If True, show a Cancel button

        Returns:
            ProgressDialog instance from Core.dialogs
        """
        return ProgressDialog(title=title, cancelable=cancelable)
