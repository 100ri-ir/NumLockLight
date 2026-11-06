@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title NumLock Light - Installer Builder
cd /d "%~dp0.."

set VER=1.1.0
set OUT=build\installer\NumLockLight-Setup-%VER%.exe

echo ============================================
echo   NumLock Light %VER% - Setup Installer
echo   (Inno Setup - real wizard + uninstaller)
echo ============================================
echo.

if exist "dist\NumLockLight\NumLockLight.exe" goto :HAVE_DIST
echo [INFO] onedir bundle not found - building it first...
call build\Build_Portable.bat ci
if errorlevel 1 goto :FAIL

:HAVE_DIST
taskkill /f /im NumLockLight.exe >nul 2>&1

if not exist "build\installer" mkdir "build\installer" 2>nul
if exist "%OUT%" del /f /q "%OUT%" 2>nul

call :FIND_ISCC
if not "!ISCC!"=="" goto :COMPILE

echo [INFO] Inno Setup not found. Trying to install it automatically...
where winget >nul 2>&1
if errorlevel 1 goto :DOWNLOAD_INNO
winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements
call :FIND_ISCC
if not "!ISCC!"=="" goto :COMPILE

:DOWNLOAD_INNO
echo [INFO] Downloading Inno Setup from jrsoftware.org ...
set "INNO_EXE=%TEMP%\innosetup-installer.exe"
if exist "%INNO_EXE%" del /f /q "%INNO_EXE%" >nul 2>&1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -UseBasicParsing 'https://jrsoftware.org/download.php/is.exe' -OutFile '%INNO_EXE%'"
if exist "%INNO_EXE%" (
    echo [INFO] Installing Inno Setup silently...
    "%INNO_EXE%" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER
    del /f /q "%INNO_EXE%" >nul 2>&1
)
call :FIND_ISCC
if not "!ISCC!"=="" goto :COMPILE

echo.
echo [ERROR] Could not install Inno Setup automatically.
echo         Download it manually from: https://jrsoftware.org/isdl.php
echo         Install it, then run this script again.
goto :FAIL

:COMPILE
echo [INFO] Using Inno Setup: !ISCC!
"!ISCC!" "build\NumLockLight.iss"
if errorlevel 1 goto :FAIL
if not exist "%OUT%" goto :FAIL

echo.
echo ============================================
echo   INSTALLER BUILT
echo   Output: %CD%\%OUT%
if not "%1"=="ci" if not exist "release\v%VER%" mkdir "release\v%VER%"
if not "%1"=="ci" copy /y "%OUT%" "release\v%VER%\" >nul
if not "%1"=="ci" echo   Copy:   %CD%\release\v%VER%\NumLockLight-Setup-%VER%.exe
echo ============================================
if not "%1"=="ci" pause
exit /b 0

:FAIL
echo.
echo [ERROR] Installer build failed. See messages above.
if not "%1"=="ci" pause
exit /b 1

:FIND_ISCC
set "ISCC="
for %%V in (7 6 5) do (
    if "!ISCC!"=="" call :CHK_ISCC "%ProgramFiles(x86)%\Inno Setup %%V\ISCC.exe"
    if "!ISCC!"=="" call :CHK_ISCC "%ProgramFiles%\Inno Setup %%V\ISCC.exe"
    if "!ISCC!"=="" call :CHK_ISCC "%LOCALAPPDATA%\Programs\Inno Setup %%V\ISCC.exe"
)
if not "!ISCC!"=="" goto :eof
where ISCC.exe >nul 2>&1
if not errorlevel 1 set "ISCC=ISCC.exe"
goto :eof

:CHK_ISCC
if exist %1 set "ISCC=%~1"
goto :eof
