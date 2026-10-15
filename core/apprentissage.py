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


def _mm():
    from core.memory_manager import get_memory_manager

    return get_memory_manager()


def _connectee(m) -> bool:
    """Une mémoire utilisable pour l'apprentissage (un double de test minimal n'en est pas une)."""
    try:
        return bool(m.is_connected()) and hasattr(m, "apprentissage_lire")
    except Exception:
        return False


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
    m = _mm()
    if not _connectee(m):
        _signaler_indisponible("mémoire indisponible")
        return False
    if not m.apprentissage_ecrire(doc_id, libelle, meta):
        _signaler_indisponible("écriture impossible (embeddings ou mémoire)")
        return False
    return True


def _lire(ids: list[str]) -> list[dict]:
    m = _mm()
    if neutralise() or not _connectee(m):
        return []
    try:
        return m.apprentissage_lire(ids)
    except Exception as e:
        logger.warning("Apprentissage : lecture impossible (%s)", e)
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
_VOULU_VIDE = re.compile(r"^(?:juste|rien|pas|savoir|dire merci|que ça|que ca)\b", re.IGNORECASE)
_CORRECTIONS = [
    re.compile(r"^(?:non|nan)?[\s,.!]*(?:c'?est pas ça|c'?est pas ca|ce n'est pas ça|ce n'est pas ca|pas ça|pas ca)"
               r"[\s,.!]*(?:je voulais dire|je voulais|je veux)?\s*(?:que tu\s+)?(?P<v>.+)$", re.IGNORECASE),
    re.compile(r"^(?:non|nan)?[\s,.!]*je t'ai demand[ée]\s+(?:de\s+|d')?(?P<v>.+)$", re.IGNORECASE),
    re.compile(r"^(?:non|nan)[\s,.!]*(?:je voulais dire|je voulais|je veux)\s+(?:que tu\s+)?(?P<v>.+)$",
               re.IGNORECASE),
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
    None, "correction": bool}.
    """
    if neutralise():
        return {"phrase": phrase, "annonce": None, "correction": False}
    voulu = detecter_correction(phrase, echange_precedent())
    if voulu:
        precedente = echange_precedent()["phrase"]
        etat = apprendre_correction(precedente, voulu, origine)
        annonce = f"D'accord : « {precedente} », c'était « {voulu} ». Je le retiens." if etat == "appris" else None
        return {"phrase": voulu, "annonce": annonce, "correction": True}
    appris = correction_pour(phrase)
    if appris:
        return {"phrase": appris, "annonce": f"Comme tu me l'as appris, je comprends « {appris} ».",
                "correction": False}
    return {"phrase": phrase, "annonce": None, "correction": False}


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

def lister() -> list[dict]:
    m = _mm()
    if not _connectee(m):
        return []
    try:
        recs = m.apprentissage_lire(None)
    except Exception as e:
        logger.warning("Apprentissage : liste impossible (%s)", e)
        return []
    return sorted(({"id": r["id"], "type": r["meta"].get("type", "?"), "libelle": r["libelle"],
                    "details": {k: v for k, v in r["meta"].items() if k not in ("created_at", "timestamp")},
                    "depuis": r["meta"].get("timestamp", "")} for r in recs), key=lambda r: r["depuis"])


def chercher(sujet: str) -> list[dict]:
    n = normaliser(sujet)
    if not n:
        return []
    return [r for r in lister() if n in normaliser(r["libelle"]) or n in normaliser(r["details"].get("cle", ""))]


def oublier(ids: list[str]) -> int:
    if not ids:
        return 0
    m = _mm()
    if not _connectee(m):
        return 0
    n = m.apprentissage_effacer(ids)
    logger.info("[APPRENTISSAGE] %d enregistrement(s) oublié(s)", n)
    return n


def texte_liste(sujet: Optional[str] = None) -> str:
    recs = chercher(sujet) if sujet else lister()
    if not recs:
        return f"Je n'ai rien appris sur « {sujet} »." if sujet else "Je n'ai encore rien appris."
    lignes = [f"- {r['libelle']}" for r in recs]
    return "Voici ce que j'ai appris :\n" + "\n".join(lignes)
