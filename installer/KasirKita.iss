; KasirKita Windows installer (Inno Setup 6)
; Least-privilege installer: installs only for the current Windows user.
#define MyAppName "KasirKita"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Choco Anak Baik"
#define MyAppExeName "KasirKita.exe"

[Setup]
AppId={{C8F21E54-8A0C-4B14-A0D4-3F74B5E3A9D1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\KasirKita
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupLogging=yes
CloseApplications=yes
RestartApplications=no
OutputDir=..\
OutputBaseFilename=KasirKita-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat ikon di Desktop"; GroupDescription: "Pintasan tambahan:"; Flags: unchecked

[Files]
Source: "..\package\KasirKita\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\package\README.md"; DestDir: "{app}\Dokumentasi"; Flags: ignoreversion
Source: "..\package\PANDUAN_PENGGUNA.md"; DestDir: "{app}\Dokumentasi"; Flags: ignoreversion
Source: "..\package\PETUNJUK.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

; The installer does not auto-launch the application after installation.
; Users can start it from the Start Menu or optional Desktop shortcut.
