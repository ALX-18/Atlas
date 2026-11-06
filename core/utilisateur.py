"""
Sprint Installeur — la personne qu'Atlas aide : son prénom, demandé au premier lancement.

Chez un proche, Atlas ne doit pas l'appeler « Alexis » (le créateur d'Atlas, qui reste dans son identité).
Le prénom est dans settings.json (`utilisateur.prenom`) ; vide, Atlas parle de « la personne » et ne donne
aucun prénom. Il sert dans la consigne du modèle, dans celles du lecteur et du rédacteur de mails, et dans
celle des documents.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
REGLAGES = ROOT / "config" / "settings.json"
_cache: dict = {}


def prenom() -> Optional[str]:
    """Le prénom de la personne, ou None (relu si settings.json a changé)."""
    try:
        mtime = REGLAGES.stat().st_mtime
        if _cache.get("mtime") != mtime:
            utilisateur = json.loads(REGLAGES.read_text(encoding="utf-8")).get("utilisateur") or {}
            _cache.update(mtime=mtime, prenom=nettoyer(utilisateur.get("prenom", "")))
        return _cache.get("prenom")
    except Exception:
        return None


def nettoyer(texte: str) -> Optional[str]:
    """Un prénom : lettres, espaces, tirets et apostrophes, 40 caractères au plus ; sinon None."""
    t = re.sub(r"\s+", " ", (texte or "")).strip()
    if not t or len(t) > 40 or not re.fullmatch(r"[^\W\d_]+(?:[ '’-][^\W\d_]+)*", t):
        return None
    return t


def nom_ou(defaut: str = "la personne") -> str:
    return prenom() or defaut


def de_nom(defaut: str = "la personne") -> str:
    """« d'Alexis », « de Marie », « de la personne » (l'élision devant une voyelle ou un h)."""
    n = nom_ou(defaut)
    return f"d'{n}" if n[:1].lower() in "aeiouyhàâéèêëîïôöûü" else f"de {n}"


def enregistrer(texte: str, chemin: pathlib.Path = REGLAGES) -> Optional[str]:
    """Écrit le prénom dans settings.json (premier lancement). Rend le prénom retenu, ou None s'il est refusé."""
    p = nettoyer(texte)
    if p is None:
        return None
    reglages = json.loads(chemin.read_text(encoding="utf-8"))
    reglages.setdefault("utilisateur", {})["prenom"] = p
    chemin.write_text(json.dumps(reglages, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    _cache.clear()
    return p
