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
python -m pycompiler_ark check /path/to/workspace --json
python -m pycompiler_ark --cli
```

For reliable prechecks, point `check --strict` at a workspace that already
defines an entrypoint in `ark.yml`.

Release-oriented checks should follow the CLI examples in this guide and the README.
For publishing steps, follow [`docs/release_process.md`](./release_process.md).

## Where to make changes

- CLI behavior: `Ui/Cli/`
- headless discovery and payload helpers: `Ui/Cli/discovery.py`
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
- Treat i18n as shared architecture, not as per-widget local logic.
- Add or update tests when changing heuristics, parsing, or orchestration behavior.
- If you change CLI flags, commands, or docs-linked behavior, update the README.
- If you change the command hierarchy (`gui`, `engine`, `workspace`, `init`, `config-auto`, `check`, `scaffold`) or JSON outputs, update the CLI docs.
- Keep CI-facing exit codes stable, or document the change explicitly in the README.
- For CI/CD behavior, keep [`docs/ci_cd_ark_cli.md`](./ci_cd_ark_cli.md) as the single source of truth and align other docs/examples to it.
- For GUI behavior that impacts CI expectations (entrypoint, workspace persistence, engine config), explicitly state whether behavior is temporary session state or persisted workspace state.
- If you change IDE/classic behavior, update the IDE docs when appropriate.
- If you change translated GUI behavior, follow [`docs/dev_docs/i18n_ark.md`](./dev_docs/i18n_ark.md) and keep classic/IDE wiring aligned.

## i18n architecture rule

ARK has a specific i18n architecture and contributors should follow it instead of
adding local ad-hoc translation code.

- Add keys in `languages/*.json`.
- Map widgets first, then wire shared GUI translations in `Core/i18n.py`.
- Reuse classic GUI translation flow when exposing the same feature in IDE-like GUI.
- For IDE proxy controls such as the `(...)` menu, prefer reusing existing translated classic controls or the active `self._tr` table instead of hardcoding new strings.
- Test language switching live, without restarting the app.
- Use [`docs/dev_docs/i18n_ark.md`](./dev_docs/i18n_ark.md) as the reference integration guide.

## Documentation expectations

Contributors should update documentation when they modify:

- public CLI behavior
- workflow or release steps
- architecture-relevant module boundaries
- dependency analyzer heuristics
- IDE/classic parity behavior

## Good first doc touchpoints

- [Release process](./release_process.md)
- [Architecture overview](./architecture.md)
- [Dependency analyzer](./dependency_analyzer.md)
- [Dedicated CLI](./dedicated_cli.md)
- [ARK i18n architecture](./dev_docs/i18n_ark.md)
