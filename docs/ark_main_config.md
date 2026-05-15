## **ark.yml** — Workspace Configuration

This file customizes how a workspace is scanned and built. It lives at the
workspace root and is created automatically when the workspace is first set
in the GUI (if missing).

The configuration is loaded by `Core/ArkConfig/` and merged with
defaults.

## Location

The spec-first CLI requires `ark.yml` at the workspace root. The compatibility
loader still accepts the older names used by the classic GUI path.

## Minimal Example

```yaml
project:
  name: my_app
  version: 1.0.0
  entry: app.py

workspace:
  exclude:
    - "**/__pycache__/**"
    - "**/*.pyc"
    - "venv/**"

build:
  engine: pyinstaller
  output: dist/
  data: []
```

## Build Entrypoint

`project.entry` defines the single file to compile. It must be a path
relative to the workspace root.

Behavior:
- If `entrypoint` is set and the file exists, only that file is compiled.
- If it is missing or invalid, compilation is blocked until a valid entrypoint
  is selected.

GUI shortcut:
- Right‑click a file in the workspace list → **Set as entrypoint**.
- Right‑click again → **Clear entrypoint**.
- The entrypoint is marked with an icon in the list.

## Notes

- Keep paths relative (ex: `"src/main.py"`).
- Entrypoint is stored in `ark.yml` as `project.entry` and can be edited manually.
- This file is separate from `bcasl.yml` (which remains the canonical BCASL plugin config file).
- A small compatibility bridge also exists under `plugins.*` for workspace-level BCASL defaults such as:
  - `plugins.bcasl_enabled`
  - `plugins.plugin_timeout`

## Advanced Config Editor (GUI)

The main GUI has a **Configurations avancées** button that opens a dedicated
editor for:
- `ark.yml`
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
