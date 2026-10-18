"""
Sprint Artefacts — ce qu'Atlas annonce de lui-même, hors d'une réponse : un travail long qui se
termine (un document rédigé en arrière-plan).

- `publier(message, origine)` : rangé ici, et montré tout de suite par une notification Windows ;
  à la voix, prononcé si le moteur vocal tourne ;
- `lire()` : la fenêtre d'Atlas les relève (GET /api/annonces, toutes les 1,5 s) et les affiche.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

logger = logging.getLogger("atlas.annonces")

_verrou = threading.Lock()
_file: list[dict] = []
NOTIFIER = True            # les tests le coupent (conftest) : aucune notification sur l'écran d'Alexis


def voix_active():
    """Le moteur vocal s'il tourne, sinon None (sans jamais le créer)."""
    import sys

    module = sys.modules.get("core.voice_engine")
    moteur = getattr(module, "_voice_engine", None) if module else None
    return moteur if getattr(moteur, "_running", False) else None


def publier(message: str, origine: Optional[str] = None, titre: str = "Atlas",
            parole: Optional[str] = None) -> None:
    """parole (Compétences 1) : la phrase à prononcer si la voix est active, quelle que soit
    l'origine (un rappel arrive sans demande) ; sinon, prononcé seulement pour une demande vocale."""
    with _verrou:
        _file.append({"message": message, "origine": origine, "quand": time.strftime("%H:%M:%S")})
    logger.info("[ANNONCE] %s", message)

    def notifier():
        try:
            import asyncio

            from tools.notifier import notify

            asyncio.run(notify(message[:240], title=titre))
        except Exception as e:
            logger.debug("Notification impossible : %s", e)

    if NOTIFIER:
        threading.Thread(target=notifier, name="atlas-annonce", daemon=True).start()   # hors de la boucle de l'API
    if parole:
        moteur = voix_active()
        if moteur is not None:
            try:
                moteur._speak_sync(parole)
            except Exception as e:
                logger.debug("Annonce vocale impossible : %s", e)
    elif origine == "voix":
        try:
            from core.voice_engine import get_voice_engine

            moteur = get_voice_engine()
            if getattr(moteur, "_running", False):
                moteur._speak_sync(message.split(" : ")[0] + ".")      # la phrase, pas le chemin
        except Exception as e:
            logger.debug("Annonce vocale impossible : %s", e)


def lire() -> list[dict]:
    with _verrou:
        out = list(_file)
        _file.clear()
    return out
