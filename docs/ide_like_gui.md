## IDE-like Main GUI (`gui main --ide`)

PyCompiler ARK can launch an alternative main interface layout inspired by IDE tools.
The preferred entrypoint is the grouped CLI form `gui main --ide`.

Use:

```bash
python pycompiler_ark.py gui main --ide
# or
python -m pycompiler_ark gui main --ide
```

From the dedicated CLI:

```text
ark-cli> main --ide-gui
```

Legacy compatibility alias:

```bash
python -m pycompiler_ark --ide-gui
```

## What It Changes

- Loads `ui/ui_ide_design2.ui` as the main window layout.
- Keeps existing Core logic (workspace, compilation, cancellation, etc.).
- Reuses the classic shared signal wiring and policies instead of duplicating them.
- Uses a wiring layer only (no duplicated business logic) through:
  - `Core/IdeLikeGui/__init__.py`
  - `Core/IdeLikeGui/connections.py`
- Keeps IDE-specific affordances:
  - `...` activity-bar menu
  - dependencies activity button
- Tunes the loaded layout at runtime to reduce label compression in the header, center panel, and logs area.

## Runtime Switch

The launcher sets:

```text
PYCOMPILER_UI_VARIANT=ide2
```

`Core/Gui.py` then selects `init_ide_like_ui()` and falls back to `init_ui()` if needed.

## Current Scope

The IDE-like wiring reuses the classic shared signal connector, then adds its
own IDE-specific actions on top.

In practice, the IDE-like GUI inherits the classic main workflow instead of
exposing only a small subset of actions.

Notable points:

- classic shared signal wiring is reused
- IDE-specific actions are connected afterward
- the entrypoint selector is initialized in IDE mode as well

For parity details and remaining checks, review the IDE/classic behavior in the current GUI implementation and tests.
