@echo off
rem ============================================================
rem  NumLock Light - per-user uninstaller (IExpress install)
rem ============================================================
setlocal
echo Removing NumLock Light ...
taskkill /f /im NumLockLight.exe >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\NumLockLight100ri" /f >nul 2>&1
del "%USERPROFILE%\Desktop\NumLock Light.lnk" >nul 2>&1
rd /s /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\NumLock Light" >nul 2>&1
rd /s /q "%LOCALAPPDATA%\Programs\NumLockLight" >nul 2>&1
echo Done. NumLock Light has been removed.
echo (User settings in %%APPDATA%%\NumLockLight were kept.)
pause
