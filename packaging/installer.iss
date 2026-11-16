; Instalator Inno Setup 6 — KRÓTKI WSPORNIK ST
#define AppName "KRÓTKI WSPORNIK ST"
#define AppVersion "1.0.0"
#define AppExe "KrotkiWspornikST.exe"

[Setup]
AppId={{6B0E4C7A-3D5F-4B8E-9A21-5C2E7F1D9A01}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={autopf}\KrotkiWspornikST
DefaultGroupName={#AppName}
OutputDir=..\dist\installer
OutputBaseFilename=KrotkiWspornikST-{#AppVersion}-setup
SetupIconFile=icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ChangesAssociations=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\KrotkiWspornikST\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.kwst"; ValueType: string; ValueName: ""; ValueData: "KrotkiWspornikST.Projekt"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\KrotkiWspornikST.Projekt"; ValueType: string; ValueName: ""; ValueData: "Projekt KRÓTKI WSPORNIK ST"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\KrotkiWspornikST.Projekt\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\KrotkiWspornikST.Projekt\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
