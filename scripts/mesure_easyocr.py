"""
Sprint Check-up / CK5 — EasyOCR : premier usage, temps d'une lecture, mémoire et VRAM ajoutées.

Mesure le processus OCR d'Atlas (tools/ocr_worker.py) tel qu'Atlas le lance, sur des images
synthétiques (aucune capture de l'écran d'Alexis) : une fenêtre de 460 × 220 et un écran 1920 × 1080.

    python scripts/mesure_easyocr.py --out mesure_cpu.json
    <python d'un venv à torch CUDA> scripts/mesure_easyocr.py --out mesure_gpu.json

Le matériel est celui que voit torch dans l'interpréteur qui lance le script. Ne modifie rien.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _image(largeur: int, hauteur: int, lignes: list[str]):
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (largeur, hauteur), (32, 34, 37))          # fond sombre, façon Discord
    d = ImageDraw.Draw(img)
    try:
        police = ImageFont.truetype("segoeui.ttf", 18)
    except Exception:
        police = ImageFont.load_default()
    for i, texte in enumerate(lignes):
        d.text((20 + (i % 3) * (largeur // 3), 20 + (i // 3) * 40), texte, fill=(220, 221, 222), font=police)
    return np.array(img)


def _vram_mo() -> int | None:
    try:
        out = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout
        return int(out.strip().splitlines()[0])
    except Exception:
        return None


def _rss_mo(pid: int) -> int | None:
    try:
        import psutil

        # Le python.exe du venv est un lanceur : le vrai processus est son enfant.
        racine = psutil.Process(pid)
        return round(sum(x.memory_info().rss for x in [racine, *racine.children(recursive=True)]) / 1048576)
    except Exception:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--repetitions", type=int, default=5)
    a = ap.parse_args(argv)

    import importlib.metadata as md

    res: dict = {"python": sys.executable, "torch": md.version("torch"), "easyocr": md.version("easyocr")}
    mots = ["Bibliothèque", "Magasin", "Communauté", "Paramètres", "Amis", "Boutique", "Messages privés",
            "Rechercher", "En ligne", "Ajouter un ami", "Profil", "Télécharger"]
    petite = _image(460, 220, mots[:6])
    ecran = _image(1920, 1080, mots * 6)

    vram_avant = _vram_mo()
    from tools.ocr_worker import EasyOCRWorker

    t = time.perf_counter()
    w = EasyOCRWorker()
    res["premier_usage_demarrage_s"] = round(time.perf_counter() - t, 2)
    try:
        t = time.perf_counter()
        lus = w.readtext(petite)
        res["premiere_lecture_fenetre_s"] = round(time.perf_counter() - t, 2)
        res["lu_fenetre"] = [x[1] for x in lus]
        for nom, img in (("fenetre_460x220", petite), ("ecran_1920x1080", ecran)):
            durees = []
            for _ in range(a.repetitions):
                t = time.perf_counter()
                w.readtext(img)
                durees.append(time.perf_counter() - t)
            durees.sort()
            res[f"lecture_{nom}_mediane_s"] = round(durees[len(durees) // 2], 3)
        res["rss_processus_ocr_mo"] = _rss_mo(w.pid)
        vram_apres = _vram_mo()
        res["vram_ajoutee_mo"] = (vram_apres - vram_avant) if None not in (vram_avant, vram_apres) else None
        res["materiel"] = subprocess.run(
            [sys.executable, "-c", "import torch; print('GPU ' + torch.cuda.get_device_name(0) "
                                   "if torch.cuda.is_available() else 'processeur')"],
            capture_output=True, text=True, timeout=120).stdout.strip()
    finally:
        w.stop()
    pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
