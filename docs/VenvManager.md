# Technical Documentation: Virtual Environment Manager (`VenvManager`)

---

## 1. Overview & Architectural Vision

The `VenvManager` system in **PyCompiler_ARK** handles virtual environment detection, creation, and management for workspace projects.

### Key Architectural Principles:
- **Strict Decoupling**: Python code (`Manager.py`, `config.py`, `executor.py`) contains **no hardcoded manager names** (`poetry`, `pip`, `uv`, etc.) or hardcoded detection rules (`if os.path.exists(...)`).
- **Declarative YAML Configuration**: All detection rules, executors, and command definitions are maintained exclusively in the central configuration file `pycompiler_ark/data/VenvManagers.yml`.
- **3-Tier Resolution Strategy**:
  1. **Tier 1 (User Preference)**: Reads `.ark/pref.json` (`"manager"` and `"venv_path"` keys).
  2. **Tier 2 (Automatic Detection)**: Dynamically evaluates workspace indicator files and priority rules defined in YAML.
  3. **Tier 3 (Default Fallback)**: Uses the default fallback manager configured in system (`self._config.get_default_manager()`).

---

## 2. YAML Schema Specification (`VenvManagers.yml`)

The file `pycompiler_ark/data/VenvManagers.yml` registers all available environment managers:

```yaml
managers:

  poetry:
    executor:
      type: executable
      executable: poetry
    detection:
      priority: 100
      files:
        - pyproject.toml
      patterns:
        pyproject.toml: "[tool.poetry]"
    commands:
      create_venv:
        - env
        - use
        - "{python}"
      get_venv_path:
        - env
        - info
        - -p
      install:
        - install
      add:
        - add
      check:
        - check

  pip:
    executor:
      type: python_module
      module: pip
    executors:
      create_venv:
        type: python_module
        module: venv
    detection:
      priority: 10
      files:
        - requirements.txt
        - setup.py
    commands:
      create_venv:
        - "{venv_path}"
      install:
        - install
        - -r
      add:
        - install
      check:
        - check
```

### Field Definitions:

- `executor`: Defines the primary command executor (`python_module` or `executable`).
- `executors`: Optional action-specific executor overrides (e.g., `create_venv` for `pip` using the `venv` module).
- `detection`:
  - `priority` *(integer)*: Evaluation priority order (higher priority values are evaluated first).
  - `files` *(list)*: Indicator files located at workspace root.
  - `patterns` *(dictionary)*: Required substring/pattern in target indicator file (e.g., `[tool.poetry]` in `pyproject.toml`).
- `commands`: Argument lists for actions (`create_venv`, `get_venv_path`, `install`, `add`, `check`).
  - Supports dynamic placeholders: `{python}` (target Python interpreter) and `{venv_path}` (target virtual environment path).

---

## 3. Core Engine Components (`pycompiler_ark/Core/Venv_Manager/`)

### A. Command Executors (`executor.py`)
- `PythonModuleExecutor`: Resolves commands in the form `<python_interpreter> -m <module> <args...>`.
- `ExecutableExecutor`: Resolves standalone executables `<executable> <args...>`.
- `ExecutorFactory`: Dynamically instantiates the correct executor from YAML configuration.

### B. Configuration Parser (`config.py`)
- `get_available_managers()`: Returns available manager names.
- `get_default_manager()`: Retrieves default manager (lowest priority or configured fallback).
- `get_detection_rules(manager_name)`: Returns normalized detection rules.
- `detect_manager_for_workspace(workspace_dir)`: Evaluates workspace indicator files and patterns in priority order and returns matching manager.

### C. Manager Engine (`Manager.py`)
- `resolve_workspace_manager(workspace_dir)`: Dynamically resolves workspace manager and updates `self._detected_manager`.
- `_query_manager_venv_path(base_dir)`: Dynamically queries manager executable via YAML `get_venv_path` command to locate external virtualenvs (e.g., Poetry cache).
- `_prepare_manager_command(action, extra_args, python_exe, kwargs)`: Builds `(program, args)` tuple with placeholder substitution for `{python}` and `{venv_path}`.
- `save_workspace_pref(workspace_dir)`: Persists active manager and environment selection into `.ark/pref.json`.

---

## 4. GUI and CLI Integration

- **GUI (`VenvDialog.py` / `VenvManagerUI`)**:
  - Registers UI delegates (`_ui_callbacks`) to display progress dialogs (`ProgressDialog`), stream standard output/error logs, and show confirmation prompts (`QMessageBox`).
- **CLI (`Ui/Cli/app.py`)**:
  - Automatically triggers dynamic manager resolution during workspace build or initialization operations.
- **Automatic Persistence**:
  - Whenever a virtual environment is created or detected, preferences are persisted to `.ark/pref.json`:
    ```json
    {
      "manager": "poetry",
      "venv_mode": "venv",
      "venv_path": "/path/to/virtualenv"
    }
    ```

---

## 5. How to Add a New Environment Manager

To add support for a new custom environment manager, **no Python code changes are required**.

Simply add its definition entry to `VenvManagers.yml`:

```yaml
  custom_manager:
    executor:
      type: executable
      executable: custom_cmd
    detection:
      priority: 90
      files:
        - custom_lock.json
        - pyproject.toml
      patterns:
        pyproject.toml: "[tool.custom]"
    commands:
      create_venv:
        - env
        - create
        - "{venv_path}"
      get_venv_path:
        - env
        - info
        - --path
      install:
        - install
      add:
        - add
      check:
        - check
```
