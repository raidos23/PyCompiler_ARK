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
Engine Configuration Manager
Gère la persistance des configurations spécifiques à chaque engine dans .pycompiler/
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Dict
import os


class EngineConfigManager:
    """Gestionnaire de configuration persistante pour les engines."""

    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialise le gestionnaire de configuration.

        Args:
            config_dir: Répertoire de configuration (.pycompiler). 
                       Si None, utilise ~/.pycompiler
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            self.config_dir = Path.home() / ".pycompiler"

        self.engines_dir = self.config_dir / "engines"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Crée les répertoires de configuration s'ils n'existent pas."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.engines_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise RuntimeError(f"Failed to create config directories: {e}")

    def _get_engine_config_path(self, engine_id: str) -> Path:
        """Retourne le chemin du fichier de configuration pour un engine."""
        return self.engines_dir / f"{engine_id}.json"

    def load(self, engine_id: str, schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Charge la configuration d'un engine.

        Args:
            engine_id: Identifiant unique de l'engine
            schema: Schéma de validation optionnel (dict avec clés par défaut)

        Returns:
            Dictionnaire de configuration chargé ou schéma par défaut
        """
        config_path = self._get_engine_config_path(engine_id)

        if not config_path.exists():
            return schema.copy() if schema else {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            if not isinstance(config, dict):
                return schema.copy() if schema else {}

            # Fusionner avec le schéma si fourni
            if schema:
                merged = schema.copy()
                merged.update(config)
                return merged

            return config

        except (json.JSONDecodeError, IOError) as e:
            # Retourner le schéma par défaut en cas d'erreur
            return schema.copy() if schema else {}

    def save(self, engine_id: str, config: Dict[str, Any]) -> bool:
        """
        Sauvegarde la configuration d'un engine.

        Args:
            engine_id: Identifiant unique de l'engine
            config: Dictionnaire de configuration à sauvegarder

        Returns:
            True si succès, False sinon
        """
        if not isinstance(config, dict):
            return False

        config_path = self._get_engine_config_path(engine_id)

        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            return True
        except (IOError, TypeError) as e:
            return False

    def delete(self, engine_id: str) -> bool:
        """
        Supprime la configuration d'un engine.

        Args:
            engine_id: Identifiant unique de l'engine

        Returns:
            True si succès, False sinon
        """
        config_path = self._get_engine_config_path(engine_id)

        try:
            if config_path.exists():
                config_path.unlink()
            return True
        except OSError:
            return False

    def exists(self, engine_id: str) -> bool:
        """Vérifie si une configuration existe pour un engine."""
        return self._get_engine_config_path(engine_id).exists()

    def list_engines(self) -> list[str]:
        """Retourne la liste des engines ayant une configuration sauvegardée."""
        try:
            if not self.engines_dir.exists():
                return []
            return [
                f.stem
                for f in self.engines_dir.glob("*.json")
                if f.is_file()
            ]
        except Exception:
            return []

    def get_config_dir(self) -> Path:
        """Retourne le chemin du répertoire de configuration."""
        return self.config_dir

    def get_engines_dir(self) -> Path:
        """Retourne le chemin du répertoire des configurations d'engines."""
        return self.engines_dir


# Instance globale singleton
_MANAGER: Optional[EngineConfigManager] = None


def get_config_manager(config_dir: Optional[str] = None) -> EngineConfigManager:
    """
    Retourne l'instance globale du gestionnaire de configuration.

    Args:
        config_dir: Répertoire de configuration (utilisé uniquement à la première initialisation)

    Returns:
        Instance du gestionnaire de configuration
    """
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = EngineConfigManager(config_dir)
    return _MANAGER


def reset_config_manager() -> None:
    """Réinitialise le gestionnaire de configuration (utile pour les tests)."""
    global _MANAGER
    _MANAGER = None
