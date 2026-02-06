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
Command Helpers Module

Fonctions utilitaires pour la construction et validation des commandes
de compilation dans PyCompiler ARK.

Fournit:
- build_command(): Construction de la commande de compilation
- validate_command(): Validation des arguments
- escape_arguments(): Échappement des arguments
- CommandBuilder(): Classe pour construire des commandes complexes
"""

from __future__ import annotations

import os
import sys
import shlex
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple, Union
import re


def build_command(
    program: str,
    args: Optional[List[str]] = None,
    working_dir: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    use_shell: bool = False,
) -> Tuple[str, Dict[str, str]]:
    """
    Construit une commande de compilation complète.

    Args:
        program: Programme principal (python, pyinstaller, etc.)
        args: Arguments de la commande
        working_dir: Répertoire de travail
        env: Variables d'environnement supplémentaires
        use_shell: Utiliser shell pour l'exécution

    Returns:
        Tuple (commande str, environnement dict)
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
    Valide une commande de compilation.

    Args:
        program: Programme principal
        args: Arguments
        working_dir: Répertoire de travail

    Returns:
        Tuple (est_valide, message_erreur)
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
    Échappe les arguments pour une utilisation sécurisée.

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
    Sanitize un chemin pour éviter les injections.

    Args:
        path: Chemin à sanitizer

    Returns:
        Chemin sanitisé
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
    Classe pour construire des commandes de compilation complexes.

    Supporte:
    - Arguments positionnels et nommés
    - Options conditionnelles
    - Validation progressive
    - Génération de documentation
    """

    def __init__(self, program: str):
        """
        Initialise le builder avec un programme.

        Args:
            program: Programme principal
        """
        self.program = program
        self.args: List[str] = []
        self.env: Dict[str, str] = {}
        self.working_dir: Optional[str] = None
        self._flags: Dict[str, bool] = {}
        self._options: Dict[str, Any] = {}

    def add_arg(self, arg: str) -> "CommandBuilder":
        """
        Ajoute un argument simple.

        Args:
            arg: Argument à ajouter

        Returns:
            self pour chainage
        """
        sanitized = (
            sanitize_path(arg) if any(c in arg for c in [" ", "(", ")", "&"]) else arg
        )
        self.args.append(sanitized)
        return self

    def add_option(self, option: str, value: Any) -> "CommandBuilder":
        """
        Ajoute une option avec valeur.

        Args:
            option: Nom de l'option (avec ou sans --)
            value: Valeur de l'option

        Returns:
            self pour chainage
        """
        if not option.startswith("--"):
            option = "--" + option
        self.args.append(option)
        self.args.append(str(value))
        return self

    def add_flag(self, flag: str, condition: bool = True) -> "CommandBuilder":
        """
        Ajoute un flag conditionnel.

        Args:
            flag: Nom du flag (avec ou sans --)
            condition: Condition pour ajouter le flag

        Returns:
            self pour chainage
        """
        if condition:
            if not flag.startswith("--"):
                flag = "--" + flag
            self.args.append(flag)
        return self

    def add_file_option(self, option: str, file_path: str) -> "CommandBuilder":
        """
        Ajoute une option de fichier avec validation.

        Args:
            option: Nom de l'option
            file_path: Chemin du fichier

        Returns:
            self pour chainage
        """
        sanitized = sanitize_path(file_path)
        if os.path.exists(sanitized):
            self.add_option(option, sanitized)
        return self

    def add_directory_option(self, option: str, dir_path: str) -> "CommandBuilder":
        """
        Ajoute une option de répertoire avec validation.

        Args:
            option: Nom de l'option
            dir_path: Chemin du répertoire

        Returns:
            self pour chainage
        """
        sanitized = sanitize_path(dir_path)
        if os.path.isdir(sanitized):
            self.add_option(option, sanitized)
        return self

    def set_env(self, key: str, value: str) -> "CommandBuilder":
        """
        Définit une variable d'environnement.

        Args:
            key: Nom de la variable
            value: Valeur

        Returns:
            self pour chainage
        """
        self.env[key] = str(value)
        return self

    def set_working_dir(self, path: str) -> "CommandBuilder":
        """
        Définit le répertoire de travail.

        Args:
            path: Chemin du répertoire

        Returns:
            self pour chainage
        """
        sanitized = sanitize_path(path)
        if os.path.isdir(sanitized):
            self.working_dir = sanitized
        return self

    def add_multiple(self, option: str, values: List[str]) -> "CommandBuilder":
        """
        Ajoute plusieurs valeurs pour une même option.

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
        Construit la commande finale.

        Returns:
            Tuple (commande str, environnement, répertoire de travail)
        """
        full_env = os.environ.copy()
        full_env.update(self.env)
        full_env.setdefault("PYTHONUNBUFFERED", "1")

        cmd = [self.program] + self.args
        cmd_str = " ".join(escape_arguments(cmd))

        return cmd_str, full_env, self.working_dir

    def build_for_execution(self) -> Tuple[List[str], Dict[str, str], Optional[str]]:
        """
        Construit la commande pour exécution directe.

        Returns:
            Tuple (commande list, environnement, répertoire de travail)
        """
        full_env = os.environ.copy()
        full_env.update(self.env)
        full_env.setdefault("PYTHONUNBUFFERED", "1")

        return [self.program] + self.args, full_env, self.working_dir

    def get_summary(self) -> Dict[str, Any]:
        """
        Retourne un résumé de la commande.

        Returns:
            Dictionnaire avec le résumé
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
        Crée une copie du builder.

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
    Détecte l'exécutable Python à utiliser.

    Returns:
        Chemin de l'exécutable Python
    """
    # Utiliser le Python courant
    return sys.executable


def get_interpreter_version(python_path: Optional[str] = None) -> Tuple[int, int, int]:
    """
    Retourne la version de l'interpréteur Python.

    Args:
        python_path: Chemin de l'interpréteur (défaut: sys.executable)

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


def check_module_available(module_name: str, python_path: Optional[str] = None) -> bool:
    """
    Vérifie si un module Python est disponible.

    Args:
        module_name: Nom du module
        python_path: Chemin de l'interpréteur

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
