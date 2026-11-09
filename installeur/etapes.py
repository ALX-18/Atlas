"""
Sprint Installeur / IN2 — les étapes de l'installation, après la copie des fichiers par l'installeur.

L'installeur (Inno Setup) a déjà vérifié la machine (precheck_atlas.ps1) et copié Atlas et son Python
embarqué. Ce programme, lancé avec ce Python, fait le reste, dans une fenêtre en français :

  1. les dépendances Python, depuis PyPI, à des versions fixes, avec leurs empreintes (--require-hashes) ;
  2. Ollama, par son installeur officiel (vérifié), en silence ; puis : il n'écoute que sur 127.0.0.1, sa
     version est relevée et comparée à la référence ;
  3. Tesseract (lecture du texte à l'écran) et le français ;
  4. le modèle de langue du palier, puis son empreinte comparée à l'épinglage (config/modeles.json) ;
  5. la voix, le mot d'éveil, la transcription et la mémoire (download_voice_models.py, vérifiés) ;
  6. le test de capacité réelle : le modèle chargé, une courte réponse, la part sur la carte et le temps ;
     un résultat qui contredit le palier est dit, et le palier inférieur proposé ;
  7. les réglages : le modèle du palier ; les mails en « simulation » à la première installation.

Chaque étape réussie est notée (installeur/etat.json) : relancer l'installeur reprend où il s'est arrêté.
Un téléchargement interrompu reprend aussi (en-tête Range). Rien d'existant n'est écrasé : un Ollama ou un
Tesseract déjà installé est gardé tel quel.

    python installeur/etapes.py --palier qwen2.5:7b [--sur carte] [--provisoire] [--sans-fenetre]

Code de sortie : 0 terminé ; 1 une étape a échoué (le message dit laquelle et quoi faire) ; 3 la machine ne
tient pas le palier et la personne a choisi d'arrêter.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Optional

ICI = pathlib.Path(__file__).resolve().parent
ROOT = ICI.parent
PY = pathlib.Path(sys.executable)
SOURCES = json.loads((ICI / "sources.json").read_text(encoding="utf-8"))
CACHE = pathlib.Path(os.environ.get("ATLAS_CACHE_INSTALLATION") or (ICI / "cache"))
ETAT = ICI / "etat.json"
JOURNAL = ICI / "installation.log"
OLLAMA_URL = "http://127.0.0.1:11434"
MODELES = json.loads((ROOT / "config" / "modeles.json").read_text(encoding="utf-8"))

# Test de capacité : ce qu'un palier doit tenir (Réunion n° 1 : vérifier la capacité réelle, pas la fiche).
PART_CARTE_MIN_PCT = 90      # sur carte : le modèle doit tenir presque entier dans la mémoire de la carte
JETONS_S_MIN_CARTE = 15.0    # qwen2.5:7b sur une carte de 8 Go : ~40 jetons/s mesurés ; 15 laisse de la marge
JETONS_S_MIN_PROCESSEUR = 3.0  # en dessous, une réponse de 3 phrases prend plus d'une demi-minute


class Echec(Exception):
    """Une étape échoue : le message dit quoi, en français simple, et quoi faire."""


# --------------------------------------------------------------------------- #
#  Journal et état (reprise)
# --------------------------------------------------------------------------- #

def journal(message: str) -> None:
    try:
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def lire_etat() -> dict:
    try:
        return json.loads(ETAT.read_text(encoding="utf-8"))
    except Exception:
        return {"faites": [], "mesures": {}}


def ecrire_etat(etat: dict) -> None:
    ETAT.write_text(json.dumps(etat, ensure_ascii=False, indent=1), encoding="utf-8")


# --------------------------------------------------------------------------- #
#  Téléchargement vérifié, avec reprise
# --------------------------------------------------------------------------- #

def sha256_fichier(chemin: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def git_sha1_fichier(chemin: pathlib.Path) -> str:
    """L'empreinte Git d'un fichier (celle que GitHub publie pour chaque fichier d'un dépôt)."""
    h = hashlib.sha1(f"blob {chemin.stat().st_size}\0".encode())
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def verifier_empreinte(chemin: pathlib.Path, source: dict) -> None:
    if source.get("sha256"):
        attendue, trouvee = source["sha256"].lower(), sha256_fichier(chemin)
    elif source.get("git_sha1"):
        attendue, trouvee = source["git_sha1"].lower(), git_sha1_fichier(chemin)
    else:
        raise Echec(f"aucune empreinte connue pour {chemin.name} : téléchargement refusé")
    if trouvee != attendue:
        chemin.unlink(missing_ok=True)
        raise Echec(f"le fichier téléchargé {chemin.name} n'est pas celui attendu (empreinte {trouvee[:12]}…, "
                    f"attendue {attendue[:12]}…). Il a été effacé ; relancez l'installation.")


def telecharger(source: dict, nom: str, progres: Callable[[float, str], None] = lambda f, t: None,
                ouvrir=urllib.request.urlopen) -> pathlib.Path:
    """Télécharge source["url"] dans le cache, reprend un fichier partiel, vérifie l'empreinte."""
    url = source["url"]
    if not url.startswith("https://"):
        raise Echec(f"adresse refusée (pas en HTTPS) : {url}")
    CACHE.mkdir(parents=True, exist_ok=True)
    final = CACHE / nom
    if final.exists():
        try:
            verifier_empreinte(final, source)
            return final
        except Echec:
            pass                                 # effacé : on recommence
    partiel = CACHE / (nom + ".part")
    deja = partiel.stat().st_size if partiel.exists() else 0
    total = int(source.get("taille") or 0)
    for essai in range(4):
        req = urllib.request.Request(url, headers={"User-Agent": "Atlas-installeur",
                                                   **({"Range": f"bytes={deja}-"} if deja else {})})
        try:
            with ouvrir(req, timeout=60) as r:
                if deja and getattr(r, "status", 200) != 206:
                    deja = 0                     # le serveur ne reprend pas : depuis le début
                mode = "ab" if deja else "wb"
                with open(partiel, mode) as f:
                    while True:
                        bloc = r.read(1 << 20)
                        if not bloc:
                            break
                        f.write(bloc)
                        deja += len(bloc)
                        if total:
                            progres(min(1.0, deja / total), f"{deja / 1e6:.0f} Mo sur {total / 1e6:.0f} Mo")
            break
        except (urllib.error.URLError, OSError, TimeoutError) as e:
            journal(f"téléchargement {nom} interrompu ({e}), reprise {essai + 1}")
            if essai == 3:
                raise Echec(f"le téléchargement de {nom} a échoué ({e}). Vérifiez la connexion à internet, "
                            "puis relancez l'installation : elle reprendra où elle s'est arrêtée.")
            time.sleep(3 * (essai + 1))
    partiel.replace(final)
    verifier_empreinte(final, source)
    return final


# --------------------------------------------------------------------------- #
#  Ollama
# --------------------------------------------------------------------------- #

def _api(chemin: str, corps: Optional[dict] = None, delai: float = 10.0) -> dict:
    donnees = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(OLLAMA_URL + chemin, data=donnees, method="POST" if corps is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=delai) as r:
        return json.loads(r.read().decode("utf-8"))


def ollama_exe() -> Optional[pathlib.Path]:
    trouve = shutil.which("ollama")
    if trouve:
        return pathlib.Path(trouve)
    cand = pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "ollama.exe"
    return cand if cand.exists() else None


def attendre_ollama(secondes: float = 90.0) -> str:
    fin = time.monotonic() + secondes
    while time.monotonic() < fin:
        try:
            return _api("/api/version", delai=3).get("version") or "?"
        except Exception:
            time.sleep(2)
    raise Echec("Ollama est installé mais ne répond pas. Redémarrez l'ordinateur, puis relancez l'installation.")


def adresses_ecoute(port: int = 11434) -> list[str]:
    import psutil

    return sorted({c.laddr.ip for c in psutil.net_connections(kind="inet")
                   if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port == port})


def verifier_ollama_local(adresses: list[str]) -> None:
    exposees = [a for a in adresses if a not in ("127.0.0.1", "::1")]
    if exposees:
        raise Echec("Ollama est ouvert au réseau (" + ", ".join(exposees) + ") : n'importe quel appareil du réseau "
                    "pourrait s'en servir. Dans l'application Ollama, désactivez « Expose Ollama to the network », "
                    "puis relancez l'installation.")


def etape_ollama(progres) -> dict:
    src = SOURCES["ollama"]
    deja = ollama_exe()
    if deja:
        journal(f"Ollama déjà installé ({deja}) : gardé tel quel")
    else:
        if os.environ.get("OLLAMA_HOST", "").startswith("0.0.0.0"):
            raise Echec("La variable OLLAMA_HOST ouvre Ollama au réseau : retirez-la, puis relancez l'installation.")
        setup = telecharger(src, "OllamaSetup.exe", progres)
        progres(None, "installation d'Ollama (une à deux minutes)…")
        r = subprocess.run([str(setup), *src["options"]], timeout=1800)
        if r.returncode != 0:
            raise Echec(f"l'installeur d'Ollama a échoué (code {r.returncode}). Relancez l'installation.")
        exe = ollama_exe()
        if exe is None:
            raise Echec("Ollama ne s'est pas installé. Relancez l'installation.")
        try:
            _api("/api/version", delai=3)
        except Exception:
            subprocess.Popen([str(exe), "serve"], creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    version = attendre_ollama()
    verifier_ollama_local(adresses_ecoute())
    ref = MODELES.get("ollama_reference")
    return {"ollama_version": version, "ollama_reference": ref, "ollama_deja_la": bool(deja),
            "ollama_meme_mineure": version.split(".")[:2] == (ref or "").split(".")[:2]}


# --------------------------------------------------------------------------- #
#  Tesseract
# --------------------------------------------------------------------------- #

def tesseract_dossiers() -> list[pathlib.Path]:
    return [pathlib.Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR",
            pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR"]


def tesseract_exe() -> Optional[pathlib.Path]:
    trouve = shutil.which("tesseract")
    if trouve:
        return pathlib.Path(trouve)
    return next((d / "tesseract.exe" for d in tesseract_dossiers() if (d / "tesseract.exe").exists()), None)


def etape_tesseract(progres) -> dict:
    exe = tesseract_exe()
    deja = exe is not None
    if not deja:
        src = SOURCES["tesseract"]
        setup = telecharger(src, "tesseract-setup.exe", progres)
        progres(None, "installation de Tesseract (Windows peut demander une autorisation)…")
        r = subprocess.run([str(setup), *src["options"]], timeout=900)
        exe = tesseract_exe()
        if r.returncode != 0 or exe is None:
            raise Echec("Tesseract (lecture du texte à l'écran) ne s'est pas installé. Atlas marchera sans, mais ne "
                        "saura pas lire le texte des fenêtres. Relancez l'installation pour réessayer.")
    tessdata = exe.parent / "tessdata"
    francais = tessdata / "fra.traineddata"
    ajoute = False
    if not francais.exists():
        f = telecharger(SOURCES["tesseract_francais"], "fra.traineddata", progres)
        try:
            shutil.copy2(f, francais)
            ajoute = True
        except PermissionError:
            # Tesseract installé pour toute la machine : le français va dans un dossier d'Atlas (TESSDATA_PREFIX)
            perso = ROOT / "models" / "tessdata"
            perso.mkdir(parents=True, exist_ok=True)
            for existant in tessdata.glob("*.traineddata"):
                shutil.copy2(existant, perso / existant.name)
            shutil.copy2(f, perso / "fra.traineddata")
            ajoute = True
    return {"tesseract": str(exe), "tesseract_deja_la": deja, "francais_ajoute": ajoute}


# --------------------------------------------------------------------------- #
#  Les dépendances Python
# --------------------------------------------------------------------------- #

def etape_dependances(progres, sur: str) -> dict:
    verrous = [ICI / "requirements-verrou.txt"] + ([ICI / "requirements-nvidia-verrou.txt"] if sur == "carte" else [])
    for v in verrous:
        if not v.exists():
            raise Echec(f"fichier manquant dans l'installeur : {v.name}")
    cmd = [str(PY), "-m", "pip", "install", "--require-hashes", "--no-deps", "--only-binary", ":all:",
           "--no-cache-dir", "--no-warn-script-location", "--disable-pip-version-check", "--find-links", str(ICI / "roues")]
    for v in verrous:
        cmd += ["-r", str(v)]
    progres(None, "téléchargement des bibliothèques d'Atlas (quelques minutes)…")
    with open(JOURNAL, "a", encoding="utf-8") as j:
        r = subprocess.run(cmd, stdout=j, stderr=subprocess.STDOUT, timeout=7200,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise Echec("l'installation des bibliothèques d'Atlas a échoué (détails dans installeur\\installation.log). "
                    "Vérifiez la connexion à internet, puis relancez l'installation.")
    return {"verrous": [v.name for v in verrous]}


# --------------------------------------------------------------------------- #
#  Le modèle de langue
# --------------------------------------------------------------------------- #

def tirer_modele(modele: str, progres) -> None:
    req = urllib.request.Request(OLLAMA_URL + "/api/pull", data=json.dumps({"model": modele, "stream": True}).encode(),
                                 method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=7200) as r:
        for ligne in r:
            if not ligne.strip():
                continue
            ev = json.loads(ligne)
            if ev.get("error"):
                raise Echec(f"le téléchargement du modèle {modele} a échoué ({ev['error']}). Relancez l'installation.")
            if ev.get("total"):
                progres(ev.get("completed", 0) / ev["total"],
                        f"{ev.get('completed', 0) / 1e9:.1f} Go sur {ev['total'] / 1e9:.1f} Go")


def empreinte_installee(modele: str) -> Optional[str]:
    return next((m.get("digest") for m in _api("/api/tags").get("models", []) if m.get("name") == modele), None)


def etape_modele(progres, modele: str) -> dict:
    if empreinte_installee(modele) is None:
        tirer_modele(modele, progres)
    trouvee = empreinte_installee(modele)
    attendue = (MODELES["modeles"].get(modele) or {}).get("digest")
    if trouvee is None:
        raise Echec(f"le modèle {modele} n'apparaît pas dans Ollama après le téléchargement. Relancez l'installation.")
    return {"modele": modele, "empreinte": trouvee, "empreinte_attendue": attendue,
            "empreinte_conforme": trouvee == attendue}


# --------------------------------------------------------------------------- #
#  Les modèles de la voix et de la mémoire
# --------------------------------------------------------------------------- #

def etape_voix(progres) -> dict:
    progres(None, "voix, mot d'éveil, transcription et mémoire (environ 1,5 Go)…")
    with open(JOURNAL, "a", encoding="utf-8") as j:
        r = subprocess.run([str(PY), str(ROOT / "scripts" / "download_voice_models.py")], cwd=ROOT, stdout=j,
                           stderr=subprocess.STDOUT, timeout=7200, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if r.returncode != 0:
        raise Echec("un modèle de la voix ou de la mémoire n'a pas pu être téléchargé (détails dans "
                    "installeur\\installation.log). Relancez l'installation.")
    return {}


# --------------------------------------------------------------------------- #
#  Le test de capacité réelle
# --------------------------------------------------------------------------- #

@dataclass
class Capacite:
    modele: str
    sur: str
    part_carte_pct: Optional[int]
    jetons_s: Optional[float]
    chargement_s: Optional[float]
    total_s: float
    texte: str
    contredit: bool = False
    raison: str = ""
    mesures: dict = field(default_factory=dict)


def juger_capacite(modele: str, sur: str, part_carte_pct: Optional[int], jetons_s: Optional[float]) -> tuple[bool, str]:
    """(contredit, raison) : la mesure contredit-elle le palier choisi ?"""
    if sur == "carte":
        if part_carte_pct is not None and part_carte_pct < PART_CARTE_MIN_PCT:
            return True, (f"le modèle ne tient qu'à {part_carte_pct} % dans la mémoire de la carte graphique "
                          f"(il en faut {PART_CARTE_MIN_PCT} %) : les réponses seraient lentes")
        if jetons_s is not None and jetons_s < JETONS_S_MIN_CARTE:
            return True, f"le modèle écrit {jetons_s:.0f} mots par seconde environ (il en faut {JETONS_S_MIN_CARTE:.0f})"
        return False, ""
    if jetons_s is not None and jetons_s < JETONS_S_MIN_PROCESSEUR:
        return True, (f"sur le processeur, le modèle écrit {jetons_s:.1f} mots par seconde environ : une réponse de "
                      "quelques phrases prendrait plus d'une demi-minute")
    return False, ""


def mesurer_capacite(modele: str, sur: str) -> Capacite:
    t0 = time.perf_counter()
    r = _api("/api/generate", {"model": modele, "stream": False, "keep_alive": "5m",
                               "prompt": "Réponds en une phrase : quelle est la capitale de l'Italie ?",
                               "options": {"num_ctx": 8192, "temperature": 0.2}}, delai=900)
    total = time.perf_counter() - t0
    part = None
    for m in _api("/api/ps").get("models", []):
        if m.get("name") == modele and m.get("size"):
            part = round(100 * m.get("size_vram", 0) / m["size"])
    jetons = round(r["eval_count"] / (r["eval_duration"] / 1e9), 1) if r.get("eval_duration") else None
    contredit, raison = juger_capacite(modele, sur, part if sur == "carte" else None, jetons)
    return Capacite(modele, sur, part, jetons, round(r.get("load_duration", 0) / 1e9, 1), round(total, 1),
                    (r.get("response") or "").strip()[:200], contredit, raison)


def palier_inferieur(modele: str) -> Optional[str]:
    from_haut = {"qwen2.5:7b": "gemma4:e4b"}
    return from_haut.get(modele)


# --------------------------------------------------------------------------- #
#  Les réglages
# --------------------------------------------------------------------------- #

def etape_reglages(modele: str, premiere_installation: bool) -> dict:
    chemin = ROOT / "config" / "settings.json"
    reglages = json.loads(chemin.read_text(encoding="utf-8"))
    reglages.setdefault("ollama", {})["model"] = modele
    if premiere_installation:
        reglages.setdefault("mail", {})["envoi"] = "simulation"
    chemin.write_text(json.dumps(reglages, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    return {"reglage_modele": modele, "mail_envoi": reglages.get("mail", {}).get("envoi")}


# --------------------------------------------------------------------------- #
#  Le déroulé
# --------------------------------------------------------------------------- #

ETAPES = [("dependances", "Bibliothèques d'Atlas"), ("ollama", "Ollama (le moteur du modèle de langue)"),
          ("tesseract", "Tesseract (lire le texte à l'écran)"), ("modele", "Le modèle de langue"),
          ("voix", "La voix et la mémoire"), ("capacite", "Test de capacité de cet ordinateur"),
          ("reglages", "Les réglages")]


class Deroule:
    def __init__(self, palier: str, sur: str, provisoire: bool, interface):
        self.palier, self.sur, self.provisoire, self.ui = palier, sur, provisoire, interface
        self.etat = lire_etat()
        self.premiere = "reglages" not in self.etat["faites"] and not self.etat.get("installee_une_fois")

    def _faire(self, cle: str, fonction: Callable[[], dict]) -> None:
        if cle in self.etat["faites"] and cle != "capacite":
            self.ui.etape(cle, "deja")
            return
        self.ui.etape(cle, "en_cours")
        t0 = time.perf_counter()
        mesures = fonction() or {}
        mesures["duree_s"] = round(time.perf_counter() - t0, 1)
        self.etat["mesures"][cle] = mesures
        if cle not in self.etat["faites"]:
            self.etat["faites"].append(cle)
        ecrire_etat(self.etat)
        journal(f"étape {cle} : faite {json.dumps(mesures, ensure_ascii=False)}")
        self.ui.etape(cle, "faite")

    def capacite(self) -> dict:
        c = mesurer_capacite(self.palier, self.sur)
        mesure = {"modele": c.modele, "sur": c.sur, "part_carte_pct": c.part_carte_pct, "jetons_s": c.jetons_s,
                  "chargement_s": c.chargement_s, "total_s": c.total_s, "contredit": c.contredit, "raison": c.raison}
        if not c.contredit:
            self.ui.info(f"Test réussi : le modèle répond en {c.total_s:.0f} s"
                         f"{f', {c.part_carte_pct} % sur la carte graphique' if c.part_carte_pct is not None else ''}.")
            return mesure
        inferieur = palier_inferieur(self.palier)
        if inferieur:
            if self.ui.question(f"Le test montre que {c.raison}.\n\nInstaller plutôt le modèle plus léger "
                                f"({inferieur}, provisoire) ?"):
                mesure["palier_abandonne"] = self.palier
                self.palier, self.provisoire = inferieur, True
                self.etat["faites"] = [f for f in self.etat["faites"] if f != "modele"]
                self._faire("modele", lambda: etape_modele(self.ui.progres, self.palier))
                c2 = mesurer_capacite(self.palier, self.sur)
                mesure["apres"] = {"modele": c2.modele, "part_carte_pct": c2.part_carte_pct, "jetons_s": c2.jetons_s,
                                   "total_s": c2.total_s, "contredit": c2.contredit, "raison": c2.raison}
                return mesure
        if not self.ui.question(f"Le test montre que {c.raison}.\n\nAtlas marchera, mais lentement. Continuer quand "
                                "même ?"):
            mesure["arret"] = True
        return mesure

    def lancer(self) -> int:
        try:
            self._faire("dependances", lambda: etape_dependances(self.ui.progres, self.sur))
            self._faire("ollama", lambda: etape_ollama(self.ui.progres))
            self._faire("tesseract", lambda: etape_tesseract(self.ui.progres))
            self._faire("modele", lambda: etape_modele(self.ui.progres, self.palier))
            self._faire("voix", lambda: etape_voix(self.ui.progres))
            self._faire("capacite", self.capacite)
            if self.etat["mesures"].get("capacite", {}).get("arret"):
                self.ui.fin(False, "Installation arrêtée : cet ordinateur est trop lent pour Atlas.")
                return 3
            self._faire("reglages", lambda: etape_reglages(self.palier, self.premiere))
        except Echec as e:
            journal(f"échec : {e}")
            self.ui.fin(False, f"L'installation n'est pas terminée : {e}")
            return 1
        except Exception as e:
            journal(f"erreur inattendue : {type(e).__name__}: {e}")
            self.ui.fin(False, f"L'installation n'est pas terminée (erreur inattendue : {type(e).__name__}). "
                               "Relancez l'installation : elle reprendra où elle s'est arrêtée.")
            return 1
        self.etat["installee_une_fois"] = True
        ecrire_etat(self.etat)
        provisoire = " (provisoire)" if self.provisoire else ""
        self.ui.fin(True, f"Atlas est installé, avec le modèle {self.palier}{provisoire}.")
        return 0


# --------------------------------------------------------------------------- #
#  Les deux interfaces : la fenêtre, et le texte (Sandbox, tests)
# --------------------------------------------------------------------------- #

class Texte:
    def __init__(self, reponses: Optional[list[bool]] = None):
        self.reponses = list(reponses or [])
        self.journal: list[str] = []

    def etape(self, cle, etat):
        self.journal.append(f"{cle}:{etat}")
        print(f"[{etat}] {dict(ETAPES)[cle]}", flush=True)

    def progres(self, fraction, texte):
        pass

    def info(self, texte):
        self.journal.append(f"info:{texte}")
        print(texte, flush=True)

    def question(self, texte):
        r = self.reponses.pop(0) if self.reponses else True
        self.journal.append(f"question:{r}:{texte}")
        print(f"{texte} → {'oui' if r else 'non'}", flush=True)
        return r

    def fin(self, ok, texte):
        self.journal.append(f"fin:{ok}:{texte}")
        print(texte, flush=True)


class Fenetre:
    """Une fenêtre Tkinter : la liste des étapes, une barre de progression, le texte en cours."""

    def __init__(self):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.racine = tk.Tk()
        self.racine.title("Installation d'Atlas")
        self.racine.geometry("560x420")
        self.racine.resizable(False, False)
        tk.Label(self.racine, text="Atlas s'installe", font=("Segoe UI", 15, "bold")).pack(pady=(16, 4))
        tk.Label(self.racine, text="Gardez cet ordinateur allumé et branché à internet. Cela peut prendre du temps : "
                                   "plusieurs gigaoctets sont téléchargés.", wraplength=500,
                 font=("Segoe UI", 10)).pack(pady=(0, 10))
        self.lignes = {}
        cadre = tk.Frame(self.racine)
        cadre.pack(fill="x", padx=30)
        for cle, nom in ETAPES:
            v = tk.StringVar(value=f"   {nom}")
            tk.Label(cadre, textvariable=v, anchor="w", font=("Segoe UI", 10)).pack(fill="x")
            self.lignes[cle] = (v, nom)
        self.barre = ttk.Progressbar(self.racine, length=500, mode="determinate", maximum=1.0)
        self.barre.pack(pady=(14, 4))
        self.texte = tk.StringVar(value="")
        tk.Label(self.racine, textvariable=self.texte, font=("Segoe UI", 9), fg="#555").pack()
        self.bouton = tk.Button(self.racine, text="Fermer", state="disabled", command=self.racine.destroy, width=12)
        self.bouton.pack(pady=12)
        self._q_reponse = None

    def _dans_fil(self, f):
        self.racine.after(0, f)

    def etape(self, cle, etat):
        v, nom = self.lignes[cle]
        signe = {"en_cours": "→", "faite": "✓", "deja": "✓"}[etat]
        self._dans_fil(lambda: (v.set(f"{signe}  {nom}"), self.barre.configure(value=0), self.texte.set("")))

    def progres(self, fraction, texte):
        def f():
            if fraction is None:
                self.barre.configure(mode="indeterminate")
                self.barre.start(15)
            else:
                self.barre.stop()
                self.barre.configure(mode="determinate", value=fraction)
            self.texte.set(texte)
        self._dans_fil(f)

    def info(self, texte):
        self._dans_fil(lambda: self.texte.set(texte))

    def question(self, texte):
        from tkinter import messagebox

        fait = threading.Event()

        def demander():
            self._q_reponse = messagebox.askyesno("Atlas", texte, parent=self.racine)
            fait.set()
        self._dans_fil(demander)
        fait.wait()
        return bool(self._q_reponse)

    def fin(self, ok, texte):
        def f():
            self.barre.stop()
            self.barre.configure(mode="determinate", value=1.0 if ok else 0)
            self.texte.set(texte)
            self.bouton.configure(state="normal", text="Terminer" if ok else "Fermer")
        self._dans_fil(f)


def main(argv=None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--palier", required=True)
    ap.add_argument("--sur", default="carte", choices=("carte", "processeur"))
    ap.add_argument("--provisoire", action="store_true")
    ap.add_argument("--sans-fenetre", action="store_true")
    a = ap.parse_args(argv)
    journal(f"début : palier {a.palier} sur {a.sur}{' (provisoire)' if a.provisoire else ''}")
    if a.sans_fenetre:
        return Deroule(a.palier, a.sur, a.provisoire, Texte()).lancer()
    ui = Fenetre()
    code = {"v": 1}

    def travail():
        code["v"] = Deroule(a.palier, a.sur, a.provisoire, ui).lancer()
    threading.Thread(target=travail, daemon=True).start()
    ui.racine.mainloop()
    return code["v"]


if __name__ == "__main__":
    raise SystemExit(main())
