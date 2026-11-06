@echo off
rem ============================================================
rem  NumLock Light - IExpress SFX bootstrap installer (1.1.0)
rem  Runs from the SFX extraction dir; all real work is in
rem  install.ps1. Installs per-user (no admin required) into
rem  %LOCALAPPDATA%\Programs\NumLockLight
rem ============================================================
setlocal
set "SRC=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SRC%install.ps1" -SrcDir "%SRC%"
exit /b %ERRORLEVEL%
