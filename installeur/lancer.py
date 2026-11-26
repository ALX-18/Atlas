"""
Sprint Installeur — le raccourci « Atlas » : démarre le serveur d'Atlas (sans fenêtre noire), puis la fenêtre.

Lancé par pythonw.exe (raccourcis du Bureau et du menu Démarrer, démarrage avec Windows). Si Atlas tourne déjà,
seule la fenêtre s'ouvre. Le journal du serveur va dans data/logs/atlas_serveur.log.

Ollama d'abord : s'il ne répond pas sur 127.0.0.1:11434, son serveur est lancé sans fenêtre (jamais l'application
Ollama, qui ouvre une fenêtre et invite à se connecter à un compte), et c'est noté dans le journal d'Atlas.

IF7 (Réunion n° 3) : `127.0.0.1` est commun aux sessions Windows d'un PC. Avant de se brancher sur un Ollama
(11434) ou un Atlas (8550) qui écoute, le lanceur vérifie qu'il appartient au compte courant (illisible : pas à
moi). Sinon : refus, avec [Réessayer] et [Fermer], et rien n'est envoyé. Au démarrage avec Windows (rien ne
s'affiche sous pythonw), le refus est noté au journal et dit à la première ouverture. L'Ollama que le lanceur
lance est noté (data/ollama_lance.json) : Atlas l'arrêtera en quittant, et lui seul.

    pythonw installeur/lancer.py [--sans-fenetre]     # --sans-fenetre : démarrage avec Windows, serveur seul
"""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import proprietaire  # noqa: E402
from core.proprietaire import Verdict, debut_processus  # noqa: E402

PORT = 8550
PORT_OLLAMA = 11434
JOURNAL = ROOT / "data" / "logs" / "atlas_serveur.log"
JOURNAL_OLLAMA = ROOT / "data" / "logs" / "ollama_serveur.log"
REFUS_DEMARRAGE = ROOT / "data" / "logs" / "refus_demarrage.json"
OLLAMA_LANCE = ROOT / "data" / "ollama_lance.json"
_refus_ollama: Optional[Verdict] = None


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


def verdict_atlas() -> Verdict:
    return proprietaire.verifier(PORT)


def verdict_ollama() -> Verdict:
    return proprietaire.verifier(PORT_OLLAMA)


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


def demarrer_ollama_sans_fenetre(exe: pathlib.Path, journal: pathlib.Path, popen=subprocess.Popen):
    """Le serveur d'Ollama seul (`ollama serve`), sans fenêtre, sur 127.0.0.1 quel que soit l'environnement.
    Il survit au lanceur et à l'installeur ; sa sortie va dans `journal`. Rend le processus lancé."""
    journal.parent.mkdir(parents=True, exist_ok=True)
    sortie = open(journal, "a", encoding="utf-8")
    return popen([str(exe), "serve"], stdout=sortie, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                 env={**os.environ, "OLLAMA_HOST": f"127.0.0.1:{PORT_OLLAMA}"},
                 creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


def noter_ollama_lance(processus, par: str, chemin: Optional[pathlib.Path] = None) -> None:
    """Le numéro et l'heure de démarrage de l'Ollama lancé pour Atlas : Atlas l'arrêtera en quittant, lui seul."""
    pid = getattr(processus, "pid", None)
    if not pid:
        return
    try:
        from core import ollama_lance

        ollama_lance.noter(pid, debut_processus(pid), par, chemin or OLLAMA_LANCE)
    except Exception as e:
        noter(f"Ollama lancé (processus {pid}) : note impossible ({type(e).__name__}) — Atlas ne l'arrêtera pas")


def assurer_ollama(ecoute=None, exe=None, demarrer=None, noter=None, verifier=None) -> str:
    """« tourne » (le sien, rien à faire), « lance » (serveur démarré sans fenêtre), « absent » (Ollama
    introuvable), ou « autre » / « illisible » (IF7 : un Ollama qui n'est pas au compte écoute déjà : refus)."""
    noter = noter or globals()["noter"]
    exe = exe or ollama_installe
    demarrer = demarrer or demarrer_ollama_sans_fenetre
    if verifier is None:
        verifier = (lambda: Verdict("a_moi" if ecoute() else "libre")) if ecoute is not None else verdict_ollama
    global _refus_ollama
    v = verifier()
    _refus_ollama = v if v.refuse else None
    if v.a_moi:
        return "tourne"
    if v.refuse:
        noter(f"refus : l'Ollama qui écoute sur 127.0.0.1:{PORT_OLLAMA} n'est pas à ce compte ({v.etat}, "
              f"processus {v.pid}) — rien ne lui est envoyé")
        return v.etat
    chemin = exe()
    if chemin is None:
        noter("Ollama introuvable : Atlas démarre sans son modèle de langue (relancer l'installation d'Atlas)")
        return "absent"
    processus = demarrer(chemin, JOURNAL_OLLAMA)
    noter(f"Ollama ne tournait pas : son serveur est lancé sans fenêtre, sur 127.0.0.1:{PORT_OLLAMA}")
    noter_ollama_lance(processus, "lanceur")
    return "lance"


def demarrer_serveur() -> None:
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    journal = open(JOURNAL, "a", encoding="utf-8")
    subprocess.Popen([python_console(), str(ROOT / "main.py")], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT,
                     env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                     creationflags=subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP)


def ouvrir_fenetre() -> None:
    subprocess.Popen([sys.executable, str(ROOT / "desktop" / "atlas_desktop.py")], cwd=ROOT)


def demarrer_atlas() -> Optional[tuple[str, Verdict]]:
    """Ollama, puis le serveur d'Atlas. None : prêt. Sinon (composant, verdict) : refusé, rien n'a été envoyé."""
    r = assurer_ollama()
    if r in ("autre", "illisible"):
        return "Ollama", _refus_ollama or Verdict(r)
    v = verdict_atlas()
    if v.refuse:
        noter(f"refus : l'Atlas qui écoute sur 127.0.0.1:{PORT} n'est pas à ce compte ({v.etat}, processus {v.pid})")
        return "Atlas", v
    if v.a_moi:
        return None
    demarrer_serveur()
    for _ in range(240):
        v = verdict_atlas()
        if v.a_moi:
            return None
        if v.refuse:      # tour 2 : notre serveur n'a pas démarré, et un autre a pris le port pendant l'attente
            noter(f"refus : pendant le démarrage, 127.0.0.1:{PORT} a été pris par un Atlas qui n'est pas à ce compte "
                  f"({v.etat}, processus {v.pid})")
            return "Atlas", v
        time.sleep(0.5)
    noter(f"le serveur d'Atlas ne répond pas après 2 minutes (journal : {JOURNAL.name})")
    return None


def _ecrire_refus_demarrage(composant: str, v: Verdict) -> None:
    try:
        REFUS_DEMARRAGE.parent.mkdir(parents=True, exist_ok=True)
        REFUS_DEMARRAGE.write_text(json.dumps({"composant": composant, "etat": v.etat,
                                               "quand": f"{datetime.datetime.now():%H:%M}"}), encoding="utf-8")
    except OSError:
        pass


def _lire_refus_demarrage() -> Optional[str]:
    try:
        note = json.loads(REFUS_DEMARRAGE.read_text(encoding="utf-8"))
        REFUS_DEMARRAGE.unlink()
    except (OSError, ValueError):
        return None
    composant = note.get("composant", "Atlas")
    pourquoi = ("son propriétaire n'a pas pu être vérifié" if note.get("etat") == "illisible"
                else "il était lancé par une autre session Windows de ce PC")
    return (f"Au démarrage de Windows, à {note.get('quand', '?')}, Atlas n'a pas pu s'ouvrir : {composant} était déjà "
            f"lancé et {pourquoi}. Rien ne lui a été envoyé. Maintenant, Atlas s'ouvre normalement.")


class FenetreRefus:
    """Le refus, en clair : [Réessayer] (revérifie) ou [Fermer]."""

    def refuser(self, texte: str) -> bool:
        import tkinter as tk
        from tkinter import ttk

        choix = {"reessayer": False}
        racine = tk.Tk()
        racine.title("Atlas ne peut pas s'ouvrir pour l'instant")
        racine.resizable(False, False)
        cadre = ttk.Frame(racine, padding=18)
        cadre.pack(fill="both", expand=True)
        ttk.Label(cadre, text=texte, wraplength=480, justify="left").pack(anchor="w")
        boutons = ttk.Frame(cadre, padding=(0, 14, 0, 0))
        boutons.pack(anchor="e")

        def reessayer():
            choix["reessayer"] = True
            racine.destroy()

        ttk.Button(boutons, text="Réessayer", command=reessayer).pack(side="left", padx=4)
        ttk.Button(boutons, text="Fermer", command=racine.destroy).pack(side="left", padx=4)
        racine.protocol("WM_DELETE_WINDOW", racine.destroy)
        racine.attributes("-topmost", True)
        racine.mainloop()
        return choix["reessayer"]

    def informer(self, texte: str) -> None:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showinfo("Atlas", texte, parent=racine)
        racine.destroy()


def main(argv=None, ui=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    sans_fenetre = "--sans-fenetre" in args
    note = None if sans_fenetre else _lire_refus_demarrage()
    while True:
        refus = demarrer_atlas()
        if refus is None:
            break
        composant, v = refus
        if sans_fenetre:
            _ecrire_refus_demarrage(composant, v)
            noter("refus noté : il sera dit à la première ouverture de la fenêtre")
            return 4
        ui = ui or FenetreRefus()
        if not ui.refuser(proprietaire.message_refus(composant, v, sortie="reessayer")):
            noter("refus : la personne a fermé la fenêtre de refus")
            return 4
        noter("refus : la personne réessaie")
    if sans_fenetre:
        return 0
    if note:
        (ui or FenetreRefus()).informer(note)
    ouvrir_fenetre()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
