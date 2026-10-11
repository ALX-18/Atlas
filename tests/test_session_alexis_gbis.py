"""
Suivi G-bis — trois défauts trouvés par Alexis lors de sa session de test du 11/10/2026.

Phrases et réponses EXACTES de la session (logs/atlas.log, atlas_conversations) :
  1. « ok tu peux te fermer » → « D'accord, je vais me fermer. » — rien de fait, et la garde
     ne l'a pas vu : elle ne connaissait pas le pronom « me ».
  2. Une réponse ordinaire remplacée par « Je ne sais pas encore faire ça. » : la garde a pris
     « Je réponds » pour une action.
  3. « met steam en premier plan » : la cible n'a pas été lue, l'action a été refusée, et la
     route a laissé le modèle répondre (« Ctrl + Tab en faisant glisser la fenêtre… ») au lieu
     de transmettre le refus.
"""

import asyncio
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import core.intent_engine as ie
from core import confirmation


# --------------------------------------------------------------------------- #
#  1 et 2 — la garde
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("reponse", [
    "D'accord, je vais me fermer. N'hésitez pas à revenir si vous avez d'autres questions ou besoin d'aide.",
    "Je vais m'arrêter maintenant.",
    "D'accord, je vais nous mettre en mode silencieux.",
])
def test_suivi_la_garde_voit_les_pronoms_reflechis(reponse):
    from core.validator import claims_action

    assert claims_action(reponse), f"non détectée : {reponse!r}"


@pytest.mark.parametrize("reponse", [
    "Je réponds à ta question : la capitale de l'Italie est Rome.",
    "Je réponds avec plaisir. Je suis Atlas, ton assistant.",
    "Je vais répondre à ta question en deux phrases.",
    "Je vais passer en revue les options possibles.",
    "Je vais changer de sujet si tu veux.",
])
def test_suivi_la_garde_ne_bloque_pas_une_reponse_ordinaire(reponse):
    from core.validator import claims_action

    assert not claims_action(reponse), f"faux positif : {reponse!r} (« {claims_action(reponse)} »)"


@pytest.mark.parametrize("reponse", [
    "D'accord, je réponds à ton dernier mail.",
    "Je vais répondre à ce message de Paul.",
])
def test_suivi_repondre_a_un_mail_reste_une_affirmation(reponse):
    from core.validator import claims_action

    assert claims_action(reponse), f"non détectée : {reponse!r}"


# --------------------------------------------------------------------------- #
#  3 — la cible, et le refus transmis tel quel
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase,titre", [
    ("met steam en premier plan", "steam"),
    ("mets Discord au premier plan", "discord"),
    ("mets la fenêtre de discord en premier plan", "discord"),
])
def test_suivi_la_cible_du_premier_plan_est_lue(phrase, titre):
    from core.intent_classifier import get_classifier

    intent = get_classifier().classify(phrase, {})
    assert (intent.category, intent.verb) == ("window_mgmt", "focus"), intent
    assert (intent.params.get("title") or "").lower() == titre, intent.params


class MemoireLecture:
    def __init__(self):
        self.ingeres = []

    def recall_for_prompt(self, q):
        return []

    def ingest_conversation(self, user, assistant, **k):
        self.ingeres.append((user, assistant))

    def __getattr__(self, name):
        return lambda *a, **k: None


@pytest.mark.parametrize("phrase", ["ok tu peux te fermer", "ferme la fenêtre"])
def test_suivi_un_refus_est_transmis_sans_laisser_parler_le_modele(monkeypatch, phrase):
    import api.routes as routes
    import core.memory_manager as mm
    from api.models import ChatRequest

    mem = MemoireLecture()
    monkeypatch.setattr(mm, "_instance", mem)
    appels = []

    async def modele(*a, **k):
        appels.append(1)
        yield "D'accord, je vais me fermer."

    monkeypatch.setattr(routes, "chat_stream", modele)
    confirmation._pending.clear()
    r = asyncio.run(routes.chat_endpoint(ChatRequest(message=phrase, history=[])))
    assert appels == [], f"le modèle a répondu à la place du refus : {r}"
    assert "refusée" in r["message"].lower(), r
    assert mem.ingeres == []


def test_suivi_le_flux_web_transmet_aussi_le_refus(monkeypatch):
    import api.routes as routes
    import core.memory_manager as mm
    from api.models import ChatRequest

    monkeypatch.setattr(mm, "_instance", MemoireLecture())
    appels = []

    async def modele(*a, **k):
        appels.append(1)
        yield "D'accord, je vais me fermer."

    monkeypatch.setattr(routes, "chat_stream", modele)

    async def lire():
        resp = await routes.chat_stream_endpoint(ChatRequest(message="ok tu peux te fermer", history=[]))
        return "".join([chunk async for chunk in resp.body_iterator])

    flux = asyncio.run(lire())
    assert appels == [], flux[:300]
    assert "refus" in flux.lower(), flux[:300]
