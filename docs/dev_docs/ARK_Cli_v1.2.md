# **ARK CLI Specification v1.2**

This document defines the final, streamlined specification for the ARK Command Line Interface.

---

### **1. Philosophy**

The CLI is designed to be simple, predictable, and headless-friendly.

- **Unified Binary**: Use `ark` (or `python pycompiler_ark.py`).
- **Explicit Commands**: No hidden magic; every action requires an explicit command.
- **CLI-First**: All features accessible via GUI are also available via CLI.
- **Reproducibility**: Guaranteed via functional locking comparison.

---

### **2. Final Commands**

```bash
# Workspace (User)
ark init --entry <path> [--icon <path>] [--with-venv] [--install-requirements] [--generate-requirements]
ark build
ark build --engine <id>
ark build --lock [file] 

# Execution
ark run bcasl 

# GUI
ark gui
ark gui --legacy 

# Configuration (Developer)
ark set user-engine-dir <path>
ark set user-plugin-dir <path>
ark set dev-engine-dir <path>
ark set dev-plugin-dir <path> 

ark get user-engine-dir
ark get user-plugin-dir
ark get dev-engine-dir
ark get dev-plugin-dir 

ark unset user-engine-dir
ark unset user-plugin-dir
ark unset dev-engine-dir
ark unset dev-plugin-dir 

# Discovery
ark list engines
ark list plugins 

# Scaffolding
ark scaffold engine <name> [--path <dir>]
ark scaffold plugin-bcasl <name> [--path <dir>]
```

---

### **3. GUI Status**

| GUI Mode | Command | Status |
| :--- | :--- | :--- |
| **IDE-like GUI** | `ark gui` | **Active** (Modern, full feature set) |
| **Classic GUI** | `ark gui --legacy` | **Frozen** (Legacy maintenance only) |

---

### **4. Engine and Plugin Discovery**

ARK loads components from multiple locations in order of priority:

| Tier | Role | Default Location |
| :--- | :--- | :--- |
| **Dev** | Development | Optional (set via `ark set dev-*`) |
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
  data:
    - source: plugins/
      destination: plugins/
  icon: assets/icon.ico

plugins:
  bcasl_enabled: true
```

---

### **8. Detailed Command Behavior**

#### **`ark init --entry <path>`**

Initializes the current directory as a workspace.

- **Requirement**: The directory must already exist.
- **Validation**: `--entry` must point to a file, not a directory.

#### **`ark build`**

- **Default**: Validates `ark.yml` and builds using the configured engine.
- **Engine Override**: `--engine <id>` uses a temporary engine without modifying `ark.yml`.
- **Reproducible Rebuild**: `--lock [file]` rebuilds strictly from a lock file (default: `.ark/lock/latest.lock.yml`).
  - **Git State**: Automatically verifies if the current branch and commit match the lock. Offers automatic checkout on Linux.
  - **Integrity Check**: ARK generates a shadow lock from the rebuild environment and performs a **Functional Equivalence** comparison. Detailed diffs are displayed in case of mismatch.
- **Constraint**: `--engine` and `--lock` cannot be used together.

---

### **9. Summary Rules**

- **CLI1**: No interactive questions; behavior is strictly deterministic.
- **CLI2**: `ark init` only operates on the current working directory.
- **CLI3**: All build artifacts and metadata stay inside the workspace `.ark/` folder.
- **CLI4**: Engines and plugins follow a clear `dev > user > core` priority.

---
*End of Specification v1.2*
