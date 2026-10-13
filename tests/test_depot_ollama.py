"""
Sprint Dépôt + Ollama — les restes de G-ter (partie C).

C1 — « tu peux faire quoi ? » à la voix : une version courte, construite depuis le MÊME
     registre que la version écrite ; et le « détail d'une famille » qu'elle propose existe.
C2 — window_restore : le classifieur l'annonçait, le moteur ne l'avait pas.
C3 — une écriture dans la vraie mémoire par un essai lancé à part n'est plus possible.

Outils, fenêtres et mémoire SIMULÉS : rien n'est exécuté sur la machine, rien n'est écrit
dans la mémoire d'Alexis.
"""

import asyncio
import os
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


def _familles_ecrites(texte):
    return [ligne[2:].split(" :")[0] for ligne in texte.splitlines() if ligne.startswith("- ")
            and ligne[2:].split(" :")[0] in ie.CAPABILITY_FAMILIES]


# --------------------------------------------------------------------------- #
#  C1 — la version vocale courte
# --------------------------------------------------------------------------- #

def test_c1_la_version_vocale_est_courte_et_propose_le_detail():
    court = ie.capabilities_reply_voice()
    # La version écrite fait ~1 250 caractères, près d'une minute lue à voix haute.
    assert len(court) < 400, f"trop long pour la voix ({len(court)} caractères) : {court}"
    assert "détail" in court.lower(), court
    assert "confirmation" in court.lower(), court
    for jargon in ("_", "window", "*", "\n- "):
        assert jargon not in court, f"« {jargon} » dans la version vocale : {court}"


def test_c1_les_deux_versions_citent_les_memes_familles():
    ecrit = _familles_ecrites(ie.capabilities_reply())
    court = ie.capabilities_reply_voice().lower()
    assert ecrit, "aucune famille dans la version écrite"
    for famille in ie.CAPABILITY_FAMILIES:
        assert (famille.lower() in court) == (famille in ecrit), (famille, ecrit, court)


def test_c1_meme_registre_une_famille_sans_outil_disparait_des_deux(monkeypatch):
    """Une seule source : retirer du registre les outils d'une famille la retire des DEUX réponses."""
    sans_memoire = {t for t in ie.capability_tools() if ie.TOOL_CAPABILITIES[t][0] != "Mémoire"}
    monkeypatch.setattr(ie, "capability_tools", lambda: set(sans_memoire))
    assert "Mémoire" not in _familles_ecrites(ie.capabilities_reply())
    assert "mémoire" not in ie.capabilities_reply_voice().lower()


DETAIL = [
    ("que sais-tu faire avec les fenêtres ?", "Applications et fenêtres"),
    ("tu peux faire quoi avec les applications ?", "Applications et fenêtres"),
    ("tu peux faire quoi sur internet ?", "Internet"),
    ("qu'est-ce que tu sais faire avec la mémoire ?", "Mémoire"),
    ("que peux-tu faire sur le système ?", "Système"),
    ("tu sais faire quoi avec les modes ?", "Modes et automatisations"),
    ("qu'est-ce que tu peux faire pour écrire ailleurs ?", "Écrire ailleurs"),
    ("le détail de la famille internet", "Internet"),
    ("détaille la famille mémoire", "Mémoire"),
]


@pytest.mark.parametrize("phrase,famille", DETAIL)
def test_c1_le_detail_d_une_famille_existe_et_ne_lance_rien(executed, phrase, famille):
    """La version courte dit « demandez-moi le détail d'une famille » : ça doit marcher."""
    r = _run(phrase)
    assert executed == [], f"{phrase!r} a déclenché {executed}"
    texte = _message(r)
    outils = ie.capability_tools()
    attendus = [label for t, (fam, label) in ie.TOOL_CAPABILITIES.items() if fam == famille and t in outils]
    autres = [label for t, (fam, label) in ie.TOOL_CAPABILITIES.items() if fam != famille and t in outils]
    assert attendus, famille
    for label in attendus:
        assert label in texte, f"{phrase!r} : « {label} » manque dans {texte!r}"
    for label in autres:
        # « l'oublier » (Mémoire) est contenu dans d'autres libellés ? non ; on vérifie en entier.
        assert f" {label}," not in f" {texte}," and f" {label}." not in f" {texte}", \
            f"{phrase!r} : « {label} » d'une autre famille dans {texte!r}"


def test_c1_une_question_sur_un_mode_precis_reste_une_question_sur_ce_mode():
    """« tu peux faire quoi avec le mode travail ? » parle d'UN mode, pas de la famille."""
    intent = _classify("c'est quoi le mode travail ?")
    assert intent.verb != "capabilities_family", intent


def test_c1_la_voix_prononce_la_version_courte(monkeypatch):
    """Le chemin vocal dit la version courte ; l'écran garde la version complète."""
    import core.context_monitor as cm
    import core.memory_manager as mm
    import core.world_state as wsm
    from core.voice_engine import VoiceEngine

    memoire = SimpleNamespace(recall_texts=lambda *a, **k: [], add_to_session=lambda *a, **k: None)
    monde = SimpleNamespace(update_from_context=lambda c: None, add_to_history=lambda *a: None)
    monkeypatch.setattr(cm, "collect_context", lambda: {})
    monkeypatch.setattr(mm, "get_memory_manager", lambda: memoire)
    monkeypatch.setattr(wsm, "get_world_state", lambda: monde)

    moteur = VoiceEngine.__new__(VoiceEngine)
    dit = asyncio.run(moteur._run_text_pipeline("tu peux faire quoi ?"))
    assert dit == ie.capabilities_reply_voice(), dit
    # À l'écran, la réponse reste la version complète (GT1).
    assert _message(_run("tu peux faire quoi ?")) == ie.capabilities_reply()


# --------------------------------------------------------------------------- #
#  C2 — window_restore : le moteur l'exécute, avec les règles de window_focus
# --------------------------------------------------------------------------- #

def test_c2_window_restore_existe_dans_le_moteur_et_est_annonce():
    assert "window_restore" in ie.TOOL_HANDLERS, "le classifieur l'annonce, le moteur ne l'a pas"
    assert "window_restore" in ie.capability_tools()


@pytest.mark.parametrize("phrase,cible", [
    ("restaure le bloc-notes", "bloc-notes"),
    ("restaure la fenêtre steam", "steam"),
    ("restore notepad", "notepad"),
])
def test_c2_restaurer_une_fenetre_nommee_est_compris(phrase, cible):
    r = _resolve(phrase)
    assert r.tool == "window_restore", (phrase, r.tool, r.params)
    assert r.params.get("title", "").lower() == cible, r.params


def test_c2_restaurer_atteint_l_outil_sans_confirmation(executed):
    r = _run("restaure le bloc-notes")
    assert executed == [("window_restore", {"title": "bloc-notes"})], (executed, r)


def _fenetres(monkeypatch, windows, premier_plan_obeit=True):
    from tools import window_controller as wc

    devant = {"titre": "Atlas Desktop"}
    restaurees = []
    monkeypatch.setattr(wc, "_list_visible_windows", lambda: list(windows))
    monkeypatch.setattr(wc, "_restore_hwnd", lambda hwnd: restaurees.append(hwnd) or True)

    def focus(title):
        if premier_plan_obeit:
            devant["titre"] = title
        return {"success": True, "message": "focus (simulé)", "title": title}

    monkeypatch.setattr(wc._controller, "focus_window", focus)
    monkeypatch.setattr(wc.gw, "getActiveWindow", lambda: SimpleNamespace(title=devant["titre"]))
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    return devant, restaurees


def test_c2_la_fenetre_nommee_est_restauree_puis_verifiee_au_premier_plan(monkeypatch):
    from tools import window_controller as wc

    devant, restaurees = _fenetres(monkeypatch, [{"hwnd": 11, "title": "Sans titre - Bloc-notes", "process": "notepad.exe"},
                                                 {"hwnd": 12, "title": "Steam", "process": "steamwebhelper.exe"}])
    r = wc.window_restore("bloc-notes")
    assert r["success"] is True, r
    assert restaurees == [11], restaurees
    assert devant["titre"] == "Sans titre - Bloc-notes"
    assert "restaurée" in r["message"] and "Bloc-notes" in r["message"], r["message"]


def test_c2_sans_premier_plan_le_succes_n_est_pas_annonce(monkeypatch):
    from tools import window_controller as wc

    _, restaurees = _fenetres(monkeypatch, [{"hwnd": 11, "title": "Sans titre - Bloc-notes", "process": "notepad.exe"}],
                              premier_plan_obeit=False)
    r = wc.window_restore("bloc-notes")
    assert r["success"] is False, r
    assert "premier plan" in r["message"], r["message"]


@pytest.mark.parametrize("titre", ["", "   ", None])
def test_c2_titre_vide_ne_touche_aucune_fenetre(monkeypatch, titre):
    from tools import window_controller as wc

    _, restaurees = _fenetres(monkeypatch, [{"hwnd": 11, "title": "Sans titre - Bloc-notes", "process": "notepad.exe"}])
    r = wc.window_restore(titre)
    assert r["success"] is False and restaurees == [], (r, restaurees)


def test_c2_plusieurs_fenetres_on_demande_laquelle(monkeypatch):
    from tools import window_controller as wc

    _, restaurees = _fenetres(monkeypatch, [{"hwnd": 11, "title": "a.txt - Bloc-notes", "process": "notepad.exe"},
                                            {"hwnd": 12, "title": "b.txt - Bloc-notes", "process": "notepad.exe"}])
    r = wc.window_restore("bloc-notes")
    assert r["success"] is False and restaurees == [], (r, restaurees)
    assert "plusieurs" in r["message"], r["message"]


def test_c2_aucune_fenetre_rien_n_est_restaure(monkeypatch):
    from tools import window_controller as wc

    _, restaurees = _fenetres(monkeypatch, [{"hwnd": 12, "title": "Steam", "process": "steamwebhelper.exe"}])
    r = wc.window_restore("bloc-notes")
    assert r["success"] is False and restaurees == [], (r, restaurees)


def test_c2_une_automatisation_ne_restaure_pas_de_fenetre():
    """Comme réduire ou agrandir : la fenêtre au moment du déclenchement est inconnue."""
    from core import validator

    exclus = set().union(*validator._AUTOMATION_EXCLUSIONS.values())
    assert "window_restore" in exclus


# --------------------------------------------------------------------------- #
#  C3 — un essai lancé à part n'écrit plus dans la vraie mémoire
# --------------------------------------------------------------------------- #

def test_c3_hors_d_atlas_la_vraie_memoire_n_est_pas_branchee(monkeypatch):
    """L'essai à blanc de G-ter (un `python -c` qui importait le moteur) a écrit dans
    atlas_errors. Sans ATLAS_MEMORY=real, posé par main.py, aucune connexion n'est ouverte."""
    import chromadb
    import core.memory_manager as mm

    connexions = []
    monkeypatch.delenv("ATLAS_MEMORY", raising=False)
    monkeypatch.setattr(chromadb, "HttpClient", lambda *a, **k: connexions.append(k) or (_ for _ in ()).throw(
        AssertionError("connexion à la vraie mémoire")))
    m = mm.MemoryManager()
    m.save("error", "intent=automation cible= app=")
    assert connexions == [], connexions
    assert m.is_connected() is False


def test_c3_main_py_branche_la_vraie_memoire():
    texte = (pathlib.Path(__file__).resolve().parent.parent / "main.py").read_text(encoding="utf-8")
    assert 'os.environ.setdefault("ATLAS_MEMORY", "real")' in texte, "main.py doit brancher la vraie mémoire"
    # Posé AVANT les imports d'Atlas, comme ANONYMIZED_TELEMETRY.
    assert texte.index('"ATLAS_MEMORY"') < texte.index("from core"), "à poser avant les imports"


def test_c3_la_regle_est_inscrite_dans_rapport_rules():
    texte = (pathlib.Path(__file__).resolve().parent.parent / "docs" / "RAPPORT_RULES.md").read_text(encoding="utf-8")
    assert "sans lui redemander" in texte and "apply-ids" in texte, "règle C3 absente"
