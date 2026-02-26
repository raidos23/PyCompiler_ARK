## IDE-like Main GUI (`--ide-gui`)

PyCompiler ARK can launch an alternative main interface layout inspired by IDE tools.

Use:

```bash
python pycompiler_ark.py --ide-gui
# or
python -m pycompiler_ark --ide-gui
```

From the dedicated CLI:

```text
ark-cli> main --ide-gui
```

## What It Changes

- Loads `ui/ui_ide_design2.ui` as the main window layout.
- Keeps existing Core logic (workspace, compilation, cancellation, etc.).
- Uses a wiring layer only (no duplicated business logic) through:
  - `Core/IdeLikeGui/__init__.py`
  - `Core/IdeLikeGui/connections.py`

## Runtime Switch

The launcher sets:

```text
PYCOMPILER_UI_VARIANT=ide2
```

`Core/Gui.py` then selects `init_ide_like_ui()` and falls back to `init_ui()` if needed.

## Current Scope

The IDE-like wiring currently connects these existing actions:

- Build (`compile_all`)
- Cancel (`cancel_all_compilations`)
- Select workspace (`select_workspace`)

Additional controls can be mapped incrementally to existing Core methods.
