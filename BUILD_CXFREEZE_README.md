# 🏗️ cx_Freeze Build Configuration for PyCompiler ARK++

Build standalone executables for PyCompiler ARK++ using cx_Freeze.

## 📋 What is cx_Freeze?

cx_Freeze is a cross-platform tool that freezes Python scripts into executables. It's a mature alternative to PyInstaller with some unique advantages:
- Good cross-platform support
- Simple configuration
- Reliable dependency detection
- Creates distributable directory with executable

## 🎯 Key Features

- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Simple setup.py configuration
- ✅ Good performance
- ✅ MSI installer support (Windows)
- ✅ DMG installer support (macOS with bdist_dmg)
- ✅ Minimal dependencies

## 📋 Available Build Methods

### 1. Python Build Script (Recommended)
```bash
python build_cxfreeze.py
```

### 2. Shell Script (Linux/macOS)
```bash
./build_cxfreeze.sh
```

### 3. Batch Script (Windows)
```cmd
build_cxfreeze.bat
```

### 4. Direct cx_Freeze Command
```bash
# After running build_cxfreeze.py once to generate setup_cxfreeze.py
python setup_cxfreeze.py build_exe
```

## 🔧 Build Configuration

The build script creates `setup_cxfreeze.py` with this structure:

```python
build_exe_options = {
    "build_exe": "build/cxfreeze",
    "packages": ["PySide6", "Core", ...],
    "includes": ["PySide6.QtCore", ...],
    "excludes": ["tkinter", "matplotlib", ...],
    "include_files": [
        ("themes", "themes"),
        ("languages", "languages"),
        ...
    ],
    "optimize": 2,
}
```

## ⚙️ Prerequisites

### All Platforms
- Python 3.10 or higher
- cx_Freeze (auto-installed by scripts)
- All project dependencies

### Windows
- No additional requirements (works out of the box)

### Linux
- System libraries for Qt:
  ```bash
  # Debian/Ubuntu
  sudo apt-get install libxcb-xinerama0 libxcb-cursor0
  
  # Fedora/RHEL
  sudo dnf install libxcb
  ```

### macOS
- Xcode Command Line Tools (optional):
  ```bash
  xcode-select --install
  ```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt -c constraints.txt
   pip install cx_Freeze
   ```

2. **Build:**
   ```bash
   # Option 1: Python script (recommended)
   python build_cxfreeze.py
   
   # Option 2: Platform script
   ./build_cxfreeze.sh      # Linux/macOS
   build_cxfreeze.bat       # Windows
   
   # Option 3: Direct command (after first build)
   python setup_cxfreeze.py build_exe
   ```

3. **Run the application:**
   ```bash
   cd build/cxfreeze
   ./PyCompiler-ARK           # Linux/macOS
   PyCompiler-ARK.exe         # Windows
   ```

## 📦 Output Structure

```
build/cxfreeze/
├── PyCompiler-ARK(.exe)     # Main executable
├── lib/                     # Python libraries
│   ├── PySide6/
│   ├── Core/
│   └── ...
├── themes/                  # Your data files
├── languages/
├── logo/
└── ui/
```

## 🎨 Customization

### Edit Build Configuration

Modify `BUILD_CONFIG` in `build_cxfreeze.py`:

```python
BUILD_CONFIG = {
    "build_exe": "dist/app",  # Change output directory
    "optimize": 2,             # 0, 1, or 2
    "silent": False,           # True for less output
    # ... other options
}
```

### Add Packages
```python
"packages": [
    "PySide6",
    "your_package",  # Add here
],
```

### Add Data Files
```python
"include_files": [
    ("themes", "themes"),
    ("your_data", "data"),  # Add here
],
```

### Exclude Modules (reduce size)
```python
"excludes": [
    "tkinter",
    "unnecessary_module",  # Add here
],
```

### Create Windows MSI Installer
```bash
python setup_cxfreeze.py bdist_msi
```

### Create macOS DMG (requires bdist_dmg)
```bash
pip install dmgbuild
python setup_cxfreeze.py bdist_dmg
```

## 📊 Build Performance

- **First build**: 2-5 minutes
- **Subsequent builds**: 1-3 minutes
- **Incremental** (no clean): <1 minute

**Output size:**
- **Directory**: ~150-300 MB
- **MSI installer**: ~120-250 MB (compressed)

## 🐛 Troubleshooting

### "cx_Freeze not found"
```bash
pip install cx_Freeze
```

### "Module not found" errors at runtime
Add the module to `packages` or `includes`:
```python
"packages": ["missing_module"],
```

### Qt platform plugin errors (Linux)
```bash
sudo apt-get install libxcb-xinerama0 libxcb-cursor0
```

### Large output size
Add more modules to excludes:
```python
"excludes": ["tkinter", "unittest", "test", "email"],
```

### DLL/Library errors (Windows)
Ensure all required DLLs are in the build directory or system PATH

### Permission denied (macOS/Linux)
```bash
chmod +x build/cxfreeze/PyCompiler-ARK
```

## 🆚 Comparison with Other Tools

### cx_Freeze vs PyInstaller

**cx_Freeze:**
- ✅ More reliable on some platforms
- ✅ Better for complex dependencies
- ✅ Simple configuration
- ✅ MSI/DMG support
- ❌ Larger output size
- ❌ Slower builds than PyInstaller

**PyInstaller:**
- ✅ Onefile mode
- ✅ Faster builds
- ✅ Smaller executables
- ❌ Sometimes unreliable
- ❌ Harder to debug

### cx_Freeze vs Nuitka

**cx_Freeze:**
- ✅ Faster builds
- ✅ No C compiler needed
- ✅ Easier setup
- ❌ Slower runtime
- ❌ No optimization

**Nuitka:**
- ✅ Compiled code (faster)
- ✅ Better optimization
- ❌ Requires C compiler
- ❌ Much longer builds

### When to Use cx_Freeze
- ✅ Reliable cross-platform builds
- ✅ Need MSI/DMG installers
- ✅ Complex dependencies
- ✅ Moderate distribution (not onefile needed)
- ✅ PyInstaller gives issues

## 💡 Advanced Features

### 1. Custom Icon
```python
Executable(
    "pycompiler_ark.py",
    icon="logo/logo.ico",  # Windows: .ico
    # macOS: .icns
)
```

### 2. Hide Console (Windows)
```python
base = "Win32GUI"  # In setup_cxfreeze.py
```

### 3. Version Info (Windows)
Create a version_info.txt and reference it in setup

### 4. Multiple Executables
```python
executables=[
    Executable("main.py", target_name="PyCompiler-ARK"),
    Executable("cli.py", target_name="pycompiler-cli"),
]
```

### 5. Platform-Specific Options
```python
import sys

if sys.platform == "win32":
    build_exe_options["include_msvcr"] = True
elif sys.platform == "darwin":
    build_exe_options["iconfile"] = "logo/logo.icns"
```

## 📦 Distribution

### Windows MSI
```bash
python setup_cxfreeze.py bdist_msi
# Output: dist/PyCompiler-ARK-1.0.0-win64.msi
```

### macOS DMG
```bash
pip install dmgbuild
python setup_cxfreeze.py bdist_dmg
# Output: dist/PyCompiler-ARK-1.0.0.dmg
```

### Linux Package
```bash
# Copy build/cxfreeze directory
# Or create tar.gz
tar -czf PyCompiler-ARK-1.0.0-linux-x64.tar.gz -C build cxfreeze
```

## 💡 Best Practices

1. **Test on target platform:**
   Always test the built application on the target OS

2. **Use virtual environment:**
   Build in a clean venv to avoid including dev dependencies

3. **Version your setup script:**
   Commit `setup_cxfreeze.py` to version control

4. **Optimize excludes:**
   Carefully exclude unnecessary modules to reduce size

5. **Document platform-specific requirements:**
   Note any system libraries needed by users

## 📚 Additional Resources

- [cx_Freeze Documentation](https://cx-freeze.readthedocs.io/)
- [cx_Freeze GitHub](https://github.com/marcelotduarte/cx_Freeze)
- [Setup Script Examples](https://cx-freeze.readthedocs.io/en/latest/setup_script.html)
- [FAQ](https://cx-freeze.readthedocs.io/en/latest/faq.html)

## 🔄 Development Workflow

```bash
# Development
python pycompiler_ark.py  # Normal Python execution

# Testing build
python build_cxfreeze.py   # Full build

# Testing executable
cd build/cxfreeze
./PyCompiler-ARK          # Test the built app

# Release
python setup_cxfreeze.py bdist_msi  # Windows
python setup_cxfreeze.py bdist_dmg  # macOS
```

## 📝 License

Same as PyCompiler ARK++ - Apache License 2.0