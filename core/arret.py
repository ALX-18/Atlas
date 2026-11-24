"""
Brief Installeur — fin, IF7 (Réunion n° 3, point 4) : « Quitter » est un arrêt ordonné.

Avant : « Quitter » (icône près de l'horloge) faisait os._exit(0), qui court-circuitait le nettoyage : verrou,
pont, et l'Ollama lancé par Atlas restait à l'écoute (un autre compte du PC restait bloqué). Désormais :

- « Quitter » demande l'arrêt au serveur uvicorn (should_exit) : le nettoyage de main.py (lifespan) s'exécute,
  dont l'arrêt de l'Ollama lancé par Atlas et la libération du verrou ;
- un dernier recours est armé : si l'arrêt n'a pas fini après DELAI secondes, l'Ollama d'Atlas est arrêté, le
  verrou libéré, puis le processus est arrêté net — et c'est noté au journal.
"""

from __future__ import annotations

import logging
import os
import signal
import threading
from typing import Callable, Optional

logger = logging.getLogger("atlas.arret")

DELAI = 20.0
SERVEUR = None          # le serveur uvicorn, posé par main.py au lancement


def demander_arret() -> None:
    if SERVEUR is not None:
        SERVEUR.should_exit = True
        return
    signal.raise_signal(signal.SIGINT)          # lancement avec rechargement : uvicorn gère Ctrl+C


def arret_force(forcer: Callable[[int], None] = os._exit, arreter_ollama: Optional[Callable[[], None]] = None,
                liberer: Optional[Callable[[], None]] = None) -> None:
    logger.warning("Quitter : l'arrêt ordonné n'a pas fini en %d s — arrêt net du processus, en dernier recours "
                   "(Ollama lancé par Atlas arrêté, verrou libéré avant)", DELAI)
    for etape in (arreter_ollama, liberer):
        if etape is None:
            continue
        try:
            etape()
        except Exception as e:
            logger.warning("Quitter, dernier recours : %s (%s)", type(e).__name__, e)
    forcer(0)


def arret_ordonne(demander: Callable[[], None] = demander_arret, minuteur=threading.Timer,
                  forcer: Callable[[int], None] = os._exit, arreter_ollama: Optional[Callable[[], None]] = None,
                  liberer: Optional[Callable[[], None]] = None, delai: float = DELAI) -> None:
    logger.info("Quitter : arrêt ordonné demandé")
    t = minuteur(delai, lambda: arret_force(forcer=forcer, arreter_ollama=arreter_ollama, liberer=liberer))
    t.daemon = True
    t.start()
    demander()
