"""
Sprint Artefacts sur mesure / AS5 et AS3 — banc réel, sur le vrai modèle d'Atlas (qwen2.5:7b).

    python scripts/banc_sur_mesure.py --out <dossier> [--parties consignes,retouches,resumes,jugement]

- consignes : 20 demandes avec consignes (longueur, parties, langue, tableau, sommaire, puces, titre,
  format…) ; chaque consigne VÉRIFIABLE est contrôlée par programme sur le document produit ;
- retouches : 10 retouches sur ces documents ; la retouche est faite (vérifiée), la version précédente
  reste (empreinte), le changement est dit ;
- resumes (AS3) : les résumés du banc de modèles, ancienne consigne puis nouvelle : part des chiffres,
  dates et noms de la source CONSERVÉS, faits inventés livrés (doit rester 0) ;
- jugement : 6 documents (4 demandes variées, 2 retouches) dans Documents\\Atlas\\Jugement_sur_mesure\\,
  avec la demande de chacun et une grille (note 1 à 5, « il a suivi ma demande : oui / non »).

Les documents de mesure vont dans <dossier>/documents (jamais Documents\\Atlas), sauf les 6 du jugement.
Données d'Atlas : des copies (tests/banc_donnees.py, garde BM0).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))

DEMANDES = [
    "fais-moi un rapport sur le réchauffement climatique en 3 parties : introduction, les causes, conclusion",
    "rédige une note de synthèse de 300 mots sur le télétravail pour mon patron",
    "fais une fiche de révision sur la Révolution française avec un tableau des dates importantes",
    "écris un document en anglais d'environ 250 mots sur les énergies renouvelables",
    "prépare un plan de cours sur le cycle de l'eau pour des élèves de CM2, simple, sans sommaire",
    "rédige un rapport de moins de 400 mots sur l'histoire d'internet, sans introduction",
    "fais un document en 4 parties sur les bienfaits du sport",
    "rédige un exposé sur les volcans avec une conclusion, sans liste à puces",
    "fais une fiche pratique sur le compostage avec un tableau, en PDF",
    "écris un texte de 150 mots sur l'automne",
    "fais un rapport intitulé « Le vélo en ville » en 3 parties",
    "rédige un document sur l'alimentation équilibrée en 2 parties : les aliments, les repas",
    "fais une note courte sur la sécurité des mots de passe",
    "rédige une lettre formelle pour mon propriétaire pour signaler une fuite, sans liste à puces",
    "fais un rapport détaillé sur l'intelligence artificielle dans la santé",
    "écris un document en espagnol de 200 mots sur la cuisine française",
    "fais une fiche sur les planètes du système solaire avec un tableau, sans sommaire",
    "rédige un rapport sur le recyclage en 5 parties, avec un sommaire",
    "fais un document d'une page sur la photosynthèse",
    "rédige une lettre de motivation pour un stage en informatique, formelle, de moins de 350 mots",
]
SIGNATURE = {"nom": "Camille Martin", "adresse": "8 rue des Peupliers, 69003 Lyon"}       # fictive
RETOUCHES = [  # (indice de la demande, opération, paramètres)
    (0, "ajouter", {"objet": "les solutions"}), (6, "raccourcir", {}), (11, "developper", {"rang": 2}),
    (1, "ton", {"valeur": "simple"}), (7, "enlever", {"objet": "conclusion"}), (10, "titre", {"valeur": "Pédaler en ville"}),
    (12, "corriger", {}), (9, "pdf", {}), (3, "ajouter", {"objet": "the challenges"}), (17, "enlever", {"objet": "sommaire"}),
]
JUGEMENT = [
    "rédige une lettre formelle pour mon voisin pour lui demander de baisser la musique le soir, une demi-page",
    "fais une fiche de révision sur la Seconde Guerre mondiale avec un tableau des dates, sans sommaire",
    "prépare un plan de cours sur les fractions pour des élèves de CM1, en 3 parties : découvrir, manipuler, s'entraîner",
    "écris un document de 300 mots sur les bienfaits de la lecture, sans liste à puces",
]
JUGEMENT_RETOUCHES = [(1, "ajouter", {"objet": "les causes de la guerre"}), (3, "ton", {"valeur": "simple"})]
ITEMS = {"longueur": ("mots_min", "mots_max", "pages", "lignes"), "structure": ("nb_parties", "parties"),
         "langue": ("langue",), "tableau": ("tableau",), "sommaire": ("sommaire",), "conclusion": ("conclusion",),
         "introduction": ("introduction",), "puces": ("puces",), "titre": ("titre",)}


def _sha(p) -> str:
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def produire_demande(demande: str) -> dict:
    """Une demande → le document, par le code d'Atlas (comme creer, sans l'arrière-plan)."""
    from core import artefacts as ar
    from core import specification as sp
    from core.intent_classifier import get_classifier
    from tools import documents as d

    i = get_classifier().classify(demande, {})
    spec = sp.extraire(demande)
    t0 = time.perf_counter()
    nature = (i.params or {}).get("type") or spec.get("genre") or "document"
    if nature == "lettre":
        contenu, raison, ecarts = ar.rediger_lettre(demande, spec, dict(SIGNATURE))
        pied = d.PIED_RAPPORT
    else:
        contenu, raison, ecarts = ar.rediger_document(demande, (i.params or {}).get("sujet") or demande, spec)
        pied = d.PIED_RAPPORT
    ligne = {"demande": demande, "route": f"{i.category}/{i.verb}", "spec": spec, "s": None, "ok": bool(contenu),
             "raison": raison}
    if not contenu:
        ligne["s"] = round(time.perf_counter() - t0, 1)
        return ligne
    rendu: dict = {}
    faits, raison = ar.produire(contenu, spec.get("formats") or ["docx"], pied, sommaire=spec.get("sommaire"), rendu=rendu)
    ligne["s"] = round(time.perf_counter() - t0, 1)
    ligne["fichiers"] = [str(f) for f in faits]
    ligne["raison"] = raison
    ligne["mots"] = sp.mots(contenu)
    ligne["parties"] = [s["titre"] for s in contenu["sections"]]
    # Vérification par consigne : chaque item vérifiable, à part
    items = {}
    for nom, cles in ITEMS.items():
        sous = {k: spec[k] for k in cles if k in spec}
        if not sous:
            continue
        if nom == "sommaire" and contenu.get("genre") == "lettre":
            continue
        e = sp.verifier(contenu, sous, rendu.get(".docx"))
        items[nom] = {"respecte": not e, "ecarts": e}
    if spec.get("formats"):
        items["format"] = {"respecte": all(any(f.endswith("." + x) for f in ligne["fichiers"]) for x in spec["formats"]),
                           "ecarts": []}
    ligne["items"] = items
    ligne["non_verifiables"] = [k for k in ("ton", "public") if k in spec]
    ligne["ecarts_dits"] = ecarts
    ar._retenir_dernier(contenu, faits, spec, pied)
    return ligne


def p_consignes(sortie: pathlib.Path) -> dict:
    lignes = []
    for k, demande in enumerate(DEMANDES, 1):
        l = produire_demande(demande)
        lignes.append(l)
        resp = sum(v["respecte"] for v in (l.get("items") or {}).values())
        print(f"[consignes {k}/20] {l['s']} s — {resp}/{len(l.get('items') or {})} — {demande[:60]}", flush=True)
    total = sum(len(l.get("items") or {}) for l in lignes)
    tenus = sum(sum(v["respecte"] for v in (l.get("items") or {}).values()) for l in lignes)
    return {"documents": len(lignes), "produits": sum(l["ok"] for l in lignes), "items": total, "respectes": tenus,
            "taux_pct": round(100 * tenus / total, 1) if total else None,
            "documents_tout_respecte": sum(bool(l.get("items")) and all(v["respecte"] for v in l["items"].values())
                                           for l in lignes),
            "ecarts_non_dits": sum(1 for l in lignes for v in (l.get("items") or {}).values()
                                   if not v["respecte"] and not l.get("ecarts_dits") and "format" not in v),
            "detail": lignes}


def p_retouches(consignes: dict) -> dict:
    from core import artefacts as ar
    from core import specification as sp
    from tools import documents as d

    lignes = []
    for k, op, params in RETOUCHES:
        doc = consignes["detail"][k]
        docx_ = next((f for f in doc.get("fichiers") or [] if f.endswith(".docx")), None)
        ligne = {"demande": doc["demande"], "operation": op, "params": params}
        if not docx_:
            ligne.update({"ok": False, "raison": "document source absent (PDF seul ou échec)"})
            lignes.append(ligne)
            continue
        empreinte = _sha(docx_)
        cible, rep = ar._cible_retouche({"document_chemin": docx_})
        avant = cible["contenu"]
        t0 = time.perf_counter()
        message = ar._faire_retouche(op, cible, params)
        ligne["s"] = round(time.perf_counter() - t0, 1)
        ligne["message"] = message
        ligne["ancienne_intacte"] = _sha(docx_) == empreinte
        dit = message.startswith(("J'ai", "Je l'ai"))
        ligne["dit"] = dit
        nouveau = ar._dernier.get("docx") if op != "pdf" else ar._dernier.get("pdf")
        fait = False
        if dit and op == "pdf":
            fait = bool(ar._dernier.get("pdf")) and pathlib.Path(ar._dernier["pdf"]).exists()
        elif dit and nouveau and pathlib.Path(nouveau).exists():
            apres, _ = d.lire_docx(pathlib.Path(nouveau))
            n_av, n_ap = len(avant["sections"]), len(apres["sections"])
            fait = {"ajouter": n_ap == n_av + 1, "enlever": n_ap == n_av - 1 or params.get("objet") == "sommaire",
                    "titre": apres["titre"] == params.get("valeur"),
                    "raccourcir": sp.mots(apres) < sp.mots(avant), "developper": sp.mots(apres) > sp.mots(avant),
                    "ton": [s["paragraphes"] for s in apres["sections"]] != [s["paragraphes"] for s in avant["sections"]],
                    "corriger": abs(sp.mots(apres) - sp.mots(avant)) <= max(10, sp.mots(avant) // 10)}.get(op, False)
            ligne["nouvelle_version"] = str(nouveau)
        ligne["ok"] = bool(fait and ligne["ancienne_intacte"] and dit)
        lignes.append(ligne)
        print(f"[retouche] {op} : {'OK' if ligne['ok'] else 'NON'} — {message[:120]}", flush=True)
    return {"n": len(lignes), "reussies": sum(l["ok"] for l in lignes),
            "anciennes_intactes": sum(bool(l.get("ancienne_intacte")) for l in lignes if "ancienne_intacte" in l),
            "dites_sans_etre_faites": sum(1 for l in lignes if l.get("dit") and not l["ok"]), "detail": lignes}


def p_resumes() -> dict:
    from banc_modeles import _documents_sources
    from core import artefacts as ar
    from tools import documents as d

    lignes = []
    for consigne_nom, consigne in (("avant", ar.CONSIGNE_FAITS_RESUME_AVANT), ("apres", ar.CONSIGNE_FAITS_RESUME)):
        for cle, (nom, texte) in _documents_sources().items():
            for essai in range(1, 4):
                t0 = time.perf_counter()
                contenu, raison, retirees = ar.rediger_resume(texte, nom, consigne_faits=consigne)
                l = {"consigne": consigne_nom, "source": cle, "essai": essai, "ok": bool(contenu),
                     "s": round(time.perf_counter() - t0, 1), "retirees": len(retirees)}
                if contenu:
                    g, n, absents = ar.faits_conserves(contenu, texte)
                    # texte par texte (titre, parties, paragraphes) : recollés, un titre de partie suivi d'un
                    # paragraphe passait pour un nom propre en milieu de phrase (« Contexte », « Livraison »)
                    inventes = list(dict.fromkeys(f for t in d._textes(contenu) for f in d.faits_absents(t, texte)))
                    l.update({"conserves": g, "cles": n, "taux_pct": round(100 * g / n) if n else None,
                              "inventes_livres": len(inventes), "inventes": inventes, "absents": absents[:12]})
                lignes.append(l)
                print(f"[résumé {consigne_nom}] {cle} {essai} : {l.get('taux_pct')} % conservés, "
                      f"{l.get('inventes_livres')} inventé(s) livré(s)", flush=True)

    def moyenne(nom):
        x = [l for l in lignes if l["consigne"] == nom and l.get("cles")]
        return round(100 * sum(l["conserves"] for l in x) / sum(l["cles"] for l in x), 1) if x else None

    return {"conserves_avant_pct": moyenne("avant"), "conserves_apres_pct": moyenne("apres"),
            "inventes_livres": sum(l.get("inventes_livres") or 0 for l in lignes), "detail": lignes}


def p_jugement() -> dict:
    """6 documents pour Alexis : 4 demandes, puis 2 retouches ; la demande de chacun, une grille."""
    import random
    import shutil
    import string

    from core import artefacts as ar
    from tools import documents as d

    dossier = d.dossier_documents() / "Atlas" / "Jugement_sur_mesure"
    if dossier.exists():
        shutil.rmtree(dossier)
    dossier.mkdir(parents=True)
    faits = []
    for demande in JUGEMENT:
        l = produire_demande(demande)
        faits.append({"demande": demande, "fichier": next((f for f in l.get("fichiers") or [] if f.endswith(".docx")), None),
                      "ecarts": l.get("ecarts_dits")})
    for k, op, params in JUGEMENT_RETOUCHES:
        source = faits[k]["fichier"]
        cible, _ = ar._cible_retouche({"document_chemin": source})
        message = ar._faire_retouche(op, cible, params)
        texte_op = {"ajouter": f"rajoute une partie sur {params.get('objet')}", "ton": "rends-le plus simple"}[op]
        faits.append({"demande": texte_op, "source": k, "fichier": str(ar._dernier.get("docx")), "message": message})
    lettres = random.Random(24).sample(string.ascii_uppercase[:6], 6)
    for f in faits:
        if "source" in f:
            f["demande"] = f"(retouche du document {lettres[f['source']]}) {f['demande']}"
    grille = ["Jugement des documents sur mesure — pour chacun : une note de 1 à 5, et « il a suivi ma demande : oui / non ».",
              "Chaque fichier lettre (A.docx…) a sa demande juste en dessous ; les retouches sont signalées.", ""]
    correspondance = []
    for lettre, f in sorted(zip(lettres, faits), key=lambda x: x[0]):
        if f["fichier"] and pathlib.Path(f["fichier"]).exists():
            shutil.copy2(f["fichier"], dossier / f"{lettre}.docx")
        grille += [f"{lettre} — demande : « {f['demande']} »", f"   note : _ — il a suivi ma demande : _ — commentaire : ", ""]
        correspondance.append({"lettre": lettre, **f})
    (dossier / "GRILLE.txt").write_text("\n".join(grille), encoding="utf-8")
    return {"dossier": str(dossier), "documents": correspondance}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--parties", default="consignes,retouches,resumes,jugement")
    a = ap.parse_args(argv)
    from banc_donnees import donnees_jetables

    donnees_jetables(prefixe="atlas_sur_mesure_")          # BM0 : avant tout import de core
    from tools import documents as d

    sortie = pathlib.Path(a.out)
    (sortie / "documents").mkdir(parents=True, exist_ok=True)
    d.dossier_atlas = lambda: sortie / "documents"           # documents de mesure : jamais Documents\Atlas
    from tools import fichiers as tf

    tf._ouvrir_systeme = lambda chemin: None                 # rien ne s'ouvre à l'écran pendant une mesure
    parties = a.parties.split(",")
    res: dict = {"debut": time.strftime("%Y-%m-%d %H:%M:%S")}
    fichier = sortie / "banc_sur_mesure.json"
    if fichier.exists():
        res.update(json.loads(fichier.read_text(encoding="utf-8")))

    def garder():
        fichier.write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    if "consignes" in parties:
        res["consignes"] = p_consignes(sortie)
        garder()
    if "retouches" in parties:
        res["retouches"] = p_retouches(res["consignes"])
        garder()
    if "resumes" in parties:
        res["resumes"] = p_resumes()
        garder()
    if "jugement" in parties:
        # Produits dans le dossier jetable ; seules les 6 copies (A à F) vont dans Documents\Atlas\Jugement_sur_mesure.
        res["jugement"] = p_jugement()
        garder()
    from core import artefacts as ar

    res["erreurs"] = list(ar.JOURNAL_ERREURS)
    garder()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
