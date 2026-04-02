## **ARK_Main_Config.yml** — Workspace Configuration

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

plugins:
  bcasl_enabled: true
  plugin_timeout: 0

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
- This file is separate from `bcasl.yml` (which remains the canonical BCASL plugin config file).
- A small compatibility bridge also exists under `plugins.*` for workspace-level BCASL defaults such as:
  - `plugins.bcasl_enabled`
  - `plugins.plugin_timeout`

## Advanced Config Editor (GUI)

The main GUI has a **Configurations avancées** button that opens a dedicated
editor for:
- `ARK_Main_Config.yml`
- `bcasl.yml`
- `.ark/pref.json` (workspace‑specific preferences)

Features:
- Monospace editor
- Simple YAML/JSON syntax highlighting
- Diff view before saving
- Basic validation on save (YAML/JSON)

## Workspace Prefs (.ark/pref.json)

Per‑workspace preferences are stored in:
```
<workspace>/.ark/pref.json
```

Currently used keys:
```json
{
  "venv_mode": "venv" | "system",
  "venv_path": "/abs/path/to/venv" | null
}
```

These values are updated when you select a venv or System Python, and are
re‑applied automatically when the workspace is loaded.
