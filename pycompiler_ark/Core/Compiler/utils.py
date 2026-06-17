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
Compiler Utilities

Pure Python compilation helpers for PyCompiler ARK.
These functions do not depend on Qt and are safe to use in CLI.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple


def build_command(
    program: str,
    args: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    use_shell: bool = False,
) -> Tuple[str, Dict[str, str]]:
    """
    Build a complete compilation command.

    Args:
     program: Programme main (python, pyinstaller, etc.)
     args: Arguments de la commande
     working_dir: Répertoire de travail
     env: Variables d'environment supplémentaires
     use_shell: Utiliser shell pour l'exécution

    Returns:
     Tuple (commande str, environment dict)
    """
    # Construire la commande
    if args:
        cmd_parts = [program] + args
    else:
        cmd_parts = [program]

    if use_shell:
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd_parts)
    else:
        cmd_str = " ".join(cmd_parts)

    # Préparer l'environnement
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    # Ajouter des variables par défaut
    full_env.setdefault("PYTHONUNBUFFERED", "1")
    full_env.setdefault("ARK_COMPILER", "PyCompiler_ARK")

    return cmd_str, full_env


def validate_command(
    program: str, args: Optional[List[str]] = None, working_dir: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validate a compilation command.

    Args:
     program: Programme main
     args: Arguments
     working_dir: Répertoire de travail

    Returns:
     Tuple (est_validate, message_erreur)
    """
    # Vérifier le programme
    if not program:
        return False, "No program specified"

    # Vérifier si le programme existe
    program_path = None

    # Chercher dans le PATH
    for path in os.environ.get("PATH", "").split(os.pathsep):
        test_path = os.path.join(path, program)
        if os.path.isfile(test_path) and os.access(test_path, os.X_OK):
            program_path = test_path
            break

    # Vérifier si c'est un chemin absolu
    if not program_path and os.path.isabs(program):
        if os.path.isfile(program) and os.access(program, os.X_OK):
            program_path = program

    # Si pas trouvé et pas d'extension, essayer avec .py
    if not program_path and not program.endswith((".exe", ".py")):
        py_program = program + ".py"
        for path in os.environ.get("PATH", "").split(os.pathsep):
            test_path = os.path.join(path, py_program)
            if os.path.isfile(test_path):
                program_path = test_path
                break

    if not program_path:
        # Pour Python, on peut utiliser sys.executable
        if program in ("python", "python3"):
            program_path = sys.executable
        else:
            return False, f"Program not found: {program}"

    # Vérifier le répertoire de travail
    if working_dir and not os.path.isdir(working_dir):
        return False, f"Working directory not found: {working_dir}"

    # Valider les arguments
    if args:
        for i, arg in enumerate(args):
            if not isinstance(arg, str):
                return False, f"Invalid argument type at position {i}: {type(arg)}"

    return True, "Command is valid"


def escape_arguments(args: List[str]) -> List[str]:
    """
    Escape arguments for secure usage.

    Args:
     args: Liste d'arguments

    Returns:
     Liste d'arguments échappés
    """
    escaped = []
    for arg in args:
        # Échapper les caractères spéciaux
        escaped.append(shlex.quote(str(arg)))
    return escaped


def sanitize_path(path: str) -> str:
    """
    Sanitize a path to avoid injections.

    Args:
     path: Path à sanitizer

    Returns:
     Path sanitisé
    """
    # Supprimer les caractères dangereux
    dangerous_chars = [
        ";",
        "|",
        "&",
        "$",
        "`",
        "(",
        ")",
        "{",
        "}",
        "[",
        "]",
        "<",
        ">",
        "\n",
        "\r",
    ]
    sanitized = path
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    # Normaliser le chemin
    try:
        sanitized = os.path.normpath(sanitized)
        # Vérifier qu'il ne sort pas du répertoire racine
        if not os.path.isabs(sanitized):
            sanitized = os.path.abspath(sanitized)
    except Exception:
        return ""

    return sanitized


class CommandBuilder:
    """
    Class to build advanced compilation commands.

    Supports:
    - Positional and named arguments
    - Conditional flags/options
    - Progressive validation
    - Command documentation output
    """

    def __init__(self, program: str):
        """
        Initialize builder with a target program.

        Args:
          program: Main executable/program.
        """
        self.program = program
        self.args: List[str] = []
        self.env: Dict[str, str] = {}
        self.working_dir: Optional[str] = None
        self._flags: Dict[str, bool] = {}
        self._options: Dict[str, Any] = {}

    def add_arg(self, arg: str) -> "CommandBuilder":
        """
        Add a simple argument.

        Args:
          arg: Argument to append.

        Returns:
          `self` for fluent chaining.
        """
        sanitized = (
            sanitize_path(arg) if any(c in arg for c in [" ", "(", ")", "&"]) else arg
        )
        self.args.append(sanitized)
        return self

    def add_option(self, option: str, value: Any) -> "CommandBuilder":
        """
        Add an option with value.

        Args:
          option: Option name (with or without `--`).
          value: Option value.

        Returns:
          `self` for fluent chaining.
        """
        if not option.startswith("--"):
            option = "--" + option
        self.args.append(option)
        self.args.append(str(value))
        return self

    def add_flag(self, flag: str, condition: bool = True) -> "CommandBuilder":
        """
        Add a conditional flag.

        Args:
          flag: Flag name (with or without `--`).
          condition: Condition used to include the flag.

        Returns:
          `self` for fluent chaining.
        """
        if condition:
            if not flag.startswith("--"):
                flag = "--" + flag
            self.args.append(flag)
        return self

    def add_file_option(self, option: str, file_path: str) -> "CommandBuilder":
        """
        Add a file option with path validation.

        Args:
          option: Option name.
          file_path: File path.

        Returns:
          `self` for fluent chaining.
        """
        sanitized = sanitize_path(file_path)
        if os.path.exists(sanitized):
            self.add_option(option, sanitized)
        return self

    def add_directory_option(self, option: str, dir_path: str) -> "CommandBuilder":
        """
        Add a directory option with path validation.

        Args:
          option: Option name.
          dir_path: Directory path.

        Returns:
          `self` for fluent chaining.
        """
        sanitized = sanitize_path(dir_path)
        if os.path.isdir(sanitized):
            self.add_option(option, sanitized)
        return self

    def set_env(self, key: str, value: str) -> "CommandBuilder":
        """
        Set an environment variable override.

        Args:
          key: Variable name.
          value: Variable value.

        Returns:
          `self` for fluent chaining.
        """
        self.env[key] = str(value)
        return self

    def set_working_dir(self, path: str) -> "CommandBuilder":
        """
        Set le directory de travail.

        Args:
         path: Path du directory

        Returns:
         self pour chainage
        """
        sanitized = sanitize_path(path)
        if os.path.isdir(sanitized):
            self.working_dir = sanitized
        return self

    def add_multiple(self, option: str, values: List[str]) -> "CommandBuilder":
        """
        Add multiple values for the same option.

        Args:
         option: Nom de l'option
         values: Liste de valeurs

        Returns:
         self pour chainage
        """
        for value in values:
            self.add_option(option, value)
        return self

    def build(self) -> Tuple[str, Dict[str, str], Optional[str]]:
        """
        Build la commande finale.

        Returns:
         Tuple (commande str, environment, directory de travail)
        """
        full_env = os.environ.copy()
        full_env.update(self.env)
        full_env.setdefault("PYTHONUNBUFFERED", "1")

        cmd = [self.program] + self.args
        cmd_str = " ".join(escape_arguments(cmd))

        return cmd_str, full_env, self.working_dir

    def build_for_execution(self) -> Tuple[List[str], Dict[str, str], Optional[str]]:
        """
        Build command for direct execution.

        Returns:
         Tuple (commande list, environment, directory de travail)
        """
        full_env = os.environ.copy()
        full_env.update(self.env)
        full_env.setdefault("PYTHONUNBUFFERED", "1")

        return [self.program] + self.args, full_env, self.working_dir

    def get_summary(self) -> Dict[str, Any]:
        """
        Return un summary de la commande.

        Returns:
         Dictionnaire avec le summary
        """
        return {
            "program": self.program,
            "args": self.args,
            "arg_count": len(self.args),
            "env_vars": list(self.env.keys()),
            "working_dir": self.working_dir,
        }

    def copy(self) -> "CommandBuilder":
        """
        Create a copy of the builder.

        Returns:
         Nouvelle instance avec les mêmes paramètres
        """
        builder = CommandBuilder(self.program)
        builder.args = self.args.copy()
        builder.env = self.env.copy()
        builder.working_dir = self.working_dir
        return builder


def detect_python_executable() -> str:
    """
    Detect Python executable to use.

    Returns:
     Path de l'executable Python
    """
    # Utiliser le Python courant
    return sys.executable


def get_interpreter_version(python_path: Optional[str] = None) -> Tuple[int, int, int]:
    """
    Return Python interpreter version.

    Args:
     python_path: Path de l'interpréteur (défaut: sys.executable)

    Returns:
     Tuple (major, minor, patch)
    """
    if python_path is None:
        python_path = sys.executable

    try:
        result = subprocess.run(
            [python_path, "--version"], capture_output=True, text=True, timeout=5
        )
        version_str = result.stdout or result.stderr
        match = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
        if match:
            return int(match.group(1)), int(match.group(2)), int(match.group(3))
    except Exception:
        pass

    return sys.version_info.major, sys.version_info.minor, sys.version_info.micro


def get_interpreter_version_str(python_path: Optional[str] = None) -> str:
    """
    Return Python interpreter version as a string.

    Args:
     python_path: Path de l'interpréteur (défaut: sys.executable)

    Returns:
     Version string (ex: "3.10.12")
    """
    v = get_interpreter_version(python_path)
    return f"{v[0]}.{v[1]}.{v[2]}"


def check_module_available(module_name: str, python_path: Optional[str] = None) -> bool:
    """
    Check whether a Python module is available.

    Args:
     module_name: Nom du module
     python_path: Path de l'interpréteur

    Returns:
     True si le module est disponible
    """
    try:
        if python_path:
            result = subprocess.run(
                [python_path, "-c", f"import {module_name}"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        else:
            import importlib

            importlib.import_module(module_name)
            return True
    except Exception:
        return False


def check_internet_connection(timeout: float = 3.0, retries: int = 0) -> bool:
    """
    Check if internet connection is available with high certainty.
    Prioritizes checking connectivity to essential services like PyPI.
    """
    import socket
    import http.client
    import time

    # Essential hosts to verify connectivity for tool installation
    # pypi.org is the most important one for pip installs
    hosts = ["pypi.org", "www.google.com", "www.cloudflare.com", "1.1.1.1"]

    for attempt in range(retries + 1):
        # Try each host
        for host in hosts:
            try:
                # If it looks like an IP, use direct connection
                if host[0].isdigit():
                    with socket.create_connection((host, 53), timeout=timeout):
                        return True
                else:
                    # For domains, try both resolution and a quick HTTP HEAD request
                    # This handles environments with DNS but no real internet egress
                    socket.gethostbyname(host)
                    conn = http.client.HTTPSConnection(host, timeout=timeout)
                    conn.request("HEAD", "/")
                    res = conn.getresponse()
                    conn.close()
                    if 200 <= res.status < 400:
                        return True
            except Exception:
                continue

        if attempt < retries:
            time.sleep(1.0)

    return False
