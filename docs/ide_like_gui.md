# IDE-like Main GUI (`gui main --ide`)

This page documents the IDE-like variant of the ARK main GUI.

## Launch

Preferred command:

```bash
python pycompiler_ark.py gui main --ide
```

Equivalent forms:

```bash
python -m pycompiler_ark gui main --ide
python -m pycompiler_ark --ide-gui
```

From dedicated CLI:

```text
ark-cli> main --ide-gui
```

## What This Mode Changes

- Loads the IDE-like UI layout (`Ui/Forms/ide_main_window.ui`).
- Keeps the same Core workflow as classic GUI:
  - workspace selection
  - compile/cancel flow
  - engine and plugin integration
  - entrypoint handling
- Adds IDE-oriented affordances (activity area, overflow menu, dependencies quick access).

## What This Mode Does Not Change

- No separate business logic is introduced for compilation.
- No dedicated engine/runtime pipeline is introduced.
- CLI and CI/CD behavior remains unchanged.

## Architecture Notes

IDE-like mode is a wiring layer on top of existing Core behavior:

- `Core/IdeLikeGui/__init__.py`
- `Core/IdeLikeGui/connections.py`
- `Core/Gui.py` (variant switch + fallback)

Runtime variant switch:

```text
PYCOMPILER_UI_VARIANT=ide2
```

If IDE-like UI cannot be loaded, ARK falls back to the classic GUI.

## Maintenance Rule

When GUI behavior changes:

1. Keep parity with classic mode for shared features.
2. Update this document if launch commands, scope, or fallback behavior changes.
3. Keep CI/CD guidance in `docs/ci_cd_ark_cli.md` as source of truth for pipeline behavior.
