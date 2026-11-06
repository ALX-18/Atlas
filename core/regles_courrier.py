"""
Sprint Compétences 2 — les règles déterministes des demandes de mails, d'agenda et de connexion.

Appelées en tête de `IntentClassifier.classify`, sur le texte « plat » (minuscules, sans accents), APRÈS les
règles de Compétences 1. Elles rendent (outil, paramètres) pour la catégorie « courrier », None sinon.

Chaque règle exige son objet : « mail », « e-mail », « courriel », « Gmail », « boîte de réception »,
« brouillon », « agenda », « rendez-vous »… — un verbe seul ne suffit jamais. Les exceptions :
- « lis-moi le 2 », « résume le 3 » : la suite d'une liste de mails (l'outil dit s'il n'y en a pas) ;
- « réponds à Paul que… » : « répondre à quelqu'un que… » n'a pas d'autre sens pour Atlas.
Les négatifs restent ailleurs : « envoie-moi une blague », « mon agenda papier », « nouveaux messages Discord ».

Le mail visé est désigné par son NUMÉRO dans la dernière liste, jamais par ce que le modèle en a compris.
"""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

from core import horloge
from core.regles_competences import _FIN, _LEAD, _brut_depuis

_MAIL = r"(?:e-?mails?|mails?|courriels?|messages?\s+gmail|gmail)"
_NUM = {"premier": 1, "premiere": 1, "1er": 1, "deuxieme": 2, "second": 2, "seconde": 2, "troisieme": 3,
        "quatrieme": 4, "cinquieme": 5, "sixieme": 6, "septieme": 7, "huitieme": 8, "neuvieme": 9, "dixieme": 10,
        "un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10}
_N = r"(?P<n>\d{1,2}|premier|premiere|1er|deuxieme|second|seconde|troisieme|quatrieme|cinquieme|sixieme|septieme|" \
     r"huitieme|neuvieme|dixieme|un|deux|trois|quatre|cinq|six|sept|huit|neuf|dix)"


def _m(motif: str, plain: str):
    return re.match(_LEAD + "(?:" + motif + ")" + _FIN, plain)


def _numero(m) -> Optional[int]:
    v = m.group("n") or (m.groupdict().get("n2") or "")
    return int(v) if v.isdigit() else _NUM.get(v)


def _service(t: str) -> Optional[str]:
    if re.search(r"\b(?:agenda|calendrier)\b", t):
        if re.search(r"\b(?:outlook|hotmail|icloud|apple|papier)\b", t):
            return None
        return "agenda_google"
    for cle, motif in (("gmail", r"gmail|google\s*mail"), ("icloud", r"icloud|mail\s+apple"),
                       ("outlook", r"outlook|hotmail|live\.fr")):
        if re.search(rf"\b(?:{motif})\b", t):
            return cle
    if re.search(rf"\b(?:{_MAIL}|boite\s+(?:mail|de\s+reception|aux\s+lettres\s+electronique))\b", t):
        return "gmail"
    return None


# --------------------------------------------------------------------------- #
#  Agenda : le jour, la plage
# --------------------------------------------------------------------------- #

def _jour(t: str) -> Optional[date]:
    ref = horloge.maintenant()
    if re.search(r"\bapres[- ]demain\b", t):
        return ref.date() + timedelta(days=2)
    if re.search(r"\bdemain\b", t):
        return ref.date() + timedelta(days=1)
    if re.search(r"\b(?:aujourd'hui|ce\s+soir|ce\s+matin|cet\s+apres[- ]midi|tantot)\b", t):
        return ref.date()
    d = horloge._date_nommee(t, ref)
    if d:
        return d
    js = horloge._jour_semaine(t)
    if js is not None:
        ecart = (js - ref.weekday()) % 7
        if re.search(r"\bprochain\b", t) and ecart == 0:
            ecart = 7
        return ref.date() + timedelta(days=ecart)
    return None


_WE = r"week[- ]?end"


def _periode(t: str) -> Optional[dict]:
    """Sprint Installeur / IN7 : « cette semaine », « la semaine prochaine », « ce week-end ».
    Rend {"du", "au" (inclus), "periode"} ; {"periode_inconnue": True} pour un mois ou le passé, que l'agenda
    ne lit pas encore (et le dit, au lieu de répondre pour aujourd'hui)."""
    auj = horloge.maintenant().date()
    lundi = auj - timedelta(days=auj.weekday())
    if re.search(r"\bsemaine\s+prochaine\b|\bprochaine\s+semaine\b", t):
        d = lundi + timedelta(days=7)
        return {"du": d, "au": d + timedelta(days=6), "periode": "la semaine prochaine"}
    if re.search(r"\bsemaine\s+(?:derniere|passee)\b|\b(?:ce|du)\s+mois(?:-ci)?\b|\bmois\s+(?:prochain|dernier)\b", t):
        return {"periode_inconnue": True}
    if re.search(r"\b(?:cette|de\s+la|la)\s+semaine\b", t):
        return {"du": auj, "au": lundi + timedelta(days=6), "periode": "cette semaine"}
    if re.search(rf"\b{_WE}\s+prochain\b|\bprochain\s+{_WE}\b", t):
        samedi = lundi + timedelta(days=5) + timedelta(days=7 if auj.weekday() >= 5 else 0)
        return {"du": samedi, "au": samedi + timedelta(days=1), "periode": "le week-end prochain"}
    if re.search(rf"\b(?:ce|du|le|pour\s+le)\s+{_WE}\b", t):
        samedi = lundi + timedelta(days=5)
        return {"du": max(auj, samedi), "au": samedi + timedelta(days=1), "periode": "ce week-end"}
    return None


def _periode_params(per: dict) -> dict:
    if per.get("periode_inconnue"):
        return {"periode_inconnue": True}
    return {"du": per["du"].isoformat(), "au": per["au"].isoformat(), "periode": per["periode"]}


def _plage(t: str) -> tuple[int, int, str]:
    if re.search(r"\bmatin(?:ee)?\b", t):
        return 8, 12, "le matin"
    if re.search(r"\bapres[- ]midi\b|\btantot\b", t):
        return 12, 18, "l'après-midi"
    if re.search(r"\bsoir(?:ee)?\b", t):
        return 18, 23, "le soir"
    return 8, 20, ""


# --------------------------------------------------------------------------- #
#  Reconnaître
# --------------------------------------------------------------------------- #

def reconnaitre(raw: str, plain: str) -> Optional[tuple[str, dict]]:
    t = plain
    if not re.search(r"\b(?:e-?mails?|mails?|courriels?|gmail|icloud|outlook|hotmail|boite|brouillons?|agenda|"
                     r"calendrier|rendez-vous|rdv|reponds?|repondre|libre|prevu|programme|lis|lire|resume|"
                     r"envoie|lien|j'ai|ai-je|qu'ai-je|evenement|dispo|disponible)\b", t):
        return None
    if re.search(r"\bagenda\s+papier\b|\bpapier\b.*\bagenda\b", t):
        return None

    # ---- connexion, déconnexion
    m = _m(r"(?P<v>connecte|connecter|branche|brancher|relie|relier|configure|configurer|ajoute|ajouter|"
           r"deconnecte|deconnecter|debranche|debrancher|oublie|retire|retirer|supprime)(?:-moi|\s+moi)?\s+"
           r"(?:a\s+|au\s+|de\s+)?(?:mon|ma|mes|le|la|les)\s+(?P<objet>.{2,40}?)", t)
    if m:
        service = _service(m.group("objet"))
        if service and not re.search(r"\b(?:rendez-vous|rdv|evenement)\b", m.group("objet")):
            deco = m.group("v").startswith(("deconnect", "debranch", "oublie", "retire", "supprime"))
            if deco and m.group("v") in ("oublie", "supprime", "retire", "retirer") and not re.search(
                    r"\bcompte\b|\bconnexion\b|\bgmail\b|\bicloud\b|\boutlook\b|\bagenda\b", m.group("objet")):
                return None          # « supprime mes mails » n'est pas une déconnexion (et n'est pas fait)
            return ("courrier_deconnecter" if deco else "courrier_connecter"), {"service": service}

    # ---- envoyer le brouillon préparé
    if _m(r"envoie[- ]le|envoie[- ]la|envoie\s+(?:le|mon|ce|la|ma)\s+(?:brouillon|reponse|mail|e-?mail|courriel)"
          r"(?:\s+(?:prepare|que\s+tu\s+as\s+prepare))?|tu\s+peux\s+l'envoyer", t):
        return "courrier_envoyer", {}

    # ---- un lien d'un mail
    m = _m(rf"(?:ouvre|ouvrir|suis|clique\s+sur)\s+le\s+lien\s+{_N}(?:\s+du\s+(?:mail|message)(?:\s+(?P<mail>\d{{1,2}}))?)?", t)
    if m:
        p = {"lien": _numero(m)}
        if m.group("mail"):
            p["numero"] = int(m.group("mail"))
        return "courrier_ouvrir_lien", p

    # ---- répondre
    m = re.match(_LEAD + r"(?:reponds?|repondre|fais\s+une\s+reponse)(?:\s+|(?=-lui))(?:(?P<lui>-?lui|a\s+ce\s+mail|a\s+ce\s+message)"
                 rf"|au\s+(?:mail\s+|message\s+)?(?:numero\s+)?{_N}|(?:a\s+(?:l'|la\s+|le\s+)?|au\s+)(?:mail|message|courriel)\s+"
                 r"(?:de\s+|d')(?P<qui2>.+?)|a\s+(?P<qui>.+?))\s+(?:pour\s+(?:lui\s+)?dire\s+|en\s+disant\s+)?"
                 r"(?P<consigne>(?:que|qu'|ok|d'accord|oui|non|merci|je|j')\b.*)$", t)
    if m:
        debut = m.start("consigne")
        consigne = _brut_depuis(raw, t, debut)
        p = {"consigne": consigne}
        if m.group("n"):
            p["numero"] = _numero(m)
        elif m.group("lui"):
            p["numero"] = "dernier_lu"
        else:
            qui_g = "qui2" if m.group("qui2") else "qui"
            p["qui"] = _brut_depuis(raw, t, m.start(qui_g), m.end(qui_g))
        return "courrier_repondre", p
    # « réponds à mon dernier mail » : sans ce qu'il faut dire, l'outil le demande (rien n'est préparé)
    m = _m(r"(?:reponds?|repondre)\s+(?:a|au)\s+(?:mon|ce|le)?\s*(?:dernier\s+)?(?:mail|message|courriel)(?:\s+de\s+(?P<qui>.+?))?", t)
    if m:
        return "courrier_repondre", ({"qui": _brut_depuis(raw, t, m.start("qui"), m.end("qui"))} if m.group("qui")
                                     else {"numero": "dernier_lu"})

    # ---- lire, résumer un mail de la liste
    m = _m(rf"(?P<v>lis|lire|relis|ouvre|resume|resumer)(?:-moi|\s+moi|-le-moi)?\s+(?:le\s+|la\s+)?"
           rf"(?:(?:mail|message|courriel|e-?mail)\s+(?:numero\s+)?{_N}|(?:numero\s+)?{_N.replace('?P<n>', '?P<n2>')}(?:\s+(?:mail|message|courriel))?)", t)
    if m and not (m.group("v") == "ouvre" and not re.search(r"\b(?:mail|message|courriel|e-?mail)\b", t)):
        n = _numero(m)
        if n:
            return ("courrier_resumer" if m.group("v").startswith("resum") else "courrier_lire"), {"numero": n}

    # ---- lister, résumer une liste, le dernier
    if re.search(rf"\b{_MAIL}\b|\bboite\s+de\s+reception\b|\bboite\s+mail\b|\binbox\b", t):
        if re.search(r"\b(?:envoie|envoyer|ecris|ecrire|redige|rediger|supprime|efface|vide|transfere|reponds?|repondre|"
                     r"comment|explique|pourquoi)\b", t) and \
                not re.search(r"\b(?:recu|reçu)\b", t):
            return None          # écrire un mail à quelqu'un, effacer : pas dans ce sprint (dit par le classifieur général)
        p: dict = {}
        if re.search(r"\b(?:nouveaux?|nouvelles?|non\s+lus?|pas\s+lus?)\b", t):
            p["non_lus"] = True
        if re.search(r"\bce\s+matin\b|\bde\s+la\s+matinee\b", t):
            p["quand"] = "matin"
        elif re.search(r"\baujourd'hui\b|\bdu\s+jour\b", t):
            p["quand"] = "aujourd'hui"
        elif re.search(r"\bdepuis\s+hier\b|\bd'hier\b|\bhier\b", t):
            p["quand"] = "hier"
        elif re.search(r"\bcette\s+semaine\b|\bde\s+la\s+semaine\b", t):
            p["quand"] = "semaine"
        if re.search(r"\bresumes?\b|\bresumer\b|\bresume-moi\b|\ben\s+bref\b", t):
            p["resumer"] = True
        if re.search(r"\bdernier\b", t) and not re.search(r"\bderniers\b", t):
            p["dernier"] = True
        mq = re.search(rf"\b{_MAIL}\s+(?:de|d'|du|des|venant\s+de|envoyes?\s+par)\s*(?P<qui>.+?)\s*(?:\?|$)", t)
        if mq:
            qui = mq.group("qui")
            qui = re.sub(r"\s+(?:ce\s+matin|aujourd'hui|hier|cette\s+semaine)$", "", qui).strip()
            qui = re.sub(r"^(?:la|le|les|l')\s*", "", qui).strip()
            if qui and qui not in ("ce matin", "aujourd'hui", "hier", "cette semaine", "la semaine", "la matinee",
                                   "la journee", "jour", "gmail", "test", "moi") and not qui.startswith(("ce ", "cette ")):
                deb = t.index(qui, mq.start("qui"))
                p["qui"] = _brut_depuis(raw, t, deb, deb + len(qui))
        intention = re.search(r"\b(?:j'ai|ai-je|est-ce\s+que\s+j'ai|tu\s+as|as-tu|y\s+a-t-il|il\s+y\s+a|recu|"
                              r"des|mes|mon|ma|les|ouvre|montre|affiche|liste|lis|donne|"
                              r"quoi\s+de\s+neuf|resume|le\s+dernier|les\s+derniers|nouveaux|regarde|verifie|check)\b", t)
        if intention:
            return "courrier_lister", p

    # ---- agenda : créer
    if re.search(r"\b(?:rendez-vous|rdv|evenement)\b|\b(?:a|dans)\s+mon\s+(?:agenda|calendrier)\b|"
                 r"\b(?:au|a\s+l'|dans\s+l')\s*(?:agenda|calendrier)\b", t):
        m = re.match(_LEAD + r"(?:ajoute|ajouter|mets|mettre|cree|creer|note|noter|programme|planifie|prends|prendre|"
                     r"cale|caler|inscris|place)(?:-moi|\s+moi)?\s+(?P<reste>.+)$", t)
        if m and re.search(r"\b(?:rendez-vous|rdv|evenement|agenda|calendrier)\b", m.group("reste")):
            reste = m.group("reste")
            debut_reste = m.start("reste")
            p = {"quand_texte": _brut_depuis(raw, t, debut_reste)}
            fin = re.search(r"\b(?:jusqu'a|a)\s+(\d{1,2}\s*(?:h|heures?)\s*\d{0,2})\s*$", reste)
            de = re.search(r"\bde\s+\d{1,2}\s*(?:h|heures?)\s*\d{0,2}\s+a\s+(\d{1,2}\s*(?:h|heures?)\s*\d{0,2})", reste)
            if de:
                p["fin_texte"] = de.group(1)
                p["quand_texte"] = _brut_depuis(raw, t, debut_reste, debut_reste + de.start(1))
            md = re.search(r"\b(?:pendant|pour)\s+(\d{1,2})\s*(h|heures?|min|minutes?)\b", reste)
            if md:
                p["duree_min"] = int(md.group(1)) * (60 if md.group(2).startswith("h") else 1)
            p["titre"] = _titre(raw, t, debut_reste)
            return "agenda_creer", p
        if not re.search(r"\b(?:prochain|libre|qu'est-ce|quoi|j'ai|ai-je|montre|affiche|lis|dis)\b", t):
            return None

    # ---- agenda : lire
    if re.search(r"\b(?:prochain|prochaine)\s+(?:rendez-vous|rdv|evenement|reunion)\b", t):
        return "agenda_lire", {"prochain": True}
    m = re.search(r"\b(?:je\s+suis|suis-je|serai-je|je\s+serai|est-ce\s+que\s+je\s+suis)\s+(?:libre|dispo(?:nible)?)\b", t)
    if m:
        h0, h1, plage = _plage(t)
        per = _periode(t)
        if per:
            return "agenda_lire", {**_periode_params(per), "libre": True, "de": h0, "a": h1, "plage": plage}
        jour = _jour(t) or horloge.maintenant().date()
        return "agenda_lire", {"jour": jour.isoformat(), "libre": True, "de": h0, "a": h1, "plage": plage}
    # « qu'est-ce que j'ai demain ? » : le jour doit suivre (« qu'est-ce que j'ai fait hier » n'est pas l'agenda)
    _JOUR = (r"(?:apres[- ]demain|demain|aujourd'hui|ce\s+soir|ce\s+matin|cet\s+apres[- ]midi|cette\s+semaine|"
             r"(?:la\s+)?semaine\s+prochaine|(?:ce|le)\s+week[- ]?end(?:\s+prochain)?|ce\s+mois(?:-ci)?|"
             r"le\s+mois\s+prochain|"
             r"(?:ce\s+|le\s+)?(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)(?:\s+prochain)?(?:\s+(?:matin|soir|"
             r"apres[- ]midi))?|le\s+\d{1,2}(?:er)?\s+\w+)")
    question = re.search(
        r"\b(?:qu'est-ce\s+que\s+j'ai|j'ai\s+quoi|qu'ai-je|ai-je\s+quelque\s+chose|j'ai\s+(?:des\s+|un\s+)?(?:rendez-vous|rdv)|"
        r"qu'est-ce\s+qui\s+est\s+prevu|quoi\s+de\s+prevu|qu'y\s+a-t-il|mon\s+programme)"
        r"(?:\s+(?:de\s+prevu|au\s+programme|comme\s+(?:rendez-vous|rdv)|d'autre))?\s+(?:pour\s+)?" + _JOUR + r"\b", t)
    concept = re.search(r"\b(?:explique|c'est\s+quoi|qu'est-ce\s+qu'(?:un|une)|comment|definition|pourquoi)\b", t)
    if (re.search(r"\b(?:mon|ton|l')\s*(?:agenda|calendrier)\b", t) and not concept) or question:
        per = _periode(t)
        if per:
            return "agenda_lire", _periode_params(per)
        jour = _jour(t)
        return "agenda_lire", {"jour": (jour or horloge.maintenant().date()).isoformat()}
    return None


_MOMENT = re.compile(
    r"\s*\b(?:(?:le\s+)?(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)(?:\s+prochain)?|apres[- ]demain|demain|"
    r"aujourd'hui|ce\s+soir|ce\s+matin|cet\s+apres[- ]midi|le\s+\d{1,2}(?:er)?\s+\w+(?:\s+\d{4})?|\d{1,2}/\d{1,2}(?:/\d{4})?|"
    r"(?:a|vers|de|jusqu'a)\s+\d{1,2}\s*(?:h|heures?|:)\s*\d{0,2}(?:\s+et\s+(?:demie?|quart))?|midi|minuit|"
    r"(?:pendant|pour)\s+\d{1,2}\s*(?:h|heures?|min|minutes?)|(?:du|le)\s+matin|(?:du|le)\s+soir|de\s+l'apres[- ]midi)\b")


def _titre(raw: str, t: str, debut: int) -> str:
    """Le titre du rendez-vous : la demande sans le verbe, le mot « rendez-vous » et le moment."""
    reste = _brut_depuis(raw, t, debut)
    plat = horloge.plat(reste)
    morceaux, i = [], 0
    for m in _MOMENT.finditer(plat):
        morceaux.append(reste[i:m.start()])
        i = m.end()
    morceaux.append(reste[i:])
    titre = re.sub(r"\s+", " ", " ".join(morceaux)).strip(" ,.")
    titre = re.sub(r"^(?:un|une|le|la|mon|ma)\s+", "", titre, flags=re.IGNORECASE)
    titre = re.sub(r"\s*(?:(?:(?:à|a|dans)\s+(?:mon\s+|l')|au\s+)(?:agenda|calendrier)(?:\s+google)?)\s*", " ", titre,
                   flags=re.IGNORECASE).strip()
    sans = re.sub(r"^(?:rendez-vous|rdv|événement|evenement)\s*", "", titre, flags=re.IGNORECASE).strip()
    if not sans:
        return "Rendez-vous"
    if re.match(r"^(?:chez|avec|au|à|a|pour)\b", sans, re.IGNORECASE) or sans != titre:
        return f"Rendez-vous {sans}"
    return sans[:1].upper() + sans[1:]
