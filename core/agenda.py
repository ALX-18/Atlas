"""
Sprint Compétences 2 / CM5 — l'agenda Google, sans compte technique ni OAuth.

- LECTURE : l'adresse privée au format iCal du Google Agenda (Paramètres → Intégrer l'agenda), saisie dans la
  fenêtre de connexion (champ masqué : c'est un secret, quiconque la connaît lit l'agenda). Elle est lue à la
  demande, analysée ici (événements récurrents, exceptions, journées entières, fuseaux horaires) et jamais
  envoyée ailleurs.
- CRÉATION : un lien Google Agenda PRÉ-REMPLI, ouvert dans le navigateur après une confirmation qui montre la
  date, l'heure et le titre. C'est la personne qui enregistre, chez Google. Atlas dit « J'ai ouvert le
  rendez-vous pré-rempli dans Google Agenda : enregistre-le là-bas. » — jamais « c'est ajouté ».

Les titres d'événements peuvent venir d'invitations d'inconnus : ce sont des données, montrées telles quelles,
jamais données au modèle, et la réponse n'entre pas dans l'historique (`non_fiable`).
"""

from __future__ import annotations

import logging
import re
import secrets as _aleatoire
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from core import coffre

logger = logging.getLogger("atlas.agenda")

SERVICE = "agenda_google"
CACHE_S = 300.0
PROCHAIN_JOURS = 60


@dataclass
class Evenement:
    titre: str
    debut: datetime          # aware ; journée entière : minuit local
    fin: datetime
    journee: bool = False
    lieu: str = ""
    occupe: bool = True


# --------------------------------------------------------------------------- #
#  Lecture du fichier iCal (RFC 5545), sans bibliothèque de plus que dateutil
# --------------------------------------------------------------------------- #

def _local():
    return datetime.now().astimezone().tzinfo


def _deplier(texte: str) -> list[str]:
    lignes = []
    for l in texte.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if l[:1] in (" ", "\t") and lignes:
            lignes[-1] += l[1:]
        elif l:
            lignes.append(l)
    return lignes


def _propriete(ligne: str) -> tuple[str, dict, str]:
    tete, _, valeur = "", "", ""
    dans, coupe = False, None
    for i, c in enumerate(ligne):
        if c == '"':
            dans = not dans
        elif c == ":" and not dans:
            coupe = i
            break
    if coupe is None:
        return ligne.upper(), {}, ""
    tete, valeur = ligne[:coupe], ligne[coupe + 1:]
    morceaux = tete.split(";")
    params = {}
    for m in morceaux[1:]:
        k, _, v = m.partition("=")
        params[k.upper()] = v.strip('"')
    return morceaux[0].upper(), params, valeur


def _texte(v: str) -> str:
    return re.sub(r"\\([\\;,nN])", lambda m: "\n" if m.group(1) in "nN" else m.group(1), v).strip()


def _zone(tzid: Optional[str]):
    if not tzid:
        return None
    try:
        return ZoneInfo(tzid)
    except Exception:
        return None


def _instant(valeur: str, params: dict) -> tuple[datetime, bool]:
    """(datetime aware, journée entière ?)"""
    v = valeur.strip()
    if params.get("VALUE") == "DATE" or re.fullmatch(r"\d{8}", v):
        d = datetime.strptime(v[:8], "%Y%m%d")
        return d.replace(tzinfo=_local()), True
    utc = v.endswith("Z")
    d = datetime.strptime(v.rstrip("Z")[:15], "%Y%m%dT%H%M%S")
    if utc:
        return d.replace(tzinfo=timezone.utc), False
    return d.replace(tzinfo=_zone(params.get("TZID")) or _local()), False


def _duree(v: str) -> timedelta:
    m = re.fullmatch(r"([+-])?P(?:(\d+)W)?(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", v.strip())
    if not m:
        return timedelta(hours=1)
    s, w, d, h, mi, se = m.groups()
    t = timedelta(weeks=int(w or 0), days=int(d or 0), hours=int(h or 0), minutes=int(mi or 0), seconds=int(se or 0))
    return -t if s == "-" else t


def analyser_ical(texte: str, debut: datetime, fin: datetime) -> list[Evenement]:
    """Les événements qui recoupent [debut, fin[, récurrences dépliées, exceptions appliquées."""
    from dateutil.rrule import rrulestr

    bruts, courant = [], None
    for ligne in _deplier(texte):
        nom, params, valeur = _propriete(ligne)
        if nom == "BEGIN" and valeur.upper() == "VEVENT":
            courant = {"EXDATE": []}
        elif nom == "END" and valeur.upper() == "VEVENT" and courant is not None:
            bruts.append(courant)
            courant = None
        elif courant is not None:
            if nom == "EXDATE":
                courant["EXDATE"] += [(x, params) for x in valeur.split(",") if x]
            else:
                courant.setdefault(nom, (valeur, params))
    remplaces: dict[tuple[str, datetime], dict] = {}
    for b in bruts:
        if "RECURRENCE-ID" in b and "UID" in b:
            rid, _ = _instant(*b["RECURRENCE-ID"])
            remplaces[(b["UID"][0], rid.astimezone(timezone.utc))] = b
    sortie: list[Evenement] = []

    def ajouter(b: dict, d0: datetime, journee: bool, longueur: timedelta):
        if (b.get("STATUS", ("",))[0].upper() == "CANCELLED"):
            return
        d1 = d0 + longueur
        if d1 <= debut or d0 >= fin:
            return
        sortie.append(Evenement(titre=_texte(b.get("SUMMARY", ("(sans titre)",))[0]) or "(sans titre)", debut=d0,
                                fin=d1, journee=journee, lieu=_texte(b.get("LOCATION", ("",))[0]),
                                occupe=b.get("TRANSP", ("OPAQUE",))[0].upper() != "TRANSPARENT"))

    for b in bruts:
        if "DTSTART" not in b or "RECURRENCE-ID" in b:
            continue
        try:
            d0, journee = _instant(*b["DTSTART"])
            if "DTEND" in b:
                longueur = _instant(*b["DTEND"])[0] - d0
            elif "DURATION" in b:
                longueur = _duree(b["DURATION"][0])
            else:
                longueur = timedelta(days=1) if journee else timedelta(0)
        except Exception as e:
            logger.debug("[AGENDA] Événement illisible (%s)", type(e).__name__)
            continue
        uid = b.get("UID", ("",))[0]
        if "RRULE" not in b:
            ajouter(b, d0, journee, longueur)
            continue
        exclues = set()
        for x, prm in b["EXDATE"]:
            try:
                exclues.add(_instant(x, prm)[0].astimezone(timezone.utc))
            except Exception:
                pass
        try:
            regle = b["RRULE"][0]
            if journee:
                base = d0.replace(tzinfo=None)
                regle = re.sub(r"UNTIL=(\d{8})T\d{6}Z?", r"UNTIL=\1", regle)
                occ = rrulestr("RRULE:" + regle, dtstart=base)
                dates = [o.replace(tzinfo=_local()) for o in occ.between(debut.replace(tzinfo=None) - longueur,
                                                                         fin.replace(tzinfo=None), inc=True)]
            else:
                if "UNTIL=" in regle and not re.search(r"UNTIL=\d{8}T\d{6}Z", regle):
                    regle = re.sub(r"UNTIL=(\d{8})(?:T(\d{6}))?",
                                   lambda m: "UNTIL=" + m.group(1) + "T" + (m.group(2) or "235959") + "Z", regle)
                occ = rrulestr("RRULE:" + regle, dtstart=d0)
                dates = occ.between(debut - longueur, fin, inc=True)
        except Exception as e:
            logger.debug("[AGENDA] Récurrence illisible (%s) : première occurrence seulement", type(e).__name__)
            dates = [d0]
        for o in dates:
            cle = (uid, o.astimezone(timezone.utc))
            if cle[1] in exclues:
                continue
            r = remplaces.pop(cle, None)
            if r is not None:
                try:
                    r0, rj = _instant(*r["DTSTART"])
                    rl = (_instant(*r["DTEND"])[0] - r0) if "DTEND" in r else longueur
                    ajouter(r, r0, rj, rl)
                except Exception:
                    pass
                continue
            ajouter(b, o, journee, longueur)
    for r in remplaces.values():          # une occurrence déplacée dont la date d'origine sort de la fenêtre
        try:
            r0, rj = _instant(*r["DTSTART"])
            ajouter(r, r0, rj, (_instant(*r["DTEND"])[0] - r0) if "DTEND" in r else timedelta(hours=1))
        except Exception:
            pass
    sortie.sort(key=lambda e: e.debut)
    return sortie


# --------------------------------------------------------------------------- #
#  Le téléchargement (remplacé par les tests)
# --------------------------------------------------------------------------- #

class AdresseRefusee(Exception):
    pass


class Injoignable(Exception):
    pass


def _telecharger(adresse: str) -> str:
    import httpx

    if not adresse.startswith("https://"):
        raise AdresseRefusee("l'adresse doit commencer par https://")
    try:
        r = httpx.get(adresse, timeout=20.0, follow_redirects=False)
    except Exception as e:
        raise Injoignable(type(e).__name__) from None
    if r.status_code in (401, 403, 404):
        raise AdresseRefusee(f"Google répond {r.status_code}")
    if r.status_code != 200:
        raise Injoignable(f"réponse {r.status_code}")
    if "BEGIN:VCALENDAR" not in r.text[:2000]:
        raise AdresseRefusee("ce n'est pas un agenda au format iCal")
    return r.text


telecharger = _telecharger

_cache: dict = {}
_verrou = threading.Lock()


def reinitialiser() -> None:
    with _verrou:
        _cache.clear()
        _prepares.clear()


def _ical() -> str:
    r = coffre.lire(SERVICE)
    if not r:
        raise LookupError
    with _verrou:
        if _cache.get("quand", 0) > time.monotonic() - CACHE_S:
            return _cache["texte"]
    texte = telecharger(r[1])
    with _verrou:
        _cache.update(quand=time.monotonic(), texte=texte)
    return texte


# --------------------------------------------------------------------------- #
#  Dire l'agenda
# --------------------------------------------------------------------------- #

def _h(d: datetime) -> str:
    from core.horloge import heure_fr

    return heure_fr(d.astimezone(_local()).replace(tzinfo=None))


def _jour_fr(d: date) -> str:
    from core import horloge

    aujourd = horloge.maintenant().date()
    if d == aujourd:
        return f"aujourd'hui ({horloge.date_fr(d, annee=False)})"
    if d == aujourd + timedelta(days=1):
        return f"demain ({horloge.date_fr(d, annee=False)})"
    return horloge.date_fr(d, annee=d.year != aujourd.year)


def _ligne(e: Evenement) -> str:
    lieu = f" ({e.lieu})" if e.lieu else ""
    if e.journee:
        return f"toute la journée : « {e.titre} »{lieu}"
    return f"{_h(e.debut)} – {_h(e.fin)} : « {e.titre} »{lieu}"


def _bornes(jour: date) -> tuple[datetime, datetime]:
    d0 = datetime.combine(jour, datetime.min.time()).replace(tzinfo=_local())
    return d0, d0 + timedelta(days=1)


def _pas_connecte() -> dict:
    return {"success": False, "message": "Ton agenda Google n'est pas connecté. Dis « connecte mon agenda Google » : "
            "une fenêtre d'Atlas t'explique où trouver ton adresse privée au format iCal, et tu la colles dans un "
            "champ masqué."}


def agenda_lire(p: dict) -> dict:
    """« Qu'est-ce que j'ai demain ? », « mon prochain rendez-vous », « je suis libre jeudi après-midi ? »."""
    from core import courrier, horloge

    refus = courrier._refus_origine()
    if refus:
        return refus
    try:
        texte = _ical()
    except LookupError:
        return _pas_connecte()
    except AdresseRefusee as e:
        from core_conversational import degradations

        degradations.signaler("agenda_refuse", f"adresse iCal refusée ({e})")
        return {"success": False, "message": f"Google refuse l'adresse privée de ton agenda ({e}) : elle a peut-être été "
                "réinitialisée. Dis « déconnecte mon agenda Google », puis « connecte mon agenda Google »."}
    except Injoignable as e:
        return {"success": False, "message": f"Google Agenda ne répond pas pour le moment ({e})."}
    now = horloge.maintenant().astimezone()
    if p.get("prochain"):
        evs = [e for e in analyser_ical(texte, now, now + timedelta(days=PROCHAIN_JOURS)) if e.debut >= now]
        if not evs:
            return {"success": True, "non_fiable": True,
                    "message": f"Aucun rendez-vous dans les {PROCHAIN_JOURS} prochains jours."}
        e = evs[0]
        return {"success": True, "non_fiable": True,
                "message": f"Ton prochain rendez-vous : {_jour_fr(e.debut.astimezone(_local()).date())}, {_ligne(e)}."}
    jour = date.fromisoformat(p["jour"]) if p.get("jour") else now.date()
    d0, d1 = _bornes(jour)
    if p.get("libre"):
        h0, h1 = p.get("de", 0), p.get("a", 24)
        f0 = d0 + timedelta(hours=h0)
        f1 = d0 + timedelta(hours=h1) if h1 < 24 else d1
        occupes = [e for e in analyser_ical(texte, f0, f1) if e.occupe]
        plage = f"{_jour_fr(jour)}{(' ' + p['plage']) if p.get('plage') else ''}"
        if not occupes:
            return {"success": True, "non_fiable": True,
                    "message": f"Oui : rien de prévu {plage} ({h0} h – {h1} h) dans ton agenda Google."}
        return {"success": True, "non_fiable": True,
                "message": f"Non, {plage} tu as :\n" + "\n".join(f"- {_ligne(e)}" for e in occupes)}
    evs = analyser_ical(texte, d0, d1)
    if not evs:
        return {"success": True, "non_fiable": True, "message": f"Rien de prévu {_jour_fr(jour)} dans ton agenda Google."}
    return {"success": True, "non_fiable": True,
            "message": f"{_jour_fr(jour)[:1].upper()}{_jour_fr(jour)[1:]} :\n" + "\n".join(f"- {_ligne(e)}" for e in evs)}


# --------------------------------------------------------------------------- #
#  Créer : le lien pré-rempli, après la confirmation
# --------------------------------------------------------------------------- #

_prepares: dict[str, dict] = {}


def lien_google(titre: str, debut: datetime, fin: datetime, journee: bool = False) -> str:
    if journee:
        dates = f"{debut:%Y%m%d}/{fin:%Y%m%d}"
    else:
        dates = (f"{debut.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}/"
                 f"{fin.astimezone(timezone.utc):%Y%m%dT%H%M%SZ}")
    return "https://calendar.google.com/calendar/render?" + urlencode(
        {"action": "TEMPLATE", "text": titre, "dates": dates})


def preparer_creation(p: dict) -> dict:
    """Avant la confirmation : la date, l'heure et le titre, résolus ici et montrés tels quels."""
    from core import courrier, horloge

    refus = courrier._refus_origine()
    if refus:
        return {"resultat": refus}
    titre = re.sub(r"\s+", " ", (p.get("titre") or "").strip())[:120] or "Rendez-vous"
    phrase = p.get("quand_texte") or ""
    now = horloge.maintenant()
    m = horloge.moment(phrase, now)
    if m.get("jour_sans_heure") or not m:
        return {"resultat": {"success": False, "message": f"À quelle heure, le rendez-vous « {titre} » ? Dis par "
                             "exemple « ajoute un rendez-vous chez le dentiste jeudi à 14 h »."}}
    if m.get("question"):
        return {"resultat": {"success": False, "message": m["question"] + " Redis-le avec l'heure exacte."}}
    debut = m["quand"]
    if debut < now:
        return {"resultat": {"success": False, "message": "Ce moment est déjà passé : je ne prépare pas le rendez-vous."}}
    duree = timedelta(minutes=int(p.get("duree_min") or 60))
    fin_dite = horloge.heure_dite(p.get("fin_texte") or "") if p.get("fin_texte") else None
    fin = debut.replace(hour=fin_dite["h"], minute=fin_dite["m"]) if fin_dite else debut + duree
    if fin <= debut:
        fin = debut + duree
    debut, fin = debut.replace(tzinfo=_local()), fin.replace(tzinfo=_local())
    jeton = _aleatoire.token_hex(4)
    with _verrou:
        _prepares[jeton] = {"titre": titre, "debut": debut, "fin": fin}
    jour = horloge.date_fr(debut.date())
    return {"params": {"jeton": jeton, "libelle": "ouvrir le rendez-vous pré-rempli dans Google Agenda"},
            "cible": f"Le {jour}, de {_h(debut)} à {_h(fin)} : « {titre} »\n(Google Agenda s'ouvre pré-rempli dans le "
                     "navigateur ; c'est toi qui enregistres.)"}


def agenda_creer(p: dict) -> dict:
    with _verrou:
        ev = _prepares.pop(p.get("jeton") or "", None)
    if not ev:
        return {"success": False, "message": "Je n'ouvre que le rendez-vous que tu as confirmé à l'écran : rien n'est ouvert."}
    import webbrowser

    webbrowser.open(lien_google(ev["titre"], ev["debut"], ev["fin"]), new=2)
    return {"success": True, "message": "J'ai ouvert le rendez-vous pré-rempli dans Google Agenda : enregistre-le là-bas."}
