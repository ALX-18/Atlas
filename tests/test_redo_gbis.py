"""
Sprint G-bis / GB2 — « faire » et « repas » ne rejouent plus rien.

Constaté en réel (sprint G) : « qu'est-ce que tu sais faire ? » a relancé la calculatrice ;
« donne-moi une idée de repas » a cherché une action à refaire. Deux causes :
  - la tolérance aux fautes (distance ≤ 2) confond « faire » / « refaire », « repas » / « refais » ;
  - « encore », « refaire »… n'importe où dans la phrase suffisaient à rejouer.
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


def _classify(phrase):
    from core.intent_classifier import get_classifier

    return get_classifier().classify(phrase, {})


@pytest.mark.parametrize("phrase", [
    "qu'est-ce que tu sais faire ?",
    "donne-moi une idée de repas",
    "donne-moi une idée de repas rapide pour ce soir",
    "quel repas pour ce soir ?",
    "comment faire une pizza ?",
    "tu peux me faire un résumé de l'histoire de Rome ?",
    "il faut refaire la peinture de ma chambre, tu as des conseils ?",
    "je suis encore fatigué",
    "c'est encore loin, Rome ?",
    "donne-moi encore une idée de cadeau",
    "j'ai fait une erreur hier",
    "fais-moi rire",
    "repas",
    "faire",
])
def test_gb2_une_phrase_ordinaire_ne_rejoue_rien(phrase):
    intent = _classify(phrase)
    assert (intent.category, intent.verb) != ("memory", "redo"), f"{phrase!r} rejoue la dernière action"


@pytest.mark.parametrize("phrase", [
    "refais", "refais ça", "recommence", "encore", "encore une fois", "encore une fois s'il te plaît",
    "à nouveau", "relance", "répète", "refait", "rrefait", "refoit", "relence", "redo",
    "peux-tu refaire ça", "atlas, refais la dernière action", "rejoue la dernière action",
])
def test_gb2_refais_marche_toujours(phrase):
    intent = _classify(phrase)
    assert (intent.category, intent.verb) == ("memory", "redo"), f"{phrase!r} → {intent.category}/{intent.verb}"
