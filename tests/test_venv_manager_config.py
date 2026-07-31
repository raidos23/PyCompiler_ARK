import unittest
from unittest.mock import MagicMock

from pycompiler_ark.Core.Venv_Manager.config import VenvManagerConfig
from pycompiler_ark.Core.Venv_Manager.executor import (
    ExecutorFactory,
    PythonModuleExecutor,
    ExecutableExecutor,
)
from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager


class TestVenvManagerConfig(unittest.TestCase):
    def test_loads_default_commands_from_yaml(self):
        config = VenvManagerConfig()

        executor = config.get_executor("pip")
        self.assertEqual(executor, {"type": "python_module", "module": "pip"})

        commands = config.get_commands("pip")
        self.assertEqual(commands["create_venv"], ["{venv_path}"])
        self.assertEqual(
            config.get_executor("pip", "create_venv"),
            {"type": "python_module", "module": "venv"},
        )
        self.assertEqual(commands["install"], ["install", "-r"])
        self.assertEqual(commands["add"], ["install"])
        self.assertEqual(commands["check"], ["check"])

    def test_loads_poetry_config_from_yaml(self):
        config = VenvManagerConfig()

        executor = config.get_executor("poetry")
        self.assertEqual(
            executor, {"type": "executable", "executable": "poetry"}
        )

        commands = config.get_commands("poetry")
        self.assertEqual(commands["create_venv"], ["env", "use", "{python}"])
        self.assertEqual(commands["install"], ["install"])
        self.assertEqual(commands["add"], ["add"])
        self.assertEqual(commands["check"], ["check"])


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


class TestVenvManagerCommandPreparation(unittest.TestCase):
    def test_prepare_manager_command_pip_install(self):
        manager = VenvManager(MagicMock())
        program, args = manager._prepare_manager_command(
            "install",
            extra_args=["reqs.txt"],
            python_exe="/fake/python",
        )
        self.assertEqual(program, "/fake/python")
        self.assertEqual(args, ["-m", "pip", "install", "-r", "reqs.txt"])

    def test_prepare_manager_command_pip_create_venv(self):
        manager = VenvManager(MagicMock())
        manager._detected_manager = "pip"
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
