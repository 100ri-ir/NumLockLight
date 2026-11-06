# ============================================================
#  NumLock Light 1.1.0 - per-user installer script
#  Used by the IExpress self-extracting fallback installer
#  (Build_Installer.bat generates it when Inno Setup is not
#  available). No admin rights required.
# ============================================================
param([string]$SrcDir = $PSScriptRoot)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Version = '__VER__'
$Dest    = Join-Path $env:LOCALAPPDATA 'Programs\NumLockLight'
$Zip     = Join-Path $SrcDir 'NumLockLight-Payload.zip'

if (-not (Test-Path $Zip)) {
    Write-Host "[ERROR] NumLockLight-Payload.zip not found next to install.ps1"
    exit 1
}

Write-Host "Installing NumLock Light $Version (per-user)..."

# Stop a running copy so its files can be overwritten
Get-Process NumLockLight -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 400

# Extract the onedir tree
New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Expand-Archive -Path $Zip -DestinationPath $Dest -Force

$Exe = Join-Path $Dest 'NumLockLight.exe'
if (-not (Test-Path $Exe)) {
    Write-Host "[ERROR] Extracted package is damaged (NumLockLight.exe missing)."
    exit 1
}

# Copy the uninstaller next to the app
Copy-Item (Join-Path $SrcDir 'uninstall.cmd') $Dest -Force

# --- Shortcuts -----------------------------------------------------------
$Wsh = New-Object -ComObject WScript.Shell

$DesktopLnk = Join-Path ([Environment]::GetFolderPath('Desktop')) 'NumLock Light.lnk'
$s = $Wsh.CreateShortcut($DesktopLnk)
$s.TargetPath = $Exe; $s.WorkingDirectory = $Dest; $s.Save()

$StartDir = Join-Path ([Environment]::GetFolderPath('Programs')) 'NumLock Light'
New-Item -ItemType Directory -Force -Path $StartDir | Out-Null
$MenuLnk = Join-Path $StartDir 'NumLock Light.lnk'
$s = $Wsh.CreateShortcut($MenuLnk)
$s.TargetPath = $Exe; $s.WorkingDirectory = $Dest; $s.Save()

$Uninst = Join-Path $Dest 'uninstall.cmd'
$UninstLnk = Join-Path $StartDir 'Uninstall NumLock Light.lnk'
$s = $Wsh.CreateShortcut($UninstLnk)
$s.TargetPath = $Uninst; $s.WorkingDirectory = $Dest; $s.Save()

# --- Add / Remove Programs entry (per-user) ------------------------------
$Reg = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\NumLockLight100ri'
New-Item -Path $Reg -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'DisplayName'     -Value 'NumLock Light'                    -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'DisplayVersion'  -Value $Version                           -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'Publisher'       -Value 'sadri1993 - 100ri.ir'             -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'DisplayIcon'     -Value $Exe                                -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'UninstallString' -Value ('"{0}"' -f $Uninst)                -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'URLInfoAbout'    -Value 'https://github.com/100ri-ir/NumLockLight' -PropertyType String -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'NoModify'        -Value 1                                   -PropertyType DWord  -Force | Out-Null
New-ItemProperty -Path $Reg -Name 'NoRepair'        -Value 1                                   -PropertyType DWord  -Force | Out-Null

Write-Host ""
Write-Host "Installed to: $Dest"
Write-Host "Starting NumLock Light..."
Start-Process $Exe
exit 0
