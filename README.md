<p align="center">
  <img src="https://raw.githubusercontent.com/raidos23/PyCompiler_ARK/main/pycompiler_ark/images/logo2.png" alt="PyCompiler ARK logo" width="100%"/>
</p>

# **PyCompiler ARK**

A Python project build workshop with a Qt GUI, a headless-friendly CLI, a pre-compilation pipeline, and a multi-engine system.

---

## Why this app?

Build Python apps with a predictable workflow, a configurable pre-compile pipeline, and the freedom to choose your build engine.

## Core capabilities

- **BCASL pre-compile pipeline**: validation, preparation, transformation before the build, with safety controls.
- **Unified EngineRunner architecture**: a single source of truth for both CLI and GUI compilation, ensuring identical build results across all interfaces.
- **BuildContext-driven builds**: engines receive a normalized project context, abstracting away the source of configuration (YAML vs. Lock files).
- **Multi-engine support**: switch between PyInstaller, Nuitka, and cx_Freeze seamlessly.
- **Extensible SDKs**: create new engines and BCASL plugins using simplified, consolidated APIs.
- **Zero-Config auto-mapping for 80+ libraries**: automatic import detection via requirements covers major AI, modern web, data science, and automation stacks, with engine-specific arguments applied without manual tuning.
- **Simplified build inclusions**: `build.include` forces package bundling and ARK translates it automatically per engine.
- **Workspace-first UI**: filter files, manage exclusions, and follow progress and logs in one place.
- **Venv-aware execution**: engines can use the project virtual environment automatically.
- **Theme-aware dynamic UI**: 100% dynamic integration using QPalette and themed SVGs.

---

## Quick Start

### Install

```bash
git clone https://github.com/raidos23/PyCompiler_ARK.git
cd PyCompiler_ARK
pip install -e .
```

### Launch Gui

```bash
pycompiler_ark gui
# or
python -m pycompiler_ark gui
```
---

## CLI Usage

The PyCompiler ARK CLI provides a structured set of commands for workspace management, building, and developer tasks.

### Core Commands

```bash
# Workspace Initialization
python3 -m pycompiler_ark init --entry src/main.py [--icon icon.ico] [--with-venv]

# Building
python3 -m pycompiler_ark build                      # Build using ark.yml engine
python3 -m pycompiler_ark build --engine nuitka      # Override engine
python3 -m pycompiler_ark build --lock latest         # Rebuild from the latest lock file

# Execution
python3 -m pycompiler_ark run bcasl                  # Execute BCASL pipeline
python3 -m pycompiler_ark run bcasl --list-plugins   # List active plugins

# GUI
python3 -m pycompiler_ark gui                        # Launch modern IDE-like GUI
python3 -m pycompiler_ark gui --legacy               # Launch classic GUI
```

### Developer Commands

```bash
# Discovery
python3 -m pycompiler_ark list engines               # List available engines
python3 -m pycompiler_ark list plugins               # List available BCASL plugins

# Configuration (User Paths)
python3 -m pycompiler_ark set user-engine-dir /path  # Set custom engine directory
python3 -m pycompiler_ark get user-engine-dir        # Retrieve path

# Scaffolding
python3 -m pycompiler_ark scaffold engine demo       # Create a new engine template
python3 -m pycompiler_ark scaffold plugin-bcasl demo # Create a new BCASL plugin template
```

### JSON Output

For CI/CD and scripting, key commands support the `--json` flag to return machine-readable results:

```bash
python3 -m pycompiler_ark build --json
python3 -m pycompiler_ark init --entry main.py --json
```

---

## Documentation

- [Contributing guide](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/contributing.md)
- [How to create an engine](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/how_to_create_an_engine.md)
- [How to create a BC plugin](https://github.com/raidos23/PyCompiler_ARK/blob/main/docs/how_to_create_a_bc_plugin.md)

---

## Configuration

- **`ark.yml`**: Project metadata, build entrypoint, build include/exclude rules, and global BCASL activation.
- **`bcasl.yml`**: Detailed BCASL pipeline configuration, plugin settings, and execution order.

---

## License

Apache-2.0 (see [`LICENSE`](https://github.com/raidos23/PyCompiler_ARK/blob/main/LICENSE)).
