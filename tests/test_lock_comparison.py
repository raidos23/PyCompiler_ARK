import pytest
from Core.Locking import compare_lock_payloads

def test_compare_lock_payloads_functional_equivalence():
    """Test that comparison ignores build_id but detects critical changes."""
    lock_a = {
        "build_id": "ARK_2026_05_31_001",
        "project": {"name": "App", "version": "1.0.0", "entry": "main.py"},
        "build": {"output": "dist/", "exclude": [], "data": []},
        "engine": {"name": "nuitka", "version": "2.0", "config": {"standalone": True}},
        "platform": {"os": "linux", "python_version": "3.12"},
        "dependencies": {"requests": "2.31.0"}
    }
    
    # Same functional metadata, different build_id
    lock_b = dict(lock_a)
    lock_b["build_id"] = "ARK_2026_05_31_002"
    
    assert compare_lock_payloads(lock_a, lock_b) is True
    
    # Different dependency version
    lock_c = dict(lock_a)
    lock_c["dependencies"] = {"requests": "2.32.0"}
    assert compare_lock_payloads(lock_a, lock_c) is False
    
    # Different engine config
    lock_d = dict(lock_a)
    lock_d["engine"] = dict(lock_a["engine"])
    lock_d["engine"]["config"] = {"standalone": False}
    assert compare_lock_payloads(lock_a, lock_d) is False

def test_compare_lock_payloads_with_diff():
    """Test that we can get a list of differences."""
    lock_a = {
        "project": {"name": "App", "version": "1.0.0", "entry": "main.py"},
        "dependencies": {"numpy": "1.24.0"}
    }
    lock_b = {
        "project": {"name": "App", "version": "1.1.0", "entry": "main.py"},
        "dependencies": {"numpy": "1.25.0"}
    }
    
    ok, diffs = compare_lock_payloads(lock_a, lock_b, return_diff=True)
    assert ok is False
    assert any("project.version: 1.0.0 -> 1.1.0" in d for d in diffs)
    assert any("dependencies.numpy: 1.24.0 -> 1.25.0" in d for d in diffs)
