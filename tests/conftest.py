"""
Configuration commune de la suite (sprint B-minimal, BM5 ; sprint Sans Docker, SD2).

Règle : aucun test ne lit ni n'écrit la mémoire ou les données réelles d'Atlas.

- Mémoire : depuis la sortie de Docker, ChromaDB est intégré (un DOSSIER). La suite reçoit un
  dossier jetable (ATLAS_CHROMA_PATH), créé avant la collecte. Deux gardes :
    * chromadb.PersistentClient refuse d'ouvrir la vraie base (data/chromadb du projet) ;
    * chromadb.HttpClient lève une erreur : plus aucun ChromaDB réseau n'existe.
- data/ : les chemins de données des modules sont redirigés vers un projet temporaire, qui
  contient une copie des 4 workflows modèles versionnés et de config/settings.json.
- api/routes.py calcule le chemin de data/ à partir de son propre __file__ (défaut produit,
  à centraliser en B-complet) : le module `pathlib` qu'il voit est remplacé par une copie
  dont Path(routes.__file__) pointe dans le projet temporaire.

Variable d'entrée : ATLAS_TEST_NO_CHROMA=1 simule une machine dont la mémoire est en panne.

Tests ignorés (sprint Check-up, CK4) : chaque test ignoré doit avoir une raison écrite dans
SKIPS_JUSTIFIES, ET la condition annoncée par cette raison doit être réellement réunie (Ollama
vraiment injoignable, fichier vraiment absent…). Sinon la suite échoue : un test ignoré sans
raison, ou dont la sonde est tombée sur une cause sans rapport (les 27 tests mémoire du sprint
Sans Docker), ne passe plus en silence. Le résumé compte et liste chaque test ignoré.

Variables exposées aux tests :
- ATLAS_TEST_CHROMA_PATH : dossier de la mémoire jetable (absent si ATLAS_TEST_NO_CHROMA=1)
- ATLAS_TEST_ROOT : racine du projet temporaire
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import types

import pytest

PROJECT_ROOT = pathlib.Path(__file__).resolve().parent.parent
REAL_CHROMA = (PROJECT_ROOT / "data" / "chromadb").resolve()
TEMPLATE_WORKFLOWS = ("demarrage_matin.yaml", "mode_gaming.yaml", "mode_travail.yaml", "nettoyage_systeme.yaml")

_state: dict = {"proc": None, "dirs": []}


def _isolate_chroma() -> pathlib.Path:
    import chromadb

    workdir = pathlib.Path(tempfile.mkdtemp(prefix="atlas_tests_chroma_"))
    _state["dirs"].append(workdir)
    if os.environ.get("ATLAS_TEST_NO_CHROMA") == "1":
        (workdir / "fichier").write_text("pas un dossier")
        path = workdir / "fichier" / "chromadb"          # ouverture impossible : mémoire en panne
    else:
        path = workdir / "chromadb"
        os.environ["ATLAS_TEST_CHROMA_PATH"] = str(path)
    os.environ["ATLAS_CHROMA_PATH"] = str(path)

    real_persistent = chromadb.PersistentClient

    def guarded_persistent(path=None, *args, **kwargs):
        if path is not None and pathlib.Path(str(path)).resolve() == REAL_CHROMA:
            raise RuntimeError("tests : la vraie mémoire (data/chromadb) est interdite")
        return real_persistent(path, *args, **kwargs) if path is not None else real_persistent(*args, **kwargs)

    def no_http(*args, **kwargs):
        raise RuntimeError("tests : aucun ChromaDB réseau depuis la sortie de Docker")

    guarded_persistent.original = real_persistent
    chromadb.PersistentClient = guarded_persistent
    chromadb.HttpClient = no_http

    import core.memory_manager as mm
    mm.CHROMA_PATH = str(path)
    mm._instance = None  # un singleton déjà créé pointerait encore vers l'ancienne cible
    return path


def _isolate_data() -> pathlib.Path:
    root = pathlib.Path(tempfile.mkdtemp(prefix="atlas_tests_root_"))
    _state["dirs"].append(root)
    data = root / "data"
    (data / "workflows").mkdir(parents=True)
    for name in TEMPLATE_WORKFLOWS:
        shutil.copy2(PROJECT_ROOT / "data" / "workflows" / name, data / "workflows" / name)
    (root / "config").mkdir()
    shutil.copy2(PROJECT_ROOT / "config" / "settings.json", root / "config" / "settings.json")

    import core.atlas_logger as atlas_logger
    import core.context_monitor as context_monitor
    import core.file_indexer as file_indexer
    import core.file_organizer as file_organizer
    import core.scheduler as scheduler
    import core.trigger_engine as trigger_engine
    import core.workflow_engine as workflow_engine
    import tools.app_launcher as app_launcher
    import tools.grounding as grounding
    import tools.system_config as system_config
    import api.routes as routes

    import core.apprentissage_store as apprentissage_store

    atlas_logger.LOG_FILE = data / "atlas_actions.jsonl"
    apprentissage_store.DB_PATH = data / "apprentissage.db"      # Apprentissage 2 : jamais le vrai
    context_monitor._DB_PATH = data / "habits.db"
    file_indexer.DATA_DIR, file_indexer.INDEX_FILE = data, data / "file_index.json"
    file_organizer.DATA_DIR, file_organizer.HISTORY_FILE = data, data / "file_reorg_history.jsonl"
    scheduler.DATA_DIR, scheduler.SCHEDULES_FILE = data, data / "schedules.json"
    trigger_engine.DATA_DIR, trigger_engine.TRIGGERS_FILE = data, data / "triggers.json"
    workflow_engine.DATA_DIR, workflow_engine.WORKFLOWS_DIR = data, data / "workflows"
    app_launcher.FILE_INDEX_PATH = data / "file_index.json"
    grounding._DEBUG_IMAGE_DIR = str(data / "debug")
    system_config._AUDIT_LOG_PATH = data / "audit_log.jsonl"

    routes_file = pathlib.Path(routes.__file__).resolve()
    fake_routes_file = root / "api" / "routes.py"
    real_path = pathlib.Path

    def redirected_path(*args, **kwargs):
        if len(args) == 1 and not kwargs and real_path(args[0]).resolve() == routes_file:
            return fake_routes_file
        return real_path(*args, **kwargs)

    shim = types.ModuleType("pathlib")
    shim.__dict__.update(pathlib.__dict__)
    shim.Path = redirected_path
    routes.pathlib = shim
    return root


def pytest_configure(config):
    sys.path.insert(0, str(PROJECT_ROOT))
    _isolate_chroma()
    # Dépôt + Ollama / C3 : hors de main.py, la mémoire est neutralisée. Ici, la mémoire est
    # un dossier JETABLE (ci-dessus) : on peut donc la brancher.
    os.environ["ATLAS_MEMORY"] = "real"
    os.environ["ATLAS_TEST_ROOT"] = str(_isolate_data())


@pytest.fixture(autouse=True)
def _bascules_vierges():
    """Sprint Check-up / CK2 : le registre des bascules est global au processus. Un test qui
    simule un composant absent ne doit pas faire dire sa bascule aux réponses des suivants."""
    from core_conversational.degradations import reinitialiser

    reinitialiser()
    yield
    reinitialiser()


# --------------------------------------------------------------------------- #
#  Sprint Check-up / CK4 — les tests ignorés, comptés et justifiés un par un
# --------------------------------------------------------------------------- #

def ollama_absent() -> bool:
    """Ollama injoignable, ou simulé absent (ATLAS_TEST_NO_OLLAMA=1). Sonde commune aux tests."""
    import socket

    if os.environ.get("ATLAS_TEST_NO_OLLAMA") == "1":
        return True
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1.0):
            return False
    except OSError:
        return True


def _cublas_pip_absent() -> bool:
    try:
        import nvidia

        return not any(pathlib.Path(p, "cublas", "bin", "cublas64_12.dll").exists() for p in nvidia.__path__)
    except Exception:
        return True


# (motif de la raison, justification, condition qui DOIT être vraie pour que l'abandon soit légitime)
SKIPS_JUSTIFIES = [
    (r"^Ollama (absent|injoignable)",
     "le test interroge le vrai Ollama, arrêté ou simulé absent (ATLAS_TEST_NO_OLLAMA=1)", ollama_absent),
    (r"^ChromaDB de test (non disponible|indisponible)",
     "mémoire de test en panne simulée (ATLAS_TEST_NO_CHROMA=1)",
     lambda: os.environ.get("ATLAS_TEST_NO_CHROMA") == "1"),
    (r"^modèle de mot d'éveil absent",
     "modèle Hey Atlas non téléchargé sur cette machine (scripts/download_voice_models.py)",
     lambda: not (PROJECT_ROOT / "models" / "wakewords" / "hey_atlas.onnx").exists()),
    (r"^voix Piper absente",
     "voix Piper non téléchargée sur cette machine (scripts/download_voice_models.py)",
     lambda: not (PROJECT_ROOT / "data" / "voices" / "fr_FR-siwis-medium.onnx").exists()),
    (r"^Windows uniquement", "vérification propre à Windows", lambda: os.name != "nt"),
    (r"^nvidia-cublas-cu12 absent", "paquet pip de cuBLAS absent de cet environnement", _cublas_pip_absent),
]

_SKIPS: dict[str, list] = {"justifies": [], "fautifs": []}


def _classer_skip(nodeid: str, longrepr) -> None:
    import re

    raison = longrepr[2] if isinstance(longrepr, tuple) else str(longrepr)
    raison = raison.removeprefix("Skipped: ").strip()
    for motif, justification, condition in SKIPS_JUSTIFIES:
        if re.search(motif, raison):
            if condition():
                _SKIPS["justifies"].append((nodeid, raison, justification))
            else:
                _SKIPS["fautifs"].append((nodeid, raison, "condition annoncée non réunie : la sonde est "
                                                          "tombée sur une autre cause"))
            return
    _SKIPS["fautifs"].append((nodeid, raison, "sans justification écrite (tests/conftest.py, SKIPS_JUSTIFIES)"))


def pytest_runtest_logreport(report):
    if report.skipped and not hasattr(report, "wasxfail"):
        _classer_skip(report.nodeid, report.longrepr)


def pytest_collectreport(report):
    if report.skipped:
        _classer_skip(report.nodeid, report.longrepr)


def pytest_sessionfinish(session, exitstatus):
    if _SKIPS["fautifs"] and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter):
    j, f = _SKIPS["justifies"], _SKIPS["fautifs"]
    terminalreporter.write_line(f"atlas: tests ignorés : {len(j) + len(f)} ({len(j)} justifié(s), {len(f)} fautif(s))")
    for nodeid, raison, pourquoi in j:
        terminalreporter.write_line(f"  justifié : {nodeid} — « {raison} » — {pourquoi}")
    for nodeid, raison, pourquoi in f:
        terminalreporter.write_line(f"  FAUTIF   : {nodeid} — « {raison} » — {pourquoi}", red=True)


def pytest_report_header(config):
    chemin = os.environ.get("ATLAS_TEST_CHROMA_PATH", "en panne (ATLAS_TEST_NO_CHROMA=1)")
    return [f"atlas: mémoire de test = {chemin}", f"atlas: données de test = {os.environ.get('ATLAS_TEST_ROOT')}"]


def pytest_unconfigure(config):
    for d in _state["dirs"]:
        for _ in range(10):  # Windows libère les fichiers SQLite/HNSW avec un léger délai
            shutil.rmtree(d, ignore_errors=True)
            if not d.exists():
                break
            time.sleep(0.5)
