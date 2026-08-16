# Changelog

## Version 1.1.0

### Added
- Added configurable virtualenv manager support through YAML-based configuration.
- Added scaffold templates for engine and BCASL project generation.

### Changed
- Improved dependency analysis and module exclusion handling.
- Improved CLI/GUI consistency and strengthened workspace validation.
- Unified the application around a single GUI experience.
- Simplified the `gui` CLI command so it always launches the only supported GUI.

### Removed
- Removed the `pycompiler_ark gui --legacy` entrypoint.
- Removed the legacy/classic GUI variant from the CLI launcher.

### Documentation
- Expanded and clarified the documentation for the current architecture and build workflow.
