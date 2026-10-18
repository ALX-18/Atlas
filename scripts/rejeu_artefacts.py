"""
Sprint Artefacts — rejeu réel par Atlas : les deux documents laissés à Alexis, et la question quand
une information manque.

    python scripts/rejeu_artefacts.py --out <dossier> [--sujet "…"]

1. un document de TEST (« AtlasEssai rapport de stage.docx », fictif) est posé dans
   Documents\\AtlasEssaiArtefacts ; Atlas réel démarre (mémoire, apprentissage, journal, habitudes :
   copies ; index et Documents\\Atlas : les vrais) et l'indexe ;
2. « fais-moi un rapport sur <sujet> » : réponse immédiate, puis l'annonce (relevée sur
   /api/annonces) ; le fichier est ouvert par Atlas ;
3. « résume mon rapport de stage AtlasEssai dans un Word » : idem ;
4. « rédige un compte rendu de mes notes de réunion AtlasEssai » : la question (date,
   participants) ; « laisse tomber » : rien n'est rédigé ;
5. le document source et son dossier sont supprimés ; les DEUX documents produits restent dans
   Documents\\Atlas pour qu'Alexis les juge.
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
from banc_artefacts import REUNION, STAGE, _docx_source  # noqa: E402
from checkup_dynamique import API, DATA, PY, ROOT, attendre, req  # noqa: E402


def _get(chemin: str) -> dict:
    import urllib.request

    with urllib.request.urlopen(API + chemin, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sujet", default="l'intelligence artificielle dans la vie quotidienne")
    a = ap.parse_args(argv)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    from tools import documents as d

    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    essai = d.dossier_documents() / "AtlasEssaiArtefacts"
    essai.mkdir(exist_ok=True)
    _docx_source(essai / "AtlasEssai rapport de stage.docx", STAGE)
    (essai / "AtlasEssai notes de réunion.txt").write_text(REUNION, encoding="utf-8")
    avant = set(d.dossier_atlas().glob("*")) if d.dossier_atlas().exists() else set()
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ar_"))
    shutil.copytree(DATA / "chromadb", travail / "chromadb", ignore=shutil.ignore_patterns("*.lock"))
    if (DATA / "habits.db").exists():
        shutil.copy2(DATA / "habits.db", travail / "habits.db")
    env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8",
           "ATLAS_CHROMA_PATH": str(travail / "chromadb"), "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
           "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl"), "ATLAS_HABITS_DB": str(travail / "habits.db")}
    res = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "scenarios": []}
    journal = open(dossier / "atlas.log", "w", encoding="utf-8")
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)

    def chat(phrase):
        out, _ = req("/chat", {"message": phrase, "history": [], "origine": "fenetre"})
        return out

    def scenario(phrase, attendre_annonce=True, limite=900):
        t0 = time.perf_counter()
        r = chat(phrase)
        ligne = {"phrase": phrase, "reponse": (r.get("message") or "")[:300],
                 "reponse_s": round(time.perf_counter() - t0, 2)}
        if attendre_annonce:
            while time.perf_counter() - t0 < limite:
                ann = _get("/annonces").get("annonces", [])
                if ann:
                    ligne["annonce"] = ann[0]["message"]
                    ligne["total_s"] = round(time.perf_counter() - t0, 1)
                    break
                time.sleep(3)
        res["scenarios"].append(ligne)
        print(json.dumps(ligne, ensure_ascii=False)[:600], flush=True)
        return ligne

    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")
        t0 = time.time()
        while time.time() - t0 < 1800:
            if "AtlasEssai rapport de stage" in (chat("où est mon rapport de stage AtlasEssai ?").get("message") or ""):
                break
            time.sleep(15)
        res["attente_index_s"] = round(time.time() - t0)
        scenario(f"fais-moi un rapport sur {a.sujet}")
        scenario("résume mon rapport de stage AtlasEssai dans un Word")
        scenario("rédige un compte rendu de mes notes de réunion AtlasEssai", attendre_annonce=False)
        scenario("laisse tomber", attendre_annonce=False)
        time.sleep(5)
        res["annonces_restantes"] = _get("/annonces").get("annonces", [])
    finally:
        try:
            os.kill(atlas.pid, signal.CTRL_BREAK_EVENT)
            atlas.wait(60)
            res["arret"] = "propre"
        except Exception as e:
            atlas.kill()
            res["arret"] = f"forcé ({e!r})"
        journal.close()
        shutil.rmtree(essai, ignore_errors=True)
        res["source_de_test_supprimee"] = not essai.exists()
        res["documents_laisses"] = sorted(str(p) for p in set(d.dossier_atlas().glob("*")) - avant)
        shutil.rmtree(travail, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
