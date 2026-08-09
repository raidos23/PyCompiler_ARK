import json
import tempfile
import unittest
from pathlib import Path

from pycompiler_ark.Core.Venv_Manager.venvengine import VenvEngine


class TestVenvEngine(unittest.TestCase):
    def setUp(self):
        self.engine = VenvEngine()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_workspace_pref_read_write_clear(self):
        pref_data = {
            "manager": "pip",
            "venv_mode": "venv",
            "venv_path": "/tmp/test",
        }
        written = self.engine.write_workspace_pref(
            self.workspace_dir, pref_data
        )
        self.assertTrue(written)

        read_data = self.engine.read_workspace_pref(self.workspace_dir)
        self.assertEqual(read_data, pref_data)

        cleared = self.engine.clear_workspace_pref(self.workspace_dir)
        self.assertTrue(cleared)
        self.assertIsNone(self.engine.read_workspace_pref(self.workspace_dir))

    def test_validate_venv_strict_invalid_dir(self):
        ok, reason = self.engine.validate_venv_strict("/non/existent/path")
        self.assertFalse(ok)
        self.assertIn("Chemin invalide", reason)

    def test_compute_file_hash_and_requirements_marker(self):
        req_file = Path(self.workspace_dir) / "requirements.txt"
        req_file.write_text("requests==2.28.1\n", encoding="utf-8")

        file_hash = self.engine.compute_file_hash(str(req_file))
        self.assertIsNotNone(file_hash)

        marker_dir = Path(self.workspace_dir) / ".ark"
        updated = self.engine.update_requirements_marker(
            str(marker_dir), str(req_file)
        )
        self.assertTrue(updated)

        up_to_date = self.engine.is_requirements_up_to_date(
            str(marker_dir), str(req_file)
        )
        self.assertTrue(up_to_date)

    def test_prepare_manager_command(self):
        prog, args = self.engine.prepare_manager_command(
            "create_venv",
            manager_name="pip",
            kwargs={"venv_path": "/tmp/my_venv", "python": "python3"},
        )
        self.assertTrue(
            prog.endswith("python")
            or prog.endswith("python3")
            or prog.endswith("python.exe")
        )
        self.assertEqual(args, ["-m", "venv", "/tmp/my_venv"])

    def test_can_use_system_python(self):
        can_use, missing, has_source = self.engine.can_use_system_python(
            self.workspace_dir
        )
        self.assertTrue(can_use)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
