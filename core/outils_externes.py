"""
Sprint Installeur — les programmes externes qu'Atlas utilise, trouvés là où l'installeur les a mis.

Tesseract (lecture du texte à l'écran) est cherché par pytesseract dans le PATH. Chez un proche, l'installeur
officiel le met dans « Program Files » ou dans le profil, sans toujours toucher au PATH : Atlas ajoute ces
dossiers à SON PATH (celui de son processus, rien n'est changé dans Windows). Si le français a dû être rangé
dans un dossier d'Atlas (Tesseract installé pour toute la machine, dossier protégé), TESSDATA_PREFIX y pointe.
"""

from __future__ import annotations

import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent


def preparer() -> dict:
    ajoute = []
    if not shutil.which("tesseract"):
        for d in (pathlib.Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR",
                  pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR"):
            if (d / "tesseract.exe").exists():
                os.environ["PATH"] = f"{d}{os.pathsep}{os.environ.get('PATH', '')}"
                ajoute.append(str(d))
                break
    perso = ROOT / "models" / "tessdata"
    if (perso / "fra.traineddata").exists() and not os.environ.get("TESSDATA_PREFIX"):
        os.environ["TESSDATA_PREFIX"] = str(perso)
    return {"path_ajoute": ajoute, "tessdata": os.environ.get("TESSDATA_PREFIX")}
