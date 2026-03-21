# Release Smoke Checklist

Use this checklist before cutting a release tag or publishing release artifacts.

## CI

- Confirm the `CI` workflow is green on:
  - Ubuntu / Python 3.12
  - Ubuntu / Python 3.13
  - Windows / Python 3.12
  - Windows / Python 3.13
- Confirm `lint`, `tests`, and `smoke` jobs all passed.

## CLI Smoke

Run these commands from a clean environment:

```bash
python -m pycompiler_ark --help
python -m pycompiler_ark --version
python -m pycompiler_ark --info
python -m pycompiler_ark engines --dry-run
python -m py_compile pycompiler_ark.py
```

Expected outcome:

- Help renders without traceback.
- Version prints the resolved app version.
- System info returns successfully.
- `engines --dry-run` lists engines without opening the GUI.
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
- Open BCASL standalone with `python -m pycompiler_ark bcasl`.
- Open Engines standalone with `python -m pycompiler_ark engines`.

## Release Artifacts

- If the release workflow is used, confirm artifacts are attached for each target OS.
- Confirm checksum files are generated and included.
- Confirm third-party license output is present when expected.
