"""
Sprint Compétences 1 / CP3 — le son, par pycaw (déjà présent).

Chaque fonction AGIT puis RELIT : ce qu'elle rend est l'état lu après coup, jamais la valeur
demandée. Les appels COM se font dans un fil à part, initialisé et libéré à chaque fois : le
serveur d'Atlas appelle depuis des fils qui n'ont pas forcément initialisé COM.

`Materiel` est la seule porte vers Windows ; les tests la remplacent (`MATERIEL`).
"""

from __future__ import annotations

import ctypes
import threading
from typing import Callable, Optional


_travaux: "queue.Queue" = None          # type: ignore[assignment]
_verrou_fil = threading.Lock()


def _fil_com() -> None:
    """LE fil COM du son : initialisé une fois, jamais fermé.

    Mesuré au rejeu réel du 18/10 : avec un fil COM par appel (CoInitialize … CoUninitialize), des
    objets pycaw survivaient au fil ; le ramasse-miettes les libérait plus tard, COM déjà fermé →
    violation d'accès, processus tué sans trace. Ici les objets sont créés, utilisés et libérés
    (gc.collect) dans ce fil, dont l'appartement COM reste ouvert."""
    import gc

    import comtypes

    try:
        comtypes.CoInitialize()
    except OSError:
        pass                                    # déjà initialisé dans ce fil (selon l'ordre des imports)
    while True:
        fonction, sortie, fini = _travaux.get()
        try:
            sortie["v"] = fonction()
        except BaseException as e:            # noqa: BLE001 — rendue à l'appelant
            sortie["e"] = e.with_traceback(None)          # la trace retiendrait des objets COM
        finally:
            fonction = None
            gc.collect()
            fini.set()


def _en_com(fonction: Callable):
    """Exécute `fonction` dans le fil COM du son ; relance son exception."""
    import queue

    global _travaux
    with _verrou_fil:
        if _travaux is None:
            _travaux = queue.Queue()
            threading.Thread(target=_fil_com, name="atlas-son-com", daemon=True).start()
    sortie: dict = {}
    fini = threading.Event()
    _travaux.put((fonction, sortie, fini))
    if not fini.wait(10):
        raise TimeoutError("le service audio de Windows ne répond pas")
    if "e" in sortie:
        raise sortie["e"]
    return sortie["v"]


class Materiel:
    """Le vrai son de Windows (périphérique de sortie par défaut, sessions des programmes)."""

    @staticmethod
    def _volume():
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

        dev = AudioUtilities.GetSpeakers()
        iface = dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        # QueryInterface, PAS ctypes.cast (exemple de pycaw) : cast crée un second pointeur sans
        # AddRef ; les deux sont libérés → double Release → violation d'accès au ramasse-miettes.
        return iface.QueryInterface(IAudioEndpointVolume)

    def general(self) -> dict:
        def f():
            v = self._volume()
            return {"niveau": round(v.GetMasterVolumeLevelScalar() * 100), "muet": bool(v.GetMute())}
        return _en_com(f)

    def regler_general(self, niveau: Optional[int] = None, muet: Optional[bool] = None) -> None:
        def f():
            v = self._volume()
            if niveau is not None:
                v.SetMasterVolumeLevelScalar(max(0, min(100, niveau)) / 100.0, None)
            if muet is not None:
                v.SetMute(1 if muet else 0, None)
        _en_com(f)

    @staticmethod
    def _sessions():
        from pycaw.pycaw import AudioUtilities

        return [s for s in AudioUtilities.GetAllSessions() if s.Process]

    def programmes(self) -> list[dict]:
        def f():
            out = []
            for s in self._sessions():
                v = s.SimpleAudioVolume
                out.append({"processus": s.Process.name(), "pid": s.Process.pid,
                            "niveau": round(v.GetMasterVolume() * 100), "muet": bool(v.GetMute())})
            return out
        return _en_com(f)

    def regler_programme(self, pid: int, niveau: Optional[int] = None, muet: Optional[bool] = None) -> None:
        def f():
            for s in self._sessions():
                if s.Process.pid == pid:
                    v = s.SimpleAudioVolume
                    if niveau is not None:
                        v.SetMasterVolume(max(0, min(100, niveau)) / 100.0, None)
                    if muet is not None:
                        v.SetMute(1 if muet else 0, None)
        _en_com(f)


MATERIEL = Materiel()


def disponible() -> tuple[bool, str]:
    try:
        MATERIEL.general()
        return True, "pycaw : volume général lu"
    except Exception as e:
        return False, f"pycaw : {type(e).__name__}: {e}"


# --------------------------------------------------------------------------- #
#  Agir, puis relire
# --------------------------------------------------------------------------- #

def etat() -> dict:
    return MATERIEL.general()


def regler(niveau: Optional[int] = None, delta: Optional[int] = None, muet: Optional[bool] = None) -> dict:
    """Règle le volume général et rend {"avant", "apres"} — « apres » est RELU."""
    avant = MATERIEL.general()
    cible = None
    if niveau is not None:
        cible = niveau
    elif delta is not None:
        cible = avant["niveau"] + delta
    # Monter ou régler le volume rétablit le son coupé (comme les touches du clavier).
    if muet is None and cible is not None and avant["muet"] and (delta or 0) >= 0:
        muet = False
    MATERIEL.regler_general(None if cible is None else max(0, min(100, cible)), muet)
    return {"avant": avant, "apres": MATERIEL.general()}


def _nom(processus: str) -> str:
    return processus[:-4] if processus.lower().endswith(".exe") else processus


def trouver_programme(nom: str) -> list[dict]:
    """Les sessions audio dont le processus correspond au nom dit (« spotify » → Spotify.exe)."""
    from core.horloge import plat

    voulu = plat(nom).replace(" ", "")
    progs = MATERIEL.programmes()
    exacts = [p for p in progs if plat(_nom(p["processus"])).replace(" ", "") == voulu]
    if exacts:
        return exacts
    return [p for p in progs if voulu and voulu in plat(p["processus"]).replace(" ", "")]


def regler_programme(nom: str, niveau: Optional[int] = None, delta: Optional[int] = None,
                     muet: Optional[bool] = None) -> dict:
    """{"trouves": [...], "avant", "apres"} — toutes les sessions du programme, relues."""
    trouves = trouver_programme(nom)
    if not trouves:
        return {"trouves": []}
    avant = trouves[0]
    cible = niveau if niveau is not None else (avant["niveau"] + delta if delta is not None else None)
    if muet is None and cible is not None and avant["muet"] and (delta or 0) >= 0:
        muet = False
    for p in trouves:
        MATERIEL.regler_programme(p["pid"], None if cible is None else max(0, min(100, cible)), muet)
    relus = [p for p in MATERIEL.programmes() if p["pid"] in {t["pid"] for t in trouves}]
    return {"trouves": trouves, "avant": avant, "apres": relus[0] if relus else None, "nom": _nom(avant["processus"])}
