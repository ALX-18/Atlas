"""
Sprint G-ter — la première impression d'un testeur.

Les phrases EXACTES de la session d'Alexis du 11/10/2026 servent de tests :
« tu peux faire quoi ? », « toi fais le », « il consiste à quoi le mode gaming ? »,
« Fermes, Steam. », « ouvre steam » après fermeture de la fenêtre.

Outils, fenêtres et processus SIMULÉS : rien n'est exécuté sur la machine.
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


def _resolve(phrase):
    from core.validator import get_validator

    return get_validator().resolve(_classify(phrase), {})


@pytest.fixture
def executed(monkeypatch):
    calls = []
    for name in list(ie.TOOL_HANDLERS):
        if name in ("workflow_describe",):
            continue
        monkeypatch.setitem(ie.TOOL_HANDLERS, name,
                            (lambda n: lambda args: calls.append((n, args)) or {"success": True, "message": n})(name))
    monkeypatch.setattr(ie, "_save_action_to_memory", lambda *a, **k: None)
    confirmation._pending.clear()
    yield calls
    confirmation._pending.clear()


def _run(phrase):
    return asyncio.run(ie.get_execution_engine().execute(_resolve(phrase), {}))


def _message(r):
    res = r.get("result")
    return (res.get("message") if isinstance(res, dict) else None) or r.get("message") or ""


# --------------------------------------------------------------------------- #
#  GT1 — « tu peux faire quoi ? » : une réponse fixe, construite depuis le registre
# --------------------------------------------------------------------------- #

FORMES_AIDE = ["tu peux faire quoi ?", "tu sais faire quoi ?", "qu'est-ce que tu sais faire ?",
               "qu'est-ce que tu peux faire ?", "aide", "tes capacités", "AH ok ok et donc tu peux faire quoi ?"]


@pytest.mark.parametrize("phrase", FORMES_AIDE)
def test_gt1_les_formes_d_aide_recoivent_la_reponse_fixe(executed, phrase):
    r = _run(phrase)
    assert executed == [], f"{phrase!r} a déclenché {executed}"
    assert _message(r) == ie.capabilities_reply(), f"{phrase!r} → {_message(r)[:120]!r}"


def test_gt1_qu_est_ce_que_tu_sais_faire_ne_rejoue_toujours_rien():
    intent = _classify("qu'est-ce que tu sais faire ?")
    assert (intent.category, intent.verb) != ("memory", "redo")


def test_gt1_la_reponse_n_annonce_que_des_outils_reels_et_les_annonce_tous():
    """Une seule source de vérité : le registre des outils que le moteur exécute."""
    from core.intent_classifier import INTENT_CATEGORIES

    exposes = {t for cat in INTENT_CATEGORIES.values() for t in cat.get("tools", {}).values()}
    reels = exposes & set(ie.TOOL_HANDLERS)
    annonces = ie.capability_tools()
    assert annonces <= set(ie.TOOL_HANDLERS), f"annoncés sans outil : {annonces - set(ie.TOOL_HANDLERS)}"
    assert reels <= annonces, f"outils réels absents de la réponse : {reels - annonces}"
    # Dépôt + Ollama / C2 : window_restore était annoncé par le classifieur sans exister dans
    # le moteur, donc tenu hors de la réponse. Il existe désormais : plus aucun outil exposé
    # ne manque au moteur.
    assert exposes <= set(ie.TOOL_HANDLERS), f"exposés sans outil : {exposes - set(ie.TOOL_HANDLERS)}"
    assert "window_restore" in annonces


def test_gt1_la_reponse_dit_ce_qui_demande_une_confirmation_et_reste_lisible():
    texte = ie.capabilities_reply()
    assert "confirmation" in texte.lower()
    for jargon in ("_", "window", "launch", "workflow_run", "TOOL"):
        assert jargon not in texte, f"jargon « {jargon} » : {texte}"
    # Avec la ligne des modes existants (chargés au démarrage), environ 1 250 caractères.
    assert len(texte) < 1400, f"trop long ({len(texte)} caractères)"


def test_gt1_la_consigne_ne_fait_plus_nier_qu_atlas_sait_agir():
    from core.ollama_client import build_system_prompt

    prompt = build_system_prompt({}, memories=[])
    assert "Tu n'agis JAMAIS toi-même" not in prompt
    assert "ouvrir une application" in prompt, "le modèle doit savoir ce qu'Atlas sait faire"


# --------------------------------------------------------------------------- #
#  GT2 — une question sur un mode n'est pas un ordre
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase", ["il consiste à quoi le mode gaming ?", "c'est quoi le mode gaming ?",
                                    "que fait le mode travail ?", "qu'est-ce qu'il y a dans le mode gaming ?"])
def test_gt2_une_question_sur_un_mode_le_decrit_sans_rien_lancer(executed, phrase):
    r = _run(phrase)
    assert r.get("status") != "confirmation_required", f"{phrase!r} propose de lancer le mode : {r}"
    assert executed == []
    msg = _message(r)
    assert "Steam" in msg or "VS Code" in msg, f"description absente : {msg!r}"


def test_gt2_lancer_le_mode_demande_toujours_la_confirmation(executed):
    r = _run("lance le mode travail")
    assert r.get("status") == "confirmation_required", r
    assert "Mode Travail" in r.get("target", ""), f"la confirmation doit nommer le mode et ses étapes : {r}"


@pytest.mark.parametrize("phrase,nom", [("lance le mode gaming", "Mode Gaming"),
                                        ("nettoie le système", "Nettoyage Système")])
def test_gt2_un_mode_desactive_n_est_pas_propose_au_lancement(executed, phrase, nom):
    """Mode Gaming (arrête un processus) et Nettoyage Système (vide la corbeille) sont désactivés
    depuis B1-ter : une action à confirmation n'a pas sa place dans un mode. Demander une
    confirmation pour répondre ensuite « désactivé » serait une promesse non tenue."""
    r = _run(phrase)
    assert r.get("status") != "confirmation_required", f"{phrase!r} : {r}"
    msg = _message(r)
    assert nom in msg and "désactivé" in msg and "lance le" not in msg, msg


def test_gt2_la_liste_des_capacites_ne_cite_que_les_modes_utilisables():
    from core.workflow_engine import get_workflow_engine

    get_workflow_engine().load_workflows()
    texte = ie.capabilities_reply()
    assert "Mode Travail" in texte and "Mode Gaming" not in texte, texte


@pytest.mark.parametrize("phrase", ["active le mode sombre", "active le mode avion"])
def test_gt2_un_mode_inexistant_n_est_jamais_propose(executed, phrase):
    r = _run(phrase)
    assert r.get("status") != "confirmation_required", f"{phrase!r} : {r}"
    msg = _message(r)
    # Seuls les modes utilisables sont cités (Mode Gaming est désactivé depuis B1-ter).
    assert "connais pas" in msg and "Mode Travail" in msg and "Mode Gaming" not in msg, msg


# --------------------------------------------------------------------------- #
#  GT3 — la cible ne garde pas le verbe
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase,verbe,cible", [
    ("Fermes, Steam.", "close", "steam"),          # transcription réelle de la session
    ("Ferme, Steam !", "close", "steam"),
    ("Fermez Steam", "close", "steam"),
    ("ferme-moi Steam", "close", "steam"),
    ("Fermer Steam.", "close", "steam"),
    ("Ouvres Discord.", "open", "discord"),
    ("Réduis, Chrome.", "minimize", "chrome"),
    ("Mets Steam au premier plan.", "focus", "steam"),
])
def test_gt3_la_cible_ne_contient_ni_le_verbe_ni_la_ponctuation(phrase, verbe, cible):
    intent = _classify(phrase)
    assert (intent.category, intent.verb) == ("window_mgmt", verbe), f"{phrase!r} → {intent.category}/{intent.verb}"
    titre = (intent.params.get("title") or intent.params.get("name") or "").lower()
    assert titre == cible, f"{phrase!r} → cible {titre!r}"


# --------------------------------------------------------------------------- #
#  GT4 — « ouvre steam » quand Steam tourne déjà
# --------------------------------------------------------------------------- #

def _machine(monkeypatch, windows, running=True):
    import tools.app_launcher as al
    from tools import window_controller as wc

    devant = {"titre": "Atlas Desktop"}
    lances = []
    monkeypatch.setattr(al, "_is_process_running", lambda n: running)
    monkeypatch.setattr(wc, "_list_visible_windows", lambda: list(windows))

    def focus(title):
        devant["titre"] = title
        return {"success": True, "message": "focus (simulé)", "title": title}

    monkeypatch.setattr(wc._controller, "focus_window", focus)
    monkeypatch.setattr(wc.gw, "getActiveWindow", lambda: SimpleNamespace(title=devant["titre"]))
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    monkeypatch.setattr(al.os, "startfile", lambda target: lances.append(target))
    monkeypatch.setattr(al, "time", SimpleNamespace(sleep=lambda s: None, monotonic=lambda: 0.0))
    return devant, lances


def test_gt4_une_fenetre_existe_elle_revient(monkeypatch):
    import tools.app_launcher as al

    # Réalité constatée : les fenêtres de Steam appartiennent à steamwebhelper.exe.
    devant, lances = _machine(monkeypatch, [{"hwnd": 6, "title": "Liste de contacts", "process": "steamwebhelper.exe"},
                                            {"hwnd": 7, "title": "Steam", "process": "steamwebhelper.exe"}])
    r = al.bring_running_app("steam")
    assert r and r["success"] is True, r
    assert devant["titre"] == "Steam" and lances == []
    assert "ramène" in r["message"] and "Steam" in r["message"], r["message"]


def test_gt4_steam_sans_fenetre_est_rappele_sans_second_exemplaire(monkeypatch):
    import tools.app_launcher as al

    fenetres = []
    devant, lances = _machine(monkeypatch, fenetres)
    real_startfile = al.os.startfile

    def startfile(target):
        lances.append(target)
        fenetres.append({"hwnd": 8, "title": "Steam", "process": "steamwebhelper.exe"})   # Steam réaffiche sa fenêtre

    monkeypatch.setattr(al.os, "startfile", startfile)
    r = al.bring_running_app("steam")
    assert lances == ["steam://open/main"], f"Steam doit être rappelé par son protocole : {lances}"
    assert r["success"] is True and "Steam" in r["message"], r


def test_gt4_une_application_sans_fenetre_inconnue_n_est_pas_relancee(monkeypatch):
    import tools.app_launcher as al

    devant, lances = _machine(monkeypatch, [])
    r = al.bring_running_app("notepad")
    assert lances == [], "second exemplaire ouvert"
    assert r["success"] is False and "arrière-plan" in r["message"], r


def test_gt4_le_moteur_ne_dit_plus_seulement_deja_lance(monkeypatch, executed):
    import tools.app_launcher as al

    monkeypatch.setattr(al, "bring_running_app",
                        lambda n: {"success": True, "message": "Steam était déjà lancé, je ramène sa fenêtre."})
    monkeypatch.setattr(al, "_is_process_running", lambda n: True)
    r = asyncio.run(ie.get_execution_engine().execute(_resolve("ouvre steam"), {}))
    assert "ramène sa fenêtre" in _message(r), r
    assert "déjà accomplie" not in _message(r)


# --------------------------------------------------------------------------- #
#  GT5 — l'avertissement GPU dit ce que la transcription utilise vraiment
# --------------------------------------------------------------------------- #

def test_gt5_pas_d_alerte_gpu_quand_la_transcription_tourne_sur_le_gpu(monkeypatch):
    import main

    level, message = main._voice_gpu_status({"enabled": True, "stt_device": "cuda"},
                                           ct2_cuda_devices=1, torch_cuda=False)
    assert level == "info", (level, message)
    assert "aucun GPU" not in message and "GPU" in message


def test_gt5_alerte_si_la_transcription_ne_voit_pas_de_gpu(monkeypatch):
    import main

    level, message = main._voice_gpu_status({"enabled": True, "stt_device": "cuda"},
                                           ct2_cuda_devices=0, torch_cuda=False)
    assert level == "warning" and "lente" in message, (level, message)


def test_gt5_doctor_ne_dit_plus_que_main_affiche_un_faux_message():
    texte = (pathlib.Path(__file__).resolve().parent.parent / "scripts" / "doctor.py").read_text(encoding="utf-8")
    assert "faux 'aucun GPU CUDA'" not in texte


def test_gt4_seule_une_fenetre_secondaire_steam_est_rappele(monkeypatch):
    """Rejeu réel (G-ter) : fenêtre principale fermée, « Liste de contacts » restée ouverte.
    « ouvre steam » a répondu « je ramène sa fenêtre » en ramenant la liste de contacts — la
    fenêtre principale, elle, n'est pas revenue. Annonce trompeuse."""
    import tools.app_launcher as al

    fenetres = [{"hwnd": 6, "title": "Liste de contacts", "process": "steamwebhelper.exe"}]
    devant, lances = _machine(monkeypatch, fenetres)

    def startfile(target):
        lances.append(target)
        fenetres.append({"hwnd": 8, "title": "Steam", "process": "steamwebhelper.exe"})

    monkeypatch.setattr(al.os, "startfile", startfile)
    r = al.bring_running_app("steam")
    assert lances == ["steam://open/main"], f"la fenêtre principale doit être rappelée : {lances}"
    assert r["success"] is True and "Liste de contacts" not in r["message"], r


def test_gt4_le_succes_n_est_annonce_que_si_la_fenetre_principale_revient(monkeypatch):
    import tools.app_launcher as al

    fenetres = [{"hwnd": 6, "title": "Liste de contacts", "process": "steamwebhelper.exe"}]
    devant, lances = _machine(monkeypatch, fenetres)        # le rappel ne fait rien apparaître
    r = al.bring_running_app("steam")
    assert r["success"] is False and "aucune fenêtre" in r["message"], r


@pytest.mark.parametrize("phrase", ["toi fais le", "fais-le", "vas-y fais-le", "fais le toi", "tu peux le faire ?"])
def test_gt1_toi_fais_le_recoit_une_reponse_fixe_qui_ne_nie_pas(executed, phrase):
    """Session d'Alexis : « toi fais le » → « je ne peux pas effectuer d'action sur votre
    ordinateur ». Rejeu G-ter, consigne corrigée : encore 3 fois sur 5 « je ne peux pas effectuer
    cette action pour vous ». Une réponse juste ne repose pas sur une probabilité."""
    r = _run(phrase)
    msg = _message(r)
    assert executed == []
    assert "ne peux pas" not in msg.lower() and "directement" in msg, f"{phrase!r} → {msg!r}"
