"""
Sprint pré-beta — ce qui casserait chez un proche.

PB1 — une taille de contexte explicite (num_ctx), la même pour toutes les requêtes au modèle,
      et une garde déterministe : l'historique est raccourci, jamais la consigne ni la demande.
PB2 — logs\\ créé au démarrage : un clone neuf ne plante plus à l'import de main.py.
PB3 — collect_context sous 0,2 s : la liste des processus et le CPU ne bloquent plus la demande.
PB4 — doctor.py signale Ollama exposé au réseau, sa version, et le modèle.
PB5 — les deux tests de grounding sont ignorés, pas en échec, quand Ollama est absent.

Requêtes, processus et réseau SIMULÉS : rien n'est envoyé au vrai modèle, rien n'est exécuté.
"""

import asyncio
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SETTINGS = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
NUM_CTX = SETTINGS["ollama"]["context_window"]


# --------------------------------------------------------------------------- #
#  PB1 — num_ctx partout, une seule valeur
# --------------------------------------------------------------------------- #

class _FakeStream:
    """Remplace httpx.AsyncClient.stream : garde la requête, renvoie une réponse vide."""

    sent: list = []

    def __init__(self, client, method, url, **kw):
        _FakeStream.sent.append(kw.get("json"))

    async def __aenter__(self):
        async def lines():
            yield json.dumps({"message": {"content": "ok"}, "done": True})
        return SimpleNamespace(raise_for_status=lambda: None, aiter_lines=lines)

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def envoyes(monkeypatch):
    import httpx

    _FakeStream.sent = []
    monkeypatch.setattr(httpx.AsyncClient, "stream", lambda c, m, u, **kw: _FakeStream(c, m, u, **kw))

    async def post(client, url, **kw):
        _FakeStream.sent.append(kw.get("json"))
        return SimpleNamespace(raise_for_status=lambda: None,
                               json=lambda: {"message": {"content": "résumé"}, "response": "{}"})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    return _FakeStream.sent


def test_pb1_la_valeur_unique_est_dans_la_configuration():
    import core.ollama_client as oc

    assert NUM_CTX == 8192
    assert oc.NUM_CTX == NUM_CTX, "la configuration n'est pas lue (context_window était annoncé, jamais appliqué)"


def _num_ctx(payload):
    return (payload or {}).get("options", {}).get("num_ctx")


def test_pb1_conversation_en_flux(envoyes):
    from core.ollama_client import chat_stream

    async def run():
        return [t async for t in chat_stream("bonjour", {})]

    asyncio.run(run())
    assert envoyes and _num_ctx(envoyes[-1]) == NUM_CTX, envoyes[-1].get("options")


def test_pb1_planification_et_voix(envoyes):
    """chat_full avec une consigne fournie : le chemin de la planification et de la voix."""
    from core.ollama_client import chat_full, generate_speech_response

    asyncio.run(chat_full("planifie", {}, system_prompt="Tu planifies."))
    asyncio.run(generate_speech_response("bonjour", {}))
    assert len(envoyes) >= 2
    assert all(_num_ctx(p) == NUM_CTX for p in envoyes), [p.get("options") for p in envoyes]


def test_pb1_resume_d_une_page_web(envoyes, monkeypatch):
    import tools.web_reader as wr

    async def page(url, max_chars=0):
        return {"success": True, "url": url, "title": "t", "content": "texte", "word_count": 1, "truncated": False}

    monkeypatch.setattr(wr, "read_url", page)
    asyncio.run(wr.summarize_url("https://exemple.org"))
    assert envoyes and _num_ctx(envoyes[-1]) == NUM_CTX, envoyes[-1]


def test_pb1_client_conversationnel_partage():
    from core_conversational.llm_client import LLMClient

    payload = LLMClient()._payload("consigne", "bonjour", [])
    assert _num_ctx(payload) == NUM_CTX, payload.get("options")


def test_pb1_vision():
    import tools.grounding as g

    payload = g._vision_payload("minicpm-v", "trouve le bouton", "aW1hZ2U=")
    assert _num_ctx(payload) == NUM_CTX, payload


# --------------------------------------------------------------------------- #
#  PB1 — garde de dépassement
# --------------------------------------------------------------------------- #

def _historique(n, taille):
    h = []
    for i in range(n):
        h.append({"role": "user", "content": f"question {i} " + "q" * taille})
        h.append({"role": "assistant", "content": f"réponse {i} " + "r" * taille})
    return h


def test_pb1_une_conversation_qui_tient_n_est_pas_touchee(envoyes):
    from core.ollama_client import chat_stream

    histo = _historique(10, 300)

    async def run():
        return [t async for t in chat_stream("et ensuite ?", {}, history=histo)]

    asyncio.run(run())
    msgs = envoyes[-1]["messages"]
    assert msgs[1:-1] == histo


def test_pb1_le_depassement_raccourcit_l_historique_jamais_la_consigne(envoyes):
    from core.ollama_client import build_system_prompt, chat_stream
    from core_conversational.llm_client import estimate_messages_tokens

    histo = _historique(40, 1500)          # ~120 000 caractères : bien au-delà de 8 192 jetons
    demande = "et pour finir, la toute dernière question ?"

    async def run():
        return [t async for t in chat_stream(demande, {}, history=histo)]

    asyncio.run(run())
    msgs = envoyes[-1]["messages"]
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == build_system_prompt({}), "consigne modifiée"
    assert msgs[-1] == {"role": "user", "content": demande}, "demande en cours modifiée"
    gardes = msgs[1:-1]
    assert 0 < len(gardes) < len(histo), "l'historique devait être raccourci, pas supprimé"
    assert gardes == histo[-len(gardes):], "on retire les plus ANCIENS, dans l'ordre"
    assert gardes[0]["role"] == "user", "l'historique gardé commence par une question"
    assert estimate_messages_tokens(msgs) <= NUM_CTX - 1024


def test_pb1_l_estimation_ne_sous_estime_pas_le_cas_mesure():
    """Cas réel mesuré au sprint Dépôt + Ollama : 17 786 caractères, 22 messages → 5 261 jetons."""
    from core_conversational.llm_client import estimate_messages_tokens

    msgs = [{"role": "user", "content": "x" * (17786 // 22)} for _ in range(22)]
    assert estimate_messages_tokens(msgs) >= 5261


# --------------------------------------------------------------------------- #
#  PB2 — un clone neuf démarre sans « mkdir logs »
# --------------------------------------------------------------------------- #

def test_pb2_import_de_main_sans_dossier_logs(tmp_path):
    fichiers = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    for f in filter(None, fichiers):
        src = ROOT / f
        if src.is_file():
            dst = tmp_path / f
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    assert not (tmp_path / "logs").exists()
    env = {**os.environ, "ATLAS_MEMORY": "off", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", "import main"], cwd=tmp_path, capture_output=True, text=True,
                       timeout=180, env=env)
    assert r.returncode == 0, r.stderr[-1500:]
    assert (tmp_path / "logs" / "atlas.log").exists()


# --------------------------------------------------------------------------- #
#  PB3 — collect_context ne bloque plus la demande
# --------------------------------------------------------------------------- #

@pytest.fixture
def machine_lente(monkeypatch):
    """Les mesures lentes d'avant (1,6 s de processus, 0,3 s de CPU) deviennent encore plus lentes."""
    import psutil

    import core.context_monitor as cm

    cm.stop_sampler()
    vraie_cpu = psutil.cpu_percent

    def cpu_lent(interval=None, **kw):
        if interval:
            time.sleep(interval + 1.0)
        return 12.5

    monkeypatch.setattr(cm.psutil, "cpu_percent", cpu_lent)
    monkeypatch.setattr(cm, "_get_gpu_usage", lambda: (time.sleep(0.5), 33.0)[1])
    monkeypatch.setattr(cm, "_process_snapshot", lambda: (time.sleep(0.5), {
        4: {"name": "System", "rss": 1 << 20, "cpu100ns": 0},
        100: {"name": "steam.exe", "rss": 500 << 20, "cpu100ns": 10_000_000},
        200: {"name": "notepad.exe", "rss": 20 << 20, "cpu100ns": 0},
    })[1])
    monkeypatch.setattr(cm, "_track_process_habits", lambda ctx: None)
    yield cm
    cm.stop_sampler()
    psutil.cpu_percent = vraie_cpu


def test_pb3_collect_context_repond_en_moins_de_0_2_s(machine_lente):
    cm = machine_lente
    cm.start_sampler(interval=0.2)
    assert cm.wait_first_sample(timeout=5), "aucun échantillon"
    durees = []
    for _ in range(5):
        t = time.perf_counter()
        ctx = cm.collect_context()
        durees.append(time.perf_counter() - t)
    assert max(durees) < 0.2, f"collect_context : {[round(d, 3) for d in durees]} s"
    # Même contenu qu'avant
    for cle in ("timestamp", "foreground_window", "running_processes", "audio_active_processes", "cpu_usage",
                "ram_usage", "ram_available_gb", "gpu_usage", "disk_usage", "network_active_processes"):
        assert cle in ctx, cle
    assert ctx["cpu_usage"] == 12.5 and ctx["gpu_usage"] == 33.0
    noms = [p["name"] for p in ctx["running_processes"]]
    assert noms[0] == "steam.exe", noms


def test_pb3_le_fil_s_arrete_et_ne_survit_pas(machine_lente):
    cm = machine_lente
    cm.start_sampler(interval=0.2)
    cm.start_sampler(interval=0.2)          # idempotent : un seul fil
    fils = [t for t in threading.enumerate() if t.name == "atlas-context-sampler"]
    assert len(fils) == 1 and fils[0].daemon, fils
    cm.stop_sampler(timeout=3)
    assert not [t for t in threading.enumerate() if t.name == "atlas-context-sampler" and t.is_alive()]


def test_pb3_main_demarre_et_arrete_l_echantillonneur():
    texte = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "start_sampler(" in texte and "stop_sampler(" in texte


def test_pb3_l_instantane_des_processus_est_coherent_avec_psutil():
    """Sur la vraie machine : l'appel système unique voit les mêmes processus que psutil."""
    import psutil

    import core.context_monitor as cm

    if os.name != "nt":
        pytest.skip("Windows uniquement")
    snap = cm._process_snapshot()
    assert snap is not None, "instantané Windows en échec : Atlas retomberait sur psutil (CK4 : plus ignoré)"
    moi = os.getpid()
    assert moi in snap and snap[moi]["name"].lower().startswith("python")
    communs = set(snap) & set(psutil.pids())
    assert len(communs) >= 0.9 * len(psutil.pids())


# --------------------------------------------------------------------------- #
#  PB4 — doctor.py vérifie Ollama
# --------------------------------------------------------------------------- #

def _doctor():
    sys.path.insert(0, str(ROOT / "scripts"))
    import doctor

    return doctor


@pytest.mark.parametrize("adresses,attendu", [
    (["0.0.0.0"], False), (["::"], False), (["127.0.0.1", "0.0.0.0"], False), (["192.168.1.20"], False),
    (["127.0.0.1"], True), (["::1", "127.0.0.1"], True),
])
def test_pb4_ollama_expose_au_reseau(adresses, attendu):
    d = _doctor()
    c = d.ollama_exposure_check(adresses)
    assert c.ok is attendu, (adresses, c)
    if not attendu:
        assert c.severity == d.WARNING and "Expose Ollama to the network" in c.fix, c.fix


def test_pb4_ollama_ne_tourne_pas():
    d = _doctor()
    assert d.ollama_exposure_check([]).ok is True     # rien n'écoute : la joignabilité le dit déjà


@pytest.mark.parametrize("version,attendu", [("0.40.3", True), ("0.40.2", False), ("0.41.0", False), (None, False)])
def test_pb4_version_comparee_a_la_reference(version, attendu):
    d = _doctor()
    assert d.OLLAMA_REFERENCE_VERSION == "0.40.3"
    c = d.ollama_version_check(version)
    assert c.ok is attendu and c.severity == d.WARNING, c
    assert "0.40.3" in (c.detail + c.fix)


def test_pb4_check_ollama_ajoute_version_et_exposition(monkeypatch):
    d = _doctor()

    def http(url, timeout=3.0):
        return True, json.dumps({"version": "0.40.3"}) if url.endswith("/api/version") else "{}"

    monkeypatch.setattr(d, "_http_get", http)
    monkeypatch.setattr(d, "body_full", lambda url, timeout=5.0: json.dumps({"models": [{"name": "qwen2.5:7b"}]}))
    monkeypatch.setattr(d, "_ollama_listen_addresses", lambda: ["0.0.0.0"])
    noms = {c.name: c for c in d.check_ollama({"ollama": {"model": "qwen2.5:7b"}})}
    assert any("réseau" in n for n in noms), list(noms)
    assert any("Version" in n for n in noms), list(noms)
    assert noms["Modèle configuré 'qwen2.5:7b' présent"].ok


# --------------------------------------------------------------------------- #
#  PB5 — sans Ollama, les deux tests de grounding sont ignorés
# --------------------------------------------------------------------------- #

def test_pb5_les_deux_tests_sont_ignores_sans_ollama():
    cibles = ["tests/test_sprint_kimi_understanding_v51.py::test_grounding_layer_order_steam_includes_heuristic",
              "tests/test_vision_parsers.py::TestGroundingTimeoutEnforced::test_layer_timeout_aborts_slow_layer"]
    env = {**os.environ, "ATLAS_TEST_NO_OLLAMA": "1", "ATLAS_TEST_NO_CHROMA": "1", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rs", *cibles],
                       cwd=ROOT, capture_output=True, text=True, timeout=300, env=env)
    assert "2 skipped" in r.stdout and "failed" not in r.stdout, r.stdout[-1500:]
