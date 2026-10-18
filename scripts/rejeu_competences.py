"""
Sprint Compétences 1 / CP9 — rejeu réel par Atlas, Alexis présent (le son, les écrans, la musique
se voient ou s'entendent).

    python scripts/rejeu_competences.py --out <dossier> [--etapes heure,rappels,son,lumiere,veille,bluetooth,musique]

Atlas réel démarre sur des COPIES (mémoire, apprentissage, journal, habitudes, rappels : jetables).
Pour chaque action, ce script RELIT lui-même l'état de la machine (volume, luminosité DDC/CI, session
multimédia), indépendamment d'Atlas, et le compare à ce qu'Atlas a annoncé.

- heure : réponse comparée à l'horloge du système ;
- rappels : minuteur de 1 minute (annonce relevée), puis un rappel dans 1 minute, Atlas ARRÊTÉ avant
  l'heure et redémarré après : le rappel manqué doit être annoncé au démarrage ;
- son : 20 %, +pas, couper, rétablir, programme ; volume et sourdine d'origine remis à la fin ;
- lumière : 50 % puis +pas sur chaque écran qui accepte ; luminosités d'origine remises à la fin ;
- veille : « éteins l'écran » (Alexis regarde ; rien à relire) ;
- bluetooth : état ; « désactive le bluetooth » seulement si Alexis l'a accepté (--bluetooth-ok) ;
- musique : pause, lecture, suivant, « qu'est-ce qui passe ? », puis la recherche par chaque service.
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from checkup_dynamique import API, DATA, PY, ROOT, attendre, req  # noqa: E402


def _get(chemin: str) -> dict:
    with urllib.request.urlopen(API + chemin, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


class Atlas:
    def __init__(self, travail: pathlib.Path, journal: pathlib.Path):
        self.env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8",
                    "ATLAS_CHROMA_PATH": str(travail / "chromadb"),
                    "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
                    "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl"),
                    "ATLAS_HABITS_DB": str(travail / "habits.db"), "ATLAS_RAPPELS_DB": str(travail / "rappels.db")}
        self.journal_chemin, self.proc, self.journal = journal, None, None

    def demarrer(self):
        self.journal = open(self.journal_chemin, "a", encoding="utf-8")
        self.proc = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=self.journal, stderr=subprocess.STDOUT,
                                     env=self.env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")

    def arreter(self) -> str:
        try:
            os.kill(self.proc.pid, signal.CTRL_BREAK_EVENT)
            self.proc.wait(60)
            issue = "propre"
        except Exception as e:
            self.proc.kill()
            issue = f"forcé ({e!r})"
        self.journal.close()
        return issue


def chat(phrase: str) -> dict:
    out, s = req("/chat", {"message": phrase, "history": [], "origine": "fenetre"})
    return {"phrase": phrase, "reponse": out.get("message") or "", "type": out.get("type"), "s": s,
            "confirmation_id": out.get("confirmation_id")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--etapes", default="heure,rappels,son,lumiere,veille,bluetooth,musique")
    ap.add_argument("--bluetooth-ok", action="store_true", help="Alexis a accepté qu'on coupe le Bluetooth")
    ap.add_argument("--recherche", default="Daft Punk")
    a = ap.parse_args(argv)
    etapes = a.etapes.split(",")
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    from core import horloge
    from tools import affichage, bluetooth, musique, son

    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_cp_"))
    shutil.copytree(DATA / "chromadb", travail / "chromadb", ignore=shutil.ignore_patterns("*.lock"))
    if (DATA / "habits.db").exists():
        shutil.copy2(DATA / "habits.db", travail / "habits.db")
    res: dict = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "etapes": {}}
    origine = {"son": son.etat(), "ecrans": affichage.ecrans()}
    res["etat_d_origine"] = origine
    atlas = Atlas(travail, dossier / "atlas.log")

    def noter(etape, ligne):
        res["etapes"].setdefault(etape, []).append(ligne)
        print(etape, json.dumps(ligne, ensure_ascii=False)[:400], flush=True)

    try:
        atlas.demarrer()
        if "heure" in etapes:
            for p in ("quelle heure est-il ?", "on est quel jour ?", "quelle date dans 3 semaines ?"):
                r = chat(p)
                r["horloge_systeme"] = horloge.heure_fr(horloge.maintenant()) + " — " + horloge.date_fr(horloge.maintenant().date())
                noter("heure", r)

        if "rappels" in etapes:
            _get("/annonces")
            t0 = time.monotonic()
            noter("rappels", chat("mets un minuteur de 1 minute"))
            annonce = None
            while time.monotonic() - t0 < 120 and not annonce:
                time.sleep(1)
                annonce = (_get("/annonces").get("annonces") or [None])[0]
            noter("rappels", {"annonce": annonce, "apres_s": round(time.monotonic() - t0, 1)})
            r = chat("rappelle-moi dans 1 minute de vérifier le rejeu AtlasEssai")
            noter("rappels", r)
            noter("rappels", chat("quels sont mes rappels ?"))
            noter("rappels", {"arret_avant_l_heure": atlas.arreter()})
            time.sleep(150)                                   # le rappel tombe pendant qu'Atlas est éteint
            atlas.demarrer()
            time.sleep(5)
            noter("rappels", {"au_redemarrage": _get("/annonces").get("annonces")})

        if "son" in etapes:
            for p in ("mets le son à 20 %", "monte le son", "baisse le volume", "coupe le son", "remets le son"):
                r = chat(p)
                r["relu_par_le_rejeu"] = son.etat()
                noter("son", r)
            progs = son.MATERIEL.programmes()
            if progs:
                nom = progs[0]["processus"].removesuffix(".exe")
                avant = progs[0]["niveau"]
                r = chat(f"baisse le son de {nom}")
                r["relu_par_le_rejeu"] = [p for p in son.MATERIEL.programmes() if p["processus"] == progs[0]["processus"]]
                noter("son", r)
                for p in son.MATERIEL.programmes():
                    if p["processus"] == progs[0]["processus"]:
                        son.MATERIEL.regler_programme(p["pid"], niveau=avant)
            noter("son", chat("baisse le son de ta voix"))

        if "lumiere" in etapes:
            for p in ("mets la luminosité à 50 %", "augmente la luminosité", "quelle est la luminosité ?"):
                r = chat(p)
                r["relu_par_le_rejeu"] = [(e["nom"], e["niveau"]) for e in affichage.ecrans()]
                noter("lumiere", r)

        if "veille" in etapes:
            print("\n>>> Les écrans vont se mettre en veille dans une seconde. Bouge la souris après 5 s.\n", flush=True)
            r = chat("éteins l'écran")
            noter("veille", r)
            time.sleep(8)

        if "bluetooth" in etapes:
            noter("bluetooth", chat("est-ce que le bluetooth est activé ?"))
            noter("bluetooth", {"etat_relu_par_le_rejeu": bluetooth.diagnostic()})
            if a.bluetooth_ok:
                r = chat("désactive le bluetooth")
                noter("bluetooth", r)
                if r.get("confirmation_id"):
                    noter("bluetooth", {"confirmation": "laissée à Alexis (non acceptée par le script)"})
                noter("bluetooth", chat("active le bluetooth"))
            noter("bluetooth", chat("connecte mon casque"))

        if "musique" in etapes:
            for p in ("qu'est-ce qui passe ?", "mets la musique en pause", "reprends la musique",
                      "passe à la chanson suivante", "chanson précédente"):
                r = chat(p)
                try:
                    r["relu_par_le_rejeu"] = musique.MATERIEL.courante()
                except Exception as e:
                    r["relu_par_le_rejeu"] = repr(e)
                noter("musique", r)
            noter("musique", chat(f"mets du {a.recherche}"))           # la question du service
            noter("musique", chat("Spotify"))
            for service in ("Deezer", "Apple Music", "YouTube Music"):
                time.sleep(6)
                r = chat(f"mets du {a.recherche} sur {service}")
                time.sleep(6)
                try:
                    r["sessions_apres_6s"] = musique.MATERIEL.sessions()
                except Exception as e:
                    r["sessions_apres_6s"] = repr(e)
                noter("musique", r)
    finally:
        try:
            res["arret"] = atlas.arreter()
        except Exception as e:
            res["arret"] = repr(e)
        # Remettre ce qui a été changé : volume, sourdine, luminosités
        try:
            son.MATERIEL.regler_general(origine["son"]["niveau"], origine["son"]["muet"])
            res["son_remis"] = son.etat()
        except Exception as e:
            res["son_remis"] = repr(e)
        try:
            for e in origine["ecrans"]:
                if e["methode"] == "ddc" and e["niveau"] is not None:
                    affichage.MATERIEL.ddc_regler(e["rang"], e["niveau"])
                elif e["methode"] == "wmi" and e["niveau"] is not None:
                    affichage.MATERIEL.wmi_regler(e["niveau"])
            time.sleep(1)
            res["ecrans_remis"] = [(e["nom"], e["niveau"]) for e in affichage.ecrans()]
        except Exception as e:
            res["ecrans_remis"] = repr(e)
        shutil.rmtree(travail, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
