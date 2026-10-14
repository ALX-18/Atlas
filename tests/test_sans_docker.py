"""
Sprint Sans Docker — la mémoire dans Atlas, l'installation simplifiée.

SD2 — ChromaDB intégré : un dossier, aucun réseau, un seul processus à la fois, un état lisible.
SD3 — sauvegarde, vérification et restauration sans Docker.
SD4 — plus de SearXNG ni de Docker.
SD5 — embeddings ONNX par défaut, installés sans export manuel ; torch seulement pour l'OCR.
SD6 — keep_alive à 5 min partout ; seuils de doctor.py.

Mémoire JETABLE (dossier temporaire) : jamais data/chromadb.
"""

import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SETTINGS = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))


def _py(code, env_extra=None, timeout=180):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "ANONYMIZED_TELEMETRY": "False", **(env_extra or {})}
    return subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, env=env,
                          timeout=timeout)


# --------------------------------------------------------------------------- #
#  SD2 — ChromaDB intégré
# --------------------------------------------------------------------------- #

def test_sd2_la_memoire_est_un_dossier_sans_reseau(tmp_path):
    code = ("import chromadb\n"
            "def interdit(*a, **k): raise AssertionError('appel réseau à ChromaDB')\n"
            "chromadb.HttpClient = interdit\n"
            "import core.memory_manager as mm\n"
            "m = mm.MemoryManager()\n"
            "print(m.is_connected(), m.status()['etat'], type(m._client).__name__)\n"
            "mid = m.save('user_fact', 'le code du portail est 4521')\n"
            "print(bool(mid))")
    r = _py(code, {"ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(tmp_path / "chromadb")})
    lignes = r.stdout.strip().splitlines()
    assert lignes[-2].startswith("True ok"), r.stdout + r.stderr[-800:]
    assert lignes[-1] == "True", r.stdout + r.stderr[-800:]
    assert (tmp_path / "chromadb" / "chroma.sqlite3").exists()


def test_sd2_le_chemin_par_defaut_est_data_chromadb():
    import core.memory_manager as mm

    assert SETTINGS["memory"]["chroma_path"] == "data/chromadb"
    assert pathlib.Path(mm.DEFAULT_CHROMA_PATH) == ROOT / "data" / "chromadb"


def test_sd2_un_second_processus_ne_prend_pas_la_meme_base(tmp_path):
    """Jamais deux Atlas sur la même base : le second trouve la base verrouillée et le dit."""
    base = tmp_path / "chromadb"
    garde = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, core.memory_manager as mm; m = mm.MemoryManager(); print(m.status()['etat'], flush=True); "
         "sys.stdin.readline()"],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        env={**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(base), "PYTHONIOENCODING": "utf-8"})
    try:
        assert garde.stdout.readline().strip() == "ok"
        r = _py("import core.memory_manager as mm; m = mm.MemoryManager(); s = m.status(); "
                "print(m.is_connected(), s['etat']); print(s['detail'])",
                {"ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(base)})
        lignes = r.stdout.strip().splitlines()
        assert lignes[-2] == "False verrouillee", r.stdout + r.stderr[-800:]
        import psutil

        pids = {garde.pid} | {c.pid for c in psutil.Process(garde.pid).children(recursive=True)}
        assert "autre" in lignes[-1].lower() and any(f" {p})" in lignes[-1] for p in pids), (lignes[-1], pids)
    finally:
        garde.stdin.write("\n")
        garde.stdin.flush()
        garde.wait(30)
    # Le verrou est rendu à la fin du premier processus
    r = _py("import core.memory_manager as mm; print(mm.MemoryManager().status()['etat'])",
            {"ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(base)})
    assert r.stdout.strip().splitlines()[-1] == "ok", r.stdout + r.stderr[-500:]


def test_sd2_atlas_refuse_de_demarrer_si_la_base_est_prise():
    texte = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "verrouillee" in texte, "main.py doit refuser de démarrer sur une base verrouillée"


def test_sd2_etats_distincts(tmp_path):
    r = _py("import core.memory_manager as mm; print(mm.MemoryManager().status()['etat'])", {"ATLAS_MEMORY": "off"})
    assert r.stdout.strip().splitlines()[-1] == "neutralisee", r.stdout + r.stderr[-500:]
    bloque = tmp_path / "fichier"
    bloque.write_text("pas un dossier")
    r = _py("import core.memory_manager as mm; print(mm.MemoryManager().status()['etat'])",
            {"ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(bloque / "chromadb")})
    assert r.stdout.strip().splitlines()[-1] == "en_panne", r.stdout + r.stderr[-500:]


def test_sd2_health_distingue_les_etats(monkeypatch):
    import asyncio

    import api.routes as routes
    import core.memory_manager as mm

    class Faux:
        def __init__(self, etat):
            self.etat = etat

        def status(self):
            return {"etat": self.etat, "detail": "…"}

        def is_connected(self):
            return self.etat == "ok"

        def __getattr__(self, name):
            return lambda *a, **k: None

    for etat in ("ok", "neutralisee", "verrouillee", "en_panne"):
        monkeypatch.setattr(mm, "_instance", Faux(etat))
        h = asyncio.run(routes.api_health())
        h = h if isinstance(h, dict) else json.loads(h.body)
        mem = h["services"]["memoire"]
        assert mem["etat"] == etat and mem["ok"] is (etat == "ok"), h["services"]


def test_sd2_les_tests_n_ouvrent_jamais_la_vraie_base():
    import core.memory_manager as mm

    assert pathlib.Path(mm.CHROMA_PATH).resolve() != (ROOT / "data" / "chromadb").resolve()
    import chromadb

    with pytest.raises(Exception):
        chromadb.PersistentClient(path=str(ROOT / "data" / "chromadb"))


# --------------------------------------------------------------------------- #
#  SD4 — plus de SearXNG ni de Docker
# --------------------------------------------------------------------------- #

def test_sd4_docker_compose_et_searxng_retires():
    assert not (ROOT / "docker-compose.yml").exists()
    assert not (ROOT / "config" / "searxng").exists()
    assert "searxng_url" not in json.dumps(SETTINGS.get("web", {}))


def test_sd4_aucun_appel_restant_a_8001_ou_searxng():
    r = subprocess.run(["git", "grep", "-n", "-I", "-i", "-E",
                        r"localhost:8001|:8888|searxng_url|_search_searxng|HttpClient[(]", "--",
                        "*.py", ":!tests/*", ":!scripts/manual/*", ":!scripts/prototype_sans_docker.py",
                        ":!scripts/migrer_memoire.py"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.stdout.strip() == "", r.stdout[:1500]


def test_sd4_la_recherche_passe_par_duckduckgo_et_un_echec_est_dit(monkeypatch):
    import asyncio

    import tools.web_search as ws

    appels = []

    def ddg(q, n):
        appels.append(q)
        raise RuntimeError("réseau coupé")

    monkeypatch.setattr(ws, "_search_duckduckgo_sync", ddg)
    r = asyncio.run(ws.search("météo Paris"))
    assert appels == ["météo Paris"]
    assert r and "échou" in json.dumps(r, ensure_ascii=False).lower(), r


# --------------------------------------------------------------------------- #
#  SD5 — embeddings ONNX par défaut
# --------------------------------------------------------------------------- #

def test_sd5_onnx_par_defaut():
    assert SETTINGS["memory"]["embedding_backend"] == "onnx"


def test_sd5_l_installation_prepare_l_onnx_sans_export_manuel():
    texte = (ROOT / "scripts" / "download_voice_models.py").read_text(encoding="utf-8")
    assert "def download_e5_onnx" in texte and "onnx/model.onnx" in texte


# --------------------------------------------------------------------------- #
#  SD6 — réglages
# --------------------------------------------------------------------------- #

def test_sd6_keep_alive_5_min_partout():
    from core.ollama_client import KEEP_ALIVE
    from core_conversational.llm_client import LLMClient

    assert SETTINGS["ollama"]["keep_alive"] == "5m" and KEEP_ALIVE == "5m"
    assert LLMClient().keep_alive == "5m"


@pytest.mark.parametrize("ram,vram_go,attendu", [
    (15.8, 8, "ok"),          # une machine de 16 Go affiche ~15,8 Go
    (32.0, 8, "ok"),
    (12.0, 8, "degrade"),     # 12 Go : juste
    (32.0, 6, "degrade"),     # carte de 6 Go : juste
    (8.0, 8, "ko"),
])
def test_sd6_seuils_de_doctor(ram, vram_go, attendu):
    sys.path.insert(0, str(ROOT / "scripts"))
    import doctor

    m = {"windows": True, "arch64": True, "ram_gib": ram, "gpu_name": "NVIDIA GeForce", "vram_mib": vram_go * 1024 - 41,
         "virtualization": False, "disk_free_gib": 100}
    verdict, raisons = doctor.machine_verdict(m)
    attendu_v = {"ok": doctor.VERDICT_OK, "degrade": doctor.VERDICT_DEGRADED, "ko": doctor.VERDICT_KO}[attendu]
    assert verdict == attendu_v, (ram, vram_go, verdict, raisons)
    assert not any("virtualisation" in r.lower() or "docker" in r.lower() for r in raisons), raisons


# --------------------------------------------------------------------------- #
#  SD3 — sauvegarde, vérification, restauration, nettoyage, sans Docker
# --------------------------------------------------------------------------- #

def _faux_vecteur(texte):
    import hashlib

    h = hashlib.sha256(texte.encode("utf-8")).digest()
    v = [b / 255 - 0.5 for b in h[:16]]
    n = sum(x * x for x in v) ** 0.5
    return [x / n for x in v]


def _memoire_jetable(path):
    import chromadb

    c = chromadb.PersistentClient(path=str(path))
    for nom in ("atlas_memory_e5", "atlas_conversations", "atlas_documents", "atlas_errors"):
        col = c.get_or_create_collection(nom, metadata={"hnsw:space": "cosine"})
        docs = [f"{nom} souvenir {i} Discord Steam Opera" for i in range(12)]
        col.add(ids=[f"{nom}_{i}" for i in range(12)], documents=docs,
                embeddings=[_faux_vecteur(d) for d in docs], metadatas=[{"i": i} for i in range(12)])
    del c
    from chromadb.api.client import SharedSystemClient

    SharedSystemClient.clear_system_cache()      # rend les fichiers (Windows)


@pytest.fixture
def sauvegarde(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import backup_memory as bm

    monkeypatch.setattr(bm, "embed", _faux_vecteur)
    source = tmp_path / "chromadb"
    _memoire_jetable(source)
    return bm, source, tmp_path / "sauvegardes"


def _seul_dossier(d):
    (x,) = [p for p in d.iterdir() if p.is_dir()]
    return x


def test_sd3_backup_verify_restore_de_bout_en_bout(sauvegarde, tmp_path):
    bm, source, dest = sauvegarde
    assert bm.main(["backup", "--source", str(source), "--dest", str(dest)]) == 0
    sv = _seul_dossier(dest)
    assert (sv / "SHA256SUMS").exists() and (sv / "manifest.json").exists()
    manifest = json.loads((sv / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["collections"]["atlas_memory_e5"]["count"] == 12 and len(manifest["requetes"]) == 40
    assert bm.main(["verify", str(sv)]) == 0
    rapport = json.loads(sorted(sv.glob("verify_*.json"))[-1].read_text(encoding="utf-8"))
    assert rapport["ok"] and rapport["requetes_40"]["ordres_differents"] == 0
    # Restauration vers une base existante : elle est mise de côté, jamais effacée
    cible = tmp_path / "restauree"
    # La base en place a été écrite par un autre processus (Atlas), arrêté depuis.
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); import test_sans_docker as t; "
                    "t._memoire_jetable(sys.argv[1])", str(cible)], cwd=ROOT, check=True)
    assert bm.main(["restore", str(sv), "--vers", str(cible), "--oui"]) == 0
    assert list(tmp_path.glob("restauree.avant_restauration_*")), "l'ancienne base n'a pas été mise de côté"


def test_sd3_restore_exige_oui_et_un_verify(sauvegarde, tmp_path):
    bm, source, dest = sauvegarde
    bm.main(["backup", "--source", str(source), "--dest", str(dest)])
    sv = _seul_dossier(dest)
    with pytest.raises(SystemExit):
        bm.main(["restore", str(sv), "--vers", str(tmp_path / "x"), "--oui"])      # pas de verify
    bm.main(["verify", str(sv)])
    with pytest.raises(SystemExit):
        bm.main(["restore", str(sv), "--vers", str(tmp_path / "x")])               # pas de --oui


def test_sd3_une_sauvegarde_alteree_est_refusee(sauvegarde):
    bm, source, dest = sauvegarde
    bm.main(["backup", "--source", str(source), "--dest", str(dest)])
    sv = _seul_dossier(dest)
    (sv / "data" / "chroma.sqlite3").write_bytes((sv / "data" / "chroma.sqlite3").read_bytes() + b"x")
    assert bm.main(["verify", str(sv)]) == 1


def test_sd3_backup_refuse_si_la_base_est_tenue(sauvegarde, tmp_path):
    bm, source, dest = sauvegarde
    garde = subprocess.Popen(
        [sys.executable, "-c", "import sys, core.memory_manager as mm; ok, _ = mm.acquire_memory_lock(sys.argv[1]); "
         "print(ok, flush=True); sys.stdin.readline()", str(source)],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert garde.stdout.readline().strip() == "True"
        with pytest.raises(SystemExit) as e:
            bm.main(["backup", "--source", str(source), "--dest", str(dest)])
        assert "Arrêter Atlas" in str(e.value)
    finally:
        garde.stdin.write("\n")
        garde.stdin.flush()
        garde.wait(30)


def test_sd3_memory_cleanup_sur_la_nouvelle_base(tmp_path):
    base = tmp_path / "chromadb"
    _memoire_jetable(base)
    ids = tmp_path / "ids.json"
    ids.write_text(json.dumps({"atlas_errors": {"atlas_errors_3": "atlas_errors souvenir 3"}}), encoding="utf-8")
    plan = subprocess.run([sys.executable, "scripts/memory_cleanup.py", "plan-ids", "--ids", str(ids), "--path", str(base)],
                          cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert "supprimer 1" in plan.stdout, plan.stdout + plan.stderr[-500:]
    app = subprocess.run([sys.executable, "scripts/memory_cleanup.py", "apply-ids", "--ids", str(ids), "--path", str(base),
                          "--yes"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert "12 → 11" in app.stdout, app.stdout + app.stderr[-500:]


# --------------------------------------------------------------------------- #
#  Régression du sprint Performance trouvée en réel : le premier usage d'EasyOCR échouait
# --------------------------------------------------------------------------- #

def test_regression_premier_usage_easyocr_a_le_temps_de_charger(monkeypatch):
    """Depuis que le chargement d'EasyOCR (~10 s) tourne hors de la boucle, le délai de 4 s de sa
    couche l'interrompait : le premier usage échouait toujours (vu en réel le 14/10)."""
    import tools.grounding as g

    monkeypatch.setattr(g, "_EASYOCR_READER", None)
    monkeypatch.setattr(g, "_EASYOCR_ATTEMPTED", False)
    assert g._layer_timeout("easyocr") >= g.GROUNDING_LAYER_TIMEOUT["easyocr"] + 10
    monkeypatch.setattr(g, "_EASYOCR_READER", object())
    assert g._layer_timeout("easyocr") == g.GROUNDING_LAYER_TIMEOUT["easyocr"]
    assert g._layer_timeout("ocr") == g.GROUNDING_LAYER_TIMEOUT["ocr"]
