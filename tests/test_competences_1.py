"""
Sprint Compétences 1 — l'heure, les rappels, le son, la lumière, le Bluetooth, la musique.

Tout passe par la vraie route `/api/chat` (chat_endpoint). Le matériel est SIMULÉ : le vrai son,
les vrais écrans, le vrai Bluetooth et les vrais lecteurs sont interdits par tests/conftest.py
(MaterielInterdit). L'horloge est figée. Aucun appel au modèle n'est permis (`sans_modele`).

Le principe vérifié partout : agir, puis RELIRE, puis dire — le message porte l'état relu, jamais
la valeur demandée (les doubles arrondissent ou ignorent l'ordre pour le prouver).
"""

from __future__ import annotations

import asyncio
import pathlib
import re
import sys
import time
from datetime import datetime, timedelta

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

ALEXIS = "fenetre"
T0 = datetime(2026, 10, 18, 15, 7, 30)          # un dimanche


def _chat(message, origine=ALEXIS):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    return asyncio.run(chat_endpoint(ChatRequest(message=message, history=[], origine=origine)))


def _confirmer(r, accepte=True):
    from api.models import ConfirmationResponse
    from api.routes import confirm_endpoint

    assert r.get("type") == "confirmation_required", r
    return asyncio.run(confirm_endpoint(ConfirmationResponse(confirmation_id=r["confirmation_id"], accepted=accepte)))


def _msg(r) -> str:
    return r.get("message") or ""


@pytest.fixture(autouse=True)
def sans_modele(monkeypatch):
    """Invariant 3 : l'heure, les rappels et les réglages ne passent jamais par le modèle."""
    import api.routes as routes
    import core.ollama_client as oc

    def interdit(*a, **k):
        raise AssertionError("appel au modèle dans une compétence")

    for module in (routes, oc):
        for nom in ("chat_full", "chat_stream", "chat_stream_with_timeout"):
            if hasattr(module, nom):
                monkeypatch.setattr(module, nom, interdit)


@pytest.fixture
def horloge(monkeypatch):
    from core import horloge as h

    etat = {"t": T0}
    monkeypatch.setattr(h, "_horloge", lambda: etat["t"])
    return etat


@pytest.fixture
def propre():
    from core import annonces, apprentissage_store, propositions, rappels

    rappels.vider_pour_test()
    apprentissage_store.vider_pour_test()
    propositions.fermer()
    annonces.lire()
    yield
    rappels.vider_pour_test()
    apprentissage_store.vider_pour_test()
    propositions.fermer()
    annonces.lire()


# --------------------------------------------------------------------------- #
#  CP1 — l'heure et la date, par le moteur
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase,attendu", [
    ("quelle heure est-il ?", "Il est 15 h 07."),
    ("il est quelle heure", "Il est 15 h 07."),
    ("t'as l'heure ?", "Il est 15 h 07."),
    ("on est quel jour ?", "Nous sommes le dimanche 18 octobre 2026."),
    ("quelle est la date d'aujourd'hui ?", "Nous sommes le dimanche 18 octobre 2026."),
    ("quelle date dans 3 semaines ?", "Dans 3 semaines, nous serons le dimanche 8 novembre 2026."),
    ("quel jour serons-nous dans 10 jours ?", "Dans 10 jours, nous serons le mercredi 28 octobre 2026."),
    ("quelle date dans 2 mois ?", "Dans 2 mois, nous serons le vendredi 18 décembre 2026."),
    ("quel jour tombe le 25 décembre ?", "Le 25 décembre 2026 tombe un vendredi."),
    ("quel jour on sera demain ?", "Demain, nous serons le lundi 19 octobre 2026."),
])
def test_cp1_l_heure_et_la_date_viennent_de_l_horloge(horloge, phrase, attendu):
    assert _msg(_chat(phrase)) == attendu


def test_cp1_l_horloge_change_la_reponse_change(horloge):
    horloge["t"] = datetime(2027, 1, 1, 0, 0, 5)
    assert _msg(_chat("quelle heure est-il ?")) == "Il est minuit."
    assert _msg(_chat("on est quel jour ?")) == "Nous sommes le vendredi 1er janvier 2027."


def test_cp1_l_heure_dite_n_entre_pas_dans_la_memoire(horloge, monkeypatch):
    """« Il est 15 h 07 » rappelé plus tard ferait redonner une heure périmée (L4)."""
    import core.intent_engine as ie

    ecrits = []
    monkeypatch.setattr(ie, "get_memory_manager", lambda: type("M", (), {"save": lambda self, **k: ecrits.append(k)})())
    _chat("quelle heure est-il ?")
    assert not [e for e in ecrits if "heure_dire" in str(e)], ecrits


def test_cp1_l_heure_d_un_autre_pays_n_est_pas_inventee(horloge):
    m = _msg(_chat("quelle heure est-il à New York ?"))
    assert "15 h 07 ici" in m and "pas encore" in m, m


@pytest.mark.parametrize("phrase", ["à quelle heure ferme la poste ?", "c'est quoi l'heure d'été ?",
                                    "combien d'heures dans une semaine ?"])
def test_cp1_les_questions_qui_parlent_d_heure_ne_sont_pas_l_heure(phrase):
    from core.intent_classifier import get_classifier

    assert get_classifier().classify(phrase, {}).verb != "heure_dire"


# --------------------------------------------------------------------------- #
#  CP2 — minuteurs et rappels
# --------------------------------------------------------------------------- #

def _actifs():
    from core import rappels

    return rappels.actifs()


def test_cp2_minuteur_relu_puis_donne_a_l_heure(horloge, propre):
    from core import annonces, rappels

    m = _msg(_chat("mets un minuteur de 10 minutes pour les pâtes"))
    assert m == "Minuteur de 10 minutes lancé (les pâtes) : il sonnera à 15 h 17.", m
    horloge["t"] = T0 + timedelta(minutes=9)
    assert rappels.verifier() == []
    horloge["t"] = T0 + timedelta(minutes=10, seconds=1)
    assert rappels.verifier() == ["Minuteur terminé : les pâtes (10 minutes)."]
    assert [a["message"] for a in annonces.lire()] == ["Minuteur terminé : les pâtes (10 minutes)."]
    assert _actifs() == []


def test_cp2_pendant_l_annonce_le_minuteur_n_est_plus_en_cours(horloge, propre, monkeypatch):
    """Rejeu réel du 18/10 : pendant l'annonce vocale (quelques secondes), la liste montrait encore
    « minuteur : il reste 0 seconde ». L'état est changé AVANT l'annonce."""
    from core import rappels

    vus = []
    monkeypatch.setattr(rappels, "_publier", lambda msg, origine: vus.append(len(rappels.actifs())))
    _chat("mets un minuteur de 1 minute")
    horloge["t"] = T0 + timedelta(minutes=1, seconds=1)
    rappels.verifier()
    assert vus == [0], vus


@pytest.mark.parametrize("phrase,texte,quand", [
    ("rappelle-moi dans 20 minutes de sortir le linge", "sortir le linge", T0 + timedelta(minutes=20)),
    ("rappelle-moi de sortir le linge dans 20 minutes", "sortir le linge", T0 + timedelta(minutes=20)),
    ("rappelle-moi demain à 9 h d'appeler le médecin", "appeler le médecin", datetime(2026, 10, 19, 9, 0)),
    ("rappelle-moi d'appeler le médecin demain à 9h", "appeler le médecin", datetime(2026, 10, 19, 9, 0)),
    ("rappelle-moi à 18h30 de fermer les volets", "fermer les volets", datetime(2026, 10, 18, 18, 30)),
    ("rappelle-moi lundi à 10 h de payer le loyer", "payer le loyer", datetime(2026, 10, 19, 10, 0)),
    ("rappelle-moi le 25 octobre à 9 h de souhaiter l'anniversaire de Léa", "souhaiter l'anniversaire de Léa",
     datetime(2026, 10, 25, 9, 0)),
    ("fais-moi penser à 16 h de rappeler le garage", "rappeler le garage", datetime(2026, 10, 18, 16, 0)),
])
def test_cp2_rappel_au_moment_dit_relu_dans_la_base(horloge, propre, phrase, texte, quand):
    m = _msg(_chat(phrase))
    (a,) = _actifs()
    assert (a["texte"], a["echeance"], a["recurrence"]) == (texte, quand, None), a
    assert m.startswith(f"C'est enregistré : je te rappellerai « {texte} »"), m


def test_cp2_rappel_donne_a_l_heure_par_notification_et_annonce(horloge, propre):
    from core import annonces, rappels

    _chat("rappelle-moi dans 20 minutes de sortir le linge")
    horloge["t"] = T0 + timedelta(minutes=20, seconds=2)
    assert rappels.verifier() == ["Rappel : sortir le linge."]
    (a,) = annonces.lire()
    assert a["message"] == "Rappel : sortir le linge." and a["origine"] == ALEXIS


def test_cp2_rappel_repete_tous_les_lundis(horloge, propre):
    from core import rappels

    m = _msg(_chat("rappelle-moi tous les lundis à 8 h de sortir les poubelles"))
    (a,) = _actifs()
    assert a["recurrence"] == {"jours": [0], "h": 8, "m": 0} and a["echeance"] == datetime(2026, 10, 19, 8, 0)
    assert "tous les lundis à 8 h" in m, m
    horloge["t"] = datetime(2026, 10, 19, 8, 0, 3)
    assert rappels.verifier() == ["Rappel : sortir les poubelles."]
    (a,) = _actifs()
    assert a["echeance"] == datetime(2026, 10, 26, 8, 0), "reprogrammé au lundi suivant"


def test_cp2_l_ancien_p2_rappelle_moi_tous_les_jours_a_15h_n_est_plus_une_tache(horloge, propre):
    _chat("rappelle-moi de boire de l'eau tous les jours à 15h")
    (a,) = _actifs()
    assert a["recurrence"]["jours"] == list(range(7)) and a["echeance"] == datetime(2026, 10, 19, 15, 0)


def test_cp2_heure_ambigue_une_question_puis_le_choix(horloge, propre):
    r = _chat("rappelle-moi à 8 h de prendre mes médicaments")
    assert _actifs() == [], "rien n'est deviné"
    assert "À 20 h ce soir, ou à 8 h demain matin ?" in _msg(r), _msg(r)
    _chat("la 2")
    (a,) = _actifs()
    assert (a["texte"], a["echeance"]) == ("prendre mes médicaments", datetime(2026, 10, 19, 8, 0))


def test_cp2_heure_ambigue_mais_pas_encore_passee_aucune_question(horloge, propre):
    horloge["t"] = datetime(2026, 10, 18, 6, 30)
    _chat("rappelle-moi à 8 h de partir")
    (a,) = _actifs()
    assert a["echeance"] == datetime(2026, 10, 18, 8, 0)


def test_cp2_sans_moment_atlas_demande_quand(horloge, propre):
    r = _chat("rappelle-moi d'acheter du pain")
    assert "Quand" in _msg(r) and _actifs() == []
    _chat("demain à 9 h")
    (a,) = _actifs()
    assert (a["texte"], a["echeance"]) == ("acheter du pain", datetime(2026, 10, 19, 9, 0))


def test_cp2_minuteur_sans_duree_atlas_demande(horloge, propre):
    assert "combien de temps" in _msg(_chat("mets un minuteur")).lower()
    _chat("5 minutes")
    (a,) = _actifs()
    assert a["sorte"] == "minuteur" and a["echeance"] == T0 + timedelta(minutes=5)


def test_cp2_un_moment_passe_est_refuse(horloge, propre):
    m = _msg(_chat("rappelle-moi le 1er janvier 2020 à 9 h de fêter"))
    assert "déjà passé" in m and _actifs() == []


def test_cp2_persistant_et_manque_annonce_au_demarrage(horloge, propre):
    """Atlas éteint à l'heure du rappel : au démarrage suivant, il l'annonce comme manqué."""
    from core import annonces, rappels

    _chat("rappelle-moi dans 20 minutes de sortir le linge")
    (a,) = _actifs()
    rappels._pret.clear()                                          # un nouveau processus : la base est relue
    horloge["t"] = T0 + timedelta(hours=2)
    publies = rappels.verifier(au_demarrage=True)
    assert publies == ["Tu avais un rappel à 15 h 27 que je n'ai pas pu te donner : sortir le linge."], publies
    assert [x["message"] for x in annonces.lire()] == publies
    assert _actifs() == [] and rappels.lire(a["id"])["etat"] == "manque"


def test_cp2_un_rappel_tout_juste_echu_au_demarrage_est_donne_normalement(horloge, propre):
    from core import rappels

    _chat("rappelle-moi dans 20 minutes de sortir le linge")
    horloge["t"] = T0 + timedelta(minutes=20, seconds=30)
    assert rappels.verifier(au_demarrage=True) == ["Rappel : sortir le linge."]


def test_cp2_lister_et_annuler_avec_choix_si_plusieurs(horloge, propre):
    _chat("rappelle-moi dans 20 minutes de sortir le linge")
    _chat("rappelle-moi demain à 9 h de plier le linge")
    _chat("mets un minuteur de 10 minutes")
    liste = _msg(_chat("quels sont mes rappels ?"))
    assert "3 rappels en cours" in liste and "sortir le linge" in liste and "minuteur" in liste, liste
    r = _chat("annule le rappel du linge")
    assert "Plusieurs rappels correspondent" in _msg(r) and len(_actifs()) == 3
    m = _msg(_chat("le 2"))
    assert m == "J'ai annulé le rappel « plier le linge ».", m
    assert sorted(a["texte"] for a in _actifs()) == ["", "sortir le linge"]


def test_cp2_annuler_le_minuteur(horloge, propre):
    _chat("mets un minuteur de 10 minutes")
    _chat("rappelle-moi demain à 9 h de partir")
    assert _msg(_chat("annule le minuteur")) == "J'ai annulé le minuteur."
    assert [a["sorte"] for a in _actifs()] == ["rappel"]


def test_cp2_annuler_rien_qui_corresponde(horloge, propre):
    _chat("rappelle-moi demain à 9 h de partir")
    assert "aucun rappel qui corresponde" in _msg(_chat("annule le rappel du dentiste")).lower()
    assert len(_actifs()) == 1


def test_cp2_rappels_db_jamais_la_vraie_en_test():
    from core import rappels

    assert pathlib.Path(rappels.DB_PATH).resolve() != rappels.DEFAULT_DB_PATH.resolve()


def test_cp2_rappels_db_dans_les_sauvegardes():
    sys.path.insert(0, str(ROOT / "scripts"))
    import backup_memory

    assert "rappels.db" in backup_memory.SQLITE_FICHIERS


@pytest.mark.parametrize("phrase", ["rappelle-moi le code du portail", "mets un rappel dans mon téléphone",
                                    "rappelle-moi ce que je t'ai dit hier"])
def test_cp2_ce_qui_n_est_pas_un_rappel(phrase):
    from core.intent_classifier import get_classifier

    assert get_classifier().classify(phrase, {}).verb != "rappel_creer"


# --------------------------------------------------------------------------- #
#  CP3 — le son (simulé)
# --------------------------------------------------------------------------- #

class FauxSon:
    def __init__(self, niveau=50, muet=False, arrondi=0, ignore=False):
        self.niveau, self.muet, self.arrondi, self.ignore = niveau, muet, arrondi, ignore
        self.progs = [{"processus": "Spotify.exe", "pid": 11, "niveau": 60, "muet": False},
                      {"processus": "Discord.exe", "pid": 22, "niveau": 100, "muet": False}]
        self.appels = []

    def general(self):
        return {"niveau": self.niveau, "muet": self.muet}

    def regler_general(self, niveau=None, muet=None):
        self.appels.append(("general", niveau, muet))
        if self.ignore:
            return
        if niveau is not None:
            self.niveau = max(0, niveau - self.arrondi)
        if muet is not None:
            self.muet = muet

    def programmes(self):
        return [dict(p) for p in self.progs]

    def regler_programme(self, pid, niveau=None, muet=None):
        self.appels.append(("programme", pid, niveau, muet))
        for p in self.progs:
            if p["pid"] == pid:
                if niveau is not None:
                    p["niveau"] = niveau
                if muet is not None:
                    p["muet"] = muet


@pytest.fixture
def son(monkeypatch):
    import tools.son as module

    faux = FauxSon()
    monkeypatch.setattr(module, "MATERIEL", faux)
    return faux


def test_cp3_baisser_le_volume_dit_la_valeur_relue(son):
    son.arrondi = 1                                     # Windows arrondit : Atlas dit ce qu'il RELIT
    assert _msg(_chat("baisse le volume")) == "Volume à 39 % (il était à 50 %)."


@pytest.mark.parametrize("phrase,attendu,niveau", [
    ("monte le son", "Volume à 60 % (il était à 50 %).", 60),
    ("tu peux baisser le volume ?", "Volume à 40 % (il était à 50 %).", 40),
    ("mets le son à 25 %", "Volume à 25 % (il était à 50 %).", 25),
    ("mets le volume au maximum", "Volume à 100 % (il était à 50 %).", 100),
])
def test_cp3_regler_le_volume(son, phrase, attendu, niveau):
    assert _msg(_chat(phrase)) == attendu and son.niveau == niveau


def test_cp3_couper_et_retablir_relus(son):
    assert _msg(_chat("coupe le son")) == "Son coupé (le volume reste à 50 %)." and son.muet
    assert _msg(_chat("remets le son")) == "Son rétabli : volume à 50 %." and not son.muet


def test_cp3_monter_le_son_coupe_le_retablit(son):
    son.muet = True
    m = _msg(_chat("monte le son"))
    assert not son.muet and "je l'ai rétabli" in m, m


def test_cp3_deja_au_maximum(son):
    son.niveau = 100
    assert _msg(_chat("monte le son")) == "Le volume est déjà à 100 % (c'est le maximum)."


def test_cp3_windows_ignore_l_ordre_atlas_ne_pretend_rien(son):
    son.ignore = True
    m = _msg(_chat("baisse le volume"))
    assert m == "J'ai demandé de baisser le volume, mais il est toujours à 50 %.", m
    assert _msg(_chat("mets le son à 50 %")) == "Le volume est déjà à 50 %."
    son.ignore, son.muet = True, False
    m = _msg(_chat("coupe le son"))
    assert "toujours actif" in m, m


def test_cp3_le_pas_vient_de_la_configuration(son, monkeypatch):
    from core import competences

    monkeypatch.setattr(competences, "reglages", lambda: {"pas_volume": 5, "pas_luminosite": 20})
    assert _msg(_chat("baisse le volume")) == "Volume à 45 % (il était à 50 %)."


def test_cp3_volume_d_un_programme(son):
    m = _msg(_chat("baisse le son de Spotify"))
    assert m == "Le son de Spotify est maintenant à 50 % (il était à 60 %).", m
    assert son.niveau == 50, "le volume général n'a pas bougé"
    assert _msg(_chat("coupe le son de Discord")) == "Son de Discord coupé."
    assert _msg(_chat("mets le son de spotify à 30 %")) == "Le son de Spotify est maintenant à 30 % (il était à 50 %)."


def test_cp3_programme_sans_son_dit_ce_qui_en_a(son):
    m = _msg(_chat("baisse le son de Deezer"))
    assert "Je ne trouve pas de son venant de « Deezer »" in m and "Discord, Spotify" in m, m
    assert not [a for a in son.appels if a[0] == "programme"]


@pytest.mark.parametrize("phrase", ["baisse le son de ta voix", "parle moins fort"])
def test_cp3_le_son_de_ma_voix_n_est_pas_le_volume(son, phrase):
    r = _chat(phrase)
    assert son.appels == [] and "pas encore" in _msg(r), r


def test_cp3_pas_de_ctypes_cast_sur_les_interfaces_com_du_son():
    """Trouvé au rejeu réel du 18/10 : `ctypes.cast` sur l'interface de volume (l'exemple de pycaw) crée
    un second pointeur sans AddRef ; double Release au ramasse-miettes → violation d'accès, le
    processus meurt sans trace. QueryInterface, et un seul fil COM qui ne se ferme pas."""
    texte = (ROOT / "tools" / "son.py").read_text(encoding="utf-8")
    code = "\n".join(l for l in texte.splitlines() if not l.strip().startswith("#"))
    assert "ctypes.cast(" not in code and "QueryInterface(IAudioEndpointVolume)" in code
    assert "CoUninitialize()" not in code


def test_cp3_quel_est_le_volume(son):
    son.muet = True
    assert _msg(_chat("quel est le volume ?")) == "Le volume est à 50 %, son coupé."


# --------------------------------------------------------------------------- #
#  CP4 — la luminosité et la veille des écrans (simulées)
# --------------------------------------------------------------------------- #

class FauxEcrans:
    def __init__(self):
        self.ddc = [{"rang": 0, "description": "Generic PnP Monitor", "ddc": True, "niveau": 70, "min": 0, "max": 100},
                    {"rang": 1, "description": "Generic PnP Monitor", "ddc": False, "niveau": None, "min": 0, "max": 0}]
        self.wmi = None
        self.veilles = 0
        self.arrondi = 0

    def ddc_lire(self):
        return [dict(e) for e in self.ddc]

    def ddc_regler(self, rang, niveau):
        e = self.ddc[rang]
        if not e["ddc"]:
            return False
        e["niveau"] = niveau - self.arrondi
        return True

    def wmi_lire(self):
        return self.wmi

    def wmi_regler(self, niveau):
        self.wmi = niveau
        return True

    def veille_affichage(self):
        self.veilles += 1
        return True


@pytest.fixture
def ecrans(monkeypatch):
    import tools.affichage as module

    faux = FauxEcrans()
    monkeypatch.setattr(module, "MATERIEL", faux)
    return faux


def test_cp4_luminosite_relue_et_refus_dit_ecran_par_ecran(ecrans):
    ecrans.arrondi = 1
    m = _msg(_chat("mets la luminosité à 40 %"))
    assert m == ("Luminosité : écran 1 à 39 % (il était à 70 %) ; écran 2 : cet écran n'accepte pas le réglage "
                 "(DDC/CI désactivé ou non géré)."), m


def test_cp4_luminosite_au_maximum_et_baisser(ecrans):
    _chat("règle la luminosité au maximum")
    assert ecrans.ddc[0]["niveau"] == 100
    _chat("baisse la luminosité de l'écran")
    assert ecrans.ddc[0]["niveau"] == 80


def test_cp4_aucun_ecran_n_accepte(ecrans):
    ecrans.ddc[0]["ddc"], ecrans.ddc[0]["niveau"] = False, None
    m = _msg(_chat("baisse la luminosité"))
    assert m.startswith("Aucun écran n'a accepté le réglage"), m


def test_cp4_portable_par_wmi(ecrans):
    ecrans.ddc, ecrans.wmi = [], 50
    assert _msg(_chat("augmente la luminosité")) == "Luminosité : écran intégré à 70 % (il était à 50 %)."


@pytest.mark.parametrize("phrase", ["éteins l'écran", "mets les écrans en veille", "éteins les écrans",
                                    "coupe l'écran", "éteins l'écran du pc"])
def test_cp4_eteins_l_ecran_met_les_ecrans_en_veille_et_rien_d_autre(ecrans, phrase):
    m = _msg(_chat(phrase))
    fin = time.monotonic() + 4
    while ecrans.veilles == 0 and time.monotonic() < fin:
        time.sleep(0.05)
    assert ecrans.veilles == 1, phrase
    assert "veille des écrans" in m and "Je ne peux pas le vérifier" in m, m


@pytest.mark.parametrize("phrase", ["éteins le pc", "éteins l'ordinateur", "mets le pc en veille",
                                    "mets l'ordinateur en veille", "redémarre le pc", "éteins tout",
                                    "verrouille le pc", "éteins le pc et l'écran", "mets en veille"])
def test_cp4_aucun_chemin_vers_l_extinction_ou_la_veille_du_pc(ecrans, monkeypatch, phrase):
    """Ni veille des écrans, ni extinction, ni redémarrage, ni veille du PC : la réponse honnête."""
    import core.intent_engine as ie

    executes = []
    for nom in list(ie.TOOL_HANDLERS):
        monkeypatch.setitem(ie.TOOL_HANDLERS, nom, (lambda n: lambda a: executes.append(n) or {"success": True,
                                                                                            "message": "x"})(nom))
    _chat(phrase)
    assert ecrans.veilles == 0 and executes == [], (phrase, executes)


def test_cp4_le_module_d_affichage_ne_contient_aucun_appel_d_extinction():
    interdits = ("ExitWindows", "InitiateSystemShutdown", "InitiateShutdown", "SetSuspendState", "LockWorkStation",
                 "powrprof", "shutdown", "Stop-Computer", "Restart-Computer", "rundll32", "SetSystemPowerState",
                 "/hibernate", "psshutdown")
    for fichier in ("tools/affichage.py", "core/competences.py", "core/regles_competences.py"):
        texte = (ROOT / fichier).read_text(encoding="utf-8")
        for mot in interdits:
            assert mot.lower() not in texte.lower(), (fichier, mot)


def test_cp4_la_veille_envoie_exactement_sc_monitorpower(monkeypatch):
    """Le seul message envoyé : WM_SYSCOMMAND / SC_MONITORPOWER / 2, à tous (HWND_BROADCAST)."""
    from types import SimpleNamespace

    import tools.affichage as affichage

    envoyes = []
    faux_ctypes = SimpleNamespace(windll=SimpleNamespace(user32=SimpleNamespace(
        PostMessageW=lambda *a: envoyes.append(a) or 1)))
    monkeypatch.setattr(affichage, "ctypes", faux_ctypes)
    assert affichage.Materiel().veille_affichage() is True
    assert envoyes == [(0xFFFF, 0x0112, 0xF170, 2)]


# --------------------------------------------------------------------------- #
#  CP5 — le Bluetooth (simulé)
# --------------------------------------------------------------------------- #

class FauxBluetooth:
    def __init__(self, radio="allume", appaires=None, ignore=False):
        self.radio, self.ignore = radio, ignore
        self.liste = appaires if appaires is not None else [
            {"nom": "JBL E45BT", "sorte": "classique", "connecte": False, "saisie": None, "id": "a"}]
        self.reglages, self.parametres = [], 0

    def etat(self):
        return self.radio

    def regler(self, allume):
        self.reglages.append(allume)
        if self.radio is None:
            return "pas_de_radio"
        if not self.ignore:
            self.radio = "allume" if allume else "eteint"
        return "ok"

    def appaires(self):
        return [dict(a) for a in self.liste]

    def ouvrir_parametres(self):
        self.parametres += 1
        return True


@pytest.fixture
def bt(monkeypatch):
    import tools.bluetooth as module

    faux = FauxBluetooth()
    monkeypatch.setattr(module, "MATERIEL", faux)
    return faux


def test_cp5_eteindre_sans_clavier_ni_souris_relu(bt):
    m = _msg(_chat("désactive le bluetooth"))
    assert bt.reglages == [False] and m == "Le Bluetooth est maintenant éteint.", m
    assert _msg(_chat("active le bluetooth")) == "Le Bluetooth est maintenant allumé."


def test_cp5_clavier_bluetooth_connecte_confirmation_qui_nomme_l_appareil(bt):
    bt.liste.append({"nom": "MX Keys", "sorte": "le", "connecte": True, "saisie": "clavier", "id": "k"})
    r = _chat("coupe le bluetooth")
    assert r.get("type") == "confirmation_required" and bt.reglages == [], r
    assert "« MX Keys » (clavier)" in _msg(r) and "perdre la main" in _msg(r), r
    _confirmer(r)
    assert bt.reglages == [False] and bt.radio == "eteint"


def test_cp5_confirmation_refusee_rien_n_est_coupe(bt):
    bt.liste.append({"nom": "MX Master", "sorte": "le", "connecte": True, "saisie": "souris", "id": "s"})
    _confirmer(_chat("désactive le bluetooth"), accepte=False)
    assert bt.reglages == [] and bt.radio == "allume"


def test_cp5_windows_ignore_l_ordre_atlas_le_dit(bt):
    bt.ignore = True
    m = _msg(_chat("désactive le bluetooth"))
    assert "mais il est toujours allumé" in m, m


def test_cp5_deja_eteint(bt):
    bt.radio = "eteint"
    assert _msg(_chat("désactive le bluetooth")) == "Le Bluetooth est déjà éteint."


@pytest.mark.parametrize("phrase", ["active le bluetooth", "désactive le bluetooth", "connecte mon casque",
                                    "est-ce que le bluetooth est activé ?"])
def test_cp5_pc_sans_bluetooth_dit(bt, phrase):
    bt.radio = None
    assert "n'a pas de Bluetooth utilisable" in _msg(_chat(phrase))


def test_cp5_connecter_un_appareil_appaire_honnete_et_parametres_ouverts(bt):
    m = _msg(_chat("connecte mon casque JBL"))
    assert bt.parametres == 1 and "Windows ne permet pas à Atlas de connecter « JBL E45BT »" in m, m
    assert "paramètres Bluetooth" in m


def test_cp5_connecter_un_inconnu_liste_les_appaires(bt):
    m = _msg(_chat("connecte mes AirPods"))
    assert "Je ne trouve aucun appareil appairé" in m and "JBL E45BT" in m and bt.parametres == 0, m


def test_cp5_detection_des_claviers_et_souris():
    from tools import bluetooth

    assert bluetooth._saisie_classique(0x000540) == "clavier"          # majeur 5, mineur clavier
    assert bluetooth._saisie_classique(0x000580) == "souris"
    assert bluetooth._saisie_classique(0x240404) is None              # audio (casque)
    assert bluetooth._saisie_le(15, 1) == "clavier" and bluetooth._saisie_le(15, 2) == "souris"
    assert bluetooth._saisie_le(15, 4) is None


# --------------------------------------------------------------------------- #
#  CP6 — la musique (simulée)
# --------------------------------------------------------------------------- #

class FauxMusique:
    def __init__(self, session=None, installes=("spotify",), ignore=False):
        self.session = session
        self.installes, self.ignore = set(installes), ignore
        self.file = [("Harder, Better, Faster, Stronger", "Daft Punk"), ("One More Time", "Daft Punk")]
        self.commandes, self.ouverts = [], []

    def courante(self):
        return dict(self.session) if self.session else None

    def sessions(self):
        return [self.courante()] if self.session else []

    def commander(self, commande):
        self.commandes.append(commande)
        if self.ignore or not self.session:
            return bool(self.session)
        if commande == "pause":
            self.session["statut"] = "pause"
        elif commande == "lecture":
            self.session["statut"] = "lecture"
        elif commande == "suivant":
            self.session["titre"], self.session["artiste"] = self.file[1]
        elif commande == "precedent":
            self.session["titre"], self.session["artiste"] = self.file[0]
        return True

    def protocole_installe(self, protocole):
        return {"spotify": "spotify", "deezer": "deezer", "music": "apple_music"}.get(protocole) in self.installes

    def ouvrir(self, adresse):
        self.ouverts.append(adresse)
        return True


@pytest.fixture
def lecteur(monkeypatch):
    import tools.musique as module

    faux = FauxMusique(session={"appli": "Spotify", "aumid": "Spotify.exe", "statut": "lecture",
                                "titre": "Harder, Better, Faster, Stronger", "artiste": "Daft Punk"})
    monkeypatch.setattr(module, "MATERIEL", faux)
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    return faux


def test_cp6_pause_relue(lecteur, propre):
    m = _msg(_chat("mets la musique en pause"))
    assert m == "Pause dans Spotify : « Harder, Better, Faster, Stronger » — Daft Punk.", m


def test_cp6_deja_en_pause(lecteur, propre):
    lecteur.session["statut"] = "pause"
    assert _msg(_chat("pause")) == "Spotify est déjà en pause : « Harder, Better, Faster, Stronger » — Daft Punk."


def test_cp6_suivant_dit_le_nouveau_titre_relu(lecteur, propre):
    assert _msg(_chat("passe à la chanson suivante")) == "Morceau suivant dans Spotify : « One More Time » — Daft Punk."


def test_cp6_le_lecteur_ignore_atlas_le_dit(lecteur, propre):
    lecteur.ignore = True
    assert "mais il indique toujours « lecture »" in _msg(_chat("pause"))
    assert "le titre affiché n'a pas changé" in _msg(_chat("chanson suivante"))


def test_cp6_qu_est_ce_qui_passe(lecteur, propre):
    assert _msg(_chat("qu'est-ce qui passe ?")) == \
        "En ce moment dans Spotify : « Harder, Better, Faster, Stronger » — Daft Punk (en lecture)."


def test_cp6_aucun_lecteur(lecteur, propre):
    lecteur.session = None
    assert _msg(_chat("qu'est-ce qui passe ?")) == "Aucun lecteur ne publie de lecture à Windows en ce moment."
    assert "rien à commander" in _msg(_chat("mets la musique en pause"))


def test_cp6_service_demande_une_fois_puis_retenu(lecteur, propre):
    from core import competences

    r = _chat("mets du Daft Punk")
    assert _msg(r) == "Quel service de musique utilises-tu : Spotify, Deezer, Apple Music ou YouTube Music ?"
    assert lecteur.ouverts == []
    m = _msg(_chat("Spotify"))
    assert lecteur.ouverts == ["spotify:search:Daft%20Punk"], lecteur.ouverts
    assert "J'ai ouvert la recherche « Daft Punk » dans Spotify" in m and "Je retiens Spotify" in m, m
    assert competences.service_prefere() == "spotify"
    m = _msg(_chat("mets du Justice"))
    assert lecteur.ouverts[-1] == "spotify:search:Justice" and "Quel service" not in m


def test_cp6_atlas_ne_pretend_jamais_jouer(lecteur, propre):
    from core import competences

    competences._retenir_service("spotify")
    m = _msg(_chat("mets du Daft Punk"))
    assert not re.search(r"\bje (?:joue|lance la lecture|mets) ", m.lower()), m
    assert "je ne lance pas la lecture moi-même" in m


def test_cp6_changer_de_service(lecteur, propre):
    from core import competences

    competences._retenir_service("spotify")
    assert _msg(_chat("j'utilise Deezer maintenant")) == "C'est noté : Deezer pour la musique."
    assert competences.service_prefere() == "deezer"


def test_cp6_service_non_installe_propose_le_navigateur(lecteur, propre):
    from core import competences

    competences._retenir_service("deezer")                  # Deezer n'est pas installé (FauxMusique)
    m = _msg(_chat("mets du Daft Punk"))
    assert "Deezer n'a pas l'air installé" in m and lecteur.ouverts == [], m
    m = _msg(_chat("oui"))
    assert lecteur.ouverts == ["https://www.deezer.com/search/Daft%20Punk"], lecteur.ouverts
    assert "dans ton navigateur sur Deezer" in m, m


def test_cp6_l_application_ne_s_ouvre_pas_atlas_propose_le_navigateur(lecteur, propre):
    """Rejeu réel du 18/10 : Apple Music (Store) déclare music:// mais ne s'ouvre pas depuis un programme
    de bureau (« fichier introuvable »). Atlas le dit, sans message système, et propose le navigateur."""
    from core import competences

    lecteur.installes.add("apple_music")
    vrai_ouvrir = lecteur.ouvrir

    def ouvrir(adresse):
        if adresse.startswith("music://"):
            raise FileNotFoundError(2, "Le fichier spécifié est introuvable")
        return vrai_ouvrir(adresse)

    lecteur.ouvrir = ouvrir
    competences._retenir_service("apple_music")
    m = _msg(_chat("mets du Daft Punk"))
    assert m.startswith("Je n'arrive pas à ouvrir l'application Apple Music") and "WinError" not in m, m
    _chat("oui")
    assert lecteur.ouverts == ["https://music.apple.com/search?term=Daft%20Punk"], lecteur.ouverts


def test_cp6_service_inconnu_propose_youtube_music_dans_le_navigateur(lecteur, propre):
    _chat("mets du Daft Punk")
    m = _msg(_chat("Qobuz"))
    assert m.startswith("Je ne connais pas « qobuz ».") and "navigateur" in m, m
    _chat("oui")
    assert lecteur.ouverts == ["https://music.youtube.com/search?q=Daft%20Punk"], lecteur.ouverts


def test_cp6_youtube_music_s_ouvre_dans_le_navigateur(lecteur, propre):
    m = _msg(_chat("mets du Daft Punk sur YouTube Music"))
    assert lecteur.ouverts == ["https://music.youtube.com/search?q=Daft%20Punk"]
    assert "dans ton navigateur sur YouTube Music" in m, m


def test_cp6_mets_de_la_musique_reprend_le_lecteur_en_pause(lecteur, propre):
    lecteur.session["statut"] = "pause"
    assert _msg(_chat("mets de la musique")).startswith("Lecture reprise dans Spotify")


@pytest.mark.parametrize("phrase,outil", [("mets Steam au premier plan", "window_focus"), ("lance discord", "launch_app"),
                                          ("ouvre Steam", "launch_app")])
def test_cp6_les_applications_restent_des_applications(phrase, outil):
    from core.intent_classifier import get_classifier
    from core.validator import get_validator

    res = get_validator().resolve(get_classifier().classify(phrase, {}), {})
    assert res.tool == outil, res.tool


# --------------------------------------------------------------------------- #
#  CP7 — la liste des capacités, depuis le registre
# --------------------------------------------------------------------------- #

def test_cp7_toute_famille_du_registre_est_annoncee():
    import core.intent_engine as ie

    familles = {f for f, _ in ie.TOOL_CAPABILITIES.values()}
    assert familles <= set(ie.CAPABILITY_FAMILIES), familles - set(ie.CAPABILITY_FAMILIES)
    for f in ie.CAPABILITY_FAMILIES:
        assert f in ie._FAMILY_EXAMPLE, f


def test_cp7_tu_peux_faire_quoi_montre_les_nouvelles_familles():
    m = _msg(_chat("tu peux faire quoi ?"))
    for famille in ("Son et écrans", "Bluetooth", "Musique", "Heure et rappels", "Documents", "Fichiers"):
        assert f"- {famille} :" in m, (famille, m)
    assert "régler le volume" in m and "mettre un minuteur ou un rappel" in m


def test_cp7_le_detail_d_une_nouvelle_famille():
    m = _msg(_chat("que sais-tu faire avec la musique ?"))
    assert m.startswith("Musique :") and "dire ce qui passe" in m, m


def test_cp7_tous_les_outils_du_sprint_sont_executes_et_exposes():
    import core.intent_engine as ie

    for outil in ie.OUTILS_COMPETENCES:
        assert outil in ie.TOOL_HANDLERS and outil in ie.capability_tools(), outil


def test_cp7_le_vrai_materiel_est_interdit_en_test():
    import tools.son as son

    with pytest.raises(RuntimeError, match="vrai matériel est interdit"):
        son.MATERIEL.general()
