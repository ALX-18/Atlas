"""
Brief Installeur — fin, IF7 (Réunion n° 3) : à qui appartient ce qui écoute sur un port de 127.0.0.1 ?

`127.0.0.1` est commun à toutes les sessions Windows ouvertes d'un PC. Un Atlas (8550) ou un Ollama (11434) qui
écoute peut donc appartenir à un AUTRE compte. Avant de s'y brancher, chaque point de connexion (le lanceur, la
fenêtre, le serveur, l'installeur) vérifie le propriétaire du processus qui écoute :

- « libre »     : rien n'écoute ;
- « a_moi »     : le processus appartient au compte courant ;
- « autre »     : il appartient à un autre compte (son nom a pu être lu) ;
- « illisible » : Windows refuse de dire à qui il appartient. Il compte comme « pas à moi ».

Sans droits d'administrateur, Windows donne le numéro du processus qui écoute (GetExtendedTcpTable), mais pas,
en général, le compte d'un processus d'un autre compte : c'est le cas « illisible », mesuré sur `AtlasTest`.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Iterable, Optional

logger = logging.getLogger("atlas.proprietaire")

PORT_ATLAS = 8550
PORT_OLLAMA = 11434
_ADRESSES = ("127.0.0.1", "0.0.0.0")       # celles qui reçoivent une connexion à 127.0.0.1, la plus précise d'abord


@dataclass(frozen=True)
class Verdict:
    etat: str                               # libre | a_moi | autre | illisible
    pid: Optional[int] = None
    compte: Optional[str] = None            # le compte lu, s'il a pu l'être

    @property
    def a_moi(self) -> bool:
        return self.etat == "a_moi"

    @property
    def refuse(self) -> bool:
        return self.etat in ("autre", "illisible")


class AutreCompte(RuntimeError):
    """Ce qui écoute n'appartient pas au compte courant (ou son propriétaire est illisible) : rien n'est envoyé."""

    def __init__(self, composant: str, verdict: Verdict):
        self.composant, self.verdict = composant, verdict
        super().__init__(message_refus(composant, verdict, sortie="relancer"))


# --------------------------------------------------------------------------- #
#  Lectures (le système) — remplaçables dans les tests
# --------------------------------------------------------------------------- #

def connexions_tcp() -> list:
    import psutil

    return psutil.net_connections(kind="tcp4")


def compte_du_processus(pid: int, process=None) -> Optional[str]:
    """Le compte (DOMAINE\\nom) du processus, ou None s'il est illisible (refus d'accès, processus parti)."""
    try:
        import psutil

        return (process or psutil.Process)(pid).username() or None
    except Exception:
        return None


def debut_processus(pid: int) -> Optional[float]:
    try:
        import psutil

        return psutil.Process(pid).create_time()
    except Exception:
        return None


def compte_courant() -> str:
    try:
        import psutil

        return psutil.Process().username()
    except Exception:
        import os

        return f"{os.environ.get('USERDOMAIN', '')}\\{os.environ.get('USERNAME', '')}"


def ecouteur(port: int, connexions: Optional[Iterable] = None) -> Optional[int]:
    """Le processus qui recevrait une connexion à 127.0.0.1:port. None : personne ; 0 : quelqu'un, numéro inconnu."""
    trouves = {}
    for c in (connexions_tcp() if connexions is None else connexions):
        laddr = getattr(c, "laddr", None)
        if str(getattr(c, "status", "")).upper() != "LISTEN" or not laddr or laddr.port != port:
            continue
        if laddr.ip in _ADRESSES and laddr.ip not in trouves:
            trouves[laddr.ip] = c.pid or 0
    for ip in _ADRESSES:
        if ip in trouves:
            return trouves[ip]
    return None


def _meme_compte(a: Optional[str], b: Optional[str]) -> bool:
    return bool(a) and bool(b) and a.strip().lower() == b.strip().lower()


def verifier(port: int, *, connexions: Optional[Iterable] = None, compte_de: Optional[Callable] = None,
             moi: Optional[str] = None) -> Verdict:
    pid = ecouteur(port, connexions)
    if pid is None:
        return Verdict("libre")
    if not pid:
        return Verdict("illisible", pid=None)
    compte = (compte_de or compte_du_processus)(pid)
    if compte is None:
        return Verdict("illisible", pid=pid)
    if _meme_compte(compte, moi or compte_courant()):
        return Verdict("a_moi", pid=pid, compte=compte)
    return Verdict("autre", pid=pid, compte=compte)


# --------------------------------------------------------------------------- #
#  La garde : vérifier à chaque connexion, relire le compte seulement si le processus a changé
# --------------------------------------------------------------------------- #

class Garde:
    """Avant chaque échange : qui écoute ? Le même processus (numéro ET heure de démarrage) qu'au dernier contrôle
    réussi : rien à relire (~2 ms). Un autre : son compte est relu. Pas à moi : AutreCompte, rien n'est envoyé."""

    def __init__(self, port: int, composant: str, *, connexions: Optional[Callable] = None,
                 compte_de: Optional[Callable] = None, moi: Optional[str] = None,
                 debut: Optional[Callable] = None):
        self.port, self.composant = port, composant
        self._connexions, self._compte_de, self._moi, self._debut = connexions, compte_de, moi, debut
        self._vu: Optional[tuple] = None
        self._verrou = threading.Lock()

    def _liste(self):
        return self._connexions() if self._connexions else None

    def verifier(self) -> Verdict:
        with self._verrou:
            debut = self._debut or debut_processus
            if self._vu is not None:
                pid = ecouteur(self.port, self._liste())
                if pid and (pid, debut(pid)) == self._vu:
                    return Verdict("a_moi", pid=pid)
            v = verifier(self.port, connexions=self._liste(), compte_de=self._compte_de, moi=self._moi)
            if v.refuse:
                self._vu = None
                logger.warning("[COMPTES] %s sur 127.0.0.1:%d : %s (processus %s) — refusé, rien n'est envoyé",
                               self.composant, self.port, v.etat, v.pid)
                raise AutreCompte(self.composant, v)
            self._vu = (v.pid, debut(v.pid)) if v.a_moi else None
            return v


_GARDES: dict[int, Garde] = {}


def garde(port: int, composant: str) -> Verdict:
    g = _GARDES.get(port)
    if g is None:
        g = _GARDES.setdefault(port, Garde(port, composant))
    return g.verifier()


def garde_ollama() -> Verdict:
    """Avant de parler à Ollama (serveur d'Atlas, installeur). Un refus est une bascule, dite et visible."""
    try:
        v = garde(PORT_OLLAMA, "Ollama")
    except AutreCompte as e:
        try:
            from core_conversational.degradations import signaler

            signaler("ollama_autre_compte", f"{e.verdict.etat} (processus {e.verdict.pid})")
        except Exception:
            pass
        raise
    if v.a_moi:
        try:
            from core_conversational.degradations import lever

            lever("ollama_autre_compte")
        except Exception:
            pass
    return v


def reinitialiser_gardes() -> None:
    _GARDES.clear()


# --------------------------------------------------------------------------- #
#  Ce que la personne lit
# --------------------------------------------------------------------------- #

_DESCRIPTION = {
    "Atlas": "Atlas",
    "Ollama": "Ollama, le moteur qui fait réfléchir Atlas,",
}
_SORTIES = {
    "reessayer": "Puis cliquez sur Réessayer.",
    "installation": "Puis relancez l'installation.",
    "relancer": "Puis relancez Atlas.",
}


def _nom_court(compte: Optional[str]) -> str:
    return (compte or "").rsplit("\\", 1)[-1].strip()


def message_refus(composant: str, verdict: Verdict, *, sortie: str = "reessayer", rien_envoye: bool = True) -> str:
    """Nomme le composant, ne dit que ce qui a été vérifié, et donne une vraie sortie."""
    desc = _DESCRIPTION.get(composant, composant)
    if verdict.etat == "illisible":
        constat = (f"Atlas n'a pas pu vérifier à qui appartient {desc.rstrip(',')}, déjà lancé sur ce PC. "
                   "Par prudence, il ne s'en sert pas.")
        qui = "Si une autre personne a une session ouverte sur ce PC, elle doit se déconnecter"
    else:
        nom = _nom_court(verdict.compte)
        par = f" (compte « {nom} »)" if nom else ""
        if composant == "Atlas":
            constat = (f"Atlas est déjà ouvert dans une autre session Windows de ce PC{par}. Il ne peut tourner que "
                       "pour une personne à la fois.")
        else:
            constat = (f"{desc} est déjà lancé dans une autre session Windows de ce PC{par}. Atlas ne s'en sert "
                       "pas : il appartient à un autre compte.")
        qui = "Pour utiliser Atlas ici, la personne de l'autre session doit se déconnecter"
    parties = [constat]
    if rien_envoye:
        parties.append(f"Atlas ne s'est pas connecté à cet {composant} : rien n'a été envoyé.")
    parties.append(f"{qui} : Démarrer > son nom > Se déconnecter (« Changer d'utilisateur » ne suffit pas). "
                   f"Ou bien redémarrez le PC. {_SORTIES.get(sortie, _SORTIES['reessayer'])}")
    return "\n\n".join(parties)
