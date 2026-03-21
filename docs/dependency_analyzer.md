# Dependency Analyzer

PyCompiler ARK includes an internal dependency analyzer used by the GUI dependency suggestion flow.

Main entrypoint:

- `Core/deps_analyser/analyser.py`
- GUI action: `suggest_missing_dependencies()`

## Goal

The analyzer scans Python files in the current workspace, extracts imported modules, classifies them, and suggests third-party dependencies that may be missing from the selected environment.

## Classification

Each detected import is classified into one of four categories:

- `stdlib`: Python standard library or built-in modules.
- `internal`: modules that belong to the current workspace.
- `third_party`: modules resolved from installed packages such as `site-packages` or `dist-packages`.
- `unknown`: modules that cannot be resolved safely.

## Main heuristics

The analyzer uses several heuristics to improve signal quality:

- Path normalization based on `realpath()` and normalized case.
- Workspace source root discovery for common layouts:
  - `src/`
  - `lib/`
  - `python/`
  - `lib/python/`
  - `src/python/`
- `pyproject.toml` parsing for:
  - `[project]`
  - `[tool.poetry]`
  - Poetry package include/from declarations
  - setuptools package discovery hints
- `setup.cfg` parsing for:
  - `[metadata] name`
  - `package_dir`
  - `options.packages.find.where`
- Package-chain inspection through `__init__.py` files.
- Relative import resolution using the file location plus detected workspace roots.
- Dynamic import detection for:
  - `__import__(...)`
  - `importlib.import_module(...)`

## File filtering

Before parsing, the analyzer excludes files that are very likely irrelevant or harmful to scan:

- virtual environments: `venv`, `.venv`, `env`, `.env`
- caches: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- automation environments: `.tox`, `.nox`
- installed package trees: `site-packages`, `dist-packages`
- build artifacts: `build`, `dist`
- dependency folders: `node_modules`
- package metadata: `*.egg-info`, `*.dist-info`

## Testable import parser

The import extraction logic is intentionally exposed through helpers so it can be tested independently from the GUI:

- `_extract_imported_modules_from_source()`
- `_extract_imported_modules_from_file()`

These helpers are used by `suggest_missing_dependencies()` instead of duplicating parsing logic in the GUI flow.

## Limits

The analyzer is heuristic-based. It is intentionally conservative and may still miss or misclassify some cases:

- imports built dynamically from variables or string concatenation
- optional imports guarded by platform/runtime checks
- namespace packages without a classic `__init__.py` chain
- project-specific packaging layouts not declared in `pyproject.toml` or `setup.cfg`
- distribution-name vs import-name mismatches not captured by the current logic

## Practical guidance

- Prefer declaring project structure clearly in `pyproject.toml` or `setup.cfg`.
- Keep source roots conventional when possible.
- Add tests when changing classification heuristics.
- Treat analyzer output as a guided suggestion, not as a strict package lock source.
