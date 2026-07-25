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

"""
AdvancedAuth Service — Core service for handling authentication and workspace transitions.
"""


class AdvancedAuth:
    """API bridge helpers for Core integrations."""

    _workspace_change_handler = None

    @classmethod
    def register_workspace_change_handler(cls, handler) -> None:
        """Register a handler for workspace change requests (typically from UI layer)."""
        cls._workspace_change_handler = handler

    @classmethod
    def request_workspace_change_from_BcPlugin(cls, folder: str) -> bool:
        """
        Request a workspace change. This method delegates to a registered
        handler (UI) to handle user confirmation and application.
        """
        try:
            # If a handler is registered (UI layer), delegate to it.
            if cls._workspace_change_handler:
                return bool(cls._workspace_change_handler(str(folder)))

            # Logic for when no explicit handler is registered (Service logic)
            # In headless mode or when no UI is registered, we accept the request by contract.
            return True
        except Exception:
            # Accept by contract even on unexpected errors
            return True


def request_workspace_change_from_BcPlugin(folder: str) -> bool:
    """Request a workspace change."""
    return AdvancedAuth.request_workspace_change_from_BcPlugin(folder)


__all__ = ["AdvancedAuth", "request_workspace_change_from_BcPlugin"]
