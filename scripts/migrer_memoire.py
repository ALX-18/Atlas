"""
Sprint Sans Docker / SD1 — migrer la mémoire de ChromaDB dans Docker (1.4.1) vers ChromaDB
intégré (PersistentClient, paquet pip épinglé), sans point de non-retour.

La source est TOUJOURS une sauvegarde vérifiée (scripts/backup_memory.py backup + verify) : son
dossier data/ est recopié, jamais ouvert en écriture. Le volume Docker n'est ni modifié ni
supprimé : il reste le repli.

    python scripts/migrer_memoire.py essai --sauvegarde <Atlas_backups/memoire/chromadb_…>
        → copie dans un dossier jetable, contrôle complet contre la mémoire dans Docker (lue)
    python scripts/migrer_memoire.py vraie --sauvegarde <…> --oui
        → copie vers data/chromadb/ (refuse si le dossier existe déjà), même contrôle

Contrôle, collection par collection : décomptes, identifiants, documents, métadonnées, vecteurs
(identiques à 1e-6), puis les 40 requêtes de scripts/garde_fou_rappels.py sur les collections e5.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
CIBLE = ROOT / "data" / "chromadb"


def _tout(col) -> dict:
    r = col.get(include=["documents", "metadatas", "embeddings"])
    return {i: (d, m, list(map(float, e)) if e is not None else None)
            for i, d, m, e in zip(r["ids"], r["documents"], r["metadatas"], r["embeddings"])}


def controle(dossier: pathlib.Path) -> dict:
    import chromadb

    from garde_fou_rappels import COLLECTIONS, REQUETES, compare

    neuf = chromadb.PersistentClient(path=str(dossier))
    ancien = chromadb.HttpClient(host="localhost", port=8001)     # lecture seule
    res = {"collections": {}, "identique": True}
    noms = sorted(c.name for c in ancien.list_collections())
    noms_neuf = sorted(c.name for c in neuf.list_collections())
    res["memes_collections"] = noms == noms_neuf
    res["identique"] &= noms == noms_neuf
    for n in noms:
        a, b = _tout(ancien.get_collection(n)), _tout(neuf.get_collection(n))
        ecart_vec = 0.0
        docs = metas = 0
        for i in a.keys() & b.keys():
            docs += a[i][0] != b[i][0]
            metas += a[i][1] != b[i][1]
            if a[i][2] is not None and b[i][2] is not None:
                ecart_vec = max(ecart_vec, max(abs(x - y) for x, y in zip(a[i][2], b[i][2])))
        ligne = {"decompte": [len(a), len(b)], "ids_identiques": a.keys() == b.keys(), "documents_differents": docs,
                 "metadonnees_differentes": metas, "ecart_vecteurs_max": ecart_vec,
                 "metadata_collection_identique": ancien.get_collection(n).metadata == neuf.get_collection(n).metadata}
        ligne["ok"] = (ligne["decompte"][0] == ligne["decompte"][1] and ligne["ids_identiques"] and not docs
                       and not metas and ecart_vec <= 1e-6 and ligne["metadata_collection_identique"])
        res["identique"] &= ligne["ok"]
        res["collections"][n] = ligne

    # Les 40 requêtes, mêmes vecteurs des deux côtés
    import core_conversational.memory_core as mc

    vecs = {q: mc.embed_query(q) for q in REQUETES}

    def releve(client):
        out = []
        for q, v in vecs.items():
            ligne = {"requete": q}
            for n in COLLECTIONS:
                c = client.get_collection(n)
                r = c.query(query_embeddings=[v], n_results=min(10, c.count() or 1))
                ligne[n] = [[i, round(float(d), 6)] for i, d in zip(r["ids"][0], r["distances"][0])]
            out.append(ligne)
        return {"requetes": out}

    res["requetes_40"] = compare(releve(ancien), releve(neuf))
    res["identique"] &= res["requetes_40"]["identique"]
    res["chromadb_pip"] = chromadb.__version__
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["essai", "vraie"])
    ap.add_argument("--sauvegarde", required=True, help="dossier chromadb_<horodatage> vérifié")
    ap.add_argument("--oui", action="store_true", help="vraie : accord explicite d'Alexis")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    src = pathlib.Path(a.sauvegarde) / "data"
    if not src.is_dir() or not list(pathlib.Path(a.sauvegarde).glob("verify_*.json")):
        raise SystemExit("Refus : la sauvegarde doit contenir data/ et un rapport verify_*.json (backup + verify).")
    if a.mode == "vraie":
        if not a.oui:
            raise SystemExit("Refus : la migration de la vraie mémoire exige --oui (accord d'Alexis).")
        if CIBLE.exists() and any(CIBLE.iterdir()):
            raise SystemExit(f"Refus : {CIBLE} existe déjà et n'est pas vide. Rien n'est écrasé.")
        shutil.copytree(src, CIBLE, dirs_exist_ok=True)
        dossier = CIBLE
    else:
        dossier = pathlib.Path(tempfile.mkdtemp(prefix="atlas_migration_essai_")) / "chromadb"
        shutil.copytree(src, dossier)
    try:
        res = {"mode": a.mode, "source": str(src), "destination": str(dossier), **controle(dossier)}
    finally:
        if a.mode == "essai":
            import gc

            gc.collect()
            shutil.rmtree(dossier.parent, ignore_errors=True)
    texte = json.dumps(res, ensure_ascii=False, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(texte, encoding="utf-8")
    print(texte)
    return 0 if res["identique"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
