; KasirKita Windows installer (Inno Setup 6)
; Build from the repository root after creating package/KasirKita.
#define MyAppName "KasirKita"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "The Choco Corporation"
#define MyAppExeName "KasirKita.exe"

[Setup]
AppId={{C8F21E54-8A0C-4B14-A0D4-3F74B5E3A9D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\KasirKita
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\
OutputBaseFilename=KasirKita-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "indonesian"; MessagesFile: "compiler:Languages\Indonesian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat ikon di Desktop"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked

[Files]
Source: "..\package\KasirKita\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\package\README.md"; DestDir: "{app}\Dokumentasi"; Flags: ignoreversion
Source: "..\package\PANDUAN_PENGGUNA.md"; DestDir: "{app}\Dokumentasi"; Flags: ignoreversion
Source: "..\package\PETUNJUK.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan KasirKita"; Flags: postinstall nowait skipifsilent
