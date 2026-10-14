"""
Sprint Performance / PF3 et PF4 — garde-fou de qualité de la mémoire.

40 requêtes de rappel, jouées sur une COPIE de la mémoire (jamais la vraie), avec un moteur
d'embeddings donné et un mode d'accès donné. Chaque requête relève, dans les trois collections
vectorisées par e5 (atlas_memory_e5, atlas_conversations, atlas_documents), les 10 premiers
résultats et leur distance. Deux relevés se comparent : mêmes résultats, même ordre, distances
à 1e-3 près — sinon le changement n'est pas appliqué.

    python scripts/garde_fou_rappels.py releve --copie <data/> --moteur sentence-transformers --out a.json
    python scripts/garde_fou_rappels.py releve --copie <data/> --moteur onnx --out b.json
    python scripts/garde_fou_rappels.py compare a.json b.json

La copie est recopiée dans un dossier jetable à chaque relevé : la sauvegarde n'est jamais
ouverte en écriture.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

COLLECTIONS = ("atlas_memory_e5", "atlas_conversations", "atlas_documents")

REQUETES = [
    "tu te souviens de Discord ?", "ouvre steam", "quelle application j'utilise le matin ?",
    "qu'est-ce que je t'ai demandé hier ?", "le mode gaming", "ferme la fenêtre", "Opera GX",
    "mes habitudes de jeu", "la météo à Paris", "le bloc-notes", "paramètres de discord",
    "quelle est la capitale de l'Italie ?", "monte le son", "vide la corbeille", "Visual Studio Code",
    "le projet Atlas", "un assistant de bureau local", "les erreurs de clic", "mets steam au premier plan",
    "est-ce que tu te souviens de ma préférence ?", "lance le mode travail", "la musique", "Spotify",
    "réduis la fenêtre", "cherche sur internet", "retiens que j'aime le café", "le dernier message envoyé",
    "Bibliothèque Steam", "qu'as-tu retenu sur moi ?", "Docker", "Ollama", "le mot d'éveil Hey Atlas",
    "transcription vocale", "une conversation privée", "le mode sombre", "Helldivers", "la calculatrice",
    "écris bonjour dans Discord", "planifie une tâche", "quelle heure est-il ?",
]


def releve(copie: str, moteur: str, acces: str) -> dict:
    import chromadb

    import core_conversational.memory_core as mc

    work = pathlib.Path(tempfile.mkdtemp(prefix="atlas_garde_fou_"))
    shutil.copytree(copie, work / "data")
    try:
        mc.set_embedding_backend(moteur, str(ROOT / "models" / "embeddings" / "multilingual-e5-base"))
        t0 = time.perf_counter()
        mc.embed_query("chargement")
        charge_s = time.perf_counter() - t0
        if acces == "integre":
            client = chromadb.PersistentClient(path=str(work / "data"))
        else:
            raise SystemExit("seul l'accès intégré est relevé ici (la copie n'est jamais servie par Docker)")
        cols = {}
        for name in COLLECTIONS:
            try:
                cols[name] = client.get_collection(name)
            except Exception:
                pass
        out, durees = [], []
        for q in REQUETES:
            t = time.perf_counter()
            vec = mc.embed_query(q)
            ligne = {"requete": q}
            for name, col in cols.items():
                r = col.query(query_embeddings=[vec], n_results=min(10, col.count() or 1))
                ligne[name] = [[i, round(float(d), 6)] for i, d in zip(r["ids"][0], r["distances"][0])]
            durees.append(time.perf_counter() - t)
            out.append(ligne)
        return {"moteur": mc.embedding_backend(), "acces": acces, "chargement_s": round(charge_s, 2),
                "rappel_ms_median": round(1000 * sorted(durees)[len(durees) // 2], 1),
                "collections": {n: c.count() for n, c in cols.items()}, "requetes": out}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def compare(a: dict, b: dict, tol: float = 1e-3) -> dict:
    ecarts, max_d, n = [], 0.0, 0
    for la, lb in zip(a["requetes"], b["requetes"]):
        for name in COLLECTIONS:
            ra, rb = la.get(name, []), lb.get(name, [])
            ids_a, ids_b = [x[0] for x in ra], [x[0] for x in rb]
            n += 1
            if ids_a != ids_b:
                ecarts.append({"requete": la["requete"], "collection": name, "a": ids_a[:5], "b": ids_b[:5]})
                continue
            for (_, da), (_, db) in zip(ra, rb):
                max_d = max(max_d, abs(da - db))
    return {"listes_comparees": n, "ordres_differents": len(ecarts), "ecart_distance_max": max_d,
            "identique": not ecarts and max_d <= tol, "detail": ecarts[:10]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("releve")
    r.add_argument("--copie", required=True)
    r.add_argument("--moteur", choices=["sentence-transformers", "onnx"], required=True)
    r.add_argument("--acces", choices=["integre"], default="integre")
    r.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    args = ap.parse_args(argv)
    if args.cmd == "releve":
        res = releve(args.copie, args.moteur, args.acces)
        pathlib.Path(args.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({k: v for k, v in res.items() if k != "requetes"}, ensure_ascii=False))
    else:
        a = json.loads(pathlib.Path(args.a).read_text(encoding="utf-8"))
        b = json.loads(pathlib.Path(args.b).read_text(encoding="utf-8"))
        print(json.dumps(compare(a, b), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
