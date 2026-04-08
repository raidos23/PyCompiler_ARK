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
Process Killer Module

Process termination and cleanup module for PyCompiler ARK.
Provides utilities to stop compilation processes and their child processes
reliably across supported platforms.

Provides:
- `ProcessKiller` class for process termination
- `kill_process()` utility function
- `kill_process_tree()` utility for parent + child termination
- `get_child_pids()` utility for child process discovery
"""

from __future__ import annotations

import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# Platform detection
_IS_WINDOWS = sys.platform == "win32"
_IS_LINUX = sys.platform.startswith("linux")
_IS_MACOS = sys.platform == "darwin"


class ProcessInfo:
    """Information about a process."""

    def __init__(self, pid: int, name: str, command: str):
        """
    Initialize process information.

    Args:
      pid: Process ID.
      name: Process name.
      command: Full command line.
    """
        self.pid = pid
        self.name = name
        self.command = command
        self.start_time = datetime.now()
        self.children: List[int] = []

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
  Helper class to terminate compilation processes safely.

  Supports:
  - Single process termination
  - Process tree termination (parent + children)
  - Multiple termination strengths (graceful, force, kill)
  - Zombie process cleanup
  """

    # Délais de terminaison en secondes
    TERMINATE_TIMEOUT = 5.0  # Temps pour terminate()
    KILL_TIMEOUT = 2.0  # Temps pour kill() après terminate

    def __init__(self, timeout: Optional[float] = None):
        """
    Initialize the process killer helper.

    Args:
      timeout: Optional global termination timeout.
    """
        self.timeout = timeout or (self.TERMINATE_TIMEOUT + self.KILL_TIMEOUT)

    def kill(
        self, pid: int, force: bool = False, recursive: bool = False
    ) -> Dict[str, Any]:
        """
    Kill one process.

    Args:
      pid: ID du process à tuer
      force: Utiliser kill() directement au lieu de terminate()
      recursive: Killr aussi les process enfants

    Returns:
      Dictionnaire avec le résultat
    """
        result = {
            "success": False,
            "pid": pid,
            "killed_children": [],
            "message": "",
            "duration": 0.0,
        }

        start_time = time.time()

        try:
            # Vérifier si le processus existe
            if not self._is_process_alive(pid):
                result["message"] = f"Process {pid} is not running"
                return result

            if recursive:
                # Tuer d'abord les enfants
                children = self.get_child_pids(pid)
                for child_pid in children:
                    child_result = self.kill(child_pid, force, False)
                    if child_result["success"]:
                        result["killed_children"].append(child_pid)

            # Tuer le processus principal
            if force:
                self._kill_signal(pid)
                result["success"] = True
                result["message"] = f"Process {pid} killed (forced)"
            else:
                self._terminate_signal(pid)
                # Attendre la terminaison
                if self._wait_for_termination(pid, self.TERMINATE_TIMEOUT):
                    result["success"] = True
                    result["message"] = f"Process {pid} terminated gracefully"
                else:
                    # Forcer la terminaison
                    self._kill_signal(pid)
                    result["success"] = True
                    result["message"] = f"Process {pid} killed after timeout"

        except ProcessLookupError:
            result["message"] = f"Process {pid} not found"
        except PermissionError:
            result["message"] = f"Permission denied to kill process {pid}"
        except Exception as e:
            result["message"] = f"Error killing process {pid}: {str(e)}"

        result["duration"] = time.time() - start_time
        return result

    def kill_process_tree(
        self, pid: int, include_parent: bool = True
    ) -> Dict[str, Any]:
        """
    Kill one process and all its children.

    Args:
      pid: ID du process parent
      include_parent: Inclure le process parent dans la terminaison

    Returns:
      Dictionnaire avec le résultat
    """
        result = {
            "success": False,
            "parent_pid": pid,
            "killed_pids": [],
            "message": "",
            "duration": 0.0,
        }

        start_time = time.time()

        try:
            # 收集所有进程ID
            all_pids = [pid] if include_parent else []
            all_pids.extend(self.get_child_pids(pid))

            # Tuer de bas en haut (les enfants d'abord)
            for child_pid in self.get_child_pids(pid):
                kill_result = self.kill(child_pid, force=True, recursive=True)
                if kill_result["success"]:
                    result["killed_pids"].append(child_pid)

            # Tuer le parent en dernier
            if include_parent:
                kill_result = self.kill(pid, force=False, recursive=False)
                if kill_result["success"]:
                    result["killed_pids"].append(pid)

            result["success"] = len(result["killed_pids"]) > 0
            result["message"] = f"Killed {len(result['killed_pids'])} process(es)"

        except Exception as e:
            result["message"] = f"Error killing process tree: {str(e)}"

        result["duration"] = time.time() - start_time
        return result

    def kill_by_name(
        self, process_name: str, exclude_pids: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """
    Kill all processes matching a given name.

    Args:
      process_name: Nom du process à tuer
      exclude_pids: Liste de PID à exclure

    Returns:
      Dictionnaire avec le résultat
    """
        result = {
            "success": False,
            "process_name": process_name,
            "killed_pids": [],
            "message": "",
        }

        exclude_pids = exclude_pids or []

        try:
            # Trouver les processus par nom
            pids = self.find_pids_by_name(process_name)

            for pid in pids:
                if pid not in exclude_pids:
                    kill_result = self.kill(pid, force=True, recursive=True)
                    if kill_result["success"]:
                        result["killed_pids"].append(pid)

            result["success"] = len(result["killed_pids"]) > 0
            result["message"] = (
                f"Found {len(pids)} process(es), killed {len(result['killed_pids'])}"
            )

        except Exception as e:
            result["message"] = f"Error killing by name: {str(e)}"

        return result

    def get_child_pids(self, pid: int) -> List[int]:
        """
    Return child PIDs for a parent process.

    Args:
      pid: Parent process ID.

    Returns:
      List of child process IDs.
    """
        children = []

        if _IS_WINDOWS:
            # Sur Windows, utiliser tasklist
            try:
                result = subprocess.run(
                    [
                        "wmic",
                        "process",
                        "where",
                        f"ParentProcessId={pid}",
                        "get",
                        "ProcessId",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                for line in result.stdout.splitlines():
                    if line.strip().isdigit():
                        children.append(int(line.strip()))
            except Exception:
                pass
        else:
            # Sur Linux/MacOS, lire /proc
            proc_path = Path("/proc")

            try:
                for entry in proc_path.iterdir():
                    if entry.name.isdigit():
                        try:
                            status_file = entry / "status"
                            if status_file.exists():
                                content = status_file.read_text()
                                for line in content.splitlines():
                                    if line.startswith("PPid:"):
                                        ppid = int(line.split(":")[1].strip())
                                        if ppid == pid:
                                            children.append(int(entry.name))
                                        break
                        except Exception:
                            continue
            except Exception:
                pass

        return children

    def find_pids_by_name(self, process_name: str) -> List[int]:
        """
    Find all PIDs matching a process name.

    Args:
      process_name: Nom du process

    Returns:
      Liste des PID trouvés
    """
        pids = []

        if _IS_WINDOWS:
            try:
                result = subprocess.run(
                    ["tasklist", "/FO", "CSV", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for line in result.stdout.splitlines():
                    if process_name.lower() in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                pids.append(int(parts[1]))
                            except ValueError:
                                pass
            except Exception:
                pass
        else:
            try:
                result = subprocess.run(
                    ["pgrep", "-f", process_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                for line in result.stdout.strip().splitlines():
                    try:
                        pids.append(int(line.strip()))
                    except ValueError:
                        pass
            except FileNotFoundError:
                # pgrep n'est pas disponible, utiliser une méthode alternative
                for pid in self._get_all_pids():
                    try:
                        cmdline = self._get_process_cmdline(pid)
                        if cmdline and process_name in cmdline:
                            pids.append(pid)
                    except Exception:
                        pass
            except Exception:
                pass

        return pids

    def _get_all_pids(self) -> List[int]:
        """Return all system process IDs."""
        pids = []
        proc_path = Path("/proc")

        try:
            for entry in proc_path.iterdir():
                if entry.name.isdigit():
                    pids.append(int(entry.name))
        except Exception:
            pass

        return pids

    def _get_process_cmdline(self, pid: int) -> Optional[str]:
        """Return command line for a process."""
        try:
            cmdline_file = Path(f"/proc/{pid}/cmdline")
            if cmdline_file.exists():
                return cmdline_file.read_text().replace("\x00", " ")
        except Exception:
            pass
        return None

    def _is_process_alive(self, pid: int) -> bool:
        """Check whether a process is still alive."""
        if _IS_WINDOWS:
            try:
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                return str(pid) in result.stdout
            except Exception:
                return False
        else:
            try:
                os.kill(pid, 0)
                return True
            except ProcessLookupError:
                return False
            except PermissionError:
                # Le processus existe mais on n'a pas les droits
                return True
            except Exception:
                return False

    def _terminate_signal(self, pid: int) -> None:
        """Send termination signal (SIGTERM or equivalent)."""
        if _IS_WINDOWS:
            # Sur Windows, utiliser os.terminate()
            os.terminate()
        else:
            os.kill(pid, signal.SIGTERM)

    def _kill_signal(self, pid: int) -> None:
        """Send forced termination signal (SIGKILL or equivalent)."""
        if _IS_WINDOWS:
            # Sur Windows, pas de SIGKILL équivalent direct
            os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGKILL)

    def _wait_for_termination(self, pid: int, timeout: float) -> bool:
        """Wait for process termination."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not self._is_process_alive(pid):
                return True
            time.sleep(0.1)

        return False


def kill_process(
    pid: int, force: bool = False, recursive: bool = False
) -> Dict[str, Any]:
    """
  Kill one process (utility function).

  Args:
    pid: ID du process
    force: Utiliser kill() directement
    recursive: Killr aussi les enfants

  Returns:
    Dictionnaire avec le résultat
  """
    killer = ProcessKiller()
    return killer.kill(pid, force, recursive)


def kill_process_tree(pid: int, include_parent: bool = True) -> Dict[str, Any]:
    """
  Kill one process and all its children (utility function).

  Args:
    pid: ID du process parent
    include_parent: Inclure le parent

  Returns:
    Dictionnaire avec le résultat
  """
    killer = ProcessKiller()
    return killer.kill_process_tree(pid, include_parent)


def get_process_info(pid: int) -> Optional[ProcessInfo]:
    """
  Return information for one process.

  Args:
    pid: ID du process

  Returns:
    ProcessInfo ou None si non trouvé
  """
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
            cmdline = Path(f"/proc/{pid}/cmdline").read_text().replace("\x00", " ")
            comm = Path(f"/proc/{pid}/comm").read_text().strip()
            return ProcessInfo(pid, comm, cmdline)
    except Exception:
        pass
    return None
