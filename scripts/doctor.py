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
    ("aiosqlite", "aiosqlite", WARNING, "SQLite async"),
    ("pyautogui", "pyautogui", CRITICAL, "clics / clavier"),
    ("pygetwindow", "pygetwindow", CRITICAL, "fenêtres"),
    ("pyperclip", "pyperclip", CRITICAL, "presse-papiers"),
    ("pywinauto", "pywinauto", CRITICAL, "grounding UIA"),
    ("pywin32", "win32api", CRITICAL, "API Windows"),
    ("comtypes", "comtypes", CRITICAL, "COM Windows"),
    ("pycaw", "pycaw", WARNING, "contrôle du volume"),
    ("wmi", "wmi", WARNING, "diagnostics matériels"),
    ("plyer", "plyer", WARNING, "notifications"),
    ("websockets", "websockets", CRITICAL, "browser bridge"),
    ("pytesseract", "pytesseract", CRITICAL, "OCR couche 1"),
    ("easyocr", "easyocr", WARNING, "OCR couche 2 (absent de requirements.txt)"),
    ("chromadb", "chromadb", CRITICAL, "mémoire long terme"),
    ("sentence-transformers", "sentence_transformers", CRITICAL, "embeddings"),
    ("beautifulsoup4", "bs4", WARNING, "lecture web"),
    ("lxml", "lxml", WARNING, "lecture web"),
    ("ddgs", "ddgs", WARNING, "recherche web (repli SearXNG)"),
    ("playwright", "playwright", WARNING, "navigateur piloté"),
    ("numpy", "numpy", CRITICAL, "audio / OCR"),
    ("sounddevice", "sounddevice", WARNING, "micro / haut-parleur"),
    ("openwakeword", "openwakeword", WARNING, "mot d'éveil"),
    ("faster-whisper", "faster_whisper", WARNING, "STT"),
    ("piper-tts", "piper", WARNING, "TTS"),
    ("onnxruntime", "onnxruntime", WARNING, "inférence wake word / TTS"),
    ("pystray", "pystray", WARNING, "icône systray"),
    ("pytest", "pytest", INFO, "tests (absent de requirements.txt)"),
    ("pytest-asyncio", "pytest_asyncio", INFO, "tests async (absent de requirements.txt)"),
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
                        "Lancer Ollama (icône systray) ou 'ollama serve'. "
                        "Ne PAS lancer le service ollama de docker-compose en même temps (conflit port 11434)."))
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
    return checks


def body_full(url: str, timeout: float = 5.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def check_memory_and_web(settings: dict | None) -> list[Check]:
    mem = (settings or {}).get("memory", {})
    host, port = mem.get("chroma_host", "localhost"), mem.get("chroma_port", 8001)
    ok, body = _http_get(f"http://{host}:{port}/api/v2/heartbeat")
    checks = [Check("Mémoire", f"ChromaDB joignable ({host}:{port})", ok, WARNING,
                    "répond" if ok else f"{body} — Atlas démarre en mode dégradé (sans mémoire)",
                    "docker compose up -d chromadb searxng  (nécessite la virtualisation BIOS + WSL2) "
                    f"ou en natif : chroma run --path data/chromadb --port {port}")]
    web = (settings or {}).get("web", {})
    url = web.get("searxng_url", "http://localhost:8888").rstrip("/")
    ok_sx, body_sx = _http_get(f"{url}/healthz")
    ddgs_ok = _pkg_version("ddgs") is not None
    checks.append(Check("Web", f"SearXNG joignable ({url})", ok_sx,
                        WARNING if ddgs_ok else CRITICAL,
                        "répond" if ok_sx else f"{body_sx} — repli ddgs {'disponible' if ddgs_ok else 'ABSENT'}",
                        "docker compose up -d searxng (nécessite Docker) ; sinon le repli ddgs est utilisé"))
    return checks


def check_virtualization() -> list[Check]:
    if os.name != "nt":
        return []
    state, detail = _virtualization_state()
    enabled = bool(state)
    docker = shutil.which("docker")
    checks = [Check("Docker", "Virtualisation activée dans le BIOS", enabled, WARNING, detail,
                    "Activer Intel VT-x / AMD-V (SVM) dans le BIOS, puis redémarrer. "
                    "Sans cela, WSL2 et Docker Desktop ne démarrent pas (HCS_E_HYPERV_NOT_INSTALLED).")]
    checks.append(Check("Docker", "CLI docker installée", docker is not None, INFO, docker or "absente",
                        "Installer Docker Desktop (optionnel si ChromaDB tourne en natif)"))
    if docker:
        code, out = _run([docker, "info", "--format", "{{.ServerVersion}}"], timeout=15)
        running = code == 0 and out.strip() and "error" not in out.lower()
        checks.append(Check("Docker", "Moteur Docker démarré", bool(running), INFO,
                            out.strip()[:200] or "pas de réponse",
                            "Démarrer Docker Desktop"))
        if running:
            checks += check_docker_services(docker)
    return checks


def check_docker_services(docker: str) -> list[Check]:
    checks = []
    code, out = _run([docker, "ps", "--format", "{{.Names}}"], timeout=15)
    names = set(out.split()) if code == 0 else set()
    # Le service ollama de docker-compose.yml écoute sur [::]:11434 : un client qui résout
    # « localhost » en IPv6 parle alors à ce conteneur et non à l'Ollama natif (constaté).
    for ollama in ("atlas_ollama", "assistant_ollama"):
        if ollama in names and shutil.which("ollama"):
            checks.append(Check("Docker", "Pas de second Ollama (conteneur) sur le port 11434", False, WARNING,
                                f"conteneur {ollama} actif en plus de l'Ollama natif",
                                f"docker stop {ollama} ; le service est derrière le profil docker-ollama (docker compose up -d suffit)"))
    chroma = next((c for c in ("atlas_chromadb", "assistant_chromadb") if c in names), None)
    if chroma:
        # L'image persiste dans persist_path (/data) : ce chemin doit être un volume ou un montage,
        # sinon la mémoire vit dans la couche du conteneur et disparaît avec lui (risque L21).
        code, out = _run([docker, "exec", chroma, "sh", "-c", "grep -h persist_path /config.yaml 2>/dev/null"], timeout=15)
        persist = next((l.split(":", 1)[1].strip().strip('"') for l in out.splitlines() if "persist_path" in l), "")
        code, mounts = _run([docker, "inspect", chroma, "--format",
                             "{{range .Mounts}}{{.Destination}}={{.Type}}:{{.Name}}{{.Source}};{{end}}"], timeout=15)
        mounted = dict(m.split("=", 1) for m in mounts.strip().split(";") if "=" in m)
        mounted_ok = bool(persist) and persist in mounted
        checks.append(Check("Mémoire", "ChromaDB persiste dans un volume", mounted_ok, CRITICAL,
                            f"{chroma} : persist_path={persist or '?'} ; montages={mounted or 'aucun'}",
                            f"NE PAS supprimer {chroma} (la mémoire est dans sa couche). Sauvegarder d'abord : "
                            "python scripts/backup_memory.py backup, puis monter un volume sur persist_path."))
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
        checks.append(Check("GPU", "torch voit le GPU (EasyOCR, embeddings)", cuda, WARNING, detail,
                            "torch est une build CPU : EasyOCR et les embeddings tournent sur CPU "
                            "(la transcription n'est pas concernée : elle passe par CTranslate2, vérifié "
                            "juste en dessous). Build CUDA : "
                            "pip install torch --index-url https://download.pytorch.org/whl/cu128 "
                            "(RTX 50xx : CUDA 12.8 minimum)"))
    except Exception as e:
        checks.append(Check("GPU", "torch voit le GPU (EasyOCR, embeddings)", False, WARNING, str(e)[:200]))
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
#  Sprint G / G5 — verdict lisible par un non-informaticien
#
#  Bibliothèque standard UNIQUEMENT dans cette section : la pré-vérification
#  (--precheck) doit tourner sur le PC d'un proche avant toute installation,
#  avec un Python nu (testé avec `python -S`, sans site-packages).
#
#  Seuils fondés sur les mesures, justifiées dans RAPPORT_SPRINT_G.md :
#    - VRAM : pic 6 674 Mio, chaîne complète (qwen2.5:7b + transcription GPU, sprint E) ;
#    - RAM  : pic 18,7 Go sans Docker, 23,4 Go avec, sur 24 Go (98 %, sprint A, L23) ;
#    - disque : ~17 Go installés (venv 3,6 ; Ollama 2,8 ; qwen2.5:7b 4,4 ; e5 1,1 ;
#      whisper 0,1 ; Docker Desktop 3,9 ; images ChromaDB + SearXNG 1,2 — sprint G) ;
#    - sans NVIDIA : transcription ~5 s par phrase au lieu de 0,3 s.
# --------------------------------------------------------------------------- #

VERDICT_OK = "✅ Atlas tournera bien"
VERDICT_DEGRADED = "⚠️ Atlas tournera, en mode dégradé"
VERDICT_KO = "❌ Atlas ne tournera pas correctement"

RAM_COMFORT_GIB = 31.0     # machines de 32 Go : marge au-dessus du pic de 23,4 Go
RAM_TIGHT_GIB = 23.0       # 24 Go : mesuré plein à 98 % avec Docker
RAM_MIN_GIB = 15.0         # 16 Go : au-dessous du pic sans Docker (18,7) — pagination
VRAM_COMFORT_MIB = 7_500   # cartes 8 Go : pic mesuré 6 674 Mio
DISK_MIN_GIB = 25.0        # ~17 Go installés + installeurs et caches pendant l'installation


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


def _virtualization_state() -> tuple[bool | None, str]:
    """True / False, ou None si la question n'a pas pu être posée."""
    if os.name != "nt":
        return None, "hors Windows"
    # VirtualizationFirmwareEnabled vaut False dès qu'un hyperviseur tourne (WSL2/Docker) :
    # on accepte aussi HypervisorPresent=True (constaté au sprint A).
    code, out = _run(["powershell", "-NoProfile", "-Command",
                      "'{0};{1}' -f (Get-CimInstance Win32_Processor | Select-Object -First 1).VirtualizationFirmwareEnabled,"
                      "(Get-CimInstance Win32_ComputerSystem).HypervisorPresent"],
                     timeout=15)
    firmware, _, hypervisor = out.strip().partition(";")
    detail = f"VirtualizationFirmwareEnabled={firmware or '?'} HypervisorPresent={hypervisor or '?'}"
    if code != 0 or not (firmware or hypervisor):
        return None, detail
    return "true" in (firmware.lower(), hypervisor.lower()), detail


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
    virtualization, _ = _virtualization_state()
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
        "virtualization": virtualization,
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
                  f"{DISK_MIN_GIB:.0f} (Atlas occupe environ 17 Go une fois installé).")

    ram = float(m.get("ram_gib") or 0)
    if ram < RAM_MIN_GIB:
        ko.append(f"Pas assez de mémoire vive : {ram:.0f} Go, il en faut au moins 16.")
    elif ram < RAM_TIGHT_GIB:
        degraded.append(f"Mémoire vive juste ({ram:.0f} Go) : l'ordinateur ralentira pendant qu'Atlas "
                        "travaille. Fermer le navigateur et les jeux aide.")
    elif ram < RAM_COMFORT_GIB:
        degraded.append(f"Mémoire vive un peu juste ({ram:.0f} Go) : elle a été mesurée pleine à 98 % sur "
                        "un ordinateur de 24 Go quand tout Atlas tourne. Éviter de garder un jeu ouvert "
                        "en même temps.")

    vram = m.get("vram_mib")
    if not m.get("gpu_name") or not vram:
        degraded.append("Pas de carte graphique NVIDIA (ou pilote absent) : Atlas mettra environ "
                        "5 secondes à comprendre chaque phrase dite à voix haute, au lieu d'un tiers "
                        "de seconde, et ses réponses seront plus lentes.")
    elif vram < VRAM_COMFORT_MIB:
        degraded.append(f"Carte graphique un peu juste ({m['gpu_name']}, {vram / 1024:.0f} Go de "
                        "mémoire) : il faudra choisir un modèle plus petit à l'installation, sinon "
                        "Atlas répondra lentement.")

    if m.get("virtualization") is False:
        degraded.append("La virtualisation n'est pas activée dans le BIOS : Docker ne pourra pas "
                        "démarrer, donc pas de mémoire à long terme (« retiens que… ») ni de "
                        "recherche web locale. Elle s'active dans le BIOS (Intel VT-x ou AMD-V).")
    elif m.get("virtualization") is None:
        degraded.append("Impossible de vérifier si la virtualisation est activée (nécessaire pour "
                        "Docker et la mémoire d'Atlas) : à contrôler dans le BIOS.")

    if ko:
        return VERDICT_KO, ko + degraded
    if degraded:
        return VERDICT_DEGRADED, degraded
    return VERDICT_OK, ["Mémoire vive, carte graphique, disque et virtualisation suffisent."]


def render_verdict(verdict: str, reasons: list[str], m: dict) -> None:
    print(verdict)
    for r in reasons:
        print(f"  - {r}")
    gpu = f"{m['gpu_name']} ({m['vram_mib']} Mio)" if m.get("gpu_name") else "aucune carte NVIDIA détectée"
    print(f"  (Windows {m.get('windows_release')} — {m.get('ram_gib')} Go de mémoire vive — {gpu} — "
          f"{m.get('disk_free_gib')} Go libres — virtualisation : {m.get('virtualization')})")


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
    args = parser.parse_args(argv)

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

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
    checks += check_memory_and_web(settings)
    checks += check_playwright()
    checks += check_virtualization()
    gpu_checks, gpu = detect_gpu()
    checks += gpu_checks
    models = next((c.data.get("models", {}) for c in ollama_checks if c.data.get("models")), {})
    checks += recommend(gpu, settings, models)
    checks += check_voice(settings)

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
