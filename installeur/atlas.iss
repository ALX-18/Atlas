; Sprint Installeur — l'installeur d'Atlas (Inno Setup). Construit par installeur/construire.py :
;   ISCC /DPaquet=<build\installeur\paquet> /O<build\installeur> installeur\atlas.iss
; Installation pour la personne seule (PrivilegesRequired=lowest) : aucun droit administrateur pour Atlas.
; Avant de copier quoi que ce soit : le diagnostic de la machine (precheck_atlas.ps1), qui choisit le modèle.
; Après la copie : installeur\etapes.py (dépendances, Ollama, Tesseract, modèles, test de capacité).

#ifndef Paquet
  #error "Paquet non défini : lancer installeur/construire.py"
#endif
#ifndef Version
  #define Version "1.0.0"
#endif
#include Paquet + "\tailles.iss"

[Setup]
AppId={{6F2B9C41-3D7A-4E8B-9A15-2C0D7E4B8A63}
AppName=Atlas
AppVersion={#Version}
AppPublisher=Projet Atlas
DefaultDirName={autopf}\Atlas
DisableProgramGroupPage=yes
DisableDirPage=auto
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputBaseFilename=AtlasSetup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
UninstallDisplayName=Atlas
UninstallDisplayIcon={app}\python\pythonw.exe
CloseApplications=no

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "bureau"; Description: "Mettre un raccourci Atlas sur le Bureau"
Name: "demarrage"; Description: "Démarrer Atlas avec Windows (vous pourrez le changer plus tard)"; Flags: unchecked

[Files]
Source: "{#Paquet}\atlas\scripts\precheck_atlas.ps1"; Flags: dontcopy
Source: "{#Paquet}\atlas\*"; DestDir: "{app}"; Excludes: "\config\settings.json"; Flags: recursesubdirs ignoreversion
; Les réglages : jamais écrasés par une réinstallation (le choix du modèle, les mails, la voix restent)
Source: "{#Paquet}\atlas\config\settings.json"; DestDir: "{app}\config"; Flags: onlyifdoesntexist
Source: "{#Paquet}\python\*"; DestDir: "{app}\python"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Atlas"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\installeur\lancer.py"""; WorkingDir: "{app}"; Comment: "Atlas, l'assistant de bureau"
Name: "{autodesktop}\Atlas"; Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\installeur\lancer.py"""; WorkingDir: "{app}"; Tasks: bureau

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Atlas"; ValueData: """{app}\python\pythonw.exe"" ""{app}\installeur\lancer.py"" --sans-fenetre"; Tasks: demarrage; Flags: uninsdeletevalue

[Run]
Filename: "{app}\python\pythonw.exe"; Parameters: """{app}\installeur\premier_lancement.py"""; WorkingDir: "{app}"; Description: "Lancer Atlas maintenant"; Flags: postinstall nowait skipifsilent; Check: EtapesReussies

[UninstallDelete]
Type: filesandordirs; Name: "{app}\python"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\installeur"

[Code]
var
  Verdict, Modele, Sur: String;
  Provisoire: Boolean;
  Attentions, Refus: String;
  Etapes: Integer;
  GarderDonnees: Boolean;

function Valeur(const Ligne, Cle: String): String;
begin
  Result := '';
  if Pos(Cle + '=', Ligne) = 1 then
    Result := Copy(Ligne, Length(Cle) + 2, Length(Ligne));
end;

{ Le diagnostic de la machine : precheck_atlas.ps1, en lecture seule, avant toute copie. }
function Diagnostiquer(): Boolean;
var
  Code, I: Integer;
  Lignes: TArrayOfString;
  Fichier: String;
begin
  Result := False;
  ExtractTemporaryFile('precheck_atlas.ps1');
  Fichier := ExpandConstant('{tmp}\precheck.txt');
  if not Exec('powershell.exe', '-NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\precheck_atlas.ps1') +
              '" -Sortie "' + Fichier + '"', '', SW_HIDE, ewWaitUntilTerminated, Code) then
    Exit;
  if not LoadStringsFromFile(Fichier, Lignes) then
    Exit;
  Attentions := ''; Refus := '';
  for I := 0 to GetArrayLength(Lignes) - 1 do
  begin
    if Valeur(Lignes[I], 'verdict') <> '' then Verdict := Valeur(Lignes[I], 'verdict');
    if Pos('modele=', Lignes[I]) = 1 then Modele := Valeur(Lignes[I], 'modele');
    if Pos('sur=', Lignes[I]) = 1 then Sur := Valeur(Lignes[I], 'sur');
    if Valeur(Lignes[I], 'provisoire') = '1' then Provisoire := True;
    if Valeur(Lignes[I], 'attention') <> '' then Attentions := Attentions + '  - ' + Valeur(Lignes[I], 'attention') + #13#10;
    if Valeur(Lignes[I], 'ko') <> '' then Refus := Refus + '  - ' + Valeur(Lignes[I], 'ko') + #13#10;
  end;
  Result := Verdict <> '';
end;

function InitializeSetup(): Boolean;
begin
  Result := False;
  if not Diagnostiquer() then
  begin
    SuppressibleMsgBox('Le diagnostic de cet ordinateur n''a pas pu se faire : l''installation s''arrête, rien n''a été ' +
                       'installé.', mbCriticalError, MB_OK, IDOK);
    Exit;
  end;
  if (Verdict = 'ko') or (Modele = '') then
  begin
    SuppressibleMsgBox('Cette machine ne convient pas à Atlas :' + #13#10#13#10 + Refus + #13#10 +
                       'L''installation s''arrête : rien n''a été installé.', mbCriticalError, MB_OK, IDOK);
    Exit;
  end;
  Result := True;
end;

{ Les tailles sont en Mo entiers (tailles.iss) : pas de nombres à virgule, qui dépendent de la langue de Windows. }
function TailleMo(): Integer;
begin
  Result := {#TailleBaseMo};
  if Sur = 'carte' then Result := Result + {#TailleNvidiaMo};
  if Modele = 'qwen2.5:7b' then Result := Result + {#TailleQwenMo} else Result := Result + {#TailleGemmaMo};
end;

function TailleTotale(): String;
begin
  Result := IntToStr(TailleMo() div 1000) + ',' + IntToStr((TailleMo() mod 1000) div 100);
end;

function MinutesA50Mbits(): Integer;
begin
  { 50 Mbit/s = 6,25 Mo/s, soit 375 Mo par minute ; plus environ 5 minutes d'installation et de test }
  Result := TailleMo() div 375 + 5;
end;

procedure InitializeWizard();
var
  Page: TOutputMsgMemoWizardPage;
  Texte, Pr: String;
begin
  if Provisoire then Pr := ' (provisoire : un modèle plus léger, mesuré pendant l''installation)' else Pr := '';
  Texte := 'Modèle de langue choisi pour cet ordinateur : ' + Modele + Pr + #13#10;
  if Sur = 'processeur' then Texte := Texte + 'Il tournera sur le processeur : les réponses seront lentes.' + #13#10;
  Texte := Texte + #13#10 + 'Téléchargement total : environ ' + TailleTotale() + ' Go, soit environ ' +
           IntToStr(MinutesA50Mbits()) + ' minutes avec une connexion de 50 Mbit/s.' + #13#10 +
           'Gardez l''ordinateur allumé et branché à internet pendant l''installation.' + #13#10#13#10 +
           'Ce qui est installé : Atlas et son propre Python (aucun autre Python n''est touché), Ollama (le moteur ' +
           'du modèle de langue), Tesseract (pour lire le texte à l''écran), et les modèles de la voix et de la mémoire. ' +
           'Tout vient des sites officiels et chaque fichier est vérifié.' + #13#10#13#10 +
           'Atlas s''installe pour vous seul, sans droits d''administrateur. Windows peut toutefois demander une ' +
           'autorisation pour Tesseract.' + #13#10;
  if Attentions <> '' then Texte := Texte + #13#10 + 'À savoir sur cet ordinateur :' + #13#10 + Attentions;
  Page := CreateOutputMsgMemoPage(wpWelcome, 'Ce qui va être installé', 'Le diagnostic de cet ordinateur est fait.',
                                  'Lisez ceci, puis cliquez sur Suivant.', Texte);
end;

function EtapesReussies(): Boolean;
begin
  Result := Etapes = 0;
end;

{ Une étape ratée : l'installeur ne répond pas « réussi » (0), même en mode silencieux.
  10, hors des codes 1 à 8 propres à Inno Setup. }
function GetCustomSetupExitCode(): Integer;
begin
  Result := 0;
  if Etapes <> 0 then
    Result := 10;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  Params: String;
begin
  if CurStep = ssPostInstall then
  begin
    { Démarrage avec Windows décoché : retirer une entrée laissée par une installation précédente }
    if not WizardIsTaskSelected('demarrage') then
      RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'Atlas');
    Params := '"' + ExpandConstant('{app}\installeur\etapes.py') + '" --palier ' + Modele + ' --sur ' + Sur;
    if Provisoire then Params := Params + ' --provisoire';
    if WizardSilent then Params := Params + ' --sans-fenetre';
    WizardForm.StatusLabel.Caption := 'Téléchargement et installation des composants d''Atlas…';
    if not Exec(ExpandConstant('{app}\python\pythonw.exe'), Params, ExpandConstant('{app}'), SW_SHOW,
                ewWaitUntilTerminated, Etapes) then
      Etapes := -1;
    if Etapes <> 0 then
      SuppressibleMsgBox('L''installation d''Atlas n''est pas terminée (le détail est dans la fenêtre précédente et ' +
                         'dans ' + ExpandConstant('{app}\installeur\installation.log') + ').' + #13#10#13#10 +
                         'Relancez cet installeur : il reprendra où il s''est arrêté, sans tout retélécharger.',
                         mbError, MB_OK, IDOK);
  end;
end;

{ La désinstallation : arrêter Atlas, retirer ses secrets, demander pour la mémoire. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Code: Integer;
  Py, Script, Rapport, Params: String;
  Lignes: TArrayOfString;
  I: Integer;
  Dit: String;
begin
  if CurUninstallStep = usUninstall then
  begin
    Py := ExpandConstant('{app}\python\python.exe');
    Script := '"' + ExpandConstant('{app}\installeur\desinstaller.py') + '"';
    Rapport := ExpandConstant('{tmp}\desinstallation.txt');
    { /MEMOIRE=effacer (désinstallation silencieuse des essais dans Windows Sandbox) : la réponse « Non », sans question }
    if ExpandConstant('{param:MEMOIRE|demander}') = 'effacer' then
      GarderDonnees := False
    else
      GarderDonnees := SuppressibleMsgBox('Garder ta mémoire, ce qu''Atlas a appris et tes rappels ?' + #13#10#13#10 +
                                          'Oui : ils restent sur cet ordinateur, et une future installation d''Atlas ' +
                                          'les retrouvera. Non : ils sont effacés.', mbConfirmation,
                                          MB_YESNO or MB_DEFBUTTON1, IDYES) = IDYES;
    Params := Script + ' --arreter --secrets --rapport "' + Rapport + '"';
    if not GarderDonnees then
    begin
      if SuppressibleMsgBox('Faire d''abord une sauvegarde de ta mémoire (dans Documents\Atlas sauvegarde) ?',
                            mbConfirmation, MB_YESNO or MB_DEFBUTTON1, IDYES) = IDYES then
        Params := Params + ' --sauvegarder "' + ExpandConstant('{userdocs}\Atlas sauvegarde') + '"';
      Params := Params + ' --effacer-donnees';
    end;
    if FileExists(Py) then
      Exec(Py, Params, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, Code);
    Dit := '';
    if LoadStringsFromFile(Rapport, Lignes) then
      for I := 0 to GetArrayLength(Lignes) - 1 do
        Dit := Dit + Lignes[I] + #13#10;
    SuppressibleMsgBox(Dit + #13#10 + 'Ollama et Tesseract restent installés : ils peuvent servir à d''autres ' +
                       'programmes. Vous pouvez les retirer vous-même depuis Paramètres > Applications.',
                       mbInformation, MB_OK, IDOK);
  end;
  if CurUninstallStep = usPostUninstall then
  begin
    { Ce qu'Atlas a créé en marchant (caches Python…) ; data\ reste si on la garde }
    DelTree(ExpandConstant('{app}\config'), True, True, True);
    DelTree(ExpandConstant('{app}\api'), True, True, True);
    DelTree(ExpandConstant('{app}\core'), True, True, True);
    DelTree(ExpandConstant('{app}\core_conversational'), True, True, True);
    DelTree(ExpandConstant('{app}\tools'), True, True, True);
    DelTree(ExpandConstant('{app}\ui'), True, True, True);
    DelTree(ExpandConstant('{app}\desktop'), True, True, True);
    DelTree(ExpandConstant('{app}\scripts'), True, True, True);
    DelTree(ExpandConstant('{app}\tests'), True, True, True);
    DelTree(ExpandConstant('{app}\__pycache__'), True, True, True);
    if not GarderDonnees then
      DelTree(ExpandConstant('{app}'), True, True, True);
  end;
end;
