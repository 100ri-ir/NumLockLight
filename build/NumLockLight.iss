; ============================================================
;  NumLock Light 1.1.0 - Inno Setup installer script
;  Build:  ISCC.exe build\NumLockLight.iss
;  Output: build\installer\NumLockLight-Setup-1.1.0.exe
; ============================================================

#define MyAppName "NumLock Light"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "sadri1993 - 100ri.ir"
#define MyAppURL "https://100ri.ir"
#define MyAppExeName "NumLockLight.exe"

[Setup]
AppId={{7C1A9E42-5B23-4D18-9A6B-3E0F21C51001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
VersionInfoVersion={#MyAppVersion}
; --- install location: ALWAYS ask the user ---
DefaultDirName={autopf}\NumLock Light
DisableDirPage=no
UsePreviousAppDir=yes
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; --- Add/Remove Programs entry (created automatically by Inno) ---
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
; --- output ---
OutputDir=installer
OutputBaseFilename=NumLockLight-Setup-{#MyAppVersion}
SetupIconFile=..\assets\icons\app.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; Per-user install by default (no admin), user may choose "all users" in a dialog
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
ArchitecturesInstallIn64BitMode=x64
CloseApplications=force
RestartApplications=no
#if FileExists("..\LICENSE")
LicenseFile=..\LICENSE
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
CreateDesktopIcon=Create a &desktop shortcut / ایجاد میان‌بر در دسکتاپ
StartWithWindows=Start with &Windows (tray indicator) / اجرای خودکار با ویندوز
LaunchProgram=Launch {#MyAppName} / اجرای برنامه
DeleteUserData=Also delete user settings and log (%APPDATA%\NumLockLight)?%n%nتنظیمات کاربر و فایل گزارش هم حذف شود؟

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "{cm:StartWithWindows}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\NumLockLight\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\README_FA.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "NumLockLight100ri"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/f /im {#MyAppExeName}"; Flags: runhidden; RunOnceId: "KillNumLockLight"

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}') + '\NumLockLight';
    if DirExists(DataDir) and (not UninstallSilent) then
      if MsgBox(ExpandConstant('{cm:DeleteUserData}'), mbConfirmation, MB_YESNO) = IDYES then
        DelTree(DataDir, True, True, True);
  end;
end;
