"""Configuration loader for Python environment managers."""

from __future__ import annotations

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
        """Return complete manager configuration."""
        managers = self._data.get("managers", {})

        if isinstance(managers, dict):
            manager = managers.get(manager_name)

            if isinstance(manager, dict):
                return manager

        return None

    def get_commands(self, manager_name: str) -> dict[str, list[str]]:
        """Return manager commands with their arguments."""
        manager = self.get_manager(manager_name)

        if not manager:
            return {}

        commands = manager.get("commands", {})

        if not isinstance(commands, dict):
            return {}

        result: dict[str, list[str]] = {}

        for name, command in commands.items():
            if isinstance(command, list) and all(
                isinstance(item, str) for item in command
            ):
                result[name] = command
            elif isinstance(command, dict):
                args = command.get("args", [])
                if isinstance(args, list) and all(
                    isinstance(item, str) for item in args
                ):
                    result[name] = args

        return result

    def get_executor(self, manager_name: str) -> dict[str, Any]:
        """Return executor configuration of a manager."""
        manager = self.get_manager(manager_name)

        if not manager:
            return {}

        executor = manager.get("executor", {})

        if isinstance(executor, dict):
            return executor

        return {}

    def get_command(
        self,
        manager_name: str,
        command_name: str,
    ) -> list[str]:
        """Return only command arguments."""
        commands = self.get_commands(manager_name)
        return commands.get(command_name, [])

    def get_available_managers(self) -> list[str]:
        """Return available manager names."""
        managers = self._data.get("managers", {})

        if isinstance(managers, dict):
            return [name for name in managers.keys() if isinstance(name, str)]

        return []
