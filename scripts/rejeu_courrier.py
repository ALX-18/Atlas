"""
Sprint Compétences 2 / CM8 — le rejeu réel des mails et de l'agenda, avec Alexis présent.

    python scripts/rejeu_courrier.py demarrer --out <dossier>   # un Atlas d'ESSAI + la fenêtre Atlas Desktop
    python scripts/rejeu_courrier.py dire --out <dossier> "j'ai des nouveaux mails ?"
    python scripts/rejeu_courrier.py arreter --out <dossier>

- Atlas d'essai : toutes les redirections ATLAS_* vers un dossier jetable (mémoire vide, journal, apprentissage,
  rappels, habitudes, index) — il n'écrit jamais dans `data/` d'Alexis et n'exécute pas ses déclencheurs ni ses
  tâches planifiées (CM0). Le Gestionnaire d'identification, lui, est le vrai : c'est ce qu'on éprouve.
- Les secrets se saisissent dans la fenêtre de connexion d'Atlas, par Alexis ; les confirmations se donnent par
  Alexis dans la fenêtre Atlas Desktop. Ce script n'envoie que des demandes, et relève les réponses (`rejeu.json`).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
BASE = "http://127.0.0.1:8550/api"


def _req(chemin: str, corps: dict | None = None, delai: float = 600.0) -> dict:
    donnees = json.dumps(corps).encode("utf-8") if corps is not None else None
    r = urllib.request.Request(BASE + chemin, data=donnees, method="POST" if corps is not None else "GET",
                               headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(r, timeout=delai) as rep:
        return json.loads(rep.read().decode("utf-8"))


def demarrer(dossier: pathlib.Path) -> None:
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_rejeu_courrier_"))
    (travail / "chromadb").mkdir()
    env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8",
           "ATLAS_CHROMA_PATH": str(travail / "chromadb"), "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
           "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl"), "ATLAS_HABITS_DB": str(travail / "habits.db"),
           "ATLAS_RAPPELS_DB": str(travail / "rappels.db"), "ATLAS_FILE_INDEX_DB": str(travail / "file_index.db")}
    journal = open(dossier / "atlas.log", "w", encoding="utf-8")
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
    for _ in range(240):
        try:
            _req("/health", delai=3)
            break
        except Exception:
            time.sleep(1)
    else:
        raise SystemExit("Atlas d'essai ne répond pas (voir atlas.log).")
    bureau = subprocess.Popen([PY, "desktop/atlas_desktop.py"], cwd=ROOT, env=env,
                              creationflags=subprocess.DETACHED_PROCESS)
    (dossier / "etat.json").write_text(json.dumps({"atlas": atlas.pid, "bureau": bureau.pid, "travail": str(travail)}),
                                       encoding="utf-8")
    print(f"Atlas d'essai prêt (PID {atlas.pid}), fenêtre Atlas Desktop ouverte (PID {bureau.pid}).")


def dire(dossier: pathlib.Path, phrase: str) -> None:
    fichier = dossier / "rejeu.json"
    rejeu = json.loads(fichier.read_text(encoding="utf-8")) if fichier.exists() else []
    t0 = time.perf_counter()
    r = _req("/chat", {"message": phrase, "history": [], "origine": "fenetre"})
    ligne = {"quand": time.strftime("%H:%M:%S"), "phrase": phrase, "type": r.get("type"),
             "reponse": r.get("message") or "", "duree_s": round(time.perf_counter() - t0, 1)}
    if r.get("type") == "confirmation_required":
        tr = (r.get("tool_results") or [{}])[0]
        ligne["confirmation"] = {"outil": tr.get("tool"), "cible": tr.get("target")}
    rejeu.append(ligne)
    fichier.write_text(json.dumps(rejeu, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(ligne, ensure_ascii=False, indent=1))


def annonces(dossier: pathlib.Path) -> None:
    print(json.dumps(_req("/annonces?depuis=0"), ensure_ascii=False, indent=1))


def arreter(dossier: pathlib.Path) -> None:
    e = json.loads((dossier / "etat.json").read_text(encoding="utf-8"))
    for pid in (e["bureau"], e["atlas"]):
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
    print("Atlas d'essai et fenêtre arrêtés ; dossier jetable :", e["travail"])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=("demarrer", "dire", "annonces", "arreter"))
    ap.add_argument("phrase", nargs="?")
    ap.add_argument("--out", required=True)
    a = ap.parse_intermixed_args(argv)
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    {"demarrer": lambda: demarrer(dossier), "dire": lambda: dire(dossier, a.phrase or ""),
     "annonces": lambda: annonces(dossier), "arreter": lambda: arreter(dossier)}[a.action]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
