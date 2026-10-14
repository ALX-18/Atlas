"""
Sprint Performance — Atlas sur une machine ordinaire, sans perdre en qualité.

Chaque test vérifie une seule chose, sans rien charger de lourd ni toucher à la mémoire réelle.
"""

import asyncio
import json
import os
import pathlib
import subprocess
import sys
import time
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- #
#  PF1 — mesurer Atlas complet sur une COPIE de la mémoire
# --------------------------------------------------------------------------- #

def test_pf1_atlas_peut_viser_un_chromadb_jetable():
    """ATLAS_CHROMA_PORT fait viser à Atlas un autre ChromaDB que la mémoire réelle (8001) :
    les mesures en scénario n'écrivent ainsi que dans une copie."""
    code = ("import core.memory_manager as mm; print(mm.CHROMA_HOST, mm.CHROMA_PORT)")
    env = {**os.environ, "ATLAS_CHROMA_PORT": "8101", "ATLAS_MEMORY": "off"}
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env=env, timeout=120)
    assert r.stdout.strip().splitlines()[-1] == "localhost 8101", r.stdout + r.stderr[-500:]


# --------------------------------------------------------------------------- #
#  PF2 — torch au démarrage, EasyOCR à la demande
# --------------------------------------------------------------------------- #

def test_pf2_le_message_gpu_du_demarrage_n_importe_plus_torch():
    """torch (~200 Mo) n'était chargé au démarrage QUE pour savoir s'il est compilé pour CUDA."""
    code = ("import sys, main; main._warn_if_voice_gpu_missing(True); "
            "print('torch' in sys.modules)")
    env = {**os.environ, "ATLAS_MEMORY": "off", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env=env, timeout=180)
    assert r.stdout.strip().splitlines()[-1] == "False", r.stdout[-300:] + r.stderr[-500:]


@pytest.fixture
def easyocr_simule(monkeypatch):
    """Un faux processus EasyOCR qui se compte ; aucune vraie charge."""
    import tools.grounding as g

    crees, annonces, arretes = [], [], []

    class FauxProcessus:
        def __init__(self):
            crees.append(self)

        def readtext(self, img):
            return []

        def stop(self):
            arretes.append(self)

    monkeypatch.setattr(g, "_start_easyocr_worker", FauxProcessus)
    monkeypatch.setattr(g, "_announce", lambda msg: annonces.append(msg))
    g._release_easyocr()
    crees.clear(), arretes.clear()
    yield g, crees, annonces, arretes
    g._release_easyocr()


def test_pf2_easyocr_charge_au_premier_usage_et_annonce(easyocr_simule):
    g, crees, annonces, _ = easyocr_simule
    assert g._EASYOCR_READER is None and crees == []
    asyncio.run(g._ensure_easyocr())
    asyncio.run(g._ensure_easyocr())
    assert len(crees) == 1, "chargé une seule fois"
    assert len(annonces) == 1 and "lecture de l'écran" in annonces[0], annonces


def test_pf2_easyocr_libere_apres_inactivite(easyocr_simule, monkeypatch):
    g, crees, annonces, arretes = easyocr_simule
    monkeypatch.setattr(g, "EASYOCR_IDLE_UNLOAD_S", 0.3)
    asyncio.run(g._ensure_easyocr())
    assert g._EASYOCR_READER is not None
    time.sleep(0.8)
    assert g._EASYOCR_READER is None, "toujours chargé après l'inactivité"
    assert arretes == crees[:1], "le processus EasyOCR n'a pas été arrêté"
    asyncio.run(g._ensure_easyocr())
    assert len(crees) == 2 and len(annonces) == 2, "rechargé, et annoncé à nouveau"


def test_pf2_le_vrai_processus_ocr_repond_puis_s_arrete(monkeypatch):
    """Le vrai processus (lecteur factice) : aller-retour, puis arrêt réel."""
    import numpy as np

    from tools.ocr_worker import EasyOCRWorker

    monkeypatch.setenv("ATLAS_OCR_WORKER_FAKE", "1")
    w = EasyOCRWorker()
    try:
        res = w.readtext(np.zeros((20, 20, 3), dtype=np.uint8))
        assert res and res[0][1] == "Fichier" and len(res[0][0]) == 4, res
    finally:
        w.stop()
    assert not w.alive(), "le processus OCR survit à l'arrêt"


def test_pf2_atlas_n_importe_ni_torch_ni_easyocr_pour_lire_l_ecran():
    code = ("import os, sys, asyncio, numpy as np; os.environ['ATLAS_OCR_WORKER_FAKE'] = '1'; "
            "import tools.grounding as g; g._announce = lambda m: None; "
            "r = asyncio.run(g._ensure_easyocr()); r.readtext(np.zeros((8, 8, 3), dtype=np.uint8)); "
            "g._release_easyocr(); print('torch' in sys.modules, 'easyocr' in sys.modules)")
    env = {**os.environ, "ATLAS_MEMORY": "off", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env=env, timeout=180)
    assert r.stdout.strip().splitlines()[-1] == "False False", r.stdout[-300:] + r.stderr[-500:]


def test_pf2_la_valeur_d_inactivite_vient_de_la_configuration():
    import tools.grounding as g

    cfg = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))
    assert g.EASYOCR_IDLE_UNLOAD_S == cfg["grounding"]["easyocr_idle_unload_s"]


# --------------------------------------------------------------------------- #
#  PF3 — embeddings ONNX : mêmes étapes que sentence-transformers
# --------------------------------------------------------------------------- #

def test_pf3_onnx_moyenne_sur_les_vrais_jetons_puis_normalise():
    import numpy as np

    from core_conversational.memory_core import _OnnxE5

    e = _OnnxE5.__new__(_OnnxE5)
    e._np = np
    e._tok = SimpleNamespace(encode_batch=lambda texts: [
        SimpleNamespace(ids=[0, 5, 2], attention_mask=[1, 1, 1]),
        SimpleNamespace(ids=[0, 2, 1], attention_mask=[1, 1, 0]),     # un jeton de remplissage
    ])
    hidden = np.array([[[1, 0], [3, 0], [2, 0]], [[0, 2], [0, 4], [9, 9]]], dtype=np.float32)
    e._sess = SimpleNamespace(run=lambda _o, feeds: [hidden])
    v = e.encode(["a", "b"])
    assert np.allclose(v[0], [1, 0]) and np.allclose(v[1], [0, 1]), v   # (9, 9) ignoré : masqué


def test_pf3_un_moteur_onnx_introuvable_retombe_sans_planter(monkeypatch):
    import core_conversational.memory_core as mc

    monkeypatch.setattr(mc, "_model", None)
    monkeypatch.setattr(mc, "_load_attempted", False)
    monkeypatch.setitem(sys.modules, "sentence_transformers",
                        SimpleNamespace(SentenceTransformer=lambda name: "repli"))
    mc.set_embedding_backend("onnx", str(ROOT / "dossier_qui_n_existe_pas"))
    try:
        assert mc._load_model() == "repli"
    finally:
        mc.set_embedding_backend("sentence-transformers", None)
        monkeypatch.setattr(mc, "_model", None)
        monkeypatch.setattr(mc, "_load_attempted", False)


# --------------------------------------------------------------------------- #
#  PF5.1 — la partie fixe de la consigne d'abord
# --------------------------------------------------------------------------- #

def test_pf5_la_partie_fixe_precede_ce_qui_change():
    from core.ollama_client import build_system_prompt

    a = build_system_prompt({"foreground_window": {"title": "A", "process": "a.exe"}, "cpu_usage": 14.8,
                             "ram_usage": 70}, memories=["souvenir un"])
    b = build_system_prompt({"foreground_window": {"title": "B", "process": "b.exe"}, "cpu_usage": 18.2,
                             "ram_usage": 71}, memories=["autre souvenir"])
    k = next(i for i, (x, y) in enumerate(zip(a, b)) if x != y)
    commun = a[:k]
    for fixe in ("RÈGLES", "CE QU'ATLAS SAIT FAIRE", "TON TRAVAIL"):
        assert fixe in commun, f"« {fixe} » est après la première partie variable"


def test_pf5_la_voix_garde_la_meme_partie_fixe_que_l_ecrit():
    from core.ollama_client import VOICE_RESPONSE_SUFFIX, build_system_prompt

    ecrit = build_system_prompt({"cpu_usage": 1, "ram_usage": 2})
    voix = build_system_prompt({"cpu_usage": 3, "ram_usage": 4}, extra_fixed=VOICE_RESPONSE_SUFFIX)
    fixe = ecrit.split("CONTEXTE DU PC")[0].rstrip()
    assert voix.startswith(fixe), "la voix ne partage pas le début de la consigne écrite"
    assert voix.index(VOICE_RESPONSE_SUFFIX.strip()) < voix.index("CONTEXTE DU PC")


# --------------------------------------------------------------------------- #
#  PF5.2 — préchauffage au démarrage, sans bloquer
# --------------------------------------------------------------------------- #

def test_pf5_prechauffage_meme_num_ctx_et_sans_bloquer(monkeypatch):
    import httpx

    import core.embeddings as emb
    import core.ollama_client as oc

    envoyes, embeds = [], []

    async def post(client, url, **kw):
        await asyncio.sleep(0.3)
        envoyes.append((url, kw.get("json")))
        return SimpleNamespace(status_code=200, raise_for_status=lambda: None, json=lambda: {})

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    monkeypatch.setattr(emb, "embed_query", lambda t: (time.sleep(0.3), embeds.append(t))[0])

    async def run():
        t = time.perf_counter()
        task = oc.prewarm()
        rendu = time.perf_counter() - t
        await task
        return rendu

    rendu = asyncio.run(run())
    assert rendu < 0.1, f"le préchauffage bloque ({rendu:.2f} s)"
    assert envoyes and envoyes[0][1]["options"]["num_ctx"] == oc.NUM_CTX, envoyes
    assert envoyes[0][1]["keep_alive"] == oc.KEEP_ALIVE
    assert embeds, "embeddings non préchauffés"


def test_pf5_main_lance_le_prechauffage():
    texte = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "prewarm()" in texte


# --------------------------------------------------------------------------- #
#  PF6 — une demande trop longue est refusée, la consigne n'est jamais coupée
# --------------------------------------------------------------------------- #

class _Memoire:
    def __init__(self):
        self.ingeres, self.session = [], []

    def recall_for_prompt(self, q):
        return []

    def recall_texts(self, q, top_k=5):
        return []

    def add_to_session(self, role, content):
        self.session.append((role, content))

    def ingest_conversation(self, *a, **k):
        self.ingeres.append(a)

    def __getattr__(self, name):
        return lambda *a, **k: None


@pytest.fixture
def api_sans_modele(monkeypatch):
    import api.routes as routes
    import core.intent_engine as ie
    import core.memory_manager as mm
    import core.ollama_client as oc
    from core import confirmation

    appels, executes = [], []
    mem = _Memoire()
    monkeypatch.setattr(mm, "_instance", mem)

    async def stream(*a, **k):
        appels.append("stream")
        yield "réponse"

    async def full(*a, **k):
        appels.append("full")
        return "réponse"

    monkeypatch.setattr(routes, "chat_stream", stream)
    monkeypatch.setattr(oc, "chat_stream", stream)
    monkeypatch.setattr(oc, "chat_full", full)
    for name in list(ie.TOOL_HANDLERS):
        monkeypatch.setitem(ie.TOOL_HANDLERS, name,
                            (lambda n: lambda args: executes.append(n) or {"success": True, "message": n})(name))
    monkeypatch.setattr(ie, "_save_action_to_memory", lambda *a, **k: None)
    confirmation._pending.clear()
    yield appels, executes, mem
    confirmation._pending.clear()


def _chiffres(texte):
    return texte.replace(" ", "").replace("\xa0", "").replace(" ", "")


def test_pf6_demande_trop_longue_refusee_sans_appel_ni_memoire(api_sans_modele):
    from api.models import ChatRequest
    from api.routes import chat_endpoint
    from core.ollama_client import MAX_REQUEST_CHARS

    appels, executes, mem = api_sans_modele
    texte = "ouvre steam " + "x" * MAX_REQUEST_CHARS
    r = asyncio.run(chat_endpoint(ChatRequest(message=texte, history=[])))
    assert "trop longue" in r["message"] and str(MAX_REQUEST_CHARS) in _chiffres(r["message"]), r
    assert appels == [] and executes == [] and mem.ingeres == [], (appels, executes, mem.ingeres)


def test_pf6_flux_web_refuse_aussi(api_sans_modele):
    from api.models import ChatRequest
    from api.routes import chat_stream_endpoint
    from core.ollama_client import MAX_REQUEST_CHARS

    appels, _, _ = api_sans_modele

    async def lire():
        resp = await chat_stream_endpoint(ChatRequest(message="x" * (MAX_REQUEST_CHARS + 1), history=[]))
        return "".join([chunk async for chunk in resp.body_iterator])

    flux = asyncio.run(lire())
    assert "trop longue" in flux and appels == [], flux[:300]


def test_pf6_une_demande_a_la_limite_passe(api_sans_modele):
    from api.models import ChatRequest
    from api.routes import chat_endpoint
    from core.ollama_client import MAX_REQUEST_CHARS

    r = asyncio.run(chat_endpoint(ChatRequest(message="raconte " + "a" * (MAX_REQUEST_CHARS - 8), history=[])))
    assert "trop longue" not in (r.get("message") or ""), r


def test_pf6_la_voix_refuse_aussi(monkeypatch):
    import core.context_monitor as cm
    import core.memory_manager as mm
    import core.world_state as wsm
    from core.ollama_client import MAX_REQUEST_CHARS
    from core.voice_engine import VoiceEngine

    monkeypatch.setattr(cm, "collect_context", lambda: {})
    monkeypatch.setattr(mm, "get_memory_manager", lambda: _Memoire())
    monkeypatch.setattr(wsm, "get_world_state", lambda: SimpleNamespace(update_from_context=lambda c: None,
                                                                         add_to_history=lambda *a: None))
    dit = asyncio.run(VoiceEngine.__new__(VoiceEngine)._run_text_pipeline("x" * (MAX_REQUEST_CHARS + 1)))
    assert "trop longue" in dit, dit


def test_pf6_la_plus_longue_demande_admise_tient_avec_la_consigne_la_plus_lourde():
    """Consigne vocale + 9 souvenirs longs + la plus longue demande admise : sous le budget."""
    from core.ollama_client import MAX_REQUEST_CHARS, NUM_CTX, VOICE_RESPONSE_SUFFIX, build_system_prompt
    from core_conversational.llm_client import OUTPUT_RESERVE_TOKENS, estimate_messages_tokens

    consigne = build_system_prompt({"foreground_window": {"title": "t" * 200, "process": "p.exe"}, "cpu_usage": 50,
                                    "ram_usage": 50}, memories=["m" * 600] * 9, extra_fixed=VOICE_RESPONSE_SUFFIX)
    msgs = [{"role": "system", "content": consigne}, {"role": "user", "content": "x" * MAX_REQUEST_CHARS}]
    assert estimate_messages_tokens(msgs) <= NUM_CTX - OUTPUT_RESERVE_TOKENS
