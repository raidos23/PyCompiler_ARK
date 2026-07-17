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

from typing import Any

CliMessage = str | tuple[str, str] | list[str]


def cli_text(message: CliMessage) -> str:
    """Resolve a CLI message according to active language (FR/EN)."""
    if isinstance(message, (tuple, list)) and len(message) >= 2:
        fr, en = str(message[0]), str(message[1])
        try:
            from pycompiler_ark.Ui.i18n import tr_fr_en

            return tr_fr_en(None, fr, en)
        except Exception:
            return en
    return str(message)


class CliSpecError(RuntimeError):
    """Raised when a spec-level CLI rule is violated."""

    def __init__(self, message: CliMessage):
        self.raw_message = message
        super().__init__(cli_text(message))


def cli_click_exception(message: CliMessage):
    """Build a ClickException with a localized message."""
    import click

    return click.ClickException(cli_text(message))
