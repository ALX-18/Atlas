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

Sprint Artefacts sur mesure — la structure vient de la demande, pas d'un gabarit :
- les consignes deviennent une spécification (core/specification.py) ; le document produit est
  vérifié contre elle ; un écart donne UNE régénération ciblée, puis ce qui reste est DIT ;
- une retouche écrit une NOUVELLE version (v2, v3…) et dit ce qui a changé ; un Word externe est
  relu, et ce que sa mise en forme perd est mesuré et dit ;
- les faits retenus (nom, adresse, établissement) ne sont pas redemandés, et leur source est citée.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import re
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

SYSTEME = ("Tu es Atlas, un assistant de bureau. Tu rédiges en FRANÇAIS, de façon claire et sobre. Tu réponds "
           "UNIQUEMENT par le JSON demandé, sans texte autour.")

SCHEMA_PLAN = {"type": "object", "properties": {"titre": {"type": "string"},
               "sections": {"type": "array", "items": {"type": "string"}}}, "required": ["titre", "sections"]}
SCHEMA_SECTION = {"type": "object", "properties": {"paragraphes": {"type": "array", "items": {"type": "string"}},
                  "points": {"type": "array", "items": {"type": "string"}}}, "required": ["paragraphes"]}
# Artefacts sur mesure : un tableau rendu par le modèle, dessiné par le moteur.
SCHEMA_TABLEAU = {"type": "object", "properties": {"colonnes": {"type": "array", "items": {"type": "string"}},
                  "lignes": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}}},
                  "required": ["colonnes", "lignes"]}
SCHEMA_SECTION_TABLEAU = {"type": "object", "properties": {
    "paragraphes": {"type": "array", "items": {"type": "string"}}, "points": {"type": "array", "items": {"type": "string"}},
    "tableau": SCHEMA_TABLEAU}, "required": ["paragraphes", "tableau"]}
SCHEMA_PLAN_LIBRE = {"type": "object", "properties": {"titre": {"type": "string"},
                     "sections": {"type": "array", "items": {"type": "string"}},
                     "section_du_tableau": {"type": "integer"}}, "required": ["titre", "sections"]}
SCHEMA_LETTRE = {"type": "object", "properties": {"objet": {"type": "string"},
                 "paragraphes": {"type": "array", "items": {"type": "string"}}}, "required": ["objet", "paragraphes"]}
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
    from core.ollama_client import BASE_URL, KEEP_ALIVE, champs_modele, ollama_options

    payload = {**champs_modele(), "stream": False, "keep_alive": KEEP_ALIVE, "format": schema,
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

_NOMS_LANGUES = {"en": "anglais", "es": "espagnol", "de": "allemand", "it": "italien", "pt": "portugais", "fr": "français"}


def systeme(langue: str = "fr") -> str:
    if langue == "fr":
        return SYSTEME
    nom = _NOMS_LANGUES.get(langue, langue).upper()
    return (f"Tu es Atlas, un assistant de bureau. Tu rédiges ENTIÈREMENT en {nom}, de façon claire et sobre. Tu réponds "
            "UNIQUEMENT par le JSON demandé, sans texte autour.")


# Artefacts sur mesure / AS6 : les erreurs sont distinguées (Réunion n° 1) — génération (le modèle n'a rien
# rendu de lisible), validation (le moteur a refusé ce qu'il a rendu), exécution (le fichier n'a pas pu être écrit).
JOURNAL_ERREURS: list[dict] = []


def _noter_erreur(sorte: str, raison: str) -> None:
    JOURNAL_ERREURS.append({"sorte": sorte, "raison": raison, "quand": time.strftime("%H:%M:%S")})
    del JOURNAL_ERREURS[:-200]


def _essayer(consigne: str, schema: dict, valide: Callable[[Any], tuple[bool, str]],
             systeme_: Optional[str] = None) -> tuple[Optional[dict], str]:
    """Une rédaction, et UNE seule nouvelle tentative si elle est invalide (raison donnée au modèle)."""
    s = systeme_ or SYSTEME
    r = _generer_json(s, consigne, schema)
    if r is None:
        _noter_erreur("generation", "réponse vide ou JSON illisible")
    ok, raison = valide(r) if r is not None else (False, "réponse vide ou JSON illisible")
    if ok:
        return r, ""
    if r is not None:
        _noter_erreur("validation", raison)
    logger.info("[ARTEFACT] Contenu invalide (%s) : nouvelle tentative", raison)
    r = _generer_json(s, f"{consigne}\n\nTa réponse précédente était invalide : {raison}. Corrige-la.", schema)
    if r is None:
        _noter_erreur("generation", "réponse vide ou JSON illisible (nouvelle tentative)")
    ok, raison2 = valide(r) if r is not None else (False, "réponse vide ou JSON illisible")
    if not ok and r is not None:
        _noter_erreur("validation", raison2 or raison)
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


# --------------------------------------------------------------------------- #
#  Artefacts sur mesure / AS1 — un document générique : la structure vient de la demande
# --------------------------------------------------------------------------- #

GENRES_LIBELLES = {"rapport": "un rapport", "document": "un document", "fiche": "une fiche", "note": "une note",
                   "plan_de_cours": "un plan de cours", "lettre": "une lettre", "resume": "un résumé",
                   "compte_rendu": "un compte rendu"}


# Jugement d'Alexis : un genre n'est pas qu'un mot dans la consigne. La structure reste celle de la demande.
CONSIGNES_DE_GENRE = {
    "fiche": "C'est une fiche : phrases courtes, l'essentiel seulement, chaque information une seule fois dans tout le document.",
    "plan_de_cours": "C'est un plan de cours écrit pour l'enseignant, jamais adressé à l'élève : donne pour cette partie "
                     "l'objectif, la durée, le matériel et le déroulé (ce que fait l'enseignant, ce que font les élèves). "
                     "Vérifie chaque exemple et chaque calcul.",
}


def _budget(spec: dict, n_sections: int) -> tuple[int, int, int]:
    """(paragraphes, mots min, mots max) par section, d'après la longueur demandée."""
    lo, hi = spec.get("mots_min"), spec.get("mots_max")
    if not lo and not hi:
        if spec.get("genre") in ("fiche", "plan_de_cours"):
            return 1, 40, 80                             # l'essentiel, le reste en points courts
        return 3, 120, 180                               # sans consigne : comme avant (rapport Artefacts)
    cible = ((lo or hi * 0.7) + (hi or lo * 1.3)) / 2
    par = max(25, int(cible / max(1, n_sections)))
    paras = 1 if par < 130 else (2 if par < 280 else 3)
    return paras, max(15, int(par * 0.75 / paras)), max(25, int(par * 1.05 / paras))


def _plan(demande: str, sujet: str, spec: dict) -> tuple[Optional[dict], str]:
    from core import specification as sp

    if spec.get("parties"):                              # la personne a imposé ses parties : le moteur les tient
        titre = spec.get("titre") or ((sujet[:1].upper() + sujet[1:]) if sujet else "Document")
        return {"titre": titre, "sections": list(spec["parties"]),
                "section_du_tableau": 1 if spec.get("tableau") else None}, ""
    n = spec.get("nb_parties")
    combien = f"exactement {n}" if n else ("2 ou 3" if (spec.get("mots_max") or 9999) <= 450 else "de 3 à 6")
    contraintes = []
    if spec.get("introduction") is False:
        contraintes.append("pas d'introduction")
    if spec.get("conclusion") is False:
        contraintes.append("pas de conclusion")
    if spec.get("conclusion"):
        contraintes.append("une conclusion à la fin")
    if spec.get("introduction"):
        contraintes.append("une introduction au début")
    genre = GENRES_LIBELLES.get(spec.get("genre") or "document", "un document")
    consigne = (f"La personne demande : « {demande} ».\nIl s'agit de {genre}. Propose son titre et {combien} titres de "
                "parties ADAPTÉS À CETTE DEMANDE (la structure vient de la demande, pas d'un modèle de rapport). "
                + (f"Contraintes : {', '.join(contraintes)}. " if contraintes else "")
                + (f"Consignes : {sp.consignes_en_texte(spec)}. " if sp.consignes_en_texte(spec) else "")
                + ("Indique dans section_du_tableau le numéro (à partir de 1) de la partie qui contiendra le tableau. "
                   if spec.get("tableau") else ""))

    def valide(r):
        if not isinstance(r, dict) or not isinstance(r.get("titre"), str) or not r["titre"].strip():
            return False, "titre absent"
        s = r.get("sections")
        if not isinstance(s, list) or not all(isinstance(x, str) and x.strip() for x in s):
            return False, "titres de parties absents"
        if n and len(s) != n:
            return False, f"il faut exactement {n} parties"
        if not n and not (1 <= len(s) <= 8):
            return False, "il faut de 1 à 8 parties"
        return True, ""

    plan, raison = _essayer(consigne, SCHEMA_PLAN_LIBRE, valide, systeme(spec.get("langue", "fr")))
    if plan and spec.get("titre"):
        plan["titre"] = spec["titre"]
    return plan, raison


def _rediger_section(demande: str, plan: dict, titre_section: str, spec: dict, avec_tableau: bool,
                     paras: int, lo: int, hi: int, precision: str = "") -> tuple[Optional[dict], str]:
    from core import specification as sp
    from tools import documents as d

    langue = spec.get("langue", "fr")
    consigne = (f"La personne demande : « {demande} ».\nDocument « {plan['titre']} ». Parties : {' ; '.join(plan['sections'])}.\n"
                f"Rédige UNIQUEMENT la partie « {titre_section} » : {paras} paragraphe{'s' if paras > 1 else ''} de "
                f"{lo} à {hi} mots chacun"
                + ("" if spec.get("puces") is False else ", et si utile 2 à 4 points courts")
                + ". Pas de titre, pas de répétition des autres parties. N'invente ni chiffre précis, ni citation, ni nom "
                  "de personne. Si tu n'es pas sûr d'une date ou d'un fait, ne l'écris pas."
                + (f" {CONSIGNES_DE_GENRE[spec['genre']]}" if spec.get("genre") in CONSIGNES_DE_GENRE else "")
                + (f" Consignes : {sp.consignes_en_texte(spec)}." if sp.consignes_en_texte(spec) else "")
                + (" Ajoute un TABLEAU utile à cette partie (colonnes nommées, lignes complètes)." if avec_tableau else "")
                + (f" {precision}" if precision else ""))

    def valide(r):
        if not isinstance(r, dict):
            return False, "structure : un objet JSON était attendu"
        # Un tableau absent n'invalide pas la partie : la vérification contre la demande le voit, le
        # redemande une fois (régénération ciblée), puis le DIT s'il manque encore.
        if avec_tableau and r.get("tableau") is not None and d._tableau_valide(r["tableau"]):
            r = {k: v for k, v in r.items() if k != "tableau"}
        return d.valider_contenu({"titre": "Section", "sections": [{"titre": "Section", **r}]}, langue=langue)

    return _essayer(consigne, SCHEMA_SECTION_TABLEAU if avec_tableau else SCHEMA_SECTION, valide, systeme(langue))


def _plus_proche(avant: dict, nouveau: dict, spec: dict) -> dict:
    """La régénération ne remplace que si elle fait mieux : moins d'écarts, ou à égalité plus près de la
    longueur demandée (mesuré : 380 mots pour 300, régénérés en 155, étaient remplacés)."""
    from core import specification as sp

    def distance(c):
        n, lo, hi = sp.mots(c), spec.get("mots_min") or 0, spec.get("mots_max") or float("inf")
        return lo - n if n < lo else (n - hi if n > hi else 0)

    a, b = len(sp.verifier(avant, spec)), len(sp.verifier(nouveau, spec))
    if b != a:
        return nouveau if b < a else avant
    return nouveau if distance(nouveau) <= distance(avant) else avant


def rediger_document(demande: str, sujet: str, spec: dict) -> tuple[Optional[dict], str, list[str]]:
    """(contenu, raison de l'échec, écarts restants). Vérifié contre la spécification ; un écart donne
    UNE régénération ciblée, puis ce qui reste est rendu (pour être dit, jamais caché)."""
    from core import specification as sp
    from tools import documents as d

    plan, raison = _plan(demande, sujet, spec)
    if not plan:
        return None, f"le plan n'a pas pu être rédigé ({raison})", []
    paras, lo, hi = _budget(spec, len(plan["sections"]))
    idx_tab = None
    if spec.get("tableau"):
        k = plan.get("section_du_tableau")
        idx_tab = (k - 1) if isinstance(k, int) and 1 <= k <= len(plan["sections"]) else min(1, len(plan["sections"]) - 1)

    def ecrire(precision: str = "", facteur: float = 1.0, seulement: Optional[set] = None, avant: Optional[dict] = None):
        sections = []
        for k, ts in enumerate(plan["sections"]):
            if seulement is not None and k not in seulement and avant:
                sections.append(avant["sections"][k])
                continue
            corps, r = _rediger_section(demande, plan, ts, spec, k == idx_tab, paras, max(10, int(lo * facteur)),
                                        max(15, int(hi * facteur)), precision)
            if not corps:
                return None, f"la partie « {ts} » n'a pas pu être rédigée ({r})"
            s = {"titre": ts.strip(), "paragraphes": corps["paragraphes"], "points": corps.get("points") or []}
            if corps.get("tableau") and not d._tableau_valide(corps["tableau"]):
                s["tableau"] = {"colonnes": [str(c) for c in corps["tableau"]["colonnes"]],
                                "lignes": [[str(c) for c in l] for l in corps["tableau"]["lignes"]]}
            sections.append(s)
        return sp.appliquer({"titre": plan["titre"].strip(), "genre": spec.get("genre"), "sections": sections}, spec), ""

    contenu, raison = ecrire()
    if not contenu:
        return None, raison, []
    ecarts = sp.verifier(contenu, spec)
    if ecarts:
        # UNE régénération ciblée, selon l'écart
        logger.info("[ARTEFACT] Écarts à la demande (%s) : une régénération ciblée", "; ".join(ecarts))
        n = sp.mots(contenu)
        facteur, precision, seulement = 1.0, "", None
        # Viser le MILIEU de ce qui est demandé : le modèle dépasse (ou reste en deçà) de façon assez constante,
        # on corrige la consigne de ce rapport (ask × cible / obtenu).
        lo_t, hi_t = spec.get("mots_min"), spec.get("mots_max")
        cible = ((lo_t or hi_t * 0.7) + (hi_t or lo_t * 1.3)) / 2 if (lo_t or hi_t) else n
        if hi_t and n > hi_t:
            facteur = max(0.25, cible / n)
            precision = "Sois plus BREF que d'habitude."
        elif lo_t and n < lo_t:
            facteur = min(3.0, cible / max(1, n))
            precision = "Développe davantage."
        if any("langue" in e for e in ecarts):
            precision += f" Écris ENTIÈREMENT en {_NOMS_LANGUES.get(spec.get('langue'), '')}, pas en français."
        if any("tableau" in e for e in ecarts) and idx_tab is not None and facteur == 1.0:
            seulement = {idx_tab}
        nouveau, raison2 = ecrire(precision.strip(), facteur, seulement, contenu)
        if nouveau:
            ok, _ = d.valider_contenu(nouveau, langue=spec.get("langue", "fr"))
            if ok:
                contenu = _plus_proche(contenu, nouveau, spec)
        ecarts = sp.verifier(contenu, spec)
    ok, raison = d.valider_contenu(contenu, langue=spec.get("langue", "fr"))
    return (contenu, "", ecarts) if ok else (None, raison, [])


# --------------------------------------------------------------------------- #
#  Lettres : les informations personnelles sont demandées, ou reprises des faits retenus
# --------------------------------------------------------------------------- #

def faits_retenus() -> dict:
    """{"nom", "adresse", "etablissement"} trouvés dans les faits que la personne a fait retenir
    (« retiens que mon adresse est … »), avec le fait d'origine pour dire d'où Atlas le tient."""
    import re

    out: dict = {}
    try:
        from core import memory_manager as mm

        mem = mm.get_memory_manager()
        if not mem.is_connected():
            return out
        for cle, requete, motif in (
                ("nom", "mon nom je m'appelle", r"(?:je m'appelle|mon nom (?:est|c'est)|mon nom complet est)\s+(?P<v>.+)"),
                ("adresse", "mon adresse", r"(?:mon adresse (?:est|c'est)|j'habite(?: au)?)\s+(?P<v>.+)"),
                ("etablissement", "mon école mon entreprise mon établissement mon lycée",
                 r"(?:mon (?:ecole|école|entreprise|etablissement|établissement|lycee|lycée|employeur|universite|université)"
                 r"(?: est|, c'est)?|je travaille (?:chez|a|à)|je suis (?:a|à|au) (?:la |l')?)\s+(?P<v>.+)")):
            for f in mem.recall(requete, top_k=3, category="user_fact") or []:
                m = re.search(motif, f["content"], re.IGNORECASE)
                if m:
                    out[cle] = {"valeur": m.group("v").strip().rstrip(" ."), "source": f["content"]}
                    break
    except Exception as e:
        logger.info("[ARTEFACT] Faits retenus illisibles : %s", e)
    return out


def _destinataire(demande: str) -> Optional[str]:
    """« … pour mon voisin … » → « mon voisin » : à qui s'adresse la lettre, si la phrase le dit."""
    m = re.search(r"(?i)\b(?:pour|à|a)\s+((?:mon|ma|notre)\s+[\w'’-]+)", demande or "")
    return m.group(1) if m else None


def rediger_lettre(demande: str, spec: dict, infos: dict) -> tuple[Optional[dict], str, list[str]]:
    """infos : nom (obligatoire), adresse, destinataire. La lettre est assemblée par le moteur."""
    from core import specification as sp
    from tools import documents as d

    langue = spec.get("langue", "fr")
    infos = {**infos, "destinataire": infos.get("destinataire") or _destinataire(demande)}
    paras, lo, hi = _budget(spec, 1) if (spec.get("mots_min") or spec.get("mots_max")) else (3, 50, 110)
    sans_titre = {k: v for k, v in spec.items() if k not in ("titre", "nb_parties", "parties")}

    def consigne(facteur: float = 1.0) -> str:
        return (f"La personne demande : « {demande} ».\nRédige le CORPS de cette lettre, signée par {infos['nom']}"
                + (f" ({infos['etablissement']})" if infos.get("etablissement") else "")
                + (f", adressée à {infos['destinataire']}" if infos.get("destinataire") else "")
                + f" : la formule d'appel, puis {max(2, paras)} à {max(3, paras + 1)} paragraphes "
                  f"({max(15, int(lo * facteur))} à {max(25, int(hi * facteur))} mots chacun), "
                  "puis la formule de politesse. Dès le premier paragraphe, dis clairement ce qui est demandé, de façon "
                  "concrète (l'action précise, pas « un compromis »). Donne aussi l'objet, en quelques mots. N'invente ni date, ni chiffre, ni "
                  "adresse, ni nom qui ne soit pas dans la demande."
                + (f" Consignes : {sp.consignes_en_texte(spec)}." if sp.consignes_en_texte(spec) else ""))

    def valide(r):
        if not isinstance(r, dict) or not isinstance(r.get("objet"), str) or not r["objet"].strip():
            return False, "objet absent"
        if not isinstance(r.get("paragraphes"), list) or len(r["paragraphes"]) < 2:
            return False, "il faut au moins 2 paragraphes"
        return d.valider_contenu({"titre": r["objet"][:150] or "Lettre", "sections": [{"titre": "Lettre",
                                  "paragraphes": r["paragraphes"]}]}, langue=langue)

    jours = time.strftime("%d/%m/%Y")
    # Le nom et l'adresse d'un destinataire ne s'inventent pas : ce qui manque est marqué, à compléter
    dest = (infos.get("destinataire") or "").strip()
    if not dest:
        bloc = ["[nom et adresse du destinataire à compléter]"]
    elif re.match(r"(?i)^(mon|ma|mes|notre|nos|le|la|les|un|une)\b", dest):
        bloc = [f"[nom et adresse de {dest} à compléter]"]
    else:
        bloc = [dest[:1].upper() + dest[1:]]

    def assembler(r: dict) -> dict:
        corps = [p.strip() for p in r["paragraphes"] if p.strip()]
        if langue == "fr" and not re.search(r"(?i)agr[ée]er|salutations|cordialement|sentiments", " ".join(corps[-2:])):
            corps.append("Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées.")
        contenu = {"genre": "lettre", "titre": spec.get("titre") or f"Lettre — {r['objet'].strip()}"[:150],
                   "expediteur": [infos["nom"]] + ([x.strip() for x in infos["adresse"].split(",")] if infos.get("adresse") else []),
                   "destinataire": bloc,
                   "lieu_date": f"Le {jours}", "objet": r["objet"].strip(), "signature": infos["nom"],
                   "sections": [{"titre": "Lettre", "paragraphes": corps}]}
        return sp.appliquer(contenu, {k: v for k, v in spec.items() if k != "titre"})

    r, raison = _essayer(consigne(), SCHEMA_LETTRE, valide, systeme(langue))
    if not r:
        return None, f"la lettre n'a pas pu être rédigée ({raison})", []
    contenu = assembler(r)
    ecarts = sp.verifier(contenu, sans_titre)
    lo_t, hi_t = spec.get("mots_min"), spec.get("mots_max")
    n = sp.mots(contenu)
    if (lo_t or hi_t) and n and ((lo_t and n < lo_t) or (hi_t and n > hi_t)):
        # UNE régénération ciblée sur la longueur, comme pour les documents (demande × cible / obtenu)
        cible = ((lo_t or hi_t * 0.7) + (hi_t or lo_t * 1.3)) / 2
        r2, _ = _essayer(consigne(max(0.25, min(3.0, cible / n))), SCHEMA_LETTRE, valide, systeme(langue))
        if r2:
            contenu = _plus_proche(contenu, assembler(r2), sans_titre)
            ecarts = sp.verifier(contenu, sans_titre)
    return contenu, "", ecarts


OUVERTURE_ATTENTE_S = 5.0


def _ouvrir(fichiers) -> None:
    """Ouvre les fichiers produits, sans jamais bloquer le travail : une application occupée (Word avec une
    boîte de dialogue) peut figer l'ouverture ; au-delà de quelques secondes, on continue sans elle."""
    import threading

    from tools import fichiers as tf

    def ouvrir():
        for f in fichiers:
            try:
                tf._ouvrir_systeme(str(f))
            except Exception as e:
                logger.info("[ARTEFACT] Ouverture impossible : %s", e)

    t = threading.Thread(target=ouvrir, name="atlas-ouverture", daemon=True)
    t.start()
    t.join(OUVERTURE_ATTENTE_S)
    if t.is_alive():
        logger.warning("[ARTEFACT] L'ouverture ne répond pas après %.0f s : le travail continue sans l'attendre",
                       OUVERTURE_ATTENTE_S)


def _avertissement_faits(contenu: dict) -> str:
    """Un document rédigé de mémoire qui cite des dates ou des chiffres : le modèle peut se tromper, c'est dit."""
    from tools import documents as d

    if not re.search(r"\d", " ".join(d._textes(contenu)) + " ".join(
            str(x) for s in contenu.get("sections", []) for ligne in ((s.get("tableau") or {}).get("lignes") or []) for x in ligne)):
        return ""
    return " Je l'ai rédigé de mémoire, sans internet : vérifie les dates, les chiffres et les noms avant de t'en servir."


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


# Artefacts sur mesure / AS3 : l'ancienne consigne (« N'utilise QUE ces points : aucun nom, date ou chiffre
# qui n'y soit pas ») poussait des modèles à RETIRER des faits pourtant présents (« un certain montant »,
# banc de modèles §6.3). La consigne dit maintenant les deux moitiés : garder, et ne rien ajouter.
CONSIGNE_FAITS_RESUME = ("Les chiffres, les dates, les montants et les noms des points sont EXACTS : reprends-les TELS "
                         "QUELS dans le texte, sans les arrondir, les généraliser ni les remplacer par une formule vague "
                         "(« un certain montant », « une entreprise »). N'en ajoute AUCUN qui ne soit pas dans les points.")
CONSIGNE_FAITS_RESUME_AVANT = "N'utilise QUE ces points : aucun nom, date ou chiffre qui n'y soit pas."


def rediger_resume(texte: str, nom: str, compte_rendu: Optional[str] = None, spec: Optional[dict] = None,
                   consigne_faits: Optional[str] = None) -> tuple[Optional[dict], str, list]:
    """Chaque morceau → points factuels ; puis la synthèse ; puis rien d'inventé (phrases retirées).
    spec (Artefacts sur mesure) : longueur, langue, parties… de la demande ; consigne_faits : pour le banc AS3."""
    from core import specification as sp
    from tools import documents as d

    spec = spec or {}
    faits = consigne_faits or CONSIGNE_FAITS_RESUME

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
    consignes = sp.consignes_en_texte(spec)
    structure = (f"Les parties, dans cet ordre : {' ; '.join(spec['parties'])}." if spec.get("parties") else
                 f"Exactement {spec['nb_parties']} sections." if spec.get("nb_parties") else "")
    if compte_rendu:
        consigne = (f"Rédige le compte rendu de « {nom} » à partir de ces points :\n- " + "\n- ".join(points) +
                    "\n" + (structure or "Sections : « Points abordés », « Décisions », « Actions à suivre » (une section "
                                         "vide n'est pas écrite).") + f" {faits}")
    else:
        consigne = ("Rédige un résumé structuré du document « " + nom + " » à partir de ces points :\n- " +
                    "\n- ".join(points) + "\n" + (structure or "Un titre, 2 à 4 sections avec des paragraphes")
                    + ("." if spec.get("puces") is False else ", et 3 à 6 points clés.") + f" {faits}")
    if consignes:
        consigne += f" Consignes de la personne : {consignes}."
    langue = spec.get("langue", "fr")
    contenu, raison = _essayer(consigne, SCHEMA_DOCUMENT, lambda c: d.valider_contenu(c, langue=langue), systeme(langue))
    if not contenu:
        return None, raison, []
    source = texte + ("\n" + compte_rendu if compte_rendu else "")
    propre, retirees = d.retirer_faits_inventes(contenu, source)
    if compte_rendu:
        propre["sections"].insert(0, {"titre": "Date et participants", "paragraphes": [compte_rendu.strip()]})
    propre = sp.appliquer(propre, spec)
    ok, raison = d.valider_contenu(propre, langue=langue)
    return (propre, "", retirees) if ok else (None, f"après retrait des faits inventés : {raison}", retirees)


def faits_conserves(resume: dict, source: str) -> tuple[int, int, list[str]]:
    """AS3 — (conservés, clés de la source, absents) : chiffres, dates et noms propres de la source
    retrouvés dans le résumé livré."""
    import re

    from tools import documents as d

    cles = set(d._DATE.findall(source)) | {n.strip() for n in d._NOMBRE.findall(source)} | set(d._noms_propres(source))
    texte = d._plat(" ".join(d._textes(resume)))
    nombres = {d._nombre_norm(n) for n in d._NOMBRE.findall(" ".join(d._textes(resume)))}
    gardes, absents = 0, []
    for c in sorted(cles):
        ok = (d._nombre_norm(c) in nombres) if re.fullmatch(r"[\d   .,]+", c) else (d._plat(c) in texte)
        if ok:
            gardes += 1
        else:
            absents.append(c)
    return gardes, len(cles), absents


# --------------------------------------------------------------------------- #
#  Produire, relire, ranger, ouvrir, annoncer
# --------------------------------------------------------------------------- #

def produire(contenu: dict, formats: list[str], pied: str, sommaire: Optional[bool] = None,
             chemins: Optional[dict] = None, rendu: Optional[dict] = None) -> tuple[list[pathlib.Path], str]:
    """chemins (retouches) : {".docx": chemin imposé, ".pdf": …} — sinon un nom libre dans Documents\\Atlas.
    rendu : rempli avec ce que le moteur a écrit (sommaire, tableaux) — pour la vérification."""
    from core import file_indexer as fi
    from tools import documents as d

    faits = []
    for fmt in formats:
        ext = ".pdf" if fmt == "pdf" else ".docx"
        chemin = (chemins or {}).get(ext) or d.chemin_libre(contenu["titre"], ext)
        try:
            r = (d.ecrire_pdf if ext == ".pdf" else d.ecrire_docx)(contenu, chemin, pied=pied, sommaire=sommaire)
            if rendu is not None and isinstance(r, dict):
                rendu[ext] = r
        except ImportError as e:              # python-docx ou fpdf2 absent : bascule dite
            from core_conversational.degradations import signaler

            signaler("documents", f"{type(e).__name__}: {e}")
            _noter_erreur("execution", str(e))
            return faits, f"il me manque de quoi écrire le {ext[1:].upper()} ({e.name or e})"
        except Exception as e:
            _noter_erreur("execution", f"{type(e).__name__}: {e}")
            return faits, f"l'écriture du {ext[1:].upper()} a échoué ({type(e).__name__}: {e})"
        ok, raison, _ = d.verifier_fichier(chemin, exige_titres=contenu.get("genre") != "lettre")
        if not ok:
            _noter_erreur("execution", raison)
            return faits, f"le {ext[1:].upper()} produit ne se relit pas ({raison})"
        faits.append(chemin)
        try:
            fi.indexer_un_fichier(str(chemin))
        except Exception as e:
            logger.info("[ARTEFACT] Indexation immédiate impossible (%s) : le prochain passage le prendra", e)
    return faits, ""


# --------------------------------------------------------------------------- #
#  Le dernier document créé (Artefacts sur mesure : « raccourcis-le », « mets-le en PDF »)
# --------------------------------------------------------------------------- #

_dernier: dict = {}
DUREE_DOCUMENT_RECENT_S = 2 * 3600


def dernier_document_recent() -> Optional[dict]:
    """Le dernier document créé ou retouché par CET Atlas, il y a moins de 2 h (sinon None)."""
    if _dernier and time.time() - _dernier.get("quand", 0) <= DUREE_DOCUMENT_RECENT_S:
        return dict(_dernier)
    return None


def _retenir_dernier(contenu: dict, faits: list[pathlib.Path], spec: dict, pied: str) -> None:
    _dernier.clear()
    _dernier.update({"contenu": contenu, "spec": spec, "pied": pied, "quand": time.time(),
                     "docx": next((f for f in faits if f.suffix == ".docx"), None),
                     "pdf": next((f for f in faits if f.suffix == ".pdf"), None)})


def _ecarts_en_texte(ecarts: list[str]) -> str:
    if not ecarts:
        return ""
    return " Ce que je n'ai pas réussi à tenir : " + " ; ".join(ecarts) + "."


def _travail(nature: str, params: dict, origine: Optional[str]) -> None:
    global _en_cours
    from core import annonces
    from core import specification as sp
    from tools import documents as d

    t0 = time.perf_counter()
    retirees: list = []
    ecarts: list[str] = []
    memoire = ""
    spec = params.get("spec") or {}
    try:
        if nature == "lettre":
            contenu, raison, ecarts = rediger_lettre(params["demande"], spec, params["infos"])
            pied = d.PIED_RAPPORT
            if contenu and any("à compléter" in x for x in contenu.get("destinataire") or []):
                memoire = " Complète le nom et l'adresse du destinataire : je ne les invente pas."
        elif nature in ("resume", "compte_rendu"):
            contenu, raison, retirees = rediger_resume(params["texte"], params["nom"],
                                                       compte_rendu=params.get("details") if nature == "compte_rendu" else None,
                                                       spec=spec)
            ecarts = sp.verifier(contenu, {k: v for k, v in spec.items() if k != "titre"}) if contenu else []
            pied = d.PIED_RESUME
        else:
            contenu, raison, ecarts = rediger_document(params["demande"], params["sujet"], spec)
            pied = d.PIED_RAPPORT
            memoire = _avertissement_faits(contenu) if contenu else ""
        if not contenu:
            annonces.publier(f"Je n'ai pas pu rédiger le document : {raison}. Aucun fichier n'a été créé.", origine)
            return
        rendu: dict = {}
        faits, raison = produire(contenu, params["formats"], pied, sommaire=spec.get("sommaire"), rendu=rendu)
        if raison:
            annonces.publier(f"Je n'ai pas pu créer le document : {raison}." +
                             (" Le fichier incomplet n'est pas ouvert." if faits else " Aucun fichier n'a été créé."),
                             origine)
            return
        if ".docx" in rendu and spec.get("sommaire") is not None:
            ecarts += sp.verifier({"titre": contenu["titre"], "sections": []}, {"sommaire": spec["sommaire"]}, rendu[".docx"])
        _retenir_dernier(contenu, faits, spec, pied)
        _ouvrir(faits)
        retire = ""
        if retirees:
            retire = (f" J'ai retiré {len(retirees)} phrase{'s' if len(retirees) > 1 else ''} qui citai"
                      f"{'ent' if len(retirees) > 1 else 't'} des éléments absents du document source.")
        quoi = " et ".join(str(f) for f in faits)
        annonces.publier(f"J'ai créé « {contenu['titre']} » : {quoi}. Je l'ouvre.{retire}{_ecarts_en_texte(ecarts)}"
                         f"{params.get('sources_infos') or ''}{memoire} ({round(time.perf_counter() - t0)} s)", origine)
    except Exception as e:
        logger.exception("[ARTEFACT] Échec")
        _noter_erreur("execution", f"{type(e).__name__}: {e}")
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


def _lancer(nature: str, travail: dict, quoi: str, duree: int, origine: Optional[str]) -> dict:
    global _en_cours
    if not _occupe.acquire(blocking=False):
        return {"success": False, "message": f"Je rédige déjà {_en_cours} : attends qu'il soit prêt."}
    _en_cours = quoi
    fmt = {("docx",): "Word", ("pdf",): "PDF"}.get(tuple(travail["formats"]), "Word et PDF")
    try:
        _en_arriere_plan(lambda: _travail(nature, travail, origine))
    except Exception:
        _en_cours = None
        _occupe.release()
        raise
    return {"success": True, "message": f"Je rédige {quoi} ({fmt}), environ {duree} secondes. "
                                        "Je te préviens quand c'est prêt, et je l'ouvre."}


def creer(params: dict) -> dict:
    """Vérifie ce qui manque, puis lance la rédaction en arrière-plan ; répond tout de suite."""
    from core import file_indexer as fi
    from core import propositions
    from core import specification as sp

    origine = params.get("_origine")
    phrase = params.get("phrase") or ""
    spec = {**sp.extraire(phrase), **(params.get("spec") or {})}
    if params.get("formats"):
        spec["formats"] = params["formats"]
    nature = params.get("type") or spec.get("genre") or "rapport"
    formats = spec.get("formats") or ["docx"]
    if nature == "lettre":
        infos = {"destinataire": params.get("destinataire")}
        retenus = faits_retenus()
        cites = []
        nom = (params.get("signature") or "").strip()
        if not nom and retenus.get("nom"):
            nom = retenus["nom"]["valeur"]
            cites.append("ton nom")
        if not nom:
            propositions.proposer(None, "complement", origine, completer=f"{phrase} — signée :")
            return {"success": True, "message": "Pour la lettre : à quel nom dois-je la signer ? (Ajoute ton adresse si tu "
                                                "veux qu'elle y figure : je n'invente ni l'un ni l'autre.)"}
        m = re.match(r"^(?P<n>[^,]+?)(?:\s*,\s*(?P<a>.+))?$", nom)
        infos["nom"] = m.group("n").strip()
        adresse = (m.group("a") or "").strip()
        if not adresse and retenus.get("adresse"):
            adresse = retenus["adresse"]["valeur"]
            cites.append("ton adresse")
        infos["adresse"] = adresse or None
        if retenus.get("etablissement"):
            infos["etablissement"] = retenus["etablissement"]["valeur"]
            cites.append("ton établissement")
        cle_de = {"ton nom": "nom", "ton adresse": "adresse", "ton établissement": "etablissement"}
        sources = (" J'ai repris ce que tu m'avais dit : " + " ; ".join(
            f"{c} (« {retenus[cle_de[c]]['source']} »)" for c in cites) + "." if cites else "")
        travail = {"demande": phrase, "spec": spec, "infos": infos, "formats": formats, "sources_infos": sources}
        return _lancer("lettre", travail, "la lettre", SECONDES_PAR_SECTION * 2, origine)
    if nature in ("resume", "compte_rendu"):
        src, reponse = _source(params) if (params.get("source") or params.get("source_chemin")) else \
            (None, {"success": True, "message": "Quel fichier dois-je " + ("résumer ?" if nature == "resume" else
                                                                           "utiliser pour le compte rendu ?")})
        if reponse:
            if not (params.get("source") or params.get("source_chemin")):
                propositions.proposer(None, "complement", origine, completer=f"{phrase or 'résume'} le fichier")
            return reponse
        if nature == "compte_rendu" and not (params.get("details") or "").strip():
            propositions.proposer(None, "complement", origine,
                                  completer=f"rédige un compte rendu du fichier {src['chemin']} — détails :")
            return {"success": True, "message": "Pour le compte rendu : quelle était la date, et qui participait ? "
                                                "Je ne veux pas l'inventer."}
        texte = fi.extraire_texte(src["chemin"], src["ext"], 400_000)
        if len(texte.strip()) < 100:
            return {"success": False, "message": f"Je n'arrive pas à lire le texte de « {src['nom']} » : je ne rédige rien."}
        travail = {"texte": texte, "nom": src["nom"], "details": params.get("details"), "spec": spec, "formats": formats}
        quoi = ("le compte rendu de" if nature == "compte_rendu" else "le résumé de") + f" « {src['nom']} »"
        return _lancer(nature, travail, quoi, SECONDES_PAR_MORCEAU * len(_morceaux(texte)) + SECONDES_PAR_SECTION, origine)
    # Tout autre document : la structure vient de la demande (rapport, fiche, note, plan de cours, document…)
    sujet = (params.get("sujet") or "").strip()
    if not sujet:
        propositions.proposer(None, "complement", origine, completer=f"{phrase or 'fais un document'} sur")
        libelle = GENRES_LIBELLES.get(nature, "le document").split(" ", 1)[-1]
        return {"success": True, "message": f"Sur quel sujet dois-je rédiger {('la ' if libelle in ('fiche', 'note') else 'le ')}{libelle} ?"}
    spec.setdefault("genre", nature if nature in GENRES_LIBELLES else "document")
    n = spec.get("nb_parties") or (len(spec["parties"]) if spec.get("parties") else 5)
    travail = {"demande": phrase or sujet, "sujet": sujet, "spec": spec, "formats": formats}
    quoi = f"{GENRES_LIBELLES.get(spec['genre'], 'le document').replace('un ', 'le ').replace('une ', 'la ')} sur « {sujet} »"
    return _lancer("document", travail, quoi, SECONDES_PAR_SECTION * (n + 2), origine)


# --------------------------------------------------------------------------- #
#  Artefacts sur mesure / AS2 — les retouches : une NOUVELLE version, jamais d'écrasement
# --------------------------------------------------------------------------- #

OPERATIONS = ("ajouter", "raccourcir", "developper", "ton", "enlever", "titre", "corriger", "pdf")
_RANGS = {"premiere": 1, "1ere": 1, "1re": 1, "deuxieme": 2, "seconde": 2, "2e": 2, "troisieme": 3, "3e": 3,
          "quatrieme": 4, "4e": 4, "cinquieme": 5, "5e": 5, "sixieme": 6, "derniere": -1}


def _cible_retouche(params: dict) -> tuple[Optional[dict], Optional[dict]]:
    """(le document à retoucher, None) ou (None, réponse). Document : {chemin, contenu, spec, pied, externe,
    mise_en_forme, pdf}."""
    from core import file_indexer as fi
    from core import propositions
    from tools import documents as d
    from tools import fichiers as tf

    chemin = params.get("document_chemin")
    if not chemin and params.get("document"):
        demande = tf.nettoyer_requete(params["document"])
        try:
            trouves = [r for r in fi.chercher_nom(demande, limite=8) if r.get("ext") in (".docx",)]
        except Exception as e:
            return None, tf._indisponible(e)
        if not trouves:
            return None, {"success": False, "message": f"Je ne trouve aucun document Word « {demande} » à retoucher. "
                                                       "Je sais retoucher un document Word (.docx)."}
        if len(trouves) > 1 and trouves[0].get("rang") == trouves[1].get("rang"):
            options = trouves[:5]
            propositions.proposer(None, "choix_retouche", params.get("_origine"),
                                  options=[f"{params.get('phrase_retouche') or params.get('phrase')} — document : {r['chemin']}"
                                           for r in options])
            lignes = "\n".join(f"{k + 1}. {r['nom']} — {os.path.dirname(r['chemin'])}" for k, r in enumerate(options))
            return None, {"success": True, "message": f"Plusieurs documents « {demande} » :\n{lignes}\nLequel ? Dis « le 1 »…"}
        chemin = trouves[0]["chemin"]
    if not chemin:
        dernier = dernier_document_recent()
        if dernier:
            return {"chemin": dernier.get("docx") or dernier.get("pdf"), "contenu": dernier["contenu"], "spec": dernier["spec"],
                    "pied": dernier["pied"], "externe": False, "mise_en_forme": {}, "pdf": dernier.get("pdf"),
                    "docx": dernier.get("docx")}, None
        return None, {"success": False, "message": "Je n'ai pas de document récent à retoucher : dis-moi lequel "
                                                   "(par exemple « raccourcis mon rapport de stage »)."}
    chemin = pathlib.Path(chemin)
    if chemin.suffix.lower() != ".docx" or not chemin.exists():
        return None, {"success": False, "message": f"Je ne sais retoucher qu'un document Word (.docx) : « {chemin.name} »."}
    try:
        contenu, mf = d.lire_docx(chemin)
    except Exception as e:
        _noter_erreur("execution", f"lecture de {chemin.name} : {type(e).__name__}")
        return None, {"success": False, "message": f"Je n'arrive pas à lire « {chemin.name} » ({type(e).__name__})."}
    if not contenu["sections"]:
        return None, {"success": False, "message": f"« {chemin.name} » ne contient pas de texte que je sache retoucher."}
    externe = d.dossier_atlas().resolve() not in chemin.resolve().parents
    pdf = chemin.with_suffix(".pdf")
    # Une retouche ne casse pas les consignes d'avant : ce que le document n'a pas, on ne le lui remet pas.
    from core import specification as sp

    spec = {"sommaire": bool(mf.get("sommaire")), "langue": sp.langue(" ".join(d._textes(contenu))) or "fr"}
    if not any(s.get("points") for s in contenu["sections"]):
        spec["puces"] = False
    return {"chemin": chemin, "contenu": contenu, "spec": spec, "pied": d.PIED_RAPPORT, "externe": externe,
            "mise_en_forme": mf, "docx": chemin, "pdf": pdf if pdf.exists() else None}, None


def _section_index(contenu: dict, params: dict) -> Optional[int]:
    from core import specification as sp

    sections = contenu["sections"]
    rang = params.get("rang")
    if isinstance(rang, int) and rang:
        k = rang - 1 if rang > 0 else len(sections) - 1
        return k if 0 <= k < len(sections) else None
    nom = (params.get("objet") or "").strip()
    if nom:
        for k, s in enumerate(sections):
            if sp._proche(nom, s["titre"]) or sp._proche(s["titre"], nom):
                return k
    return None


def _reecrire_section(s: dict, consigne: str, langue: str = "fr") -> tuple[Optional[dict], str]:
    """Le modèle réécrit une partie ; ce qu'il AJOUTE comme fait (chiffre, date, nom) est retiré."""
    from tools import documents as d

    texte = "\n".join(s["paragraphes"] + [f"- {p}" for p in s.get("points") or []])
    r, raison = _essayer(f"Partie « {s['titre']} » :\n---\n{texte}\n---\n{consigne}", SCHEMA_SECTION,
                         lambda x: d.valider_contenu({"titre": "Section", "sections": [{"titre": "Section", **x}]}, langue=langue)
                         if isinstance(x, dict) else (False, "objet JSON attendu"), systeme(langue))
    if not r:
        return None, raison
    nouvelle = {"titre": s["titre"], "paragraphes": r["paragraphes"], "points": r.get("points") or []}
    if s.get("tableau"):
        nouvelle["tableau"] = s["tableau"]
    propre, _ = d.retirer_faits_inventes({"titre": "x", "sections": [nouvelle]}, texte + " " + s["titre"])
    return (propre["sections"][0] if propre["sections"] else None), ""


def _appliquer_retouche(op: str, cible: dict, params: dict) -> tuple[Optional[dict], str, str]:
    """(nouveau contenu, ce qui a changé — en clair, raison de l'échec)."""
    import copy

    from core import specification as sp
    from tools import documents as d

    c = copy.deepcopy(cible["contenu"])
    sections = c["sections"]
    langue = (cible.get("spec") or {}).get("langue", "fr")
    if op == "titre":
        ancien = c["titre"]
        c["titre"] = (params.get("valeur") or "").strip().strip("«»\"“” ")
        if not c["titre"]:
            return None, "", "quel titre ?"
        return c, f"J'ai changé le titre « {ancien} » en « {c['titre']} », et gardé le reste.", ""
    if op == "enlever":
        quoi = sp.plat(params.get("objet") or "")
        if quoi in ("sommaire", "le sommaire", "table des matieres"):
            c["_sommaire"] = False
            return c, "J'ai enlevé le sommaire, et gardé le reste.", ""
        if "tableau" in quoi:
            n = sum(1 for s in sections if s.pop("tableau", None))
            return (c, f"J'ai enlevé {n} tableau{'x' if n > 1 else ''}, et gardé le reste.", "") if n else \
                (None, "", "ce document n'a pas de tableau")
        k = _section_index(c, {"objet": params.get("objet"), "rang": params.get("rang")})
        if k is None and re.search(r"\bconclusion\b", quoi):
            k = next((i for i, s in enumerate(sections) if re.search(r"\bconclusion\b|\bpour conclure\b", sp.plat(s["titre"]))), None)
        if k is None and re.search(r"\bintroduction\b", quoi):
            k = next((i for i, s in enumerate(sections) if re.search(r"\bintroduction\b", sp.plat(s["titre"]))), None)
        if k is None:
            return None, "", f"je ne trouve pas de partie « {params.get('objet')} » dans ce document"
        if len(sections) == 1:
            return None, "", "c'est la seule partie du document"
        retiree = sections.pop(k)
        return c, f"J'ai enlevé la partie « {retiree['titre']} », et gardé le reste.", ""
    if op == "pdf":
        return c, "", ""
    if op == "ajouter":
        sujet = (params.get("objet") or "").strip()
        if not sujet:
            return None, "", "sur quoi doit porter la nouvelle partie ?"
        titre = sujet[:1].upper() + sujet[1:]
        plan = {"titre": c["titre"], "sections": [s["titre"] for s in sections] + [titre]}
        paras, lo, hi = 2, 90, 150
        corps, raison = _rediger_section(f"ajouter au document une partie sur {sujet}", plan, titre,
                                         cible.get("spec") or {}, False, paras, lo, hi,
                                         "La partie doit compléter le document sans répéter les autres parties.")
        if not corps:
            return None, "", f"la nouvelle partie n'a pas pu être rédigée ({raison})"
        nouvelle = {"titre": titre, "paragraphes": corps["paragraphes"], "points": corps.get("points") or []}
        if re.search(r"\b(causes?|origines?|contexte|definitions?|presentation|historique)\b", sp.plat(sujet)):
            # Ce qui explique le reste va en tête (après l'introduction s'il y en a une), pas après les conséquences
            k = 1 if re.search(r"\bintroduction\b", sp.plat(sections[0]["titre"])) else 0
            ou = "après l'introduction" if k else "au début"
        else:
            k = next((i for i, s in enumerate(sections) if re.search(r"\bconclusion\b|\bpour conclure\b", sp.plat(s["titre"]))),
                     len(sections))
            ou = "avant la conclusion" if k < len(sections) else "à la fin"
        sections.insert(k, nouvelle)
        n = len(nouvelle["paragraphes"])
        return c, f"J'ai ajouté une partie « {titre} » ({n} paragraphe{'s' if n > 1 else ''}), {ou}, et gardé le reste.", ""
    if op in ("raccourcir", "developper", "ton", "corriger"):
        avant = sp.mots(c)
        if op == "developper":
            k = _section_index(c, params)
            cibles = [k] if k is not None else (list(range(len(sections))) if not (params.get("rang") or params.get("objet"))
                                                else [])
            if not cibles:
                return None, "", "je ne trouve pas cette partie dans le document"
        else:
            cibles = list(range(len(sections)))
        modifiees, refusees = 0, 0
        for k in cibles:
            s = sections[k]
            n = sum(len(p.split()) for p in s["paragraphes"])
            if op == "raccourcir":
                # Le modèle rend environ 2/3 de ce qu'on lui demande (mesuré : 835 → 245, 960 → 386 pour « moitié »)
                consigne = (f"Réécris cette partie en environ {max(25, int(n * 0.7))} mots : garde les idées principales, "
                            "et TOUS les chiffres, dates et noms qu'elle contient. N'ajoute rien.")
            elif op == "developper":
                consigne = (f"Développe cette partie en environ {n * 2} mots : explique davantage, avec des exemples "
                            "généraux. Garde tout ce qu'elle dit. N'invente ni chiffre, ni date, ni nom.")
            elif op == "ton":
                ton = {"formel": "un ton plus formel et soutenu", "simple": "un langage plus simple, sans jargon, des "
                       "phrases plus courtes", "enfant": "des mots simples, pour un enfant", "amical": "un ton plus amical",
                       "professionnel": "un ton plus professionnel"}.get(params.get("valeur") or "", f"un ton {params.get('valeur')}")
                consigne = (f"Réécris cette partie avec {ton}. Garde le même sens, la même longueur environ, et tous les "
                            "chiffres, dates et noms. N'ajoute rien.")
            else:
                consigne = ("Corrige UNIQUEMENT l'orthographe, la grammaire, les accords et la ponctuation de cette partie. "
                            "Ne change ni le sens, ni la longueur, ni les mots corrects, ni les chiffres, ni les noms.")
            nouvelle, raison = _reecrire_section(s, consigne, langue)
            if nouvelle is None:
                return None, "", f"la partie « {s['titre']} » n'a pas pu être réécrite ({raison or 'tout aurait été retiré'})"
            if op in ("corriger", "ton") and len(nouvelle.get("points") or []) != len(s.get("points") or []):
                # Banc du 03/11 : le modèle « corrigeait » en perdant les points de liste ; ils ne se perdent pas
                nouvelle["points"] = list(s.get("points") or [])
            if op == "corriger":
                ancien = " ".join(s["paragraphes"])
                neuf = " ".join(nouvelle["paragraphes"])
                # une « correction » qui change la longueur de plus de 10 % réécrit le texte : refusée (banc du 03/11)
                if not (0.9 <= len(neuf) / max(1, len(ancien)) <= 1.1):
                    refusees += 1
                    continue
            if nouvelle["paragraphes"] != s["paragraphes"] or nouvelle.get("points") != s.get("points"):
                modifiees += 1
            sections[k] = nouvelle
        apres = sp.mots(c)
        if op == "corriger":
            if not modifiees and refusees:
                return cible["contenu"], ("Je n'ai gardé aucune correction : celles que j'ai obtenues réécrivaient le texte "
                                          "au lieu de le corriger. Le texte est inchangé."), ""
            if not modifiees:
                return cible["contenu"], "Je n'ai trouvé aucune faute à corriger : le texte est inchangé.", ""
            return c, f"J'ai corrigé {modifiees} partie{'s' if modifiees > 1 else ''} sur {len(sections)}, sans changer le sens.", ""
        if op == "raccourcir":
            return c, f"Je l'ai raccourci : {avant} → {apres} mots, les {len(sections)} parties gardées.", ""
        if op == "developper":
            quoi = f"la partie « {sections[cibles[0]]['titre']} »" if len(cibles) == 1 else "toutes les parties"
            return c, f"J'ai développé {quoi} : {avant} → {apres} mots au total, et gardé le reste.", ""
        return c, f"Je l'ai réécrit avec {params.get('valeur') and ('un ton ' + params['valeur']) or 'le ton demandé'} " \
                  f"({modifiees} partie{'s' if modifiees > 1 else ''}), même structure.", ""
    return None, "", f"je ne sais pas faire cette retouche ({op})"


def _travail_retouche(op: str, cible: dict, params: dict, origine: Optional[str]) -> None:
    global _en_cours
    from core import annonces

    try:
        message = _faire_retouche(op, cible, params)
        annonces.publier(message, origine)
    except Exception as e:
        logger.exception("[ARTEFACT] Retouche : échec")
        _noter_erreur("execution", f"{type(e).__name__}: {e}")
        annonces.publier(f"Je n'ai pas pu retoucher le document : erreur inattendue ({type(e).__name__}). "
                         "Le document d'origine n'a pas changé.", origine)
    finally:
        _en_cours = None
        _occupe.release()


def _faire_retouche(op: str, cible: dict, params: dict) -> str:
    """Applique, écrit la nouvelle version, la relit. Le message ne dit « j'ai… » qu'après la relecture."""
    from tools import documents as d

    contenu, change, raison = _appliquer_retouche(op, cible, params)
    nom = pathlib.Path(cible["chemin"]).name
    if contenu is None:
        return f"Je n'ai pas pu retoucher « {nom} » : {raison}. Le document d'origine n'a pas changé."
    if contenu is cible["contenu"]:
        return f"{change} Je n'ai pas écrit de nouvelle version de « {nom} »."
    sommaire = contenu.pop("_sommaire", (cible.get("spec") or {}).get("sommaire"))
    chemins: dict = {}
    formats = []
    if op == "pdf":
        base = pathlib.Path(cible.get("docx") or cible["chemin"]).with_suffix(".pdf")
        chemins[".pdf"] = base if not base.exists() else d.chemin_version(base)
        formats = ["pdf"]
    else:
        for ext, ancien in ((".docx", cible.get("docx")), (".pdf", cible.get("pdf"))):
            if ancien:
                chemins[ext] = d.chemin_version(pathlib.Path(ancien))
                formats.append(ext[1:])
    faits, raison = produire(contenu, formats, cible.get("pied") or d.PIED_RAPPORT, sommaire=sommaire, chemins=chemins)
    if raison or not faits:
        return f"Je n'ai pas pu écrire la nouvelle version de « {nom} » : {raison or 'aucun fichier'}. " \
               "Le document d'origine n'a pas changé."
    _retenir_dernier(contenu, faits, cible.get("spec") or {}, cible.get("pied") or d.PIED_RAPPORT)
    if cible.get("docx") and op == "pdf":
        _dernier["docx"] = pathlib.Path(cible["docx"])
    _ouvrir(faits)
    ou = " et ".join(str(f) for f in faits)
    if op == "pdf":
        texte = f"J'ai mis « {contenu['titre']} » en PDF : {ou}. Le Word reste tel quel."
    else:
        texte = f"{change} Nouvelle version : {ou}. L'ancienne reste : {pathlib.Path(cible['chemin']).name}."
    if cible.get("externe"):
        perdu = d.perte_de_mise_en_forme(cible.get("mise_en_forme") or {})
        texte += (" Attention : ce document n'a pas été créé par moi ; la nouvelle version a ma mise en page, et ce "
                  "qui n'a pas été gardé : " + ", ".join(perdu) + "." if perdu else
                  " Ce document n'a pas été créé par moi ; sa mise en forme était simple : rien de mesurable n'a été perdu.")
    return texte


def retoucher(params: dict) -> dict:
    """L'outil artefact_retoucher. Rapide (titre, enlever, PDF) : tout de suite ; avec le modèle : en arrière-plan."""
    global _en_cours
    op = params.get("operation")
    if op not in OPERATIONS:
        return {"success": False, "message": "Je ne sais pas faire cette retouche."}
    cible, reponse = _cible_retouche(params)
    if reponse:
        return reponse
    if op in ("titre", "enlever", "pdf"):
        message = _faire_retouche(op, cible, params)
        return {"success": not message.startswith("Je n'ai pas pu"), "message": message}
    if not _occupe.acquire(blocking=False):
        return {"success": False, "message": f"Je rédige déjà {_en_cours} : attends qu'il soit prêt."}
    nom = pathlib.Path(cible["chemin"]).name
    _en_cours = f"la retouche de « {nom} »"
    n = len(cible["contenu"]["sections"])
    duree = SECONDES_PAR_SECTION * (1 if op in ("ajouter", "developper") and (params.get("rang") or params.get("objet")) else n)
    try:
        _en_arriere_plan(lambda: _travail_retouche(op, cible, params, params.get("_origine")))
    except Exception:
        _en_cours = None
        _occupe.release()
        raise
    libelle = {"ajouter": "j'ajoute une partie à", "raccourcis": "je raccourcis", "raccourcir": "je raccourcis",
               "developper": "je développe", "ton": "je réécris", "corriger": "je corrige"}.get(op, "je retouche")
    return {"success": True, "message": f"D'accord, {libelle} « {nom} », environ {duree} secondes. L'original n'est pas "
                                        "modifié : j'écris une nouvelle version, et je te préviens quand elle est prête."}
