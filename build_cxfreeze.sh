#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# PyCompiler ARK++ - cx_Freeze Build Script (Linux/macOS)

set -e

echo "======================================================================"
echo "🚀 Building PyCompiler ARK++ with cx_Freeze"
echo "======================================================================"

# Check if cx_Freeze is installed
if ! python3 -c "import cx_Freeze" &> /dev/null; then
    echo "⚠️  cx_Freeze is not installed"
    echo "📦 Installing cx_Freeze..."
    python3 -m pip install cx_Freeze
fi

# Detect platform
OS_TYPE=$(uname -s)
echo "📋 Platform: $OS_TYPE"

# Create setup script
echo "🏗️  Creating setup script..."
python3 build_cxfreeze.py

echo ""
echo "======================================================================"
echo "✅ Build completed successfully!"
echo "======================================================================"
echo "📦 Application: build/cxfreeze/PyCompiler-ARK"
echo ""
echo "💡 To run:"
echo "   cd build/cxfreeze"
echo "   ./PyCompiler-ARK"
echo ""