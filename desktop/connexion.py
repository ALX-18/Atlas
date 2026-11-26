"""
Brief Installeur — fin, IF7 (Réunion n° 3) : la fenêtre native ne parle qu'à l'Atlas de son compte.

Chaque demande de la fenêtre passe par ConnexionAtlas :
1. qui écoute sur 127.0.0.1:8550 ? Il doit appartenir au compte (illisible : pas à moi). Sinon la connexion est
   COUPÉE : ni la clé ni la demande ne partent, et plus rien ne part ensuite (un serveur étranger qui prend le port
   pendant que la fenêtre interroge ne reçoit rien) ;
2. la clé locale est relue (data/cle_locale) et portée dans l'en-tête X-Atlas-Cle ;
3. un refus de clé (401) : la clé est relue ; une lecture est redemandée une fois, une action ne l'est JAMAIS.
"""

from __future__ import annotations

from typing import Callable, Optional

import httpx

from core import cle_locale, proprietaire
from core.proprietaire import Verdict


class ServeurRefuse(RuntimeError):
    """Ce qui écoute sur le port d'Atlas n'appartient pas au compte : la connexion est coupée."""


class ServeurAbsent(RuntimeError):
    """Rien n'écoute sur le port d'Atlas : rien n'est envoyé."""


class CleChangee(RuntimeError):
    """La clé a changé pendant une action : relue, mais l'action n'est pas renvoyée."""


def _verdict_garde(port: int) -> Callable[[], Verdict]:
    g = proprietaire.Garde(port, "Atlas")

    def verifier() -> Verdict:
        try:
            return g.verifier()
        except proprietaire.AutreCompte as e:
            return e.verdict
    return verifier


class ConnexionAtlas:
    def __init__(self, base: str, port: int, *, verifier: Optional[Callable[[], Verdict]] = None,
                 lire_cle: Optional[Callable[[], str]] = None, transport: Optional[httpx.BaseTransport] = None):
        self.base, self.port = base.rstrip("/"), port
        self._verifier = verifier or _verdict_garde(port)
        self._lire_cle = lire_cle or cle_locale.lire
        self._transport = transport
        self.coupee = False
        self.message_coupure = ""

    def _verifier_serveur(self) -> None:
        if self.coupee:
            raise ServeurRefuse(self.message_coupure)
        v = self._verifier()
        if v.refuse:
            self.coupee = True
            self.message_coupure = proprietaire.message_refus("Atlas", v, sortie="relancer")
            raise ServeurRefuse(self.message_coupure)
        if not v.a_moi:
            raise ServeurAbsent("Atlas ne répond pas encore (rien n'écoute sur son port).")

    def _envoyer(self, methode: str, chemin: str, cle: str, timeout: float, **kw) -> httpx.Response:
        with httpx.Client(timeout=timeout, transport=self._transport) as client:
            return client.request(methode, f"{self.base}{chemin}", headers={cle_locale.ENTETE: cle}, **kw)

    def requete(self, methode: str, chemin: str, *, timeout: float = 10.0, rejouable: bool, **kw) -> httpx.Response:
        self._verifier_serveur()
        r = self._envoyer(methode, chemin, self._lire_cle(), timeout, **kw)
        if r.status_code != 401:
            return r
        nouvelle = self._lire_cle()            # la clé a pu changer (Atlas recréé) : relue
        if not rejouable:
            raise CleChangee("Atlas a refusé la demande : la clé locale ne correspondait plus. Je l'ai relue, mais je "
                             "ne renvoie pas une action toute seule : rien n'a été fait. Renvoie ta demande.")
        self._verifier_serveur()
        return self._envoyer(methode, chemin, nouvelle, timeout, **kw)

    def get(self, chemin: str, *, timeout: float = 10.0, **kw) -> httpx.Response:
        return self.requete("GET", chemin, timeout=timeout, rejouable=True, **kw)

    def post(self, chemin: str, *, timeout: float = 60.0, **kw) -> httpx.Response:
        return self.requete("POST", chemin, timeout=timeout, rejouable=False, **kw)
