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

    def get_executor(
        self, manager_name: str, action: str | None = None
    ) -> dict[str, Any]:
        """Return executor configuration of a manager (action-specific or general)."""
        manager = self.get_manager(manager_name)

        if not manager:
            return {}

        if action:
            executors = manager.get("executors", {})
            if isinstance(executors, dict) and action in executors:
                act_exec = executors[action]
                if isinstance(act_exec, dict):
                    return act_exec

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

    def get_default_manager(self) -> str:
        """Return default fallback manager name from configuration."""
        available = self.get_available_managers()
        if not available:
            return "pip"

        rules = [
            (name, self.get_detection_rules(name).get("priority", 0))
            for name in available
        ]
        rules.sort(key=lambda x: x[1])
        return rules[0][0]

    def get_detection_rules(self, manager_name: str) -> dict[str, Any]:
        """Return detection rules of a manager."""
        manager = self.get_manager(manager_name)

        if not manager or not isinstance(manager.get("detection"), dict):
            return {"priority": 0, "files": [], "patterns": {}}

        detection = manager["detection"]
        priority = detection.get("priority", 0)
        if not isinstance(priority, int):
            priority = 0

        files = detection.get("files", [])
        if not isinstance(files, list):
            files = []
        files = [f for f in files if isinstance(f, str)]

        patterns = detection.get("patterns", {})
        if not isinstance(patterns, dict):
            patterns = {}
        patterns = {
            k: str(v) for k, v in patterns.items() if isinstance(k, str)
        }

        return {
            "priority": priority,
            "files": files,
            "patterns": patterns,
        }

    def detect_manager_for_workspace(self, workspace_dir: str) -> str | None:
        """Detect environment manager for a workspace directory based on detection rules."""
        try:
            workspace_path = Path(workspace_dir)
            if not workspace_path.is_dir():
                return None
        except Exception:
            return None

        available = self.get_available_managers()
        manager_rules = []

        for name in available:
            rules = self.get_detection_rules(name)
            if rules["files"]:
                manager_rules.append((name, rules))

        manager_rules.sort(key=lambda item: item[1]["priority"], reverse=True)

        for name, rules in manager_rules:
            files = rules["files"]
            patterns = rules["patterns"]

            for filename in files:
                target_file = workspace_path / filename
                if target_file.is_file():
                    required_pattern = patterns.get(filename)
                    if required_pattern:
                        try:
                            content = target_file.read_text(
                                encoding="utf-8", errors="ignore"
                            )
                            if required_pattern in content:
                                return name
                        except Exception:
                            continue
                    else:
                        return name

        return None
