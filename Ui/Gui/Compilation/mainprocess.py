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

Main process module for PyCompiler ARK.
Coordinates compilation, workspace lifecycle, and engine interactions.

Provides:
- `MainProcess` class for compilation orchestration
- Workspace management
- User interface communication
- ArkConfig integration for file exclusion rules
"""

from __future__ import annotations

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

# Importations ArkConfig pour la gestion des exclusions
from Core.Configs import DEFAULT_EXCLUDE_PATTERNS, load_ark_config, should_exclude_file
from Core.engine.build_context import BuildContext
from Ui.Gui.Compilation.compiler import CompilationStatus, CompilerCore


class ProcessState(Enum):
    """Possible states of the main process."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    COMPILING = "compiling"
    CANCELLING = "cancelling"
    ERROR = "error"


class MainProcess(QObject):
    """
    Main process class used to orchestrate compilation.

    Coordinates the full compilation flow:
    - Workspace initialization
    - Engine selection and configuration
    - Compilation execution
    - Error handling and cancellation

    Uses `CompilerCore` for the underlying execution.
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
        Initialize the main process.

        Args:
          workspace_dir: Optional workspace path.
          parent: Optional parent object.
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
        """Connect compiler signals to process-level signals."""
        # Signaux du compilateur vers le processus
        self.compiler.output_ready.connect(self.output_ready.emit)
        self.compiler.error_ready.connect(self.error_ready.emit)
        self.compiler.finished.connect(self._on_compilation_finished)
        self.compiler.status_changed.connect(self._on_status_changed)
        self.compiler.progress_update.connect(self.progress_update.emit)
        self.compiler.log_message.connect(self.log_message.emit)

    def _set_state(self, state: ProcessState) -> None:
        """Update process state."""
        self._state = state
        self.state_changed.emit(state)

    @property
    def state(self) -> ProcessState:
        """Return current process state."""
        return self._state

    @property
    def workspace_dir(self) -> Optional[str]:
        """Return workspace path."""
        return self._workspace_dir

    @property
    def current_file(self) -> Optional[str]:
        """Return the file currently being compiled."""
        return self._current_file

    @property
    def current_engine(self) -> Optional[str]:
        """Return the current compilation engine."""
        return self._current_engine

    @property
    def is_ready(self) -> bool:
        """Return True when the process is ready."""
        return self._state in (ProcessState.READY, ProcessState.IDLE)

    @property
    def is_compiling(self) -> bool:
        """Return True when a compilation is currently running."""
        return self._state == ProcessState.COMPILING

    @property
    def is_idle(self) -> bool:
        """Return True when the process is idle."""
        return self._state == ProcessState.IDLE

    def set_workspace(self, workspace_dir: str) -> bool:
        """
        Set workspace directory.

        Args:
         workspace_dir: Path du workspace

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
        Set file to compile.

        Args:
         file_path: Path du file Python

        Returns:
         True si le file a été défini, False sinon
        """
        if not file_path or not os.path.isfile(file_path):
            self.log_message.emit("error", f"File not found: {file_path}")
            return False

        self._current_file = file_path
        self.log_message.emit("info", f"File set: {file_path}")

        return True

    def set_engine(self, engine_id: str) -> None:
        """
        Set compilation engine to use.

        Args:
         engine_id: Identifiant du engine
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
        Start a compilation.

        Args:
         program: Programme à executer
         args: Arguments de compilation
         env: Variables d'environment (optionnel)
         engine_id: Identifiant du engine (optionnel)
         file_path: Path du file (optionnel)
         workspace_dir: Répertoire de travail (optionnel)

        Returns:
         True si la compilation a démarré, False sinon
        """
        if self.is_compiling:
            self.log_message.emit("warning", "Compilation already in progress")
            return False

        if not file_path:
            self.log_message.emit("error", "Compilation requires an entrypoint file")
            return False
        if not os.path.isfile(file_path):
            self.log_message.emit(
                "error", f"Entrypoint missing or obsolete: {file_path}"
            )
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
        Cancel current compilation.

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
        Simulate compilation without execution.

        Args:
         program: Programme à executer
         args: Arguments
         env: Variables d'environment (optionnel)
         workspace_dir: Répertoire de travail (optionnel)

        Returns:
         Description de la commande à executer
        """
        working_dir = workspace_dir or self._workspace_dir
        return self.compiler.dry_run(program, args, env, working_dir)

    def _on_compilation_finished(self, return_code: int) -> None:
        """Called when compilation is finished."""
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
        """Called when compiler status changes."""
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
        Return current compilation information.

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

    def compile_from_context(
        self,
        workspace: Path | str,
        engine_id: str,
        context: BuildContext,
        engine_config: Optional[Dict[str, Any]] = None,
        is_rebuild: bool = False,
    ) -> bool:
        """
        Start an async compilation from a :class:`BuildContext`.

        Delegates to :class:`CompilerCore` which uses the unified core logic.

        Args:
            workspace:     Absolute path to the project workspace.
            engine_id:     Registered engine identifier.
            context:       BuildContext describing the project.
            engine_config: Optional per-engine config overrides.
            is_rebuild:    Whether this is a rebuild from a lock file.

        Returns:
            ``True`` if the compilation thread started successfully.
        """
        workspace = Path(workspace)

        # Mettre à jour le workspace
        self._workspace_dir = str(workspace)
        self._current_engine = engine_id
        self._current_file = context.entry_point

        # Émettre le signal de début (approximation pour compatibilité UI)
        compile_info = {
            "engine": engine_id,
            "file": context.entry_point,
            "workspace": str(workspace),
            "command": "[Resolved by Core]",
        }
        self.compilation_started.emit(compile_info)

        return self.compiler.compile_from_context(
            workspace=workspace,
            engine_id=engine_id,
            context=context,
            engine_config=engine_config,
            is_rebuild=is_rebuild,
        )

    def reset(self) -> None:
        """Reset process state for a new compilation."""
        self._current_file = None
        self._current_engine = None
        self._set_state(ProcessState.READY)
        self.log_message.emit("info", "Process reset")

    # =========================================================================
    # FONCTIONS DE GESTION DES EXCLUSIONS (intégration ArkConfig)
    # =========================================================================

    def get_exclusion_patterns(self) -> List[str]:
        """
        Return configured exclusion patterns.

        Returns:
         Liste des patterns d'exclusion
        """
        if self._workspace_dir:
            try:
                config = load_ark_config(self._workspace_dir)
                # Pour la compilation, on utilise désormais build: exclude
                build_cfg = config.get("build", {})
                if isinstance(build_cfg, dict):
                    return build_cfg.get("exclude", DEFAULT_EXCLUDE_PATTERNS)
            except Exception:
                pass
        return DEFAULT_EXCLUDE_PATTERNS

    def should_exclude(self, file_path: str) -> bool:
        """
        Determine whether a file must be excluded from compilation.

        Args:
         file_path: Path absolu du file à checkr

        Returns:
         True si le file doit être exclu, False sinon
        """
        if not self._workspace_dir:
            return False
        patterns = self.get_exclusion_patterns()
        return should_exclude_file(file_path, self._workspace_dir, patterns)


# =========================================================================
# FONCTIONS DE CONSTRUCTION ET VALIDATION DE COMMANDES
# =========================================================================
# Ces fonctions ont été déplacées dans Core.Compiler.utils
# et sont importées au début de ce fichier pour maintenir la compatibilité.
# =========================================================================
