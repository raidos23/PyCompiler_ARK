# Release Process

This document is the release source of truth for PyCompiler ARK.

## Scope

Use this process for all public tags, starting with `v1.0.0`.

## 1. Freeze

1. Ensure `main` is green on CI (`lint`, `tests`, `smoke`).
2. Stop feature merges; accept only release blockers.
3. Confirm `CHANGELOG.md` is updated for the target version.
4. Confirm docs impacted by behavior changes are updated (`README.md`, `docs/ci_cd_ark_cli.md`, feature docs).

## 2. Local validation

Run at minimum:

```bash
ruff check .
black --check .
pytest -q tests
python -m compileall -q Core OnlyMod bcasl Plugins_SDK EngineLoader cli engine_sdk Plugins pycompiler_ark.py
python -m pycompiler_ark --help
python -m pycompiler_ark --version
python -m pycompiler_ark doctor --json
```

Optional but recommended:

```bash
python -m pycompiler_ark check /path/to/workspace --json --strict
python -m pycompiler_ark engine list --json
```

## 3. Tag and publish

1. Create and push tag:

```bash
git checkout main
git pull --ff-only
git tag -a v1.0.0 -m "PyCompiler ARK v1.0.0"
git push origin v1.0.0
```

2. .github/workflows/release.yml triggers :
- Lint/test/smoke CI.
- Self-build Nuitka Linux onefile.
- GH Release auto (artifacts + notes).

## 4. Post-release checks

1. Verify the GitHub Release exists and is not missing assets.
2. Validate checksums file is present.
3. Add follow-up issues for any deferred fixes.

## 5. Rollback guidance

If a critical release blocker is found after tagging:

1. Create a hotfix commit on `main`.
2. Tag next patch (`vX.Y.Z+1`) instead of reusing the previous tag.
3. Publish release notes describing the fix delta.

