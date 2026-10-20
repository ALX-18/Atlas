"""
Banc de modèles / BM0 — les bancs (GB1, O, banc de modèles) travaillent sur des COPIES.

À appeler AVANT tout `import core…` : les modules lisent leurs chemins à l'import. La mémoire est
copiée (rappels réels, comme avant, mais jamais la vraie base ouverte) ; journal, apprentissage,
habitudes et rappels vont dans le même dossier jetable. L'index des fichiers n'est pas redirigé :
hors d'Atlas, le garde l'ouvre en lecture seule.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import tempfile

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"


def donnees_jetables(copier_memoire: bool = True, prefixe: str = "atlas_banc_") -> pathlib.Path:
    dossier = pathlib.Path(tempfile.mkdtemp(prefix=prefixe))
    if copier_memoire and (DATA / "chromadb").exists():
        shutil.copytree(DATA / "chromadb", dossier / "chromadb", ignore=shutil.ignore_patterns("*.lock"))
    if (DATA / "habits.db").exists():
        shutil.copy2(DATA / "habits.db", dossier / "habits.db")
    os.environ.update({
        "ATLAS_CHROMA_PATH": str(dossier / "chromadb"),
        "ATLAS_ACTIONS_LOG": str(dossier / "atlas_actions.jsonl"),
        "ATLAS_APPRENTISSAGE_DB": str(dossier / "apprentissage.db"),
        "ATLAS_HABITS_DB": str(dossier / "habits.db"),
        "ATLAS_RAPPELS_DB": str(dossier / "rappels.db"),
    })
    return dossier
