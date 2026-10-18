"""
Sprint Compétences 1 / CP6 — la musique.

1. Commandes universelles (lecture, pause, suivant, précédent, « qu'est-ce qui passe ? ») : par les
   sessions multimédia de Windows (SMTC, `Windows.Media.Control`), que publient les lecteurs
   (Spotify, les navigateurs pour YouTube Music…). L'état est RELU après la commande.
2. Chercher et jouer : par le service préféré, ouvert par son moyen propre (lien `spotify:`,
   `deezer://`, page Apple Music ou YouTube Music). Atlas dit ce qu'il a fait (« J'ai ouvert la
   recherche… ») : il ne prétend pas jouer ce qu'il ne sait pas.

`MATERIEL` est la seule porte vers Windows ; les tests la remplacent.
"""

from __future__ import annotations

import asyncio
import ctypes
import threading
import time
import urllib.parse
from typing import Callable, Optional

SERVICES = {
    "spotify": {"nom": "Spotify", "protocole": "spotify", "app": "spotify:search:{q}",
                "web": "https://open.spotify.com/search/{q}"},
    "deezer": {"nom": "Deezer", "protocole": "deezer", "app": "deezer://www.deezer.com/search/{q}",
               "web": "https://www.deezer.com/search/{q}"},
    "apple_music": {"nom": "Apple Music", "protocole": "music", "app": "music://music.apple.com/search?term={q}",
                    "web": "https://music.apple.com/search?term={q}"},
    "youtube_music": {"nom": "YouTube Music", "protocole": None, "app": None,
                      "web": "https://music.youtube.com/search?q={q}"},
}
NOMS_SERVICES = {
    "spotify": "spotify", "deezer": "deezer", "apple music": "apple_music", "applemusic": "apple_music",
    "itunes": "apple_music", "apple": "apple_music", "youtube music": "youtube_music", "yt music": "youtube_music",
    "youtube": "youtube_music", "youtubemusic": "youtube_music",
}

# Ce que publie chaque lecteur à Windows (identifiant d'application de la session) → nom lisible.
_APPLIS = (("spotify", "Spotify"), ("deezer", "Deezer"), ("applemusic", "Apple Music"), ("apple", "Apple Music"),
           ("operagx", "Opera GX"), ("opera", "Opera"), ("chrome", "Chrome"), ("msedge", "Edge"),
           ("firefox", "Firefox"), ("brave", "Brave"), ("vlc", "VLC"), ("zunemusic", "Lecteur multimédia"),
           ("zunevideo", "Films et TV"))


def nom_appli(aumid: str) -> str:
    a = (aumid or "").lower().replace(".", "").replace(" ", "")
    for cle, nom in _APPLIS:
        if cle in a:
            return nom
    return aumid or "un lecteur"


def _executer(coro_fabrique: Callable):
    sortie: dict = {}

    def fil():
        try:
            sortie["v"] = asyncio.run(coro_fabrique())
        except BaseException as e:          # noqa: BLE001
            sortie["e"] = e

    t = threading.Thread(target=fil, name="atlas-musique", daemon=True)
    t.start()
    t.join(15)
    if "e" in sortie:
        raise sortie["e"]
    if "v" not in sortie:
        raise TimeoutError("les sessions multimédia de Windows ne répondent pas")
    return sortie["v"]


_STATUTS = {0: "fermé", 1: "ouvert", 2: "changement", 3: "arrêté", 4: "lecture", 5: "pause"}


class Materiel:
    async def _session(self):
        from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Gestionnaire

        g = await Gestionnaire.request_async()
        return g.get_current_session(), g

    async def _decrire(self, s) -> Optional[dict]:
        if s is None:
            return None
        info = s.get_playback_info()
        titre = artiste = None
        try:
            p = await s.try_get_media_properties_async()
            titre, artiste = p.title or None, p.artist or None
        except Exception:
            pass
        return {"appli": nom_appli(s.source_app_user_model_id), "aumid": s.source_app_user_model_id,
                "statut": _STATUTS.get(int(info.playback_status), "inconnu"), "titre": titre, "artiste": artiste}

    def courante(self) -> Optional[dict]:
        async def f():
            s, _ = await self._session()
            return await self._decrire(s)
        return _executer(f)

    def sessions(self) -> list[dict]:
        async def f():
            _, g = await self._session()
            return [await self._decrire(s) for s in g.get_sessions()]
        return _executer(f)

    def commander(self, commande: str) -> bool:
        async def f():
            s, _ = await self._session()
            if s is None:
                return False
            action = {"lecture": s.try_play_async, "pause": s.try_pause_async, "bascule": s.try_toggle_play_pause_async,
                      "suivant": s.try_skip_next_async, "precedent": s.try_skip_previous_async}[commande]
            return bool(await action())
        return _executer(f)

    @staticmethod
    def protocole_installe(protocole: str) -> bool:
        """Windows sait-il QUI ouvre ce lien ? (AssocQueryString : application de bureau ou du Store).
        Une simple clé de registre ne suffit pas : « itmss » y figure sans programme (« choisir une
        application »), constaté sur le PC d'Alexis."""
        from ctypes import wintypes

        def demander(code: int) -> Optional[str]:
            n = wintypes.DWORD(1024)
            buf = ctypes.create_unicode_buffer(1024)
            hr = ctypes.windll.shlwapi.AssocQueryStringW(0x1000, code, protocole, "open", buf, ctypes.byref(n))
            return buf.value if hr == 0 else None

        appid = demander(20)                  # ASSOCSTR_APPID
        return bool(demander(4) and appid and appid.lower() != "undecided")

    @staticmethod
    def ouvrir(adresse: str) -> bool:
        import os

        os.startfile(adresse)
        return True


MATERIEL = Materiel()


def service_connu(texte: str) -> Optional[str]:
    from core.horloge import plat

    t = plat(texte).strip(" .!?")
    for nom in sorted(NOMS_SERVICES, key=len, reverse=True):
        if t == nom or t.endswith(" " + nom) or t.startswith(nom + " ") or f" {nom} " in f" {t} ":
            return NOMS_SERVICES[nom]
    return None


def commander(commande: str, attente_s: float = 0.8) -> dict:
    """{"avant", "envoye", "apres"} — « apres » est RELU après la commande."""
    avant = MATERIEL.courante()
    if avant is None:
        return {"avant": None, "envoye": False, "apres": None}
    envoye = MATERIEL.commander(commande)
    apres = avant
    if envoye:
        time.sleep(attente_s)
        apres = MATERIEL.courante()
        # Le lecteur met parfois un instant à publier le nouveau titre ou le nouvel état.
        for _ in range(5):
            if not apres or _a_change(commande, avant, apres):
                break
            time.sleep(0.3)
            apres = MATERIEL.courante()
    return {"avant": avant, "envoye": envoye, "apres": apres}


def _a_change(commande: str, avant: dict, apres: dict) -> bool:
    if commande == "pause":
        return apres["statut"] == "pause"
    if commande == "lecture":
        return apres["statut"] == "lecture"
    if commande == "bascule":
        return apres["statut"] != avant["statut"]
    return (apres["titre"], apres["artiste"]) != (avant["titre"], avant["artiste"])


def adresse(service: str, recherche: str, web: bool = False) -> str:
    s = SERVICES[service]
    q = urllib.parse.quote(recherche)
    return (s["web"] if web or not s["app"] else s["app"]).format(q=q)


def installe(service: str) -> bool:
    s = SERVICES[service]
    if not s["protocole"]:
        return True                     # YouTube Music : dans le navigateur, toujours
    return MATERIEL.protocole_installe(s["protocole"])


def diagnostic() -> dict:
    try:
        sess = MATERIEL.sessions()
        return {"ok": True, "sessions": [s["appli"] for s in sess],
                "services": {k: installe(k) for k in SERVICES}}
    except Exception as e:
        return {"ok": False, "erreur": f"{type(e).__name__}: {e}"}
