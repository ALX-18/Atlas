"""
Sprint Index des fichiers — rejeu réel des quatre capacités, avec des FICHIERS DE TEST créés pour
l'occasion puis supprimés (jamais un fichier d'Alexis n'est ouvert).

    python scripts/rejeu_index.py --out <dossier>

1. crée les fichiers de test (noms « AtlasEssai… », un mot unique dans le contenu) dans
   Documents\\AtlasEssaiIndex et Téléchargements ;
2. lance Atlas réel (mémoire, apprentissage et journal : COPIES ; l'index : le vrai, celui du PC) ;
   attend que l'index ait vu les fichiers de test ;
3. joue : ouvrir par le nom, plusieurs correspondances → « le 1 », où est + « ouvre le dossier »,
   le dernier PDF téléchargé (liste, sans ouvrir), le contenu, un script (confirmation, ANNULÉE) ;
4. referme ce qui a été ouvert (Bloc-notes et explorateur ouverts par le rejeu, PID et titres notés),
   supprime les fichiers de test, et repasse l'index pour qu'ils en sortent.

Le résultat (rejeu.json) contient les réponses d'Atlas ; les lignes qui citeraient un fichier
qui n'est pas de test sont remplacées par leur nombre.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from checkup_dynamique import API, DATA, PY, ROOT, attendre, req  # noqa: E402

MOT_UNIQUE = "zorglubfinance"


def _fichiers_de_test() -> dict[str, pathlib.Path]:
    docs = pathlib.Path(os.path.expandvars("%USERPROFILE%")) / "Documents" / "AtlasEssaiIndex"
    dl = pathlib.Path(os.path.expandvars("%USERPROFILE%")) / "Downloads"
    return {"cv": docs / "AtlasEssai CV.txt", "stage": docs / "AtlasEssai rapport de stage.txt",
            "annuel": docs / "AtlasEssai rapport annuel.md", "budget": docs / "AtlasEssai budget.docx",
            "pdf": dl / "AtlasEssai facture.pdf", "script": dl / "AtlasEssai installe.bat"}


def _creer(f: dict[str, pathlib.Path]) -> None:
    f["cv"].parent.mkdir(parents=True, exist_ok=True)
    f["cv"].write_text("Curriculum de test pour Atlas.", encoding="utf-8")
    f["stage"].write_text("Rapport de stage de test.", encoding="utf-8")
    f["annuel"].write_text("# Rapport annuel de test", encoding="utf-8")
    with zipfile.ZipFile(f["budget"], "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body><w:p><w:t>Le budget {MOT_UNIQUE} de test "
                                        "prévoit 1200 euros.</w:t></w:p></w:body></w:document>")
    f["pdf"].write_bytes(b"%PDF-1.4\n% fichier de test Atlas\n")
    f["script"].write_text("@echo Ce script de test ne doit jamais etre lance\r\n", encoding="utf-8")


def _chat(message: str) -> dict:
    t = time.perf_counter()
    out, _ = req("/chat", {"message": message, "history": [], "origine": "fenetre"})
    out["_duree_s"] = round(time.perf_counter() - t, 2)
    return out


def _caviarder(texte: str) -> str:
    """Garde les lignes qui parlent des fichiers de test ; compte les autres."""
    lignes, autres = [], 0
    for l in (texte or "").splitlines():
        if re.search(r"\.\w{2,5}\b", l) and "AtlasEssai" not in l:
            autres += 1
        else:
            lignes.append(l)
    if autres:
        lignes.append(f"[{autres} ligne(s) citant d'autres fichiers, non recopiées]")
    return "\n".join(lignes).replace(os.path.expandvars("%USERNAME%"), "<utilisateur>")


def _resume(out: dict) -> dict:
    tr = (out.get("tool_results") or [{}])[0]
    return {"type": out.get("type"), "outil": tr.get("tool"), "message": _caviarder(out.get("message") or ""),
            "cible": _caviarder(out.get("target") or ""), "confirmation_id": out.get("confirmation_id"),
            "duree_s": out.get("_duree_s")}


def _pids(nom: str) -> set[int]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {nom}", "/FO", "CSV", "/NH"], capture_output=True,
                         text=True).stdout
    return {int(m[1]) for l in out.splitlines() if len(m := [x.strip('"') for x in l.split('","')]) > 1
            and m[1].isdigit()}


def _fermer_explorateur_de_test() -> int:
    import win32con
    import win32gui

    n = []

    def cb(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h) == "AtlasEssaiIndex":
            win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
            n.append(h)
    win32gui.EnumWindows(cb, None)
    return len(n)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    f = _fichiers_de_test()
    _creer(f)
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ix_"))
    shutil.copytree(DATA / "chromadb", travail / "chromadb", ignore=shutil.ignore_patterns("*.lock"))
    env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8",
           "ATLAS_CHROMA_PATH": str(travail / "chromadb"), "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
           "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl"), "ATLAS_HABITS_DB": str(travail / "habits.db")}
    notepad_avant = _pids("notepad.exe")
    res = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "scenarios": []}
    journal = open(dossier / "atlas.log", "w", encoding="utf-8")
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

    def note(phrase, r):
        res["scenarios"].append({"phrase": phrase, **r})
        print(json.dumps(res["scenarios"][-1], ensure_ascii=False)[:400], flush=True)

    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")
        t0 = time.time()
        while time.time() - t0 < 3600:          # l'index (passage de démarrage) doit voir les fichiers de test
            r = _chat("où est mon CV AtlasEssai ?")
            if "AtlasEssai CV.txt" in (r.get("message") or ""):
                break
            time.sleep(20)
        res["attente_index_s"] = round(time.time() - t0)
        note("où en est l'index ?", _resume(_chat("où en est l'index ?")))
        note("ouvre mon CV AtlasEssai", _resume(_chat("ouvre mon CV AtlasEssai")))
        r = _resume(_chat("ouvre le rapport AtlasEssai"))
        note("ouvre le rapport AtlasEssai", r)
        note("le 1", _resume(_chat("le 1")))
        note("où est mon budget AtlasEssai ?", _resume(_chat("où est mon budget AtlasEssai ?")))
        note("ouvre le dossier", _resume(_chat("ouvre le dossier")))
        note("le dernier PDF téléchargé", _resume(_chat("le dernier PDF téléchargé")))
        note(f"le document où je parle de {MOT_UNIQUE}", _resume(_chat(f"le document où je parle de {MOT_UNIQUE}")))
        r = _resume(_chat("ouvre le fichier AtlasEssai installe"))
        if r.get("confirmation_id"):
            rep, _ = req("/confirm", {"confirmation_id": r["confirmation_id"], "accepted": False})
            r["reponse_annuler"] = rep.get("message")
        note("ouvre le fichier AtlasEssai installe", r)
        time.sleep(3)
    finally:
        try:
            os.kill(atlas.pid, signal.CTRL_BREAK_EVENT)
            atlas.wait(60)
            res["arret"] = "propre"
        except Exception as e:
            atlas.kill()
            res["arret"] = f"forcé ({e!r})"
        journal.close()
        nouveaux = _pids("notepad.exe") - notepad_avant
        for pid in nouveaux:
            subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True)
        res["bloc_notes_refermes"] = len(nouveaux)
        res["explorateurs_refermes"] = _fermer_explorateur_de_test()
        time.sleep(2)
        for p in f.values():
            p.unlink(missing_ok=True)
        try:
            f["cv"].parent.rmdir()
        except OSError:
            pass
        res["fichiers_de_test_supprimes"] = not any(p.exists() for p in f.values())
        from core import file_indexer as fi

        idx = fi.FileIndexer()
        idx._cfg = {**idx._cfg, "cpu_max_pourcent": 100,
                    "scan_roots": [str(f["cv"].parent.parent), str(f["pdf"].parent)]}
        # Repasser seulement Documents et Téléchargements : les fichiers de test sortent de l'index.
        idx.passage()
        res["fichiers_de_test_dans_l_index"] = sum(len(fi.chercher_nom(f"AtlasEssai {k}", limite=5)) for k in
                                                   ("cv", "rapport", "budget", "facture", "installe"))
        shutil.rmtree(travail, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"→ {dossier / 'rejeu.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
