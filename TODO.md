# Integration of Robust Compilation Launching from "Only Mod" Engines

## Tasks
- [ ] Modify `start_compilation_process` in `Core/Compiler/mainprocess.py` to use subprocess.Popen instead of QProcess
- [ ] Implement select-based real-time stdout/stderr reading
- [ ] Update cancellation logic for better process termination
- [ ] Ensure remaining output is read after process completion
- [ ] Test compilation functionality
- [ ] Verify real-time output display
- [ ] Ensure cancellation works properly

## Status
- Plan approved by user
- Implementation in progress
