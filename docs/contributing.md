# Contributing Guide

This guide is meant to be directly usable by contributors working on PyCompiler ARK.

## Setup

```bash
git clone https://github.com/raidos23/PyCompiler_ARK.git
cd PyCompiler_ARK
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On Windows:

```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

## Recommended workflow

1. Create a branch from the active development branch.
2. Make a focused change set.
3. Run lint, tests, and smoke checks locally when relevant.
4. Update documentation when behavior changes.
5. Commit with a clear message describing the user-visible impact.

## Local checks

Baseline checks:

```bash
ruff check .
black --check .
pytest -q tests
python -m py_compile pycompiler_ark.py
```

Useful smoke commands:

```bash
python -m pycompiler_ark --help
python -m pycompiler_ark --version
python -m pycompiler_ark --info
python -m pycompiler_ark engine list --json
python -m pycompiler_ark workspace inspect . --json
python -m pycompiler_ark doctor --json
python -m pycompiler_ark ci smoke /path/to/workspace --json --strict --require-entrypoint
python -m pycompiler_ark --cli
```

When using `--require-entrypoint`, point the smoke command at a workspace that
already defines an entrypoint in `ARK_Main_Config.yml`.

Release-oriented checks are documented in [Release smoke checklist](./release_smoke_checklist.md).

## Where to make changes

- CLI behavior: `cli/`
- headless CLI operations and JSON payloads: `cli/headless_ops.py`
- classic GUI wiring: `Core/UiConnection.py`
- IDE-like GUI wiring: `Core/IdeLikeGui/`
- compilation logic: `Core/Compiler/`
- environment and dependency logic: `Core/Venv_Manager/`, `Core/deps_analyser/`
- built-in engines: `ENGINES/`
- BCASL plugins and runtime: `Plugins/`, `bcasl/`, `Plugins_SDK/`
- documentation: `docs/`

## Contribution rules of thumb

- Prefer extending existing shared helpers over copying logic.
- Keep UI-specific code thin.
- Keep engine-specific behavior inside engines.
- Add or update tests when changing heuristics, parsing, or orchestration behavior.
- If you change CLI flags, commands, or docs-linked behavior, update the README.
- If you change the command hierarchy (`gui`, `engine`, `workspace`, `doctor`, `scaffold`, `ci`) or JSON outputs, update the CLI docs and smoke checklist.
- Keep CI-facing exit codes stable, or document the change explicitly in the README and release smoke checklist.
- If you change IDE/classic behavior, update the parity matrix when appropriate.

## Documentation expectations

Contributors should update documentation when they modify:

- public CLI behavior
- workflow or release steps
- architecture-relevant module boundaries
- dependency analyzer heuristics
- IDE/classic parity behavior

## Good first doc touchpoints

- [Architecture overview](./architecture.md)
- [Dependency analyzer](./dependency_analyzer.md)
- [IDE/classic parity matrix](./ide_classic_parity.md)
- [Dedicated CLI](./dedicated_cli.md)
- [Release smoke checklist](./release_smoke_checklist.md)
