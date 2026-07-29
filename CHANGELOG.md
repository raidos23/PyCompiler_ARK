# Changelog

## Upcoming

### Added
- Added a dedicated configuration layer for the Venv Manager through `pycompiler_ark/Core/Venv_Manager/config.py`.
- Added `pycompiler_ark/data/VenvManagers.yml` as the configuration source for Python environment managers.
- Added regression coverage for Venv Manager configuration loading.

### Changed
- Refactored the Venv Manager to consume YAML-backed configuration instead of hardcoded command mappings.
- Improved cross-platform path handling in CLI discovery tests to avoid Windows short-path issues.
- Updated the project documentation and README to reflect the current Python support baseline (`3.11+`).

### Fixed
- Fixed test reliability for plugin-root discovery across different Windows path formats.

### Documentation
- Expanded and clarified the project documentation for the current architecture and build workflow.

### Notes
- The current package version remains `1.0.1` in `pyproject.toml`.
- This section is intended as a pre-release summary pending the next version bump.
