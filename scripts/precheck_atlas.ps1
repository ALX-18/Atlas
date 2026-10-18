# precheck_atlas.ps1 — Atlas peut-il tourner sur ce PC ?
# Lecture seule : ce script n'installe rien, ne modifie rien, n'envoie rien sur internet.
# Mêmes seuils que scripts/doctor.py --precheck (sprints Performance et Sans Docker).
# Lancement : double-clic sur precheck_atlas.bat (à côté de ce fichier).

$ErrorActionPreference = "SilentlyContinue"

$RAM_COMFORT_GIB  = 15.0   # 16 Go (Windows en affiche ~15,8)
$RAM_MIN_GIB      = 11.0   # 12 Go : juste
$VRAM_COMFORT_MIB = 7500   # carte 8 Go
$VRAM_TIGHT_MIB   = 5500   # carte 6 Go : juste
$DISK_MIN_GIB     = 20.0   # ~14 Go installés + installeurs et caches

$ok = @(); $warn = @(); $ko = @()

Write-Host ""
Write-Host "=== Atlas - pre-verification de ce PC ===" -ForegroundColor Cyan
Write-Host ""

# --- Windows ---
$os = Get-CimInstance Win32_OperatingSystem
$build = [int]$os.BuildNumber
$is64 = [Environment]::Is64BitOperatingSystem
$winName = if ($build -ge 22000) { "Windows 11" } elseif ($build -ge 10240) { "Windows 10" } else { "Windows ancien" }
Write-Host ("Systeme   : {0} (build {1}), {2}" -f $winName, $build, $(if ($is64) { "64 bits" } else { "32 bits" }))
if ($is64 -and $build -ge 10240) { $ok += "Windows 10/11 64 bits" }
else { $ko += "Atlas demande Windows 10 ou 11 en 64 bits" }

# --- Processeur ---
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
Write-Host ("Processeur: {0} ({1} coeurs, {2} threads)" -f $cpu.Name.Trim(), $cpu.NumberOfCores, $cpu.NumberOfLogicalProcessors)

# --- RAM ---
$ramGib = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)
Write-Host ("Memoire   : {0} Go" -f $ramGib)
if ($ramGib -ge $RAM_COMFORT_GIB) { $ok += "RAM suffisante ($ramGib Go)" }
elseif ($ramGib -ge $RAM_MIN_GIB) { $warn += "RAM juste ($ramGib Go) : fermer les applications lourdes pendant l'usage d'Atlas" }
else { $ko += "RAM insuffisante ($ramGib Go, 12 Go minimum)" }

# --- Carte graphique ---
$gpus = Get-CimInstance Win32_VideoController
foreach ($g in $gpus) { Write-Host ("Carte     : {0} (pilote {1})" -f $g.Name, $g.DriverVersion) }
$smi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if (-not $smi) {
    $cand = "$env:SystemRoot\System32\nvidia-smi.exe"
    if (Test-Path $cand) { $smi = Get-Item $cand }
}
$hasNvidiaName = ($gpus | Where-Object { $_.Name -match "NVIDIA" }) -ne $null
if ($smi) {
    $line = & $smi.Source --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    if ($line) {
        $parts = $line -split ",\s*"
        $vram = [int]$parts[1]
        Write-Host ("NVIDIA    : {0}, {1} Mo de memoire video, pilote {2}" -f $parts[0], $vram, $parts[2])
        if ($vram -ge $VRAM_COMFORT_MIB) { $ok += "Carte NVIDIA suffisante ($vram Mo)" }
        elseif ($vram -ge $VRAM_TIGHT_MIB) { $warn += "Carte NVIDIA juste ($vram Mo) : eviter de jouer pendant l'usage d'Atlas" }
        else { $warn += "Carte NVIDIA trop petite ($vram Mo) : le modele de langue debordera sur le processeur, reponses lentes" }
    } else {
        $warn += "nvidia-smi present mais muet : pilote NVIDIA a verifier"
    }
} elseif ($hasNvidiaName) {
    $warn += "Carte NVIDIA vue, mais pilote NVIDIA introuvable : installer le pilote a jour"
} else {
    $warn += "Pas de carte NVIDIA : Atlas tournera, mais lentement (transcription ~5 s par phrase, reponses plus lentes)"
}

# --- Disque ---
$sys = Get-PSDrive -Name ($env:SystemDrive.TrimEnd(':'))
$freeGib = [math]::Round($sys.Free / 1GB, 1)
Write-Host ("Disque {0}  : {1} Go libres" -f $env:SystemDrive, $freeGib)
if ($freeGib -ge $DISK_MIN_GIB) { $ok += "Place libre suffisante ($freeGib Go)" }
else { $ko += "Place libre insuffisante ($freeGib Go, 20 Go minimum)" }

# --- Informations utiles (ne changent pas le verdict) ---
$py = Get-Command py -ErrorAction SilentlyContinue
$ol = Get-Command ollama -ErrorAction SilentlyContinue
Write-Host ("Python    : {0}" -f $(if ($py) { "lanceur py present" } else { "absent (l'installation s'en chargera)" }))
Write-Host ("Ollama    : {0}" -f $(if ($ol) { "deja installe" } else { "absent (l'installation s'en chargera)" }))
# Competences 1 : le Bluetooth (Atlas sait l'allumer et l'eteindre). Sans lui, Atlas le dit ; le verdict n'en depend pas.
$bt = @(Get-PnpDevice -Class Bluetooth -PresentOnly -ErrorAction SilentlyContinue | Where-Object { $_.Status -eq "OK" })
Write-Host ("Bluetooth : {0}" -f $(if ($bt.Count -gt 0) { "present" } else { "absent ou desactive (Atlas le dira ; sans effet sur le verdict)" }))

# --- Verdict ---
Write-Host ""
if ($ko.Count -gt 0) {
    Write-Host "VERDICT : Atlas ne tournera pas correctement" -ForegroundColor Red
} elseif ($warn.Count -gt 0) {
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
