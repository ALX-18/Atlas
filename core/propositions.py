"""
Sprint Apprentissage 2 — une question d'Atlas en attente du « oui » ou du « non » d'Alexis.

Atlas propose, il n'exécute jamais de lui-même :
  - AQ1 : un clic non vérifié n'est pas refait ; Atlas demande « tu veux que je réessaie ? » ;
  - AQ4 : une habitude détectée ; Atlas demande « Je l'ouvre ? ».

Un « oui » (forme courte et fermée, comparée sur la phrase normalisée) route la demande proposée
par le chemin normal : classifieur, validateur, confirmations. Un « non » ferme la question.
Toute autre phrase la ferme aussi : un « oui » tardif ne déclenche jamais une vieille proposition.
Aucun modèle de langue ici (invariant 3).
"""

from __future__ import annotations

import logging
import time
from typing import Optional

logger = logging.getLogger("atlas.propositions")

DUREE_S = 120.0
_OUI = {"oui", "ouais", "ok", "okay", "d accord", "vas y", "oui vas y", "ok vas y", "go", "yes", "fais le",
        "oui fais le", "reessaie", "oui reessaie", "reessaye", "oui reessaye", "je veux bien", "oui je veux bien",
        "volontiers", "oui volontiers", "oui ouvre le", "ouvre le", "oui s il te plait"}
_NON = {"non", "nan", "non c est bon", "pas maintenant", "non pas maintenant", "laisse tomber", "non laisse tomber",
        "non laisse", "c est bon", "non ca ira", "ca ira", "pas besoin", "non pas besoin"}

_en_attente: Optional[dict] = None

_ORDINAUX = {"premier": 0, "premiere": 0, "deuxieme": 1, "second": 1, "seconde": 1, "troisieme": 2, "quatrieme": 3,
             "cinquieme": 4, "un": 0, "une": 0, "deux": 1, "trois": 2, "quatre": 3, "cinq": 4}


def _rang(n: str) -> Optional[int]:
    """« le 2 », « 2 », « le deuxième », « numéro 3 », « ouvre le 1 » → l'indice ; sinon None."""
    import re

    m = re.fullmatch(r"(?:ouvre\s+)?(?:le\s+|la\s+|l\s+)?(?:numero\s+|n\s+)?(\w+)(?:\s+fichier)?", n)
    if not m:
        return None
    mot = m.group(1)
    if mot.isdigit():
        return int(mot) - 1
    return _ORDINAUX.get(mot)


def proposer(phrase: Optional[str], sorte: str, origine: Optional[str], cle: Optional[str] = None,
             options: Optional[list[str]] = None, completer: Optional[str] = None) -> None:
    """Retient la demande à faire si Alexis répond « oui » (une seule question à la fois).

    options (Index des fichiers) : un CHOIX ; « le 2 », « le deuxième », « 2 » route options[1]."""
    global _en_attente
    # completer (Artefacts) : Atlas a POSÉ UNE QUESTION (le sujet, la date…) ; la réponse, quelle qu'elle
    # soit, complète la demande : « fais-moi un rapport sur » + « la photosynthèse ».
    _en_attente = {"phrase": phrase, "sorte": sorte, "origine": origine, "cle": cle, "options": options or [],
                   "completer": completer, "quand": time.monotonic()}
    logger.info("[PROPOSITION] %s : « %s »%s", sorte, phrase, f" ({len(options)} choix)" if options else "")


def en_attente() -> Optional[dict]:
    if _en_attente and time.monotonic() - _en_attente["quand"] <= DUREE_S:
        return dict(_en_attente)
    return None


def fermer() -> None:
    global _en_attente
    _en_attente = None


def repondre(message: str, origine: Optional[str]) -> Optional[dict]:
    """Le message répond-il à la question en attente ?

    Retourne {"oui": True, "phrase", "sorte", "cle"} ; {"oui": False, …} pour un « non » ; None si le
    message n'est pas une réponse (la question est alors fermée).
    """
    from core.apprentissage import normaliser

    question = en_attente()
    fermer()
    if not question or question["origine"] != origine:
        return None
    n = normaliser(message).replace("'", " ").replace("-", " ").strip(" !.?,")
    if question.get("completer"):
        if n in _NON or n in {"annule", "laisse tomber", "oublie", "rien"} or not n:
            return {"oui": False, **question}
        return {"oui": True, **question, "phrase": f"{question['completer']} {message.strip()}"}
    if question.get("options"):
        k = _rang(n)
        if k is not None and 0 <= k < len(question["options"]):
            return {"oui": True, **question, "phrase": question["options"][k]}
        if k is not None or n in _NON:
            return {"oui": False, **question} if n in _NON else None
        return None
    if n in _OUI and question.get("phrase"):
        return {"oui": True, **question}
    if n in _NON:
        return {"oui": False, **question}
    return None
