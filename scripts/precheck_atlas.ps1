# precheck_atlas.ps1 — Atlas peut-il tourner sur ce PC ?
# Lecture seule : ce script n'installe rien, ne modifie rien, n'envoie rien sur internet.
# Mêmes seuils et mêmes paliers que scripts/doctor.py --precheck (sprints Performance, Sans Docker, Installeur).
# Lancement : double-clic sur precheck_atlas.bat (à côté de ce fichier).
#   -Sortie <fichier> : l'installeur d'Atlas y lit le verdict et le palier (clé=valeur, UTF-8) ;
#   -Simuler <json>   : une machine décrite à la main, pour les tests (rien n'est lu sur ce PC).
param([string]$Sortie = "", [string]$Simuler = "")

$ErrorActionPreference = "SilentlyContinue"

$RAM_COMFORT_GIB  = 15.0   # 16 Go (Windows en affiche ~15,8)
$RAM_MIN_GIB      = 11.0   # 12 Go : juste
$VRAM_COMFORT_MIB = 7500   # carte 8 Go
$VRAM_TIGHT_MIB   = 5500   # carte 6 Go : juste
$DISK_MIN_GIB     = 20.0   # ~14 Go installés + installeurs et caches
$MODELE_PALIER_HAUT  = "qwen2.5:7b"
$MODELE_PALIER_MOYEN = "gemma4:e4b"

$ok = @(); $warn = @(); $ko = @()
$muet = ($Sortie -ne "") -or ($Simuler -ne "")
function Dire($texte, $couleur = "Gray") { if (-not $muet) { Write-Host $texte -ForegroundColor $couleur } }

# --- La machine : lue sur ce PC, ou décrite par -Simuler ---
if ($Simuler -ne "") {
    $s = $Simuler | ConvertFrom-Json
    $is64 = [bool]$s.arch64; $build = if ($s.windows) { 22631 } else { 0 }
    $ramGib = [double]$s.ram_gib; $freeGib = [double]$s.disk_free_gib
    $gpuName = $s.gpu_name; $vram = if ($s.vram_mib) { [int]$s.vram_mib } else { 0 }
    $hasNvidiaName = [bool]$gpuName; $smiMuet = $false
} else {
    $os = Get-CimInstance Win32_OperatingSystem
    $build = [int]$os.BuildNumber
    $is64 = [Environment]::Is64BitOperatingSystem
    $ramGib = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
    $sys = Get-PSDrive -Name ($env:SystemDrive.TrimEnd(':'))
    $freeGib = [math]::Round($sys.Free / 1GB, 1)
    $gpus = Get-CimInstance Win32_VideoController
    $hasNvidiaName = ($gpus | Where-Object { $_.Name -match "NVIDIA" }) -ne $null
    $gpuName = $null; $vram = 0; $smiMuet = $false
    $smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $smi) {
        $cand = "$env:SystemRoot\System32\nvidia-smi.exe"
        if (Test-Path $cand) { $smi = Get-Item $cand }
    }
    if ($smi) {
        $line = & $smi.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null | Select-Object -First 1
        if ($line) { $parts = $line -split ",\s*"; $gpuName = $parts[0]; $vram = [int]$parts[1] } else { $smiMuet = $true }
    }
}

Dire ""
Dire "=== Atlas - pre-verification de ce PC ===" Cyan
Dire ""

# --- Windows ---
$winName = if ($build -ge 22000) { "Windows 11" } elseif ($build -ge 10240) { "Windows 10" } else { "Windows ancien" }
Dire ("Systeme   : {0} (build {1}), {2}" -f $winName, $build, $(if ($is64) { "64 bits" } else { "32 bits" }))
if ($is64 -and $build -ge 10240) { $ok += "Windows 10/11 64 bits" }
else { $ko += "Atlas demande Windows 10 ou 11 en 64 bits" }

# --- Processeur ---
if ($Simuler -eq "") {
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    Dire ("Processeur: {0} ({1} coeurs, {2} threads)" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)
}

# --- RAM ---
Dire ("Memoire   : {0} Go" -f $ramGib)
if ($ramGib -ge $RAM_COMFORT_GIB) { $ok += "RAM suffisante ($ramGib Go)" }
elseif ($ramGib -ge $RAM_MIN_GIB) { $warn += "RAM juste ($ramGib Go) : fermer les applications lourdes pendant l'usage d'Atlas" }
else { $ko += "RAM insuffisante ($ramGib Go, 12 Go minimum)" }

# --- Carte graphique ---
if ($Simuler -eq "") { foreach ($g in $gpus) { Dire ("Carte     : {0} (pilote {1})" -f $g.Name, $g.DriverVersion) } }
if ($gpuName) {
    Dire ("NVIDIA    : {0}, {1} Mo de memoire video" -f $gpuName, $vram)
    if ($vram -ge $VRAM_COMFORT_MIB) { $ok += "Carte NVIDIA suffisante ($vram Mo)" }
    elseif ($vram -ge $VRAM_TIGHT_MIB) { $warn += "Carte NVIDIA juste ($vram Mo) : modele plus leger, provisoire ; eviter de jouer pendant l'usage d'Atlas" }
    else { $warn += "Carte NVIDIA trop petite ($vram Mo) : modele plus leger, sur le processeur, reponses lentes" }
} elseif ($smiMuet) {
    $warn += "nvidia-smi present mais muet : pilote NVIDIA a verifier"
} elseif ($hasNvidiaName) {
    $warn += "Carte NVIDIA vue, mais pilote NVIDIA introuvable : installer le pilote a jour"
} else {
    $warn += "Pas de carte NVIDIA : Atlas tournera, mais lentement (transcription ~5 s par phrase, reponses plus lentes)"
}

# --- Disque ---
Dire ("Disque {0}  : {1} Go libres" -f $env:SystemDrive, $freeGib)
if ($freeGib -ge $DISK_MIN_GIB) { $ok += "Place libre suffisante ($freeGib Go)" }
else { $ko += "Place libre insuffisante ($freeGib Go, 20 Go minimum)" }

# --- Le palier (le modèle que l'installeur choisira) : mêmes règles que doctor.palier ---
$modele = ""; $provisoire = $false; $sur = ""
if ($ko.Count -eq 0) {
    if ($gpuName -and $vram -ge $VRAM_COMFORT_MIB) { $modele = $MODELE_PALIER_HAUT; $sur = "carte" }
    elseif ($gpuName -and $vram -ge $VRAM_TIGHT_MIB) { $modele = $MODELE_PALIER_MOYEN; $provisoire = $true; $sur = "carte" }
    elseif ($ramGib -ge $RAM_COMFORT_GIB) { $modele = $MODELE_PALIER_MOYEN; $provisoire = $true; $sur = "processeur" }
    else { $ko += "Cette machine ne convient pas a Atlas : sans carte NVIDIA de 6 Go, il faut au moins 16 Go de memoire vive" }
}

# --- Informations utiles (ne changent pas le verdict) ---
if ($Simuler -eq "") {
    $py = Get-Command py -ErrorAction SilentlyContinue
    $ol = Get-Command ollama -ErrorAction SilentlyContinue
    Dire ("Python    : {0}" -f $(if ($py) { "lanceur py present" } else { "absent (l'installation s'en chargera)" }))
    Dire ("Ollama    : {0}" -f $(if ($ol) { "deja installe" } else { "absent (l'installation s'en chargera)" }))
    # Competences 1 : le Bluetooth (Atlas sait l'allumer et l'eteindre). Sans lui, Atlas le dit ; le verdict n'en depend pas.
    $bt = @(Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "OK" })
    Dire ("Bluetooth : {0}" -f $(if ($bt.Count -gt 0) { "present" } else { "absent ou desactive (Atlas le dira ; sans effet sur le verdict)" }))
}
if ($modele) { Dire ("Modele    : {0}{1}" -f $modele, $(if ($provisoire) { " (provisoire)" } else { "" })) }

# --- Verdict ---
$verdict = if ($ko.Count -gt 0) { "ko" } elseif ($warn.Count -gt 0) { "degrade" } else { "ok" }
if ($Sortie -ne "" -or $Simuler -ne "") {
    $lignes = @("verdict=$verdict", "modele=$modele", "provisoire=$(if ($provisoire) { 1 } else { 0 })", "sur=$sur",
                "ram_gib=$ramGib", "vram_mib=$vram", "disk_free_gib=$freeGib")
    foreach ($m in $ko) { $lignes += "ko=$m" }
    foreach ($m in $warn) { $lignes += "attention=$m" }
    if ($Sortie -ne "") { [IO.File]::WriteAllLines($Sortie, [string[]]$lignes, (New-Object Text.UTF8Encoding($true))) }
    else { $lignes | ForEach-Object { Write-Output $_ } }
    exit $(if ($verdict -eq "ko") { 2 } elseif ($verdict -eq "degrade") { 1 } else { 0 })
}
Write-Host ""
if ($verdict -eq "ko") {
    Write-Host "VERDICT : Atlas ne tournera pas correctement" -ForegroundColor Red
} elseif ($verdict -eq "degrade") {
    Write-Host "VERDICT : Atlas tournera, en mode degrade" -ForegroundColor Yellow
} else {
    Write-Host "VERDICT : Atlas tournera bien" -ForegroundColor Green
}
Write-Host ""
foreach ($m in $ko)   { Write-Host "  [X] $m" -ForegroundColor Red }
foreach ($m in $warn) { Write-Host "  [!] $m" -ForegroundColor Yellow }
foreach ($m in $ok)   { Write-Host "  [OK] $m" -ForegroundColor Green }
Write-Host ""
Write-Host "Ce script n'a rien installe ni modifie." -ForegroundColor DarkGray
