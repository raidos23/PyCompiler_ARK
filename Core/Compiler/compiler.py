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
Compiler Core Module

Module principal du compilateur PyCompiler ARK.
Gère l'exécution des processus de compilation avec support threading
et communication en temps réel avec l'interface utilisateur.

Fournit:
- Classe CompilationThread pour l'exécution non-bloquante
- Classe CompilerCore pour la gestion de la compilation
- Signaux pour la communication avec l'UI
"""

from __future__ import annotations

import os
import sys
import subprocess
import select
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum

from PySide6.QtCore import QThread, Signal, QObject


class CompilationStatus(Enum):
    """Statut de la compilation."""

    IDLE = "idle"
    RUNNING = "running"
    CANCELLED = "cancelled"
    SUCCESS = "success"
    FAILED = "failed"


class CompilationSignals(QObject):
    """Signaux pour la communication avec l'interface utilisateur."""

    output_ready = Signal(str)  # Signal pour stdout
    error_ready = Signal(str)  # Signal pour stderr
    finished = Signal(int)  # Code de retour
    status_changed = Signal(CompilationStatus)  # Changement de statut
    progress_update = Signal(int, str)  # Progression, message


class CompilationThread(QThread):
    """
    Thread pour exécuter la compilation sans bloquer l'UI.

    Gère l'exécution d'un processus de compilation avec:
    - Lecture en temps réel de stdout et stderr
    - Support de l'annulation
    - Gestion propre des ressources
    """

    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)
    progress_update = Signal(int, str)

    def __init__(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        """
        Initialise le thread de compilation.

        Args:
            program: Chemin de l'exécutable
            args: Liste des arguments
            env: Variables d'environnement (optionnel)
            working_dir: Répertoire de travail (optionnel)
            timeout: Timeout en secondes (optionnel)
        """
        super().__init__()
        self.program = program
        self.args = args
        self.env = env
        self.working_dir = working_dir
        self.timeout = timeout
        self.cancel_requested = False
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[datetime] = None

    def run(self) -> None:
        """Exécute le processus de compilation."""
        self.start_time = datetime.now()
        self.cancel_requested = False

        try:
            # Préparer l'environnement
            env = os.environ.copy()
            if self.env:
                env.update(self.env)

            # Créer le processus
            self.process = subprocess.Popen(
                [self.program] + self.args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=self.working_dir,
                bufsize=1,
            )

            self.progress_update.emit(0, "Process started")

            # Boucle principale de lecture
            self._read_output()

            # Lire les données restantes
            self._read_remaining()

            # Signaler la fin
            return_code = self.process.returncode
            self.finished.emit(return_code)

        except Exception as e:
            error_msg = f"Error: {str(e)}"
            self.error_ready.emit(error_msg)
            self.finished.emit(1)

    def _read_output(self) -> None:
        """Lit stdout et stderr en temps réel."""
        while True:
            # Vérifier l'annulation
            if self.cancel_requested:
                self._terminate_process()
                self.finished.emit(-1)  # Code spécial pour annulation
                return

            # Vérifier si le processus est terminé
            if self.process is None or self.process.poll() is not None:
                break

            # Utiliser select pour attendre des données
            try:
                ready, _, _ = select.select(
                    [self.process.stdout, self.process.stderr], [], [], 0.1
                )

                for stream in ready:
                    if stream == self.process.stdout:
                        line = self.process.stdout.readline()
                        if line:
                            self.output_ready.emit(line.rstrip())
                            self._update_progress(line)
                    elif stream == self.process.stderr:
                        line = self.process.stderr.readline()
                        if line:
                            self.error_ready.emit(line.rstrip())
                            self._update_progress(line)

            except Exception:
                break

            time.sleep(0.01)

    def _read_remaining(self) -> None:
        """Lit les données restantes dans les buffers après la fin du processus."""
        if self.process is None:
            return

        # Lire stdout restant
        try:
            remaining_stdout = self.process.stdout.read()
            if remaining_stdout:
                for line in remaining_stdout.strip().split("\n"):
                    if line:
                        self.output_ready.emit(line.rstrip())
        except Exception:
            pass

        # Lire stderr restant
        try:
            remaining_stderr = self.process.stderr.read()
            if remaining_stderr:
                for line in remaining_stderr.strip().split("\n"):
                    if line:
                        self.error_ready.emit(line.rstrip())
        except Exception:
            pass

    def _update_progress(self, line: str) -> None:
        """Met à jour la progression basée sur la sortie."""
        # Détecter les patterns de progression courants
        progress_patterns = [
            r"\[(\d+)%\]",
            r"Progress:\s*(\d+)",
            r"(\d+)/(\d+)",
        ]

        for pattern in progress_patterns:
            import re

            match = re.search(pattern, line)
            if match:
                if len(match.groups()) == 1:
                    progress = int(match.group(1))
                    self.progress_update.emit(progress, line)
                elif len(match.groups()) == 2:
                    current = int(match.group(1))
                    total = int(match.group(2))
                    progress = int((current / total) * 100)
                    self.progress_update.emit(progress, line)
                break

    def _terminate_process(self) -> None:
        """Tue le processus de compilation."""
        if self.process is None:
            return

        try:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        except Exception:
            pass

    def cancel(self) -> None:
        """Demande l'annulation de la compilation."""
        self.cancel_requested = True
        self._terminate_process()

    @property
    def duration(self) -> Optional[float]:
        """Retourne la durée d'exécution en secondes."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return None


class CompilerCore(QObject):
    """
    Classe principale du compilateur.

    Gère la compilation avec support pour:
    - Exécution asynchrone via threads
    - Annulation en temps réel
    - Collecte des logs et erreurs
    - Gestion de l'état de compilation
    """

    # Signaux
    output_ready = Signal(str)
    error_ready = Signal(str)
    finished = Signal(int)
    status_changed = Signal(CompilationStatus)
    progress_update = Signal(int, str)
    log_message = Signal(str, str)  # niveau, message

    def __init__(self, parent: Optional[QObject] = None):
        """
        Initialise le compilateur.

        Args:
            parent: Widget parent (optionnel)
        """
        super().__init__(parent)
        self._thread: Optional[CompilationThread] = None
        self._status = CompilationStatus.IDLE
        self._current_engine: Optional[str] = None
        self._current_file: Optional[str] = None
        self._workspace_dir: Optional[str] = None

    @property
    def status(self) -> CompilationStatus:
        """Retourne le statut actuel de la compilation."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Retourne True si une compilation est en cours."""
        return self._status == CompilationStatus.RUNNING

    @property
    def current_engine(self) -> Optional[str]:
        """Retourne le moteur de compilation actuel."""
        return self._current_engine

    @property
    def current_file(self) -> Optional[str]:
        """Retourne le fichier en cours de compilation."""
        return self._current_file

    @property
    def duration(self) -> Optional[float]:
        """Retourne la durée de la dernière compilation."""
        if self._thread:
            return self._thread.duration
        return None

    def compile(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
        engine_id: Optional[str] = None,
        file_path: Optional[str] = None,
        workspace_dir: Optional[str] = None,
    ) -> bool:
        """
        Démarre une compilation.

        Args:
            program: Chemin de l'exécutable
            args: Liste des arguments
            env: Variables d'environnement (optionnel)
            working_dir: Répertoire de travail (optionnel)
            engine_id: Identifiant du moteur (optionnel)
            file_path: Chemin du fichier à compiler (optionnel)
            workspace_dir: Chemin du workspace (optionnel)

        Returns:
            True si la compilation a démarré, False sinon
        """
        if self.is_running:
            self.log_message.emit("warning", "Compilation already in progress")
            return False

        # Stocker les infos
        self._current_engine = engine_id
        self._current_file = file_path
        self._workspace_dir = workspace_dir

        # Créer le thread
        self._thread = CompilationThread(
            program=program, args=args, env=env, working_dir=working_dir
        )

        # Connecter les signaux
        self._thread.output_ready.connect(self.output_ready.emit)
        self._thread.error_ready.connect(self.error_ready.emit)
        self._thread.finished.connect(self._on_finished)
        self._thread.progress_update.connect(self.progress_update.emit)

        # Changer le statut
        self._set_status(CompilationStatus.RUNNING)
        self.log_message.emit(
            "info", f"Starting compilation with {engine_id or 'unknown'}"
        )

        # Démarrer le thread
        self._thread.start()

        return True

    def cancel(self) -> bool:
        """
        Annule la compilation en cours.

        Returns:
            True si l'annulation a été demandée, False sinon
        """
        if not self.is_running:
            return False

        if self._thread:
            self._thread.cancel()
            self.log_message.emit("info", "Cancellation requested")
        return True

    def _set_status(self, status: CompilationStatus) -> None:
        """Change le statut de la compilation."""
        self._status = status
        self.status_changed.emit(status)

    def _on_finished(self, return_code: int) -> None:
        """Appelé lorsque la compilation est terminée."""
        if return_code == -1:
            self._set_status(CompilationStatus.CANCELLED)
            self.log_message.emit("info", "Compilation cancelled")
        elif return_code == 0:
            self._set_status(CompilationStatus.SUCCESS)
            duration = self.duration
            if duration:
                self.log_message.emit(
                    "success", f"Compilation successful! ({duration:.2f}s)"
                )
            else:
                self.log_message.emit("success", "Compilation successful!")
        else:
            self._set_status(CompilationStatus.FAILED)
            duration = self.duration
            if duration:
                self.log_message.emit(
                    "error",
                    f"Compilation failed (code {return_code}) in {duration:.2f}s",
                )
            else:
                self.log_message.emit(
                    "error", f"Compilation failed with code {return_code}"
                )

        self.finished.emit(return_code)

    def get_command_line(self, program: str, args: List[str]) -> str:
        """
        Retourne la ligne de commande formatée.

        Args:
            program: Programme à exécuter
            args: Arguments

        Returns:
            Ligne de commande formatée
        """
        cmd = [program] + args
        return " ".join(cmd)

    def dry_run(
        self,
        program: str,
        args: List[str],
        env: Optional[Dict[str, str]] = None,
        working_dir: Optional[str] = None,
    ) -> str:
        """
        Simule une compilation et retourne la commande.

        Args:
            program: Programme à exécuter
            args: Arguments
            env: Variables d'environnement (optionnel)
            working_dir: Répertoire de travail (optionnel)

        Returns:
            Commande formatée
        """
        cmd = self.get_command_line(program, args)
        result = f"[DRY RUN] Command: {cmd}\n"
        result += f"Working directory: {working_dir or 'current'}\n"

        if env:
            env_info = "\n  ".join(
                [f"{k}={v}" for k, v in env.items() if "ARK" in k or "PATH" in k]
            )
            result += f"Environment:\n  {env_info}"

        return result
