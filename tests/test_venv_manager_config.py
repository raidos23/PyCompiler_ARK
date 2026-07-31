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
        self.assertEqual(commands["create_venv"], ["-m", "venv"])
        self.assertEqual(commands["install"], ["install", "-r"])
        self.assertEqual(commands["add"], ["install"])
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
        cfg = {"type": "executable", "executable": "uv"}
        executor = ExecutorFactory.create(cfg)
        self.assertIsInstance(executor, ExecutableExecutor)

        program, args = executor.build_command(["pip", "install", "requests"])
        self.assertEqual(program, "uv")
        self.assertEqual(args, ["pip", "install", "requests"])


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


if __name__ == "__main__":
    unittest.main()
