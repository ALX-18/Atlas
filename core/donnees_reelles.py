"""
Sprint Banc de modèles / BM0 — UN garde pour les données réelles d'Alexis.

Trois fois, un script d'essai a écrit dans `data/` (Index : habits.db ; Compétences 1 : le journal
et un apprentissage.db vide, par mesure_routes.py et gb1_mesure.py). Désormais :

- seul Atlas lancé normalement (`main.py`) peut écrire dans les données réelles : la mémoire, le
  journal des actions, habits.db, apprentissage.db, rappels.db, l'index des fichiers. `main.py`
  appelle `autoriser_atlas()`, qui pose ATLAS_DONNEES=reelles — et refuse si une redirection
  ATLAS_* est posée : un Atlas d'ESSAI (rejeu) n'écrit jamais dans les vraies données, même s'il
  a oublié une redirection ;
- tout autre processus est refusé s'il vise un chemin réel (sous `data/`), même sans redirection :
  `DonneesReellesInterdites`, avec un message qui dit quoi faire ;
- les redirections ATLAS_* restent la façon normale de travailler sur des copies ;
- les outils de MAINTENANCE (scripts/backup_memory.py, memory_cleanup.py, memory_inventory.py,
  reencode_memory.py, retirer_collections_vides.py, nettoyer_journal.py) ouvrent leurs propres
  accès, ne passent pas par ce garde, et exigent l'accord explicite (--oui, --yes) pour écrire.
"""

from __future__ import annotations

import logging
import os
import pathlib

logger = logging.getLogger("atlas.donnees_reelles")

DOSSIER = pathlib.Path(__file__).resolve().parent.parent / "data"
VARIABLE = "ATLAS_DONNEES"
REDIRECTIONS = ("ATLAS_CHROMA_PATH", "ATLAS_APPRENTISSAGE_DB", "ATLAS_ACTIONS_LOG", "ATLAS_HABITS_DB",
                "ATLAS_RAPPELS_DB", "ATLAS_FILE_INDEX_DB")
_dits: set[str] = set()

# Compétences 2 / CM0 : ce qui touche `data/` SANS passer par ce garde, et pourquoi. Un test recense tous les
# fichiers qui écrivent près de `data/` : chacun passe par le garde, ou figure ici avec sa raison.
ECRIVAINS_HORS_GARDE = {
    "core/donnees_reelles.py": "le garde lui-même",
    "core_conversational/memory_core.py": "ouvert par core/memory_manager.py, qui garde la mémoire avant de l'ouvrir",
    "scripts/backup_memory.py": "maintenance : écrit hors de data/ (sauvegardes), restaure seulement avec --oui",
    "scripts/nettoyer_journal.py": "maintenance : exige --oui",
    "scripts/migrer_memoire.py": "maintenance : part d'une sauvegarde vérifiée, refuse si data/chromadb existe",
    "scripts/repro_chroma.py": "mesure : refuse le vrai data/chromadb",
    "scripts/garde_fou_rappels.py": "mesure : travaille sur une copie dans un dossier jetable",
    "scripts/prototype_sans_docker.py": "mesure : travaille sur une copie dans un dossier jetable",
    "scripts/mesure_ressources.py": "mesure : lit data/voices, travaille sur une copie de la mémoire",
    "scripts/checkup_dynamique.py": "mesure : Atlas sur une copie de la mémoire (redirections ATLAS_*)",
    "scripts/download_voice_models.py": "installation : télécharge les voix dans data/voices, à la demande",
}


class DonneesReellesInterdites(PermissionError):
    """Un processus qui n'est pas Atlas vise les données réelles d'Alexis."""


def autoriser_atlas() -> bool:
    """Appelé par main.py seulement. Faux (et rien n'est autorisé) pour un Atlas d'essai."""
    redirections = [v for v in REDIRECTIONS if os.environ.get(v)]
    if redirections:
        os.environ.pop(VARIABLE, None)
        logger.info("Atlas d'essai (%s) : données réelles interdites.", ", ".join(redirections))
        return False
    os.environ[VARIABLE] = "reelles"
    return True


def autorise() -> bool:
    return os.environ.get(VARIABLE) == "reelles"


def est_reel(chemin) -> bool:
    try:
        p = pathlib.Path(chemin).resolve()
        racine = pathlib.Path(DOSSIER).resolve()
    except Exception:
        return False
    return p == racine or racine in p.parents


def interdit(chemin) -> bool:
    """Vrai si ce processus n'a pas le droit d'écrire à ce chemin."""
    return est_reel(chemin) and not autorise()


def verifier_ecriture(chemin, quoi: str) -> None:
    """Lève DonneesReellesInterdites si ce processus vise, pour écrire, un chemin réel."""
    if not interdit(chemin):
        return
    message = (f"Refus : {quoi} — écriture dans les données réelles d'Alexis ({chemin}) par un processus qui "
               f"n'est pas Atlas. Travailler sur une copie : {', '.join(REDIRECTIONS)}.")
    if str(chemin) not in _dits:
        _dits.add(str(chemin))
        logger.error("[DONNEES REELLES] %s", message)
    raise DonneesReellesInterdites(message)


def lecture_seule(chemin):
    """Une connexion SQLite en LECTURE SEULE sur un fichier réel existant (ni création, ni verrou),
    pour un processus qui n'a pas le droit d'écrire. Le fichier absent : DonneesReellesInterdites."""
    import sqlite3

    p = pathlib.Path(chemin)
    if not p.exists():
        verifier_ecriture(p, f"création de {p.name}")
    return sqlite3.connect(f"file:{p.resolve().as_posix()}?mode=ro", uri=True, timeout=5.0, check_same_thread=False)
