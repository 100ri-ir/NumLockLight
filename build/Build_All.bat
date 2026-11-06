@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title NumLock Light - Full Release Builder
cd /d "%~dp0.."

echo ====================================================
echo   NumLock Light - FULL RELEASE (v1.1.0 FINAL)
echo   Builds: onedir EXE + portable ZIP + installer
echo   Output: release\v1.1.0\
echo ====================================================
echo.

set VER=1.1.0
set REL=release\v%VER%

:: ---------- 1) onedir exe bundle ----------
echo [1/4] Building onedir EXE bundle...
call build\Build_Portable.bat %1
if errorlevel 1 exit /b 1
echo.

:: ---------- 2) portable zip ----------
echo [2/4] Packing portable ZIP...
if exist "%REL%" rmdir /s /q "%REL%"
mkdir "%REL%\portable" 2>nul

xcopy /e /i /y "dist\NumLockLight" "%REL%\portable\NumLockLight" >nul
echo. > "%REL%\portable\NumLockLight\portable.flag"
if exist "README_FA.md" copy /y "README_FA.md" "%REL%\portable\" >nul
copy /y "LICENSE" "%REL%\portable\" >nul

powershell -NoProfile -Command "$ProgressPreference='SilentlyContinue'; Compress-Archive -Path 'release\v%VER%\portable\*' -DestinationPath 'release\v%VER%\NumLockLight-%VER%-Portable.zip' -Force"
if errorlevel 1 (
    echo [ERROR] Could not create ZIP.
    if not "%1"=="ci" pause
    exit /b 1
)
rmdir /s /q "%REL%\portable"
echo Portable ZIP OK.
echo.

:: ---------- 3) installer ----------
echo [3/4] Building setup installer...
call build\Build_Installer.bat %1
if errorlevel 1 exit /b 1
move /y "build\installer\NumLockLight-Setup-%VER%.exe" "%REL%\NumLockLight-Setup-%VER%.exe" >nul
echo.

:: ---------- 4) checksums + notes ----------
echo [4/4] Checksums...
powershell -NoProfile -Command "Get-ChildItem 'release\v%VER%' | ForEach-Object { $h = Get-FileHash $_.FullName -Algorithm SHA256; ('{0}  {1}' -f $h.Hash, $_.Name) } | Set-Content -Encoding ascii 'release\v%VER%\SHA256SUMS.txt'"

(
echo NumLock Light %VER% - Release
echo ================================
echo.
echo Files:
echo   NumLockLight-Setup-%VER%.exe      Installer ^(recommended^)
echo   NumLockLight-%VER%-Portable.zip   Portable version ^(onedir^)
echo   SHA256SUMS.txt                    Integrity checks
echo.
echo Portable: extract anywhere and run NumLockLight.exe. A "portable.flag"
echo file inside makes settings stay next to the EXE.
echo Installer: settings live in %%APPDATA%%\NumLockLight.
echo Troubleshooting: run "NumLockLight.exe --check" and read
echo NumLockLight.log next to settings.json.
) > "%REL%\README.txt"

echo.
echo ====================================================
echo   RELEASE READY:  %CD%\%REL%\
echo.
dir /b "%REL%"
echo ====================================================
echo.
echo NEXT STEPS
echo   - Test the portable ZIP and the setup EXE once.
echo   - Publish everything to GitHub with:
echo       Publish_To_Github.bat   ^(automatic, see Github.html^)
echo   - Or follow the manual guide in Github.html.
echo ====================================================
if not "%1"=="ci" pause
exit /b 0