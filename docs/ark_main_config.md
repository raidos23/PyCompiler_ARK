## **ark.yml** — Workspace Configuration

This file defines the project settings used to build the normalized **BuildContext**. It lives at the workspace root and is created automatically when the workspace is first set in the GUI (if missing).

The configuration is loaded by `Core/Configs/` and serves as the primary source of truth for project metadata.

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
  icon: assets/icon.ico
  data:
    - source: assets/
      destination: assets/
```

## Build Entrypoint

`project.entry` defines the primary script to compile. It must be a path relative to the workspace root.

Behavior:
- When a build is triggered (CLI or GUI), this entrypoint is used to populate the `BuildContext`.
- In the GUI, you can select any file to compile, but the `project.entry` remains the default configuration.
- If it is missing or invalid, compilation is blocked until a valid entrypoint is selected.

GUI shortcuts:
- Right‑click a file in the workspace list → **Set as entrypoint**.
- Right‑click again → **Clear entrypoint**.
- The entrypoint is marked with an icon in the list.

## Relationship to BuildContext

The fields in `ark.yml` are mapped directly to the `BuildContext` data structure passed to engines:

| ark.yml field | BuildContext field |
| :--- | :--- |
| `project.name` | `project_name` |
| `project.entry` | `entry_point` |
| `workspace.exclude` | `exclude_patterns` |
| `build.output` | `output_dir` |
| `build.data` | `data_mappings` |
| `build.icon` | `icon` |

## Plugins Configuration

`ark.yml` controls the global activation of the **BCASL** (Before-Compilation Actions System) pipeline.

```yaml
plugins:
  bcasl_enabled: true  # Global toggle for the BCASL pipeline
```

If `bcasl_enabled` is set to `false`, the entire pipeline is skipped during compilation. This setting is also manageable via the **BCASL Pipeline** dialog in the GUI.

## Advanced Config Editor (GUI)

The main GUI has a **Configurations avancées** button that opens a dedicated editor for `ark.yml`, `bcasl.yml`, and other configuration files.
