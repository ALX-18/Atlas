"""
Sprint Index des fichiers / IX1.1 — ce que contient le PC (LECTURE SEULE, aucun nom de fichier relevé).

    python scripts/mesure_disques.py --out <fichier.json>

Pour chaque disque fixe : nombre de fichiers et de dossiers parcourus, hors exclusions de la
configuration (`filesystem_assistant.exclude_names`, `exclude_dirs`), nombre et taille des
documents par type, durée du parcours. Priorité basse. Seuls des comptes sortent du script.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _priorite_basse() -> None:
    try:
        import psutil

        psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    _priorite_basse()
    from core import file_indexer as fi

    regles = fi.Exclusions.depuis_config(fi.charger_config())
    res = {"disques": {}, "debut": time.strftime("%Y-%m-%d %H:%M:%S")}
    t_total = time.perf_counter()
    for disque in fi.disques_fixes():
        t0 = time.perf_counter()
        fichiers = dossiers = refus = 0
        docs, octets = Counter(), Counter()
        for dossier, sous, noms in fi.parcourir(disque, regles):
            dossiers += 1
            for nom in noms:
                fichiers += 1
                ext = os.path.splitext(nom)[1].lower()
                if ext in fi.EXTENSIONS_DOCUMENTS:
                    try:
                        octets[ext] += os.stat(os.path.join(dossier, nom)).st_size
                        docs[ext] += 1
                    except OSError:
                        refus += 1
        res["disques"][disque] = {"fichiers": fichiers, "dossiers": dossiers, "documents": dict(docs),
                                  "documents_total": sum(docs.values()),
                                  "documents_octets": sum(octets.values()), "illisibles": refus,
                                  "duree_s": round(time.perf_counter() - t0, 1)}
        print(disque, json.dumps(res["disques"][disque], ensure_ascii=False), flush=True)
    res["duree_totale_s"] = round(time.perf_counter() - t_total, 1)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
