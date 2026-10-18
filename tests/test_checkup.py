"""
Sprint Check-up — chaque composant sert-il vraiment, et comme on le croit ?

Tests écrits AVANT le code, sans exception (règle de ce sprint).
"""

import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _py(code, env_extra=None, timeout=180):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "ATLAS_MEMORY": "off", **(env_extra or {})}
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=timeout)


# --------------------------------------------------------------------------- #
#  CK1 — mesure dynamique : les modules réellement chargés
# --------------------------------------------------------------------------- #

def test_ck1_atlas_ecrit_ses_modules_charges(tmp_path):
    sortie = tmp_path / "atlas.json"
    r = _py("import main; main._dump_modules()", {"ATLAS_MODULES_DUMP": str(sortie)})
    assert r.returncode == 0, r.stderr[-800:]
    d = json.loads(sortie.read_text(encoding="utf-8"))
    assert d["processus"] == "atlas" and "fastapi" in d["modules"] and "torch" not in d["modules"], d.get("processus")


def test_ck1_sans_la_variable_rien_n_est_ecrit(tmp_path):
    r = _py("import main; main._dump_modules(); print('ok')")
    assert r.returncode == 0 and r.stdout.strip().endswith("ok"), r.stderr[-500:]


def test_ck1_le_processus_ocr_ecrit_aussi_ses_modules(tmp_path):
    sortie = tmp_path / "ocr.json"
    code = ("import numpy as np; from tools.ocr_worker import EasyOCRWorker; w = EasyOCRWorker(); "
            "w.readtext(np.zeros((8, 8, 3), dtype=np.uint8)); w.stop()")
    r = _py(code, {"ATLAS_MODULES_DUMP": str(sortie), "ATLAS_OCR_WORKER_FAKE": "1"})
    assert r.returncode == 0, r.stderr[-800:]
    fichiers = list(tmp_path.glob("ocr*.json"))
    assert fichiers, "aucun fichier écrit par le processus OCR"
    d = json.loads(fichiers[0].read_text(encoding="utf-8"))
    assert d["processus"] == "ocr_worker"


def test_ck1_le_processus_ocr_ecrit_ses_modules_meme_tue(tmp_path):
    """Arrêt brutal (Ctrl+Pause reçu avec Atlas, ou kill) : la liste est déjà écrite après une lecture."""
    sortie = tmp_path / "ocr.json"
    code = ("import numpy as np; from tools.ocr_worker import EasyOCRWorker; w = EasyOCRWorker(); "
            "w.readtext(np.zeros((8, 8, 3), dtype=np.uint8)); w._proc.kill(); w._proc.wait(5)")
    r = _py(code, {"ATLAS_MODULES_DUMP": str(sortie), "ATLAS_OCR_WORKER_FAKE": "1"})
    assert r.returncode == 0, r.stderr[-800:]
    fichiers = list(tmp_path.glob("ocr*.json"))
    assert fichiers, "aucun fichier écrit par le processus OCR tué"
    assert json.loads(fichiers[0].read_text(encoding="utf-8"))["processus"] == "ocr_worker"


# --------------------------------------------------------------------------- #
#  CK2 — aucune dégradation silencieuse
# --------------------------------------------------------------------------- #

import ast
import asyncio
import logging
import re
import types

PROD_DIRS = ("api", "core", "core_conversational", "tools", "desktop")


def _fichiers_prod():
    return [ROOT / "main.py"] + [p for d in PROD_DIRS for p in sorted((ROOT / d).rglob("*.py"))]


def _rel(f) -> str:
    return str(f.relative_to(ROOT)).replace("\\", "/")


@pytest.fixture
def registre():
    from core_conversational import degradations as dg

    dg.reinitialiser()
    yield dg
    dg.reinitialiser()


def _cles(dg) -> list[str]:
    return [b["cle"] for b in dg.actives()]


def test_ck2_une_bascule_est_journalisee_une_fois_avec_sa_cause(registre, caplog):
    with caplog.at_level(logging.WARNING):
        registre.signaler("tesseract", "binaire introuvable")
        registre.signaler("tesseract", "binaire introuvable")
    lignes = [r for r in caplog.records if r.levelno == logging.WARNING and "binaire introuvable" in r.getMessage()]
    assert len(lignes) == 1, [r.getMessage() for r in caplog.records]


def test_ck2_une_cle_hors_catalogue_est_refusee(registre):
    with pytest.raises(KeyError):
        registre.signaler("bascule_inventee", "x")


def test_ck2_le_catalogue_dit_ce_que_l_utilisateur_perd(registre):
    assert len(registre.CATALOGUE) >= 10
    for cle, b in registre.CATALOGUE.items():
        assert b["composant"] and b["perte"], cle
        if b["vecue"]:
            assert b["message"], f"{cle} : bascule vécue sans phrase pour la dire"


def test_ck2_chaque_bascule_du_catalogue_est_branchee():
    """Rien d'annoncé que le code ne signale, rien de signalé hors catalogue."""
    from core_conversational.degradations import CATALOGUE

    appels = set()
    for f in _fichiers_prod():
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and (getattr(n.func, "attr", None) or getattr(n.func, "id", None)) == "signaler" \
                    and n.args and isinstance(n.args[0], ast.Constant):
                appels.add(n.args[0].value)
    assert set(CATALOGUE) - appels == set(), "au catalogue mais jamais signalées"
    assert appels - set(CATALOGUE) == set(), "signalées mais absentes du catalogue"


def test_ck2_aucun_except_importerror_silencieux():
    """Un composant absent à l'import est signalé (signaler) ou l'erreur remonte (raise)."""
    fautifs = []
    for f in _fichiers_prod():
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.ExceptHandler) and n.type is not None and "ImportError" in ast.unparse(n.type):
                corps = ast.unparse(ast.Module(body=n.body, type_ignores=[]))
                if "signaler(" not in corps and "raise" not in corps:
                    fautifs.append(f"{_rel(f)}:{n.lineno}")
    assert fautifs == []


def test_ck2_health_montre_les_bascules(registre):
    from api.routes import api_health

    registre.signaler("embeddings_onnx", "modèle ONNX introuvable")
    h = asyncio.run(api_health())
    b = {x["cle"]: x for x in h["bascules"]}
    assert b["embeddings_onnx"]["cause"] == "modèle ONNX introuvable" and b["embeddings_onnx"]["perte"]


def test_ck2_la_premiere_reponse_dit_la_bascule_une_seule_fois(registre):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    registre.signaler("embeddings_onnx", "modèle ONNX introuvable")
    phrase = registre.CATALOGUE["embeddings_onnx"]["message"]
    r1 = asyncio.run(chat_endpoint(ChatRequest(message="tu peux faire quoi ?", history=[])))
    r2 = asyncio.run(chat_endpoint(ChatRequest(message="tu peux faire quoi ?", history=[])))
    assert phrase in r1["message"] and phrase not in r2["message"]


def test_ck2_une_bascule_sans_effet_vecu_n_est_pas_dite(registre):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    cle = next(k for k, b in registre.CATALOGUE.items() if not b["vecue"])
    registre.signaler(cle, "essai")
    r = asyncio.run(chat_endpoint(ChatRequest(message="tu peux faire quoi ?", history=[])))
    assert "ℹ️" not in (r["message"] or "")


def test_ck2_la_voix_dit_aussi_la_bascule(registre):
    from core.voice_engine import VoiceEngine

    registre.signaler("stt_gpu", "cuBLAS absent")
    dit = asyncio.run(VoiceEngine()._run_text_pipeline("tu peux faire quoi ?"))
    assert registre.CATALOGUE["stt_gpu"]["message"] in dit


def test_ck2_atlas_annonce_au_demarrage_ce_qui_manque(registre, monkeypatch):
    import main

    dits = []
    monkeypatch.setattr(main, "_notifier", lambda message: dits.append(message))
    registre.signaler("tesseract", "binaire introuvable")
    main._annoncer_bascules()
    assert dits and registre.CATALOGUE["tesseract"]["message"] in dits[0]


def test_ck2_onnx_absent_est_signale(registre, monkeypatch):
    import core_conversational.memory_core as mc

    faux = types.ModuleType("sentence_transformers")
    faux.SentenceTransformer = lambda name: object()
    monkeypatch.setitem(sys.modules, "sentence_transformers", faux)
    monkeypatch.setattr(mc, "_model", None)
    monkeypatch.setattr(mc, "_load_attempted", False)
    monkeypatch.setattr(mc, "_backend", "onnx")
    monkeypatch.setattr(mc, "_onnx_dir", str(ROOT / "dossier_qui_n_existe_pas"))
    mc._load_model()
    assert "embeddings_onnx" in _cles(registre)


def test_ck2_aucun_moteur_d_embeddings_est_signale(registre, monkeypatch):
    import core_conversational.memory_core as mc

    def casse(name):
        raise OSError("modèle illisible")

    faux = types.ModuleType("sentence_transformers")
    faux.SentenceTransformer = casse
    monkeypatch.setitem(sys.modules, "sentence_transformers", faux)
    monkeypatch.setattr(mc, "_model", None)
    monkeypatch.setattr(mc, "_load_attempted", False)
    monkeypatch.setattr(mc, "_backend", "sentence-transformers")
    mc._load_model()
    assert "embeddings_absents" in _cles(registre)


def test_ck2_transcription_repliee_sur_processeur_est_signalee(registre, monkeypatch):
    import core.voice_engine as ve

    def charge(cls, name, device):
        if device == "cuda":
            raise RuntimeError("cublas64_12.dll introuvable")
        return types.SimpleNamespace(transcribe=lambda *a, **k: ([], None))

    monkeypatch.setattr(ve, "_load_whisper", charge)
    monkeypatch.setattr(ve, "ensure_cuda_libraries", lambda: (True, "ok"))
    e = ve.VoiceEngine()
    e._config = {**e._config, "stt_device": "cuda"}
    monkeypatch.setattr(e, "_app_names_prompt", lambda: None)
    asyncio.run(e._transcribe(b"\x00\x00" * 1600))
    assert "stt_gpu" in _cles(registre)


def test_ck2_synthese_repliee_puis_muette_est_signalee(registre, monkeypatch):
    from core.voice_engine import VoiceEngine

    e = VoiceEngine()
    monkeypatch.setattr(e, "_speak_piper", lambda t: False)
    monkeypatch.setattr(e, "_speak_sapi", lambda t: True)
    e._speak_sync("bonjour")
    assert "tts_piper" in _cles(registre)
    monkeypatch.setattr(e, "_speak_sapi", lambda t: False)
    e._speak_sync("bonjour")
    assert "tts_muet" in _cles(registre)


def test_ck2_easyocr_indisponible_est_signale(registre, monkeypatch):
    import tools.grounding as g

    def echec():
        raise RuntimeError("torch introuvable")

    monkeypatch.setattr(g, "_EASYOCR_READER", None)
    monkeypatch.setattr(g, "_EASYOCR_ATTEMPTED", False)
    monkeypatch.setattr(g, "_start_easyocr_worker", echec)
    g._get_easyocr_reader()
    assert "easyocr" in _cles(registre)


def test_ck2_uia_indisponible_est_signale(registre, monkeypatch):
    import tools.grounding as g

    monkeypatch.setitem(sys.modules, "pywinauto", None)
    asyncio.run(g._try_uia("AtlasFenetreQuiNExistePas", "Bouton"))
    assert "uia" in _cles(registre)


@pytest.mark.parametrize("etat,signale", [("en_panne", True), ("verrouillee", True), ("ok", False),
                                          ("neutralisee", False)])
def test_ck2_memoire_indisponible_au_demarrage_est_signalee(registre, etat, signale):
    import main

    main._verifier_memoire(types.SimpleNamespace(status=lambda: {"etat": etat, "detail": "essai"}))
    assert ("memoire" in _cles(registre)) is signale


def test_ck2_lecture_d_ecran_par_easyocr_fonctionne(monkeypatch):
    """Régression du sprint Performance : le processus OCR ne prend pas « detail=0 »."""
    import pytesseract
    from PIL import Image

    import tools.grounding as g
    import tools.screen_reader as sr

    class Lecteur:
        def readtext(self, image):
            return [([[0, 0], [1, 0], [1, 1], [0, 1]], "Bibliothèque", 0.9)]

    monkeypatch.setattr(pytesseract, "image_to_string", lambda *a, **k: "")
    monkeypatch.setattr(g, "_get_easyocr_reader", lambda: Lecteur())
    assert sr._ocr_text(Image.new("RGB", (8, 8))) == "Bibliothèque"


def _doctor():
    sys.path.insert(0, str(ROOT / "scripts"))
    import doctor

    return doctor


def test_ck2_doctor_montre_les_bascules_d_atlas(monkeypatch):
    doctor = _doctor()
    sante = {"bascules": [{"cle": "embeddings_onnx", "composant": "Embeddings", "cause": "modèle ONNX introuvable",
                           "perte": "rappel plus lent"}]}
    monkeypatch.setattr(doctor, "_atlas_health", lambda: sante)
    checks = doctor.check_bascules()
    assert any(not c.ok and "modèle ONNX introuvable" in c.detail for c in checks)


def test_ck2_doctor_sans_atlas_verifie_les_conditions_des_bascules(monkeypatch):
    doctor = _doctor()
    monkeypatch.setattr(doctor, "_atlas_health", lambda: None)
    noms = " | ".join(c.name for c in doctor.check_bascules())
    for attendu in ("ONNX", "EasyOCR", "Piper"):
        assert attendu in noms, noms


# --------------------------------------------------------------------------- #
#  CK5 — Tesseract et sa langue fra, vérifiés et signalés
# --------------------------------------------------------------------------- #

def test_ck5_tesseract_absent_est_signale(registre, monkeypatch):
    import pytesseract

    import tools.grounding as g

    def absent(*a, **k):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr(pytesseract, "get_tesseract_version", absent)
    etat = g.tesseract_etat(rafraichir=True)
    assert etat["ok"] is False and "tesseract" in _cles(registre)


def test_ck5_tesseract_sans_francais_est_signale(registre, monkeypatch):
    import pytesseract

    import tools.grounding as g

    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.5.0")
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "osd"])
    etat = g.tesseract_etat(rafraichir=True)
    assert etat["ok"] is True and etat["fra"] is False and "tesseract_fra" in _cles(registre)


def test_ck5_tesseract_complet_rien_n_est_signale(registre, monkeypatch):
    import pytesseract

    import tools.grounding as g

    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.5.0")
    monkeypatch.setattr(pytesseract, "get_languages", lambda config="": ["eng", "fra", "osd"])
    etat = g.tesseract_etat(rafraichir=True)
    assert etat["ok"] and etat["fra"] and _cles(registre) == []


# --------------------------------------------------------------------------- #
#  CK3 — chaque clé de configuration est lue ; une clé lue absente a un défaut documenté
# --------------------------------------------------------------------------- #

# Exceptions justifiées : clé conservée alors qu'aucun code ne la lit.
CLES_EXCEPTIONS = {
    "steam_games": "table des jeux Steam d'Alexis, conservée pour le sprint qui reliera "
                   "app_launcher.launch_steam_game (une fonction : hors du périmètre Check-up)",
}
# Récepteurs qui désignent la configuration (CONFIG, cfg, _WEB_CFG, self._config, _rules…).
_RECEPTEUR_CONFIG = re.compile(r"(config|cfg|settings|_rules)", re.I)
_CODE_CONFIG = [ROOT / "main.py"] + [p for d in (*PROD_DIRS, "scripts") for p in sorted((ROOT / d).rglob("*.py"))
                                     if "manual" not in p.parts]


def _settings() -> dict:
    return json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))


def _feuilles(d: dict, chemin=()):
    for k, v in d.items():
        if k.startswith("_"):            # commentaires (_note…, _previous…)
            continue
        yield chemin + (k,)
        if isinstance(v, dict):
            yield from _feuilles(v, chemin + (k,))


def _lectures():
    """(fichier, ligne, récepteur, clé, avec_défaut) pour chaque .get("clé"…) et ["clé"] du code."""
    out = []
    for f in _CODE_CONFIG:
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("get", "setdefault") \
                    and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                out.append((_rel(f), n.lineno, ast.unparse(n.func.value), n.args[0].value, len(n.args) > 1))
            elif isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant) and isinstance(n.slice.value, str):
                out.append((_rel(f), n.lineno, ast.unparse(n.value), n.slice.value, False))
    return out


def test_ck3_chaque_cle_de_settings_est_lue_par_le_code():
    lues = {cle for *_, cle, _ in _lectures()}
    mortes = [".".join(c) for c in _feuilles(_settings())
              if c[0] not in CLES_EXCEPTIONS and not all(k in lues for k in c)]
    assert mortes == [], "clés que personne ne lit (les relier, les retirer, ou justifier l'exception)"


def test_ck3_une_cle_lue_mais_absente_a_un_defaut_documente():
    presentes = {k for c in _feuilles(_settings()) for k in c}
    doc = (ROOT / "docs" / "CONFIGURATION.md").read_text(encoding="utf-8")
    fautes = []
    for f, l, recepteur, cle, defaut in _lectures():
        if not _RECEPTEUR_CONFIG.search(recepteur) or cle in presentes:
            continue
        if not defaut:
            fautes.append(f"{f}:{l} {recepteur}[{cle!r}] lue sans défaut et absente de settings.json")
        elif f"`{cle}`" not in doc:
            fautes.append(f"{f}:{l} {cle!r} : défaut non documenté dans docs/CONFIGURATION.md")
    assert fautes == []


def test_ck3_les_exceptions_sont_justifiees_et_existent():
    s = _settings()
    for cle, raison in CLES_EXCEPTIONS.items():
        assert cle in s and len(raison) > 30, cle


# --------------------------------------------------------------------------- #
#  CK4 — un test ignoré sans raison écrite, ou dont la sonde ment, fait échouer la suite
# --------------------------------------------------------------------------- #

def _pytest_isole(tmp_path, code_test: str, env_extra=None):
    (tmp_path / "conftest.py").write_text("from tests.conftest import *  # noqa\n", encoding="utf-8")
    (tmp_path / "test_essai_ck4.py").write_text(code_test, encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env_extra or {})}
    return subprocess.run([sys.executable, "-m", "pytest", str(tmp_path), "-q", "-p", "no:cacheprovider"],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env=env, timeout=300)


def test_ck4_un_test_ignore_sans_justification_fait_echouer_la_suite(tmp_path):
    r = _pytest_isole(tmp_path, "import pytest\n\ndef test_a():\n    pytest.skip('flemme')\n")
    assert r.returncode != 0, r.stdout[-1500:]
    assert "sans justification" in r.stdout


def test_ck4_une_sonde_qui_ment_fait_echouer_la_suite(tmp_path):
    """La raison est connue, mais sa condition n'est pas réunie : la sonde est tombée sur autre chose."""
    r = _pytest_isole(tmp_path, "import pytest\n\ndef test_a():\n    pytest.skip('Windows uniquement')\n")
    assert r.returncode != 0, r.stdout[-1500:]
    assert "condition" in r.stdout


def test_ck4_un_test_ignore_justifie_passe_et_est_compte(tmp_path):
    r = _pytest_isole(tmp_path, "import pytest\n\ndef test_a():\n    pytest.skip('ChromaDB de test indisponible')\n",
                      {"ATLAS_TEST_NO_CHROMA": "1"})
    assert r.returncode == 0, r.stdout[-1500:]
    assert "tests ignorés : 1" in r.stdout


# --------------------------------------------------------------------------- #
#  CK6 — doctor.py --composants
# --------------------------------------------------------------------------- #

def test_ck6_doctor_composants_json():
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "doctor.py"), "--composants", "--json"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", env=env, timeout=300)
    assert r.returncode == 0, r.stderr[-1500:]
    lignes = json.loads(r.stdout)
    noms = {x["composant"] for x in lignes}
    for attendu in ("Ollama", "Tesseract", "EasyOCR", "torch", "Embeddings (ONNX)", "sentence-transformers",
                    "Transcription (faster-whisper)", "Synthèse (Piper)", "Mot d'éveil (openWakeWord)",
                    "Mémoire (ChromaDB)", "Pilote NVIDIA", "cuBLAS / cuDNN"):
        assert attendu in noms, attendu
    for x in lignes:
        assert {"composant", "present", "version", "materiel", "bascule"} <= set(x), x
    st = next(x for x in lignes if x["composant"] == "sentence-transformers")
    assert "repli" in st["role"]


# --------------------------------------------------------------------------- #
#  CK7 — corrections
# --------------------------------------------------------------------------- #

def test_ck7_les_scripts_qui_vectorisent_suivent_le_reglage_d_atlas():
    """Importer memory_core seul laisse le moteur par défaut (sentence-transformers, torch)."""
    fautifs = []
    for f in _CODE_CONFIG:
        rel = _rel(f)
        if rel.startswith("core_conversational/") or rel == "core/embeddings.py":
            continue
        texte = f.read_text(encoding="utf-8")
        if "memory_core" in texte and "core.embeddings" not in texte and "set_embedding_backend" not in texte:
            fautifs.append(rel)
    assert fautifs == []


def test_ck7_reencode_memory_vectorise_avec_onnx():
    r = _py("import sys; sys.path.insert(0, 'scripts'); import reencode_memory; "
            "import core_conversational.memory_core as mc; print(mc._backend)")
    assert r.returncode == 0, r.stderr[-800:]
    assert r.stdout.strip().splitlines()[-1] == _settings()["memory"]["embedding_backend"]


def test_ck7_doctor_presente_sentence_transformers_comme_un_repli():
    doctor = _doctor()
    ligne = next(p for p in doctor.PACKAGES if p[0] == "sentence-transformers")
    assert ligne[2] != doctor.CRITICAL and "repli" in ligne[3]


def _noms(fichier: str) -> set[str]:
    out = set()
    for line in (ROOT / fichier).read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line and not line.startswith("-"):
            out.add(re.split(r"[<>=\[ ;!~]", line)[0].lower().replace("_", "-"))
    return out


def test_ck7_requirements_sans_paquet_mort_et_avec_ceux_qui_servent():
    req = _noms("requirements.txt")
    for mort in ("aiosqlite", "pydantic-settings", "wmi", "duckduckgo-search", "pvporcupine"):
        assert mort not in req, mort
    for utile in ("easyocr", "pypdf"):
        assert utile in req, utile
    dev = _noms("requirements-dev.txt")
    assert {"pytest", "pytest-asyncio", "pytest-cov"} <= dev


# Paquets déclarés qu'aucun « import » du code ne nomme, mais qui servent (prouvé en CK1).
DECLARES_INDIRECTS = {
    "lxml": "analyseur de BeautifulSoup, désigné par son nom (« lxml ») dans tools/web_reader.py",
}


def test_ck7_chaque_paquet_declare_est_importe_ou_justifie():
    sys.path.insert(0, str(ROOT / "scripts"))
    import inventaire_composants as inv

    stat = inv.statique()
    jamais = sorted(p["paquet"] for p in stat["paquets"]
                    if p["provenance"] == "déclaré" and not p["importe_par"])
    assert sorted(set(jamais) - set(DECLARES_INDIRECTS)) == []
    assert sorted(set(DECLARES_INDIRECTS) - set(jamais)) == [], "exception devenue inutile"


def test_ck2_instantane_des_processus_en_echec_est_signale(registre, monkeypatch):
    """Repli psutil de l'échantillonneur (sprint Pré-beta) : signalé, plus seulement en debug."""
    import core.context_monitor as cm

    def casse(*a, **k):
        raise OSError("ntdll illisible")

    monkeypatch.setattr(cm.sys, "platform", "win32")
    monkeypatch.setattr(cm.ctypes, "WinDLL", casse)
    assert cm._process_snapshot() is None
    assert "instantane_processus" in _cles(registre)


def test_ck2_icone_de_la_zone_de_notification_absente_est_signalee(registre, monkeypatch):
    from tools.systray import AtlasSystray

    monkeypatch.setitem(sys.modules, "pystray", None)
    AtlasSystray(on_open=lambda: None, on_toggle_voice=lambda v: None, on_quit=lambda: None)
    assert "systray" in _cles(registre)


def test_ck2_notifications_impossibles_sont_signalees(registre, monkeypatch):
    from tools.notifier import notify

    monkeypatch.setitem(sys.modules, "plyer", None)
    asyncio.run(notify("essai"))
    assert "notifications" in _cles(registre)
