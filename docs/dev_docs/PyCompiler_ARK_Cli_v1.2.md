# **PyCompiler ARK CLI Specification v1.3**

This document defines the final, streamlined specification for the PyCompiler ARK Command Line Interface.

---

### **1. Philosophy**

The CLI is designed to be simple, predictable, and headless-friendly.

- **Unified Binary**: Use `pycompiler-ark` (or `python pycompiler_ark.py`).
- **Explicit Commands**: No hidden magic; every action requires an explicit command.
- **CLI-First**: All features accessible via GUI are also available via CLI.
- **Reproducibility**: Guaranteed via functional locking comparison.
- **Headless-Ready**: Support for non-interactive execution (CI/CD).

---

### **2. Final Commands**

```bash
# Workspace (User)
pycompiler-ark init --entry <path> [--icon <path>] [--with-venv] [--install-requirements] [--generate-requirements]
pycompiler-ark build [-y|--yes] [-v|--verbose] [--json]
pycompiler-ark build --engine <id> [-y|--yes]
pycompiler-ark build --lock [file] [-y|--yes]

# Execution
pycompiler-ark run bcasl [-y|--yes] [--list-plugins]

# GUI
pycompiler-ark gui
pycompiler-ark gui --legacy 

# Configuration (Developer)
pycompiler-ark set user-engine-dir <path>
pycompiler-ark set user-plugin-dir <path>
pycompiler-ark set dev-engine-dir <path>
pycompiler-ark set dev-plugin-dir <path> 

pycompiler-ark get user-engine-dir
pycompiler-ark get user-plugin-dir
pycompiler-ark get dev-engine-dir
pycompiler-ark get dev-plugin-dir 

pycompiler-ark unset user-engine-dir
pycompiler-ark unset user-plugin-dir
pycompiler-ark unset dev-engine-dir
pycompiler-ark unset dev-plugin-dir 

# Discovery
pycompiler-ark list engines
pycompiler-ark list plugins 

# Scaffolding
pycompiler-ark scaffold engine <name> [--path <dir>]
pycompiler-ark scaffold plugin-bcasl <name> [--path <dir>]
```

---

### **3. GUI Status**

| GUI Mode | Command | Status |
| :--- | :--- | :--- |
| **IDE-like GUI** | `pycompiler-ark gui` | **Active** (Modern, full feature set) |
| **Classic GUI** | `pycompiler-ark gui --legacy` | **Frozen** (Legacy maintenance only) |

---

### **4. Engine and Plugin Discovery**

PyCompiler ARK loads components from multiple locations in order of priority:

| Tier | Role | Default Location |
| :--- | :--- | :--- |
| **Dev** | Development | Optional (set via `pycompiler-ark set dev-*`) |
| **User** | User-installed | `~/ark_user/` (created automatically) |
| **Core** | Built-in engines | `ENGINES/` folder in installation root |

**Priority**: `Dev > User > Core`

---

### **5. Configuration (~/.arkconf/)**

Global user settings are stored in text files under `~/.arkconf/`:

- `pref.json`: Global GUI and runtime preferences.
- `user_engine_dir`: Path to user-installed engines.
- `user_plugin_dir`: Path to user-installed BCASL plugins.
- `dev_engine_dir`: Path to active engine development.
- `dev_plugin_dir`: Path to active plugin development.

---

### **6. Workspace Structure (.ark/)**

A initialized workspace contains a hidden `.ark/` directory:

- `lock/`: Immutable build snapshots and `latest.lock.yml`.
- `cache/`: Internal build cache and rebuild comparison data.
- `build/`: Temporary engine build artifacts.
- `logs/`: Compilation and pipeline execution logs.

---

### **7. Configuration (ark.yml)**

The project configuration file:

```yaml
project:
  name: my_app
  version: 1.0.0
  entry: src/main.py 

workspace:
  exclude:
    - "**/__pycache__/**" 

build:
  engine: nuitka
  output: dist/
  exclude:
    - "tests/**/*"
  include:
    - "requests"
    - "custom_package"
  data:
    - source: plugins/
      destination: plugins/
  icon: assets/icon.ico

plugins:
  bcasl_enabled: true
```

---

### **8. Detailed Command Behavior**

#### **`pycompiler-ark init --entry <path>`**

Initializes the current directory as a PyCompiler ARK workspace.

- **Requirement**: The directory must already exist.
- **Validation**: `--entry` must point to a file, not a directory.

#### **`pycompiler-ark build`**

- **Default**: Validates `ark.yml` and builds using the configured engine.
- **Auto-Confirm**: `-y` or `--yes` bypasses all interactive prompts (Git alignment, BCASL plugin confirmations).
- **Engine Override**: `--engine <id>` uses a temporary engine without modifying `ark.yml`.
- **Reproducible Rebuild**: `--lock [file]` rebuilds strictly from a lock file (default: `.ark/lock/latest.lock.yml`).
  - **Git State**: Automatically verifies if the current branch and commit match the lock. Offers automatic checkout on Linux.
  - **Integrity Check**: PyCompiler ARK generates a shadow lock from the rebuild environment and performs a **Functional Equivalence** comparison. Detailed diffs are displayed in case of mismatch.
- **Constraint**: `--engine` and `--lock` cannot be used together.

#### **`pycompiler-ark run bcasl`**

Executes the pre-compilation pipeline manually.
- **Auto-Confirm**: `-y` or `--yes` ensures all plugins demanding confirmation are automatically accepted.

---

### **9. Summary Rules**

- **CLI1**: Non-interactive by default when `-y` is provided.
- **CLI2**: `pycompiler-ark init` only operates on the current working directory.
- **CLI3**: All build artifacts and metadata stay inside the workspace `.ark/` folder.
- **CLI4**: Engines and plugins follow a clear `dev > user > core` priority.

---
*End of Specification v1.3*
