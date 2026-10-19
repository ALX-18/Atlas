"""
Sprint Apprentissage 2 / AQ2 — ce qu'Atlas apprend est dans SQLite (`data/apprentissage.db`).

Décision d'Alexis (15/10) : ce qui est appris se lit par identifiant exact, jamais par ressemblance.
Une base vectorielle n'apporte rien, et les collections jeunes de ChromaDB sont justement celles
que son défaut de lecture touche (rapport Apprentissage 1, AP0).

- une table `appris` : un enregistrement explicite par ligne (id, type, libellé lisible, détails
  JSON, dates) — corrections, méthodes, refus, habitudes qu'Alexis ne veut plus se voir proposer ;
- une table `propositions` : quand une habitude a été proposée (limites de fréquence, AQ4) ;
- une table `etat` : clé → valeur (interrupteur global des suggestions).

Écritures atomiques : une transaction par écriture (journal SQLite par défaut, synchronous=FULL).
Un seul processus : le verrou du système d'exploitation de la mémoire (`acquire_memory_lock`) est
pris sur ce fichier, comme sur `data/chromadb` ; un second Atlas, ou un script de sauvegarde,
est refusé tant que le premier tourne.

ATLAS_APPRENTISSAGE_DB : un autre fichier (les rejeux réels travaillent sur une copie).
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sqlite3
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("atlas.apprentissage")

DEFAULT_DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "apprentissage.db"
DB_PATH: pathlib.Path = pathlib.Path(os.environ.get("ATLAS_APPRENTISSAGE_DB") or DEFAULT_DB_PATH)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS appris (
    id      TEXT PRIMARY KEY,
    type    TEXT NOT NULL,
    libelle TEXT NOT NULL,
    meta    TEXT NOT NULL,
    cree    TEXT NOT NULL,
    maj     TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS propositions (
    cle   TEXT NOT NULL,
    quand REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS propositions_quand ON propositions(quand);
CREATE TABLE IF NOT EXISTS etat (
    cle    TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
"""

_verrou = threading.Lock()
_pret: set[str] = set()


class Indisponible(RuntimeError):
    """Le fichier ne peut pas être ouvert (verrouillé par un autre processus, disque…)."""


def _connexion(ecriture: bool = True) -> sqlite3.Connection:
    chemin = pathlib.Path(DB_PATH)
    cle = str(chemin.resolve())
    # BM0 : un processus qui n'est pas Atlas ne crée, ne verrouille ni n'écrit le vrai apprentissage.db ;
    # il peut le lire s'il existe. Refus rendu comme Indisponible : les appelants savent déjà s'en passer.
    from core import donnees_reelles

    if donnees_reelles.interdit(chemin):
        try:
            if ecriture:
                donnees_reelles.verifier_ecriture(chemin, "écriture dans apprentissage.db")
            return donnees_reelles.lecture_seule(chemin)
        except donnees_reelles.DonneesReellesInterdites as e:
            raise Indisponible(str(e)) from e
    if cle not in _pret:
        from core.memory_manager import acquire_memory_lock

        chemin.parent.mkdir(parents=True, exist_ok=True)
        ok, pourquoi = acquire_memory_lock(cle)
        if not ok:
            raise Indisponible(pourquoi.replace("la mémoire", "l'apprentissage"))
    try:
        conn = sqlite3.connect(cle, timeout=5.0)
        conn.execute("PRAGMA synchronous=FULL")
        if cle not in _pret:
            with conn:
                conn.executescript(_SCHEMA)
            _pret.add(cle)
        return conn
    except sqlite3.Error as e:
        raise Indisponible(str(e)) from e


def ecrire(doc_id: str, type_: str, libelle: str, meta: dict) -> None:
    """Écrit ou remplace un enregistrement (une transaction)."""
    maintenant = datetime.now().isoformat(timespec="seconds")
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                ancien = conn.execute("SELECT cree FROM appris WHERE id = ?", (doc_id,)).fetchone()
                conn.execute("INSERT OR REPLACE INTO appris (id, type, libelle, meta, cree, maj) VALUES (?,?,?,?,?,?)",
                             (doc_id, type_, libelle, json.dumps(meta, ensure_ascii=False),
                              ancien[0] if ancien else maintenant, maintenant))
        finally:
            conn.close()


def lire(ids: Optional[list[str]] = None) -> list[dict]:
    """Les enregistrements demandés (tous si ids est None) : {id, type, libelle, meta, depuis}."""
    with _verrou:
        conn = _connexion(ecriture=False)
        try:
            if ids is None:
                rows = conn.execute("SELECT id, type, libelle, meta, cree FROM appris ORDER BY cree, id").fetchall()
            else:
                if not ids:
                    return []
                marques = ",".join("?" * len(ids))
                rows = conn.execute(f"SELECT id, type, libelle, meta, cree FROM appris WHERE id IN ({marques})",
                                    list(ids)).fetchall()
        finally:
            conn.close()
    return [{"id": i, "type": t, "libelle": l, "meta": json.loads(m), "depuis": c} for i, t, l, m, c in rows]


def effacer(ids: list[str]) -> int:
    if not ids:
        return 0
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                marques = ",".join("?" * len(ids))
                return conn.execute(f"DELETE FROM appris WHERE id IN ({marques})", list(ids)).rowcount
        finally:
            conn.close()


def noter_proposition(cle: str, quand: Optional[float] = None) -> None:
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                conn.execute("INSERT INTO propositions (cle, quand) VALUES (?, ?)", (cle, quand or time.time()))
        finally:
            conn.close()


def propositions_depuis(depuis: float, cle: Optional[str] = None) -> int:
    with _verrou:
        conn = _connexion(ecriture=False)
        try:
            if cle is None:
                return conn.execute("SELECT COUNT(*) FROM propositions WHERE quand >= ?", (depuis,)).fetchone()[0]
            return conn.execute("SELECT COUNT(*) FROM propositions WHERE quand >= ? AND cle = ?",
                                (depuis, cle)).fetchone()[0]
        finally:
            conn.close()


def etat(cle: str, defaut: Optional[str] = None) -> Optional[str]:
    with _verrou:
        conn = _connexion(ecriture=False)
        try:
            r = conn.execute("SELECT valeur FROM etat WHERE cle = ?", (cle,)).fetchone()
        finally:
            conn.close()
    return r[0] if r else defaut


def fixer_etat(cle: str, valeur: str) -> None:
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                conn.execute("INSERT OR REPLACE INTO etat (cle, valeur) VALUES (?, ?)", (cle, valeur))
        finally:
            conn.close()


def vider_pour_test() -> None:
    """Tests seulement : vide les trois tables du fichier de TEST (jamais appelé par Atlas)."""
    if pathlib.Path(DB_PATH).resolve() == DEFAULT_DB_PATH.resolve():
        raise RuntimeError("refus : vider_pour_test() sur le vrai data/apprentissage.db")
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                conn.executescript("DELETE FROM appris; DELETE FROM propositions; DELETE FROM etat;")
        finally:
            conn.close()
