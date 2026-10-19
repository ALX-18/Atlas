"""
Sprint Compétences 1 / CP2 — minuteurs et rappels.

« mets un minuteur de 10 minutes », « rappelle-moi dans 20 minutes de… », « rappelle-moi demain à
9 h de… », « tous les lundis à 8 h ». C'est le P2 du rapport Fiabilité : avant, « rappelle-moi »
créait une tâche planifiée QUOTIDIENNE, quel que soit le moment dit.

- Les moments sont calculés par `core.horloge` (déterministe) ; une heure ambiguë fait poser une
  question (deux choix), rien n'est deviné.
- Persistants : `data/rappels.db` (SQLite, une transaction par écriture ; ATLAS_RAPPELS_DB pour un
  Atlas d'essai). Inclus dans les sauvegardes (scripts/backup_memory.py).
- Au moment venu : notification Windows, annonce dans la fenêtre d'Atlas et voix si elle est active
  (`core.annonces`).
- Manqué parce qu'Atlas était éteint : annoncé au démarrage (« Tu avais un rappel à 15 h que je n'ai
  pas pu te donner : … »). Un rappel répété manqué est annoncé une fois, puis reprogrammé.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Optional

from core import horloge

logger = logging.getLogger("atlas.rappels")

DEFAULT_DB_PATH = pathlib.Path(__file__).resolve().parent.parent / "data" / "rappels.db"
DB_PATH: pathlib.Path = pathlib.Path(os.environ.get("ATLAS_RAPPELS_DB") or DEFAULT_DB_PATH)
TOLERANCE_S = 90           # au-delà, un rappel non donné à l'heure est « manqué » (Atlas éteint)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS rappels (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    sorte       TEXT NOT NULL,           -- minuteur | rappel
    texte       TEXT NOT NULL,
    echeance    TEXT NOT NULL,           -- ISO, heure locale
    recurrence  TEXT,                    -- JSON {"jours": [...], "h", "m"} ou NULL
    origine     TEXT,
    cree        TEXT NOT NULL,
    etat        TEXT NOT NULL,           -- actif | donne | manque | annule
    donne       TEXT
);
CREATE INDEX IF NOT EXISTS rappels_actifs ON rappels(etat, echeance);
"""

_verrou = threading.Lock()
_pret: set[str] = set()
_reveil = threading.Event()
_fil: Optional[threading.Thread] = None
_arret = threading.Event()


def _connexion(ecriture: bool = True) -> sqlite3.Connection:
    chemin = pathlib.Path(DB_PATH)
    from core import donnees_reelles

    if donnees_reelles.interdit(chemin):          # BM0 : seul Atlas crée ou écrit le vrai rappels.db
        if ecriture:
            donnees_reelles.verifier_ecriture(chemin, "écriture dans rappels.db")
        return donnees_reelles.lecture_seule(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(chemin), timeout=5.0)
    conn.execute("PRAGMA synchronous=FULL")
    cle = str(chemin.resolve())
    if cle not in _pret:
        with conn:
            conn.executescript(_SCHEMA)
        _pret.add(cle)
    return conn


def _ligne(r) -> dict:
    return {"id": r[0], "sorte": r[1], "texte": r[2], "echeance": datetime.fromisoformat(r[3]),
            "recurrence": json.loads(r[4]) if r[4] else None, "origine": r[5], "cree": r[6], "etat": r[7]}


_COLS = "id, sorte, texte, echeance, recurrence, origine, cree, etat"


def ajouter(sorte: str, texte: str, echeance: datetime, recurrence: Optional[dict] = None,
            origine: Optional[str] = None) -> dict:
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                cur = conn.execute(
                    "INSERT INTO rappels (sorte, texte, echeance, recurrence, origine, cree, etat) "
                    "VALUES (?,?,?,?,?,?, 'actif')",
                    (sorte, texte, echeance.isoformat(timespec="seconds"),
                     json.dumps(recurrence) if recurrence else None, origine,
                     horloge.maintenant().isoformat(timespec="seconds")))
                rid = cur.lastrowid
            r = conn.execute(f"SELECT {_COLS} FROM rappels WHERE id = ?", (rid,)).fetchone()
        finally:
            conn.close()
    _reveil.set()
    return _ligne(r)


def actifs() -> list[dict]:
    with _verrou:
        conn = _connexion(ecriture=False)
        try:
            rows = conn.execute(f"SELECT {_COLS} FROM rappels WHERE etat = 'actif' ORDER BY echeance, id").fetchall()
        finally:
            conn.close()
    return [_ligne(r) for r in rows]


def lire(rid: int) -> Optional[dict]:
    with _verrou:
        conn = _connexion(ecriture=False)
        try:
            r = conn.execute(f"SELECT {_COLS} FROM rappels WHERE id = ?", (rid,)).fetchone()
        finally:
            conn.close()
    return _ligne(r) if r else None


def _changer(rid: int, etat: str, echeance: Optional[datetime] = None) -> None:
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                if echeance is not None:
                    conn.execute("UPDATE rappels SET echeance = ?, donne = ? WHERE id = ?",
                                 (echeance.isoformat(timespec="seconds"),
                                  horloge.maintenant().isoformat(timespec="seconds"), rid))
                else:
                    conn.execute("UPDATE rappels SET etat = ?, donne = ? WHERE id = ?",
                                 (etat, horloge.maintenant().isoformat(timespec="seconds"), rid))
        finally:
            conn.close()


def annuler(rid: int) -> bool:
    r = lire(rid)
    if not r or r["etat"] != "actif":
        return False
    _changer(rid, "annule")
    _reveil.set()
    return True


def vider_pour_test() -> None:
    if pathlib.Path(DB_PATH).resolve() == DEFAULT_DB_PATH.resolve():
        raise RuntimeError("refus : vider_pour_test() sur le vrai data/rappels.db")
    with _verrou:
        conn = _connexion()
        try:
            with conn:
                conn.execute("DELETE FROM rappels")
        finally:
            conn.close()


# --------------------------------------------------------------------------- #
#  Écrire ce qui sera dit
# --------------------------------------------------------------------------- #

def libelle(r: dict, ref: Optional[datetime] = None) -> str:
    ref = ref or horloge.maintenant()
    if r["sorte"] == "minuteur":
        reste = r["echeance"] - ref
        quoi = f" ({r['texte']})" if r["texte"] else ""
        return f"minuteur{quoi} : il reste {horloge.duree_fr(max(reste, timedelta(0)))}"
    quand = horloge.recurrence_fr(r["recurrence"]) if r["recurrence"] else horloge.quand_fr(r["echeance"], ref)
    return f"« {r['texte'] or 'rappel'} », {quand}"


def message_echeance(r: dict) -> str:
    if r["sorte"] == "minuteur":
        return f"Minuteur terminé{' : ' + r['texte'] if r['texte'] else ''} ({horloge.duree_fr(_duree_minuteur(r))})."
    return f"Rappel : {r['texte'] or 'tu m’avais demandé de te prévenir maintenant'}."


def _duree_minuteur(r: dict) -> timedelta:
    try:
        return r["echeance"] - datetime.fromisoformat(r["cree"])
    except Exception:
        return timedelta(0)


def message_manque(r: dict, echeance: datetime) -> str:
    ref = horloge.maintenant()
    quand = horloge.heure_fr(echeance) if echeance.date() == ref.date() else horloge.quand_fr(echeance, ref)
    if r["sorte"] == "minuteur":
        return f"Ton minuteur{' (' + r['texte'] + ')' if r['texte'] else ''} s'est terminé à {quand}, pendant que j'étais éteint."
    return f"Tu avais un rappel à {quand} que je n'ai pas pu te donner : {r['texte'] or 'sans objet'}."


# --------------------------------------------------------------------------- #
#  La surveillance
# --------------------------------------------------------------------------- #

def _publier(message: str, origine: Optional[str]) -> None:
    from core import annonces

    annonces.publier(message, origine, titre="Atlas — rappel", parole=message)


def verifier(au_demarrage: bool = False) -> list[str]:
    """Donne ce qui est arrivé à échéance (une passe). Retourne les messages publiés."""
    ref = horloge.maintenant()
    publies = []
    for r in actifs():
        if r["echeance"] > ref:
            continue
        retard = (ref - r["echeance"]).total_seconds()
        manque = au_demarrage and retard > TOLERANCE_S or retard > 6 * 3600
        msg = message_manque(r, r["echeance"]) if manque else message_echeance(r)
        # D'abord l'état, ensuite l'annonce : la voix prend quelques secondes, et pendant ce temps
        # « quels sont mes rappels ? » listait encore le minuteur (« il reste 0 seconde », rejeu du 18/10).
        if r["recurrence"]:
            _changer(r["id"], "actif", echeance=horloge.prochaine(r["recurrence"], ref))
        else:
            _changer(r["id"], "manque" if manque else "donne")
        _publier(msg, r["origine"])
        publies.append(msg)
    return publies


def prochaine_echeance() -> Optional[datetime]:
    a = actifs()
    return a[0]["echeance"] if a else None


def _boucle() -> None:
    try:
        verifier(au_demarrage=True)
    except Exception as e:
        logger.error("Rappels : vérification au démarrage impossible : %s", e)
    while not _arret.is_set():
        try:
            verifier()
            p = prochaine_echeance()
            attente = 30.0 if p is None else max(0.2, min(30.0, (p - horloge.maintenant()).total_seconds()))
        except Exception as e:
            logger.error("Rappels : %s", e)
            attente = 30.0
        _reveil.wait(attente)
        _reveil.clear()


def demarrer() -> None:
    global _fil
    if _fil and _fil.is_alive():
        return
    _arret.clear()
    _fil = threading.Thread(target=_boucle, name="atlas-rappels", daemon=True)
    _fil.start()
    logger.info("⏰ Rappels : surveillance démarrée (%d actif(s))", len(actifs()))


def arreter() -> None:
    _arret.set()
    _reveil.set()
