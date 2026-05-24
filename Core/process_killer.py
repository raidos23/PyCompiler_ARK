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
Process Killer Module - Robust Implementation

Provides utilities to stop compilation processes and their child processes
reliably across supported platforms, using psutil when available for
maximum reliability and process group killing on Unix.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    import psutil
except ImportError:
    psutil = None

_logger = logging.getLogger("process_killer")

# Platform detection
_IS_WINDOWS = sys.platform == "win32"

@dataclass
class ProcessInfo:
    """Information about a process."""
    pid: int
    name: str
    command: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    children: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary containing process information."""
        return {
            "pid": self.pid,
            "name": self.name,
            "command": self.command,
            "children": self.children,
            "start_time": self.start_time.isoformat(),
        }


class ProcessKiller:
    """
    Helper class to terminate compilation processes safely and powerfully.
    """

    def __init__(self, timeout: float = 5.0):
        """
        Initialize the process killer.

        Args:
          timeout: Maximum time to wait for graceful termination before forcing.
        """
        self.timeout = timeout

    def kill_process_tree(self, pid: int, include_parent: bool = True) -> bool:
        """
        Kill a process and all its descendants.
        Uses psutil if available, otherwise falls back to platform-specific methods.
        """
        if pid <= 0:
            return False

        _logger.info("Requesting kill for process tree starting at PID %d", pid)

        if psutil:
            return self._kill_with_psutil(pid, include_parent)
        
        if _IS_WINDOWS:
            return self._kill_with_taskkill(pid, include_parent)
        
        return self._kill_with_signals(pid, include_parent)

    def _kill_with_psutil(self, pid: int, include_parent: bool) -> bool:
        try:
            parent = psutil.Process(pid)
            # Use a set to avoid duplicates and handle circular dependencies if any
            all_procs = set(parent.children(recursive=True))
            if include_parent:
                all_procs.add(parent)
            
            # Sort by depth if possible, or just kill children first
            procs = sorted(list(all_procs), key=lambda p: len(p.parents()), reverse=True)
            
            # Phase 1: SIGTERM / Terminate
            for p in procs:
                try:
                    if p.is_running():
                        p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Wait for they to exit
            gone, alive = psutil.wait_procs(procs, timeout=self.timeout / 2)

            # Phase 2: Force kill remaining (SIGKILL)
            for p in alive:
                try:
                    if p.is_running():
                        _logger.warning("Forcing kill on PID %d (%s)", p.pid, p.name())
                        p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Final wait to reap zombies
            if alive:
                psutil.wait_procs(alive, timeout=2.0)
                
            return not any(p.is_running() for p in procs)
        except psutil.NoSuchProcess:
            return True # Already gone
        except Exception as e:
            _logger.error("Error killing process tree with psutil: %s", e)
            return False

    def _kill_with_taskkill(self, pid: int, include_parent: bool) -> bool:
        """Windows fallback using taskkill /T /F."""
        try:
            # /T kills the tree, /F forces it
            cmd = ["taskkill", "/F", "/T", "/PID", str(pid)]
            subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
                timeout=self.timeout,
            )
            return True
        except Exception as e:
            _logger.error("Error killing process tree with taskkill: %s", e)
            return False

    def _kill_with_signals(self, pid: int, include_parent: bool) -> bool:
        """Unix fallback using signals and process groups."""
        try:
            # Try to get the process group ID
            pgid = -1
            try:
                pgid = os.getpgid(pid)
            except Exception:
                pass

            if pgid > 1: # Avoid killing system-wide groups
                try:
                    # Terminate the whole group
                    os.killpg(pgid, signal.SIGTERM)
                    # Wait a bit
                    for _ in range(int(self.timeout * 2)):
                        if not self._is_alive(pid):
                            break
                        time.sleep(0.5)
                    
                    if self._is_alive(pid):
                        _logger.warning("Forcing kill on process group %d", pgid)
                        os.killpg(pgid, signal.SIGKILL)
                    return True
                except Exception as e:
                    _logger.debug("Group kill failed, falling back to PID: %s", e)

            # Fallback to killing only the pid and trying to find children via /proc
            if not _IS_WINDOWS:
                self._kill_unix_children_fallback(pid)

            if include_parent:
                try:
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(self.timeout / 2)
                    if self._is_alive(pid):
                        os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            return True
        except Exception as e:
            _logger.error("Error killing process with signals: %s", e)
            return False

    def _kill_unix_children_fallback(self, ppid: int) -> None:
        """Fallback to kill children on Unix without psutil or pgid."""
        try:
            # Try using pgrep to find children
            result = subprocess.run(
                ["pgrep", "-P", str(ppid)],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    child_pid = int(line.strip())
                    self._kill_unix_children_fallback(child_pid)
                    try:
                        os.kill(child_pid, signal.SIGKILL)
                    except Exception:
                        pass
        except Exception:
            pass

    def kill_by_name(self, name: str, ignore_case: bool = True) -> int:
        """
        Kill all processes matching the given name.
        Returns the number of processes killed.
        """
        killed_count = 0
        if psutil:
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name']
                    match = proc_name.lower() == name.lower() if ignore_case else proc_name == name
                    if match:
                        proc.kill()
                        killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        else:
            if _IS_WINDOWS:
                try:
                    # Case insensitive by default on Windows
                    cmd = ["taskkill", "/F", "/IM", name]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    killed_count = 1 
                except Exception:
                    pass
            else:
                try:
                    subprocess.run(["pkill", "-f", name], check=False)
                    killed_count = 1
                except Exception:
                    pass
        return killed_count

    def _is_alive(self, pid: int) -> bool:
        if pid <= 0:
            return False
        if psutil:
            try:
                p = psutil.Process(pid)
                return p.is_running() and p.status() != psutil.STATUS_ZOMBIE
            except psutil.NoSuchProcess:
                return False
        
        try:
            if _IS_WINDOWS:
                # Tasklist can be slow, but it's reliable for existence
                res = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return str(pid) in res.stdout
            else:
                # On Unix, kill(pid, 0) checks if process exists
                os.kill(pid, 0)
                return True
        except (ProcessLookupError, PermissionError):
            return False
        except Exception:
            return False


def kill_process_tree(pid: int, include_parent: bool = True) -> bool:
    """Utility function for quick process tree termination."""
    killer = ProcessKiller()
    return killer.kill_process_tree(pid, include_parent)


def kill_process(pid: int) -> bool:
    """Kill a single process."""
    try:
        if psutil:
            p = psutil.Process(pid)
            p.terminate()
            try:
                p.wait(timeout=1.0)
            except psutil.TimeoutExpired:
                p.kill()
            return True
        
        if _IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False)
        else:
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.5)
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        return True
    except Exception:
        return False

def kill_by_name(name: str) -> int:
    """Kill processes by name."""
    killer = ProcessKiller()
    return killer.kill_by_name(name)

def get_process_info(pid: int) -> Optional[ProcessInfo]:
    """Return information for one process."""
    if psutil:
        try:
            p = psutil.Process(pid)
            return ProcessInfo(
                pid=pid,
                name=p.name(),
                command=" ".join(p.cmdline()),
                start_time=datetime.fromtimestamp(p.create_time()),
                children=[c.pid for c in p.children()]
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
    
    # Fallback
    try:
        if _IS_WINDOWS:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            lines = result.stdout.strip().splitlines()
            if len(lines) > 1:
                parts = lines[1].split(",")
                if len(parts) >= 2:
                    name = parts[0].strip('"')
                    return ProcessInfo(pid, name, "")
        else:
            # Simple proc reading for Linux
            cmdline_path = Path(f"/proc/{pid}/cmdline")
            if cmdline_path.exists():
                cmdline = cmdline_path.read_text().replace("\x00", " ")
                comm_path = Path(f"/proc/{pid}/comm")
                comm = comm_path.read_text().strip() if comm_path.exists() else ""
                return ProcessInfo(pid, comm, cmdline)
    except Exception:
        pass
    return None
