"""
Sprint Installeur — le raccourci « Atlas » : démarre le serveur d'Atlas (sans fenêtre noire), puis la fenêtre.

Lancé par pythonw.exe (raccourcis du Bureau et du menu Démarrer, démarrage avec Windows). Si Atlas tourne déjà,
seule la fenêtre s'ouvre. Le journal du serveur va dans data/logs/atlas_serveur.log.

Ollama d'abord : s'il ne répond pas sur 127.0.0.1:11434, son serveur est lancé sans fenêtre (jamais l'application
Ollama, qui ouvre une fenêtre et invite à se connecter à un compte), et c'est noté dans le journal d'Atlas.

    pythonw installeur/lancer.py [--sans-fenetre]     # --sans-fenetre : démarrage avec Windows, serveur seul
"""

from __future__ import annotations

import datetime
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8550
PORT_OLLAMA = 11434
JOURNAL = ROOT / "data" / "logs" / "atlas_serveur.log"
JOURNAL_OLLAMA = ROOT / "data" / "logs" / "ollama_serveur.log"


def python_console() -> str:
    """python.exe (le serveur) à côté de pythonw.exe (ce lanceur)."""
    exe = pathlib.Path(sys.executable)
    cand = exe.with_name("python.exe")
    return str(cand if cand.exists() else exe)


def _ecoute(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def atlas_tourne() -> bool:
    return _ecoute(PORT)


def ollama_ecoute() -> bool:
    return _ecoute(PORT_OLLAMA)


def ollama_installe() -> Optional[pathlib.Path]:
    trouve = shutil.which("ollama")
    if trouve:
        return pathlib.Path(trouve)
    cand = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return cand if cand.exists() else None


def noter(message: str) -> None:
    try:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} [lanceur] {message}\n")
    except OSError:
        pass


def demarrer_ollama_sans_fenetre(exe: pathlib.Path, journal: pathlib.Path, popen=subprocess.Popen) -> None:
    """Le serveur d'Ollama seul (`ollama serve`), sans fenêtre, sur 127.0.0.1 quel que soit l'environnement.
    Il survit au lanceur et à l'installeur ; sa sortie va dans `journal`."""
    journal.parent.mkdir(parents=True, exist_ok=True)
    sortie = open(journal, "a", encoding="utf-8")
    popen([str(exe), "serve"], stdout=sortie, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
          env={**os.environ, "OLLAMA_HOST": f"127.0.0.1:{PORT_OLLAMA}"},
          creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


def assurer_ollama(ecoute=ollama_ecoute, exe=ollama_installe, demarrer=demarrer_ollama_sans_fenetre,
                   noter=noter) -> str:
    """« tourne » (rien à faire), « lance » (serveur démarré sans fenêtre) ou « absent » (Ollama introuvable)."""
    if ecoute():
        return "tourne"
    chemin = exe()
    if chemin is None:
        noter("Ollama introuvable : Atlas démarre sans son modèle de langue (relancer l'installation d'Atlas)")
        return "absent"
    demarrer(chemin, JOURNAL_OLLAMA)
    noter(f"Ollama ne tournait pas : son serveur est lancé sans fenêtre, sur 127.0.0.1:{PORT_OLLAMA}")
    return "lance"


def demarrer_serveur() -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    journal = open(JOURNAL, "a", encoding="utf-8")
    subprocess.Popen([python_console(), str(ROOT / "main.py")], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT,
                     env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                     creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    assurer_ollama()
    if not atlas_tourne():
        demarrer_serveur()
        for _ in range(240):
            if atlas_tourne():
                break
            time.sleep(0.5)
    if "--sans-fenetre" in args:
        return 0
    subprocess.Popen([sys.executable, str(ROOT / "desktop" / "atlas_desktop.py")], cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
