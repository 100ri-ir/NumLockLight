@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title NumLock Light - Publish to GitHub (100ri-ir)
cd /d "%~dp0"

:: ============================================================
::  NumLock Light 1.1.0 - ONE-CLICK GitHub PUBLISHER
::
::  HOW TO RUN: double-click this file. That is all.
::  (If Windows SmartScreen shows a blue warning, click
::   "More info" and then "Run anyway" - the file is yours.)
::
::  What this script does, in order:
::    1. Makes sure a proper .gitignore exists
::    2. Installs Git automatically if missing (via winget)
::    3. Installs GitHub CLI automatically if missing (via winget)
::    4. Logs you into GitHub (first run opens your browser)
::    5. Creates the public repo  100ri-ir/NumLockLight
::    6. Uploads the whole SOURCE tree
::    7. Creates release  v1.1.0  and attaches:
::         - NumLockLight-1.1.0-Portable.zip
::         - NumLockLight-Setup-1.1.0.exe
::         - SHA256SUMS.txt  +  README.txt
::    8. Opens the finished repo page in your browser
::
::  For future versions: change VER below (e.g. to 1.2.0).
::  Full step-by-step manual guide: Github.html
:: ============================================================

set VER=1.1.0
set OWNER=100ri-ir
set REPO=NumLockLight
set ASSETS=release\v%VER%
set REPO_URL=https://github.com/%OWNER%/%REPO%

echo ============================================================
echo   NumLock Light %VER%  -  GitHub PUBLISHER
echo   Target: %REPO_URL%
echo   Tip: maximize this window so you can read everything.
echo ============================================================
echo.

:: ---------- 0) release files present? -------------------------
if not exist "%ASSETS%\NumLockLight-%VER%-Portable.zip" (
    if not exist "%ASSETS%\NumLockLight-Setup-%VER%.exe" (
        echo [WARN] %ASSETS% has no release files yet.
        echo        Run  build\Build_All.bat  first to create them.
        echo        ^(The source will still be published now.^)
        echo.
    )
)

:: ---------- 1) find / install git -----------------------------
call :FIND_GIT
if "!GIT!"=="" (
    echo [INFO] Git is not installed yet - installing it now.
    echo        This happens only ONCE. Please wait 1-3 minutes...
    where winget.exe >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] winget is not available on this computer.
        echo Install Git from  https://git-scm.com/download/win
        echo and run this file again.
        start "" https://git-scm.com/download/win
        pause
        exit /b 1
    )
    winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
    call :FIND_GIT
)
if "!GIT!"=="" (
    echo [ERROR] Git could not be installed automatically.
    echo Install it from  https://git-scm.com/download/win
    echo and run this file again.
    pause
    exit /b 1
)
echo [1/6] Git is ready.

:: ---------- 2) git identity (safe local defaults) -------------
"!GIT!" config user.name >nul 2>&1
if errorlevel 1 (
    "!GIT!" config user.name  "%OWNER%"
    "!GIT!" config user.email "%OWNER%@users.noreply.github.com"
)

:: ---------- 3) .gitignore safety net --------------------------
if not exist ".gitignore" (
    echo dist/            > .gitignore
    echo release/         >> .gitignore
    echo .pyinstaller_work/ >> .gitignore
    echo build/installer/ >> .gitignore
    echo __pycache__/     >> .gitignore
    echo *.py[cod]        >> .gitignore
    echo NumLockLight_Data/ >> .gitignore
    echo *.log            >> .gitignore
    echo *.zip            >> .gitignore
    echo *.exe            >> .gitignore
)

:: ---------- 4) init / commit ----------------------------------
if not exist ".git" (
    echo [2/6] Creating a local git repository...
    "!GIT!" init -b main >nul
) else (
    echo [2/6] Local repository found.
)
"!GIT!" add -A
"!GIT!" diff --cached --quiet >nul 2>&1
if not errorlevel 1 (
    echo       Nothing new to upload - the local copy is current.
) else (
    "!GIT!" commit -m "NumLock Light v%VER% - final release" >nul
)

:: ---------- 5) find / install GitHub CLI ----------------------
call :FIND_GH
if "!GH!"=="" (
    echo [INFO] GitHub CLI is not installed yet - installing it now.
    echo        This also happens only ONCE. Please wait 1-3 minutes...
    where winget.exe >nul 2>&1
    if not errorlevel 1 (
        winget install --id GitHub.cli -e --silent --accept-package-agreements --accept-source-agreements
        call :FIND_GH
    )
)
if "!GH!"=="" goto :MANUAL_PUSH
echo [3/6] GitHub CLI is ready.

:: ---------- 6) login ------------------------------------------
"!GH!" auth status >nul 2>&1
if errorlevel 1 (
    echo [4/6] You are not logged into GitHub yet.
    echo.
    echo        A one-time code like  XXXX-XXXX  will appear below,
    echo        and a browser window will open. Then:
    echo          1. Copy the code from this window.
    echo          2. In the browser press:  Sign in with a web browser
    echo          3. Paste the code - Continue - Authorize.
    echo        IMPORTANT: log in with the  %OWNER%  account!
    echo.
    "!GH!" auth login --web --git-protocol https
    "!GH!" auth status >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Login did not finish. Run this file again.
        pause
        exit /b 1
    )
) else (
    echo [4/6] Already logged in. OK.
)
:: Let git use the GitHub CLI credentials - no passwords, ever.
"!GH!" auth setup-git >nul 2>&1

:: ---------- 7) create / connect / push the repo ---------------
"!GH!" repo view %OWNER%/%REPO% >nul 2>&1
if errorlevel 1 (
    echo [5/6] Creating the public repository %REPO_URL% ...
    "!GH!" repo create %REPO% --public --source . --remote origin --push
    if errorlevel 1 (
        echo [ERROR] Could not create the repository.
        echo See the message above, or use the manual method in Github.html.
        pause
        exit /b 1
    )
) else (
    echo [5/6] Repository exists - uploading your files...
    "!GIT!" remote get-url origin >nul 2>&1
    if errorlevel 1 "!GIT!" remote add origin https://github.com/%OWNER%/%REPO%.git
    "!GIT!" push -u origin main
    if errorlevel 1 (
        echo.
        echo [ASK] The online repository is not empty - it probably only
        echo       has the README that GitHub created automatically when
        echo       you made the repository on the website.
        echo       Overwrite it with YOUR local version?
        set /p OVERWRITE=       Type YES and press Enter to overwrite: 
        if /i "!OVERWRITE!"=="YES" (
            "!GIT!" push --force -u origin main
            if errorlevel 1 (
                echo [ERROR] Upload failed. See the message above, or
                echo follow the manual method in Github.html.
                pause
                exit /b 1
            )
        ) else (
            echo [INFO] Skipped. Open Github.html and follow the manual
            echo method there to merge the two versions.
            pause
            exit /b 1
        )
    )
)
echo       Your source is online:  %REPO_URL%

:: ---------- 8) release + asset files --------------------------
echo [6/6] Creating the GitHub Release  v%VER%  ...

set ASSET_FILES=
if exist "%ASSETS%\NumLockLight-%VER%-Portable.zip" set ASSET_FILES=%ASSET_FILES% "%ASSETS%\NumLockLight-%VER%-Portable.zip"
if exist "%ASSETS%\NumLockLight-Setup-%VER%.exe"     set ASSET_FILES=%ASSET_FILES% "%ASSETS%\NumLockLight-Setup-%VER%.exe"
if exist "%ASSETS%\SHA256SUMS.txt"                   set ASSET_FILES=%ASSET_FILES% "%ASSETS%\SHA256SUMS.txt"
if exist "%ASSETS%\README.txt"                       set ASSET_FILES=%ASSET_FILES% "%ASSETS%\README.txt"

set NOTES_ARGS=--notes "NumLock Light v%VER% - final release. Design: sadri1993 - 100ri.ir"
if exist "build\release-notes-v%VER%.md" set NOTES_ARGS=--notes-file "build\release-notes-v%VER%.md"

"!GH!" release view v%VER% >nul 2>&1
if errorlevel 1 (
    if "!ASSET_FILES!"=="" (
        "!GH!" release create v%VER% !NOTES_ARGS! --title "NumLock Light v%VER%"
    ) else (
        "!GH!" release create v%VER% !ASSET_FILES! !NOTES_ARGS! --title "NumLock Light v%VER%"
    )
    if errorlevel 1 (
        echo [ERROR] Creating the release failed.
        echo You can attach the files manually - see the Release section
        echo of Github.html.
        pause
        exit /b 1
    )
) else (
    if not "!ASSET_FILES!"=="" (
        echo       Release v%VER% already exists - refreshing its files...
        "!GH!" release upload v%VER% !ASSET_FILES! --clobber
    )
)

echo.
echo ============================================================
echo   PUBLISHED !!
echo.
echo   Repository : %REPO_URL%
echo   This release: %REPO_URL%/releases/tag/v%VER%
echo   Always-latest: %REPO_URL%/releases/latest
echo.
echo   Put the "Always-latest" link on your website 100ri.ir
echo   - it automatically points to every future version.
echo ============================================================
start "" %REPO_URL%
echo.
pause
exit /b 0

:: ============================================================
:FIND_GIT
set GIT=
where git.exe >nul 2>&1 && set GIT=git.exe
if "!GIT!"=="" if exist "%ProgramFiles%\Git\cmd\git.exe" set GIT=%ProgramFiles%\Git\cmd\git.exe
if "!GIT!"=="" if exist "%ProgramFiles(x86)%\Git\cmd\git.exe" set GIT=%ProgramFiles(x86)%\Git\cmd\git.exe
if "!GIT!"=="" if exist "%LOCALAPPDATA%\Programs\Git\cmd\git.exe" set GIT=%LOCALAPPDATA%\Programs\Git\cmd\git.exe
goto :eof

:FIND_GH
set GH=
where gh.exe >nul 2>&1 && set GH=gh.exe
if "!GH!"=="" if exist "%ProgramFiles%\GitHub CLI\gh.exe" set GH=%ProgramFiles%\GitHub CLI\gh.exe
if "!GH!"=="" if exist "%ProgramFiles(x86)%\GitHub CLI\gh.exe" set GH=%ProgramFiles(x86)%\GitHub CLI\gh.exe
if "!GH!"=="" if exist "%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe" set GH=%LOCALAPPDATA%\Programs\GitHub CLI\gh.exe
goto :eof

:: ============================================================
:MANUAL_PUSH
echo ============================================================
echo   MANUAL MODE - the GitHub CLI could not be installed.
echo   Your source is committed locally. Do this once:
echo.
echo   1^) A browser tab is opening now at:  github.com/new
echo   2^) Repository name:  %REPO%     - choose  Public
echo   3^) Do NOT tick "Add a README file"
echo   4^) Press the green  Create repository  button
echo   5^) Come back to this window and press any key
echo.
echo   Note: the very first upload may open a browser window
echo   asking you to sign in to GitHub - approve it.
echo ============================================================
start "" https://github.com/new
pause

"!GIT!" remote get-url origin >nul 2>&1
if errorlevel 1 "!GIT!" remote add origin https://github.com/%OWNER%/%REPO%.git
"!GIT!" push -u origin main
if errorlevel 1 (
    echo [ERROR] Push failed - read the message above.
    pause
    exit /b 1
)
echo.
echo Uploaded. Now create the release in the browser:
echo   Open:  %REPO_URL%/releases/new
echo   Tag:   v%VER%
echo   Attach the files from:  %ASSETS%
start "" %REPO_URL%/releases/new
pause
exit /b 0
