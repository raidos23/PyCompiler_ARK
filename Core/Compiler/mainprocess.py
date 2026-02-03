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
"""

from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QObject, Signal

from Core.Compiler.compiler import (
    CompilerCore,
    CompilationThread,
    CompilationStatus,
    CompilationSignals,
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
