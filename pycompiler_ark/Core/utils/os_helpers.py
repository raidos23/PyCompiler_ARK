from __future__ import annotations

import locale
import os
import platform
import re
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional, Union

Pathish = Union[str, Path]

# -------------------------------
# OS helpers
# -------------------------------


def open_path(path: Pathish) -> bool:
    """Open a file or directory with the OS default handler. Returns True on attempt."""
    try:
        p = str(path)
        sysname = platform.system()
        if sysname == "Windows":
            os.startfile(p)  # type: ignore[attr-defined]
        elif sysname == "Linux":
            import subprocess

            subprocess.run(["xdg-open", p])
        else:
            import subprocess

            subprocess.run(["open", p])
        return True
    except Exception:
        return False
