@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title NumLock Light - Portable Builder
cd /d "%~dp0.."

echo ============================================
echo   NumLock Light 1.1.0 - Portable Builder
echo   Output: dist\NumLockLight\ (onedir)
echo   Design: sadri1993 - 100ri.ir
echo ============================================
echo.

:: ---------- Check Python ----------
where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python launcher not found.
    echo Install Python 3.10+ and enable "Add Python to PATH".
    if not "%1"=="ci" pause
    exit /b 1
)
py -3 --version
echo.

:: ---------- Smart dependency check (BUILD-TIME ONLY) ----------
echo [1/3] Checking dependencies...
set NEED_INSTALL=0
py -3 -c "import pystray" >nul 2>&1 || set NEED_INSTALL=1
py -3 -c "import PIL" >nul 2>&1 || set NEED_INSTALL=1
py -3 -c "import arabic_reshaper" >nul 2>&1 || set NEED_INSTALL=1
py -3 -c "import bidi.algorithm" >nul 2>&1 || set NEED_INSTALL=1
py -3 -c "import PyInstaller" >nul 2>&1 || set NEED_INSTALL=1

if !NEED_INSTALL!==0 (
    echo All dependencies already installed.
    goto :skip_pip
)

echo Missing dependencies detected. Installing...
py -3 -m pip install --disable-pip-version-check -r requirements.txt pyinstaller
if errorlevel 1 (
    echo PyPI failed. Trying mirror...
    py -3 -m pip install --disable-pip-version-check -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt pyinstaller
)
if errorlevel 1 (
    echo [ERROR] Could not install dependencies.
    if not "%1"=="ci" pause
    exit /b 1
)
:skip_pip
echo.

:: ---------- Verify bundled assets (build-time; Fetch_Assets never runs at user install time) ----------
echo [2/3] Verifying assets...
if not exist "assets\fonts\Vazirmatn-Regular.ttf" (
    echo [WARN] Fonts missing. Running Fetch_Assets.py ...
    py -3 build\Fetch_Assets.py
)
if not exist "assets\sounds\on-chime.wav" (
    echo [WARN] Sounds missing. Running Fetch_Assets.py ...
    py -3 build\Fetch_Assets.py
)
if not exist "assets\icons\app.ico" (
    echo [ERROR] assets\icons\app.ico not found. Run: py -3 build\Fetch_Assets.py
    if not "%1"=="ci" pause
    exit /b 1
)
echo Assets OK.
echo.

:: ---------- Build (onedir) ----------
echo [3/3] Building portable onedir bundle...

:: A running copy of the app locks dist\ files — the previous build
:: attempts failed with "Access is denied" because of exactly this.
taskkill /f /im NumLockLight.exe >nul 2>&1

if exist ".pyinstaller_work" rmdir /s /q ".pyinstaller_work"
if exist "dist" rmdir /s /q "dist"

py -3 -m PyInstaller --noconfirm --clean --workpath .pyinstaller_work ^
    --distpath dist ^
    build\NumLockLight.spec

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    if not "%1"=="ci" pause
    exit /b 1
)

if not exist "dist\NumLockLight\NumLockLight.exe" (
    echo [ERROR] Expected dist\NumLockLight\NumLockLight.exe not found.
    if not "%1"=="ci" pause
    exit /b 1
)

echo.
echo ============================================
echo   BUILD SUCCESSFUL (onedir)
echo   Output: %CD%\dist\NumLockLight\
echo   Run:    dist\NumLockLight\NumLockLight.exe
echo   Portable: add portable.flag next to the exe
echo   (settings then stay in NumLockLight_Data\)
echo ============================================
if not "%1"=="ci" pause
exit /b 0
