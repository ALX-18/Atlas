"""
Sprint Installeur / IN6 — préparer un essai dans Windows Sandbox (le fichier .wsb, avec les bons dossiers).

    python installeur/sandbox/preparer.py --mode complet          # 16 Go de mémoire : le parcours entier
    python installeur/sandbox/preparer.py --mode ne_convient_pas  # 8 Go : l'installation doit s'arrêter proprement
    python installeur/sandbox/preparer.py --mode complet --stockage T:\\AtlasSandbox   # gros fichiers hors de C:

Puis double-clic sur le .wsb produit (build/installeur/sandbox_<mode>.wsb). Dossiers partagés : l'installeur (lecture
seule), ce script (lecture seule), le cache des téléchargements (écriture : 1,6 Go d'Ollama, vérifiés par empreinte à
chaque usage) et les résultats (écriture). Rien d'autre du PC n'est visible dans la Sandbox. Pas de carte graphique.

Le disque de la Sandbox vit toujours sur C:. Avec --stockage, le cache des téléchargements et une réserve des modèles
d'Ollama (plusieurs Go) sont rangés dans ce dossier. La réserve est vue dans la Sandbox en C:\\modeles_prets :
parcours.ps1 la copie d'un bloc à la place par défaut d'Ollama avant d'installer (l'installeur trouve le modèle et
vérifie son empreinte), ou l'y range après un premier téléchargement. Ollama ne lit jamais le modèle à travers le
dossier partagé : lu ainsi par morceaux, il ne répondait pas en 15 minutes au test de capacité (Sandbox, 10/11).
"""

from __future__ import annotations

import argparse
import pathlib
from xml.sax.saxutils import escape

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
BUILD = ROOT / "build" / "installeur"
MODELES_SANDBOX = r"C:\modeles_prets"

WSB = """<Configuration>
  <VGpu>Disable</VGpu>
  <Networking>Default</Networking>
  <MemoryInMB>{memoire}</MemoryInMB>
  <ClipboardRedirection>Disable</ClipboardRedirection>
  <PrinterRedirection>Disable</PrinterRedirection>
  <AudioInput>Disable</AudioInput>
  <VideoInput>Disable</VideoInput>
  <MappedFolders>
    <MappedFolder><HostFolder>{build}</HostFolder><SandboxFolder>C:\\atlas_build</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>{sandbox}</HostFolder><SandboxFolder>C:\\atlas_sandbox</SandboxFolder><ReadOnly>true</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>{cache}</HostFolder><SandboxFolder>C:\\cache</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>
    <MappedFolder><HostFolder>{resultats}</HostFolder><SandboxFolder>C:\\resultats</SandboxFolder><ReadOnly>false</ReadOnly></MappedFolder>{modeles}
  </MappedFolders>
  <LogonCommand>
    <Command>powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$env:ATLAS_CACHE_INSTALLATION='C:\\cache'; &amp; C:\\atlas_sandbox\\parcours.ps1 -Mode {mode}"</Command>
  </LogonCommand>
</Configuration>
"""

MODELES = ("\n    <MappedFolder><HostFolder>{hote}</HostFolder><SandboxFolder>{sandbox}</SandboxFolder>"
           "<ReadOnly>false</ReadOnly></MappedFolder>")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("complet", "ne_convient_pas"), default="complet")
    ap.add_argument("--stockage", help="dossier du PC (hors de C:) pour le cache et les modèles d'Ollama de la Sandbox")
    a = ap.parse_args(argv)
    if not (BUILD / "AtlasSetup.exe").exists():
        raise SystemExit("Construire d'abord l'installeur : python installeur/construire.py")
    resultats = BUILD / f"resultats_{a.mode}"
    if a.stockage:
        stockage = pathlib.Path(a.stockage)
        cache, modeles = stockage / "cache", stockage / "ollama_models"
    else:
        cache, modeles = BUILD / "cache_sandbox", None
    for d in (resultats, cache) + ((modeles,) if modeles else ()):
        d.mkdir(parents=True, exist_ok=True)
    sortie = BUILD / f"sandbox_{a.mode}.wsb"
    sortie.write_text(WSB.format(memoire=16384 if a.mode == "complet" else 8192, build=escape(str(BUILD)),
                                 sandbox=escape(str(ROOT / "installeur" / "sandbox")), cache=escape(str(cache)),
                                 resultats=escape(str(resultats)), mode=a.mode,
                                 modeles=MODELES.format(hote=escape(str(modeles)), sandbox=MODELES_SANDBOX)
                                 if modeles else ""), encoding="utf-8")
    print(sortie)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
