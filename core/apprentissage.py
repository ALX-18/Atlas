"""
Sprint Apprentissage 1 — Atlas retient tes corrections et ses échecs.

Ce qui est appris est un ENREGISTREMENT EXPLICITE, lu par identifiant — pas un poids caché, pas
un voisin sémantique (le mécanisme du sprint F4 récupérait des voisins et n'a jamais changé le
comportement d'Atlas : rapport D, §4.1). Deux sortes :

- « correction » : demande d'origine NORMALISÉE → la phrase qu'Alexis voulait dire. Appliquée à
  la même demande normalisée, jamais à une demande « qui ressemble ». La phrase voulue repasse
  par le classifieur, le validateur et CONFIRMATION_POLICY, comme toute demande.
- « methode » : outil + application + cible → la couche ou la méthode qui a marché (tentée en
  premier), celles qui ont échoué avant elle ou trop tardé (évitées), et le nombre d'échecs
  complets d'affilée.

Règles :
- on n'apprend que d'Alexis : une demande venue de la fenêtre d'Atlas, de l'interface web ou de la
  voix (ORIGINES_ALEXIS). Un script, un test ou un essai n'envoie pas d'origine ;
- ATLAS_APPRENTISSAGE=off neutralise tout (ni lecture ni écriture) : comportement d'avant ;
- mémoire indisponible : Atlas fonctionne sans, et le dit (bascule « apprentissage ») ;
- tout se liste (« qu'est-ce que tu as appris ? ») et s'efface (« oublie ce que tu as appris
  sur … », avec confirmation).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
import unicodedata
from typing import Optional

logger = logging.getLogger("atlas.apprentissage")

ORIGINES_ALEXIS = {"bureau", "fenetre", "voix"}
FENETRE_SUITE_S = 180.0          # une correction suit la demande qu'elle corrige de près
METHODES_SANS_LECON = {"cache"}  # le cache de clics manque souvent : ce n'est pas un échec à éviter


# --------------------------------------------------------------------------- #
#  Outils
# --------------------------------------------------------------------------- #

def neutralise() -> bool:
    return os.environ.get("ATLAS_APPRENTISSAGE", "").strip().lower() in ("off", "0", "non", "false")


def _sans_accents(texte: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texte) if unicodedata.category(c) != "Mn")


_POLITESSE = re.compile(r"\b(?:s'il te plait|s'il vous plait|stp|svp|merci|please|atlas)\b")
_TETE_POLIE = re.compile(r"^(?:est-ce que tu peux|est ce que tu peux|tu peux|peux-tu|peux tu|pourrais-tu|"
                         r"pourrais tu|tu pourrais)\s+")


def normaliser(phrase: str) -> str:
    """Minuscules, sans accents, sans politesse ni ponctuation : la clé d'une correction."""
    t = _sans_accents((phrase or "").replace("’", "'").lower())
    t = _POLITESSE.sub(" ", t)
    t = re.sub(r"[^\w\s'-]", " ", t)
    t = " ".join(t.split())
    t = _TETE_POLIE.sub("", t)
    return t.strip(" -'")


def _id(prefixe: str, cle: str) -> str:
    return f"{prefixe}_{hashlib.sha1(cle.encode('utf-8')).hexdigest()[:16]}"


def _signaler_indisponible(cause: str) -> None:
    from core_conversational.degradations import signaler

    signaler("apprentissage", cause)


def _ecrire(doc_id: str, libelle: str, meta: dict) -> bool:
    """Apprentissage 2 / AQ2 : SQLite (core/apprentissage_store.py), une transaction par écriture."""
    from core import apprentissage_store as store

    try:
        store.ecrire(doc_id, meta.get("type", "?"), libelle, meta)
        return True
    except Exception as e:
        logger.warning("Apprentissage : écriture impossible (%s)", e)
        _signaler_indisponible(f"écriture impossible ({e})")
        return False


def _lire(ids: Optional[list[str]]) -> list[dict]:
    from core import apprentissage_store as store

    if neutralise():
        return []
    try:
        return store.lire(ids)
    except Exception as e:
        logger.warning("Apprentissage : lecture impossible (%s)", e)
        _signaler_indisponible(f"lecture impossible ({e})")
        return []


# --------------------------------------------------------------------------- #
#  Causes d'échec (défaut 2 du rapport D : les vrais messages étaient mal classés)
# --------------------------------------------------------------------------- #

def classify_cause(message: Optional[str], code: Optional[str] = None) -> str:
    t = _sans_accents(f"{message or ''} {code or ''}".lower())
    if "timeout" in t or "trop lente" in t:
        return "timeout"
    if "ambig" in t:
        return "ambiguous"
    if re.search(r"fenetre '.*' introuvable|aucune fenetre trouvee|app_not_found|aucune application cible", t):
        return "app_not_found"
    if re.search(r"aucune couche n'a reussi|impossible de trouver|not found|introuvable|no_match|all_failed", t):
        return "not_found"
    if "permission" in t or "denied" in t or "refus" in t:
        return "permission_denied"
    return "other"


# --------------------------------------------------------------------------- #
#  L'échange précédent (une correction suit la demande qu'elle corrige)
# --------------------------------------------------------------------------- #

_ECHANGE: dict = {"phrase": None, "quand": 0.0, "origine": None}


def noter_echange(phrase: str, origine: Optional[str]) -> None:
    _ECHANGE.update({"phrase": phrase, "quand": time.monotonic(), "origine": origine})


def echange_precedent() -> Optional[dict]:
    if _ECHANGE["phrase"] and time.monotonic() - _ECHANGE["quand"] <= FENETRE_SUITE_S:
        return dict(_ECHANGE)
    return None


def reinitialiser_echange() -> None:
    _ECHANGE.update({"phrase": None, "quand": 0.0, "origine": None})


# --------------------------------------------------------------------------- #
#  AP2 — reconnaître une correction
# --------------------------------------------------------------------------- #

_PAS_UNE_CORRECTION = re.compile(
    r"^(?:non|nan)?[\s,.!]*(?:merci|c'?est bon|ca ira|ça ira|pas maintenant|pas besoin|pas grave|"
    r"c'?est pas grave|je ne veux pas|je veux pas|pourquoi)\b|^pas (?:mal|besoin|grave|maintenant)\b",
    re.IGNORECASE)
_VOULU_VIDE = re.compile(r"^(?:juste|rien|pas|savoir|dire merci|que ça|que ca|toi|moi|ça|ca|du tout|"
                         r"pour rire|une blague)\b", re.IGNORECASE)
_CORRECTIONS = [
    re.compile(r"^(?:non|nan)?[\s,.!]*(?:c'?est pas ça|c'?est pas ca|ce n'est pas ça|ce n'est pas ca|pas ça|pas ca)"
               r"[\s,.!]*(?:je voulais dire|je voulais|je veux)?\s*(?:que tu\s+)?(?P<v>.+)$", re.IGNORECASE),
    re.compile(r"^(?:non|nan)?[\s,.!]*je t'ai demand[ée]\s+(?:de\s+|d')?(?P<v>.+)$", re.IGNORECASE),
    re.compile(r"^(?:non|nan)[\s,.!]*(?:je voulais dire|je voulais|je veux)\s+(?:que tu\s+)?(?P<v>.+)$",
               re.IGNORECASE),
    # Apprentissage 2 / AQ5 : « tu t'es trompé, c'était… », « je parlais de… », « non, c'était… »
    re.compile(r"^(?:non|nan)?[\s,.!]*tu t'es tromp[ée]e?[\s,.!]*(?:c'?[ée]tait|je voulais dire|je voulais|je veux)"
               r"\s+(?:que tu\s+)?(?P<v>.+)$", re.IGNORECASE),
    re.compile(r"^(?:non|nan)?[\s,.!]*je parlais d(?:e\s+|')(?P<v>.+)$", re.IGNORECASE),
    re.compile(r"^(?:non|nan)[\s,.!]*c'?[ée]tait\s+(?P<v>.+)$", re.IGNORECASE),
]
_PAS_X_MAIS_Y = re.compile(r"^pas\s+(?P<x>.+?)\s*,\s*(?:mais\s+)?(?P<y>.+)$", re.IGNORECASE)


def detecter_correction(phrase: str, precedente: Optional[dict]) -> Optional[str]:
    """La demande voulue si `phrase` corrige la demande précédente, sinon None.

    « non merci », « non c'est bon » ne sont pas des corrections ; sans demande précédente
    (dans la fenêtre de suite), rien n'en est une.
    """
    if not precedente or not precedente.get("phrase"):
        return None
    texte = (phrase or "").replace("’", "'").strip()
    if _PAS_UNE_CORRECTION.search(texte):
        return None
    voulu = None
    for motif in _CORRECTIONS:
        m = motif.match(texte)
        if m:
            voulu = m.group("v")
            break
    if voulu is None:
        m = _PAS_X_MAIS_Y.match(texte)
        if m:
            avant = precedente["phrase"]
            x = m.group("x").strip()
            i = avant.lower().find(x.lower())
            if i < 0:
                return None
            voulu = avant[:i] + m.group("y").strip().rstrip(" .!?") + avant[i + len(x):]
    if voulu is None:
        return None
    voulu = voulu.strip().rstrip(" .!?")
    if not voulu or _VOULU_VIDE.match(voulu):
        return None
    return voulu


# --------------------------------------------------------------------------- #
#  AP2 — corrections apprises
# --------------------------------------------------------------------------- #

def apprendre_correction(phrase: str, voulu: str, origine: Optional[str]) -> str:
    """'appris' | 'neutralise' | 'non_alexis' | 'ignore' | 'indisponible'."""
    if neutralise():
        return "neutralise"
    if origine not in ORIGINES_ALEXIS:
        logger.info("[APPRENTISSAGE] Correction NON retenue (origine %r : pas Alexis) : %r → %r", origine, phrase, voulu)
        return "non_alexis"
    cle = normaliser(phrase)
    if not cle or cle == normaliser(voulu):
        return "ignore"
    if _dans_le_corpus(cle):
        logger.info("[APPRENTISSAGE] « %s » est dans le corpus de routes avec une autre route : la correction "
                    "d'Alexis prime ; à revoir dans le corpus.", phrase)
    ok = _ecrire(_id("corr", cle), f"« {phrase} » → « {voulu} »",
                 {"type": "correction", "cle": cle, "phrase": phrase, "voulu": voulu, "origine": origine})
    if ok:
        logger.info("[APPRENTISSAGE] Correction retenue : %r → %r", cle, voulu)
    return "appris" if ok else "indisponible"


def correction_pour(phrase: str) -> Optional[str]:
    """La phrase voulue apprise pour cette demande (normalisée), sinon None."""
    cle = normaliser(phrase)
    if not cle:
        return None
    recs = _lire([_id("corr", cle)])
    return recs[0]["meta"].get("voulu") if recs else None


def _dans_le_corpus(cle: str) -> bool:
    try:
        from pathlib import Path

        corpus = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "corpus_routes.json"
        return any(normaliser(e["phrase"]) == cle for e in json.loads(corpus.read_text(encoding="utf-8")))
    except Exception:
        return False


def preparer(phrase: str, origine: Optional[str]) -> dict:
    """Avant de router une demande : est-ce une correction ? une demande déjà corrigée ?

    Retourne {"phrase": la demande à router, "annonce": ce qu'Atlas dit en tête de réponse ou
    None, "correction": bool, "reponse": réponse directe sans rien router ou None, "a_noter": la
    demande qu'une correction suivante corrigerait, ou None}.

    Apprentissage 2 : d'abord, est-ce le « oui » ou le « non » d'Alexis à une question d'Atlas
    (réessayer un clic, une habitude) ? Ce n'est pas un apprentissage : jamais neutralisé.
    """
    from core import habitudes, propositions

    commande = habitudes.commande(phrase, origine)       # AQ4 : « arrête de me proposer ça »…
    if commande:
        return {"phrase": phrase, "annonce": None, "correction": False, "a_noter": None, "reponse": commande}
    reponse = propositions.repondre(phrase, origine)
    if reponse and reponse["oui"]:
        return {"phrase": reponse["phrase"], "annonce": None, "correction": False, "reponse": None,
                "a_noter": reponse["phrase"]}
    if reponse:
        return {"phrase": phrase, "annonce": None, "correction": False, "a_noter": None,
                "reponse": "D'accord, je n'y touche pas."}
    if neutralise():
        return {"phrase": phrase, "annonce": None, "correction": False, "reponse": None, "a_noter": phrase}
    voulu = detecter_correction(phrase, echange_precedent())
    if voulu:
        precedente = echange_precedent()["phrase"]
        etat = apprendre_correction(precedente, voulu, origine)
        annonce = f"D'accord : « {precedente} », c'était « {voulu} ». Je le retiens." if etat == "appris" else None
        return {"phrase": voulu, "annonce": annonce, "correction": True, "reponse": None, "a_noter": None}
    appris = correction_pour(phrase)
    if appris:
        return {"phrase": appris, "annonce": f"Comme tu me l'as appris, je comprends « {appris} ».",
                "correction": False, "reponse": None, "a_noter": phrase}
    return {"phrase": phrase, "annonce": None, "correction": False, "reponse": None, "a_noter": phrase}


# --------------------------------------------------------------------------- #
#  AP1 — méthodes qui marchent (clic, premier plan, lancement)
# --------------------------------------------------------------------------- #

LIBELLES_OUTILS = {"ui_click_element": "Clic sur", "window_focus": "Premier plan de", "launch_app": "Lancement de"}


def _cle_methode(outil: str, app: str, cible: str) -> str:
    return f"{outil}|{normaliser(app)}|{normaliser(cible)}"


def ordre_appris(outil: str, app: str, cible: str) -> Optional[dict]:
    recs = _lire([_id("meth", _cle_methode(outil, app, cible))])
    if not recs:
        return None
    m = recs[0]["meta"]
    return {"premiere": m.get("premiere") or None, "eviter": json.loads(m.get("eviter") or "[]"),
            "echecs_totaux": int(m.get("echecs_totaux") or 0), "cause": m.get("cause") or "",
            "chemin": m.get("chemin") or None}


def appliquer_ordre(methodes: list[str], appris: Optional[dict]) -> list[str]:
    """La méthode gagnante en premier ; celles qui ont échoué ou trop tardé, en DERNIER.

    Évitées mais pas retirées : quand la gagnante marche, on s'arrête avant elles (aussi
    rapide qu'un retrait) ; si elle échoue un jour, elles restent là, dans la même demande.
    """
    if not appris:
        return list(methodes)
    eviter = [x for x in methodes if x in set(appris.get("eviter") or [])]
    ordre = [x for x in methodes if x not in eviter] + eviter
    premiere = appris.get("premiere")
    if premiere in ordre:
        ordre = [premiere] + [x for x in ordre if x != premiere]
    return ordre


def noter_methodes(outil: str, app: str, cible: str, tentatives: list[dict], origine: Optional[str],
                   chemin: Optional[str] = None) -> Optional[dict]:
    """Retient ce qui a marché (et ce qui a échoué) pour cet outil, cette application, cette cible.

    tentatives : [{"methode": nom de couche ou de méthode RÉELLE, "resultat": success|failure|
    timeout|skipped|disambiguation}] — jamais l'issue globale (défaut 1 du rapport D).
    """
    if neutralise() or origine not in ORIGINES_ALEXIS or not tentatives:
        return None
    precedent = ordre_appris(outil, app, cible) or {}
    gagnante = next((t["methode"] for t in tentatives if t.get("resultat") == "success"), None)
    if gagnante:
        avant = []
        for t in tentatives:
            if t["methode"] == gagnante:
                break
            if t.get("resultat") in ("failure", "timeout") and t["methode"] not in METHODES_SANS_LECON:
                avant.append(t["methode"])
        rec = {"premiere": gagnante, "eviter": avant, "echecs_totaux": 0, "cause": ""}
    else:
        lentes = [t["methode"] for t in tentatives if t.get("resultat") == "timeout"]
        premiere = precedent.get("premiere")
        if premiere and any(t["methode"] == premiere for t in tentatives):
            premiere = None          # la gagnante d'avant vient d'échouer : l'écran a changé
        rec = {"premiere": premiere, "eviter": lentes, "echecs_totaux": precedent.get("echecs_totaux", 0) + 1,
               "cause": "timeout" if lentes else "not_found"}
    rec["chemin"] = chemin or (precedent.get("chemin") if gagnante else None)
    nom = LIBELLES_OUTILS.get(outil, outil)
    morceaux = [f"commencer par « {rec['premiere']} »"] if rec["premiere"] else []
    if rec["eviter"]:
        morceaux.append("éviter " + ", ".join(f"« {x} »" for x in rec["eviter"]))
    if rec["echecs_totaux"]:
        morceaux.append(f"{rec['echecs_totaux']} échec(s) complet(s) d'affilée")
    sujet = f"« {cible} » dans « {app} »" if cible else f"« {app} »"
    libelle = f"{nom} {sujet} : " + ("; ".join(morceaux) or "rien de particulier")
    meta = {"type": "methode", "outil": outil, "app": app, "cible": cible, "premiere": rec["premiere"] or "",
            "eviter": json.dumps(rec["eviter"]), "echecs_totaux": rec["echecs_totaux"], "cause": rec["cause"],
            "chemin": rec["chemin"] or "", "origine": origine}
    if _ecrire(_id("meth", _cle_methode(outil, app, cible)), libelle, meta):
        logger.info("[APPRENTISSAGE] %s", libelle)
        return rec
    return None


# --------------------------------------------------------------------------- #
#  Lister, chercher, oublier
# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #
#  Apprentissage 2 / AQ3 — tes refus
#
#  Un refus, c'est Annuler dans un dialogue de confirmation, sur une demande venue d'Alexis.
#  Une expiration n'en est pas un (Alexis était peut-être absent). Effet : à partir du 2e refus
#  d'affilée de la même demande normalisée pour la même action, Atlas le dit AVANT de proposer
#  et suggère la correction. La confirmation reste affichée ; rien n'est sauté ni refusé.
#  Une acceptation remet le compte à zéro (Alexis peut avoir changé d'avis).
# --------------------------------------------------------------------------- #

REFUS_AVANT_RAPPEL = 2
_NOMBRES = {2: "deux", 3: "trois", 4: "quatre", 5: "cinq"}


def _id_refus(demande: str, outil: str) -> str:
    return _id("refus", f"{outil}|{normaliser(demande)}")


def noter_refus(demande: Optional[str], outil: str, cible: Optional[str], origine: Optional[str]) -> Optional[int]:
    """Enregistre un Annuler d'Alexis ; retourne le nombre de refus d'affilée (None si rien retenu)."""
    if neutralise() or origine not in ORIGINES_ALEXIS or not (demande or "").strip():
        return None
    doc_id = _id_refus(demande, outil)
    avant = _lire([doc_id])
    fois = int(avant[0]["meta"].get("fois") or 0) + 1 if avant else 1
    libelle = f"Refus : « {demande} » annulé {fois} fois d'affilée"
    meta = {"type": "refus", "outil": outil, "cible": str(cible or ""), "demande": demande,
            "cle": normaliser(demande), "fois": fois, "origine": origine}
    if _ecrire(doc_id, libelle, meta):
        logger.info("[APPRENTISSAGE] %s", libelle)
        return fois
    return None


def accepte(demande: Optional[str], outil: str) -> None:
    """Alexis a confirmé : les refus d'avant ne disent plus rien de ce qu'il veut."""
    if neutralise() or not (demande or "").strip():
        return
    doc_id = _id_refus(demande, outil)
    if _lire([doc_id]):
        oublier([doc_id])


def rappel_refus(demande: Optional[str], outil: str) -> Optional[str]:
    """La phrase dite avant de proposer, à partir du 2e refus d'affilée ; sinon None."""
    if neutralise() or not (demande or "").strip():
        return None
    recs = _lire([_id_refus(demande, outil)])
    if not recs:
        return None
    m = recs[0]["meta"]
    fois = int(m.get("fois") or 0)
    if fois < REFUS_AVANT_RAPPEL:
        return None
    return (f"Les {_NOMBRES.get(fois, str(fois))} dernières fois, tu as annulé « {m.get('demande')} ». "
            "Je te le propose quand même ; si tu voulais autre chose, dis « non, je voulais… ».")


def lister_enregistrements() -> list[dict]:
    return [{"id": r["id"], "type": r["type"], "libelle": r["libelle"],
             "details": dict(r["meta"]), "depuis": r["depuis"]} for r in _lire(None)]


def lister() -> list[dict]:
    """Tout ce qui est appris : les enregistrements, puis les habitudes actives (AQ4, calculées)."""
    from core import habitudes

    try:
        calculees = habitudes.comme_enregistrements()
    except Exception as e:
        logger.warning("Habitudes : liste impossible (%s)", e)
        calculees = []
    return lister_enregistrements() + calculees


def chercher(sujet: str) -> list[dict]:
    n = normaliser(sujet)
    if not n:
        return []
    return [r for r in lister() if n in normaliser(r["libelle"]) or n in normaliser(r["details"].get("cle", ""))]


def oublier(ids: list[str]) -> int:
    from core import apprentissage_store as store

    if not ids:
        return 0
    from core import habitudes

    # AQ4 : une habitude calculée ne s'efface pas du journal ; « l'oublier », c'est l'écarter.
    ecartees = habitudes.oublier_virtuelles(ids)
    ids = [i for i in ids if i not in ecartees]
    try:
        n = store.effacer(ids) + len(ecartees) if ids else len(ecartees)
    except Exception as e:
        logger.warning("Apprentissage : effacement impossible (%s)", e)
        _signaler_indisponible(f"effacement impossible ({e})")
        return 0
    logger.info("[APPRENTISSAGE] %d enregistrement(s) oublié(s)", n)
    return n


def texte_liste(sujet: Optional[str] = None) -> str:
    recs = chercher(sujet) if sujet else lister()
    if not recs:
        return f"Je n'ai rien appris sur « {sujet} »." if sujet else "Je n'ai encore rien appris."
    lignes = [f"- {r['libelle']}" for r in recs]
    return "Voici ce que j'ai appris :\n" + "\n".join(lignes)
