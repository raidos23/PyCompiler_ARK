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
    - "**/__pycache__/**"

build:
  engine: pyinstaller
  output: dist/
  icon: assets/icon.ico
  exclude:
    - "tkinter"
    - "unittest"
  data:
    - source: assets/
      destination: assets/
      type: dir
    - source: config.json
      destination: config.json
      type: file

plugins:
  bcasl_enabled: true
```

## Build Data Mappings

The `build.data` section defines external files and directories to be bundled with the executable. Each entry must specify:

- `source`: The relative path to the asset.
- `destination`: The relative path where the asset will be placed in the final bundle.
- `type`: Explicitly categorize the asset:
    - `dir`: For entire directories.
    - `file`: For single files.

> **Note**: For backward compatibility, `type` defaults to `dir` if omitted, but explicit typing is highly recommended.

## Build Exclusions vs Workspace Exclusions

It is critical to distinguish between these two exclusion sections. Using them interchangeably is a common source of build failures.

### 1. `workspace.exclude` (UI Filter)
Used exclusively for the **GUI workspace view filter**. 
- **Purpose**: Hide files and folders from the file list in the user interface.
- **Usage**: Perfect for `.git/`, `venv/`, `__pycache__/`, or other technical folders you don't want to see in the GUI.

### 2. `build.exclude` (Python Packages)
Determines which **Python packages/modules** are ignored by the compiler.
- **Purpose**: Prevent specific Python libraries from being bundled.
- **Restriction**: This is **NOT** a general folder excluder. It should **NEVER** contain technical patterns like `*.pyc`, `__pycache__`, or `.git`. These are handled automatically by the Core or should be hidden via `workspace.exclude`.

⚠️ **CRITICAL WARNING: Name Collisions**
Patterns in `build.exclude` are passed to engines (like Nuitka or PyInstaller) as **logical module exclusions**. 

If you have a local folder named `venv` (your virtual environment) and you add `venv` to `build.exclude` thinking you are excluding a directory, you are actually telling the compiler: *"Do not bundle the Python package named 'venv'"*. 
If your project or any dependency uses `import venv` (the standard library), your application **will crash** because the library was removed from the bundle. 

**Rule of thumb**: Only use `build.exclude` for real Python modules you want to remove (e.g., `tkinter`, `unittest`, or a specific large sub-package). For everything else, use `workspace.exclude`.

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

The main GUI has a **Configurations avancées** button that opens a dedicated editor for `ark.yml` managed by PyCompiler ARK.
