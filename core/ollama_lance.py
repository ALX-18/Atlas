"""
Brief Installeur — fin, IF7 (Réunion n° 3, point 4) : Atlas arrête, à sa fermeture, l'Ollama qu'il a lancé
lui-même. Jamais un Ollama qu'il a trouvé déjà en marche.

Le lanceur (installeur/lancer.py) et l'installeur (installeur/etapes.py) notent l'Ollama qu'ils lancent dans
`data/ollama_lance.json` : son numéro de processus ET son heure de démarrage (un numéro peut être réutilisé par
Windows). À l'arrêt ordonné, le serveur d'Atlas relit la note et n'arrête ce processus que si les trois concordent :
même heure de démarrage, c'est bien Ollama, et il appartient au compte courant. Sinon, rien n'est arrêté, et la
note périmée est retirée.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import pathlib
from typing import Callable, Optional

logger = logging.getLogger("atlas.ollama_lance")

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHEMIN = ROOT / "data" / "ollama_lance.json"


def noter(pid: int, debut: Optional[float], par: str, chemin: pathlib.Path = CHEMIN) -> None:
    chemin = pathlib.Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_name(chemin.name + ".nouveau")
    temporaire.write_text(json.dumps({"pid": int(pid), "debut": debut, "par": par,
                                      "quand": f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S}"}), encoding="utf-8")
    os.replace(temporaire, chemin)


def _retirer(chemin: pathlib.Path) -> None:
    try:
        chemin.unlink()
    except FileNotFoundError:
        pass


def _attendre(procs, timeout):
    import psutil

    return psutil.wait_procs(procs, timeout=timeout)


def arreter(chemin: pathlib.Path = CHEMIN, process: Optional[Callable] = None, moi: Optional[str] = None,
            attendre: Callable = _attendre) -> str:
    """« aucun » (pas de note), « arrete », « parti » (déjà arrêté) ou « pas_le_sien » (rien n'est arrêté)."""
    chemin = pathlib.Path(chemin)
    try:
        note = json.loads(chemin.read_text(encoding="utf-8"))
        pid, debut = int(note["pid"]), note.get("debut")
    except FileNotFoundError:
        return "aucun"
    except Exception as e:
        logger.warning("Note de l'Ollama lancé par Atlas illisible (%s) : rien n'est arrêté", type(e).__name__)
        _retirer(chemin)
        return "pas_le_sien"
    if process is None:
        import psutil

        process = psutil.Process
    if moi is None:
        from core.proprietaire import compte_courant

        moi = compte_courant()
    try:
        p = process(pid)
        meme_debut = debut is not None and abs(float(p.create_time()) - float(debut)) < 0.01
        est_ollama = (p.name() or "").lower().startswith("ollama")
        a_moi = (p.username() or "").strip().lower() == (moi or "").strip().lower()
    except Exception as e:
        if type(e).__name__ == "NoSuchProcess":
            _retirer(chemin)
            return "parti"
        logger.warning("Ollama lancé par Atlas (processus %s) : illisible (%s) — rien n'est arrêté", pid,
                       type(e).__name__)
        _retirer(chemin)
        return "pas_le_sien"
    if not (meme_debut and est_ollama and a_moi):
        logger.info("Ollama noté (processus %s) : ce n'est plus celui qu'Atlas a lancé — rien n'est arrêté", pid)
        _retirer(chemin)
        return "pas_le_sien"
    try:
        enfants = list(p.children(recursive=True))
    except Exception:
        enfants = []
    tous = [p, *enfants]
    for q in tous:
        try:
            q.terminate()
        except Exception:
            pass
    _, restants = attendre(tous, timeout=5)
    for q in restants:
        try:
            q.kill()
        except Exception:
            pass
    _retirer(chemin)
    logger.info("Ollama lancé par Atlas (processus %s, %d sous-processus) arrêté", pid, len(enfants))
    return "arrete"
