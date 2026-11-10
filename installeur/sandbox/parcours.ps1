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
# Attendre un installeur, et lui seul. `Start-Process -Wait` (PowerShell 5.1) attend aussi les programmes qu'il
# lance : Ollama, démarré par son installeur, ne s'arrête jamais, et le parcours restait bloqué (Sandbox, 09-10/11).
function Lancer($exe, $arguments) {
    $p = Start-Process -FilePath $exe -ArgumentList $arguments -PassThru
    $null = $p.Handle
    $p.WaitForExit()
    # la désinstallation d'Inno Setup se relance depuis un dossier temporaire (_iu*.tmp) : l'attendre aussi
    for ($i = 0; $i -lt 300; $i++) {
        if (-not (Get-Process | Where-Object { $_.Name -like "_iu*" -or $_.Name -like "AtlasSetup*" })) { break }
        Start-Sleep 2
    }
    return $p.ExitCode
}
function Installer($etiquette) {
    $t0 = Get-Date
    $code = Lancer $Setup @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=$R\setup_$etiquette.log")
    Noter "installation_$etiquette" @{ code = $code; minutes = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1) }
    if (Test-Path "$App\installeur\etat.json") { Copy-Item "$App\installeur\etat.json" "$R\etat_$etiquette.json" -Force }
    if (Test-Path "$App\installeur\installation.log") { Copy-Item "$App\installeur\installation.log" "$R\installation_$etiquette.log" -Force }
    return $code
}
function Demarrer() {
    # sans attendre : lancer.py démarre Atlas, qui reste ouvert
    Start-Process -FilePath "$App\python\pythonw.exe" -ArgumentList "`"$App\installeur\lancer.py`"", "--sans-fenetre"
    for ($i = 0; $i -lt 120; $i++) { try { Invoke-RestMethod "http://127.0.0.1:8550/api/health" -TimeoutSec 3 | Out-Null; return $true } catch { Start-Sleep 2 } }
    return $false
}
function Arreter() {
    Get-Process python, pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "$App*" } | Stop-Process -Force
    Start-Sleep 3
}

# Les journaux copiés toutes les 30 s : un parcours bloqué se lit depuis le PC, sans ouvrir la Sandbox
Start-Job -ArgumentList $App, $R -ScriptBlock {
    param($App, $R)
    while ($true) {
        if (Test-Path "$App\installeur\installation.log") { Copy-Item "$App\installeur\installation.log" "$R\en_cours.log" -Force -ErrorAction SilentlyContinue }
        if (Test-Path "$env:LOCALAPPDATA\Ollama\server.log") { Copy-Item "$env:LOCALAPPDATA\Ollama\server.log" "$R\ollama_server.log" -Force -ErrorAction SilentlyContinue }
        $ecoute = @(Get-NetTCPConnection -LocalPort 11434 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $_.LocalAddress }) -join ","
        "$(Get-Date -Format s) port 11434 : [$ecoute]" | Add-Content "$R\ollama_port.txt"
        Get-Process | Where-Object { $_.Path -and $_.Path -notlike "C:\Windows\*" } | Select-Object Name, Path, StartTime |
            Out-File "$R\processus.txt" -Encoding utf8 -Width 300
        Start-Sleep 30
    }
} | Out-Null

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
$t0 = Get-Date
if (Demarrer) {
    Noter "demarrage_atlas_s" ([math]::Round(((Get-Date) - $t0).TotalSeconds))
    $t1 = Get-Date; Noter "reponse_heure" (Chat "quelle heure est-il ?"); Noter "reponse_heure_s" ([math]::Round(((Get-Date) - $t1).TotalSeconds))
    Noter "retiens" (Chat "retiens que ma couleur préférée est le vert sapin")
    $t1 = Get-Date; Noter "question_libre" (Chat "explique-moi en une phrase ce qu'est la photosynthèse"); Noter "question_libre_s" ([math]::Round(((Get-Date) - $t1).TotalSeconds))
} else { Noter "demarrage_atlas" "ECHEC" }
cmdkey /generic:"Atlas:essai_sandbox" /user:"essai" /pass:"valeur-fictive-de-test" | Out-Null
Arreter

# 3. Réinstallation par-dessus : rien n'est perdu
$code = Installer "reinstallation"
if (Demarrer) { Noter "rappel_apres_reinstallation" (Chat "quelle est ma couleur préférée ?") }
Arreter

# 4. Désinstallation silencieuse (réponse par défaut : garder la mémoire)
$t0 = Get-Date
$codeD = Lancer "$App\unins000.exe" @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LOG=$R\desinstallation_garder.log")
Start-Sleep 5
Noter "desinstallation_garder" @{ code = $codeD; minutes = [math]::Round(((Get-Date) - $t0).TotalMinutes, 1);
    donnees_gardees = (Test-Path "$App\data"); code_retire = -not (Test-Path "$App\core");
    python_retire = -not (Test-Path "$App\python"); raccourci_retire = -not (Test-Path "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Atlas.lnk");
    secret_retire = -not ((cmdkey /list) -match "Atlas:essai_sandbox");
    ollama_garde = (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") }

# 5. Réinstallation (la mémoire gardée revient), puis désinstallation « effacer »
$code = Installer "retour"
if (Demarrer) { Noter "rappel_apres_retour" (Chat "quelle est ma couleur préférée ?") }
Arreter
$codeD = Lancer "$App\unins000.exe" @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/MEMOIRE=effacer", "/LOG=$R\desinstallation_effacer.log")
Start-Sleep 5
Noter "desinstallation_effacer" @{ code = $codeD; dossier_retire = -not (Test-Path $App);
    ollama_garde = (Test-Path "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe") }
Noter "fin" (Get-Date).ToString("s")
