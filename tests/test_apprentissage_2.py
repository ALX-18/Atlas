"""
Sprint Apprentissage 2 — un seul clic (AQ1), stockage SQLite (AQ2), refus (AQ3), habitudes (AQ4).

Tous les tests passent par le vrai chemin `/api/chat` (`chat_endpoint`) ; les couches de
grounding, les fenêtres et les lancements sont simulés, jamais exécutés.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

ALEXIS = "fenetre"


def _chat(message, origine=ALEXIS):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    return asyncio.run(chat_endpoint(ChatRequest(message=message, history=[], origine=origine)))


@pytest.fixture
def apprentissage_vide(monkeypatch, tmp_path):
    """Apprentissage vide au début et à la fin (base de test, jamais la vraie)."""
    import core.apprentissage as ap
    import core.apprentissage_store as store
    from core import propositions

    monkeypatch.delenv("ATLAS_APPRENTISSAGE", raising=False)
    store.vider_pour_test()
    ap.reinitialiser_echange()
    propositions.fermer()
    yield ap
    store.vider_pour_test()
    ap.reinitialiser_echange()
    propositions.fermer()


def _vider_propositions():
    """Oublie quand des habitudes ont été proposées (les limites de fréquence repartent de zéro)."""
    import sqlite3

    import core.apprentissage_store as store

    with sqlite3.connect(store.DB_PATH) as c:
        c.execute("DELETE FROM propositions")


# --------------------------------------------------------------------------- #
#  AQ1 — un clic non vérifié n'est jamais refait
# --------------------------------------------------------------------------- #

@pytest.fixture
def fenetre_qui_compte(monkeypatch):
    """Une fenêtre de test qui COMPTE les clics reçus. Toute couche qui « trouve » la cible clique.
    La vérification après clic échoue toujours (cible peu lisible, comme la fenêtre sombre)."""
    import core.intent_engine as ie
    import tools.grounding as g

    clics = []
    trouvent = {"cache", "easyocr"}

    def couche(nom):
        async def essai(app, element):
            if nom in trouvent:
                clics.append(nom)
                return {"success": True, "method": nom, "message": f"Clic {nom} sur '{element}'.",
                        "coords": (10, 10)}
            return None
        essai.__name__ = f"_try_{nom}"
        return essai

    async def jamais_verifie(app, element):
        return {"verified": False, "confidence": 0.53, "method": "test"}

    monkeypatch.setattr(g, "_find_candidate_windows", lambda app: [object()])
    monkeypatch.setattr(g, "_build_layers", lambda app_type, app_title="": [couche(n) for n in
                                                                            ("uia", "cache", "ocr", "easyocr")])
    monkeypatch.setattr(g, "verify_post_click", jamais_verifie)
    monkeypatch.setattr(ie, "_click_verification_disabled", lambda: False, raising=False)
    return clics


def test_aq1_un_clic_non_verifie_n_est_jamais_refait(apprentissage_vide, fenetre_qui_compte):
    clics = fenetre_qui_compte
    r = _chat("clique sur Magasin dans AtlasEssaiSombre")
    assert len(clics) == 1, f"{len(clics)} clics reçus : {clics}"
    msg = (r.get("message") or "").lower()
    assert "pas pu vérifier" in msg, r.get("message")
    assert not msg.startswith("clic "), "le message ne prétend plus que le clic est sûr"


def test_aq1_une_nouvelle_tentative_passe_par_une_question(apprentissage_vide, fenetre_qui_compte):
    clics = fenetre_qui_compte
    r = _chat("clique sur Magasin dans AtlasEssaiSombre")
    assert "réessaie" in (r.get("message") or "").lower(), r.get("message")
    assert len(clics) == 1
    _chat("oui")                                                       # Alexis accepte : un clic de plus
    assert len(clics) == 2, clics


def test_aq1_sans_reponse_d_alexis_rien_n_est_reclique(apprentissage_vide, fenetre_qui_compte):
    clics = fenetre_qui_compte
    _chat("clique sur Magasin dans AtlasEssaiSombre")
    _chat("non")
    _chat("oui")                                                       # la question a été close par « non »
    assert len(clics) == 1, clics


# --------------------------------------------------------------------------- #
#  AQ2 — ce qui est appris est dans SQLite ; sauvegarde et restauration l'incluent
# --------------------------------------------------------------------------- #

from test_sans_docker import _seul_dossier, sauvegarde  # noqa: E402,F401  (fixture SD3 réutilisée)


def test_aq2_ce_qui_est_appris_est_dans_sqlite_pas_dans_chromadb(apprentissage_vide):
    import sqlite3

    import core.apprentissage_store as store
    import core.memory_manager as mm

    apprentissage_vide.apprendre_correction("mets le témoin devant", "mets AtlasTemoin au premier plan", ALEXIS)
    with sqlite3.connect(store.DB_PATH) as c:
        assert c.execute("SELECT COUNT(*) FROM appris WHERE type = 'correction'").fetchone()[0] == 1
    assert "apprentissage" not in mm.PARTITIONS
    assert not {"habits", "context_apps"} & set(mm.PARTITIONS)


def test_aq2_une_ecriture_ratee_ne_laisse_rien(apprentissage_vide):
    import core.apprentissage_store as store

    with pytest.raises(TypeError):
        store.ecrire("x", "methode", "libellé", {"pas_json": object()})     # échoue avant la transaction
    assert store.lire(["x"]) == []


def _sqlite_jetable(dossier, nom, lignes):
    import sqlite3

    with sqlite3.connect(dossier / nom) as c:
        c.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
        c.executemany("INSERT INTO t (v) VALUES (?)", [(f"ligne {i}",) for i in range(lignes)])


def test_aq2_backup_verify_restore_incluent_apprentissage_et_habits(sauvegarde, tmp_path):
    import sqlite3

    bm, source, dest = sauvegarde
    _sqlite_jetable(source.parent, "apprentissage.db", 3)
    _sqlite_jetable(source.parent, "habits.db", 5)
    assert bm.main(["backup", "--source", str(source), "--dest", str(dest)]) == 0
    sv = _seul_dossier(dest)
    manifest = json.loads((sv / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["sqlite"]["apprentissage.db"]["tables"] == {"t": 3}
    assert manifest["sqlite"]["habits.db"]["tables"] == {"t": 5}
    assert bm.main(["verify", str(sv)]) == 0
    # Restauration : les fichiers en place sont mis de côté, jamais effacés
    cible = tmp_path / "ailleurs" / "chromadb"
    cible.parent.mkdir()
    _sqlite_jetable(cible.parent, "apprentissage.db", 1)
    assert bm.main(["restore", str(sv), "--vers", str(cible), "--oui"]) == 0
    with sqlite3.connect(cible.parent / "apprentissage.db") as c:
        assert c.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 3
    assert list(cible.parent.glob("apprentissage.db.avant_restauration_*"))


def test_aq2_une_sauvegarde_sqlite_alteree_est_refusee(sauvegarde):
    bm, source, dest = sauvegarde
    _sqlite_jetable(source.parent, "apprentissage.db", 3)
    bm.main(["backup", "--source", str(source), "--dest", str(dest)])
    sv = _seul_dossier(dest)
    f = sv / "sqlite" / "apprentissage.db"
    f.write_bytes(f.read_bytes() + b"x")
    assert bm.main(["verify", str(sv)]) == 1


def test_aq2_backup_refuse_si_apprentissage_db_est_tenu(sauvegarde):
    import subprocess

    bm, source, dest = sauvegarde
    _sqlite_jetable(source.parent, "apprentissage.db", 1)
    db = source.parent / "apprentissage.db"
    garde = subprocess.Popen(
        [sys.executable, "-c", "import sys, core.memory_manager as mm; ok, _ = mm.acquire_memory_lock(sys.argv[1]); "
         "print(ok, flush=True); sys.stdin.readline()", str(db)],
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


def test_aq2_un_second_atlas_ne_peut_pas_ouvrir_apprentissage_db(tmp_path, monkeypatch):
    import subprocess

    import core.apprentissage_store as store

    db = tmp_path / "apprentissage.db"
    garde = subprocess.Popen(
        [sys.executable, "-c", "import sys, core.memory_manager as mm; ok, _ = mm.acquire_memory_lock(sys.argv[1]); "
         "print(ok, flush=True); sys.stdin.readline()", str(db)],
        cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert garde.stdout.readline().strip() == "True"
        monkeypatch.setattr(store, "DB_PATH", db)
        with pytest.raises(store.Indisponible):
            store.lire(None)
    finally:
        garde.stdin.write("\n")
        garde.stdin.flush()
        garde.wait(30)


# --------------------------------------------------------------------------- #
#  AQ3 — tes refus
# --------------------------------------------------------------------------- #

@pytest.fixture
def fermeture(monkeypatch):
    """« ferme AtlasEssaiRefus » : confirmation toujours demandée ; la fermeture est comptée, jamais faite."""
    import core.intent_engine as ie

    fermes = []
    monkeypatch.setitem(ie.TOOL_HANDLERS, "window_close",
                        lambda args: fermes.append(args.get("title")) or {"success": True, "message": "Fenêtre fermée."})
    return fermes


def _repondre(r, accepte, origine_http=None):
    from api.models import ConfirmationResponse
    from api.routes import confirm_endpoint

    assert r.get("type") == "confirmation_required", r
    return asyncio.run(confirm_endpoint(ConfirmationResponse(confirmation_id=r["confirmation_id"], accepted=accepte)))


DEMANDE_REFUS = "ferme AtlasEssaiRefus"


def test_aq3_avant_apres_neutralise_le_deuxieme_refus_change_la_reponse(apprentissage_vide, fermeture, monkeypatch):
    r1 = _chat(DEMANDE_REFUS)
    assert "annulé" not in r1["message"]                                  # avant : rien
    _repondre(r1, False)
    r2 = _chat(DEMANDE_REFUS)
    assert "dernières fois" not in r2["message"], r2["message"]            # un seul refus : rien
    _repondre(r2, False)
    r3 = _chat(DEMANDE_REFUS)                                              # après : c'est dit, avant de proposer
    assert r3["type"] == "confirmation_required"                           # la confirmation reste
    assert "les deux dernières fois, tu as annulé « ferme atlasessairefus »" in r3["message"].lower(), r3["message"]
    assert "non, je voulais" in r3["message"]
    assert fermeture == []
    _repondre(r3, True)                                                    # Alexis a changé d'avis : c'est fait
    assert fermeture == ["atlasessairefus"]
    monkeypatch.setenv("ATLAS_APPRENTISSAGE", "off")                       # neutralisé : comme avant
    _repondre(_chat(DEMANDE_REFUS), False)
    _repondre(_chat(DEMANDE_REFUS), False)
    assert "dernières fois" not in _chat(DEMANDE_REFUS)["message"]


def test_aq3_une_expiration_n_est_pas_un_refus(apprentissage_vide, fermeture):
    from core.confirmation import _pending
    from core.intent_engine import purge_expired_confirmations

    for _ in range(3):
        r = _chat(DEMANDE_REFUS)
        _pending[r["confirmation_id"]]["expires_at"] = 0              # Alexis n'a pas répondu
        purge_expired_confirmations()
    assert "dernières fois" not in _chat(DEMANDE_REFUS)["message"]
    assert apprentissage_vide.lister() == []


def test_aq3_un_refus_ne_vient_que_d_alexis(apprentissage_vide, fermeture):
    for _ in range(3):
        _repondre(_chat(DEMANDE_REFUS, origine=None), False)
    assert apprentissage_vide.lister() == []
    assert "dernières fois" not in _chat(DEMANDE_REFUS, origine=None)["message"]


def test_aq3_un_refus_ne_fait_jamais_sauter_ni_bloquer_une_confirmation(apprentissage_vide, fermeture):
    for _ in range(5):
        _repondre(_chat(DEMANDE_REFUS), False)
    r = _chat(DEMANDE_REFUS)
    assert r["type"] == "confirmation_required" and fermeture == []
    _repondre(r, True)
    assert fermeture == ["atlasessairefus"]                              # jamais refusé d'exécuter


def test_aq3_une_acceptation_remet_le_compte_a_zero(apprentissage_vide, fermeture):
    _repondre(_chat(DEMANDE_REFUS), False)
    _repondre(_chat(DEMANDE_REFUS), False)
    _repondre(_chat(DEMANDE_REFUS), True)
    _repondre(_chat(DEMANDE_REFUS), False)
    assert "dernières fois" not in _chat(DEMANDE_REFUS)["message"]


def test_aq3_listable_et_effacable(apprentissage_vide, fermeture):
    _repondre(_chat(DEMANDE_REFUS), False)
    _repondre(_chat(DEMANDE_REFUS), False)
    liste = _chat("qu'est-ce que tu as appris ?")["message"]
    assert "ferme atlasessairefus" in liste.lower() and "annul" in liste.lower(), liste
    r = _chat("oublie ce que tu as appris sur ferme AtlasEssaiRefus")
    _repondre(r, True)
    assert apprentissage_vide.lister() == []
    assert "dernières fois" not in _chat(DEMANDE_REFUS)["message"]


# --------------------------------------------------------------------------- #
#  AQ4 — tes habitudes : proposer, jamais exécuter
# --------------------------------------------------------------------------- #

from datetime import datetime, timedelta  # noqa: E402


def _evt(quand, app, origine="fenetre", outil="launch_app", phrase=None):
    return {"timestamp": quand.isoformat(), "user_input": phrase or f"ouvre {app}", "intent": "window_mgmt/open",
            "tool": outil, "target": app, "result": "success", "origine": origine}


@pytest.fixture
def journal(monkeypatch):
    """Le journal des actions (fichier de TEST), vidé ; écrit des événements passés."""
    import core.atlas_logger as al

    al.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    al.LOG_FILE.write_text("", encoding="utf-8")

    def ecrire(evts):
        with open(al.LOG_FILE, "a", encoding="utf-8") as f:
            for e in evts:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")
    yield ecrire
    al.LOG_FILE.write_text("", encoding="utf-8")


def _steam_puis_discord(jours, origine="fenetre", ecart_min=5):
    maintenant = datetime.now()
    evts = []
    for j in range(1, jours + 1):
        # À l'opposé de l'heure actuelle : pas d'habitude HORAIRE qui se mêlerait au test.
        t = (maintenant - timedelta(days=j)).replace(hour=(maintenant.hour + 12) % 24, minute=0, second=0,
                                                     microsecond=0)
        evts += [_evt(t, "steam", origine), _evt(t + timedelta(minutes=ecart_min), "discord", origine)]
    return evts


@pytest.fixture
def lancements(monkeypatch):
    """« ouvre X » : lancement compté, jamais fait ; vérifié comme apparu."""
    import core.intent_engine as ie
    import core.validator as v
    import tools.app_launcher as al

    faits = []
    monkeypatch.setitem(ie.TOOL_HANDLERS, "launch_app",
                        lambda args: faits.append(args.get("name")) or
                        {"success": True, "message": f"{args.get('name')} lancé.", "resolved_by": "index"})
    monkeypatch.setattr(v.Validator, "_is_app_running", lambda self, target, context: False)
    monkeypatch.setattr(al, "instantane", lambda: {"pids": set(), "hwnds": set()})
    monkeypatch.setattr(al, "apparu_depuis", lambda avant, nom: f"fenêtre « {nom} »")
    monkeypatch.setattr(ie, "LANCEMENT_ATTENTE_S", 0.05)

    async def jamais_deja_fait(*a, **k):            # Steam ouvert sur ce PC ne doit rien changer
        return None

    monkeypatch.setattr(ie.ExecutionEngine, "_check_idempotence", jamais_deja_fait)
    return faits


def test_aq4_calcul_deterministe_seuils_lus_dans_la_configuration(apprentissage_vide, journal, monkeypatch):
    from core import habitudes

    journal(_steam_puis_discord(2))
    assert habitudes.detecter() == []                                     # 2 jours < D = 3
    journal(_steam_puis_discord(3, origine=None))                          # sans origine : pas Alexis
    assert habitudes.detecter() == []
    monkeypatch.setitem(habitudes._CFG, "jours_min", 2)                   # les seuils viennent de la config
    monkeypatch.setitem(habitudes._CFG, "occurrences_min", 2)
    (h,) = [h for h in habitudes.detecter() if h["sorte"] == "enchainement"]
    assert (h["a"], h["b"], h["jours"]) == ("steam", "discord", 2)
    assert habitudes.detecter() == habitudes.detecter()                    # déterministe


def test_aq4_avant_apres_neutralise_proposer_sans_executer(apprentissage_vide, journal, lancements, monkeypatch):
    r = _chat("ouvre steam")                                               # avant : pas d'historique
    assert "je l'ouvre" not in r["message"].lower()
    journal(_steam_puis_discord(3))
    lancements.clear()
    r = _chat("ouvre steam")                                               # après : proposé
    assert "tu ouvres souvent discord après steam. je l'ouvre ?" in r["message"].lower(), r["message"]
    assert lancements == ["steam"], "proposer, jamais exécuter"
    _chat("oui")
    assert lancements == ["steam", "discord"]                              # le oui passe par le chemin normal
    _vider_propositions()
    monkeypatch.setenv("ATLAS_APPRENTISSAGE", "off")                       # neutralisé : rien
    assert "je l'ouvre" not in _chat("ouvre steam")["message"].lower()


def test_aq4_une_proposition_par_habitude_et_par_jour(apprentissage_vide, journal, lancements):
    journal(_steam_puis_discord(3))
    assert "je l'ouvre" in _chat("ouvre steam")["message"].lower()
    _chat("non")
    assert "je l'ouvre" not in _chat("ouvre steam")["message"].lower()


def test_aq4_au_plus_x_propositions_par_heure(apprentissage_vide, journal, lancements, monkeypatch):
    from core import habitudes

    monkeypatch.setitem(habitudes._CFG, "max_propositions_par_heure", 1)
    maintenant = datetime.now()
    evts = []
    for j in range(1, 4):
        t = (maintenant - timedelta(days=j)).replace(hour=(maintenant.hour + 12) % 24, minute=0)
        evts += [_evt(t, "steam"), _evt(t + timedelta(minutes=3), "discord"),
                 _evt(t + timedelta(minutes=30), "spotify"), _evt(t + timedelta(minutes=33), "opera")]
    journal(evts)
    assert "je l'ouvre" in _chat("ouvre steam")["message"].lower()
    _chat("non")
    assert "je l'ouvre" not in _chat("ouvre spotify")["message"].lower()   # limite horaire atteinte


def test_aq4_arrete_de_me_proposer_ca(apprentissage_vide, journal, lancements):
    journal(_steam_puis_discord(3))
    _chat("ouvre steam")
    r = _chat("arrête de me proposer ça")
    assert "je ne te proposerai plus" in r["message"].lower(), r["message"]
    _vider_propositions()
    assert "je l'ouvre" not in _chat("ouvre steam")["message"].lower()
    assert "discord après steam" in apprentissage_vide.texte_liste().lower()     # listé : écartée
    (rec,) = [r for r in apprentissage_vide.lister() if r["type"] == "habitude_ecartee"]
    apprentissage_vide.oublier([rec["id"]])                                       # effacé : reproposée
    assert "je l'ouvre" in _chat("ouvre steam")["message"].lower()


def test_aq4_interrupteur_global(apprentissage_vide, journal, lancements):
    journal(_steam_puis_discord(3))
    assert "plus de suggestions" in _chat("arrête les suggestions")["message"].lower()
    assert "je l'ouvre" not in _chat("ouvre steam")["message"].lower()
    assert "suggestions reprennent" in _chat("reprends les suggestions")["message"].lower()
    assert "je l'ouvre" in _chat("ouvre steam")["message"].lower()


def test_aq4_habitude_horaire(apprentissage_vide, journal, lancements):
    maintenant = datetime.now()
    journal([_evt((maintenant - timedelta(days=j)).replace(minute=0), "bloc-notes") for j in range(1, 4)])
    r = _chat("ouvre steam")
    assert f"vers {maintenant.hour} h" in r["message"].lower() and "bloc notes" in r["message"].lower(), r["message"]
    assert lancements == ["steam"]


def test_aq4_listee_avec_ce_qui_est_appris(apprentissage_vide, journal):
    journal(_steam_puis_discord(3))
    texte = apprentissage_vide.texte_liste().lower()
    assert "habitude" in texte and "discord après steam" in texte, texte


def test_aq4_par_la_voix_la_proposition_vient_apres_la_reponse(apprentissage_vide, journal, lancements):
    from core.voice_engine import VoiceEngine

    journal(_steam_puis_discord(3))
    ve = VoiceEngine.__new__(VoiceEngine)
    ve._announce_on_screen = lambda *a, **k: None
    texte = asyncio.run(ve._run_text_pipeline("ouvre steam"))
    i = texte.lower().find("je l'ouvre")
    assert i > 0 and texte.lower().find("steam") < i, texte                 # jamais au milieu de la réponse
    assert texte.rstrip().endswith("?"), texte


# --------------------------------------------------------------------------- #
#  AQ5 — formulations de correction élargies (positifs et négatifs)
# --------------------------------------------------------------------------- #

PRECEDENTE = {"phrase": "ouvre la calculatrice"}


@pytest.mark.parametrize("phrase,voulu", [
    ("tu t'es trompé, c'était ouvre discord", "ouvre discord"),
    ("tu t'es trompée c'était lance spotify", "lance spotify"),
    ("tu t'es trompé, je voulais ouvrir steam", "ouvrir steam"),
    ("je parlais de ouvre le bloc-notes", "ouvre le bloc-notes"),
    ("non, je parlais de lance steam", "lance steam"),
    ("pas ça, ouvre le bloc-notes", "ouvre le bloc-notes"),
    ("pas ça ! lance discord", "lance discord"),
    ("non c'était ouvre opera", "ouvre opera"),
])
def test_aq5_formulations_de_correction_elargies(phrase, voulu):
    from core.apprentissage import detecter_correction

    assert (detecter_correction(phrase, PRECEDENTE) or "").lower() == voulu


@pytest.mark.parametrize("phrase", [
    "tu t'es trompé", "c'était bien", "c'était parfait", "je parlais de rien", "pas ça ?", "non c'était juste une question",
    "tu t'es trompé ?", "je parlais de toi", "c'était pour rire", "pas ça du tout", "non merci c'est bon",
])
def test_aq5_negatifs_elargis(phrase):
    from core.apprentissage import detecter_correction

    assert detecter_correction(phrase, PRECEDENTE) is None


def _base_avec_collections(chemin, pleines=()):
    import chromadb

    c = chromadb.PersistentClient(path=str(chemin))
    for nom in ("atlas_memory_e5", "atlas_apprentissage", "atlas_habits", "atlas_context_apps"):
        col = c.get_or_create_collection(nom, metadata={"hnsw:space": "cosine"})
        if nom in pleines or nom == "atlas_memory_e5":
            col.add(ids=["a"], documents=["x"], embeddings=[[0.1, 0.2, 0.3]])
    del c


def _sauvegarde_verifiee(tmp_path, ok=True):
    d = tmp_path / "sauvegarde"
    d.mkdir(exist_ok=True)
    (d / "verify_1.json").write_text(json.dumps({"ok": ok}), encoding="utf-8")
    return d


def _script_retirer(args):
    import subprocess

    return subprocess.run([sys.executable, "scripts/retirer_collections_vides.py", *args], cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8", env={**__import__("os").environ,
                                                                                 "PYTHONIOENCODING": "utf-8"})


def test_aq2_collections_vides_retirees_apres_sauvegarde_verifiee(tmp_path):
    import chromadb

    base = tmp_path / "chromadb"
    import subprocess
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); import test_apprentissage_2 as t; "
                    "t._base_avec_collections(sys.argv[1])", str(base)], cwd=ROOT, check=True)
    r = _script_retirer(["--chemin", str(base), "--sauvegarde", str(_sauvegarde_verifiee(tmp_path))])
    assert r.returncode == 0 and "--oui" in r.stdout, r.stdout + r.stderr                 # plan seulement
    r = _script_retirer(["--chemin", str(base), "--sauvegarde", str(_sauvegarde_verifiee(tmp_path)), "--oui"])
    assert r.returncode == 0, r.stdout + r.stderr
    noms = {c.name for c in chromadb.PersistentClient(path=str(base)).list_collections()}
    assert noms == {"atlas_memory_e5"}, noms


def test_aq2_retrait_refuse_sans_verify_ou_si_une_collection_n_est_pas_vide(tmp_path):
    import subprocess

    base = tmp_path / "chromadb"
    subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, 'tests'); import test_apprentissage_2 as t; "
                    "t._base_avec_collections(sys.argv[1], ('atlas_habits',))", str(base)], cwd=ROOT, check=True)
    r = _script_retirer(["--chemin", str(base), "--sauvegarde", str(_sauvegarde_verifiee(tmp_path, ok=False)), "--oui"])
    assert r.returncode != 0 and "verify" in (r.stdout + r.stderr)
    r = _script_retirer(["--chemin", str(base), "--sauvegarde", str(_sauvegarde_verifiee(tmp_path)), "--oui"])
    assert r.returncode != 0 and "pas vide" in (r.stdout + r.stderr)


def test_aq4_meme_application_avec_ou_sans_tiret(apprentissage_vide, journal, lancements):
    """Rejeu réel du 15/10 : « bloc-notes » (la demande) et « bloc notes » (le journal) sont la même application."""
    maintenant = datetime.now()
    evts = []
    for j in range(1, 4):
        t = (maintenant - timedelta(days=j)).replace(hour=(maintenant.hour + 12) % 24, minute=0)
        evts += [_evt(t, "bloc notes"), _evt(t + timedelta(minutes=5), "calculatrice")]
    journal(evts)
    r = _chat("ouvre le bloc-notes")
    assert "calculatrice après bloc notes. je l'ouvre ?" in r["message"].lower(), r["message"]


def test_aq4_les_etapes_d_un_mode_ne_font_pas_une_habitude(apprentissage_vide, journal):
    """Vrai journal (lecture seule, 15/10) : les étapes de « Mode Gaming » (user_input « workflow:… »)
    ressemblaient à « Steam puis Bloc-notes ». Le mode compte, pas ses étapes."""
    from core import habitudes

    maintenant = datetime.now()
    evts = []
    for j in range(1, 4):
        t = (maintenant - timedelta(days=j)).replace(hour=(maintenant.hour + 12) % 24, minute=0)
        evts += [_evt(t, "lancer steam", phrase="workflow:mode_gaming"),
                 _evt(t + timedelta(minutes=1), "notepad", phrase="workflow:mode_gaming"),
                 _evt(t + timedelta(minutes=2), "x", phrase="automation:declencheur")]
    journal(evts)
    assert habitudes.detecter() == []


def test_aq2_un_atlas_d_essai_n_ecrit_ni_dans_le_journal_ni_dans_l_apprentissage_d_alexis():
    """Constaté au 15/10 : les rejeux des sprints précédents écrivaient dans data/atlas_actions.jsonl,
    la source des habitudes. Tout script qui lance main.py redirige le journal et l'apprentissage."""
    fautifs = []
    for f in sorted((ROOT / "scripts").glob("*.py")):
        s = f.read_text(encoding="utf-8")
        if '"main.py"' in s and "Popen" in s:
            # Index des fichiers (17/10) : habits.db aussi — deux lancements d'essai y avaient écrit.
            # Compétences 1 : rappels.db aussi — un Atlas d'essai ne donne ni ne crée les rappels d'Alexis.
            if not ("ATLAS_ACTIONS_LOG" in s and "ATLAS_APPRENTISSAGE_DB" in s and "ATLAS_HABITS_DB" in s
                    and "ATLAS_RAPPELS_DB" in s):
                fautifs.append(f.name)
    assert fautifs == [], fautifs
