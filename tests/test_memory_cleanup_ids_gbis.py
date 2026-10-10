"""
Sprint G-bis / GB7 — retirer de la mémoire EXACTEMENT ce que les tests du sprint G ont écrit.

Décision d'Alexis : tout ce que les tests du sprint G ont écrit est retiré (rapport G,
annexe B). Le script de nettoyage ne savait faire que les règles du sprint E, et protégeait
atlas_conversations. Il gagne un mode « identifiants explicites », testé ici avec un client
ChromaDB SIMULÉ (règle permanente depuis l'incident I-1 du sprint M-bis).

Ce qui est vérifié :
  - atlas_memory (le retour arrière du sprint D) est refusée, même nommée explicitement ;
  - un seul identifiant introuvable, ou dont le texte diffère de celui consigné, et RIEN
    n'est supprimé ;
  - seuls les identifiants listés disparaissent ; tout le reste est intact ;
  - les modes automatiques du sprint E protègent toujours atlas_conversations.
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


class FakeCollection:
    def __init__(self, items):
        self.items = dict(items)          # id → texte
        self.deleted: list[str] = []

    def get(self, ids=None, include=None):
        keys = [i for i in (ids or self.items) if i in self.items]
        return {"ids": keys, "documents": [self.items[k] for k in keys],
                "metadatas": [{} for _ in keys]}

    def count(self):
        return len(self.items)

    def delete(self, ids):
        for i in ids:
            if self.items.pop(i, None) is not None:
                self.deleted.append(i)


class FakeClient:
    def __init__(self, collections):
        self.collections = {name: FakeCollection(items) for name, items in collections.items()}

    def get_collection(self, name):
        if name not in self.collections:
            raise ValueError(f"collection inconnue : {name}")
        return self.collections[name]


@pytest.fixture
def client():
    return FakeClient({
        "atlas_memory": {"vieux_1": "souvenir historique"},
        "atlas_memory_e5": {"correction_test": "L'utilisateur a refusé l'action 'kill_process'",
                            "souvenir_alexis": "Alexis préfère le mode sombre"},
        "atlas_conversations": {"conv_test": "Utilisateur: vide la corbeille\nAtlas: Commande corbeille lancée.",
                                "conv_alexis": "Utilisateur: parle-moi de Rome\nAtlas: Rome est..."},
    })


VOULU = {
    "atlas_memory_e5": {"correction_test": "L'utilisateur a refusé l'action 'kill_process'"},
    "atlas_conversations": {"conv_test": "Utilisateur: vide la corbeille"},
}


def test_gb7_seuls_les_identifiants_listes_disparaissent(client):
    from scripts.memory_cleanup import apply_ids_plan, build_ids_plan

    plan = build_ids_plan(client, VOULU)
    apply_ids_plan(client, plan)
    assert client.collections["atlas_memory_e5"].deleted == ["correction_test"]
    assert client.collections["atlas_conversations"].deleted == ["conv_test"]
    assert "souvenir_alexis" in client.collections["atlas_memory_e5"].items
    assert "conv_alexis" in client.collections["atlas_conversations"].items
    assert client.collections["atlas_memory"].deleted == []


def test_gb7_atlas_memory_refusee_meme_nommee(client):
    from scripts.memory_cleanup import build_ids_plan

    with pytest.raises(ValueError, match="atlas_memory"):
        build_ids_plan(client, {"atlas_memory": {"vieux_1": "souvenir"}})
    assert client.collections["atlas_memory"].deleted == []


@pytest.mark.parametrize("voulu", [
    {"atlas_memory_e5": {"correction_test": "L'utilisateur a refusé", "inexistant": "x"}},
    {"atlas_memory_e5": {"souvenir_alexis": "L'utilisateur a refusé"}},   # texte différent
])
def test_gb7_un_seul_doute_et_rien_n_est_supprime(client, voulu):
    from scripts.memory_cleanup import build_ids_plan

    with pytest.raises(ValueError):
        build_ids_plan(client, voulu)
    assert all(c.deleted == [] for c in client.collections.values())


def test_gb7_les_regles_du_sprint_e_protegent_toujours_les_conversations():
    from scripts.memory_cleanup import PROTECTED

    assert {"atlas_memory", "atlas_conversations"} <= PROTECTED
