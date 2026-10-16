"""
Sprint Index des fichiers / IX4.2 — retirer de `data/atlas_actions.jsonl` les lignes écrites par les
ESSAIS du développeur, et seulement celles reconnaissables sans aucun doute (décision d'Alexis, 16/10).

    python scripts/nettoyer_journal.py plan  --sortie <plan.json> [--phrase "ouvre notepad" ...]
    python scripts/nettoyer_journal.py retirer --plan <plan.json> --oui

Une ligne est retenue si :
- G1 : elle vise une fenêtre de test (« AtlasEssai… ») ou une phrase propre au check-up
  (« essai de check-up », « bonjour checkup ») ;
- G2 : elle est dans une SESSION D'ESSAI (lignes à moins de 10 minutes les unes des autres, dont au
  moins une ligne G1) ET sa demande est mot pour mot une phrase des scripts d'essai
  (checkup_dynamique, rejeu_fiabilite, rejeu_apprentissage, mesure_ressources) ;
- G3 : elle est dans une session d'essai ET c'est une automatisation déclenchée par l'Atlas d'essai ;
- G4 : sa demande est l'une des phrases données par --phrase (désignées par Alexis).
Tout le reste est gardé — y compris, dans une session d'essai, une demande que je ne peux pas
attribuer sans doute à un script.

`retirer` exige --oui ET que le journal n'ait pas changé depuis le plan (empreinte) ; il sauvegarde
d'abord le journal (copie + empreinte) dans le dossier de sauvegardes, puis écrit le nouveau journal
de façon atomique (fichier temporaire, puis remplacement).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "data" / "atlas_actions.jsonl"
SAUVEGARDES = Path.home() / "Atlas_backups" / "journal"
SCRIPTS_D_ESSAI = ("checkup_dynamique.py", "rejeu_fiabilite.py", "rejeu_apprentissage.py", "mesure_ressources.py")
ECART_SESSION = timedelta(minutes=10)


def _sha(octets: bytes) -> str:
    return hashlib.sha256(octets).hexdigest()


def phrases_des_scripts() -> set[str]:
    phr = set()
    for nom in SCRIPTS_D_ESSAI:
        s = (ROOT / "scripts" / nom).read_text(encoding="utf-8")
        phr |= {m.group(1) for m in re.finditer(r'"([^"\n]{6,120})"', s)}
        phr |= {m.group(1) for m in re.finditer(r"'([^'\n]{6,120})'", s)}
    return phr


def _marqueur(e: dict) -> bool:
    u = f"{e.get('user_input') or ''} {e.get('target') or ''}"
    return "AtlasEssai" in u or "essai de check-up" in u or "bonjour checkup" in u


def planifier(lignes: list[str], phrases_alexis: list[str]) -> dict:
    phr = phrases_des_scripts()
    evts = []
    for n, l in enumerate(lignes):
        try:
            e = json.loads(l)
            evts.append((n, e, datetime.fromisoformat(e["timestamp"])))
        except (ValueError, KeyError):
            continue                    # illisible : gardée
    evts.sort(key=lambda x: x[2])
    sessions, cur = [], []
    for x in evts:
        if cur and x[2] - cur[-1][2] > ECART_SESSION:
            sessions.append(cur)
            cur = []
        cur.append(x)
    if cur:
        sessions.append(cur)
    retenues = {}
    for s in sessions:
        essai = any(_marqueur(e) for _, e, _ in s)
        for n, e, _ in s:
            u = e.get("user_input") or ""
            groupe = None
            if _marqueur(e):
                groupe = "G1"
            elif essai and u in phr:
                groupe = "G2"
            elif essai and u.startswith("automation:"):
                groupe = "G3"
            elif u in phrases_alexis:
                groupe = "G4"
            if groupe:
                retenues[n] = {"ligne": n + 1, "groupe": groupe, "date": e["timestamp"][:19], "demande": u,
                               "outil": e.get("tool"), "sha": _sha(lignes[n].encode("utf-8"))}
    return {"journal": str(JOURNAL), "lignes": len(lignes), "a_retirer": [retenues[k] for k in sorted(retenues)]}


def cmd_plan(a) -> int:
    brut = JOURNAL.read_bytes()
    lignes = brut.decode("utf-8").splitlines()
    plan = planifier(lignes, a.phrase or [])
    plan["empreinte_journal"] = _sha(brut)
    plan["phrases_alexis"] = a.phrase or []
    Path(a.sortie).write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    par_groupe = {}
    for r in plan["a_retirer"]:
        par_groupe[r["groupe"]] = par_groupe.get(r["groupe"], 0) + 1
    print(f"{plan['lignes']} lignes ; à retirer : {len(plan['a_retirer'])} {par_groupe} ; gardées : "
          f"{plan['lignes'] - len(plan['a_retirer'])}. Plan → {a.sortie}")
    return 0


def cmd_retirer(a) -> int:
    if not a.oui:
        raise SystemExit("Refus : retirer exige --oui (après l'accord d'Alexis sur la liste).")
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    brut = JOURNAL.read_bytes()
    if _sha(brut) != plan["empreinte_journal"]:
        raise SystemExit("Refus : le journal a changé depuis le plan. Refaire le plan et le remontrer.")
    lignes = brut.decode("utf-8").splitlines()
    a_retirer = {r["ligne"] - 1 for r in plan["a_retirer"]}
    for r in plan["a_retirer"]:
        if _sha(lignes[r["ligne"] - 1].encode("utf-8")) != r["sha"]:
            raise SystemExit(f"Refus : la ligne {r['ligne']} ne correspond plus au plan.")
    SAUVEGARDES.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    copie = SAUVEGARDES / f"atlas_actions_{stamp}.jsonl"
    shutil.copy2(JOURNAL, copie)
    if _sha(copie.read_bytes()) != plan["empreinte_journal"]:
        raise SystemExit("Échec : la copie de sauvegarde ne correspond pas. Rien n'est retiré.")
    (SAUVEGARDES / f"atlas_actions_{stamp}.sha256").write_text(f"{plan['empreinte_journal']}  {copie.name}\n",
                                                               encoding="utf-8")
    gardees = [l for n, l in enumerate(lignes) if n not in a_retirer]
    tmp = JOURNAL.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(l + "\n" for l in gardees), encoding="utf-8")
    os.replace(tmp, JOURNAL)
    print(f"Sauvegarde : {copie}")
    print(f"Avant : {len(lignes)} lignes ; retirées : {len(a_retirer)} ; après : {len(gardees)}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pl = sub.add_parser("plan")
    pl.add_argument("--sortie", required=True)
    pl.add_argument("--phrase", action="append")
    rt = sub.add_parser("retirer")
    rt.add_argument("--plan", required=True)
    rt.add_argument("--oui", action="store_true")
    a = p.parse_args(argv)
    return {"plan": cmd_plan, "retirer": cmd_retirer}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
