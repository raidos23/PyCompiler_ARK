# How to Create a Compilation Engine

This guide explains how to implement a **compilation engine** for PyCompiler ARK++ using the Engine SDK.

**What are Compilation Engines?**
Compilation engines are pluggable modules that handle the actual compilation/packaging of Python applications. They integrate with the PyCompiler ARK++ GUI to provide options, execute builds, and manage dependencies. Examples include PyInstaller, Nuitka, and cx_Freeze.

**Note:** This guide is for compilation engines only. For creating BC (Before Compilation) plugins, see [How to Create a BC Plugin](./how_to_create_a_BC_plugin.md).

## Quick Navigation
- [TL;DR](#0-tldr-copy-paste-template)
- [Folder layout](#1-folder-layout)
- [Minimal engine](#2-minimal-engine)
- [Engine registration](#3-engine-registration)
- [Building commands](#4-building-commands)
- [Preflight checks](#5-preflight-checks)
- [GUI integration](#6-gui-integration)
- [Internationalization (i18n)](#7-internationalization-i18n)
- [Testing and debugging](#8-testing-and-debugging)
- [Checklist](#9-developer-checklist)

## 0) TL;DR (copy‑paste template)

Create `ENGINES/my_engine/__init__.py`:

```python
from __future__ import annotations

import os
import sys
from typing import Optional

from engine_sdk import CompilerEngine


class MyEngine(CompilerEngine):
    id = "my_engine"
    name = "My Engine"
    version = "1.0.0"
    required_core_version = "1.0.0"
    required_sdk_version = "1.0.0"

    def preflight(self, gui, file: str) -> bool:
        """Perform preflight checks. Return True if OK, False to abort."""
        try:
            # Check for required tools, dependencies, etc.
            # Log messages using gui.log.append(gui.tr(fr, en))
            return True
        except Exception:
            return False

    def build_command(self, gui, file: str) -> list[str]:
        """Return the full command list [program, arg1, arg2, ...]."""
        return [sys.executable, "-m", "my_engine", file]

    def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
        """Resolve program and args for QProcess. Default implementation works for most cases."""
        cmd = self.build_command(gui, file)
        if not cmd:
            return None
        return cmd[0], cmd[1:]

    def environment(self, gui, file: str) -> Optional[dict[str, str]]:
        """Return environment variables to inject. Return None for no changes."""
        return None

    def create_tab(self, gui):
        """Create and return (widget, label) for engine options tab, or None."""
        return None

    def on_success(self, gui, file: str) -> None:
        """Hook called when build succeeds."""
        pass

    def apply_i18n(self, gui, tr: dict[str, str]) -> None:
        """Apply internationalization to engine UI elements."""
        pass


# Register the engine using the new engine_register function
from engine_sdk import engine_register
engine_register(MyEngine)
```

Create `ENGINES/my_engine/mapping.json`:

```json
{
  "engine_id": "my_engine",
  "engine_name": "My Engine",
  "version": "1.0.0",
  "description": "Description of what this engine does",
  "auto_plugins": []
}
```

## 1) Folder layout

```
<project root>
└── ENGINES/
    └── my_engine/
        ├── __init__.py
        ├── mapping.json
        ├── languages/
        │   ├── en.json
        │   ├── fr.json
        │   └── ...
        └── (optional) other modules
```

**Key Points:**
- Engine directory name should match the engine ID for clarity
- `__init__.py` must define the engine class and call `register()`
- `mapping.json` provides metadata for auto-discovery
- `languages/` directory contains i18n JSON files (optional but recommended)
- Engine class must inherit from `CompilerEngine`

## 2) Minimal engine

A minimal compilation engine requires:

### 2.1) Import necessary classes

```python
from __future__ import annotations

import sys
from typing import Optional

from engine_sdk import CompilerEngine
from Core.engines_loader.registry import register
```

### 2.2) Define the engine class

```python
class MyEngine(CompilerEngine):
    # Required class attributes
    id = "my_engine"                    # Unique identifier
    name = "My Engine"                  # Display name
    version = "1.0.0"                   # Engine version
    required_core_version = "1.0.0"     # Minimum core version
    required_sdk_version = "1.0.0"      # Minimum SDK version

    def build_command(self, gui, file: str) -> list[str]:
        """Return the full command list including program at index 0."""
        return [sys.executable, "-m", "my_engine", file]
```

### 2.3) Register the engine

```python
# At module level, after class definition
from engine_sdk import engine_register
engine_register(MyEngine)
```

**Note:** The old `register` function is still available as an alias for backward compatibility, but `engine_register` is the recommended new name.

### 2.4) Create mapping.json

```json
{
  "engine_id": "my_engine",
  "engine_name": "My Engine",
  "version": "1.0.0",
  "description": "Brief description of the engine",
  "auto_plugins": []
}
```

**Important:**
- The `id` attribute must be unique across all engines
- `build_command()` must return a list with the program at index 0
- `register()` must be called at module level to register the engine
- All version attributes must follow semantic versioning

## 3) Engine registration

### 3.1) Registry API

The `engine_sdk` module provides the registration system via `engine_register`:

```python
from engine_sdk import (
    engine_register,    # Register an engine class (new name)
    register,           # Register an engine class (alias for backward compatibility)
    CompilerEngine,
)

# Register your engine (using new name)
engine_register(MyEngine)

# Later, retrieve it
from Core.engines_loader.registry import get_engine, available_engines, create

engine_cls = get_engine("my_engine")
engine_instance = create("my_engine")
available = available_engines()
```

### 3.2) Registration rules

- **Unique ID:** Each engine must have a unique `id` attribute
- **Conflict handling:** If an engine with the same ID is registered twice:
  - If it's the same class object, registration is a no-op
  - If it's a different class, the new registration is ignored
- **Fail-safe:** Registration failures don't crash the application
- **Lazy instantiation:** Engines are instantiated only when needed

### 3.3) Engine lifecycle

```python
# 1. Engine class is defined and registered
class MyEngine(CompilerEngine):
    id = "my_engine"
    ...

register(MyEngine)

# 2. Engine is discovered by the registry
available = available_engines()  # ["my_engine", ...]

# 3. Engine instance is created when needed
engine = create("my_engine")

# 4. Engine methods are called during build process
engine.preflight(gui, file)
cmd = engine.build_command(gui, file)
engine.on_success(gui, file)
```

## 4) Building commands

### 4.1) build_command() method

The `build_command()` method must return a complete command list:

```python
def build_command(self, gui, file: str) -> list[str]:
    """
    Build the complete command for compilation.
    
    Args:
        gui: GUI object with workspace info and logging
        file: Path to the Python script to compile
    
    Returns:
        List of command arguments [program, arg1, arg2, ...]
    """
    cmd = [sys.executable, "-m", "my_engine", file]
    
    # Add optional arguments based on GUI state
    try:
        if hasattr(gui, "output_dir_input"):
            output_dir = gui.output_dir_input.text().strip()
            if output_dir:
                cmd.extend(["--output", output_dir])
    except Exception:
        pass
    
    return cmd
```

### 4.2) program_and_args() method

The `program_and_args()` method resolves the executable and arguments for QProcess:

```python
def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
    """
    Resolve program and arguments for QProcess execution.
    
    Default implementation splits build_command() into program and args.
    Override for custom resolution (e.g., venv python, remote execution).
    
    Returns:
        (program_path, [arg1, arg2, ...]) or None to abort
    """
    cmd = self.build_command(gui, file)
    if not cmd:
        return None
    return cmd[0], cmd[1:]
```

**Advanced example with venv resolution:**

```python
def program_and_args(self, gui, file: str) -> Optional[tuple[str, list[str]]]:
    try:
        # Resolve venv python
        vm = getattr(gui, "venv_manager", None)
        if not vm:
            return None
        
        vroot = vm.resolve_project_venv()
        if not vroot:
            gui.log.append(gui.tr("❌ Venv not found", "❌ Venv not found"))
            return None
        
        # Get python from venv
        import platform
        vbin = os.path.join(
            vroot, "Scripts" if platform.system() == "Windows" else "bin"
        )
        python_exe = os.path.join(
            vbin, "python.exe" if platform.system() == "Windows" else "python"
        )
        
        if not os.path.isfile(python_exe):
            gui.log.append(gui.tr("❌ Python not found in venv", "❌ Python not found in venv"))
            return None
        
        cmd = self.build_command(gui, file)
        # Replace sys.executable with venv python
        if cmd and cmd[0].endswith(("python", "python.exe")):
            cmd[0] = python_exe
        
        return python_exe, cmd[1:]
    except Exception:
        return None
```

### 4.3) environment() method

Return environment variables to inject into the build process:

```python
def environment(self, gui, file: str) -> Optional[dict[str, str]]:
    """
    Return environment variables to inject for the build process.
    
    Returns:
        Dict of {VAR_NAME: value} or None for no changes
    """
    env = {}
    
    # Example: Set optimization level
    env["PYTHONOPTIMIZE"] = "2"
    
    # Example: Disable bytecode generation
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    
    return env if env else None
```

## 5) Preflight checks

### 5.1) preflight() method

The `preflight()` method performs checks before compilation:

```python
def preflight(self, gui, file: str) -> bool:
    """
    Perform preflight checks and setup.
    
    Args:
        gui: GUI object with workspace info and logging
        file: Path to the Python script to compile
    
    Returns:
        True if OK to proceed, False to abort build
    """
    try:
        # Check for required tools
        import shutil
        if not shutil.which("my_tool"):
            gui.log.append(gui.tr(
                "❌ my_tool not found in PATH",
                "❌ my_tool not found in PATH"
            ))
            return False
        
        # Check for required dependencies
        try:
            import my_module
        except ImportError:
            gui.log.append(gui.tr(
                "❌ my_module not installed",
                "❌ my_module not installed"
            ))
            return False
        
        gui.log.append(gui.tr(
            "✅ All preflight checks passed",
            "✅ All preflight checks passed"
        ))
        return True
    except Exception as e:
        gui.log.append(gui.tr(
            f"❌ Preflight error: {e}",
            f"❌ Preflight error: {e}"
        ))
        return False
```

### 5.2) Logging in preflight

Use `gui.log.append()` with `gui.tr()` for bilingual logging:

```python
# French and English messages
gui.log.append(gui.tr(
    "🔍 Vérification des dépendances…",
    "🔍 Checking dependencies…"
))

# Use emoji for visual clarity
gui.log.append(gui.tr("✅ Succès", "✅ Success"))
gui.log.append(gui.tr("⚠️ Avertissement", "⚠️ Warning"))
gui.log.append(gui.tr("❌ Erreur", "❌ Error"))
```

### 5.3) System dependency management

For complex system dependencies, use `SysDependencyManager`:

```python
from engine_sdk import SysDependencyManager

def preflight(self, gui, file: str) -> bool:
    try:
        sdm = SysDependencyManager(parent_widget=gui)
        
        # Detect package manager (Linux)
        pm = sdm.detect_linux_package_manager()
        if not pm:
            gui.log.append(gui.tr(
                "❌ Package manager not detected",
                "❌ Package manager not detected"
            ))
            return False
        
        # Install packages
        packages = ["build-essential", "python3-dev"]
        proc = sdm.install_packages_linux(packages, pm=pm)
        
        if proc is None:
            gui.log.append(gui.tr(
                "⏳ Installation in background…",
                "⏳ Installation in background…"
            ))
            return False  # Retry after installation
        
        return True
    except Exception:
        return False
```

## 6) GUI integration

### 6.1) create_tab() method

Create a custom options tab for your engine:

```python
def create_tab(self, gui):
    """
    Create and return a QWidget tab for engine options.
    
    Returns:
        (widget, label_str) or None if no tab needed
    """
    try:
        from PySide6.QtWidgets import (
            QWidget, QVBoxLayout, QHBoxLayout,
            QLabel, QLineEdit, QPushButton, QCheckBox
        )
    except Exception:
        return None
    
    tab = QWidget()
    layout = QVBoxLayout(tab)
    
    # Add controls
    label = QLabel(gui.tr("Output Directory", "Output Directory"))
    layout.addWidget(label)
    
    output_edit = QLineEdit()
    output_edit.setPlaceholderText(gui.tr(
        "Path to output directory",
        "Path to output directory"
    ))
    layout.addWidget(output_edit)
    
    # Store reference for later access in build_command()
    self._output_edit = output_edit
    
    layout.addStretch()
    
    return tab, gui.tr("My Engine", "My Engine")
```

### 6.2) Accessing tab controls in build_command()

```python
def build_command(self, gui, file: str) -> list[str]:
    cmd = [sys.executable, "-m", "my_engine", file]
    
    # Access controls created in create_tab()
    try:
        if hasattr(self, "_output_edit"):
            output_dir = self._output_edit.text().strip()
            if output_dir:
                cmd.extend(["--output", output_dir])
    except Exception:
        pass
    
    return cmd
```

### 6.3) on_success() hook

Execute actions after successful compilation:

```python
def on_success(self, gui, file: str) -> None:
    """Called when build completes successfully."""
    try:
        # Example: Open output directory
        import platform
        import subprocess
        
        output_dir = self._get_output_dir(gui)
        if output_dir and os.path.isdir(output_dir):
            if platform.system() == "Windows":
                os.startfile(output_dir)
            elif platform.system() == "Linux":
                subprocess.run(["xdg-open", output_dir])
            else:
                subprocess.run(["open", output_dir])
    except Exception:
        pass
```

## 7) Internationalization (i18n)

### 7.1) apply_i18n() method

Implement i18n to support multiple languages:

```python
def apply_i18n(self, gui, tr: dict[str, str]) -> None:
    """
    Apply internationalization to engine UI elements.
    
    Args:
        gui: GUI object
        tr: Translation dictionary (may be empty on first call)
    """
    try:
        from Core.engines_loader.registry import resolve_language_code
        
        # Resolve language code
        code = resolve_language_code(gui, tr)
        
        # Load engine-local translations
        lang_data = self._load_language_file(code)
        
        # Apply to UI elements
        if hasattr(self, "_output_label"):
            text = lang_data.get("output_label", "Output Directory")
            self._output_label.setText(text)
    except Exception:
        pass
```

### 7.2) Language files

Create `ENGINES/my_engine/languages/en.json`:

```json
{
  "_meta": {
    "code": "en",
    "name": "English"
  },
  "output_label": "Output Directory",
  "output_placeholder": "Path to output directory",
  "tt_output": "Specify where to save the compiled executable"
}
```

Create `ENGINES/my_engine/languages/fr.json`:

```json
{
  "_meta": {
    "code": "fr",
    "name": "Français"
  },
  "output_label": "Dossier de sortie",
  "output_placeholder": "Chemin du dossier de sortie",
  "tt_output": "Spécifiez où enregistrer l'exécutable compilé"
}
```

### 7.3) Loading language files

```python
def _load_language_file(self, code: str) -> dict:
    """Load language file for the given code."""
    try:
        import importlib.resources as ilr
        import json
        
        pkg = __package__
        lang_data = {}
        
        # Try exact code first
        try:
            with ilr.as_file(
                ilr.files(pkg).joinpath("languages", f"{code}.json")
            ) as p:
                if os.path.isfile(str(p)):
                    with open(str(p), encoding="utf-8") as f:
                        lang_data = json.load(f) or {}
                    return lang_data
        except Exception:
            pass
        
        # Fallback to base language (e.g., "fr" from "fr-CA")
        if "-" in code:
            base = code.split("-", 1)[0]
            try:
                with ilr.as_file(
                    ilr.files(pkg).joinpath("languages", f"{base}.json")
                ) as p:
                    if os.path.isfile(str(p)):
                        with open(str(p), encoding="utf-8") as f:
                            lang_data = json.load(f) or {}
                        return lang_data
            except Exception:
                pass
        
        # Final fallback to English
        try:
            with ilr.as_file(
                ilr.files(pkg).joinpath("languages", "en.json")
            ) as p:
                if os.path.isfile(str(p)):
                    with open(str(p), encoding="utf-8") as f:
                        lang_data = json.load(f) or {}
        except Exception:
            pass
        
        return lang_data
    except Exception:
        return {}
```

## 8) Testing and debugging

### 8.1) Manual testing

1. **Create your engine** in `ENGINES/my_engine/__init__.py`
2. **Launch PyCompiler ARK++** - engine should auto-discover
3. **Check engine appears** in the compiler tabs
4. **Test preflight** - click compile to trigger preflight checks
5. **Test build** - verify command is correct
6. **Check logs** - verify logging output

### 8.2) Debugging tips

**Enable verbose logging:**
```python
def build_command(self, gui, file: str) -> list[str]:
    cmd = [sys.executable, "-m", "my_engine", file]
    gui.log.append(f"DEBUG: Command = {cmd}")
    return cmd
```

**Test command manually:**
```bash
# Run the command directly to verify it works
python -m my_engine /path/to/script.py
```

**Check engine registration:**
```python
from Core.engines_loader.registry import available_engines, get_engine
print(available_engines())  # Should include "my_engine"
print(get_engine("my_engine"))  # Should return your engine class
```

**Test with different workspaces:**
- Test with workspace containing venv
- Test with workspace without venv
- Test with missing dependencies

### 8.3) Common issues

| Issue | Solution |
|-------|----------|
| Engine not appearing in tabs | Check `register()` is called at module level |
| `build_command()` returns wrong path | Verify `sys.executable` or venv resolution |
| Preflight always fails | Check exception handling, add logging |
| Tab controls not updating | Store references in `create_tab()`, access in `build_command()` |
| i18n not working | Verify language files exist and are valid JSON |
| Command fails to execute | Test command manually in terminal |

## 9) Developer checklist

**Engine Structure:**
- [ ] Engine class inherits from `CompilerEngine`
- [ ] All required attributes defined (`id`, `name`, `version`, etc.)
- [ ] `build_command()` implemented and returns valid command list
- [ ] `register()` called at module level
- [ ] `mapping.json` created with correct metadata

**Implementation:**
- [ ] `preflight()` checks for required tools/dependencies
- [ ] `program_and_args()` resolves executable correctly
- [ ] `environment()` returns environment variables if needed
- [ ] `create_tab()` creates UI controls if needed
- [ ] `on_success()` performs post-build actions if needed
- [ ] `apply_i18n()` applies translations if needed
- [ ] Robust error handling throughout
- [ ] Logging uses `gui.tr()` for bilingual messages

**Internationalization:**
- [ ] Language files created in `languages/` directory
- [ ] All UI strings have translations
- [ ] Language code resolution implemented
- [ ] Fallback to English works

**Testing:**
- [ ] Engine auto-discovers in PyCompiler ARK++
- [ ] Preflight checks work correctly
- [ ] Build command is correct
- [ ] Tab controls work (if implemented)
- [ ] i18n works with different languages
- [ ] Error handling is robust
- [ ] Tested with various workspace configurations

**Documentation:**
- [ ] Clear comments explaining engine purpose
- [ ] Documented any special requirements
- [ ] Examples of expected input/output
- [ ] Known limitations documented

## Anti-patterns to avoid

❌ **Don't:**
- Hardcode absolute paths
- Assume workspace structure without validation
- Block the UI thread with long operations
- Ignore exceptions silently
- Use `sys.executable` without considering venv
- Forget to call `register()`
- Return invalid command lists from `build_command()`
- Assume GUI controls exist without checking

✅ **Do:**
- Use relative paths or resolve from workspace
- Validate workspace before using it
- Use async operations for long tasks
- Log errors with informative messages
- Resolve venv python when available
- Call `register()` at module level
- Return complete, valid command lists
- Check for control existence with `hasattr()`

## See Also

- [Engine SDK Documentation](./About_Sdks.md) - Engine SDK API reference
- [ARK Configuration Guide](./ARK_Configuration.md) - Global configuration system
- [How to Create a BC Plugin](./how_to_create_a_BC_plugin.md) - Creating BC plugins
- [Existing Engines](../ENGINES/) - Reference implementations (PyInstaller, Nuitka, cx_Freeze)
