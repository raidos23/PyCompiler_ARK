**Overview**
A PyCompiler_ARK engine is a Python package placed in `ENGINES/` and auto‑loaded at startup. It registers itself with `@engine_register` and provides a `CompilerEngine` that builds the compile command and, optionally, a dedicated UI tab.

**Discovery And Loading**
- Engines are discovered only in `ENGINES/<engine_id>/`.
- The folder must contain an `__init__.py`.
- At startup, `EngineLoader` scans `ENGINES/` and imports each package.
- Auto discovery can be disabled with `ARK_ENGINES_AUTO_DISCOVER=0`.

**Package Layout**
- `ENGINES/<engine_id>/__init__.py`: engine code, registration, UI.
- `ENGINES/<engine_id>/languages/<code>.json`: optional translations.
- `ENGINES/<engine_id>/mapping.json`: optional mapping for the auto‑builder.
- Optional internal modules, assets, helpers.

**Minimal Example**
```python
from __future__ import annotations

import sys
from engine_sdk import CompilerEngine, engine_register


@engine_register
class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"
    version = "0.1.0"
    required_core_version = "1.0.0"
    required_sdk_version = "1.0.0"

    @property
    def required_tools(self):
        return {"python": ["mytool"], "system": []}

    def build_command(self, gui, file):
        return [sys.executable, "-m", "mytool", file]
```

**Lifecycle**
1. Package import from `ENGINES/<engine_id>`.
2. `@engine_register` adds the class to the registry.
3. The GUI calls `create_tab` if present to create a tab.
4. When compile is triggered, the engine provides the command via `build_command`.
5. The process runs the command and calls `on_success` on success.

**Full API**
Required attributes.
- `id`: stable unique id (used by UI and config).
- `name`: display label.
- `version`: engine version.
- `required_core_version`: minimal Core version.
- `required_sdk_version`: minimal SDK version.

Core methods.
- `build_command(self, gui, file) -> list[str]`: full command, index 0 is the program.
- `program_and_args(self, gui, file) -> (program, args) | None`: override if needed.
- `preflight(self, gui, file) -> bool`: checks before compile, return False to abort.
- `environment(self) -> dict[str, str] | None`: env vars to inject.
- `on_success(self, gui, file) -> None`: post‑build hook.

UI and i18n.
- `create_tab(self, gui) -> (QWidget, label) | None`: adds a tab.
- `apply_i18n(self, gui, tr)`: update text on language change.

Tools and dependencies.
- `required_tools`: dict `{ "python": [...], "system": [...] }`.
- `ensure_tools_installed(self, gui)`: installs missing tools when possible.

**Tools And Dependencies**
- Python tools install through the project venv when available.
- System tools use `SysDependencyManager` (GUI supported) if available.
- Keep the list minimal to avoid unnecessary installs.

**UI Tab**
- In `create_tab`, create widgets and store them on `self` (ex: `self._opt_onefile`).
- Avoid heavy work in `__init__` to keep loading fast.
- Wire signals locally and use `gui.log.append(...)` for logs.

**I18n**
- Add `languages/en.json`, `languages/fr.json`, etc. in your engine package.
- Use `resolve_language_code` and `load_engine_language_file` (SDK) to load translations.
- See `ENGINES/pyinstaller`, `ENGINES/nuitka`, `ENGINES/cx_freeze` for patterns.

**Auto Command Builder (Optional)**
The auto‑builder can read a `mapping.json` to generate engine options from detected imports.

Minimal example.
```json
{
  "numpy": {
    "pyinstaller": ["--hidden-import", "{import_name}"],
    "nuitka": "--include-package={import_name}"
  },
  "__aliases__": {
    "import_to_package": {"cv2": "opencv-python"},
    "package_to_import_name": {"opencv-python": "cv2"}
  }
}
```

Key points.
- Top‑level keys are package names.
- Engine values accept `str`, `list[str]`, or `dict` with `args` or `flags`.
- `"{import_name}"` is replaced by the actual import name.
- For advanced logic, expose `AUTO_BUILDER` in `ENGINES/<engine_id>/auto_plugins.py`.

**Best Practices**
- Keep engines stateless and drive behavior from `gui` and the target file.
- Validate paths, handle exceptions, and log clearly.
- Provide safe defaults when widgets are missing.
- Use `CompilerCore.dry_run` when helpful.
