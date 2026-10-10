"""
Nettoyage de la mémoire décidé par le superviseur (sprint E, prélude).

Supprime UNIQUEMENT ce que le brief E a listé :
  - artefacts de test dans `atlas_documents` et `atlas_errors` (règles de memory_inventory) ;
  - entrées écrites par le test D1 (identifiants explicites) ;
  - doublons exacts dans `atlas_memory_e5`, `atlas_documents` et `atlas_errors`,
    en gardant la plus ancienne occurrence.

`atlas_memory` (384 dimensions) est PROTÉGÉE : c'est le retour arrière du sprint D.
`atlas_conversations` n'est pas touchée.

    python scripts/memory_cleanup.py plan            # aucune écriture
    python scripts/memory_cleanup.py apply --yes     # supprime, après sauvegarde vérifiée
    python scripts/memory_cleanup.py plan-ids --ids liste.json           # GB7 : liste explicite
    python scripts/memory_cleanup.py apply-ids --ids liste.json --yes

Exige une sauvegarde vérifiée au préalable (scripts/backup_memory.py backup + verify).
"""

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import chromadb

from scripts.memory_inventory import classify_artefact, keep_choice, load

# Collections que ce script ne doit JAMAIS modifier.
PROTECTED = {"atlas_memory", "atlas_conversations"}

# Artefacts : collections concernées par le brief E.
ARTEFACT_TARGETS = ["atlas_documents", "atlas_errors"]
# Doublons : collections concernées par le brief E.
DEDUP_TARGETS = ["atlas_memory_e5", "atlas_documents", "atlas_errors"]
# Entrées écrites par le test D1 (rapport D, D-R3).
D1_TEST_IDS = ["err_d6824758fa78", "err_0888b88f2bbf", "err_4cd2a3a29cd7"]


def build_plan(client) -> dict:
    """Décide, sans rien écrire, ce qui serait supprimé dans chaque collection."""
    plan: dict[str, dict] = {}
    for name in sorted(set(ARTEFACT_TARGETS) | set(DEDUP_TARGETS)):
        assert name not in PROTECTED, f"{name} est protégée"
        items = load(client, name)
        if items is None:
            continue
        doomed: dict[str, str] = {}   # id → raison

        if name in ARTEFACT_TARGETS:
            for it in items:
                why = classify_artefact(it["text"])
                if why:
                    doomed[it["id"]] = f"artefact de test : {why}"
            for mid in D1_TEST_IDS:
                if any(it["id"] == mid for it in items):
                    doomed[mid] = "entrée écrite par le test D1 (rapport D, D-R3)"

        if name in DEDUP_TARGETS:
            groups = collections.defaultdict(list)
            for it in items:
                groups[(it["category"], it["text"])].append(it)
            for entries in groups.values():
                if len(entries) < 2:
                    continue
                keep = keep_choice(entries)
                for it in entries:
                    if it["id"] != keep["id"] and it["id"] not in doomed:
                        doomed[it["id"]] = f"doublon exact ; conservée : {keep['id']}"

        plan[name] = {
            "total": len(items),
            "delete": doomed,
            "reste": len(items) - len(doomed),
            "textes_uniques_restants": len({it["text"] for it in items if it["id"] not in doomed}),
        }
    return plan


# --------------------------------------------------------------------------- #
#  Sprint G-bis / GB7 — identifiants explicites
#
#  Décision d'Alexis : retirer exactement ce que les tests du sprint G ont écrit.
#  Le fichier liste {collection: {identifiant: début du texte attendu}}. Un seul
#  identifiant introuvable ou dont le texte diffère, et RIEN n'est supprimé.
#  atlas_memory reste intouchable. atlas_conversations n'est atteignable QUE par
#  cette liste explicite : les règles automatiques du sprint E ne la touchent pas.
# --------------------------------------------------------------------------- #

NEVER_TOUCH = {"atlas_memory"}


def build_ids_plan(client, wanted: dict) -> dict:
    """Vérifie, sans rien écrire, que chaque identifiant existe et porte le texte attendu."""
    plan: dict[str, dict] = {}
    problems: list[str] = []
    for name, ids in wanted.items():
        if name in NEVER_TOUCH:
            raise ValueError(f"{name} est intouchable (retour arrière du sprint D)")
        coll = client.get_collection(name)
        got = coll.get(ids=list(ids), include=["documents"])
        found = dict(zip(got.get("ids") or [], got.get("documents") or []))
        for mid, expected in ids.items():
            if mid not in found:
                problems.append(f"{name}/{mid} introuvable")
            elif not (found[mid] or "").startswith(expected):
                problems.append(f"{name}/{mid} : texte différent ({(found[mid] or '')[:60]!r})")
        plan[name] = {"total": coll.count(), "delete": sorted(ids), "texts": found}
    if problems:
        raise ValueError("rien n'est supprimé — " + " ; ".join(problems))
    return plan


def apply_ids_plan(client, plan: dict) -> dict:
    """Supprime exactement les identifiants du plan ; vérifie le décompte après chaque collection."""
    done: dict[str, dict] = {}
    for name, info in plan.items():
        assert name not in NEVER_TOUCH, f"{name} est intouchable"
        coll = client.get_collection(name)
        before = coll.count()
        coll.delete(ids=info["delete"])
        after = coll.count()
        if before - after != len(info["delete"]):
            raise RuntimeError(f"{name} : {before} → {after}, attendu −{len(info['delete'])}")
        done[name] = {"avant": before, "après": after, "ids": info["delete"]}
    return done


def show(plan: dict) -> None:
    for name, info in plan.items():
        artefacts = sum(1 for r in info["delete"].values() if r.startswith("artefact"))
        d1 = sum(1 for r in info["delete"].values() if r.startswith("entrée écrite"))
        dups = sum(1 for r in info["delete"].values() if r.startswith("doublon"))
        print(f"{name:20} {info['total']:4} éléments → supprimer {len(info['delete']):4} "
              f"(artefacts {artefacts}, test D1 {d1}, doublons {dups}) → reste {info['reste']}")
    print(f"\nProtégées, non modifiées : {', '.join(sorted(PROTECTED))}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["plan", "apply", "plan-ids", "apply-ids"])
    parser.add_argument("--ids", help="GB7 : JSON {collection: {identifiant: début du texte attendu}}")
    parser.add_argument("--yes", action="store_true", help="confirmation explicite requise pour apply")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--report", help="fichier JSON listant les identifiants supprimés")
    args = parser.parse_args()

    client = chromadb.HttpClient(host=args.host, port=args.port)
    client.heartbeat()

    if args.command in ("plan-ids", "apply-ids"):
        if not args.ids:
            print("Refus : --ids FICHIER est obligatoire.")
            return 1
        wanted = json.loads(pathlib.Path(args.ids).read_text(encoding="utf-8"))
        try:
            plan = build_ids_plan(client, wanted)
        except ValueError as e:
            print(f"Refus : {e}")
            return 1
        for name, info in plan.items():
            print(f"{name:20} {info['total']:4} éléments → supprimer {len(info['delete'])}")
            for mid in info["delete"]:
                print(f"    {mid}  {(info['texts'][mid] or '')[:90]!r}")
        if args.command == "plan-ids":
            print("\nAucune écriture : mode plan-ids.")
            return 0
        if not args.yes:
            print("\nRefus : 'apply-ids' exige --yes (et une sauvegarde vérifiée au préalable).")
            return 1
        done = apply_ids_plan(client, plan)
        for name, d in done.items():
            print(f"{name:20} {d['avant']} → {d['après']} ({len(d['ids'])} supprimés)")
        if args.report:
            pathlib.Path(args.report).write_text(json.dumps(done, ensure_ascii=False, indent=2),
                                                 encoding="utf-8")
            print(f"\nIdentifiants supprimés consignés : {args.report}")
        return 0

    plan = build_plan(client)
    show(plan)

    if args.command == "plan":
        print("\nAucune écriture : mode plan.")
        return 0

    if not args.yes:
        print("\nRefus : 'apply' exige --yes (et une sauvegarde vérifiée au préalable).")
        return 1

    deleted: dict[str, list[str]] = {}
    for name, info in plan.items():
        assert name not in PROTECTED, f"{name} est protégée"
        ids = sorted(info["delete"])
        if not ids:
            continue
        coll = client.get_collection(name)
        before = coll.count()
        coll.delete(ids=ids)
        after = coll.count()
        deleted[name] = ids
        print(f"{name:20} {before} → {after} ({before - after} supprimés)")

    for name in sorted(PROTECTED):
        try:
            print(f"{name:20} {client.get_collection(name).count()} éléments (protégée, inchangée)")
        except Exception:
            pass

    if args.report:
        payload = {name: {"ids": ids, "raisons": plan[name]["delete"]} for name, ids in deleted.items()}
        pathlib.Path(args.report).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                             encoding="utf-8")
        print(f"\nIdentifiants supprimés consignés : {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
