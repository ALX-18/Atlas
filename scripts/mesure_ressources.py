"""
Sprint Performance / PF1 — qui consomme quoi, en mémoire vive (RAM) et vidéo (VRAM).

Rejouable. Ne modifie rien : il lit l'état de la machine, charge des composants dans des
processus jetables, et lance Atlas contre une COPIE de la mémoire (jamais la vraie).

    python scripts/mesure_ressources.py machine     # machine, Ollama, Docker / WSL, hors Atlas
    python scripts/mesure_ressources.py composants  # chaque composant seul, dans son processus
    python scripts/mesure_ressources.py atlas --copie <dossier de la mémoire ou data/ d'une sauvegarde>
    python scripts/mesure_ressources.py tout --copie <...> --out mesure.json

RSS = mémoire vive réellement occupée par le processus (« working set »). « Privée » = ce que
le processus ne partage avec aucun autre. VRAM : nvidia-smi ne donne pas la mémoire par
processus sous Windows (mode WDDM) ; on lit donc la VRAM totale avant et pendant le
chargement de chaque composant, seul. L'écart inclut le bruit des autres applications
(± quelques dizaines de Mo).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

import psutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable
MB = 1024 * 1024


def vram_used_mb() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def vram_total_mb() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def proc_mem(p: psutil.Process) -> dict:
    try:
        mi = p.memory_full_info() if sys.platform == "win32" else p.memory_info()
        return {"rss_mb": round(mi.rss / MB), "privee_mb": round(getattr(mi, "private", getattr(mi, "uss", 0)) / MB)}
    except (psutil.AccessDenied, psutil.NoSuchProcess):
        try:
            return {"rss_mb": round(p.memory_info().rss / MB), "privee_mb": None}
        except Exception:
            return {"rss_mb": None, "privee_mb": None}


def tree_mem(p: psutil.Process) -> dict:
    """Le processus et ses enfants (Atlas lance Tesseract, nvidia-smi…)."""
    total = proc_mem(p)
    for c in p.children(recursive=True):
        m = proc_mem(c)
        total["rss_mb"] = (total["rss_mb"] or 0) + (m["rss_mb"] or 0)
        total["privee_mb"] = (total["privee_mb"] or 0) + (m["privee_mb"] or 0)
    return total


# --------------------------------------------------------------------------- #
#  1. et 3. Machine et services hors Atlas
# --------------------------------------------------------------------------- #

def by_name(names: set[str]) -> list[dict]:
    out = []
    for p in psutil.process_iter(["name"]):
        if (p.info["name"] or "").lower() in names:
            out.append({"nom": p.info["name"], "pid": p.pid, **proc_mem(p)})
    return out


def docker_stats() -> list[dict]:
    """`docker stats --no-stream` : lecture seule."""
    docker = shutil.which("docker")
    if not docker:
        return []
    r = subprocess.run([docker, "stats", "--no-stream", "--format", "{{json .}}"],
                       capture_output=True, text=True, timeout=60)
    rows = []
    for line in r.stdout.splitlines():
        try:
            d = json.loads(line)
            rows.append({"conteneur": d.get("Name"), "memoire": d.get("MemUsage"), "cpu": d.get("CPUPerc")})
        except Exception:
            pass
    return rows


def mesure_machine() -> dict:
    vm = psutil.virtual_memory()
    ollama = by_name({"ollama.exe", "ollama app.exe", "llama-server.exe"})
    wsl = by_name({"vmmem", "vmmem.exe", "vmmemwsl", "vmmemwsl.exe"})
    atlas = [{"pid": p.pid, "cmd": " ".join(p.cmdline()[-2:]), **proc_mem(p)}
             for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == "python.exe"
             and any("main.py" in a or "atlas_desktop" in a for a in _safe_cmdline(p))]
    try:
        ps = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception:
        ps = "indisponible"
    return {
        "ram_totale_mb": round(vm.total / MB), "ram_utilisee_mb": round((vm.total - vm.available) / MB),
        "vram_totale_mb": vram_total_mb(), "vram_utilisee_mb": vram_used_mb(),
        "ollama": ollama, "ollama_ps": ps, "wsl_vmmem": wsl, "docker": docker_stats(),
        "atlas_en_cours": atlas,
    }


def _safe_cmdline(p) -> list[str]:
    try:
        return p.cmdline()
    except Exception:
        return []


# --------------------------------------------------------------------------- #
#  2. Chaque composant isolé, dans un processus propre
# --------------------------------------------------------------------------- #

_WAIT = "import sys; print('PRET', flush=True); sys.stdin.readline()"

COMPOSANTS: dict[str, str] = {
    "python nu": "pass",
    "Atlas sans modèles (import main : FastAPI, cœur, outils)": "import main",
    "fenêtre Atlas (tkinter, module desktop)": "import tkinter as tk; r = tk.Tk(); r.update(); import desktop.atlas_desktop",
    "torch (import seul)": "import torch",
    "embeddings e5-base (sentence-transformers + torch)":
        "from core_conversational.memory_core import embed_query; embed_query('test')",
    "EasyOCR (lecteur fr+en, torch compris)": "import easyocr; easyocr.Reader(['fr', 'en'], verbose=False)",
    "faster-whisper base (GPU)":
        "from core.voice_engine import ensure_cuda_libraries, _load_whisper; ensure_cuda_libraries(); "
        "from faster_whisper import WhisperModel; m = _load_whisper(WhisperModel, 'base', 'cuda')",
    "Piper (voix fr_FR-siwis-medium)":
        "from piper import PiperVoice; v = PiperVoice.load('data/voices/fr_FR-siwis-medium.onnx')",
    "openWakeWord (Hey Atlas)":
        "from openwakeword.model import Model; m = Model(wakeword_models=['models/wakewords/hey_atlas.onnx'], "
        "inference_framework='onnx')",
    "ChromaDB intégré (base jetable vide)":
        "import chromadb, tempfile; c = chromadb.PersistentClient(path=tempfile.mkdtemp()); c.heartbeat()",
}

# Tesseract est un programme à part, lancé à chaque lecture : on mesure son pic.
_TESSERACT = r"""
import json, threading, time, psutil, pytesseract
from PIL import Image, ImageDraw
img = Image.new('RGB', (1600, 900), 'white'); d = ImageDraw.Draw(img)
for i in range(30): d.text((20, 20 + 28 * i), 'Fichier Edition Affichage Bibliothèque Magasin Communauté', fill='black')
peak = [0]; stop = [False]
def watch():
    me = psutil.Process()
    while not stop[0]:
        for c in me.children(recursive=True):
            try: peak[0] = max(peak[0], c.memory_info().rss)
            except Exception: pass
        time.sleep(0.02)
t = threading.Thread(target=watch); t.start()
t0 = time.perf_counter(); pytesseract.image_to_string(img, lang='fra'); dt = time.perf_counter() - t0
stop[0] = True; t.join()
print(json.dumps({'pic_tesseract_mb': round(peak[0] / 1048576), 'duree_s': round(dt, 2)}))
"""


def mesure_composant(nom: str, code: str, timeout: float = 600) -> dict:
    env = {**os.environ, "ATLAS_MEMORY": "off", "PYTHONIOENCODING": "utf-8", "ANONYMIZED_TELEMETRY": "False"}
    vram_avant = vram_used_mb()
    t0 = time.perf_counter()
    p = subprocess.Popen([PY, "-c", f"{code}\n{_WAIT}"], cwd=ROOT, env=env, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
    ligne = ""
    try:
        while time.perf_counter() - t0 < timeout:
            ligne = p.stdout.readline()
            if not ligne or ligne.strip() == "PRET":
                break
        charge_s = round(time.perf_counter() - t0, 1)
        if ligne.strip() != "PRET":
            err = p.stderr.read()[-600:] if p.poll() is not None else "délai dépassé"
            return {"composant": nom, "erreur": err}
        time.sleep(1.5)
        mem = tree_mem(psutil.Process(p.pid))   # le python.exe d un venv est un lanceur : le vrai Python est son enfant
        vram_pendant = vram_used_mb()
        return {"composant": nom, **mem, "chargement_s": charge_s,
                "vram_mb": (vram_pendant - vram_avant) if None not in (vram_avant, vram_pendant) else None}
    finally:
        try:
            p.stdin.write("\n")
            p.stdin.flush()
        except Exception:
            pass
        try:
            p.wait(30)
        except Exception:
            p.kill()


# Cumul : un seul processus charge les composants dans l'ordre d'Atlas ; chaque ligne est ce
# que l'étape AJOUTE. Contrairement à la mesure isolée, rien n'est compté deux fois (Python,
# numpy, onnxruntime, torch partagés) : la somme doit retomber sur Atlas complet au repos.
_CUMUL = r"""
import json, os, sys, time, psutil
me = psutil.Process()
variante, embeddings = sys.argv[1], sys.argv[2]
def rss(): return me.memory_info().rss / 1048576
prec = rss(); out = []
def etape(nom):
    global prec
    time.sleep(1.0); r = rss(); out.append({"etape": nom, "ajout_mb": round(r - prec), "total_mb": round(r)}); prec = r
etape("Python et outils de mesure")
if variante == "avant":
    import torch  # avant ce sprint : importé au démarrage (message GPU) et par ctranslate2
    etape("torch (importé au démarrage)")
import main
etape("Atlas sans modèles (main : FastAPI, cœur, outils, client ChromaDB)")
from core.voice_engine import ensure_cuda_libraries, _load_whisper
ensure_cuda_libraries()
from faster_whisper import WhisperModel
w = _load_whisper(WhisperModel, "base", "cuda")
etape("transcription faster-whisper base (GPU)")
from piper import PiperVoice
p = PiperVoice.load("data/voices/fr_FR-siwis-medium.onnx")
etape("voix Piper")
from openwakeword.model import Model
m = Model(wakeword_models=["models/wakewords/hey_atlas.onnx"], inference_framework="onnx")
etape("mot d'éveil openWakeWord")
import core_conversational.memory_core as mc
mc.set_embedding_backend(embeddings, "models/embeddings/multilingual-e5-base")
mc.embed_query("test")
etape(f"embeddings e5-base ({mc.embedding_backend()})")
out.append({"etape": "— total au repos (sans EasyOCR) —", "total_mb": round(rss())})
import easyocr
r = easyocr.Reader(["fr", "en"], verbose=False)
etape("EasyOCR (au premier clic sur un libellé non trouvé par Tesseract)")
print(json.dumps({"torch_charge": "torch" in sys.modules, "lignes": out}, ensure_ascii=False))
"""


def mesure_cumul(variante: str, embeddings: str) -> dict:
    env = {**os.environ, "ATLAS_MEMORY": "off", "PYTHONIOENCODING": "utf-8", "ANONYMIZED_TELEMETRY": "False"}
    r = subprocess.run([PY, "-c", _CUMUL, variante, embeddings], cwd=ROOT, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=900)
    try:
        res = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"erreur": r.stderr[-800:]}
    for ligne in res["lignes"]:
        print(f"  {ligne}", flush=True)
    return {"variante": variante, "embeddings": embeddings, **res}


def mesure_composants() -> list[dict]:
    rows = []
    for nom, code in COMPOSANTS.items():
        r = mesure_composant(nom, code)
        print(f"  {nom:58} {r}", flush=True)
        rows.append(r)
    t = subprocess.run([PY, "-c", _TESSERACT], cwd=ROOT, capture_output=True, text=True, timeout=300)
    try:
        tess = json.loads(t.stdout.strip().splitlines()[-1])
    except Exception:
        tess = {"erreur": t.stderr[-400:]}
    rows.append({"composant": "Tesseract (programme externe, pendant une lecture d'écran)", **tess})
    print(f"  Tesseract {tess}", flush=True)
    return rows


# --------------------------------------------------------------------------- #
#  4. Atlas complet, en scénarios, contre une COPIE de la mémoire
# --------------------------------------------------------------------------- #

def _get(url, timeout=3):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def _chat(msg, timeout=180):
    req = urllib.request.Request("http://127.0.0.1:8550/api/chat",
                                 data=json.dumps({"message": msg, "history": []}).encode(),
                                 headers={"Content-Type": "application/json"})
    t = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = json.loads(r.read())
    return round(time.perf_counter() - t, 2), (body.get("response") or body.get("message") or "")[:120]


def _wait_http(url, timeout=180) -> bool:
    t = time.perf_counter()
    while time.perf_counter() - t < timeout:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def mesure_atlas(copie: str, duree_melange_s: int = 600) -> dict:
    """Atlas lancé sur une COPIE de la mémoire (ChromaDB intégré, ATLAS_CHROMA_PATH)."""
    work = pathlib.Path(tempfile.mkdtemp(prefix="atlas_mesure_"))
    shutil.copytree(copie, work / "chromadb")
    res: dict = {"copie": str(copie), "scenarios": []}
    atlas = None
    try:
        env = {**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(work / "chromadb"),
               "PYTHONIOENCODING": "utf-8",
               # Apprentissage 2 : jamais le journal d'Alexis ni ce qu'il a appris
               "ATLAS_ACTIONS_LOG": str(work / "atlas_actions.jsonl"),
               "ATLAS_APPRENTISSAGE_DB": str(work / "apprentissage.db"),
               "ATLAS_HABITS_DB": str(work / "habits.db")}
        t0 = time.perf_counter()
        atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, env=env, stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        if not _wait_http("http://127.0.0.1:8550/api/health", 300):
            res["erreur"] = "Atlas injoignable"
            return res
        res["demarrage_s"] = round(time.perf_counter() - t0, 1)
        proc = psutil.Process(atlas.pid)

        def point(nom, extra=None):
            time.sleep(3)
            row = {"scenario": nom, **tree_mem(proc), "vram_mb": vram_used_mb(), **(extra or {})}
            res["scenarios"].append(row)
            print(f"  {row}", flush=True)

        time.sleep(20)
        point("au repos après démarrage")
        dt, rep = _chat("quelle est la capitale de l'Italie ?")
        point("après une demande écrite", {"duree_s": dt, "reponse": rep})
        dt, rep = _chat("tu te souviens de ce que je t'ai demandé sur Steam ?")
        point("après un rappel mémoire", {"duree_s": dt, "reponse": rep})

        # Clic sur un libellé : dans une fenêtre créée ici, jamais une fenêtre d'Alexis.
        tk = subprocess.Popen([PY, "-c", "import tkinter as t; r = t.Tk(); r.title('AtlasEssaiOCR'); "
                               "r.geometry('420x200+300+300'); t.Label(r, text='Bibliothèque', font=('Segoe UI', 20)).pack(pady=50); "
                               "r.mainloop()"])
        time.sleep(3)
        try:
            dt, rep = _chat("clique sur Bibliothèque dans AtlasEssaiOCR")
            point("après un clic sur un libellé (OCR)", {"duree_s": dt, "reponse": rep})
        finally:
            tk.terminate()

        # Pic sur un usage mêlé
        demandes = ["quelle est la capitale de l'Italie ?", "liste les fenêtres", "combien font 12 fois 8 ?",
                    "tu peux faire quoi ?", "explique-moi la photosynthèse en une phrase",
                    "que sais-tu faire avec les fenêtres ?", "tu te souviens de Discord ?"]
        pic = {"rss_mb": 0, "privee_mb": 0}
        vram_pic = 0
        debut, i = time.perf_counter(), 0
        while time.perf_counter() - debut < duree_melange_s:
            try:
                _chat(demandes[i % len(demandes)])
            except Exception:
                pass
            i += 1
            m = tree_mem(proc)
            pic = {k: max(pic[k], m[k] or 0) for k in pic}
            vram_pic = max(vram_pic, vram_used_mb() or 0)
            time.sleep(5)
        res["scenarios"].append({"scenario": f"pic sur {duree_melange_s // 60} min d'usage mêlé ({i} demandes)",
                                 **pic, "vram_mb": vram_pic})
        print(f"  pic {pic} vram {vram_pic}", flush=True)
        res["machine_pendant"] = mesure_machine()
        return res
    finally:
        if atlas is not None:
            atlas.terminate()
            try:
                atlas.wait(20)
            except Exception:
                atlas.kill()
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("quoi", choices=["machine", "composants", "cumul", "atlas", "tout"])
    ap.add_argument("--variante", choices=["avant", "apres"], default="apres", help="cumul : torch au démarrage (avant)")
    ap.add_argument("--embeddings", choices=["sentence-transformers", "onnx"], default="sentence-transformers")
    ap.add_argument("--copie", help="dossier data/ d'une sauvegarde (copié, jamais modifié)")
    ap.add_argument("--duree", type=int, default=600, help="durée de l'usage mêlé, en secondes")
    ap.add_argument("--out", help="fichier JSON de sortie")
    a = ap.parse_args(argv)
    out: dict = {"date": time.strftime("%Y-%m-%d %H:%M:%S")}
    if a.quoi in ("machine", "tout"):
        out["machine"] = mesure_machine()
        print(json.dumps(out["machine"], ensure_ascii=False, indent=1))
    if a.quoi in ("composants", "tout"):
        out["composants"] = mesure_composants()
    if a.quoi == "cumul":
        out["cumul"] = mesure_cumul(a.variante, a.embeddings)
    if a.quoi in ("atlas", "tout"):
        if not a.copie:
            ap.error("--copie est obligatoire : Atlas n'est jamais mesuré sur la mémoire réelle")
        out["atlas"] = mesure_atlas(a.copie, a.duree)
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
