# ARK_Main_Config.yml — Workspace Configuration

This file customizes how a workspace is scanned and built. It lives at the
workspace root and is created automatically when the workspace is first set
in the GUI (if missing).

The configuration is loaded by `Core/ArkConfigManager.py` and merged with
defaults.

## Location

The loader checks, in order:
- `ARK_Main_Config.yaml`
- `ARK_Main_Config.yml`
- `.ARK_Main_Config.yaml`
- `.ARK_Main_Config.yml`

## Minimal Example

```yaml
exclusion_patterns:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "venv/**"

inclusion_patterns:
  - "**/*.py"

dependencies:
  auto_generate_from_imports: true

environment_manager:
  priority: ["poetry", "pipenv", "conda", "pdm", "uv", "pip"]
  auto_detect: true
  fallback_to_pip: true

build:
  entrypoint: "app.py"
```

## Build Entrypoint

`build.entrypoint` defines a single file to compile. It must be a path
relative to the workspace root.

Behavior:
- If `entrypoint` is set and the file exists, only that file is compiled.
- If it is missing or invalid, the build falls back to selected files
  (or all files if none are selected).

GUI shortcut:
- Right‑click a file in the workspace list → **Set as entrypoint**.
- Right‑click again → **Clear entrypoint**.
- The entrypoint is marked with an icon in the list.

## Notes

- Keep paths relative (ex: `"src/main.py"`).
- Entrypoint is stored in `ARK_Main_Config.yml` and can be edited manually.
- This file is separate from `bcasl.yml` (which is only for BCASL plugins).
