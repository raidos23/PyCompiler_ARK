# 🏗️ Pynsist Build Configuration for PyCompiler ARK++

Create Windows installers with bundled Python using pynsist.

## 📋 What is Pynsist?

Pynsist is a tool that creates Windows installers for Python applications. Unlike PyInstaller or cx_Freeze, it doesn't freeze your code into an executable. Instead, it:
- Bundles Python itself with your application
- Creates a native Windows installer (NSIS-based)
- Users don't need Python pre-installed
- Easier updates (just replace .py files)

## 🎯 Key Features

- ✅ **No Python required**: Installer includes Python
- ✅ **Easy updates**: Users can modify .py files if needed
- ✅ **Small updates**: Only changed files need redistribution
- ✅ **Native installer**: Professional Windows installer experience
- ✅ **Start Menu integration**: Automatic shortcuts
- ✅ **Uninstaller**: Standard Windows uninstall support

## ⚠️ Windows Only

Pynsist only creates Windows installers. For other platforms:
- **macOS/Linux**: Use Briefcase, cx_Freeze, or PyInstaller
- **Cross-platform**: Use Briefcase or cx_Freeze

## 📋 Available Build Methods

### 1. Python Build Script (Recommended)
```cmd
python build_pynsist.py
```

### 2. Batch Script (Windows)
```cmd
build_pynsist.bat
```

### 3. Direct Command
```cmd
pynsist installer.cfg
```

## 🔧 Build Configuration

Configuration is in `installer.cfg`:

```ini
[Application]
name = PyCompiler ARK++
version = 1.0.0
entry_point = pycompiler_ark:main
console = true
icon = logo/logo.ico

[Python]
version = 3.10.11
format = bundled

[Include]
packages = 
    PySide6
    psutil
files = 
    main.py
    Core
    themes
```

## ⚙️ Prerequisites

### Required
1. **Windows OS**: Pynsist only runs on Windows
2. **Python 3.7+**: For running the build script
3. **NSIS**: Nullsoft Scriptable Install System

### Installing NSIS

**Option 1: Winget (Recommended)**
```cmd
winget install NSIS.NSIS
```

**Option 2: Chocolatey**
```cmd
choco install nsis
```

**Option 3: Manual Download**
Download from: https://nsis.sourceforge.io/Download

### Installing Pynsist
```cmd
pip install pynsist
```

## 🚀 Quick Start

1. **Install prerequisites:**
   ```cmd
   REM Install NSIS
   winget install NSIS.NSIS
   
   REM Install pynsist
   pip install pynsist
   ```

2. **Build installer:**
   ```cmd
   REM Option 1: Python script (creates config automatically)
   python build_pynsist.py
   
   REM Option 2: Batch script
   build_pynsist.bat
   
   REM Option 3: Direct command (if installer.cfg exists)
   pynsist installer.cfg
   ```

3. **Find installer:**
   ```
   build\nsis\PyCompiler-ARK-Setup-1.0.0.exe
   ```

4. **Test installer:**
   - Run the installer on a clean Windows machine
   - Verify Start Menu shortcuts
   - Test uninstaller

## 📦 Output Structure

After installation on user's machine:
```
C:\Program Files\PyCompiler ARK++\
├── Python\              # Bundled Python
│   ├── python.exe
│   ├── python310.dll
│   └── Lib\
├── pkgs\                # Installed packages
│   ├── PySide6\
│   ├── psutil\
│   └── ...
├── main.py              # Your application files
├── pycompiler_ark.py
├── Core\
├── themes\
├── languages\
└── PyCompiler ARK++.launch.pyw  # Launcher script
```

## 🎨 Customization

### Edit Application Info

Edit `installer.cfg`:

```ini
[Application]
name = Your App Name
version = 2.0.0
entry_point = your_script:main_function
console = false  # Hide console for GUI apps
icon = path/to/icon.ico
```

### Change Python Version

```ini
[Python]
version = 3.11.0  # Any Python 3.x version
bitness = 64      # 32 or 64 (optional)
```

### Add/Remove Packages

```ini
[Include]
packages = 
    PySide6
    your-package>=1.0.0
```

### Include More Files

```ini
files = 
    main.py
    config.json
    assets/
    data/
```

### Customize Installer

```ini
[Installer]
license_file = LICENSE.txt
publisher = Your Company
# Add desktop shortcut
shortcuts = 
    App Name = your_script.pyw
```

### Exclude Files

```ini
exclude = 
    *.pyc
    __pycache__
    tests/
    *.git*
```

## 📊 Build Performance

- **First build**: 5-10 minutes (downloads Python and packages)
- **Subsequent builds**: 2-5 minutes (uses cache)
- **Installer size**: ~100-200 MB (includes Python)

## 🆚 Comparison with Other Tools

### Pynsist vs PyInstaller

| Feature | Pynsist | PyInstaller |
|---------|---------|-------------|
| Bundles Python | ✅ Yes (visible) | ✅ Yes (hidden) |
| Users can modify code | ✅ Yes | ❌ No (frozen) |
| Installer size | ~100-200 MB | ~100-200 MB |
| Startup time | Fast | Slower |
| Updates | Easy (replace files) | Full rebuild |
| Platform | Windows only | Cross-platform |
| Build time | 5-10 min | 2-5 min |

### When to Use Pynsist

✅ **Good for:**
- Windows-only applications
- Users who might need to modify code
- Easier debugging (Python installed)
- Frequent updates (just replace .py files)
- Professional Windows distribution

❌ **Not good for:**
- Cross-platform apps
- Maximum performance needed
- Code protection required
- Minimizing file size

## 💡 Advanced Features

### 1. GUI Application (No Console)

```ini
[Application]
console = false
entry_point = your_gui_app.pyw:main
```

### 2. Multiple Shortcuts

```ini
[Installer]
shortcuts = 
    Main App = main_app.pyw
    Configuration = config_tool.pyw
    Documentation = docs.html
```

### 3. Add to PATH

```ini
[Installer]
add_to_path = true
```

### 4. Custom Install Directory

Users can choose during installation, but you can suggest:
```ini
[Installer]
default_install_dir = $PROGRAMFILES64\YourApp
```

### 5. Pre/Post Install Scripts

Create Python scripts that run during installation:
```python
# pre_install.py
def pre_install():
    # Runs before installation
    pass

# post_install.py  
def post_install():
    # Runs after installation
    pass
```

### 6. Include PyPI Wheels

For packages with C extensions:
```ini
[Include]
packages = 
    numpy==1.21.0
    # pynsist will download the appropriate wheel
```

## 🐛 Troubleshooting

### "NSIS not found"
Install NSIS:
```cmd
winget install NSIS.NSIS
```
Ensure it's in PATH (may need to restart terminal)

### "Could not find Python version X.X.X"
Check available versions at: https://www.python.org/downloads/
Use a version that exists (e.g., 3.10.11, not 3.10.x)

### "Package not found"
Ensure package name is correct (case-sensitive):
```ini
packages = 
    PyYAML  # Correct
    # pyyaml  # Wrong
```

### Icon not showing
- Icon must be `.ico` format (not `.png`)
- Convert using online tools or ImageMagick:
  ```cmd
  magick logo.png -define icon:auto-resize=256,128,64,48,32,16 logo.ico
  ```

### Large installer size
This is normal - includes full Python. To reduce:
1. Use fewer packages
2. Exclude unnecessary files
3. Consider PyInstaller for smaller executables

### Import errors at runtime
Add missing packages to `[Include] packages`:
```ini
packages = 
    missing_package
```

## 📦 Distribution

### Testing

1. **Test on clean VM**: Always test on a machine without your dev environment
2. **Test install/uninstall**: Verify both processes work correctly
3. **Test shortcuts**: Ensure Start Menu shortcuts work
4. **Test upgrades**: Install old version, then new version

### Code Signing (Recommended for Production)

Get a code signing certificate, then:
```cmd
signtool sign /f certificate.pfx /p password /t http://timestamp.server PyCompiler-ARK-Setup.exe
```

### Distribution Channels

- **Website**: Direct download
- **GitHub Releases**: Attach .exe to release
- **Windows Package Manager**: Submit to winget
- **Chocolatey**: Create and submit package

## 💡 Best Practices

1. **Version everything**: Update version in installer.cfg for each release
2. **Test installers**: Always test on clean Windows installation
3. **Document requirements**: Note Windows version requirements
4. **Code signing**: Professional releases should be signed
5. **Keep Python updated**: Use latest stable Python version
6. **Minimal packages**: Only include necessary packages

## 📚 Additional Resources

- [Pynsist Documentation](https://pynsist.readthedocs.io/)
- [NSIS Documentation](https://nsis.sourceforge.io/Docs/)
- [Configuration Examples](https://pynsist.readthedocs.io/en/latest/cfgfile.html)
- [FAQ](https://pynsist.readthedocs.io/en/latest/faq.html)

## 🔄 Development Workflow

```cmd
REM Development
python pycompiler_ark.py

REM Test build
python build_pynsist.py

REM Test installer (on VM or clean machine)
build\nsis\PyCompiler-ARK-Setup-1.0.0.exe

REM Make changes, increment version
REM Edit installer.cfg: version = 1.0.1

REM Rebuild
python build_pynsist.py

REM Test upgrade
REM Install old version first, then new installer
```

## 📝 Notes

- **Python bundled**: Each installer is ~100-200 MB because it includes Python
- **No freezing**: Unlike PyInstaller, code is not compiled/frozen
- **User modifications**: Advanced users can modify your .py files
- **Easy debugging**: Users can see Python tracebacks
- **Windows only**: Cannot create macOS/Linux installers

## 📝 License

Same as PyCompiler ARK++ - Apache License 2.0