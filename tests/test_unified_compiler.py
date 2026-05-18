# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ague Samuel Amen

import pytest
import threading
import time
import sys
import os
from pathlib import Path
from Core.Compiler.engine_runner import run_engine_compile_streaming, BuildContext

def create_test_context(entry_point="main.py"):
    return BuildContext(
        project_name="TestProject",
        entry_point=entry_point,
        output_dir="dist/",
        exclude_patterns=[],
        data_mappings=[]
    )

def test_run_engine_compile_streaming_success(tmp_path):
    # Create a dummy python script to "compile"
    entry = tmp_path / "main.py"
    entry.write_text("import sys\nprint('Hello World')\nsys.stdout.flush()\nprint('Line 2')\nsys.stdout.flush()", encoding="utf-8")
    
    context = create_test_context("main.py")
    
    stdout_lines = []
    def on_stdout(line):
        stdout_lines.append(line)
        
    import Core.Compiler.engine_runner as er
    original_resolve = er.resolve_engine_command
    er.resolve_engine_command = lambda eid, ctx, cfg: (sys.executable, [str(entry)], {})
    
    try:
        result = run_engine_compile_streaming(
            workspace=tmp_path,
            engine_id="mock_engine",
            context=context,
            on_stdout=on_stdout
        )
        
        assert result["success"] is True
        assert result["return_code"] == 0
        assert "Hello World" in stdout_lines
        assert "Line 2" in stdout_lines
    finally:
        er.resolve_engine_command = original_resolve

def test_run_engine_compile_streaming_cancellation(tmp_path):
    entry = tmp_path / "long_run.py"
    # Script that runs for a while and ignores SIGTERM if possible (though python's sleep responds to it)
    entry.write_text("import time\nimport sys\nprint('Started')\nsys.stdout.flush()\ntry:\n    time.sleep(10)\nexcept BaseException:\n    pass\nprint('Finished')\nsys.stdout.flush()", encoding="utf-8")
    
    context = create_test_context("long_run.py")
    
    stdout_lines = []
    def on_stdout(line):
        stdout_lines.append(line)

    stop_requested = False
    def stop_signal():
        return stop_requested

    import Core.Compiler.engine_runner as er
    original_resolve = er.resolve_engine_command
    er.resolve_engine_command = lambda eid, ctx, cfg: (sys.executable, [str(entry)], {})

    try:
        # Run in a thread so we can cancel it
        result_container = {}
        def run():
            result_container["res"] = run_engine_compile_streaming(
                workspace=tmp_path,
                engine_id="mock_engine",
                context=context,
                on_stdout=on_stdout,
                stop_signal=stop_signal
            )

        t = threading.Thread(target=run)
        t.start()
        
        # Wait for it to start
        start_wait = time.time()
        while "Started" not in stdout_lines and time.time() - start_wait < 5:
            time.sleep(0.1)
            
        assert "Started" in stdout_lines
        
        # Cancel
        stop_requested = True
        t.join(timeout=10) # Give it plenty of time to cleanup
        
        assert not t.is_alive()
        # Finished should NOT be in stdout because kill_process_tree should have SIGKILLed it if SIGTERM failed
        assert "Finished" not in stdout_lines
        assert result_container["res"]["success"] is False
    finally:
        er.resolve_engine_command = original_resolve

def test_run_engine_compile_streaming_failure(tmp_path):
    entry = tmp_path / "fail.py"
    entry.write_text("import sys\nprint('Error line')\nsys.stdout.flush()\nsys.exit(1)", encoding="utf-8")
    
    context = create_test_context("fail.py")
    
    stdout_lines = []
    def on_stdout(line):
        stdout_lines.append(line)

    import Core.Compiler.engine_runner as er
    original_resolve = er.resolve_engine_command
    er.resolve_engine_command = lambda eid, ctx, cfg: (sys.executable, [str(entry)], {})

    try:
        result = run_engine_compile_streaming(
            workspace=tmp_path,
            engine_id="mock_engine",
            context=context,
            on_stdout=on_stdout
        )
        
        assert result["success"] is False
        assert result["return_code"] == 1
        assert "Error line" in stdout_lines
    finally:
        er.resolve_engine_command = original_resolve
