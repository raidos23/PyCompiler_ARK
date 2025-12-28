@echo off
REM SPDX-License-Identifier: Apache-2.0
REM PyCompiler ARK++ - cx_Freeze Build Script (Windows)

setlocal enabledelayedexpansion

echo ======================================================================
echo 🚀 Building PyCompiler ARK++ with cx_Freeze
echo ======================================================================

REM Check if cx_Freeze is installed
python -c "import cx_Freeze" >nul 2>&1
if errorlevel 1 (
    echo ⚠️  cx_Freeze is not installed
    echo 📦 Installing cx_Freeze...
    python -m pip install cx_Freeze
)

echo 📋 Platform: Windows

REM Create and run setup script
echo 🏗️  Creating and running setup script...
python build_cxfreeze.py

if errorlevel 1 (
    echo.
    echo ======================================================================
    echo ❌ Build failed!
    echo ======================================================================
    exit /b 1
)

echo.
echo ======================================================================
echo ✅ Build completed successfully!
echo ======================================================================
echo 📦 Application: build\cxfreeze\PyCompiler-ARK.exe
echo.
echo 💡 To run:
echo    cd build\cxfreeze
echo    PyCompiler-ARK.exe
echo.

endlocal