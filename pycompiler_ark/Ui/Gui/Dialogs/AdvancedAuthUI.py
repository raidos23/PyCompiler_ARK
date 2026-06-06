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
AdvancedAuthUI — GUI layer for AdvancedAuth service.
"""

from pycompiler_ark.Ui.Gui.Dialogs.WorkspaceDialog import WorkspaceDialog


class AdvancedAuthUI:
    """GUI implementations for AdvancedAuth service operations."""

    @staticmethod
    def handle_workspace_change_request(gui, folder: str) -> bool:
        """
        Interactively confirm and apply a workspace change request.
        """
        try:
            if not WorkspaceDialog.confirm_workspace_change(gui, str(folder)):
                return False

            if hasattr(gui, "apply_workspace_selection"):
                return bool(gui.apply_workspace_selection(str(folder), source="plugin"))

            # Fallback if the GUI instance doesn't have the method directly
            return bool(
                WorkspaceDialog.apply_workspace_selection(
                    gui, str(folder), source="plugin"
                )
            )
        except Exception:
            return False
