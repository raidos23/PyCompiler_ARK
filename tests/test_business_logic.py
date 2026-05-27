
import pytest
from pathlib import Path
from Core.Configs import (
    normalize_ark_config,
    should_exclude_file,
    DEFAULT_EXCLUDE_PATTERNS
)

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
    raw = {
        "project": {"name": "TestApp"},
        "build": {"engine": "nuitka"}
    }
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

from Core.Locking import (
    ensure_workspace_layout,
    included_workspace_files,
    installed_distributions_snapshot
)

def test_ensure_workspace_layout(tmp_path):
    """Test that .ark subdirectories are created."""
    ensure_workspace_layout(tmp_path)
    assert (tmp_path / ".ark" / "lock").is_dir()
    assert (tmp_path / ".ark" / "cache").is_dir()
    assert (tmp_path / ".ark" / "build").is_dir()
    assert (tmp_path / ".ark" / "logs").is_dir()

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
