## **PyCompiler_ARK Engine Guide**

Practical reference for building, packaging, and integrating custom compilation engines.

### **Overview**

A PyCompiler_ARK engine is a Python package placed in `engines/` and auto‑loaded at startup. It registers itself with `@engine_register` and provides a `CompilerEngine` that builds the compile command and, optionally, a dedicated UI tab.

### **Discovery And Loading**

- Engines are discovered only in `engines/<engine_id>/`.
- The folder must contain an `__init__.py`.
- Discovery is lazy: the registry loads engines on first real access such as `get_engine`, `available_engines`, `create`, or `bind_tabs`.
- Auto discovery can be disabled with `ARK_ENGINES_AUTO_DISCOVER=0`.

### **Package Layout**

- `engines/<engine_id>/__init__.py`: engine code, registration, UI.
- `engines/<engine_id>/languages/<code>.json`: optional translations.
- `engines/<engine_id>/mapping.json`: optional mapping for the auto‑builder.
- Optional internal modules, assets, helpers.

#### **Minimal Example**

```python
from __future__ import annotations

import sys
from engine_sdk import BuildContext, CompilerEngine, engine_register


@engine_register
class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"
    version = "0.1.0"
    required_core_version = "1.1.0"
    required_sdk_version = "1.0.0"

    @property
    def required_tools(self):
        return {"python": ["mytool"], "system": []}

    def build_command(self, context: BuildContext):
        return [sys.executable, "-m", "mytool", context.entry_point]
```

### **Lifecycle**

1. Package import from `engines/<engine_id>`.
2. `@engine_register` adds the class to the registry.
3. The GUI calls `create_tab` if present to create a tab.
4. When compile is triggered, the engine provides the command via `build_command`.
5. The process runs the command and calls `on_success` on success. **Note**: ARK automatically opens the output directory (from `BuildContext.output_dir`) before calling this hook.

### **Workspace Entrypoint**

The workspace defines its entrypoint in `ark.yml` under `project.entry`.
That value is normalized by Core into `BuildContext.entry_point` and used as the
primary script for compilation. A legacy `build.entrypoint` key is still accepted
as a fallback during normalization, but `project.entry` is the canonical field.

See `docs/ark_main_config.md`.

### **Full API**

Required attributes.

- `id`: stable unique id (used by UI and config).
- `name`: display label.
- `version`: engine version.
- `required_core_version`: minimal Core version.
- `required_sdk_version`: minimal SDK version.

Core methods.

- `build_command(self, context: BuildContext) -> list[str]`: Primary API, full command, index 0 is the program.
- `program_and_args(self, context: BuildContext) -> (program, args) | None`: override if needed.
- `preflight(self, gui, file) -> bool`: checks before compile, return False to abort.
- `environment(self) -> dict[str, str] | None`: env vars to inject.
- `on_success(self, gui, file) -> None`: post‑build hook. Use this for specific cleanup or custom notifications. (The output directory is already opened by ARK).

UI and i18n.

- `create_tab(self, gui) -> (QWidget, label) | None`: adds a tab.
- `engine_translate(self_or_id, key, default=None)`: simple engine-local translation lookup.
- `apply_i18n(self, gui, tr)`: update text on language change.

Tools and dependencies.

- `required_tools`: dict `{ "python": [...], "system": [...] }`.
- `ensure_tools_installed(self, gui)`: installs missing tools when possible.

### **Tools And Dependencies**

- Python tools install through the project venv when available.
- System tools use `SysDependencyManager` (GUI supported) if available.
- Keep the list minimal to avoid unnecessary installs.

### **UI Tab**

- In `create_tab`, create widgets and store them on `self` (ex: `self._opt_onefile`).
- Avoid heavy work in `__init__` to keep loading fast.
- Wire signals locally and prefer `gui.log.append(...)` for logs.
- Do not add your own scroll area unless you need custom behavior; the host wraps large engine tabs automatically.
- **IMPORTANT**: Do not include UI components for **Icon** selection or **Output directory** in your engine tab. These are globally managed in `ark.yml` and passed to your engine via the `BuildContext`. Focus only on engine‑specific flags and options.
- Prefer grouping options with `QGroupBox` sections and compact hints, following the built-in engines layout style.
- Keep widget attribute names stable once they are used by config persistence or compilation logic.

### **Engine Config (get_config / set_config)**

ARK can persist engine UI options per workspace in:
`<workspace>/.ark/<engine_id>/config.json`.

Flow:

- `get_config(gui)` returns a JSON‑serializable dict of current UI state.
- `set_config(gui, cfg)` applies a config dict back to the widgets.
- The Core saves configs on compile and reloads them when a workspace is applied.

#### Minimal example

```python
class MyEngine(CompilerEngine):
    # ...
    def create_tab(self, gui):
        self._opt_fast = QCheckBox("Fast")
        # Global icon and output are handled by ark.yml
        # No need for widgets for those.
        # ...
        return tab, "My Engine"

    def get_config(self, gui) -> dict:
        return {
            "fast": bool(self._opt_fast.isChecked()) if self._opt_fast else False,
        }

    def set_config(self, gui, cfg: dict) -> None:
        if not isinstance(cfg, dict):
            return
        if self._opt_fast and "fast" in cfg:
            self._opt_fast.setChecked(bool(cfg.get("fast")))
```

Notes.

- Keep the config flat and JSON‑safe (bool, str, list, dict).
- Always guard for missing keys and absent widgets.

### **Advanced Config Control (Special Engines)**

Special engines can override where config is stored and whether the UI may save it.

New hooks:

- `config_policy(gui) -> dict`: control permissions
  - `read`: allow Core to load/apply config
  - `write`: allow Core to persist config
  - `ui_edit`: allow UI‑driven save
- `load_config(gui, workspace_dir) -> dict | None`: custom loader
- `save_config(gui, workspace_dir, options) -> bool | None`: custom saver

If a custom loader returns `None`, Core falls back to the default
`.ark/<engine_id>/config.json` behavior. A custom saver that returns `None`
also falls back to the default storage path.

#### Example: custom path + read‑only UI

```python
class SpecialEngine(CompilerEngine):
    id = "special"
    name = "Special"

    def config_policy(self, gui):
        return {"read": True, "write": True, "ui_edit": False}

    def load_config(self, gui, workspace_dir):
        # Load from a custom JSON file
        path = os.path.join(workspace_dir, "special.engine.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_config(self, gui, workspace_dir, options):
        # Persist to a custom path
        path = os.path.join(workspace_dir, "special.engine.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(options or {}, f, indent=2)
        return True
```

**Monolithic Tab Example**
The following dummy engine shows how to build a very large UI tab. The UI will
handle scrolling automatically if needed. You do not need to wrap your engine
tab in an extra scroll area for this use case, because the host UI already adds
scrolling behavior when a tab becomes too large.

```python
from __future__ import annotations

import sys
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QCheckBox,
    QLineEdit,
    QPushButton,
)
from engine_sdk import BuildContext, CompilerEngine, engine_register


@engine_register
class MonolithicEngine(CompilerEngine):
    id = "monolithic"
    name = "Monolithic Engine"
    version = "0.1.0"
    required_core_version = "1.0.0"
    required_sdk_version = "1.0.0"

    def build_command(self, context: BuildContext):
        # Use settings from _config_overrides (populated from get_config or saved JSON)
        cfg = getattr(self, "_config_overrides", {})
        
        cmd = [sys.executable, "-m", "mytool"]
        if cfg.get("fast"):
            cmd.append("--fast")
        if cfg.get("safe"):
            cmd.append("--safe")
        if cfg.get("verbose"):
            cmd.append("--verbose")
        
        output = str(context.output_dir or cfg.get("output_dir") or "").strip()
        if output:
            cmd.extend(["--output", output])
            
        cmd.append(context.entry_point)
        return cmd

    def create_tab(self, gui):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        # ... (GUI setup omitted for brevity, see SDK helpers)
        return root, "Monolithic"
```

**SDK UI Helpers**
Use the shared helpers to reduce duplication across engines.

```python
from engine_sdk import add_form_checkbox, add_icon_selector, add_output_dir

# Inside create_tab(...)
form = QFormLayout()
self._opt_onefile = add_form_checkbox(form, "Mode:", "Onefile", "opt_onefile_dynamic")
self._opt_windowed = add_form_checkbox(form, "Console:", "Windowed", "opt_windowed_dynamic")

self._btn_select_icon, self._icon_path_input = add_icon_selector(
    layout,
    "🎨 Choose icon (.ico)",
    self.select_icon,
    "btn_select_icon_dynamic",
    "icon_path_input_dynamic",
)

self._output_dir_input = add_output_dir(
    layout,
    "Output directory",
    "output_dir_input_dynamic",
)
```

**I18n**

- Add `languages/en.json`, `languages/fr.json`, etc. in your engine package.
- Two supported approaches:
  - simple mode with `engine_translate(...)` for direct key lookup
  - advanced mode with `apply_i18n(...)` for explicit widget refresh on language changes
- The host keeps engine translations synchronized automatically when the language changes.
- See `engines/pyinstaller`, `engines/nuitka`, `engines/cx_freeze` for patterns.
Concrete example (files + code).

`engines/my_engine/languages/en.json`

```json
{
  "tab_title": "My Engine",
  "opt_onefile": "Onefile",
  "opt_clean": "Clean build",
  "btn_icon": "Choose icon",
  "label_output": "Output directory"
}
```

`engines/my_engine/languages/fr.json`

```json
{
  "tab_title": "Mon Moteur",
  "opt_onefile": "Un seul fichier",
  "opt_clean": "Build propre",
  "btn_icon": "Choisir une icone",
  "label_output": "Dossier de sortie"
}
```

`engines/my_engine/__init__.py` (simple mode + live refresh).

```python
from engine_sdk import CompilerEngine, engine_register, engine_translate


@engine_register
class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"

    def create_tab(self, gui):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        self._opt_onefile = QCheckBox()
        self._opt_clean = QCheckBox()
        self._btn_icon = QPushButton()
        self._output_dir = QLineEdit()
        form = QFormLayout()
        form.addRow("", self._opt_onefile)
        form.addRow("", self._opt_clean)
        form.addRow("", self._btn_icon)
        form.addRow("", self._output_dir)
        layout.addLayout(form)

        self.apply_i18n(gui, getattr(gui, "_tr", {}))

        return tab, engine_translate(self, "tab_title", self.name)

    def apply_i18n(self, gui, tr):
        self._opt_onefile.setText(self.engine_translate("opt_onefile", "Onefile"))
        self._opt_clean.setText(self.engine_translate("opt_clean", "Clean build"))
        self._btn_icon.setText(self.engine_translate("btn_icon", "Choose icon"))
        self._output_dir.setPlaceholderText(
            self.engine_translate("label_output", "Output directory")
        )
```

Notes.

- `engine_translate(...)` reads the active engine translation cache and falls back safely.
- `apply_i18n(...)` remains the right place to refresh existing widgets after a language switch.
- `load_engine_language_file(engine_package, lang)` is still available if you need custom/manual loading.
- If a key is missing, always provide a safe fallback string.

**Auto Command Builder (Integrated)**
The auto-builder is integrated into the core compilation pipeline. It can read
`mapping.json` from the engine package, the workspace `engines/<engine_id>/`
folder, or the `PYCOMPILER_MAPPING` environment variable to generate options
from detected modules.

You no longer need to call `compute_auto_for_engine` manually in your `build_command`. The core runner will:

1. Prefer `requirements.txt` or `requirements.in` when present.
2. Fall back to `pyproject.toml` dependencies.
3. Fall back to scanning Python imports.
4. Read the engine mapping and generate the appropriate flags.
5. Insert them into your command, usually before the entry point.

#### **Minimal mapping.json example.**

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

- Top-level keys are package names.
- Engine values accept `str`, `list[str]`, or `dict` with `args` or `flags`.
- `"{import_name}"` is replaced by the matched import name.
- For advanced logic, expose `AUTO_BUILDER`, `get_auto_builder()`, or
  `register_auto_builder()` in `engines/<engine_id>/auto_plugins.py`.

**Deep Examples Catalog (40)**
Each example includes context, intent, and a working pattern. Adjust IDs and labels to match your engine.

1. Minimal engine with a clean tool invocation.

```python
class MinimalToolEngine(CompilerEngine):
    id = "minimal"
    name = "Minimal"
    def build_command(self, context: BuildContext):
        return [sys.executable, "-m", "mytool", context.entry_point]
```

Notes.

- Best for CLI wrappers.
- No UI required.

1. Engine using venv python with fallback.

```python
def build_command(self, context: BuildContext):
    python_exe = sys.executable
    if hasattr(self, "_gui") and self._gui:
        venv_manager = getattr(self._gui, "venv_manager", None)
        if venv_manager:
            venv_path = venv_manager.resolve_project_venv()
            if venv_path:
                python_exe = venv_manager.python_path(venv_path)
    return [python_exe, "-m", "mytool", context.entry_point]
```

Notes.

- Keeps isolation inside the project venv.
- Always safe if venv missing.

1. Preflight to block invalid files.

```python
def preflight(self, gui, file):
    if not os.path.isfile(file):
        log_i18n_level(gui, "error", "Fichier non trouvé", "File not found")
        return False
    return True
```

Notes.

- Fail fast before building command.

1. Environment injection for stable logs.

```python
def environment(self):
    return {"PYTHONIOENCODING": "utf-8", "LC_ALL": "C", "PYTHONUTF8": "0"}
```

Notes.

- Avoids mojibake in logs.

1. Override program_and_args for a non‑Python tool.

```python
def program_and_args(self, context: BuildContext):
    exe = "/usr/local/bin/some_tool"
    args = ["--input", context.entry_point]
    return exe, args
```

Notes.

- Bypasses Python modules entirely.

1. Required tools with python + system dependencies.

```python
@property
def required_tools(self):
    return {"python": ["mytool"], "system": ["patchelf", "gcc"]}
```

Notes.

- Use minimal list to avoid heavy installs.

1. on_success with output directory log.

```python
def on_success(self, gui, file):
    out = getattr(self, "_output_dir", None)
    if out and out.text().strip():
        log_i18n_level(gui, "success", f"Sortie: {out.text()}", f"Output: {out.text()}")
```

Notes.

- Keep logs short and actionable.

1. mapping.json for a single library.

```json
{ "numpy": { "pyinstaller": ["--collect-all", "{import_name}"] } }
```

Notes.

- Good for quick wins.

1. mapping.json with aliases.

```json
{ "__aliases__": { "import_to_package": { "cv2": "opencv-python" } } }
```

Notes.

- Detect `cv2` even if requirements mention `opencv-python`.

1. mapping.json using structured args.

```json
{ "Pillow": { "nuitka": { "args": ["--include-package-data={import_name}"] } } }
```

Notes.

- Use `args` or `flags` interchangeably.

1. mapping.json with multiple engines.

```json
{ "numpy": { "pyinstaller": ["--collect-all", "{import_name}"], "nuitka": "--enable-plugin=numpy" } }
```

Notes.

- One file can serve all engines.

1. mapping.json for GUI frameworks.

```json
{ "PySide6": { "nuitka": "--enable-plugin=pyside6", "pyinstaller": ["--collect-all", "{import_name}"] } }
```

Notes.

- Ensure Qt data/plugins are bundled.

1. mapping.json for hidden imports.

```json
{ "PyYAML": { "pyinstaller": ["--hidden-import", "{import_name}"] } }
```

Notes.

- Good for packages with dynamic imports.

1. mapping.json for data packages.

```json
{ "matplotlib": { "nuitka": ["--include-package-data={import_name}"] } }
```

Notes.

- Fix missing data files at runtime.

1. UI: single checkbox option.

```python
self._opt_onefile = QCheckBox("Onefile")
layout.addWidget(self._opt_onefile)
```

Notes.

- Keep labels short.

1. UI: form layout for grouped options.

```python
form = QFormLayout()
form.addRow("Mode:", self._opt_onefile)
layout.addLayout(form)
```

Notes.

- Clean alignment for labels + widgets.

1. UI: output directory input.

```python
self._output_dir = QLineEdit()
self._output_dir.setPlaceholderText("Output directory")
```

Notes.

- Always give a hint.

1. UI: icon selector button.

```python
btn = QPushButton("Choose Icon")
btn.clicked.connect(self.select_icon)
```

Notes.

- Keep the handler small, update a field.

1. UI: store data files list.

```python
self._data_files = []
self._data_files.append(("/path/a.txt", "a.txt"))
```

Notes.

- Use tuples for source/dest.

1. UI: QFileDialog for icon.

```python
path, _ = QFileDialog.getOpenFileName(gui, "Select", "", "*.ico")
if path:
    self._selected_icon = path
```

Notes.

- Validate extension if needed.

1. UI: read state in build_command.

```python
if self._opt_onefile.isChecked():
    cmd.append("--onefile")
```

Notes.

- Only access widgets you created.

1. Design: concise labels and grouping.

```python
self._opt_clean = QCheckBox("Clean")
self._opt_fast = QCheckBox("Fast")
```

Notes.

- Avoid long labels in dense UIs.

1. Design: placeholder and tooltip.

```python
self._output_name.setPlaceholderText("Output name")
self._output_name.setToolTip("Name of the final binary")
```

Notes.

- Tooltips clarify ambiguous options.

1. Design: spacing and stretch.

```python
layout.addLayout(form_layout)
layout.addSpacing(8)
layout.addStretch()
```

Notes.

- Keeps the tab readable at all sizes.

1. Design: avoid heavy work in **init**.

```python
# do not scan files here; use preflight/build_command
```

Notes.

- Keeps startup fast.

1. Design: keep UI responsive.

```python
# long tasks should run in QProcess, not in the GUI thread
```

Notes.

- Avoid freezing the app.

1. I18n: translate labels with gui.tr.

```python
self._opt_onefile.setText(gui.tr("Un seul fichier", "Onefile"))
```

Notes.

- Works even if no language file exists.

1. I18n: simple lookup with engine_translate.

```python
self._opt_onefile.setText(self.engine_translate("onefile_checkbox", "Onefile"))
```

Notes.

- Best default for engine-local labels and placeholders.

1. I18n: apply_i18n hook.

```python
def apply_i18n(self, gui, tr):
    self._opt_onefile.setText(self.engine_translate("onefile", "Onefile"))
```

Notes.

- Keep this hook for live widget refresh; host synchronization stays automatic.

1. Logging with GUI.

```python
gui.log.append("Building...")
```

Notes.

- Avoid noisy logs in loops.

1. Safe fallback when widgets are missing.

```python
opt = getattr(self, "_opt_onefile", None)
if opt and opt.isChecked():
    cmd.append("--onefile")
```

Notes.

- Robust if tab not created.

1. Use gui.workspace_dir.

```python
work = getattr(gui, "workspace_dir", None)
if work:
    cmd.extend(["--work-dir", work])
```

Notes.

- Keep outputs in the project.

1. Normalize output path.

```python
out = os.path.abspath(self._output_dir.text().strip())
cmd.extend(["--output-dir", out])
```

Notes.

- Avoid relative path issues.

1. Avoid duplicate args.

```python
if "--onefile" not in cmd:
    cmd.append("--onefile")
```

Notes.

- Helpful when merging auto args.

1. Build command by concatenation.

```python
cmd = [python_path, "-m", "tool"] + extra_args + [file]
```

Notes.

- Simple and readable.

1. Auto builder plugin for advanced logic.

```python
# engines/my_engine/auto_plugins.py

def get_auto_builder():
    def builder(matched, pkg_to_import):
        args = []
        if "torch" in matched:
            args.append("--include-package=torch")
        return args
    return builder
```

Notes.

- Use this when simple mapping is not enough.

1. mapping.json for torch (example).

```json
{ "torch": { "pyinstaller": ["--collect-all", "torch"] } }
```

Notes.

- PyInstaller often needs full collect‑all.

1. Multiple args per package.

```json
{ "numpy": { "nuitka": ["--enable-plugin=numpy", "--include-package=numpy"] } }
```

Notes.

- Use list for ordered args.

1. Detection source (requirements preferred).

```python
# Auto-builder prioritizes `requirements.txt` or `requirements.in` when present.
```

Notes.

- Keeps build consistent with declared deps.

1. Auto report for debugging.

```bash
PYCOMPILER_AUTO_REPORT=1
```

Notes.

- Produces a JSON report in the workspace.

**Best Practices**

- Keep engines stateless and drive behavior from `gui` and the target file.
- Validate paths, handle exceptions, and log clearly.
- Provide safe defaults when widgets are missing.
- Use `CompilerCore.dry_run` when helpful.
