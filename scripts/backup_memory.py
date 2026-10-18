"""
Sauvegarde, vérification et restauration de la mémoire d'Atlas — sans Docker (sprint Sans Docker, SD3).

La mémoire est un dossier, ouvert par ChromaDB intégré (data/chromadb par défaut). Toute
opération sur la base prend le VERROU de la mémoire (le même qu'Atlas) : si Atlas tourne, le
script refuse, et la copie est donc toujours cohérente.

    python scripts/backup_memory.py backup  [--source data/chromadb] [--dest %USERPROFILE%/Atlas_backups/memoire]
    python scripts/backup_memory.py verify  <dossier_de_sauvegarde>
    python scripts/backup_memory.py restore <dossier_de_sauvegarde> --vers data/chromadb --oui

- backup : copie horodatée chromadb_<AAAAMMJJ_HHMMSS>/data, empreintes SHA-256 de chaque fichier
  (SHA256SUMS), manifeste : collections, décomptes, dimensions, l'EMPREINTE DE CHAQUE ÉLÉMENT
  (identifiant, texte, métadonnées, vecteur en float32 tel que stocké), et les résultats des 40
  requêtes du garde-fou (scripts/garde_fou_rappels.py), relevés sur une copie jetable.
- verify : empreintes des fichiers revérifiées, puis la sauvegarde est ouverte dans un dossier
  JETABLE : décomptes, dimensions et chaque élément relu à l'identique. Les 40 requêtes sont
  rejouées À TITRE INDICATIF (sprint Index des fichiers, décision du superviseur, 16/10/2026) : la
  recherche par ressemblance de ChromaDB est approchée et son ordre varie d'une ouverture à
  l'autre sur des fichiers identiques ; un écart est signalé, il ne fait pas échouer.
  Rapport verify_<horodatage>.json. Rien n'est modifié.
- restore : exige un verify réussi et --oui. La base en place n'est jamais effacée : elle est
  mise de côté (<dossier>.avant_restauration_<horodatage>), puis la sauvegarde est copiée et
  revérifiée sur place.

Apprentissage 2 / AQ2 : les bases SQLite d'Atlas voisines du dossier de la mémoire
(SQLITE_FICHIERS : data/apprentissage.db, data/habits.db) sont copiées avec l'API de sauvegarde de
SQLite dans <sauvegarde>/sqlite/, avec leurs empreintes, leurs décomptes par table et un
`PRAGMA integrity_check` dans le manifeste ; verify les rouvre sur une copie jetable ; restore
met de côté le fichier en place (<fichier>.avant_restauration_<horodatage>) avant de le remettre.
Le verrou d'apprentissage.db est pris comme celui de la mémoire : Atlas lancé, le script refuse.

Les sauvegardes faites du temps de Docker ont un autre manifeste : elles ne passent pas par
verify / restore, mais par scripts/migrer_memoire.py, qui les contrôle contre la mémoire d'origine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

DEFAULT_SOURCE = ROOT / "data" / "chromadb"
DEFAULT_DEST = Path.home() / "Atlas_backups" / "memoire"
QUERY_COLLECTIONS = ("atlas_memory_e5", "atlas_conversations", "atlas_documents")
SQLITE_FICHIERS = ("apprentissage.db", "habits.db", "rappels.db")   # voisins du dossier de la mémoire (data/) ; rappels : Compétences 1
SQLITE_VERROUILLES = ("apprentissage.db",)               # tenus par Atlas comme la mémoire


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)).replace("\\", "/"): sha256_file(p)
            for p in sorted(root.rglob("*")) if p.is_file()}


def _client(path: Path):
    """Un client ChromaDB intégré sur un dossier JETABLE (jamais la vraie base)."""
    import chromadb
    from chromadb.config import Settings

    return chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))


def embed(text: str):
    import core.embeddings as emb

    return emb.embed_query(text)


def summarize(path: Path, essais: int = 3) -> dict:
    """Décomptes et 40 requêtes sur une copie jetable. Sprint Fiabilité : ChromaDB 1.5.1 cesse
    parfois de lire l'index d'une collection pour toute la vie d'un client (« hnsw segment
    reader: Nothing found on disk », 1 relevé sur 15 environ) ; le relevé est alors refait
    entièrement avec un client neuf. Lecture seule."""
    for essai in range(1, essais + 1):
        try:
            return _summarize(path)
        except Exception as e:
            if "hnsw segment reader" not in str(e) or essai == essais:
                raise
            log(f"Index illisible ({str(e)[:80]}) : relevé refait avec un client neuf ({essai + 1}/{essais}).")


def _empreinte_element(i: str, doc, meta, vecteur) -> str:
    """Identifiant, texte, métadonnées (clés triées) et vecteur float32 tel que stocké."""
    import numpy as np

    h = hashlib.sha256()
    h.update(json.dumps([i, doc, meta or {}], ensure_ascii=False, sort_keys=True, default=str).encode("utf-8"))
    if vecteur is not None:
        h.update(np.asarray(vecteur, dtype=np.float32).tobytes())
    return h.hexdigest()


def _releve_donnees(col, count: int, lot: int = 200) -> dict:
    elements = {}
    for debut in range(0, count, lot):
        r = col.get(include=["documents", "metadatas", "embeddings"], limit=lot, offset=debut)
        embs = r.get("embeddings")
        for k, i in enumerate(r["ids"]):
            elements[i] = _empreinte_element(i, (r.get("documents") or [None] * len(r["ids"]))[k],
                                             (r.get("metadatas") or [None] * len(r["ids"]))[k],
                                             embs[k] if embs is not None and len(embs) > k else None)
    return {"count": len(elements), "elements": elements}


def _summarize(path: Path) -> dict:
    """Collections, décomptes, dimensions, empreinte de chaque élément, et résultats des 40
    requêtes (indicatifs), sur une COPIE jetable."""
    from garde_fou_rappels import REQUETES

    work = Path(tempfile.mkdtemp(prefix="atlas_sauvegarde_"))
    try:
        shutil.copytree(path, work / "data")
        client = _client(work / "data")
        cols = {}
        for c in sorted(client.list_collections(), key=lambda c: c.name):
            col = client.get_collection(c.name)
            first = col.get(limit=1, include=["embeddings"])
            emb_ = first.get("embeddings")
            dim = len(emb_[0]) if emb_ is not None and len(emb_) else None
            cols[c.name] = {"count": col.count(), "dim": dim}
        donnees = {n: _releve_donnees(client.get_collection(n), cols[n]["count"]) for n in cols}
        requetes, requetes_erreur = [], None
        try:
            for q in REQUETES:
                v = embed(q)
                ligne = {"requete": q}
                for n in QUERY_COLLECTIONS:
                    if n in cols and cols[n]["count"]:
                        r = client.get_collection(n).query(query_embeddings=[v], n_results=min(10, cols[n]["count"]))
                        ligne[n] = [[i, round(float(d), 6)] for i, d in zip(r["ids"][0], r["distances"][0])]
                requetes.append(ligne)
        except Exception as e:          # indicatives : une recherche approchée qui échoue est signalée
            requetes_erreur = f"{type(e).__name__}: {str(e)[:160]}"
            log(f"40 requêtes interrompues (indicatives) : {requetes_erreur}")
        del client
        return {"collections": cols, "donnees": donnees, "requetes": requetes, "requetes_erreur": requetes_erreur}
    finally:
        import gc

        try:
            from chromadb.api.client import SharedSystemClient

            SharedSystemClient.clear_system_cache()     # rend les fichiers de la copie (Windows)
        except Exception:
            pass
        gc.collect()
        shutil.rmtree(work, ignore_errors=True)


def _lock(source: Path) -> None:
    from core.memory_manager import acquire_memory_lock

    for chemin in [source] + [source.parent / n for n in SQLITE_VERROUILLES]:
        ok, why = acquire_memory_lock(str(chemin))
        if not ok:
            raise SystemExit(f"Refus : {why}. Arrêter Atlas avant de sauvegarder ou de restaurer.")


def _sqlite_releve(fichier: Path) -> dict:
    """Décomptes par table et contrôle d'intégrité, sur une copie jetable. Lecture seule."""
    import sqlite3

    work = Path(tempfile.mkdtemp(prefix="atlas_sqlite_"))
    try:
        copie = work / fichier.name
        shutil.copy2(fichier, copie)
        conn = sqlite3.connect(copie)
        try:
            integrite = conn.execute("PRAGMA integrity_check").fetchone()[0]
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            comptes = {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        finally:
            conn.close()
        return {"integrite": integrite, "tables": comptes}
    except Exception as e:
        return {"integrite": f"illisible : {e}", "tables": {}}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _sqlite_sauvegarder(dossier_data: Path, target: Path) -> dict:
    """Copie cohérente (API de sauvegarde de SQLite) de chaque base présente, puis relevé."""
    import sqlite3

    out = {}
    (target / "sqlite").mkdir(exist_ok=True)
    for nom in SQLITE_FICHIERS:
        src = dossier_data / nom
        if not src.exists():
            continue
        dst = target / "sqlite" / nom
        a, b = sqlite3.connect(src), sqlite3.connect(dst)
        try:
            a.backup(b)
        finally:
            a.close()
            b.close()
        out[nom] = {"sha256": sha256_file(dst), **_sqlite_releve(dst)}
        log(f"  {nom:22} {out[nom]['tables']}  intégrité={out[nom]['integrite']}")
    return out


def cmd_backup(args) -> int:
    source = Path(args.source).resolve()
    if not (source / "chroma.sqlite3").exists():
        raise SystemExit(f"Refus : aucune mémoire dans {source}.")
    _lock(source)                       # Atlas arrêté : personne n'écrit pendant la copie
    stamp = time.strftime("%Y%m%d_%H%M%S")
    target = Path(args.dest) / f"chromadb_{stamp}"
    data = target / "data"
    target.mkdir(parents=True, exist_ok=False)
    log(f"Copie de {source} → {data}")
    avant = hashes(source)
    shutil.copytree(source, data, ignore=shutil.ignore_patterns("*.lock"))
    apres = hashes(data)
    if apres != avant or hashes(source) != avant:
        shutil.rmtree(target, ignore_errors=True)
        raise SystemExit("Échec : la base a changé pendant la copie. Sauvegarde annulée.")
    (target / "SHA256SUMS").write_text("".join(f"{h}  {p}\n" for p, h in apres.items()), encoding="utf-8")
    log("Empreintes identiques ; relevé du manifeste sur une copie jetable…")
    manifest = {"cree": stamp, "source": str(source), "fichiers": len(apres), **summarize(data),
                "sqlite": _sqlite_sauvegarder(source.parent, target)}
    (target / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, c in manifest["collections"].items():
        log(f"  {n:22} {c['count']:5} éléments  dim={c['dim']}")
    log(f"Étape suivante obligatoire : python scripts/backup_memory.py verify \"{target}\"")
    print(target)
    return 0


def _compare_requetes(a: list, b: list, tol: float = 1e-3) -> tuple[int, float]:
    ordres, ecart = 0, 0.0
    for la, lb in zip(a, b):
        for n in QUERY_COLLECTIONS:
            ra, rb = la.get(n, []), lb.get(n, [])
            if [x[0] for x in ra] != [x[0] for x in rb]:
                ordres += 1
                continue
            for (_, da), (_, db) in zip(ra, rb):
                ecart = max(ecart, abs(da - db))
    return ordres, ecart


def verify_dir(backup: Path, data: Path | None = None, sqlite_dir: Path | None = None) -> dict:
    data = data or backup / "data"
    sums = {}
    for line in (backup / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        h, p = line.split("  ", 1)
        sums[p] = h
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    actuelles = hashes(data)
    empreintes_ok = all(actuelles.get(p) == h for p, h in sums.items())
    now = summarize(data)
    cols_ok = now["collections"] == manifest["collections"]
    donnees_ok, donnees = _donnees_verifier(manifest.get("donnees"), now["donnees"])
    ordres, ecart = _compare_requetes(manifest.get("requetes", []), now["requetes"])
    sqlite_ok, sqlite = _sqlite_verifier(manifest.get("sqlite", {}), sqlite_dir or backup / "sqlite")
    ok = empreintes_ok and cols_ok and donnees_ok and sqlite_ok
    return {"ok": ok, "empreintes_identiques": empreintes_ok, "collections_identiques": cols_ok,
            "collections": now["collections"], "donnees_identiques": donnees_ok, "donnees": donnees,
            "requetes_40": {"indicatif": True, "ordres_differents": ordres, "ecart_distance_max": ecart,
                            "erreur": now.get("requetes_erreur")},
            "sqlite_identiques": sqlite_ok, "sqlite": sqlite}


def _donnees_verifier(attendu: dict | None, relu: dict) -> tuple[bool, dict]:
    """Chaque élément relu à l'identique (identifiant, texte, métadonnées, vecteur)."""
    if attendu is None:
        return False, {"_": "manifeste d'avant le 16/10/2026 sans empreinte des éléments : refaire une sauvegarde"}
    res, ok = {}, True
    for n in sorted(set(attendu) | set(relu)):
        a = (attendu.get(n) or {}).get("elements", {})
        b = (relu.get(n) or {}).get("elements", {})
        differents = sorted(i for i in set(a) & set(b) if a[i] != b[i])
        manquants = sorted(set(a) - set(b))
        en_trop = sorted(set(b) - set(a))
        res[n] = {"count": len(b), "differents": differents, "manquants": manquants, "en_trop": en_trop}
        ok = ok and not (differents or manquants or en_trop)
    return ok, res


def _sqlite_verifier(attendu: dict, dossier: Path) -> tuple[bool, dict]:
    """Chaque base du manifeste : même empreinte, intégrité « ok », mêmes décomptes."""
    res, ok = {}, True
    for nom, m in attendu.items():
        f = dossier / nom
        if not f.exists():
            res[nom], ok = {"present": False}, False
            continue
        now = {"sha256": sha256_file(f), **_sqlite_releve(f)}
        bon = now["sha256"] == m["sha256"] and now["integrite"] == "ok" and now["tables"] == m["tables"]
        res[nom] = {"identique": bon, "tables": now["tables"], "integrite": now["integrite"]}
        ok = ok and bon
    return ok, res


def cmd_verify(args) -> int:
    backup = Path(args.dossier).resolve()
    if not (backup / "manifest.json").exists() or not (backup / "SHA256SUMS").exists():
        raise SystemExit("Refus : manifest.json ou SHA256SUMS absent — sauvegarde incomplète.")
    res = verify_dir(backup)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    (backup / f"verify_{stamp}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for n, c in res["collections"].items():
        log(f"  {n:22} {c['count']:5} éléments  dim={c['dim']}")
    log(f"Empreintes : {'identiques' if res['empreintes_identiques'] else 'DIFFÉRENTES'} ; "
        f"collections : {'identiques' if res['collections_identiques'] else 'DIFFÉRENTES'} ; "
        f"éléments : {'identiques' if res['donnees_identiques'] else 'DIFFÉRENTS'} ; "
        f"40 requêtes (indicatives) : {res['requetes_40']['ordres_differents']} ordre(s) différent(s), "
        f"écart {res['requetes_40']['ecart_distance_max']:.1e} ; "
        f"bases SQLite : {'identiques' if res['sqlite_identiques'] else 'DIFFÉRENTES'} {list(res['sqlite'])}")
    log("RESTAURATION PROUVÉE." if res["ok"] else "ÉCHEC : cette sauvegarde n'est pas fiable.")
    return 0 if res["ok"] else 1


def cmd_restore(args) -> int:
    backup = Path(args.dossier).resolve()
    cible = Path(args.vers).resolve()
    if not args.oui:
        raise SystemExit("Refus : la restauration exige --oui.")
    rapports = sorted(backup.glob("verify_*.json"))
    if not rapports or not json.loads(rapports[-1].read_text(encoding="utf-8")).get("ok", False):
        raise SystemExit("Refus : aucun verify réussi pour cette sauvegarde. Lancer verify d'abord.")
    _lock(cible)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    if cible.exists() and any(cible.iterdir()):
        mise_de_cote = cible.with_name(f"{cible.name}.avant_restauration_{stamp}")
        shutil.move(str(cible), str(mise_de_cote))
        log(f"Base en place mise de côté (rien n'est effacé) : {mise_de_cote}")
    shutil.copytree(backup / "data", cible, dirs_exist_ok=True)
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    for nom in manifest.get("sqlite", {}):
        en_place = cible.parent / nom
        if en_place.exists():
            mise_de_cote = en_place.with_name(f"{nom}.avant_restauration_{stamp}")
            shutil.move(str(en_place), str(mise_de_cote))
            log(f"{nom} en place mis de côté (rien n'est effacé) : {mise_de_cote}")
        shutil.copy2(backup / "sqlite" / nom, en_place)
    res = verify_dir(backup, cible, cible.parent)
    log("Restaurée et revérifiée sur place." if res["ok"] else "ÉCHEC de la vérification après restauration.")
    return 0 if res["ok"] else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backup", help="copie horodatée, empreintes et manifeste")
    b.add_argument("--source", default=str(DEFAULT_SOURCE))
    b.add_argument("--dest", default=str(DEFAULT_DEST))
    v = sub.add_parser("verify", help="prouver la restauration dans un dossier jetable")
    v.add_argument("dossier")
    r = sub.add_parser("restore", help="restaurer une sauvegarde vérifiée (la base en place est mise de côté)")
    r.add_argument("dossier")
    r.add_argument("--vers", default=str(DEFAULT_SOURCE))
    r.add_argument("--oui", action="store_true")
    args = p.parse_args(argv)
    return {"backup": cmd_backup, "verify": cmd_verify, "restore": cmd_restore}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
