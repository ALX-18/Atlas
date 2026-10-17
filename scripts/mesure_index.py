"""
Sprint Index des fichiers / IX1.3 — l'index d'Atlas sur ce PC : première indexation, ressources,
vitesse de requête. Aucun nom de fichier ne sort du script (comptes, durées, tailles).

    python scripts/mesure_index.py --out <fichier.json> [--base <fichier.db>] [--cpu 25] [--passages 2]

- passage 1 : première indexation (base neuve) ; passage 2 : mise à jour incrémentale (rien ou
  presque n'a changé) ;
- RAM : pointe de la mémoire du processus pendant le passage (relevée 4 fois par seconde) ;
- CPU : temps processeur consommé, et part d'un cœur ;
- disque : taille de la base (et de son journal WAL) ;
- requêtes : nom, contenu, récents — moyenne de 5, mots génériques.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--base", default=None, help="base à mesurer (défaut : celle d'Atlas, data/file_index.db)")
    ap.add_argument("--cpu", type=int, default=None, help="plafond CPU (défaut : la configuration)")
    ap.add_argument("--passages", type=int, default=2)
    a = ap.parse_args(argv)
    import psutil

    from core import file_indexer as fi

    if a.base:
        fi.DB_PATH = Path(a.base)
    proc = psutil.Process()
    idx = fi.FileIndexer()
    if a.cpu is not None:
        idx._cfg = {**idx._cfg, "cpu_max_pourcent": a.cpu}
    res = {"cpu_max_pourcent": idx._cfg.get("cpu_max_pourcent"), "racines": len(fi.racines(idx._cfg)), "passages": []}
    rss_repos = proc.memory_info().rss
    for n in range(1, a.passages + 1):
        pointe = {"rss": proc.memory_info().rss}
        fin_releve = threading.Event()

        def relever():
            while not fin_releve.is_set():
                pointe["rss"] = max(pointe["rss"], proc.memory_info().rss)
                time.sleep(0.25)

        th = threading.Thread(target=relever, daemon=True)
        th.start()
        t_cpu, t0 = proc.cpu_times(), time.perf_counter()
        fin = idx.passage()
        duree = time.perf_counter() - t0
        c = proc.cpu_times()
        fin_releve.set()
        th.join()
        cpu_s = (c.user - t_cpu.user) + (c.system - t_cpu.system)
        res["passages"].append({"passage": n, **fin, "duree_mesuree_s": round(duree, 1), "cpu_s": round(cpu_s, 1),
                                "part_d_un_coeur_pourcent": round(100 * cpu_s / duree, 1) if duree else None,
                                "ram_pointe_mo": round(pointe["rss"] / 2**20), "ram_avant_mo": round(rss_repos / 2**20)})
        print(json.dumps(res["passages"][-1], ensure_ascii=False), flush=True)
    base = Path(fi.DB_PATH)
    res["disque_mo"] = round(sum(p.stat().st_size for p in base.parent.glob(base.name + "*")) / 2**20, 1)
    st = idx.status()
    res["fichiers"], res["documents_lus"] = st.get("count"), st.get("documents_lus")
    mesures = {}
    for nom, f in {"nom (« rapport »)": lambda: fi.chercher_nom("rapport", limite=5),
                   "contenu (« budget »)": lambda: fi.chercher_contenu("budget", limite=5),
                   "récents (7 jours)": lambda: fi.recents(time.time() - 7 * 86400, limite=10)}.items():
        durees, n_res = [], 0
        for _ in range(5):
            t = time.perf_counter()
            n_res = len(f())
            durees.append(time.perf_counter() - t)
        mesures[nom] = {"resultats": n_res, "duree_moyenne_s": round(sum(durees) / 5, 4)}
    res["requetes"] = mesures
    print(json.dumps({k: v for k, v in res.items() if k != "passages"}, ensure_ascii=False), flush=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
