@echo off
REM SPDX-License-Identifier: Apache-2.0
REM PyCompiler ARK++ - Pynsist Build Script (Windows)

setlocal enabledelayedexpansion

echo ======================================================================
echo 🚀 Building PyCompiler ARK++ Windows Installer with pynsist
echo ======================================================================

REM Check if pynsist is installed
python -m pip show pynsist >nul 2>&1
if errorlevel 1 (
    echo ⚠️  pynsist is not installed
    echo 📦 Installing pynsist...
    python -m pip install pynsist
)

REM Check if NSIS is installed
where makensis >nul 2>&1
if errorlevel 1 (
    echo.
    echo ⚠️  NSIS is not installed!
    echo    pynsist requires NSIS to create Windows installers.
    echo.
    echo 📥 Install NSIS:
    echo    Download from: https://nsis.sourceforge.io/Download
    echo    Or use: winget install NSIS.NSIS
    echo    Or use: choco install nsis
    echo.
    echo After installing NSIS, run this script again.
    exit /b 1
)

echo 📋 Platform: Windows

REM Create installer configuration
echo 🏗️  Creating installer configuration...
python build_pynsist.py

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
echo 📦 Installer: build\nsis\PyCompiler-ARK-Setup-1.0.0.exe
echo.
echo 💡 The installer includes Python and all dependencies
echo    Users don't need Python installed!
echo.

endlocal