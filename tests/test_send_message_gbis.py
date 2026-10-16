"""
Sprint G-bis / GB4 — écrire, et envoyer, dans une autre application.

Constaté au sprint G :
  - « écris (Atlas) Bonjour, je suis Atlas, l'assistant d'Alexis… dans Discord » ne gardait que
    « assistant d » (l'apostrophe était prise pour un guillemet) ;
  - sans guillemets, la casse et la ponctuation étaient perdues, et « dans discord » tapé ;
  - la fenêtre « #général | Atlas - Discord » n'était pas trouvée ;
  - Entrée était refusée : aucun message ne pouvait partir.

Envoyer un message, c'est agir au nom d'Alexis, et ça ne se reprend pas : l'envoi passe par
une confirmation qui montre le texte exact et la fenêtre exacte.

Fenêtres, clavier et focus SIMULÉS : rien n'est tapé sur la machine.
"""

import asyncio
import pathlib
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import core.intent_engine as ie
from core import confirmation


def _classify(phrase):
    from core.intent_classifier import get_classifier

    return get_classifier().classify(phrase, {})


# --------------------------------------------------------------------------- #
#  1. Le texte reste intact
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase,verbe,texte,cible", [
    ("écris (Atlas) Bonjour, je suis Atlas, l'assistant d'Alexis. Message de test. dans Discord",
     "type", "(Atlas) Bonjour, je suis Atlas, l'assistant d'Alexis. Message de test.", "Discord"),
    ("tape (Atlas) Bonjour dans Discord", "type", "(Atlas) Bonjour", "Discord"),
    ('écris "Salut, ça va ?" dans le bloc-notes', "type", "Salut, ça va ?", "bloc-notes"),
    ("écris « Je suis dans le train » dans Discord", "type", "Je suis dans le train", "Discord"),
    ("dans Discord, écris Bonjour à tous", "type", "Bonjour à tous", "Discord"),
    ("envoie (Atlas) Test d'envoi ! dans Discord", "send", "(Atlas) Test d'envoi !", "Discord"),
    ("écris Coucou, c'est Atlas dans Discord et envoie", "send", "Coucou, c'est Atlas", "Discord"),
    ("envoie « Rendez-vous à 18 h » sur la fenêtre Atlas — salon de test", "send", "Rendez-vous à 18 h",
     "Atlas — salon de test"),
])
def test_gb4_le_texte_et_la_cible_sont_intacts(phrase, verbe, texte, cible):
    intent = _classify(phrase)
    assert (intent.category, intent.verb) == ("interaction", verbe), f"{phrase!r} → {intent.category}/{intent.verb}"
    assert intent.params.get("text") == texte, f"texte : {intent.params.get('text')!r}"
    assert intent.params.get("target") == cible, f"cible : {intent.params.get('target')!r}"


# --------------------------------------------------------------------------- #
#  2. L'envoi : un outil à part, toujours confirmé, jamais sans fenêtre nommée
# --------------------------------------------------------------------------- #

def test_gb4_envoyer_passe_par_la_confirmation():
    from core.validator import confirmation_reason, get_validator

    resolved = get_validator().resolve(_classify("envoie (Atlas) Test dans Discord"), {})
    assert resolved.tool == "window_send_message", resolved
    assert resolved.confirmation_required is True
    assert confirmation_reason("window_send_message", interactive=False), "un appel direct doit aussi confirmer"


def test_gb4_sans_fenetre_nommee_rien_n_est_envoye():
    from core.validator import get_validator

    resolved = get_validator().resolve(_classify("envoie bonjour"), {})
    assert resolved.tool != "window_send_message", "un envoi ne doit jamais hériter d'une fenêtre"


def test_gb4_une_automatisation_ne_peut_pas_envoyer():
    from core.validator import check_automation_action

    assert check_automation_action({"tool": "window_send_message",
                                    "params": {"text": "x", "target": "Discord"}})


# --------------------------------------------------------------------------- #
#  3. La fenêtre est retrouvée — et quand il y en a plusieurs, Atlas demande laquelle
# --------------------------------------------------------------------------- #

FENETRES = [
    {"hwnd": 1, "title": "#général | Atlas - Discord", "process": "Discord.exe"},
    {"hwnd": 2, "title": "Sans titre - Bloc-notes", "process": "notepad.exe"},
    {"hwnd": 3, "title": "Rapport.txt - Bloc-notes", "process": "notepad.exe"},
    {"hwnd": 4, "title": "Mon salon", "process": "Slack.exe"},
]


@pytest.fixture
def bureau(monkeypatch):
    from tools import window_controller as wc

    monkeypatch.setattr(wc, "_list_visible_windows", lambda: list(FENETRES))
    return wc


@pytest.mark.parametrize("nom,titre", [
    ("discord", "#général | Atlas - Discord"),
    ("Discord", "#général | Atlas - Discord"),
    ("slack", "Mon salon"),                      # retrouvée par le nom du programme
])
def test_gb4_la_fenetre_est_retrouvee_par_le_nom_de_l_application(bureau, nom, titre):
    fenetre, erreur = bureau.resolve_app_window(nom)
    assert erreur is None and fenetre["title"] == titre, (fenetre, erreur)


def test_gb4_plusieurs_fenetres_atlas_demande_laquelle(bureau):
    fenetre, erreur = bureau.resolve_app_window("bloc-notes")
    assert fenetre is None
    assert "Sans titre - Bloc-notes" in erreur and "Rapport.txt - Bloc-notes" in erreur, erreur


def test_gb4_un_titre_avec_des_caracteres_speciaux_ne_casse_pas_la_recherche(monkeypatch):
    """« | » dans un titre devenait une alternative dans l'expression de pywinauto. Depuis le sprint
    Index des fichiers (IX4.3), pywinauto vise la fenêtre résolue par son hwnd : plus d'expression."""
    from tools import window_controller as wc

    vus = []

    class FauxPywinauto:
        def __init__(self, backend=None):
            pass

        def connect(self, title_re=None, handle=None, timeout=None):
            vus.append({"title_re": title_re, "handle": handle})
            raise RuntimeError("simulé")

    def refus(hwnd):
        raise RuntimeError("simulé")

    monkeypatch.setattr(wc, "PywinautoApplication", FauxPywinauto, raising=False)
    monkeypatch.setattr(wc, "HAS_PYWINAUTO", True)
    monkeypatch.setattr(wc, "HAS_WIN32", False)
    monkeypatch.setattr(wc.gw, "getWindowsWithTitle", lambda t: [])
    monkeypatch.setattr(wc.gw, "Win32Window", refus, raising=False)
    monkeypatch.setattr(wc, "_list_visible_windows",
                        lambda: [{"hwnd": 5, "title": "#général | Atlas - Discord", "process": "Discord.exe"}])
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    wc._controller.focus_window("#général | Atlas - Discord")
    assert vus and all(v["title_re"] is None and v["handle"] == 5 for v in vus), vus


# --------------------------------------------------------------------------- #
#  4. L'outil d'envoi : Entrée en dernier, seulement si la fenêtre est toujours devant
# --------------------------------------------------------------------------- #

class Clavier:
    def __init__(self, monkeypatch, garde_le_focus=True):
        from tools import window_controller as wc

        self.devant = "Autre fenêtre"
        self.evenements = []
        self.garde = garde_le_focus

        def focus(title):
            self.devant = title
            return {"success": True, "message": "focus (simulé)", "title": title}

        def actif():
            return SimpleNamespace(title=self.devant)

        def taper(text, interval=0.02, use_clipboard=False):
            self.evenements.append(("texte", self.devant, text))
            if not self.garde:
                self.devant = "Une notification - Windows"
            return {"success": True, "message": "tapé"}

        monkeypatch.setattr(wc._controller, "focus_window", focus)
        monkeypatch.setattr(wc._controller, "type_text", taper)
        monkeypatch.setattr(wc._controller, "send_hotkey",
                            lambda *k: self.evenements.append(("touche", self.devant, k)) or {"success": True})
        monkeypatch.setattr(wc.gw, "getActiveWindow", actif)
        monkeypatch.setattr(wc, "_list_visible_windows", lambda: list(FENETRES))
        monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))


def test_gb4_envoi_tape_puis_entree_dans_la_bonne_fenetre(monkeypatch):
    from tools import window_controller as wc

    clavier = Clavier(monkeypatch)
    r = wc.window_send_message("(Atlas) Bonjour, c'est un test.", target="discord")
    assert r["success"] is True, r
    assert clavier.evenements == [
        ("texte", "#général | Atlas - Discord", "(Atlas) Bonjour, c'est un test."),
        ("touche", "#général | Atlas - Discord", ("enter",)),
    ]


def test_gb4_pas_d_entree_si_la_fenetre_a_perdu_le_premier_plan(monkeypatch):
    from tools import window_controller as wc

    clavier = Clavier(monkeypatch, garde_le_focus=False)
    r = wc.window_send_message("(Atlas) Bonjour", target="discord")
    assert r["success"] is False
    assert [e for e in clavier.evenements if e[0] == "touche"] == [], "Entrée envoyée ailleurs"


# --------------------------------------------------------------------------- #
#  5. La confirmation montre le texte exact et la fenêtre exacte
# --------------------------------------------------------------------------- #

def test_gb4_la_confirmation_montre_le_texte_et_la_fenetre(monkeypatch):
    from tools import window_controller as wc

    monkeypatch.setattr(wc, "_list_visible_windows", lambda: list(FENETRES))
    envoyes = []
    monkeypatch.setitem(ie.TOOL_HANDLERS, "window_send_message",
                        lambda args: envoyes.append(args) or {"success": True, "message": "envoyé"})
    confirmation._pending.clear()
    r = ie.request_confirmation("window_send_message", {"text": "(Atlas) Bonjour !", "target": "discord"},
                                {}, "envoyer un message")
    assert r["status"] == "confirmation_required", r
    assert "(Atlas) Bonjour !" in r["target"] and "#général | Atlas - Discord" in r["target"], r["target"]
    assert envoyes == [], "envoyé avant la confirmation"
    asyncio.run(ie.execute_confirmed(r["confirmation_id"], {}))
    assert envoyes == [{"text": "(Atlas) Bonjour !", "target": "#général | Atlas - Discord"}], envoyes
    confirmation._pending.clear()


def test_gb4_plusieurs_fenetres_rien_n_est_propose(monkeypatch):
    from tools import window_controller as wc

    monkeypatch.setattr(wc, "_list_visible_windows", lambda: list(FENETRES))
    confirmation._pending.clear()
    r = ie.request_confirmation("window_send_message", {"text": "x", "target": "bloc-notes"}, {}, "envoyer")
    assert r["status"] != "confirmation_required" and confirmation._pending == {}
    assert "Rapport.txt - Bloc-notes" in r["message"], r


# --------------------------------------------------------------------------- #
#  6. Constaté en réel : la ponctuation dépendait du clavier de la machine
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("texte", ["(Atlas) Bonjour", "Rendez-vous à 18 h !", "test 5", "a.b"])
def test_gb4_la_ponctuation_ne_depend_pas_du_clavier(monkeypatch, texte):
    """Rejeu réel (sprint G-bis) : « (Atlas) » est arrivé « 5Atlas° » — la frappe simulée suit
    un clavier américain ; sur un clavier AZERTY, « ( » et « ) » tombent sur « 5 » et « ° »,
    et « 5 » sur « ( ». Seuls les lettres et les espaces sont sûrs : le reste passe par le
    presse-papiers, qui est restauré ensuite."""
    from tools import window_controller as wc

    frappes, collages, presse = [], [], {"v": "contenu d'Alexis"}
    monkeypatch.setattr(wc.pyautogui, "typewrite", lambda t, interval=0: frappes.append(t))
    monkeypatch.setattr(wc.pyautogui, "hotkey", lambda *k: collages.append((presse["v"], k)))
    monkeypatch.setattr(wc.pyperclip, "copy", lambda t: presse.__setitem__("v", t))
    monkeypatch.setattr(wc.pyperclip, "paste", lambda: presse["v"])
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    wc._controller.type_text(texte)
    assert frappes == [], f"frappé touche par touche : {frappes}"
    assert collages == [(texte, ("ctrl", "v"))], collages
    assert presse["v"] == "contenu d'Alexis", "presse-papiers d'Alexis non restauré"
