"""
Sprint Artefacts — Atlas rédige des documents Word et PDF : rapports structurés, résumés d'un
fichier du PC, comptes rendus.

La boucle contrôlée s'applique : le modèle RÉDIGE un contenu structuré (JSON imposé par un schéma) ;
`tools/documents.py`, déterministe, le VALIDE, PRODUIT le fichier, le RELIT. Atlas ne dit « j'ai
créé » qu'après cette relecture ; sinon l'échec est dit.

- Ce qui manque est DEMANDÉ, jamais inventé : le sujet d'un rapport ; le fichier à résumer ;
  la date et les participants d'un compte rendu.
- Un rapport vient des connaissances du modèle local (sans internet) : le pied de page le dit.
- Un résumé n'invente rien : chaque phrase qui cite un nombre, une date ou un nom propre absent du
  document source est RETIRÉE, et Atlas dit combien (choix : retirer plutôt que signaler dans le
  texte — un document présenté ne doit pas contenir de fait faux, même balisé).
- Rédiger est long : la réponse dit tout de suite « je rédige…, environ N secondes » ; le travail
  se fait en arrière-plan ; la fin est annoncée (core/annonces.py : fenêtre, notification, voix).
- Documents longs : section par section (rapport), morceaux puis synthèse (résumé), dans la
  limite de num_ctx (8 192).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import threading
import time
from typing import Any, Callable, Optional

import httpx

logger = logging.getLogger("atlas.artefacts")

MORCEAU_CARACTERES = 6000          # un morceau + sa consigne tiennent largement dans 8 192 jetons
# Estimations annoncées, mesurées au banc (rapport Artefacts) : un appel de section ~7 s, un morceau ~6 s.
SECONDES_PAR_SECTION = 7
SECONDES_PAR_MORCEAU = 6
_occupe = threading.Lock()
_en_cours: Optional[str] = None

SYSTEME = ("Tu es Atlas, l'assistant d'Alexis. Tu rédiges en FRANÇAIS, de façon claire et sobre. Tu réponds "
           "UNIQUEMENT par le JSON demandé, sans texte autour.")

SCHEMA_PLAN = {"type": "object", "properties": {"titre": {"type": "string"},
               "sections": {"type": "array", "items": {"type": "string"}}}, "required": ["titre", "sections"]}
SCHEMA_SECTION = {"type": "object", "properties": {"paragraphes": {"type": "array", "items": {"type": "string"}},
                  "points": {"type": "array", "items": {"type": "string"}}}, "required": ["paragraphes"]}
SCHEMA_POINTS = {"type": "object", "properties": {"points": {"type": "array", "items": {"type": "string"}}},
                 "required": ["points"]}
SCHEMA_DOCUMENT = {"type": "object", "properties": {
    "titre": {"type": "string"},
    "sections": {"type": "array", "items": {"type": "object", "properties": {
        "titre": {"type": "string"}, "paragraphes": {"type": "array", "items": {"type": "string"}},
        "points": {"type": "array", "items": {"type": "string"}}}, "required": ["titre", "paragraphes"]}},
    "points_cles": {"type": "array", "items": {"type": "string"}}}, "required": ["titre", "sections"]}


# --------------------------------------------------------------------------- #
#  Le modèle (remplacé par les tests)
# --------------------------------------------------------------------------- #

def _generer_json(systeme: str, consigne: str, schema: dict, temperature: float = 0.4) -> Optional[dict]:
    """Un appel à Ollama, sortie JSON imposée par le schéma. None si l'appel ou le JSON échoue."""
    from core.ollama_client import BASE_URL, KEEP_ALIVE, MODEL, ollama_options

    payload = {"model": MODEL, "stream": False, "keep_alive": KEEP_ALIVE, "format": schema,
               "options": ollama_options(temperature=temperature),
               "messages": [{"role": "system", "content": systeme}, {"role": "user", "content": consigne}]}
    try:
        r = httpx.post(f"{BASE_URL}/api/chat", json=payload, timeout=240.0)
        r.raise_for_status()
        return json.loads(r.json()["message"]["content"])
    except Exception as e:
        logger.warning("[ARTEFACT] Appel au modèle échoué : %s", e)
        return None


def _en_arriere_plan(fonction: Callable[[], None]) -> None:
    threading.Thread(target=fonction, name="atlas-artefact", daemon=True).start()


# --------------------------------------------------------------------------- #
#  Rédaction
# --------------------------------------------------------------------------- #

def _essayer(consigne: str, schema: dict, valide: Callable[[Any], tuple[bool, str]]) -> tuple[Optional[dict], str]:
    """Une rédaction, et UNE seule nouvelle tentative si elle est invalide (raison donnée au modèle)."""
    r = _generer_json(SYSTEME, consigne, schema)
    ok, raison = valide(r) if r is not None else (False, "réponse vide ou JSON illisible")
    if ok:
        return r, ""
    logger.info("[ARTEFACT] Contenu invalide (%s) : nouvelle tentative", raison)
    r = _generer_json(SYSTEME, f"{consigne}\n\nTa réponse précédente était invalide : {raison}. Corrige-la.", schema)
    ok, raison2 = valide(r) if r is not None else (False, "réponse vide ou JSON illisible")
    return (r, "") if ok else (None, raison2 or raison)


def _plan_valide(r: Any) -> tuple[bool, str]:
    if not isinstance(r, dict) or not isinstance(r.get("titre"), str) or not r["titre"].strip():
        return False, "titre absent"
    s = r.get("sections")
    if not isinstance(s, list) or not (3 <= len(s) <= 8) or not all(isinstance(x, str) and x.strip() for x in s):
        return False, "il faut de 3 à 8 titres de sections"
    return True, ""


def _section_valide(r: Any) -> tuple[bool, str]:
    from tools import documents as d

    if not isinstance(r, dict):
        return False, "structure : un objet JSON était attendu"
    return d.valider_contenu({"titre": "Section", "sections": [{"titre": "Section", **r}]})


def rediger_rapport(sujet: str) -> tuple[Optional[dict], str]:
    """Le plan, puis chaque section séparément (num_ctx 8 192 : un appel par section)."""
    from tools import documents as d

    plan, raison = _essayer(f"Propose le plan d'un rapport structuré sur : {sujet}.\nDonne un titre précis et de 4 à 6 "
                            "titres de sections (introduction et conclusion comprises).", SCHEMA_PLAN, _plan_valide)
    if not plan:
        return None, f"le plan n'a pas pu être rédigé ({raison})"
    sections = []
    for titre_section in plan["sections"]:
        corps, raison = _essayer(
            f"Rapport « {plan['titre']} ». Plan : {' ; '.join(plan['sections'])}.\nRédige UNIQUEMENT la section "
            f"« {titre_section} » : 3 paragraphes de 120 à 180 mots chacun, et si utile 2 à 4 points courts. "
            "Pas de titre, pas de répétition des autres sections. N'invente ni chiffre précis ni citation.",
            SCHEMA_SECTION, _section_valide)
        if not corps:
            return None, f"la section « {titre_section} » n'a pas pu être rédigée ({raison})"
        sections.append({"titre": titre_section.strip(), "paragraphes": corps["paragraphes"],
                         "points": corps.get("points") or []})
    contenu = {"titre": plan["titre"].strip(), "sections": sections}
    ok, raison = d.valider_contenu(contenu)
    return (contenu, "") if ok else (None, raison)


def _morceaux(texte: str, taille: int = MORCEAU_CARACTERES) -> list[str]:
    """Découpage déterministe sur les fins de paragraphe (sinon de phrase), sans perte."""
    paras, out, cur = [p for p in texte.replace("\r", "").split("\n") if p.strip()], [], ""
    for p in paras:
        while len(p) > taille:
            coupe = p.rfind(". ", 0, taille)
            coupe = taille if coupe < taille // 2 else coupe + 1
            if cur:
                out.append(cur)
                cur = ""
            out.append(p[:coupe])
            p = p[coupe:].strip()
        if len(cur) + len(p) + 1 > taille and cur:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n{p}" if cur else p
    if cur:
        out.append(cur)
    return out


def rediger_resume(texte: str, nom: str, compte_rendu: Optional[str] = None) -> tuple[Optional[dict], str, list]:
    """Chaque morceau → points factuels ; puis la synthèse ; puis rien d'inventé (phrases retirées)."""
    from tools import documents as d

    morceaux = _morceaux(texte)
    points = []
    for k, m in enumerate(morceaux, 1):
        r, raison = _essayer(f"Voici la partie {k}/{len(morceaux)} du document « {nom} ».\n---\n{m}\n---\n"
                             "Relève de 3 à 6 points FACTUELS de cette partie, en français, en reprenant exactement "
                             "les noms, les dates et les chiffres du texte. N'ajoute rien qui n'y soit pas.",
                             SCHEMA_POINTS, lambda x: (isinstance(x, dict) and isinstance(x.get("points"), list)
                                                       and all(isinstance(p, str) for p in x["points"]), "points absents"))
        if not r:
            return None, f"la partie {k} n'a pas pu être lue ({raison})", []
        points += [p for p in r["points"] if p.strip()]
    if compte_rendu:
        consigne = (f"Rédige le compte rendu de « {nom} » à partir de ces points :\n- " + "\n- ".join(points) +
                    "\nSections : « Points abordés », « Décisions », « Actions à suivre » (une section vide n'est pas "
                    "écrite). N'utilise QUE ces points : aucun nom, date ou chiffre qui n'y soit pas.")
    else:
        consigne = ("Rédige un résumé structuré du document « " + nom + " » à partir de ces points :\n- " +
                    "\n- ".join(points) + "\nUn titre, 2 à 4 sections avec des paragraphes, et 3 à 6 points clés. "
                    "N'utilise QUE ces points : aucun nom, date ou chiffre qui n'y soit pas.")
    contenu, raison = _essayer(consigne, SCHEMA_DOCUMENT, d.valider_contenu)
    if not contenu:
        return None, raison, []
    source = texte + ("\n" + compte_rendu if compte_rendu else "")
    propre, retirees = d.retirer_faits_inventes(contenu, source)
    if compte_rendu:
        propre["sections"].insert(0, {"titre": "Date et participants", "paragraphes": [compte_rendu.strip()]})
    ok, raison = d.valider_contenu(propre)
    return (propre, "", retirees) if ok else (None, f"après retrait des faits inventés : {raison}", retirees)


# --------------------------------------------------------------------------- #
#  Produire, relire, ranger, ouvrir, annoncer
# --------------------------------------------------------------------------- #

def produire(contenu: dict, formats: list[str], pied: str) -> tuple[list[pathlib.Path], str]:
    from core import file_indexer as fi
    from tools import documents as d

    faits = []
    for fmt in formats:
        ext = ".pdf" if fmt == "pdf" else ".docx"
        chemin = d.chemin_libre(contenu["titre"], ext)
        try:
            (d.ecrire_pdf if ext == ".pdf" else d.ecrire_docx)(contenu, chemin, pied=pied)
        except ImportError as e:              # python-docx ou fpdf2 absent : bascule dite
            from core_conversational.degradations import signaler

            signaler("documents", f"{type(e).__name__}: {e}")
            return faits, f"il me manque de quoi écrire le {ext[1:].upper()} ({e.name or e})"
        except Exception as e:
            return faits, f"l'écriture du {ext[1:].upper()} a échoué ({type(e).__name__}: {e})"
        ok, raison, _ = d.verifier_fichier(chemin)
        if not ok:
            return faits, f"le {ext[1:].upper()} produit ne se relit pas ({raison})"
        faits.append(chemin)
        try:
            fi.indexer_un_fichier(str(chemin))
        except Exception as e:
            logger.info("[ARTEFACT] Indexation immédiate impossible (%s) : le prochain passage le prendra", e)
    return faits, ""


def _travail(nature: str, params: dict, origine: Optional[str]) -> None:
    global _en_cours
    from core import annonces
    from tools import documents as d
    from tools import fichiers as tf

    t0 = time.perf_counter()
    retirees: list = []
    try:
        if nature == "rapport":
            contenu, raison = rediger_rapport(params["sujet"])
            pied = d.PIED_RAPPORT
        else:
            contenu, raison, retirees = rediger_resume(params["texte"], params["nom"],
                                                       compte_rendu=params.get("details") if nature == "compte_rendu" else None)
            pied = d.PIED_RESUME
        if not contenu:
            annonces.publier(f"Je n'ai pas pu rédiger le document : {raison}. Aucun fichier n'a été créé.", origine)
            return
        faits, raison = produire(contenu, params["formats"], pied)
        if raison:
            annonces.publier(f"Je n'ai pas pu créer le document : {raison}." +
                             (" Le fichier incomplet n'est pas ouvert." if faits else " Aucun fichier n'a été créé."),
                             origine)
            return
        for f in faits:
            try:
                tf._ouvrir_systeme(str(f))
            except Exception as e:
                logger.info("[ARTEFACT] Ouverture impossible : %s", e)
        retire = ""
        if retirees:
            retire = (f" J'ai retiré {len(retirees)} phrase{'s' if len(retirees) > 1 else ''} qui citai"
                      f"{'ent' if len(retirees) > 1 else 't'} des éléments absents du document source.")
        quoi = " et ".join(str(f) for f in faits)
        annonces.publier(f"J'ai créé « {contenu['titre']} » : {quoi}. Je l'ouvre.{retire} "
                         f"({round(time.perf_counter() - t0)} s)", origine)
    except Exception as e:
        logger.exception("[ARTEFACT] Échec")
        annonces.publier(f"Je n'ai pas pu créer le document : erreur inattendue ({type(e).__name__}).", origine)
    finally:
        _en_cours = None
        _occupe.release()


# --------------------------------------------------------------------------- #
#  L'outil (TOOL_HANDLERS["artefact_creer"])
# --------------------------------------------------------------------------- #

def _source(params: dict) -> tuple[Optional[dict], Optional[dict]]:
    """(le fichier source, None) ou (None, réponse : aucun, plusieurs → question)."""
    from core import file_indexer as fi
    from core import propositions
    from tools import fichiers as tf

    if params.get("source_chemin"):
        r = fi.par_chemin(params["source_chemin"])
        return (r, None) if r else (None, {"success": False, "message": "Ce fichier n'est plus dans l'index."})
    demande = tf.nettoyer_requete(params.get("source") or "")
    try:
        trouves = fi.chercher_nom(demande, limite=6)
    except Exception as e:
        return None, tf._indisponible(e)
    if not trouves:
        return None, {"success": False, "message": f"Je n'ai trouvé aucun fichier « {demande} » : je ne rédige rien. "
                                                   "Dis-moi son nom exact."}
    if len(trouves) > 1 and trouves[0].get("rang") == trouves[1].get("rang"):
        fmt = " et en PDF" if params.get("formats") == ["docx", "pdf"] else (" en PDF" if params.get("formats") == ["pdf"] else "")
        verbe = "rédige un compte rendu du fichier" if params["type"] == "compte_rendu" else "résume le fichier"
        options = trouves[:5]
        propositions.proposer(None, "choix_source", params.get("_origine"),
                              options=[f"{verbe} {r['chemin']}{fmt}" for r in options])
        lignes = "\n".join(f"{k + 1}. {r['nom']} — {os.path.dirname(r['chemin'])}" for k, r in enumerate(options))
        return None, {"success": True, "message": f"Plusieurs fichiers « {demande} » :\n{lignes}\nLequel ? Dis « le 1 », « le 2 »…"}
    return trouves[0], None


def creer(params: dict) -> dict:
    """Vérifie ce qui manque, puis lance la rédaction en arrière-plan ; répond tout de suite."""
    from core import file_indexer as fi
    from core import propositions

    global _en_cours
    origine = params.get("_origine")
    nature = params.get("type") or "rapport"
    if nature in ("rapport", "document"):
        nature = "rapport"
        sujet = (params.get("sujet") or "").strip()
        if not sujet:
            propositions.proposer(None, "complement", origine, completer=f"{params.get('phrase') or 'fais un rapport'} sur")
            return {"success": True, "message": "Sur quel sujet dois-je rédiger le rapport ?"}
        travail = {"sujet": sujet}
        duree = SECONDES_PAR_SECTION * 7          # le plan et 6 sections
        quoi = f"le rapport sur « {sujet} »"
    else:
        src, reponse = _source(params) if (params.get("source") or params.get("source_chemin")) else \
            (None, {"success": True, "message": "Quel fichier dois-je " + ("résumer ?" if nature == "resume" else
                                                                           "utiliser pour le compte rendu ?")})
        if reponse:
            if not (params.get("source") or params.get("source_chemin")):
                propositions.proposer(None, "complement", origine, completer=f"{params.get('phrase') or 'résume'} le fichier")
            return reponse
        if nature == "compte_rendu" and not (params.get("details") or "").strip():
            propositions.proposer(None, "complement", origine,
                                  completer=f"rédige un compte rendu du fichier {src['chemin']} — détails :")
            return {"success": True, "message": "Pour le compte rendu : quelle était la date, et qui participait ? "
                                                "Je ne veux pas l'inventer."}
        texte = fi.extraire_texte(src["chemin"], src["ext"], 400_000)
        if len(texte.strip()) < 100:
            return {"success": False, "message": f"Je n'arrive pas à lire le texte de « {src['nom']} » : je ne rédige rien."}
        travail = {"texte": texte, "nom": src["nom"], "details": params.get("details")}
        duree = SECONDES_PAR_MORCEAU * len(_morceaux(texte)) + SECONDES_PAR_SECTION
        quoi = ("le compte rendu de" if nature == "compte_rendu" else "le résumé de") + f" « {src['nom']} »"
    if not _occupe.acquire(blocking=False):
        return {"success": False, "message": f"Je rédige déjà {_en_cours} : attends qu'il soit prêt."}
    _en_cours = quoi
    travail["formats"] = params.get("formats") or ["docx"]
    fmt = {("docx",): "Word", ("pdf",): "PDF"}.get(tuple(travail["formats"]), "Word et PDF")
    try:
        _en_arriere_plan(lambda: _travail(nature, travail, origine))
    except Exception:
        _en_cours = None
        _occupe.release()
        raise
    return {"success": True, "message": f"Je rédige {quoi} ({fmt}), environ {duree} secondes. "
                                        "Je te préviens quand il est prêt, et je l'ouvre."}
