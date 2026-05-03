[Setup]
; App Information
AppId={{5F3A5D6A-72A2-4F74-983E-B2A88A3D9D42}
AppName=ND-Hub
AppVersion=0.42
AppPublisher=Dein Unternehmen
DefaultDirName={autopf}\ND-Hub
DefaultGroupName=ND-Hub
OutputDir=.\Installer
OutputBaseFilename=ND-Hub_V042_Setup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64

; Setup Icon (Optional, same as App)
; SetupIconFile=icon.ico
UninstallDisplayIcon={app}\ND-Hub.exe

[Tasks]
Name: "desktopicon"; Description: "Ein Desktop-Symbol erstellen"; GroupDescription: "Zusätzliche Symbole:"

[Files]
; IMPORTANT: Run build_windows_exe.py first so the dist/ND-Hub/ folder is populated
Source: "dist\ND-Hub\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ND-Hub"; Filename: "{app}\ND-Hub.exe"; IconFilename: "{app}\icon.ico"
Name: "{commondesktop}\ND-Hub"; Filename: "{app}\ND-Hub.exe"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Code]
var
  IsUpgrade: Boolean;
  DbOptionsPage: TInputOptionWizardPage;
  DbFilePage: TInputFileWizardPage;

function DetectUpgrade(): Boolean;
var
  UninstallKey: String;
begin
  UninstallKey := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + ExpandConstant('{#SetupSetting("AppId")}') + '_is1';
  Result := RegKeyExists(HKLM, UninstallKey) or RegKeyExists(HKCU, UninstallKey);
end;

procedure InitializeWizard;
begin
  IsUpgrade := DetectUpgrade();

  if IsUpgrade then
  begin
    SuppressibleMsgBox(
      'Bestehende ND-Hub-Installation erkannt.' + #13#10#13#10 +
      'Update-Modus ist aktiv: Programmdateien werden aktualisiert,' + #13#10 +
      'bestehende Daten und Datenbank-Konfiguration bleiben erhalten.',
      mbInformation,
      MB_OK,
      IDOK
    );
    Exit;
  end;

  // Page 1: Select Database Strategy (New vs Existing)
  DbOptionsPage := CreateInputOptionPage(wpSelectDir,
    'Datenbank Konfiguration', 'Wo soll die Datenbank gespeichert werden?',
    'Bitte wähle, ob du eine neue lokale Datenbank anlegen oder eine bestehende (z.B. auf einem Netzlaufwerk) verbinden möchtest.',
    True, False);
  
  DbOptionsPage.Add('Neue lokale Datenbank im Installationsordner anlegen (Standard)');
  DbOptionsPage.Add('Bestehende Datenbank verknüpfen (Netzlaufwerk / Freigabe-Ordner)');
  
  DbOptionsPage.SelectedValueIndex := 0;

  // Page 2: Select Existing Database File
  DbFilePage := CreateInputFilePage(DbOptionsPage.ID,
    'Datenbank auswählen', 'Speicherort der bestehenden Datenbank',
    'Wähle die bestehende nd_hub.db Datei aus.');
  
  DbFilePage.Add('Pfad zur bestehenden Datenbank (.db):',
    'Datenbank Dateien|*.db|Alle Dateien|*.*', '.db');
end;

// Skip the file selection page if "New local database" is selected
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;

  if IsUpgrade then
  begin
    if Assigned(DbOptionsPage) and (PageID = DbOptionsPage.ID) then
      Result := True;
    if Assigned(DbFilePage) and (PageID = DbFilePage.ID) then
      Result := True;
    Exit;
  end;

  if Assigned(DbFilePage) and Assigned(DbOptionsPage) and (PageID = DbFilePage.ID) and (DbOptionsPage.SelectedValueIndex = 0) then
    Result := True;
end;

// Validation for DbFilePage
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if IsUpgrade then
    Exit;

  if not Assigned(DbFilePage) then
    Exit;

  if CurPageID = DbFilePage.ID then
  begin
    if DbFilePage.Values[0] = '' then
    begin
      MsgBox('Bitte wähle eine bestehende Datenbank aus oder gehe zurück und wähle die lokale Variante.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ConfigPath: String;
  SelectedDbPath: String;
  FileLines: TArrayOfString;
begin
  if CurStep = ssPostInstall then
  begin
    ConfigPath := ExpandConstant('{app}\config.ini');

    // Keep existing config/database path on upgrades.
    if IsUpgrade and FileExists(ConfigPath) then
      Exit;

    SetArrayLength(FileLines, 3);
    FileLines[0] := '[Database]';
    
    if not Assigned(DbOptionsPage) or (DbOptionsPage.SelectedValueIndex = 0) then
    begin
      // Local Database default
      FileLines[1] := 'Path=nd_hub.db';
    end
    else
    begin
      // Existing Custom Database
      SelectedDbPath := DbFilePage.Values[0];
      FileLines[1] := 'Path=' + SelectedDbPath;
    end;
    
    FileLines[2] := '';
    SaveStringsToFile(ConfigPath, FileLines, False);
  end;
end;

[Run]
Filename: "{app}\ND-Hub.exe"; Description: "ND-Hub jetzt starten"; Flags: nowait postinstall skipifsilent
