"""
Sprint Apprentissage 2 / AQ2 — retirer de la mémoire des collections VIDES, après une sauvegarde
vérifiée.

    python scripts/retirer_collections_vides.py --sauvegarde <dossier>                 # plan seulement
    python scripts/retirer_collections_vides.py --sauvegarde <dossier> --oui           # retire

Collections visées (déclarées, jamais utilisées, ou remplacées par data/apprentissage.db) :
atlas_apprentissage, atlas_habits, atlas_context_apps.

Garde-fous :
- le verrou de la mémoire est pris (Atlas lancé : refus) ;
- la sauvegarde indiquée doit avoir un `verify` réussi (backup_memory.py verify) ;
- une collection qui n'est PAS vide est refusée : rien n'est retiré du tout ;
- sans --oui, rien n'est retiré : le plan est affiché.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

VISEES = ("atlas_apprentissage", "atlas_habits", "atlas_context_apps")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--chemin", default=str(ROOT / "data" / "chromadb"))
    p.add_argument("--sauvegarde", required=True, help="dossier d'une sauvegarde backup_memory.py vérifiée")
    p.add_argument("--oui", action="store_true")
    a = p.parse_args(argv)

    sauvegarde = Path(a.sauvegarde)
    rapports = sorted(sauvegarde.glob("verify_*.json"))
    if not rapports or not json.loads(rapports[-1].read_text(encoding="utf-8")).get("ok"):
        raise SystemExit("Refus : cette sauvegarde n'a pas de verify réussi. Sauvegarder et vérifier d'abord.")

    from core.memory_manager import MemoryLockedError, open_client

    try:
        client = open_client(a.chemin)
    except MemoryLockedError as e:
        raise SystemExit(f"Refus : {e}. Arrêter Atlas d'abord.")
    presentes = {c.name for c in client.list_collections()}
    plan = []
    for nom in VISEES:
        if nom not in presentes:
            print(f"  {nom:22} absente — rien à faire")
            continue
        n = client.get_collection(nom).count()
        print(f"  {nom:22} {n} élément(s)")
        if n:
            raise SystemExit(f"Refus : {nom} n'est pas vide ({n} élément(s)). Rien n'est retiré.")
        plan.append(nom)
    if not plan:
        print("Rien à retirer.")
        return 0
    if not a.oui:
        print(f"Plan : retirer {', '.join(plan)} (vides). Relancer avec --oui pour le faire.")
        return 0
    for nom in plan:
        client.delete_collection(nom)
        print(f"  {nom:22} retirée")
    restantes = sorted(c.name for c in client.list_collections())
    print(f"Collections restantes : {', '.join(restantes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
