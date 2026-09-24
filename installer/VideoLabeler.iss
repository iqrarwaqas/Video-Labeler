; Inno Setup script for Video Speaker Labeler.
; Build the app first (pyinstaller packaging/VideoLabeler.spec), then from the repo root:
;   iscc /DAppVersion=1.0.0 installer\VideoLabeler.iss
; Output: dist\VideoLabeler-Setup-<version>.exe

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; Never change AppId: it is how a new installer finds and upgrades the old install.
AppId={{7BCE872A-4465-463C-B463-F57B32DB53AF}
AppName=Video Speaker Labeler
AppVersion={#AppVersion}
AppPublisher=Synapsify
AppPublisherURL=https://github.com/iqrarwaqas/Video-Labeler
DefaultDirName={autopf}\Video Speaker Labeler
DefaultGroupName=Video Speaker Labeler
DisableProgramGroupPage=yes
; Per-user install (no admin prompt), so updates can install silently.
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=VideoLabeler-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
UninstallDisplayIcon={app}\VideoLabeler.exe

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[InstallDelete]
; Remove the old version's libraries so nothing stale is left after an update.
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "..\dist\VideoLabeler\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Video Speaker Labeler"; Filename: "{app}\VideoLabeler.exe"
Name: "{autodesktop}\Video Speaker Labeler"; Filename: "{app}\VideoLabeler.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\VideoLabeler.exe"; Description: "Start Video Speaker Labeler"; Flags: nowait postinstall skipifsilent
; In-app updates run the installer with /SILENT /RELAUNCH=1: start the new version afterwards.
Filename: "{app}\VideoLabeler.exe"; Flags: nowait; Check: ShouldRelaunch

[Code]
function ShouldRelaunch: Boolean;
begin
  Result := ExpandConstant('{param:relaunch|0}') = '1';
end;
