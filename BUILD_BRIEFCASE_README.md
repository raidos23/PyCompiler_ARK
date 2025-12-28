# 🏗️ Briefcase Build Configuration for PyCompiler ARK++

Build native installers for PyCompiler ARK++ using BeeWare Briefcase.

## 📋 What is Briefcase?

Briefcase is a tool from the BeeWare project that packages Python applications into native installers for different platforms:
- **Windows**: MSI installer
- **macOS**: DMG disk image with .app bundle
- **Linux**: AppImage, Flatpak, or Snap
- **iOS/Android**: Mobile app packages (advanced)

## 🎯 Key Features

- ✅ Creates native installers for each platform
- ✅ Professional application packaging
- ✅ Code signing support
- ✅ Automatic dependency management
- ✅ Development mode for testing

## 📋 Available Build Methods

### 1. Python Build Script (Recommended)
```bash
python build_briefcase.py
```

### 2. Shell Script (Linux/macOS)
```bash
./build_briefcase.sh
```

### 3. Batch Script (Windows)
```cmd
build_briefcase.bat
```

### 4. Direct Briefcase Commands
```bash
briefcase create   # Create app scaffold
briefcase build    # Build the app
briefcase package  # Create installer
briefcase run      # Run without packaging
briefcase dev      # Development mode
```

## 🔧 Build Configuration

Configuration is stored in `pyproject.toml`:

```toml
[tool.briefcase.app.pycompiler_ark]
formal_name = "PyCompiler-ARK"
description = "Python Compilation Toolkit"
sources = ["pycompiler_ark.py", "main.py", "Core", ...]
requires = ["PySide6>=6.8.0", "psutil>=5.9.0", ...]
```

## ⚙️ Prerequisites

### All Platforms
- Python 3.10 or higher
- Briefcase (auto-installed by scripts)
- Git (for some dependencies)

### Windows
- WiX Toolset (for MSI creation)
  ```powershell
  winget install --id=WiXToolset.WiX -e
  ```

### macOS
- Xcode Command Line Tools
  ```bash
  xcode-select --install
  ```

### Linux
- System packages for Qt and AppImage:
  ```bash
  # Debian/Ubuntu
  sudo apt-get install python3-dev libgirepository1.0-dev \
       libcairo2-dev libxcb-xinerama0 libxcb-cursor0
  
  # Fedora/RHEL
  sudo dnf install python3-devel gobject-introspection-devel \
       cairo-devel libxcb
  ```

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt -c constraints.txt
   pip install briefcase
   ```

2. **Initialize (first time only):**
   ```bash
   python build_briefcase.py
   # Or manually: briefcase new
   ```

3. **Build:**
   ```bash
   # Full build with installer
   python build_briefcase.py
   
   # Or step by step
   briefcase create   # Create scaffold
   briefcase build    # Compile
   briefcase package  # Create installer
   ```

4. **Development mode:**
   ```bash
   briefcase dev      # Quick test (recommended during development)
   briefcase run      # Run built app
   ```

## 📦 Output Formats

### Windows
- **Format**: MSI installer
- **Location**: `dist/PyCompiler-ARK-1.0.0.msi`
- **Size**: ~150-250 MB

### macOS
- **Format**: DMG disk image with .app bundle
- **Location**: `dist/PyCompiler-ARK-1.0.0.dmg`
- **Size**: ~150-250 MB

### Linux
- **Format**: AppImage (portable executable)
- **Location**: `dist/PyCompiler-ARK-1.0.0.AppImage`
- **Size**: ~150-250 MB
- **Alternative**: Flatpak or Snap (requires additional configuration)

## 🎨 Customization

### Edit App Metadata
Edit `pyproject.toml`:

```toml
[tool.briefcase.app.pycompiler_ark]
formal_name = "Your App Name"
version = "2.0.0"
description = "Your description"
author = "Your Name"
license = "Apache-2.0"
```

### Add Dependencies
```toml
requires = [
    "PySide6>=6.8.0",
    "your-package>=1.0.0",
]
```

### Platform-Specific Settings
```toml
[tool.briefcase.app.pycompiler_ark.macOS]
icon = "path/to/icon"
requires = ["macOS-specific-package"]

[tool.briefcase.app.pycompiler_ark.windows]
icon = "path/to/icon"
requires = ["windows-specific-package"]

[tool.briefcase.app.pycompiler_ark.linux]
system_requires = ["libsomething"]
```

## 📊 Build Performance

- **First build**: 10-20 minutes (downloads support packages)
- **Subsequent builds**: 2-5 minutes
- **Development mode** (`briefcase dev`): <1 minute

## 🐛 Troubleshooting

### "Briefcase not found"
```bash
pip install briefcase
```

### WiX Toolset not found (Windows)
Install WiX Toolset:
```powershell
winget install --id=WiXToolset.WiX -e
```

### AppImage creation fails (Linux)
Ensure you have required dependencies:
```bash
sudo apt-get install libfuse2 desktop-file-utils
```

### "Module not found" errors
Add missing packages to `requires` in `pyproject.toml`

### Code signing (macOS/Windows)
For production releases, you'll need proper code signing certificates:

**macOS:**
```bash
briefcase package --identity "Developer ID Application: Your Name"
```

**Windows:**
```bash
briefcase package --sign-with "path/to/certificate.pfx"
```

## 🆚 Comparison with Other Tools

### Briefcase vs PyInstaller
**Briefcase:**
- ✅ Native installers (MSI, DMG, AppImage)
- ✅ Better platform integration
- ✅ Development mode
- ❌ Larger file sizes
- ❌ Longer build times

**PyInstaller:**
- ✅ Faster builds
- ✅ Single executable
- ❌ No native installer
- ❌ Less platform integration

### When to Use Briefcase
- ✅ Professional distribution
- ✅ App stores (macOS, Windows Store)
- ✅ Need native installers
- ✅ Cross-platform deployment
- ✅ Long-term maintenance

### When to Use PyInstaller/Nuitka
- ✅ Quick testing
- ✅ Internal tools
- ✅ Smaller file sizes
- ✅ Faster iteration

## 💡 Best Practices

1. **Use development mode during development:**
   ```bash
   briefcase dev  # Faster than full rebuild
   ```

2. **Test on target platforms:**
   Always test installers on clean machines

3. **Version control pyproject.toml:**
   This is your app configuration

4. **Code signing for distribution:**
   Required for professional releases

5. **Update support packages regularly:**
   ```bash
   briefcase update
   ```

## 📚 Additional Resources

- [Briefcase Documentation](https://briefcase.readthedocs.io/)
- [BeeWare Tutorial](https://docs.beeware.org/en/latest/tutorial/)
- [Code Signing Guide](https://briefcase.readthedocs.io/en/latest/how-to/code-signing.html)
- [Publishing Guide](https://briefcase.readthedocs.io/en/latest/how-to/publishing.html)

## 🔄 Development Workflow

```bash
# Day-to-day development
briefcase dev              # Quick test

# Before commit
briefcase build            # Full build test

# Before release
briefcase create           # Fresh scaffold
briefcase build            # Build
briefcase package          # Create installer
# Test installer on target platform
```

## 📝 License

Same as PyCompiler ARK++ - Apache License 2.0