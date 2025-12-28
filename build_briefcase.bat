@echo off
REM SPDX-License-Identifier: Apache-2.0
REM PyCompiler ARK++ - Briefcase Build Script (Windows)

setlocal enabledelayedexpansion

echo ======================================================================
echo 🚀 Building PyCompiler ARK++ with Briefcase
echo ======================================================================

REM Check if Briefcase is installed
briefcase --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Briefcase is not installed
    echo 📦 Installing Briefcase...
    python -m pip install briefcase
)

echo 📋 Platform: Windows

echo 🏗️  Creating application scaffold...
briefcase create
if errorlevel 1 goto :error

echo 🏗️  Building application...
briefcase build
if errorlevel 1 goto :error

echo 📦 Packaging application...
briefcase package
if errorlevel 1 goto :error

echo.
echo ======================================================================
echo ✅ Build completed successfully!
echo ======================================================================
echo 📦 Installer: dist\PyCompiler-ARK-1.0.0.msi
echo.
echo ℹ️  You can also run without packaging:
echo    briefcase dev
echo    briefcase run
echo.

endlocal
exit /b 0

:error
echo.
echo ======================================================================
echo ❌ Build failed!
echo ======================================================================
endlocal
exit /b 1