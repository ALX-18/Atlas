"""
Sprint Banc de modèles / BM3 — l'évaluation à l'aveugle par Alexis.

    python scripts/banc_aveugle.py preparer --banc <dossier du banc> --modeles m1,m2,… --cle <fichier hors du dossier>
    python scripts/banc_aveugle.py reveler  --cle <fichier> --grille <grille remplie>

- preparer : pour chaque modèle retenu, les 3 productions du banc (conversation, section de rapport,
  résumé) ; chacune reçoit une lettre TIRÉE AU HASARD (une production = une lettre, sans lien d'une
  tâche à l'autre), puis tout est écrit dans Documents\\Atlas\\Banc_aveugle\\ avec la grille. La
  correspondance lettre → modèle va dans --cle, HORS de ce dossier ;
- reveler : après la notation d'Alexis, relit la grille et donne la note moyenne de chaque modèle.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import string
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TACHES = {"conversation": "Réponse de conversation — « Donne-moi trois conseils pour mieux dormir, en quelques phrases. »",
          "rapport_section": "Section de rapport — « Les bienfaits de la marche à pied » : section « Les effets sur la santé »",
          "resume": "Résumé d'un document de test (rapport de stage fictif)"}


def dossier_aveugle() -> pathlib.Path:
    sys.path.insert(0, str(ROOT))
    from tools.documents import dossier_atlas

    return dossier_atlas() / "Banc_aveugle"


def preparer(banc: pathlib.Path, modeles: list[str], cle: pathlib.Path, graine: int | None = None) -> pathlib.Path:
    productions = []
    for m in modeles:
        r = json.loads((banc / m.replace(":", "_") / "resultat.json").read_text(encoding="utf-8"))
        for tache in TACHES:
            productions.append({"modele": m, "tache": tache, "texte": r["aveugle"][tache]})
    if len(productions) > 18:
        raise SystemExit(f"Refus : {len(productions)} productions, 18 au plus (brief BM3).")
    hasard = random.Random(graine)
    lettres = hasard.sample(string.ascii_uppercase[:len(productions)], len(productions))
    hasard.shuffle(productions)
    for p, l in zip(productions, lettres):
        p["lettre"] = l
    sortie = dossier_aveugle()
    if cle.resolve().is_relative_to(sortie.resolve()):
        raise SystemExit("Refus : la correspondance doit être HORS du dossier de l'évaluation.")
    sortie.mkdir(parents=True, exist_ok=True)
    for vieux in sortie.glob("*.txt"):
        vieux.unlink()
    grille = ["Évaluation à l'aveugle — note de 1 (mauvais) à 5 (excellent), et une ligne de commentaire.",
              "Juge le français, la clarté et l'utilité. Les lettres sont tirées au hasard : rien ne relie deux productions.", ""]
    for tache, intitule in TACHES.items():
        grille.append(f"== {intitule} ==")
        for p in sorted((p for p in productions if p["tache"] == tache), key=lambda p: p["lettre"]):
            (sortie / f"{p['lettre']}.txt").write_text(f"{intitule}\n\n{p['texte']}\n", encoding="utf-8")
            grille.append(f"{p['lettre']} — note : _ — commentaire : ")
        grille.append("")
    (sortie / "GRILLE.txt").write_text("\n".join(grille), encoding="utf-8")
    # Le document résumé (fictif), pour juger ce qu'un résumé invente ou oublie.
    sys.path.insert(0, str(ROOT / "scripts"))
    from banc_artefacts import STAGE

    (sortie / "SOURCE du résumé.txt").write_text("Le document de test que les résumés résument :\n\n" + "\n\n".join(STAGE) + "\n",
                                                encoding="utf-8")
    cle.parent.mkdir(parents=True, exist_ok=True)
    cle.write_text(json.dumps([{k: p[k] for k in ("lettre", "modele", "tache")} for p in productions],
                              ensure_ascii=False, indent=1), encoding="utf-8")
    return sortie


def reveler(cle: pathlib.Path, grille: pathlib.Path) -> dict:
    corr = {x["lettre"]: x for x in json.loads(cle.read_text(encoding="utf-8"))}
    notes: dict[str, list[int]] = {}
    for ligne in grille.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z]) — note : (\d)", ligne.strip())
        if m and m.group(1) in corr:
            notes.setdefault(corr[m.group(1)]["modele"], []).append(int(m.group(2)))
    return {mod: {"notes": n, "moyenne": round(sum(n) / len(n), 2)} for mod, n in notes.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("preparer")
    p.add_argument("--banc", required=True)
    p.add_argument("--modeles", required=True)
    p.add_argument("--cle", required=True)
    r = sp.add_parser("reveler")
    r.add_argument("--cle", required=True)
    r.add_argument("--grille", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "preparer":
        print(preparer(pathlib.Path(a.banc), a.modeles.split(","), pathlib.Path(a.cle)))
    else:
        print(json.dumps(reveler(pathlib.Path(a.cle), pathlib.Path(a.grille)), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
