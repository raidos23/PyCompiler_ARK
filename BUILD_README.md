# 🏗️ PyCompiler ARK++ Build Configurations

Complete build system for creating distributable packages of PyCompiler ARK++.

## 📦 Available Packaging Tools

This project includes build configurations for **5 different Python packaging tools**:

| Tool | Platform | Build Script | Documentation |
|------|----------|--------------|---------------|
| **PyInstaller** | Win/Mac/Linux | `build_pyinstaller.py` | [README](BUILD_PYINSTALLER_README.md) |
| **Nuitka** | Win/Mac/Linux | `build_nuitka.py` | [README](BUILD_NUITKA_README.md) |
| **cx_Freeze** | Win/Mac/Linux | `build_cxfreeze.py` | [README](BUILD_CXFREEZE_README.md) |
| **Briefcase** | Win/Mac/Linux | `build_briefcase.py` | [README](BUILD_BRIEFCASE_README.md) |
| **Pynsist** | Windows only | `build_pynsist.py` | [README](BUILD_PYNSIST_README.md) |

## 🚀 Quick Start

### Choose Your Tool

Not sure which to use? See [BUILD_TOOLS_COMPARISON.md](BUILD_TOOLS_COMPARISON.md) for a detailed comparison.

**Quick recommendations:**
- **First time?** → Use PyInstaller
- **Need performance?** → Use Nuitka
- **Professional release?** → Use Briefcase
- **Windows installer?** → Use Pynsist
- **PyInstaller issues?** → Try cx_Freeze

### Build Your Application

Each tool has three ways to build:

#### Option 1: Python Script (Recommended)
```bash
# PyInstaller (fastest, easiest)
python build_pyinstaller.py

# Nuitka (best performance)
python build_nuitka.py

# cx_Freeze (most reliable)
python build_cxfreeze.py

# Briefcase (professional installers)
python build_briefcase.py

# Pynsist (Windows installer with bundled Python)
python build_pynsist.py
```

#### Option 2: Platform Scripts
```bash
# Linux/macOS
./build_pyinstaller.sh
./build_nuitka.sh
./build_cxfreeze.sh
./build_briefcase.sh

# Windows
build_pyinstaller.bat
build_nuitka.bat
build_cxfreeze.bat
build_briefcase.bat
build_pynsist.bat
```

#### Option 3: Direct Commands
```bash
# PyInstaller
pyinstaller pyinstaller_config.spec

# Nuitka
python -m nuitka @nuitka_config.txt pycompiler_ark.py

# cx_Freeze
python setup_cxfreeze.py build_exe

# Briefcase
briefcase package

# Pynsist
pynsist installer.cfg
```

## 📁 Project Structure

```
PyCompiler-ARK-Professional/
├── build_*.py              # Build scripts (5 tools)
├── build_*.sh              # Linux/macOS scripts
├── build_*.bat             # Windows scripts
├── BUILD_*_README.md       # Documentation (5 tools)
├── BUILD_TOOLS_COMPARISON.md  # Comparison guide
├── installer.cfg           # Pynsist config
├── nuitka_config.txt       # Nuitka config
├── pyinstaller_config.spec # PyInstaller spec
└── pycompiler_ark.py       # Entry point
```

## 🎯 Use Case Matrix

| Need | Recommended Tool | Alternative |
|------|------------------|-------------|
| Quick testing | PyInstaller | cx_Freeze |
| Production release | Nuitka | Briefcase |
| Windows installer | Pynsist | Briefcase |
| macOS installer | Briefcase | cx_Freeze |
| Linux AppImage | Briefcase | PyInstaller |
| Cross-platform | PyInstaller | cx_Freeze |
| Maximum performance | Nuitka | - |
| Easy updates | Pynsist | - |

## 📊 Build Comparison

| Metric | PyInstaller | Nuitka | cx_Freeze | Briefcase | Pynsist |
|--------|-------------|--------|-----------|-----------|---------|
| Build Time | 2-5 min | 5-15 min | 2-5 min | 10-20 min | 5-10 min |
| Output Size | 100-200 MB | 80-150 MB | 150-300 MB | 150-250 MB | 100-200 MB |
| Ease of Use | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| Performance | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |

## 🔧 Prerequisites by Tool

### PyInstaller
- ✅ Python 3.10+
- ✅ No C compiler needed
- ✅ Works out of the box

### Nuitka
- ✅ Python 3.10+
- ⚠️ C compiler required
- ⚠️ System dependencies (Linux)

### cx_Freeze
- ✅ Python 3.10+
- ✅ No C compiler needed
- ⚠️ Qt libraries (Linux)

### Briefcase
- ✅ Python 3.10+
- ⚠️ WiX Toolset (Windows)
- ⚠️ Xcode CLI Tools (macOS)

### Pynsist
- ✅ Python 3.10+
- ⚠️ NSIS required
- ⚠️ Windows only

## 📦 Output Locations

After building, find your executables here:

```
PyInstaller:  dist/PyCompiler-ARK(.exe)
Nuitka:       build/nuitka/PyCompiler-ARK(.exe)
cx_Freeze:    build/cxfreeze/PyCompiler-ARK(.exe)
Briefcase:    dist/PyCompiler-ARK-1.0.0.(msi|dmg|AppImage)
Pynsist:      build/nsis/PyCompiler-ARK-Setup-1.0.0.exe
```

## 🎓 Getting Started Guide

### For First-Time Users

1. **Start with PyInstaller** (easiest):
   ```bash
   pip install pyinstaller
   python build_pyinstaller.py
   ```

2. **Test the executable**:
   ```bash
   ./dist/PyCompiler-ARK  # Linux/macOS
   dist\PyCompiler-ARK.exe  # Windows
   ```

3. **If satisfied**, you're done!
4. **If you need better performance**, try Nuitka
5. **If you need professional installers**, try Briefcase

### For Production Release

1. **Choose your primary tool** (see comparison guide)
2. **Build on each target platform**
3. **Test installers on clean machines**
4. **Consider code signing** (Briefcase/Pynsist)
5. **Create release notes and distribute**

## 💡 Best Practices

### Development Workflow
```bash
# Daily development
python pycompiler_ark.py

# Test packaging weekly
python build_pyinstaller.py

# Production releases
python build_nuitka.py      # Performance
python build_briefcase.py   # Installers
```

### Testing
- ✅ Test on target OS (not just your dev machine)
- ✅ Test on clean VM/container
- ✅ Verify all features work
- ✅ Check file sizes
- ✅ Test uninstaller (if applicable)

### Distribution
- ✅ Version everything consistently
- ✅ Document system requirements
- ✅ Provide checksums (SHA256)
- ✅ Sign code (production releases)
- ✅ Test auto-updates (if implemented)

## 🐛 Troubleshooting

### Common Issues

**"Tool not found"**
```bash
# Install the tool
pip install pyinstaller  # or nuitka, cx_Freeze, briefcase, pynsist
```

**"Build failed"**
1. Check tool-specific README
2. Verify prerequisites installed
3. Check error message
4. Try alternative tool

**"Executable doesn't run"**
1. Test on clean machine
2. Check missing libraries
3. Verify icon files exist
4. Add hidden imports

### Getting Help

1. Check tool-specific README
2. See [BUILD_TOOLS_COMPARISON.md](BUILD_TOOLS_COMPARISON.md)
3. Check tool's official documentation
4. Search GitHub issues
5. Ask in project discussions

## 📚 Documentation Links

- [PyInstaller Guide](BUILD_PYINSTALLER_README.md)
- [Nuitka Guide](BUILD_NUITKA_README.md)
- [cx_Freeze Guide](BUILD_CXFREEZE_README.md)
- [Briefcase Guide](BUILD_BRIEFCASE_README.md)
- [Pynsist Guide](BUILD_PYNSIST_README.md)
- [Tools Comparison](BUILD_TOOLS_COMPARISON.md)

## 🔄 Migration Between Tools

All tools use the same entry point (`pycompiler_ark.py`), so switching is easy:

```bash
# Currently using PyInstaller?
python build_pyinstaller.py

# Want to try Nuitka?
python build_nuitka.py

# Need Briefcase installers?
python build_briefcase.py
```

No code changes needed! Just run a different build script.

## 🎯 Recommended Combinations

### For Maximum Coverage
Build with multiple tools for different audiences:

```bash
# Windows users
python build_pynsist.py      # Professional installer

# macOS users  
python build_briefcase.py    # DMG installer

# Linux users
python build_briefcase.py    # AppImage

# Power users
python build_nuitka.py       # Optimized binary
```

### For Quick Distribution
Single tool for all platforms:

```bash
# Cross-platform
python build_pyinstaller.py  # Build on each OS
```

## 📊 Summary

You have **5 complete build systems** ready to use:

1. **PyInstaller** - Fast, easy, cross-platform
2. **Nuitka** - Best performance, optimized
3. **cx_Freeze** - Reliable, mature
4. **Briefcase** - Professional installers
5. **Pynsist** - Windows installer with Python

Choose based on your needs, or use multiple tools for maximum coverage!

## 📝 License

Same as PyCompiler ARK++ - Apache License 2.0

---

**Happy Building! 🚀**

Need help? Check the [comparison guide](BUILD_TOOLS_COMPARISON.md) or individual tool READMEs.