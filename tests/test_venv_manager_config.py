import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import MagicMock
from unittest.mock import patch

from pycompiler_ark.Core.Venv_Manager.config import VenvManagerConfig
from pycompiler_ark.Core.Venv_Manager.executor import (
    ExecutorFactory,
    PythonModuleExecutor,
    ExecutableExecutor,
    WorkspacePathExecutor,
)
from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager


class TestVenvManagerConfig(unittest.TestCase):
    def test_loads_default_commands_from_yaml(self):
        config = VenvManagerConfig()
        fallback_manager = config.get_default_manager()
        self.assertIn(fallback_manager, config.get_available_managers())

        executor = config.get_executor(fallback_manager)
        self.assertIsInstance(executor, dict)

        self.assertEqual(
            config.get_executor(fallback_manager, "get_venv_path").get("type"),
            "workspace_path",
        )

        commands = config.get_commands(fallback_manager)
        self.assertEqual(commands["create_venv"], ["{venv_path}"])
        self.assertEqual(
            config.get_executor(fallback_manager, "create_venv").get("module"),
            "venv",
        )
        self.assertEqual(commands["install"], ["install", "-r"])
        self.assertEqual(commands["add"], ["install"])
        self.assertEqual(commands["check"], ["check"])
        self.assertEqual(commands["get_venv_path"], ["{workspace}/.venv"])

    def test_loads_poetry_config_from_yaml(self):
        config = VenvManagerConfig()

        executor = config.get_executor("poetry")
        self.assertEqual(
            executor, {"type": "executable", "executable": "poetry"}
        )

        commands = config.get_commands("poetry")
        self.assertEqual(commands["create_venv"], ["env", "use", "{python}"])
        self.assertEqual(commands["get_venv_path"], ["env", "info", "-p"])
        self.assertEqual(commands["install"], ["install"])
        self.assertEqual(commands["add"], ["add"])
        self.assertEqual(commands["check"], ["check"])

    @patch("pycompiler_ark.Core.Venv_Manager.executor.subprocess.run")
    def test_resolve_command_venv_path_from_yaml(self, mock_run):
        config = VenvManagerConfig()
        mock_run.return_value = SimpleNamespace(
            returncode=0,
            stdout="/tmp/poetry-env\n",
        )

        with TemporaryDirectory() as tmp:
            resolved = config.resolve_venv_path("poetry", tmp)

        self.assertEqual(resolved, "/tmp/poetry-env")

    def test_resolve_workspace_path_venv_from_yaml(self):
        config = VenvManagerConfig()
        fallback_manager = config.get_default_manager()
        with TemporaryDirectory() as tmp:
            resolved = config.resolve_venv_path(fallback_manager, tmp)

        self.assertEqual(resolved, str((Path(tmp) / ".venv").resolve()))


class TestExecutorFactory(unittest.TestCase):
    def test_python_module_executor(self):
        cfg = {"type": "python_module", "module": "pip"}
        executor = ExecutorFactory.create(cfg, "/usr/bin/python3")
        self.assertIsInstance(executor, PythonModuleExecutor)

        program, args = executor.build_command(["install", "requests"])
        self.assertEqual(program, "/usr/bin/python3")
        self.assertEqual(args, ["-m", "pip", "install", "requests"])

    def test_executable_executor(self):
        cfg = {"type": "executable", "executable": "poetry"}
        executor = ExecutorFactory.create(cfg)
        self.assertIsInstance(executor, ExecutableExecutor)

        program, args = executor.build_command(["install"])
        self.assertEqual(program, "poetry")
        self.assertEqual(args, ["install"])

    def test_workspace_path_executor(self):
        cfg = {"type": "workspace_path"}
        executor = ExecutorFactory.create(cfg)
        self.assertIsInstance(executor, WorkspacePathExecutor)

        with TemporaryDirectory() as tmp:
            result = executor.run(
                ["{workspace}/.venv"],
                cwd=tmp,
                context={"workspace": tmp},
            )

        self.assertEqual(result, str((Path(tmp) / ".venv").resolve()))


class TestVenvManagerCommandPreparation(unittest.TestCase):
    def test_prepare_manager_command_pip_install(self):
        manager = VenvManager(MagicMock())
        manager._detected_manager = VenvManagerConfig().get_default_manager()
        program, args = manager._prepare_manager_command(
            "install",
            extra_args=["reqs.txt"],
            python_exe="/fake/python",
        )
        self.assertEqual(program, "/fake/python")
        self.assertEqual(args, ["-m", "pip", "install", "-r", "reqs.txt"])

    def test_prepare_manager_command_pip_create_venv(self):
        manager = VenvManager(MagicMock())
        manager._detected_manager = VenvManagerConfig().get_default_manager()
        program, args = manager._prepare_manager_command(
            "create_venv",
            kwargs={"venv_path": "/path/to/venv", "python": "/fake/python"},
            python_exe="/fake/python",
        )
        self.assertEqual(program, "/fake/python")
        self.assertEqual(args, ["-m", "venv", "/path/to/venv"])

    def test_prepare_manager_command_poetry_create_venv(self):
        manager = VenvManager(MagicMock())
        manager._detected_manager = "poetry"
        program, args = manager._prepare_manager_command(
            "create_venv",
            kwargs={"venv_path": "/path/to/venv", "python": "/fake/python"},
        )
        self.assertEqual(program, "poetry")
        self.assertEqual(args, ["env", "use", "/fake/python"])

    def test_prepare_manager_command_poetry_add(self):
        manager = VenvManager(MagicMock())
        manager._detected_manager = "poetry"
        program, args = manager._prepare_manager_command(
            "add",
            extra_args=["requests"],
        )
        self.assertEqual(program, "poetry")
        self.assertEqual(args, ["add", "requests"])


if __name__ == "__main__":
    unittest.main()
