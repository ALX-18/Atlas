"""
Brief Installeur — fin / IF3 — relever les journaux d'Atlas et de son installeur chez un proche, sans rien de lui.

Lancé par relever_journaux.bat, depuis la clé USB, avec le Python d'Atlas. Copie dans un dossier daté de la clé :

  - les journaux de l'installeur (installeur/installation.log, etat.json, ollama_serveur.log) ;
  - les journaux d'Atlas (data/logs/*.log) ;
  - le journal d'Inno Setup de l'installation d'Atlas (%TEMP%\\Setup Log …, celui qui parle d'Atlas) ;
  - les journaux d'Ollama (%LOCALAPPDATA%\\Ollama\\server*.log, app*.log) ;
  - le diagnostic de la machine (precheck_atlas.ps1, en lecture seule).

Rien d'autre : ni la mémoire (data/chromadb, apprentissage.db), ni les actions, ni les réglages, ni les secrets.
Dans chaque fichier copié, le nom de la session Windows, le nom de l'ordinateur, le prénom réglé dans Atlas et les
adresses mail sont remplacés (<session>, <ordinateur>, <prénom>, <adresse>). RELEVE.txt dit ce qui a été pris,
ce qui manquait, et combien de remplacements ont été faits, sans jamais redire les valeurs remplacées.

    python installeur/relever_journaux.py --vers E:\\releves
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import subprocess
from typing import Callable, Iterable, Optional

ROOT = pathlib.Path(__file__).resolve().parent.parent
ADRESSE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
JOURNAUX_INSTALLEUR = ("installation.log", "etat.json", "ollama_serveur.log")


# --------------------------------------------------------------------------- #
#  Décision du superviseur (11/11) : ni noms ni chemins de fichiers du proche
# --------------------------------------------------------------------------- #
# Ce qui en porte, relevé dans le code d'Atlas : les arguments des outils (« Tool '…' executed: {'path': …} »), les
# cibles des confirmations, les titres de fenêtre (nom du document ou de la page), les messages d'exception, les
# transcriptions. Trois règles, dans cet ordre :
#   1. une ligne au format d'Atlas (« date [module] NIVEAU — message ») ne garde son message que si le module est
#      technique (liste blanche : un module nouveau est retiré par défaut) ; et, même alors, sans ce qui est dit ;
#   2. tout chemin hors des dossiers techniques (Atlas sans ses données, Ollama, Program Files, Windows) → <chemin> ;
#   3. tout nom de document → <fichier> ; toute adresse web non technique → <url> ; la recherche d'une requête → <retiré>.

LIGNE_ATLAS = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d,\d+ \[([\w.]+)\] [A-Z]+ — )(.*)$")
MODULES_TECHNIQUES = frozenset({
    "atlas",               # main.py : démarrage, modèle, verrou, arrêt
    "atlas.ollama",        # client Ollama : contexte, préchauffage
    "atlas.modele_local",  # épinglage du modèle, mode jeu
    "atlas.memory",        # état de la mémoire
    "atlas.memory_core",
    "atlas.voice",         # mot d'éveil, temps de transcription (pas ce qui est dit : règle ci-dessous)
    "atlas.systray",
    "atlas.diagnostics",
    "atlas.donnees_reelles",
    "atlas.file_indexer",  # démarrage et arrêt de l'index (aucun nom de fichier au niveau INFO)
})
# Dans un module technique, ce qui suit ces débuts de message est ce qui a été dit, entendu ou cherché.
DITS = ("[VOIX] Transcription (", "[VOIX] Transcription :", "[VOIX] Phrase dite", "[VOIX] Piper n'a produit",
        "[VOIX] «", "[VOIX] Impossible d'afficher", "[VOIX] Confirmation impossible", "[AUTOMATION]",
        "[ANNONCE]", "[HABITUDE]", "Modèle e5 indisponible", "Habitude détectée",
        # mémoire : le souvenir et le nom du document (trouvé sur un vrai journal d'Atlas d'essai, 11/11)
        "Souvenir sauvegardé", "Ingestion document")
RETIRE = "<contenu retiré>"

CHEMIN = re.compile(r"(?<![\w<])[A-Za-z]:(?:\\\\|\\|/)[^\r\n\t\"'«»<>|*?]*")
DOCUMENT = re.compile(r"[\w\-().,'’+&]+\.(?:pdf|docx?|xlsx?|pptx?|od[tsp]|rtf|txt|csv|md|epub|html?|jpe?g|png|gif|"
                      r"bmp|heic|webp|tiff?|mp3|m4a|wav|flac|ogg|mp4|mov|avi|mkv|zip|rar|7z|eml|msg|ics|vcf)\b",
                      re.IGNORECASE)
NOMS_TECHNIQUES = re.compile(r"^(?:requirements[\w-]*\.txt|precheck(?:_brut)?\.txt|desinstallation\.txt|"
                             r"LICENSE(?:\.txt|\.md)?|README\.md|sha256sum\.txt|RELEVE\.txt)$", re.IGNORECASE)
URL = re.compile(r"https?://([^/\s\"'<>)]+)[^\s\"'<>)]*")
HOTES_TECHNIQUES = re.compile(r"^(?:127\.0\.0\.1|localhost|\[::1\])(?::\d+)?$|(?:^|\.)(?:github\.com|"
                              r"githubusercontent\.com|ollama\.com|ollama\.ai|huggingface\.co|hf\.co|pypi\.org|"
                              r"pythonhosted\.org|python\.org|microsoft\.com|windowsupdate\.com)$", re.IGNORECASE)
RECHERCHE = re.compile(r"(\"(?:GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS) [^\s?\"]*)\?[^\s\"]*")
DONNEES_GARDEES = ("data\\logs", "data\\chromadb", "data\\voices", "data\\workflows")


def racines_techniques(app: pathlib.Path) -> list[str]:
    """Les dossiers où un chemin n'apprend rien de la personne : Atlas (sans ses données), Ollama, Program Files,
    Windows, et le dossier temporaire de l'installeur (is-….tmp)."""
    env = os.environ
    local = env.get("LOCALAPPDATA", "")
    profil = env.get("USERPROFILE", "")
    racines = [str(app), os.path.join(local, "Programs", "Ollama"), os.path.join(local, "Programs", "Tesseract-OCR"),
               os.path.join(local, "Ollama"), os.path.join(profil, ".ollama"),
               os.path.join(profil, ".cache", "huggingface"),
               env.get("ProgramFiles", r"C:\Program Files"), env.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
               env.get("SystemRoot", r"C:\Windows"), os.path.join(env.get("TEMP", ""), "is-")]
    return [r for r in racines if r and len(r) > 3]


def _chemin_technique(chemin: str, racines: list[str]) -> bool:
    simple = chemin.replace("\\\\", "\\").replace("/", "\\").lstrip("\\?").lower()
    for racine in racines:
        r = racine.replace("/", "\\").rstrip("\\").lower()
        if simple == r or simple.startswith(r + "\\") or (r.endswith("is-") and simple.startswith(r)):
            reste = simple[len(r):].lstrip("\\")
            if reste.startswith("data\\") and not reste.startswith(DONNEES_GARDEES):
                return False          # data\ d'Atlas : documents, captures… leurs noms sont à la personne
            return True
    return False


def _hors_des_chemins(texte: str, fonction) -> str:
    """Applique `fonction` aux morceaux de texte qui ne sont pas des chemins techniques déjà gardés."""
    morceaux, debut = [], 0
    for m in re.finditer(r"\x00[^\x00]*\x00", texte):
        morceaux.append(fonction(texte[debut:m.start()]))
        morceaux.append(m.group(0))
        debut = m.end()
    morceaux.append(fonction(texte[debut:]))
    return "".join(morceaux)


def nettoyer_contenu(texte: str, racines: list[str]) -> tuple[str, int]:
    """Le texte sans noms ni chemins de fichiers de la personne, ni ce qu'elle a dit ; et le nombre de retraits."""
    compte = [0]

    def ligne_atlas(ligne: str) -> str:
        m = LIGNE_ATLAS.match(ligne)
        if not m:
            return ligne
        entete, module, message = m.groups()
        if module not in MODULES_TECHNIQUES:
            compte[0] += 1
            return entete + RETIRE
        for debut in DITS:
            if message.startswith(debut):
                coupes = [i for i in (message.find(" : ", len(debut) - 1), message.find("«"), message.find("'"),
                                      message.find('"')) if i >= 0]
                coupe = min(coupes) if coupes else len(debut)
                compte[0] += 1
                return entete + message[:coupe].rstrip() + " : " + RETIRE
        return ligne

    texte = "\n".join(ligne_atlas(l) for l in texte.split("\n"))

    def chemin(m: re.Match) -> str:
        if _chemin_technique(m.group(0), racines):
            return "\x00" + m.group(0) + "\x00"      # protégé des règles suivantes
        compte[0] += 1
        return "<chemin>"

    texte = CHEMIN.sub(chemin, texte)

    def documents_et_adresses(morceau: str) -> str:
        def document(m: re.Match) -> str:
            if NOMS_TECHNIQUES.match(m.group(0)):
                return m.group(0)
            compte[0] += 1
            return "<fichier>"

        def adresse(m: re.Match) -> str:
            if HOTES_TECHNIQUES.search(m.group(1)):
                return m.group(0)
            compte[0] += 1
            return "<url>"

        morceau = URL.sub(adresse, morceau)
        morceau, n = RECHERCHE.subn(r"\1?<retiré>", morceau)
        compte[0] += n
        return DOCUMENT.sub(document, morceau)

    texte = _hors_des_chemins(texte, documents_et_adresses).replace("\x00", "")
    return texte, compte[0]


def _motif(valeur: str) -> re.Pattern:
    return re.compile(r"(?<!\w)" + re.escape(valeur) + r"(?!\w)", re.IGNORECASE)


def anonymiser(texte: str, session: str, ordinateur: str, prenom: str,
               autres_sessions: Iterable[str] = ()) -> tuple[str, int]:
    """Le texte sans session, ordinateur, prénom ni adresse ; et le nombre de remplacements. Une valeur de moins de
    deux lettres n'est pas remplacée (elle effacerait des mots ordinaires)."""
    total = 0
    texte, n = ADRESSE.subn("<adresse>", texte)
    total += n
    remplacements = [(ordinateur, "<ordinateur>"), (session, "<session>"),
                     *((s, "<session>") for s in autres_sessions), (prenom, "<prénom>")]
    for valeur, etiquette in sorted(remplacements, key=lambda v: -len(v[0] or "")):
        valeur = (valeur or "").strip()
        if len(valeur) < 2:
            continue
        texte, n = _motif(valeur).subn(etiquette, texte)
        total += n
    return texte, total


def _reglage(app: pathlib.Path, section: str, cle: str) -> str:
    """Une seule clé de settings.json : le reste des réglages n'est ni lu ni copié."""
    try:
        reglages = json.loads((app / "config" / "settings.json").read_text(encoding="utf-8-sig"))
        return str((reglages.get(section) or {}).get(cle) or "")
    except (OSError, ValueError, AttributeError):
        return ""


def prenom_regle(app: pathlib.Path) -> str:
    return _reglage(app, "utilisateur", "prenom")


def _lire(f: pathlib.Path) -> str:
    brut = f.read_bytes()
    try:
        return brut.decode("utf-8-sig")
    except UnicodeDecodeError:
        return brut.decode("cp1252", errors="replace")


def precheck_windows(app: pathlib.Path) -> Callable[[pathlib.Path], None]:
    def faire(fichier: pathlib.Path) -> None:
        script = app / "scripts" / "precheck_atlas.ps1"
        if script.exists():
            subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script),
                            "-Sortie", str(fichier)], timeout=300, capture_output=True)
    return faire


def relever(app: pathlib.Path, dest: pathlib.Path, temp: Optional[pathlib.Path] = None,
            dossier_ollama: Optional[pathlib.Path] = None, session: Optional[str] = None,
            ordinateur: Optional[str] = None,
            precheck: Optional[Callable[[pathlib.Path], None]] = None,
            racines: Optional[list[str]] = None) -> pathlib.Path:
    temp = temp or pathlib.Path(os.environ.get("TEMP", ""))
    dossier_ollama = dossier_ollama or pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama"
    session = os.environ.get("USERNAME", "") if session is None else session
    ordinateur = os.environ.get("COMPUTERNAME", "") if ordinateur is None else ordinateur
    profil = pathlib.Path(os.environ.get("USERPROFILE", "")).name if session == os.environ.get("USERNAME") else ""
    prenom = prenom_regle(app)
    precheck = precheck or precheck_windows(app)
    racines = racines_techniques(app) if racines is None else racines

    sortie = dest / f"releve_{datetime.datetime.now():%Y%m%d_%H%M%S}"
    sortie.mkdir(parents=True, exist_ok=False)
    lignes = [f"Relevé du {datetime.datetime.now():%d/%m/%Y à %H:%M:%S}",
              "Copiés : les journaux d'Atlas, de son installeur et d'Ollama, et le diagnostic de la machine.",
              "Jamais copiés : la mémoire, les actions, les réglages, les secrets.",
              "Remplacés dans chaque fichier : session Windows, nom de l'ordinateur, prénom réglé, adresses mail.",
              f"mails : {_reglage(app, 'mail', 'envoi') or 'inconnu (réglages absents)'}", ""]

    def copier(source: pathlib.Path, nom: str) -> None:
        if not source.is_file():
            lignes.append(f"absent : {nom}")
            return
        propre, n_fichiers = nettoyer_contenu(_lire(source), racines)
        propre, n = anonymiser(propre, session, ordinateur, prenom, [profil] if profil else [])
        n += n_fichiers
        cible = sortie / nom
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_text(propre, encoding="utf-8")
        lignes.append(f"pris : {nom} ({source.stat().st_size} octets, {n} remplacement(s))")

    for nom in JOURNAUX_INSTALLEUR:
        copier(app / "installeur" / nom, f"installeur/{nom}")
    journaux_atlas = sorted((app / "data" / "logs").glob("*.log")) if (app / "data" / "logs").is_dir() else []
    if not journaux_atlas:
        lignes.append("absent : atlas/ (aucun journal d'Atlas)")
    for f in journaux_atlas:
        copier(f, f"atlas/{f.name}")
    inno = [f for f in sorted(temp.glob("Setup Log*.txt")) if re.search(r"\bAtlas", _lire(f))] if temp.is_dir() else []
    if not inno:
        lignes.append("absent : inno/ (aucun journal d'Inno Setup qui parle d'Atlas)")
    for f in inno:
        copier(f, f"inno/{f.name}")
    journaux_ollama = ([f for motif in ("server*.log", "app*.log") for f in sorted(dossier_ollama.glob(motif))]
                       if dossier_ollama.is_dir() else [])
    if not journaux_ollama:
        lignes.append("absent : ollama/ (aucun journal d'Ollama)")
    for f in journaux_ollama:
        copier(f, f"ollama/{f.name}")

    brut = sortie / "precheck_brut.txt"
    try:
        precheck(brut)
    except Exception as e:
        lignes.append(f"diagnostic impossible : {type(e).__name__}")
    if brut.is_file():
        copier(brut, "precheck.txt")
        brut.unlink()
    else:
        lignes.append("absent : precheck.txt")

    (sortie / "RELEVE.txt").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return sortie


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Relevé anonymisé des journaux d'Atlas (clé USB).")
    ap.add_argument("--vers", required=True, help="dossier de la clé USB")
    a = ap.parse_args(argv)
    sortie = relever(ROOT, pathlib.Path(a.vers))
    print(f"Relevé écrit dans {sortie}")
    print((sortie / "RELEVE.txt").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
