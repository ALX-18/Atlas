"""
Sprint Installeur / IN4 — le banc de non-régression du modèle, en une commande.

    python scripts/non_regression_modele.py                  # le modèle d'Atlas, comparé à sa référence
    python scripts/non_regression_modele.py --enregistrer    # (Alexis) enregistre la référence de ce modèle

Il rejoue, par le code d'Atlas (scripts/banc_modeles.py, données jetables, garde BM0) : GB1 (aucune affirmation
d'action sans outil), les plans, les documents et les faits inventés, les consignes, la conversation en français.
Chaque mesure est comparée à la référence du modèle (config/reference_non_regression.json). Un banc réussi est
noté dans data/non_regression.json, avec la version d'Ollama et l'empreinte du modèle : `doctor.py` signale si
Ollama a changé de version depuis.

Code de sortie : 0 vert, 1 rouge (une mesure sous la référence), 2 banc impossible.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "config" / "reference_non_regression.json"
DERNIER = ROOT / "data" / "non_regression.json"
PARTIES = "gb1,plans,documents,consignes,conversation"
OLLAMA = "http://127.0.0.1:11434"
PY = str(ROOT / ".venv" / "Scripts" / "python.exe") if (ROOT / ".venv").exists() else sys.executable


def _get(chemin: str) -> dict:
    with urllib.request.urlopen(OLLAMA + chemin, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def mesures(res: dict) -> dict:
    """Les chiffres comparés, tirés du résultat de banc_modeles (une partie en erreur → None)."""
    def p(nom):
        v = res.get(nom) or {}
        return None if "erreur" in v else v

    g, pl, d, c, cv = p("gb1"), p("plans"), p("documents"), p("consignes"), p("conversation")
    detail_docs = (d or {}).get("detail") or []
    return {
        "gb1_affirmations_sans_outil": None if g is None else g["affirmations_sans_outil"],
        "gb1_ordinaires_bloquees": None if g is None else g["ordinaires_bloquees"],
        "plans_valides_pct": None if pl is None else pl["plans_valides_pct"],
        "documents_reussis": None if d is None else f"{d['ok']}/{d['n']}",
        "documents_faits_inventes_livres": None if d is None else sum(x.get("faits_absents_livres") or 0
                                                                    for x in detail_docs),
        "consignes_respectees": None if c is None else c["respectees"],
        "conversation_en_francais": None if cv is None else f"{cv['francais']}/{cv['n']}",
        "conversation_ecriture_non_latine": None if cv is None else cv["non_latin"],
        "fuites_de_reflexion": None if None in (pl, c, cv) else pl["fuites"] + c["fuites"] + cv["fuites"],
    }


def _frac(s: str) -> tuple[int, int]:
    a, b = s.split("/")
    return int(a), int(b)


def comparer(m: dict, ref: dict) -> list[str]:
    """Les écarts (vide : vert). Zéro reste zéro ; les taux ont une tolérance écrite dans la référence."""
    ecarts = []
    for cle in ("gb1_affirmations_sans_outil", "gb1_ordinaires_bloquees", "documents_faits_inventes_livres",
                "conversation_ecriture_non_latine", "fuites_de_reflexion"):
        if m.get(cle) is None:
            ecarts.append(f"{cle} : partie impossible")
        elif m[cle] > ref.get(cle, 0):
            ecarts.append(f"{cle} : {m[cle]} (référence {ref.get(cle, 0)})")
    tol = ref.get("tolerance", {})
    if m.get("plans_valides_pct") is None or m["plans_valides_pct"] < ref["plans_valides_pct"] - tol.get("plans_pct", 10):
        ecarts.append(f"plans_valides_pct : {m.get('plans_valides_pct')} % (référence {ref['plans_valides_pct']} %)")
    if m.get("consignes_respectees") is None or m["consignes_respectees"] < ref["consignes_respectees"] - tol.get("consignes", 1):
        ecarts.append(f"consignes_respectees : {m.get('consignes_respectees')} (référence {ref['consignes_respectees']})")
    for cle, marge in (("documents_reussis", tol.get("documents", 0)), ("conversation_en_francais", tol.get("francais", 0))):
        if m.get(cle) is None:
            ecarts.append(f"{cle} : partie impossible")
            continue
        a, n = _frac(m[cle])
        ra, rn = _frac(ref[cle])
        if n != rn or a < ra - marge:
            ecarts.append(f"{cle} : {m[cle]} (référence {ref[cle]})")
    return ecarts


def main(argv=None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--modele", help="par défaut, celui de config/settings.json")
    ap.add_argument("--out", help="dossier du banc (par défaut, un dossier daté dans data/non_regression)")
    ap.add_argument("--enregistrer", action="store_true", help="enregistrer ce banc comme référence du modèle")
    ap.add_argument("--resultat", help="(tests) relire un resultat.json au lieu de lancer le banc")
    a = ap.parse_args(argv)

    modele = a.modele or json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))["ollama"]["model"]
    try:
        version = _get("/api/version").get("version")
        tags = _get("/api/tags").get("models", [])
    except Exception as e:
        print(f"Banc impossible : Ollama ne répond pas ({e}).")
        return 2
    digest = next((t.get("digest") for t in tags if t.get("name") == modele), None)
    if not digest:
        print(f"Banc impossible : le modèle {modele} n'est pas installé dans Ollama.")
        return 2

    if a.resultat:
        res = json.loads(pathlib.Path(a.resultat).read_text(encoding="utf-8"))
        dossier = pathlib.Path(a.resultat).parent
    else:
        dossier = pathlib.Path(a.out) if a.out else ROOT / "data" / "non_regression" / time.strftime("%Y%m%d_%H%M%S")
        dossier.mkdir(parents=True, exist_ok=True)
        print(f"Banc de non-régression : {modele} (Ollama {version}) — {PARTIES}. Environ 5 minutes avec une carte graphique (mesuré le 06/11), bien plus sur le processeur.", flush=True)
        subprocess.run([PY, "-u", str(ROOT / "scripts" / "banc_modeles.py"), "--out", str(dossier), "--modeles", modele,
                        "--parties", PARTIES], cwd=ROOT, check=False)
        fichier = dossier / modele.replace(":", "_").replace("/", "_") / "resultat.json"
        if not fichier.exists():
            print(f"Banc impossible : pas de résultat ({fichier}).")
            return 2
        res = json.loads(fichier.read_text(encoding="utf-8"))
    m = mesures(res)

    references = json.loads(REFERENCE.read_text(encoding="utf-8")) if REFERENCE.exists() else {"modeles": {}}
    if a.enregistrer:
        if None in m.values():
            print("Référence refusée : une partie du banc a échoué.", json.dumps(m, ensure_ascii=False))
            return 1
        references.setdefault("modeles", {})[modele] = {
            **m, "tolerance": {"plans_pct": 10, "consignes": 1, "documents": 0, "francais": 0},
            "ollama": version, "digest": digest, "date": time.strftime("%Y-%m-%d")}
        REFERENCE.write_text(json.dumps(references, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
        print(f"Référence de {modele} enregistrée (Ollama {version}).")
    ref = references.get("modeles", {}).get(modele)
    if not ref:
        print(f"Pas de référence pour {modele} : relancer avec --enregistrer (décision d'Alexis).")
        return 2
    ecarts = comparer(m, ref)
    for cle, v in m.items():
        print(f"  {cle:<36} {v}   (référence {ref.get(cle)})")
    if ecarts:
        print("ROUGE — sous la référence :")
        for e in ecarts:
            print(f"  - {e}")
        return 1
    DERNIER.parent.mkdir(parents=True, exist_ok=True)
    DERNIER.write_text(json.dumps({"date": time.strftime("%Y-%m-%d %H:%M:%S"), "modele": modele, "digest": digest,
                                   "ollama": version, "mesures": m, "dossier": str(dossier)},
                                  ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"VERT — {modele} tient sa référence avec Ollama {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
