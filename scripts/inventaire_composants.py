"""
Sprint Check-up / CK1 — inventaire des composants d'Atlas, en deux mesures croisées.

1. statique : chaque paquet installé dans le venv, déclaré ou non dans requirements.txt, et le
   code qui l'importe (analyse des imports de main.py, api/, core/, core_conversational/,
   tools/, desktop/, scripts/) ;
2. dynamique : les modules Python réellement chargés par des processus Atlas réels (fichiers
   écrits par ATLAS_MODULES_DUMP, voir main.py et tools/ocr_worker.py), rapportés aux paquets.

    python scripts/inventaire_composants.py statique --out statique.json
    python scripts/inventaire_composants.py croise --statique statique.json --dynamique d1.json d2.json --out inventaire.json
    python scripts/inventaire_composants.py markdown --croise inventaire.json --out tableau.md

Ne modifie rien.
"""

from __future__ import annotations

import argparse
import ast
import importlib.metadata as md
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODE_DIRS = ("api", "core", "core_conversational", "tools", "desktop", "scripts")
EXCLUS = ("scripts/manual/",)


def _norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def requirements() -> dict[str, str]:
    out = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            out[_norm(re.split(r"[<>=\[ ;!~]", line)[0])] = line
    return out


def distributions() -> dict[str, md.Distribution]:
    return {_norm(d.metadata["Name"]): d for d in md.distributions()}


def _requires(d: md.Distribution, extras: set[str]) -> set[str]:
    out = set()
    for r in d.requires or []:
        m = re.search(r"extra\s*==\s*['\"]([^'\"]+)['\"]", r)
        if m and m.group(1) not in extras:
            continue
        out.add(_norm(re.split(r"[<>=!~;\[ (]", r)[0]))
    return out


def provenance(dists, reqs) -> dict[str, str]:
    """déclaré | dépendance de <paquet déclaré> | orphelin."""
    origine = {n: "déclaré" for n in reqs if n in dists}
    todo = []
    for n, line in reqs.items():
        extras = set(re.findall(r"\[([^\]]+)\]", line)[0].split(",")) if "[" in line else set()
        todo.append((n, extras, n))
    seen = set()
    while todo:
        n, extras, racine = todo.pop()
        if (n, racine) in seen or n not in dists:
            continue
        seen.add((n, racine))
        for dep in _requires(dists[n], extras):
            if dep in dists:
                origine.setdefault(dep, f"dépendance de {racine}")
                todo.append((dep, set(), racine))
    return {n: origine.get(n, "orphelin") for n in dists}


def imports_du_code() -> dict[str, set[str]]:
    """module de premier niveau → fichiers qui l'importent (au niveau module OU dans une fonction)."""
    out: dict[str, set[str]] = {}
    fichiers = [ROOT / "main.py"] + [p for d in CODE_DIRS for p in (ROOT / d).rglob("*.py")]
    for f in fichiers:
        rel = str(f.relative_to(ROOT)).replace("\\", "/")
        if rel.startswith(EXCLUS):
            continue
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                noms = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                noms = [node.module]
            else:
                continue
            for n in noms:
                out.setdefault(n.split(".")[0], set()).add(rel)
    return out


def module_vers_paquets() -> dict[str, list[str]]:
    return {k: [_norm(x) for x in v] for k, v in md.packages_distributions().items()}


def statique() -> dict:
    dists, reqs = distributions(), requirements()
    prov = provenance(dists, reqs)
    m2p = module_vers_paquets()
    importe_par: dict[str, set[str]] = {}
    for module, fichiers in imports_du_code().items():
        for p in m2p.get(module, []):
            importe_par.setdefault(p, set()).update(fichiers)
    lignes = []
    for n, d in sorted(dists.items()):
        lignes.append({"paquet": n, "version": d.version, "provenance": prov[n],
                       "importe_par": sorted(importe_par.get(n, set()))})
    return {"paquets": lignes, "requirements": reqs}


def croise(stat: dict, dynamiques: list[dict]) -> dict:
    m2p = module_vers_paquets()
    charges: dict[str, set[str]] = {}
    for dyn in dynamiques:
        for module in dyn.get("modules", []):
            for p in m2p.get(module.split(".")[0], []):
                charges.setdefault(p, set()).add(dyn.get("processus", "?"))
    for ligne in stat["paquets"]:
        ligne["charge_par"] = sorted(charges.get(ligne["paquet"], set()))
    return stat


def markdown(croise_json: dict) -> str:
    """Le tableau complet (annexe du rapport) : un paquet par ligne."""
    lignes = ["| Paquet | Version | Déclaré où | Importé par le code | Chargé en exécution (processus) |",
              "|---|---|---|---|---|"]
    for p in croise_json["paquets"]:
        imp = p["importe_par"]
        imp_txt = (f"{len(imp)} fichier(s) : " + ", ".join(f"`{x}`" for x in imp[:3]) + (" …" if len(imp) > 3 else "")) \
            if imp else "—"
        charge = ", ".join(p.get("charge_par", [])) or "**jamais**"
        lignes.append(f"| {p['paquet']} | {p['version']} | {p['provenance']} | {imp_txt} | {charge} |")
    return "\n".join(lignes) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("statique")
    s.add_argument("--out", required=True)
    c = sub.add_parser("croise")
    c.add_argument("--statique", required=True)
    c.add_argument("--dynamique", nargs="+", required=True)
    c.add_argument("--out", required=True)
    m = sub.add_parser("markdown")
    m.add_argument("--croise", required=True)
    m.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "markdown":
        texte = markdown(json.loads(pathlib.Path(a.croise).read_text(encoding="utf-8")))
        pathlib.Path(a.out).write_text(texte, encoding="utf-8")
        print(f"→ {a.out}")
        return 0
    if a.cmd == "statique":
        res = statique()
    else:
        res = croise(json.loads(pathlib.Path(a.statique).read_text(encoding="utf-8")),
                     [json.loads(pathlib.Path(p).read_text(encoding="utf-8")) for p in a.dynamique])
    pathlib.Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(res['paquets'])} paquets → {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
