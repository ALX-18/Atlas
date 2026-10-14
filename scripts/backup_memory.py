"""
Sauvegarde, vérification et restauration de la mémoire d'Atlas — sans Docker (sprint Sans Docker, SD3).

La mémoire est un dossier, ouvert par ChromaDB intégré (data/chromadb par défaut). Toute
opération sur la base prend le VERROU de la mémoire (le même qu'Atlas) : si Atlas tourne, le
script refuse, et la copie est donc toujours cohérente.

    python scripts/backup_memory.py backup  [--source data/chromadb] [--dest %USERPROFILE%/Atlas_backups/memoire]
    python scripts/backup_memory.py verify  <dossier_de_sauvegarde>
    python scripts/backup_memory.py restore <dossier_de_sauvegarde> --vers data/chromadb --oui

- backup : copie horodatée chromadb_<AAAAMMJJ_HHMMSS>/data, empreintes SHA-256 de chaque fichier
  (SHA256SUMS), manifeste : collections, décomptes, dimensions, et les résultats des 40 requêtes
  du garde-fou (scripts/garde_fou_rappels.py), relevés sur une copie jetable de la sauvegarde.
- verify : empreintes revérifiées, puis la sauvegarde est ouverte dans un dossier JETABLE :
  décomptes et dimensions, et les 40 requêtes rejouées (mêmes résultats, même ordre, distances à
  1e-3). Rapport verify_<horodatage>.json. Rien n'est modifié.
- restore : exige un verify réussi et --oui. La base en place n'est jamais effacée : elle est
  mise de côté (<dossier>.avant_restauration_<horodatage>), puis la sauvegarde est copiée et
  revérifiée sur place.

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


def summarize(path: Path) -> dict:
    """Collections, décomptes, dimensions et résultats des 40 requêtes, sur une COPIE jetable."""
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
        requetes = []
        for q in REQUETES:
            v = embed(q)
            ligne = {"requete": q}
            for n in QUERY_COLLECTIONS:
                if n in cols and cols[n]["count"]:
                    r = client.get_collection(n).query(query_embeddings=[v], n_results=min(10, cols[n]["count"]))
                    ligne[n] = [[i, round(float(d), 6)] for i, d in zip(r["ids"][0], r["distances"][0])]
            requetes.append(ligne)
        del client
        return {"collections": cols, "requetes": requetes}
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

    ok, why = acquire_memory_lock(str(source))
    if not ok:
        raise SystemExit(f"Refus : {why}. Arrêter Atlas avant de sauvegarder ou de restaurer.")


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
    manifest = {"cree": stamp, "source": str(source), "fichiers": len(apres), **summarize(data)}
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


def verify_dir(backup: Path, data: Path | None = None) -> dict:
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
    ordres, ecart = _compare_requetes(manifest["requetes"], now["requetes"])
    ok = empreintes_ok and cols_ok and ordres == 0 and ecart <= 1e-3
    return {"ok": ok, "empreintes_identiques": empreintes_ok, "collections_identiques": cols_ok,
            "collections": now["collections"], "requetes_40": {"ordres_differents": ordres, "ecart_distance_max": ecart}}


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
        f"40 requêtes : {res['requetes_40']['ordres_differents']} ordre(s) différent(s), "
        f"écart {res['requetes_40']['ecart_distance_max']:.1e}")
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
    res = verify_dir(backup, cible)
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
