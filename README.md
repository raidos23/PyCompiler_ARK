<p align="center">
  <img src="./images/logo2.png" alt="PyCompiler ARK logo" width="100%"/>
</p>

# **PyCompiler ARK**

A Python project build workshop with a Qt GUI, a headless-friendly CLI, a BCASL pre-compilation pipeline, and a multi-engine system.

---

## Why this app?

Build Python apps with a predictable workflow, a configurable pre-compile pipeline, and the freedom to choose your build engine.

## Core capabilities

- **BCASL pre-compile pipeline**: validation, preparation, transformation before the build, with timeouts and safety controls.
- **Unified EngineRunner architecture**: a single source of truth for both CLI and GUI compilation, ensuring identical build results across all interfaces.
- **BuildContext-driven builds**: engines receive a normalized project context, abstracting away the source of configuration (YAML vs. Lock files).
- **Multi-engine support**: switch between PyInstaller, Nuitka, and cx_Freeze seamlessly.
- **Extensible SDKs**: create new engines and BCASL plugins using simplified, consolidated APIs.
- **Auto-detection for tricky dependencies**: engine-specific auto-args based on requirements or import scanning.
- **Workspace-first UI**: filter files, manage exclusions, and follow progress and logs in one place.
- **Venv-aware execution**: engines can use the project virtual environment automatically.
- **Theme-aware dynamic UI**: 100% dynamic integration using QPalette and themed SVGs.

---

## Quick Start

### Install

```bash
git clone https://github.com/raidos23/PyCompiler_ARK.git
cd PyCompiler_ARK
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

### Launch

```bash
python pycompiler_ark.py
# or
python -m pycompiler_ark
```

*Note: The application features a centered and auto-scaled splash screen for a professional startup experience.*

---

## How it works

1. Select a workspace.
2. Add or filter files to compile.
3. Configure an engine (PyInstaller, Nuitka, cx_Freeze).
4. Build and follow logs and progress.

### BCASL pipeline (quick view)

```text
Workspace
  |
  |-- Load bcasl.yml
  |-- Discover plugins (Plugins/)
  |-- Enable / order / priorities
  |-- Sandboxed execution (timeouts,  
  |   optional parallelism)
  |  
  v
Compilation (PyInstaller / Nuitka / cx_Freeze)
```

---

## CLI Usage

The ARK CLI provides a structured set of commands for workspace management, building, and developer tasks.

### Core Commands

```bash
# Workspace Initialization
python3 pycompiler_ark.py init --entry src/main.py [--icon icon.ico] [--with-venv]

# Building
python3 pycompiler_ark.py build                      # Build using ark.yml engine
python3 pycompiler_ark.py build --engine nuitka      # Override engine
python3 pycompiler_ark.py build --lock latest.lock   # Rebuild from lock file

# Execution
python3 pycompiler_ark.py run bcasl                  # Execute BCASL pipeline
python3 pycompiler_ark.py run bcasl --timeout 30     # With custom timeout

# GUI
python3 pycompiler_ark.py gui                        # Launch modern IDE-like GUI
python3 pycompiler_ark.py gui --legacy               # Launch classic GUI
```

### Developer Commands

```bash
# Discovery
python3 pycompiler_ark.py list engines               # List available engines
python3 pycompiler_ark.py list plugins               # List available BCASL plugins

# Configuration (User Paths)
python3 pycompiler_ark.py set user-engine-dir /path  # Set custom engine directory
python3 pycompiler_ark.py get user-engine-dir        # Retrieve path

# Scaffolding
python3 pycompiler_ark.py scaffold engine demo       # Create a new engine template
python3 pycompiler_ark.py scaffold plugin-bcasl demo # Create a new BCASL plugin template
```

### JSON Output
For CI/CD and scripting, key commands support the `--json` flag to return machine-readable results:
```bash
python3 pycompiler_ark.py build --json
python3 pycompiler_ark.py init --entry main.py --json
```

---

## How it works

- [Contributing guide](docs/contributing.md)
- [How to create an engine](docs/how_to_create_an_engine.md)
- [How to create a BC plugin](docs/how_to_create_a_bc_plugin.md)

---

## Configuration

- **`ark.yml`**: inclusion/exclusion patterns, build entrypoint, and a few workspace-level defaults consumed by BCASL bootstrap.
- **`bcasl.yml`**: plugin enable/disable, order, and timeouts.

---

## Project layout

- `Ui/Cli/`: Command-line interface implementation and entry points.
- `Core/`: Core business logic for compilation, workspace management, and settings.
- `Core/Compiler/`: The **EngineRunner** and **MainProcess** (single source of truth for builds).
- `engines/`: Built-in compilation engines (PyInstaller, Nuitka, cx_Freeze).
- `bcasl/`: BCASL core engine and plugin loader.
- `Plugins/`: Pre-compile pipeline plugins.
- `engine_sdk/` & `Plugins_SDK/`: Developer kits for extending ARK.
- `Ui/Forms/`: Qt Designer `.ui` files for the IDE-like and Classic layouts.
- `languages/` & `themes/`: Application-wide translations and QSS themes.

---

## Development

```bash
# Linting and testing
ruff check .
pytest -q tests

# Help discovery
python3 pycompiler_ark.py --help
python3 pycompiler_ark.py run bcasl --help
python3 pycompiler_ark.py build --help
```

Quality status:

- all documented quality-plan phases are closed
- the active backlog is considered closed under the current quality freeze

---

## License

Apache-2.0 (see [`LICENSE`](LICENSE)).
