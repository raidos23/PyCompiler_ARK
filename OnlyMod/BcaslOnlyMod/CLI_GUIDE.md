# PyCompiler ARK++ CLI Usage Guide

## Overview

PyCompiler ARK++ now supports Click-based command-line interface for flexible launching of different application modes.

## Installation

### Install Click (Required)

```bash
pip install click
```

Click is required for the CLI interface to work properly.

## Basic Usage

### Launch Main Application

```bash
# Default: launches main application
python -m pycompiler_ark

# Explicit main command
python -m pycompiler_ark main
```

### Launch BCASL Standalone

```bash
# Without workspace
python -m pycompiler_ark bcasl

# With workspace path
python -m pycompiler_ark bcasl /path/to/project
python -m pycompiler_ark bcasl .
python -m pycompiler_ark bcasl ~/my-project
```

### Show Help

```bash
# Show main help
python -m pycompiler_ark --help

# Show detailed help
python -m pycompiler_ark --help-all

# Show command-specific help
python -m pycompiler_ark bcasl --help
python -m pycompiler_ark main --help
```

### Show Version

```bash
python -m pycompiler_ark --version
```

## Command Reference

### Main Command Group

```
Usage: python -m pycompiler_ark [OPTIONS] COMMAND [ARGS]...

Options:
  --version      Show version information
  --help-all     Show detailed help
  --help         Show this message and exit

Commands:
  bcasl          Launch BCASL standalone module
  main           Launch main application
```

### BCASL Subcommand

```
Usage: python -m pycompiler_ark bcasl [OPTIONS] [WORKSPACE]

Arguments:
  WORKSPACE  Optional path to workspace directory

Options:
  --help     Show this message and exit

Examples:
  python -m pycompiler_ark bcasl
  python -m pycompiler_ark bcasl /path/to/project
  python -m pycompiler_ark bcasl .
```

### Main Subcommand

```
Usage: python -m pycompiler_ark main [OPTIONS]

Options:
  --help     Show this message and exit
```

## Examples

### Example 1: Launch Main Application

```bash
python -m pycompiler_ark
```

### Example 2: Launch BCASL with Current Directory

```bash
cd /path/to/my/project
python -m pycompiler_ark bcasl .
```

### Example 3: Launch BCASL with Absolute Path

```bash
python -m pycompiler_ark bcasl /home/user/projects/my-app
```

### Example 4: Show Help

```bash
python -m pycompiler_ark --help
```

### Example 5: Show Version

```bash
python -m pycompiler_ark --version
```

### Example 6: Show Detailed Help

```bash
python -m pycompiler_ark --help-all
```

## Advanced Usage

### Batch Processing with BCASL

```bash
#!/bin/bash
# Process multiple projects

for project in ~/projects/*; do
    if [ -d "$project" ]; then
        echo "Processing: $(basename "$project")"
        python -m pycompiler_ark bcasl "$project"
    fi
done
```

### Conditional Launching

```bash
#!/bin/bash
# Launch BCASL if workspace exists, otherwise main app

WORKSPACE="/path/to/workspace"

if [ -d "$WORKSPACE" ]; then
    python -m pycompiler_ark bcasl "$WORKSPACE"
else
    python -m pycompiler_ark
fi
```

### With Environment Variables

```bash
# Set timeout for BCASL plugins
export PYCOMPILER_BCASL_PLUGIN_TIMEOUT=60
python -m pycompiler_ark bcasl /path/to/project

# Enable verbose logging
export PYCOMPILER_VERBOSE=1
python -m pycompiler_ark bcasl /path/to/project
```

## Integration with Shell Scripts

### Bash Integration

```bash
#!/bin/bash
# ark.sh - Wrapper script for PyCompiler ARK++

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

python pycompiler_ark.py "$@"
```

Usage:
```bash
chmod +x ark.sh
./ark.sh bcasl /path/to/project
./ark.sh --help
```

### Windows Batch Integration

```batch
@echo off
REM ark.bat - Wrapper script for PyCompiler ARK++

cd /d "%~dp0"
python pycompiler_ark.py %*
```

Usage:
```batch
ark.bat bcasl C:\Users\User\Projects\MyProject
ark.bat --help
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (import failed, invalid arguments, etc.) |

## Environment Variables

### BCASL-Specific

- `PYCOMPILER_BCASL_PLUGIN_TIMEOUT`: Plugin timeout in seconds (default: 0 = unlimited)
- `PYCOMPILER_VERBOSE`: Enable verbose logging (set to any value to enable)

### Qt-Specific

- `QT_AUTO_SCREEN_SCALE_FACTOR`: Enable high-DPI scaling
- `QT_ENABLE_HIGHDPI_SCALING`: Enable high-DPI scaling
- `QT_WAYLAND_DISABLE_FRACTIONAL_SCALE`: Disable fractional scaling on Wayland

## Troubleshooting

### Click Not Found

**Error:** `ModuleNotFoundError: No module named 'click'`

**Solution:**
Click is required for the CLI to work. Install it with:
```bash
pip install click
```

### Invalid Workspace Path

**Error:** `Warning: Workspace directory does not exist`

**Solution:**
The application will attempt to create the directory. If it fails:
1. Check parent directory permissions
2. Verify path syntax
3. Use absolute paths instead of relative paths

### Permission Denied

**Error:** `Failed to create directory: Permission denied`

**Solution:**
1. Check directory permissions
2. Use a different workspace location
3. Run with appropriate permissions

## Tips and Best Practices

1. **Use absolute paths** for workspace directories
2. **Set environment variables** before launching for consistent behavior
3. **Check help** for command-specific options: `python -m pycompiler_ark bcasl --help`
4. **Use batch scripts** for repeated operations
5. **Monitor exit codes** in automated workflows

## Future Enhancements

Potential CLI improvements:
- Configuration file support (`--config`)
- Output format options (`--json`, `--csv`)
- Logging level control (`--log-level`)
- Dry-run mode (`--dry-run`)
- Parallel execution (`--parallel`)
- Plugin filtering (`--plugin`)

## Support

For issues or questions:
1. Check this guide
2. Run `python -m pycompiler_ark --help`
3. Review project documentation
4. Check application logs
