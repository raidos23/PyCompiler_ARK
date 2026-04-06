# Practical CI/CD with ARK CLI

This page provides a practical and reproducible CI/CD flow using `pycompiler_ark`.

## Goal

Automate the following steps for a workspace:

1. Initialize workspace base files
2. Detect/configure the entrypoint
3. Run a strict precheck gate
4. Compile with a selected engine

## Prerequisites

- Python available on your CI agent
- ARK repository available (or ARK installed in the environment)
- Project workspace accessible on the agent

Example ARK command:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py
```

## Minimal Pipeline (copy/paste)

```bash
ARK_BIN="python3 /path/to/PyCompiler_ARK/pycompiler_ark.py"
WORKSPACE_DIR="/path/to/workspace"
ENGINE_ID="pyinstaller"

$ARK_BIN init "$WORKSPACE_DIR" --with-venv --json > "$WORKSPACE_DIR/.ark_init.json"
$ARK_BIN cfg-auto "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_cfg_auto.json"
$ARK_BIN check "$WORKSPACE_DIR" --json --strict > "$WORKSPACE_DIR/.ark_check.json"

ENTRYPOINT_REL="$(python3 - <<'PY'
import json, os
from pathlib import Path
ws = os.environ["WORKSPACE_DIR"]
cfg = Path(ws) / ".ark_cfg_auto.json"
data = json.loads(cfg.read_text(encoding="utf-8"))
print(data.get("entrypoint") or "main.py")
PY
)"
ENTRYPOINT_FILE="$WORKSPACE_DIR/$ENTRYPOINT_REL"

$ARK_BIN engine info "$ENGINE_ID" --workspace "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_engine_info.json"
$ARK_BIN engine compile "$ENGINE_ID" "$ENTRYPOINT_FILE" --workspace "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_build_result.json"
```

## Command Breakdown

- `init --with-venv`
  - prepares workspace
  - creates `ARK_Main_Config.yml`, `bcasl.yml`, `.ark/pref.json`
  - creates/reuses a local virtual environment

- `cfg-auto`
  - detects an entrypoint
  - updates workspace configuration

- `check --strict`
  - CI/CD gate
  - exits non-zero when precheck fails

- `engine compile`
  - compiles the resolved entrypoint with the selected engine

## Choosing an Engine

List available engines:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine list --json
```

Common choices:

- `pyinstaller`
- `nuitka`
- `cx_freeze`

## Useful Exit Codes

- `0`: success
- `2`: usage error (invalid command/arguments)
- `3`: strict precheck failure (`check --strict`)
- `4`: invalid workspace
- `5`: engine not found

## Ready-to-use Script

A concrete validated example can be run with:

```bash
./ci_cd_ark.sh
```

This script chains `init`, `cfg-auto`, `check`, and `engine compile`, and writes JSON reports.

## GitHub Actions Dogfooding Workflow

This repository includes a workflow where ARK compiles itself using ARK CLI:

- Workflow file: `.github/workflows/ark-self-build.yml`
- Engine used: `pyinstaller`
- Flow: `init` -> `cfg-auto` -> `check --strict` -> `engine compile`
- Uploaded artifacts:
  - build output (`dist/`, `build/` when available)
  - ARK workspace reports (`.ark_ci_artifacts/*.json`)
  - workspace `.ark/` snapshot for debugging

## Practical Tips

- ARK consumes workspace configuration files during CI runs. For reproducible and correct builds, commit these files:
  - `ARK_Main_Config.yml`
  - `bcasl.yml`
  - `.ark/` (especially `.ark/pref.json` and `.ark/<engine_id>/config.json`)
- `.ark/` stores engine command options used by ARK at build time; commit it to keep builds reproducible across local and CI environments.
- Keep `.ark_*.json` files as CI artifacts for debugging.
- Start with `pyinstaller`, then evaluate `nuitka` if you want runtime performance optimization.

## Reproducibility Note for Engine Options

For full reproducibility, engine-specific options should be configured from the GUI first.

Why:

- Some engine options are UI-driven and persisted per workspace.
- Those options are stored under:
  - `.ark/<engine_id>/config.json`

Recommended workflow:

1. Open the GUI and set engine options for the workspace.
2. Save/apply those options in the engine UI.
3. Commit engine config files (`.ark/<engine_id>/config.json`) and workspace preference (`.ark/pref.json`) so CI consumes the same configuration.
4. In CI, run the same workspace path and engine id so ARK reuses the persisted config.

Useful inspection commands:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config path pyinstaller --workspace /path/to/workspace
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config show pyinstaller --workspace /path/to/workspace --json
```
