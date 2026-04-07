# Practical CI/CD with ARK CLI

This page provides a practical and reproducible CI/CD flow using `pycompiler_ark`.

## Goal

Automate the following steps for a workspace:

1. Apply workspace setup in one deterministic step
2. Run a strict precheck gate
3. Compile with a selected engine

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
ENGINE_ID="<engine_id>"

# Single-step workspace flow (init + auto-config + inspect)
$ARK_BIN workspace apply "$WORKSPACE_DIR" --with-venv --strict --json > "$WORKSPACE_DIR/.ark_workspace_apply.json"

# Optional explicit gate (kept in many teams for readability in CI logs)
$ARK_BIN check "$WORKSPACE_DIR" --json --strict > "$WORKSPACE_DIR/.ark_check.json"

ENTRYPOINT_REL="$(python3 - <<'PY'
import json, os
from pathlib import Path
ws = os.environ["WORKSPACE_DIR"]
report = Path(ws) / ".ark_workspace_apply.json"
data = json.loads(report.read_text(encoding="utf-8"))
inspect_payload = data.get("inspect") or {}
print(inspect_payload.get("entrypoint") or "main.py")
PY
)"
ENTRYPOINT_FILE="$WORKSPACE_DIR/$ENTRYPOINT_REL"

$ARK_BIN engine info "$ENGINE_ID" --workspace "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_engine_info.json"
$ARK_BIN engine compile "$ENGINE_ID" "$ENTRYPOINT_FILE" --workspace "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_build_result.json"
```

You can explicitly set or clear entrypoint in CI when needed:

```bash
$ARK_BIN workspace entrypoint-set "$WORKSPACE_DIR" src/main.py --json
$ARK_BIN workspace entrypoint-clear "$WORKSPACE_DIR" --json
```

## Command Breakdown

- `workspace apply --with-venv --strict`
  - applies full workspace setup in one command
  - creates/reuses `ARK_Main_Config.yml`, `bcasl.yml`, `.ark/pref.json`
  - runs auto-config (unless disabled)
  - can fail with strict precheck semantics when entrypoint is required

- `check --strict`
  - CI/CD gate
  - exits non-zero when precheck fails

- `engine compile`
  - compiles the resolved entrypoint with the selected engine
- `engine config set/reset`
  - lets CI apply or reset workspace engine options without opening GUI
- `venv status/use-system/use-venv/install-req`
  - lets CI enforce workspace Python mode and requirements installation policy

## Workspace Apply Options (CI-focused)

`workspace apply` (and alias `workspace select`) supports options designed for pipelines:

- `--with-venv`
  - create/reuse workspace virtual environment
- `--entrypoint <path>`
  - force entrypoint instead of relying on detection
- `--no-auto-config`
  - skip auto-configuration stage (useful for fully pre-committed config flows)
- `--no-inspect-files`
  - skip recursive `.py` workspace scan
- `--no-apply-venv-pref`
  - skip applying `.ark/pref.json` workspace venv preference
- `--no-apply-engine-configs`
  - skip loading `.ark/<engine_id>/config.json` workspace engine configs
- `--strict`
  - fail when required checks are missing
- `--require-entrypoint`
  - explicit entrypoint requirement (also implied by `--strict`)
- `--json`
  - machine-readable output for pipeline parsing

Examples:

```bash
# Strict default for CI
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py workspace apply /path/to/workspace --with-venv --strict --json

# Explicit entrypoint override
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py workspace apply /path/to/workspace --entrypoint src/main.py --json

# Alias forms
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py workspace select /path/to/workspace --json
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py ws apply /path/to/workspace --json
```

## Choosing an Engine

List available engines:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine list --json
```

Then pick one engine id from your environment.

## Engine Config in CI (No GUI Required)

Read config:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config show <engine_id> --workspace /path/to/workspace --json
```

Set config from inline JSON:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config set <engine_id> --workspace /path/to/workspace --options-json '{"onefile": true}' --json
```

Set config from file:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config set <engine_id> --workspace /path/to/workspace --options-file /path/to/options.json --json
```

Replace (instead of merge):

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config set <engine_id> --workspace /path/to/workspace --replace --options-file /path/to/options.json --json
```

Reset config:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config reset <engine_id> --workspace /path/to/workspace --json
```

## Venv Control in CI

Inspect current mode:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py venv status /path/to/workspace --json
```

Force system Python:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py venv use-system /path/to/workspace --json
```

Force workspace venv:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py venv use-venv /path/to/workspace --create --json
```

Install requirements explicitly:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py venv install-req /path/to/workspace --json
```

## Useful Exit Codes

- `0`: success
- `2`: usage error (invalid command/arguments)
- `3`: strict precheck failure (`check --strict`)
- `4`: invalid workspace
- `5`: engine not found

## Reusable Shell Wrapper (optional)

If your team prefers a checked-in shell wrapper, create a script that chains:

1. `workspace apply ... --json`
2. `check ... --json --strict`
3. `engine compile ... --json`

Then archive JSON outputs as CI artifacts for troubleshooting.

## GitHub Actions Dogfooding Workflow

This repository includes a workflow where ARK compiles itself using ARK CLI:

- Workflow file: `.github/workflows/ark-self-build.yml`
- Engine used: `nuitka`
- Flow: `workspace apply` (or `init` + `cfg-auto`) -> `check --strict` -> `engine compile`
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
- Use `engine list --json` to select the target engine id dynamically per environment.

## GUI Selection Equivalent in CLI

When users say "select workspace" in GUI terms, the CI/CD equivalent is:

```bash
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py workspace apply /path/to/workspace --with-venv --strict
```

This gives a deterministic, scriptable workflow that mirrors the practical setup steps usually performed after selecting a workspace in the GUI.

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
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config path <engine_id> --workspace /path/to/workspace
python3 /path/to/PyCompiler_ARK/pycompiler_ark.py engine config show <engine_id> --workspace /path/to/workspace --json
```
