"""
Sprint Installeur / IN5 — ce que la désinstallation fait avant que Windows retire les fichiers d'Atlas.

    python installeur/desinstaller.py --arreter                 # arrête Atlas s'il tourne (son serveur, sa fenêtre)
    python installeur/desinstaller.py --secrets                 # retire les secrets d'Atlas du coffre de Windows
    python installeur/desinstaller.py --sauvegarder <dossier>   # sauvegarde la mémoire avant de l'effacer
    python installeur/desinstaller.py --effacer-donnees         # efface la mémoire, l'apprentissage, les rappels…

Le résultat (ce qui a été fait, en français) est écrit dans --rapport <fichier> pour que l'installeur le dise.
Ollama et Tesseract ne sont jamais touchés ici : ils peuvent servir à autre chose (l'installeur le dit).
"""

from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREFIXE_SECRETS = "Atlas:"
DONNEES = ("data",)          # la mémoire, l'apprentissage, les rappels, l'index, les journaux d'Atlas


def arreter() -> list[str]:
    """Les processus Python d'ATLAS (ceux de son dossier), et eux seuls."""
    import psutil

    dossier = str(ROOT).lower()
    arretes = []
    for p in psutil.process_iter(["pid", "exe", "name"]):
        try:
            exe = (p.info.get("exe") or "").lower()
            if exe.startswith(dossier) and pathlib.Path(exe).name in ("python.exe", "pythonw.exe") and p.pid != os.getpid():
                p.terminate()
                arretes.append(str(p.pid))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    psutil.wait_procs([psutil.Process(int(x)) for x in arretes if psutil.pid_exists(int(x))], timeout=10)
    return arretes


def retirer_secrets(lister=None, supprimer=None) -> list[str]:
    """Les identifiants génériques « Atlas:… » du Gestionnaire d'identification de Windows (et eux seuls)."""
    if lister is None or supprimer is None:
        import win32cred

        lister = lister or (lambda: [c["TargetName"] for c in (win32cred.CredEnumerate(PREFIXE_SECRETS + "*", 0) or [])])
        supprimer = supprimer or (lambda nom: win32cred.CredDelete(nom, win32cred.CRED_TYPE_GENERIC, 0))
    try:
        noms = [n for n in lister() if n.startswith(PREFIXE_SECRETS)]
    except Exception:
        noms = []                                  # aucun secret : CredEnumerate lève une erreur « introuvable »
    retires = []
    for n in noms:
        try:
            supprimer(n)
            retires.append(n)
        except Exception:
            pass
    return retires


def sauvegarder(dest: pathlib.Path) -> pathlib.Path:
    dest.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "backup_memory.py"), "backup", "--dest", str(dest)],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-500:])
    return dest


def effacer_donnees() -> list[str]:
    effaces = []
    for nom in DONNEES:
        d = ROOT / nom
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
            effaces.append(nom)
    return effaces


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arreter", action="store_true")
    ap.add_argument("--secrets", action="store_true")
    ap.add_argument("--sauvegarder")
    ap.add_argument("--effacer-donnees", action="store_true")
    ap.add_argument("--rapport")
    a = ap.parse_args(argv)
    lignes, code = [], 0
    if a.arreter:
        try:
            n = arreter()
            lignes.append(f"Atlas arrêté ({len(n)} processus)." if n else "Atlas ne tournait pas.")
        except Exception as e:
            lignes.append(f"Atlas n'a pas pu être arrêté ({type(e).__name__}).")
    if a.secrets:
        r = retirer_secrets()
        lignes.append(f"{len(r)} secret(s) d'Atlas retiré(s) du coffre de Windows" + (f" ({', '.join(r)})." if r else "."))
    if a.sauvegarder:
        try:
            lignes.append(f"Mémoire sauvegardée dans {sauvegarder(pathlib.Path(a.sauvegarder))}.")
        except Exception as e:
            lignes.append(f"La sauvegarde a échoué : la mémoire n'est PAS effacée ({e}).")
            a.effacer_donnees, code = False, 1
    if a.effacer_donnees:
        e = effacer_donnees()
        lignes.append("Mémoire, apprentissage et rappels effacés." if e else "Aucune donnée à effacer.")
    if a.rapport:
        pathlib.Path(a.rapport).write_text("\n".join(lignes) + "\n", encoding="utf-8-sig")
    print("\n".join(lignes))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
