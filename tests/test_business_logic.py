from pycompiler_ark.Core.Configs import normalize_ark_config, should_exclude_file


def test_normalize_ark_config_empty():
    """Test normalization of an empty config dict."""
    raw = {}
    normalized = normalize_ark_config(raw)

    assert "project" in normalized
    assert "workspace" in normalized
    assert "build" in normalized
    assert normalized["project"]["version"] == "1.0.0"


def test_normalize_ark_config_partial():
    """Test normalization with partial data."""
    raw = {"project": {"name": "TestApp"}, "build": {"engine": "nuitka"}}
    normalized = normalize_ark_config(raw)

    assert normalized["project"]["name"] == "TestApp"
    assert normalized["build"]["engine"] == "nuitka"
    assert normalized["project"]["version"] == "1.0.0"  # Default should be present


def test_should_exclude_file(tmp_path):
    """Test the should_exclude_file logic."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    file_log = workspace / "test.log"
    file_log.touch()

    file_temp = workspace / "temp" / "data.txt"
    file_temp.parent.mkdir()
    file_temp.touch()

    file_src = workspace / "src" / "main.py"
    file_src.parent.mkdir()
    file_src.touch()

    exclude = ["*.log", "temp/**"]

    assert should_exclude_file(str(file_log), str(workspace), exclude) is True
    assert should_exclude_file(str(file_temp), str(workspace), exclude) is True
    assert should_exclude_file(str(file_src), str(workspace), exclude) is False


from pycompiler_ark.Core.Locking import (
    ensure_workspace_layout,
    included_workspace_files,
    installed_distributions_snapshot,
    get_git_commit_hash,
    build_lock_payload,
)
from unittest.mock import patch, MagicMock


def test_get_git_commit_hash(tmp_path):
    """Test Git commit hash retrieval (mocked)."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="abc12345\n", returncode=0)
        commit = get_git_commit_hash(tmp_path)
        assert commit == "abc12345"
        mock_run.assert_called_once()


def test_build_lock_payload_with_git(tmp_path):
    """Test that build_lock_payload includes git commit and include list."""
    config = {
        "project": {"name": "Test", "version": "1.0.0", "entry": "main.py"},
        "build": {
            "engine": "nuitka",
            "include": ["requests", "rich"]
        },
    }
    with patch("Core.Locking.get_git_commit_hash") as mock_git:
        mock_git.return_value = "git_hash_123"
        payload = build_lock_payload(tmp_path, config, engine_id="nuitka")

        assert payload["project"]["git_commit"] == "git_hash_123"
        assert payload["engine"]["name"] == "nuitka"
        assert payload["build"]["include"] == ["requests", "rich"]


def test_check_internet_connection_success():
    """Test internet check success (mocked)."""
    from pycompiler_ark.Core.Compiler.utils import check_internet_connection

    with patch("socket.create_connection") as mock_conn:
        # Mock success on first IP
        mock_conn.return_value.__enter__.return_value = MagicMock()
        assert check_internet_connection() is True


def test_check_internet_connection_failure():
    """Test internet check failure (mocked)."""
    from pycompiler_ark.Core.Compiler.utils import check_internet_connection

    with patch("socket.create_connection", side_effect=Exception("Offline")):
        with patch("http.client.HTTPSConnection") as mock_http:
            mock_http.return_value.getresponse.side_effect = Exception("Offline")
            assert check_internet_connection(timeout=0.1, retries=0) is False


def test_ensure_workspace_layout(tmp_path):
    """Test that .ark subdirectories and .gitignore are created."""
    ensure_workspace_layout(tmp_path)
    assert (tmp_path / ".ark" / "lock").is_dir()
    assert (tmp_path / ".ark" / "cache").is_dir()
    assert (tmp_path / ".ark" / "build").is_dir()
    assert (tmp_path / ".ark" / "logs").is_dir()

    gitignore = tmp_path / ".ark" / ".gitignore"
    assert gitignore.is_file()
    content = gitignore.read_text()
    assert "pref.json" in content
    assert "cache/" in content
    assert "logs/" in content
    assert "build/" in content
    assert "lock/" not in content


def test_included_workspace_files(tmp_path):
    """Test workspace file discovery with exclusion."""
    workspace = tmp_path
    (workspace / "main.py").touch()
    (workspace / "data.txt").touch()
    (workspace / ".ark").mkdir()
    (workspace / ".ark" / "secret.txt").touch()
    (workspace / "node_modules").mkdir()
    (workspace / "node_modules" / "pkg.js").touch()

    # .ark/ is excluded by default in included_workspace_files (hardcoded skip)
    # node_modules/ we can pass in exclude patterns
    files = included_workspace_files(workspace, ["node_modules/**"])

    names = [f.name for f in files]
    assert "main.py" in names
    assert "data.txt" in names
    assert "secret.txt" not in names
    assert "pkg.js" not in names


def test_distributions_snapshot():
    """Test that we can get a snapshot of installed packages."""
    snapshot = installed_distributions_snapshot()
    assert isinstance(snapshot, dict)
    if snapshot:
        # pytest should be in the snapshot since we are running it
        assert "pytest" in snapshot or "PySide6" in snapshot
