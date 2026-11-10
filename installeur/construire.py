"""
Sprint Installeur / IN1 — construire l'installeur d'Atlas (sur le PC d'Alexis), en une commande.

    python installeur/construire.py                    # tout : paquet, Python embarqué, verrous, puis Inno Setup
    python installeur/construire.py --paquet-seul      # (tests) seulement le dossier du paquet, sans rien télécharger

Ce qui entre dans l'installeur :
- le code d'Atlas tel qu'il est COMMITÉ (git archive HEAD) — jamais le dossier de travail : ni data/ (mémoire,
  journaux, apprentissage, index), ni la configuration locale d'Alexis, ni secret. Seuls les dossiers de code
  listés dans INCLUS y vont ; `verifier_paquet` le prouve sur le dossier produit (et un test le rejoue) ;
- un Python 3.12 embarqué propre à Atlas (python.org, MD5 publié vérifié, python.exe signé par la Python
  Software Foundation), avec Tkinter (tcltk.msi, signé) et pip (empreinte PyPI) ;
- les verrous des dépendances (versions fixes, empreintes SHA-256 de PyPI), et les quelques bibliothèques que
  PyPI ne publie qu'en sources, construites ici en « roues » (leurs empreintes sont dans le verrou).
Les dépendances elles-mêmes, Ollama, Tesseract et les modèles sont téléchargés PENDANT l'installation.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ICI = pathlib.Path(__file__).resolve().parent
ROOT = ICI.parent
BUILD = ROOT / "build" / "installeur"
PAQUET = BUILD / "paquet"
TELECHARGES = BUILD / "telecharges"
VENV_PY = ROOT / ".venv" / "Scripts" / "python.exe"

PYTHON_VERSION = "3.12.10"
CONSTRUCTION = {
    "python_embarque": {"url": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip",
                        "md5": "fe8ef205f2e9c3ba44d0cf9954e1abd3", "taille": 11133606},
    "tcltk": {"url": f"https://www.python.org/ftp/python/{PYTHON_VERSION}/amd64/tcltk.msi", "signe_par": "Python Software Foundation",
              "taille": 3584000},
    "pip": {"url": "https://files.pythonhosted.org/packages/py3/p/pip/pip-26.3-py3-none-any.whl",
            "sha256": "f3b60b20ffaadd4415ed7957212a38ac63fa4c5fa375bd0f4a797777940fad13", "taille": 1950951},
}

# Ce qui part chez un proche : le code, les réglages par défaut, l'interface, les tests (le banc de non-régression
# les utilise : ce sont des données fictives), les modes par défaut. Rien d'autre.
INCLUS = ("api/", "core/", "core_conversational/", "tools/", "ui/", "desktop/", "config/", "installeur/",
          "scripts/", "tests/", "data/workflows/", "main.py", "requirements.txt", "LICENSE", "README.md")
EXCLUS_FICHIERS = re.compile(r"(^|/)(__pycache__|\.pytest_cache)/|\.pyc$|^installeur/(cache|roues|etat\.json|installation\.log)")
NVIDIA = re.compile(r"^nvidia-", re.I)


# --------------------------------------------------------------------------- #
#  1. Le paquet : le code commité
# --------------------------------------------------------------------------- #

def construire_paquet(dest: pathlib.Path = PAQUET / "atlas", ref: str = "HEAD") -> list[str]:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    archive = subprocess.run(["git", "archive", "--format=tar", ref], cwd=ROOT, capture_output=True, check=True).stdout
    pris = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for membre in tar.getmembers():
            nom = membre.name
            if not membre.isfile() or not nom.startswith(INCLUS) or EXCLUS_FICHIERS.search(nom):
                continue
            cible = dest / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            cible.write_bytes(tar.extractfile(membre).read())
            pris.append(nom)
    # Les réglages installés : ceux du dépôt, envoi des mails en simulation (IN : toujours, chez un proche)
    reglages_f = dest / "config" / "settings.json"
    reglages = json.loads(reglages_f.read_text(encoding="utf-8"))
    reglages.setdefault("mail", {})["envoi"] = "simulation"
    reglages.setdefault("utilisateur", {})["prenom"] = ""        # demandé au premier lancement, chez la personne
    reglages_f.write_text(json.dumps(reglages, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    return pris


# Ce qu'aucun fichier du paquet ne doit contenir (données d'Alexis, chemins de son PC, secrets)
INTERDITS_CHEMINS = re.compile(r"(^|/)(data/(?!workflows/)|\.venv/|venv/|models/|build/|\.git/)|\.(db|sqlite3?|jsonl|log|"
                               r"bak|onnx|bin|traineddata)$|(^|/)chromadb/", re.I)
# Les marqueurs sont assemblés par morceaux : ce fichier (qui part dans le paquet) ne les contient pas en clair.
_ALEXIS = b"al" + b"exis"
INTERDITS_CONTENU = [
    (re.compile(b"all" + b"exis" + b"redaud@", re.I), "l'adresse personnelle d'Alexis"),
    (re.compile(rb"C:(?:\\\\?|/)Users(?:\\\\?|/)" + _ALEXIS + rb"\b", re.I), "un chemin du PC d'Alexis"),
    (re.compile(rb"calendar\.google\.com/calendar/ical/[^\"'\s]*private-(?!0123456789abcdef)[0-9a-f]{6}", re.I),
     "une adresse iCal privée"),
]
REGLAGES_INTERDITS = [(re.compile(rb"\"envoi\"\s*:\s*\"reel\""), "l'envoi réel des mails"),
                      (re.compile(rb"\"prenom\"\s*:\s*\"[^\"]+\""), "un prénom")]


def verifier_paquet(dossier: pathlib.Path) -> list[str]:
    """Les fautes (vide : le paquet ne contient rien d'Alexis)."""
    fautes = []
    for f in dossier.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(dossier).as_posix()
        if INTERDITS_CHEMINS.search(rel) and not rel.startswith(("python/", "atlas/data/workflows/")):
            fautes.append(f"fichier interdit : {rel}")
            continue
        if rel.startswith("python/") or f.suffix.lower() in (".whl", ".png", ".ico", ".exe", ".dll", ".pyd", ".zip"):
            continue
        contenu = f.read_bytes()
        for motif, quoi in INTERDITS_CONTENU + (REGLAGES_INTERDITS if rel.startswith("atlas/config/") else []):
            if motif.search(contenu):
                fautes.append(f"{rel} contient {quoi}")
    if (dossier / "atlas" / "data").exists():
        en_trop = [p.relative_to(dossier).as_posix() for p in (dossier / "atlas" / "data").rglob("*")
                   if p.is_file() and not p.relative_to(dossier / "atlas" / "data").as_posix().startswith("workflows/")]
        fautes += [f"donnée d'Atlas dans le paquet : {x}" for x in en_trop]
    if (dossier / "python").exists():
        fautes += [f"bibliothèque C++ de Microsoft absente du Python embarqué : {n}" for n in RUNTIME_VC
                   if not (dossier / "python" / n).exists()]
    return fautes


# --------------------------------------------------------------------------- #
#  2. Le Python embarqué
# --------------------------------------------------------------------------- #

def _empreinte(chemin: pathlib.Path, algo: str) -> str:
    h = hashlib.new(algo)
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _telecharger(cle: str) -> pathlib.Path:
    src = CONSTRUCTION[cle]
    TELECHARGES.mkdir(parents=True, exist_ok=True)
    f = TELECHARGES / src["url"].rsplit("/", 1)[1]
    if not f.exists():
        print(f"  téléchargement : {src['url']} ({src['taille'] / 1e6:.1f} Mo)", flush=True)
        with urllib.request.urlopen(src["url"], timeout=120) as r, open(f, "wb") as out:
            shutil.copyfileobj(r, out)
    if "md5" in src and _empreinte(f, "md5") != src["md5"]:
        raise SystemExit(f"{f.name} : MD5 différent de celui publié par python.org")
    if "sha256" in src and _empreinte(f, "sha256") != src["sha256"]:
        raise SystemExit(f"{f.name} : SHA-256 différent de celui publié")
    if "signe_par" in src:
        verifier_signature(f, src["signe_par"])
    return f


def verifier_signature(f: pathlib.Path, editeur: str) -> None:
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"$s = Get-AuthenticodeSignature -LiteralPath '{f}'; \"$($s.Status)|$($s.SignerCertificate.Subject)\""],
                       capture_output=True, text=True)
    etat, _, sujet = r.stdout.strip().partition("|")
    if etat != "Valid" or editeur not in sujet:
        raise SystemExit(f"{f.name} : signature invalide ou d'un autre éditeur ({etat}, {sujet})")


# La bibliothèque C++ de Microsoft (« Visual C++ Redistributable »). onnxruntime (mot d'éveil, mémoire e5) importe
# MSVCP140.dll et MSVCP140_1.dll, torch MSVCP140_ATOMIC_WAIT.dll : absentes d'un Windows neuf (Sandbox, 10/11 :
# « DLL load failed »). Le Python embarqué n'apporte que vcruntime140. Elles sont copiées à côté de python.exe
# (déploiement local, prévu par Microsoft), depuis le System32 du PC qui construit : signature Microsoft vérifiée,
# version au moins égale à celle du Python embarqué, toutes à la même version (vcruntime140 compris).
RUNTIME_VC = ("vcruntime140.dll", "vcruntime140_1.dll", "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll",
              "msvcp140_atomic_wait.dll", "msvcp140_codecvt_ids.dll", "concrt140.dll")


def version_fichier(f: pathlib.Path) -> tuple:
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        f"$v = (Get-Item -LiteralPath '{f}').VersionInfo; "
                        "\"$($v.FileMajorPart).$($v.FileMinorPart).$($v.FileBuildPart).$($v.FilePrivatePart)\""],
                       capture_output=True, text=True)
    return tuple(int(x) for x in r.stdout.strip().split("."))


def copier_runtime_vc(dest: pathlib.Path, source: pathlib.Path | None = None) -> dict:
    source = source or pathlib.Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"
    manquent = [n for n in RUNTIME_VC if not (source / n).exists()]
    if manquent:
        raise SystemExit("bibliothèque C++ de Microsoft absente de ce PC (" + ", ".join(manquent) + ") : installer "
                         "« Microsoft Visual C++ Redistributable » (x64) avant de construire l'installeur")
    minimum = version_fichier(dest / "vcruntime140.dll")
    versions = {}
    for n in RUNTIME_VC:
        verifier_signature(source / n, "Microsoft Corporation")
        versions[n] = version_fichier(source / n)
        if versions[n] < minimum:
            raise SystemExit(f"{n} {'.'.join(map(str, versions[n]))} plus ancien que le vcruntime140 du Python "
                             f"embarqué ({'.'.join(map(str, minimum))}) : mettre à jour le Visual C++ Redistributable")
    if len(set(versions.values())) != 1:
        raise SystemExit(f"bibliothèque C++ de Microsoft à des versions mélangées : {versions}")
    for n in RUNTIME_VC:
        shutil.copy2(source / n, dest / n)
    v = ".".join(map(str, versions[RUNTIME_VC[0]]))
    print(f"  bibliothèque C++ de Microsoft : {len(RUNTIME_VC)} fichiers, version {v}")
    return {"runtime_vc": v}


PTH = """python312.zip
.
Lib
Lib\\site-packages
..
import site
"""


def construire_python(dest: pathlib.Path = PAQUET / "python") -> dict:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(_telecharger("python_embarque")) as z:
        z.extractall(dest)
    verifier_signature(dest / "python.exe", "Python Software Foundation")
    (dest / "python312._pth").write_text(PTH, encoding="ascii")
    runtime = copier_runtime_vc(dest)
    # Tkinter : extrait de tcltk.msi (installation « administrative » : des fichiers, rien d'enregistré dans Windows)
    msi = _telecharger("tcltk")
    extrait = TELECHARGES / "tcltk"
    shutil.rmtree(extrait, ignore_errors=True)
    r = subprocess.run(["msiexec", "/a", str(msi), "/qn", f"TARGETDIR={extrait}"], timeout=300)
    if r.returncode != 0:
        raise SystemExit(f"extraction de tcltk.msi impossible (code {r.returncode})")
    for nom in ("_tkinter.pyd", "tcl86t.dll", "tk86t.dll", "zlib1.dll"):
        for cand in extrait.rglob(nom):
            shutil.copy2(cand, dest / nom)
            break
    shutil.copytree(next(extrait.rglob("tkinter")), dest / "Lib" / "tkinter", dirs_exist_ok=True)
    shutil.copytree(extrait / "tcl", dest / "tcl", dirs_exist_ok=True)
    # pip, installé dans le Python embarqué depuis sa roue (empreinte PyPI vérifiée)
    roue = _telecharger("pip")
    # pip refuse de s'installer lui-même depuis sa roue ; une roue est une archive : on l'extrait à sa place
    site = dest / "Lib" / "site-packages"
    site.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(roue) as z:
        z.extractall(site)
    essai = subprocess.run([str(dest / "python.exe"), "-c", "import tkinter, pip, sys; r = tkinter.Tk(); r.destroy(); "
                            "print(sys.version.split()[0], "
                            "tkinter.TkVersion, pip.__version__)"], capture_output=True, text=True)
    if essai.returncode != 0:
        raise SystemExit(f"le Python embarqué ne marche pas : {essai.stderr[-400:]}")
    print(f"  Python embarqué : {essai.stdout.strip()}")
    return {"python": essai.stdout.strip(), **runtime}


# --------------------------------------------------------------------------- #
#  3. Les verrous des dépendances
# --------------------------------------------------------------------------- #

def construire_verrous(dest: pathlib.Path = PAQUET / "atlas" / "installeur") -> dict:
    """pip résout requirements.txt (sans rien installer) et rend chaque fichier avec son empreinte PyPI."""
    rapport = BUILD / "resolution.json"
    # Les versions TESTÉES : celles du .venv où la suite passe (torch « 2.12.1+cpu » → torch 2.12.1 de PyPI)
    gel = subprocess.run([str(VENV_PY), "-m", "pip", "list", "--format=freeze", "--disable-pip-version-check"],
                         capture_output=True, text=True, check=True).stdout
    contraintes = BUILD / "contraintes_venv.txt"
    contraintes.write_text("\n".join(re.sub(r"\+[\w.]+$", "", l) for l in gel.splitlines() if "==" in l) + "\n",
                           encoding="utf-8")
    subprocess.run([str(VENV_PY), "-m", "pip", "install", "--dry-run", "--ignore-installed", "--quiet",
                    "--disable-pip-version-check", "--report", str(rapport), "-r", str(ROOT / "requirements.txt"),
                    "-c", str(contraintes)], check=True)
    installes = json.loads(rapport.read_text(encoding="utf-8"))["install"]
    roues = dest / "roues"
    roues.mkdir(parents=True, exist_ok=True)
    base, nvidia, tailles = [], [], {"base": 0, "nvidia": 0}
    for x in installes:
        nom, version = x["metadata"]["name"], x["metadata"]["version"]
        info = x["download_info"]
        url, h = info["url"], info["archive_info"]["hashes"]["sha256"]
        if not url.endswith(".whl"):
            # PyPI ne publie que les sources : la roue est construite ici, depuis ces sources vérifiées
            subprocess.run([str(VENV_PY), "-m", "pip", "wheel", "--no-deps", "--quiet", "-w", str(roues),
                            f"{nom}=={version}", "--no-binary", nom], check=True)
            roue = next(roues.glob(f"{re.sub(r'[-.]', '_', nom)}-{version}-*.whl"), None) or \
                next(p for p in roues.glob("*.whl") if p.name.lower().startswith(re.sub(r"[-.]", "_", nom).lower()))
            h, taille = _empreinte(roue, "sha256"), roue.stat().st_size
        else:
            taille = _taille_distante(url)
        ligne = f"{nom}=={version} --hash=sha256:{h}"
        (nvidia if NVIDIA.match(nom) else base).append(ligne)
        tailles["nvidia" if NVIDIA.match(nom) else "base"] += taille
    entete = "# Généré par installeur/construire.py — versions fixes, empreintes SHA-256 (pip --require-hashes).\n"
    (dest / "requirements-verrou.txt").write_text(entete + "\n".join(sorted(base, key=str.lower)) + "\n", encoding="utf-8")
    (dest / "requirements-nvidia-verrou.txt").write_text(entete + "\n".join(sorted(nvidia, key=str.lower)) + "\n",
                                                         encoding="utf-8")
    return {"paquets": len(base), "paquets_nvidia": len(nvidia), "tailles": tailles}


def _taille_distante(url: str) -> int:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=30) as r:
            return int(r.headers.get("Content-Length") or 0)
    except Exception:
        return 0


# --------------------------------------------------------------------------- #
#  4. Inno Setup
# --------------------------------------------------------------------------- #

def iscc() -> pathlib.Path:
    for d in (pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 7",
              pathlib.Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 7",
              pathlib.Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 7",
              pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6",
              pathlib.Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6"):
        if (d / "ISCC.exe").exists():
            return d / "ISCC.exe"
    raise SystemExit("Inno Setup (ISCC.exe) introuvable.")


def ecrire_tailles(info: dict) -> None:
    sources = json.loads((ICI / "sources.json").read_text(encoding="utf-8"))
    modeles = json.loads((ROOT / "config" / "modeles.json").read_text(encoding="utf-8"))["modeles"]
    t = info["tailles"]
    voix = 1.5e9       # e5 ONNX (1,1 Go), voix Piper (63 Mo), transcription (145 Mo), mot d'éveil
    base = t["base"] + sources["ollama"]["taille"] + sources["tesseract"]["taille"] + voix
    lignes = [f"#define TailleBaseMo {round(base / 1e6)}",
              f"#define TailleNvidiaMo {round(t['nvidia'] / 1e6)}",
              f"#define TailleQwenMo {round(modeles['qwen2.5:7b']['taille'] / 1e6)}",
              f"#define TailleGemmaMo {round(modeles['gemma4:e4b']['taille'] / 1e6)}"]
    (PAQUET / "tailles.iss").write_text("\n".join(lignes) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--paquet-seul", action="store_true")
    ap.add_argument("--ref", default="HEAD", help="le commit dont le code part dans l'installeur")
    a = ap.parse_args(argv)
    print("1/4 Le paquet (code commité)…", flush=True)
    pris = construire_paquet(ref=a.ref)
    print(f"  {len(pris)} fichiers")
    if a.paquet_seul:
        fautes = verifier_paquet(PAQUET)
        print("\n".join(fautes) or "  paquet propre")
        return 1 if fautes else 0
    print("2/4 Le Python embarqué…", flush=True)
    construire_python()
    print("3/4 Les verrous des dépendances…", flush=True)
    info = construire_verrous()
    print(f"  {info}")
    ecrire_tailles(info)
    fautes = verifier_paquet(PAQUET)
    if fautes:
        print("Paquet refusé :\n" + "\n".join(fautes))
        return 1
    print("4/4 Inno Setup…", flush=True)
    r = subprocess.run([str(iscc()), f"/DPaquet={PAQUET}", f"/O{BUILD}", str(ICI / "atlas.iss")])
    if r.returncode == 0:
        print(f"Installeur : {BUILD / 'AtlasSetup.exe'} ({(BUILD / 'AtlasSetup.exe').stat().st_size / 1e6:.1f} Mo)")
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
