"""
Sprint Artefacts / AR1 — rejeu réel : deux fenêtres homonymes « AtlasEssai Rapport A » et « B ».

    python scripts/rejeu_fenetres.py --out <dossier> [--racine <copie du dépôt>]

1. « ferme AtlasEssai Rapport » : la question « laquelle ? » (avant : une confirmation qui,
   acceptée, fermait la première trouvée) ;
2. « ferme AtlasEssai Rapport B » : confirmation, acceptée ; on relève quelle fenêtre est fermée ;
3. « réduis AtlasEssai Rapport » (homonymes) ; « réduis AtlasEssai Rapport A ».

Atlas réel, sur des copies (mémoire, apprentissage, journal, habitudes). Seules les fenêtres de
test créées ici sont touchées ; elles sont fermées à la fin.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from checkup_dynamique import API, DATA, PY, ROOT, attendre, req  # noqa: E402

TITRES = ("AtlasEssai Rapport A", "AtlasEssai Rapport B")


def _fenetre(titre: str, x: int):
    code = (f"import tkinter as t\nr = t.Tk(); r.title({titre!r}); r.geometry('360x160+{x}+300')\n"
            f"t.Label(r, text={titre!r}).pack(pady=50)\nr.mainloop()\n")
    return subprocess.Popen([PY, "-c", code])


def _etat(fen: dict) -> dict:
    import win32gui

    vus = {}
    win32gui.EnumWindows(lambda h, _: vus.setdefault(win32gui.GetWindowText(h), h)
                         if win32gui.IsWindowVisible(h) else None, None)
    out = {}
    for t, p in fen.items():
        h = vus.get(t)
        out[t] = "fermée" if p.poll() is not None or not h else ("réduite" if win32gui.IsIconic(h) else "ouverte")
    return out


def _chat(message: str) -> dict:
    out, _ = req("/chat", {"message": message, "history": [], "origine": "fenetre"})
    return {"type": out.get("type"), "message": (out.get("message") or "")[:400], "cible": out.get("target"),
            "confirmation_id": out.get("confirmation_id")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--racine", default=str(ROOT))
    a = ap.parse_args(argv)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ar1_"))
    shutil.copytree(DATA / "chromadb", travail / "chromadb", ignore=shutil.ignore_patterns("*.lock"))
    if (DATA / "habits.db").exists():
        shutil.copy2(DATA / "habits.db", travail / "habits.db")
    env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8",
           "ATLAS_CHROMA_PATH": str(travail / "chromadb"), "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
           "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl"), "ATLAS_HABITS_DB": str(travail / "habits.db"),
           "ATLAS_FILE_INDEX_DB": str(travail / "file_index.db")}
    fen = {t: _fenetre(t, 100 + 420 * k) for k, t in enumerate(TITRES)}
    time.sleep(3)
    res = {"racine": a.racine, "debut": time.strftime("%Y-%m-%d %H:%M:%S"), "scenarios": []}
    journal = open(dossier / "atlas.log", "w", encoding="utf-8")
    atlas = subprocess.Popen([PY, "main.py"], cwd=a.racine, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

    def jouer(phrase, accepter=True):
        r = _chat(phrase)
        if r.get("confirmation_id") and accepter:
            rep, _ = req("/confirm", {"confirmation_id": r["confirmation_id"], "accepted": True})
            r["apres_confirmation"] = (rep.get("message") or str((rep.get("result") or {}).get("message", "")))[:200]
            time.sleep(1.5)
        r["fenetres"] = _etat(fen)
        res["scenarios"].append({"phrase": phrase, **r})
        print(json.dumps(res["scenarios"][-1], ensure_ascii=False)[:500], flush=True)

    def rouvrir():
        for k, t in enumerate(TITRES):
            if fen[t].poll() is not None:
                fen[t] = _fenetre(t, 100 + 420 * k)
        time.sleep(2)

    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")
        time.sleep(10)
        jouer("ferme AtlasEssai Rapport")
        rouvrir()
        jouer("ferme AtlasEssai Rapport B")
        rouvrir()
        jouer("réduis AtlasEssai Rapport")
        jouer("réduis AtlasEssai Rapport A")
    finally:
        try:
            os.kill(atlas.pid, signal.CTRL_BREAK_EVENT)
            atlas.wait(60)
            res["arret"] = "propre"
        except Exception as e:
            atlas.kill()
            res["arret"] = f"forcé ({e!r})"
        journal.close()
        for p in fen.values():
            p.terminate()
        shutil.rmtree(travail, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
