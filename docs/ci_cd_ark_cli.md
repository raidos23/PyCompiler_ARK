# Practical CI/CD with ARK CLI

This page provides a practical and reproducible CI/CD flow using `pycompiler_ark`.

## CI/CD Source Of Truth

Use this document as the single source of truth for ARK CI/CD behavior and examples.
When pipeline behavior changes (flags, exit codes, fail-fast rules, JSON contracts),
update this page first and keep other references aligned to it.

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

If you use the project wrapper script, prefer CLI flags over environment variables:

```bash
./ci_cd_ark.sh --workspace /path/to/workspace --engine pyinstaller --no-bcasl
./ci_cd_ark.sh --workspace /path/to/workspace --engine pyinstaller --with-bcasl --bcasl-timeout 120
```

Direct ARK CLI flow:

```bash
ARK_BIN="python3 /path/to/PyCompiler_ARK/pycompiler_ark.py"
WORKSPACE_DIR="/path/to/workspace"
ENGINE_ID="<engine_id>"
export ARK_AUTO_INSTALL_SYSTEM_TOOLS=1

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

# Optional BCASL stage (enable explicitly when required)
# $ARK_BIN bcasl run "$WORKSPACE_DIR" --timeout 120 > "$WORKSPACE_DIR/.ark_bcasl_run.log"

$ARK_BIN engine info "$ENGINE_ID" --workspace "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_engine_info.json"
if ! $ARK_BIN engine compile "$ENGINE_ID" "$ENTRYPOINT_FILE" --workspace "$WORKSPACE_DIR" --json > "$WORKSPACE_DIR/.ark_build_result.json"; then
  WORKSPACE_DIR="$WORKSPACE_DIR" python3 - <<'PY'
import json, os
from pathlib import Path
p = Path(os.environ["WORKSPACE_DIR"]) / ".ark_build_result.json"
try:
    d = json.loads(p.read_text(encoding="utf-8"))
    print("Compilation failed:", d.get("error") or "unknown error")
except Exception:
    print("Compilation failed (invalid .ark_build_result.json)")
PY
  exit 1
fi
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

- `bcasl run` (optional)
  - include BCASL plugin execution in pipeline when needed
  - recommended through wrapper flags: `--with-bcasl` / `--no-bcasl`

- `engine compile`
  - compiles the resolved entrypoint with the selected engine
  - returns non-zero on build failure, even in `--json` mode (pipeline-friendly)
- `engine config set/reset`
  - lets CI apply or reset workspace engine options without opening GUI
- `venv status/use-system/use-venv/install-req`
  - lets CI enforce workspace Python mode and requirements installation policy

## Fail-fast Rule

CI/CD flow should be fail-fast:

- if one stage fails, stop the pipeline immediately
- do not continue to later stages (for example, do not compile after a BCASL failure)
- mark non-executed stages as skipped in the final summary

## System Tool Auto-install Policy (CI Security)

When `ARK_AUTO_INSTALL_SYSTEM_TOOLS=1` is set, ARK can attempt to install missing
system tools required by engines. In CI/headless mode:

- installation is strictly non-interactive
- ARK does not prompt for or persist sudo passwords
- ARK uses root privileges when already running as root, otherwise `sudo -n`

If auto-install fails in CI:

- run the pipeline as root, or
- preinstall required system tools in the runner/base image, or
- configure narrowly-scoped `sudoers` rules (NOPASSWD) for your CI user

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

## Final Summary Pattern

For readable CI logs, print a final status summary from generated JSON reports.
This keeps one clear block with step-by-step `OK`/`FAIL` states:

```bash
WORKSPACE_DIR="/path/to/workspace"
WORKSPACE_DIR="$WORKSPACE_DIR" python3 - <<'PY'
import json, os
from pathlib import Path

ws = Path(os.environ["WORKSPACE_DIR"])
reports = [
    ("workspace-apply", ws / ".ark_workspace_apply.json", lambda d: bool(d.get("ok"))),
    # Optional BCASL report generated by your wrapper script when enabled
    ("bcasl-run", ws / ".ark_bcasl_run.json", lambda d: bool(d.get("ok"))),
    ("check", ws / ".ark_check.json", lambda d: bool(d.get("ok"))),
    ("engine-info", ws / ".ark_engine_info.json", lambda d: bool(d.get("found", True))),
    ("compile", ws / ".ark_build_result.json", lambda d: bool(d.get("success"))),
]

for name, path, ok_fn in reports:
    if not path.exists():
        print(f"[MISS] {name}: {path.name} not found")
        continue
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"[FAIL] {name}: invalid json ({exc})")
        continue
    ok = bool(ok_fn(data))
    detail = data.get("error") or data.get("message") or ""
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {name}" + (f": {detail}" if detail else ""))
PY
```

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
