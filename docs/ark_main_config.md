## **ark.yml** - Workspace Configuration

This file defines the project settings used to build the normalized **BuildContext**. It lives at the workspace root and is created automatically when the workspace is first configured in the GUI, if missing.

The configuration is loaded by `Core/Configs/` and is the primary source of truth for PyCompiler ARK project metadata.

## Minimal Example

```yaml
project:
  name: my_app
  version: 1.0.0
  entry: app.py

workspace:
  exclude:
    - ".git/**"
    - "venv/**"

build:
  engine: pyinstaller
  output: dist/
  icon: assets/icon.ico
  exclude:
    - "tests/**"
  data:
    - source: assets/
      destination: assets/

plugins:
  bcasl_enabled: true
```

## Build Entrypoint

`project.entry` defines the primary script to compile. It must be a path relative to the workspace root.

Behavior:

- When a build is triggered from the CLI or GUI, this entrypoint is used to populate the `BuildContext`.
- In the GUI, you can select any file to compile, but `project.entry` remains the default configuration.
- If it is missing or invalid, compilation is blocked until a valid entrypoint is selected.

GUI shortcuts:

- Right‑click a file in the workspace list → **Set as entrypoint**.
- Right‑click again → **Clear entrypoint**.
- The entrypoint is marked with an icon in the list.

## Relationship to BuildContext

The fields in `ark.yml` are mapped directly to the `BuildContext` data structure passed to engines and BC plugins:

| ark.yml field | BuildContext field |
| :--- | :--- |
| `project.name` | `project_name` |
| `project.entry` | `entry_point` |
| `build.exclude` | `exclude_patterns` |
| `build.output` | `output_dir` |
| `build.data` | `data_mappings` |
| `build.icon` | `icon` |

> **Note**: `workspace.exclude` is used only for the GUI workspace view filter. `build.exclude` determines which files are ignored during compilation and BCASL phases.

## Plugins Configuration

`ark.yml` controls the global activation of the **BCASL** (Before-Compilation Actions System) pipeline.

```yaml
plugins:
  bcasl_enabled: true  # Global toggle for the BCASL pipeline
```

If `bcasl_enabled` is set to `false`, the entire pipeline is skipped during compilation. You can also change this setting in the **BCASL Pipeline** dialog in the GUI.

## Advanced Config Editor (GUI)

The main GUI has a **Configurations avancées** button that opens a dedicated editor for `ark.yml`, `bcasl.yml`, and other configuration files managed by PyCompiler ARK.
