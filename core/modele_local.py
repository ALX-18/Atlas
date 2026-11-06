"""
Sprint Installeur / IN4 — le modèle de langue local : épinglé, et rendu au jeu.

- Épinglage : au démarrage, le modèle configuré doit avoir l'empreinte de `config/modeles.json`
  (celle qu'Ollama donne dans /api/tags). Sinon : bascule « modele_non_epingle », annoncée avec
  l'empreinte attendue et celle trouvée. Un modèle hors de la liste n'est pas vérifié.
- Mode jeu : quand un jeu occupe tout l'écran, Atlas décharge son modèle (keep_alive 0) et rend la
  mémoire de la carte graphique. À la demande suivante qui en a besoin, il le dit (« Je recharge mon
  modèle, quelques secondes ») et Ollama le recharge. Les navigateurs et les lecteurs vidéo en plein
  écran ne comptent pas comme un jeu (une vidéo ne demande pas la carte graphique).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import threading
import time
from typing import Callable, Optional

import httpx

logger = logging.getLogger("atlas.modele_local")

ROOT = pathlib.Path(__file__).resolve().parent.parent
FICHIER_MODELES = ROOT / "config" / "modeles.json"

ANNONCE_RECHARGE = "Je recharge mon modèle, quelques secondes."
INTERVALLE_S = 5.0          # un coup d'œil à la fenêtre au premier plan toutes les 5 s
TOURS_AVANT_DECHARGE = 2    # le jeu doit être au premier plan deux fois de suite (10 s)
REPOS_AVANT_DECHARGE_S = 60.0   # pas de déchargement si le modèle a servi il y a moins d'une minute

PAS_UN_JEU = frozenset({
    "chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe", "vivaldi.exe", "iexplore.exe",
    "vlc.exe", "mpc-hc.exe", "mpc-hc64.exe", "mpc-be64.exe", "wmplayer.exe", "potplayer.exe", "potplayermini64.exe",
    "video.ui.exe", "microsoft.media.player.exe", "netflix.exe", "applicationframehost.exe", "powerpnt.exe",
    "python.exe", "pythonw.exe",
})


def modeles_epingles() -> dict:
    try:
        return json.loads(FICHIER_MODELES.read_text(encoding="utf-8")).get("modeles", {})
    except Exception as e:
        logger.warning("[MODÈLE] %s illisible : %s", FICHIER_MODELES, e)
        return {}


def ollama_reference() -> Optional[str]:
    try:
        return json.loads(FICHIER_MODELES.read_text(encoding="utf-8")).get("ollama_reference")
    except Exception:
        return None


# --------------------------------------------------------------------------- #
#  Épinglage
# --------------------------------------------------------------------------- #

def verifier_epinglage(modele: str, tags: Optional[list[dict]] = None) -> dict:
    """{"etat": "conforme" | "different" | "absent" | "non_epingle" | "injoignable", "attendue", "trouvee"}."""
    attendu = (modeles_epingles().get(modele) or {}).get("digest")
    if not attendu:
        return {"etat": "non_epingle", "attendue": None, "trouvee": None}
    if tags is None:
        from core.ollama_client import BASE_URL

        try:
            tags = httpx.get(f"{BASE_URL}/api/tags", timeout=5.0).json().get("models", [])
        except Exception:
            return {"etat": "injoignable", "attendue": attendu, "trouvee": None}
    trouve = next((m.get("digest") for m in tags if m.get("name") == modele or m.get("model") == modele), None)
    if trouve is None:
        return {"etat": "absent", "attendue": attendu, "trouvee": None}
    return {"etat": "conforme" if trouve == attendu else "different", "attendue": attendu, "trouvee": trouve}


def signaler_epinglage(modele: str, tags: Optional[list[dict]] = None) -> dict:
    from core_conversational import degradations

    r = verifier_epinglage(modele, tags)
    if r["etat"] == "different":
        degradations.signaler("modele_non_epingle", f"{modele} : empreinte attendue {r['attendue'][:12]}…, "
                                                    f"trouvée {r['trouvee'][:12]}…")
        logger.warning("[MODÈLE] %s n'a pas l'empreinte attendue (attendue %s, trouvée %s).", modele,
                       r["attendue"], r["trouvee"])
    elif r["etat"] == "conforme":
        degradations.lever("modele_non_epingle")
    return r


# --------------------------------------------------------------------------- #
#  Mode jeu
# --------------------------------------------------------------------------- #

def _processus_au_premier_plan() -> Optional[str]:
    try:
        import psutil
        import win32gui
        import win32process

        _, pid = win32process.GetWindowThreadProcessId(win32gui.GetForegroundWindow())
        return psutil.Process(pid).name().lower()
    except Exception:
        return None


def jeu_au_premier_plan() -> bool:
    from core.file_indexer import jeu_en_plein_ecran

    if not jeu_en_plein_ecran():
        return False
    return (_processus_au_premier_plan() or "") not in PAS_UN_JEU


def _modele_charge(modele: str) -> bool:
    from core.ollama_client import BASE_URL

    try:
        charges = httpx.get(f"{BASE_URL}/api/ps", timeout=3.0).json().get("models", [])
    except Exception:
        return False
    return any(m.get("name") == modele or m.get("model") == modele for m in charges)


def _decharger(modele: str) -> bool:
    from core.ollama_client import BASE_URL

    try:
        httpx.post(f"{BASE_URL}/api/generate", json={"model": modele, "keep_alive": 0}, timeout=15.0)
        return True
    except Exception as e:
        logger.warning("[MODE JEU] Déchargement impossible : %s", e)
        return False


class ModeJeu:
    """Un fil discret : il regarde la fenêtre au premier plan, décharge le modèle pendant un jeu."""

    def __init__(self, modele: str, jeu: Callable[[], bool] = jeu_au_premier_plan,
                 charge: Callable[[str], bool] = _modele_charge, decharger: Callable[[str], bool] = _decharger,
                 horloge: Callable[[], float] = time.monotonic):
        self.modele = modele
        self._jeu, self._charge, self._decharger, self._horloge = jeu, charge, decharger, horloge
        self._tours = 0
        self.decharge = False
        self.dernier_usage = -1e9
        self._arret = threading.Event()
        self._fil: Optional[threading.Thread] = None
        self._verrou = threading.Lock()

    def tour(self) -> None:
        """Un coup d'œil (appelé toutes les INTERVALLE_S secondes par le fil, ou par les tests)."""
        if not self._jeu():
            self._tours = 0
            return
        self._tours += 1
        if self._tours < TOURS_AVANT_DECHARGE or self.decharge:
            return
        if self._horloge() - self.dernier_usage < REPOS_AVANT_DECHARGE_S or not self._charge(self.modele):
            return
        if self._decharger(self.modele):
            with self._verrou:
                self.decharge = True
            logger.info("[MODE JEU] Jeu en plein écran : modèle %s déchargé, mémoire de la carte rendue.", self.modele)

    def avant_appel(self) -> Optional[str]:
        """Chaque appel au modèle passe ici : l'annonce du rechargement, une seule fois."""
        with self._verrou:
            self.dernier_usage = self._horloge()
            if not self.decharge:
                return None
            self.decharge = False
        return ANNONCE_RECHARGE

    def demarrer(self) -> None:
        if self._fil or os.name != "nt":
            return

        def boucle():
            while not self._arret.wait(INTERVALLE_S):
                try:
                    self.tour()
                except Exception as e:
                    logger.debug("[MODE JEU] %s", e)

        self._fil = threading.Thread(target=boucle, name="atlas-mode-jeu", daemon=True)
        self._fil.start()

    def arreter(self) -> None:
        self._arret.set()


_instance: Optional[ModeJeu] = None


def mode_jeu() -> Optional[ModeJeu]:
    return _instance


def demarrer_mode_jeu(modele: str) -> Optional[ModeJeu]:
    global _instance
    if _instance is None:
        _instance = ModeJeu(modele)
        _instance.demarrer()
    return _instance


def avant_appel_modele(origine: Optional[str] = None) -> None:
    """Appelé avant chaque requête au modèle (core.ollama_client.champs_modele) : si le modèle a été rendu au jeu,
    Atlas le dit, à l'écran et à la voix, pendant qu'Ollama le recharge."""
    m = _instance
    if m is None:
        return
    annonce = m.avant_appel()
    if annonce:
        try:
            from core import annonces

            annonces.publier(annonce, origine, parole=annonce)
        except Exception as e:
            logger.debug("[MODE JEU] annonce : %s", e)
