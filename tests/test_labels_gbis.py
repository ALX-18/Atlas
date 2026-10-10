"""
Sprint G-bis / GB6 — chaque action à confirmer a un libellé lisible dans la fenêtre Atlas.

Le dialogue affichait le nom technique « memory_forget ». Plutôt que d'ajouter deux libellés à
la main, on exige un libellé pour CHAQUE action de CONFIRMATION_POLICY : une action ajoutée
demain sans libellé fera échouer ce test.
"""

import ast
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

DESKTOP = pathlib.Path(__file__).resolve().parent.parent / "desktop" / "atlas_desktop.py"


def _action_labels() -> dict:
    """ACTION_LABELS lu dans le source (la fenêtre Tk n'est pas instanciée)."""
    tree = ast.parse(DESKTOP.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "ACTION_LABELS" for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("ACTION_LABELS introuvable")


def test_gb6_chaque_action_a_confirmer_a_un_libelle_lisible():
    from core.validator import CONFIRMATION_POLICY

    labels = _action_labels()
    manquants = sorted(set(CONFIRMATION_POLICY) - set(labels))
    assert manquants == [], f"le dialogue afficherait le nom technique de : {manquants}"
    for tool, label in labels.items():
        assert "_" not in label and label[0].isupper(), f"libellé peu lisible pour {tool} : {label!r}"


def test_gb6_libelles_de_l_oubli_et_de_l_envoi():
    labels = _action_labels()
    assert labels.get("memory_forget") == "Oublier ce souvenir"
    assert labels.get("window_send_message") == "Envoyer le message"
