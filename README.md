# PyCompiler ARK++

A Qt-based workshop to compile Python projects with a pre-compilation plugin pipeline (BCASL) and a multi-engine system.

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

<p align="center">
  <img src="./logo/logo2.png" alt="PyCompiler ARK++ logo" width="70%"/>
</p>

---

## Why it exists

Build Python apps with a predictable workflow, a configurable pre-compile pipeline, and the freedom to choose your build engine.

## Core capabilities

- **BCASL pre-compile pipeline**: validation, preparation, transformation before the build, with timeouts and safety controls.
- **Multi-engine builds**: switch between PyInstaller, Nuitka, and cx_Freeze without changing your workflow.
- **Extensible engines**: create your own engine and add it to ARK++ when needed.
- **Auto-detection for tricky dependencies**: engine-specific auto-args based on requirements or import scanning.
- **Workspace-first UI**: filter files, manage exclusions, and follow progress and logs in one place.
- **Venv-aware execution**: engines can use the project virtual environment automatically.
- **Standalone tools**: dedicated BCASL and Engines managers, plus CLI entry points and dry-run support.
- **Extensible SDKs**: create new engines and BCASL plugins with the provided SDKs.
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

## CLI shortcuts

```bash
python pycompiler_ark.py --help
python pycompiler_ark.py --version
python pycompiler_ark.py --info
```

### BCASL standalone (GUI)

```bash
python pycompiler_ark.py bcasl
python pycompiler_ark.py bcasl /path/to/workspace
```

### Engines standalone (GUI)

```bash
python pycompiler_ark.py engines
python pycompiler_ark.py engines /path/to/workspace
python pycompiler_ark.py engines --dry-run
```

### Standalone modules

```bash
python -m OnlyMod.BcaslOnlyMod --gui
python -m OnlyMod.BcaslOnlyMod --list-plugins
python -m OnlyMod.BcaslOnlyMod --run --workspace /path/to/workspace
python -m OnlyMod.EngineOnlyMod
python -m OnlyMod.EngineOnlyMod --list-engines
python -m OnlyMod.EngineOnlyMod --check-compat nuitka
python -m OnlyMod.EngineOnlyMod --engine nuitka -f script.py --dry-run
```

---

## Documentation

- [How to create an engine](docs/how_to_create_an_engine.md)
- [How to create a BC plugin](docs/how_to_create_a_bc_plugin.md)

---

## Configuration

- **`ARK_Main_Config.yml`**: inclusion and exclusion patterns, BCASL options.
- **`bcasl.yml`**: plugin enable/disable, order, and timeouts.

---

## Project layout

- `Core/` — main UI logic.
- `ENGINES/` — built-in engines.
- `EngineLoader/` — discovery and registry.
- `Plugins/` — BCASL plugins.
- `Plugins_SDK/` — plugin SDK.
- `bcasl/` — BCASL core.
- `OnlyMod/` — standalone tools (BCASL and Engines).
- `ui/` — Qt Designer UI.
- `languages/` — translations.
- `themes/` — QSS themes.

---

## Development

```bash
ruff check .
black --check .
mypy .
pytest
```

---

## License

Apache-2.0 (see [`LICENSE`](LICENSE)).
