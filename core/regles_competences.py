"""
Sprint Compétences 1 — les règles déterministes qui reconnaissent les nouvelles demandes : l'heure, les
minuteurs et rappels, le son, la luminosité et les écrans, le Bluetooth, la musique.

Appelées en tête de `IntentClassifier.classify`, sur le texte « plat » (minuscules, sans accents).
Elles rendent (verbe, paramètres) pour la catégorie « competence », None sinon. Chaque règle exige
l'objet de la demande (« son », « volume », « luminosité », « écran », « bluetooth », « musique »,
« minuteur », « rappel »…) : un verbe seul ne suffit jamais (« mets Steam au premier plan », « lance
Discord » restent aux fenêtres et aux applications).

Ce qu'Atlas ne pilote pas reste honnête : « éteins la lumière » (une lampe), « baisse le son de ta
voix », « mets un rappel dans mon téléphone ».
"""

from __future__ import annotations

import re
from typing import Optional

from core import horloge

_LEAD = (r"^(?:atlas[\s,]*)?(?:s'il te plait[\s,]*)?(?:(?:ok|bon|alors|allez|et)[\s,]+)?"
         r"(?:(?:tu peux|peux-tu|pourrais-tu|tu pourrais|est-ce que tu peux|est-ce que tu pourrais|"
         r"je voudrais que tu|j'aimerais que tu|je veux que tu|il faut)\s+(?:me\s+|m')?)?")
_FIN = r"(?:\s+(?:s'il te plait|stp|svp|merci|maintenant|un peu|stp merci))*\s*$"


def _m(motif: str, plain: str):
    return re.match(_LEAD + "(?:" + motif + ")" + _FIN, plain)


def _nombre(texte: str) -> Optional[int]:
    m = re.search(r"\b(\d{1,3})\s*(?:%|pour ?cents?|pourcents?)?", texte)
    if m and 0 <= int(m.group(1)) <= 100:
        return int(m.group(1))
    return None


def _brut_depuis(raw: str, plain: str, debut: int, fin: Optional[int] = None, nettoyer: bool = True) -> str:
    """Le morceau de la phrase d'origine (casse et accents) qui correspond à plain[debut:fin]."""
    r = raw.strip().replace("’", "'").rstrip(" .!?")
    morceau = r[debut:fin] if len(r) == len(plain) else plain[debut:fin]
    return morceau.strip() if nettoyer else morceau


# --------------------------------------------------------------------------- #
#  Minuteurs et rappels
# --------------------------------------------------------------------------- #

_MOMENTS = [
    r"\bdans\s+(?:une?\s+(?:demi[- ]heure|quart\s+d'heure)|" + horloge._NOMBRE + r"\s*(?:secondes?|sec|minutes?|min|mn|heures?|h|jours?|semaines?)"
    r"(?:\s*(?:et\s+)?\d{1,2}(?:\s*(?:minutes?|min))?)?(?:\s+et\s+demie?)?)",
    r"\b(?:apres[- ]demain|demain)(?:\s+(?:matin|soir|apres[- ]midi))?",
    r"\b(?:aujourd'hui|ce\s+soir|ce\s+matin|cet\s+apres[- ]midi|cette\s+nuit)",
    r"\b(?:tous\s+les|toutes\s+les|chaque)\s+(?:jours?|(?:(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)s?"
    r"(?:\s*(?:,|et)\s*(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)s?)*))",
    r"\ben\s+semaine\b|\ble\s+week-?end\b|\bdu\s+lundi\s+au\s+vendredi\b",
    r"\b(?:le\s+)?(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)(?:\s+prochain)?\b",
    r"\ble\s+(?:\d{1,2}|1er|premier)\s+(?:" + "|".join(horloge.MOIS) + r")(?:\s+\d{4})?",
    r"\b(?:a|vers|pour)\s+\d{1,2}\s*(?:h|heures?|:)\s*(?:\d{2})?(?:\s+et\s+(?:demie?|quart))?"
    r"(?:\s+(?:du\s+matin|du\s+soir|de\s+l'apres[- ]midi))?",
    r"\b(?:a|vers)\s+(?:midi|minuit)(?:\s+et\s+demie?)?",
]
_MOMENT_RE = re.compile("|".join(f"(?:{m})" for m in _MOMENTS))

_RAPPEL_DEBUT = re.compile(
    _LEAD + r"(?:rappelle[- ]moi|rappeler|fais[- ]moi\s+penser|previens[- ]moi|n'oublie\s+pas\s+de\s+me\s+rappeler|"
    r"(?:mets|met|cree|ajoute|programme|enregistre)(?:[- ]moi)?\s+un\s+rappel(?:\s+pour)?)\b(?P<reste>.*)$")
_PAS_ICI = re.compile(r"\b(?:dans|sur)\s+(?:mon|le|ton)\s+(?:telephone|portable|smartphone|iphone|agenda|calendrier)\b")


def _sans_moments(raw: str, plain: str, debut: int) -> tuple[str, str]:
    """(texte du rappel sans les moments, avec sa préposition « de … ») depuis plain[debut:]."""
    reste_plain = plain[debut:]
    brut = _brut_depuis(raw, plain, debut, nettoyer=False)          # même longueur que reste_plain
    garde, k = [], 0
    for a, b in (m.span() for m in _MOMENT_RE.finditer(reste_plain)):
        garde.append(brut[k:a])
        k = b
    garde.append(brut[k:])
    quoi = re.sub(r"\s+", " ", "".join(garde)).strip(" ,")
    quoi = re.sub(r"^(?:qu'il\s+faut|qu'il\s+faudra)\s+", "de ", quoi)
    texte = re.sub(r"^(?:de\s+|d'|que\s+|qu')", "", quoi, flags=re.IGNORECASE).strip()
    return texte, quoi


def _rappels(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    # Lister
    if re.search(r"\b(?:quels?\s+sont|liste|lister|montre|affiche|donne|dis)[- ](?:moi\s+)?(?:mes|les)\s+(?:rappels|minuteurs)\b",
                 plain) or re.fullmatch(r"(?:et\s+)?mes\s+(?:rappels|minuteurs)\s*\??", plain) or \
            re.search(r"\bj'ai\s+(?:quels|des|combien de)\s+(?:rappels|minuteurs)\b|\bqu'est-ce\s+que\s+j'ai\s+comme\s+rappels\b",
                      plain):
        return "rappel_lister", {"minuteurs_seulement": "minuteur" in plain}
    if re.search(r"\b(?:il\s+reste\s+combien(?:\s+de\s+temps)?|combien\s+de\s+temps\s+(?:il\s+)?reste|ou\s+en\s+est)\b.*\b(?:minuteur|timer)\b",
                 plain):
        return "rappel_lister", {"minuteurs_seulement": True}
    # Annuler
    m = re.match(_LEAD + r"(?:annule|annuler|supprime|supprimer|efface|effacer|enleve|retire|oublie|arrete|stoppe|coupe)\s+"
                 r"(?:le|mon|ce|la|les|mes|tous\s+mes|tous\s+les)\s+(?P<sorte>rappels?|minuteurs?|timers?)"
                 r"(?:\s+(?:de|du|d'|des|pour|qui|sur|concernant|a\s+propos\s+de)\s*(?P<q>.+?))?" + _FIN, plain)
    if m:
        q = m.group("q") or ""
        mid = re.fullmatch(r"#?(\d+)", q.strip())
        sorte = "minuteur" if m.group("sorte").startswith(("minuteur", "timer")) else "rappel"
        if mid:
            return "rappel_annuler", {"id": int(mid.group(1)), "sorte": sorte}
        quoi = _brut_depuis(raw, plain, m.start("q"), m.end("q")) if m.group("q") else ""
        return "rappel_annuler", {"quoi": quoi, "sorte": sorte}
    m = re.match(_LEAD + r"annule\s+le\s+rappel\s+#(\d+)\s*$", plain)
    if m:
        return "rappel_annuler", {"id": int(m.group(1))}
    # Minuteur
    m = re.match(_LEAD + r"(?:mets|met|mettre|lance|lancer|demarre|demarrer|programme|programmer|regle|regler|fais|cree|creer|"
                 r"ajoute|active|declenche)(?:[- ]moi)?\s+(?:un|une|le|mon)\s+(?:minuteur|timer|compte\s+a\s+rebours|chrono)\b"
                 r"(?P<reste>.*)$", plain) or re.match(r"^(?:atlas[\s,]*)?(?:minuteur|timer)\b(?P<reste>.*)$", plain)
    if m:
        reste = m.group("reste")
        t = re.search(r"\b(?:pour|de)\s+(?!" + horloge._NOMBRE + r"\b|une?\s+(?:demi|quart)|(?:\d+\s*)?(?:minutes?|heures?|secondes?)\b)(?P<t>.+)$",
                      reste)
        texte = _brut_depuis(raw, plain, m.start("reste") + t.start("t")).rstrip(" .!?") if t else ""
        texte = _MOMENT_RE.sub("", texte).strip(" ,")
        return "rappel_creer", {"sorte": "minuteur", "texte": texte, "phrase": plain,
                                "duree_texte": reste[:t.start()] if t else reste}
    # Rappel
    m = _RAPPEL_DEBUT.match(plain)
    if m and not _PAS_ICI.search(plain):
        reste = m.group("reste").strip()
        commence = re.match(r"^(?:de\b|d'|que\b|qu'|dans\b|demain|apres[- ]demain|ce\s+soir|ce\s+matin|cet\s+apres|aujourd'hui|"
                            r"a\s+\d|a\s+midi|a\s+minuit|vers\s+\d|tous\s+les|toutes\s+les|chaque|le\s+\d|le\s+1er|"
                            r"(?:le\s+)?(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)|en\s+semaine)", reste)
        if not commence and reste:
            return None                       # « rappelle-moi le code du portail » : la mémoire
        texte, quoi = _sans_moments(raw, plain, m.start("reste"))
        return "rappel_creer", {"sorte": "rappel", "texte": texte, "quoi_brut": quoi, "phrase": plain}
    return None


# --------------------------------------------------------------------------- #
#  Le son
# --------------------------------------------------------------------------- #

_OBJ_SON = r"(?:le\s+|du\s+)?(?:son|volume)"
_APP_SON = r"(?:\s+(?:de|du|d'|des|sur)\s*(?P<app>(?!ta\s|ma\s|la\s+voix|l'ordi|l'ordinateur|mon\s+pc|du\s+pc|pc\b|l'ecran)[\w' .&-]+?))?"


def _son(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    if not re.search(r"\b(?:son|volume|sourdine|muet|moins\s+fort|plus\s+fort)\b", plain):
        return None
    if re.search(r"\b(?:ta|votre)\s+voix\b|\bparle\s+(?:moins|plus)\s+fort\b|\bvolume\s+de\s+(?:ta|la)\s+voix\b", plain):
        return "__unsupported__", {}
    if re.search(r"\b(?:quel\s+est\s+le\s+(?:volume|niveau\s+du\s+son)|le\s+(?:son|volume)\s+est\s+a\s+combien|"
                 r"a\s+combien\s+est\s+le\s+(?:son|volume)|c'est\s+quoi\s+le\s+volume|le\s+volume\s+actuel)\b", plain):
        return "son_regler", {"action": "etat"}

    def app(m) -> Optional[str]:
        if not m or not m.groupdict().get("app"):
            return None
        a = _brut_depuis(raw, plain, m.start("app"), m.end("app"))
        a = re.sub(r"^(?:l'|le\s+|la\s+|les\s+)", "", a, flags=re.IGNORECASE).strip()
        return a or None

    m = _m(r"(?:coupe|couper|mute|muter|desactive|desactiver|enleve|enlever|retire)\s+" + _OBJ_SON + _APP_SON, plain) or \
        _m(r"(?:mets|met|mettre)\s+(?:le\s+son\s+)?(?:en\s+sourdine|en\s+muet|sur\s+muet)", plain) or \
        _m(r"(?:mets|met|mettre)\s+(?P<app>[\w' .&-]+?)\s+en\s+(?:sourdine|muet)", plain)
    if m:
        return "son_regler", {"action": "couper", "programme": app(m)}
    m = _m(r"(?:remets|remettre|retablis|retablir|reactive|reactiver|active|activer|rallume|rallumer|unmute|demute|"
           r"enleve\s+la\s+sourdine\s+(?:du\s+son)?|remets\s+le\s+son\s+en\s+marche)\s*" + r"(?:" + _OBJ_SON + r")?" + _APP_SON,
           plain)
    if m and re.search(r"\b(?:son|volume|sourdine)\b", plain) and not _nombre(plain):
        return "son_regler", {"action": "retablir", "programme": app(m)}
    m = _m(r"(?:mets|met|mettre|remets|remettre|regle|regler|ajuste|ajuster|fixe|fixer|passe|passer|monte|baisse)\s+" + _OBJ_SON + _APP_SON +
           r"\s+(?:a|au|sur)\s+(?P<n>\d{1,3}\s*(?:%|pour ?cents?|pourcents?)?|(?:au\s+)?max(?:imum)?|(?:au\s+)?min(?:imum)?|fond)", plain) or \
        _m(r"(?:le\s+)?(?:son|volume)" + _APP_SON + r"\s+(?:a|au)\s+(?P<n>\d{1,3}\s*(?:%|pour ?cents?)?|max(?:imum)?|min(?:imum)?)", plain)
    if m:
        n = m.group("n")
        niveau = 100 if n.startswith(("max", "au max", "fond")) else 0 if n.startswith(("min", "au min")) else _nombre(n)
        if niveau is None:
            return None
        return "son_regler", {"action": "regler", "niveau": niveau, "programme": app(m)}
    m = _m(r"(?:monte|monter|augmente|augmenter|hausse|hausser|leve|lever|remonte|remonter)\s+(?:un\s+peu\s+)?" + _OBJ_SON + _APP_SON,
           plain) or _m(r"(?:mets|met|mettre|parle)\s+(?:le\s+son\s+)?plus\s+fort", plain) or \
        _m(r"(?:plus\s+fort|monte\s+le\s+son|volume\s+(?:plus|\+))", plain)
    if m:
        return "son_regler", {"action": "monter", "programme": app(m)}
    m = _m(r"(?:baisse|baisser|diminue|diminuer|reduis|reduire|descends|descendre|rabaisse)\s+(?:un\s+peu\s+)?" + _OBJ_SON + _APP_SON,
           plain) or _m(r"(?:mets|met|mettre)\s+(?:le\s+son\s+)?moins\s+fort", plain) or \
        _m(r"(?:moins\s+fort|volume\s+(?:moins|-))", plain)
    if m:
        return "son_regler", {"action": "baisser", "programme": app(m)}
    return None


# --------------------------------------------------------------------------- #
#  La luminosité et les écrans
# --------------------------------------------------------------------------- #

_ECRAN_N = r"(?:\s+(?:de|sur|du)\s+(?:l'|le\s+)?(?:ecran|moniteur)\s*(?P<e>\d|un|deux|trois|principal|secondaire)|" \
           r"\s+du\s+(?P<e2>premier|deuxieme|second|troisieme)\s+(?:ecran|moniteur))?"
_RANGS = {"1": 1, "un": 1, "premier": 1, "principal": 1, "2": 2, "deux": 2, "deuxieme": 2, "second": 2,
          "secondaire": 2, "3": 3, "trois": 3, "troisieme": 3}


def _ecran(m) -> Optional[int]:
    if not m:
        return None
    v = m.groupdict().get("e") or m.groupdict().get("e2")
    return _RANGS.get(v) if v else None


def _lumiere(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    # Veille de l'affichage, et RIEN d'autre (jamais l'ordinateur)
    sans_possesseur = re.sub(r"\s+(?:du\s+pc|de\s+l'ordinateur|de\s+l'ordi|de\s+mon\s+pc)\b", "", plain)
    if re.search(r"\b(?:ecrans?|moniteurs?)\b", plain) and \
            not re.search(r"\b(?:pc|ordinateur|ordi|session|systeme)\b", sans_possesseur):
        if _m(r"(?:eteins|eteindre|eteint|coupe|couper)\s+(?:l'|les\s+|mon\s+|mes\s+|le\s+|ton\s+)?"
              r"(?:ecrans?|moniteurs?)(?:\s+en\s+veille)?(?:\s+(?:du\s+pc|de\s+l'ordinateur|de\s+l'ordi|de\s+mon\s+pc))?",
              plain) or \
                _m(r"(?:mets|met|mettre)\s+(?:l'|les\s+|mon\s+|mes\s+|le\s+)?(?:ecrans?|moniteurs?)\s+en\s+veille", plain) or \
                _m(r"(?:veille\s+(?:des|de\s+l'|de\s+mes)\s+ecrans?|ecrans?\s+en\s+veille)", plain):
            return "ecrans_veille", {}
    if not re.search(r"\b(?:luminosite|lumineux|lumineuse|eclaircis|assombris|eclaire)\b", plain) and \
            not re.search(r"\blumiere\s+de\s+l'ecran\b", plain):
        return None
    if re.search(r"\b(?:quelle\s+est\s+la\s+luminosite|la\s+luminosite\s+est\s+a\s+combien|a\s+combien\s+est\s+la\s+luminosite|"
                 r"luminosite\s+actuelle)\b", plain):
        return "luminosite_regler", {"action": "etat"}
    obj = r"(?:la\s+)?(?:luminosite|lumiere)(?:\s+de\s+l'ecran|\s+des\s+ecrans|\s+de\s+mes\s+ecrans)?"
    m = _m(r"(?:mets|met|mettre|regle|regler|ajuste|ajuster|fixe|fixer|passe|passer|monte|baisse)\s+" + obj + _ECRAN_N +
           r"\s+(?:a|au|sur)\s+(?P<n>\d{1,3}\s*(?:%|pour ?cents?)?|(?:au\s+)?max(?:imum)?|(?:au\s+)?min(?:imum)?|fond)", plain) or \
        _m(r"(?:la\s+)?luminosite" + _ECRAN_N + r"\s+(?:a|au)\s+(?P<n>\d{1,3}\s*(?:%|pour ?cents?)?|max(?:imum)?|min(?:imum)?)", plain)
    if m:
        n = m.group("n")
        niveau = 100 if n.startswith(("max", "au max", "fond")) else 0 if n.startswith(("min", "au min")) else _nombre(n)
        if niveau is None:
            return None
        return "luminosite_regler", {"action": "regler", "niveau": niveau, "ecran": _ecran(m)}
    m = _m(r"(?:monte|monter|augmente|augmenter|hausse|hausser|remonte)\s+(?:un\s+peu\s+)?" + obj + _ECRAN_N, plain) or \
        _m(r"(?:eclaircis|eclaircir|eclaire)\s+(?:l'|les\s+)?ecrans?", plain) or \
        _m(r"(?:mets|met|rends)\s+(?:l'|les\s+)?ecrans?\s+plus\s+lumineux", plain)
    if m:
        return "luminosite_regler", {"action": "monter", "ecran": _ecran(m)}
    m = _m(r"(?:baisse|baisser|diminue|diminuer|reduis|reduire|descends)\s+(?:un\s+peu\s+)?" + obj + _ECRAN_N, plain) or \
        _m(r"(?:assombris|assombrir)\s+(?:l'|les\s+)?ecrans?", plain) or \
        _m(r"(?:mets|met|rends)\s+(?:l'|les\s+)?ecrans?\s+moins\s+lumineux", plain)
    if m:
        return "luminosite_regler", {"action": "baisser", "ecran": _ecran(m)}
    return None


# --------------------------------------------------------------------------- #
#  Le Bluetooth
# --------------------------------------------------------------------------- #

_APPAREILS = r"(?:casque|ecouteurs|enceinte|airpods|buds|oreillettes|haut-parleurs?|jbl|bose|sony|manette|souris|clavier)"


def _bluetooth(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    if "bluetooth" in plain:
        if re.search(r"\b(?:est-ce\s+que\s+le\s+bluetooth\s+est|le\s+bluetooth\s+est(?:-il)?\s+(?:active|allume|actif|on)|"
                     r"etat\s+du\s+bluetooth|le\s+bluetooth\s+est\s+comment)\b", plain) or \
                re.fullmatch(r"(?:et\s+)?le\s+bluetooth\s*\??", plain):
            return "bluetooth_regler", {"action": "etat"}
        if _m(r"(?:active|activer|allume|allumer|demarre|demarrer|lance|lancer|mets|mettre|remets|remettre|rallume|rallumer|"
              r"reactive|reactiver)\s+(?:le\s+)?bluetooth(?:\s+en\s+marche)?", plain) or _m(r"bluetooth\s+on", plain):
            return "bluetooth_regler", {"allume": True}
        if _m(r"(?:desactive|desactiver|eteins|eteindre|coupe|couper|arrete|arreter|stoppe|stopper|enleve)\s+(?:le\s+)?bluetooth",
              plain) or _m(r"bluetooth\s+off", plain):
            return "bluetooth_regler", {"allume": False}
    m = _m(r"(?:connecte|connecter|reconnecte|reconnecter|branche|brancher|appaire|appairer|associe|associer)(?:[- ]moi)?\s+"
           r"(?P<nom>.+?)(?:\s+(?:en|au|par)\s+bluetooth)?", plain)
    if m and (re.search(r"\b" + _APPAREILS + r"\b", m.group("nom")) or "bluetooth" in plain):
        nom = _brut_depuis(raw, plain, m.start("nom"), m.end("nom"))
        nom = re.sub(r"^(?:mon|ma|mes|le|la|les|l')\s*", "", nom, flags=re.IGNORECASE).strip()
        return "bluetooth_connecter", {"nom": nom}
    return None


# --------------------------------------------------------------------------- #
#  La musique
# --------------------------------------------------------------------------- #

_SERVICE = r"(?P<s>spotify|deezer|apple\s+music|itunes|youtube\s+music|yt\s+music|youtube)"
_MEDIA = r"(?:la\s+)?(?:musique|lecture|chanson|morceau|piste|video|son\s+de\s+la\s+video|titre)"
_PAS_DE_LA_MUSIQUE = re.compile(r"^(?:son|volume|luminosite|lumiere|bluetooth|wifi|minuteur|rappel|pause|texte|temps|ordre|"
                                r"cote|place|ecran|pc|ordinateur|note|alarme|fond d'ecran|mode|premier plan)\b")


def _musique(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    # Le service préféré
    m = re.match(r"^(?:atlas[\s,]*)?(?:(?:maintenant|desormais)[\s,]+)?(?:j'utilise|j'ecoute\s+sur|je\s+suis\s+sur|"
                 r"(?:mon\s+service\s+(?:de\s+musique\s+)?|pour\s+la\s+musique\s*,?\s*)(?:c'est|est|ce\s+sera)|"
                 r"utilise|passe\s+(?:sur|a)|change\s+pour)\s+" + _SERVICE +
                 r"(?:\s+(?:maintenant|desormais|pour\s+la\s+musique|a\s+la\s+place|plutot))*\s*$", plain)
    if m:
        return "musique_service", {"service": m.group("s")}
    if re.search(r"\bquel\s+service\s+de\s+musique\b", plain):
        return "musique_service", {"action": "lire"}
    # « mets Daft Punk — service : Deezer » (réponse à la question du service)
    m = re.match(r"^mets\s+(?P<q>.+?)\s+—\s+service\s*:\s*(?P<d>.*)$", plain)
    if m:
        d = m.group("d").strip()
        return "musique_chercher", {"recherche": _brut_depuis(raw, plain, m.start("q"), m.end("q")),
                                    "service_dit": d if d not in ("", "navigateur", "le navigateur") else None,
                                    "web": d in ("navigateur", "le navigateur")}
    # Commandes universelles
    if re.search(r"\b(?:qu'est-ce\s+qui\s+(?:passe|joue)(?:\s+en\s+ce\s+moment|\s+la)?(?:\s+comme\s+(?:musique|chanson))?|"
                 r"c'est\s+quoi\s+(?:cette|ce)\s+(?:musique|chanson|morceau|titre)|"
                 r"c'est\s+quoi\s+la\s+(?:musique|chanson)\s+qui\s+passe|"
                 r"quelle\s+est\s+(?:cette|la)\s+(?:musique|chanson)(?:\s+qui\s+passe)?|qu'est-ce\s+que\s+j'ecoute|"
                 r"quel\s+est\s+(?:ce|le)\s+morceau(?:\s+qui\s+passe)?|c'est\s+qui\s+qui\s+chante)\s*\??$", plain):
        return "musique_commande", {"commande": "quoi"}
    if _m(r"(?:mets|met|mettre)\s+(?:" + _MEDIA + r"\s+)?en\s+pause|pause(?:\s+" + _MEDIA + r")?|"
          r"(?:arrete|arreter|stoppe|stopper|coupe|couper)\s+(?:la\s+musique|la\s+lecture|la\s+chanson|le\s+morceau)", plain):
        return "musique_commande", {"commande": "pause"}
    if _m(r"(?:reprends|reprendre|relance|relancer|remets|remettre|continue|continuer)\s+(?:la\s+musique|la\s+lecture|"
          r"la\s+chanson|le\s+morceau|la\s+video)|lecture|play|(?:enleve|retire)\s+la\s+pause", plain):
        return "musique_commande", {"commande": "lecture"}
    if _m(r"(?:passe\s+(?:a\s+la|au|la|le|cette)?\s*|mets\s+(?:la|le)\s+|joue\s+(?:la|le)\s+)?(?:chanson|piste|morceau|titre|musique)\s+"
          r"suivante?|(?:chanson|piste|morceau|titre)\s+d'apres|suivante?|next|skip|passe\s+(?:la|cette)\s+(?:chanson|musique|piste)|"
          r"change\s+de\s+(?:chanson|musique|morceau)", plain):
        return "musique_commande", {"commande": "suivant"}
    if _m(r"(?:reviens\s+(?:a\s+la|au)|passe\s+(?:a\s+la|au)|remets\s+(?:la|le)|mets\s+(?:la|le)|joue\s+(?:la|le))?\s*"
          r"(?:chanson|piste|morceau|titre|musique)\s+(?:precedente?|d'avant)|precedente?|previous", plain):
        return "musique_commande", {"commande": "precedent"}
    # Chercher et jouer
    m = re.match(_LEAD + r"(?:mets|met|mettre|joue|jouer|passe|passer|lance|lancer|ecoute|ecouter|fais\s+jouer)(?:[- ]moi|[- ]nous)?\s+"
                 r"(?P<q>.+?)(?:\s+(?:sur|avec|dans|via)\s+" + _SERVICE + r")?(?P<nav>\s+dans\s+le\s+navigateur)?" + _FIN, plain)
    if not m:
        return None
    q_plain, service = m.group("q"), m.group("s")
    explicite = bool(service)
    musique = re.match(r"^(?:de\s+la\s+|la\s+|un\s+peu\s+de\s+)?musique(?:\s+(?:de|d')\s*(?P<a>.+))?$", q_plain)
    titre = re.match(r"^(?:la\s+chanson|le\s+morceau|l'album|la\s+playlist|le\s+titre|un\s+morceau\s+(?:de|d')|une\s+chanson\s+"
                     r"(?:de|d')|des\s+chansons\s+(?:de|d')|l'artiste|du\s+son\s+de)\s*(?P<a>.+)$", q_plain)
    partitif = re.match(r"^(?:du|de\s+la|des|de\s+l'|un\s+peu\s+de|un\s+peu\s+d')\s*(?P<a>.+)$", q_plain)
    debut_q = m.start("q")
    if musique:
        a = musique.group("a")
        recherche = _brut_depuis(raw, plain, debut_q + musique.start("a"), m.end("q")) if a else ""
    elif titre:
        recherche = _brut_depuis(raw, plain, debut_q + titre.start("a"), m.end("q"))
    elif partitif and re.match(r"^(?:mets|met|mettre|joue|jouer|passe|ecoute|fais)", plain[len(re.match(_LEAD, plain).group(0)):]) \
            and not _PAS_DE_LA_MUSIQUE.match(partitif.group("a")):
        recherche = _brut_depuis(raw, plain, debut_q + partitif.start("a"), m.end("q"))
    elif explicite:
        recherche = _brut_depuis(raw, plain, debut_q, m.end("q"))
    else:
        return None
    return "musique_chercher", {"recherche": recherche, "service_dit": service, "web": bool(m.group("nav"))}


# --------------------------------------------------------------------------- #

def reconnaitre(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    """(verbe, paramètres) — le verbe est le nom de l'outil ; « __unsupported__ » : réponse honnête."""
    if re.search(r"https?://|www\.", plain):
        return None
    q = horloge.question(plain)
    if q:
        return "heure_dire", {"question": q}
    for regle in (_rappels, _lumiere, _bluetooth, _son, _musique):
        r = regle(raw, plain)
        if r is not None:
            return r
    return None
