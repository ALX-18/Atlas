# mesure_comptes.ps1 - IF7, etape 0 du parcours sur AtlasTest (brief Installeur - fin, section 6).
# Mesure, depuis un compte Windows, ce qu'il voit de l'Atlas et de l'Ollama d'un AUTRE compte du meme PC :
#   - le proprietaire de ce qui ecoute sur 11434 (Ollama), 8550 (Atlas), 9999 (pont), sans droits d'administrateur ;
#   - si l'API d'Atlas refuse une demande sans la cle (rien n'est lu, rien n'est execute) ;
#   - si le pont refuse une connexion qui ne vient pas de l'extension ;
#   - ce qui se passe quand ce compte veut le meme port (avec et sans SO_REUSEADDR).
# Ne telecharge rien, n'installe rien, ne change aucun reglage. N'ecrit que son rapport. N'envoie aucune phrase.
# Aucun nom de compte ni chemin n'est ecrit dans le rapport : "ce compte", "un autre compte".
# Lancement : clic droit > Executer avec PowerShell, ou mesure_comptes.bat a cote de ce fichier.
param([string]$Sortie = "")

$ErrorActionPreference = "SilentlyContinue"
$lignes = New-Object System.Collections.Generic.List[string]
function Noter($t) { $lignes.Add($t); Write-Host $t }

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
Noter ("mesure : {0}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))
Noter ("droits d'administrateur : {0}" -f $(if ($admin) { "OUI (la mesure doit se faire SANS)" } else { "non" }))
$sessions = (quser 2>$null | Measure-Object -Line).Lines - 1
Noter ("sessions Windows ouvertes (quser) : {0}" -f $(if ($sessions -ge 0) { $sessions } else { "illisible" }))

function Proprietaire([int]$port) {
    $c = Get-NetTCPConnection -State Listen -LocalPort $port |
         Where-Object { $_.LocalAddress -eq "127.0.0.1" -or $_.LocalAddress -eq "0.0.0.0" } | Select-Object -First 1
    if (-not $c) { return "libre" }
    $idp = [int]$c.OwningProcess
    if ($idp -le 0) { return "illisible (numero de processus absent)" }
    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$idp"
    if (-not $proc) { return "illisible (processus introuvable par CIM)" }
    $o = Invoke-CimMethod -InputObject $proc -MethodName GetOwner
    if (-not $o) { return "illisible (GetOwner muet)" }
    if ($o.ReturnValue -ne 0 -or -not $o.User) { return ("illisible (GetOwner code {0})" -f $o.ReturnValue) }
    if ($o.User -ieq $env:USERNAME -and $o.Domain -ieq $env:USERDOMAIN) { return "ce compte" }
    return "un autre compte (nom lu)"
}

Noter ""
Noter "--- 1. A qui appartient ce qui ecoute ---"
foreach ($p in @(@(11434, "Ollama"), @(8550, "Atlas"), @(9999, "pont navigateur"))) {
    Noter ("{0,-16} 127.0.0.1:{1,-5} : {2}" -f $p[1], $p[0], (Proprietaire $p[0]))
}

function Http([string]$methode, [string]$url, [string]$corps = "") {
    try {
        $req = [Net.HttpWebRequest]::Create($url)
        $req.Method = $methode; $req.Timeout = 5000
        if ($corps) {
            $octets = [Text.Encoding]::UTF8.GetBytes($corps)
            $req.ContentType = "application/json"; $req.ContentLength = $octets.Length
            $f = $req.GetRequestStream(); $f.Write($octets, 0, $octets.Length); $f.Close()
        }
        $r = $req.GetResponse(); $code = [int]$r.StatusCode; $r.Close(); return $code
    } catch [Net.WebException] {
        if ($_.Exception.Response) { return [int]$_.Exception.Response.StatusCode }
        return ("pas de reponse ({0})" -f $_.Exception.Status)
    }
}

Noter ""
Noter "--- 2. L'API d'Atlas, SANS la cle (attendu : 401 partout, sauf / qui dit que l'interface web est coupee) ---"
Noter ("GET  /api/health                   : {0}" -f (Http "GET" "http://127.0.0.1:8550/api/health"))
Noter ("GET  /api/memory/recall?q=essai     : {0}" -f (Http "GET" "http://127.0.0.1:8550/api/memory/recall?q=essai"))
Noter ("GET  /api/confirmations            : {0}" -f (Http "GET" "http://127.0.0.1:8550/api/confirmations"))
Noter ("POST /api/confirm (id invente)     : {0}" -f (Http "POST" "http://127.0.0.1:8550/api/confirm" '{"confirmation_id":"mesure-if7","accepted":false}'))
Noter ("GET  /                             : {0}" -f (Http "GET" "http://127.0.0.1:8550/"))
Noter ""
Noter "--- 3. Ollama (logiciel tiers, sans authentification ; seule sa version est demandee) ---"
Noter ("GET  /api/version                  : {0}" -f (Http "GET" "http://127.0.0.1:11434/api/version"))

function Poignee([string]$origine) {
    $t = New-Object Net.Sockets.TcpClient
    try {
        if (-not $t.ConnectAsync("127.0.0.1", 9999).Wait(1000)) { return "rien n'ecoute" }
        $s = $t.GetStream(); $s.ReadTimeout = 3000
        $entete = "GET / HTTP/1.1`r`nHost: 127.0.0.1:9999`r`nUpgrade: websocket`r`nConnection: Upgrade`r`n" +
                  "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==`r`nSec-WebSocket-Version: 13`r`n"
        if ($origine) { $entete += "Origin: $origine`r`n" }
        $o = [Text.Encoding]::ASCII.GetBytes($entete + "`r`n"); $s.Write($o, 0, $o.Length)
        $tampon = New-Object byte[] 256; $n = $s.Read($tampon, 0, 256)
        return ([Text.Encoding]::ASCII.GetString($tampon, 0, $n) -split "`r`n")[0]
    } catch { return ("erreur ({0})" -f $_.Exception.GetType().Name) } finally { $t.Close() }
}
Noter ""
Noter "--- 4. Le pont navigateur (attendu : 403, ou rien n'ecoute) ---"
Noter ("origine page web   : {0}" -f (Poignee "https://exemple.invalid"))
Noter ("sans origine       : {0}" -f (Poignee ""))

function Lier([int]$port, [bool]$reutiliser) {
    $s = New-Object Net.Sockets.Socket([Net.Sockets.AddressFamily]::InterNetwork, [Net.Sockets.SocketType]::Stream,
                                       [Net.Sockets.ProtocolType]::Tcp)
    try {
        if ($reutiliser) { $s.SetSocketOption([Net.Sockets.SocketOptionLevel]::Socket,
                                              [Net.Sockets.SocketOptionName]::ReuseAddress, $true) }
        $s.Bind((New-Object Net.IPEndPoint([Net.IPAddress]::Parse("127.0.0.1"), $port)))
        return "LIAISON ACCEPTEE (ce compte pourrait prendre le port)"
    } catch [Net.Sockets.SocketException] {
        return ("refusee : {0} ({1})" -f $_.Exception.SocketErrorCode, $_.Exception.ErrorCode)
    } finally { $s.Close() }
}
Noter ""
Noter "--- 5. Ce compte veut le meme port (liaison seulement, jamais d'ecoute ; fermee aussitot) ---"
foreach ($port in @(8550, 11434)) {
    $occupant = Proprietaire $port
    Noter ("127.0.0.1:{0,-5} (tenu par : {1})" -f $port, $occupant)
    if ($occupant -eq "libre") { Noter "    port libre : une liaison acceptee est normale, la mesure ne dit rien ici"; continue }
    Noter ("    sans SO_REUSEADDR : {0}" -f (Lier $port $false))
    Noter ("    avec SO_REUSEADDR : {0}" -f (Lier $port $true))
}

if ($Sortie -eq "") {
    $dossier = Join-Path $PSScriptRoot "releves"
    New-Item -ItemType Directory -Force -Path $dossier | Out-Null
    $Sortie = Join-Path $dossier ("mesure_comptes_{0}.txt" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
}
[IO.File]::WriteAllLines($Sortie, $lignes.ToArray(), (New-Object Text.UTF8Encoding($true)))
Write-Host ""
Write-Host "Rapport ecrit a cote de ce fichier, dans releves\ ." -ForegroundColor DarkGray
Write-Host "Ce script n'a rien installe ni modifie." -ForegroundColor DarkGray
