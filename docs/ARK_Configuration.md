# ARK Configuration Guide

## Overview

The ARK configuration system provides centralized configuration management for PyCompiler ARK++ through YAML configuration files. This system controls compilation behavior, file patterns, dependencies, and plugin settings.

## Quick Navigation
- [Configuration File](#configuration-file)
- [File Patterns](#file-patterns)
- [Compilation Behavior](#compilation-behavior)
- [Dependencies](#dependencies-configuration)
- [Environment Manager](#environment-manager-configuration)
- [Plugins](#plugins-configuration)
- [Plugins Reference](#Plugins-reference)

---

## Configuration File

### File Format

ARK uses **YAML format only** for configuration files. The configuration file must be named `ARK_Main_Config.yml` or `ARK_Main_Config.yaml`.

### File Priority

The configuration loader searches for files in the following priority order:

1. `ARK_Main_Config.yaml` (highest priority)
2. `ARK_Main_Config.yml`
3. `.ARK_Main_Config.yaml` (hidden file)
4. `.ARK_Main_Config.yml` (hidden file)

The first file found is used. If no configuration file exists, default values are used.

### Location

Configuration files must be placed in the **workspace root directory** (the directory selected as the workspace in PyCompiler ARK++).

### Creating Default Configuration

To create a default configuration file:

```python
from Core.ArkConfigManager import create_default_ark_config

success = create_default_ark_config("/path/to/workspace")
```

Or use the UI to generate a default configuration when first setting up a workspace.

---

## File Patterns

### Exclusion Patterns

Files and directories matching these glob patterns are excluded from compilation:

```yaml
exclusion_patterns:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "**/*.pyo"
  - "**/*.pyd"
  - ".git/**"
  - ".svn/**"
  - ".hg/**"
  - "venv/**"
  - ".venv/**"
  - "env/**"
  - ".env/**"
  - "node_modules/**"
  - "build/**"
  - "dist/**"
  - "*.egg-info/**"
  - ".pytest_cache/**"
  - ".mypy_cache/**"
  - ".tox/**"
  - "site-packages/**"
```

**Key Points:**
- User-defined patterns are **merged** with default patterns (not replaced)
- Patterns use glob syntax (`**` matches any number of directories)
- Patterns are case-sensitive
- Both relative and absolute paths are supported

### Inclusion Patterns

Files matching these patterns are included for compilation:

```yaml
inclusion_patterns:
  - "**/*.py"
```

**Key Points:**
- Inclusion patterns are evaluated **after** exclusion patterns
- User-defined patterns **replace** default patterns
- Used by BCASL plugins and file discovery utilities

### Pattern Examples

```yaml
# Exclude specific directories
exclusion_patterns:
  - "tests/**"
  - "docs/**"
  - "examples/**"

# Include only specific file types
inclusion_patterns:
  - "**/*.py"
  - "**/*.pyw"
```

---

## Compilation Behavior

### Configuration Options

```yaml
compile_only_main: false
main_file_names:
  - "main.py"
  - "app.py"
auto_detect_entry_points: true
```

### Options Explained

#### `compile_only_main` (boolean)
- **Default:** `false`
- **Purpose:** When `true`, only compile the main entry point file
- **Use case:** Single-file applications or when you want to compile only the entry point

#### `main_file_names` (list of strings)
- **Default:** `["main.py", "app.py"]`
- **Purpose:** List of filenames to recognize as main entry points
- **Use case:** Auto-detection of entry points when multiple files exist

#### `auto_detect_entry_points` (boolean)
- **Default:** `true`
- **Purpose:** Automatically detect entry points based on `main_file_names`
- **Use case:** Simplify project setup by automatically finding entry points

### Example Usage

```yaml
# Compile only the main file
compile_only_main: true
main_file_names:
  - "main.py"
  - "run.py"
  - "start.py"
auto_detect_entry_points: true
```

---

## Dependencies Configuration

```yaml
dependencies:
  requirements_files:
    - "requirements.txt"
    - "requirements-prod.txt"
    - "requirements-dev.txt"
    - "Pipfile"
    - "Pipfile.lock"
    - "pyproject.toml"
    - "setup.py"
    - "setup.cfg"
    - "poetry.lock"
    - "conda.yml"
    - "environment.yml"
  auto_generate_from_imports: true
```

### Options

#### `requirements_files` (array of strings)
- **Default:** Multiple common dependency file formats
- **Purpose:** List of dependency files to scan for requirements
- **Use case:** Support multiple package managers and formats

#### `auto_generate_from_imports` (boolean)
- **Default:** `true`
- **Purpose:** Automatically detect dependencies from import statements
- **Use case:** Ensure all imported packages are included in compilation

### Example

```yaml
dependencies:
  requirements_files:
    - "requirements.txt"
    - "pyproject.toml"
  auto_generate_from_imports: true
```

---

## Environment Manager Configuration

```yaml
environment_manager:
  priority:
    - "poetry"
    - "pipenv"
    - "conda"
    - "pdm"
    - "uv"
    - "pip"
  auto_detect: true
  fallback_to_pip: true
```

### Options

#### `priority` (array of strings)
- **Default:** `["poetry", "pipenv", "conda", "pdm", "uv", "pip"]`
- **Purpose:** Order of preference for package managers
- **Use case:** Control which package manager to use when multiple are detected

#### `auto_detect` (boolean)
- **Default:** `true`
- **Purpose:** Automatically detect which package managers are available
- **Use case:** Simplify setup by detecting environment automatically

#### `fallback_to_pip` (boolean)
- **Default:** `true`
- **Purpose:** Use pip if no other package manager is found
- **Use case:** Ensure compilation can proceed with pip as last resort

### Supported Package Managers

1. **Poetry** - Modern Python packaging and dependency management
2. **Pipenv** - Python development workflow tool
3. **Conda** - Package, dependency and environment manager
4. **PDM** - Modern Python package manager
5. **uv** - Extremely fast Python package installer
6. **pip** - Standard Python package installer

### Example

```yaml
environment_manager:
  priority:
    - "poetry"
    - "pip"
  auto_detect: true
  fallback_to_pip: true
```

---

## Plugins Configuration

```yaml
plugins:
  bcasl_enabled: true
  plugin_timeout: 0.0
```

### Options

#### `bcasl_enabled` (boolean)
- **Default:** `true`
- **Purpose:** Enable or disable BCASL pre-compilation plugins globally
- **Use case:** Disable all plugins temporarily without uninstalling them

#### `plugin_timeout` (float)
- **Default:** `0.0` (unlimited)
- **Purpose:** Maximum execution time for each plugin in seconds
- **Values:**
  - `0.0` or negative: No timeout (unlimited)
  - Positive value: Timeout in seconds

### Example

```yaml
plugins:
  bcasl_enabled: true
  plugin_timeout: 30.0  # 30 seconds maximum per plugin
```

### Integration with BCASL

These settings are merged with BCASL-specific configuration (`bcasl.yml`):

- **Priority:** ARK configuration takes precedence over BCASL configuration
- **Merge behavior:**
  - `bcasl_enabled`: ARK value overrides BCASL value
  - `plugin_timeout`: ARK value overrides BCASL value if non-zero
  - File patterns: Merged (union of both configurations)

See [BCASL Configuration Guide](./BCASL_Configuration.md) for more details.

---

## Plugins Reference

### Loading Configuration

```python
from Core.ArkConfigManager import load_ark_config

# Load configuration for a workspace
config = load_ark_config("/path/to/workspace")

# Access specific sections
exclusion_patterns = config["exclusion_patterns"]
dependencies = config["dependencies"]
```

### Getting Specific Options

```python
from Core.ArkConfigManager import (
    get_compiler_options,
    get_dependency_options,
    get_environment_manager_options,
)

# Get compiler-specific options
pyinstaller_opts = get_compiler_options(config, "pyinstaller")
nuitka_opts = get_compiler_options(config, "nuitka")

# Get dependency options
dep_opts = get_dependency_options(config)

# Get environment manager options
env_opts = get_environment_manager_options(config)
```

### File Exclusion Check

```python
from Core.ArkConfigManager import should_exclude_file

# Check if a file should be excluded
is_excluded = should_exclude_file(
    file_path="/path/to/file.py",
    workspace_dir="/path/to/workspace",
    exclusion_patterns=config["exclusion_patterns"]
)
```

### Creating Default Configuration

```python
from Core.ArkConfigManager import create_default_ark_config

# Create default configuration file
success = create_default_ark_config("/path/to/workspace")
```

---

## Complete Configuration Example

```yaml
# ═══════════════════════════════════════════════════════════════
# ARK Main Configuration File
# ══════════════════════════════════��════════════════════════════

# FILE PATTERNS
exclusion_patterns:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - "**/*.pyo"
  - "**/*.pyd"
  - ".git/**"
  - ".svn/**"
  - "venv/**"
  - ".venv/**"
  - "env/**"
  - "build/**"
  - "dist/**"
  - "*.egg-info/**"
  - ".pytest_cache/**"
  - ".mypy_cache/**"
  - "node_modules/**"
  - "tests/**"        # Custom exclusion
  - "docs/**"         # Custom exclusion

inclusion_patterns:
  - "**/*.py"

# COMPILATION BEHAVIOR
compile_only_main: false
main_file_names:
  - "main.py"
  - "app.py"
  - "run.py"
auto_detect_entry_points: true

# DEPENDENCIES
dependencies:
  requirements_files:
    - "requirements.txt"
    - "pyproject.toml"
  auto_generate_from_imports: true

# ENVIRONMENT MANAGER
environment_manager:
  priority:
    - "poetry"
    - "pipenv"
    - "conda"
    - "pdm"
    - "uv"
    - "pip"
  auto_detect: true
  fallback_to_pip: true

# PLUGINS CONFIGURATION
plugins:
  bcasl_enabled: true
  plugin_timeout: 30.0
```

---

## Configuration Merging

When a configuration file exists, it is **merged** with default values:

1. **Deep Merge:** Nested dictionaries are merged recursively
2. **User Values Take Precedence:** User-defined values override defaults
3. **Exclusion Patterns:** User patterns are **added** to defaults (not replaced)
4. **Inclusion Patterns:** User patterns **replace** defaults
5. **Missing Values:** Default values are used for any missing options

### Example Merge Behavior

**User Configuration:**
```yaml
dependencies:
  auto_generate_from_imports: false
```

**Resulting Configuration:**
```yaml
dependencies:
  auto_generate_from_imports: false  # User value
  requirements_files: [...]          # Default value
```

---

## Best Practices

1. **Start with Defaults:** Use `create_default_ark_config()` to generate a template
2. **Version Control:** Commit `ARK_Main_Config.yml` to version control
3. **Document Custom Settings:** Add comments to explain non-standard options
4. **Test Incrementally:** Test configuration changes with small builds first
5. **Use Relative Paths:** Use workspace-relative paths for portability
6. **Separate Environments:** Use different configurations for dev/prod builds
7. **Backup Before Changes:** Keep a backup before making significant changes

---

## Troubleshooting

### Configuration Not Loading

**Symptoms:** Default values are used instead of configuration file

**Solutions:**
1. Verify file name is exactly `ARK_Main_Config.yml` or `ARK_Main_Config.yaml`
2. Check file is in workspace root directory
3. Verify YAML syntax is valid (proper indentation, no tabs)
4. Check file permissions (must be readable)
5. Look for error messages in application logs

### Invalid YAML Syntax

**Symptoms:** Configuration file is ignored or application shows errors

**Solutions:**
1. Use a YAML validator to check syntax
2. Ensure proper indentation (use spaces, not tabs)
3. Quote strings containing special characters
4. Verify array syntax uses hyphens (`-`)

### Patterns Not Working

**Symptoms:** Files not excluded/included as expected

**Solutions:**
1. Test patterns using Python's `pathlib.Path.match()`
2. Use `**` for recursive directory matching
3. Ensure patterns are case-sensitive
4. Check `should_exclude_file()` function behavior
5. Review pattern order (exclusions are checked before inclusions)

---

## See Also

- [BCASL Configuration Guide](./BCASL_Configuration.md) - Plugin system configuration
- [How to Create an Engine](./how_to_create_an_engine.md) - Engine development guide
- [How to Create a BCASL Plugin](./how_to_create_a_BC_plugin.md) - Plugin development guide
