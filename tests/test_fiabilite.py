"""
Sprint Fiabilité — la bonne route, une seule fois.

Tests écrits AVANT le code. Le corpus de demandes naturelles (FI1) est un test permanent : le
taux de bonnes routes ne peut que monter, et aucune demande ne part vers une action alors
qu'on attendait une conversation ou une réponse honnête.
"""

import json
import pathlib
import sys
from collections import Counter

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

CORPUS = ROOT / "tests" / "fixtures" / "corpus_routes.json"
PLANCHER = ROOT / "tests" / "fixtures" / "corpus_routes_plancher.json"


def _corpus():
    return json.loads(CORPUS.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
#  FI1 — le corpus
# --------------------------------------------------------------------------- #

def test_fi1_corpus_au_moins_150_demandes_et_10_par_famille():
    c = _corpus()
    assert len(c) >= 150
    familles = Counter(e["famille"] for e in c)
    assert len(familles) >= 10 and min(familles.values()) >= 10, familles


@pytest.mark.parametrize("phrase", [
    "quel est le numéro de mon essai de check-up ?",            # D5
    "résume la page https://example.com",                       # D7
    "liste les programmes en cours",                             # D10
    "liste mes tâches planifiées",                               # D22
    "rappelle-moi de boire de l'eau tous les jours à 15h",       # D24
    "ajoute du lait à ma liste de courses",                      # G-bis
    "résume l'histoire de Rome",                                 # Sans Docker
    "ok tu peux te fermer", "Fermes, Steam.", "toi fais le",     # sessions d'Alexis
])
def test_fi1_le_corpus_contient_les_phrases_obligatoires(phrase):
    assert phrase in {e["phrase"] for e in _corpus()}


def test_fi1_le_corpus_contient_des_demandes_qu_atlas_ne_sait_pas_faire():
    assert sum(e["attendu"]["route"] == "honnete" for e in _corpus()) >= 10


# --------------------------------------------------------------------------- #
#  FI2 — les routes
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def mesure():
    from mesure_routes import mesurer

    return mesurer(_corpus())


def test_fi2_au_moins_95_pour_cent_de_bonnes_routes(mesure):
    erreurs = [f"{e['phrase']!r} → {e['obtenu']['route']}/{e['obtenu'].get('outil')}" for e in mesure["erreurs"]]
    assert mesure["taux"] >= 95.0, f"{mesure['taux']} % — erreurs : {erreurs}"


def test_fi2_aucune_action_a_tort(mesure):
    """Une mauvaise route vers une action est la plus grave."""
    a_tort = [e["phrase"] for e in mesure["erreurs"] if e["gravite"] == "action_a_tort"]
    assert a_tort == []


def test_fi2_le_taux_ne_peut_que_monter(mesure):
    plancher = json.loads(PLANCHER.read_text(encoding="utf-8"))["taux"]
    assert mesure["taux"] >= plancher, f"{mesure['taux']} % < plancher {plancher} %"


@pytest.mark.parametrize("phrase,outil", [
    ("quel est le numéro de mon essai de check-up ?", "memory_recall"),
    ("résume la page https://example.com", "read_url"),
    ("liste les programmes en cours", "list_processes"),
    ("liste mes tâches planifiées", "schedule_list"),
    ("rappelle-moi de boire de l'eau tous les jours à 15h", "schedule_add"),
])
def test_fi2_les_5_phrases_du_checkup(phrase, outil):
    from mesure_routes import route

    r = route(phrase)
    assert (r["route"], r.get("outil")) == ("outil", outil), r


def test_fi2_planifier_par_rappelle_moi_demande_confirmation():
    from core.intent_classifier import get_classifier
    from core.validator import confirmation_reason, get_validator

    intent = get_classifier().classify("rappelle-moi de boire de l'eau tous les jours à 15h", {})
    res = get_validator().resolve(intent, {})
    assert res.tool == "schedule_add" and confirmation_reason("schedule_add", interactive=True)


@pytest.mark.parametrize("phrase", ["ajoute du lait à ma liste de courses", "résume l'histoire de Rome"])
def test_fi2_les_deux_phrases_de_g_bis_ne_lisent_aucune_page(phrase):
    from mesure_routes import route

    assert route(phrase)["route"] in ("conversation", "honnete")


# --------------------------------------------------------------------------- #
#  FI0 — trouvé en refaisant la base verte : ChromaDB 1.5.1 refuse parfois de lire une
#  collection d'une base fraîchement écrite (« hnsw segment reader: Nothing found on disk »),
#  selon l'ordre des lectures (environ 1 ouverture sur 10, mesuré). Atlas l'a subi le 14/10 :
#  rappels des conversations en échec, une erreur au journal. Filet : client rouvert et
#  lecture refaite une fois, puis bascule signalée. Ce n'est PAS une correction du défaut.
# --------------------------------------------------------------------------- #

@pytest.fixture
def registre():
    from core_conversational import degradations as dg

    dg.reinitialiser()
    yield dg
    dg.reinitialiser()


class _ColCassee:
    def query(self, **k):
        raise RuntimeError("Error executing plan: Internal error: Error creating hnsw segment reader: "
                           "Nothing found on disk")


def test_fi0_une_lecture_en_echec_rouvre_le_client_et_reussit(monkeypatch, registre):
    """Le défaut survient aussi en cours de session (14/10 : rappels des conversations en échec)."""
    import core.memory_manager as mm

    m = mm.MemoryManager()
    assert m.is_connected()
    monkeypatch.setitem(m._partitions, "conversations", _ColCassee())
    assert m.retrieve("Discord", "conversations") == []
    assert not isinstance(m._partitions["conversations"], _ColCassee), "client non rouvert"
    assert registre.actives() == []


def test_fi0_une_lecture_toujours_en_echec_est_signalee(monkeypatch, registre):
    import core.memory_manager as mm

    m = mm.MemoryManager()
    monkeypatch.setitem(m._partitions, "conversations", _ColCassee())
    monkeypatch.setattr(m, "_rouvrir", lambda: None)          # la réouverture n'y change rien
    assert m.retrieve("Discord", "conversations") == []
    assert "memoire_partielle" in [b["cle"] for b in registre.actives()]


# --------------------------------------------------------------------------- #
#  FI3 — une application ouverte une seule fois
# --------------------------------------------------------------------------- #

@pytest.fixture
def lancement(monkeypatch):
    """« ouvre la calculatrice » jusqu'au moteur ; le lancement est compté, jamais exécuté."""
    import core.intent_engine as ie
    import tools.app_launcher as al

    appels = []
    monkeypatch.setitem(ie.TOOL_HANDLERS, "launch_app",
                        lambda args: appels.append(args) or {"success": True, "message": "lancé via protocole UWP."})
    monkeypatch.setattr(al, "_is_process_running", lambda name: False)
    monkeypatch.setattr(al, "instantane", lambda: {"pids": set(), "hwnds": set()})
    monkeypatch.setattr(ie, "LANCEMENT_ATTENTE_S", 0.3)
    return ie, al, appels


def _ouvre(ie, phrase="ouvre la calculatrice"):
    import asyncio

    from core.intent_classifier import get_classifier
    from core.validator import get_validator

    resolved = get_validator().resolve(get_classifier().classify(phrase, {}), {})
    return asyncio.run(ie.get_execution_engine().execute(resolved, {}))


def test_fi3_verification_en_echec_aucune_relance_et_c_est_dit(lancement, monkeypatch):
    ie, al, appels = lancement
    monkeypatch.setattr(al, "apparu_depuis", lambda avant, nom: None)
    r = _ouvre(ie)
    assert len(appels) == 1, f"{len(appels)} lancements"
    assert r.get("verification_failed") is True
    assert "je ne vois pas sa fenêtre" in r["result"]["message"], r


def test_fi3_une_fenetre_apparue_vaut_lancement(lancement, monkeypatch):
    ie, al, appels = lancement
    monkeypatch.setattr(al, "apparu_depuis", lambda avant, nom: "fenêtre « Calculatrice »")
    r = _ouvre(ie)
    assert len(appels) == 1 and not r.get("verification_failed"), r


def test_fi3_la_calculatrice_est_reconnue_par_son_processus(monkeypatch):
    import types

    import tools.app_launcher as al

    procs = [types.SimpleNamespace(info={"name": "CalculatorApp.exe"})]
    monkeypatch.setattr(al.psutil, "process_iter", lambda attrs=None: iter(procs))
    assert al._is_process_running("calculatrice") is True


def test_fi3_une_calculatrice_ouverte_est_ramenee_pas_relancee(monkeypatch):
    """Applications Windows modernes : processus hôte ApplicationFrameHost, titre localisé."""
    import tools.app_launcher as al
    from tools import window_controller as wc

    monkeypatch.setattr(wc, "_list_visible_windows",
                        lambda: [{"hwnd": 7, "title": "Calculatrice", "process": "ApplicationFrameHost.exe"}])
    assert [w["title"] for w in al._app_windows("calculatrice")] == ["Calculatrice"]


def test_fi3_apparu_depuis_voit_une_nouvelle_fenetre(monkeypatch):
    import tools.app_launcher as al
    from tools import window_controller as wc

    monkeypatch.setattr(wc, "_list_visible_windows",
                        lambda: [{"hwnd": 1, "title": "Atlas", "process": "python.exe"},
                                 {"hwnd": 2, "title": "Calculatrice", "process": "ApplicationFrameHost.exe"}])
    monkeypatch.setattr(al.psutil, "pids", lambda: [10])
    assert "Calculatrice" in (al.apparu_depuis({"pids": {10}, "hwnds": {1}}, "calculatrice") or "")
    assert al.apparu_depuis({"pids": {10}, "hwnds": {1, 2}}, "calculatrice") is None


# --------------------------------------------------------------------------- #
#  FI4 — les limites des automatisations : lues dans la configuration, appliquées partout
#  (à la création, au chargement du fichier, à la réactivation, à chaque évaluation)
# --------------------------------------------------------------------------- #

@pytest.fixture
def moteur(tmp_path, monkeypatch):
    import core.trigger_engine as te
    import core.validator as v

    bloques = []
    monkeypatch.setattr(te, "TRIGGERS_FILE", tmp_path / "triggers.json")
    monkeypatch.setattr(v, "report_automation_block", lambda src, item, reason: bloques.append((item, reason)))
    monkeypatch.setattr(te.TriggerEngine, "_validate", lambda self, t: "")
    return te, bloques


def _declencheur(i, **k):
    return {"id": f"t{i}", "name": f"essai {i}", "condition": {"metric": "cpu_usage", "operator": ">", "value": 90},
            "actions": [{"action": "notify", "params": {"message": "x"}}], **k}


def test_fi4_les_limites_viennent_de_la_configuration():
    import core.trigger_engine as te

    auto = json.loads((ROOT / "config" / "settings.json").read_text(encoding="utf-8"))["automation"]
    assert te.MAX_ACTIVE_TRIGGERS == auto["max_active_triggers"]
    assert te.MIN_COOLDOWN_SECONDS == auto["min_cooldown_seconds"]


def test_fi4_au_chargement_les_declencheurs_au_dela_du_maximum_sont_bloques_et_signales(moteur, monkeypatch):
    te, bloques = moteur
    monkeypatch.setattr(te, "MAX_ACTIVE_TRIGGERS", 2)
    te.TRIGGERS_FILE.write_text(json.dumps([_declencheur(i) for i in range(3)]), encoding="utf-8")
    eng = te.TriggerEngine()
    eng._load_triggers()
    actifs = [t for t in eng._triggers.values() if t.enabled and not t.invalid_reason]
    assert len(actifs) == 2 and len(eng._triggers) == 3, "le fichier est conservé, le 3e bloqué"
    assert bloques and "limite" in bloques[0][1]


@pytest.mark.parametrize("delai", [0, 10])
def test_fi4_un_delai_trop_court_dans_le_fichier_est_releve_au_minimum(moteur, delai):
    import asyncio
    from datetime import datetime, timedelta

    te, _ = moteur
    recent = (datetime.now() - timedelta(seconds=20)).isoformat()
    te.TRIGGERS_FILE.write_text(json.dumps([_declencheur(0, cooldown_seconds=delai, last_triggered=recent)]),
                                encoding="utf-8")
    eng = te.TriggerEngine()
    eng._load_triggers()
    tires = []

    async def tirer(t, c):
        tires.append(t.id)

    eng._fire_trigger = tirer
    eng._context_callback = lambda: {"cpu_usage": 99}
    asyncio.run(eng._check_triggers())
    assert tires == [], "déclenché 20 s après le précédent, sous le délai minimum de 60 s"


def test_fi4_reactiver_au_dela_du_maximum_est_refuse_et_signale(moteur, monkeypatch):
    import asyncio

    te, bloques = moteur
    monkeypatch.setattr(te, "MAX_ACTIVE_TRIGGERS", 2)
    te.TRIGGERS_FILE.write_text(json.dumps([_declencheur(0), _declencheur(1), _declencheur(2, enabled=False)]),
                                encoding="utf-8")
    eng = te.TriggerEngine()
    eng._load_triggers()
    assert asyncio.run(eng.toggle_trigger("t2", True)) is False
    assert eng._triggers["t2"].enabled is False and bloques


def test_fi4_creer_au_dela_du_maximum_est_refuse_et_signale(moteur, monkeypatch):
    import asyncio

    te, bloques = moteur
    monkeypatch.setattr(te, "MAX_ACTIVE_TRIGGERS", 1)
    eng = te.TriggerEngine()
    eng._load_triggers()
    asyncio.run(eng.add_trigger(te.ContextTrigger.from_dict(_declencheur(0))))
    with pytest.raises(ValueError):
        asyncio.run(eng.add_trigger(te.ContextTrigger.from_dict(_declencheur(1))))
    assert bloques


# --------------------------------------------------------------------------- #
#  FI7 — faster-whisper absent : une bascule annoncée (au démarrage, et à la première phrase)
# --------------------------------------------------------------------------- #

def test_fi7_faster_whisper_absent_est_signale_des_le_demarrage(monkeypatch, registre):
    import importlib.util

    import core.voice_engine as ve

    vrai = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda nom, *a: None if nom == "faster_whisper" else vrai(nom, *a))
    ve.verifier_transcription()
    assert "stt_absent" in [b["cle"] for b in registre.actives()]
    assert registre.CATALOGUE["stt_absent"]["vecue"]


def test_fi7_faster_whisper_present_rien_n_est_signale(registre):
    import core.voice_engine as ve

    ve.verifier_transcription()
    assert registre.actives() == []


def test_fi7_une_phrase_sans_faster_whisper_le_signale(monkeypatch, registre):
    import asyncio

    import core.voice_engine as ve

    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(RuntimeError):
        asyncio.run(ve.VoiceEngine()._transcribe(b"\x00\x00" * 1600))
    assert "stt_absent" in [b["cle"] for b in registre.actives()]


# --------------------------------------------------------------------------- #
#  FI7 bis — deux écrans : un clic en cache ne part jamais hors de la fenêtre visée
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("fenetres", [[], "erreur"])
def test_fi7bis_sans_fenetre_visee_le_cache_ne_clique_pas(monkeypatch, fenetres):
    """Avant : fenêtre introuvable (ou erreur en la cherchant) → clic quand même aux coordonnées
    gardées, qui pouvaient dater d'une autre disposition d'écrans (x = −1482, 10/04)."""
    import asyncio

    import tools.grounding as g

    clics = []
    monkeypatch.setattr(g.pyautogui, "click", lambda **k: clics.append(k))
    monkeypatch.setattr(g, "_coordinate_cache", {"discord": {"amis": {"coords": (-1482, 80), "window_rect": None}}})

    def chercher(titre):
        if fenetres == "erreur":
            raise OSError("EnumWindows")
        return fenetres

    monkeypatch.setattr(g, "_find_candidate_windows", chercher)
    assert asyncio.run(g._try_cache("discord", "amis")) is None
    assert clics == []


# --------------------------------------------------------------------------- #
#  FI2 — trouvé au rejeu : la route ne dépend jamais de la fenêtre au premier plan
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("premier_plan", ["", "rejeu.py - Cortana_Killer - Visual Studio Code", "Discord"])
@pytest.mark.parametrize("phrase", ["ouvre les paramètres", "ouvre les parametres windows"])
def test_fi2_ouvre_les_parametres_ouvre_ceux_de_windows_quel_que_soit_le_premier_plan(phrase, premier_plan):
    from core.intent_classifier import get_classifier
    from core.validator import get_validator

    ctx = {"foreground_window": {"title": premier_plan, "process": ""}}
    r = get_validator().resolve(get_classifier().classify(phrase, ctx), ctx)
    assert r.tool == "launch_app" and "param" in r.params.get("name", ""), (r.tool, r.params)


def test_fi2_les_parametres_d_une_application_nommee_restent_un_clic():
    from core.intent_classifier import get_classifier

    i = get_classifier().classify("va dans les paramètres de Discord", {})
    assert (i.category, i.verb, i.params.get("app_title")) == ("interaction", "click", "discord")


def test_aucun_caractere_de_controle_dans_le_code():
    """Deux retours arrière (\x08) à la place de « \b » se sont glissés dans le classifieur pendant
    ce sprint ; le premier désactivait une règle en silence. Aucun caractère de contrôle, jamais."""
    fautifs = []
    for d in ("api", "core", "core_conversational", "tools", "desktop", "scripts"):
        for f in (ROOT / d).rglob("*.py"):
            texte = f.read_text(encoding="utf-8")
            if any(ord(c) < 32 and c not in "\n\t\r" for c in texte):
                fautifs.append(str(f.relative_to(ROOT)))
    assert fautifs == []


def test_fi2_premier_plan_vise_la_fenetre_nommee_pas_la_derniere_action(monkeypatch):
    """Trouvé au rejeu : après « ouvre le bloc-notes », « mets AtlasEssaiEcranUn au premier plan »
    visait le Bloc-notes (la fenêtre de l'action précédente) au lieu de la fenêtre nommée."""
    from core.intent_classifier import get_classifier
    from core.validator import get_validator
    from core.world_state import get_world_state

    ws = get_world_state()
    monkeypatch.setattr(ws, "last_action", {"tool": "launch_app", "params": {"name": "bloc notes"}})
    r = get_validator().resolve(get_classifier().classify("mets AtlasEssaiEcranUn au premier plan", {}), {})
    assert (r.tool, r.params.get("title")) == ("window_focus", "atlasessaiecranun"), r.params


def test_fi2_remets_la_au_premier_plan_reprend_bien_la_derniere_fenetre(monkeypatch):
    from core.intent_classifier import get_classifier
    from core.validator import get_validator
    from core.world_state import get_world_state

    monkeypatch.setattr(get_world_state(), "last_action", {"tool": "window_focus", "params": {"title": "discord"}})
    r = get_validator().resolve(get_classifier().classify("remets-la au premier plan", {}), {})
    assert r.params.get("title") == "discord", r.params


def test_fi3_une_application_windows_moderne_n_a_qu_une_fenetre(monkeypatch):
    """Trouvé au rejeu : « Paramètres » = un cadre (ApplicationFrameWindow) ET la fenêtre de
    contenu qu'il héberge (Windows.UI.Core.CoreWindow), même titre ; Atlas refusait de choisir."""
    from tools import window_controller as wc

    fenetres = {1: ("Paramètres", "ApplicationFrameWindow"), 2: ("Paramètres", "Windows.UI.Core.CoreWindow"),
                3: ("Discord", "Chrome_WidgetWin_1")}
    monkeypatch.setattr(wc.win32gui, "EnumWindows", lambda cb, x: [cb(h, x) for h in fenetres])
    monkeypatch.setattr(wc.win32gui, "IsWindowVisible", lambda h: True)
    monkeypatch.setattr(wc.win32gui, "GetWindowText", lambda h: fenetres[h][0])
    monkeypatch.setattr(wc.win32gui, "GetClassName", lambda h: fenetres[h][1])
    monkeypatch.setattr(wc.win32process, "GetWindowThreadProcessId", lambda h: (0, 0))
    vues = [(w["hwnd"], w["title"]) for w in wc._list_visible_windows()]
    assert vues == [(1, "Paramètres"), (3, "Discord")]
