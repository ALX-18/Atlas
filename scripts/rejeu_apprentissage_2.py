"""
Sprint Apprentissage 2 — rejeu réel : un seul clic (AQ1), tes refus (AQ3), tes habitudes (AQ4),
le lancement appris et l'ordre du premier plan (AQ5).

    python scripts/rejeu_apprentissage_2.py --out <dossier> [--racine <copie du dépôt>] [--parties aq1,aq3,aq4,aq5]

Atlas réel, lancé plusieurs fois, TOUJOURS sur des copies :
- la mémoire (ATLAS_CHROMA_PATH) : copie de data/chromadb ;
- ce qui est appris (ATLAS_APPRENTISSAGE_DB) : un fichier neuf, dans le dossier de travail ;
- le journal des actions (ATLAS_ACTIONS_LOG) : un fichier neuf, avec un historique SYNTHÉTIQUE
  (Steam puis Discord, trois jours, origine « fenetre ») — jamais le journal d'Alexis ;
- les fichiers protégés de data/ (checkup_dynamique.PROTEGES) : empreinte avant/après, remis en état.

--racine : lancer Atlas depuis une autre copie du dépôt (mesure « avant » : un worktree de main).

Les demandes portent l'origine « fenetre » : elles jouent Alexis au clavier. Seules des fenêtres
de test créées ici sont cliquées ou fermées. Steam et Discord, s'ils sont déjà ouverts, ne sont
que mis au premier plan ; le Bloc-notes ouvert par le rejeu est refermé à la fin (PID notés).
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
from datetime import datetime, timedelta

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from checkup_dynamique import API, DATA, PROTEGES, PY, ROOT, _empreinte, attendre, req  # noqa: E402


def _fenetre(titre: str, x: int, y: int, texte: str, fond: str, encre: str, taille: int, compteur: pathlib.Path,
             apres_clic: str = ""):
    """Une fenêtre de test qui COMPTE les clics reçus (fichier compteur).

    apres_clic : le libellé du bouton une fois cliqué (« Envoyer » → « Envoyé ») — la vérification
    après clic ne retrouve plus « Envoyer » et échoue : c'est le bouton qu'on ne clique pas deux fois."""
    code = (
        "import tkinter as t, pathlib\n"
        f"r = t.Tk(); r.title({titre!r}); r.geometry('420x200+{x}+{y}'); r.configure(bg={fond!r}); "
        "r.attributes('-topmost', True)\n"          # comme le rejeu d'Apprentissage 1
        f"f = pathlib.Path({str(compteur)!r}); f.write_text('0')\n"
        "def clic():\n    f.write_text(str(int(f.read_text() or 0) + 1))\n"
        + (f"    b.config(text={apres_clic!r})\n" if apres_clic else "")
        + f"b = t.Button(r, text={texte!r}, font=('Segoe UI', {taille}), bg={fond!r}, fg={encre!r}, relief='flat', "
        f"activebackground={fond!r}, command=clic)\nb.pack(pady=60)\n"
        "r.mainloop()\n")
    p = subprocess.Popen([PY, "-c", code])
    time.sleep(2)
    return p


def _clics(compteur: pathlib.Path) -> int:
    try:
        return int(compteur.read_text() or 0)
    except Exception:
        return -1


def _premier_plan() -> str:
    try:
        import win32gui

        return win32gui.GetWindowText(win32gui.GetForegroundWindow())
    except Exception:
        return "?"


def _chat(message: str) -> dict:
    t = time.perf_counter()
    out, _ = req("/chat", {"message": message, "history": [], "origine": "fenetre"})
    out["_duree_s"] = round(time.perf_counter() - t, 2)
    return out


def _resume(out: dict) -> dict:
    tr = (out.get("tool_results") or [{}])[0]
    inner = tr.get("result") if isinstance(tr.get("result"), dict) else {}
    return {"type": out.get("type"), "message": (out.get("message") or "")[:400], "outil": tr.get("tool"),
            "statut": tr.get("status"),
            "couches": [(a.get("layer"), a.get("result")) for a in inner.get("layer_attempts") or []],
            "tentatives": [(a.get("methode"), a.get("resultat")) for a in inner.get("tentatives") or []],
            "resolved_by": inner.get("resolved_by"), "duree_s": out.get("_duree_s"),
            "confirmation_id": out.get("confirmation_id")}


def _confirmer(cid: str, accepte: bool) -> str:
    rep, _ = req("/confirm", {"confirmation_id": cid, "accepted": accepte})
    return (rep.get("message") or str((rep.get("result") or {}).get("message", "")) or str(rep))[:200]


class Atlas:
    def __init__(self, racine: pathlib.Path, env_extra: dict, journal: pathlib.Path):
        env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8", **env_extra}
        self.journal = open(journal, "w", encoding="utf-8")
        self.p = subprocess.Popen([PY, "main.py"], cwd=racine, stdout=self.journal, stderr=subprocess.STDOUT, env=env,
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


def _historique_synthetique(chemin: pathlib.Path) -> None:
    """Steam puis Discord (5 min après), et Bloc-notes puis Calculatrice (30 min plus tard), trois jours,
    à l'heure opposée : pas d'habitude horaire. Personne ne répond « oui » à la Calculatrice : elle
    sert à « arrête de me proposer ça »."""
    maintenant = datetime.now()
    lignes = []
    for j in (1, 2, 3):
        t = (maintenant - timedelta(days=j)).replace(hour=(maintenant.hour + 12) % 24, minute=0, second=0,
                                                     microsecond=0)
        for quand, app in ((t, "steam"), (t + timedelta(minutes=5), "discord"),
                           (t + timedelta(minutes=30), "bloc notes"), (t + timedelta(minutes=35), "calculatrice")):
            lignes.append({"timestamp": quand.isoformat(), "user_input": f"ouvre {app}", "intent": "window_mgmt/open",
                           "tool": "launch_app", "target": app, "result": "success", "origine": "fenetre",
                           "synthetique": True})
    chemin.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lignes), encoding="utf-8")


def _pids(nom: str) -> set[int]:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {nom}", "/FO", "CSV", "/NH"], capture_output=True,
                         text=True).stdout
    pids = set()
    for ligne in out.splitlines():
        morceaux = [m.strip('"') for m in ligne.split('","')]
        if len(morceaux) > 1 and morceaux[1].isdigit():
            pids.add(int(morceaux[1]))
    return pids


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--racine", default=str(ROOT))
    ap.add_argument("--parties", default="aq1,aq3,aq4,aq5")
    ap.add_argument("--neutralise", action="store_true", help="un 3e lancement, apprentissage neutralisé")
    a = ap.parse_args(argv)
    parties = set(a.parties.split(","))
    racine = pathlib.Path(a.racine)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    avant = {n: _empreinte(DATA / n) for n in PROTEGES}
    journal_alexis = DATA / "atlas_actions.jsonl"
    journal_alexis_avant = _empreinte(journal_alexis)
    gardes = pathlib.Path(tempfile.mkdtemp(prefix="atlas_aq_garde_"))
    for n in PROTEGES:
        src = DATA / n
        if src.is_dir():
            shutil.copytree(src, gardes / n)
        elif src.exists():
            shutil.copy2(src, gardes / n)
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_aq_"))
    shutil.copytree(DATA / "chromadb", travail / "chromadb", ignore=shutil.ignore_patterns("*.lock"))
    _historique_synthetique(travail / "atlas_actions.jsonl")
    env = {"ATLAS_CHROMA_PATH": str(travail / "chromadb"), "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
           "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl")}

    fen, res = {}, {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "racine": str(racine), "aq1": [], "aq3": [],
                    "aq4": [], "aq5": [], "arrets": []}
    notepad_avant = _pids("notepad.exe")
    atlas = None

    def note(cle, ligne):
        res[cle].append(ligne)
        print(cle, json.dumps(ligne, ensure_ascii=False)[:400], flush=True)

    try:
        if "aq1" in parties:
            fen["sombre"] = _fenetre("AtlasEssaiSombre", 600, 300, "Magasin", "#2b2d31", "#5c5f66", 10,
                                     dossier / "clics_sombre.txt")
            fen["envoi"] = _fenetre("AtlasEssaiEnvoi", 100, 300, "Envoyer", "#ffffff", "#000000", 20,
                                    dossier / "clics_envoi.txt", apres_clic="Envoyé")
        if "aq3" in parties:
            fen["refus"] = _fenetre("AtlasEssaiRefus", 100, 560, "Refus", "#ffffff", "#000000", 14,
                                    dossier / "clics_refus.txt")
        if "aq5" in parties:
            fen["pyw"] = _fenetre("AtlasEssaiPyw", 1100, 300, "Pyw", "#f0f0f0", "#000000", 14, dossier / "c_pyw.txt")
            fen["pyw2"] = _fenetre("AtlasEssaiPyw outils", 1100, 560, "Outils", "#f0f0f0", "#000000", 14,
                                   dossier / "c_pyw2.txt")

        def lendemain():
            """Atlas arrêté : la COPIE oublie quand les habitudes ont été proposées (« le lendemain »)."""
            import sqlite3

            db = travail / "apprentissage.db"
            if db.exists():
                with sqlite3.connect(db) as c:
                    c.execute("DELETE FROM propositions")

        def bloc_notes(lancement, arreter=False):
            avant_bn = _pids("notepad.exe")
            r = _resume(_chat("ouvre le bloc-notes"))
            if "aq4" in parties:
                note("aq4", {"lancement": lancement, "phrase": "ouvre le bloc-notes", **r})
                if arreter:
                    note("aq4", {"lancement": lancement, "phrase": "arrête de me proposer ça",
                                 **_resume(_chat("arrête de me proposer ça"))})
            time.sleep(3)
            nouveaux = _pids("notepad.exe") - avant_bn
            for pid in nouveaux:                    # refermé : la fois suivante, c'est un vrai lancement
                subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True)
            time.sleep(2)
            note("aq5", {"lancement": lancement, "phrase": "ouvre le bloc-notes", "refermes": len(nouveaux), **r})

        def premier_plan_pyw(lancement):
            r = _resume(_chat("mets AtlasEssaiPyw au premier plan"))
            titre = _premier_plan()
            r["premier_plan"] = titre if titre.startswith("AtlasEssai") else "autre"
            note("aq5", {"lancement": lancement, "phrase": "mets AtlasEssaiPyw au premier plan", **r})

        # --- Lancement 1 ---
        atlas = Atlas(racine, env, dossier / "atlas_1.log")
        if "aq1" in parties:
            for phrase, compteur in (("clique sur Magasin dans AtlasEssaiSombre", "clics_sombre.txt"),
                                     ("clique sur Envoyer dans AtlasEssaiEnvoi", "clics_envoi.txt")):
                r = _resume(_chat(phrase))
                time.sleep(2)
                r["clics_recus"] = _clics(dossier / compteur)
                note("aq1", {"phrase": phrase, **r})
        if "aq3" in parties:
            for i in (1, 2):
                r = _resume(_chat("ferme AtlasEssaiRefus"))
                r["reponse_annuler"] = _confirmer(r["confirmation_id"], False) if r.get("confirmation_id") else None
                r["fenetre_ouverte"] = fen["refus"].poll() is None
                note("aq3", {"lancement": 1, "essai": i, **r})
        if "aq4" in parties:
            r = _resume(_chat("ouvre steam"))
            r["premier_plan"] = "steam" if "steam" in _premier_plan().lower() else "autre"
            note("aq4", {"lancement": 1, "phrase": "ouvre steam", **r})
            r = _resume(_chat("oui"))
            time.sleep(2)
            r["premier_plan"] = "discord" if "discord" in _premier_plan().lower() else "autre"
            note("aq4", {"lancement": 1, "phrase": "oui", **r})
        if "aq5" in parties:
            bloc_notes(1)
            premier_plan_pyw(1)
        res["arrets"].append(atlas.arreter())

        # --- Lancement 2 : après redémarrage ; « le lendemain » pour les habitudes ---
        lendemain()
        atlas = Atlas(racine, env, dossier / "atlas_2.log")
        if "aq3" in parties:
            r = _resume(_chat("ferme AtlasEssaiRefus"))
            r["reponse_confirmer"] = _confirmer(r["confirmation_id"], True) if r.get("confirmation_id") else None
            time.sleep(2)
            r["fenetre_ouverte"] = fen["refus"].poll() is None
            note("aq3", {"lancement": 2, "essai": 3, **r})
        if "aq4" in parties:
            r = _resume(_chat("ouvre steam"))           # Discord ouvert il y a moins de N minutes
            note("aq4", {"lancement": 2, "phrase": "ouvre steam (le lendemain)", **r})
        if "aq5" in parties:
            bloc_notes(2, arreter=True)                 # proposée (Calculatrice), puis « arrête »
            premier_plan_pyw(2)
        res["arrets"].append(atlas.arreter())

        # --- Lancement 3 : encore « le lendemain » : l'habitude écartée reste muette ---
        if "aq4" in parties:
            lendemain()
            atlas = Atlas(racine, env, dossier / "atlas_3.log")
            bloc_notes(3)                               # écartée : plus proposée
            note("aq4", {"lancement": 3, "phrase": "qu'est-ce que tu as appris ?",
                         **_resume(_chat("qu'est-ce que tu as appris ?"))})
            res["arrets"].append(atlas.arreter())
        atlas = None

        # --- Lancement 4 : apprentissage neutralisé ---
        if a.neutralise:
            lendemain()
            atlas = Atlas(racine, {**env, "ATLAS_APPRENTISSAGE": "off"}, dossier / "atlas_4.log")
            if "aq3" in parties:
                fen["refus4"] = _fenetre("AtlasEssaiRefus", 100, 560, "Refus", "#ffffff", "#000000", 14,
                                         dossier / "clics_refus4.txt")
                r = _resume(_chat("ferme AtlasEssaiRefus"))
                r["reponse_annuler"] = _confirmer(r["confirmation_id"], False) if r.get("confirmation_id") else None
                note("aq3", {"lancement": "4 (neutralisé)", "essai": 4, **r})
            if "aq4" in parties:
                note("aq4", {"lancement": "4 (neutralisé)", "phrase": "ouvre steam", **_resume(_chat("ouvre steam"))})
            if "aq5" in parties:
                bloc_notes("4 (neutralisé)")
                premier_plan_pyw("4 (neutralisé)")
            res["arrets"].append(atlas.arreter())
            atlas = None
    finally:
        if atlas:
            res["arrets"].append(atlas.arreter())
        for p in fen.values():
            p.terminate()
        nouveaux = _pids("notepad.exe") - notepad_avant
        for pid in nouveaux:                         # seulement le Bloc-notes ouvert par ce rejeu
            subprocess.run(["taskkill", "/PID", str(pid)], capture_output=True)
        res["bloc_notes_refermes"] = len(nouveaux)
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
        res["journal_d_alexis_inchange"] = _empreinte(journal_alexis) == journal_alexis_avant
        res["apprentissage_db_reel_absent"] = not (DATA / "apprentissage.db").exists()
        try:
            shutil.copy2(travail / "atlas_actions.jsonl", dossier / "journal_copie.jsonl")
        except Exception:
            pass
        import gc

        gc.collect()
        shutil.rmtree(travail, ignore_errors=True)
        shutil.rmtree(gardes, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(f"→ {dossier / 'rejeu.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
