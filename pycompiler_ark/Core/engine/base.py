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

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

from ...Ui import output

if TYPE_CHECKING:
    from .build_context import BuildContext


@dataclass(frozen=True)
class EngineMeta:
    """Métadonnées d'un moteur de compilation."""

    id: str
    name: str
    version: str
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"
    description: str = ""
    author: str = ""

    def __post_init__(self) -> None:
        nid = str(self.id or "").strip()
        nname = str(self.name or "").strip()
        nversion = str(self.version or "").strip()
        if not nid:
            raise ValueError("EngineMeta invalide: 'id' requis")
        if not nname:
            raise ValueError("EngineMeta invalide: 'name' requis")
        if not nversion:
            raise ValueError("EngineMeta invalide: 'version' requis")
        object.__setattr__(self, "id", nid)
        object.__setattr__(self, "name", nname)
        object.__setattr__(self, "version", nversion)
        object.__setattr__(
            self,
            "required_core_version",
            str(self.required_core_version or "1.0.0").strip() or "1.0.0",
        )
        object.__setattr__(
            self,
            "required_sdk_version",
            str(self.required_sdk_version or "1.0.0").strip() or "1.0.0",
        )
        object.__setattr__(
            self, "description", str(self.description or "").strip()
        )
        object.__setattr__(self, "author", str(self.author or "").strip())


def resolve_engine_meta(engine_or_cls: object) -> EngineMeta:
    """Resolve engine metadata from a meta object or legacy class attributes."""

    meta = getattr(engine_or_cls, "meta", None)
    if isinstance(meta, EngineMeta):
        return meta

    if isinstance(meta, dict):
        return EngineMeta(
            id=str(
                meta.get("id") or getattr(engine_or_cls, "id", "") or "base"
            ),
            name=str(
                meta.get("name")
                or getattr(engine_or_cls, "name", "")
                or "BaseEngine"
            ),
            version=str(
                meta.get("version")
                or getattr(engine_or_cls, "version", "")
                or "1.0.0"
            ),
            required_core_version=str(
                meta.get("required_core_version")
                or getattr(engine_or_cls, "required_core_version", "1.0.0")
            ),
            required_sdk_version=str(
                meta.get("required_sdk_version")
                or getattr(engine_or_cls, "required_sdk_version", "1.0.0")
            ),
            description=str(meta.get("description") or ""),
            author=str(meta.get("author") or ""),
        )

    return EngineMeta(
        id=str(getattr(engine_or_cls, "id", "") or "base"),
        name=str(getattr(engine_or_cls, "name", "") or "BaseEngine"),
        version=str(getattr(engine_or_cls, "version", "") or "1.0.0"),
        required_core_version=str(
            getattr(engine_or_cls, "required_core_version", "1.0.0")
        ),
        required_sdk_version=str(
            getattr(engine_or_cls, "required_sdk_version", "1.0.0")
        ),
        description=str(getattr(engine_or_cls, "description", "") or ""),
        author=str(getattr(engine_or_cls, "author", "") or ""),
    )


class CompilerEngine:
    """
    Base class for a pluggable compilation engine.

    An engine is responsible for:
    - building the command (program, args) for a given file and GUI state
    - performing preflight checks (venv tools, system dependencies)
    - post-success hooks (e.g., open output folder)

    Engines must be stateless or keep minimal transient state; GUI state is
    provided via the `gui` object.
    """

    meta: EngineMeta = EngineMeta(
        id="base", name="BaseEngine", version="1.0.0"
    )
    id: str = "base"
    name: str = "BaseEngine"
    version: str = "1.0.0"
    required_core_version: str = "1.0.0"
    required_sdk_version: str = "1.0.0"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            resolved = resolve_engine_meta(cls)
            cls.meta = resolved
            cls.id = resolved.id
            cls.name = resolved.name
            cls.version = resolved.version
            cls.required_core_version = resolved.required_core_version
            cls.required_sdk_version = resolved.required_sdk_version
            if resolved.description and not getattr(cls, "description", None):
                cls.description = resolved.description
            if resolved.author and not getattr(cls, "author", None):
                cls.author = resolved.author
        except Exception:
            pass

    def preflight(self, gui, file: str) -> bool:
        """Perform preflight checks and setup. Return True if OK, False to abort."""
        return True

    def build_command(self, context: "BuildContext") -> list[str]:
        """
        Return the full command list for a normalized build context.

        This is the primary entry point for command generation. Engines should
        use the provided `context` for project settings and `self._config_overrides`
        for engine-specific options.
        """
        raise NotImplementedError

    def program_and_args(
        self, context: "BuildContext"
    ) -> Optional[tuple[str, list[str]]]:
        """
        Resolve the program and arguments for a normalized build context.
        Default implementation splits `build_command`.
        """
        cmd = self.build_command(context)
        if not cmd:
            return None
        return cmd[0], cmd[1:]

    def on_success(self, gui, file: str) -> None:
        """Hook called when a build is successful."""
        pass

    def open_output_dir(self, output_dir: str) -> None:
        """Open the output directory with the default system handler."""
        if not output_dir:
            return

        import os

        from ..utils import open_path

        path = output_dir
        if not os.path.isabs(path):
            # Try to find workspace_dir to resolve relative path
            ws = getattr(self, "workspace_dir", None)
            if not ws and hasattr(self, "_gui"):
                ws = getattr(self._gui, "workspace_dir", None)

            if ws:
                path = os.path.join(ws, path)
            else:
                path = os.path.abspath(path)

        if os.path.isdir(path):
            # Log attempt to open
            gui = getattr(self, "_gui", None)
            if gui:
                output.info(
                    f"Ouverture du dossier de sortie : {path}", gui=gui
                )
            open_path(path)

    def create_tab(self, gui):
        """
        Optionally create and return a QWidget tab and its label for the GUI.
        Return value: (widget, label: str) or None if the engine does not add a tab.
        The engine is responsible for creating its own controls and wiring signals.
        """
        return None

    def get_config(self, gui) -> dict:
        """Return a JSON-serializable dict of current engine UI options."""
        return {}

    def set_config(self, gui, cfg: dict) -> None:
        """Apply a config dict to engine UI widgets."""
        pass

    def config_policy(self, gui) -> dict:
        """
        Define how the engine wants its config to be handled.

        Return a dict with any of:
        - read (bool): allow Core to read/apply config
        - write (bool): allow Core to persist config
        - ui_edit (bool): allow UI-driven save of config
        """
        return {"read": True, "write": True, "ui_edit": True}

    def load_config(self, gui, workspace_dir: str) -> Optional[dict]:
        """
        Optional custom config loader for special engines.
        Return a dict (payload or options). Return None to use default storage.
        """
        return None

    def save_config(
        self, gui, workspace_dir: str, options: dict
    ) -> Optional[bool]:
        """
        Optional custom config saver for special engines.
        Return True/False to override default save, or None to use default storage.
        """
        return None

    def environment(self) -> Optional[dict[str, str]]:
        """
        Optionally return a mapping of environment variables to inject for the engine process.
        Values here will override the current process environment. Return None for no changes.
        """
        return None

    @property
    def required_tools(self) -> dict[str, list[str]]:
        """
        Return dict of required tools with installation modes.
        Keys: 'python' for pip-installable tools, 'system' for system packages.
        Used by VenvManager for Python tools and system installer for system tools.
        Example: {'python': ['<tool_name>'], 'system': ['<system_package>']}
        """
        return {"python": [], "system": []}

    def get_log_prefix(self, file_basename: str) -> str:
        """
        Return a log prefix string for the engine's compilation messages.
        Default includes engine name and version.
        """
        return f"{self.name} ({self.version})"
