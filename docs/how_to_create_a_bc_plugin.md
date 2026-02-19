## **BC Plugin Guide**
## **BCASL = Before Compilation Action System & Loader.**

**Overview**
A BC plugin (BCASL) is a package placed in `Plugins/` and executed before compilation. It registers automatically, respects execution order (priority, tags, dependencies), and uses `PreCompileContext` to work with the workspace.

**Discovery And Loading**
- Plugins are discovered in `Plugins/<plugin_name>/`.
- The folder must contain an `__init__.py`.
- The loader imports each package and detects plugins via `@bc_register` or `bcasl_register(manager)`.
- If `bcasl.yml` is missing, a default file is generated.

**Package Layout**
- `Plugins/<plugin_name>/__init__.py`: main plugin code.
- Optional internal modules: helpers, config, assets.

**Recommended Registration (Decorator)**
```python
from __future__ import annotations

from bcasl import bc_register
from Plugins_SDK.BcPluginContext import BcPluginBase, PluginMeta, PreCompileContext
from Plugins_SDK.GeneralContext import Dialog

log = Dialog()

META = PluginMeta(
    id="example.clean",
    name="Example Clean",
    version="0.1.0",
    description="Remove .pyc files before build",
    author="You",
    tags=("clean",),
    required_bcasl_version="2.0.0",
    required_core_version="1.0.0",
    required_plugins_sdk_version="1.0.0",
    required_bc_plugin_context_version="1.0.0",
    required_general_context_version="1.0.0",
)


@bc_register
class ExampleClean(BcPluginBase):
    meta = META

    def __init__(self):
        super().__init__(META)

    def on_pre_compile(self, ctx: PreCompileContext) -> None:
        if not ctx.is_workspace_valid():
            log.log_warn("Workspace not valid or bcasl.yml missing")
            return
        for pyc in ctx.iter_files(["**/*.pyc"], ctx.get_exclude_patterns()):
            try:
                pyc.unlink()
            except Exception as exc:
                log.log_warn(f"Failed to remove {pyc}: {exc}")
```

**Legacy Registration (Function)**
```python
from bcasl import BCASL
from Plugins_SDK.BcPluginContext import BcPluginBase, PluginMeta

class MyPlugin(BcPluginBase):
    meta = PluginMeta(id="legacy", name="Legacy", version="1.0.0")
    def on_pre_compile(self, ctx):
        pass


def bcasl_register(manager: BCASL) -> None:
    manager.add_plugin(MyPlugin())
```

**PluginMeta And Compatibility**
Important fields.
- `id`: unique and stable id (used in `bcasl.yml`).
- `name`, `version`, `description`, `author`.
- `tags`: used for default ordering when no explicit order is provided.
- `required_*_version`: compatibility requirements (BCASL, Core, SDK, Context).

Validation.
- `bcasl/validator.py` provides compatibility utilities.

**Ordering And Dependencies**
- `priority`: lower runs earlier.
- `requires`: list of required plugin IDs.
- `tags`: used for default ordering if `plugin_order` is absent.
- If a dependency cycle is found, BCASL falls back to a safe ordering.

**Configuration (bcasl.yml)**
BCASL reads `bcasl.yml` or `.bcasl.yml` in the workspace root. Only the `.yml` extension is supported.

Example.
```yaml
required_files:
- main.py
file_patterns:
- "**/*.py"
exclude_patterns:
- "**/__pycache__/**"
- "**/*.pyc"
options:
  enabled: true
  sandbox: true
  plugin_timeout_s: 5
  plugin_parallelism: 0
  iter_files_cache: true
  plugin_limits:
    mem_mb: 0
    cpu_time_s: 0
    nofile: 0
    fsize_mb: 0
plugins:
  example.clean:
    enabled: true
    priority: 10
plugin_order:
- example.clean
```

Important notes.
- Keys in `plugins` are the `PluginMeta.id` values.
- `plugin_order` forces ordering and adjusts priority.
- If `bcasl.yml` is missing, a default file is generated.

**Execution Context (PreCompileContext)**
Key methods.
- `get_workspace_root()` and `get_workspace_name()`.
- `get_workspace_config()` and `get_workspace_metadata()`.
- `get_file_patterns()` and `get_exclude_patterns()`.
- `get_required_files()` and `has_required_file(name)`.
- `iter_files(include, exclude)` with optional cache.
- `is_workspace_valid()` checks presence of `bcasl.yml`.

Pattern usage example.
```python
for path in ctx.iter_files(ctx.get_file_patterns(), ctx.get_exclude_patterns()):
    ...
```

**Workspace Switch (Allowed)**
A plugin can request a workspace change via the SDK.

```python
from Plugins_SDK.BcPluginContext import set_selected_workspace

ok = set_selected_workspace("/path/to/new/workspace")
```

Behavior.
- The request is accepted by contract (returns True).
- The target directory is created if needed (best‑effort).
- If the UI is present, the Core applies the change and may stop ongoing builds.
- After requesting a switch, avoid using the old `ctx` for sensitive actions.

**UI And Logs**
- Use `Plugins_SDK.GeneralContext.Dialog` for messages and progress.
- Dialogs are routed through the UI thread and inherit the theme.
- Direct Qt dialogs (like `QProgressDialog`) are blocked in sandboxed runs.

**Sandbox, Timeout, Parallelism**
- If `options.sandbox` is `true`, plugins can run in isolated processes.
- Timeout via `options.plugin_timeout_s` or `PYCOMPILER_BCASL_PLUGIN_TIMEOUT`.
- Parallelism via `options.plugin_parallelism` or `PYCOMPILER_BCASL_PARALLELISM`.
- Resource limits via `options.plugin_limits` (mem, cpu, files, size).

**Plugins_SDK Utilities**
The SDK provides many helpers.
- Project and Python file analysis.
- Dependency and venv inspection.
- Git, Docker, CI, tests, metrics, security utilities.
- Template generation with `Generate_Bc_Plugin_Template()`.

**Best Practices**
- Keep plugins idempotent and error‑tolerant.
- Use `ctx.iter_files` so you respect `exclude_patterns`.
- Avoid relying on global state if sandbox is enabled.
- Minimize external dependencies (stdlib preferred).
