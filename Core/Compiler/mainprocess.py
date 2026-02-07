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
Main Process Module

Module de processus principal pour PyCompiler ARK.
Coordonne la compilation, la gestion des workspaces et l'interaction
avec les moteurs de compilation.

Fournit:
- Classe MainProcess pour orchestrer la compilation
- Gestion du workspace
- Communication avec l'interface utilisateur
- Intégration ArkConfigManager pour les exclusions de fichiers
"""

from __future__ import annotations

import os
import sys
import subprocess
import shlex
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple, Union
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal

from Core.Compiler.compiler import (
    CompilerCore,
    CompilationThread,
    CompilationStatus,
    CompilationSignals,
)

# Importations ArkConfigManager pour la gestion des exclusions
from Core.ArkConfigManager import (
    load_ark_config,
    should_exclude_file,
    DEFAULT_EXCLUSION_PATTERNS,
)


class ProcessState(Enum):
    """États possibles du processus principal."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    COMPILING = "compiling"
    CANCELLING = "cancelling"
    ERROR = "error"


class MainProcessSignals(QObject):
    """Signaux pour la communication avec l'interface utilisateur."""

    state_changed = Signal(ProcessState)
    log_message = Signal(str, str)  # niveau, message
    compilation_started = Signal(dict)  # infos de compilation
    compilation_finished = Signal(int, dict)  # code retour, infos
    engine_ready = Signal(str)  # engine_id
    workspace_changed = Signal(str)  # workspace_path


class MainProcess(QObject):
    """
    Classe principale de processus pour la compilation.

    Coordonne l'ensemble du processus de compilation:
    - Initialisation du workspace
    - Sélection et configuration du moteur
    - Exécution de la compilation
    - Gestion des erreurs et annulation

    Utilise CompilerCore pour l'exécution réelle.
    """

    # Signaux
    state_changed = Signal(ProcessState)
    log_message = Signal(str, str)  # niveau, message
    compilation_started = Signal(dict)
    compilation_finished = Signal(int, dict)
    engine_ready = Signal(str)
    workspace_changed = Signal(str)
    output_ready = Signal(str)
    error_ready = Signal(str)
    progress_update = Signal(int, str)

    def __init__(
        self, workspace_dir: Optional[str] = None, parent: Optional[QObject] = None
    ):
        """
        Initialise le processus principal.

        Args:
            workspace_dir: Chemin du workspace (optionnel)
            parent: Widget parent (optionnel)
        """
        super().__init__(parent)

        # État interne
        self._state = ProcessState.IDLE
        self._workspace_dir: Optional[str] = None
        self._current_file: Optional[str] = None
        self._current_engine: Optional[str] = None

        # Composants
        self.compiler = CompilerCore()
        self._connect_signals()

        # Workspace
        if workspace_dir:
            self.set_workspace(workspace_dir)

        self._set_state(ProcessState.READY)

    def _connect_signals(self) -> None:
        """Connecte les signaux du compilateur aux signaux du processus."""
        # Signaux du compilateur vers le processus
        self.compiler.output_ready.connect(self.output_ready.emit)
        self.compiler.error_ready.connect(self.error_ready.emit)
        self.compiler.finished.connect(self._on_compilation_finished)
        self.compiler.status_changed.connect(self._on_status_changed)
        self.compiler.progress_update.connect(self.progress_update.emit)
        self.compiler.log_message.connect(self.log_message.emit)

    def _set_state(self, state: ProcessState) -> None:
        """Change l'état du processus."""
        self._state = state
        self.state_changed.emit(state)

    @property
    def state(self) -> ProcessState:
        """Retourne l'état actuel du processus."""
        return self._state

    @property
    def workspace_dir(self) -> Optional[str]:
        """Retourne le chemin du workspace."""
        return self._workspace_dir

    @property
    def current_file(self) -> Optional[str]:
        """Retourne le fichier en cours de compilation."""
        return self._current_file

    @property
    def current_engine(self) -> Optional[str]:
        """Retourne le moteur de compilation actuel."""
        return self._current_engine

    @property
    def is_ready(self) -> bool:
        """Retourne True si le processus est prêt."""
        return self._state in (ProcessState.READY, ProcessState.IDLE)

    @property
    def is_compiling(self) -> bool:
        """Retourne True si une compilation est en cours."""
        return self._state == ProcessState.COMPILING

    @property
    def is_idle(self) -> bool:
        """Retourne True si le processus est inactif."""
        return self._state == ProcessState.IDLE

    def set_workspace(self, workspace_dir: str) -> bool:
        """
        Définit le workspace de travail.

        Args:
            workspace_dir: Chemin du workspace

        Returns:
            True si le workspace a été défini, False sinon
        """
        if not workspace_dir or not os.path.isdir(workspace_dir):
            self.log_message.emit(
                "error", f"Invalid workspace directory: {workspace_dir}"
            )
            return False

        self._workspace_dir = workspace_dir

        # Configurer les variables d'environnement
        os.environ["ARK_WORKSPACE"] = workspace_dir

        self.log_message.emit("info", f"Workspace set to: {workspace_dir}")
        self.workspace_changed.emit(workspace_dir)

        return True

    def set_file(self, file_path: str) -> bool:
        """
        Définit le fichier à compiler.

        Args:
            file_path: Chemin du fichier Python

        Returns:
            True si le fichier a été défini, False sinon
        """
        if not file_path or not os.path.isfile(file_path):
            self.log_message.emit("error", f"File not found: {file_path}")
            return False

        self._current_file = file_path
        self.log_message.emit("info", f"File set: {file_path}")

        return True

    def set_engine(self, engine_id: str) -> None:
        """
        Définit le moteur de compilation à utiliser.

        Args:
            engine_id: Identifiant du moteur
        """
        self._current_engine = engine_id
        self.log_message.emit("info", f"Engine selected: {engine_id}")
        self.engine_ready.emit(engine_id)

    def compile(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        engine_id: Optional[str] = None,
        file_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
    ) -> bool:
        """
        Démarre une compilation.

        Args:
            program: Programme à exécuter
            args: Arguments de compilation
            env: Variables d'environnement (optionnel)
            engine_id: Identifiant du moteur (optionnel)
            file_path: Chemin du fichier (optionnel)
            workspace_dir: Répertoire de travail (optionnel)

        Returns:
            True si la compilation a démarré, False sinon
        """
        if self.is_compiling:
            self.log_message.emit("warning", "Compilation already in progress")
            return False

        # Mettre à jour le workspace si fourni
        if workspace_dir and workspace_dir != self._workspace_dir:
            self._workspace_dir = workspace_dir

        # Vérifier l'exclusion avant de lancer la compilation
        if file_path and self._workspace_dir:
            if self.should_exclude(file_path):
                self.log_message.emit(
                    "warning", f"File excluded by ARK config: {file_path}"
                )
                return False

        # Déterminer le répertoire de travail
        working_dir = workspace_dir or self._workspace_dir
        if file_path:
            working_dir = working_dir or os.path.dirname(file_path)

        # Déterminer les variables d'environnement
        compile_env = env or {}
        if self._workspace_dir:
            compile_env["ARK_WORKSPACE"] = self._workspace_dir

        # Préparer les infos de compilation
        compile_info = {
            "engine": engine_id or self._current_engine,
            "file": file_path or self._current_file,
            "workspace": working_dir,
            "command": " ".join([program] + args),
        }

        # Émettre le signal de début
        self.compilation_started.emit(compile_info)

        # Démarrer la compilation
        success = self.compiler.compile(
            program=program,
            args=args,
            env=compile_env,
            working_dir=working_dir,
            engine_id=engine_id or self._current_engine,
            file_path=file_path or self._current_file,
            workspace_dir=working_dir,
        )

        if success:
            self._set_state(ProcessState.COMPILING)
            self.log_message.emit("info", "Compilation started")

        return success

    def cancel(self) -> bool:
        """
        Annule la compilation en cours.

        Returns:
            True si l'annulation a été demandée, False sinon
        """
        if not self.is_compiling:
            return False

        self._set_state(ProcessState.CANCELLING)
        return self.compiler.cancel()

    def dry_run(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        workspace_dir: Optional[str] = None,
    ) -> str:
        """
        Simule une compilation sans l'exécuter.

        Args:
            program: Programme à exécuter
            args: Arguments
            env: Variables d'environnement (optionnel)
            workspace_dir: Répertoire de travail (optionnel)

        Returns:
            Description de la commande à exécuter
        """
        working_dir = workspace_dir or self._workspace_dir
        return self.compiler.dry_run(program, args, env, working_dir)

    def _on_compilation_finished(self, return_code: int) -> None:
        """Appelé lorsque la compilation est terminée."""
        compile_info = {
            "engine": self._current_engine,
            "file": self._current_file,
            "workspace": self._workspace_dir,
            "duration": self.compiler.duration,
        }

        self.compilation_finished.emit(return_code, compile_info)

        if self._state == ProcessState.CANCELLING:
            self._set_state(ProcessState.READY)
        elif return_code == 0:
            self._set_state(ProcessState.READY)
        else:
            self._set_state(ProcessState.ERROR)

    def _on_status_changed(self, status: CompilationStatus) -> None:
        """Appelé lorsque le statut du compilateur change."""
        # Traduire le statut du compilateur vers l'état du processus
        if status == CompilationStatus.RUNNING:
            self._set_state(ProcessState.COMPILING)
        elif status == CompilationStatus.SUCCESS:
            self._set_state(ProcessState.READY)
        elif status == CompilationStatus.FAILED:
            self._set_state(ProcessState.ERROR)
        elif status == CompilationStatus.CANCELLED:
            self._set_state(ProcessState.READY)
        else:
            self._set_state(ProcessState.READY)

    def get_compilation_info(self) -> Dict[str, Any]:
        """
        Retourne les informations de compilation actuelles.

        Returns:
            Dictionnaire avec les infos de compilation
        """
        return {
            "engine": self._current_engine,
            "file": self._current_file,
            "workspace": self._workspace_dir,
            "state": self._state.value,
            "is_compiling": self.is_compiling,
            "duration": self.compiler.duration,
        }

    def reset(self) -> None:
        """Réinitialise le processus pour une nouvelle compilation."""
        self._current_file = None
        self._current_engine = None
        self._set_state(ProcessState.READY)
        self.log_message.emit("info", "Process reset")

    # =========================================================================
    # FONCTIONS DE GESTION DES EXCLUSIONS (intégration ArkConfigManager)
    # =========================================================================

    def get_exclusion_patterns(self) -> List[str]:
        """
        Retourne les patterns d'exclusion configurés.

        Returns:
            Liste des patterns d'exclusion
        """
        if self._workspace_dir:
            try:
                config = load_ark_config(self._workspace_dir)
                return config.get("exclusion_patterns", DEFAULT_EXCLUSION_PATTERNS)
            except Exception:
                pass
        return DEFAULT_EXCLUSION_PATTERNS

    def should_exclude(self, file_path: str) -> bool:
        """
        Détermine si un fichier doit être exclu de la compilation.

        Args:
            file_path: Chemin absolu du fichier à vérifier

        Returns:
            True si le fichier doit être exclu, False sinon
        """
        if not self._workspace_dir:
            return False
        patterns = self.get_exclusion_patterns()
        return should_exclude_file(file_path, self._workspace_dir, patterns)


# =========================================================================
# FONCTIONS DE CONSTRUCTION ET VALIDATION DE COMMANDES
# =========================================================================
# Ces fonctions étaient dans command_helpers.py et sont maintenant
# intégrées directement dans mainprocess.py pour supporter le processus
# de compilation avec ArkConfigManager
# =========================================================================


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
