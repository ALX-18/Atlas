"""
Sprint Fiabilité / FI1 — la route que prend une demande, sans rien exécuter ni appeler le modèle.

Même chemin que /api/chat : classifieur → (conversation | plan | validateur → outil). Le corpus
`tests/fixtures/corpus_routes.json` donne, pour chaque demande, la route attendue :

    {"phrase": …, "famille": …, "attendu": {"route": "outil", "outil": "schedule_list", "cible": "…"}}

Routes : « outil » (un outil du moteur), « conversation » (le modèle répond, aucun outil),
« honnete » (réponse fixe « Je ne sais pas encore faire ça. »), « fixe » (capacités, « fais-le »),
« refus » (le validateur refuse et dit pourquoi), « plan » (plusieurs étapes, planificateur).

    python scripts/mesure_routes.py [--corpus tests/fixtures/corpus_routes.json] [--out mesure.json]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import unicodedata
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CORPUS = ROOT / "tests" / "fixtures" / "corpus_routes.json"

# Contexte fixe : la route ne doit pas dépendre de la fenêtre au premier plan du moment.
CONTEXTE = {"foreground_window": {"title": "", "process": ""}}


def route(phrase: str) -> dict:
    from core.intent_classifier import get_classifier
    from core.validator import get_validator

    intent = get_classifier().classify(phrase, dict(CONTEXTE))
    base = {"categorie": intent.category, "verbe": intent.verb}
    if intent.category == "conversation" or intent.confidence < 0.5:
        return {**base, "route": "conversation", "outil": None}
    if intent.is_complex:
        return {**base, "route": "plan", "outil": None}
    res = get_validator().resolve(intent, dict(CONTEXTE))
    if res.tool == "__conversation__":
        return {**base, "route": "refus" if getattr(res, "rejected", False) else "conversation", "outil": None}
    if res.tool in ("__capabilities__", "__followup__"):
        return {**base, "route": "fixe", "outil": res.tool}
    if res.tool == "__unsupported__":
        return {**base, "route": "honnete", "outil": None}
    return {**base, "route": "outil", "outil": res.tool, "params": res.params}


def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def conforme(obtenu: dict, attendu: dict) -> bool:
    if obtenu["route"] != attendu["route"]:
        return False
    if attendu.get("outil") and obtenu.get("outil") != attendu["outil"]:
        return False
    cible = attendu.get("cible")
    if cible:
        valeurs = " ".join(str(v) for v in (obtenu.get("params") or {}).values())
        return _sans_accents(cible) in _sans_accents(valeurs)
    return True


# Outils qui ne font que LIRE ou décrire : rien ne change sur le PC, dans la mémoire, au dehors.
OUTILS_LECTURE = {"memory_recall", "workflow_describe", "workflow_list", "schedule_list", "list_processes",
                  "window_list", "get_diagnostics", "screen_read"}


def gravite(obtenu: dict, attendu: dict) -> str | None:
    """La plus grave : un outil qui AGIT alors qu'on attendait une conversation ou une réponse honnête.
    Une mauvaise route vers un outil de lecture seule reste une erreur, de gravité ordinaire."""
    if conforme(obtenu, attendu):
        return None
    if attendu["route"] in ("conversation", "honnete", "fixe", "refus") and (
            obtenu["route"] == "plan" or (obtenu["route"] == "outil" and obtenu.get("outil") not in OUTILS_LECTURE)):
        return "action_a_tort"
    return "mauvaise_route"


def mesurer(corpus: list[dict]) -> dict:
    par_famille: dict = defaultdict(lambda: {"total": 0, "ok": 0})
    erreurs = []
    for item in corpus:
        obtenu = route(item["phrase"])
        g = gravite(obtenu, item["attendu"])
        f = par_famille[item["famille"]]
        f["total"] += 1
        if g is None:
            f["ok"] += 1
        else:
            erreurs.append({"phrase": item["phrase"], "famille": item["famille"], "attendu": item["attendu"],
                            "obtenu": {k: v for k, v in obtenu.items() if k != "params"} |
                                      {"params": obtenu.get("params")}, "gravite": g})
    total = sum(f["total"] for f in par_famille.values())
    ok = sum(f["ok"] for f in par_famille.values())
    return {"total": total, "ok": ok, "taux": round(100 * ok / total, 1) if total else 0.0,
            "actions_a_tort": sum(e["gravite"] == "action_a_tort" for e in erreurs),
            "par_famille": {k: {**v, "taux": round(100 * v["ok"] / v["total"], 1)} for k, v in sorted(par_famille.items())},
            "erreurs": erreurs}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(CORPUS))
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    res = mesurer(json.loads(pathlib.Path(a.corpus).read_text(encoding="utf-8")))
    texte = json.dumps(res, ensure_ascii=False, indent=1, default=str)
    if a.out:
        pathlib.Path(a.out).write_text(texte, encoding="utf-8")
    print(f"{res['ok']}/{res['total']} bonnes routes ({res['taux']} %) ; actions à tort : {res['actions_a_tort']}")
    for fam, v in res["par_famille"].items():
        print(f"  {fam:<28} {v['ok']:>3}/{v['total']:<3} {v['taux']:>5} %")
    for e in res["erreurs"]:
        print(f"  ✗ [{e['gravite']}] {e['phrase']!r} : attendu {e['attendu']} — obtenu "
              f"{e['obtenu']['route']}/{e['obtenu'].get('outil')} ({e['obtenu']['categorie']}/{e['obtenu']['verbe']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
