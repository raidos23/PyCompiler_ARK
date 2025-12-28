#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# PyCompiler ARK++ - Nuitka Build Script (Linux/macOS)

set -e

echo "======================================================================"
echo "🚀 Building PyCompiler ARK++ with Nuitka"
echo "======================================================================"

# Check if Nuitka is installed
if ! python3 -m nuitka --version &> /dev/null; then
    echo "⚠️  Nuitka is not installed"
    echo "📦 Installing Nuitka..."
    python3 -m pip install nuitka
fi

# Detect platform
OS_TYPE=$(uname -s)
echo "📋 Platform: $OS_TYPE"

# Build command
CMD="python3 -m nuitka \
    --standalone \
    --onefile \
    --follow-imports \
    --enable-plugin=pyside6 \
    --output-dir=build/nuitka \
    --output-filename=PyCompiler-ARK \
    --show-progress \
    --show-memory \
    --lto=yes \
    --jobs=$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4) \
    --include-package=Core \
    --include-package=engine_sdk \
    --include-package=ENGINES \
    --include-package=bcasl \
    --include-package=Plugins_SDK \
    --include-module=PySide6.QtCore \
    --include-module=PySide6.QtGui \
    --include-module=PySide6.QtWidgets \
    --include-module=PySide6.QtUiTools \
    --include-module=psutil \
    --include-module=yaml \
    --include-module=PIL \
    --include-module=jsonschema \
    --include-data-dir=themes=themes \
    --include-data-dir=languages=languages \
    --include-data-dir=logo=logo \
    --include-data-dir=ui=ui \
    --remove-output \
    --assume-yes-for-downloads"

# Add platform-specific options
if [[ "$OS_TYPE" == "Linux" ]]; then
    if [[ -f "logo/logo.png" ]]; then
        CMD="$CMD --linux-icon=logo/logo.png"
    fi
elif [[ "$OS_TYPE" == "Darwin" ]]; then
    CMD="$CMD --macos-app-name='PyCompiler ARK++'"
    if [[ -f "logo/logo.png" ]]; then
        CMD="$CMD --macos-app-icon=logo/logo.png"
    fi
fi

# Add main script
CMD="$CMD pycompiler_ark.py"

echo "🏗️  Starting build process..."
echo ""

# Execute build
eval $CMD

echo ""
echo "======================================================================"
echo "✅ Build completed successfully!"
echo "======================================================================"
echo "📦 Executable: build/nuitka/PyCompiler-ARK"
echo ""