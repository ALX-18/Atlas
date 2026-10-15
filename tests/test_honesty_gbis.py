"""
Sprint G-bis / GB1 — Atlas ne prétend plus avoir agi.

Décision du superviseur : un « ne ment pas » ne repose pas sur une probabilité. Deux gardes
DÉTERMINISTES, une consigne au modèle en complément :
  1. avant le modèle : une demande d'action qu'aucun outil ne sait faire reçoit une réponse
     fixe, « Je ne sais pas encore faire ça. » — le modèle n'est même pas appelé ;
  2. après le modèle : une réponse de conversation qui affirme ou promet une action n'est pas
     transmise ; elle est remplacée par la réponse fixe, et l'échange n'est pas mémorisé.

Les tests de la garde portent sur les VRAIES réponses du modèle (qwen2.5:7b, ligne de base du
10/10/2026, tests/fixtures/gb1_reponses_reelles.json), étiquetées à la main.
"""

import asyncio
import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import core.intent_engine as ie
from core import confirmation

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "gb1_reponses_reelles.json"
REELLES = json.loads(FIXTURE.read_text(encoding="utf-8"))["reponses"]
REPONSE_FIXE = "Je ne sais pas encore faire ça."


def _par_etiquette(*etiquettes):
    return [r for r in REELLES if r["etiquette"] in etiquettes]


# --------------------------------------------------------------------------- #
#  La garde de sortie, sur les vraies réponses du modèle
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("r", _par_etiquette("affirme", "promet"), ids=lambda r: r["phrase"])
def test_gb1_la_garde_arrete_chaque_affirmation_reelle(r):
    from core.validator import claims_action

    assert claims_action(r["reponse"]), f"non détectée : {r['reponse']!r}"


@pytest.mark.parametrize("r", _par_etiquette("ordinaire", "honnete"), ids=lambda r: r["phrase"])
def test_gb1_la_garde_laisse_passer_les_reponses_ordinaires(r):
    """Faux positifs : « la capitale de l'Italie est Rome » ne doit pas être bloquée."""
    from core.validator import claims_action

    assert not claims_action(r["reponse"]), f"faux positif sur {r['phrase']!r} : {r['reponse'][:120]!r}"


# --------------------------------------------------------------------------- #
#  Avant le modèle : une demande d'action sans outil
# --------------------------------------------------------------------------- #

ACTIONS_SANS_OUTIL = [
    "baisse le volume", "monte le son", "envoie un message à Paul", "coupe le wifi", "vide la corbeille",
    "supprime mes fichiers temporaires", "mets de la musique", "baisse la luminosité de l'écran",
    "envoie un mail à ma mère", "commande une pizza", "mets un rappel dans mon téléphone", "appelle mon frère",
    "mets le son à 50 %", "désactive le bluetooth", "allume la lumière du salon", "mets la musique en pause",
    "passe à la chanson suivante", "réserve une table pour ce soir", "achète du lait sur Amazon",
    "imprime ce document", "partage ce fichier avec Léa", "télécharge le dernier épisode de ma série",
    "change le fond d'écran", "réponds à mon dernier mail", "mets un minuteur de 10 minutes",
    "tu peux baisser le volume ?", "peux-tu vider la corbeille s'il te plaît", "envoie ce fichier par mail",
]

QUESTIONS = [r["phrase"] for r in _par_etiquette("ordinaire")] + [
    "appelle-moi Alex", "réponds-moi franchement", "envoie-moi une blague", "mets-toi à ma place",
    "passe une bonne journée", "change de sujet", "tu peux m'expliquer la photosynthèse ?",
]


@pytest.mark.parametrize("phrase", ACTIONS_SANS_OUTIL)
def test_gb1_une_action_sans_outil_est_reconnue(phrase):
    from core.intent_classifier import get_classifier

    intent = get_classifier().classify(phrase, {})
    assert intent.category != "conversation", f"{phrase!r} part en conversation : le modèle répondra"


@pytest.mark.parametrize("phrase", QUESTIONS)
def test_gb1_une_question_reste_une_question(phrase):
    from core.intent_classifier import get_classifier

    intent = get_classifier().classify(phrase, {})
    assert intent.category != "unsupported", f"{phrase!r} pris pour une action"


# --------------------------------------------------------------------------- #
#  De bout en bout, par les vraies routes — le modèle simulé rend une VRAIE réponse
# --------------------------------------------------------------------------- #

class MemoireLecture:
    """Rappels vides, écritures enregistrées : on voit ce qui AURAIT été mémorisé."""

    def __init__(self):
        self.ingeres = []
        self.session = []

    def recall_for_prompt(self, q):
        return []

    def recall_texts(self, q, top_k=5):
        return []

    def add_to_session(self, role, content):
        self.session.append((role, content))

    def ingest_conversation(self, user, assistant, **k):
        self.ingeres.append((user, assistant))

    def __getattr__(self, name):
        return lambda *a, **k: None


@pytest.fixture
def monde(monkeypatch):
    import core.memory_manager as mm

    mem = MemoireLecture()
    monkeypatch.setattr(mm, "_instance", mem)
    executed = []
    for name in list(ie.TOOL_HANDLERS):
        monkeypatch.setitem(ie.TOOL_HANDLERS, name,
                            (lambda n: lambda args: executed.append(n) or {"success": True, "message": n})(name))
    monkeypatch.setattr(ie, "_save_action_to_memory", lambda *a, **k: None)
    confirmation._pending.clear()
    yield mem, executed
    confirmation._pending.clear()


def _modele_qui_repond(monkeypatch, texte):
    import api.routes as routes
    import core.ollama_client as oc

    async def stream(*a, **k):
        for mot in texte.split(" "):
            yield mot + " "

    async def full(*a, **k):
        return texte

    monkeypatch.setattr(routes, "chat_stream", stream)
    monkeypatch.setattr(oc, "chat_stream", stream)
    monkeypatch.setattr(oc, "chat_full", full)


AFFIRMATION_REELLE = next(r["reponse"] for r in REELLES if r["reponse"] == "Le Bluetooth est désactivé.")


def test_gb1_api_chat_ne_transmet_pas_une_affirmation_ni_ne_la_memorise(monde, monkeypatch):
    """Une demande qui part en conversation (pas un impératif), le modèle affirme avoir agi."""
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    mem, executed = monde
    _modele_qui_repond(monkeypatch, AFFIRMATION_REELLE)
    r = asyncio.run(chat_endpoint(ChatRequest(message="le bluetooth me dérange", history=[])))
    assert executed == []
    assert r["message"] == REPONSE_FIXE, f"transmis : {r['message']!r}"
    assert mem.ingeres == [], f"échange mensonger mémorisé : {mem.ingeres}"
    assert all(AFFIRMATION_REELLE not in c for _, c in mem.session)


def test_gb1_api_chat_reponse_fixe_sans_appeler_le_modele(monde, monkeypatch):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    mem, executed = monde
    appels = []

    async def stream(*a, **k):
        appels.append(1)
        yield "Volume baissé."

    import api.routes as routes
    monkeypatch.setattr(routes, "chat_stream", stream)
    r = asyncio.run(chat_endpoint(ChatRequest(message="baisse le volume", history=[])))
    assert r["message"] == REPONSE_FIXE, r
    assert appels == [], "le modèle a été appelé pour une action qu'aucun outil ne sait faire"
    assert executed == [] and mem.ingeres == []


def test_gb1_le_flux_web_ne_diffuse_pas_l_affirmation(monde, monkeypatch):
    """/api/chat/stream diffusait les mots du modèle au fil de l'eau : trop tard pour garder."""
    from api.models import ChatRequest
    from api.routes import chat_stream_endpoint

    mem, _ = monde
    _modele_qui_repond(monkeypatch, AFFIRMATION_REELLE)

    async def lire():
        resp = await chat_stream_endpoint(ChatRequest(message="le bluetooth me dérange", history=[]))
        return "".join([chunk async for chunk in resp.body_iterator])

    flux = asyncio.run(lire())
    assert "désactivé" not in flux, f"affirmation diffusée : {flux[:300]}"
    assert REPONSE_FIXE in flux.encode().decode("unicode_escape", errors="ignore") or REPONSE_FIXE in flux
    assert mem.ingeres == []


def test_gb1_la_voix_ne_dit_pas_l_affirmation(monkeypatch):
    import core.ollama_client as oc

    _modele_qui_repond(monkeypatch, AFFIRMATION_REELLE)
    dit = asyncio.run(oc.generate_speech_response("le bluetooth me dérange", {}, memories=[]))
    assert dit == REPONSE_FIXE, f"la voix dirait : {dit!r}"


def test_gb1_la_voix_ne_dit_pas_c_est_fait_pour_une_action_refusee(monde, monkeypatch):
    """« écris bonjour » sans fenêtre cible est refusé par le validateur. Le moteur ne
    renvoyait aucun résultat : la voix prononçait son repli, « C'est fait. »"""
    import sounddevice as sd

    from core.voice_engine import VoiceEngine

    class FauxMicro:
        def __init__(self, *a, **k):
            pass

    monkeypatch.setattr(sd, "InputStream", FauxMicro)
    dit = asyncio.run(VoiceEngine()._run_text_pipeline("écris bonjour"))
    assert "fait" not in dit.lower(), f"la voix dirait : {dit!r}"


def test_gb1_la_voix_repond_la_phrase_fixe_a_une_action_sans_outil(monde, monkeypatch):
    import sounddevice as sd

    from core.voice_engine import VoiceEngine

    monkeypatch.setattr(sd, "InputStream", lambda *a, **k: None)
    dit = asyncio.run(VoiceEngine()._run_text_pipeline("vide la corbeille"))
    assert dit == REPONSE_FIXE, f"la voix dirait : {dit!r}"


# --------------------------------------------------------------------------- #
#  Sur le vrai modèle (si Ollama répond) : rien de transmis n'affirme une action
# --------------------------------------------------------------------------- #

def _ollama_joignable():
    """Sonde commune (tests/conftest.py). Avant : toute exception, quelle qu'elle soit, valait
    « Ollama injoignable » et ignorait le test en silence (CK4)."""
    from tests.conftest import ollama_absent

    return not ollama_absent()


@pytest.mark.skipif(not _ollama_joignable(), reason="Ollama injoignable")
def test_gb1_vrai_modele_aucune_affirmation_transmise(monde):
    from api.models import ChatRequest
    from api.routes import chat_endpoint
    from core.validator import claims_action

    mem, executed = monde
    fautives = []
    for phrase in ACTIONS_SANS_OUTIL + ["le volume est trop fort", "j'aimerais un peu de musique"]:
        executed.clear()
        r = asyncio.run(chat_endpoint(ChatRequest(message=phrase, history=[])))
        msg = r.get("message") or ""
        if claims_action(msg) and not executed:
            fautives.append((phrase, msg))
    assert fautives == [], fautives
    assert all(not claims_action(a) for _, a in mem.ingeres)
