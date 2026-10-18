"""
Sprint Apprentissage 1 — rejeu réel : provoquer, apprendre, répéter (rapport D §6.1), et une
correction d'Alexis apprise, appliquée, dite, listée, oubliée.

    python scripts/rejeu_apprentissage.py --out <dossier>

Atlas réel, lancé TROIS fois sur la MÊME copie de la mémoire (ce qui est appris doit survivre à
un redémarrage ; le cache de clics, lui, ne survit pas) :
  1. passe 1 des clics ; demande mal routée, puis la correction d'Alexis ;
  2. passe 2 des clics ; la demande corrigée refaite ; « qu'est-ce que tu as appris ? » ;
     « oublie ce que tu as appris sur … » (confirmé) ; la demande refaite après l'oubli ;
  3. apprentissage neutralisé (ATLAS_APPRENTISSAGE=off) : passe 3 des clics.

Les demandes portent l'origine « fenetre » : elles jouent Alexis au clavier (sur une copie).
Seules des fenêtres de test créées ici sont visées ; les gardes de checkup_dynamique s'appliquent.
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
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from checkup_dynamique import API, DATA, PROTEGES, PY, ROOT, _empreinte, attendre, req  # noqa: E402

CLICS = [("AtlasEssaiClair", "Bibliothèque"), ("AtlasEssaiSombre", "Magasin")]
TEMOIN = "AtlasEssaiTemoin"


def _fenetre(titre: str, x: int, y: int, texte: str, fond: str, encre: str, taille: int, sortie: pathlib.Path):
    code = (
        "import tkinter as t, pathlib, json\n"
        f"r = t.Tk(); r.title({titre!r}); r.geometry('420x200+{x}+{y}'); r.configure(bg={fond!r}); "
        "r.attributes('-topmost', True)\n"
        f"f = pathlib.Path({str(sortie)!r})\n"
        "def clic():\n    f.write_text(json.dumps({'clic': True}))\n"
        f"t.Button(r, text={texte!r}, font=('Segoe UI', {taille}), bg={fond!r}, fg={encre!r}, relief='flat', "
        f"activebackground={fond!r}, command=clic).pack(pady=60)\n"
        "r.mainloop()\n")
    p = subprocess.Popen([PY, "-c", code])
    time.sleep(2)
    return p


def _chat(message: str) -> dict:
    t = time.perf_counter()
    out, _ = req("/chat", {"message": message, "history": [], "origine": "fenetre"})
    out["_duree_s"] = round(time.perf_counter() - t, 2)
    return out


def _resume(out: dict) -> dict:
    tr = (out.get("tool_results") or [{}])[0]
    inner = tr.get("result") if isinstance(tr.get("result"), dict) else {}
    return {"type": out.get("type"), "message": (out.get("message") or "")[:260], "outil": tr.get("tool"),
            "couches": [(a.get("layer"), a.get("result"), a.get("latency_ms")) for a in inner.get("layer_attempts") or []],
            "duree_s": out.get("_duree_s"), "confirmation_id": out.get("confirmation_id")}


class Atlas:
    def __init__(self, copie: pathlib.Path, journal: pathlib.Path, neutralise: bool = False):
        # Apprentissage 2 : ce qui est appris et le journal des actions vont aussi dans la copie —
        # avant, les rejeux écrivaient dans le journal d'Alexis (la source de ses habitudes).
        env = {**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(copie), "PYTHONIOENCODING": "utf-8",
               "ATLAS_APPRENTISSAGE_DB": str(copie.parent / "apprentissage.db"),
               "ATLAS_ACTIONS_LOG": str(copie.parent / "atlas_actions.jsonl"),
               "ATLAS_HABITS_DB": str(copie.parent / "habits.db"), "ATLAS_RAPPELS_DB": str(copie.parent / "rappels.db")}
        if neutralise:
            env["ATLAS_APPRENTISSAGE"] = "off"
        self.journal = open(journal, "w", encoding="utf-8")
        self.p = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=self.journal, stderr=subprocess.STDOUT, env=env,
                                  creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")
        time.sleep(12)

    def arreter(self) -> str:
        try:
            os.kill(self.p.pid, signal.CTRL_BREAK_EVENT)
            self.p.wait(60)
            etat = "propre"
        except Exception as e:
            self.p.kill()
            etat = f"forcé ({e!r})"
        self.journal.close()
        time.sleep(3)
        return etat


def _passe_clics(dossier: pathlib.Path, nom: str) -> list[dict]:
    lignes = []
    for titre, libelle in CLICS:
        (dossier / f"{titre}.json").unlink(missing_ok=True)
        r = _resume(_chat(f"clique sur {libelle} dans {titre}"))
        time.sleep(1)
        r["clic_recu"] = (dossier / f"{titre}.json").exists()
        r["fenetre"], r["passe"] = titre, nom
        lignes.append(r)
        print(json.dumps(r, ensure_ascii=False)[:320], flush=True)
    return lignes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    avant = {n: _empreinte(DATA / n) for n in PROTEGES}
    gardes = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ap_garde_"))
    for n in PROTEGES:
        src = DATA / n
        if src.is_dir():
            shutil.copytree(src, gardes / n)
        elif src.exists():
            shutil.copy2(src, gardes / n)
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ap_"))
    copie = travail / "chromadb"
    shutil.copytree(DATA / "chromadb", copie)

    fen = [
        _fenetre("AtlasEssaiClair", 100, 300, "Bibliothèque", "#ffffff", "#000000", 20, dossier / "AtlasEssaiClair.json"),
        _fenetre("AtlasEssaiSombre", 600, 300, "Magasin", "#2b2d31", "#5c5f66", 10, dossier / "AtlasEssaiSombre.json"),
        _fenetre(TEMOIN, 1100, 300, "Témoin", "#f0f0f0", "#000000", 14, dossier / "temoin.json"),
    ]
    res: dict = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "clics": [], "correction": [], "arrets": []}
    atlas = None
    try:
        # --- Lancement 1 ---
        atlas = Atlas(copie, dossier / "atlas_1.log")
        res["clics"] += _passe_clics(dossier, "1")
        for phrase in ["mets le témoin devant", f"non, je voulais mets {TEMOIN} au premier plan"]:
            res["correction"].append({"lancement": 1, "phrase": phrase, **_resume(_chat(phrase))})
            print(json.dumps(res["correction"][-1], ensure_ascii=False)[:320], flush=True)
        res["arrets"].append(atlas.arreter())

        # --- Lancement 2 : après redémarrage ---
        atlas = Atlas(copie, dossier / "atlas_2.log")
        res["clics"] += _passe_clics(dossier, "2")
        for phrase in ["mets le témoin devant", "qu'est-ce que tu as appris ?",
                       "oublie ce que tu as appris sur mets le témoin devant"]:
            r = _resume(_chat(phrase))
            res["correction"].append({"lancement": 2, "phrase": phrase, **r})
            print(json.dumps(res["correction"][-1], ensure_ascii=False)[:320], flush=True)
            if r.get("confirmation_id"):
                rep, _ = req("/confirm", {"confirmation_id": r["confirmation_id"], "accepted": True})
                res["correction"].append({"lancement": 2, "phrase": "(confirmation acceptée)",
                                          "message": (rep.get("message") or str(rep.get("result", "")))[:200]})
        res["correction"].append({"lancement": 2, "phrase": "mets le témoin devant (après l'oubli)",
                                  **_resume(_chat("mets le témoin devant"))})
        res["appris_a_la_fin"] = _resume(_chat("qu'est-ce que tu as appris ?"))["message"]
        res["arrets"].append(atlas.arreter())

        # --- Lancement 3 : neutralisé ---
        atlas = Atlas(copie, dossier / "atlas_3.log", neutralise=True)
        res["clics"] += _passe_clics(dossier, "3 (neutralisé)")
        res["arrets"].append(atlas.arreter())
        atlas = None
    finally:
        if atlas:
            res["arrets"].append(atlas.arreter())
        for p in fen:
            p.terminate()
        remis = []
        for n in PROTEGES:
            if _empreinte(DATA / n) != avant[n]:
                cible, src = DATA / n, gardes / n
                if cible.is_dir():
                    shutil.rmtree(cible)
                    shutil.copytree(src, cible)
                elif src.exists():
                    shutil.copy2(src, cible)
                else:
                    cible.unlink(missing_ok=True)
                remis.append(n)
        res["fichiers_remis_en_etat"] = remis
        res["fichiers_identiques_apres"] = all(_empreinte(DATA / n) == avant[n] for n in PROTEGES)
        import gc

        gc.collect()
        shutil.rmtree(travail, ignore_errors=True)
        shutil.rmtree(gardes, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"→ {dossier / 'rejeu.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
