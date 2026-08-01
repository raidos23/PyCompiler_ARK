"""Command execution resolvers for Venv Managers."""

from __future__ import annotations

from abc import ABC, abstractmethod
import os
import subprocess
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

    @abstractmethod
    def run(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        context: dict[str, str] | None = None,
    ) -> str | None:
        """Execute or resolve the configured strategy and return a result."""


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

    def run(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        context: dict[str, str] | None = None,
    ) -> str | None:
        program, argv = self.build_command(args)
        completed = subprocess.run(
            [program, *argv],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return None
        output = completed.stdout.strip().splitlines()
        if not output:
            return None
        return output[-1].strip() or None


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

    def run(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        context: dict[str, str] | None = None,
    ) -> str | None:
        program, argv = self.build_command(args)
        completed = subprocess.run(
            [program, *argv],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return None
        output = completed.stdout.strip().splitlines()
        if not output:
            return None
        return output[-1].strip() or None


class WorkspacePathExecutor(BaseExecutor):
    """Executor that resolves a workspace-relative path template."""

    def build_command(
        self,
        args: list[str],
    ) -> tuple[str, list[str]]:
        raise NotImplementedError(
            "WorkspacePathExecutor does not build subprocess commands"
        )

    def run(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        context: dict[str, str] | None = None,
    ) -> str | None:
        if not args:
            return None
        template = args[0]
        if not isinstance(template, str) or not template.strip():
            return None
        base = dict(context or {})
        workspace = base.get("workspace", cwd or "")
        if not workspace:
            return None
        base["workspace"] = workspace
        base["cwd"] = base.get("cwd", workspace)
        resolved = template.format(**base)
        if not os.path.isabs(resolved):
            resolved = os.path.abspath(os.path.join(workspace, resolved))
        return resolved


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

        if executor_type == "workspace_path":
            return WorkspacePathExecutor(
                executor_config,
                python_interpreter,
            )

        raise ValueError(f"Unsupported executor type: {executor_type}")
