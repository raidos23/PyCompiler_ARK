# Release Smoke Checklist

Use this checklist before cutting a release tag or publishing release artifacts.

## CI

- Confirm the `CI` workflow is green on:
  - Ubuntu / Python 3.12
  - Ubuntu / Python 3.13
  - Windows / Python 3.12
  - Windows / Python 3.13
- Confirm `lint`, `tests`, and `smoke` jobs all passed.
- Re-check the [Quality freeze policy](./quality_freeze.md) before tagging.

## CLI Smoke

Run these commands from a clean environment:

```bash
python -m pycompiler_ark --help
python -m pycompiler_ark --version
python -m pycompiler_ark --info
python -m pycompiler_ark engine list --json
python -m pycompiler_ark workspace inspect . --json
python -m pycompiler_ark doctor --json
python -m pycompiler_ark ci smoke . --json --strict --require-entrypoint
python -m py_compile pycompiler_ark.py
```

Expected outcome:

- Help renders without traceback.
- Version prints the resolved app version.
- System info returns successfully.
- `engine list --json` returns a valid engine inventory without opening the GUI.
- `workspace inspect . --json` returns workspace data without loading the GUI stack.
- `doctor --json` returns a diagnostic snapshot successfully.
- `ci smoke . --json --strict --require-entrypoint` returns a valid smoke payload and fails the job when a preflight breaks.
- Source compilation check succeeds.

## GUI Parity

- Re-check the IDE/classic parity notes in [IDE/classic parity](./ide_classic_parity.md).
- Verify the IDE `...` menu labels and tooltips are translated after a language switch.
- Verify the IDE dependencies activity button keeps the expected tooltip and action.
- Verify the entrypoint selector is available from the IDE file list context menu.

## Manual GUI Spot Checks

- Launch the classic GUI.
- Launch the IDE-like GUI.
- Open the dedicated CLI with `python -m pycompiler_ark --cli`.
- Open BCASL standalone with `python -m pycompiler_ark gui bcasl`.
- Open Engines standalone with `python -m pycompiler_ark gui engines`.

## Release Artifacts

- If the release workflow is used, confirm artifacts are attached for each target OS.
- Confirm checksum files are generated and included.
- Confirm third-party license output is present when expected.

## Blocking bug status

As validated by the current smoke-check plan, no known blocking bug remains open in the quality plan.
