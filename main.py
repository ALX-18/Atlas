"""
Atlas — Assistant Bureau Windows
Point d'entrée principal FastAPI.
"""

import json
import logging
import os
import pathlib
import socket
import sys
import asyncio
import webbrowser
from contextlib import asynccontextmanager

# Sprint G / G3 : « 100 % local » doit être vrai. Le serveur ChromaDB (docker-compose)
# avait coupé sa télémétrie, pas le client dans ce processus — qui envoyait des statistiques
# d'usage anonymes (« Anonymized telemetry enabled »). Posé AVANT tout import qui crée un
# client, et imposé (pas setdefault) : un réglage de la machine ne doit pas la rallumer.
os.environ["ANONYMIZED_TELEMETRY"] = "False"
# Dépôt + Ollama / C3 : seul Atlas lui-même branche la vraie mémoire (core/memory_manager.py).
os.environ.setdefault("ATLAS_MEMORY", "real")


def _import_ctranslate2_without_torch() -> None:
    """Sprint Performance / PF2 — ctranslate2 (le moteur de la transcription) importe torch
    « au cas où » (ctranslate2/specs/model_spec.py, pour CONVERTIR des modèles) : ~200 Mo et
    3,5 s, sans servir à transcrire (transcriptions identiques avec et sans, mesuré). On
    l'importe ici, au chargement de main.py, quand un seul fil tourne, en lui cachant torch ;
    torch reste importable ensuite pour qui en a vraiment besoin (EasyOCR, embeddings)."""
    if "torch" in sys.modules or "ctranslate2" in sys.modules:
        return
    sys.modules["torch"] = None
    try:
        import ctranslate2  # noqa: F401
    except Exception:
        pass
    finally:
        if sys.modules.get("torch", 0) is None:
            del sys.modules["torch"]


_import_ctranslate2_without_torch()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# --------------------------------------------------------------------------- #
#  Logging
# --------------------------------------------------------------------------- #

# Pré-beta / PB2 : logs\ n'est pas versionné ; sans lui, un clone neuf plantait ici.
(pathlib.Path(__file__).parent / "logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            pathlib.Path(__file__).parent / "logs" / "atlas.log",
            encoding="utf-8",
        ),
    ],
)
logger = logging.getLogger("atlas")

# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #

CONFIG_PATH = pathlib.Path(__file__).parent / "config" / "settings.json"
with open(CONFIG_PATH, encoding="utf-8") as f:
    CONFIG = json.load(f)

HOST = CONFIG["server"]["host"]
PORT = CONFIG["server"]["port"]
LOCK_FILE = pathlib.Path(__file__).parent / "data" / "atlas.lock"
_INSTANCE_LOCK_FH = None


def _verifier_memoire(mem) -> None:
    """Sprint Check-up / CK2 : une mémoire en panne ou tenue ailleurs est une bascule vécue
    (Atlas ne retient plus rien). « neutralisee » ne concerne que les processus hors d'Atlas."""
    etat = mem.status()
    if etat.get("etat") in ("en_panne", "verrouillee"):
        from core_conversational.degradations import signaler

        signaler("memoire", f"{etat['etat']} : {etat.get('detail', '')}")


def _notifier(message: str) -> None:
    """Notification Windows, sans bloquer le démarrage."""
    import threading

    def _go():
        try:
            from plyer import notification

            notification.notify(title="Atlas", message=message[:250], timeout=8)
        except Exception as e:
            from core_conversational.degradations import signaler

            signaler("notifications", f"{type(e).__name__}: {e}")

    threading.Thread(target=_go, daemon=True).start()


def _annoncer_bascules() -> None:
    """CK2 : ce qui manque au démarrage et touche l'utilisateur est DIT (notification), en plus
    du journal, de /api/health et de doctor. La première réponse le redit."""
    from core_conversational.degradations import a_annoncer

    for message in a_annoncer():
        _notifier(message)


def _voice_gpu_status(voice_cfg: dict, ct2_cuda_devices: int, torch_cuda: bool) -> tuple[str, str]:
    """(niveau, message) sur le GPU de la transcription — ce qu'elle utilise RÉELLEMENT.

    Sprint G-ter / GT5 : le message disait « aucun GPU CUDA détecté » d'après torch, alors que
    la transcription passe par CTranslate2 (faster-whisper), qui voit le GPU. torch en version
    processeur ne concerne qu'EasyOCR et les embeddings.
    """
    device = voice_cfg.get("stt_device", "cuda")
    if device != "cuda":
        return "info", "Atlas Voice : transcription réglée sur le processeur (voice.stt_device=cpu), environ 5 s par phrase."
    if ct2_cuda_devices <= 0:
        return ("warning", "⚠️ Atlas Voice : CTranslate2 ne voit aucun GPU CUDA — la transcription passera sur "
                           "le processeur et sera lente (environ 5 s par phrase).")
    extra = "" if torch_cuda else " (torch est en version processeur : seuls EasyOCR et les embeddings tournent sur le processeur)"
    return "info", f"Atlas Voice : transcription sur GPU ({ct2_cuda_devices} périphérique(s) CUDA vu(s) par CTranslate2){extra}."


def _dump_modules() -> None:
    """Sprint Check-up / CK1 : si ATLAS_MODULES_DUMP est posé, écrit la liste des modules
    Python réellement chargés (mesure dynamique de l'inventaire). Rien sinon."""
    target = os.environ.get("ATLAS_MODULES_DUMP")
    if not target:
        return
    try:
        pathlib.Path(target).write_text(json.dumps({"processus": "atlas", "pid": os.getpid(),
                                                    "modules": sorted(sys.modules)}), encoding="utf-8")
    except Exception as e:
        logging.getLogger("atlas").warning("ATLAS_MODULES_DUMP : écriture impossible (%s)", e)


def _torch_has_cuda_build() -> bool:
    """torch est-il compilé pour CUDA ? Lu dans torch/version.py, SANS importer torch.

    Sprint Performance / PF2 : importer torch (~200 Mo) au démarrage pour ce seul message
    le chargeait même quand ni l'OCR ni les embeddings ne servent.
    """
    try:
        import importlib.util
        import re

        spec = importlib.util.find_spec("torch")
        if spec is None or not spec.submodule_search_locations:
            return False
        version = pathlib.Path(list(spec.submodule_search_locations)[0]) / "version.py"
        m = re.search(r"^cuda\s*(?::[^=]*)?=\s*(.+)$", version.read_text(encoding="utf-8"), re.M)
        return bool(m) and m.group(1).strip() not in ("None", "''", '""')
    except Exception:
        return False


def _warn_if_voice_gpu_missing(voice_enabled: bool):
    """Annonce le GPU de la transcription d'après CTranslate2, qui la fait (GT5)."""
    if not voice_enabled:
        return
    try:
        import ctranslate2

        ct2 = ctranslate2.get_cuda_device_count()
    except Exception:
        ct2 = 0
    level, message = _voice_gpu_status(CONFIG.get("voice", {}), ct2, _torch_has_cuda_build())
    (logger.warning if level == "warning" else logger.info)(message)


def _is_port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def _find_available_port(host: str, preferred_port: int, max_tries: int = 20) -> int:
    if _is_port_free(host, preferred_port):
        return preferred_port
    for offset in range(1, max_tries + 1):
        candidate = preferred_port + offset
        if _is_port_free(host, candidate):
            return candidate
    return preferred_port


def acquire_instance_lock() -> tuple[bool, str]:
    """
    Acquire a process-level lock to guarantee a single Atlas instance.
    Returns (ok, message).
    """
    global _INSTANCE_LOCK_FH

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _INSTANCE_LOCK_FH is None:
        _INSTANCE_LOCK_FH = open(LOCK_FILE, "a+", encoding="utf-8")

    try:
        if os.name == "nt":
            import msvcrt

            # Lock first byte in non-blocking mode.
            _INSTANCE_LOCK_FH.seek(0)
            msvcrt.locking(_INSTANCE_LOCK_FH.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(_INSTANCE_LOCK_FH.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

        _INSTANCE_LOCK_FH.seek(0)
        _INSTANCE_LOCK_FH.truncate(0)
        _INSTANCE_LOCK_FH.write(f"pid={os.getpid()}\n")
        _INSTANCE_LOCK_FH.flush()
        return True, "instance lock acquired"
    except OSError:
        return False, "Une autre instance Atlas est déjà active. Arrêt propre du second lancement."


def release_instance_lock() -> None:
    """Release instance lock if held."""
    global _INSTANCE_LOCK_FH
    if _INSTANCE_LOCK_FH is None:
        return

    try:
        if os.name == "nt":
            import msvcrt

            _INSTANCE_LOCK_FH.seek(0)
            msvcrt.locking(_INSTANCE_LOCK_FH.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(_INSTANCE_LOCK_FH.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.debug("Release lock warning: %s", e)
    finally:
        try:
            _INSTANCE_LOCK_FH.close()
        except Exception:
            pass
        _INSTANCE_LOCK_FH = None


async def _wait_port_released(host: str, port: int, timeout_seconds: float = 3.0):
    """Wait briefly for a port to be released after shutdown."""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        if _is_port_free(host, port):
            return True
        await asyncio.sleep(0.1)
    return _is_port_free(host, port)

# Ensure data directory exists
DATA_DIR = pathlib.Path(__file__).parent / "data" / "chromadb"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
#  Lifespan — startup / shutdown
# --------------------------------------------------------------------------- #

async def execute_automation_action(action: dict) -> dict:
    """Point d'exécution commun du planificateur, des déclencheurs et des workflows (B1-ter).

    Ces chemins ne passent pas par le validateur : l'action enregistrée est recontrôlée ici,
    au moment de l'exécution. Une action qui demande une confirmation — impossible sans
    utilisateur présent — n'est plus laissée en attente en silence : elle est annulée,
    journalisée et signalée.
    """
    from core.confirmation import resolve_pending
    from core.context_monitor import collect_context
    from core.intent_engine import execute_tool
    from core.validator import check_automation_action, report_automation_block

    tool = action.get("action", "") if isinstance(action, dict) else ""
    error = check_automation_action(action)
    if error:
        report_automation_block("automatisation", tool or "?", error)
        return {"status": "blocked", "message": f"Action refusée : {error}.",
                "error_code": "ERR_AUTOMATION_BLOCKED"}

    result = await execute_tool(tool, action.get("params") or {}, collect_context())
    if result.get("status") == "confirmation_required":
        if result.get("confirmation_id"):
            resolve_pending(result["confirmation_id"])
        reason = (f"'{tool}' demande une confirmation, impossible en exécution automatique"
                  f" ({result.get('reason') or result.get('message') or 'sans motif'})")
        report_automation_block("automatisation", tool, reason)
        return {"status": "blocked", "message": f"Action non exécutée : {reason}.",
                "error_code": "ERR_AUTOMATION_BLOCKED"}
    return result


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise la détection des habitudes et la mémoire au démarrage."""
    from core.context_monitor import start_new_session, collect_context, start_sampler, stop_sampler
    from core.memory_manager import get_memory_manager
    from tools.browser_bridge import get_bridge
    from core.world_state import get_world_state
    from core.intent_classifier import get_classifier
    from core.validator import get_validator, set_automation_notifier
    from core.intent_engine import get_execution_engine, execute_tool
    from core.scheduler import get_scheduler
    from core.trigger_engine import get_trigger_engine
    from core.workflow_engine import get_workflow_engine
    from core.confirmation import classify_process
    from tools.notifier import notify
    from tools.systray import AtlasSystray
    from core.voice_engine import get_voice_engine
    from core.file_indexer import get_file_indexer

    lock_ok, lock_msg = acquire_instance_lock()
    if not lock_ok:
        logger.error("⛔ %s", lock_msg)
        raise RuntimeError(lock_msg)
    logger.info("🔒 Mono-instance lock acquis")

    # Pré-beta / PB3 : processus, CPU et GPU échantillonnés en arrière-plan ; une demande lit
    # le dernier état au lieu d'attendre ~2 s. Arrêté au shutdown ci-dessous.
    start_sampler()

    # Sprint Performance / PF5.2 : modèle de langue et embeddings chargés en arrière-plan ;
    # le démarrage n'attend pas, la première demande ne paie plus ~30 s.
    from core.ollama_client import prewarm

    app.state.prewarm_task = prewarm()

    # v5.1 corrective — mitigate Python 3.12 + Proactor + Windows socket cleanup bug
    # AssertionError raised in asyncio.proactor_events._attach when a deferred IOCP
    # completion fires after self._sockets is cleaned. Not actionable; log and swallow.
    try:
        loop = asyncio.get_running_loop()

        def _proactor_exception_handler(loop_, context):
            exc = context.get("exception")
            if isinstance(exc, AssertionError):
                src = (context.get("message") or "")
                # Only swallow proactor _attach assertion — surface anything else.
                if "_attach" in src or "_sockets" in src or "proactor" in src.lower():
                    logger.warning(
                        "[asyncio] Proactor socket cleanup AssertionError silencée (bug connu Python 3.12 Windows): %s",
                        src,
                    )
                    return
            loop_.default_exception_handler(context)

        loop.set_exception_handler(_proactor_exception_handler)
    except Exception as e:
        logger.debug("Proactor handler install warning: %s", e)

    # Sprint Check-up / CK5 : Tesseract et sa langue fra. Absents, c'est une bascule (signalée,
    # visible dans /api/health et doctor, dite à Alexis) — plus jamais « 20 fois plus lent » en silence.
    from tools.grounding import tesseract_etat

    tess = await asyncio.to_thread(tesseract_etat)
    if tess["ok"]:
        logger.info("🔍 Tesseract OCR : %s (fra : %s)", tess.get("version"), "oui" if tess["fra"] else "NON")

    start_new_session()
    mem = get_memory_manager()
    etat_memoire = mem.status()
    _verifier_memoire(mem)
    # Sans Docker / SD2 : jamais deux Atlas sur la même base. Si elle est tenue par un autre
    # processus, Atlas refuse de démarrer et dit pourquoi (au lieu de tourner sans mémoire).
    if etat_memoire["etat"] == "verrouillee":
        logger.error("⛔ Démarrage refusé : %s", etat_memoire["detail"])
        raise RuntimeError(f"Démarrage refusé : {etat_memoire['detail']}")
    logger.info("🧠 Mémoire : %s (%s)", etat_memoire["etat"], etat_memoire["detail"])

    # Instantiate v2.3 components
    ws = get_world_state()
    classifier = get_classifier()
    validator = get_validator()
    engine = get_execution_engine()
    logger.info("🏗️ Architecture v2.3 : WorldState + Classifier + Validator + Engine initialisés")

    # --- MVP 3.0 : Automation components ---

    # Shared execution callback for scheduler/trigger/workflow
    # B1-ter : contrôle à l'exécution et signalement, voir execute_automation_action.
    _execute_action = execute_automation_action

    def _automation_toast(title: str, message: str) -> None:
        try:
            asyncio.get_running_loop().create_task(notify(message, title=title))
        except RuntimeError:
            logger.warning("[AUTOMATION] notification impossible hors boucle : %s", message)

    set_automation_notifier(_automation_toast)

    # Protection callback
    def _check_protection(process_name: str) -> str:
        level = classify_process(process_name, collect_context())
        if "INTOUCHABLE" in level:
            return "intouchable"
        elif "DEMANDE" in level:
            return "demande"
        return "libre"

    # Workflow Engine — B1-ter : chargé en premier, les tâches et déclencheurs qui lancent un
    # workflow sont contrôlés contre cette liste.
    workflow_engine = get_workflow_engine()
    workflow_engine.set_execution_callback(_execute_action)
    workflow_engine.set_protection_callback(_check_protection)
    workflow_engine.set_notification_callback(lambda msg: notify(msg))
    workflow_engine.load_workflows()

    # Scheduler
    scheduler = get_scheduler()
    scheduler.set_execution_callback(_execute_action)
    await scheduler.start()

    # Trigger Engine
    trigger_engine = get_trigger_engine()
    trigger_engine.set_execution_callback(_execute_action)
    trigger_engine.set_context_callback(collect_context)
    trigger_engine.set_protection_callback(_check_protection)
    # Load check interval from settings
    trigger_check_interval = CONFIG.get("automation", {}).get("trigger_check_interval_seconds", 10)
    trigger_engine.set_check_interval(trigger_check_interval)
    await trigger_engine.start()

    logger.info("🤖 Architecture v3.0 : Scheduler + TriggerEngine + WorkflowEngine initialisés")

    # --- v4.0: Voice & Presence (optional) ---
    voice_cfg = CONFIG.get("voice", {})
    voice_enabled = bool(voice_cfg.get("enabled", False))

    systray = None
    voice_engine = None
    if voice_enabled:
        _warn_if_voice_gpu_missing(voice_enabled=True)

        loop = asyncio.get_running_loop()

        def _on_open_ui():
            try:
                webbrowser.open(f"http://{HOST}:{PORT}")
            except Exception as e:
                logger.debug("Open UI from systray failed: %s", e)

        def _on_toggle_voice(new_enabled: bool):
            if voice_engine is None:
                return

            async def _apply():
                try:
                    if new_enabled:
                        await voice_engine.start()
                    else:
                        await voice_engine.stop()
                except Exception as e:
                    logger.warning("Voice toggle failed: %s", e)

            loop.call_soon_threadsafe(lambda: asyncio.create_task(_apply()))

        def _on_quit_app():
            # pystray callback runs in dedicated thread; hard-exit is the most reliable here.
            os._exit(0)

        systray = AtlasSystray(
            on_open=_on_open_ui,
            on_toggle_voice=_on_toggle_voice,
            on_quit=_on_quit_app,
        )
        systray.set_voice_enabled(True)
        systray.start()

        voice_engine = get_voice_engine(systray=systray)
        try:
            await voice_engine.start()
            logger.info("🎙️ VoiceEngine demarre")
        except Exception as e:
            from core_conversational.degradations import signaler

            signaler("voix", f"{type(e).__name__}: {e}")

    # Démarrer le Browser Bridge WebSocket (MVP 2.2)
    bridge = get_bridge()
    try:
        await bridge.start()
        logger.info("🔌 Browser Bridge : WebSocket prêt sur le port %d", bridge.port)
    except Exception as e:
        from core_conversational.degradations import signaler

        signaler("browser_bridge", f"{type(e).__name__}: {e}")

    file_indexer = get_file_indexer()
    if file_indexer.enabled():
        try:
            await file_indexer.start()
            logger.info("📂 FileIndexer actif (mode passif)")
        except Exception as e:
            from core_conversational.degradations import signaler

            signaler("file_indexer", f"{type(e).__name__}: {e}")

    _annoncer_bascules()

    yield

    # Shutdown
    _dump_modules()
    try:
        stop_sampler()
    except Exception:
        pass
    try:
        from tools.grounding import _release_easyocr

        _release_easyocr()
    except Exception:
        pass
    try:
        if voice_engine is not None:
            await voice_engine.stop()
    except Exception:
        pass
    try:
        if systray is not None:
            systray.stop()
    except Exception:
        pass
    try:
        await scheduler.stop()
    except Exception:
        pass
    try:
        await trigger_engine.stop()
    except Exception:
        pass
    try:
        await bridge.stop()
    except Exception:
        pass
    try:
        await file_indexer.stop()
    except Exception:
        pass

    try:
        bridge_released = await _wait_port_released(HOST, int(CONFIG.get("browser_bridge", {}).get("port", 9999)))
        api_released = await _wait_port_released(HOST, PORT)
        logger.info(
            "🧹 Ports shutdown — api:%s bridge:%s",
            "libéré" if api_released else "occupé",
            "libéré" if bridge_released else "occupé",
        )
    except Exception as e:
        logger.debug("Port release check warning: %s", e)

    release_instance_lock()
    logger.info("🔓 Mono-instance lock libéré")
    logger.info("Atlas arrêt propre.")


# --------------------------------------------------------------------------- #
#  App
# --------------------------------------------------------------------------- #

app = FastAPI(
    title="Atlas — Assistant Bureau Windows",
    version="4.0.0",
    description="Assistant local intelligent pour le contrôle de PC Windows — Architecture Controlled Loop + Automatisation + Voix & Presence",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    # Sprint G / G1 : plus de « * ». Seule l'interface servie par Atlas lui-même.
    allow_origins=[f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def _refus_autre_origine(request) -> str:
    """Motif de refus si la requête vient d'ailleurs qu'Atlas lui-même, sinon « ».

    Sprint G / G1. Restreindre allow_origins ne suffit pas : le CORS empêche seulement le
    navigateur de LIRE la réponse, et une requête « simple » est exécutée quand même. Le
    serveur refuse donc lui-même :
      - un Host qui n'est pas la machine (rebinding DNS : un domaine hostile résolu vers
        127.0.0.1 est « la même origine » pour le navigateur) ;
      - une Origin qui n'est pas exactement l'adresse d'Atlas (comparée au Host, donc
        valable quel que soit le port retenu au démarrage) ;
      - Sec-Fetch-Site « cross-site » ou « same-site » : une balise <img> ou un lien
        n'envoient pas d'Origin, mais le navigateur envoie toujours cet en-tête.
    La fenêtre desktop (httpx) n'envoie ni Origin ni Sec-Fetch-Site : elle passe.
    """
    host = (request.headers.get("host") or "").strip().lower()
    name = host.split("]")[0] + "]" if host.startswith("[") else host.rsplit(":", 1)[0]
    if name not in _LOOPBACK_HOSTS:
        return f"hôte « {host} »"
    origin = request.headers.get("origin")
    if origin is not None and origin.strip().rstrip("/").lower() != f"http://{host}":
        return f"origine « {origin} »"
    if (request.headers.get("sec-fetch-site") or "").lower() in ("cross-site", "same-site"):
        return "requête venue d'un autre site"
    return ""


@app.middleware("http")
async def _seul_atlas(request, call_next):
    motif = _refus_autre_origine(request)
    if motif:
        from fastapi.responses import JSONResponse

        logger.warning("[SECURITE] Requête refusée (%s) : %s %s", motif, request.method, request.url.path)
        return JSONResponse(status_code=403,
                            content={"detail": "Atlas n'accepte que les demandes venant d'Atlas lui-même."})
    return await call_next(request)

# Mount API routes
from api.routes import router as api_router
app.include_router(api_router, prefix="/api")

# Serve static UI files
UI_DIR = pathlib.Path(__file__).parent / "ui"
app.mount("/static", StaticFiles(directory=str(UI_DIR)), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(str(UI_DIR / "index.html"))


@app.get("/health")
async def health():
    from core.memory_manager import get_memory_manager
    mem = get_memory_manager()
    return {
        "status": "ok",
        "model": CONFIG["ollama"]["model"],
        "memory_connected": mem.is_connected(),
    }

# --------------------------------------------------------------------------- #
#  Launch
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    lock_ok, lock_msg = acquire_instance_lock()
    if not lock_ok:
        logger.error("⛔ %s", lock_msg)
        raise SystemExit(1)

    # Release here because the authoritative lock is held in lifespan.
    release_instance_lock()

    if not _is_port_free(HOST, PORT):
        logger.error("⛔ Port %d déjà occupé. Vérifiez qu'Atlas n'est pas déjà démarré.", PORT)
        raise SystemExit(1)

    actual_port = PORT

    logger.info("🚀 Atlas démarrage — %s:%d", HOST, actual_port)
    logger.info("📡 Modèle Ollama : %s", CONFIG["ollama"]["model"])
    logger.info("🌐 Interface : http://%s:%d", HOST, actual_port)

    # Important: éviter les boucles de reload causées par les écritures de logs/data.
    # Active le reload uniquement si demandé explicitement via ATLAS_RELOAD=1.
    reload_enabled = os.getenv("ATLAS_RELOAD", "0") == "1"

    uvicorn.run(
        "main:app",
        host=HOST,
        port=actual_port,
        reload=reload_enabled,
        reload_excludes=["logs/*", "data/*"],
        log_level="info",
    )
