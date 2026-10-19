"""
Sprint Banc de modèles — BM0 : un seul garde pour les données réelles.

Le garde se teste sur un FAUX dossier de données réelles (règle : « un garde-fou se teste avec des
commandes simulées ») : `donnees_reelles.DOSSIER` et les chemins par défaut des modules sont pointés
vers un dossier jetable, dans un processus à part, sans aucune variable ATLAS_*. Si le garde lâchait,
c'est ce dossier jetable qui serait écrit — jamais `data/` d'Alexis.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_SCRIPT = r"""
import asyncio, json, os, pathlib, sys
sys.path.insert(0, sys.argv[2])
faux = pathlib.Path(sys.argv[1])
os.environ["ATLAS_MEMORY"] = "real"                 # comme les bancs et les rejeux le posent eux-mêmes
from core import donnees_reelles
donnees_reelles.DOSSIER = faux                       # le FAUX dossier des données réelles
import core.atlas_logger as atlas_logger, core.apprentissage_store as store, core.rappels as rappels
import core.context_monitor as cm, core.file_indexer as fi, core.memory_manager as mm, core.validator as v
atlas_logger.LOG_FILE = faux / "atlas_actions.jsonl"
store.DB_PATH, rappels.DB_PATH, cm._DB_PATH = faux / "apprentissage.db", faux / "rappels.db", faux / "habits.db"
fi.DB_PATH, mm.CHROMA_PATH = faux / "file_index.db", str(faux / "chromadb")
issues = {}
def essai(nom, f):
    try:
        f(); issues[nom] = "ECRIT"
    except Exception as e:
        issues[nom] = type(e).__name__
essai("journal", lambda: asyncio.run(atlas_logger.log_action("x", "c", "v", "t", None, "success", None, 1)))
v.report_automation_block("essai", "x", "raison")          # avale ses erreurs : jugé sur le fichier
issues["automatisation"] = "ECRIT" if (faux / "atlas_actions.jsonl").exists() and "automation:essai" in \
    (faux / "atlas_actions.jsonl").read_text(encoding="utf-8") else "refuse"
essai("apprentissage", lambda: store.ecrire("id", "type", "libellé", {}))
essai("apprentissage_lecture", lambda: store.lire())
essai("rappels", lambda: rappels.ajouter("rappel", "x", __import__("datetime").datetime(2030, 1, 1)))
essai("rappels_lecture", lambda: rappels.actifs())
cm._init_db(); cm._persist_habit("x.exe", 3)             # avalent leurs erreurs : jugés sur le fichier
issues["habitudes"] = "ECRIT" if (faux / "habits.db").exists() else "refuse"
essai("index_ajout", lambda: fi.indexer_un_fichier(str(pathlib.Path(sys.argv[2]) / "main.py")))
essai("index_oubli", lambda: fi.oublier_index())
if os.environ.get("ATLAS_DONNEES") != "reelles":        # autorisé, ce serait un vrai passage sur les disques
    essai("index_passage", lambda: fi.FileIndexer().passage())
    m = mm.MemoryManager()
    issues["memoire"] = m.status()["etat"]
print(json.dumps(issues))
"""


def _empreinte(dossier: pathlib.Path) -> dict:
    return {str(p.relative_to(dossier)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(dossier.rglob("*")) if p.is_file()}


def _jouer(faux: pathlib.Path, autorise: bool = False) -> dict:
    env = {k: v for k, v in os.environ.items() if not k.startswith("ATLAS_")}
    env["PYTHONIOENCODING"] = "utf-8"
    if autorise:
        env["ATLAS_DONNEES"] = "reelles"
    r = subprocess.run([sys.executable, "-c", _SCRIPT, str(faux), str(ROOT)], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_bm0_un_script_sans_redirection_n_ecrit_rien_dans_les_donnees_reelles(tmp_path):
    faux = tmp_path / "data"
    faux.mkdir()
    issues = _jouer(faux)
    assert _empreinte(faux) == {}, f"créé dans les données réelles : {list(_empreinte(faux))} ; {issues}"
    assert "ECRIT" not in issues.values(), issues
    assert issues["memoire"] == "neutralisee", issues


def test_bm0_les_fichiers_reels_existants_ne_changent_pas_et_restent_lisibles(tmp_path):
    import sqlite3

    faux = tmp_path / "data"
    faux.mkdir()
    (faux / "atlas_actions.jsonl").write_text('{"user_input": "ligne d\'Alexis"}\n', encoding="utf-8")
    with sqlite3.connect(faux / "apprentissage.db") as c:
        c.executescript("CREATE TABLE appris (id TEXT PRIMARY KEY, type TEXT, libelle TEXT, meta TEXT, cree TEXT, "
                        "maj TEXT); CREATE TABLE etat (cle TEXT PRIMARY KEY, valeur TEXT); "
                        "CREATE TABLE propositions (cle TEXT, quand REAL); "
                        "INSERT INTO appris VALUES ('a', 't', 'l', '{}', 'x', 'x');")
    avant = _empreinte(faux)
    issues = _jouer(faux)
    assert _empreinte(faux) == avant, issues
    assert issues["apprentissage_lecture"] == "ECRIT", "lire un fichier réel existant reste possible"
    assert issues["apprentissage"] == "Indisponible" and issues["journal"] == "DonneesReellesInterdites", issues


def test_bm0_atlas_lui_meme_ecrit(tmp_path):
    """Le garde ne bloque pas tout : avec l'autorisation de main.py, les écritures passent."""
    faux = tmp_path / "data"
    faux.mkdir()
    issues = _jouer(faux, autorise=True)
    assert issues["journal"] == "ECRIT" and issues["apprentissage"] == "ECRIT" and issues["rappels"] == "ECRIT", issues
    assert (faux / "atlas_actions.jsonl").exists() and (faux / "rappels.db").exists()


def test_bm0_seul_atlas_normal_est_autorise_jamais_un_atlas_d_essai(monkeypatch):
    from core import donnees_reelles as dr

    for v in dr.REDIRECTIONS:
        monkeypatch.delenv(v, raising=False)
    monkeypatch.delenv(dr.VARIABLE, raising=False)
    assert dr.autoriser_atlas() is True and dr.autorise()
    monkeypatch.setenv("ATLAS_ACTIONS_LOG", "C:/ailleurs/journal.jsonl")          # un rejeu
    assert dr.autoriser_atlas() is False and not dr.autorise(), "un Atlas d'essai n'a jamais le droit"


def test_bm0_main_pose_l_autorisation_au_lancement_seulement():
    texte = (ROOT / "main.py").read_text(encoding="utf-8")
    bloc = texte[texte.index('if __name__ == "__main__":'):]
    assert "autoriser_atlas()" in bloc and bloc.index("autoriser_atlas()") < bloc.index("uvicorn.run(")
    assert texte.count("autoriser_atlas()") == 1, "importer main (tests) n'autorise rien"


@pytest.mark.parametrize("fichier,marque", [
    ("core/atlas_logger.py", "verifier_ecriture"), ("core/validator.py", "verifier_ecriture"),
    ("core/apprentissage_store.py", "donnees_reelles.interdit"), ("core/rappels.py", "donnees_reelles.interdit"),
    ("core/context_monitor.py", "verifier_ecriture"), ("core/file_indexer.py", "verifier_ecriture"),
    ("core/memory_manager.py", "donnees_reelles.interdit"),
])
def test_bm0_chaque_ecrivain_passe_par_le_garde(fichier, marque):
    assert marque in (ROOT / fichier).read_text(encoding="utf-8")


@pytest.fixture
def banc_factice(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import banc_aveugle
    from tools import documents

    monkeypatch.setattr(documents, "dossier_atlas", lambda: tmp_path / "Documents" / "Atlas")
    banc = tmp_path / "banc"
    for m in ("m1:7b", "m2:4b"):
        d = banc / m.replace(":", "_")
        d.mkdir(parents=True)
        (d / "resultat.json").write_text(json.dumps({"aveugle": {t: f"texte {m} {t}" for t in banc_aveugle.TACHES}}),
                                         encoding="utf-8")
    return banc_aveugle, banc, tmp_path


def test_bm3_productions_anonymes_correspondance_hors_du_dossier_puis_revelee(banc_factice):
    ba, banc, tmp = banc_factice
    cle = tmp / "hors" / "correspondance.json"
    sortie = ba.preparer(banc, ["m1:7b", "m2:4b"], cle, graine=1)
    fichiers = sorted(p.name for p in sortie.iterdir())
    assert fichiers == ["A.txt", "B.txt", "C.txt", "D.txt", "E.txt", "F.txt", "GRILLE.txt", "SOURCE du résumé.txt"], fichiers
    for p in sortie.iterdir():
        assert "m1" not in p.read_text(encoding="utf-8").replace("texte m1", "") or p.name != "GRILLE.txt"
    assert "m1:7b" not in (sortie / "GRILLE.txt").read_text(encoding="utf-8")
    corr = json.loads(cle.read_text(encoding="utf-8"))
    grille = (sortie / "GRILLE.txt").read_text(encoding="utf-8")
    for x in corr:                                     # Alexis note : 5 pour m1, 2 pour m2
        grille = grille.replace(f"{x['lettre']} — note : _", f"{x['lettre']} — note : {5 if x['modele'] == 'm1:7b' else 2}")
    (sortie / "GRILLE.txt").write_text(grille, encoding="utf-8")
    assert ba.reveler(cle, sortie / "GRILLE.txt") == {"m1:7b": {"notes": [5, 5, 5], "moyenne": 5.0},
                                                      "m2:4b": {"notes": [2, 2, 2], "moyenne": 2.0}}


def test_bm3_refus_si_la_cle_est_dans_le_dossier_ou_plus_de_18_productions(banc_factice):
    ba, banc, tmp = banc_factice
    with pytest.raises(SystemExit, match="HORS"):
        ba.preparer(banc, ["m1:7b"], ba.dossier_aveugle() / "cle.json")
    with pytest.raises(SystemExit, match="18 au plus"):
        ba.preparer(banc, ["m1:7b", "m2:4b"] * 4, tmp / "cle.json")


def test_bm0_les_bancs_travaillent_sur_des_copies():
    for banc in ("tests/gb1_mesure.py", "tests/o_mesure_ollama.py"):
        assert "donnees_jetables(" in (ROOT / banc).read_text(encoding="utf-8"), banc
