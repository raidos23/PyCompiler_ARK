# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

from __future__ import annotations

import logging
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)


class PathCompleter:
    """Intelligent path completion for workspaces."""

    @staticmethod
    def complete_paths(incomplete: str, dir_only: bool = True) -> List[str]:
        try:
            if not incomplete:
                return [".", str(Path.home())]

            path = Path(incomplete).expanduser()

            if path.is_dir():
                base_path = path
                prefix = ""
            else:
                base_path = path.parent
                prefix = path.name

            if not base_path.exists():
                return []

            completions = []
            try:
                for item in sorted(base_path.iterdir()):
                    if dir_only and not item.is_dir():
                        continue

                    if item.name.startswith(prefix):
                        if item.is_dir():
                            completions.append(str(item) + "/")
                        else:
                            completions.append(str(item))
            except PermissionError:
                pass

            return completions[:20]
        except Exception as exc:
            logger.debug("Error completing paths: %s", exc)
            return []
