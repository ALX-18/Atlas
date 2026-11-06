"""
Sprint Installeur — le raccourci « Atlas » : démarre le serveur d'Atlas (sans fenêtre noire), puis la fenêtre.

Lancé par pythonw.exe (raccourcis du Bureau et du menu Démarrer, démarrage avec Windows). Si Atlas tourne déjà,
seule la fenêtre s'ouvre. Le journal du serveur va dans data/logs/atlas_serveur.log.

    pythonw installeur/lancer.py [--sans-fenetre]     # --sans-fenetre : démarrage avec Windows, serveur seul
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8550


def python_console() -> str:
    """python.exe (le serveur) à côté de pythonw.exe (ce lanceur)."""
    exe = pathlib.Path(sys.executable)
    cand = exe.with_name("python.exe")
    return str(cand if cand.exists() else exe)


def atlas_tourne() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def demarrer_serveur() -> None:
    logs = ROOT / "data" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    journal = open(logs / "atlas_serveur.log", "a", encoding="utf-8")
    subprocess.Popen([python_console(), str(ROOT / "main.py")], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT,
                     env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                     creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
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
