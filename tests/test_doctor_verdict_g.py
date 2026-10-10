"""
Sprint G / G5 — doctor.py dit, en une ligne, si une machine peut faire tourner Atlas.

Alexis va installer Atlas sur des PC qu'il ne connaît pas. Le verdict doit être lisible par
un non-informaticien, fondé sur ce qui a été MESURÉ :
  - VRAM : pic 6 674 Mio sur la chaîne complète (qwen2.5:7b + transcription GPU, sprint E) ;
  - RAM : pic 18,7 Go sans Docker, 23,4 Go avec, sur une machine de 24 Go (sprint A, L23) ;
  - disque : ~17 Go installés (mesuré sur la machine d'Alexis, sprint G) ;
  - virtualisation du BIOS nécessaire pour Docker (sprint A) ;
  - sans carte NVIDIA, transcription ~5 s par phrase au lieu de 0,3 s.

Les machines ci-dessous sont simulées : aucun test ne lit le vrai matériel.
"""

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

BIEN = "✅ Atlas tournera bien"
DEGRADE = "⚠️ Atlas tournera, en mode dégradé"
NON = "❌ Atlas ne tournera pas correctement"


def machine(**changes):
    """Une machine confortable ; chaque test en dégrade un aspect."""
    m = {"windows": True, "windows_release": "11", "arch64": True, "ram_gib": 31.8,
         "gpu_name": "NVIDIA GeForce RTX 4060", "vram_mib": 8188, "virtualization": True,
         "disk_free_gib": 120.0}
    m.update(changes)
    return m


def verdict(m):
    import doctor

    return doctor.machine_verdict(m)


def test_g5_machine_confortable():
    niveau, raisons = verdict(machine())
    assert niveau == BIEN, raisons


@pytest.mark.parametrize("changes,niveau,mot", [
    ({"ram_gib": 23.9}, DEGRADE, "mémoire vive"),            # la machine d'Alexis : 98 % mesurés
    ({"ram_gib": 15.8}, DEGRADE, "mémoire vive"),            # 16 Go : le système paginera
    ({"ram_gib": 7.9}, NON, "mémoire vive"),
    ({"gpu_name": None, "vram_mib": None}, DEGRADE, "5 secondes"),
    ({"gpu_name": "NVIDIA GeForce GTX 1650", "vram_mib": 4096}, DEGRADE, "carte graphique"),
    ({"virtualization": False}, DEGRADE, "Docker"),
    ({"disk_free_gib": 12.0}, NON, "disque"),
    ({"arch64": False}, NON, "64 bits"),
    ({"windows": False}, NON, "Windows"),
])
def test_g5_verdict_selon_les_mesures(changes, niveau, mot):
    obtenu, raisons = verdict(machine(**changes))
    assert obtenu == niveau, f"{changes} → {obtenu} ({raisons})"
    assert any(mot.lower() in r.lower() for r in raisons), f"raison absente ({mot}) : {raisons}"


def test_g5_les_raisons_sont_lisibles_par_un_non_informaticien():
    _, raisons = verdict(machine(ram_gib=15.8, gpu_name=None, vram_mib=None, virtualization=False))
    texte = " ".join(raisons)
    for jargon in ("VRAM", "CUDA", "WSL", "Mio", "GiB", "STT", "LLM"):
        assert jargon not in texte, f"jargon « {jargon} » dans : {texte}"


def test_g5_la_pre_verification_tourne_sans_rien_installer():
    """`python -S` : sans site-packages, seule la bibliothèque standard est disponible —
    comme sur le PC d'un proche où Atlas n'est pas encore installé."""
    r = subprocess.run([sys.executable, "-S", str(ROOT / "scripts" / "doctor.py"), "--precheck", "--json"],
                       capture_output=True, text=True, encoding="utf-8", timeout=120, cwd=ROOT)
    assert r.returncode in (0, 1, 2), r.stderr[-800:]
    data = json.loads(r.stdout)
    assert data["verdict"] in (BIEN, DEGRADE, NON), data
    assert isinstance(data["reasons"], list) and data["machine"]["ram_gib"] > 0, data


def test_g5_le_verdict_est_en_tete_du_rapport():
    r = subprocess.run([sys.executable, "-S", str(ROOT / "scripts" / "doctor.py"), "--precheck"],
                       capture_output=True, text=True, encoding="utf-8", timeout=120, cwd=ROOT)
    premiere = next(l for l in r.stdout.splitlines() if l.strip())
    assert any(v in premiere for v in (BIEN, DEGRADE, NON)), f"première ligne : {premiere!r}"
