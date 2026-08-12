import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pycompiler_ark.Core.Venv_Manager.config import VenvManagerConfig
from pycompiler_ark.Core.Venv_Manager.Manager import VenvManager


class TestVenvManagerDetection(unittest.TestCase):
    def setUp(self):
        self.config = VenvManagerConfig()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_detect_poetry_workspace(self):
        pyproject = Path(self.workspace_dir) / "pyproject.toml"
        pyproject.write_text(
            "[tool.poetry]\nname = 'test'\n", encoding="utf-8"
        )

        manager = self.config.detect_manager_for_workspace(self.workspace_dir)
        self.assertEqual(manager, "poetry")

    def test_detect_pip_workspace(self):
        reqs = Path(self.workspace_dir) / "requirements.txt"
        reqs.write_text("requests==2.28.1\n", encoding="utf-8")

        manager = self.config.detect_manager_for_workspace(self.workspace_dir)
        self.assertEqual(manager, "pip")

    def test_detection_priority(self):
        pyproject = Path(self.workspace_dir) / "pyproject.toml"
        pyproject.write_text(
            "[tool.poetry]\nname = 'test'\n", encoding="utf-8"
        )

        reqs = Path(self.workspace_dir) / "requirements.txt"
        reqs.write_text("requests==2.28.1\n", encoding="utf-8")

        manager = self.config.detect_manager_for_workspace(self.workspace_dir)
        self.assertEqual(manager, "poetry")

    def test_fallback_to_default(self):
        manager = self.config.detect_manager_for_workspace(self.workspace_dir)
        self.assertIsNone(manager)

        venv_manager = VenvManager(MagicMock())
        resolved = venv_manager.resolve_workspace_manager(self.workspace_dir)
        self.assertEqual(resolved, self.config.get_default_manager())

    def test_user_preference_override(self):
        # Even with poetry detected, user pref in .ark/pref.json should override
        pyproject = Path(self.workspace_dir) / "pyproject.toml"
        pyproject.write_text(
            "[tool.poetry]\nname = 'test'\n", encoding="utf-8"
        )

        ark_dir = Path(self.workspace_dir) / ".ark"
        ark_dir.mkdir(parents=True, exist_ok=True)
        pref_file = ark_dir / "pref.json"
        fallback_manager = self.config.get_default_manager()
        pref_file.write_text(
            json.dumps({"manager": fallback_manager}), encoding="utf-8"
        )

        venv_manager = VenvManager(MagicMock())
        resolved = venv_manager.resolve_workspace_manager(self.workspace_dir)
        self.assertEqual(resolved, fallback_manager)

    def test_detect_environment_manager_uses_yaml_default_when_needed(self):
        venv_manager = VenvManager(MagicMock())
        resolved = venv_manager._detect_environment_manager(self.workspace_dir)
        self.assertEqual(resolved, self.config.get_default_manager())

    @patch(
        "pycompiler_ark.Core.Venv_Manager.Manager.os.path.isfile",
        return_value=True,
    )
    @patch("pycompiler_ark.Core.Venv_Manager.Manager.subprocess.run")
    def test_is_tool_installed_checks_importable_module_in_venv(
        self, mock_run, _mock_isfile
    ):
        venv_manager = VenvManager(MagicMock())
        venv_manager.python_path = MagicMock(
            return_value="/fake/venv/bin/python"
        )
        venv_manager.has_tool_binary = MagicMock(return_value=False)
        mock_run.return_value = SimpleNamespace(returncode=0)

        self.assertTrue(
            venv_manager.is_tool_installed("/fake/venv", "cx-Freeze")
        )
        venv_manager.has_tool_binary.assert_not_called()


if __name__ == "__main__":
    unittest.main()
