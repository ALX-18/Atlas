"""
Sprint Performance / PF4 — prototype SANS Docker, mesure seulement : rien n'est migré.

1. ChromaDB intégré (PersistentClient, dans le processus) sur une COPIE de la mémoire, comparé
   au ChromaDB actuel dans Docker. Les 40 requêtes de scripts/garde_fou_rappels.py sont
   vectorisées UNE fois, puis jouées des deux côtés avec les mêmes vecteurs : seul l'accès
   change. Côté Docker, la mémoire réelle n'est QUE lue (requêtes) ; les écritures ne sont
   mesurées que sur la copie.
2. Recherche web : 15 recherches réelles, SearXNG (Docker) contre DuckDuckGo (repli actuel).

    python scripts/prototype_sans_docker.py chroma --copie <data/ d'une sauvegarde> --out c.json
    python scripts/prototype_sans_docker.py web --out w.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import shutil
import statistics as st
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from garde_fou_rappels import COLLECTIONS, REQUETES  # noqa: E402

_INTEGRE = r"""
import json, sys, time, statistics as st, psutil, uuid
me = psutil.Process(); r0 = me.memory_info().rss
t0 = time.perf_counter()
import chromadb
client = chromadb.PersistentClient(path=sys.argv[1])
cols = {n: client.get_collection(n) for n in sys.argv[3].split(",")}
vecs = json.load(open(sys.argv[2], encoding="utf-8"))
first = None; durees = []; out = []
for q, v in vecs.items():
    t = time.perf_counter(); ligne = {"requete": q}
    for n, c in cols.items():
        r = c.query(query_embeddings=[v], n_results=min(10, c.count() or 1))
        ligne[n] = [[i, round(float(d), 6)] for i, d in zip(r["ids"][0], r["distances"][0])]
    d = time.perf_counter() - t
    if first is None: first = time.perf_counter() - t0
    durees.append(d); out.append(ligne)
tmp = client.get_or_create_collection("mesure_ecriture_jetable", metadata={"hnsw:space": "cosine"})
ecr = []
for v in list(vecs.values())[:10]:
    t = time.perf_counter(); tmp.add(ids=[uuid.uuid4().hex], embeddings=[v], documents=["mesure"]); ecr.append(time.perf_counter() - t)
time.sleep(1)
print(json.dumps({"ouverture_et_premiere_requete_s": round(first, 2), "rappel_ms_median": round(1000 * st.median(durees), 1),
                  "ecriture_ms_median": round(1000 * st.median(ecr), 1), "ram_ajoutee_mb": round((me.memory_info().rss - r0) / 1048576),
                  "requetes": out}))
"""


def _vecteurs(path: pathlib.Path) -> None:
    import core_conversational.memory_core as mc

    mc.set_embedding_backend("sentence-transformers")
    path.write_text(json.dumps({q: mc.embed_query(q) for q in REQUETES}), encoding="utf-8")


def chroma(copie: str) -> dict:
    work = pathlib.Path(tempfile.mkdtemp(prefix="atlas_sans_docker_"))
    try:
        shutil.copytree(copie, work / "data")
        vec_path = work / "vecteurs.json"
        _vecteurs(vec_path)
        vecs = json.loads(vec_path.read_text(encoding="utf-8"))

        # Intégré, dans un processus propre (RAM ajoutée par chromadb + la base ouverte)
        r = subprocess.run([sys.executable, "-c", _INTEGRE, str(work / "data"), str(vec_path), ",".join(COLLECTIONS)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                           env={**os.environ, "ANONYMIZED_TELEMETRY": "False"})
        integre = json.loads(r.stdout.strip().splitlines()[-1])

        # Docker : la mémoire réelle, en lecture seule (requêtes)
        import chromadb

        client = chromadb.HttpClient(host="localhost", port=8001)
        t0 = time.perf_counter()
        cols = {n: client.get_collection(n) for n in COLLECTIONS}
        durees, out, first = [], [], None
        for q, v in vecs.items():
            t = time.perf_counter()
            ligne = {"requete": q}
            for n, c in cols.items():
                rr = c.query(query_embeddings=[v], n_results=min(10, c.count() or 1))
                ligne[n] = [[i, round(float(d), 6)] for i, d in zip(rr["ids"][0], rr["distances"][0])]
            durees.append(time.perf_counter() - t)
            first = first or (time.perf_counter() - t0)
            out.append(ligne)
        docker = {"ouverture_et_premiere_requete_s": round(first, 2), "rappel_ms_median": round(1000 * st.median(durees), 1),
                  "requetes": out}

        from garde_fou_rappels import compare

        comp = compare({"requetes": docker["requetes"]}, {"requetes": integre["requetes"]})
        for d in (docker, integre):
            d.pop("requetes")
        return {"docker_memoire_reelle_lecture": docker, "integre_copie": integre, "comparaison": comp}
    finally:
        shutil.rmtree(work, ignore_errors=True)


WEB = ["météo Paris", "horaires mairie Lyon", "recette crêpes", "prix RTX 5060", "Ollama 0.40 nouveautés",
       "résultats Ligue 1", "comment réinitialiser Windows 11", "capitale de l'Australie", "définition photosynthèse",
       "Steam soldes octobre", "Discord bot python", "taux de change euro dollar", "film sorti cette semaine",
       "traduction bonjour en japonais", "Helldivers 2 mise à jour"]


def web() -> dict:
    import tools.web_search as ws

    async def run():
        rows = []
        for q in WEB:
            row = {"requete": q}
            for nom, fn in (("searxng", ws._search_searxng), ("duckduckgo", ws._search_duckduckgo)):
                t = time.perf_counter()
                try:
                    res = await fn(q, 5)
                    row[nom] = {"n": len(res), "s": round(time.perf_counter() - t, 2),
                                "titres": [r.get("title", "")[:70] for r in res[:3]],
                                "urls": [r.get("url", "") for r in res[:5]]}
                except Exception as e:
                    row[nom] = {"n": 0, "s": round(time.perf_counter() - t, 2), "erreur": str(e)[:120]}
                await asyncio.sleep(1.0)
            a = set(row["searxng"].get("urls", []))
            b = set(row["duckduckgo"].get("urls", []))
            row["urls_communes_top5"] = len(a & b)
            rows.append(row)
        return rows

    rows = asyncio.run(run())

    def resume(nom):
        ok = [r[nom] for r in rows if r[nom]["n"] > 0]
        return {"reussites": len(ok), "echecs": len(rows) - len(ok),
                "temps_median_s": round(st.median([r[nom]["s"] for r in rows]), 2),
                "resultats_moyens": round(st.mean([r[nom]["n"] for r in rows]), 1)}

    return {"searxng": resume("searxng"), "duckduckgo": resume("duckduckgo"),
            "urls_communes_top5_moyenne": round(st.mean(r["urls_communes_top5"] for r in rows), 1), "detail": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("quoi", choices=["chroma", "web"])
    ap.add_argument("--copie")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    res = chroma(a.copie) if a.quoi == "chroma" else web()
    pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "detail"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
