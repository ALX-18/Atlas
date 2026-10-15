"""
Sprint Apprentissage 1 / AP0 — reproduit « hnsw segment reader: Nothing found on disk ».

Autonome : ne dépend que de chromadb et de la bibliothèque standard, pour être lancé avec
l'interpréteur d'un venv jetable portant une autre version de ChromaDB.

Chaque ouverture :
  1. un AUTRE processus écrit dans la base (comme une session d'Atlas, arrêtée ensuite) ;
  2. ce processus-ci l'ouvre et lit dans l'ordre qui déclenche le défaut : `get` (avec les
     vecteurs) et `count` sur chaque collection, puis une `query` sur chacune.

    <python> scripts/repro_chroma.py fraiche --n 100 --out res.json
        base neuve à chaque ouverture (4 collections de 12 éléments)
    <python> scripts/repro_chroma.py copie --source <copie de data/chromadb> --n 100 --out res.json
        copie de la mémoire, 3 souvenirs ajoutés à chaque ouverture (comme une session)

Ne touche jamais à data/chromadb : `copie` refuse un dossier nommé data/chromadb du projet.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ECRIRE = r'''
import hashlib, sys, chromadb
from chromadb.config import Settings

def vec(t, dim):
    h = hashlib.sha256(t.encode()).digest() * (dim // 32 + 1)
    v = [b / 255 - 0.5 for b in h[:dim]]
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v]

chemin, mode, graine = sys.argv[1], sys.argv[2], sys.argv[3]
c = chromadb.PersistentClient(path=chemin, settings=Settings(anonymized_telemetry=False))
if mode == "fraiche":
    for nom in ("atlas_memory_e5", "atlas_conversations", "atlas_documents", "atlas_errors"):
        col = c.get_or_create_collection(nom, metadata={"hnsw:space": "cosine"})
        docs = [f"{nom} souvenir {i} Discord Steam Opera" for i in range(12)]
        col.add(ids=[f"{nom}_{i}" for i in range(12)], documents=docs, embeddings=[vec(d, 16) for d in docs])
else:
    for nom in ("atlas_conversations", "atlas_memory_e5"):
        col = c.get_collection(nom)
        r = col.get(limit=1, include=["embeddings"])
        dim = len(r["embeddings"][0]) if r["embeddings"] is not None and len(r["embeddings"]) else 768
        docs = [f"essai {graine} souvenir {i}" for i in range(3)]
        col.add(ids=[f"essai_{graine}_{nom}_{i}" for i in range(3)], documents=docs,
                embeddings=[vec(d, dim) for d in docs], metadatas=[{"essai": "repro_chroma"}] * 3)
'''


def _vec(t: str, dim: int) -> list[float]:
    h = hashlib.sha256(t.encode()).digest() * (dim // 32 + 1)
    v = [b / 255 - 0.5 for b in h[:dim]]
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v]


def lire(chemin: pathlib.Path) -> str | None:
    """L'ordre de lecture qui déclenche le défaut. None si tout est lu, sinon l'étape en échec."""
    import chromadb
    from chromadb.api.client import SharedSystemClient
    from chromadb.config import Settings

    c = chromadb.PersistentClient(path=str(chemin), settings=Settings(anonymized_telemetry=False))
    etape = None
    try:
        noms = sorted(x.name for x in c.list_collections())
        dims = {}
        for n in noms:
            etape = f"get+count {n}"
            col = c.get_collection(n)
            r = col.get(limit=1, include=["embeddings"])
            dims[n] = len(r["embeddings"][0]) if r["embeddings"] is not None and len(r["embeddings"]) else None
            col.count()
        for n in noms:
            if dims[n]:
                etape = f"query {n}"
                c.get_collection(n).query(query_embeddings=[_vec("Discord", dims[n])], n_results=3)
        return None
    except Exception as e:
        return f"{etape} : {type(e).__name__}: {str(e)[:120]}"
    finally:
        del c
        SharedSystemClient.clear_system_cache()
        gc.collect()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["fraiche", "copie"])
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--source")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    import chromadb

    if a.mode == "copie":
        src = pathlib.Path(a.source).resolve()
        if src.name == "chromadb" and src.parent.name == "data" and (src.parent.parent / "main.py").exists():
            raise SystemExit("Refus : jamais la vraie mémoire ; donner une COPIE.")
    res = {"chromadb": chromadb.__version__, "mode": a.mode, "ouvertures": 0, "echecs": 0, "detail": []}
    t0 = time.perf_counter()
    for i in range(a.n):
        d = pathlib.Path(tempfile.mkdtemp(prefix="repro_chroma_"))
        base = d / "base"
        if a.mode == "copie":
            shutil.copytree(src, base, ignore=shutil.ignore_patterns("*.lock"))
        subprocess.run([sys.executable, "-c", ECRIRE, str(base), a.mode, str(i)], check=True)
        echec = lire(base)
        res["ouvertures"] += 1
        if echec:
            res["echecs"] += 1
            res["detail"].append({"ouverture": i, "echec": echec})
        shutil.rmtree(d, ignore_errors=True)
    res["duree_s"] = round(time.perf_counter() - t0, 1)
    pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"chromadb {res['chromadb']} — {a.mode} — {res['echecs']} échec(s) sur {res['ouvertures']} ouvertures "
          f"({res['duree_s']} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
