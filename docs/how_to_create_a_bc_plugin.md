**Overview**
BC plugins (BCASL) run before compilation. They are Python packages placed in `Plugins/`, discovered automatically, and executed through the `on_pre_compile` hook.

**Steps**
1. Create a package folder in `Plugins/<plugin_name>/` with an `__init__.py`.
2. Implement a subclass of `BcPluginBase` and decorate it with `@bc_register`.
3. Define a `PluginMeta` with a unique `id`.
4. Configure the plugin in `bcasl.yml` (optional but recommended for ordering and enable/disable).

**Minimal Plugin**
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

**Configuration**
BCASL reads `bcasl.yml` or `.bcasl.yml` in the workspace root. Only the `.yml` extension is supported.
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
plugins:
  example.clean:
    enabled: true
    priority: 10
plugin_order:
- example.clean
```

**Notes**
- Plugin ids come from `PluginMeta.id`, and configuration uses those ids.
- Plugins can also register via a legacy `bcasl_register(manager)` function, but `@bc_register` is preferred.
- Use `Plugins_SDK.GeneralContext.Dialog` for UI interactions and logging. Direct Qt dialogs are blocked in sandboxed runs.
- Timeouts can be controlled with `options.plugin_timeout_s` or the env var `PYCOMPILER_BCASL_PLUGIN_TIMEOUT`.
- Parallelism can be controlled with `options.plugin_parallelism` or the env var `PYCOMPILER_BCASL_PARALLELISM`.
