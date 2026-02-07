**Overview**
PyCompiler_ARK engines are Python packages loaded from `ENGINES/` at startup. Each engine registers itself with `@engine_register` and provides a `CompilerEngine` subclass that builds the command used to compile a file.

**Steps**
1. Create a package folder in `ENGINES/<engine_id>/` with an `__init__.py`.
2. Implement a subclass of `CompilerEngine` in that `__init__.py`.
3. Decorate the class with `@engine_register` and set the required attributes.
4. Restart the app so the loader auto-discovers the package.

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

**Required API**
- `id`: Unique engine id (string).
- `name`: Display name.
- `version`: Engine version.
- `required_core_version` and `required_sdk_version`: Compatibility info.
- `build_command(self, gui, file) -> list[str]`: Full command list with the program at index 0.

**Optional API**
- `preflight(self, gui, file) -> bool`: Return False to abort.
- `program_and_args(self, gui, file)`: Override if you need custom program/args separation.
- `environment(self) -> dict[str, str] | None`: Inject environment variables.
- `on_success(self, gui, file)`: Post-build hook.
- `required_tools` property: Python and system tools that should be installed.
- `create_tab(self, gui)`: Provide a custom settings tab for your engine.
- `apply_i18n(self, gui, tr)`: Update text when language changes. Provide `languages/<code>.json` in your engine package if you want translations.

**Notes**
- The loader only imports packages under `ENGINES/` that contain `__init__.py`. Plain `.py` files are ignored.
- Keep engines stateless. GUI state is passed in `gui`.
