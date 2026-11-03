"""
Sprint Artefacts sur mesure / AS1 — la demande de la personne devient une SPÉCIFICATION explicite,
extraite sans modèle, puis VÉRIFIÉE sur le document produit.

    spec = extraire("fais-moi une lettre formelle pour mon propriétaire, une page, sans liste à puces")
    ecarts = verifier(contenu, spec)        # [] si tout est respecté, sinon des phrases à dire

Ce qui se vérifie par programme l'est : longueur (mots, lignes, pages estimées), parties imposées et
leur ordre, langue, tableau, sommaire, conclusion, introduction, listes à puces, titre. Le ton et le
public ne se vérifient pas par programme : ils sont transmis au modèle, et le rapport le dit.

Une page ≈ MOTS_PAR_PAGE mots (Calibri 11, titres compris) : c'est une ESTIMATION, dite comme telle.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

MOTS_PAR_PAGE = 420
_NOMBRES = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
            "neuf": 9, "dix": 10, "demi": 0.5}
_N = r"(\d+(?:[.,]\d+)?|une?|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)"


def plat(texte: str) -> str:
    t = unicodedata.normalize("NFD", (texte or "").lower().replace("’", "'"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _n(mot: str) -> float:
    mot = mot.replace(",", ".")
    try:
        return float(mot)
    except ValueError:
        return _NOMBRES.get(mot, 1)


GENRES = {
    "lettre": r"lettre(?:\s+de\s+motivation|\s+de\s+resiliation|\s+formelle)?|courrier|mail|e-mail|courriel",
    "fiche": r"fiche(?:\s+de\s+revision|\s+recapitulative|\s+pratique|\s+memo)?|aide-memoire|memo",
    "plan_de_cours": r"plan\s+de\s+cours|plan\s+de\s+(?:la\s+)?le[cç]on|deroule\s+de\s+cours|sequence\s+pedagogique",
    "note": r"note(?:\s+de\s+synthese|\s+d'information|\s+de\s+service)?",
    "compte_rendu": r"compte[ -]rendus?",
    "resume": r"resume|synthese",
    "rapport": r"rapport|expose",          # « dossier » : ambigu (un dossier de fichiers), écarté
    "document": r"document|texte|doc",
}

LANGUES = {"anglais": "en", "espagnol": "es", "allemand": "de", "italien": "it", "portugais": "pt", "francais": "fr"}
_STOP = {
    "fr": {"le", "la", "les", "de", "des", "et", "est", "un", "une", "que", "qui", "pour", "dans", "avec", "pas", "sur"},
    "en": {"the", "and", "is", "of", "to", "in", "that", "with", "for", "this", "are", "be", "it", "on", "as"},
    "es": {"el", "los", "las", "y", "es", "que", "en", "con", "para", "una", "por", "del", "se", "como", "su"},
    "de": {"der", "die", "das", "und", "ist", "nicht", "mit", "für", "auf", "ein", "eine", "zu", "den", "von", "sich"},
    "it": {"il", "lo", "gli", "e", "che", "di", "per", "una", "con", "non", "sono", "della", "nel", "come", "anche"},
    "pt": {"o", "os", "as", "e", "que", "de", "do", "da", "em", "um", "uma", "para", "com", "não", "por"},
}
TONS = {"formel": r"formel(?:le)?|soutenu|professionnel(?:le)?|officiel(?:le)?",
        "simple": r"simple|facile|accessible|clair|sans jargon|vulgaris[eé]",
        "enfant": r"pour (?:un|une|des) enfants?|pour (?:mon|ma) (?:fils|fille|petit|petite)|niveau (?:primaire|cm\d|ce\d)",
        "amical": r"amical(?:e)?|chaleureu(?:x|se)|decontracte|familier",
        "humour": r"drole|humour|humoristique"}
_PUBLICS = r"(?:mon|ma|mes|un|une|des|le|la|les|notre)\s+(?:prof(?:esseur)?s?|enseignant(?:e)?s?|client(?:e)?s?|patron(?:ne)?|" \
           r"chef|manager|responsable|directeur|directrice|equipe|collegues?|parents?|eleves?|etudiants?|jury|" \
           r"proprietaire|banque|assurance|mairie|employeur|recruteur|grand-mere|grand-pere|famille|amis?|voisins?)" \
           r"(?:\s+de\s+(?!la\b|le\b|l'|les\b)[\w-]+)?"


def extraire(phrase: str) -> dict:
    """La spécification de la demande. Les clés absentes ne sont pas des contraintes."""
    t = plat(phrase.strip())
    spec: dict[str, Any] = {}
    # Genre
    for genre, motif in GENRES.items():
        if re.search(rf"\b(?:{motif})\b", t):
            spec["genre"] = genre
            break
    # Format
    pdf, word = bool(re.search(r"\bpdf\b", t)), bool(re.search(r"\b(?:word|docx)\b", t))
    spec["formats"] = ["docx", "pdf"] if (pdf and word) else (["pdf"] if pdf else ["docx"])
    # Longueur
    m = re.search(rf"\b(?:en\s+|de\s+|d'environ\s+|environ\s+|pas\s+plus\s+de\s+|au\s+plus\s+|maximum\s+|max\s+|"
                  rf"moins\s+de\s+|au\s+moins\s+|minimum\s+|plus\s+de\s+)?{_N}\s+(?:mots)\b", t)
    if m:
        n = int(_n(m.group(1)))
        avant = t[max(0, m.start() - 20):m.start(1)]
        if re.search(r"moins de|pas plus de|au plus|maximum|max", avant):
            spec["mots_max"] = n
        elif re.search(r"au moins|minimum|plus de", avant):
            spec["mots_min"] = n
        else:
            spec["mots_min"], spec["mots_max"] = int(n * 0.9), int(n * 1.1)   # 240 mots ne sont pas « 300 mots »
    m = re.search(rf"\b(?:en\s+|sur\s+|de\s+|d'|tenir\s+(?:en|sur)\s+)?{_N}\s+pages?\b", t)
    if m and "mots_max" not in spec and "mots_min" not in spec:
        p = _n(m.group(1))
        spec["pages"] = p
        spec["mots_min"], spec["mots_max"] = int(p * MOTS_PAR_PAGE * 0.6), int(p * MOTS_PAR_PAGE * 1.15)
    elif re.search(r"\b(?:une|1)\s+demi[- ]page\b|\bune page maximum\b", t):
        spec["pages"] = 0.5
        spec["mots_min"], spec["mots_max"] = 100, int(0.5 * MOTS_PAR_PAGE * 1.2)
    m = re.search(rf"\ben\s+{_N}\s+lignes\b", t)
    if m:
        spec["lignes"] = int(_n(m.group(1)))
        spec["mots_max"] = spec["lignes"] * 18
    if not any(k in spec for k in ("mots_min", "mots_max")):
        if re.search(r"\b(?:court|courte|bref|breve|succinct|succincte|concis|concise|rapide)\b", t):
            spec["mots_max"] = 350
        elif re.search(r"\b(?:detaille|detaillee|long|longue|approfondi|approfondie|complet|complete)\b", t):
            spec["mots_min"] = 1200
    # Langue
    m = re.search(r"\ben\s+(anglais|espagnol|allemand|italien|portugais)\b", t)
    if m:
        spec["langue"] = LANGUES[m.group(1)]
    # Ton et public (transmis au modèle, non vérifiés par programme)
    tons = [nom for nom, motif in TONS.items() if re.search(rf"\b(?:{motif})\b", t)]
    if tons:
        spec["ton"] = tons
    m = re.search(rf"\b(?:pour|destine(?:e)?\s+a|a\s+l'attention\s+de|adresse(?:e)?\s+a)\s+({_PUBLICS})", t)
    if m:
        spec["public"] = m.group(1)
    # Structure imposée : « en 3 parties : introduction, les causes, conclusion »
    m = re.search(rf"\ben\s+{_N}\s+(?:parties|sections|chapitres)\b", t)
    if m:
        spec["nb_parties"] = int(_n(m.group(1)))
        liste = re.match(r"\s*[:(]\s*(?P<l>.+?)\s*(?:\)|$|[.;]|,?\s+(?:avec|sans|en\s+(?:pdf|word))\b)", t[m.end():])
        if liste:
            # Les titres tels que la personne les a écrits (accents, majuscules), si l'alignement le permet.
            brut = phrase.strip().replace("’", "'")
            a, b = m.end() + liste.start("l"), m.end() + liste.end("l")
            source = brut[a:b] if len(brut) == len(t) else liste.group("l")
            noms = [x.strip(" .") for x in re.split(r",|\s+puis\s+|\s+et\s+", source) if x.strip(" .")]
            if len(noms) >= 2:
                spec["parties"] = [n[0].upper() + n[1:] for n in noms]
    # Éléments demandés / interdits
    def demande(motif):
        return bool(re.search(rf"\b(?:avec|y compris|comprenant|qui contient|contenant|et)\s+(?:un|une|des|le|la|les|l')?\s*(?:{motif})", t))

    def interdit(motif):
        return bool(re.search(rf"\b(?:sans|pas de|aucun|aucune|ni)\s+(?:de\s+|d')?(?:un\s+|une\s+|les\s+|le\s+|la\s+)?(?:{motif})", t))

    for cle, motif in (("tableau", r"tableaux?"), ("sommaire", r"sommaire|table des matieres"),
                       ("conclusion", r"conclusion"), ("introduction", r"introduction"),
                       ("puces", r"listes?\s+a\s+puces|puces|listes?|enumerations?")):
        if interdit(motif):
            spec[cle] = False
        elif demande(motif) or (cle == "tableau" and re.search(r"\bsous forme de tableau\b|\ben tableau\b", t)):
            spec[cle] = True
    # Titre imposé : « intitulé “X” », « avec le titre X », « titre : X »
    m = re.search(r"(?:intitule(?:e)?|avec (?:le|comme) titre|titre\s*:|qui s'appelle)\s*[«\"“]?\s*(?P<x>[^»\"”,.;]+)", t)
    if m:
        debut = m.start("x")
        brut = phrase.strip().replace("’", "'")
        spec["titre"] = brut[debut:debut + len(m.group("x"))].strip(" «»\"“”") if len(brut) == len(t) else m.group("x").strip()
    return spec


# --------------------------------------------------------------------------- #
#  Vérification du document produit
# --------------------------------------------------------------------------- #

def _mots(texte: str) -> int:
    return len(re.findall(r"[\wÀ-ÿ'’-]+", texte or ""))


def textes(contenu: dict) -> list[str]:
    out = [contenu.get("titre", "")]
    for s in contenu.get("sections", []):
        out.append(s.get("titre", ""))
        out += list(s.get("paragraphes", [])) + list(s.get("points") or [])
        for ligne in (s.get("tableau") or {}).get("lignes") or []:
            out += [str(c) for c in ligne]
    out += list(contenu.get("points_cles") or [])
    return [x for x in out if isinstance(x, str)]


def mots(contenu: dict) -> int:
    return sum(_mots(x) for x in textes(contenu))


def langue(texte: str) -> Optional[str]:
    m = [x for x in re.findall(r"[a-zàâäéèêëîïôöùûüçñßü']+", (texte or "").lower())]
    if len(m) < 20:
        return None
    scores = {lg: sum(x in mots_lg for x in m) / len(m) for lg, mots_lg in _STOP.items()}
    meilleure = max(scores, key=scores.get)
    return meilleure if scores[meilleure] >= 0.06 else None


def _proche(a: str, b: str) -> bool:
    a, b = plat(a).strip(), plat(b).strip()
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    ma, mb = set(re.findall(r"\w{4,}", a)), set(re.findall(r"\w{4,}", b))
    return bool(ma) and len(ma & mb) / len(ma) >= 0.5


def verifier(contenu: dict, spec: dict, rendu: Optional[dict] = None) -> list[str]:
    """Les écarts entre le document et la spécification, en phrases à dire. [] : tout est tenu.
    rendu : ce que le moteur a vraiment écrit (sommaire, tableaux) — décidé par lui, pas par le modèle."""
    ecarts = []
    n = mots(contenu)
    pages = spec.get("pages")
    if spec.get("mots_max") and n > spec["mots_max"]:
        ecarts.append(f"il fait {n} mots, pour {spec['mots_max']} au plus" +
                      (f" (environ {round(n / MOTS_PAR_PAGE, 1)} page(s) au lieu de {pages})" if pages else ""))
    if spec.get("mots_min") and n < spec["mots_min"]:
        ecarts.append(f"il fait {n} mots, pour {spec['mots_min']} au moins" +
                      (f" (environ {round(n / MOTS_PAR_PAGE, 1)} page(s) au lieu de {pages})" if pages else ""))
    sections = contenu.get("sections", [])
    titres = [s.get("titre", "") for s in sections]
    if spec.get("parties"):
        manquantes = [p for p in spec["parties"] if not any(_proche(p, t) for t in titres)]
        if manquantes:
            ecarts.append("parties absentes : " + ", ".join(f"« {p} »" for p in manquantes))
        else:
            ordre = [next(k for k, t in enumerate(titres) if _proche(p, t)) for p in spec["parties"]]
            if ordre != sorted(ordre):
                ecarts.append("les parties ne sont pas dans l'ordre demandé")
    elif spec.get("nb_parties") and len(sections) != spec["nb_parties"]:
        ecarts.append(f"il a {len(sections)} parties, pour {spec['nb_parties']} demandées")
    if spec.get("langue"):
        lg = langue(" ".join(textes(contenu)))
        if lg and lg != spec["langue"]:
            ecarts.append(f"il n'est pas rédigé dans la langue demandée ({spec['langue']})")
    if spec.get("tableau") and not any((s.get("tableau") or {}).get("lignes") for s in sections):
        ecarts.append("il n'y a pas de tableau")
    if spec.get("tableau") is False and any((s.get("tableau") or {}).get("lignes") for s in sections):
        ecarts.append("il contient un tableau")
    sommaire = (rendu or {}).get("sommaire")
    if spec.get("sommaire") is False and sommaire:
        ecarts.append("il contient un sommaire")
    if spec.get("sommaire") and sommaire is False:
        ecarts.append("il n'a pas de sommaire")
    a_conclusion = any(re.search(r"\bconclusion\b|\ben resume\b|\bpour conclure\b", plat(t)) for t in titres)
    if spec.get("conclusion") and not a_conclusion:
        ecarts.append("il n'a pas de conclusion")
    if spec.get("conclusion") is False and a_conclusion:
        ecarts.append("il a une conclusion")
    a_intro = any(re.search(r"\bintroduction\b", plat(t)) for t in titres)
    if spec.get("introduction") and not a_intro:
        ecarts.append("il n'a pas d'introduction")
    if spec.get("introduction") is False and a_intro:
        ecarts.append("il a une introduction")
    a_puces = any(s.get("points") for s in sections) or bool(contenu.get("points_cles"))
    if spec.get("puces") is False and a_puces:
        ecarts.append("il contient des listes à puces")
    if spec.get("titre") and plat(contenu.get("titre", "")).strip() != plat(spec["titre"]).strip():
        ecarts.append(f"son titre n'est pas « {spec['titre']} »")
    return ecarts


def appliquer(contenu: dict, spec: dict) -> dict:
    """Ce que le MOTEUR peut tenir lui-même, sans le modèle : titre imposé, puces interdites
    (fondues dans le paragraphe), conclusion ou introduction interdites (retirées)."""
    import copy

    c = copy.deepcopy(contenu)
    if spec.get("titre"):
        c["titre"] = spec["titre"]
    if spec.get("puces") is False:
        for s in c.get("sections", []):
            if s.get("points"):
                s.setdefault("paragraphes", []).append(" ".join(p.rstrip(" .") + "." for p in s["points"]))
                s["points"] = []
        c["points_cles"] = []
    for cle, motif in (("conclusion", r"\bconclusion\b|\bpour conclure\b"), ("introduction", r"\bintroduction\b")):
        if spec.get(cle) is False and len(c.get("sections", [])) > 1:
            c["sections"] = [s for s in c["sections"] if not re.search(motif, plat(s.get("titre", "")))]
    if spec.get("tableau") is False:
        for s in c.get("sections", []):
            s.pop("tableau", None)
    return c


def consignes_en_texte(spec: dict) -> str:
    """Les consignes, en clair, pour le modèle (ce qu'il doit tenir)."""
    out = []
    if spec.get("mots_max") and spec.get("mots_min"):
        out.append(f"entre {spec['mots_min']} et {spec['mots_max']} mots au total")
    elif spec.get("mots_max"):
        out.append(f"{spec['mots_max']} mots au plus au total")
    elif spec.get("mots_min"):
        out.append(f"au moins {spec['mots_min']} mots au total")
    if spec.get("lignes"):
        out.append(f"{spec['lignes']} lignes au plus")
    if spec.get("langue") and spec["langue"] != "fr":
        nom = next(k for k, v in LANGUES.items() if v == spec["langue"])
        out.append(f"rédigé ENTIÈREMENT en {nom}")
    for ton in spec.get("ton") or []:
        out.append({"formel": "ton formel et soutenu", "simple": "langage simple, sans jargon",
                    "enfant": "adapté à un enfant (phrases courtes, mots simples)", "amical": "ton amical et chaleureux",
                    "humour": "une touche d'humour"}[ton])
    if spec.get("public"):
        out.append(f"destiné à : {spec['public']}")
    if spec.get("tableau"):
        out.append("contient un tableau")
    if spec.get("puces") is False:
        out.append("aucune liste à puces")
    if spec.get("puces"):
        out.append("avec des listes à puces")
    return " ; ".join(out)
