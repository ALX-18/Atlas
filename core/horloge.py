"""
Sprint Compétences 1 / CP1–CP2 — l'heure, la date et les moments, calculés par le moteur.

Le défaut L4 du sprint G : le modèle inventait l'heure. Ici, tout part de l'horloge du système
(`maintenant()`, que les tests figent) et se calcule sans modèle :
- les questions : « quelle heure est-il ? », « on est quel jour ? », « quelle date dans 3 semaines ? »,
  « quel jour tombe le 25 décembre ? » ;
- les durées : « 10 minutes », « 1 h 30 », « une demi-heure », « un quart d'heure » ;
- les moments : « demain à 9 h », « lundi à 8 h », « ce soir à 8 h », « le 25 octobre à 9 h » ;
- les répétitions : « tous les jours à 7 h », « tous les lundis à 8 h », « chaque mardi et jeudi ».

Une heure ambiguë (« à 8 h » dite à 15 h : ce soir ou demain matin ?) n'est pas tranchée : elle est
rendue comme une question à poser.

Les textes reçus sont « plats » : minuscules, sans accents (voir `plat`).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Optional

_horloge = datetime.now          # les tests le remplacent : horloge figée


def maintenant() -> datetime:
    return _horloge().replace(microsecond=0)


def plat(texte: str) -> str:
    t = unicodedata.normalize("NFD", (texte or "").lower().replace("’", "'"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre",
        "novembre", "decembre"]
_MOIS_ECRITS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre",
                "novembre", "décembre"]

NOMBRES = {"un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8,
           "neuf": 9, "dix": 10, "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15, "seize": 16,
           "vingt": 20, "trente": 30, "quarante": 40, "quarante-cinq": 45, "cinquante": 50, "soixante": 60,
           "vingt-cinq": 25, "dix-huit": 18, "dix-sept": 17, "dix-neuf": 19}
_NOMBRE = r"(?:\d+|" + "|".join(sorted(map(re.escape, NOMBRES), key=len, reverse=True)) + r")"


def _n(mot: str) -> int:
    return int(mot) if mot.isdigit() else NOMBRES[mot]


# --------------------------------------------------------------------------- #
#  Écrire en français
# --------------------------------------------------------------------------- #

def heure_fr(dt: datetime) -> str:
    """15 h 05, 9 h, midi, minuit."""
    if dt.hour == 12 and dt.minute == 0:
        return "midi"
    if dt.hour == 0 and dt.minute == 0:
        return "minuit"
    return f"{dt.hour} h {dt.minute:02d}" if dt.minute else f"{dt.hour} h"


def date_fr(d: date, annee: bool = True) -> str:
    """samedi 18 octobre 2026 (« 1er » pour le premier du mois)."""
    jour = "1er" if d.day == 1 else str(d.day)
    texte = f"{JOURS[d.weekday()]} {jour} {_MOIS_ECRITS[d.month - 1]}"
    return f"{texte} {d.year}" if annee else texte


def quand_fr(dt: datetime, ref: Optional[datetime] = None) -> str:
    """aujourd'hui à 15 h, demain à 9 h, lundi 20 octobre à 8 h."""
    ref = ref or maintenant()
    ecart = (dt.date() - ref.date()).days
    if ecart == 0:
        jour = "aujourd'hui"
    elif ecart == 1:
        jour = "demain"
    elif ecart == -1:
        jour = "hier"
    else:
        jour = date_fr(dt.date(), annee=dt.year != ref.year)
    return f"{jour} à {heure_fr(dt)}"


def duree_fr(d: timedelta) -> str:
    """1 h 30, 10 minutes, 45 secondes, 2 jours et 3 h."""
    s = int(round(d.total_seconds()))
    if s < 60:
        return f"{s} seconde{'s' if s > 1 else ''}"
    j, s = divmod(s, 86400)
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    morceaux = []
    if j:
        morceaux.append(f"{j} jour{'s' if j > 1 else ''}")
    if h and m and not j:
        morceaux.append(f"{h} h {m:02d}")
    else:
        if h:
            morceaux.append(f"{h} h")
        if m:
            morceaux.append(f"{m} minute{'s' if m > 1 else ''}")
    if s and not j and not h:
        morceaux.append(f"{s} s")
    return " et ".join(morceaux)


# --------------------------------------------------------------------------- #
#  Durées
# --------------------------------------------------------------------------- #

_UNITES = {
    "secondes": "s", "seconde": "s", "sec": "s", "s": "s",
    "minutes": "m", "minute": "m", "min": "m", "mn": "m",
    "heures": "h", "heure": "h", "h": "h",
    "jours": "j", "jour": "j", "semaines": "sem", "semaine": "sem",
}
_DUREE_RE = re.compile(
    r"(?P<n>" + _NOMBRE + r")\s*(?P<u>secondes?|sec|minutes?|min|mn|heures?|h|jours?|semaines?|s)\b"
    r"(?:\s*(?:et\s+)?(?P<n2>\d{1,2}|" + _NOMBRE + r")(?:\s*(?:minutes?|min|mn))?(?=\s|$|[,.!?]))?"
    r"(?P<demie>\s+et\s+demie?)?"
)


def duree(texte: str) -> Optional[timedelta]:
    """La première durée nommée dans le texte (plat), ou None. « 1 h 30 », « une demi-heure »…"""
    t = plat(texte)
    if re.search(r"\bune?\s+demi[- ]heure\b", t):
        return timedelta(minutes=30)
    if re.search(r"\bun\s+quart\s+d'?heure\b", t):
        return timedelta(minutes=15)
    if re.search(r"\btrois\s+quarts?\s+d'?heure\b", t):
        return timedelta(minutes=45)
    total, vu = timedelta(), False
    for m in _DUREE_RE.finditer(t):
        n, u = _n(m.group("n")), _UNITES[m.group("u")]
        pas = {"s": timedelta(seconds=1), "m": timedelta(minutes=1), "h": timedelta(hours=1),
               "j": timedelta(days=1), "sem": timedelta(weeks=1)}[u]
        total += n * pas
        if m.group("n2") and u == "h":
            total += timedelta(minutes=_n(m.group("n2")))
        if m.group("demie"):
            total += pas / 2
        vu = True
    return total if vu and total.total_seconds() > 0 else None


def dans(texte: str) -> Optional[timedelta]:
    """« dans 20 minutes », « dans 3 semaines », « dans 2 mois » (en jours calendaires approchés : non)."""
    m = re.search(r"\bdans\s+(.+)", plat(texte))
    return duree(m.group(1)) if m else None


def ajouter_mois(d: date, n: int) -> date:
    mois = d.month - 1 + n
    annee, mois = d.year + mois // 12, mois % 12 + 1
    import calendar

    return date(annee, mois, min(d.day, calendar.monthrange(annee, mois)[1]))


# --------------------------------------------------------------------------- #
#  Heures et moments
# --------------------------------------------------------------------------- #

_HEURE_RE = re.compile(
    r"\b(?:a\s+|vers\s+|pour\s+)?(?P<h>\d{1,2})\s*(?:h|heures?|:)\s*(?P<m>\d{2})?(?:\s*(?:min|minutes?))?\b"
    r"|\b(?:a\s+)?(?P<mot>midi|minuit)(?:\s+et\s+demie?)?\b"
)


def _qualif(t: str) -> Optional[str]:
    if re.search(r"\b(?:du|le|ce|demain)\s+matin\b|\bmatin\b", t):
        return "matin"
    if re.search(r"\b(?:du|ce|le|demain)\s+soir\b|\bsoir\b|\bde\s+l'apres[- ]midi\b|\bcet\s+apres[- ]midi\b|"
                 r"\bdans\s+l'apres[- ]midi\b|\bapres[- ]midi\b", t):
        return "soir"
    return None


def heure_dite(texte: str) -> Optional[dict]:
    """{"h", "m", "qualif", "ambigu"} pour l'heure nommée dans le texte, ou None.

    ambigu : une heure de 1 à 11 sans « matin » ni « soir » (« à 8 h ») — selon le moment, elle peut
    désigner 8 h ou 20 h ; c'est l'appelant qui décide s'il doit demander."""
    t = plat(texte)
    m = _HEURE_RE.search(t)
    if not m:
        return None
    if m.group("mot"):
        h, mn = (12 if m.group("mot") == "midi" else 0), (30 if "demi" in m.group(0) else 0)
        return {"h": h, "m": mn, "qualif": None, "ambigu": False}
    h, mn = int(m.group("h")), int(m.group("m") or 0)
    if "et demie" in t[m.end():m.end() + 10]:
        mn = 30
    elif "et quart" in t[m.end():m.end() + 10]:
        mn = 15
    if h > 23 or mn > 59:
        return None
    q = _qualif(t)
    if q == "soir" and 1 <= h <= 11:
        h += 12
    return {"h": h, "m": mn, "qualif": q, "ambigu": q is None and 1 <= h <= 11}


def _jour_semaine(t: str) -> Optional[int]:
    for k, j in enumerate(JOURS):
        if re.search(rf"\b{j}\b", t):
            return k
    return None


def _date_nommee(t: str, ref: datetime) -> Optional[date]:
    """« le 25 octobre », « le 3 », « 25/10 », « le 1er novembre 2027 »."""
    m = re.search(r"\b(?:le\s+)?(?P<j>\d{1,2}|1er|premier)\s+(?P<mois>" + "|".join(MOIS) + r")(?:\s+(?P<a>\d{4}))?\b", t)
    if m:
        j = 1 if m.group("j") in ("1er", "premier") else int(m.group("j"))
        mois = MOIS.index(m.group("mois")) + 1
        annee = int(m.group("a")) if m.group("a") else ref.year
        try:
            d = date(annee, mois, j)
        except ValueError:
            return None
        if not m.group("a") and d < ref.date():
            d = date(annee + 1, mois, j)
        return d
    m = re.search(r"\b(?P<j>\d{1,2})/(?P<mois>\d{1,2})(?:/(?P<a>\d{4}))?\b", t)
    if m:
        try:
            d = date(int(m.group("a") or ref.year), int(m.group("mois")), int(m.group("j")))
        except ValueError:
            return None
        if not m.group("a") and d < ref.date():
            d = d.replace(year=d.year + 1)
        return d
    return None


def moment(texte: str, ref: Optional[datetime] = None) -> dict:
    """Le moment désigné par une phrase de rappel.

    {"quand": datetime} — calculé ;
    {"question": "…", "options": [(libellé, datetime), …]} — heure ambiguë, à demander ;
    {} — aucun moment dans la phrase.
    """
    ref = ref or maintenant()
    t = plat(texte)
    d = dans(t)
    if d is not None and re.search(r"\bdans\s+" + _NOMBRE + r"|\bdans\s+une?\s+(?:demi|quart)", t):
        return {"quand": ref + d}
    hd = heure_dite(t)
    jour: Optional[date] = None
    explicite = True
    if re.search(r"\bapres[- ]demain\b", t):
        jour = ref.date() + timedelta(days=2)
    elif re.search(r"\bdemain\b", t):
        jour = ref.date() + timedelta(days=1)
    elif re.search(r"\b(?:aujourd'hui|ce soir|ce matin|cet apres[- ]midi|tout a l'heure)\b", t):
        jour = ref.date()
    elif (dn := _date_nommee(t, ref)) is not None:
        jour = dn
    elif (js := _jour_semaine(t)) is not None:
        ecart = (js - ref.weekday()) % 7
        if ecart == 0 and (not hd or (hd["h"], hd["m"]) <= (ref.hour, ref.minute)):
            ecart = 7
        jour = ref.date() + timedelta(days=ecart)
    else:
        explicite = False
        jour = ref.date()
    if not hd:
        if explicite and jour != ref.date():
            return {"jour_sans_heure": jour}
        return {}
    h, mn = hd["h"], hd["m"]
    cible = datetime.combine(jour, datetime.min.time()).replace(hour=h, minute=mn)
    if hd["ambigu"]:
        if not explicite:
            # « à 8 h » sans jour : 8 h n'est pas passée → 8 h aujourd'hui, sans question (le matin
            # ou plus tard dans la journée). Passée : ce soir 20 h ou demain 8 h ? On demande.
            if cible > ref:
                return {"quand": cible}
            soir = cible.replace(hour=h + 12)
            demain = cible + timedelta(days=1)
            if soir > ref:
                return {"question": f"À {heure_fr(soir)} ce soir, ou à {heure_fr(demain)} demain matin ?",
                        "options": [(f"ce soir à {heure_fr(soir)}", soir), (f"demain à {heure_fr(demain)}", demain)]}
            return {"quand": demain}
        return {"quand": cible}
    if not explicite and cible <= ref:
        cible += timedelta(days=1)
    return {"quand": cible}


def recurrence(texte: str) -> Optional[dict]:
    """« tous les jours à 7 h », « tous les lundis à 8 h », « chaque mardi et jeudi à 18 h »,
    « en semaine à 7 h » → {"jours": [0..6], "h", "m"} ; sans heure dite : None."""
    t = plat(texte)
    if not re.search(r"\b(?:tous les|toutes les|chaque|en semaine|le week-?end|les week-?ends)\b", t):
        return None
    hd = heure_dite(t)
    if not hd:
        return None
    if re.search(r"\b(?:tous les jours|chaque jour|quotidien)", t):
        jours = list(range(7))
    elif re.search(r"\ben semaine\b|\bdu lundi au vendredi\b", t):
        jours = [0, 1, 2, 3, 4]
    elif re.search(r"\bweek-?ends?\b", t):
        jours = [5, 6]
    else:
        jours = [k for k, j in enumerate(JOURS) if re.search(rf"\b{j}s?\b", t)]
    if not jours:
        return None
    h = hd["h"]
    return {"jours": jours, "h": h, "m": hd["m"]}


def prochaine(rec: dict, apres: datetime) -> datetime:
    """La prochaine occurrence d'une répétition, strictement après `apres`."""
    base = apres.replace(second=0, microsecond=0)
    for k in range(0, 8):
        jour = base.date() + timedelta(days=k)
        if jour.weekday() not in rec["jours"]:
            continue
        cible = datetime.combine(jour, datetime.min.time()).replace(hour=rec["h"], minute=rec["m"])
        if cible > apres:
            return cible
    raise ValueError("répétition sans jour")


def recurrence_fr(rec: dict) -> str:
    jours = rec["jours"]
    h = heure_fr(datetime(2000, 1, 1, rec["h"], rec["m"]))
    if len(jours) == 7:
        return f"tous les jours à {h}"
    if jours == [0, 1, 2, 3, 4]:
        return f"en semaine à {h}"
    if jours == [5, 6]:
        return f"le week-end à {h}"
    noms = [JOURS[j] + "s" for j in jours]
    return f"tous les {' et '.join(noms) if len(noms) <= 2 else ', '.join(noms[:-1]) + ' et ' + noms[-1]} à {h}"


# --------------------------------------------------------------------------- #
#  CP1 — les questions sur l'heure et la date
# --------------------------------------------------------------------------- #

_Q_HEURE = re.compile(
    r"^(?:atlas[\s,]*)?(?:(?:dis[- ]moi|tu peux me dire|peux-tu me dire|tu sais|sais-tu)\s+)?"
    r"(?:quelle\s+heure\s+(?:est[- ]il|il\s+est|c'est|on\s+est|est-ce)|il\s+est\s+quelle\s+heure|"
    r"(?:t'as|tu as|as-tu|vous avez)\s+l'heure|l'heure\s+(?:qu'il\s+est|actuelle|s'il te plait)?|"
    r"c'est\s+quelle\s+heure|on\s+est\s+a\s+quelle\s+heure|quelle\s+heure)"
    r"(?P<lieu>\s+(?:a|au|aux|en)\s+[\w' -]+)?\s*(?:maintenant|actuellement|exactement|la)?\s*[?!.]*$"
)
_Q_DATE = re.compile(
    r"^(?:atlas[\s,]*)?(?:(?:dis[- ]moi|tu peux me dire|peux-tu me dire|tu sais)\s+)?"
    r"(?:on\s+est\s+(?:quel\s+jour|le\s+combien|quelle\s+date)|quel\s+jour\s+(?:on\s+est|sommes-nous|est-on|"
    r"nous\s+sommes|est-ce|c'est|on\s+est\s+aujourd'hui)|quelle\s+est\s+la\s+date(?:\s+d'aujourd'hui|\s+du\s+jour)?|"
    r"c'est\s+quoi\s+la\s+date(?:\s+d'aujourd'hui)?|quelle\s+date\s+(?:on\s+est|sommes-nous|est-on|"
    r"aujourd'hui|c'est)|la\s+date\s+(?:d'aujourd'hui|du\s+jour)|nous\s+sommes\s+quel\s+jour|"
    r"c'est\s+quel\s+jour(?:\s+aujourd'hui)?|quel\s+jour\s+aujourd'hui)"
    r"(?:\s+aujourd'hui)?\s*[?!.]*$"
)
_Q_DATE_RELATIVE = re.compile(
    r"^(?:atlas[\s,]*)?(?:quelle\s+date|quel\s+jour|on\s+sera\s+quel\s+jour|on\s+sera\s+le\s+combien)\s*"
    r"(?:(?:on\s+sera|serons-nous|sera-t-on|ce\s+sera|ca\s+fera|ca\s+sera|sera-t-il|tombe|sera)\s+)?"
    r"(?P<rel>dans\s+.+|demain|apres[- ]demain|hier|avant[- ]hier)\s*[?!.]*$"
)
_Q_JOUR_DE = re.compile(
    r"^(?:atlas[\s,]*)?(?:quel\s+jour\s+(?:de\s+la\s+semaine\s+)?(?:tombe|sera|est|c'est|ce\s+sera|tombera)\s+)"
    r"(?P<d>.+?)\s*[?!.]*$"
)


def question(texte: str) -> Optional[dict]:
    """La question sur l'heure ou la date posée par la phrase, ou None. {"sorte", …}."""
    t = plat(texte).strip().rstrip(" ?!.")
    m = _Q_HEURE.match(t)
    if m:
        return {"sorte": "heure", "lieu": (m.group("lieu") or "").strip() or None}
    if _Q_DATE.match(t):
        return {"sorte": "date"}
    m = _Q_DATE_RELATIVE.match(t)
    if m:
        rel = m.group("rel")
        if rel.startswith("dans") and not re.search(r"\bmois\b|\bans?\b|\bannees?\b", rel) and duree(rel) is None:
            return None
        return {"sorte": "date_relative", "rel": rel}
    m = _Q_JOUR_DE.match(t)
    if m and (_date_nommee(m.group("d"), maintenant()) or re.search(r"\bnoel\b|\bnouvel an\b", m.group("d"))):
        return {"sorte": "jour_de", "d": m.group("d")}
    return None


def repondre(q: dict) -> str:
    """La réponse, calculée depuis l'horloge du système."""
    now = maintenant()
    if q["sorte"] == "heure":
        texte = f"Il est {heure_fr(now)}."
        if q.get("lieu"):
            texte = (f"Je ne connais que l'heure de ton ordinateur : il est {heure_fr(now)} ici. "
                     "L'heure d'un autre pays, je ne sais pas encore la calculer.")
        return texte
    if q["sorte"] == "date":
        return f"Nous sommes le {date_fr(now.date())}."
    if q["sorte"] == "date_relative":
        rel = q["rel"]
        if rel in ("demain",):
            d, verbe = now.date() + timedelta(days=1), "Demain, nous serons le"
        elif rel.startswith("apres"):
            d, verbe = now.date() + timedelta(days=2), "Après-demain, nous serons le"
        elif rel == "hier":
            d, verbe = now.date() - timedelta(days=1), "Hier, nous étions le"
        elif rel.startswith("avant"):
            d, verbe = now.date() - timedelta(days=2), "Avant-hier, nous étions le"
        else:
            m = re.search(r"dans\s+(" + _NOMBRE + r")\s+(mois|ans?|annees?)\b", rel)
            if m:
                n = _n(m.group(1))
                d = ajouter_mois(now.date(), n if m.group(2) == "mois" else 12 * n)
            else:
                d = (now + duree(rel)).date()
            verbe = f"{rel[0].upper()}{rel[1:]}, nous serons le"
        return f"{verbe} {date_fr(d)}."
    if q["sorte"] == "jour_de":
        txt = q["d"]
        if re.search(r"\bnoel\b", txt):
            d = date(now.year, 12, 25)
            d = d if d >= now.date() else date(now.year + 1, 12, 25)
        elif re.search(r"\bnouvel an\b", txt):
            d = date(now.year + 1, 1, 1)
        else:
            d = _date_nommee(txt, now)
        return f"Le {date_fr(d)[len(JOURS[d.weekday()]) + 1:]} tombe un {JOURS[d.weekday()]}."
    raise ValueError(q)
