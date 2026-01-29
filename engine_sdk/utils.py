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

"""
engine_sdk.utils — Robust helpers for engine authors

These helpers improve safety and reliability when building engine commands,
validating paths, and preparing environments.

Typical usage (inside an engine plugin):

    from engine_sdk.utils import (
        redact_secrets,
        is_within_workspace,
        safe_join,
        validate_args,
        build_env,
        clamp_text,
        normalized_program_and_args,
    )

    class MyEngine(CompilerEngine):
        id = "my_engine"; name = "My Engine"
        def program_and_args(self, gui, file: str):
            ws = gui.workspace_dir
            program = safe_join(ws, "venv", "bin", "myprog")
            args = validate_args(["--build", file])
            prog, args = normalized_program_and_args(program, args)
            return prog, args
"""

import os
import platform
import re
import shutil
import subprocess
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional, Union

try:
    from PySide6.QtCore import QProcess  # type: ignore
except Exception:  # pragma: no cover - optional at import time
    QProcess = None  # type: ignore

Pathish = Union[str, Path]

# -------------------------------
# Secret redaction for logs
# -------------------------------
_REDACT_PATTERNS = [
    re.compile(r"(password\s*[:=]\s*)([^\s]+)", re.IGNORECASE),
    re.compile(r"(authorization\s*[:]\s*bearer\s+)([A-Za-z0-9\-_.]+)", re.IGNORECASE),
    re.compile(r"(token\s*[:=]\s*)([A-Za-z0-9\-_.]{12,})", re.IGNORECASE),
]


def redact_secrets(text: str) -> str:
    """Return text with obvious secrets masked to avoid log leakage."""
    if not text:
        return text
    redacted = str(text)
    try:
        for pat in _REDACT_PATTERNS:
            redacted = pat.sub(lambda m: m.group(1) + "<redacted>", redacted)
    except Exception:
        pass
    return redacted


# -------------------------------
# Workspace path safety
# -------------------------------


def is_within_workspace(workspace: Pathish, p: Pathish) -> bool:
    """True if path p resolves within workspace."""
    try:
        ws = Path(workspace).resolve()
        rp = Path(p).resolve()
        _ = rp.relative_to(ws)
        return True
    except Exception:
        return False


def safe_join(workspace: Pathish, *parts: Pathish) -> Path:
    """Join parts under workspace and ensure the resolved path stays within it.
    Raises ValueError if the result escapes the workspace.
    """
    base = Path(workspace)
    p = base
    for part in parts:
        p = p / Path(part)
    rp = p.resolve()
    if not is_within_workspace(base, rp):
        raise ValueError(f"Path escapes workspace: {rp}")
    return rp


# -------------------------------
# Output/log safety
# -------------------------------


def clamp_text(text: str, *, max_len: int = 10000) -> str:
    """Clamp long text to max_len characters (suffix with …)."""
    if text is None:
        return ""
    s = str(text)
    return s if len(s) <= max_len else (s[: max_len - 1] + "…")


# -------------------------------
# i18n & logging helpers
# -------------------------------


def tr(gui: Any, fr: str, en: str) -> str:
    """Robust translator wrapper using the host GUI translator when available."""
    try:
        fn = getattr(gui, "tr", None)
        if callable(fn):
            return fn(fr, en)
    except Exception:
        pass
    # Fallback: prefer English when current_language is English
    try:
        cur = getattr(gui, "current_language", None)
        if isinstance(cur, str) and cur.lower().startswith("en"):
            return en
    except Exception:
        pass
    return fr


essential_log_max_len = 10000


def safe_log(gui: Any, text: str, *, redact: bool = True, clamp: bool = True) -> None:
    """Append text to GUI log safely (or print), with optional redaction and clamping."""
    try:
        msg = str(text)
        if redact:
            msg = redact_secrets(msg)
        if clamp:
            msg = clamp_text(msg, max_len=essential_log_max_len)
        if hasattr(gui, "log") and getattr(gui, "log") is not None:
            try:
                gui.log.append(msg)
                return
            except Exception:
                pass
        print(msg)
    except Exception:
        try:
            print(text)
        except Exception:
            pass


# -------------------------------
# Executable resolution helper
# -------------------------------


def resolve_executable(
    program: Pathish, base_dir: Optional[Pathish] = None, *, prefer_path: bool = True
) -> str:
    """Resolve an executable path according to a clear, cross-platform policy.

    - Absolute program path: returned as-is.
    - Bare command (no path separator) and prefer_path=True: use shutil.which to resolve real path if available;
      otherwise return the command name (so the OS can resolve it via PATH at runtime).
    - Otherwise: join relative to base_dir (or CWD) and return an absolute path.
    """
    prog = str(program)
    try:
        # Absolute path -> as is
        if os.path.isabs(prog):
            return prog
        bare = (os.path.sep not in prog) and (not prog.startswith("."))
        if prefer_path and bare:
            try:
                found = shutil.which(prog)
                if found:
                    return found
            except Exception:
                pass
            # Keep bare command to allow OS PATH resolution later
            return prog
        # Else, resolve relative to base_dir (or CWD)
        base = str(base_dir) if base_dir is not None else os.getcwd()
        return os.path.abspath(os.path.join(base, prog))
    except Exception:
        # Fallback: return the original string
        return prog


# Fallback: host-level resolver override if available; else use SDK's resolve_executable
try:  # pragma: no cover
    from EngineLoader.external import resolve_executable_path as resolve_executable_path  # type: ignore
except Exception:  # pragma: no cover

    def resolve_executable_path(
        program: Pathish,
        base_dir: Optional[Pathish] = None,
        *,
        prefer_path: bool = True,
    ) -> str:  # type: ignore
        return resolve_executable(program, base_dir, prefer_path=prefer_path)


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


def open_dir_candidates(candidates: Sequence[Pathish]) -> Optional[str]:
    """Open the first existing directory from candidates, return the opened path or None."""
    for c in candidates:
        try:
            d = str(c)
            if d and os.path.isdir(d):
                if open_path(d):
                    return d
        except Exception:
            continue
    return None


# ---------------------------------------------
# Universal output directory discovery and open
# ---------------------------------------------
from collections.abc import Sequence as _Seq


def discover_output_candidates(
    gui: Any,
    engine_id: Optional[str] = None,
    source_file: Optional[Pathish] = None,
    artifacts: Optional[_Seq[Pathish]] = None,
) -> list[str]:
    """Discover plausible output directory candidates in a plug-and-play manner.

    Strategy (generic; no engine-specific dependencies):
      1) GUI fields likely representing output directories (heuristic: names containing 'output'/'dist' and 'dir'/'path').
      2) Directories of known artifacts (if provided).
      3) Conventional fallbacks under the workspace (dist/, build/, <base>.dist).

    Returns an ordered list of unique path strings; non-existing paths are allowed (will be filtered by opener).
    """
    cands: list[str] = []

    def _add(p: Optional[Pathish]) -> None:
        try:
            if not p:
                return
            s = str(p).strip()
            if s and s not in cands:
                cands.append(s)
        except Exception:
            pass

    try:
        ws = getattr(gui, "workspace_dir", None) or os.getcwd()
    except Exception:
        ws = os.getcwd()

    # 1) GUI fields (global common fields and heuristic scan)
    try:
        out = getattr(gui, "output_dir_input", None)
        if out and hasattr(out, "text") and callable(out.text):
            _add(out.text())
    except Exception:
        pass

    # Heuristic scan of GUI attributes for line edits that look like output fields
    try:
        for nm in dir(gui):
            try:
                w = getattr(gui, nm)
            except Exception:
                continue
            if not w or not hasattr(w, "text") or not callable(w.text):
                continue
            label_parts: list[str] = [nm]
            try:
                on = getattr(w, "objectName", None)
                if callable(on):
                    label_parts.append(str(on()))
                elif isinstance(on, str):
                    label_parts.append(on)
            except Exception:
                pass
            try:
                an = getattr(w, "accessibleName", None)
                if callable(an):
                    label_parts.append(str(an()))
                elif isinstance(an, str):
                    label_parts.append(an)
            except Exception:
                pass
            lab = " ".join([str(x) for x in label_parts if x]).lower()
            if any(tok in lab for tok in ("output", "dist")) and any(
                tok in lab for tok in ("dir", "path")
            ):
                try:
                    _add(w.text())
                except Exception:
                    pass
    except Exception:
        pass

    # 2) Artifacts parents (most recent first)
    try:
        arts = artifacts
        if arts is None:
            arts = getattr(gui, "_last_artifacts", None)
        parents: list[tuple[float, str]] = []
        if arts:
            for a in arts:
                try:
                    ap = str(a)
                    d = os.path.dirname(ap)
                    mt = os.path.getmtime(ap) if os.path.exists(ap) else 0.0
                    parents.append((mt, d))
                except Exception:
                    continue
            for _mt, d in sorted(parents, key=lambda t: t[0], reverse=True):
                _add(d)
    except Exception:
        pass

    # 3) Conventional fallbacks
    try:
        _add(os.path.join(ws, "dist"))
        _add(os.path.join(ws, "build"))
        if source_file:
            try:
                base = os.path.splitext(os.path.basename(str(source_file)))[0]
                _add(os.path.join(ws, f"{base}.dist"))
            except Exception:
                pass
    except Exception:
        pass

    return cands


def open_output_directory(
    gui: Any,
    engine_id: Optional[str] = None,
    source_file: Optional[Pathish] = None,
    artifacts: Optional[_Seq[Pathish]] = None,
) -> Optional[str]:
    """Open a plausible output directory for the last successful build using generic discovery.

    Does not call engine hooks; respects plug-and-play by avoiding engine-specific code paths.
    Returns the opened directory path or None if none found.
    """
    try:
        cands = discover_output_candidates(
            gui, engine_id=engine_id, source_file=source_file, artifacts=artifacts
        )
        return open_dir_candidates(cands) if cands else None
    except Exception:
        return None


# Filesystem safety helpers


def ensure_dir(path: Pathish) -> Path:
    """Ensure directory exists and return its Path."""
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def atomic_write_text(path: Pathish, text: str, *, encoding: str = "utf-8") -> bool:
    """Write text atomically with a temp file and rename. Returns True on success."""
    target = Path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    import tempfile

    try:
        fd, tmp = tempfile.mkstemp(prefix=".sdk_", dir=str(target.parent))
        try:
            with open(fd, "w", encoding=encoding) as f:
                f.write(text)
            os.replace(tmp, str(target))
            try:
                os.chmod(str(target), 0o644)
            except Exception:
                pass
            return True
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
    except Exception:
        return False
