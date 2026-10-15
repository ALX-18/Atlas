"""
Sprint Check-up / CK1 — mesure dynamique : Atlas réel, sur une COPIE de la mémoire, à travers un
jeu de scénarios qui couvre toutes les familles d'outils. On relève, pour chaque processus
(Atlas, processus OCR, Ollama), les DLL chargées et les modules Python (ATLAS_MODULES_DUMP).

    python scripts/checkup_dynamique.py --out <dossier>

Garde-fous :
- refuse si Atlas tourne déjà (port 8550 occupé) ;
- la mémoire est une copie jetable (ATLAS_CHROMA_PATH) ; la vraie n'est jamais ouverte ;
- seules des fenêtres créées ici (titres « AtlasEssai… ») sont visées ;
- toute action à confirmer (fermer, lancer un mode, planifier) est ANNULÉE ;
- schedules.json, triggers.json, workflows/, habits.db, file_index.json : empreinte avant/après,
  remis tels quels s'ils ont bougé (traces de mes essais, règle C3), et listés dans le résultat ;
- arrêt PROPRE d'Atlas (Ctrl+Pause sur son groupe de processus) pour que la fermeture écrive la
  liste des modules.

Partie voix (« par fichier audio », Alexis absent) : après l'arrêt d'Atlas, un second processus
synthétise une phrase avec la voix d'Atlas (Piper), la fait transcrire par la chaîne d'Atlas
(faster-whisper), la passe au pipeline vocal, puis prononce la réponse.
"""

from __future__ import annotations

import argparse
import hashlib
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

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
API = "http://127.0.0.1:8550/api"
DATA = ROOT / "data"
def copies_journal_et_apprentissage(copie: pathlib.Path) -> dict:
    """Apprentissage 2 : un Atlas d'essai écrit son journal des actions et ce qu'il apprend à côté de
    la copie de la mémoire — jamais dans data/ (le journal d'Alexis est la source de ses habitudes)."""
    return {"ATLAS_ACTIONS_LOG": str(pathlib.Path(copie).parent / "atlas_actions.jsonl"),
            "ATLAS_APPRENTISSAGE_DB": str(pathlib.Path(copie).parent / "apprentissage.db")}


PROTEGES = ["schedules.json", "triggers.json", "workflows", "habits.db", "file_index.json"]


# --------------------------------------------------------------------------- #
#  Outils
# --------------------------------------------------------------------------- #

def _empreinte(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    fichiers = sorted(p.rglob("*")) if p.is_dir() else [p]
    for f in fichiers:
        if f.is_file():
            h.update(str(f.relative_to(DATA)).encode())
            h.update(f.read_bytes())
    return h.hexdigest() if p.exists() else "absent"


def req(path: str, body=None, timeout=240):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    out = json.loads(urllib.request.urlopen(r, timeout=timeout).read() or b"{}")
    return out, round(time.perf_counter() - t, 2)


def attendre(url: str, timeout=300) -> bool:
    t = time.perf_counter()
    while time.perf_counter() - t < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def dlls(p) -> list[str]:
    try:
        return sorted({m.path for m in p.memory_maps() if m.path.lower().endswith((".dll", ".pyd", ".exe"))})
    except Exception as e:
        return [f"illisible: {type(e).__name__}"]


def fenetre(nom: str, code_tk: str, x: int):
    # Positions distinctes : une fenêtre de test ne doit pas en recouvrir une autre (l'OCR lit l'écran)
    p = subprocess.Popen([PY, "-c", "import tkinter as t, pathlib, sys\nr = t.Tk(); r.title(%r)\n"
                          "r.geometry('460x220+%d+300'); r.attributes('-topmost', True)\n" % (nom, x) + code_tk
                          + "\nr.mainloop()"])
    time.sleep(3)
    return p


# --------------------------------------------------------------------------- #
#  Scénarios (famille, phrase, ce qui est attendu)
# --------------------------------------------------------------------------- #

SCENARIOS = [
    ("écrit", "tu peux faire quoi ?", "réponse fixe, depuis le registre"),
    ("écrit", "quelle est la capitale de l'Italie ?", "conversation, Ollama"),
    ("rappel", "tu te souviens de Discord ?", "rappel, embeddings + base intégrée"),
    ("rappel", "retiens que mon essai de check-up porte le numéro 7", "écrit dans la COPIE"),
    ("rappel", "quel est le numéro de mon essai de check-up ?", "rappel de ce qui vient d'être retenu"),
    ("recherche", "cherche sur internet la météo à Paris", "DuckDuckGo"),
    ("recherche", "résume la page https://example.com", "lecture d'une page (phrasé naturel)"),
    ("recherche", "lis https://example.com", "lecture d'une page"),
    ("système", "quel est l'état de mon ordinateur ?", "diagnostic"),
    ("système", "liste les programmes en cours", "processus (phrasé naturel)"),
    ("système", "liste les processus", "processus"),
    ("fenêtres", "liste les fenêtres ouvertes", "liste"),
    ("fenêtres", "restaure AtlasEssaiRestaure", "restaurée"),
    ("fenêtres", "ferme AtlasEssaiRestaure", "confirmation, ANNULÉE"),
    ("ocr_tesseract", "clique sur Bibliothèque dans AtlasEssaiOCR", "clic par Tesseract"),
    ("ocr_easyocr", "clique sur Introuvable dans AtlasEssaiOCR", "Tesseract échoue → EasyOCR lancé"),
    ("fenêtres", "mets AtlasEssaiOCR au premier plan", "premier plan"),
    ("écran", "lis l'écran", "lecture d'écran (fenêtre de premier plan)"),
    ("saisie", "écris bonjour checkup dans AtlasEssaiSaisie", "texte arrivé dans ma fenêtre"),
    ("modes", "il consiste à quoi le mode gaming ?", "décrit, rien lancé"),
    ("modes", "lance le mode travail", "confirmation, ANNULÉE"),
    ("planification", "liste mes tâches planifiées", "liste (phrasé naturel)"),
    ("planification", "liste les tâches planifiées", "liste"),
    ("planification", "rappelle-moi de boire de l'eau tous les jours à 15h", "confirmation (phrasé naturel)"),
    ("planification", "planifie de boire de l'eau tous les jours à 15h", "confirmation, ANNULÉE"),
    ("applications", "ouvre la calculatrice", "lancée (fermée ensuite)"),
]


def _fenetres(titre: str) -> set:
    import win32gui

    vues = set()
    win32gui.EnumWindows(lambda h, _: vues.add(h) if win32gui.GetWindowText(h) == titre else None, None)
    return vues


def _annuler_confirmations() -> int:
    pend, _ = req("/confirmations")
    n = 0
    for c in pend.get("pending") or []:
        cid = c.get("confirmation_id") or c.get("id")
        if cid:
            req("/confirm", {"confirmation_id": cid, "accepted": False})
            n += 1
    return n


def _resume(out: dict) -> str:
    texte = out.get("message") or ""
    tr = out.get("tool_results") or []
    if tr:
        texte += " | " + json.dumps(tr, ensure_ascii=False, default=str)[:500]
    return texte[:700]


def phase_atlas(dossier: pathlib.Path, copie: pathlib.Path) -> dict:
    import psutil
    import win32con
    import win32gui

    res: dict = {"scenarios": [], "processus": {}}
    saisie_fichier = dossier / "saisie.txt"
    fen = [
        fenetre("AtlasEssaiRestaure", "", 20),
        fenetre("AtlasEssaiOCR", "t.Label(r, text='Bibliothèque', font=('Segoe UI', 20)).pack(pady=50)", 520),
        fenetre("AtlasEssaiSaisie",
                "e = t.Text(r, font=('Segoe UI', 14)); e.pack(fill='both', expand=True); e.focus_set()\n"
                f"f = pathlib.Path({str(saisie_fichier)!r})\n"
                "def s():\n    f.write_text(e.get('1.0', 'end'), encoding='utf-8'); r.after(300, s)\n"
                "r.after(300, s)", 1020),
    ]
    dump = dossier / "modules_atlas.json"
    env = {**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(copie),
           "ATLAS_MODULES_DUMP": str(dump), "PYTHONIOENCODING": "utf-8", **copies_journal_et_apprentissage(copie)}
    journal = open(dossier / "atlas_stdout.log", "w", encoding="utf-8")
    t0 = time.perf_counter()
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu en 300 s")
        res["api_prete_s"] = round(time.perf_counter() - t0, 1)
        time.sleep(15)
        res["health_depart"], _ = req("/health")

        racine = psutil.Process(atlas.pid)
        vrai = [c for c in racine.children() if "main.py" in " ".join(c.cmdline())] or [racine]
        proc_atlas = vrai[0]

        for famille, phrase, attendu in SCENARIOS:
            if phrase.startswith("restaure"):
                h = win32gui.FindWindow(None, "AtlasEssaiRestaure")
                win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
                time.sleep(1)
            if famille == "applications":
                calc_avant = _fenetres("Calculatrice")
            try:
                out, dt = req("/chat", {"message": phrase, "history": []})
                ligne = {"famille": famille, "phrase": phrase, "attendu": attendu, "duree_s": dt,
                         "obtenu": _resume(out)}
            except Exception as e:
                ligne = {"famille": famille, "phrase": phrase, "attendu": attendu, "erreur": repr(e)[:300]}
            ligne["confirmations_annulees"] = _annuler_confirmations()
            if famille == "saisie":
                time.sleep(1)
                ligne["texte_recu"] = saisie_fichier.read_text(encoding="utf-8").strip() \
                    if saisie_fichier.exists() else None
            if famille == "applications":
                time.sleep(8)
                nouvelles = _fenetres("Calculatrice") - calc_avant
                ligne["calculatrices_ouvertes_par_atlas"] = len(nouvelles)
                for h in nouvelles:       # seulement celles ouvertes par ce scénario
                    win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
            res["scenarios"].append(ligne)
            print(json.dumps(ligne, ensure_ascii=False)[:400], flush=True)

        # Le flux (/chat/stream), utilisé par la fenêtre Atlas
        r = urllib.request.Request(API + "/chat/stream", data=json.dumps(
            {"message": "dis bonjour en trois mots", "history": []}).encode(),
            headers={"Content-Type": "application/json"})
        t = time.perf_counter()
        corps = urllib.request.urlopen(r, timeout=240).read().decode("utf-8", "replace")
        res["scenarios"].append({"famille": "écrit (flux)", "phrase": "dis bonjour en trois mots",
                                 "duree_s": round(time.perf_counter() - t, 2), "obtenu": corps[:300]})
        res["health_fin"], _ = req("/health")

        # DLL de chaque processus, pendant qu'ils tournent
        res["processus"]["atlas"] = {"pid": proc_atlas.pid, "dll": dlls(proc_atlas),
                                     "rss_mo": round(proc_atlas.memory_info().rss / 1048576)}
        for c in proc_atlas.children(recursive=True):
            cmd = " ".join(c.cmdline())
            nom = "ocr_worker" if "ocr_worker" in cmd else f"enfant_{c.name()}"
            res["processus"][nom] = {"pid": c.pid, "cmd": cmd[:200], "dll": dlls(c),
                                     "rss_mo": round(c.memory_info().rss / 1048576)}
        for p in psutil.process_iter(["name", "exe"]):
            n = (p.info["name"] or "").lower()
            if "ollama" in n or "llama" in n:
                res["processus"][f"ollama:{n}:{p.pid}"] = {"pid": p.pid, "exe": p.info["exe"], "dll": dlls(p),
                                                          "rss_mo": round(p.memory_info().rss / 1048576)}
        try:
            res["nvidia_smi"] = subprocess.run(
                ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=20).stdout.strip().splitlines()
        except Exception as e:
            res["nvidia_smi"] = [repr(e)]
    finally:
        # Arrêt propre : Ctrl+Pause sur le groupe → uvicorn exécute la fermeture (lifespan)
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
    time.sleep(3)
    for f in sorted(dossier.glob("modules_atlas*.json")):
        res.setdefault("dumps", []).append(f.name)
    return res


# --------------------------------------------------------------------------- #
#  Voix par fichier audio (processus séparé, Atlas arrêté, même copie)
# --------------------------------------------------------------------------- #

VOIX = r'''
import asyncio, io, json, os, sys, time, wave, pathlib
import numpy as np
sys.path.insert(0, os.getcwd())
import main  # noqa: F401 — démarre comme Atlas : ctranslate2 importé sans torch, configuration, journal
from core.voice_engine import VoiceEngine
out = {}
ve = VoiceEngine()
from piper import PiperVoice
voix = PiperVoice.load(str(pathlib.Path("data/voices") / (ve._config.get("tts_voice", "fr_FR-siwis-medium") + ".onnx")))
buf = io.BytesIO()
with wave.open(buf, "wb") as w:
    voix.synthesize_wav("Quelle est la capitale de l'Espagne ?", w)
buf.seek(0)
with wave.open(buf, "rb") as w:
    sr = w.getframerate(); pcm = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
x = np.interp(np.arange(0, len(pcm), sr / 16000), np.arange(len(pcm)), pcm).astype(np.int16)
pathlib.Path(sys.argv[1]).with_name("voix_phrase.wav").write_bytes(buf.getvalue())
t = time.perf_counter(); texte = asyncio.run(ve._transcribe(x.tobytes())); out["transcription"] = texte
out["transcription_s"] = round(time.perf_counter() - t, 2); out["stt"] = ve.stt_status()
t = time.perf_counter(); rep = asyncio.run(ve._run_text_pipeline(texte)); out["reponse"] = rep
out["pipeline_s"] = round(time.perf_counter() - t, 2)
t = time.perf_counter(); out["parle"] = ve._speak_sync(rep); out["tts_s"] = round(time.perf_counter() - t, 2)
out["tts"] = ve.tts_status()
import psutil
p = psutil.Process()
out["dll"] = sorted({m.path for m in p.memory_maps() if m.path.lower().endswith((".dll", ".pyd"))})
out["modules"] = sorted(sys.modules)
pathlib.Path(sys.argv[1]).write_text(json.dumps(out, ensure_ascii=False, default=str), encoding="utf-8")
'''


def phase_voix(dossier: pathlib.Path, copie: pathlib.Path) -> dict:
    sortie = dossier / "voix.json"
    env = {**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(copie), "PYTHONIOENCODING": "utf-8",
           **copies_journal_et_apprentissage(copie)}
    r = subprocess.run([PY, "-c", VOIX, str(sortie)], cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", timeout=600)
    if not sortie.exists():
        return {"erreur": r.stderr[-1500:]}
    d = json.loads(sortie.read_text(encoding="utf-8"))
    (dossier / "modules_voix.json").write_text(json.dumps({"processus": "voix", "modules": d.pop("modules")}),
                                               encoding="utf-8")
    return d


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--sans-voix", action="store_true")
    a = ap.parse_args(argv)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550). Rien n'est lancé.")
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)

    avant = {n: _empreinte(DATA / n) for n in PROTEGES}
    gardes = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ck1_garde_"))
    for n in PROTEGES:
        src = DATA / n
        if src.is_dir():
            shutil.copytree(src, gardes / n)
        elif src.exists():
            shutil.copy2(src, gardes / n)

    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_ck1_"))
    copie = travail / "chromadb"
    shutil.copytree(DATA / "chromadb", copie)
    res = {"debut": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        res["atlas"] = phase_atlas(dossier, copie)
        if not a.sans_voix:
            res["voix"] = phase_voix(dossier, copie)
    finally:
        res["fin"] = time.strftime("%Y-%m-%d %H:%M:%S")
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
        (dossier / "dynamique.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str),
                                                encoding="utf-8")
    print(f"→ {dossier / 'dynamique.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
