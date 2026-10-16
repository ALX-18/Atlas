"""
Sprint Index des fichiers — l'index (IX2), ce qu'Atlas sait faire avec (IX3), et les restes
d'Apprentissage 2 (IX4) : sauvegarde vérifiée par les données, premier plan sur la fenêtre exacte.

Aucun test ne lit les vrais disques d'Alexis : les arborescences sont créées dans des dossiers
jetables, les ouvertures sont simulées (comptées, jamais faites).
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from test_sans_docker import _seul_dossier, sauvegarde  # noqa: E402,F401  (fixture SD3 réutilisée)

ALEXIS = "fenetre"


def _chat(message, origine=ALEXIS):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    return asyncio.run(chat_endpoint(ChatRequest(message=message, history=[], origine=origine)))


# --------------------------------------------------------------------------- #
#  IX4.1 — une sauvegarde est vérifiée par ses DONNÉES ; les 40 requêtes sont indicatives
# --------------------------------------------------------------------------- #

def test_ix4_verify_par_les_donnees_un_ordre_de_requetes_different_ne_fait_pas_echouer(sauvegarde):
    bm, source, dest = sauvegarde
    assert bm.main(["backup", "--source", str(source), "--dest", str(dest)]) == 0
    sv = _seul_dossier(dest)
    m = json.loads((sv / "manifest.json").read_text(encoding="utf-8"))
    assert m["donnees"]["atlas_memory_e5"]["count"] == 12
    # La recherche approchée de ChromaDB a rendu un autre ordre au relevé (vu le 15/10) :
    for ligne in m["requetes"]:
        if ligne.get("atlas_memory_e5"):
            ligne["atlas_memory_e5"] = list(reversed(ligne["atlas_memory_e5"]))
    (sv / "manifest.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    assert bm.main(["verify", str(sv)]) == 0
    rapport = json.loads(sorted(sv.glob("verify_*.json"))[-1].read_text(encoding="utf-8"))
    assert rapport["ok"] and rapport["donnees_identiques"]
    assert rapport["requetes_40"]["ordres_differents"] > 0 and rapport["requetes_40"]["indicatif"] is True


def test_ix4_verify_echoue_si_un_element_differe(sauvegarde):
    bm, source, dest = sauvegarde
    bm.main(["backup", "--source", str(source), "--dest", str(dest)])
    sv = _seul_dossier(dest)
    m = json.loads((sv / "manifest.json").read_text(encoding="utf-8"))
    un_id = sorted(m["donnees"]["atlas_documents"]["elements"])[0]
    m["donnees"]["atlas_documents"]["elements"][un_id] = "0" * 64      # texte, métadonnées ou vecteur changé
    (sv / "manifest.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    assert bm.main(["verify", str(sv)]) == 1
    rapport = json.loads(sorted(sv.glob("verify_*.json"))[-1].read_text(encoding="utf-8"))
    assert rapport["donnees"]["atlas_documents"]["differents"] == [un_id]


def test_ix4_verify_echoue_si_un_element_manque(sauvegarde):
    bm, source, dest = sauvegarde
    bm.main(["backup", "--source", str(source), "--dest", str(dest)])
    sv = _seul_dossier(dest)
    m = json.loads((sv / "manifest.json").read_text(encoding="utf-8"))
    m["donnees"]["atlas_errors"]["elements"]["atlas_errors_fantome"] = "1" * 64
    m["donnees"]["atlas_errors"]["count"] += 1
    (sv / "manifest.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    assert bm.main(["verify", str(sv)]) == 1


# --------------------------------------------------------------------------- #
#  IX4.2 — lignes d'essais du journal : plan montré, retrait seulement avec --oui
# --------------------------------------------------------------------------- #

def _journal_jetable(tmp_path):
    lignes = [
        {"timestamp": "2026-10-15T11:00:00", "user_input": "clique sur Magasin dans AtlasEssaiSombre", "tool": "ui_click_element"},
        {"timestamp": "2026-10-15T11:02:00", "user_input": "ouvre la calculatrice", "tool": "launch_app"},     # phrase d'essai, session d'essai
        {"timestamp": "2026-10-15T11:03:00", "user_input": "automation:workflow", "tool": None},
        {"timestamp": "2026-10-15T11:04:00", "user_input": "active le mode avion", "tool": "workflow_describe"},  # doute : gardée
        {"timestamp": "2026-10-15T20:00:00", "user_input": "ouvre la calculatrice", "tool": "launch_app"},     # hors session : à Alexis
        {"timestamp": "2026-04-09T18:00:00", "user_input": "ouvre notepad", "tool": "launch_app"},             # désignée par Alexis
    ]
    j = tmp_path / "atlas_actions.jsonl"
    j.write_text("".join(json.dumps(l, ensure_ascii=False) + "\n" for l in lignes) + "pas du json\n", encoding="utf-8")
    return j


def test_ix4_journal_plan_ne_retient_que_l_indubitable_et_retirer_exige_oui(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import nettoyer_journal as nj

    j = _journal_jetable(tmp_path)
    monkeypatch.setattr(nj, "JOURNAL", j)
    monkeypatch.setattr(nj, "SAUVEGARDES", tmp_path / "sauvegardes")
    avant = j.read_bytes()
    plan = tmp_path / "plan.json"
    assert nj.main(["plan", "--sortie", str(plan), "--phrase", "ouvre notepad"]) == 0
    p = json.loads(plan.read_text(encoding="utf-8"))
    assert [r["ligne"] for r in p["a_retirer"]] == [1, 2, 3, 6]
    assert j.read_bytes() == avant                                       # le plan ne touche à rien
    with pytest.raises(SystemExit):
        nj.main(["retirer", "--plan", str(plan)])                       # sans --oui
    assert j.read_bytes() == avant
    assert nj.main(["retirer", "--plan", str(plan), "--oui"]) == 0
    restantes = j.read_text(encoding="utf-8").splitlines()
    assert len(restantes) == 3 and "active le mode avion" in restantes[0] and restantes[2] == "pas du json"
    (copie,) = (tmp_path / "sauvegardes").glob("*.jsonl")
    assert copie.read_bytes() == avant


def test_ix4_journal_change_depuis_le_plan_refuse(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import nettoyer_journal as nj

    j = _journal_jetable(tmp_path)
    monkeypatch.setattr(nj, "JOURNAL", j)
    monkeypatch.setattr(nj, "SAUVEGARDES", tmp_path / "sauvegardes")
    plan = tmp_path / "plan.json"
    nj.main(["plan", "--sortie", str(plan)])
    with open(j, "a", encoding="utf-8") as f:
        f.write('{"timestamp": "2026-10-16T09:00:00", "user_input": "ouvre steam"}\n')   # Alexis a utilisé Atlas
    with pytest.raises(SystemExit, match="a changé"):
        nj.main(["retirer", "--plan", str(plan), "--oui"])


# --------------------------------------------------------------------------- #
#  IX2 — l'index : arborescence jetable, jamais les vrais disques
# --------------------------------------------------------------------------- #

def _docx(chemin, texte):
    import zipfile

    with zipfile.ZipFile(chemin, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body><w:p><w:t>{texte}</w:t></w:p></w:body></w:document>")


@pytest.fixture
def arbre(tmp_path, monkeypatch):
    """Un faux PC : documents, dossiers exclus, et l'indexeur pointé dessus seulement."""
    import os
    import time as _t

    import core.file_indexer as fi

    r = tmp_path / "pc"
    (r / "Documents" / "Stage").mkdir(parents=True)
    (r / "Telechargements").mkdir()
    (r / "Projet" / "node_modules" / "lib").mkdir(parents=True)
    (r / "Windows" / "System32").mkdir(parents=True)
    (r / "Documents" / "CV_Alexis_2026.docx").write_bytes(b"")
    _docx(r / "Documents" / "CV_Alexis_2026.docx", "Expérience professionnelle")
    _docx(r / "Documents" / "Stage" / "Rapport de stage.docx", "Le budget prévisionnel du projet est de 4000 euros.")
    (r / "Documents" / "notes.md").write_text("liste de courses : pain, lait", encoding="utf-8")
    (r / "Telechargements" / "facture_edf.pdf").write_bytes(b"%PDF-1.4 pas un vrai pdf")
    (r / "Telechargements" / "setup_outil.exe").write_bytes(b"MZ")
    (r / "Projet" / "node_modules" / "lib" / "rapport.txt").write_text("budget", encoding="utf-8")
    (r / "Windows" / "System32" / "rapport.txt").write_text("budget", encoding="utf-8")
    hier = _t.time() - 86400
    os.utime(r / "Documents" / "notes.md", (hier, hier))
    # Le dossier jetable est sous AppDataocaltemp : exclu par chemin dans la vraie configuration.
    cfg = {**fi.charger_config(), "scan_roots": [str(r)], "exclude_dirs": [], "cpu_max_pourcent": 100,
           "pause_en_jeu": True}
    idx = fi.FileIndexer()
    idx._cfg = cfg
    monkeypatch.setattr(fi, "jeu_en_plein_ecran", lambda: False)
    fi.oublier_index()
    yield idx, r
    fi.oublier_index()


def test_ix2_exclusions_et_contenu(arbre):
    import core.file_indexer as fi

    idx, r = arbre
    fin = idx.passage()
    noms = {x["nom"] for x in fi.chercher_nom("rapport", limite=20)}
    assert "Rapport de stage.docx" in noms
    assert "rapport.txt" not in noms, "node_modules et Windows sont exclus"
    assert fin["fichiers"] == 5                                     # CV, rapport, notes, facture, setup
    (hit,) = fi.chercher_contenu("budget previsionnel")              # sans accents ni casse
    assert hit["nom"] == "Rapport de stage.docx" and "«budget»" in hit["extrait"].lower()


def test_ix2_mise_a_jour_incrementale_et_disparus(arbre):
    import core.file_indexer as fi

    idx, r = arbre
    idx.passage()
    fin = idx.passage()
    assert fin["nouveaux_ou_modifies"] == 0 and fin["documents_lus"] == 0     # rien n'a changé : rien relu
    (r / "Documents" / "notes.md").write_text("le budget des vacances", encoding="utf-8")
    (r / "Telechargements" / "facture_edf.pdf").unlink()
    fin = idx.passage()
    assert fin["nouveaux_ou_modifies"] == 1 and fin["documents_lus"] == 1
    assert not fi.chercher_nom("facture edf")
    assert {h["nom"] for h in fi.chercher_contenu("budget")} == {"Rapport de stage.docx", "notes.md"}


def test_ix2_classement_explicable(arbre):
    import core.file_indexer as fi

    idx, r = arbre
    idx.passage()
    (premier,) = fi.chercher_nom("cv", limite=1)
    assert premier["nom"] == "CV_Alexis_2026.docx" and premier["raison"] == "tous les mots dans le nom"
    (dossier,) = fi.chercher_nom("stage", limite=1)
    assert dossier["raison"] in ("tous les mots dans le nom", "tous les mots dans le dossier")
    (approche,) = fi.chercher_nom("raport de stag", limite=1)
    assert approche["nom"] == "Rapport de stage.docx" and approche["raison"] == "nom approché"


def test_ix2_recents_par_date(arbre):
    import time as _t

    import core.file_indexer as fi

    idx, r = arbre
    idx.passage()
    debut_hier = _t.time() - 2 * 86400
    assert [x["nom"] for x in fi.recents(debut_hier, _t.time() - 3600, limite=10)] == ["notes.md"]
    assert [x["nom"] for x in fi.recents(_t.time() - 3600, ext={".pdf"})] == ["facture_edf.pdf"]


def test_ix2_pause_pendant_un_jeu_en_plein_ecran(arbre, monkeypatch):
    import core.file_indexer as fi

    idx, r = arbre
    etats = iter([True, True, False] + [False] * 1000)
    pauses = []
    monkeypatch.setattr(fi, "jeu_en_plein_ecran", lambda: next(etats))
    monkeypatch.setattr(fi.time, "sleep", lambda s: pauses.append(s))
    idx._attendre(fi.time.perf_counter())
    assert pauses.count(5) == 2                                            # attend que le jeu se termine


def test_ix2_plafond_cpu(arbre, monkeypatch):
    import core.file_indexer as fi

    idx, r = arbre
    idx._cfg = {**idx._cfg, "cpu_max_pourcent": 25}
    pauses = []
    monkeypatch.setattr(fi.time, "sleep", lambda s: pauses.append(s))
    monkeypatch.setattr(fi.time, "perf_counter", lambda: 1.0)
    idx._attendre(0.0)                                                     # 1 s de travail
    assert pauses == [3.0]                                                 # 3 s de pause : 25 % d'un cœur


def test_ix2_les_profils_des_autres_et_les_disques_non_fixes(monkeypatch, tmp_path):
    import os

    import core.file_indexer as fi

    profils = tmp_path / "Users"
    (profils / "moi").mkdir(parents=True)
    (profils / "autre").mkdir()
    monkeypatch.setenv("USERPROFILE", str(profils / "moi"))
    regles = fi.Exclusions([], [])
    assert regles.exclu(str(profils / "autre"), "autre")
    assert not regles.exclu(str(profils / "moi"), "moi")
    if os.name == "nt":
        import ctypes
        for d in fi.disques_fixes():
            assert ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(d)) == 3


def test_ix2_l_index_est_une_base_a_part_ignoree_par_git_et_hors_sauvegarde():
    import subprocess

    import core.file_indexer as fi

    r = subprocess.run(["git", "check-ignore", "data/file_index.db"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, "data/file_index.db doit être ignoré par Git"
    sys.path.insert(0, str(ROOT / "scripts"))
    import backup_memory as bm

    assert "file_index.db" not in bm.SQLITE_FICHIERS                        # pas une mémoire
    assert fi.DB_PATH.name == "file_index.db"


# --------------------------------------------------------------------------- #
#  IX3 — ce qu'Atlas sait faire, sur le vrai chemin /api/chat (ouvertures simulées)
# --------------------------------------------------------------------------- #

@pytest.fixture
def pc(arbre, monkeypatch):
    """Le faux PC indexé ; « ouvrir » et « montrer dans l'explorateur » sont comptés, jamais faits."""
    import core.file_indexer as fi
    import tools.fichiers as tf
    from core import propositions

    idx, r = arbre
    (r / "Documents" / "Rapport annuel.pdf").write_bytes(b"%PDF")
    (r / "Telechargements" / "installe_moi.bat").write_text("echo", encoding="utf-8")
    idx.passage()
    ouverts, montres = [], []
    monkeypatch.setattr(tf, "_ouvrir_systeme", lambda chemin: ouverts.append(chemin))
    monkeypatch.setattr(tf, "_montrer_dans_explorateur", lambda chemin: montres.append(chemin))
    monkeypatch.setattr(tf, "dossier_telechargements", lambda: str(r / "Telechargements"))
    propositions.fermer()
    yield r, ouverts, montres
    propositions.fermer()


def test_ix3_ouvrir_par_le_nom(pc):
    r, ouverts, _ = pc
    rep = _chat("ouvre mon CV")
    assert ouverts == [str(r / "Documents" / "CV_Alexis_2026.docx")], rep
    assert "cv_alexis_2026.docx" in rep["message"].lower()


def test_ix3_plusieurs_correspondances_atlas_demande_lequel(pc):
    r, ouverts, _ = pc
    rep = _chat("ouvre le rapport")
    assert ouverts == [], "jamais le premier au hasard"
    m = rep["message"]
    assert "lequel" in m.lower() and "Rapport de stage.docx" in m and "Rapport annuel.pdf" in m, m
    _chat("le 2")
    assert len(ouverts) == 1 and ouverts[0].endswith(("Rapport de stage.docx", "Rapport annuel.pdf"))


def test_ix3_aucune_correspondance_le_dit_avec_une_suggestion(pc):
    _, ouverts, _ = pc
    rep = _chat("ouvre mon raport de stag")
    assert ouverts == [] or ouverts[0].endswith("Rapport de stage.docx")     # nom approché : ouvert, ou proposé
    rep = _chat("ouvre ma déclaration d'impôts")
    assert ouverts in ([], [ouverts[0]]) and "aucun fichier" in rep["message"].lower(), rep["message"]


def test_ix3_dire_ou_sans_ouvrir_puis_ouvrir_le_dossier(pc):
    r, ouverts, montres = pc
    rep = _chat("où est mon rapport de stage ?")
    assert ouverts == [] and str(r / "Documents" / "Stage") in rep["message"], rep["message"]
    _chat("ouvre le dossier")
    assert montres == [str(r / "Documents" / "Stage" / "Rapport de stage.docx")]


def test_ix3_le_dernier_pdf_telecharge(pc):
    r, ouverts, _ = pc
    rep = _chat("ouvre le dernier PDF téléchargé")
    assert ouverts == [str(r / "Telechargements" / "facture_edf.pdf")], rep["message"]


def test_ix3_mes_fichiers_d_hier(pc):
    _, ouverts, _ = pc
    rep = _chat("mes fichiers d'hier")
    assert "notes.md" in rep["message"] and "CV_Alexis" not in rep["message"], rep["message"]
    assert ouverts == []


def test_ix3_recherche_dans_le_contenu_avec_extrait(pc):
    _, ouverts, _ = pc
    rep = _chat("le document où je parle de budget")
    m = rep["message"]
    assert "Rapport de stage.docx" in m and "«budget»" in m.lower(), m
    assert ouverts == []


def test_ix3_un_executable_n_est_jamais_ouvert_sans_confirmation_montrant_le_chemin(pc):
    r, ouverts, _ = pc
    for phrase, nom in (("ouvre le fichier setup outil", "setup_outil.exe"), ("ouvre le fichier installe moi", "installe_moi.bat")):
        rep = _chat(phrase)
        assert ouverts == [], f"{nom} ouvert sans confirmation"
        assert rep["type"] == "confirmation_required", rep
        assert str(r / "Telechargements" / nom) in (rep.get("target") or ""), rep
    from api.models import ConfirmationResponse
    from api.routes import confirm_endpoint

    asyncio.run(confirm_endpoint(ConfirmationResponse(confirmation_id=rep["confirmation_id"], accepted=True)))
    assert ouverts == [str(r / "Telechargements" / "installe_moi.bat")]


def test_ix3_un_raccourci_vers_un_programme_est_un_programme(pc, monkeypatch):
    import tools.fichiers as tf

    r, ouverts, _ = pc
    lnk = r / "Documents" / "Lanceur.lnk"
    lnk.write_bytes(b"L")
    monkeypatch.setattr(tf, "cible_du_raccourci", lambda p: r"C:\Outils\script.ps1" if p.endswith("Lanceur.lnk") else None)
    import core.file_indexer as fi
    fi.FileIndexer.passage(pc_indexeur(r))
    rep = _chat("ouvre le fichier lanceur")
    assert rep["type"] == "confirmation_required" and r"C:\Outils\script.ps1" in (rep.get("target") or ""), rep
    assert ouverts == []


def pc_indexeur(r):
    import core.file_indexer as fi

    idx = fi.FileIndexer()
    idx._cfg = {**fi.charger_config(), "scan_roots": [str(r)], "exclude_dirs": [], "cpu_max_pourcent": 100}
    return idx


def test_ix3_ou_en_est_l_index_et_l_oubli_confirme(pc):
    rep = _chat("où en est l'index ?")
    assert "fichiers" in rep["message"].lower(), rep["message"]
    rep = _chat("oublie l'index de mes fichiers")
    assert rep["type"] == "confirmation_required", rep


def test_ix3_index_indisponible_atlas_le_dit(pc, monkeypatch):
    import core.file_indexer as fi
    from core_conversational.degradations import actives

    def casse(*a, **k):
        raise fi.sqlite3.OperationalError("database is locked")

    with monkeypatch.context() as m:              # rendu avant le nettoyage de la fixture
        m.setattr(fi, "connexion", casse)
        rep = _chat("ouvre mon CV")
    assert "index" in rep["message"].lower(), rep["message"]
    assert "file_indexer" in [b["cle"] for b in actives()]


@pytest.mark.parametrize("phrase", ["ouvre Discord", "ouvre le menu", "ouvre les paramètres", "ouvre la calculatrice",
                                    "ouvre le bloc-notes", "où est la tour Eiffel ?", "cherche sur internet la météo"])
def test_ix3_negatifs_ce_ne_sont_pas_des_fichiers(phrase):
    from core.intent_classifier import get_classifier

    i = get_classifier().classify(phrase, {})
    assert i.category != "fichiers", (phrase, i.category, i.verb)


# --------------------------------------------------------------------------- #
#  IX4.3 — premier plan sur la fenêtre EXACTE (hwnd résolu), jamais « le titre contient »
# --------------------------------------------------------------------------- #

def test_ix4_premier_plan_vise_le_hwnd_resolu_pas_un_homonyme(monkeypatch):
    """Rejeu réel du 15/10 : « AtlasEssaiPyw » ramenait « AtlasEssaiPyw outils » (pygetwindow)."""
    from types import SimpleNamespace

    import tools.window_controller as wc

    fenetres = [{"hwnd": 222, "title": "AtlasEssaiPyw outils", "process": "python.exe"},
                {"hwnd": 111, "title": "AtlasEssaiPyw", "process": "python.exe"}]
    actives = []

    class Fen:
        def __init__(self, hwnd):
            self._hWnd, self.isMinimized = hwnd, False
            self.title = next(f["title"] for f in fenetres if f["hwnd"] == hwnd)

        def activate(self):
            actives.append(self._hWnd)

    monkeypatch.setattr(wc, "_list_visible_windows", lambda: fenetres)
    monkeypatch.setattr(wc, "HAS_PYWINAUTO", False)
    monkeypatch.setattr(wc, "HAS_WIN32", False)
    monkeypatch.setattr(wc.gw, "getWindowsWithTitle", lambda t: [Fen(222), Fen(111)])   # l'ancien piège
    monkeypatch.setattr(wc.gw, "Win32Window", Fen, raising=False)
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    r = wc._controller.focus_window("AtlasEssaiPyw")
    assert r["success"] and actives == [111], (r, actives)


def test_ix4_sans_fenetre_resolue_aucune_recherche_par_morceau_de_titre(monkeypatch):
    from types import SimpleNamespace

    import tools.window_controller as wc

    appels = []
    monkeypatch.setattr(wc, "_list_visible_windows", lambda: [])
    monkeypatch.setattr(wc.gw, "getWindowsWithTitle", lambda t: appels.append(t) or [])
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    r = wc._controller.focus_window("Notepad")
    assert r["success"] is False and appels == [], appels


def test_ix4_fenetre_fermee_le_titre_est_rendu(monkeypatch):
    """Rejeu réel du 15/10 : « Fenêtre '' fermée. » — le titre était lu APRÈS la fermeture."""
    from types import SimpleNamespace

    import tools.window_controller as wc

    class Fen:
        title = "AtlasEssaiRefus"

        def close(self):
            self.title = ""                        # comme une vraie fenêtre fermée

    monkeypatch.setattr(wc.gw, "getWindowsWithTitle", lambda t: [Fen()])
    monkeypatch.setattr(wc, "time", SimpleNamespace(sleep=lambda s: None))
    r = wc.window_close("AtlasEssaiRefus")
    assert r["message"] == "Fenêtre 'AtlasEssaiRefus' fermée.", r


# --------------------------------------------------------------------------- #
#  IX4 bis — la pré-vérification sans Python garde les seuils de doctor.py --precheck
# --------------------------------------------------------------------------- #

def test_ix4bis_les_seuils_du_precheck_powershell_sont_ceux_de_doctor():
    import re

    sys.path.insert(0, str(ROOT / "scripts"))
    import doctor

    ps1 = (ROOT / "scripts" / "precheck_atlas.ps1").read_text(encoding="utf-8-sig")
    lus = {m.group(1): float(m.group(2)) for m in re.finditer(r"^\$(\w+)\s*=\s*([\d.]+)", ps1, re.M)}
    for nom in ("RAM_COMFORT_GIB", "RAM_MIN_GIB", "VRAM_COMFORT_MIB", "VRAM_TIGHT_MIB", "DISK_MIN_GIB"):
        assert lus[nom] == float(getattr(doctor, nom)), (nom, lus.get(nom), getattr(doctor, nom))


def test_ix4bis_le_bat_lance_le_ps1_sans_rien_installer():
    bat = (ROOT / "scripts" / "precheck_atlas.bat").read_text(encoding="utf-8", errors="replace").lower()
    assert "precheck_atlas.ps1" in bat and "-executionpolicy bypass" in bat
    ps1 = (ROOT / "scripts" / "precheck_atlas.ps1").read_text(encoding="utf-8-sig").lower()
    for interdit in ("install-module", "invoke-webrequest", "start-process", "set-itemproperty", "remove-item", "new-item"):
        assert interdit not in ps1, interdit


def test_ix2_un_passage_limite_a_un_dossier_retire_ses_disparus_et_rien_d_autre(arbre):
    import core.file_indexer as fi

    idx, r = arbre
    idx.passage()                                                     # tout le faux PC
    (r / "Telechargements" / "facture_edf.pdf").unlink()
    idx._cfg = {**idx._cfg, "scan_roots": [str(r / "Telechargements")]}
    idx.passage()                                                     # seulement Téléchargements
    assert not fi.chercher_nom("facture edf")
    assert fi.chercher_nom("cv"), "les fichiers des autres dossiers restent"
