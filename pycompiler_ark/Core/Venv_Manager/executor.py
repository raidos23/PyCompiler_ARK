"""Command execution resolvers for Venv Managers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseExecutor(ABC):
    """Base class for command executors."""

    def __init__(
        self,
        config: dict[str, Any],
        python_interpreter: str | None = None,
    ) -> None:
        self.config = config
        self.python_interpreter = python_interpreter

    @abstractmethod
    def build_command(
        self,
        args: list[str],
    ) -> tuple[str, list[str]]:
        """Build executable program and arguments."""


class PythonModuleExecutor(BaseExecutor):
    """Executor for Python modules (python -m module)."""

    def build_command(
        self,
        args: list[str],
    ) -> tuple[str, list[str]]:
        module = self.config.get("module")

        if not module:
            raise ValueError("Missing Python module in executor config")

        if not self.python_interpreter:
            raise ValueError("Missing Python interpreter")

        return (
            self.python_interpreter,
            [
                "-m",
                module,
                *args,
            ],
        )


class ExecutableExecutor(BaseExecutor):
    """Executor for external executables."""

    def build_command(
        self,
        args: list[str],
    ) -> tuple[str, list[str]]:
        executable = self.config.get("executable")

        if not executable:
            raise ValueError("Missing executable in executor config")

        return (
            executable,
            args,
        )


class ExecutorFactory:
    """Create executor instances from configuration."""

    @staticmethod
    def create(
        executor_config: dict[str, Any],
        python_interpreter: str | None = None,
    ) -> BaseExecutor:
        executor_type = executor_config.get("type")

        if executor_type == "python_module":
            return PythonModuleExecutor(
                executor_config,
                python_interpreter,
            )

        if executor_type == "executable":
            return ExecutableExecutor(
                executor_config,
                python_interpreter,
            )

        raise ValueError(f"Unsupported executor type: {executor_type}")
