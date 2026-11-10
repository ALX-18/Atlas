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
            precheck: Optional[Callable[[pathlib.Path], None]] = None) -> pathlib.Path:
    temp = temp or pathlib.Path(os.environ.get("TEMP", ""))
    dossier_ollama = dossier_ollama or pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Ollama"
    session = os.environ.get("USERNAME", "") if session is None else session
    ordinateur = os.environ.get("COMPUTERNAME", "") if ordinateur is None else ordinateur
    profil = pathlib.Path(os.environ.get("USERPROFILE", "")).name if session == os.environ.get("USERNAME") else ""
    prenom = prenom_regle(app)
    precheck = precheck or precheck_windows(app)

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
        propre, n = anonymiser(_lire(source), session, ordinateur, prenom, [profil] if profil else [])
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
