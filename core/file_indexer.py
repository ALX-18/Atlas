"""
Sprint Index des fichiers — Atlas connaît le PC d'Alexis (décision d'Alexis, 16/10/2026).

Un index LOCAL (`data/file_index.db`, SQLite FTS5, ignoré par Git ; rien n'en sort) :
- les fichiers de TOUS les disques fixes, hors exclusions de la configuration (système, programmes,
  AppData, corbeille, dossiers techniques, profils des autres utilisateurs ; jamais les disques
  amovibles ni réseau) ;
- le texte des documents (PDF, Word, OpenDocument, texte, Markdown, RTF, tableurs et présentations
  Office/OpenDocument), jusqu'à une taille maximale de configuration.

L'index n'est pas une mémoire : il se reconstruit, il n'entre pas dans les sauvegardes, il
s'efface par une commande (« oublie l'index de mes fichiers », avec confirmation).

Atlas reste léger : un fil d'arrière-plan, priorité basse (CPU et disque), au plus
`cpu_max_pourcent` d'un cœur (pauses mesurées), PAUSE pendant un jeu en plein écran, mise à jour
incrémentale (taille et date de modification), suppression des fichiers disparus d'un disque
parcouru en entier. Recherche déterministe, sans modèle de langue (voir `chercher_nom`).
"""

from __future__ import annotations

import asyncio
import ctypes
import difflib
import json
import logging
import os
import pathlib
import re
import sqlite3
import string
import threading
import time
import unicodedata
import zipfile
from typing import Any, Iterator, Optional

logger = logging.getLogger("atlas.file_indexer")
logging.getLogger("pypdf").setLevel(logging.ERROR)   # PDF abîmés : des milliers d'avertissements, aucun utile

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
INDEX_FILE = DATA_DIR / "file_index.json"          # ancien index (noms seulement), lu par app_launcher
DB_PATH = pathlib.Path(os.environ.get("ATLAS_FILE_INDEX_DB") or DATA_DIR / "file_index.db")
CONFIG_FILE = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json"

EXTENSIONS_DOCUMENTS = {".pdf", ".docx", ".odt", ".txt", ".md", ".rtf", ".xlsx", ".pptx", ".ods", ".odp"}

# Ouvrir l'un de ceux-là, c'est EXÉCUTER du code : confirmation « toujours », chemin complet montré.
EXTENSIONS_EXECUTABLES = {".exe", ".bat", ".cmd", ".ps1", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".wsh", ".msi",
                          ".msp", ".scr", ".com", ".pif", ".hta", ".cpl", ".msc", ".jar", ".reg", ".lnk", ".url",
                          ".appref-ms", ".psm1", ".application", ".gadget", ".inf", ".sys", ".dll"}


# --------------------------------------------------------------------------- #
#  Configuration
# --------------------------------------------------------------------------- #

def charger_config() -> dict:
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            config = json.load(f)
    except Exception as e:
        logger.warning("Index des fichiers : configuration illisible (%s)", e)
        return {}
    return dict(config.get("filesystem_assistant", {}))


def _env(p: str) -> str:
    return os.path.normcase(os.path.abspath(os.path.expanduser(os.path.expandvars(p))))


class Exclusions:
    """Dossiers jamais parcourus : par nom (où qu'ils soient) ou par chemin."""

    def __init__(self, noms: list[str], chemins: list[str]):
        self.noms = {n.lower() for n in noms}
        self.chemins = [_env(c) for c in chemins]
        profil = _env("%USERPROFILE%")
        self.dossier_profils = os.path.dirname(profil)
        self.mon_profil = profil

    @classmethod
    def depuis_config(cls, cfg: dict) -> "Exclusions":
        return cls(cfg.get("exclude_names", []), cfg.get("exclude_dirs", []))

    def exclu(self, chemin: str, nom: str) -> bool:
        n = nom.lower()
        if n in self.noms or n.startswith("$"):
            return True
        c = os.path.normcase(chemin)
        if any(c == e or c.startswith(e + os.sep) for e in self.chemins):
            return True
        # Les profils des AUTRES utilisateurs (C:\Users\<autre>), jamais le sien.
        if os.path.dirname(c) == self.dossier_profils and c != self.mon_profil:
            return True
        return False


def disques_fixes() -> list[str]:
    """Disques fixes seulement (DRIVE_FIXED) : jamais amovibles, réseau, lecteurs optiques."""
    if os.name != "nt":
        return ["/"]
    masque = ctypes.windll.kernel32.GetLogicalDrives()
    out = []
    for i, lettre in enumerate(string.ascii_uppercase):
        if masque & (1 << i):
            racine = f"{lettre}:\\"
            if ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(racine)) == 3:
                out.append(racine)
    return out


def racines(cfg: dict) -> list[str]:
    brutes = cfg.get("scan_roots") or ["*"]
    out = []
    for r in brutes:
        if r == "*":
            out += disques_fixes()
        else:
            out.append(os.path.abspath(os.path.expanduser(os.path.expandvars(r))))
    return list(dict.fromkeys(out))


def parcourir(racine: str, regles: Exclusions) -> Iterator[tuple[str, list[str], list[str]]]:
    """(dossier, sous-dossiers, fichiers), sans suivre les jonctions ni les liens symboliques."""
    pile = [racine]
    while pile:
        dossier = pile.pop()
        sous, fichiers = [], []
        try:
            with os.scandir(dossier) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if e.is_junction() if hasattr(e, "is_junction") else False:
                                continue
                            if not regles.exclu(e.path, e.name):
                                sous.append(e.name)
                        elif e.is_file(follow_symlinks=False):
                            fichiers.append(e.name)
                    except OSError:
                        continue
        except OSError:
            continue
        yield dossier, sous, fichiers
        pile.extend(os.path.join(dossier, s) for s in reversed(sous))


# --------------------------------------------------------------------------- #
#  Normalisation et texte des documents
# --------------------------------------------------------------------------- #

def normaliser(texte: str) -> str:
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^\w]+", " ", t.replace("_", " "))
    return " ".join(t.split())


_BALISES = re.compile(r"<[^>]+>")
_RTF = re.compile(r"\\[a-z]+-?\d* ?|[{}]")


def extraire_texte(chemin: str, ext: str, max_car: int) -> str:
    """Le texte d'un document, borné à max_car caractères. Erreur → texte vide."""
    try:
        if ext in (".txt", ".md"):
            with open(chemin, "rb") as f:
                brut = f.read(max_car * 4)
            for enc in ("utf-8", "cp1252"):
                try:
                    return brut.decode(enc)[:max_car]
                except UnicodeDecodeError:
                    continue
            return brut.decode("utf-8", "ignore")[:max_car]
        if ext == ".rtf":
            with open(chemin, "rb") as f:
                return _RTF.sub(" ", f.read(max_car * 4).decode("cp1252", "ignore"))[:max_car]
        if ext == ".pdf":
            from pypdf import PdfReader

            morceaux, n = [], 0
            for page in PdfReader(chemin).pages:
                t = page.extract_text() or ""
                morceaux.append(t)
                n += len(t)
                if n >= max_car:
                    break
            return " ".join(morceaux)[:max_car]
        if ext in (".docx", ".xlsx", ".pptx", ".odt", ".ods", ".odp"):
            with zipfile.ZipFile(chemin) as z:
                noms = z.namelist()
                if ext == ".docx":
                    parts = [n for n in noms if n.startswith("word/") and n.endswith(".xml")]
                elif ext == ".xlsx":
                    parts = [n for n in noms if n in ("xl/sharedStrings.xml",)]
                elif ext == ".pptx":
                    parts = sorted(n for n in noms if n.startswith("ppt/slides/slide") and n.endswith(".xml"))
                else:
                    parts = ["content.xml"] if "content.xml" in noms else []
                morceaux, n = [], 0
                for p in parts:
                    t = _BALISES.sub(" ", z.read(p).decode("utf-8", "ignore"))
                    morceaux.append(t)
                    n += len(t)
                    if n >= max_car:
                        break
                return " ".join(" ".join(morceaux).split())[:max_car]
    except Exception as e:
        logger.debug("Texte illisible (%s) : %s", ext, e)
    return ""


# --------------------------------------------------------------------------- #
#  La base
# --------------------------------------------------------------------------- #

_SCHEMA = """
CREATE TABLE IF NOT EXISTS fichiers (
    id INTEGER PRIMARY KEY,
    chemin TEXT UNIQUE NOT NULL,
    nom TEXT NOT NULL,
    nom_norm TEXT NOT NULL,
    dossier_norm TEXT NOT NULL,
    ext TEXT NOT NULL,
    taille INTEGER NOT NULL,
    mtime REAL NOT NULL,
    racine TEXT NOT NULL,
    passage INTEGER NOT NULL,
    contenu_mtime REAL
);
CREATE INDEX IF NOT EXISTS fichiers_mtime ON fichiers(mtime);
CREATE INDEX IF NOT EXISTS fichiers_racine ON fichiers(racine, passage);
CREATE VIRTUAL TABLE IF NOT EXISTS contenu USING fts5(texte, tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE IF NOT EXISTS noms USING fts5(nom_norm, dossier_norm, tokenize='unicode61 remove_diacritics 2');
CREATE INDEX IF NOT EXISTS fichiers_nom ON fichiers(nom_norm);
CREATE TABLE IF NOT EXISTS etat (cle TEXT PRIMARY KEY, valeur TEXT NOT NULL);
"""


def connexion(chemin: Optional[pathlib.Path] = None) -> sqlite3.Connection:
    p = pathlib.Path(chemin or DB_PATH)
    p.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(p), timeout=10.0, check_same_thread=False)
    c.execute("PRAGMA journal_mode=WAL")       # lectures pendant l'indexation
    c.execute("PRAGMA synchronous=NORMAL")
    c.executescript(_SCHEMA)
    return c


def _synchroniser_noms(c: sqlite3.Connection) -> int:
    """La table plein texte des noms suit `fichiers` (ajouts ; les retraits se font avec eux)."""
    n = c.execute("INSERT INTO noms (rowid, nom_norm, dossier_norm) SELECT id, nom_norm, dossier_norm FROM fichiers "
                  "WHERE id > COALESCE((SELECT MAX(rowid) FROM noms), 0)").rowcount
    c.commit()
    return n


def _etat_lire(c: sqlite3.Connection, cle: str, defaut=None):
    r = c.execute("SELECT valeur FROM etat WHERE cle = ?", (cle,)).fetchone()
    return json.loads(r[0]) if r else defaut


def _etat_ecrire(c: sqlite3.Connection, cle: str, valeur) -> None:
    c.execute("INSERT OR REPLACE INTO etat (cle, valeur) VALUES (?, ?)", (cle, json.dumps(valeur, ensure_ascii=False)))


# --------------------------------------------------------------------------- #
#  Jeu en plein écran : pause
# --------------------------------------------------------------------------- #

def jeu_en_plein_ecran() -> bool:
    """La fenêtre au premier plan couvre tout son écran (et ce n'est pas le Bureau)."""
    if os.name != "nt":
        return False
    try:
        import win32api
        import win32gui

        h = win32gui.GetForegroundWindow()
        if not h or win32gui.GetClassName(h) in ("Progman", "WorkerW", "Shell_TrayWnd"):
            return False
        r = win32gui.GetWindowRect(h)
        m = win32api.GetMonitorInfo(win32api.MonitorFromWindow(h, 2))["Monitor"]
        return tuple(r) == tuple(m)
    except Exception:
        return False


def _fil_en_arriere_plan() -> None:
    """Priorité basse pour ce fil : processeur ET disque (THREAD_MODE_BACKGROUND_BEGIN)."""
    if os.name == "nt":
        try:
            k = ctypes.windll.kernel32
            k.SetThreadPriority(k.GetCurrentThread(), 0x00010000)
        except Exception:
            pass


# --------------------------------------------------------------------------- #
#  L'indexeur
# --------------------------------------------------------------------------- #

class FileIndexer:
    def __init__(self):
        self._running = False
        self._fil: Optional[threading.Thread] = None
        self._arret = threading.Event()
        self._cfg = charger_config()
        self._progression: dict[str, Any] = {"phase": "jamais lancé"}

    # --- état ---
    def enabled(self) -> bool:
        return bool(self._cfg.get("enabled", False))

    def _c(self) -> sqlite3.Connection:
        return connexion()

    def status(self) -> dict[str, Any]:
        try:
            c = self._c()
            count = c.execute("SELECT COUNT(*) FROM fichiers").fetchone()[0]
            docs = c.execute("SELECT COUNT(*) FROM fichiers WHERE contenu_mtime IS NOT NULL").fetchone()[0]
            dernier = _etat_lire(c, "dernier_passage_complet")
            c.close()
        except Exception as e:
            return {"enabled": self.enabled(), "running": self._running, "count": 0, "erreur": str(e)}
        return {"enabled": self.enabled(), "running": self._running, "count": count, "documents_lus": docs,
                "dernier_passage_complet": dernier, "progression": dict(self._progression),
                "roots": racines(self._cfg), "generated_at": dernier}

    # --- cycle de vie ---
    async def start(self):
        if self._running or not self.enabled():
            return
        self._running = True
        self._arret.clear()
        self._fil = threading.Thread(target=self._boucle, name="atlas-index-fichiers", daemon=True)
        self._fil.start()
        logger.info("📂 Index des fichiers : démarré en arrière-plan")

    async def stop(self):
        self._running = False
        self._arret.set()
        if self._fil:
            await asyncio.to_thread(self._fil.join, 10)
            self._fil = None
        logger.info("📂 Index des fichiers : arrêté")

    def _boucle(self):
        _fil_en_arriere_plan()
        intervalle = max(60, int(self._cfg.get("scan_interval_seconds", 1800)))
        while not self._arret.is_set():
            try:
                self.passage()
            except Exception as e:
                logger.warning("Index des fichiers : passage interrompu (%s)", e)
                from core_conversational.degradations import signaler

                signaler("file_indexer", f"{type(e).__name__}: {e}")
            self._arret.wait(intervalle)

    async def run_once(self) -> dict[str, Any]:
        await asyncio.to_thread(self.passage)
        return self.status()

    # --- un passage : tous les fichiers, puis le texte des documents changés ---
    def _attendre(self, debut_lot: float) -> None:
        """Plafond CPU (part d'un cœur) ; pause tant qu'un jeu est en plein écran."""
        cpu = min(100, max(1, int(self._cfg.get("cpu_max_pourcent", 25))))
        travail = time.perf_counter() - debut_lot
        if cpu < 100:
            time.sleep(travail * (100 - cpu) / cpu)
        if self._cfg.get("pause_en_jeu", True):
            while jeu_en_plein_ecran() and not self._arret.is_set():
                self._progression["en_pause"] = "jeu en plein écran"
                time.sleep(5)
            self._progression.pop("en_pause", None)

    def passage(self) -> dict[str, Any]:
        cfg = self._cfg
        regles = Exclusions.depuis_config(cfg)
        taille_max = int(float(cfg.get("contenu_taille_max_mo", 20)) * 1024 * 1024)
        max_car = int(cfg.get("contenu_caracteres_max", 200_000))
        plafond = int(cfg.get("max_files_per_scan", 3_000_000))
        lot = 500
        c = self._c()
        try:
            n_passage = (_etat_lire(c, "passage", 0) or 0) + 1
            _etat_ecrire(c, "passage", n_passage)
            c.commit()
            debut = time.time()
            vus = nouveaux = 0
            self._progression = {"phase": "noms", "debut": time.strftime("%H:%M:%S"), "fichiers_vus": 0,
                                 "documents_lus": 0, "disque": None}
            for racine in racines(cfg):
                if self._arret.is_set():
                    break
                self._progression["disque"] = racine
                complet = True
                t_lot, en_attente = time.perf_counter(), 0
                for dossier, _, noms in parcourir(racine, regles):
                    if self._arret.is_set() or vus >= plafond:
                        complet = False
                        break
                    for nom in noms:
                        chemin = os.path.join(dossier, nom)
                        try:
                            st = os.stat(chemin)
                        except OSError:
                            continue
                        ext = os.path.splitext(nom)[1].lower()
                        cur = c.execute("UPDATE fichiers SET passage = ? WHERE chemin = ? AND taille = ? AND mtime = ?",
                                        (n_passage, chemin, st.st_size, st.st_mtime))
                        if cur.rowcount == 0:
                            c.execute("INSERT INTO fichiers (chemin, nom, nom_norm, dossier_norm, ext, taille, mtime, racine,"
                                      " passage, contenu_mtime) VALUES (?,?,?,?,?,?,?,?,?,NULL) ON CONFLICT(chemin) DO UPDATE"
                                      " SET taille=excluded.taille, mtime=excluded.mtime, passage=excluded.passage,"
                                      " contenu_mtime=NULL",
                                      (chemin, nom, normaliser(os.path.splitext(nom)[0]), normaliser(dossier), ext,
                                       st.st_size, st.st_mtime, racine, n_passage))
                            nouveaux += 1
                        vus += 1
                        en_attente += 1
                        if en_attente >= lot:
                            c.commit()
                            self._progression["fichiers_vus"] = vus
                            self._attendre(t_lot)
                            t_lot, en_attente = time.perf_counter(), 0
                c.commit()
                if complet:          # disparus : seulement d'un disque parcouru EN ENTIER
                    # Par préfixe de chemin : un passage limité à un dossier ne retire que ses disparus.
                    prefixe = os.path.join(racine, "").replace("%", "") + "%"
                    ids = [r[0] for r in c.execute("SELECT id FROM fichiers WHERE chemin LIKE ? AND passage < ?",
                                                   (prefixe, n_passage))]
                    for i in range(0, len(ids), 500):
                        part = ids[i:i + 500]
                        marques = ",".join("?" * len(part))
                        c.execute(f"DELETE FROM contenu WHERE rowid IN ({marques})", part)
                        c.execute(f"DELETE FROM noms WHERE rowid IN ({marques})", part)
                        c.execute(f"DELETE FROM fichiers WHERE id IN ({marques})", part)
                    c.commit()
            _synchroniser_noms(c)
            # Le texte des documents nouveaux ou modifiés
            self._progression["phase"] = "contenu"
            a_lire = c.execute("SELECT id, chemin, ext, taille FROM fichiers WHERE contenu_mtime IS NULL AND ext IN (%s)"
                               % ",".join("?" * len(EXTENSIONS_DOCUMENTS)), sorted(EXTENSIONS_DOCUMENTS)).fetchall()
            self._progression["documents_a_lire"] = len(a_lire)
            lus, t_lot = 0, time.perf_counter()
            for i, chemin, ext, taille in a_lire:
                if self._arret.is_set():
                    break
                texte = extraire_texte(chemin, ext, max_car) if taille <= taille_max else ""
                c.execute("DELETE FROM contenu WHERE rowid = ?", (i,))
                if texte.strip():
                    c.execute("INSERT INTO contenu (rowid, texte) VALUES (?, ?)", (i, texte))
                c.execute("UPDATE fichiers SET contenu_mtime = mtime WHERE id = ?", (i,))
                lus += 1
                if lus % 20 == 0:
                    c.commit()
                    self._progression["documents_lus"] = lus
                    self._attendre(t_lot)
                    t_lot = time.perf_counter()
            c.commit()
            fin = {"quand": time.strftime("%Y-%m-%d %H:%M:%S"), "duree_s": round(time.time() - debut, 1),
                   "fichiers": vus, "nouveaux_ou_modifies": nouveaux, "documents_lus": lus}
            if not self._arret.is_set():
                _etat_ecrire(c, "dernier_passage_complet", fin)
                c.commit()
            self._progression = {"phase": "à jour", **fin}
            return fin
        finally:
            c.close()

    # --- recherche (déterministe) ---
    async def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        return [{"name": r["nom"], "path": r["chemin"], "ext": r["ext"], "size": r["taille"], "mtime": int(r["mtime"])}
                for r in chercher_nom(query, limite=max(1, min(limit, 200)))]


# --------------------------------------------------------------------------- #
#  Recherches — sans modèle de langue, classement explicable
# --------------------------------------------------------------------------- #

def _ligne(r) -> dict:
    return {"id": r[0], "chemin": r[1], "nom": r[2], "ext": r[3], "taille": r[4], "mtime": r[5]}


_COLS = "id, chemin, nom, ext, taille, mtime"


def chercher_nom(texte: str, limite: int = 5, ext: Optional[set[str]] = None) -> list[dict]:
    """Classement : 1) nom exact, 2) tous les mots dans le nom, 3) tous les mots dans le dossier,
    4) nom approché (≥ 0,8). À rang égal : le plus récent d'abord. Chaque résultat dit son rang."""
    q = normaliser(texte)
    if not q:
        return []
    mots = q.split()
    c = connexion()
    try:
        filtre_ext = ""
        params_ext: list = []
        if ext:
            filtre_ext = " AND ext IN (%s)" % ",".join("?" * len(ext))
            params_ext = sorted(ext)
        out, vus = [], set()

        def ajouter(rows, rang, raison):
            for r in rows:
                if r[0] not in vus:
                    vus.add(r[0])
                    out.append({**_ligne(r), "rang": rang, "raison": raison})

        if c.execute("SELECT 1 FROM fichiers LIMIT 1").fetchone() and not c.execute("SELECT 1 FROM noms LIMIT 1").fetchone():
            _synchroniser_noms(c)               # base d'avant la table des noms : une fois
        cols_f = ", ".join(f"f.{x.strip()}" for x in _COLS.split(","))
        filtre_f = filtre_ext.replace(" ext ", " f.ext ")

        def par_mots(colonne: str):
            # Chaque mot doit commencer un mot du nom (ou du dossier) : « cv » trouve « CV_Alexis ».
            requete = f"{colonne} : (" + " AND ".join(f'"{m}"*' for m in mots) + ")"
            return c.execute(f"SELECT {cols_f} FROM noms JOIN fichiers f ON f.id = noms.rowid WHERE noms MATCH ?"
                             f"{filtre_f} ORDER BY f.mtime DESC LIMIT 50", [requete] + params_ext).fetchall()

        ajouter(c.execute(f"SELECT {_COLS} FROM fichiers WHERE nom_norm = ?{filtre_ext} ORDER BY mtime DESC LIMIT 50",
                          [q] + params_ext).fetchall(), 1, "nom exact")
        ajouter(par_mots("nom_norm"), 2, "tous les mots dans le nom")
        if len(out) < limite:
            ajouter(par_mots("dossier_norm"), 3, "tous les mots dans le dossier")
        if not out:
            pref = mots[0][:3]
            cands = c.execute(f"SELECT {cols_f}, f.nom_norm FROM noms JOIN fichiers f ON f.id = noms.rowid "
                              f"WHERE noms MATCH ?{filtre_f} LIMIT 5000", [f'nom_norm : "{pref}"*'] + params_ext).fetchall()
            notes = sorted(((difflib.SequenceMatcher(None, q, r[6]).ratio(), r) for r in cands),
                           key=lambda x: (-x[0], -x[1][5]))
            ajouter([r[:6] for s, r in notes if s >= 0.8], 4, "nom approché")
        return out[:limite]
    finally:
        c.close()


def suggestion(texte: str) -> Optional[dict]:
    """Le nom le plus proche (≥ 0,6), pour « je n'ai rien trouvé ; tu voulais dire … ? »."""
    q = normaliser(texte)
    if not q:
        return None
    c = connexion()
    try:
        cands = c.execute(f"SELECT {_COLS}, nom_norm FROM fichiers WHERE (' ' || nom_norm) LIKE ? LIMIT 5000",
                          [f"% {q.split()[0][:2]}%"]).fetchall()
    finally:
        c.close()
    notes = sorted(((difflib.SequenceMatcher(None, q, r[6]).ratio(), r) for r in cands), key=lambda x: -x[0])
    return _ligne(notes[0][1]) if notes and notes[0][0] >= 0.6 else None


def recents(depuis: float, jusqua: Optional[float] = None, ext: Optional[set[str]] = None,
            dossier: Optional[str] = None, limite: int = 10) -> list[dict]:
    c = connexion()
    try:
        sql, p = f"SELECT {_COLS} FROM fichiers WHERE mtime >= ?", [depuis]
        if jusqua is not None:
            sql += " AND mtime < ?"
            p.append(jusqua)
        if ext:
            sql += " AND ext IN (%s)" % ",".join("?" * len(ext))
            p += sorted(ext)
        if dossier:                      # un dossier et ses sous-dossiers (préfixe du chemin)
            sql += " AND chemin LIKE ?"
            p.append(os.path.join(dossier, "").replace("%", "") + "%")
        sql += " ORDER BY mtime DESC LIMIT ?"
        p.append(limite)
        return [_ligne(r) for r in c.execute(sql, p).fetchall()]
    finally:
        c.close()


def chercher_contenu(mots: str, limite: int = 5) -> list[dict]:
    """Recherche par mots dans le texte des documents (sans accents ni casse), avec un extrait."""
    termes = [t for t in normaliser(mots).split() if len(t) > 1]
    if not termes:
        return []
    requete = " AND ".join(f'"{t}"' for t in termes)
    c = connexion()
    try:
        rows = c.execute(f"SELECT f.id, f.chemin, f.nom, f.ext, f.taille, f.mtime, "
                         f"snippet(contenu, 0, '«', '»', '…', 14) FROM contenu JOIN fichiers f ON f.id = contenu.rowid "
                         f"WHERE contenu MATCH ? ORDER BY bm25(contenu), f.mtime DESC LIMIT ?", (requete, limite)).fetchall()
    finally:
        c.close()
    return [{**_ligne(r), "extrait": " ".join(r[6].split())} for r in rows]


def par_chemin(chemin: str) -> Optional[dict]:
    c = connexion()
    try:
        r = c.execute(f"SELECT {_COLS} FROM fichiers WHERE chemin = ?", (chemin,)).fetchone()
    finally:
        c.close()
    return _ligne(r) if r else None


def indexer_un_fichier(chemin: str) -> None:
    """Sprint Artefacts : un document créé par Atlas entre TOUT DE SUITE dans l'index (nom et texte)."""
    st = os.stat(chemin)
    nom = os.path.basename(chemin)
    ext = os.path.splitext(nom)[1].lower()
    cfg = charger_config()
    c = connexion()
    try:
        passage = _etat_lire(c, "passage", 0) or 0
        c.execute("INSERT INTO fichiers (chemin, nom, nom_norm, dossier_norm, ext, taille, mtime, racine, passage, contenu_mtime)"
                  " VALUES (?,?,?,?,?,?,?,?,?,NULL) ON CONFLICT(chemin) DO UPDATE SET taille=excluded.taille,"
                  " mtime=excluded.mtime, contenu_mtime=NULL",
                  (chemin, nom, normaliser(os.path.splitext(nom)[0]), normaliser(os.path.dirname(chemin)), ext,
                   st.st_size, st.st_mtime, os.path.splitdrive(chemin)[0] + os.sep, passage))
        (i,) = c.execute("SELECT id FROM fichiers WHERE chemin = ?", (chemin,)).fetchone()
        c.execute("DELETE FROM noms WHERE rowid = ?", (i,))
        c.execute("INSERT INTO noms (rowid, nom_norm, dossier_norm) VALUES (?, ?, ?)",
                  (i, normaliser(os.path.splitext(nom)[0]), normaliser(os.path.dirname(chemin))))
        if ext in EXTENSIONS_DOCUMENTS:
            texte = extraire_texte(chemin, ext, int(cfg.get("contenu_caracteres_max", 50_000)))
            c.execute("DELETE FROM contenu WHERE rowid = ?", (i,))
            if texte.strip():
                c.execute("INSERT INTO contenu (rowid, texte) VALUES (?, ?)", (i, texte))
            c.execute("UPDATE fichiers SET contenu_mtime = mtime WHERE id = ?", (i,))
        c.commit()
    finally:
        c.close()


def oublier_index() -> int:
    """Vide l'index (« oublie l'index de mes fichiers », confirmé). Retourne le nombre de fichiers."""
    c = connexion()
    try:
        n = c.execute("SELECT COUNT(*) FROM fichiers").fetchone()[0]
        c.executescript("DELETE FROM contenu; DELETE FROM noms; DELETE FROM fichiers; DELETE FROM etat;")
        c.commit()
        c.execute("VACUUM")
        return n
    finally:
        c.close()


_indexer: FileIndexer | None = None


def get_file_indexer() -> FileIndexer:
    global _indexer
    if _indexer is None:
        _indexer = FileIndexer()
    return _indexer
