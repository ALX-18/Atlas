"""
Sprint Compétences 2 — le coffre des secrets : le Gestionnaire d'identification de Windows.

Ce qu'il garde : les mots de passe d'application (Gmail, iCloud) et les adresses iCal privées. Chaque
secret est une identification « générique » nommée `Atlas:<service>` ; le nom d'utilisateur porte
l'adresse du compte (ce n'est pas un secret, `doctor.py` peut l'afficher). Windows chiffre le secret
pour la session de la personne (DPAPI).

Règles (Réunion n° 2, §9) :
- un secret est lu seulement quand il sert, par l'adaptateur qui se connecte ; jamais gardé dans une
  variable globale, jamais écrit dans un journal, un rapport ou une consigne au modèle ;
- il n'arrive ici que par la fenêtre de connexion d'Atlas (champ masqué), jamais par la conversation ;
- une déconnexion le supprime (`supprimer`).

Hors du modèle de menace, et dit comme tel : un logiciel malveillant qui tourne sous le compte de la
personne lit ce coffre aussi bien qu'Atlas (ou ce qu'elle tape). L'« effacement mémoire » d'une chaîne
Python n'est pas fiable : il n'est pas promis.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger("atlas.coffre")

PREFIXE = "Atlas:"


class CoffreIndisponible(RuntimeError):
    """Le Gestionnaire d'identification ne répond pas (hors Windows, service arrêté…)."""


class _Windows:
    """Le vrai coffre : le Gestionnaire d'identification de Windows (win32cred)."""

    def ecrire(self, cible: str, identifiant: str, secret: str) -> None:
        import win32cred

        win32cred.CredWrite({"Type": win32cred.CRED_TYPE_GENERIC, "TargetName": cible, "UserName": identifiant,
                             "CredentialBlob": secret, "Comment": "Atlas — connexion facultative, « déconnecte » "
                             "dans Atlas la supprime", "Persist": win32cred.CRED_PERSIST_LOCAL_MACHINE}, 0)

    def lire(self, cible: str) -> Optional[tuple[str, str]]:
        import pywintypes
        import win32cred

        try:
            c = win32cred.CredRead(cible, win32cred.CRED_TYPE_GENERIC, 0)
        except pywintypes.error as e:
            if e.winerror == 1168:          # ERROR_NOT_FOUND
                return None
            raise
        blob = c.get("CredentialBlob") or b""
        secret = blob.decode("utf-16-le") if isinstance(blob, bytes) else str(blob)
        return c.get("UserName") or "", secret

    def supprimer(self, cible: str) -> bool:
        import pywintypes
        import win32cred

        try:
            win32cred.CredDelete(cible, win32cred.CRED_TYPE_GENERIC, 0)
            return True
        except pywintypes.error as e:
            if e.winerror == 1168:
                return False
            raise


_coffre = None


def _actuel():
    global _coffre
    if _coffre is None:
        _coffre = _Windows()
    return _coffre


def utiliser(coffre) -> None:
    """Remplace le coffre (tests : un coffre en mémoire ; jamais le vrai Gestionnaire d'Alexis)."""
    global _coffre
    _coffre = coffre


def _cible(service: str) -> str:
    return PREFIXE + service


def enregistrer(service: str, identifiant: str, secret: str) -> None:
    try:
        _actuel().ecrire(_cible(service), identifiant, secret)
    except Exception as e:
        raise CoffreIndisponible(f"le Gestionnaire d'identification refuse l'enregistrement ({type(e).__name__})") from None
    logger.info("[COFFRE] Secret enregistré pour %s.", service)


def lire(service: str) -> Optional[tuple[str, str]]:
    """(identifiant, secret), ou None. À appeler au moment de se connecter, jamais avant."""
    try:
        return _actuel().lire(_cible(service))
    except Exception as e:
        raise CoffreIndisponible(f"le Gestionnaire d'identification ne répond pas ({type(e).__name__})") from None


def identifiant(service: str) -> Optional[str]:
    """L'adresse du compte enregistré (pas le secret), ou None s'il n'y en a pas."""
    try:
        r = lire(service)
    except CoffreIndisponible:
        return None
    return r[0] if r else None


def supprimer(service: str) -> bool:
    try:
        fait = _actuel().supprimer(_cible(service))
    except Exception as e:
        raise CoffreIndisponible(f"le Gestionnaire d'identification refuse la suppression ({type(e).__name__})") from None
    logger.info("[COFFRE] Secret de %s %s.", service, "supprimé" if fait else "absent")
    return fait


class EnMemoire:
    """Un coffre jetable, pour les tests."""

    def __init__(self):
        self.contenu: dict[str, tuple[str, str]] = {}

    def ecrire(self, cible, identifiant, secret):
        self.contenu[cible] = (identifiant, secret)

    def lire(self, cible):
        return self.contenu.get(cible)

    def supprimer(self, cible):
        return self.contenu.pop(cible, None) is not None
