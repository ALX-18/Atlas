"""
Brief Installeur — fin, IF7 (Réunion n° 3, « B minimal ») : une clé locale par installation.

`127.0.0.1` est commun aux sessions Windows d'un PC : sans clé, un programme d'un AUTRE compte pouvait appeler
l'API d'Atlas (lire la mémoire, confirmer une action en attente). Désormais :

- Atlas tire une clé aléatoire à son premier démarrage, l'écrit dans `data/cle_locale` (dans le dossier d'Atlas du
  compte), et la restreint au compte seul (icacls). Elle ne change plus ensuite : un redémarrage ne casse rien ;
- toute requête à l'API porte cette clé dans l'en-tête `X-Atlas-Cle`, vérifiée par le seul middleware de main.py ;
- seule la fenêtre native la porte, APRÈS avoir vérifié que le serveur appartient au compte (desktop/connexion.py) ;
- clé absente ou abîmée : une erreur qui dit comment réparer (Quitter, relancer : Atlas en crée une nouvelle).

Un Atlas d'essai (rejeu, redirections ATLAS_*) ne crée jamais la clé dans les vraies données : ses scripts
posent ATLAS_CLE_LOCALE vers un fichier jetable.
"""

from __future__ import annotations

import logging
import os
import pathlib
import secrets
import subprocess
from typing import Optional

logger = logging.getLogger("atlas.cle_locale")

ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAUT = ROOT / "data" / "cle_locale"
VARIABLE = "ATLAS_CLE_LOCALE"
ENTETE = "X-Atlas-Cle"
_LONGUEUR_MIN = 40


class CleIntrouvable(RuntimeError):
    """La clé locale est absente, illisible ou abîmée."""


def chemin() -> pathlib.Path:
    v = os.environ.get(VARIABLE)
    return pathlib.Path(v) if v else DEFAUT


def message_cle_introuvable(ou: pathlib.Path) -> str:
    return (f"La clé d'Atlas est introuvable ou abîmée ({ou.parent.name}\\{ou.name}). Sans elle, la fenêtre ne peut "
            "pas parler à Atlas. Pour réparer : quittez Atlas (icône près de l'horloge > Quitter), puis relancez-le "
            "avec son raccourci : il en crée une nouvelle.")


def _valide(cle: str) -> bool:
    return len(cle) >= _LONGUEUR_MIN and all(c.isalnum() or c in "-_" for c in cle)


def lire(ou: Optional[pathlib.Path] = None) -> str:
    ou = pathlib.Path(ou) if ou else chemin()
    try:
        cle = ou.read_text(encoding="utf-8").strip()
    except OSError as e:
        raise CleIntrouvable(message_cle_introuvable(ou)) from e
    if not _valide(cle):
        raise CleIntrouvable(message_cle_introuvable(ou))
    return cle


def _compte() -> str:
    from core.proprietaire import compte_courant

    return compte_courant()


def _restreindre(ou: pathlib.Path) -> bool:
    """Le fichier n'est lisible que par le compte : héritage retiré, une seule autorisation."""
    try:
        r = subprocess.run(["icacls", str(ou), "/inheritance:r", "/grant:r", f"{_compte()}:(F)"],
                           capture_output=True, text=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        logger.warning("[CLE] restriction au compte impossible (%s) : la clé garde les droits du dossier d'Atlas",
                       type(e).__name__)
        return False
    if r.returncode != 0:
        logger.warning("[CLE] restriction au compte refusée par icacls (code %s) : %s", r.returncode,
                       (r.stderr or r.stdout or "").strip()[:200])
        return False
    return True


def preparer(ou: Optional[pathlib.Path] = None) -> str:
    """Au démarrage du serveur : la clé existante, ou une nouvelle (créée une seule fois, puis restreinte)."""
    ou = pathlib.Path(ou) if ou else chemin()
    try:
        return lire(ou)
    except CleIntrouvable:
        pass
    from core import donnees_reelles

    donnees_reelles.verifier_ecriture(ou, "création de la clé locale")
    cle = secrets.token_urlsafe(32)
    ou.parent.mkdir(parents=True, exist_ok=True)
    temporaire = ou.with_name(ou.name + ".nouvelle")
    temporaire.write_text(cle, encoding="utf-8")
    os.replace(temporaire, ou)
    restreinte = _restreindre(ou)
    logger.info("[CLE] Nouvelle clé locale créée (%s)%s", ou.name, "" if restreinte else " — NON restreinte au compte")
    return cle


# --------------------------------------------------------------------------- #
#  La clé attendue par le serveur
# --------------------------------------------------------------------------- #

_attendue: Optional[str] = None


def installer(cle: str) -> None:
    global _attendue
    _attendue = cle


def attendue() -> Optional[str]:
    """Celle du serveur. Sans démarrage complet (tests), elle est lue dans le fichier ; absente : None (tout refusé)."""
    if _attendue:
        return _attendue
    try:
        return lire()
    except CleIntrouvable:
        return None


def entetes(ou: Optional[pathlib.Path] = None) -> dict:
    """Pour un client (fenêtre, doctor, scripts d'essai) : l'en-tête qui porte la clé."""
    return {ENTETE: lire(ou)}


def acceptee(fournie: Optional[str]) -> bool:
    cle = attendue()
    return bool(cle) and bool(fournie) and secrets.compare_digest(fournie.encode(), cle.encode())


def entetes_si_prete(ou: Optional[pathlib.Path] = None) -> dict:
    """Pour attendre qu'un Atlas démarre : l'en-tête si la clé existe déjà, sinon rien (la demande sera refusée)."""
    try:
        return entetes(ou)
    except CleIntrouvable:
        return {}


def pour_essai() -> pathlib.Path:
    """Scripts d'essai (rejeux, mesures) : leur Atlas d'essai et eux partagent une clé JETABLE, hors de data/.
    Posée dans l'environnement du script, elle passe aux processus qu'il lance."""
    import tempfile

    if not os.environ.get(VARIABLE):
        os.environ[VARIABLE] = str(pathlib.Path(tempfile.gettempdir()) / "atlas_essai_cle_locale")
    return chemin()
