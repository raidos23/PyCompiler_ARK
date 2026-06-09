## **PyCompiler ARK BCASL Plugin Guide**

**BCASL = Before-Compilation Action System & Loader.**

**Overview**
A BC plugin is a package placed in `pycompiler_ark/Plugins/` and executed before compilation. It registers automatically, respects execution order (priority, tags, dependencies), and uses `PreCompileContext` to work with the workspace.

The BCASL loader and runtime are **pure-Python**. They run in headless environments (CLI, CI) without Qt dependencies. UI integration is provided separately by the ARK GUI.

**Discovery And Loading**

- Plugins are discovered in `pycompiler_ark/Plugins/<plugin_name>/`.
- The folder must contain an `__init__.py`.
- The loader imports each package and detects plugins via `@bc_register`; legacy registration helpers remain available for older plugins when needed.
- If `bcasl.yml` is missing, BCASL generates a best-effort default file when it runs.

**Package Layout**

- `pycompiler_ark/Plugins/<plugin_name>/__init__.py`: main plugin code.
- Optional internal modules: helpers, config, assets.

**Recommended Registration (Decorator)**

```python
from __future__ import annotations

from pycompiler_ark.Plugins_SDK.BcPluginContext import (
    BcPluginBase,
    PluginMeta,
    PreCompileContext,
    bc_register,
)
from pycompiler_ark.Plugins_SDK.GeneralContext import Dialog

log = Dialog()

META = PluginMeta(
    id="example.clean",
    name="Example Clean",
    version="0.1.0",
    description="Remove .pyc files before build",
    author="You",
    tags=("clean",),
    required_bcasl_version="1.0.0",
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
        # ctx.root is a Path to the workspace root.
        # iter_files() uses the configured include/exclude patterns by default.
        for pyc in ctx.iter_files(["**/*.pyc"]):
            try:
                pyc.unlink()
            except Exception as exc:
                log.log_warn(f"Failed to remove {pyc}: {exc}")
```

**Legacy Registration (Function)**

Prefer `@bc_register` for new plugins. The SDK keeps registration inside the
plugin package, so you do not need to import host internals directly.

**PluginMeta And Compatibility**
Important fields.

- `id`: unique, stable id used in `bcasl.yml`.
- `name`, `version`, `description`, `author`.
- `tags`: used for default ordering when no explicit order is provided.
- `required_*_version`: compatibility requirements (BCASL, Core, SDK, Context).
- Tags are normalized to lowercase tuples by the SDK, so use them as stable
  ordering hints rather than free-form labels.
- `PluginMeta` defaults all SDK compatibility fields to `1.0.0`, which keeps
  plugin manifests aligned with the current PyCompiler ARK contract.

Validation.

- `pycompiler_ark.bcasl.validator` provides compatibility utilities.

**Ordering And Dependencies**

- `priority`: lower runs earlier.
- `requires`: list of required plugin IDs.
- `tags`: used for default ordering if `plugin_order` is absent.
- If a dependency cycle is found, BCASL falls back to a safe ordering.

**Configuration (bcasl.yml)**
For plugin authors, `bcasl.yml` is the canonical workspace config file.
`PreCompileContext` helpers and validation logic read it directly, so target
this format in examples and plugin code.

Example.

```yaml
file_patterns:
- "**/*.py"
exclude_patterns:
- "**/__pycache__/**"
- "**/*.pyc"
options:
  sandbox: true
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

- Global BCASL activation is managed by **`ark.yml`** (`plugins.bcasl_enabled`).
- Keys in `plugins` are the `PluginMeta.id` values.
- `plugin_order` forces ordering and adjusts priority.
- If `bcasl.yml` is missing, the workspace tools can generate a default file.
- In plugin code, assume `bcasl.yml` lives at the workspace root.

**Execution Context (PreCompileContext)**
Key properties and methods.

- `root`: Path object pointing to the workspace root.
- `project_root`: Alias for `root` kept for compatibility.
- `name`: Workspace folder name.
- `config`: Full `bcasl.yml` configuration dictionary.
- `metadata`: Additional execution metadata collected by the loader.
- `build_context`: `BuildContext` with compilation settings, when available.
- `build_context.include_packages`: Packages that ARK has been told to force into the bundle via `build.include`.
- `file_patterns`: Configured include patterns.
- `exclude_patterns`: Configured exclude patterns.
- `iter_files(include, exclude)`: Optimized iterator that respects exclusions by default and can use an internal cache when enabled.
- `iter_files()` uses the active `file_patterns` and `exclude_patterns` by default, so plugin code should not rescan the workspace manually.
- `PreCompileContext` is intentionally source-agnostic: it already represents the workspace state needed by the plugin.

BuildContext usage:

```python
def on_pre_compile(self, ctx: PreCompileContext) -> None:
    if ctx.build_context:
        # Access the output directory defined in ark.yml or the lock file.
        output_dir = ctx.build_context.output_dir
        ...
```

*Example: the **OutputCleaner** plugin uses `ctx.build_context.output_dir` to clear the output directory before compilation.*

Related SDK capabilities:

- `BcPluginBase.requires` declares plugin dependencies that the loader can use
  when sorting execution order.
- `BcPluginBase.priority` is a numeric ordering hint; lower values run earlier.
- `ExecutionReport` is available for aggregated run results when you need to
  inspect per-plugin success and timing.
- `Generate_Bc_Plugin_Template()` creates a ready-to-use plugin scaffold with
  the current SDK imports and metadata defaults.

Simplified usage:

```python
# Iterate over all project files using the bcasl.yml configuration.
for path in ctx.iter_files():
    ...

# Search specific files while still respecting global exclusions.
for path in ctx.iter_files(["**/*.json"]):
    ...
```

**Workspace Switch (Allowed)**
A plugin can request a workspace change via the SDK.

```python
from pycompiler_ark.Plugins_SDK.BcPluginContext import set_selected_workspace

ok = set_selected_workspace("/path/to/new/workspace")
```

Behavior.

- The request is accepted by contract (returns `True`).
- The target directory is created if needed, best effort.
- If the UI is present, the Core applies the change and may stop ongoing builds.
- After requesting a switch, avoid using the old `ctx` for sensitive actions.

**UI And Logs**

- Use `pycompiler_ark.Plugins_SDK.GeneralContext.Dialog` for messages and progress.
- When running in the GUI, dialogs are routed through the UI thread and inherit the theme.
- In headless/CLI mode, these are routed to standard output.
- **Important**: Avoid direct Qt imports to remain compatible with headless execution. Direct Qt dialogs such as `QProgressDialog` are not supported in sandboxed or headless runs.

**Plugin UI Config Tabs**
BCASL can expose per-plugin configuration tabs in the BCASL config UI.

Implement:

```python
def create_tab(self, parent, ctx, config):
    # return QWidget or (title, widget) or (title, widget, on_save)
    ...
```

Notes.

- `config` is a dict to read/write.
- `on_save(config_dict)` can return an updated dict.
- Each plugin entry stores its config in the `config` field inside the `plugins` collection in `bcasl.yml`.
- `create_tab(...)` may return a widget, a `(title, widget)` tuple, a `(title, widget, on_save)` tuple, or a dict with `title`, `widget`, and `on_save`.

**Plugin i18n (GeneralContext)**
Plugins can use the SDK i18n system with a `languages/` folder in the plugin package.
The Core propagates language changes to the Plugin SDK, and the SDK loads
translations for plugins found in `pycompiler_ark/Plugins/` by folder name.

Example layout:

```
pycompiler_ark/Plugins/MyPlugin/
  __init__.py
  languages/
    en.json
    fr.json
```

Load and use, with live updates when the language changes:

```python
from pycompiler_ark.Plugins_SDK.GeneralContext import (
    get_language_code, load_plugin_language_file,
    register_plugin_translations, register_i18n_handler, translate,
)

def _load_i18n():
    data = load_plugin_language_file(__package__, get_language_code())
    register_plugin_translations("my.plugin.id", data)

_load_i18n()
register_i18n_handler(lambda gui, tr: _load_i18n())

label = translate("my.plugin.id", "ui_title", "Default title")
```

Notes.

- The SDK also accepts the plugin folder name as ID (case‑insensitive).
- If a key is missing, `translate()` falls back to the default you pass in.

**Sandbox and Resource Limits**

- If `options.sandbox` is `true`, plugins can run in isolated processes.
- Resource limits via `options.plugin_limits` (mem, cpu, files, size).
- Note: global timeout and parallelism are no longer supported to keep execution sequential.

**Plugins_SDK Utilities**
The SDK provides helpers for:

- Project and Python file analysis.
- Dependency and venv inspection.
- Git, Docker, CI, tests, metrics, security utilities.
- Template generation with `Generate_Bc_Plugin_Template()`.

**Best Practices**

- Keep plugins idempotent and error‑tolerant.
- Use `ctx.iter_files` so you respect `exclude_patterns`.
- Avoid relying on global state if sandbox is enabled.
- Minimize external dependencies (stdlib preferred).
