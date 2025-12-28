# 🏗️ Nuitka Build Configuration for PyCompiler ARK++

This directory contains multiple options for building PyCompiler ARK++ with Nuitka.

## 📋 Available Build Methods

### 1. Python Build Script (Recommended)
Comprehensive cross-platform build script with detailed configuration:

```bash
python build_nuitka.py
```

**Features:**
- Automatic Nuitka installation check
- Platform detection and optimization
- Detailed build progress
- Configurable options in the script

### 2. Shell Script (Linux/macOS)
Quick build for Unix-based systems:

```bash
./build_nuitka.sh
```

### 3. Batch Script (Windows)
Quick build for Windows:

```cmd
build_nuitka.bat
```

### 4. Configuration File
Use the configuration file with Nuitka directly:

```bash
python -m nuitka @nuitka_config.txt pycompiler_ark.py
```

## 🔧 Build Configuration

### Output
- **Mode**: Standalone onefile executable
- **Location**: `build/nuitka/`
- **Filename**: `PyCompiler-ARK` (`.exe` on Windows)

### Optimizations
- **LTO**: Link Time Optimization enabled
- **Jobs**: Multi-threaded compilation (uses all CPU cores)
- **Plugin**: PySide6 plugin enabled for Qt support

### Included Data
- `themes/` - UI themes
- `languages/` - Internationalization files
- `logo/` - Application icons and images
- `ui/` - UI definition files

### Included Packages
- Core
- engine_sdk
- ENGINES
- bcasl
- Plugins_SDK

## ⚙️ Prerequisites

### All Platforms
- Python 3.10 or higher
- Nuitka (auto-installed by scripts)
- All project dependencies installed:
  ```bash
  pip install -r requirements.txt -c constraints.txt
  ```

### Linux
Required system packages:
```bash
# Debian/Ubuntu
sudo apt-get install build-essential python3-dev patchelf p7zip-full

# Fedora/RHEL
sudo dnf install gcc gcc-c++ python3-devel patchelf p7zip
```

### Windows
- Visual Studio Build Tools or MinGW-w64
- The Nuitka engine in PyCompiler ARK++ can help install MinGW-w64 automatically

### macOS
- Xcode Command Line Tools:
  ```bash
  xcode-select --install
  ```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt -c constraints.txt
   ```

2. **Run the build:**
   ```bash
   # Option 1: Python script (recommended)
   python build_nuitka.py
   
   # Option 2: Platform-specific script
   ./build_nuitka.sh      # Linux/macOS
   build_nuitka.bat       # Windows
   ```

3. **Find your executable:**
   ```
   build/nuitka/PyCompiler-ARK       # Linux/macOS
   build/nuitka/PyCompiler-ARK.exe   # Windows
   ```

## 🎨 Customization

### Editing Build Options

**Python Script** (`build_nuitka.py`):
Edit the `BUILD_CONFIG` dictionary at the top of the file.

**Configuration File** (`nuitka_config.txt`):
Uncomment or add options as needed. Each line starting with `--` is a Nuitka flag.

**Shell/Batch Scripts**:
Edit the command arguments directly in the script.

### Common Customizations

#### Change Output Directory
```python
"output_dir": "dist/nuitka"  # In build_nuitka.py
```

#### Enable Debug Mode
```python
"debug": True,  # In build_nuitka.py
```

#### Disable Onefile Mode
```python
"onefile": False,  # Creates a directory instead of single file
```

#### Add More Data Directories
```python
"include_data_dir": [
    "themes=themes",
    "languages=languages",
    "logo=logo",
    "ui=ui",
    "custom_dir=custom_dir",  # Add your directory
],
```

## 📊 Build Performance

Typical build times on modern hardware:
- **First build**: 5-15 minutes (downloads dependencies)
- **Subsequent builds**: 2-5 minutes (with cache)
- **Incremental builds**: 1-2 minutes

Build size:
- **Onefile executable**: ~80-150 MB (platform-dependent)
- **Standalone directory**: ~150-250 MB

## 🐛 Troubleshooting

### "Nuitka not found"
```bash
pip install nuitka
```

### "Missing C compiler" (Windows)
Use the PyCompiler ARK++ GUI to install MinGW-w64, or download manually from [winlibs.com](https://winlibs.com/).

### "Missing dependencies" (Linux)
Install build tools:
```bash
sudo apt-get install build-essential python3-dev patchelf
```

### Build fails with PySide6 errors
Ensure PySide6 is properly installed:
```bash
pip install --force-reinstall PySide6
```

### Large executable size
This is normal for Python applications compiled with Nuitka. The executable includes:
- Python runtime
- All dependencies (PySide6, psutil, etc.)
- Project code and data files

To reduce size, consider using standalone mode instead of onefile.

## 📚 Additional Resources

- [Nuitka Documentation](https://nuitka.net/doc/user-manual.html)
- [PySide6 with Nuitka](https://nuitka.net/doc/user-manual.html#pyside6)
- [PyCompiler ARK++ Documentation](README.md)

## 📝 License

Same as PyCompiler ARK++ - Apache License 2.0