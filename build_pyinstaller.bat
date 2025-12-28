@echo off
REM SPDX-License-Identifier: Apache-2.0
REM PyCompiler ARK++ - PyInstaller Build Script (Windows)

setlocal enabledelayedexpansion

echo ======================================================================
echo 🚀 Building PyCompiler ARK++ with PyInstaller
echo ======================================================================

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  PyInstaller is not installed
    echo 📦 Installing PyInstaller...
    python -m pip install pyinstaller
)

echo 📋 Platform: Windows
echo 🏗️  Starting build process...
echo.

REM Build with PyInstaller
pyinstaller ^
    --onefile ^
    --noconfirm ^
    --clean ^
    --noupx ^
    --name=PyCompiler-ARK ^
    --distpath=dist ^
    --workpath=build ^
    --specpath=. ^
    --icon=logo\logo.png ^
    --add-data=themes;themes ^
    --add-data=languages;languages ^
    --add-data=logo;logo ^
    --add-data=ui;ui ^
    --hidden-import=PySide6.QtCore ^
    --hidden-import=PySide6.QtGui ^
    --hidden-import=PySide6.QtWidgets ^
    --hidden-import=PySide6.QtUiTools ^
    --hidden-import=psutil ^
    --hidden-import=yaml ^
    --hidden-import=PIL ^
    --hidden-import=PIL.Image ^
    --hidden-import=jsonschema ^
    --hidden-import=multiprocessing ^
    --hidden-import=faulthandler ^
    --collect-all=PySide6 ^
    --collect-all=shiboken6 ^
    --collect-binaries=PySide6 ^
    --collect-data=PySide6 ^
    --exclude-module=tkinter ^
    --exclude-module=matplotlib ^
    --exclude-module=numpy ^
    --exclude-module=scipy ^
    --exclude-module=pandas ^
    --exclude-module=IPython ^
    --exclude-module=notebook ^
    --exclude-module=jupyter ^
    --exclude-module=pytest ^
    --exclude-module=unittest ^
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
echo 📦 Executable: dist\PyCompiler-ARK.exe
echo.

endlocal