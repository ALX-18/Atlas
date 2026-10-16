"""
Sprint Index des fichiers / IX3 — ce qu'Atlas sait faire avec l'index de tes fichiers.

- ouvrir par le nom (« ouvre mon CV ») : une correspondance → ouverte avec l'application par
  défaut ; plusieurs → la liste (5 au plus, avec leur dossier) et la question « lequel ? » ; aucune
  → dit, avec la suggestion la plus proche s'il y en a une ;
- dire où (« où est mon rapport de stage ? »), sans rien ouvrir ; « ouvre le dossier » montre le
  fichier dans l'explorateur ;
- les récents (« le dernier PDF téléchargé », « mes fichiers d'hier ») : dates calculées ici,
  de façon déterministe ;
- le contenu (« le document où je parle de budget ») : mots, sans accents ni casse, avec un extrait.

Ouvrir un DOCUMENT, oui. Ouvrir un programme ou un script (`EXTENSIONS_EXECUTABLES`, ou un
raccourci qui pointe vers l'un d'eux), c'est exécuter du code : l'outil devient
`fichier_lancer_programme`, confirmation « toujours » montrant le chemin complet (CONFIRMATION_POLICY).
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from typing import Any, Optional

logger = logging.getLogger("atlas.fichiers")

EXTENSIONS_MACROS = {".docm", ".xlsm", ".pptm", ".dotm", ".xltm"}
TYPES = {
    "pdf": {".pdf"},
    "photo": {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp", ".bmp"},
    "image": {".jpg", ".jpeg", ".png", ".heic", ".gif", ".webp", ".bmp", ".svg"},
    "video": {".mp4", ".mkv", ".mov", ".avi", ".webm"},
    "musique": {".mp3", ".flac", ".wav", ".m4a", ".ogg"},
    "word": {".docx", ".doc", ".odt"},
    "excel": {".xlsx", ".xls", ".ods", ".csv"},
    "tableur": {".xlsx", ".xls", ".ods", ".csv"},
    "presentation": {".pptx", ".ppt", ".odp"},
    "powerpoint": {".pptx", ".ppt", ".odp"},
    "document": {".pdf", ".docx", ".doc", ".odt", ".txt", ".md", ".rtf", ".xlsx", ".pptx", ".ods", ".odp"},
}

_dernier_trouve: Optional[str] = None       # pour « ouvre le dossier » après « où est… »


# --------------------------------------------------------------------------- #
#  Système (remplacés par les tests : jamais d'ouverture réelle en test)
# --------------------------------------------------------------------------- #

def _ouvrir_systeme(chemin: str) -> None:
    os.startfile(chemin)          # application par défaut


def _montrer_dans_explorateur(chemin: str) -> None:
    subprocess.Popen(["explorer", f"/select,{chemin}"])


def dossier_telechargements() -> str:
    return os.path.join(os.path.expandvars("%USERPROFILE%"), "Downloads")


def cible_du_raccourci(chemin: str) -> Optional[str]:
    """Le chemin vers lequel pointe un raccourci .lnk (lecture seule), ou None."""
    try:
        import win32com.client

        return win32com.client.Dispatch("WScript.Shell").CreateShortcut(chemin).TargetPath or None
    except Exception:
        return None


def est_executable(chemin: str) -> tuple[bool, str]:
    """(exécute du code ?, ce qui serait exécuté). Un raccourci vers un document reste un document."""
    from core.file_indexer import EXTENSIONS_EXECUTABLES

    ext = os.path.splitext(chemin)[1].lower()
    if ext == ".lnk":
        cible = cible_du_raccourci(chemin)
        if cible and os.path.splitext(cible)[1].lower() not in EXTENSIONS_EXECUTABLES | EXTENSIONS_MACROS:
            return False, cible
        return True, cible or chemin
    if ext in EXTENSIONS_EXECUTABLES or ext in EXTENSIONS_MACROS:
        return True, chemin
    return False, chemin


# --------------------------------------------------------------------------- #
#  Aides
# --------------------------------------------------------------------------- #

def _indisponible(e: Exception) -> dict:
    from core_conversational.degradations import signaler

    signaler("file_indexer", f"{type(e).__name__}: {e}")
    return {"success": False, "message": "Mon index des fichiers est indisponible pour le moment : "
                                         "je ne peux pas chercher dans tes fichiers."}


def _pas_pret() -> Optional[str]:
    from core.file_indexer import get_file_indexer

    s = get_file_indexer().status()
    if s.get("erreur"):
        raise RuntimeError(s["erreur"])
    if s.get("count", 0) == 0:
        p = s.get("progression") or {}
        if p.get("phase") in ("noms", "contenu"):
            return (f"Mon index des fichiers se construit encore ({p.get('fichiers_vus', 0)} fichiers vus) : "
                    "redemande-moi dans un moment.")
        return "Mon index des fichiers est vide pour le moment : je ne connais encore aucun fichier."
    return None


def _ligne(r: dict, numero: Optional[int] = None) -> str:
    d = datetime.fromtimestamp(r["mtime"]).strftime("%d/%m/%Y %H:%M")
    tete = f"{numero}. " if numero else "- "
    return f"{tete}{r['nom']} — {os.path.dirname(r['chemin'])} ({d})"


def nettoyer_requete(texte: str) -> str:
    """« mon CV », « le fichier rapport de stage » → « CV », « rapport de stage »."""
    t = (texte or "").strip().strip(" .!?\"'«»")
    t = re.sub(r"^(?:le |la |les |l'|l’|mon |ma |mes |un |une |du |de la |des )", "", t, flags=re.I)
    t = re.sub(r"^(?:fichier|document|doc)s?\s+(?:qui s'appelle |nomme |nommé |appele |appelé )?", "", t, flags=re.I)
    t = re.sub(r"^(?:le |la |les |l'|mon |ma |mes )", "", t, flags=re.I)
    return t.strip()


# --------------------------------------------------------------------------- #
#  Résolution (appelée par le moteur AVANT la confirmation)
# --------------------------------------------------------------------------- #

def resoudre(params: dict) -> dict:
    """Ce que veut dire « ouvre … » : {"outil": "fichier_ouvrir"|"fichier_lancer_programme", "params"}
    ou {"resultat": …} (plusieurs choix, aucun, index indisponible)."""
    from core import file_indexer as fi
    from core import propositions

    global _dernier_trouve
    try:
        if params.get("chemin"):                # choisi dans une liste : il doit être DANS l'index
            r = fi.par_chemin(params["chemin"])
            trouves = [r] if r else []
        elif params.get("ouvrir"):              # « ouvre le dernier PDF téléchargé »
            pas_pret = _pas_pret()
            if pas_pret:
                return {"resultat": {"success": False, "message": pas_pret}}
            trouves = _recents(params)[:1]
        else:
            pas_pret = _pas_pret()
            if pas_pret:
                return {"resultat": {"success": False, "message": pas_pret}}
            trouves = fi.chercher_nom(nettoyer_requete(params.get("requete", "")), limite=6)
    except Exception as e:
        return {"resultat": _indisponible(e)}
    demande = nettoyer_requete(params.get("requete", "")) or params.get("libelle") or "ce fichier"
    if params.get("ouvrir") and not trouves:
        return {"resultat": {"success": False, "message": f"Je n'ai trouvé aucun fichier pour « {demande} »."}}
    if not trouves:
        sug = None
        try:
            sug = fi.suggestion(demande)
        except Exception:
            pass
        if sug:
            propositions.proposer(f"ouvre le fichier {sug['chemin']}", "fichier", params.get("_origine"))
            return {"resultat": {"success": False, "message": f"Je n'ai trouvé aucun fichier « {demande} ». "
                                                              f"Tu voulais dire « {sug['nom']} » ({os.path.dirname(sug['chemin'])}) ? "
                                                              "Je l'ouvre ?"}}
        return {"resultat": {"success": False, "message": f"Je n'ai trouvé aucun fichier « {demande} »."}}
    if len(trouves) > 1 and trouves[0].get("rang") == trouves[1].get("rang"):
        options = trouves[:5]
        propositions.proposer(None, "choix_fichier", params.get("_origine"),
                              options=[f"ouvre le fichier {r['chemin']}" for r in options])
        lignes = "\n".join(_ligne(r, k + 1) for k, r in enumerate(options))
        plus = " (et d'autres : précise le nom)" if len(trouves) > 5 else ""
        return {"resultat": {"success": True, "message": f"J'ai trouvé plusieurs fichiers « {demande} »{plus} :\n"
                                                         f"{lignes}\nLequel ? Dis « le 1 », « le 2 »…"}}
    r = trouves[0]
    _dernier_trouve = r["chemin"]
    executable, cible = est_executable(r["chemin"])
    if executable:
        return {"outil": "fichier_lancer_programme", "params": {"chemin": r["chemin"], "cible": cible,
                                                                 "libelle": f"exécuter « {cible} »"}}
    return {"outil": "fichier_ouvrir", "params": {"chemin": cible, "nom": r["nom"]}}


# --------------------------------------------------------------------------- #
#  Outils (TOOL_HANDLERS)
# --------------------------------------------------------------------------- #

def ouvrir(args: dict) -> dict:
    chemin = args.get("chemin")
    if not chemin:
        return {"success": False, "message": "Aucun fichier désigné : rien n'est ouvert."}
    if est_executable(chemin)[0]:            # jamais par cette porte (la confirmation est ailleurs)
        return {"success": False, "message": f"« {chemin} » est un programme : il faut le confirmer."}
    try:
        _ouvrir_systeme(chemin)
    except Exception as e:
        return {"success": False, "message": f"Je n'ai pas pu ouvrir « {os.path.basename(chemin)} » : {e}"}
    return {"success": True, "message": f"J'ouvre « {args.get('nom') or os.path.basename(chemin)} » "
                                        f"({os.path.dirname(chemin)})."}


def lancer_programme(args: dict) -> dict:
    """Seulement après la confirmation « toujours » (CONFIRMATION_POLICY)."""
    chemin = args.get("chemin")
    try:
        _ouvrir_systeme(chemin)
    except Exception as e:
        return {"success": False, "message": f"Je n'ai pas pu lancer « {chemin} » : {e}"}
    return {"success": True, "message": f"Lancé : « {args.get('cible') or chemin} »."}


def ou(args: dict) -> dict:
    from core import file_indexer as fi

    global _dernier_trouve
    demande = nettoyer_requete(args.get("requete", ""))
    try:
        pas_pret = _pas_pret()
        if pas_pret:
            return {"success": False, "message": pas_pret}
        trouves = fi.chercher_nom(demande, limite=5)
    except Exception as e:
        return _indisponible(e)
    if not trouves:
        return {"success": False, "message": f"Je n'ai trouvé aucun fichier « {demande} »."}
    _dernier_trouve = trouves[0]["chemin"]
    if len(trouves) == 1:
        r = trouves[0]
        return {"success": True, "message": f"« {r['nom']} » est dans {os.path.dirname(r['chemin'])}. "
                                            "Dis « ouvre le dossier » pour le voir."}
    lignes = "\n".join(_ligne(r, k + 1) for k, r in enumerate(trouves))
    return {"success": True, "message": f"Plusieurs fichiers « {demande} » :\n{lignes}"}


def ouvrir_dossier(args: dict) -> dict:
    chemin = args.get("chemin") or _dernier_trouve
    if not chemin:
        return {"success": False, "message": "Quel dossier ? Demande-moi d'abord où est un fichier."}
    try:
        _montrer_dans_explorateur(chemin)
    except Exception as e:
        return {"success": False, "message": f"Je n'ai pas pu ouvrir l'explorateur : {e}"}
    return {"success": True, "message": f"J'ouvre {os.path.dirname(chemin)}."}


def bornes(periode: Optional[str], maintenant: Optional[datetime] = None) -> tuple[float, Optional[float], str]:
    """(depuis, jusqu'à, libellé) d'une période dite ; déterministe."""
    m = maintenant or datetime.now()
    jour = datetime(m.year, m.month, m.day)
    lundi = jour - timedelta(days=jour.weekday())
    if periode == "hier":
        return (jour - timedelta(days=1)).timestamp(), jour.timestamp(), "d'hier"
    if periode == "aujourdhui":
        return jour.timestamp(), None, "d'aujourd'hui"
    if periode == "semaine":
        return lundi.timestamp(), None, "de cette semaine"
    if periode == "semaine_derniere":
        return (lundi - timedelta(days=7)).timestamp(), lundi.timestamp(), "de la semaine dernière"
    if periode == "mois":
        return datetime(m.year, m.month, 1).timestamp(), None, "de ce mois-ci"
    return 0.0, None, "les plus récents"


def _recents(args: dict) -> list[dict]:
    from core import file_indexer as fi

    depuis, jusqua, _ = bornes(args.get("periode"))
    ext = TYPES.get(args.get("type") or "") or None
    dossier = dossier_telechargements() if args.get("telecharge") else None
    return fi.recents(depuis, jusqua, ext=ext, dossier=dossier, limite=int(args.get("limite") or 10))


def recents(args: dict) -> dict:
    try:
        pas_pret = _pas_pret()
        if pas_pret:
            return {"success": False, "message": pas_pret}
        trouves = _recents(args)
    except Exception as e:
        return _indisponible(e)
    _, _, libelle = bornes(args.get("periode"))
    quoi = {"pdf": "PDF", "photo": "photos", "image": "images", "video": "vidéos", "word": "documents Word",
            "excel": "tableurs", "tableur": "tableurs", "presentation": "présentations", "powerpoint": "présentations",
            "document": "documents"}.get(args.get("type") or "", "fichiers")
    if args.get("telecharge"):
        quoi += " téléchargés"
    if not trouves:
        return {"success": True, "message": f"Aucun de tes {quoi} {libelle}." if args.get("periode") else f"Aucun {quoi}."}
    lignes = "\n".join(_ligne(r) for r in trouves)
    return {"success": True, "message": f"Tes {quoi} {libelle} :\n{lignes}"}


def contenu(args: dict) -> dict:
    from core import file_indexer as fi
    from core import propositions

    mots = (args.get("mots") or "").strip()
    try:
        pas_pret = _pas_pret()
        if pas_pret:
            return {"success": False, "message": pas_pret}
        trouves = fi.chercher_contenu(mots, limite=5)
    except Exception as e:
        return _indisponible(e)
    if not trouves:
        return {"success": True, "message": f"Aucun de tes documents ne parle de « {mots} »."}
    lignes = "\n".join(f"{_ligne(r, k + 1)}\n   « {r['extrait']} »" for k, r in enumerate(trouves))
    propositions.proposer(None, "choix_fichier", args.get("_origine"),
                          options=[f"ouvre le fichier {r['chemin']}" for r in trouves])
    return {"success": True, "message": f"Les documents qui parlent de « {mots} » :\n{lignes}\n"
                                        "Dis « le 1 », « le 2 »… pour l'ouvrir."}


def index_etat(args: dict) -> dict:
    from core.file_indexer import get_file_indexer

    try:
        s = get_file_indexer().status()
    except Exception as e:
        return _indisponible(e)
    p = s.get("progression") or {}
    if p.get("phase") in ("noms", "contenu"):
        etape = "je relève les fichiers" if p["phase"] == "noms" else "je lis le texte des documents"
        pause = " (en pause : un jeu est en plein écran)" if p.get("en_pause") else ""
        return {"success": True, "message": f"L'index se construit : {etape}{pause}. {p.get('fichiers_vus', 0)} fichiers "
                                            f"vus, {p.get('documents_lus', 0)} documents lus sur "
                                            f"{p.get('documents_a_lire', '?')} ; {s.get('count', 0)} fichiers déjà dans l'index."}
    dernier = s.get("dernier_passage_complet") or {}
    if not dernier:
        return {"success": True, "message": f"L'index n'a pas encore fait de passage complet ({s.get('count', 0)} fichiers)."}
    return {"success": True, "message": f"L'index est à jour : {s.get('count', 0)} fichiers, dont "
                                        f"{s.get('documents_lus', 0)} documents lus ; dernier passage le "
                                        f"{dernier.get('quand')} ({dernier.get('duree_s')} s)."}


def index_oublier(args: dict) -> dict:
    from core import file_indexer as fi

    try:
        n = fi.oublier_index()
    except Exception as e:
        return _indisponible(e)
    return {"success": True, "message": f"J'ai oublié l'index de tes fichiers ({n} fichiers). Il se reconstruira "
                                        "au prochain passage."}
