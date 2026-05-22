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
        # ctx.root est un objet Path pointant vers la racine du workspace
        # iter_files() utilise par défaut les patterns d'inclusion/exclusion du projet
        for pyc in ctx.iter_files(["**/*.pyc"]):
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
For plugin authors, `bcasl.yml` is the canonical workspace config file.
`PreCompileContext` helpers and validity checks rely on it directly, so it is
the format you should target in examples and real plugin code.

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
- If `bcasl.yml` is missing, a default file is generated.
- In plugin code, assume `bcasl.yml` lives at the workspace root.

**Execution Context (PreCompileContext)**
Key properties and methods.
- `root`: Path object pointant vers la racine du workspace.
- `name`: Nom du dossier workspace.
- `config`: Dictionnaire complet de configuration (`bcasl.yml`).
- `build_context`: Objet `BuildContext` contenant les paramètres de compilation (si disponible).
- `file_patterns`: Patterns d'inclusion définis.
- `exclude_patterns`: Patterns d'exclusion définis.
- `iter_files(include, exclude)`: Itérateur optimisé (respecte les exclusions par défaut).

Usage du BuildContext :
```python
def on_pre_compile(self, ctx: PreCompileContext) -> None:
    if ctx.build_context:
        # Accès au dossier de sortie défini dans ark.yml ou le verrou
        output_dir = ctx.build_context.output_dir
        ...
```

*Exemple concret : Le plugin **OutputCleaner** utilise `ctx.build_context.output_dir` pour vider le dossier de sortie avant la compilation.*

Usage simplifié :
```python
# Parcourt tous les fichiers du projet selon la config bcasl.yml
for path in ctx.iter_files():
    ...

# Recherche spécifique tout en respectant les exclusions globales
for path in ctx.iter_files(["**/*.json"]):
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

**Plugin UI Config Tabs**
BCASL can expose per‑plugin configuration tabs in the BCASL config UI.

Implement:
```python
def build_config_tab(self, parent, ctx, config):
    # return QWidget or (title, widget) or (title, widget, on_save)
    ...
```

Notes.
- `config` is a dict to read/write.
- `on_save(config_dict)` can return an updated dict.
- Saved under `plugins.<id>.config` in `bcasl.yml`.

**Plugin i18n (GeneralContext)**
Plugins can use the SDK i18n system with a `languages/` folder in the plugin package.
The Core now propagates language changes to the Plugin SDK automatically, and the
SDK loads translations for all plugins found in `Plugins/` (by folder name).

Example layout:
```
Plugins/MyPlugin/
  __init__.py
  languages/
    en.json
    fr.json
```

Load and use (with live updates when the language changes):
```python
from Plugins_SDK.GeneralContext import (
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
- Note: Global timeout and parallelism are no longer supported to ensure sequential stability.

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
