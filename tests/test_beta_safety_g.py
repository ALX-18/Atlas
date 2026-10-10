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
