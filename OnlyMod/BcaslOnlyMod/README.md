# BCASL Standalone Module (only_mod)

## Overview

The `only_mod` module provides a standalone GUI application for managing and executing BCASL (Before-Compilation Actions System Loader) independently from the main PyCompiler ARK application.

This module allows you to:
- Select and manage workspaces
- Configure BCASL plugins
- Execute pre-compilation actions
- View detailed execution logs and reports
- Run BCASL asynchronously or synchronously

## Features

### 🎯 Core Features
- **Workspace Management**: Browse and select workspace directories
- **Plugin Configuration**: Enable/disable plugins and set execution order
- **Execution Modes**: Choose between asynchronous (non-blocking) and synchronous execution
- **Real-time Logging**: View detailed execution logs with status indicators
- **Execution Reports**: Get comprehensive reports on plugin execution results
- **Configuration Persistence**: Automatically saves plugin configuration to `bcasl.yml`

### 🎨 User Interface
- Clean, intuitive GUI built with PySide6
- Grouped controls for better organization
- Tooltips for all interactive elements
- Status bar with real-time feedback
- Progress indicator during execution
- Color-coded log output with emoji indicators

### ⚙️ Advanced Features
- Configuration caching for improved performance
- Automatic workspace configuration detection
- Integration with ARK main configuration
- Support for file pattern inclusion/exclusion
- Plugin timeout configuration
- Sandbox mode support

## Installation

### Requirements
- Python 3.8+
- PySide6
- PyYAML

### Setup
```bash
# Install dependencies
pip install PySide6 PyYAML

# Or use the project's requirements
pip install -r requirements.txt
```

## Usage

### Command Line

#### Launch without workspace
```bash
python -m bcasl.only_mod
```

#### Launch with workspace
```bash
python -m bcasl.only_mod /path/to/workspace
python -m bcasl.only_mod .
```

### Programmatic Usage

```python
from OnlyMod.BcaslOnlyMod import BcaslStandaloneApp
from PySide6.QtWidgets import QApplication
import sys

# Create application
app = QApplication(sys.argv)

# Create and show BCASL standalone window
window = BcaslStandaloneApp(workspace_dir="/path/to/workspace")
window.show()

# Run
sys.exit(app.exec())
```

## Configuration

### Workspace Configuration File

The module uses `bcasl.yml` (or `.bcasl.yml`) for configuration:

```yaml
# Enable/disable BCASL globally
options:
  enabled: true
  plugin_timeout_s: 0.0  # 0 = unlimited
  sandbox: true
  plugin_parallelism: 0

# File patterns to process
file_patterns:
  - "**/*.py"

# Patterns to exclude
exclude_patterns:
  - "**/__pycache__/**"
  - "**/*.pyc"
  - ".git/**"
  - "venv/**"

# Plugin configuration
plugins:
  plugin_id_1:
    enabled: true
    priority: 0
  plugin_id_2:
    enabled: false
    priority: 1

# Execution order
plugin_order:
  - plugin_id_1
  - plugin_id_2
```

### Environment Variables

- `PYCOMPILER_BCASL_PLUGIN_TIMEOUT`: Override plugin timeout (in seconds)

## User Interface Guide

### Main Window

1. **Workspace Configuration Group**
   - Display current workspace path
   - Browse button to select a different workspace

2. **Configuration Summary**
   - Shows number of enabled plugins
   - Displays file and exclude patterns count

3. **Execution Log**
   - Real-time display of execution progress
   - Color-coded status indicators:
     - ✅ OK: Plugin executed successfully
     - ❌ FAIL: Plugin execution failed
     - ⚠️ WARNING: Non-critical issues
     - 🧩 INFO: Plugin loading information

4. **Progress Bar**
   - Shows during execution
   - Indeterminate mode (no specific percentage)

5. **Execution Options**
   - **Run asynchronously**: Execute in background thread (recommended)
   - Unchecked: Blocks UI during execution

6. **Control Buttons**
   - **⚙️ Configure Plugins**: Open plugin configuration dialog
   - **▶️ Run BCASL**: Start execution
   - **🗑️ Clear Log**: Clear the log display
   - **Exit**: Close the application

### Plugin Configuration Dialog

1. **Global Enable/Disable**
   - Toggle BCASL execution globally
   - Disables plugin list when unchecked

2. **Plugin List**
   - Checkbox: Enable/disable individual plugins
   - Drag & Drop: Reorder execution sequence
   - Tooltip: Shows plugin description, tags, and requirements

3. **Move Buttons**
   - ⬆️: Move selected plugin up
   - ⬇️: Move selected plugin down

4. **Save/Cancel**
   - Save: Persist configuration to `bcasl.yml`
   - Cancel: Discard changes

## Execution Flow

1. **Workspace Selection**
   - User selects a workspace directory
   - Configuration is automatically loaded

2. **Plugin Configuration** (Optional)
   - User can enable/disable plugins
   - User can reorder plugin execution
   - Configuration is saved to `bcasl.yml`

3. **Execution**
   - User clicks "Run BCASL"
   - Plugins are loaded from `Plugins/` directory
   - Configuration is applied (enable/disable, priorities)
   - Plugins are executed in order
   - Results are displayed in real-time

4. **Results**
   - Execution report shows success/failure for each plugin
   - Summary statistics are displayed
   - Status bar shows overall result

## Troubleshooting

### PySide6 Import Error
```bash
pip install PySide6
```

### No Plugins Detected
- Ensure `Plugins/` directory exists in the project root
- Check that plugin packages have `__init__.py` files
- Verify plugin registration with `bcasl_register()` function

### Configuration Not Loading
- Check `bcasl.yml` syntax (must be valid YAML)
- Verify file is in workspace root directory
- Check file permissions

### Plugins Not Executing
- Verify plugins are enabled in configuration dialog
- Check plugin timeout settings
- Review execution log for error messages
- Ensure workspace path is correct

## Architecture

### Module Structure
```
bcasl/only_mod/
├── __init__.py      # Module initialization and exports
├── __main__.py      # Entry point for module execution
├── app.py           # Main GUI application class
└── README.md        # This file
```

### Key Classes

#### BcaslStandaloneApp
Main application window class that:
- Manages workspace selection
- Handles plugin configuration
- Executes BCASL operations
- Displays results and logs

### Dependencies
- **bcasl**: Core BCASL functionality
- **PySide6**: GUI framework
- **PyYAML**: Configuration file parsing

## Performance Considerations

1. **Asynchronous Execution**: Recommended for better UI responsiveness
2. **Configuration Caching**: Reduces file I/O overhead
3. **Plugin Timeout**: Set appropriate timeouts to prevent hanging
4. **Sandbox Mode**: Can impact performance but improves safety

## Security

- Configuration files are YAML-based (no code execution)
- Sandbox mode available for plugin execution
- File patterns restrict which files are processed
- Exclude patterns prevent processing of sensitive directories

## Contributing

To improve the `only_mod` module:

1. Follow the existing code style
2. Add docstrings to new functions
3. Update this README with new features
4. Test with various workspace configurations
5. Ensure backward compatibility

## License

Apache License 2.0 - See LICENSE file for details

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the execution log for error messages
3. Verify configuration files are correct
4. Check project documentation

## Version History

### v1.1.0
- Enhanced UI with better organization and tooltips
- Improved error handling and logging
- Added configuration caching
- Better documentation and examples

### v1.0.0
- Initial release
- Basic GUI for BCASL management
- Plugin configuration support
- Execution logging
