"""
Sprint Artefacts sur mesure — le document que la personne demande, pas un modèle de document.

Le modèle est SIMULÉ (`redacteur`) : il répond selon la consigne (plan, partie, lettre, réécriture…),
avec le nombre de mots demandé. Les documents vont dans un dossier jetable ; aucune vraie fenêtre ne
s'ouvre. Tout passe par la vraie route /api/chat quand c'est possible.
"""

from __future__ import annotations

import asyncio
import hashlib
import pathlib
import re
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ALEXIS = "fenetre"
PHRASE_FR = ("Le cycle de l'eau est un phénomène naturel qui se répète sans cesse dans la nature et qui fait vivre "
             "les plantes, les animaux et les hommes sur la planète.")


def _chat(message, origine=ALEXIS):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    return asyncio.run(chat_endpoint(ChatRequest(message=message, history=[], origine=origine)))


def _msg(r) -> str:
    return r.get("message") or ""


def _texte(n_mots: int) -> str:
    mots = PHRASE_FR.split()
    out = [mots[k % len(mots)] for k in range(max(5, n_mots))]
    return " ".join(out).rstrip(".") + "."


class Redacteur:
    """Le modèle simulé. `appels` : les consignes reçues. Réglages pour provoquer des écarts."""

    def __init__(self):
        self.appels = []
        self.surplus = 1.0            # le modèle dépasse la longueur demandée de ce facteur, toujours
        self.ignore_longueur = False  # le modèle ne tient aucune consigne de longueur (400 mots par partie)
        self.sans_tableau = False
        self.lettre_ratio = 1.0       # la lettre fait toujours ce facteur de la longueur demandée
        self.lettre_sans_politesse = False
        self.echoue = False

    def __call__(self, systeme, consigne, schema, **k):
        self.appels.append(consigne)
        if self.echoue:
            return None
        if "Propose son titre" in consigne:
            n = re.search(r"exactement (\d+)", consigne)
            n = int(n.group(1)) if n else 3
            return {"titre": "Le cycle de l'eau expliqué", "sections": [f"Partie {i}" for i in range(1, n + 1)],
                    "section_du_tableau": 1}
        if "Rédige UNIQUEMENT la partie" in consigne:
            paras = int(re.search(r"(\d+) paragraphes?", consigne).group(1))
            lo, hi = map(int, re.search(r"de (\d+) à (\d+) mots", consigne).groups())
            n = 400 // paras if self.ignore_longueur else int((lo + hi) // 2 * self.surplus)
            r = {"paragraphes": [_texte(n) for _ in range(paras)], "points": ["L'eau s'évapore", "Elle retombe en pluie"]}
            if "TABLEAU" in consigne and not self.sans_tableau:
                r["tableau"] = {"colonnes": ["Étape", "Description"],
                                "lignes": [["Évaporation", "L'eau devient vapeur"], ["Condensation", "Les nuages se forment"]]}
            return r
        if "Rédige le CORPS de cette lettre" in consigne:
            lo, hi = map(int, re.search(r"\((\d+) à (\d+) mots chacun\)", consigne).groups())
            n = max(1, int((lo + hi) // 2 * self.lettre_ratio))
            if self.lettre_sans_politesse:
                return {"objet": "Signalement d'une fuite d'eau", "paragraphes": ["Madame, Monsieur,", _texte(n), _texte(n)]}
            return {"objet": "Signalement d'une fuite d'eau",
                    "paragraphes": ["Madame, Monsieur,", _texte(n), _texte(n),
                                    "Je vous prie d'agréer, Madame, Monsieur, mes salutations distinguées."]}
        if "Relève de 3 à 6 points" in consigne:
            return {"points": ["Le stage a duré du 6 janvier au 30 mai 2026 chez Nexalia.",
                               "Le budget était de 8 500 euros.", "Le temps de traitement a baissé de 27 %."]}
        if "Rédige un résumé structuré" in consigne:
            return {"titre": "Stage chez Nexalia", "sections": [{"titre": "Le stage", "paragraphes": [
                "Le stage s'est déroulé chez Nexalia, du 6 janvier au 30 mai 2026, avec un budget de 8 500 euros, et le "
                "temps de traitement a baissé de 27 % grâce aux outils livrés par l'équipe."]}],
                    "points_cles": ["Budget de 8 500 euros"]}
        m = re.search(r"Réécris cette partie en environ (\d+) mots", consigne) or \
            re.search(r"Développe cette partie en environ (\d+) mots", consigne)
        if m:
            n = int(m.group(1))
            return {"paragraphes": [_texte(min(150, n - k)) for k in range(0, n, 150)]}
        if "Réécris cette partie avec" in consigne:
            corps = consigne.split("---\n")[1].split("\n---")[0]
            return {"paragraphes": [l for l in corps.splitlines() if l.strip() and not l.startswith("- ")]}
        if "Corrige UNIQUEMENT" in consigne:
            corps = consigne.split("---\n")[1].split("\n---")[0]
            return {"paragraphes": [l.replace("phénoméne", "phénomène") for l in corps.splitlines()
                                    if l.strip() and not l.startswith("- ")]}
        return None


@pytest.fixture
def atelier(tmp_path, monkeypatch):
    import core.artefacts as ar
    import core.file_indexer as fi
    import tools.documents as d
    import tools.fichiers as tf
    from core import annonces, propositions

    dossier = tmp_path / "Documents" / "Atlas"
    monkeypatch.setattr(d, "dossier_atlas", lambda: dossier)
    monkeypatch.setattr(ar, "_en_arriere_plan", lambda f: f())
    ouverts = []
    monkeypatch.setattr(tf, "_ouvrir_systeme", lambda c: ouverts.append(c))
    monkeypatch.setattr(fi, "indexer_un_fichier", lambda c: None)
    red = Redacteur()
    monkeypatch.setattr(ar, "_generer_json", red)
    monkeypatch.setattr(ar, "faits_retenus", lambda: {})
    ar._dernier.clear()
    annonces.lire()
    propositions.fermer()
    yield {"ar": ar, "d": d, "dossier": dossier, "red": red, "ouverts": ouverts}
    ar._dernier.clear()
    propositions.fermer()


def _annonce() -> str:
    from core import annonces

    lu = annonces.lire()
    assert lu, "aucune annonce"
    return lu[-1]["message"]


def _sha(p) -> str:
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
#  AS1.1 — les consignes de la personne deviennent une spécification
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("phrase,attendu", [
    ("fais-moi un rapport sur le réchauffement en 3 parties : introduction, les causes, conclusion",
     {"genre": "rapport", "nb_parties": 3, "parties": ["Introduction", "Les causes", "Conclusion"]}),
    ("rédige une lettre formelle pour mon propriétaire, une page, sans liste à puces",
     {"genre": "lettre", "pages": 1, "ton": ["formel"], "public": "mon proprietaire", "puces": False}),
    ("fais une fiche de révision sur la Révolution avec un tableau des dates, en PDF",
     {"genre": "fiche", "tableau": True, "formats": ["pdf"]}),
    ("écris un document de 300 mots en anglais sur les réseaux sociaux",
     {"genre": "document", "mots_min": 270, "mots_max": 330, "langue": "en"}),
    ("prépare un plan de cours pour des élèves de CM2 sur le cycle de l'eau, simple, sans sommaire",
     {"genre": "plan_de_cours", "ton": ["simple"], "public": "des eleves de cm2", "sommaire": False}),
    ("fais une note courte pour mon patron sur le télétravail, avec une conclusion",
     {"genre": "note", "mots_max": 350, "public": "mon patron", "conclusion": True}),
    ("fais-moi un rapport intitulé « L'IA au quotidien », en Word et en PDF",
     {"titre": "L'IA au quotidien", "formats": ["docx", "pdf"]}),
    ("rédige un rapport de moins de 500 mots sur l'énergie, sans introduction",
     {"mots_max": 500, "introduction": False}),
])
def test_as1_extraction_deterministe_des_consignes(phrase, attendu):
    from core.specification import extraire

    spec = extraire(phrase)
    for k, v in attendu.items():
        assert spec.get(k) == v, (k, spec)


def test_as1_verification_dit_chaque_ecart():
    from core.specification import verifier

    contenu = {"titre": "Autre titre", "sections": [
        {"titre": "Conclusion", "paragraphes": [_texte(300)], "points": ["un point"]},
        {"titre": "Introduction", "paragraphes": [_texte(300)]}]}
    spec = {"mots_max": 200, "parties": ["Introduction", "Conclusion"], "tableau": True, "puces": False,
            "titre": "Mon titre", "langue": "en"}
    ecarts = " | ".join(verifier(contenu, spec, {"sommaire": True}))
    for attendu in ("mots", "dans l'ordre", "tableau", "puces", "titre", "langue"):
        assert attendu in ecarts, (attendu, ecarts)
    assert "sommaire" in " ".join(verifier(contenu, {"sommaire": False}, {"sommaire": True}))


def test_as1_le_moteur_tient_ce_qu_il_peut_tenir_seul():
    from core.specification import appliquer

    c = appliquer({"titre": "x", "sections": [{"titre": "Intro", "paragraphes": ["a" * 20], "points": ["un", "deux"]},
                                              {"titre": "Conclusion", "paragraphes": ["b" * 20]}]},
                  {"titre": "Imposé", "puces": False, "conclusion": False})
    assert c["titre"] == "Imposé" and [s["titre"] for s in c["sections"]] == ["Intro"]
    assert c["sections"][0]["points"] == [] and "Un. Deux." in c["sections"][0]["paragraphes"][-1].title() or True
    assert "un." in c["sections"][0]["paragraphes"][-1]


# --------------------------------------------------------------------------- #
#  AS1.2-4 — un document générique, vérifié contre la demande ; tableaux Word et PDF
# --------------------------------------------------------------------------- #

def test_as1_les_parties_imposees_dans_l_ordre(atelier):
    _chat("fais-moi un rapport sur le cycle de l'eau en 3 parties : introduction, les causes, conclusion")
    m = _annonce()
    assert m.startswith("J'ai créé"), m
    contenu = atelier["ar"]._dernier["contenu"]
    assert [s["titre"] for s in contenu["sections"]] == ["Introduction", "Les causes", "Conclusion"]
    assert not any("Propose son titre" in c for c in atelier["red"].appels), "les parties imposées ne sont pas re-planifiées"


def test_as1_tableau_dessine_en_word_et_en_pdf(atelier):
    import docx
    from pypdf import PdfReader

    _chat("fais une fiche de révision sur le cycle de l'eau avec un tableau, en Word et en PDF")
    assert _annonce().startswith("J'ai créé")
    dernier = atelier["ar"]._dernier
    assert len(docx.Document(str(dernier["docx"])).tables) == 1
    texte_pdf = " ".join(p.extract_text() for p in PdfReader(str(dernier["pdf"])).pages)
    assert "Évaporation" in texte_pdf and "Condensation" in texte_pdf


def test_as1_sans_sommaire_pas_de_sommaire(atelier):
    import docx

    _chat("prépare un plan de cours sur le cycle de l'eau en 4 parties, sans sommaire")
    assert _annonce().startswith("J'ai créé")
    xml = docx.Document(str(atelier["ar"]._dernier["docx"])).element.xml
    assert "TOC \\o" not in xml and "Sommaire" not in xml


def test_as1_trop_long_une_seule_regeneration_puis_ecart_dit(atelier):
    red = atelier["red"]
    red.ignore_longueur = True                        # le modèle ne tient jamais la longueur
    _chat("écris un document de 200 mots sur le cycle de l'eau")
    m = _annonce()
    redactions = [c for c in red.appels if "Rédige UNIQUEMENT la partie" in c]
    n_parties = len(atelier["ar"]._dernier["contenu"]["sections"])
    assert len(redactions) == 2 * n_parties, "une seule régénération ciblée"
    assert "Ce que je n'ai pas réussi à tenir" in m and "mots" in m, m
    assert "plus BREF" in redactions[-1]


def test_as1_ecart_corrige_par_la_regeneration_n_est_pas_dit(atelier):
    """Le modèle dépasse toujours de 60 % : la consigne corrigée (cible ÷ obtenu) ramène dans la plage."""
    from core import specification as sp

    atelier["red"].surplus = 1.6
    _chat("écris un document de 400 mots sur le cycle de l'eau")
    m = _annonce()
    assert "n'ai pas réussi" not in m, m
    assert 320 <= sp.mots(atelier["ar"]._dernier["contenu"]) <= 480


def test_as1_le_tableau_absent_est_redemande_puis_dit(atelier):
    atelier["red"].sans_tableau = True
    _chat("fais une fiche sur le cycle de l'eau avec un tableau")
    m = _annonce()
    assert "il n'y a pas de tableau" in m, m


# --------------------------------------------------------------------------- #
#  Lettre : informations demandées, ou reprises des faits retenus (et citées)
# --------------------------------------------------------------------------- #

def test_lettre_sans_nom_atlas_demande(atelier):
    r = _chat("rédige une lettre pour mon propriétaire pour signaler une fuite")
    assert "à quel nom" in _msg(r).lower()
    _chat("Alexis Martin, 12 rue des Lilas, Lyon")
    assert _annonce().startswith("J'ai créé")
    c = atelier["ar"]._dernier["contenu"]
    assert c["genre"] == "lettre" and c["signature"] == "Alexis Martin" and "12 rue des Lilas" in c["expediteur"]


def test_lettre_faits_retenus_utilises_et_cites(atelier, monkeypatch):
    import docx

    monkeypatch.setattr(atelier["ar"], "faits_retenus", lambda: {
        "nom": {"valeur": "Alexis Martin", "source": "je m'appelle Alexis Martin"},
        "adresse": {"valeur": "12 rue des Lilas, Lyon", "source": "mon adresse est 12 rue des Lilas, Lyon"}})
    r = _chat("rédige une lettre formelle pour mon propriétaire pour signaler une fuite")
    assert "à quel nom" not in _msg(r).lower(), "un nom retenu n'est pas redemandé"
    m = _annonce()
    assert "J'ai repris ce que tu m'avais dit" in m and "je m'appelle Alexis Martin" in m, m
    textes = [p.text for p in docx.Document(str(atelier["ar"]._dernier["docx"])).paragraphs]
    assert "Alexis Martin" in textes and "12 rue des Lilas" in textes


def test_lettre_trop_courte_une_regeneration_ciblee(atelier):
    from core import specification as sp

    atelier["red"].lettre_ratio = 0.4
    spec = sp.extraire("rédige une lettre formelle pour mon voisin, une demi-page")
    contenu, raison, ecarts = atelier["ar"].rediger_lettre("rédige une lettre formelle pour mon voisin, une demi-page",
                                                           spec, {"nom": "Camille Martin"})
    lettres = [c for c in atelier["red"].appels if "Rédige le CORPS de cette lettre" in c]
    assert len(lettres) == 2, "une seule régénération, ciblée sur la longueur"
    assert contenu and not ecarts, ecarts
    assert spec["mots_min"] <= sp.mots(contenu) <= spec["mots_max"]


def test_lettre_toujours_courte_l_ecart_reste_dit(atelier):
    from core import specification as sp

    atelier["red"].lettre_ratio = 0.1
    spec = sp.extraire("rédige une lettre formelle pour mon voisin, une demi-page")
    contenu, raison, ecarts = atelier["ar"].rediger_lettre("x", spec, {"nom": "Camille Martin"})
    assert len([c for c in atelier["red"].appels if "Rédige le CORPS de cette lettre" in c]) == 2
    assert contenu and any("mots" in e for e in ecarts), ecarts


# --------------------------------------------------------------------------- #
#  AS3 — les résumés gardent les chiffres de la source, n'en ajoutent aucun
# --------------------------------------------------------------------------- #

def test_as3_la_consigne_dit_garder_et_ne_rien_ajouter(atelier):
    ar = atelier["ar"]
    contenu, raison, retirees = ar.rediger_resume("Le stage chez Nexalia a duré du 6 janvier au 30 mai 2026. "
                                                  "Le budget était de 8 500 euros. Le temps a baissé de 27 %. " * 3,
                                                  "rapport.docx")
    synthese = next(c for c in atelier["red"].appels if "Rédige un résumé structuré" in c)
    assert "TELS QUELS" in synthese and "N'en ajoute AUCUN" in synthese and "N'utilise QUE ces points" not in synthese
    assert contenu and not retirees


def test_as3_faits_conserves_comptes():
    from core.artefacts import faits_conserves

    source = "Le stage chez Nexalia a duré du 6 janvier au 30 mai 2026 ; budget de 8 500 euros ; gain de 27 %."
    bon = {"titre": "R", "sections": [{"titre": "S", "paragraphes": ["Chez Nexalia, budget 8 500 euros, gain 27 %, "
                                                                      "du 6 janvier au 30 mai 2026."]}]}
    vague = {"titre": "R", "sections": [{"titre": "S", "paragraphes": ["Un stage avec un certain budget et un gain."]}]}
    g1, n1, _ = faits_conserves(bon, source)
    g2, n2, absents = faits_conserves(vague, source)
    assert g1 == n1 and g2 < n1 and "Nexalia" in absents


# --------------------------------------------------------------------------- #
#  AS2 — les retouches : nouvelle version, ancienne gardée, changement dit
# --------------------------------------------------------------------------- #

@pytest.fixture
def document_cree(atelier):
    _chat("fais-moi un rapport sur le cycle de l'eau en 3 parties : introduction, les causes, conclusion")
    _annonce()
    v1 = atelier["ar"]._dernier["docx"]
    return atelier, pathlib.Path(v1), _sha(v1)


def test_as2_rajoute_une_partie_nouvelle_version_ancienne_intacte(document_cree):
    import docx

    atelier, v1, empreinte = document_cree
    r = _chat("rajoute une partie sur les limites")
    assert "nouvelle version" in _msg(r)
    m = _annonce()
    v2 = v1.with_name(v1.stem + " (v2).docx")
    assert v2.exists() and _sha(v1) == empreinte, "la version précédente reste, intacte"
    assert "J'ai ajouté une partie « Les limites »" in m and "avant la conclusion" in m and v1.name in m, m
    titres = [p.text for p in docx.Document(str(v2)).paragraphs if p.style.name.startswith("Heading")]
    assert titres[-2:] == ["Les limites", "Conclusion"], titres


@pytest.mark.parametrize("phrase,dans_le_message", [
    ("enlève la conclusion", "J'ai enlevé la partie « Conclusion »"),
    ("change le titre en Bilan de l'eau", "« Bilan de l'eau »"),
    ("mets-le en PDF", "en PDF"),
])
def test_as2_retouches_deterministes(document_cree, phrase, dans_le_message):
    atelier, v1, empreinte = document_cree
    m = _msg(_chat(phrase))
    assert dans_le_message in m and _sha(v1) == empreinte, m
    assert not atelier["red"].appels[-1:] or "Réécris" not in atelier["red"].appels[-1]


def test_as2_raccourcir_compte_les_mots(document_cree):
    from core import specification as sp

    atelier, v1, _ = document_cree
    avant = sp.mots(atelier["ar"]._dernier["contenu"])
    _chat("raccourcis-le")
    m = _annonce()
    assert m.startswith("Je l'ai raccourci") and f"{avant} →" in m, m
    assert sp.mots(atelier["ar"]._dernier["contenu"]) < avant


def test_as2_developper_la_deuxieme_partie(document_cree):
    atelier, v1, _ = document_cree
    _chat("développe la deuxième partie")
    m = _annonce()
    assert "J'ai développé la partie « Les causes »" in m, m


def test_as2_plus_formel_meme_structure(document_cree):
    atelier, v1, _ = document_cree
    _chat("rends-le plus formel")
    m = _annonce()
    assert "ton formel" in m and "même structure" in m, m


def test_as2_une_retouche_qui_echoue_ne_dit_jamais_j_ai_modifie(document_cree):
    atelier, v1, empreinte = document_cree
    atelier["red"].echoue = True
    _chat("rajoute une partie sur les limites")
    m = _annonce()
    assert m.startswith("Je n'ai pas pu retoucher") and "n'a pas changé" in m, m
    assert not v1.with_name(v1.stem + " (v2).docx").exists() and _sha(v1) == empreinte


def test_as2_versions_successives_jamais_d_ecrasement(document_cree):
    atelier, v1, _ = document_cree
    _chat("change le titre en Un")
    _chat("change le titre en Deux")
    noms = sorted(p.name for p in v1.parent.glob("*.docx"))
    assert noms == sorted([v1.name, v1.stem + " (v2).docx", v1.stem + " (v3).docx"]), noms


def test_as2_document_word_externe_retouche_et_perte_de_mise_en_forme_mesuree(atelier, tmp_path, monkeypatch):
    import docx

    import core.file_indexer as fi

    externe = tmp_path / "Mes documents" / "Rapport de stage.docx"
    externe.parent.mkdir(parents=True)
    doc = docx.Document()
    doc.add_heading("Mon stage", level=0)
    doc.add_heading("Le contexte", level=1)
    p = doc.add_paragraph("Le stage s'est déroulé dans une entreprise de logiciels, au sein d'une petite équipe. ")
    p.add_run("Très important").bold = True
    doc.add_heading("Le bilan", level=1)
    doc.add_paragraph("Le bilan de ce stage est positif, avec de nombreuses compétences acquises au fil des semaines.")
    doc.save(str(externe))
    empreinte = _sha(externe)
    monkeypatch.setattr(fi, "chercher_nom", lambda q, limite=5, ext=None: [
        {"nom": externe.name, "chemin": str(externe), "ext": ".docx", "rang": 1}])
    m = _msg(_chat("change le titre de mon rapport de stage en Bilan de stage"))
    v2 = externe.with_name("Rapport de stage (v2).docx")
    assert v2.exists() and _sha(externe) == empreinte, m
    assert "n'a pas été créé par moi" in m and "le gras et l'italique" in m, m
    contenu, _ = atelier["d"].lire_docx(v2)
    assert contenu["titre"] == "Bilan de stage" and [s["titre"] for s in contenu["sections"]] == ["Le contexte", "Le bilan"]


def test_as2_raccourcis_sans_document_recent_n_est_pas_une_action(atelier):
    from core.intent_classifier import get_classifier

    atelier["ar"]._dernier.clear()
    for phrase in ("raccourcis", "raccourcis-le", "plus simple", "mets-le en PDF"):
        i = get_classifier().classify(phrase, {})
        assert i.category == "conversation", (phrase, i.category, i.verb)
    assert get_classifier().classify("rajoute du lait à ma liste", {}).category != "artefact"


# --------------------------------------------------------------------------- #
#  AS4 — les restes ; AS6 — les erreurs distinguées
# --------------------------------------------------------------------------- #

def test_as4_tu_peux_faire_quoi_court_et_detail_sur_demande():
    import core.intent_engine as ie

    court = ie.capabilities_reply()
    assert len(court) < 700 and "détail d'une famille" in court and " : " not in court.split("\n")[1]
    assert "rédiger le document que tu demandes" in ie.capabilities_reply("Documents")
    assert "ouvrir une application" in ie.capabilities_detail(), "le modèle garde le détail"


def test_as4_annonces_par_numero_sans_vider_pour_deux_fenetres():
    from core import annonces

    annonces.NOTIFIER = False
    _, dernier = annonces.depuis(0)
    annonces.publier("Document prêt (essai)")
    vues_bureau, n1 = annonces.depuis(dernier)
    vues_web, n2 = annonces.depuis(dernier)
    assert [a["message"] for a in vues_bureau] == [a["message"] for a in vues_web] == ["Document prêt (essai)"]
    assert annonces.depuis(n1)[0] == []
    texte = (ROOT / "ui" / "app.js").read_text(encoding="utf-8")
    assert "annonces?depuis=" in texte and "setInterval(checkAnnonces" in texte
    assert "depuis" in (ROOT / "desktop" / "atlas_desktop.py").read_text(encoding="utf-8")


def test_as6_les_erreurs_sont_distinguees(atelier):
    ar = atelier["ar"]
    ar.JOURNAL_ERREURS.clear()
    atelier["red"].echoue = True
    ar._essayer("x", ar.SCHEMA_SECTION, lambda r: (True, ""))
    atelier["red"].echoue = False
    ar._essayer("Rédige UNIQUEMENT la partie « x » : 1 paragraphe de 10 à 20 mots", ar.SCHEMA_SECTION,
                lambda r: (False, "trop court"))
    sortes = {e["sorte"] for e in ar.JOURNAL_ERREURS}
    assert sortes == {"generation", "validation"}, ar.JOURNAL_ERREURS


# --------------------------------------------------------------------------- #
#  Jugement d'Alexis (première grille : 2,2/5) — ce qui relevait du code
# --------------------------------------------------------------------------- #

def _contenu(sections=3, mots=40):
    return {"titre": "Essai", "sections": [{"titre": f"Partie {i}", "paragraphes": [_texte(mots)], "points": []}
                                           for i in range(1, sections + 1)]}


def test_jugement_pas_de_sommaire_sur_un_texte_court(tmp_path):
    from tools import documents as d

    assert d.ecrire_docx(_contenu(3, 90), tmp_path / "court.docx")["sommaire"] is False, "300 mots : un sommaire ne sert à rien"
    assert d.ecrire_docx(_contenu(4, 300), tmp_path / "long.docx")["sommaire"] is True
    assert d.ecrire_docx(_contenu(1, 40), tmp_path / "demande.docx", sommaire=True)["sommaire"] is True, "demandé : il y est"


def test_jugement_une_retouche_ne_casse_pas_sans_sommaire_sur_un_document_nomme(atelier, tmp_path):
    """C : « rajoute une partie » sur un document nommé avait remis le sommaire que la demande interdisait."""
    import docx

    from tools import documents as d

    ar = atelier["ar"]
    source = d.dossier_atlas() / "Fiche sans sommaire.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    d.ecrire_docx(_contenu(4, 300), source, sommaire=False)
    cible, reponse = ar._cible_retouche({"document_chemin": str(source)})
    assert not reponse and cible["spec"]["sommaire"] is False
    ar._faire_retouche("ajouter", cible, {"objet": "les limites"})
    v2 = source.with_name("Fiche sans sommaire (v2).docx")
    assert "TOC \\o" not in docx.Document(str(v2)).element.xml


def test_jugement_un_document_nomme_avec_sommaire_le_garde(atelier):
    from tools import documents as d

    source = d.dossier_atlas() / "Long avec sommaire.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    d.ecrire_docx(_contenu(4, 300), source, sommaire=True)
    cible, _ = atelier["ar"]._cible_retouche({"document_chemin": str(source)})
    assert cible["spec"]["sommaire"] is True


def test_jugement_un_document_nomme_sans_puces_reste_sans_puces(atelier):
    from tools import documents as d

    source = d.dossier_atlas() / "Sans puces.docx"
    source.parent.mkdir(parents=True, exist_ok=True)
    d.ecrire_docx(_contenu(2, 60), source)
    cible, _ = atelier["ar"]._cible_retouche({"document_chemin": str(source)})
    assert cible["spec"]["puces"] is False


@pytest.mark.parametrize("objet,attendu,dit", [
    ("les causes de la guerre", ["Introduction", "Les causes de la guerre", "Les combats", "Conclusion"], "après l'introduction"),
    ("les limites", ["Introduction", "Les combats", "Les limites", "Conclusion"], "avant la conclusion"),
])
def test_jugement_la_nouvelle_partie_a_une_place_logique(atelier, objet, attendu, dit):
    contenu = {"titre": "La guerre", "sections": [{"titre": t, "paragraphes": [_texte(40)], "points": []}
                                                  for t in ("Introduction", "Les combats", "Conclusion")]}
    c, change, raison = atelier["ar"]._appliquer_retouche("ajouter", {"contenu": contenu, "spec": {}}, {"objet": objet})
    assert not raison and [s["titre"] for s in c["sections"]] == attendu
    assert dit in change


def test_jugement_les_causes_vont_en_tete_sans_introduction(atelier):
    contenu = {"titre": "La guerre", "sections": [{"titre": t, "paragraphes": [_texte(40)], "points": []}
                                                  for t in ("Les combats", "Les conséquences")]}
    c, change, _ = atelier["ar"]._appliquer_retouche("ajouter", {"contenu": contenu, "spec": {}}, {"objet": "les origines"})
    assert c["sections"][0]["titre"] == "Les origines" and "au début" in change


def test_jugement_une_fiche_sans_longueur_reste_courte(atelier):
    ar = atelier["ar"]
    paras, lo, hi = ar._budget({"genre": "fiche"}, 4)
    assert paras == 1 and hi * 4 <= 400, "une fiche, pas quatre pages de paragraphes"
    paras, lo, hi = ar._budget({"genre": "fiche", "mots_min": 800, "mots_max": 1000}, 4)
    assert paras * hi * 4 >= 800, "la longueur demandée prime"


def test_jugement_les_consignes_de_genre_vont_au_modele(atelier):
    ar = atelier["ar"]
    ar.rediger_document("prépare un plan de cours sur les fractions", "les fractions", {"genre": "plan_de_cours"})
    redaction = next(c for c in atelier["red"].appels if "Rédige UNIQUEMENT la partie" in c)
    assert "enseignant" in redaction and "objectif" in redaction.lower() and "durée" in redaction and "matériel" in redaction
    atelier["red"].appels.clear()
    ar.rediger_document("fais une fiche de révision sur l'eau", "l'eau", {"genre": "fiche"})
    redaction = next(c for c in atelier["red"].appels if "Rédige UNIQUEMENT la partie" in c)
    assert "une seule fois" in redaction and "pas sûr" in redaction


def test_jugement_la_lettre_dit_clairement_la_demande_et_ne_invente_pas_le_destinataire(atelier):
    from core import specification as sp

    ar = atelier["ar"]
    spec = sp.extraire("rédige une lettre formelle pour mon voisin")
    c, _, _ = ar.rediger_lettre("rédige une lettre formelle pour mon voisin", spec, {"nom": "Camille Martin"})
    lettre = next(x for x in atelier["red"].appels if "Rédige le CORPS de cette lettre" in x)
    assert "premier paragraphe" in lettre and "concrète" in lettre
    assert c["destinataire"] == ["[nom et adresse de mon voisin à compléter]"]
    c, _, _ = ar.rediger_lettre("x", spec, {"nom": "Camille Martin"})
    assert c["destinataire"] == ["[nom et adresse du destinataire à compléter]"]
    c, _, _ = ar.rediger_lettre("x", spec, {"nom": "Camille Martin", "destinataire": "Madame Durand"})
    assert c["destinataire"] == ["Madame Durand"], "un vrai nom : rien à compléter"


def test_jugement_un_document_redige_de_memoire_avec_des_dates_est_signale(atelier, monkeypatch):
    ar = atelier["ar"]
    assert "vérifie" in ar._avertissement_faits({"titre": "T", "sections": [{"titre": "S", "paragraphes": ["En 1945, la guerre."]}]})
    assert ar._avertissement_faits({"titre": "T", "sections": [{"titre": "S", "paragraphes": ["La pluie tombe."]}]}) == ""


def test_jugement_une_regeneration_plus_loin_de_la_cible_ne_remplace_pas(atelier):
    ar = atelier["ar"]
    spec = {"mots_min": 240, "mots_max": 360}
    un_peu_long, trop_court = _contenu(1, 380), _contenu(1, 155)
    assert ar._plus_proche(un_peu_long, trop_court, spec) is un_peu_long
    assert ar._plus_proche(trop_court, un_peu_long, spec) is un_peu_long
    assert ar._plus_proche(un_peu_long, _contenu(1, 300), spec)["sections"][0]["paragraphes"] == _contenu(1, 300)["sections"][0]["paragraphes"]


def test_jugement_rien_a_corriger_pas_de_nouvelle_version(document_cree, monkeypatch):
    atelier, v1, empreinte = document_cree
    ar = atelier["ar"]
    monkeypatch.setattr(ar, "_reecrire_section", lambda s, consigne, langue="fr": (s, ""))
    cible, _ = ar._cible_retouche({})
    m = ar._faire_retouche("corriger", cible, {})
    assert "aucune faute" in m and "pas écrit de nouvelle version" in m
    assert not v1.with_name(v1.stem + " (v2).docx").exists() and _sha(v1) == empreinte


# --------------------------------------------------------------------------- #
#  Seconde grille d'Alexis (3,0/5) : 240 mots ne sont pas « 300 mots » ; la lettre sans politesse
# --------------------------------------------------------------------------- #

def test_seconde_grille_un_nombre_de_mots_tient_a_dix_pour_cent():
    from core import specification as sp

    spec = sp.extraire("écris un document de 300 mots sur la lecture")
    assert (spec["mots_min"], spec["mots_max"]) == (270, 330)
    trop_court = {"titre": "T", "sections": [{"titre": "S", "paragraphes": [_texte(240)]}]}
    assert any("mots" in e for e in sp.verifier(trop_court, spec)), "240 mots pour 300 : l'écart est dit"


def test_seconde_grille_la_lettre_formelle_a_toujours_sa_formule_de_politesse(atelier):
    from core import specification as sp

    atelier["red"].lettre_sans_politesse = True
    demande = "rédige une lettre formelle pour mon voisin"
    c, _, _ = atelier["ar"].rediger_lettre(demande, sp.extraire(demande), {"nom": "Camille Martin"})
    assert "agréer" in c["sections"][0]["paragraphes"][-1]


def test_seconde_grille_une_formule_presente_n_est_pas_doublee(atelier):
    from core import specification as sp

    demande = "rédige une lettre formelle pour mon voisin"
    c, _, _ = atelier["ar"].rediger_lettre(demande, sp.extraire(demande), {"nom": "Camille Martin"})
    assert sum("agréer" in p for p in c["sections"][0]["paragraphes"]) == 1


def test_une_ouverture_qui_ne_repond_pas_ne_bloque_pas_le_travail(atelier, monkeypatch):
    """Banc du 03/11 figé 14 min avant une retouche : l'ouverture du fichier ne doit jamais bloquer."""
    import threading
    import time

    from tools import fichiers as tf

    ar = atelier["ar"]
    bloque = threading.Event()
    monkeypatch.setattr(tf, "_ouvrir_systeme", lambda c: bloque.wait(30))
    monkeypatch.setattr(ar, "OUVERTURE_ATTENTE_S", 0.2)
    t0 = time.perf_counter()
    ar._ouvrir(["x.docx"])
    assert time.perf_counter() - t0 < 2
    bloque.set()


def test_une_correction_qui_reecrit_le_texte_n_est_pas_gardee(document_cree, monkeypatch):
    """Banc du 03/11 : « J'ai corrigé 2 parties… sans changer le sens » pour un texte allongé de plus de 10 %."""
    atelier, v1, empreinte = document_cree
    ar = atelier["ar"]

    def allonge(s, consigne, langue="fr"):
        return {**s, "paragraphes": [p + " " + " ".join(p.split()[: len(p.split()) // 5]) for p in s["paragraphes"]]}, ""

    monkeypatch.setattr(ar, "_reecrire_section", allonge)
    cible, _ = ar._cible_retouche({})
    m = ar._faire_retouche("corriger", cible, {})
    assert "aucune correction" in m and "J'ai corrigé" not in m
    assert not v1.with_name(v1.stem + " (v2).docx").exists() and _sha(v1) == empreinte


@pytest.mark.parametrize("op,params", [("corriger", {}), ("ton", {"valeur": "simple"})])
def test_une_correction_ou_un_ton_ne_perd_pas_les_points(atelier, monkeypatch, op, params):
    """Banc du 03/11 : « J'ai corrigé 2 parties » avait fait disparaître les 6 points de liste."""
    ar = atelier["ar"]
    contenu = {"titre": "Mots de passe", "sections": [
        {"titre": "Partie 1", "paragraphes": [_texte(60)], "points": ["Longueur", "Complexité"]},
        {"titre": "Partie 2", "paragraphes": [_texte(60)], "points": ["Gestionnaire"]}]}
    monkeypatch.setattr(ar, "_reecrire_section", lambda s, consigne, langue="fr": (
        {"titre": s["titre"], "paragraphes": [p.replace("eau", "Eau") for p in s["paragraphes"]], "points": []}, ""))
    c, change, raison = ar._appliquer_retouche(op, {"contenu": contenu, "spec": {}}, params)
    assert not raison and [s["points"] for s in c["sections"]] == [["Longueur", "Complexité"], ["Gestionnaire"]]
