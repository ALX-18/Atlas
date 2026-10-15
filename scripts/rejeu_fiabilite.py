"""
Sprint Fiabilité — rejeu réel : Atlas lancé pour de vrai, sur une COPIE de la mémoire.

    python scripts/rejeu_fiabilite.py --out <dossier>

1. Les 5 phrases du Check-up et les 2 de G-bis, tapées (route /api/chat).
2. FI3 : « ouvre la calculatrice » (deux fois : la seconde doit ramener, pas rouvrir),
   « ouvre les paramètres », « ouvre le bloc-notes » ; instances comptées après chaque demande.
   Le Bloc-notes n'est rejoué que si aucun Bloc-notes n'est ouvert (Windows 11 ajouterait un
   onglet dans la fenêtre d'Alexis).
3. FI7 bis : une fenêtre de test sur l'écran 1, une sur l'écran 2, une à cheval ; « lis l'écran »
   puis « clique sur Bibliothèque » ; le clic est vérifié par la fenêtre elle-même.

Garde-fous : ceux de checkup_dynamique (refus si Atlas tourne, copie de la mémoire, fichiers de
data/ remis en état, arrêt propre). Toute confirmation est ANNULÉE. Seules les fenêtres ouvertes
par ce rejeu sont fermées.
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
from checkup_dynamique import (API, DATA, PROTEGES, PY, ROOT, _annuler_confirmations, _empreinte,  # noqa: E402
                               _fenetres, attendre, req)


def _fenetre_bouton(titre: str, x: int, y: int, sortie: pathlib.Path):
    """Une fenêtre Tk avec un bouton « Bibliothèque » qui note chaque clic reçu."""
    code = (
        "import tkinter as t, pathlib, json\n"
        f"r = t.Tk(); r.title({titre!r}); r.geometry('460x220+{x}+{y}'); r.attributes('-topmost', True)\n"
        f"f = pathlib.Path({str(sortie)!r})\n"
        "def clic(e=None):\n"
        "    f.write_text(json.dumps({'clic': True, 'x': r.winfo_pointerx(), 'y': r.winfo_pointery()}))\n"
        "b = t.Button(r, text='Bibliothèque', font=('Segoe UI', 20), command=clic); b.pack(pady=50)\n"
        "r.mainloop()\n")
    p = subprocess.Popen([PY, "-c", code])
    time.sleep(3)
    return p


def _instances() -> dict:
    import psutil

    noms = {"calculatorapp": 0, "systemsettings": 0, "notepad": 0}
    for p in psutil.process_iter(["name"]):
        n = (p.info["name"] or "").lower().removesuffix(".exe")
        if n in noms:
            noms[n] += 1
    return {"processus": noms, "fenetres_calculatrice": len(_fenetres("Calculatrice")),
            "fenetres_parametres": len(_fenetres("Paramètres"))}


def _fermer_nouvelles(avant: set[int]) -> int:
    import win32con
    import win32gui

    fermees = 0
    for titre in ("Calculatrice", "Paramètres"):
        for h in _fenetres(titre) - avant:
            win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
            fermees += 1
    return fermees


def _dire(phrase: str) -> dict:
    t = time.perf_counter()
    try:
        out, _ = req("/chat", {"message": phrase, "history": []})
    except Exception as e:
        return {"phrase": phrase, "erreur": repr(e)[:200]}
    tr = out.get("tool_results") or []
    ligne = {"phrase": phrase, "duree_s": round(time.perf_counter() - t, 2), "type": out.get("type"),
             "message": (out.get("message") or "")[:300],
             "outil": tr[0].get("tool") if tr else None, "statut": tr[0].get("status") if tr else None}
    ligne["confirmations_annulees"] = _annuler_confirmations()
    return ligne


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
    gardes = pathlib.Path(tempfile.mkdtemp(prefix="atlas_fi_garde_"))
    for n in PROTEGES:
        src = DATA / n
        if src.is_dir():
            shutil.copytree(src, gardes / n)
        elif src.exists():
            shutil.copy2(src, gardes / n)
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_fi_"))
    shutil.copytree(DATA / "chromadb", travail / "chromadb")

    res: dict = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "phrases": [], "applications": [], "ecrans": []}
    fen = []
    env = {**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(travail / "chromadb"),
           "PYTHONIOENCODING": "utf-8"}
    journal = open(dossier / "atlas_stdout.log", "w", encoding="utf-8")
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")
        time.sleep(15)
        res["bascules_au_depart"] = req("/health")[0].get("bascules")

        # 1. Les phrases du Check-up et de G-bis
        for phrase in ["quel est le numéro de mon essai de check-up ?", "résume la page https://example.com",
                       "liste les programmes en cours", "liste mes tâches planifiées",
                       "rappelle-moi de boire de l'eau tous les jours à 15h",
                       "ajoute du lait à ma liste de courses", "résume l'histoire de Rome"]:
            res["phrases"].append(_dire(phrase))
            print(json.dumps(res["phrases"][-1], ensure_ascii=False)[:300], flush=True)

        # 2. FI3 — une instance par demande
        calc_avant, param_avant = _fenetres("Calculatrice"), _fenetres("Paramètres")
        notepad_deja = _instances()["processus"]["notepad"] > 0
        demandes = ["ouvre la calculatrice", "ouvre la calculatrice", "ouvre les paramètres"]
        if not notepad_deja:
            demandes.append("ouvre le bloc-notes")
        else:
            res["bloc_notes"] = "non rejoué : un Bloc-notes d'Alexis est ouvert (Windows 11 y ajouterait un onglet)"
        notepad_avant = set()
        for phrase in demandes:
            if "bloc-notes" in phrase:
                notepad_avant = {h for h in _fenetres_par_processus("notepad")}
            ligne = _dire(phrase)
            time.sleep(6)
            ligne["instances_apres"] = _instances()
            res["applications"].append(ligne)
            print(json.dumps(ligne, ensure_ascii=False)[:400], flush=True)
        res["fermees_par_le_rejeu"] = _fermer_nouvelles(calc_avant | param_avant)
        if not notepad_deja:
            import win32con
            import win32gui

            for h in set(_fenetres_par_processus("notepad")) - notepad_avant:
                win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
                res["fermees_par_le_rejeu"] += 1

        # 3. FI7 bis — écran 1, écran 2, à cheval
        for nom, x, y in [("AtlasEssaiEcranUn", 300, 300), ("AtlasEssaiEcranDeux", 2300, 300),
                          ("AtlasEssaiCheval", 1690, 600)]:
            sortie = dossier / f"{nom}.json"
            sortie.unlink(missing_ok=True)
            fen.append(_fenetre_bouton(nom, x, y, sortie))
            ligne = {"fenetre": nom, "position": [x, y]}
            ligne["premier_plan"] = _dire(f"mets {nom} au premier plan")["message"][:120]
            ligne["lecture"] = _dire("lis l'écran")["message"][:200]
            clic = _dire(f"clique sur Bibliothèque dans {nom}")
            time.sleep(1)
            ligne["clic"] = clic["message"][:200]
            ligne["clic_recu_par_la_fenetre"] = json.loads(sortie.read_text()) if sortie.exists() else None
            res["ecrans"].append(ligne)
            print(json.dumps(ligne, ensure_ascii=False)[:400], flush=True)
            fen[-1].terminate()
        res["bascules_a_la_fin"] = req("/health")[0].get("bascules")
    finally:
        try:
            os.kill(atlas.pid, signal.CTRL_BREAK_EVENT)
            atlas.wait(60)
            res["arret"] = "propre"
        except Exception as e:
            atlas.kill()
            res["arret"] = f"forcé ({e!r})"
        journal.close()
        for p in fen:
            p.terminate()
        time.sleep(2)
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


def _fenetres_par_processus(nom: str) -> list[int]:
    import psutil
    import win32gui
    import win32process

    vues = []

    def rappel(h, _):
        if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h):
            try:
                _, pid = win32process.GetWindowThreadProcessId(h)
                if psutil.Process(pid).name().lower().removesuffix(".exe") == nom:
                    vues.append(h)
            except Exception:
                pass
        return True

    win32gui.EnumWindows(rappel, None)
    return vues


if __name__ == "__main__":
    raise SystemExit(main())
