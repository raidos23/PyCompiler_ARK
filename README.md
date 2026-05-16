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
- **Multi-engine builds**: switch between PyInstaller, Nuitka, and cx_Freeze without changing your workflow.
- **Extensible engines**: create your own engine and add it to ARK++ when needed.
- **Auto-detection for tricky dependencies**: engine-specific auto-args based on requirements or import scanning.
- **Workspace-first UI**: filter files, manage exclusions, and follow progress and logs in one place.
- **Venv-aware execution**: engines can use the project virtual environment automatically.
- **Structured CLI**: explicit `gui`, `engine`, `workspace`, `doctor`, and `scaffold` commands, with JSON output on key headless paths.
- **Standalone tools**: dedicated BCASL and Engines managers, plus CLI entry points and dry-run support.
- **Extensible SDKs**: create new engines and BCASL plugins with the provided SDKs.
- **Theme-aware dynamic colors and SVG icons**: 100% dynamic UI integration using QPalette and themed SVGs.
- **Customizable**: theming and translations out of the box.

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
python pycompiler_ark.py init --entry src/main.py [--icon icon.ico] [--with-venv]

# Building
python pycompiler_ark.py build                      # Build using ark.yml engine
python pycompiler_ark.py build --engine nuitka      # Override engine
python pycompiler_ark.py build --lock latest.lock   # Rebuild from lock file

# Execution
python pycompiler_ark.py run bcasl                  # Execute BCASL pipeline
python pycompiler_ark.py run bcasl --timeout 30     # With custom timeout

# GUI
python pycompiler_ark.py gui                        # Launch modern IDE-like GUI
python pycompiler_ark.py gui --legacy               # Launch classic GUI
```

### Developer Commands

```bash
# Discovery
python pycompiler_ark.py list engines               # List available engines
python pycompiler_ark.py list plugins               # List available BCASL plugins

# Configuration (User Paths)
python pycompiler_ark.py set user-engine-dir /path  # Set custom engine directory
python pycompiler_ark.py get user-engine-dir        # Retrieve path

# Scaffolding
python pycompiler_ark.py scaffold engine demo       # Create a new engine template
python pycompiler_ark.py scaffold plugin-bcasl demo # Create a new BCASL plugin template
```

### JSON Output
For CI/CD and scripting, key commands support the `--json` flag to return machine-readable results:
```bash
python pycompiler_ark.py build --json
python pycompiler_ark.py init --entry main.py --json
```

---

## How it works

- [Changelog](CHANGELOG.md)
- [Release process](docs/release_process.md)
- [Release notes v1.0.0](docs/releases/v1.0.0.md)
- [Architecture overview](docs/architecture.md)
- [Contributing guide](docs/contributing.md)
- [CI/CD with ARK CLI](docs/ci_cd_ark_cli.md)
- [Dependency analyzer](docs/dependency_analyzer.md)
- [How to create an engine](docs/how_to_create_an_engine.md)
- [How to create a BC plugin](docs/how_to_create_a_bc_plugin.md)
- [Dedicated interactive CLI (`--cli`)](docs/dedicated_cli.md)
- [IDE-like main GUI (`gui main --ide`)](docs/ide_like_gui.md)

---

## Configuration

- **`ark.yml`**: inclusion/exclusion patterns, build entrypoint, and a few workspace-level defaults consumed by BCASL bootstrap.
- **`bcasl.yml`**: plugin enable/disable, order, and timeouts.

---

## Project layout

- `Ui/Cli/` — active ARK CLI entrypoints, runtime helpers, discovery, and command tree.
- `Core/` — main UI logic.
- `Core/IdeLikeGui/` — wiring layer for the IDE-like main GUI.
- `ENGINES/` — built-in engines.
- `EngineLoader/` — discovery and registry.
- `Plugins/` — BCASL plugins.
- `Plugins_SDK/` — plugin SDK.
- `bcasl/` — BCASL core.
- `OnlyMod/` — standalone tools (BCASL and Engines).
- `Ui/Forms/` — Qt Designer UI forms.
  - `Ui/Forms/classic_main_window.ui` — default main layout
  - `Ui/Forms/ide_main_window.ui` — IDE-like layout
- `languages/` — translations.
- `themes/` — QSS themes.

---

## Development

```bash
ruff check .
black --check .
pytest -q tests
python -m py_compile pycompiler_ark.py
python -m pycompiler_ark --help
python -m pycompiler_ark workspace inspect . --json
python -m pycompiler_ark engine list --json
python -m pycompiler_ark init /path/to/workspace --json
python -m pycompiler_ark cfg-auto /path/to/workspace --json
python -m pycompiler_ark check /path/to/workspace --json
```

Quality status:

- all documented quality-plan phases are closed
- the active backlog is considered closed under the current quality freeze

---

## License

Apache-2.0 (see [`LICENSE`](LICENSE)).
