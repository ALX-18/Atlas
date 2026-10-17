"""
Sprint Apprentissage 1 — Atlas retient tes corrections et ses échecs.

Tests écrits AVANT le code. Règle du rapport D : un apprentissage se prouve par un
comportement DIFFÉRENT avant et après, sur la vraie chaîne (/api/chat), et identique à
l'avant quand l'apprentissage est neutralisé. Les fonctions isolées ne suffisent pas.
"""

import asyncio
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ALEXIS = "fenetre"          # origine d'une demande tapée par Alexis dans la fenêtre d'Atlas


@pytest.fixture
def memoire_apprentissage(monkeypatch):
    """Mémoire de test (conftest), apprentissage vide au début et à la fin."""
    import core.apprentissage as ap
    import core.memory_manager as mm

    m = mm.MemoryManager()
    assert m.is_connected()
    monkeypatch.setattr(mm, "get_memory_manager", lambda: m)
    monkeypatch.delenv("ATLAS_APPRENTISSAGE", raising=False)
    ap.oublier([r["id"] for r in ap.lister()])
    ap.reinitialiser_echange()
    yield ap
    ap.oublier([r["id"] for r in ap.lister()])
    ap.reinitialiser_echange()


def _chat(message, origine=ALEXIS):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    return asyncio.run(chat_endpoint(ChatRequest(message=message, history=[], origine=origine)))


# --------------------------------------------------------------------------- #
#  AP1 — provoquer, apprendre, répéter (le test qui manquait au sprint D)
# --------------------------------------------------------------------------- #

@pytest.fixture
def couches(monkeypatch):
    """Une fenêtre témoin dont le libellé n'est trouvé QUE par EasyOCR (couche tardive)."""
    import core.intent_engine as ie
    import tools.grounding as g

    appels = []
    reussit = {"easyocr"}

    def couche(nom):
        async def essai(app, element):
            appels.append(nom)
            if nom in reussit:
                return {"success": True, "method": nom, "message": f"Clic {nom} sur '{element}'.", "coords": (10, 10)}
            return None
        essai.__name__ = f"_try_{nom}"
        return essai

    monkeypatch.setattr(g, "_find_candidate_windows", lambda app: [object()])
    monkeypatch.setattr(g, "_build_layers", lambda app_type, app_title="": [couche(n) for n in
                                                                            ("uia", "cache", "ocr", "easyocr")])

    async def verifie(app, element):
        return {"verified": True, "confidence": 1.0, "method": "test"}

    monkeypatch.setattr(g, "verify_post_click", verifie)
    monkeypatch.setattr(ie, "_click_verification_disabled", lambda: False, raising=False)
    return appels, reussit


def _passe(appels, phrase="clique sur Bibliothèque dans AtlasTemoin", origine=ALEXIS):
    appels.clear()
    r = _chat(phrase, origine)
    return list(appels), r


def test_ap1_bout_en_bout_les_couches_changent_puis_reviennent_neutralisees(memoire_apprentissage, couches,
                                                                             monkeypatch):
    appels, _ = couches
    p1, r1 = _passe(appels)
    assert p1 == ["uia", "cache", "ocr", "easyocr"], p1
    p2, r2 = _passe(appels)
    assert p2 == ["easyocr"], f"passe 2 : {p2}"                    # la couche qui a marché, en premier
    assert "appris" in (r2.get("message") or "").lower(), r2        # Atlas dit qu'il applique un apprentissage
    monkeypatch.setenv("ATLAS_APPRENTISSAGE", "off")
    p3, _ = _passe(appels)
    assert p3 == p1, f"neutralisé : {p3}"


def test_ap1_l_apprentissage_est_dit_meme_si_la_verification_du_clic_echoue(memoire_apprentissage, couches,
                                                                           monkeypatch):
    """Rejeu réel du 15/10 (fenêtre sombre) : la vérification après clic échouait, l'ordre appris
    était appliqué sans être dit."""
    import tools.grounding as g

    async def non_verifie(app, element):
        return {"verified": False, "confidence": 0.53, "method": "test"}

    monkeypatch.setattr(g, "verify_post_click", non_verifie)
    appels, _ = couches
    _passe(appels)
    p2, r2 = _passe(appels)
    assert p2[0] == "easyocr", p2
    assert "appris" in (r2.get("message") or "").lower(), r2


def test_ap1_rien_n_est_appris_d_une_demande_qui_ne_vient_pas_d_alexis(memoire_apprentissage, couches):
    """Scripts, tests, essais : pas d'origine Alexis, rien d'appris (règle C3, fausse correction de G-bis)."""
    appels, _ = couches
    p1, _ = _passe(appels, origine=None)
    p2, _ = _passe(appels, origine=None)
    assert p2 == p1 == ["uia", "cache", "ocr", "easyocr"]
    assert memoire_apprentissage.lister() == []


def test_ap1_la_couche_enregistree_est_une_vraie_couche(memoire_apprentissage, couches):
    """Défaut 1 du rapport D : on enregistrait l'issue globale (all_failed, global_timeout)."""
    appels, reussit = couches
    reussit.clear()                                                  # tout échoue
    _passe(appels)
    (r,) = memoire_apprentissage.lister()
    assert r["type"] == "methode"
    for issue in ("all_failed", "global_timeout", "app_not_found"):
        assert issue not in r["libelle"] and issue not in str(r.get("details"))


def test_ap1_deux_echecs_totaux_la_reponse_change(memoire_apprentissage, couches):
    """reformulate : au 2e échec complet sur la même cible, Atlas le dit et demande le nom exact."""
    appels, reussit = couches
    reussit.clear()
    _, r1 = _passe(appels)
    _, r2 = _passe(appels)
    assert "deuxième fois" not in (r1.get("message") or "").lower()
    assert "deuxième fois" in (r2.get("message") or "").lower(), r2.get("message")


@pytest.mark.parametrize("message,cause", [
    ("Impossible de trouver 'bibliothèque' dans 'steam'. Aucune couche n'a réussi. Tentatives=uia,cache,ocr", "not_found"),
    ("Recherche visuelle trop lente — timeout 20s. Réessaie avec une commande plus précise.", "timeout"),
    ("Fenêtre 'steam' introuvable. Aucun clic effectué.", "app_not_found"),
    ("Aucune fenêtre trouvée pour 'discord'.", "app_not_found"),
    ("Désambiguïsation requise", "ambiguous"),
])
def test_ap1_la_cause_est_classee_depuis_les_vrais_messages(message, cause):
    """Défaut 2 du rapport D : « Aucune couche n'a réussi » tombait en « other »."""
    from core.apprentissage import classify_cause

    assert classify_cause(message) == cause


def test_ap1_premier_plan_la_methode_qui_marche_est_tentee_en_premier(memoire_apprentissage, monkeypatch):
    """Au-delà du clic : mettre au premier plan (et donc restaurer) une fenêtre."""
    from tools import window_controller as wc

    essais = []

    def methode(nom, ok):
        def f(alias, hwnd=None):              # Index des fichiers : les méthodes reçoivent le hwnd résolu
            essais.append(nom)
            return {"success": True, "message": f"Fenêtre '{alias}' mise au premier plan ({nom}).",
                    "title": alias} if ok else None
        return f

    monkeypatch.setattr(wc, "_METHODES_PREMIER_PLAN", {"pywinauto": methode("pywinauto", False),
                                                       "pygetwindow": methode("pygetwindow", False),
                                                       "win32": methode("win32", True)})
    monkeypatch.setattr(wc, "resolve_app_window", lambda t: ({"title": "AtlasTemoin", "hwnd": 1}, None))
    # Sprint Artefacts / AR1 : la vérification « fenêtre visible » regarde vraiment la liste des fenêtres.
    monkeypatch.setattr(wc, "_list_visible_windows", lambda: [{"hwnd": 1, "title": "AtlasTemoin", "process": "python.exe"}])
    monkeypatch.setattr(wc, "_PREMIER_PLAN_ATTENTES", [0.0])
    _chat("mets AtlasTemoin au premier plan")
    assert essais == ["pywinauto", "pygetwindow", "win32"], essais
    essais.clear()
    _chat("mets AtlasTemoin au premier plan")
    assert essais[0] == "win32", essais
    # Sans cible dans la fenêtre, la liste ne montre pas de guillemets vides (rejeu réel du 15/10).
    from core.apprentissage import texte_liste

    texte = texte_liste()
    assert "«  »" not in texte and "Premier plan de « atlastemoin »" in texte, texte


def test_ap1_lancement_le_chemin_qui_a_marche_est_repris(memoire_apprentissage, monkeypatch):
    """Au-delà du clic : lancer une application. La 2e fois, plus de résolution du nom."""
    import core.intent_engine as ie
    import tools.app_launcher as al

    resolutions, lances = [], []
    monkeypatch.setattr(al, "_UWP_APPS", {})
    monkeypatch.setattr(al, "_resolve_app_candidate",
                        lambda name: resolutions.append(name) or ("Témoin", r"C:\Essai\temoin.exe", "index"))
    monkeypatch.setattr(al, "_is_process_running", lambda name: False)
    monkeypatch.setattr(al.os.path, "isfile", lambda p: p == r"C:\Essai\temoin.exe")
    monkeypatch.setattr(al.subprocess, "Popen", lambda cmd, **k: lances.append(cmd))
    monkeypatch.setattr(al, "instantane", lambda: {"pids": set(), "hwnds": set()})
    monkeypatch.setattr(al, "apparu_depuis", lambda avant, nom: "fenêtre « Témoin »")
    monkeypatch.setattr(ie, "LANCEMENT_ATTENTE_S", 0.2)
    _chat("ouvre temoin")
    assert resolutions == ["temoin"] and len(lances) == 1
    _chat("ouvre temoin")
    assert resolutions == ["temoin"], "la 2e fois, le chemin appris est repris sans résoudre le nom"
    assert len(lances) == 2 and lances[1][0] == r"C:\Essai\temoin.exe"


# --------------------------------------------------------------------------- #
#  AP2 — les corrections d'Alexis
# --------------------------------------------------------------------------- #

PRECEDENTE = {"phrase": "ouvre la calculatrice"}


@pytest.mark.parametrize("phrase,voulu", [
    ("non, je voulais ouvrir discord", "ouvrir discord"),
    ("non je voulais dire lance spotify", "lance spotify"),
    ("Non ! Je voulais que tu ouvres Discord.", "ouvres discord"),
    ("c'est pas ça, ouvre le bloc-notes", "ouvre le bloc-notes"),
    ("ce n'est pas ça je voulais ouvre le bloc-notes", "ouvre le bloc-notes"),
    ("je t'ai demandé de mettre steam au premier plan", "mettre steam au premier plan"),
    ("pas la calculatrice, le bloc-notes", "ouvre le bloc-notes"),
    ("non je veux ouvrir steam", "ouvrir steam"),
])
def test_ap2_une_correction_est_reconnue(phrase, voulu):
    from core.apprentissage import detecter_correction

    assert (detecter_correction(phrase, PRECEDENTE) or "").lower() == voulu


@pytest.mark.parametrize("phrase", [
    "non merci", "non c'est bon", "non ça ira", "non", "non pas maintenant", "c'est pas grave",
    "non je ne veux pas", "pas mal", "non, pourquoi ?", "non je voulais juste savoir", "pas besoin",
])
def test_ap2_ce_qui_n_est_pas_une_correction(phrase):
    from core.apprentissage import detecter_correction

    assert detecter_correction(phrase, PRECEDENTE) is None


def test_ap2_sans_echange_precedent_rien_n_est_une_correction():
    from core.apprentissage import detecter_correction

    assert detecter_correction("non, je voulais ouvrir discord", None) is None


@pytest.fixture
def premier_plan(monkeypatch):
    """« mets … au premier plan » compté, jamais exécuté."""
    import core.intent_engine as ie

    import tools.window_controller as wc

    faits = []
    # Sprint Artefacts / AR1 : la vérification « fenêtre visible » regarde vraiment la liste des fenêtres.
    monkeypatch.setattr(wc, "_list_visible_windows", lambda: [{"hwnd": 9, "title": "AtlasTemoin", "process": "python.exe"}])
    monkeypatch.setitem(ie.TOOL_HANDLERS, "window_focus",
                        lambda args: faits.append(args.get("title")) or
                        {"success": True, "message": f"Fenêtre '{args.get('title')}' mise au premier plan."})

    async def rien(*a, **k):
        return None

    monkeypatch.setattr(ie.ExecutionEngine, "_check_idempotence", rien)
    return faits


def test_ap2_correction_appliquee_dite_listee_puis_oubliee(memoire_apprentissage, premier_plan):
    faits = premier_plan
    avant = _chat("mets le témoin devant")
    assert faits == [], avant                                           # mauvaise route : rien de fait
    r = _chat("non, je voulais mets AtlasTemoin au premier plan")
    assert faits == ["atlastemoin"], r                                  # la bonne demande est exécutée
    r = _chat("Mets le témoin devant, stp")                             # même demande, normalisée
    assert faits == ["atlastemoin", "atlastemoin"], r
    assert "comme tu me l'as appris" in r["message"].lower(), r["message"]
    liste = _chat("qu'est-ce que tu as appris ?")
    assert "mets le témoin devant" in liste["message"].lower(), liste["message"]   # tel qu'Alexis l'a tapé
    r = _chat("oublie ce que tu as appris sur mets le témoin devant")
    assert r.get("type") == "confirmation_required", r
    assert "mets le temoin devant" in r["message"].lower() or "mets le témoin devant" in str(r.get("target")).lower()
    from api.models import ConfirmationResponse
    from api.routes import confirm_endpoint

    asyncio.run(confirm_endpoint(ConfirmationResponse(confirmation_id=r["confirmation_id"], accepted=True)))
    assert memoire_apprentissage.lister() == []
    _chat("mets le témoin devant")
    assert faits == ["atlastemoin", "atlastemoin"], "oublié : comportement d'avant"


def test_ap2_neutralise_la_route_apprise_n_est_plus_prise(memoire_apprentissage, premier_plan, monkeypatch):
    faits = premier_plan
    _chat("mets le témoin devant")
    _chat("non, je voulais mets AtlasTemoin au premier plan")
    monkeypatch.setenv("ATLAS_APPRENTISSAGE", "off")
    _chat("mets le témoin devant")
    assert faits == ["atlastemoin"]


def test_ap2_une_correction_vers_une_action_a_confirmer_reste_confirmee(memoire_apprentissage, monkeypatch):
    """Rien d'appris ne contourne CONFIRMATION_POLICY : fermer demande confirmation à chaque fois."""
    import core.intent_engine as ie

    fermes = []
    monkeypatch.setitem(ie.TOOL_HANDLERS, "window_close", lambda args: fermes.append(args) or {"success": True})
    _chat("dégage le témoin")
    r = _chat("non, je voulais ferme AtlasTemoin")
    assert r.get("type") == "confirmation_required" and fermes == []
    r = _chat("dégage le témoin")
    assert r.get("type") == "confirmation_required" and fermes == [], r


def test_ap2_conflit_avec_le_corpus_journalise_et_la_parole_d_alexis_prime(memoire_apprentissage, premier_plan,
                                                                           caplog):
    """« raconte-moi une blague » est dans le corpus (route conversation) : la correction s'applique, journalisée."""
    import logging

    faits = premier_plan
    _chat("raconte-moi une blague")
    with caplog.at_level(logging.INFO):
        _chat("non, je voulais mets AtlasTemoin au premier plan")
    assert any("dans le corpus de routes" in r.getMessage() for r in caplog.records)
    _chat("raconte-moi une blague")
    assert faits == ["atlastemoin", "atlastemoin"]


def test_ap2_rien_n_est_appris_d_une_correction_qui_ne_vient_pas_d_alexis(memoire_apprentissage, premier_plan):
    _chat("mets le témoin devant", origine=None)
    _chat("non, je voulais mets AtlasTemoin au premier plan", origine=None)
    assert memoire_apprentissage.lister() == []


def test_ap2_memoire_indisponible_atlas_fonctionne_et_le_dit(memoire_apprentissage, premier_plan, monkeypatch):
    import core.apprentissage_store as store
    from core_conversational.degradations import actives

    def indisponible(*a, **k):
        raise store.Indisponible("fichier verrouillé par un autre processus")

    faits = premier_plan
    # Apprentissage 2 : le stockage est data/apprentissage.db (SQLite) ; on le rend indisponible.
    for nom in ("ecrire", "lire", "effacer"):
        monkeypatch.setattr(store, nom, indisponible)
    _chat("mets le témoin devant")
    r = _chat("non, je voulais mets AtlasTemoin au premier plan")
    assert faits == ["atlastemoin"], r                                 # la bonne demande est faite
    assert "apprentissage" in [b["cle"] for b in actives()]


def test_ap2_la_normalisation_est_deterministe():
    from core.apprentissage import normaliser

    assert normaliser("Mets le Témoin devant, s'il te plaît !") == normaliser("mets le temoin devant")
    assert normaliser("mets le témoin devant") != normaliser("mets le témoin derrière")
