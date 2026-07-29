import unittest

from pycompiler_ark.Core.Venv_Manager.config import VenvManagerConfig


class TestVenvManagerConfig(unittest.TestCase):
    def test_loads_default_commands_from_yaml(self):
        config = VenvManagerConfig()

        commands = config.get_commands("pip")

        self.assertEqual(commands["create_venv"], ["python", "-m", "venv"])
        self.assertEqual(commands["install"], ["pip", "install", "-r"])
        self.assertEqual(commands["add"], ["pip", "install"])


if __name__ == "__main__":
    unittest.main()
