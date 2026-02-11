**PyCompiler_ARK Engine Guide**
Practical reference for building, packaging, and integrating custom compilation engines.

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
- If your engine tab becomes large, wrap it in a scroll area so the UI stays usable.

**Monolithic Tab Example**
The following dummy engine shows how to build a very large UI tab with a scroll area to keep it usable.
```python
from __future__ import annotations

import sys
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QFormLayout,
    QCheckBox,
    QLineEdit,
    QPushButton,
)
from engine_sdk import CompilerEngine, engine_register


@engine_register
class MonolithicEngine(CompilerEngine):
    id = "monolithic"
    name = "Monolithic Engine"
    version = "0.1.0"
    required_core_version = "1.0.0"
    required_sdk_version = "1.0.0"

    def build_command(self, gui, file):
        cmd = [sys.executable, "-m", "mytool"]
        if getattr(self, "_opt_fast", None) and self._opt_fast.isChecked():
            cmd.append("--fast")
        if getattr(self, "_opt_safe", None) and self._opt_safe.isChecked():
            cmd.append("--safe")
        if getattr(self, "_opt_verbose", None) and self._opt_verbose.isChecked():
            cmd.append("--verbose")
        output = getattr(self, "_output_dir", None)
        if output and output.text().strip():
            cmd.extend(["--output", output.text().strip()])
        cmd.append(file)
        return cmd

    def create_tab(self, gui):
        root = QWidget()
        root_layout = QVBoxLayout(root)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)

        # Section 1: basic options
        basic = QFormLayout()
        self._opt_fast = QCheckBox("Fast mode")
        self._opt_safe = QCheckBox("Safe mode")
        self._opt_verbose = QCheckBox("Verbose logs")
        basic.addRow("Fast:", self._opt_fast)
        basic.addRow("Safe:", self._opt_safe)
        basic.addRow("Verbose:", self._opt_verbose)
        content_layout.addLayout(basic)

        # Section 2: output settings
        output = QFormLayout()
        self._output_dir = QLineEdit()
        self._output_dir.setPlaceholderText("Output directory")
        output.addRow("Output:", self._output_dir)
        content_layout.addLayout(output)

        # Section 3: extra controls (simulate large UI)
        extras = QFormLayout()
        self._opt_a = QCheckBox("Feature A")
        self._opt_b = QCheckBox("Feature B")
        self._opt_c = QCheckBox("Feature C")
        extras.addRow("Feature A:", self._opt_a)
        extras.addRow("Feature B:", self._opt_b)
        extras.addRow("Feature C:", self._opt_c)
        content_layout.addLayout(extras)

        # Section 4: actions
        btn = QPushButton("Reset to defaults")
        btn.clicked.connect(self._reset_defaults)
        content_layout.addWidget(btn)
        content_layout.addStretch()

        return root, "Monolithic"

    def _reset_defaults(self):
        for attr in ("_opt_fast", "_opt_safe", "_opt_verbose", "_opt_a", "_opt_b", "_opt_c"):
            w = getattr(self, attr, None)
            if w:
                w.setChecked(False)
        if getattr(self, "_output_dir", None):
            self._output_dir.setText("")
```
**I18n**
- Add `languages/en.json`, `languages/fr.json`, etc. in your engine package.
- Use `resolve_language_code` and `load_engine_language_file` (SDK) to load translations.
- See `ENGINES/pyinstaller`, `ENGINES/nuitka`, `ENGINES/cx_freeze` for patterns.
Concrete example (files + code).

`ENGINES/my_engine/languages/en.json`
```json
{
  "tab_title": "My Engine",
  "opt_onefile": "Onefile",
  "opt_clean": "Clean build",
  "btn_icon": "Choose icon",
  "label_output": "Output directory"
}
```

`ENGINES/my_engine/languages/fr.json`
```json
{
  "tab_title": "Mon Moteur",
  "opt_onefile": "Un seul fichier",
  "opt_clean": "Build propre",
  "btn_icon": "Choisir une icone",
  "label_output": "Dossier de sortie"
}
```

`ENGINES/my_engine/__init__.py` (extract).
```python
from engine_sdk import CompilerEngine, engine_register, load_engine_language_file


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

        # Apply translations on creation
        tr = load_engine_language_file(self.id, getattr(gui, "current_language", "en"))
        self.apply_i18n(gui, tr)

        return tab, self.name

    def apply_i18n(self, gui, tr):
        self._opt_onefile.setText(tr.get("opt_onefile", "Onefile"))
        self._opt_clean.setText(tr.get("opt_clean", "Clean build"))
        self._btn_icon.setText(tr.get("btn_icon", "Choose icon"))
        self._output_dir.setPlaceholderText(tr.get("label_output", "Output directory"))
```

Notes.
- `load_engine_language_file(engine_id, lang)` loads `languages/<lang>.json` from the engine package.
- If a key is missing, always provide a safe fallback string.

**Auto Command Builder (Optional)**
The auto‑builder can read a `mapping.json` to generate engine options from detected imports.

Recommended usage (inside `build_command`).
```python
from engine_sdk import compute_auto_for_engine

# ...
auto_args = compute_auto_for_engine(gui, self.id)
if auto_args:
    cmd.extend(auto_args)
```

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

**Deep Examples Catalog (40)**
Each example includes context, intent, and a working pattern. Adjust IDs and labels to match your engine.

1. Minimal engine with a clean tool invocation.
```python
class MinimalToolEngine(CompilerEngine):
    id = "minimal"
    name = "Minimal"
    def build_command(self, gui, file):
        return [sys.executable, "-m", "mytool", file]
```
Notes.
- Best for CLI wrappers.
- No UI required.

2. Engine using venv python with fallback.
```python
def build_command(self, gui, file):
    venv = gui.venv_manager.resolve_project_venv() if gui.venv_manager else None
    py = gui.venv_manager.python_path(venv) if venv else sys.executable
    return [py, "-m", "mytool", file]
```
Notes.
- Keeps isolation inside the project venv.
- Always safe if venv missing.

3. Preflight to block invalid files.
```python
def preflight(self, gui, file):
    if not os.path.isfile(file):
        gui.log.append("File not found")
        return False
    if not file.endswith(".py"):
        gui.log.append("Not a Python file")
        return False
    return True
```
Notes.
- Fail fast before building command.

4. Environment injection for stable logs.
```python
def environment(self):
    return {"PYTHONIOENCODING": "utf-8", "LC_ALL": "C", "PYTHONUTF8": "0"}
```
Notes.
- Avoids mojibake in logs.

5. Override program_and_args for a non‑Python tool.
```python
def program_and_args(self, gui, file):
    exe = "/usr/local/bin/some_tool"
    args = ["--input", file]
    return exe, args
```
Notes.
- Bypasses Python modules entirely.

6. Required tools with python + system dependencies.
```python
@property
def required_tools(self):
    return {"python": ["mytool"], "system": ["patchelf", "gcc"]}
```
Notes.
- Use minimal list to avoid heavy installs.

7. on_success with output directory log.
```python
def on_success(self, gui, file):
    out = getattr(self, "_output_dir", None)
    if out and out.text().strip():
        gui.log.append(f"Output: {out.text().strip()}")
```
Notes.
- Keep logs short and actionable.

8. Auto‑mapping in build_command.
```python
auto_args = compute_auto_for_engine(gui, self.id)
if auto_args:
    cmd.extend(auto_args)
```
Notes.
- Zero hardcoded package list.

9. mapping.json for a single library.
```json
{ "numpy": { "pyinstaller": ["--collect-all", "{import_name}"] } }
```
Notes.
- Good for quick wins.

10. mapping.json with aliases.
```json
{ "__aliases__": { "import_to_package": { "cv2": "opencv-python" } } }
```
Notes.
- Detect `cv2` even if requirements mention `opencv-python`.

11. mapping.json using structured args.
```json
{ "Pillow": { "nuitka": { "args": ["--include-package-data={import_name}"] } } }
```
Notes.
- Use `args` or `flags` interchangeably.

12. mapping.json with multiple engines.
```json
{ "numpy": { "pyinstaller": ["--collect-all", "{import_name}"], "nuitka": "--enable-plugin=numpy" } }
```
Notes.
- One file can serve all engines.

13. mapping.json for GUI frameworks.
```json
{ "PySide6": { "nuitka": "--enable-plugin=pyside6", "pyinstaller": ["--collect-all", "{import_name}"] } }
```
Notes.
- Ensure Qt data/plugins are bundled.

14. mapping.json for hidden imports.
```json
{ "PyYAML": { "pyinstaller": ["--hidden-import", "{import_name}"] } }
```
Notes.
- Good for packages with dynamic imports.

15. mapping.json for data packages.
```json
{ "matplotlib": { "nuitka": ["--include-package-data={import_name}"] } }
```
Notes.
- Fix missing data files at runtime.

16. UI: single checkbox option.
```python
self._opt_onefile = QCheckBox("Onefile")
layout.addWidget(self._opt_onefile)
```
Notes.
- Keep labels short.

17. UI: form layout for grouped options.
```python
form = QFormLayout()
form.addRow("Mode:", self._opt_onefile)
layout.addLayout(form)
```
Notes.
- Clean alignment for labels + widgets.

18. UI: output directory input.
```python
self._output_dir = QLineEdit()
self._output_dir.setPlaceholderText("Output directory")
```
Notes.
- Always give a hint.

19. UI: icon selector button.
```python
btn = QPushButton("Choose Icon")
btn.clicked.connect(self.select_icon)
```
Notes.
- Keep the handler small, update a field.

20. UI: store data files list.
```python
self._data_files = []
self._data_files.append(("/path/a.txt", "a.txt"))
```
Notes.
- Use tuples for source/dest.

21. UI: QFileDialog for icon.
```python
path, _ = QFileDialog.getOpenFileName(gui, "Select", "", "*.ico")
if path:
    self._selected_icon = path
```
Notes.
- Validate extension if needed.

22. UI: read state in build_command.
```python
if self._opt_onefile.isChecked():
    cmd.append("--onefile")
```
Notes.
- Only access widgets you created.

23. Design: concise labels and grouping.
```python
self._opt_clean = QCheckBox("Clean")
self._opt_fast = QCheckBox("Fast")
```
Notes.
- Avoid long labels in dense UIs.

24. Design: placeholder and tooltip.
```python
self._output_name.setPlaceholderText("Output name")
self._output_name.setToolTip("Name of the final binary")
```
Notes.
- Tooltips clarify ambiguous options.

25. Design: spacing and stretch.
```python
layout.addLayout(form_layout)
layout.addSpacing(8)
layout.addStretch()
```
Notes.
- Keeps the tab readable at all sizes.

26. Design: avoid heavy work in __init__.
```python
# do not scan files here; use preflight/build_command
```
Notes.
- Keeps startup fast.

27. Design: keep UI responsive.
```python
# long tasks should run in QProcess, not in the GUI thread
```
Notes.
- Avoid freezing the app.

28. I18n: translate labels with gui.tr.
```python
self._opt_onefile.setText(gui.tr("Un seul fichier", "Onefile"))
```
Notes.
- Works even if no language file exists.

29. I18n: apply_i18n hook.
```python
def apply_i18n(self, gui, tr):
    self._opt_onefile.setText(tr.get("onefile", "Onefile"))
```
Notes.
- Use engine language files.

30. Logging with GUI.
```python
gui.log.append("Building...")
```
Notes.
- Avoid noisy logs in loops.

31. Safe fallback when widgets are missing.
```python
opt = getattr(self, "_opt_onefile", None)
if opt and opt.isChecked():
    cmd.append("--onefile")
```
Notes.
- Robust if tab not created.

32. Use gui.workspace_dir.
```python
work = getattr(gui, "workspace_dir", None)
if work:
    cmd.extend(["--work-dir", work])
```
Notes.
- Keep outputs in the project.

33. Normalize output path.
```python
out = os.path.abspath(self._output_dir.text().strip())
cmd.extend(["--output-dir", out])
```
Notes.
- Avoid relative path issues.

34. Avoid duplicate args.
```python
if "--onefile" not in cmd:
    cmd.append("--onefile")
```
Notes.
- Helpful when merging auto args.

35. Build command by concatenation.
```python
cmd = [python_path, "-m", "tool"] + extra_args + [file]
```
Notes.
- Simple and readable.

36. Auto builder plugin for advanced logic.
```python
# ENGINES/my_engine/auto_plugins.py

def get_auto_builder():
    def builder(matched, pkg_to_import):
        args = []
        if "torch" in matched:
            args.append("--include-package=torch")
        return args
    return builder
```
Notes.
- Use when simple mapping is not enough.

37. mapping.json for torch (example).
```json
{ "torch": { "pyinstaller": ["--collect-all", "torch"] } }
```
Notes.
- PyInstaller often needs full collect‑all.

38. Multiple args per package.
```json
{ "numpy": { "nuitka": ["--enable-plugin=numpy", "--include-package=numpy"] } }
```
Notes.
- Use list for ordered args.

39. Detection source (requirements preferred).
```python
# Auto builder prioritizes requirements.txt when present
```
Notes.
- Keeps build consistent with declared deps.

40. Auto report for debugging.
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
