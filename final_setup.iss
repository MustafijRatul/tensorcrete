; PROFESSIONAL INSTALLER SCRIPT FOR TENSORCRETE
; Version 1.0 - AI Structural Analysis

#define MyAppName "TensorCrete"
#define MyAppVersion "1.0"
#define MyAppPublisher "Ratul"
#define MyAppURL "http://github.com/MustafijRatul/"
#define MyAppExeName "TensorCrete.exe"

[Setup]
; --- CORE SETTINGS ---
; Unique AppId for TensorCrete
AppId={{9C215688-5B1D-4E2F-A9C3-8845612F9E11}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; --- INSTALLATION PATH ---
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin

; --- BUILD OUTPUT ---
OutputDir=.
OutputBaseFilename=TensorCrete_Setup_v1.0
; Ensure icon.ico exists in the same folder as this script
SetupIconFile=icon.ico

; --- VISUALS & UI ---
WizardStyle=modern
Compression=lzma2/ultra64
SolidCompression=yes
UninstallDisplayIcon={app}\{#MyAppExeName}

; --- BRANDING IMAGES ---
; Uncomment these lines if you have the BMP files
WizardImageFile=sidebar.bmp
WizardSmallImageFile=logo.bmp

; --- TEXT & AGREEMENTS ---
LicenseFile=license.txt
InfoBeforeFile=readme.txt

; --- BEHAVIOR ---
CloseApplications=yes
CloseApplicationsFilter=*.exe
RestartIfNeededByRun=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; ⚠️ CRITICAL: Point this to your dist folder where PyInstaller output is
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up the AppData folder used by the Python code
Type: files; Name: "{userappdata}\RatulApps\TensorCrete\settings.json"
Type: files; Name: "{userappdata}\RatulApps\TensorCrete\history.json"
Type: dirifempty; Name: "{userappdata}\RatulApps\TensorCrete"
Type: dirifempty; Name: "{userappdata}\RatulApps"

; =====================================================================
;  CUSTOM CODE TO KILL THE APP IF RUNNING
; =====================================================================
[Code]
procedure TaskKill(FileName: String);
var
  ResultCode: Integer;
begin
    Exec(ExpandConstant('{cmd}'), '/C taskkill /F /IM "' + FileName + '" /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
begin
  TaskKill('{#MyAppExeName}');
  Result := True;
end;