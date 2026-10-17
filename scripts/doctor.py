"""
Sprint A — Diagnostic d'installation Atlas (`doctor`).

Vérifie chaque dépendance d'Atlas et affiche, pour chaque problème, une
correction actionnable. Détecte le GPU NVIDIA et la VRAM, puis recommande une
taille de modèle de langage / STT adaptée.

Approche inspirée de `scripts/doctor.py` du projet sosoj92/jarvis-assistant-vocal
(licence MIT, https://github.com/sosoj92/jarvis-assistant-vocal) : diagnostic
matériel + recommandation de modèle selon la VRAM avant installation.
Réécrit pour la pile Atlas (Ollama, Tesseract, EasyOCR, ChromaDB, SearXNG/ddgs,
OpenWakeWord, faster-whisper, Piper) — aucun code repris.

Ce script est en lecture seule : il ne modifie ni la configuration, ni les
données, ni l'environnement Python.

Usage:
    python scripts/doctor.py            # rapport lisible
    python scripts/doctor.py --json     # rapport machine (pour un futur installeur)
    python scripts/doctor.py --precheck # AVANT installation : verdict matériel, Python nu suffit
    python scripts/doctor.py --composants        # chaque composant : présent, version, matériel, bascule
    python scripts/doctor.py --composants --json

Code de retour:
    0 — aucun composant critique manquant (des avertissements peuvent subsister)
    1 — au moins un composant critique manquant
"""

from __future__ import annotations

import argparse
import importlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "config" / "settings.json"

CRITICAL = "CRITIQUE"
WARNING = "AVERTISSEMENT"
INFO = "INFO"


@dataclass
class Check:
    section: str
    name: str
    ok: bool
    severity: str  # sévérité appliquée si ok=False
    detail: str = ""
    fix: str = ""
    data: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
#  Utilitaires
# --------------------------------------------------------------------------- #

def _run(cmd: list[str], timeout: float = 10.0) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                              encoding="utf-8", errors="replace")
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except FileNotFoundError:
        return 127, "introuvable"
    except subprocess.TimeoutExpired:
        return 124, f"délai dépassé ({timeout:.0f}s)"
    except Exception as e:  # pragma: no cover - défensif
        return 1, str(e)


def _http_get(url: str, timeout: float = 3.0) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 400, resp.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(getattr(e, "reason", e))


def _load_settings() -> dict | None:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _pkg_version(dist: str) -> str | None:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return None


# --------------------------------------------------------------------------- #
#  Vérifications
# --------------------------------------------------------------------------- #

def check_python() -> list[Check]:
    v = sys.version_info
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    return [
        Check("Python", "Version 3.12", v[:2] == (3, 12), CRITICAL,
              f"Python {platform.python_version()} ({sys.executable})",
              "Installer Python 3.12 (python.org) puis recréer le venv : "
              "py -3.12 -m venv .venv"),
        Check("Python", "Environnement virtuel actif", in_venv, WARNING,
              f"sys.prefix={sys.prefix}",
              "Activer le venv : .venv\\Scripts\\activate (ou lancer .venv\\Scripts\\python.exe)"),
    ]


# (nom de distribution pip, module à importer, sévérité si absent, rôle)
PACKAGES: list[tuple[str, str, str, str]] = [
    ("fastapi", "fastapi", CRITICAL, "API"),
    ("uvicorn", "uvicorn", CRITICAL, "serveur API"),
    ("httpx", "httpx", CRITICAL, "client Ollama/Chroma"),
    ("pydantic", "pydantic", CRITICAL, "schémas API"),
    ("psutil", "psutil", CRITICAL, "processus / diagnostics"),
    ("requests", "requests", CRITICAL, "HTTP (grounding, scripts)"),
    ("pyyaml", "yaml", CRITICAL, "workflows"),
    ("apscheduler", "apscheduler", CRITICAL, "planificateur"),
    ("pyautogui", "pyautogui", CRITICAL, "clics / clavier"),
    ("pygetwindow", "pygetwindow", CRITICAL, "fenêtres"),
    ("pyperclip", "pyperclip", CRITICAL, "presse-papiers"),
    ("pywinauto", "pywinauto", CRITICAL, "grounding UIA"),
    ("pywin32", "win32api", CRITICAL, "API Windows"),
    ("comtypes", "comtypes", CRITICAL, "COM Windows"),
    ("pycaw", "pycaw", WARNING, "contrôle du volume"),
    ("plyer", "plyer", WARNING, "notifications"),
    ("websockets", "websockets", CRITICAL, "browser bridge"),
    ("pytesseract", "pytesseract", CRITICAL, "OCR couche 1"),
    ("easyocr", "easyocr", WARNING, "OCR couche 2, repli de Tesseract (processus à part)"),
    ("chromadb", "chromadb", CRITICAL, "mémoire long terme"),
    # Sprint Check-up / CK7 : les embeddings tournent sur ONNX Runtime ; sentence-transformers
    # (et torch) n'est que le REPLI si le modèle ONNX manque — jamais chargé sinon (prouvé en CK1).
    ("sentence-transformers", "sentence_transformers", WARNING, "repli des embeddings si le modèle ONNX manque"),
    ("beautifulsoup4", "bs4", WARNING, "lecture web"),
    ("lxml", "lxml", WARNING, "lecture web"),
    ("ddgs", "ddgs", WARNING, "recherche web (DuckDuckGo)"),
    ("playwright", "playwright", WARNING, "navigateur piloté"),
    ("numpy", "numpy", CRITICAL, "audio / OCR"),
    ("sounddevice", "sounddevice", WARNING, "micro / haut-parleur"),
    ("openwakeword", "openwakeword", WARNING, "mot d'éveil"),
    ("faster-whisper", "faster_whisper", WARNING, "STT"),
    ("piper-tts", "piper", WARNING, "TTS"),
    ("onnxruntime", "onnxruntime", CRITICAL, "embeddings de la mémoire, mot d'éveil, voix Piper"),
    ("pystray", "pystray", WARNING, "icône systray"),
    ("pypdf", "pypdf", WARNING, "ingestion de documents PDF dans la mémoire"),
    ("pytest", "pytest", INFO, "tests (requirements-dev.txt)"),
    ("pytest-asyncio", "pytest_asyncio", INFO, "tests async (requirements-dev.txt)"),
]


def check_packages(voice_enabled: bool) -> list[Check]:
    voice_mods = {"sounddevice", "openwakeword", "faster_whisper", "piper", "onnxruntime", "pystray"}
    out = []
    for dist, module, severity, role in PACKAGES:
        if module in voice_mods and voice_enabled:
            severity = CRITICAL
        version = _pkg_version(dist)
        ok = version is not None
        detail = f"{dist} {version}" if ok else f"{dist} non installé"
        if ok:
            # L'import réel détecte les DLL manquantes (pywin32, onnxruntime...).
            try:
                importlib.import_module(module)
            except Exception as e:
                ok = False
                detail = f"{dist} {version} installé mais import '{module}' en échec : {e}"[:300]
        out.append(Check("Paquets Python", f"{dist} — {role}", ok, severity, detail,
                         f"pip install {dist}" if version is None
                         else f"pip install --force-reinstall {dist}"))
    return out


def check_project_layout(settings: dict | None) -> list[Check]:
    checks = [
        Check("Projet", "config/settings.json lisible", settings is not None, CRITICAL,
              str(SETTINGS_PATH), "Restaurer le fichier depuis Git : git checkout -- config/settings.json"),
        # main.py ouvre logs/atlas.log à l'import sans créer le dossier (non suivi par Git).
        Check("Projet", "Dossier logs/ présent", (ROOT / "logs").is_dir(), CRITICAL,
              str(ROOT / "logs"),
              "Créer le dossier : mkdir logs  (sinon main.py plante à l'import : FileNotFoundError)"),
        Check("Projet", "Dossier data/ présent", (ROOT / "data").is_dir(), WARNING,
              str(ROOT / "data"), "Créer le dossier : mkdir data"),
    ]
    if settings:
        for key in ("ollama", "server", "memory", "web", "voice", "grounding"):
            checks.append(Check("Projet", f"Section '{key}' dans settings.json", key in settings,
                                CRITICAL if key in ("ollama", "server") else WARNING,
                                "présente" if key in settings else "absente",
                                "Comparer avec la version Git de config/settings.json"))
    return checks


def check_tesseract() -> list[Check]:
    exe = shutil.which("tesseract")
    default = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    fix_install = ("Installer Tesseract 5.x (UB-Mannheim) en cochant 'Additional language data → French', "
                   "puis ajouter C:\\Program Files\\Tesseract-OCR au PATH système et ouvrir un NOUVEAU terminal")
    if not exe:
        detail = "absent du PATH"
        if default.exists():
            detail += f" (mais présent dans {default.parent} — PATH non configuré)"
        return [Check("OCR", "Tesseract dans le PATH", False, CRITICAL, detail,
                      fix_install + ". Sans lui : ~90 s de latence sur 'clique sur X' (épisode v5.2).")]
    code, out = _run([exe, "--version"])
    version = out.strip().splitlines()[0] if out.strip() else "?"
    checks = [Check("OCR", "Tesseract dans le PATH", code == 0, CRITICAL, f"{exe} — {version}", fix_install)]
    code, out = _run([exe, "--list-langs"])
    langs = [l.strip() for l in out.strip().splitlines()[1:] if l.strip()] if code == 0 else []
    checks.append(Check("OCR", "Tesseract langues fra + eng", {"fra", "eng"} <= set(langs), CRITICAL,
                        f"langues : {', '.join(langs) or 'aucune'}",
                        "Relancer l'installeur Tesseract et cocher French, ou copier fra.traineddata "
                        "dans C:\\Program Files\\Tesseract-OCR\\tessdata"))
    try:
        import pytesseract
        v = str(pytesseract.get_tesseract_version())
        checks.append(Check("OCR", "pytesseract trouve le binaire", True, CRITICAL, f"version {v}"))
    except Exception as e:
        checks.append(Check("OCR", "pytesseract trouve le binaire", False, CRITICAL, str(e)[:200],
                            "Vérifier le PATH du processus Python (redémarrer le terminal / l'IDE)"))
    return checks


def check_playwright() -> list[Check]:
    if _pkg_version("playwright") is None:
        return []
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            exe = Path(p.chromium.executable_path)
        ok, detail = exe.is_file(), str(exe)
    except Exception as e:
        ok, detail = False, str(e)[:200]
    return [Check("Web", "Navigateur Chromium de Playwright", ok, WARNING, detail,
                  "python -m playwright install chromium")]


def check_easyocr_models() -> list[Check]:
    model_dir = Path.home() / ".EasyOCR" / "model"
    files = sorted(p.name for p in model_dir.glob("*.pth")) if model_dir.is_dir() else []
    return [Check("OCR", "Modèles EasyOCR en cache", bool(files), WARNING,
                  f"{model_dir} : {', '.join(files) or 'vide'}",
                  "Premier appel EasyOCR = téléchargement (~100 Mo) : "
                  "python -c \"import easyocr; easyocr.Reader(['fr','en'])\"")]


# Pré-beta / PB4 — version de référence : Ollama s'est mis à jour seul en 0.40.3 (12/10/2026),
# version avec laquelle les mesures du sprint Dépôt + Ollama ont été faites.
OLLAMA_REFERENCE_VERSION = "0.40.4"
_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _ollama_listen_addresses(port: int = 11434) -> list[str]:
    """Adresses sur lesquelles un processus écoute le port d'Ollama."""
    try:
        import psutil

        return sorted({c.laddr.ip for c in psutil.net_connections(kind="inet")
                       if c.status == psutil.CONN_LISTEN and c.laddr and c.laddr.port == port})
    except Exception:
        code, out = _run(["netstat", "-ano", "-p", "TCP"])
        addrs = set()
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3].upper().startswith("LISTEN") and parts[1].endswith(f":{port}"):
                addrs.add(parts[1].rsplit(":", 1)[0].strip("[]"))
        return sorted(addrs)


def ollama_exposure_check(addresses: list[str]) -> Check:
    """Ollama doit n'écouter que sur la machine : 0.0.0.0, « :: » ou une adresse du réseau
    l'ouvrent à tout appareil du réseau local, sans mot de passe."""
    exposed = [a for a in addresses if a not in _LOOPBACK]
    return Check("Ollama", "Ollama n'écoute pas sur le réseau", not exposed, WARNING,
                 f"écoute sur : {', '.join(addresses) or 'rien (Ollama arrêté ?)'}",
                 "Dans l'application Ollama : Settings → désactiver « Expose Ollama to the network ». "
                 "Si la variable d'environnement OLLAMA_HOST vaut 0.0.0.0, la retirer. "
                 "Atlas n'a besoin que de 127.0.0.1:11434.")


def _mineure(version: str | None) -> str | None:
    morceaux = (version or "").split(".")
    return ".".join(morceaux[:2]) if len(morceaux) >= 2 else None


def ollama_version_check(version: str | None) -> Check:
    """Sprint Apprentissage 1 (décision du superviseur) : Ollama se met à jour seul ; une version
    de même mineure (0.40.x) est acceptée, seul un changement de mineure est signalé."""
    ref = _mineure(OLLAMA_REFERENCE_VERSION)
    return Check("Ollama", f"Version de référence ({ref}.x)", version is not None and _mineure(version) == ref,
                 WARNING, f"version installée : {version or 'inconnue'} ; référence : {ref}.x "
                          f"(mesurée en {OLLAMA_REFERENCE_VERSION})",
                 f"Atlas a été vérifié avec Ollama {ref}.x. Une autre version mineure marche probablement, "
                 "mais n'a pas été mesurée.")


def check_ollama(settings: dict | None) -> list[Check]:
    cfg = (settings or {}).get("ollama", {})
    base = cfg.get("base_url", "http://127.0.0.1:11434").rstrip("/")
    model = cfg.get("model", "?")
    checks = []
    exe = shutil.which("ollama")
    checks.append(Check("Ollama", "Binaire ollama", exe is not None, WARNING, exe or "absent du PATH",
                        "Installer Ollama : https://ollama.com/download"))
    ok, body = _http_get(f"{base}/api/tags")
    checks.append(Check("Ollama", f"Serveur joignable ({base})", ok, CRITICAL,
                        "répond" if ok else body,
                        "Lancer Ollama (icône systray) ou 'ollama serve'."))
    models: dict[str, int] = {}
    if ok:
        try:
            models = {m["name"]: int(m.get("size", 0)) for m in json.loads(body_full(f"{base}/api/tags"))["models"]}
        except Exception:
            models = {}
        present = model in models
        checks.append(Check("Ollama", f"Modèle configuré '{model}' présent", present, CRITICAL,
                            f"modèles locaux : {', '.join(sorted(models)) or 'aucun'}",
                            f"ollama pull {model}",
                            data={"models": models}))
        version = None
        ok_v, body_v = _http_get(f"{base}/api/version")
        if ok_v:
            try:
                version = json.loads(body_v).get("version")
            except Exception:
                version = None
        checks.append(ollama_version_check(version))
    checks.append(ollama_exposure_check(_ollama_listen_addresses()))
    return checks


def body_full(url: str, timeout: float = 5.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def check_memory(settings: dict | None) -> list[Check]:
    """Sans Docker (SD4) : la mémoire est un dossier ; on vérifie où il est et la place libre."""
    mem = (settings or {}).get("memory", {})
    folder = ROOT / mem.get("chroma_path", "data/chromadb")
    exists = (folder / "chroma.sqlite3").exists()
    checks = [Check("Mémoire", "Dossier de la mémoire", True, INFO,
                    f"{folder} — {'présent' if exists else 'absent : créé au premier démarrage d’Atlas'}")]
    probe = folder if folder.exists() else folder.parent
    try:
        free = shutil.disk_usage(probe).free / 1024 ** 3
    except OSError:
        free = 0.0
    checks.append(Check("Mémoire", "Place libre pour la mémoire (2 Go au moins)", free >= 2.0, WARNING,
                        f"{free:.1f} Go libres sur le disque de {probe}",
                        "Libérer de la place : la mémoire grandit à chaque échange, et sa sauvegarde "
                        "en fait une copie complète."))
    ddgs_ok = _pkg_version("ddgs") is not None
    checks.append(Check("Web", "Recherche web (DuckDuckGo)", ddgs_ok, WARNING,
                        "paquet ddgs présent" if ddgs_ok else "paquet ddgs absent",
                        "pip install -r requirements.txt"))
    return checks


def detect_gpu() -> tuple[list[Check], dict]:
    info: dict = {}
    exe = shutil.which("nvidia-smi")
    if not exe:
        return [Check("GPU", "GPU NVIDIA (nvidia-smi)", False, WARNING, "nvidia-smi introuvable",
                      "Installer le pilote NVIDIA ; sinon régler voice.stt_device=cpu")], info
    code, out = _run([exe, "--query-gpu=name,memory.total,memory.used,memory.free,driver_version,temperature.gpu",
                      "--format=csv,noheader,nounits"])
    if code != 0 or not out.strip():
        return [Check("GPU", "GPU NVIDIA (nvidia-smi)", False, WARNING, out.strip()[:200],
                      "Réinstaller le pilote NVIDIA")], info
    parts = [p.strip() for p in out.strip().splitlines()[0].split(",")]
    name, total, used, free, driver, temp = (parts + [""] * 6)[:6]
    info = {"name": name, "vram_total_mib": int(total), "vram_used_mib": int(used),
            "vram_free_mib": int(free), "driver": driver, "temperature_c": temp}
    checks = [Check("GPU", "GPU NVIDIA", True, WARNING,
                    f"{name} — VRAM {total} Mio (utilisée {used}, libre {free}) — pilote {driver} — {temp}°C",
                    data=info)]

    # Les briques GPU d'Atlas ont chacune leur runtime : on vérifie les trois.
    try:
        import torch
        cuda = bool(torch.cuda.is_available())
        detail = f"torch {torch.__version__} (CUDA build={torch.version.cuda})"
        checks.append(Check("GPU", "torch voit le GPU (EasyOCR)", cuda, WARNING, detail,
                            "torch est une build CPU : EasyOCR tourne sur CPU (choix en cours, rapport "
                            "Check-up §CK5) "
                            "(la transcription n'est pas concernée : elle passe par CTranslate2, vérifié "
                            "juste en dessous). Build CUDA : "
                            "pip install torch --index-url https://download.pytorch.org/whl/cu128 "
                            "(RTX 50xx : CUDA 12.8 minimum)"))
    except Exception as e:
        checks.append(Check("GPU", "torch voit le GPU (EasyOCR)", False, WARNING, str(e)[:200]))
    try:
        import ctranslate2
        n = ctranslate2.get_cuda_device_count()
        checks.append(Check("GPU", "CTranslate2 voit le GPU (faster-whisper)", n > 0, WARNING,
                            f"ctranslate2 {ctranslate2.__version__} — {n} périphérique(s) CUDA",
                            "Régler voice.stt_device=cpu, ou installer cuBLAS 12 / cuDNN 9"))
    except Exception as e:
        checks.append(Check("GPU", "CTranslate2 voit le GPU (faster-whisper)", False, WARNING, str(e)[:200]))
    if os.name == "nt":
        # CTranslate2 voit le GPU même sans cuBLAS, mais chaque transcription échoue alors
        # (« cublas64_12.dll is not found ») : on tente le chargement réel de la DLL.
        import ctypes
        # Sprint G : déclarer d'abord les DLL des paquets pip nvidia-*, comme Atlas le fait
        # au démarrage (core/voice_engine.ensure_cuda_libraries). Sans cela, doctor concluait
        # « installation incomplète » sur une machine où la transcription tourne sur GPU.
        pip_dirs: list[str] = []
        try:
            import nvidia
            for base in getattr(nvidia, "__path__", []):
                pip_dirs += [str(d) for d in Path(base).glob("*/bin") if any(d.glob("*.dll"))]
        except Exception:
            pass
        for d in pip_dirs:
            os.environ["PATH"] = d + os.pathsep + os.environ.get("PATH", "")
            try:
                os.add_dll_directory(d)
            except Exception:
                pass
        try:
            ctypes.WinDLL("cublas64_12.dll")
            ok, detail = True, ("cublas64_12.dll chargeable" +
                                (" (paquets pip nvidia-*, déclarés par Atlas au démarrage)" if pip_dirs else ""))
        except OSError:
            ok, detail = False, "cublas64_12.dll introuvable (PATH et paquets pip nvidia-*) : le STT sur GPU échouera"
        voice = (_load_settings() or {}).get("voice", {})
        needed = voice.get("enabled") and voice.get("stt_device") == "cuda"
        checks.append(Check("GPU", "cuBLAS 12 pour le STT GPU", ok, CRITICAL if needed else WARNING, detail,
                            "Installer CUDA Toolkit 12.x ou 'pip install nvidia-cublas-cu12' (dossier bin dans le PATH), "
                            "ou régler voice.stt_device=cpu"))
    try:
        import onnxruntime as ort
        prov = ort.get_available_providers()
        checks.append(Check("GPU", "onnxruntime (wake word, Piper)", True, INFO,
                            f"providers : {', '.join(prov)} (CPU suffit pour ces modèles)"))
    except Exception as e:
        checks.append(Check("GPU", "onnxruntime (wake word, Piper)", False, WARNING, str(e)[:200]))
    return checks, info


# Budget VRAM approximatif (Mio) par composant, quantifications par défaut d'Ollama (Q4_K_M).
LLM_TIERS = [
    # (VRAM mini totale en Mio, modèle recommandé, whisper recommandé, stt_device)
    (15_500, "qwen2.5:14b", "small", "cuda"),
    (7_500, "qwen2.5:7b", "base", "cuda"),
    (5_500, "qwen2.5:3b", "base", "cuda"),
    (3_500, "qwen2.5:3b", "base", "cpu"),
    (0, "qwen2.5:1.5b", "base", "cpu"),
]


def recommend(gpu: dict, settings: dict | None, ollama_models: dict[str, int]) -> list[Check]:
    if not gpu:
        return [Check("Recommandation", "Taille de modèle", True, INFO,
                      "Pas de GPU NVIDIA : qwen2.5:3b (ou 1.5b), voice.stt_device=cpu, whisper 'base'.")]
    total = gpu["vram_total_mib"]
    model, whisper, device = next((m, w, d) for floor, m, w, d in LLM_TIERS if total >= floor)
    cfg = (settings or {}).get("ollama", {})
    voice = (settings or {}).get("voice", {})
    current = cfg.get("model", "?")
    lines = [
        f"VRAM totale {total} Mio → LLM recommandé : {model} ; STT : whisper '{whisper}' sur {device}.",
        f"Configuration actuelle : ollama.model={current}, voice.stt_model={voice.get('stt_model')}, "
        f"voice.stt_device={voice.get('stt_device')}, keep_alive={cfg.get('keep_alive')}.",
    ]
    checks = [Check("Recommandation", "Taille de modèle selon la VRAM", True, INFO, " ".join(lines),
                    data={"recommended_llm": model, "recommended_whisper": whisper,
                          "recommended_stt_device": device})]

    # Estimation du pic : poids du modèle + ~0,6 Gio de cache KV (ctx 8192) + STT + contexte CUDA,
    # comparée à la VRAM libre actuelle (le bureau Windows et les navigateurs en consomment déjà).
    size_mib = ollama_models.get(current, 0) // (1024 * 1024)
    if size_mib:
        stt_mib = {"tiny": 150, "base": 300, "small": 700, "medium": 1_700}.get(str(voice.get("stt_model")), 500)
        stt_mib = stt_mib if voice.get("enabled") and voice.get("stt_device") == "cuda" else 0
        peak = size_mib + 600 + stt_mib + 300
        budget = gpu["vram_free_mib"]
        # Si le modèle est déjà chargé par Ollama, sa VRAM n'est plus "libre" : on la réintègre.
        loaded_mib = 0
        try:
            base = cfg.get("base_url", "http://127.0.0.1:11434").rstrip("/")
            for m in json.loads(body_full(f"{base}/api/ps")).get("models", []):
                loaded_mib += int(m.get("size_vram", 0)) // (1024 * 1024)
        except Exception:
            pass
        budget += loaded_mib
        checks.append(Check(
            "Recommandation", "Pic VRAM estimé tient dans la VRAM disponible", peak <= budget, WARNING,
            f"estimation {peak} Mio (modèle {size_mib} + KV ~600 + STT {stt_mib} + contexte ~300) "
            f"pour {budget} Mio disponibles (libres {gpu['vram_free_mib']} + modèles Ollama chargés {loaded_mib})",
            "Pistes (à arbitrer, non appliquées) : voice.stt_device=cpu, whisper plus petit, "
            "keep_alive Ollama réduit, modèle plus petit, fermer les applis GPU"))
    return checks


def check_voice(settings: dict | None) -> list[Check]:
    voice = (settings or {}).get("voice", {})
    enabled = bool(voice.get("enabled"))
    sev = CRITICAL if enabled else INFO
    fix = "python scripts/download_voice_models.py"
    checks = [Check("Voix", "voice.enabled", True, INFO, str(enabled))]

    ww = str(voice.get("wake_word_model", ""))
    if any(c in ww for c in "/\\") or ww.endswith((".onnx", ".tflite")):
        p = Path(ww) if Path(ww).is_absolute() else ROOT / ww
        checks.append(Check("Voix", "Modèle mot d'éveil", p.is_file(), sev, str(p), fix))
    tts = voice.get("tts_voice", "fr_FR-siwis-medium")
    for suffix in (".onnx", ".onnx.json"):
        p = ROOT / "data" / "voices" / f"{tts}{suffix}"
        checks.append(Check("Voix", f"Voix Piper {tts}{suffix}", p.is_file(), sev, str(p), fix))
    try:
        import openwakeword
        res = Path(openwakeword.__file__).parent / "resources" / "models"
        needed = ["melspectrogram.onnx", "embedding_model.onnx"]
        missing = [n for n in needed if not (res / n).is_file()]
        checks.append(Check("Voix", "Modèles de support OpenWakeWord", not missing, sev,
                            f"{res} — manquants : {', '.join(missing) or 'aucun'}", fix))
    except Exception:
        pass

    # Sprint E : le repli de synthèse est la voix intégrée de Windows (SAPI via pyttsx3),
    # plus l'exécutable `piper` en ligne de commande.
    try:
        import pyttsx3  # noqa: F401
        checks.append(Check("Voix", "Repli voix Windows (SAPI)", True, WARNING,
                            "pyttsx3 disponible : Atlas parlera même si Piper échoue"))
    except Exception as e:
        checks.append(Check("Voix", "Repli voix Windows (SAPI)", False, WARNING, str(e)[:120],
                            "pip install pyttsx3"))

    # Sprint E / L2 : la transcription GPU exige cuBLAS et cuDNN, fournis par les paquets pip
    # nvidia-*. Sans eux, CTranslate2 échoue et Atlas retombe sur le processeur (~5 s/phrase).
    if str(voice.get("stt_device", "cuda")) == "cuda":
        try:
            sys.path.insert(0, str(ROOT))
            from core.voice_engine import ensure_cuda_libraries

            ok, detail = ensure_cuda_libraries()
            checks.append(Check("Voix", "Bibliothèques CUDA pour la transcription (cuBLAS/cuDNN)",
                                ok, sev, detail[:200],
                                "pip install nvidia-cublas-cu12 nvidia-cudnn-cu12"))
        except Exception as e:
            checks.append(Check("Voix", "Bibliothèques CUDA pour la transcription (cuBLAS/cuDNN)",
                                False, sev, str(e)[:160],
                                "pip install nvidia-cublas-cu12 nvidia-cudnn-cu12"))

    hf = Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub"
    stt = voice.get("stt_model", "base")
    cached = (hf / f"models--Systran--faster-whisper-{stt}").is_dir()
    checks.append(Check("Voix", f"Modèle whisper '{stt}' en cache", cached, WARNING, str(hf),
                        f"python -c \"from faster_whisper import WhisperModel; WhisperModel('{stt}', device='cpu')\""))

    try:
        import sounddevice as sd
        dev = sd.query_devices(kind="input")
        checks.append(Check("Voix", "Micro par défaut", True, sev,
                            f"{dev['name']} ({int(dev['default_samplerate'])} Hz)"))
        out = sd.query_devices(kind="output")
        checks.append(Check("Voix", "Sortie audio par défaut", True, sev, out["name"]))
    except Exception as e:
        checks.append(Check("Voix", "Micro par défaut", False, sev, str(e)[:200],
                            "Paramètres Windows → Confidentialité → Microphone : autoriser les applis de bureau ; "
                            "Paramètres → Son → Entrée : choisir le micro"))
    return checks


# --------------------------------------------------------------------------- #
#  Sprint Check-up / CK2 — les bascules : celles qu'Atlas a faites, et leurs conditions
# --------------------------------------------------------------------------- #

def _atlas_health() -> dict | None:
    """/api/health d'Atlas s'il tourne, sinon None."""
    port = int(((_load_settings() or {}).get("server", {}) or {}).get("port", 8550))
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        return None


def _onnx_present(settings: dict) -> tuple[bool, Path]:
    d = ROOT / (settings.get("memory", {}) or {}).get("embedding_onnx_dir", "models/embeddings/multilingual-e5-base")
    return (d / "model_ext.onnx").is_file() or (d / "model.onnx").is_file(), d


def check_bascules() -> list[Check]:
    """Aucune dégradation silencieuse : les bascules en cours (Atlas lancé) et, toujours, les
    conditions qui en déclencheraient une."""
    import importlib.util

    settings = _load_settings() or {}
    checks: list[Check] = []
    sante = _atlas_health()
    if sante is None:
        checks.append(Check("Bascules", "Bascules en cours dans Atlas", True, INFO,
                            "Atlas n'est pas lancé : seules les conditions ci-dessous sont vérifiées"))
    else:
        actives = sante.get("bascules") or []
        if not actives:
            checks.append(Check("Bascules", "Bascules en cours dans Atlas", True, INFO, "aucune"))
        for b in actives:
            checks.append(Check("Bascules", f"Bascule en cours : {b.get('composant', b.get('cle'))}", False, WARNING,
                                f"cause : {b.get('cause')} — ce qui est perdu : {b.get('perte')}"))

    onnx_ok, onnx_dir = _onnx_present(settings)
    checks.append(Check("Bascules", "Embeddings ONNX (sinon repli sentence-transformers, plus lent)", onnx_ok,
                        WARNING, str(onnx_dir), "python scripts/download_voice_models.py"))
    ocr_ok = importlib.util.find_spec("easyocr") is not None and importlib.util.find_spec("torch") is not None
    checks.append(Check("Bascules", "EasyOCR, repli de Tesseract (sinon certains clics impossibles)", ocr_ok,
                        WARNING, "easyocr et torch importables" if ocr_ok else "easyocr ou torch absent",
                        "pip install -r requirements.txt"))
    uia_ok = importlib.util.find_spec("pywinauto") is not None
    checks.append(Check("Bascules", "UI Automation (sinon chaque clic passe par l'OCR)", uia_ok, WARNING,
                        "pywinauto importable" if uia_ok else "pywinauto absent", "pip install -r requirements.txt"))
    tts = (settings.get("voice", {}) or {}).get("tts_voice", "fr_FR-siwis-medium")
    piper_ok = (ROOT / "data" / "voices" / f"{tts}.onnx").is_file()
    checks.append(Check("Bascules", "Voix Piper (sinon voix de Windows)", piper_ok, WARNING,
                        str(ROOT / "data" / "voices" / f"{tts}.onnx"), "python scripts/download_voice_models.py"))
    return checks


# --------------------------------------------------------------------------- #
#  Sprint Check-up / CK6 — doctor.py --composants : le tableau de CK1, en court
# --------------------------------------------------------------------------- #

def _torch_build() -> str | None:
    """« processeur » ou « CUDA x.y », lu dans torch/version.py sans importer torch."""
    import importlib.util
    import re

    spec = importlib.util.find_spec("torch")
    if spec is None or not spec.submodule_search_locations:
        return None
    try:
        texte = (Path(list(spec.submodule_search_locations)[0]) / "version.py").read_text(encoding="utf-8")
        m = re.search(r"^cuda\s*(?::[^=]*)?=\s*(.+)$", texte, re.M)
        cuda = m.group(1).strip().strip("'\"") if m else "None"
    except Exception:
        return "?"
    return "processeur" if cuda in ("None", "") else f"CUDA {cuda}"


def _ct2_cuda_devices() -> int:
    """Périphériques CUDA vus par CTranslate2, importé sans torch (comme main.py)."""
    cache = "torch" not in sys.modules
    if cache:
        sys.modules["torch"] = None
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        return 0
    finally:
        if cache and sys.modules.get("torch", 0) is None:
            del sys.modules["torch"]


def composants() -> list[dict]:
    """Chaque composant d'Atlas : présent, version, matériel utilisé, bascule active ou non."""
    settings = _load_settings() or {}
    voice = settings.get("voice", {}) or {}
    sante = _atlas_health()
    actives = {b.get("cle"): b for b in ((sante or {}).get("bascules") or [])}
    lignes: list[dict] = []

    def ligne(composant, role, present, version, materiel, bascule_si_absent, cles=()):
        active = next((actives[c] for c in cles if c in actives), None)
        if active:
            bascule = f"ACTIVE : {active.get('cause')}"
        elif not present:
            bascule = bascule_si_absent
        else:
            bascule = "aucune"
        lignes.append({"composant": composant, "role": role, "present": bool(present), "version": version or "—",
                       "materiel": materiel, "bascule": bascule})

    # Ollama et ses modèles
    base = (settings.get("ollama", {}) or {}).get("base_url", "http://127.0.0.1:11434").rstrip("/")
    ok_v, body_v = _http_get(f"{base}/api/version")
    version = json.loads(body_v).get("version") if ok_v else None
    modeles, vram = [], 0
    if ok_v:
        try:
            modeles = sorted(m["name"] for m in json.loads(body_full(f"{base}/api/tags"))["models"])
            vram = sum(int(m.get("size_vram", 0)) for m in json.loads(body_full(f"{base}/api/ps")).get("models", []))
        except Exception:
            pass
    ligne("Ollama", "modèle de langue", ok_v, f"{version} — modèles : {', '.join(modeles) or 'aucun'}" if ok_v else None,
          f"GPU ({vram // 1048576} Mo en VRAM)" if vram else ("GPU si la VRAM suffit (modèle non chargé)" if ok_v else "—"),
          "Atlas répond « modèle indisponible » (dit à chaque demande)")

    # OCR
    tess_exe = shutil.which("tesseract")
    tess_v, langs = None, []
    if tess_exe:
        code, out = _run([tess_exe, "--version"])
        tess_v = out.strip().splitlines()[0] if code == 0 and out.strip() else None
        code, out = _run([tess_exe, "--list-langs"])
        langs = [x.strip() for x in out.strip().splitlines()[1:] if x.strip()] if code == 0 else []
    ligne("Tesseract", "OCR des clics, couche rapide", bool(tess_v),
          f"{tess_v} — fra : {'oui' if 'fra' in langs else 'NON'}" if tess_v else None, "processeur",
          "clics par EasyOCR, ~20× plus lents (dit par Atlas)", ("tesseract", "tesseract_fra"))
    build = _torch_build()
    ligne("EasyOCR", "OCR de repli (processus à part)", _pkg_version("easyocr") is not None,
          _pkg_version("easyocr"), f"{build or '—'} (torch)" if build else "—",
          "certains clics impossibles (dit par Atlas)", ("easyocr",))
    ligne("torch", "EasyOCR seulement (jamais chargé par Atlas lui-même)", build is not None,
          _pkg_version("torch"), f"build {build}" if build else "—", "EasyOCR indisponible")

    # Mémoire
    onnx_ok, onnx_dir = _onnx_present(settings)
    ligne("Embeddings (ONNX)", "vecteurs de la mémoire (e5)", onnx_ok and _pkg_version("onnxruntime") is not None,
          f"onnxruntime {_pkg_version('onnxruntime')}", "processeur",
          "repli sentence-transformers : +700 Mo, rappel plus lent (dit par Atlas)",
          ("embeddings_onnx", "embeddings_absents"))
    ligne("sentence-transformers", "repli des embeddings si le modèle ONNX manque (non chargé sinon)",
          _pkg_version("sentence-transformers") is not None, _pkg_version("sentence-transformers"),
          "processeur (torch)", "aucun repli d'embeddings si ONNX manque aussi")
    mem_dir = ROOT / (settings.get("memory", {}) or {}).get("chroma_path", "data/chromadb")
    ligne("Mémoire (ChromaDB)", "mémoire à long terme (dossier)", _pkg_version("chromadb") is not None,
          f"{_pkg_version('chromadb')} — {mem_dir}", "disque", "Atlas ne retient rien (dit par Atlas)", ("memoire",))

    # Voix
    stt_dev = str(voice.get("stt_device", "cuda"))
    cuda_ok = False
    if stt_dev == "cuda":
        try:
            sys.path.insert(0, str(ROOT))
            from core.voice_engine import ensure_cuda_libraries

            cuda_ok = ensure_cuda_libraries()[0] and _ct2_cuda_devices() > 0
        except Exception:
            cuda_ok = False
    ligne("Transcription (faster-whisper)", f"voix → texte, modèle « {voice.get('stt_model', 'base')} »",
          _pkg_version("faster-whisper") is not None, _pkg_version("faster-whisper"),
          "GPU" if cuda_ok else "processeur", "on ne peut plus parler à Atlas (dit par Atlas)",
          ("stt_gpu", "stt_absent"))
    if stt_dev == "cuda" and not cuda_ok and "stt_gpu" not in actives:
        lignes[-1]["bascule"] = "→ processeur (~5 s par phrase)"
    voix_piper = ROOT / "data" / "voices" / f"{voice.get('tts_voice', 'fr_FR-siwis-medium')}.onnx"
    ligne("Synthèse (Piper)", "texte → voix", _pkg_version("piper-tts") is not None and voix_piper.is_file(),
          _pkg_version("piper-tts"), "processeur", "→ voix de Windows (SAPI) (dit par Atlas)", ("tts_piper", "tts_muet"))
    ww = ROOT / str(voice.get("wake_word_model", ""))
    ligne("Mot d'éveil (openWakeWord)", "« Hey Atlas »", _pkg_version("openwakeword") is not None and ww.is_file(),
          _pkg_version("openwakeword"), "processeur", "on ne peut plus parler à Atlas (dit par Atlas)", ("voix",))

    # Matériel NVIDIA
    exe = shutil.which("nvidia-smi")
    pilote = None
    if exe:
        code, out = _run([exe, "--query-gpu=name,driver_version", "--format=csv,noheader"])
        pilote = out.strip().splitlines()[0] if code == 0 and out.strip() else None
    ligne("Pilote NVIDIA", "GPU pour Ollama et la transcription", bool(pilote), pilote, "GPU",
          "modèle de langue et transcription sur processeur")
    cu = [f"{d} {_pkg_version(d)}" for d in ("nvidia-cublas-cu12", "nvidia-cudnn-cu12") if _pkg_version(d)]
    ligne("cuBLAS / cuDNN", "transcription sur GPU (paquets pip)", len(cu) == 2, ", ".join(cu) or None, "GPU",
          "transcription sur processeur (dit par Atlas)", ("stt_gpu",))

    # Documents (sprint Artefacts) : sans Word ni LibreOffice installés
    ligne("Documents Word (python-docx)", "rapports, résumés et comptes rendus en .docx",
          _pkg_version("python-docx") is not None, _pkg_version("python-docx"), "processeur",
          "pas de document Word : Atlas le dit (bascule « documents »)", ("documents",))
    ligne("Documents PDF (fpdf2)", "rapports, résumés et comptes rendus en .pdf",
          _pkg_version("fpdf2") is not None, _pkg_version("fpdf2"), "processeur (polices de Windows)",
          "pas de document PDF : Atlas le dit (bascule « documents »)", ("documents",))

    # Internet
    ligne("Recherche web (ddgs)", "DuckDuckGo", _pkg_version("ddgs") is not None, _pkg_version("ddgs"), "réseau",
          "recherche impossible (dit à chaque demande)")
    return lignes


def render_composants(lignes: list[dict]) -> None:
    print("Atlas — composants\n")
    largeurs = [30, 7, 44, 26]
    print(f"{'Composant':<30} {'Présent':<7} {'Version':<44} {'Matériel':<26} Bascule")
    print("-" * 140)
    for x in lignes:
        version = x["version"] if len(x["version"]) <= 43 else x["version"][:42] + "…"
        print(f"{x['composant']:<{largeurs[0]}} {'oui' if x['present'] else 'NON':<{largeurs[1]}} "
              f"{version:<{largeurs[2]}} {x['materiel'][:25]:<{largeurs[3]}} {x['bascule']}")


# --------------------------------------------------------------------------- #
#  Sprint G / G5 — verdict lisible par un non-informaticien
#
#  Bibliothèque standard UNIQUEMENT dans cette section : la pré-vérification
#  (--precheck) doit tourner sur le PC d'un proche avant toute installation,
#  avec un Python nu (testé avec `python -S`, sans site-packages).
#
#  Seuils fondés sur les mesures (RAPPORT_SPRINT_PERFORMANCE.md, sprint Sans Docker) :
#    - RAM : Atlas tout compris ≈ 2,1 Go sans Docker (Atlas 1,3 ; Ollama 0,8), plus Windows et
#      un usage ordinaire (5 à 8 Go) → 16 Go pour la même qualité, 12 Go juste ;
#    - VRAM : 5,1 Go (qwen2.5:7b à num_ctx 8 192 : 4,9 ; transcription 0,2) + l'affichage
#      → 8 Go confortables, 6 Go juste ;
#    - disque : ~14 Go installés (venv 3,6 ; Ollama 2,8 ; qwen2.5:7b 4,4 ; e5 ONNX 2,1 ;
#      whisper 0,1), plus installeurs et caches pendant l'installation ;
#    - sans NVIDIA : transcription ~5 s par phrase au lieu de 0,3 s.
# --------------------------------------------------------------------------- #

VERDICT_OK = "✅ Atlas tournera bien"
VERDICT_DEGRADED = "⚠️ Atlas tournera, en mode dégradé"
VERDICT_KO = "❌ Atlas ne tournera pas correctement"

RAM_COMFORT_GIB = 15.0     # 16 Go (Windows en affiche ~15,8) : même qualité, mesurée
RAM_MIN_GIB = 11.0         # 12 Go : juste ; au-dessous, Windows et Atlas ne tiennent pas ensemble
VRAM_COMFORT_MIB = 7_500   # cartes 8 Go : 5,1 Go pour Atlas, marge pour l'affichage
VRAM_TIGHT_MIB = 5_500     # cartes 6 Go : juste (5,1 Go + l'affichage)
DISK_MIN_GIB = 20.0        # ~14 Go installés + installeurs et caches pendant l'installation


def _ram_gib() -> float:
    if os.name != "nt":
        try:
            return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 1024 ** 3
        except (ValueError, OSError, AttributeError):
            return 0.0
    import ctypes

    class _MemStatus(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = _MemStatus()
    status.dwLength = ctypes.sizeof(_MemStatus)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
    return status.ullTotalPhys / 1024 ** 3


def collect_machine() -> dict:
    """Ce que le verdict a besoin de savoir de la machine — lecture seule, stdlib seule."""
    windows = os.name == "nt"
    release = platform.release()
    if windows:
        try:
            if int(platform.version().split(".")[-1]) >= 22000:
                release = "11"
        except ValueError:
            pass
    arch = (os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ.get("PROCESSOR_ARCHITECTURE")
            or platform.machine())
    gpu_name, vram = None, None
    exe = shutil.which("nvidia-smi")
    if exe:
        code, out = _run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
        if code == 0 and out.strip():
            name, _, total = out.strip().splitlines()[0].rpartition(",")
            try:
                gpu_name, vram = name.strip(), int(float(total.strip()))
            except ValueError:
                pass
    # Atlas s'installe dans le profil de l'utilisateur : c'est ce disque qui compte, pas
    # celui d'où le script est lancé (une clé USB, par exemple).
    disk = shutil.disk_usage(Path.home().anchor or str(Path.home()))
    return {
        "windows": windows,
        "windows_release": release,
        "arch64": str(arch).upper().endswith("64"),
        "ram_gib": round(_ram_gib(), 1),
        "gpu_name": gpu_name,
        "vram_mib": vram,
        "disk_free_gib": round(disk.free / 1024 ** 3, 1),
    }


def machine_verdict(m: dict) -> tuple[str, list[str]]:
    """(verdict, raisons) — en français courant, sans jargon."""
    ko: list[str] = []
    degraded: list[str] = []

    if not m.get("windows"):
        ko.append("Atlas ne fonctionne que sous Windows 10 ou 11.")
    elif not m.get("arch64"):
        ko.append("Windows doit être en version 64 bits.")

    disk = float(m.get("disk_free_gib") or 0)
    if disk < DISK_MIN_GIB:
        ko.append(f"Pas assez de place sur le disque : {disk:.0f} Go libres, il en faut au moins "
                  f"{DISK_MIN_GIB:.0f} (Atlas occupe environ 14 Go une fois installé).")

    ram = float(m.get("ram_gib") or 0)
    if ram < RAM_MIN_GIB:
        ko.append(f"Pas assez de mémoire vive : {ram:.0f} Go, il en faut au moins 12 (16 pour être à l'aise).")
    elif ram < RAM_COMFORT_GIB:
        degraded.append(f"Mémoire vive juste ({ram:.0f} Go) : l'ordinateur ralentira pendant qu'Atlas "
                        "travaille si d'autres programmes lourds sont ouverts (navigateur chargé, jeu).")

    vram = m.get("vram_mib")
    if not m.get("gpu_name") or not vram:
        degraded.append("Pas de carte graphique NVIDIA (ou pilote absent) : Atlas mettra environ "
                        "5 secondes à comprendre chaque phrase dite à voix haute, au lieu d'un tiers "
                        "de seconde, et ses réponses seront plus lentes.")
    elif vram < VRAM_TIGHT_MIB:
        degraded.append(f"Carte graphique trop petite pour le modèle d'Atlas ({m['gpu_name']}, "
                        f"{vram / 1024:.0f} Go) : il faudra choisir un modèle plus petit à l'installation, "
                        "sinon Atlas répondra lentement.")
    elif vram < VRAM_COMFORT_MIB:
        degraded.append(f"Carte graphique juste ({m['gpu_name']}, {vram / 1024:.0f} Go) : le modèle tient, "
                        "mais avec peu de marge ; fermer les jeux pendant qu'Atlas sert.")

    if ko:
        return VERDICT_KO, ko + degraded
    if degraded:
        return VERDICT_DEGRADED, degraded
    return VERDICT_OK, ["Mémoire vive, carte graphique et disque suffisent."]


def render_verdict(verdict: str, reasons: list[str], m: dict) -> None:
    print(verdict)
    for r in reasons:
        print(f"  - {r}")
    gpu = f"{m['gpu_name']} ({m['vram_mib']} Mio)" if m.get("gpu_name") else "aucune carte NVIDIA détectée"
    print(f"  (Windows {m.get('windows_release')} — {m.get('ram_gib')} Go de mémoire vive — {gpu} — "
          f"{m.get('disk_free_gib')} Go libres)")


# --------------------------------------------------------------------------- #
#  Rendu
# --------------------------------------------------------------------------- #

def _status(c: Check) -> str:
    if c.ok:
        return "OK"
    return {CRITICAL: "ECHEC", WARNING: "ATTENTION", INFO: "info"}[c.severity]


def render(checks: list[Check]) -> None:
    section = None
    for c in checks:
        if c.section != section:
            section = c.section
            print(f"\n== {section} " + "=" * max(0, 60 - len(section)))
        print(f"  [{_status(c):9}] {c.name}")
        if c.detail:
            print(f"              {c.detail}")
        if not c.ok and c.fix:
            print(f"              -> Correction : {c.fix}")
    crit = [c for c in checks if not c.ok and c.severity == CRITICAL]
    warn = [c for c in checks if not c.ok and c.severity == WARNING]
    print("\n" + "=" * 64)
    print(f"  {len(checks)} vérifications — {len(crit)} critique(s), {len(warn)} avertissement(s)")
    for c in crit:
        print(f"  CRITIQUE : {c.section} / {c.name}")
    print("=" * 64)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnostic d'installation Atlas")
    parser.add_argument("--json", action="store_true", help="sortie JSON")
    parser.add_argument("--precheck", action="store_true",
                        help="pré-vérification AVANT installation : matériel seulement, Python nu suffit")
    parser.add_argument("--composants", action="store_true",
                        help="chaque composant : présent, version, matériel utilisé, bascule active ou non")
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    if args.composants:
        lignes = composants()
        if args.json:
            print(json.dumps(lignes, ensure_ascii=False, indent=2))
        else:
            render_composants(lignes)
        return 0

    # G5 : le verdict d'abord, en une ligne, pour un non-informaticien.
    machine = collect_machine()
    verdict, reasons = machine_verdict(machine)
    if args.precheck:
        if args.json:
            print(json.dumps({"verdict": verdict, "reasons": reasons, "machine": machine},
                             ensure_ascii=False, indent=2))
        else:
            render_verdict(verdict, reasons, machine)
            print()
            print("Pré-vérification du matériel seulement. Après l'installation, relancer sans "
                  "--precheck pour tout vérifier.")
        return {VERDICT_OK: 0, VERDICT_DEGRADED: 1}.get(verdict, 2)

    settings = _load_settings()
    voice_enabled = bool((settings or {}).get("voice", {}).get("enabled"))

    checks: list[Check] = []
    checks += check_python()
    checks += check_project_layout(settings)
    checks += check_packages(voice_enabled)
    checks += check_tesseract()
    checks += check_easyocr_models()
    ollama_checks = check_ollama(settings)
    checks += ollama_checks
    checks += check_memory(settings)
    checks += check_playwright()
    gpu_checks, gpu = detect_gpu()
    checks += gpu_checks
    models = next((c.data.get("models", {}) for c in ollama_checks if c.data.get("models")), {})
    checks += recommend(gpu, settings, models)
    checks += check_voice(settings)
    checks += check_bascules()

    failed_critical = any(not c.ok and c.severity == CRITICAL for c in checks)
    if failed_critical and verdict != VERDICT_KO:
        verdict = VERDICT_KO
        reasons = [f"Installation incomplète : {c.section} / {c.name}."
                   for c in checks if not c.ok and c.severity == CRITICAL] + reasons
    if args.json:
        print(json.dumps({"verdict": verdict, "reasons": reasons, "machine": machine,
                          "ok": not failed_critical, "gpu": gpu,
                          "checks": [asdict(c) | {"status": _status(c)} for c in checks]},
                         ensure_ascii=False, indent=2))
    else:
        render_verdict(verdict, reasons, machine)
        render(checks)
    return 1 if failed_critical else 0


if __name__ == "__main__":
    sys.exit(main())
