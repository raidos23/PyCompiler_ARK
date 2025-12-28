# 🏗️ PyInstaller Build Configuration for PyCompiler ARK++

This directory contains multiple options for building PyCompiler ARK++ with PyInstaller.

## 📋 Available Build Methods

### 1. Python Build Script (Recommended)
Comprehensive cross-platform build script with detailed configuration:

```bash
python build_pyinstaller.py
```

**Features:**
- Automatic PyInstaller installation check
- Platform detection and optimization
- Detailed build progress
- Configurable options in the script

### 2. Shell Script (Linux/macOS)
Quick build for Unix-based systems:

```bash
./build_pyinstaller.sh
```

### 3. Batch Script (Windows)
Quick build for Windows:

```cmd
build_pyinstaller.bat
```

### 4. Spec File
Advanced configuration using PyInstaller spec file:

```bash
pyinstaller pyinstaller_config.spec
```

## 🔧 Build Configuration

### Output
- **Mode**: Onefile executable (single file)
- **Location**: `dist/`
- **Filename**: `PyCompiler-ARK` (`.exe` on Windows)

### Optimizations
- **UPX**: Disabled (prevents compatibility issues)
- **Clean build**: Removes cache before building
- **Collect all**: PySide6 and shiboken6 fully bundled

### Included Data
- `themes/` - UI themes
- `languages/` - Internationalization files
- `logo/` - Application icons and images
- `ui/` - UI definition files

### Hidden Imports
All required modules are explicitly included:
- PySide6 (QtCore, QtGui, QtWidgets, QtUiTools)
- psutil
- yaml
- PIL/Pillow
- jsonschema
- multiprocessing
- faulthandler

### Excluded Modules
The following modules are excluded to reduce executable size:
- tkinter
- matplotlib
- numpy, scipy, pandas
- IPython, jupyter, notebook
- pytest, unittest

## ⚙️ Prerequisites

### All Platforms
- Python 3.10 or higher
- PyInstaller (auto-installed by scripts)
- All project dependencies installed:
  ```bash
  pip install -r requirements.txt -c constraints.txt
  ```

### Windows
- No additional requirements (PyInstaller works out of the box)

### Linux
- System libraries for Qt:
  ```bash
  # Debian/Ubuntu
  sudo apt-get install libxcb-xinerama0 libxcb-cursor0
  
  # Fedora/RHEL
  sudo dnf install libxcb
  ```

### macOS
- Xcode Command Line Tools (optional, for better compatibility):
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
   python build_pyinstaller.py
   
   # Option 2: Platform-specific script
   ./build_pyinstaller.sh      # Linux/macOS
   build_pyinstaller.bat       # Windows
   
   # Option 3: Spec file (advanced)
   pyinstaller pyinstaller_config.spec
   ```

3. **Find your executable:**
   ```
   dist/PyCompiler-ARK       # Linux/macOS
   dist/PyCompiler-ARK.exe   # Windows
   ```

## 🎨 Customization

### Editing Build Options

**Python Script** (`build_pyinstaller.py`):
Edit the `BUILD_CONFIG` dictionary at the top of the file.

**Spec File** (`pyinstaller_config.spec`):
Advanced users can modify the spec file for fine-grained control.

**Shell/Batch Scripts**:
Edit the command arguments directly in the script.

### Common Customizations

#### Hide Console Window (GUI Only)
```python
"windowed": True,  # or --windowed flag
"console": False,  # In build_pyinstaller.py
```

#### Change Output Directory
```python
"distpath": "output/pyinstaller"  # In build_pyinstaller.py
```

#### Enable Debug Mode
```python
"debug": True,  # In build_pyinstaller.py
```

#### Disable Onefile Mode
```python
"onefile": False,  # Creates a directory instead of single file
```

#### Add More Data Files
```python
"add_data": [
    ("themes", "themes"),
    ("languages", "languages"),
    ("logo", "logo"),
    ("ui", "ui"),
    ("custom_dir", "custom_dir"),  # Add your directory
],
```

#### Add Hidden Imports
```python
"hidden_import": [
    # ... existing imports ...
    "your_module_name",
],
```

## 📊 Build Performance

Typical build times on modern hardware:
- **First build**: 2-5 minutes
- **Subsequent builds**: 1-3 minutes
- **With --clean flag**: 2-4 minutes

Build size:
- **Onefile executable**: ~100-200 MB (platform-dependent)
- **Directory mode**: ~150-300 MB

## 🐛 Troubleshooting

### "PyInstaller not found"
```bash
pip install pyinstaller
```

### "Failed to execute script" error
This usually means a module is missing. Add it to `hidden_import`:
```python
"hidden_import": ["missing_module_name"],
```

### Qt platform plugin errors (Linux)
Install Qt dependencies:
```bash
sudo apt-get install libxcb-xinerama0 libxcb-cursor0
```

### DLL load failures (Windows)
Try rebuilding with:
```bash
pyinstaller --clean build_pyinstaller.py
```

### ImportError at runtime
Add the missing module to hidden imports in the build script or spec file.

### Large executable size
This is normal for PyInstaller. The executable includes:
- Python runtime
- All dependencies (PySide6, etc.)
- Project code and data files

To reduce size:
1. Use directory mode instead of onefile
2. Add more modules to the exclusion list
3. Remove unnecessary data files

## 🆚 PyInstaller vs Nuitka

### PyInstaller
**Pros:**
- ✅ Faster build times (2-5 min)
- ✅ Easier to use
- ✅ Better compatibility out of the box
- ✅ Works on all platforms without C compiler

**Cons:**
- ❌ Larger executable size
- ❌ Slower startup time
- ❌ No optimization

### Nuitka
**Pros:**
- ✅ Better performance (compiled to C)
- ✅ Smaller executable (sometimes)
- ✅ Code optimization

**Cons:**
- ❌ Longer build times (5-15 min)
- ❌ Requires C compiler
- ❌ More complex setup

**Recommendation**: Use PyInstaller for quick testing and distribution. Use Nuitka for production releases where performance matters.

## 📚 Additional Resources

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [PyInstaller Spec Files](https://pyinstaller.org/en/stable/spec-files.html)
- [Common Issues](https://github.com/pyinstaller/pyinstaller/wiki/If-Things-Go-Wrong)
- [PyCompiler ARK++ Documentation](README.md)

## 💡 Tips

1. **Use spec file for complex builds**: The spec file gives you more control
2. **Test on target platform**: Always test on the platform you're targeting
3. **Keep dependencies minimal**: Fewer dependencies = smaller executable
4. **Use virtual environment**: Build in a clean venv to avoid including dev dependencies
5. **Version control the spec file**: It's a valuable configuration asset

## 📝 License

Same as PyCompiler ARK++ - Apache License 2.0