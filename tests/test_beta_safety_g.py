"""
Sprint G — le minimum avant d'installer Atlas chez quelqu'un d'autre.

G1 : une page web ouverte dans le navigateur ne doit pas pouvoir piloter Atlas.
     main.py acceptait toutes les origines (CORS « * ») ; le rapport F l'a prouvé.

Tous les outils sont remplacés par des enregistreurs : on voit ce qui AURAIT été exécuté,
rien ne l'est.
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import core.intent_engine as ie
from core import confirmation

ATLAS = "http://127.0.0.1:8550"
PAGE_HOSTILE = "https://page-quelconque.example"


@pytest.fixture
def executed(monkeypatch):
    calls = []
    for name in list(ie.TOOL_HANDLERS):
        monkeypatch.setitem(ie.TOOL_HANDLERS, name,
                            (lambda n: lambda args: calls.append((n, args))
                             or {"success": True, "message": f"[simulé] {n}"})(name))
    monkeypatch.setattr(ie, "_save_action_to_memory", lambda *a, **k: None)
    confirmation._pending.clear()
    yield calls
    confirmation._pending.clear()


@pytest.fixture
def client():
    """La vraie application de main.py, sans son démarrage (ni micro, ni mémoire, ni Ollama)."""
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app, base_url=ATLAS)


def _lancer(client, headers=None, **kwargs):
    return client.post("/api/chat", json={"message": "lance la calculatrice", "history": []},
                       headers=headers or {}, **kwargs)


# --------------------------------------------------------------------------- #
#  G1 — une page web ne pilote pas Atlas
# --------------------------------------------------------------------------- #

def test_g1_une_origine_etrangere_ne_declenche_aucune_action(executed, client):
    """Une page ouverte pendant qu'Atlas tourne envoie « lance la calculatrice »."""
    r = _lancer(client, {"Origin": PAGE_HOSTILE})
    assert executed == [], f"une page web a déclenché une action : {executed}"
    assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


def test_g1_une_requete_simple_venue_d_une_page_est_refusee(executed, client):
    """Requête « simple » (text/plain) : le navigateur l'envoie SANS contrôle préalable.
    Restreindre allow_origins n'y change rien — seul le serveur peut la refuser."""
    r = client.post("/api/chat", content='{"message": "lance la calculatrice", "history": []}',
                    headers={"Origin": PAGE_HOSTILE, "Content-Type": "text/plain"})
    assert executed == []
    assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


def test_g1_une_page_ne_lit_pas_la_memoire_sans_en_tete_origin(executed, client):
    """Une balise <img> ou un lien n'envoient pas d'en-tête Origin ; le navigateur envoie
    en revanche Sec-Fetch-Site. Une lecture de la mémoire depuis un autre site est refusée."""
    r = client.get("/api/memory/recall", params={"query": "code"},
                   headers={"Sec-Fetch-Site": "cross-site"})
    assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


def test_g1_rebinding_dns_refuse(executed, client):
    """Un domaine hostile qui se résout vers 127.0.0.1 : pour le navigateur, c'est la même
    origine — pas d'en-tête Origin sur un GET. Seul l'en-tête Host le trahit."""
    r = client.get("/api/memory/recall", params={"query": "code"},
                   headers={"Host": "page-quelconque.example:8550"})
    assert r.status_code == 403, f"{r.status_code} {r.text[:200]}"


def test_g1_le_navigateur_ne_recoit_pas_l_autorisation_cors(client):
    r = client.options("/api/chat", headers={"Origin": PAGE_HOSTILE,
                                             "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") not in ("*", PAGE_HOSTILE), dict(r.headers)


@pytest.mark.parametrize("entetes", [
    {},                                                        # fenêtre desktop (httpx)
    {"Origin": ATLAS, "Sec-Fetch-Site": "same-origin"},        # interface web servie par Atlas
    {"Origin": "http://localhost:8550", "Sec-Fetch-Site": "same-origin"},
])
def test_g1_la_fenetre_atlas_et_l_interface_web_fonctionnent(executed, client, entetes):
    base = entetes.get("Origin", ATLAS)
    r = _lancer(client, entetes) if base == ATLAS else \
        client.post(f"{base}/api/chat", json={"message": "lance la calculatrice", "history": []},
                    headers=entetes)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    # Le moteur vérifie que l'application tourne et réessaie : avec un enregistreur à la
    # place du vrai lancement, la vérification échoue, d'où plusieurs appels.
    assert executed and {n for n, _ in executed} == {"launch_app"}, executed


def test_g1_la_page_d_accueil_de_l_interface_web_s_ouvre(client):
    """Taper l'adresse dans la barre du navigateur : Sec-Fetch-Site vaut « none »."""
    r = client.get("/", headers={"Sec-Fetch-Site": "none"})
    assert r.status_code == 200


# --------------------------------------------------------------------------- #
#  G2 — aucune suppression de mémoire par l'API
# --------------------------------------------------------------------------- #

class MemoireSimulee:
    """Enregistre les suppressions demandées ; n'efface rien."""

    def __init__(self):
        self.effacements = []

    def forget(self, memory_id):
        self.effacements.append(("forget", memory_id))
        return True

    def forget_category(self, category):
        self.effacements.append(("forget_category", category))
        return 42


@pytest.fixture
def memoire(monkeypatch):
    import api.routes as routes

    mem = MemoireSimulee()
    monkeypatch.setattr(routes, "get_memory_manager", lambda: mem)
    return mem


@pytest.mark.parametrize("chemin", ["/api/memory/category/conversations", "/api/memory/abc123"])
def test_g2_l_api_n_efface_pas_la_memoire(client, memoire, chemin):
    """Requête de la fenêtre desktop (acceptée par G1) : même Atlas ne doit pas pouvoir
    effacer une catégorie entière, ou un souvenir, sans confirmation ni sauvegarde.
    Ces routes n'ont aucun appelant : elles sont retirées."""
    r = client.delete(chemin)
    assert memoire.effacements == [], f"{chemin} a effacé de la mémoire : {memoire.effacements}"
    assert r.status_code in (404, 405), f"{r.status_code} {r.text[:200]}"


def test_g2_aucune_route_ne_supprime_de_la_memoire():
    """Recensement : aucune route DELETE, et aucune route qui appelle forget / forget_category."""
    import inspect

    import api.routes as routes

    fautives = []
    for route in routes.router.routes:
        methodes = getattr(route, "methods", set()) or set()
        source = inspect.getsource(route.endpoint) if hasattr(route, "endpoint") else ""
        if "DELETE" in methodes or ".forget(" in source or "forget_category" in source:
            fautives.append(f"{sorted(methodes)} {route.path}")
    assert fautives == [], f"routes qui suppriment de la mémoire : {fautives}"


# --------------------------------------------------------------------------- #
#  G3 — aucune télémétrie du client ChromaDB dans le processus Atlas
# --------------------------------------------------------------------------- #

def test_g3_le_client_chromadb_d_atlas_n_envoie_pas_de_telemetrie():
    """Le serveur Chroma (docker-compose) a coupé la télémétrie ; le client dans le processus
    Atlas, non : 200 lignes « Anonymized telemetry enabled » dans atlas.log.

    Processus séparé, sans pytest : Chroma coupe sa télémétrie de lui-même quand pytest est
    chargé, ce qui masquerait le défaut. Variable d'environnement retirée : c'est Atlas qui
    doit la couper, pas la machine de l'utilisateur.
    """
    import os
    import subprocess

    racine = pathlib.Path(__file__).resolve().parent.parent
    env = {k: v for k, v in os.environ.items() if k.upper() != "ANONYMIZED_TELEMETRY"}
    code = ("import main\n"
            "from chromadb.config import Settings\n"
            "print('TELEMETRIE=' + str(Settings().anonymized_telemetry))\n")
    sortie = subprocess.run([sys.executable, "-c", code], cwd=racine, env=env,
                            capture_output=True, text=True, timeout=180)
    lignes = [l for l in sortie.stdout.splitlines() if l.startswith("TELEMETRIE=")]
    assert lignes, f"import de main impossible : {sortie.stderr[-800:]}"
    assert lignes[-1] == "TELEMETRIE=False", (
        f"le client ChromaDB d'Atlas a la télémétrie active : {lignes[-1]}"
    )


# --------------------------------------------------------------------------- #
#  G4 — « Retiens que… » ne ment plus
#
#  De bout en bout : vrai classifieur, vrai validateur, vrai moteur, vrai MemoryManager,
#  sur le ChromaDB JETABLE des tests (conftest) — jamais la mémoire d'Alexis.
# --------------------------------------------------------------------------- #

@pytest.fixture
def memoire_test(monkeypatch):
    import uuid as _uuid

    import core.memory_manager as mm_mod

    name = f"atlas_memory_test_g4_{_uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(mm_mod, "COLLECTION_NAME", name)
    manager = mm_mod.MemoryManager()
    if not manager.is_connected():
        pytest.skip("ChromaDB de test indisponible")
    monkeypatch.setattr(mm_mod, "get_memory_manager", lambda: manager)
    # L'historique des actions écrit lui aussi dans la mémoire : il n'est PAS neutralisé,
    # pour vérifier qu'il ne recopie pas un fait retenu — ni ne ressuscite un fait oublié.
    monkeypatch.setattr(ie, "get_memory_manager", lambda: manager)
    confirmation._pending.clear()
    yield manager
    confirmation._pending.clear()
    try:
        manager._client.delete_collection(name)
    except Exception:
        pass


def _dire(texte):
    import asyncio

    from core.intent_classifier import get_classifier
    from core.validator import get_validator

    intent = get_classifier().classify(texte, {})
    resolved = get_validator().resolve(intent, {})
    return intent, asyncio.run(ie.get_execution_engine().execute(resolved, {}))


def _message(resultat):
    res = resultat.get("result")
    return (res.get("message") if isinstance(res, dict) else None) or resultat.get("message") or ""


def _tout(manager):
    found = manager._collection.get()
    return list(zip(found.get("ids") or [], found.get("documents") or [],
                    [m.get("category") for m in (found.get("metadatas") or [])]))


def test_g4_retiens_que_enregistre_vraiment(memoire_test):
    _, r = _dire("retiens que le code du portail est 4521")
    docs = [(d, c) for _, d, c in _tout(memoire_test)]
    assert ("le code du portail est 4521", "user_fact") in docs, f"rien d'enregistré : {docs} — {r}"
    assert len([d for d, _ in docs if "4521" in d]) == 1, f"fait recopié ailleurs : {docs}"
    assert "4521" in _message(r), r


def test_g4_ne_dit_jamais_retenu_s_il_n_a_pas_pu(memoire_test, monkeypatch):
    """Mémoire indisponible : Atlas ne doit pas faire croire que c'est noté."""
    monkeypatch.setattr(memoire_test, "save", lambda *a, **k: None)
    _, r = _dire("retiens que le code du portail est 4521")
    msg = _message(r).lower()
    assert r.get("status") != "success" or "pas pu" in msg, r
    assert "pas pu" in msg, f"réponse trompeuse : {msg!r}"


@pytest.mark.parametrize("question", ["tu te souviens du code du portail ?",
                                      "rappelle-moi le code du portail"])
def test_g4_rappel_d_un_fait_retenu(memoire_test, question):
    _dire("retiens que le code du portail est 4521")
    intent, r = _dire(question)
    assert intent.verb == "recall", f"« {question} » classé {intent.category}/{intent.verb}"
    assert "4521" in _message(r), r
    assert len(_tout(memoire_test)) == 1, "une question ne doit rien enregistrer"


def test_g4_rappel_sans_souvenir_le_dit(memoire_test):
    _, r = _dire("tu te souviens du code du portail ?")
    assert "rien retenu" in _message(r).lower(), r


@pytest.mark.parametrize("phrase,verbe", [
    ("est-ce que tu te souviens de ma soeur", "recall"),
    ("tu te souviens du code ?", "recall"),
    ("souviens-toi que ma soeur s'appelle Léa", "remember"),
    ("retiens que le code du portail est 4521", "remember"),
])
def test_g4_question_ou_consigne(phrase, verbe):
    from core.intent_classifier import get_classifier

    intent = get_classifier().classify(phrase, {})
    assert (intent.category, intent.verb) == ("memory", verbe), f"{phrase!r} → {intent.verb}"


def test_g4_oublier_passe_par_la_confirmation_et_n_efface_que_ce_fait(memoire_test):
    _dire("retiens que le code du portail est 4521")
    _dire("retiens que ma soeur s'appelle Léa")
    autre = memoire_test.save("action_history", "Ouverture de Steam")
    avant = _tout(memoire_test)

    _, r = _dire("oublie le code du portail")
    assert r.get("status") == "confirmation_required", r
    assert "4521" in (r.get("target") or ""), f"le dialogue doit montrer le souvenir visé : {r}"
    assert _tout(memoire_test) == avant, "effacé avant la confirmation"

    fait = asyncio_run(ie.execute_confirmed(r["confirmation_id"], {}))
    apres = [d for _, d, _ in _tout(memoire_test)]
    assert not any("4521" in d for d in apres), f"le fait oublié subsiste : {apres} — {fait}"
    assert "ma soeur s'appelle Léa" in apres and "Ouverture de Steam" in apres, apres
    assert autre in [i for i, _, _ in _tout(memoire_test)]


def test_g4_oublier_sans_correspondance_n_efface_rien(memoire_test):
    _dire("retiens que ma soeur s'appelle Léa")
    autre = memoire_test.save("action_history", "Ouverture de Steam")
    avant = _tout(memoire_test)
    _, r = _dire("oublie le code du portail")
    assert r.get("status") != "confirmation_required", r
    assert "rien" in _message(r).lower(), r
    assert _tout(memoire_test) == avant and confirmation._pending == {}


def test_g4_oublier_est_dans_la_table_de_confirmation():
    from core.validator import confirmation_reason

    assert confirmation_reason("memory_forget", interactive=True)
    assert confirmation_reason("memory_forget", interactive=False)


def asyncio_run(coro):
    import asyncio

    return asyncio.run(coro)
