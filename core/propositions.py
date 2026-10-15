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


def proposer(phrase: str, sorte: str, origine: Optional[str], cle: Optional[str] = None) -> None:
    """Retient la demande à faire si Alexis répond « oui » (une seule question à la fois)."""
    global _en_attente
    _en_attente = {"phrase": phrase, "sorte": sorte, "origine": origine, "cle": cle, "quand": time.monotonic()}
    logger.info("[PROPOSITION] %s : « %s »", sorte, phrase)


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
    if n in _OUI:
        return {"oui": True, **question}
    if n in _NON:
        return {"oui": False, **question}
    return None
