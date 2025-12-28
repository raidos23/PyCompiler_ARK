#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# PyCompiler ARK++ - Briefcase Build Script (Linux/macOS)

set -e

echo "======================================================================"
echo "🚀 Building PyCompiler ARK++ with Briefcase"
echo "======================================================================"

# Check if Briefcase is installed
if ! briefcase --version &> /dev/null; then
    echo "⚠️  Briefcase is not installed"
    echo "📦 Installing Briefcase..."
    python3 -m pip install briefcase
fi

# Detect platform
OS_TYPE=$(uname -s)
echo "📋 Platform: $OS_TYPE"

echo "🏗️  Creating application scaffold..."
briefcase create

echo "🏗️  Building application..."
briefcase build

echo "📦 Packaging application..."
briefcase package

echo ""
echo "======================================================================"
echo "✅ Build completed successfully!"
echo "======================================================================"

if [[ "$OS_TYPE" == "Linux" ]]; then
    echo "📦 Package: dist/PyCompiler-ARK-1.0.0.AppImage"
elif [[ "$OS_TYPE" == "Darwin" ]]; then
    echo "📦 Package: dist/PyCompiler-ARK-1.0.0.dmg"
fi

echo ""
echo "ℹ️  You can also run without packaging:"
echo "   briefcase dev"
echo "   briefcase run"
echo ""