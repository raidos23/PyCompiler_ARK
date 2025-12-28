#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# PyCompiler ARK++ - PyInstaller Build Script (Linux/macOS)

set -e

echo "======================================================================"
echo "🚀 Building PyCompiler ARK++ with PyInstaller"
echo "======================================================================"

# Check if PyInstaller is installed
if ! pyinstaller --version &> /dev/null; then
    echo "⚠️  PyInstaller is not installed"
    echo "📦 Installing PyInstaller..."
    python3 -m pip install pyinstaller
fi

# Detect platform
OS_TYPE=$(uname -s)
echo "📋 Platform: $OS_TYPE"

# Data separator (: for Unix, ; for Windows)
SEPARATOR=":"

# Build command
pyinstaller \
    --onefile \
    --noconfirm \
    --clean \
    --noupx \
    --name=PyCompiler-ARK \
    --distpath=dist \
    --workpath=build \
    --specpath=. \
    --add-data="themes${SEPARATOR}themes" \
    --add-data="languages${SEPARATOR}languages" \
    --add-data="logo${SEPARATOR}logo" \
    --add-data="ui${SEPARATOR}ui" \
    --hidden-import=PySide6.QtCore \
    --hidden-import=PySide6.QtGui \
    --hidden-import=PySide6.QtWidgets \
    --hidden-import=PySide6.QtUiTools \
    --hidden-import=psutil \
    --hidden-import=yaml \
    --hidden-import=PIL \
    --hidden-import=PIL.Image \
    --hidden-import=jsonschema \
    --hidden-import=multiprocessing \
    --hidden-import=faulthandler \
    --collect-all=PySide6 \
    --collect-all=shiboken6 \
    --collect-binaries=PySide6 \
    --collect-data=PySide6 \
    --exclude-module=tkinter \
    --exclude-module=matplotlib \
    --exclude-module=numpy \
    --exclude-module=scipy \
    --exclude-module=pandas \
    --exclude-module=IPython \
    --exclude-module=notebook \
    --exclude-module=jupyter \
    --exclude-module=pytest \
    --exclude-module=unittest \
    pycompiler_ark.py

echo ""
echo "======================================================================"
echo "✅ Build completed successfully!"
echo "======================================================================"
echo "📦 Executable: dist/PyCompiler-ARK"
echo ""