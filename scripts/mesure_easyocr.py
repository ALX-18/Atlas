"""
Sprint Check-up / CK5 — EasyOCR : premier usage, temps d'une lecture, mémoire et VRAM ajoutées.

Mesure le processus OCR d'Atlas (tools/ocr_worker.py) tel qu'Atlas le lance, sur des images
synthétiques (aucune capture de l'écran d'Alexis) : une fenêtre de 460 × 220 et un écran 1920 × 1080.

    python scripts/mesure_easyocr.py --out mesure_cpu.json
    <python d'un venv à torch CUDA> scripts/mesure_easyocr.py --out mesure_gpu.json

Sprint Fiabilité / FI5 : le modèle de langue (qwen2.5:7b) est chargé dans Ollama pendant la
mesure, comme en vrai ; rafales de 10 lectures de fenêtre puis de 10 écrans 1080p ; on relève
si le modèle reste entier sur la carte.

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


def _ollama(chemin: str, corps: dict | None = None, timeout: float = 300) -> dict:
    import urllib.request

    r = urllib.request.Request("http://127.0.0.1:11434" + chemin,
                               data=json.dumps(corps).encode() if corps is not None else None,
                               headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout).read() or b"{}")


def _modele_sur_carte(modele: str) -> dict | None:
    """Le modèle de langue chargé : taille, part en VRAM (Fiabilité / FI5 : reste-t-il entier sur la carte ?)."""
    try:
        for m in _ollama("/api/ps").get("models", []):
            if m.get("name", "").startswith(modele):
                return {"taille_mo": round(m["size"] / 1048576), "en_vram_mo": round(m.get("size_vram", 0) / 1048576),
                        "entier_sur_la_carte": m.get("size_vram", 0) >= m["size"]}
    except Exception as e:
        return {"erreur": str(e)[:120]}
    return None


def _rafale(w, img, n: int) -> dict:
    durees = []
    for _ in range(n):
        t = time.perf_counter()
        w.readtext(img)
        durees.append(round(time.perf_counter() - t, 3))
    trie = sorted(durees)
    return {"durees_s": durees, "mediane_s": trie[len(trie) // 2], "max_s": trie[-1], "total_s": round(sum(durees), 2)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--rafale", type=int, default=10, help="lectures d'affilée (Fiabilité / FI5 : 10)")
    ap.add_argument("--modele", default="qwen2.5:7b",
                    help="modèle de langue chargé dans Ollama pendant la mesure, comme en vrai ('' : aucun)")
    a = ap.parse_args(argv)

    import importlib.metadata as md

    res: dict = {"python": sys.executable, "torch": md.version("torch"), "easyocr": md.version("easyocr")}
    mots = ["Bibliothèque", "Magasin", "Communauté", "Paramètres", "Amis", "Boutique", "Messages privés",
            "Rechercher", "En ligne", "Ajouter un ami", "Profil", "Télécharger"]
    petite = _image(460, 220, mots[:6])
    ecran = _image(1920, 1080, mots * 6)

    if a.modele:
        _ollama("/api/generate", {"model": a.modele, "prompt": "Bonjour", "stream": False, "keep_alive": "15m",
                                  "options": {"num_predict": 1, "num_ctx": 8192}})
        res["modele_avant"] = _modele_sur_carte(a.modele)
    vram_avant = _vram_mo()
    res["vram_machine_avant_mo"] = vram_avant
    from tools.ocr_worker import EasyOCRWorker

    t = time.perf_counter()
    w = EasyOCRWorker()
    res["premier_usage_demarrage_s"] = round(time.perf_counter() - t, 2)
    try:
        t = time.perf_counter()
        lus = w.readtext(petite)
        res["premiere_lecture_fenetre_s"] = round(time.perf_counter() - t, 2)
        res["lu_fenetre"] = [x[1] for x in lus]
        res["rafale_fenetre_460x220"] = _rafale(w, petite, a.rafale)
        res["rss_apres_fenetres_mo"] = _rss_mo(w.pid)
        res["rafale_ecran_1920x1080"] = _rafale(w, ecran, a.rafale)
        res["rss_apres_ecrans_mo"] = _rss_mo(w.pid)
        vram_apres = _vram_mo()
        res["vram_machine_apres_mo"] = vram_apres
        res["vram_ajoutee_mo"] = (vram_apres - vram_avant) if None not in (vram_avant, vram_apres) else None
        if a.modele:
            res["modele_apres"] = _modele_sur_carte(a.modele)
        res["materiel"] = subprocess.run(
            [sys.executable, "-c", "import torch; print('GPU ' + torch.cuda.get_device_name(0) "
                                   "if torch.cuda.is_available() else 'processeur')"],
            capture_output=True, text=True, timeout=120).stdout.strip()
    finally:
        w.stop()
    pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "lu_fenetre"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
