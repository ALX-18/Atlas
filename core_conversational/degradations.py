"""
Sprint Check-up / CK2 — aucune dégradation silencieuse.

Quand un composant manque et qu'Atlas bascule sur un repli (ou perd une fonction), le code
appelle `signaler(clé, cause)`. La bascule est alors :
  - journalisée UNE fois, en avertissement, avec sa cause ;
  - visible dans /api/health (`bascules`) et dans scripts/doctor.py ;
  - dite par Atlas si elle touche ce que vit l'utilisateur (`vecue`) : notification au
    démarrage, et une phrase ajoutée à la première réponse qui suit (écrit et voix).

Le CATALOGUE est le recensement : chaque bascule possible, ce qui la déclenche, ce que
l'utilisateur perd. Un test exige que chaque entrée soit branchée (un appel `signaler`) et
qu'aucune bascule ne soit signalée hors catalogue.

Module sans dépendance (partagé avec le compagnon Mac).
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger("atlas.bascules")

CATALOGUE: dict[str, dict] = {
    "embeddings_onnx": {
        "composant": "Embeddings (ONNX)",
        "declencheur": "modèle ONNX absent ou illisible (models/embeddings/…)",
        "perte": "mémoire sur le moteur de secours sentence-transformers : premier rappel ~15 s au lieu de 1,5 s, "
                 "+700 Mo de mémoire, torch chargé dans Atlas",
        "vecue": True,
        "message": "Ma mémoire tourne sur son moteur de secours, plus lent : le modèle ONNX est introuvable "
                   "(scripts/download_voice_models.py le télécharge).",
    },
    "embeddings_absents": {
        "composant": "Embeddings",
        "declencheur": "ni ONNX ni sentence-transformers ne se chargent",
        "perte": "rappels par mots-clés seulement (mode legacy) : je retrouve beaucoup moins bien ce qui est retenu",
        "vecue": True,
        "message": "Je retrouve mal mes souvenirs : aucun moteur d'embeddings ne se charge.",
    },
    "memoire": {
        "composant": "Mémoire (ChromaDB)",
        "declencheur": "dossier de la mémoire en panne ou tenu par un autre processus",
        "perte": "je ne retiens rien et ne me rappelle de rien",
        "vecue": True,
        "message": "Ma mémoire est indisponible : je ne retiens rien pour le moment.",
    },
    "apprentissage": {
        "composant": "Apprentissage (corrections et méthodes)",
        "declencheur": "la mémoire ne peut pas enregistrer ce qui est appris",
        "perte": "les corrections d'Alexis et les méthodes qui marchent ne sont plus retenues ; tout le reste fonctionne",
        "vecue": True,
        "message": "Je ne peux pas retenir ce que tu m'apprends pour le moment : ma mémoire est indisponible. "
                   "Je fais quand même ce que tu demandes.",
    },
    "memoire_partielle": {
        "composant": "Mémoire (ChromaDB)",
        "declencheur": "une collection reste illisible après 3 ouvertures (défaut de ChromaDB 1.5.1 à l'ouverture)",
        "perte": "les rappels de cette partie de la mémoire échouent pour toute la session",
        "vecue": True,
        "message": "Une partie de ma mémoire est illisible pour le moment : mes rappels seront incomplets. "
                   "Redémarre-moi pour réessayer.",
    },
    "tesseract": {
        "composant": "Tesseract",
        "declencheur": "binaire tesseract introuvable",
        "perte": "chaque clic sur un libellé passe par EasyOCR : environ 20 fois plus lent, une dizaine de secondes "
                 "au premier usage",
        "vecue": True,
        "message": "Tesseract est introuvable : mes clics sur un bouton nommé seront beaucoup plus lents. "
                   "Installe-le (docs/INSTALLATION_ALEXIS.md).",
    },
    "tesseract_fra": {
        "composant": "Tesseract (langue fra)",
        "declencheur": "Tesseract installé sans la langue française",
        "perte": "les libellés accentués sont mal lus : clics manqués ou passés à EasyOCR, plus lent",
        "vecue": True,
        "message": "Tesseract n'a pas la langue française : je lirai mal les boutons accentués. "
                   "Ajoute le pack « fra » (docs/INSTALLATION_ALEXIS.md).",
    },
    "easyocr": {
        "composant": "EasyOCR",
        "declencheur": "le processus OCR ne démarre pas (easyocr ou torch absent ou cassé)",
        "perte": "un libellé que Tesseract ne lit pas ne peut plus être cliqué ; lecture d'écran sans repli",
        "vecue": True,
        "message": "Ma lecture d'écran de secours (EasyOCR) ne démarre pas : certains boutons resteront introuvables.",
    },
    "uia": {
        "composant": "UI Automation (pywinauto)",
        "declencheur": "pywinauto ne s'importe pas",
        "perte": "les clics par l'accessibilité de Windows sont sautés : chaque clic passe par l'OCR, plus lent",
        "vecue": True,
        "message": "Le clic par l'accessibilité de Windows est indisponible : mes clics passeront par la lecture "
                   "de l'écran, plus lente.",
    },
    "pywinauto_fenetres": {
        "composant": "pywinauto (fenêtres)",
        "declencheur": "pywinauto ne s'importe pas",
        "perte": "mise au premier plan par l'API Windows seule (un moyen de moins)",
        "vecue": False,
        "message": "",
    },
    "win32": {
        "composant": "pywin32",
        "declencheur": "pywin32 ne s'importe pas",
        "perte": "fenêtre active et processus inconnus : contexte du PC vide, fenêtres limitées",
        "vecue": True,
        "message": "Je ne vois plus quelle fenêtre est active (pywin32 manquant) : mes réponses sur ton PC seront "
                   "moins justes.",
    },
    "pycaw": {
        "composant": "pycaw",
        "declencheur": "pycaw ne s'importe pas",
        "perte": "les applications qui jouent du son ne sont plus détectées dans le contexte",
        "vecue": False,
        "message": "",
    },
    "stt_gpu": {
        "composant": "Transcription (faster-whisper)",
        "declencheur": "la transcription ne se charge pas sur le GPU (cuBLAS/cuDNN absents ou en échec)",
        "perte": "transcription sur processeur : environ 5 s par phrase au lieu de 0,1 s",
        "vecue": True,
        "message": "Ma transcription tourne sur le processeur : je mettrai quelques secondes de plus à te comprendre.",
    },
    "stt_absent": {
        "composant": "Transcription (faster-whisper)",
        "declencheur": "le paquet faster-whisper est absent ou ne s'importe pas",
        "perte": "chaque phrase dite échoue : on ne peut plus parler à Atlas, seulement lui écrire",
        "vecue": True,
        "message": "Ma transcription (faster-whisper) est absente : je ne comprends pas ce que tu me dis "
                   "à voix haute, seulement ce que tu écris. pip install -r requirements.txt",
    },
    "tts_piper": {
        "composant": "Synthèse (Piper)",
        "declencheur": "la voix Piper ne parle pas (modèle absent ou erreur)",
        "perte": "voix de Windows (SAPI) à la place de la voix d'Atlas",
        "vecue": True,
        "message": "Ma voix habituelle (Piper) est indisponible : je parle avec la voix de Windows.",
    },
    "tts_muet": {
        "composant": "Synthèse vocale",
        "declencheur": "ni Piper ni la voix de Windows ne parlent",
        "perte": "Atlas reste muet : les réponses vocales ne sont qu'écrites",
        "vecue": True,
        "message": "Je ne peux plus parler à voix haute : aucune synthèse vocale ne fonctionne.",
    },
    "voix": {
        "composant": "Moteur vocal",
        "declencheur": "le moteur vocal ne démarre pas (micro, mot d'éveil)",
        "perte": "on ne peut plus parler à Atlas",
        "vecue": True,
        "message": "Mon écoute ne démarre pas : tu ne peux pas me parler pour le moment, seulement m'écrire.",
    },
    "browser_bridge": {
        "composant": "Pont navigateur",
        "declencheur": "le serveur WebSocket du pont ne démarre pas (port occupé…)",
        "perte": "l'extension du navigateur ne peut plus se connecter : pas de pilotage d'onglet",
        "vecue": True,
        "message": "Le pont vers ton navigateur ne démarre pas : je ne peux pas piloter tes onglets.",
    },
    "file_indexer": {
        "composant": "Index des fichiers",
        "declencheur": "l'indexation passive ne démarre pas",
        "perte": "la recherche de fichiers et l'ouverture par nom de fichier ne voient plus les nouveautés",
        "vecue": True,
        "message": "Mon index de fichiers ne démarre pas : je risque de ne pas trouver tes fichiers récents.",
    },
    "systray": {
        "composant": "Icône de la zone de notification (pystray)",
        "declencheur": "pystray ou Pillow ne s'importe pas",
        "perte": "pas d'icône : l'état d'écoute n'est plus visible, ni le menu (voix, quitter)",
        "vecue": True,
        "message": "Mon icône près de l'horloge ne s'affiche pas : tu ne vois pas si je t'écoute.",
    },
    "notifications": {
        "composant": "Notifications Windows (plyer)",
        "declencheur": "plyer ne s'importe pas ou Windows refuse la notification",
        "perte": "les avertissements à l'écran (attente d'EasyOCR, confirmation demandée à la voix, "
                 "automatisations, ce qui manque au démarrage) ne s'affichent plus",
        "vecue": True,
        "message": "Je ne peux pas afficher de notifications Windows : mes avertissements n'apparaîtront "
                   "que dans mes réponses.",
    },
    "instantane_processus": {
        "composant": "Instantané des processus (NtQuerySystemInformation)",
        "declencheur": "l'appel système unique échoue",
        "perte": "processus relevés un par un par psutil : échantillonnage du contexte nettement plus lent",
        "vecue": False,
        "message": "",
    },
    "prompt_capacites": {
        "composant": "Consigne du modèle",
        "declencheur": "la liste des capacités ne peut pas être construite pour la consigne",
        "perte": "le modèle ne connaît pas la liste des capacités (la réponse fixe « tu peux faire quoi ? » reste juste)",
        "vecue": False,
        "message": "",
    },
}

_LOCK = threading.Lock()
_ACTIVES: dict[str, dict] = {}


def signaler(cle: str, cause: str) -> None:
    """Une bascule a eu lieu. Journalisée une seule fois ; l'état reste consultable."""
    entree = CATALOGUE[cle]           # KeyError : une bascule hors catalogue est une faute
    with _LOCK:
        if cle in _ACTIVES:
            return
        _ACTIVES[cle] = {"cle": cle, "cause": str(cause)[:300], "depuis": time.strftime("%Y-%m-%d %H:%M:%S"),
                         "dite": False, "annoncee": False}
    logger.warning("[BASCULE] %s — %s (cause : %s)", entree["composant"], entree["perte"], cause)


def actives() -> list[dict]:
    """Les bascules en cours, avec ce que l'utilisateur perd (pour /api/health et doctor)."""
    with _LOCK:
        return [{**{k: CATALOGUE[c][k] for k in ("composant", "perte", "vecue")}, "cle": c,
                 "cause": a["cause"], "depuis": a["depuis"]} for c, a in _ACTIVES.items()]


def a_dire() -> list[str]:
    """Phrases à ajouter à la prochaine réponse : chaque bascule vécue, une seule fois."""
    out = []
    with _LOCK:
        for c, a in _ACTIVES.items():
            if CATALOGUE[c]["vecue"] and not a["dite"]:
                a["dite"] = True
                out.append(CATALOGUE[c]["message"])
    return out


def a_annoncer() -> list[str]:
    """Phrases pour la notification de démarrage (indépendant de a_dire : on le redit en réponse)."""
    out = []
    with _LOCK:
        for c, a in _ACTIVES.items():
            if CATALOGUE[c]["vecue"] and not a["annoncee"]:
                a["annoncee"] = True
                out.append(CATALOGUE[c]["message"])
    return out


def avec_avertissements(message: str | None) -> str | None:
    """Ajoute à une réponse les bascules vécues pas encore dites."""
    notes = a_dire()
    if not notes:
        return message
    texte = "\n".join(f"ℹ️ {n}" for n in notes)
    return f"{message}\n\n{texte}" if message else texte


def reinitialiser() -> None:
    """Pour les tests."""
    with _LOCK:
        _ACTIVES.clear()
