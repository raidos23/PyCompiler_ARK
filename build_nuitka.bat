@echo off
REM SPDX-License-Identifier: Apache-2.0
REM PyCompiler ARK++ - Nuitka Build Script (Windows)

setlocal enabledelayedexpansion

echo ======================================================================
echo 🚀 Building PyCompiler ARK++ with Nuitka
echo ======================================================================

REM Check if Nuitka is installed
python -m nuitka --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Nuitka is not installed
    echo 📦 Installing Nuitka...
    python -m pip install nuitka
)

echo 📋 Platform: Windows
echo 🏗️  Starting build process...
echo.

REM Build with Nuitka
python -m nuitka ^
    --standalone ^
    --onefile ^
    --follow-imports ^
    --enable-plugin=pyside6 ^
    --output-dir=build\nuitka ^
    --output-filename=PyCompiler-ARK ^
    --show-progress ^
    --show-memory ^
    --lto=yes ^
    --jobs=%NUMBER_OF_PROCESSORS% ^
    --include-package=Core ^
    --include-package=engine_sdk ^
    --include-package=ENGINES ^
    --include-package=bcasl ^
    --include-package=Plugins_SDK ^
    --include-module=PySide6.QtCore ^
    --include-module=PySide6.QtGui ^
    --include-module=PySide6.QtWidgets ^
    --include-module=PySide6.QtUiTools ^
    --include-module=psutil ^
    --include-module=yaml ^
    --include-module=PIL ^
    --include-module=jsonschema ^
    --include-data-dir=themes=themes ^
    --include-data-dir=languages=languages ^
    --include-data-dir=logo=logo ^
    --include-data-dir=ui=ui ^
    --windows-disable-console ^
    --windows-icon-from-ico=logo\logo.png ^
    --windows-company-name=PyCompiler ^
    --windows-product-name=PyCompiler ARK++ ^
    --windows-product-version=1.0.0 ^
    --windows-file-description=Python Compilation Toolkit ^
    --remove-output ^
    --assume-yes-for-downloads ^
    pycompiler_ark.py

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
echo 📦 Executable: build\nuitka\PyCompiler-ARK.exe
echo.

endlocal