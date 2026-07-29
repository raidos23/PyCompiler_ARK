"""Configuration loader for Python environment managers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


class VenvManagerConfig:
    """Load and expose VenvManager configuration from YAML."""

    def __init__(self, config_path: str | None = None) -> None:
        self._config_path = config_path or self._default_config_path()
        self._data = self._load_config()

    def _default_config_path(self) -> str:
        package_dir = Path(__file__).resolve().parents[2]
        return str(package_dir / "data" / "VenvManagers.yml")

    def _load_config(self) -> dict[str, Any]:
        try:
            with open(self._config_path, encoding="utf-8") as handle:
                loaded = yaml.safe_load(handle) or {}
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            pass
        return {}

    def get_manager(self, manager_name: str) -> dict[str, Any] | None:
        managers = self._data.get("managers", {})
        if isinstance(managers, dict):
            value = managers.get(manager_name)
            if isinstance(value, dict):
                return value
        return None

    def get_commands(self, manager_name: str) -> dict[str, list[str]]:
        manager = self.get_manager(manager_name)
        if not manager:
            return {}

        commands: dict[str, list[str]] = {}
        for key, value in manager.items():
            if isinstance(value, list) and all(
                isinstance(item, str) for item in value
            ):
                commands[key] = value
        return commands

    def get_available_managers(self) -> list[str]:
        managers = self._data.get("managers", {})
        if isinstance(managers, dict):
            return [name for name in managers.keys() if isinstance(name, str)]
        return []
