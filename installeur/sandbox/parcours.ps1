# Sprint Installeur / IN6 — le parcours complet dans Windows Sandbox (une machine vierge, sans carte NVIDIA).
# Lancé au démarrage de la Sandbox par atlas_sandbox.wsb. Rien ne touche le PC d'Alexis : la Sandbox est jetée
# à la fermeture. Résultats dans C:\resultats (dossier partagé, le seul en écriture).
#   installation silencieuse → Atlas répond → réinstallation par-dessus (rien n'est perdu) → désinstallation
#   (la mémoire gardée, les secrets d'Atlas retirés, Ollama laissé) → réinstallation → désinstallation « effacer ».
param([string]$Mode = "complet")

$ErrorActionPreference = "Continue"
$R = "C:\resultats"
$Setup = "C:\atlas_build\AtlasSetup.exe"
$App = "$env:LOCALAPPDATA\Programs\Atlas"
$bilan = [ordered]@{ mode = $Mode; debut = (Get-Date).ToString("s") }
function Noter($cle, $valeur) { $bilan[$cle] = $valeur; $bilan | ConvertTo-Json -Depth 6 | Set-Content "$R\bilan.json" -Encoding UTF8 }
function Chat($phrase) {
    try {
        $corps = @{ message = $phrase; history = @(); origine = "fenetre" } | ConvertTo-Json
        $r = Invoke-RestMethod -Uri "http://127.0.0.1:8550/api/chat" -Method Post -Body ([Text.Encoding]::UTF8.GetBytes($corps)) -ContentType "application/json; charset=utf-8" -TimeoutSec 900
        return $r.message
    } catch { return "ERREUR: $($_.Exception.Message)" }
}
function Installer($etiquette) {
    $t0 = Get-Date
    $p = Start-Process -FilePath $Setup -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=$R\setup_$etiquette.log" -Wait -PassThru
    Noter "installation_$etiquette" @{ code = $p.ExitCode; minutes = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1) }
    if (Test-Path "$App\installeur\etat.json") { Copy-Item "$App\installeur\etat.json" "$R\etat_$etiquette.json" -Force }
    if (Test-Path "$App\installeur\installation.log") { Copy-Item "$App\installeur\installation.log" "$R\installation_$etiquette.log" -Force }
    return $p.ExitCode
}
function Demarrer() {
    Start-Process -FilePath "$App\python\pythonw.exe" -ArgumentList "`"$App\installeur\lancer.py`"", "--sans-fenetre" -Wait
    for ($i = 0; $i -lt 120; $i++) { try { Invoke-RestMethod "http://127.0.0.1:8550/api/health" -TimeoutSec 3 | Out-Null; return $true } catch { Start-Sleep 2 } }
    return $false
}
function Arreter() {
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$App*" } | Stop-Process -Force
    Start-Sleep 3
}

$bilan["machine"] = @{ ram_go = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1);
                       cartes = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name }) }
Noter "etape" "debut"

# 1. Installation silencieuse
$code = Installer "premiere"
if ($Mode -eq "ne_convient_pas") {
    Noter "app_presente" (Test-Path $App)
    Noter "fin" (Get-Date).ToString("s")
    exit 0
}
if ($code -ne 0) {
    # Une étape a échoué (code 10) : la suite n'aurait pas de sens ; le détail est dans installation_premiere.log
    Noter "arret" "installation inachevée (code $code)"
    Noter "fin" (Get-Date).ToString("s")
    exit 1
}
Noter "raccourci_menu" (Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Atlas.lnk")
Noter "raccourci_bureau" (Test-Path "$env:USERPROFILE\Desktop\Atlas.lnk")
Noter "demarrage_windows" ((Get-ItemProperty "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue).Atlas -ne $null)
Noter "entree_applications" ((Get-ChildItem "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" | Where-Object { (Get-ItemProperty $_.PSPath).DisplayName -eq "Atlas" }) -ne $null)
Noter "ollama_ecoute" @(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $_.LocalAddress })
Noter "reglages" (Get-Content "$App\config\settings.json" -Raw | ConvertFrom-Json | Select-Object @{n="modele";e={$_.ollama.model}}, @{n="envoi";e={$_.mail.envoi}})

# 2. Atlas répond, retient, et le coffre reçoit un secret de test (une valeur fictive de la Sandbox)
if (Demarrer) {
    Noter "reponse_heure" (Chat "quelle heure est-il ?")
    Noter "retiens" (Chat "retiens que ma couleur préférée est le vert sapin")
    Noter "question_libre" (Chat "explique-moi en une phrase ce qu'est la photosynthèse")
} else { Noter "demarrage_atlas" "ECHEC" }
cmdkey /generic:"Atlas:essai_sandbox" /user:"essai" /pass:"valeur-fictive-de-test" | Out-Null
Arreter

# 3. Réinstallation par-dessus : rien n'est perdu
$code = Installer "reinstallation"
if (Demarrer) { Noter "rappel_apres_reinstallation" (Chat "quelle est ma couleur préférée ?") }
Arreter

# 4. Désinstallation silencieuse (réponse par défaut : garder la mémoire)
$t0 = Get-Date
$p = Start-Process -FilePath "$App\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=$R\desinstallation_garder.log" -Wait -PassThru
Start-Sleep 5
Noter "desinstallation_garder" @{ code = $p.ExitCode; minutes = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1);
    donnees_gardees = (Test-Path "$App\data"); code_retire = -not (Test-Path "$App\core");
    python_retire = -not (Test-Path "$App\python"); raccourci_retire = -not (Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Atlas.lnk");
    secret_retire = -not ((cmdkey /list) -match "Atlas:essai_sandbox");
    ollama_garde = (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") }

# 5. Réinstallation (la mémoire gardée revient), puis désinstallation « effacer »
$code = Installer "retour"
if (Demarrer) { Noter "rappel_apres_retour" (Chat "quelle est ma couleur préférée ?") }
Arreter
$p = Start-Process -FilePath "$App\unins000.exe" -ArgumentList "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/MEMOIRE=effacer", "/LOG=$R\desinstallation_effacer.log" -Wait -PassThru
Start-Sleep 5
Noter "desinstallation_effacer" @{ code = $p.ExitCode; dossier_retire = -not (Test-Path $App) }
Noter "fin" (Get-Date).ToString("s")
