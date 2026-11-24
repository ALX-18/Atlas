"""
Brief Installeur — fin, IF7 : plusieurs comptes Windows sur un même PC (Réunion n° 3, conclusion du 24/11).

`127.0.0.1` est commun à toutes les sessions ouvertes d'un PC. Avant : le lanceur, la fenêtre, le serveur et
l'installeur se branchaient sur n'importe quel Atlas (8550) ou Ollama (11434) qui écoutait, et l'API n'avait
aucune clé. Désormais :
- le propriétaire de ce qui écoute est vérifié à chaque point de connexion ; illisible compte comme « pas à moi » ;
- une clé locale par installation, que seule la fenêtre native porte ; l'interface web est coupée ;
- le pont navigateur lit son réglage, refuse toute origine web, et le paquet testeur le force fermé ;
- « Quitter » est un arrêt ordonné, qui arrête l'Ollama lancé par Atlas, et lui seul ;
- l'installeur ne touche qu'aux processus du compte courant, et refuse avant tout téléchargement.

Règle : « un garde-fou se teste avec des commandes simulées ». Les écouteurs, les comptes et les processus sont
SIMULÉS ; aucun test n'arrête un vrai Ollama, n'ouvre un vrai Atlas ni ne touche `data/` d'Alexis.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
from types import SimpleNamespace

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

MOI = "PC-TEST\\personne_a"
AUTRE = "PC-TEST\\personne_b"


def _ecoute(port, pid, ip="127.0.0.1", status="LISTEN"):
    return SimpleNamespace(status=status, laddr=SimpleNamespace(ip=ip, port=port), pid=pid)


class _Comptes:
    """Qui possède quel processus. `None` : propriétaire illisible (refus d'accès de Windows)."""

    def __init__(self, **par_pid):
        self.par_pid = {int(k[1:]): v for k, v in par_pid.items()}

    def __call__(self, pid):
        return self.par_pid.get(pid)


# --------------------------------------------------------------------------- #
#  Le propriétaire de ce qui écoute
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("connexions,comptes,attendu", [
    ([], {}, "libre"),
    ([_ecoute(11434, 10)], {"p10": MOI}, "a_moi"),
    ([_ecoute(11434, 10)], {"p10": AUTRE}, "autre"),
    ([_ecoute(11434, 10)], {"p10": None}, "illisible"),
    ([_ecoute(11434, None)], {}, "illisible"),
    ([_ecoute(11434, 10, status="ESTABLISHED")], {"p10": AUTRE}, "libre"),
    ([_ecoute(8550, 10)], {"p10": AUTRE}, "libre"),
    ([_ecoute(11434, 10, ip="0.0.0.0")], {"p10": AUTRE}, "autre"),
    # 127.0.0.1 exact l'emporte sur 0.0.0.0 : c'est lui qui reçoit la connexion
    ([_ecoute(11434, 10, ip="0.0.0.0"), _ecoute(11434, 11)], {"p10": AUTRE, "p11": MOI}, "a_moi"),
    ([_ecoute(11434, 10, ip="0.0.0.0"), _ecoute(11434, 11)], {"p10": MOI, "p11": AUTRE}, "autre"),
])
def test_if7_le_proprietaire_de_ce_qui_ecoute(connexions, comptes, attendu):
    from core import proprietaire as pr

    v = pr.verifier(11434, connexions=connexions, compte_de=_Comptes(**comptes), moi=MOI)
    assert v.etat == attendu, v


def test_if7_le_compte_se_compare_sans_tenir_compte_des_majuscules():
    from core import proprietaire as pr

    v = pr.verifier(11434, connexions=[_ecoute(11434, 10)], compte_de=_Comptes(p10="pc-test\\PERSONNE_A"), moi=MOI)
    assert v.etat == "a_moi"


def test_if7_un_compte_illisible_vient_d_un_refus_d_acces_de_windows():
    """Le vrai lecteur : psutil lève AccessDenied pour le processus d'un autre compte, sans droits
    d'administrateur. Ça doit donner None (illisible), jamais une exception."""
    from core import proprietaire as pr

    class Refus:
        def __init__(self, pid):
            import psutil
            raise psutil.AccessDenied(pid)

    assert pr.compte_du_processus(10, process=Refus) is None


def test_if7_la_garde_revérifie_quand_le_processus_qui_ecoute_change():
    from core import proprietaire as pr

    etat = {"connexions": [_ecoute(11434, 10)], "lectures": 0}
    comptes = _Comptes(p10=MOI, p20=AUTRE)

    def compte_de(pid):
        etat["lectures"] += 1
        return comptes(pid)

    g = pr.Garde(11434, "Ollama", connexions=lambda: etat["connexions"], compte_de=compte_de, moi=MOI,
                 debut=lambda pid: 1000.0)
    g.verifier()
    g.verifier()
    assert etat["lectures"] == 1, "même processus : pas de nouvelle lecture du compte"
    etat["connexions"] = [_ecoute(11434, 20)]
    with pytest.raises(pr.AutreCompte) as e:
        g.verifier()
    assert e.value.composant == "Ollama" and e.value.verdict.etat == "autre"


def test_if7_la_garde_revérifie_un_pid_reutilise():
    """Même numéro de processus, mais démarré à un autre moment : c'est un autre processus."""
    from core import proprietaire as pr

    debuts = {"t": 1000.0}
    comptes = {"c": MOI}
    g = pr.Garde(11434, "Ollama", connexions=lambda: [_ecoute(11434, 10)], compte_de=lambda pid: comptes["c"],
                 moi=MOI, debut=lambda pid: debuts["t"])
    g.verifier()
    comptes["c"], debuts["t"] = AUTRE, 2000.0
    with pytest.raises(pr.AutreCompte):
        g.verifier()


def test_if7_la_garde_laisse_passer_un_port_libre():
    """Rien n'écoute : la connexion échouera d'elle-même, avec le message habituel (« Ollama ne répond pas »)."""
    from core import proprietaire as pr

    g = pr.Garde(11434, "Ollama", connexions=lambda: [], compte_de=lambda pid: None, moi=MOI, debut=lambda p: 0.0)
    g.verifier()


@pytest.mark.parametrize("composant", ["Atlas", "Ollama"])
@pytest.mark.parametrize("etat", ["autre", "illisible"])
def test_if7_le_message_de_refus_nomme_le_composant_et_donne_une_vraie_sortie(composant, etat):
    from core import proprietaire as pr

    m = pr.message_refus(composant, pr.Verdict(etat, pid=10))
    assert composant in m
    assert "Se déconnecter" in m and "Changer d'utilisateur" in m and "ne suffit pas" in m
    assert "redémarrez" in m.lower()
    if etat == "illisible":
        assert "n'a pas pu vérifier à qui appartient" in m, m
        assert "autre compte" not in m.split("\n\n")[0], "il n'a pas été vérifié que c'est un autre compte"
    else:
        assert "autre session Windows" in m
    assert "personne_b" not in m


def test_if7_le_message_ne_nomme_l_autre_compte_que_s_il_a_ete_lu():
    from core import proprietaire as pr

    assert "« personne_b »" in pr.message_refus("Ollama", pr.Verdict("autre", pid=10, compte=AUTRE))
    assert "«" not in pr.message_refus("Ollama", pr.Verdict("autre", pid=10)).split("\n\n")[0]


def test_if7_rien_n_a_ete_envoye_n_est_dit_que_si_c_est_vrai():
    from core import proprietaire as pr

    v = pr.Verdict("autre", pid=10)
    assert "rien n'a été envoyé" in pr.message_refus("Atlas", v)
    assert "rien n'a été envoyé" not in pr.message_refus("Atlas", v, rien_envoye=False)


# --------------------------------------------------------------------------- #
#  Le lanceur
# --------------------------------------------------------------------------- #

def _lancer(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT / "installeur"))
    import lancer

    monkeypatch.setattr(lancer, "JOURNAL", tmp_path / "atlas_serveur.log")
    monkeypatch.setattr(lancer, "REFUS_DEMARRAGE", tmp_path / "refus_demarrage.json")
    monkeypatch.setattr(lancer, "OLLAMA_LANCE", tmp_path / "ollama_lance.json")
    monkeypatch.setattr(lancer.time, "sleep", lambda s: None)
    ouverts = {"serveur": 0, "fenetre": 0}
    monkeypatch.setattr(lancer, "demarrer_serveur", lambda: ouverts.__setitem__("serveur", ouverts["serveur"] + 1))
    monkeypatch.setattr(lancer, "ouvrir_fenetre", lambda: ouverts.__setitem__("fenetre", ouverts["fenetre"] + 1))
    return lancer, ouverts


class _UiRefus:
    def __init__(self, reponses=()):
        self.reponses, self.refus, self.infos = list(reponses), [], []

    def refuser(self, texte):
        self.refus.append(texte)
        return self.reponses.pop(0) if self.reponses else False

    def informer(self, texte):
        self.infos.append(texte)


@pytest.mark.parametrize("etat", ["autre", "illisible"])
def test_if7_le_lanceur_refuse_l_ollama_d_un_autre_compte(monkeypatch, tmp_path, etat):
    lancer, ouverts = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    lances = []
    monkeypatch.setattr(lancer, "verdict_ollama", lambda: pr.Verdict(etat, pid=10))
    monkeypatch.setattr(lancer, "verdict_atlas", lambda: pr.Verdict("libre"))
    monkeypatch.setattr(lancer, "ollama_installe", lambda: tmp_path / "ollama.exe")
    monkeypatch.setattr(lancer, "demarrer_ollama_sans_fenetre", lambda *a, **k: lances.append(a))
    ui = _UiRefus()
    assert lancer.main([], ui=ui) != 0
    assert lances == [], "aucun second Ollama"
    assert ouverts == {"serveur": 0, "fenetre": 0}, "ni serveur ni fenêtre : rien n'est envoyé à l'Ollama de l'autre"
    assert len(ui.refus) == 1 and "Ollama" in ui.refus[0]
    assert "refus" in (tmp_path / "atlas_serveur.log").read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("etat", ["autre", "illisible"])
def test_if7_le_lanceur_refuse_l_atlas_d_un_autre_compte_avant_d_ouvrir_la_fenetre(monkeypatch, tmp_path, etat):
    lancer, ouverts = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    monkeypatch.setattr(lancer, "verdict_ollama", lambda: pr.Verdict("a_moi", pid=5))
    monkeypatch.setattr(lancer, "verdict_atlas", lambda: pr.Verdict(etat, pid=10))
    ui = _UiRefus()
    assert lancer.main([], ui=ui) != 0
    assert ouverts == {"serveur": 0, "fenetre": 0}
    assert len(ui.refus) == 1 and "Atlas" in ui.refus[0] and "Ollama" not in ui.refus[0].split("\n\n")[0]


def test_if7_reessayer_reverifie_puis_ouvre_quand_l_autre_s_est_deconnecte(monkeypatch, tmp_path):
    lancer, ouverts = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    verdicts = [pr.Verdict("autre", pid=10), pr.Verdict("libre"), pr.Verdict("a_moi", pid=30)]
    monkeypatch.setattr(lancer, "verdict_ollama", lambda: pr.Verdict("a_moi", pid=5))
    monkeypatch.setattr(lancer, "verdict_atlas", lambda: verdicts.pop(0) if len(verdicts) > 1 else verdicts[0])
    ui = _UiRefus(reponses=[True])
    assert lancer.main([], ui=ui) == 0
    assert len(ui.refus) == 1
    assert ouverts == {"serveur": 1, "fenetre": 1}


def test_if7_si_le_serveur_ne_demarre_pas_le_lanceur_ne_prend_pas_celui_d_un_autre(monkeypatch, tmp_path):
    """Tour 2, sécurité : le serveur de B refuse de démarrer ; pendant l'attente, A prend 8550. La boucle
    d'attente ne doit pas prendre le serveur de A pour celui de B."""
    lancer, ouverts = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    verdicts = [pr.Verdict("libre"), pr.Verdict("libre"), pr.Verdict("autre", pid=10)]
    monkeypatch.setattr(lancer, "verdict_ollama", lambda: pr.Verdict("a_moi", pid=5))
    monkeypatch.setattr(lancer, "verdict_atlas", lambda: verdicts.pop(0) if len(verdicts) > 1 else verdicts[0])
    ui = _UiRefus()
    assert lancer.main([], ui=ui) != 0
    assert ouverts["fenetre"] == 0 and len(ui.refus) == 1


def test_if7_au_demarrage_avec_windows_le_refus_est_note_puis_dit_a_la_premiere_ouverture(monkeypatch, tmp_path):
    lancer, ouverts = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    ollama = {"v": pr.Verdict("autre", pid=10)}
    monkeypatch.setattr(lancer, "verdict_ollama", lambda: ollama["v"])
    monkeypatch.setattr(lancer, "verdict_atlas", lambda: pr.Verdict("a_moi", pid=30))
    ui = _UiRefus()
    assert lancer.main(["--sans-fenetre"], ui=ui) != 0
    assert ui.refus == [] and ui.infos == [], "au démarrage avec Windows, rien ne s'affiche (pythonw)…"
    assert (tmp_path / "refus_demarrage.json").exists(), "… mais le refus est noté"
    assert "refus" in (tmp_path / "atlas_serveur.log").read_text(encoding="utf-8").lower()
    ollama["v"] = pr.Verdict("a_moi", pid=5)
    assert lancer.main([], ui=ui) == 0
    assert len(ui.infos) == 1 and "démarrage" in ui.infos[0] and "Ollama" in ui.infos[0], ui.infos
    assert not (tmp_path / "refus_demarrage.json").exists(), "dit une fois"
    assert ouverts["fenetre"] == 1


def test_if7_le_lanceur_note_l_ollama_qu_il_lance(monkeypatch, tmp_path):
    lancer, _ = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    monkeypatch.setattr(lancer, "verdict_ollama", lambda: pr.Verdict("libre"))
    monkeypatch.setattr(lancer, "ollama_installe", lambda: tmp_path / "ollama.exe")
    monkeypatch.setattr(lancer, "demarrer_ollama_sans_fenetre", lambda exe, j: SimpleNamespace(pid=4242))
    monkeypatch.setattr(lancer, "debut_processus", lambda pid: 1234.5)
    assert lancer.assurer_ollama() == "lance"
    note = json.loads((tmp_path / "ollama_lance.json").read_text(encoding="utf-8"))
    assert note["pid"] == 4242 and note["debut"] == 1234.5 and note["par"] == "lanceur"


def test_if7_le_lanceur_ne_note_pas_un_ollama_deja_la(monkeypatch, tmp_path):
    lancer, _ = _lancer(monkeypatch, tmp_path)
    from core import proprietaire as pr

    monkeypatch.setattr(lancer, "verdict_ollama", lambda: pr.Verdict("a_moi", pid=5))
    assert lancer.assurer_ollama() == "tourne"
    assert not (tmp_path / "ollama_lance.json").exists()


# --------------------------------------------------------------------------- #
#  La clé locale
# --------------------------------------------------------------------------- #

def test_if7_la_cle_est_creee_une_fois_puis_relue_identique(tmp_path, monkeypatch):
    from core import cle_locale

    chemin = tmp_path / "cle_locale"
    monkeypatch.setattr(cle_locale, "_restreindre", lambda p: True)
    c1 = cle_locale.preparer(chemin)
    c2 = cle_locale.preparer(chemin)
    assert c1 == c2 and len(c1) >= 40, "stable par installation : un redémarrage ne la change pas"
    assert cle_locale.lire(chemin) == c1


def test_if7_la_cle_est_restreinte_au_compte_a_sa_creation(tmp_path, monkeypatch):
    from core import cle_locale

    appels = []
    monkeypatch.setattr(cle_locale, "_restreindre", lambda p: appels.append(p) or True)
    cle_locale.preparer(tmp_path / "cle_locale")
    assert appels == [tmp_path / "cle_locale"]


def test_if7_la_commande_qui_restreint_la_cle_ne_garde_que_le_compte(tmp_path, monkeypatch):
    from core import cle_locale

    commandes = []
    monkeypatch.setattr(cle_locale.subprocess, "run",
                        lambda cmd, **k: commandes.append(cmd) or SimpleNamespace(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(cle_locale, "_compte", lambda: MOI)
    assert cle_locale._restreindre(tmp_path / "cle_locale")
    (cmd,) = commandes
    assert cmd[0].lower() == "icacls" and "/inheritance:r" in cmd and f"{MOI}:(F)" in cmd


@pytest.mark.parametrize("contenu", [None, "", "  \n", "trop-court"])
def test_if7_une_cle_absente_ou_abimee_dit_comment_reparer(tmp_path, contenu):
    from core import cle_locale

    chemin = tmp_path / "cle_locale"
    if contenu is not None:
        chemin.write_text(contenu, encoding="utf-8")
    with pytest.raises(cle_locale.CleIntrouvable) as e:
        cle_locale.lire(chemin)
    m = str(e.value)
    assert "Quitter" in m and "relancez" in m.lower(), m


def test_if7_un_atlas_d_essai_ne_cree_pas_la_cle_dans_les_vraies_donnees(tmp_path, monkeypatch):
    from core import cle_locale, donnees_reelles as dr

    faux = tmp_path / "data"
    faux.mkdir()
    monkeypatch.setattr(dr, "DOSSIER", faux)
    monkeypatch.delenv(dr.VARIABLE, raising=False)
    with pytest.raises(dr.DonneesReellesInterdites):
        cle_locale.preparer(faux / "cle_locale")
    assert not (faux / "cle_locale").exists()


def test_if7_le_chemin_de_la_cle_se_redirige_pour_les_essais(tmp_path, monkeypatch):
    from core import cle_locale

    monkeypatch.setenv("ATLAS_CLE_LOCALE", str(tmp_path / "k"))
    assert cle_locale.chemin() == tmp_path / "k"
    monkeypatch.delenv("ATLAS_CLE_LOCALE")
    assert cle_locale.chemin() == ROOT / "data" / "cle_locale"


def test_if7_la_suite_de_tests_n_utilise_jamais_la_vraie_cle():
    from core import cle_locale

    assert cle_locale.chemin() != ROOT / "data" / "cle_locale"


@pytest.fixture
def client_sans_cle():
    from fastapi.testclient import TestClient

    import main

    return TestClient(main.app, base_url="http://127.0.0.1:8550")


@pytest.mark.parametrize("chemin", ["/api/health", "/api/memory/recall?q=cabane", "/api/confirmations",
                                    "/api/annonces", "/health"])
def test_if7_sans_la_cle_l_api_refuse_et_ne_lit_rien(client_sans_cle, chemin):
    r = client_sans_cle.get(chemin)
    assert r.status_code == 401, (chemin, r.status_code, r.text[:200])
    assert "clé" in r.json()["detail"]


def test_if7_une_mauvaise_cle_est_refusee(client_sans_cle):
    from core import cle_locale

    r = client_sans_cle.get("/api/confirmations", headers={cle_locale.ENTETE: "x" * 43})
    assert r.status_code == 401


def test_if7_une_action_sans_cle_n_est_ni_confirmee_ni_executee(client_sans_cle, monkeypatch):
    from core import confirmation

    vus = []
    monkeypatch.setattr(confirmation, "resolve_pending", lambda *a, **k: vus.append(a) or {"status": "success"})
    r = client_sans_cle.post("/api/confirm", json={"confirmation_id": "abc", "accepted": True})
    assert r.status_code == 401 and vus == []
    r = client_sans_cle.post("/api/memory/ingest", json={"text": "la clé de la cabane"})
    assert r.status_code == 401


def test_if7_avec_la_cle_l_api_repond(client_sans_cle):
    from core import cle_locale

    r = client_sans_cle.get("/api/confirmations", headers=cle_locale.entetes())
    assert r.status_code == 200, r.text[:200]


def test_if7_l_interface_web_est_coupee_et_le_dit(client_sans_cle):
    """Décision d'Alexis (24/11) : coupée partout, « Ouvrir » mène à la fenêtre native."""
    r = client_sans_cle.get("/", headers={"Sec-Fetch-Site": "none"})
    assert r.status_code == 200
    assert "fenêtre" in r.text and "app.js" not in r.text
    from core import cle_locale

    assert client_sans_cle.get("/static/app.js", headers=cle_locale.entetes()).status_code == 404, \
        "même avec la clé, l'interface web n'est plus servie"


def test_if7_ouvrir_mene_a_la_fenetre_native():
    """« Ouvrir » de l'icône près de l'horloge : plus de navigateur (main.py l.469 au 24/11)."""
    code = (ROOT / "main.py").read_text(encoding="utf-8")
    corps = code.split("def _on_open_ui", 1)[1].split("\n        def ", 1)[0]
    assert "webbrowser" not in corps and "ouvrir_fenetre_native" in corps


def test_if7_la_fenetre_native_s_ouvre_sans_console(monkeypatch, tmp_path):
    import main

    lances = []
    monkeypatch.setattr(main.subprocess, "Popen", lambda cmd, **k: lances.append((cmd, k)))
    main.ouvrir_fenetre_native()
    (cmd, k), = lances
    assert cmd[0].lower().endswith("pythonw.exe") or cmd[0] == sys.executable
    assert cmd[-1].endswith(os.path.join("desktop", "atlas_desktop.py"))


# --------------------------------------------------------------------------- #
#  La fenêtre native : vérifier le serveur avant d'envoyer la clé
# --------------------------------------------------------------------------- #

def _connexion(monkeypatch, verdicts, cles=None, reponses=None):
    import httpx

    from core import proprietaire as pr
    from desktop import connexion as cx

    envoyes = []
    rep = list(reponses or [])

    def gerer(requete):
        envoyes.append(requete)
        statut, corps = rep.pop(0) if rep else (200, {"ok": True})
        return httpx.Response(statut, json=corps)

    lectures = list(cles or ["c" * 43])
    c = cx.ConnexionAtlas("http://127.0.0.1:8550", 8550,
                          verifier=lambda: verdicts.pop(0) if len(verdicts) > 1 else verdicts[0],
                          lire_cle=lambda: lectures.pop(0) if len(lectures) > 1 else lectures[0],
                          transport=httpx.MockTransport(gerer))
    return c, envoyes, pr, cx


def test_if7_la_fenetre_n_envoie_rien_a_un_atlas_d_un_autre_compte(monkeypatch):
    from core import proprietaire as pr

    c, envoyes, pr, cx = _connexion(monkeypatch, [pr.Verdict("autre", pid=10)])
    with pytest.raises(cx.ServeurRefuse) as e:
        c.get("/api/confirmations")
    assert envoyes == [], "ni la clé ni la demande ne partent"
    assert "Atlas" in str(e.value)


def test_if7_un_serveur_etranger_sur_8550_pendant_que_la_fenetre_interroge_coupe_la_connexion(monkeypatch):
    from core import proprietaire as pr

    c, envoyes, pr, cx = _connexion(monkeypatch, [pr.Verdict("a_moi", pid=30), pr.Verdict("autre", pid=40)])
    c.get("/api/voice/state")
    assert len(envoyes) == 1
    with pytest.raises(cx.ServeurRefuse):
        c.get("/api/confirmations")
    with pytest.raises(cx.ServeurRefuse):
        c.get("/api/annonces")
    assert len(envoyes) == 1, "coupée : plus rien ne part, même quand le serveur redevient le sien"
    assert c.coupee


def test_if7_la_fenetre_porte_la_cle(monkeypatch):
    from core import cle_locale, proprietaire as pr

    c, envoyes, pr, cx = _connexion(monkeypatch, [pr.Verdict("a_moi", pid=30)], cles=["k" * 43])
    c.get("/api/health")
    assert envoyes[0].headers[cle_locale.ENTETE] == "k" * 43


def test_if7_apres_un_changement_de_cle_la_fenetre_la_relit_sans_rejouer_d_action(monkeypatch):
    from core import proprietaire as pr

    c, envoyes, pr, cx = _connexion(monkeypatch, [pr.Verdict("a_moi", pid=30)], cles=["a" * 43, "b" * 43],
                                    reponses=[(401, {"detail": "clé"}), (200, {"ok": 1}), (401, {"detail": "clé"})])
    r = c.get("/api/voice/state")                  # lecture : relue, puis redemandée une fois
    assert r.status_code == 200 and len(envoyes) == 2
    with pytest.raises(cx.CleChangee) as e:
        c.post("/api/confirm", json={"confirmation_id": "x", "accepted": True})
    assert len(envoyes) == 3, "l'action n'est pas renvoyée"
    assert "rien n'a été fait" in str(e.value)


def test_if7_une_cle_introuvable_dans_la_fenetre_dit_comment_reparer(monkeypatch):
    import httpx

    from core import cle_locale, proprietaire as pr
    from desktop import connexion as cx

    def absente():
        raise cle_locale.CleIntrouvable(cle_locale.message_cle_introuvable(pathlib.Path("data/cle_locale")))

    c = cx.ConnexionAtlas("http://127.0.0.1:8550", 8550, verifier=lambda: pr.Verdict("a_moi", pid=3),
                          lire_cle=absente, transport=httpx.MockTransport(lambda r: httpx.Response(200)))
    with pytest.raises(cle_locale.CleIntrouvable) as e:
        c.get("/api/health")
    assert "Quitter" in str(e.value)


def test_if7_toutes_les_demandes_de_la_fenetre_passent_par_la_connexion_verifiee():
    code = (ROOT / "desktop" / "atlas_desktop.py").read_text(encoding="utf-8")
    assert "httpx.Client(" not in code, "une demande directe enverrait la clé sans vérifier le serveur"
    assert "ConnexionAtlas" in code


# --------------------------------------------------------------------------- #
#  Le serveur : Ollama vérifié avant chaque échange
# --------------------------------------------------------------------------- #

_VISE_OLLAMA = re.compile(r"11434|BASE_URL\}/api/|base_url\}/api/|_OLLAMA_GENERATE_URL,")


def test_if7_tout_appel_du_serveur_a_ollama_passe_par_la_garde():
    """Comme CM0 pour data/ : chaque fichier du serveur qui parle à Ollama appelle la garde."""
    sans = []
    trouves = 0
    for d in ("core", "core_conversational", "tools", "api"):
        for f in sorted((ROOT / d).rglob("*.py")):
            code = "\n".join(l for l in f.read_text(encoding="utf-8").splitlines() if not l.strip().startswith("#"))
            if f.name in ("proprietaire.py",):
                continue
            if _VISE_OLLAMA.search(code):
                trouves += 1
                if "garde_ollama(" not in code:
                    sans.append(f.relative_to(ROOT).as_posix())
    assert trouves >= 7, "le recensement ne trouve plus rien : le motif est à revoir"
    assert not sans, f"appels à Ollama sans vérification du propriétaire : {sans}"


def test_if7_le_serveur_ne_parle_pas_a_l_ollama_d_un_autre_compte(monkeypatch):
    import asyncio

    import httpx

    from core import ollama_client as oc, proprietaire as pr

    envoyes = []
    monkeypatch.setattr(pr, "verifier", lambda port, **k: pr.Verdict("autre", pid=10))
    pr.reinitialiser_gardes()
    monkeypatch.setattr(httpx.AsyncClient, "send", lambda *a, **k: envoyes.append(a))

    async def go():
        return [t async for t in oc.chat_stream("bonjour", {}, [])]

    try:
        with pytest.raises(pr.AutreCompte):
            asyncio.run(go())
    finally:
        pr.reinitialiser_gardes()
    assert envoyes == []


def test_if7_le_refus_d_ollama_est_dit_tel_quel_dans_la_conversation(monkeypatch):
    from fastapi.testclient import TestClient

    import main
    from core import cle_locale, proprietaire as pr

    monkeypatch.setattr(pr, "verifier", lambda port, **k: pr.Verdict("illisible", pid=10)
                        if port == 11434 else pr.Verdict("a_moi", pid=1))
    pr.reinitialiser_gardes()
    try:
        r = TestClient(main.app, base_url="http://127.0.0.1:8550").post(
            "/api/chat", json={"message": "raconte-moi une histoire de pirates", "history": []},
            headers=cle_locale.entetes())
    finally:
        pr.reinitialiser_gardes()
    corps = r.json()
    texte = json.dumps(corps, ensure_ascii=False)
    assert "n'a pas pu vérifier à qui appartient" in texte and "Ollama" in texte, texte[:400]


# --------------------------------------------------------------------------- #
#  Le pont navigateur
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("origine,accepte", [
    ("chrome-extension://abcdefghijklmnop", True),
    (None, False),
    ("", False),
    ("http://127.0.0.1:8550", False),
    ("https://site-hostile.example", False),
    ("null", False),
    ("moz-extension://abc", False),
])
def test_if7_le_pont_n_accepte_que_l_extension(origine, accepte):
    from tools.browser_bridge import origine_acceptee

    assert origine_acceptee(origine) is accepte


def test_if7_le_pont_refuse_une_page_web_a_la_poignee_de_main():
    """Un vrai pont, sur un port libre, et deux vrais clients websockets."""
    import asyncio
    import socket

    import websockets

    from tools.browser_bridge import BrowserBridge

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    async def go():
        pont = BrowserBridge(port=port)
        await pont.start()
        try:
            with pytest.raises(websockets.exceptions.InvalidStatus):
                async with websockets.connect(f"ws://127.0.0.1:{port}", origin="https://site-hostile.example"):
                    pass
            with pytest.raises(websockets.exceptions.InvalidStatus):
                async with websockets.connect(f"ws://127.0.0.1:{port}"):
                    pass
            assert pont.connected_clients == 0
            async with websockets.connect(f"ws://127.0.0.1:{port}", origin="chrome-extension://abcdefghijklmnop"):
                await asyncio.sleep(0.1)
                assert pont.connected_clients == 1
        finally:
            await pont.stop()

    asyncio.run(go())


@pytest.mark.parametrize("reglage,paquet,attendu", [
    (True, None, True),
    (False, None, False),
    (True, {"browser_bridge_enabled": False}, False),       # mise à jour : l'ancien réglage était actif
    (None, None, True),
])
def test_if7_le_serveur_lit_le_reglage_du_pont(reglage, paquet, attendu):
    import main

    config = {"browser_bridge": {"port": 9999}} if reglage is None else {"browser_bridge": {"enabled": reglage}}
    assert main.pont_actif(config, paquet or {}) is attendu


def test_if7_le_demarrage_du_pont_depend_du_reglage():
    code = (ROOT / "main.py").read_text(encoding="utf-8")
    avant = code.split("await bridge.start()", 1)[0].rsplit("\n\n", 1)[-1]
    assert "pont_actif(" in avant, "bridge.start() est appelé sans lire le réglage (main.py l.511 au 24/11)"


def test_if7_le_paquet_testeur_force_le_pont_ferme_meme_apres_une_mise_a_jour(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "installeur"))
    import construire

    dest = tmp_path / "atlas"
    (dest / "config").mkdir(parents=True)
    (dest / "config" / "settings.json").write_text(json.dumps({"browser_bridge": {"port": 9999, "enabled": True}}),
                                                   encoding="utf-8")
    construire.regler_paquet(dest)
    assert json.loads((dest / "config" / "settings.json").read_text(encoding="utf-8"))["browser_bridge"]["enabled"] \
        is False
    paquet = json.loads((dest / "config" / "paquet.json").read_text(encoding="utf-8"))
    assert paquet["browser_bridge_enabled"] is False
    iss = (ROOT / "installeur" / "atlas.iss").read_text(encoding="utf-8")
    ligne = [l for l in iss.splitlines() if "paquet.json" in l or ("\\atlas\\*" in l and "Source" in l)]
    assert ligne and all("onlyifdoesntexist" not in l for l in ligne), "paquet.json est remplacé à chaque installation"


def test_if7_verifier_paquet_refuse_un_pont_ouvert(tmp_path):
    sys.path.insert(0, str(ROOT / "installeur"))
    import construire

    (tmp_path / "atlas" / "config").mkdir(parents=True)
    (tmp_path / "atlas" / "config" / "settings.json").write_text('{"browser_bridge": {"enabled": true}}',
                                                                 encoding="utf-8")
    fautes = construire.verifier_paquet(tmp_path)
    assert any("pont" in f for f in fautes), fautes
    assert any("paquet.json" in f for f in fautes), fautes


def test_if7_le_depot_garde_le_pont_d_alexis():
    assert not (ROOT / "config" / "paquet.json").exists(), "chez Alexis, le pont reste actif"


# --------------------------------------------------------------------------- #
#  « Quitter » : arrêt ordonné, et seul l'Ollama lancé par Atlas est arrêté
# --------------------------------------------------------------------------- #

def test_if7_quitter_ne_tue_plus_le_serveur_net():
    code = (ROOT / "main.py").read_text(encoding="utf-8")
    corps = code.split("def _on_quit_app", 1)[1].split("\n        systray = ", 1)[0]
    assert "os._exit" not in corps and "arret_ordonne(" in corps


def test_if7_l_arret_ordonne_demande_l_arret_et_arme_un_dernier_recours():
    from core import arret

    demandes, minuteurs, forces = [], [], []

    class Minuteur:
        def __init__(self, delai, fonction):
            self.delai, self.fonction, self.daemon = delai, fonction, False
            minuteurs.append(self)

        def start(self):
            pass

    arret.arret_ordonne(demander=lambda: demandes.append(True), minuteur=Minuteur, forcer=forces.append)
    assert demandes == [True] and forces == [], "rien n'est forcé tout de suite"
    (m,) = minuteurs
    assert m.daemon and 5 <= m.delai <= 60


def test_if7_le_dernier_recours_est_note_au_journal_et_arrete_quand_meme_l_ollama_d_atlas(caplog):
    import logging

    from core import arret

    faits = []
    with caplog.at_level(logging.WARNING):
        arret.arret_force(forcer=faits.append, arreter_ollama=lambda: faits.append("ollama"),
                          liberer=lambda: faits.append("verrou"))
    assert faits == ["ollama", "verrou", 0]
    assert any("dernier recours" in r.getMessage() for r in caplog.records)


def test_if7_l_arret_ordonne_passe_par_le_serveur_uvicorn():
    from core import arret

    serveur = SimpleNamespace(should_exit=False)
    arret.SERVEUR = serveur
    try:
        arret.demander_arret()
    finally:
        arret.SERVEUR = None
    assert serveur.should_exit is True


class _Proc:
    def __init__(self, pid, debut, compte, nom="ollama.exe", enfants=()):
        self.pid, self._debut, self._compte, self._nom, self._enfants = pid, debut, compte, nom, list(enfants)
        self.termine = False

    def create_time(self):
        return self._debut

    def username(self):
        return self._compte

    def name(self):
        return self._nom

    def children(self, recursive=False):
        return self._enfants

    def terminate(self):
        self.termine = True

    def kill(self):
        self.termine = True


def _note(tmp_path, pid=4242, debut=1234.5, par="lanceur"):
    f = tmp_path / "ollama_lance.json"
    f.write_text(json.dumps({"pid": pid, "debut": debut, "par": par}), encoding="utf-8")
    return f


def test_if7_atlas_arrete_l_ollama_qu_il_a_lance(tmp_path):
    from core import ollama_lance

    runner = _Proc(5000, 1300.0, MOI, "ollama.exe")
    p = _Proc(4242, 1234.5, MOI, enfants=[runner])
    f = _note(tmp_path)
    r = ollama_lance.arreter(f, process=lambda pid: p, moi=MOI, attendre=lambda procs, timeout: (procs, []))
    assert r == "arrete" and p.termine and runner.termine
    assert not f.exists()


@pytest.mark.parametrize("proc,raison", [
    (_Proc(4242, 9999.0, MOI), "pid réutilisé"),
    (_Proc(4242, 1234.5, AUTRE), "autre compte"),
    (_Proc(4242, 1234.5, MOI, "notepad.exe"), "pas Ollama"),
])
def test_if7_atlas_n_arrete_jamais_un_ollama_qu_il_n_a_pas_lance(tmp_path, proc, raison):
    from core import ollama_lance

    f = _note(tmp_path)
    r = ollama_lance.arreter(f, process=lambda pid: proc, moi=MOI, attendre=lambda procs, timeout: (procs, []))
    assert r == "pas_le_sien" and not proc.termine, raison
    assert not f.exists(), "la note périmée est retirée"


def test_if7_sans_note_atlas_n_arrete_aucun_ollama(tmp_path):
    from core import ollama_lance

    vus = []
    r = ollama_lance.arreter(tmp_path / "ollama_lance.json", process=lambda pid: vus.append(pid), moi=MOI)
    assert r == "aucun" and vus == []


def test_if7_l_arret_du_serveur_arrete_l_ollama_lance_seulement_pour_le_vrai_atlas():
    code = (ROOT / "main.py").read_text(encoding="utf-8")
    fin = code.split("    yield\n", 1)[1].split("def ", 1)[0]
    assert "ollama_lance.arreter" in fin and "autorise()" in fin, "un Atlas d'essai n'arrête aucun Ollama"


# --------------------------------------------------------------------------- #
#  L'installeur
# --------------------------------------------------------------------------- #

def _etapes(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT / "installeur"))
    import etapes

    monkeypatch.setattr(etapes, "CACHE", tmp_path / "cache")
    monkeypatch.setattr(etapes, "ETAT", tmp_path / "etat.json")
    monkeypatch.setattr(etapes, "JOURNAL", tmp_path / "installation.log")
    monkeypatch.setattr(etapes, "OLLAMA_LANCE", tmp_path / "ollama_lance.json")
    return etapes


class _P:
    def __init__(self, nom, compte):
        self.info = {"name": nom, "username": compte}
        self.tue = False

    def kill(self):
        self.tue = True


def test_if7_l_installeur_ne_voit_que_les_applications_ollama_du_compte(monkeypatch, tmp_path):
    e = _etapes(monkeypatch, tmp_path)
    procs = [_P("ollama app.exe", MOI), _P("ollama app.exe", AUTRE), _P("ollama app.exe", None), _P("x.exe", MOI)]
    monkeypatch.setattr(e, "_processus", lambda: procs)
    monkeypatch.setattr(e, "compte_courant", lambda: MOI)
    assert e.apps_ollama() == [procs[0]]


def test_if7_la_garde_de_l_installeur_ne_ferme_jamais_l_ollama_d_un_autre(monkeypatch, tmp_path):
    e = _etapes(monkeypatch, tmp_path)
    procs = [_P("ollama app.exe", AUTRE), _P("ollama app.exe", None)]
    monkeypatch.setattr(e, "_processus", lambda: procs)
    monkeypatch.setattr(e, "compte_courant", lambda: MOI)
    monkeypatch.setattr(e, "_api", lambda *a, **k: {"version": "0.40.6"})
    assert e.GardeAppOllama(tmp_path / "ollama.exe").balayer() == 0
    assert not any(p.tue for p in procs)


@pytest.mark.parametrize("port,etat,composant", [
    (11434, "autre", "Ollama"), (11434, "illisible", "Ollama"), (8550, "autre", "Atlas"),
])
def test_if7_l_installeur_refuse_avant_tout_telechargement(monkeypatch, tmp_path, port, etat, composant):
    e = _etapes(monkeypatch, tmp_path)
    from core import proprietaire as pr

    monkeypatch.setattr(e, "verdict_port", lambda p: pr.Verdict(etat, pid=10) if p == port else pr.Verdict("libre"))
    telecharges = []
    monkeypatch.setattr(e, "telecharger", lambda *a, **k: telecharges.append(a))
    monkeypatch.setattr(e, "etape_dependances", lambda *a, **k: telecharges.append("dependances"))
    ui = e.Texte()
    fins = []
    monkeypatch.setattr(ui, "fin", lambda ok, texte: fins.append((ok, texte)))
    assert e.Deroule("qwen2.5:7b", "carte", False, ui).lancer() != 0
    assert telecharges == []
    (ok, texte), = fins
    assert not ok and composant in texte and "Se déconnecter" in texte
    assert "relancez l'installation" in texte.lower()


def test_if7_l_installeur_verifie_ollama_juste_avant_de_lui_parler(monkeypatch, tmp_path):
    """Entre le diagnostic et le téléchargement du modèle, l'Ollama peut changer : chaque appel vérifie."""
    e = _etapes(monkeypatch, tmp_path)
    from core import proprietaire as pr

    monkeypatch.setattr(pr, "verifier", lambda port, **k: pr.Verdict("autre", pid=10))
    pr.reinitialiser_gardes()
    ouverts = []
    monkeypatch.setattr(e.urllib.request, "urlopen", lambda *a, **k: ouverts.append(a))
    try:
        with pytest.raises(pr.AutreCompte):
            e._api("/api/pull", {"model": "qwen2.5:7b"})
    finally:
        pr.reinitialiser_gardes()
    assert ouverts == []


def test_if7_attendre_ollama_ne_confond_pas_un_refus_avec_une_lenteur(monkeypatch, tmp_path):
    e = _etapes(monkeypatch, tmp_path)
    from core import proprietaire as pr

    def refuse(*a, **k):
        raise pr.AutreCompte("Ollama", pr.Verdict("autre", pid=10))

    monkeypatch.setattr(e, "_api", refuse)
    with pytest.raises(e.Echec) as x:
        e.attendre_ollama(secondes=60)
    assert "Ollama" in str(x.value) and "ne répond pas" not in str(x.value)


def test_if7_l_installeur_note_l_ollama_qu_il_lance(monkeypatch, tmp_path):
    e = _etapes(monkeypatch, tmp_path)
    import subprocess

    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: SimpleNamespace(pid=777))
    monkeypatch.setattr(e, "debut_processus", lambda pid: 55.5)
    e.demarrer_ollama_sans_fenetre(tmp_path / "ollama.exe", tmp_path / "ollama_serveur.log")
    note = json.loads((tmp_path / "ollama_lance.json").read_text(encoding="utf-8"))
    assert note == {**note, "pid": 777, "debut": 55.5, "par": "installeur"}


def _ps1(machine):
    import subprocess

    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                        str(ROOT / "scripts" / "precheck_atlas.ps1"), "-Simuler", json.dumps(machine)],
                       capture_output=True, text=True, encoding="utf-8", timeout=120)
    lignes = [l.split("=", 1) for l in r.stdout.splitlines() if "=" in l]
    return r.returncode, lignes


_MACHINE = {"windows": True, "windows_release": "11", "arch64": True, "disk_free_gib": 120.0, "ram_gib": 31.9,
            "gpu_name": "carte", "vram_mib": 8188}


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell de Windows")
@pytest.mark.parametrize("ports,refus", [
    ({"11434": "autre"}, "Ollama"),
    ({"11434": "illisible"}, "Ollama"),
    ({"8550": "autre"}, "Atlas"),
    ({"11434": "a_moi", "8550": "libre"}, None),
])
def test_if7_le_diagnostic_refuse_l_ollama_ou_l_atlas_d_un_autre_compte(ports, refus):
    code, lignes = _ps1({**_MACHINE, "ports": ports})
    d = dict((k, v) for k, v in lignes if k not in ("ko", "attention", "autre_compte"))
    autres = [v for k, v in lignes if k == "autre_compte"]
    if refus is None:
        assert d["verdict"] == "ok" and autres == [], lignes
        return
    assert d["verdict"] == "ko" and code == 2, lignes
    assert autres and refus in autres[0] and "Se d" in autres[0], autres


def test_if7_l_installeur_dit_le_refus_du_diagnostic_avec_son_propre_message():
    iss = (ROOT / "installeur" / "atlas.iss").read_text(encoding="utf-8")
    assert "'autre_compte'" in iss, "le refus « autre compte » n'est pas un « cette machine ne convient pas »"


def test_if7_le_vrai_diagnostic_lit_les_proprietaires_des_ports():
    ps1 = (ROOT / "scripts" / "precheck_atlas.ps1").read_text(encoding="utf-8-sig")
    assert "Get-NetTCPConnection" in ps1 and "GetOwner" in ps1
    for port in ("11434", "8550"):
        assert port in ps1


# --------------------------------------------------------------------------- #
#  doctor.py : plus d'exception avalée, et un 401 dit clairement
# --------------------------------------------------------------------------- #

def test_if7_doctor_dit_un_refus_de_cle_clairement(monkeypatch):
    import urllib.error

    from scripts import doctor

    monkeypatch.setattr(doctor, "_verdict_atlas", lambda port: SimpleNamespace(etat="a_moi"))

    def refuse(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", {}, None)

    monkeypatch.setattr(doctor.urllib.request, "urlopen", refuse)
    r = doctor._atlas_health()
    assert r["etat"] == "cle_refusee" and "clé" in r["detail"]
    checks = doctor.check_bascules()
    assert any(not c.ok and "clé" in (c.detail + c.name) for c in checks), [(c.name, c.detail) for c in checks]


def test_if7_doctor_dit_une_erreur_telle_quelle(monkeypatch):
    from scripts import doctor

    monkeypatch.setattr(doctor, "_verdict_atlas", lambda port: SimpleNamespace(etat="a_moi"))

    def casse(req, timeout=None):
        raise ValueError("réponse illisible")

    monkeypatch.setattr(doctor.urllib.request, "urlopen", casse)
    r = doctor._atlas_health()
    assert r["etat"] == "erreur" and "ValueError" in r["detail"] and "réponse illisible" in r["detail"]


def test_if7_doctor_n_envoie_pas_la_cle_a_l_atlas_d_un_autre_compte(monkeypatch):
    from scripts import doctor

    monkeypatch.setattr(doctor, "_verdict_atlas", lambda port: SimpleNamespace(etat="autre"))
    ouverts = []
    monkeypatch.setattr(doctor.urllib.request, "urlopen", lambda *a, **k: ouverts.append(a))
    r = doctor._atlas_health()
    assert r["etat"] == "autre_compte" and ouverts == []


# --------------------------------------------------------------------------- #
#  Les scripts d'essai qui parlent à un Atlas portent la clé de cet Atlas
# --------------------------------------------------------------------------- #

def test_if7_les_scripts_qui_appellent_l_api_d_atlas_portent_la_cle():
    vise = re.compile(r"127\.0\.0\.1:8550|localhost:8550|:\{PORT\}/api|API\s*=\s*f?[\"']http|\b(?:API|BASE) \+ ")
    sans = []
    for f in sorted((ROOT / "scripts").glob("*.py")) + sorted((ROOT / "tests").glob("*_mesure*.py")):
        code = f.read_text(encoding="utf-8", errors="replace")
        # ceux qui passent par req() et attendre() de checkup_dynamique portent la clé par eux
        if vise.search(code) and "cle_locale" not in code and "from checkup_dynamique import" not in code \
                and f.name != "doctor.py":
            sans.append(f.relative_to(ROOT).as_posix())
    assert not sans, f"scripts qui appellent l'API sans la clé : {sans}"


def test_if7_quitter_declenche_vraiment_le_nettoyage_d_un_vrai_serveur_uvicorn():
    """Un vrai uvicorn, sur un port libre, avec une petite application : demander_arret() fait tourner la fin du
    lifespan (là où main.py arrête l'Ollama d'Atlas et libère le verrou), puis le serveur s'arrête."""
    import socket
    import threading
    import time
    from contextlib import asynccontextmanager

    import uvicorn
    from fastapi import FastAPI

    from core import arret

    fait = []

    @asynccontextmanager
    async def cycle(app):
        fait.append("debut")
        yield
        fait.append("nettoyage")

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    serveur = uvicorn.Server(uvicorn.Config(FastAPI(lifespan=cycle), host="127.0.0.1", port=port, log_level="warning"))
    fil = threading.Thread(target=serveur.run, daemon=True)
    fil.start()
    for _ in range(100):
        if serveur.started:
            break
        time.sleep(0.05)
    assert serveur.started
    arret.SERVEUR = serveur
    try:
        arret.demander_arret()
        fil.join(timeout=10)
    finally:
        arret.SERVEUR = None
    assert not fil.is_alive(), "le serveur ne s'est pas arrêté"
    assert fait == ["debut", "nettoyage"]
