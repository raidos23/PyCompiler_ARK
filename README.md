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
python pycompiler_ark.py --cli
python pycompiler_ark.py gui main --ide
python pycompiler_ark.py gui main --classic --no-splash
python pycompiler_ark.py gui bcasl /path/to/workspace
python pycompiler_ark.py gui engines /path/to/workspace
python pycompiler_ark.py engine list --json
python pycompiler_ark.py engine doctor nuitka src/main.py --json
python pycompiler_ark.py workspace inspect . --json
python pycompiler_ark.py doctor --json
python pycompiler_ark.py init /path/to/workspace --json
python pycompiler_ark.py init /path/to/workspace --with-venv --json
python pycompiler_ark.py config-auto /path/to/workspace --json
python pycompiler_ark.py cfg-auto /path/to/workspace --json
python pycompiler_ark.py ws init /path/to/workspace --json
python pycompiler_ark.py check /path/to/workspace --json
python pycompiler_ark.py scaffold engine demo_engine --json
python pycompiler_ark.py unload --json
```

### CLI groups

- `gui`: launch graphical entrypoints explicitly
- `engine`: inspect engines, run compatibility checks, dry-run or compile
- `bcasl`: BCASL GUI or delegated headless actions
- `workspace`: inspect the current workspace and resolved entrypoint
- `init`: initialize a workspace directory and base configs (`ark.yml`, `bcasl.yml`, `.ark/pref.json`)
  - `--with-venv`: also create/reuse a local workspace venv and set it in `.ark/pref.json`
- `config-auto`: auto-detect entrypoint and update workspace config
- `cfg-auto`: short alias for `config-auto`
- `ws`: short group alias for workspace bootstrap (`ws init`, `ws config-auto`)
- `check`: strict CI/CD preflight shortcut
- `doctor`: global diagnostics snapshot
- `scaffold`: generate starter templates for engines and plugins

### Headless note

The CLI router no longer bootstraps the main Qt application for headless paths such as:

- `--help`
- `--version`
- `--info`
- `--cli`
- `unload`
- `workspace ...`

Structured command groups such as `engine`, `bcasl`, `doctor`, and `scaffold`
also avoid launching the main GUI entrypoint.

This keeps scripting and CI workflows friendly on machines where no GUI window
should be opened.

### CI-friendly exit codes

- `0`: success
- `3`: precheck failure (`check --strict`)
- `4`: invalid or missing workspace
- `5`: engine not found

These are the stable codes to key on in CI for the structured headless commands.

### Dedicated CLI quick commands

```text
ark-cli> main
ark-cli> main --ide-gui
ark-cli> bcasl run ~/my_workspace --timeout 30
ark-cli> engine dry-run pyinstaller src/main.py
ark-cli> engine list
ark-cli> unload
```

### GUI entrypoints

```bash
python pycompiler_ark.py gui main --ide
python pycompiler_ark.py gui bcasl
python pycompiler_ark.py gui engines
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

- `cli/` — CLI entrypoints, headless operations, fallback mode, and dedicated shell.
- `Core/` — main UI logic.
- `Core/IdeLikeGui/` — wiring layer for the IDE-like main GUI.
- `ENGINES/` — built-in engines.
- `EngineLoader/` — discovery and registry.
- `Plugins/` — BCASL plugins.
- `Plugins_SDK/` — plugin SDK.
- `bcasl/` — BCASL core.
- `OnlyMod/` — standalone tools (BCASL and Engines).
- `ui/` — Qt Designer UI.
  - `ui/ui_design.ui` — default main layout
  - `ui/ui_ide_design2.ui` — IDE-like layout
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
