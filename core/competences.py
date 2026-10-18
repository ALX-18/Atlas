"""
Sprint Compétences 1 — ce qu'Atlas DIT après avoir agi : l'heure, les rappels, le son, la lumière,
le Bluetooth, la musique.

Règle du sprint : agir, puis relire, puis dire. Chaque message est construit sur l'état RELU
(volume lu après le réglage, état de la radio relu, rappel relu dans la base) ; ce qui ne peut pas
être relu est dit tel quel (« J'envoie la mise en veille des écrans »). Jamais « c'est fait ».

Ce qui manque est demandé (`core.propositions`, réponse libre ou choix) ; rien n'est deviné.
Aucun appel au modèle ici (invariant 3).
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
from datetime import timedelta
from typing import Optional

from core import horloge

logger = logging.getLogger("atlas.competences")

_SETTINGS = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json"


def reglages() -> dict:
    defaut = {"pas_volume": 10, "pas_luminosite": 20}
    try:
        with open(_SETTINGS, encoding="utf-8") as f:
            return {**defaut, **(json.load(f).get("competences") or {})}
    except Exception:
        return defaut


def _ok(message: str, **extra) -> dict:
    return {"success": True, "message": message, **extra}


def _ko(message: str, **extra) -> dict:
    return {"success": False, "message": message, **extra}


def _proposer(**k) -> None:
    from core import propositions

    propositions.proposer(**k)


# --------------------------------------------------------------------------- #
#  CP1 — l'heure et la date
# --------------------------------------------------------------------------- #

def heure_dire(p: dict) -> dict:
    q = p.get("question") or horloge.question(p.get("phrase", ""))
    if not q:
        return _ko("Je n'ai pas compris la question sur l'heure ou la date.")
    return _ok(horloge.repondre(q))


# --------------------------------------------------------------------------- #
#  CP2 — minuteurs et rappels
# --------------------------------------------------------------------------- #

def _rappels():
    from core import rappels

    return rappels


def rappel_creer(p: dict) -> dict:
    r = _rappels()
    phrase, sorte, texte = p.get("phrase", ""), p.get("sorte", "rappel"), (p.get("texte") or "").strip()
    origine = p.get("_origine")
    now = horloge.maintenant()
    if sorte == "minuteur":
        d = horloge.duree(p.get("duree_texte") or phrase)
        if not d:
            _proposer(phrase=None, sorte="completer_minuteur", origine=origine, completer="mets un minuteur de")
            return _ok("De combien de temps, le minuteur ? (par exemple « 10 minutes »)")
        if d > timedelta(days=1):
            return _ko(f"Un minuteur de {horloge.duree_fr(d)}, c'est plus d'un jour : dis plutôt « rappelle-moi "
                       "demain à … de … ».")
        rec = r.ajouter("minuteur", texte, now + d, origine=origine)
        relu = r.lire(rec["id"])
        return _ok(f"Minuteur de {horloge.duree_fr(relu['echeance'] - now)} lancé{' (' + texte + ')' if texte else ''} : "
                   f"il sonnera à {horloge.heure_fr(relu['echeance'])}.", rappel_id=relu["id"])

    quoi = p.get("quoi_brut") or (f"de {texte}" if texte else "")
    rec_def = horloge.recurrence(phrase)
    if rec_def:
        premier = horloge.prochaine(rec_def, now)
        rec = r.ajouter("rappel", texte, premier, recurrence=rec_def, origine=origine)
        relu = r.lire(rec["id"])
        return _ok(f"C'est enregistré : je te rappellerai « {texte or 'ton rappel'} » "
                   f"{horloge.recurrence_fr(relu['recurrence'])} (la première fois {horloge.quand_fr(relu['echeance'], now)}).",
                   rappel_id=relu["id"])
    m = horloge.moment(phrase, now)
    if "question" in m:
        options = [f"rappelle-moi {quoi} {libelle}".replace("  ", " ") for libelle, _ in m["options"]]
        _proposer(phrase=None, sorte="choix_heure_rappel", origine=origine, options=options)
        return _ok(f"{m['question']} Dis « la 1 » ou « la 2 ».")
    if "quand" not in m:
        if "jour_sans_heure" in m:
            jour = horloge.date_fr(m["jour_sans_heure"], annee=False)
            _proposer(phrase=None, sorte="completer_rappel", origine=origine,
                      completer=f"rappelle-moi {quoi} le {jour} à")
            return _ok(f"À quelle heure, {jour} ?")
        _proposer(phrase=None, sorte="completer_rappel", origine=origine, completer=f"rappelle-moi {quoi}".strip())
        return _ok("Quand veux-tu que je te le rappelle ? (par exemple « dans 20 minutes » ou « demain à 9 h »)")
    quand = m["quand"]
    if quand <= now:
        return _ko(f"Ce moment est déjà passé ({horloge.quand_fr(quand, now)}) : dis-moi un moment à venir.")
    rec = r.ajouter("rappel", texte, quand, origine=origine)
    relu = r.lire(rec["id"])
    ecart = relu["echeance"] - now
    dans = f" (dans {horloge.duree_fr(ecart)})" if ecart < timedelta(hours=12) else ""
    return _ok(f"C'est enregistré : je te rappellerai « {texte or 'ton rappel'} » "
               f"{horloge.quand_fr(relu['echeance'], now)}{dans}.", rappel_id=relu["id"])


def _anciennes_taches_rappel() -> int:
    try:
        from core.scheduler import get_scheduler

        return sum(1 for j in get_scheduler()._jobs.values() if (j.name or "").lower().startswith("rappel"))
    except Exception:
        return 0


def rappel_lister(p: dict) -> dict:
    r = _rappels()
    actifs = r.actifs()
    now = horloge.maintenant()
    if p.get("minuteurs_seulement"):
        actifs = [a for a in actifs if a["sorte"] == "minuteur"]
    if not actifs:
        texte = "Tu n'as aucun minuteur en cours." if p.get("minuteurs_seulement") else \
            "Tu n'as aucun rappel ni minuteur en cours."
    else:
        lignes = [f"{k + 1}. {r.libelle(a, now)}" for k, a in enumerate(actifs)]
        nb = len(actifs)
        texte = f"{'Un rappel en cours' if nb == 1 else f'{nb} rappels en cours'} :\n" + "\n".join(lignes)
    anciens = _anciennes_taches_rappel()
    if anciens:
        texte += (f"\n(Il reste aussi {anciens} tâche{'s' if anciens > 1 else ''} planifiée{'s' if anciens > 1 else ''} "
                  "de l'ancien système de rappels : dis « liste mes tâches ».)")
    return _ok(texte)


def rappel_annuler(p: dict) -> dict:
    r = _rappels()
    origine = p.get("_origine")
    now = horloge.maintenant()
    if p.get("id"):
        avant = r.lire(int(p["id"]))
        if not avant or avant["etat"] != "actif":
            return _ko("Ce rappel n'est plus actif.")
        r.annuler(avant["id"])
        relu = r.lire(avant["id"])
        if relu["etat"] == "annule":
            nom = "le minuteur" + (f" ({avant['texte']})" if avant["texte"] else "") if avant["sorte"] == "minuteur" \
                else f"le rappel « {avant['texte'] or 'sans objet'} »"
            return _ok(f"J'ai annulé {nom}.")
        return _ko("Je n'ai pas réussi à annuler ce rappel.")
    actifs = r.actifs()
    quoi = horloge.plat(p.get("quoi") or "").strip()
    cands = [a for a in actifs if a["sorte"] == "minuteur"] if p.get("sorte") == "minuteur" else list(actifs)
    if quoi:
        mots = [m for m in re.findall(r"\w+", quoi) if len(m) > 2 and m not in ("les", "des", "mon", "pour")]
        cands = [a for a in cands if all(m in horloge.plat(a["texte"]) for m in mots)]
    if not cands:
        if not actifs:
            return _ko("Tu n'as aucun rappel ni minuteur en cours.")
        return _ko(f"Je ne trouve aucun rappel qui corresponde{' à « ' + p['quoi'] + ' »' if p.get('quoi') else ''}. "
                   + rappel_lister({})["message"])
    if len(cands) > 1:
        options = [f"annule le rappel #{a['id']}" for a in cands[:6]]
        _proposer(phrase=None, sorte="choix_rappel", origine=origine, options=options)
        lignes = "\n".join(f"{k + 1}. {r.libelle(a, now)}" for k, a in enumerate(cands[:6]))
        return _ok(f"Plusieurs rappels correspondent :\n{lignes}\nLequel j'annule ? Dis « le 1 », « le 2 »…")
    return rappel_annuler({**p, "id": cands[0]["id"]})


# --------------------------------------------------------------------------- #
#  CP3 — le son
# --------------------------------------------------------------------------- #

def son_regler(p: dict) -> dict:
    from tools import son

    action, niveau, programme = p.get("action"), p.get("niveau"), p.get("programme")
    pas = int(reglages()["pas_volume"])
    delta = {"monter": pas, "baisser": -pas}.get(action)
    if action == "regler" and niveau is None:
        return _ko("À combien ? Dis par exemple « mets le son à 40 % ».")
    muet = {"couper": True, "retablir": False}.get(action)
    try:
        if programme:
            r = son.regler_programme(programme, niveau=niveau if action == "regler" else None,
                                     delta=delta, muet=muet)
            if not r["trouves"]:
                progs = sorted({x["processus"][:-4] if x["processus"].lower().endswith(".exe") else x["processus"]
                                for x in son.MATERIEL.programmes()})
                return _ko(f"Je ne trouve pas de son venant de « {programme} » en ce moment."
                           + (f" Programmes qui ont une sortie audio : {', '.join(progs)}." if progs else ""))
            apres, avant, nom = r["apres"], r["avant"], r["nom"]
            if apres is None:
                return _ko(f"Je n'ai pas pu relire le son de {nom} après le réglage.")
            if action == "couper":
                return _ok(f"Son de {nom} coupé." if apres["muet"] else
                           f"J'ai demandé de couper le son de {nom}, mais Windows le donne toujours actif.")
            if action == "retablir":
                return _ok(f"Son de {nom} rétabli, à {apres['niveau']} %." if not apres["muet"] else
                           f"J'ai demandé de rétablir le son de {nom}, mais il est toujours coupé.")
            if apres["niveau"] == avant["niveau"]:
                return _ok(_inchange(f"le son de {nom}", action, niveau, apres["niveau"]))
            return _ok(f"Le son de {nom} est maintenant à {apres['niveau']} % (il était à {avant['niveau']} %).")
        if action == "etat":
            e = son.etat()
            return _ok(f"Le volume est à {e['niveau']} %{', son coupé' if e['muet'] else ''}.")
        r = son.regler(niveau=niveau if action == "regler" else None, delta=delta, muet=muet)
    except Exception as e:
        logger.warning("Son : %s", e)
        return _ko(f"Je n'arrive pas à régler le son : {e}.")
    avant, apres = r["avant"], r["apres"]
    if action == "couper":
        return _ok(f"Son coupé (le volume reste à {apres['niveau']} %)." if apres["muet"] else
                   "J'ai demandé de couper le son, mais Windows le donne toujours actif.")
    if action == "retablir":
        return _ok(f"Son rétabli : volume à {apres['niveau']} %." if not apres["muet"] else
                   "J'ai demandé de rétablir le son, mais il est toujours coupé.")
    retabli = " Le son était coupé : je l'ai rétabli." if avant["muet"] and not apres["muet"] else ""
    if apres["niveau"] == avant["niveau"]:
        return _ok(_inchange("le volume", action, niveau, apres["niveau"]) + retabli)
    return _ok(f"Volume à {apres['niveau']} % (il était à {avant['niveau']} %).{retabli}")


def _inchange(quoi: str, action: str, niveau: Optional[int], relu: int) -> str:
    """Le niveau relu n'a pas bougé : rien à faire (borne, valeur déjà là), ou l'ordre a été ignoré."""
    Quoi = quoi[0].upper() + quoi[1:]
    if action == "monter" and relu >= 100:
        return f"{Quoi} est déjà à 100 % (c'est le maximum)."
    if action == "baisser" and relu <= 0:
        return f"{Quoi} est déjà à 0 % (c'est le minimum)."
    if action == "regler" and niveau is not None and relu == max(0, min(100, niveau)):
        return f"{Quoi} est déjà à {relu} %."
    verbe = {"monter": "monter", "baisser": "baisser", "regler": "régler"}.get(action, "changer")
    return f"J'ai demandé de {verbe} {quoi}, mais il est toujours à {relu} %."


# --------------------------------------------------------------------------- #
#  CP4 — la luminosité et les écrans
# --------------------------------------------------------------------------- #

def luminosite_regler(p: dict) -> dict:
    from tools import affichage

    action, niveau = p.get("action"), p.get("niveau")
    pas = int(reglages()["pas_luminosite"])
    try:
        if action == "etat":
            ecr = affichage.ecrans()
            if not ecr:
                return _ko("Je ne trouve aucun écran dont je puisse lire la luminosité.")
            return _ok("Luminosité : " + ", ".join(
                f"{e['nom']} à {e['niveau']} %" if e["niveau"] is not None else f"{e['nom']} illisible (refuse DDC/CI)"
                for e in ecr) + ".")
        res = affichage.regler_luminosite(niveau=niveau if action == "regler" else None,
                                          delta={"monter": pas, "baisser": -pas}.get(action), ecran=p.get("ecran"))
    except Exception as e:
        logger.warning("Luminosité : %s", e)
        return _ko(f"Je n'arrive pas à régler la luminosité : {e}.")
    if not res:
        return _ko("Je ne trouve aucun écran dont je puisse régler la luminosité"
                   + (f" (pas d'écran {p['ecran']})." if p.get("ecran") else "."))
    morceaux, reussis = [], 0
    for r in res:
        if "refus" in r:
            morceaux.append(f"{r['nom']} : {r['refus']}")
        elif r.get("relu") is None:
            morceaux.append(f"{r['nom']} : réglé à {r['demande']} %, mais je n'ai pas pu le relire")
        else:
            reussis += 1
            morceaux.append(f"{r['nom']} à {r['relu']} %" + (f" (il était à {r['avant']} %)" if r["avant"] != r["relu"] else
                                                             " (inchangé)"))
    if not reussis and all("refus" in r for r in res):
        return _ko("Aucun écran n'a accepté le réglage : " + " ; ".join(morceaux) + ".")
    return _ok("Luminosité : " + " ; ".join(morceaux) + ".")


def ecrans_veille(p: dict) -> dict:
    from tools import affichage

    try:
        affichage.veille_ecrans(delai_s=float(p.get("delai_s", 1.0)))
    except Exception as e:
        return _ko(f"Je n'ai pas pu envoyer la mise en veille des écrans : {e}.")
    return _ok("J'envoie la mise en veille des écrans dans une seconde. Je ne peux pas le vérifier : un écran en "
               "veille ne répond plus. Bouge la souris ou appuie sur une touche pour les rallumer.")


# --------------------------------------------------------------------------- #
#  CP5 — le Bluetooth
# --------------------------------------------------------------------------- #

_ETATS_BT = {"allume": "allumé", "eteint": "éteint", "indisponible": "indisponible (coupé par le matériel ou le "
                                                                     "mode avion)"}
PAS_DE_BLUETOOTH = ("Ce PC n'a pas de Bluetooth utilisable : Windows ne voit aucune radio Bluetooth (adaptateur "
                    "absent, débranché ou désactivé dans le Gestionnaire de périphériques).")


def bluetooth_a_confirmer(p: dict) -> Optional[str]:
    """Le motif de confirmation avant d'éteindre, ou None. Appelé par le moteur AVANT d'agir."""
    from tools import bluetooth

    if p.get("allume") or p.get("_confirme"):
        return None
    try:
        if bluetooth.etat() != "allume":
            return None
        saisie = bluetooth.saisie_connectee()
    except Exception as e:
        return f"je n'ai pas pu vérifier si un clavier ou une souris Bluetooth est connecté ({e})"
    if not saisie:
        return None
    noms = ", ".join(f"« {a['nom']} » ({a['saisie']})" for a in saisie)
    return f"{noms} sera déconnecté : tu pourrais perdre la main sur ton PC"


def bluetooth_regler(p: dict) -> dict:
    from tools import bluetooth

    allume = bool(p.get("allume"))
    voulu = "allume" if allume else "eteint"
    try:
        if p.get("action") == "etat":
            e = bluetooth.etat()
            return _ok(PAS_DE_BLUETOOTH if e is None else f"Le Bluetooth est {_ETATS_BT[e]}.")
        r = bluetooth.regler(allume)
    except Exception as e:
        logger.warning("Bluetooth : %s", e)
        return _ko(f"Je n'arrive pas à piloter le Bluetooth : {e}.")
    if r["issue"] == "pas_de_radio":
        return _ko(PAS_DE_BLUETOOTH)
    if r["avant"] == voulu:
        return _ok(f"Le Bluetooth est déjà {_ETATS_BT[voulu]}.")
    if r["issue"].startswith("acces"):
        return _ko("Windows refuse à Atlas l'accès à la radio Bluetooth (Paramètres > Confidentialité > Radios).")
    if r["apres"] == voulu:
        return _ok(f"Le Bluetooth est maintenant {_ETATS_BT[voulu]}.")
    verbe = "d'allumer" if allume else "d'éteindre"
    return _ko(f"J'ai demandé à Windows {verbe} le Bluetooth, mais il est toujours {_ETATS_BT.get(r['apres'], '?')}.")


def bluetooth_connecter(p: dict) -> dict:
    from tools import bluetooth

    nom = (p.get("nom") or "").strip()
    try:
        if bluetooth.etat() is None:
            return _ko(PAS_DE_BLUETOOTH)
        trouves = bluetooth.trouver_appaire(nom)
    except Exception as e:
        return _ko(f"Je n'arrive pas à lire les appareils Bluetooth : {e}.")
    if not trouves:
        tous = sorted({a["nom"] for a in bluetooth.MATERIEL.appaires()})
        return _ko(f"Je ne trouve aucun appareil appairé qui s'appelle « {nom} »."
                   + (f" Appareils appairés : {', '.join(tous)}." if tous else " Aucun appareil n'est appairé."))
    if len(trouves) == 1 and trouves[0]["connecte"]:
        return _ok(f"« {trouves[0]['nom']} » est déjà connecté.")
    try:
        bluetooth.MATERIEL.ouvrir_parametres()
        ouvert = "J'ai demandé l'ouverture des paramètres Bluetooth"
    except Exception:
        ouvert = "Je n'ai pas pu ouvrir les paramètres Bluetooth"
    cible = f"« {trouves[0]['nom']} »" if len(trouves) == 1 else \
        "un appareil (appairés : " + ", ".join(a["nom"] for a in trouves) + ")"
    return _ok(f"Windows ne permet pas à Atlas de connecter {cible} proprement. {ouvert} : clique sur l'appareil, "
               "puis sur « Connecter ».")


# --------------------------------------------------------------------------- #
#  CP6 — la musique
# --------------------------------------------------------------------------- #

def _titre(s: dict) -> str:
    if not s or not s.get("titre"):
        return ""
    return f"« {s['titre']} »" + (f" — {s['artiste']}" if s.get("artiste") else "")


_LIBELLE_STATUT = {"lecture": "en lecture", "pause": "en pause", "arrêté": "à l'arrêt"}


def musique_commande(p: dict) -> dict:
    from tools import musique

    cmd = p.get("commande")
    try:
        if cmd == "quoi":
            s = musique.MATERIEL.courante()
            if not s:
                return _ok("Aucun lecteur ne publie de lecture à Windows en ce moment.")
            if not s.get("titre"):
                return _ok(f"{s['appli']} est {_LIBELLE_STATUT.get(s['statut'], s['statut'])}, sans titre publié.")
            return _ok(f"En ce moment dans {s['appli']} : {_titre(s)} ({_LIBELLE_STATUT.get(s['statut'], s['statut'])}).")
        r = musique.commander(cmd)
    except Exception as e:
        logger.warning("Musique : %s", e)
        return _ko(f"Je n'arrive pas à joindre les lecteurs : {e}.")
    avant, apres = r["avant"], r["apres"]
    if avant is None:
        if cmd == "lecture" and p.get("sans_recherche"):
            _proposer(phrase=None, sorte="completer_musique", origine=p.get("_origine"), completer="mets")
            return _ok("Aucun lecteur n'est ouvert. Que veux-tu écouter ? (par exemple « du Daft Punk »)")
        return _ko("Aucun lecteur ne publie de lecture à Windows en ce moment : je n'ai rien à commander.")
    if not r["envoye"]:
        return _ko(f"{avant['appli']} a refusé la commande.")
    appli = (apres or avant)["appli"]
    if apres is None:
        return _ko(f"J'ai envoyé la commande à {appli}, mais je ne peux plus relire son état.")
    if cmd == "pause":
        if avant["statut"] == "pause":
            return _ok(f"{appli} est déjà en pause{' : ' + _titre(apres) if _titre(apres) else ''}.")
        return _ok(f"Pause dans {appli}{' : ' + _titre(apres) if _titre(apres) else ''}." if apres["statut"] == "pause"
                   else f"J'ai demandé la pause à {appli}, mais il indique toujours « {apres['statut']} ».")
    if cmd == "lecture":
        if avant["statut"] == "lecture":
            return _ok(f"{appli} est déjà en lecture{' : ' + _titre(apres) if _titre(apres) else ''}.")
        return _ok(f"Lecture reprise dans {appli}{' : ' + _titre(apres) if _titre(apres) else ''}."
                   if apres["statut"] == "lecture" else
                   f"J'ai demandé la lecture à {appli}, mais il indique toujours « {apres['statut']} ».")
    if cmd in ("suivant", "precedent"):
        mot = "suivant" if cmd == "suivant" else "précédent"
        if (apres["titre"], apres["artiste"]) != (avant["titre"], avant["artiste"]):
            return _ok(f"Morceau {mot} dans {appli} : {_titre(apres)}.")
        return _ok(f"J'ai demandé le morceau {mot} à {appli}, mais le titre affiché n'a pas changé"
                   f"{' (' + _titre(apres) + ')' if _titre(apres) else ''}.")
    return _ok(f"{appli} : {_LIBELLE_STATUT.get(apres['statut'], apres['statut'])}.")


_CLE_SERVICE = "musique.service"


def service_prefere() -> Optional[str]:
    from core import apprentissage_store as store

    try:
        return store.etat(_CLE_SERVICE)
    except Exception as e:
        logger.warning("Service de musique : préférence illisible (%s)", e)
        return None


def _retenir_service(service: str) -> Optional[str]:
    from core import apprentissage_store as store

    store.fixer_etat(_CLE_SERVICE, service)
    return store.etat(_CLE_SERVICE)


def musique_service(p: dict) -> dict:
    from tools import musique

    if p.get("action") == "lire":
        s = service_prefere()
        return _ok(f"Pour la musique, tu utilises {musique.SERVICES[s]['nom']}." if s in musique.SERVICES else
                   "Tu ne m'as pas encore dit quel service de musique tu utilises.")
    service = musique.service_connu(p.get("service") or "")
    if not service:
        return _ko(f"Je ne connais pas le service « {p.get('service')} ». Je connais Spotify, Deezer, Apple Music et "
                   "YouTube Music.")
    relu = _retenir_service(service)
    if relu != service:
        return _ko("Je n'ai pas réussi à retenir ton service de musique.")
    return _ok(f"C'est noté : {musique.SERVICES[relu]['nom']} pour la musique.")


def musique_chercher(p: dict) -> dict:
    from tools import musique

    recherche = (p.get("recherche") or "").strip()
    origine = p.get("_origine")
    if not recherche:
        return musique_commande({**p, "commande": "lecture", "sans_recherche": True})
    dit = p.get("service_dit")
    service = musique.service_connu(dit) if dit else None
    if dit and not service:
        _proposer(phrase=f"mets {recherche} sur YouTube Music dans le navigateur", sorte="musique_navigateur",
                  origine=origine)
        return _ok(f"Je ne connais pas « {dit} ». Je connais Spotify, Deezer, Apple Music et YouTube Music. "
                   "Je peux ouvrir la recherche dans ton navigateur, sur YouTube Music : tu veux ?")
    prefere = service_prefere()
    retenu = ""
    if not service:
        service = prefere
    elif not prefere and not p.get("web"):
        if _retenir_service(service) == service:          # demandé une fois, puis retenu
            retenu = (f" Je retiens {musique.SERVICES[service]['nom']} pour la musique (pour changer : "
                      "« j'utilise Deezer maintenant »).")
    if not service:
        _proposer(phrase=None, sorte="completer_service_musique", origine=origine,
                  completer=f"mets {recherche} — service :")
        return _ok("Quel service de musique utilises-tu : Spotify, Deezer, Apple Music ou YouTube Music ?")
    nom = musique.SERVICES[service]["nom"]
    web = bool(p.get("web"))
    if not web and not musique.installe(service):
        _proposer(phrase=f"mets {recherche} sur {nom} dans le navigateur", sorte="musique_navigateur", origine=origine)
        return _ok(f"{nom} n'a pas l'air installé sur ce PC.{retenu} Je peux ouvrir la recherche dans ton navigateur : "
                   "tu veux ?")
    adresse = musique.adresse(service, recherche, web=web)
    try:
        musique.MATERIEL.ouvrir(adresse)
    except Exception as e:
        # Mesuré le 18/10 : Apple Music (application du Store) déclare « music:// » mais ne s'ouvre pas
        # depuis un programme de bureau. Atlas le dit et propose le navigateur, sans message système brut.
        logger.warning("Musique : ouverture de %s impossible (%s)", adresse, e)
        if web:
            return _ko(f"Je n'ai pas pu ouvrir la recherche dans ton navigateur ({type(e).__name__}).")
        _proposer(phrase=f"mets {recherche} sur {nom} dans le navigateur", sorte="musique_navigateur", origine=origine)
        return _ok(f"Je n'arrive pas à ouvrir l'application {nom} sur ce PC.{retenu} Je peux ouvrir la recherche dans "
                   "ton navigateur : tu veux ?")
    ou = "dans ton navigateur" if web or not musique.SERVICES[service]["app"] else f"dans {nom}"
    precision = f" sur {nom}" if ou == "dans ton navigateur" else ""
    return _ok(f"J'ai ouvert la recherche « {recherche} » {ou}{precision}. À toi de choisir le morceau : je ne lance pas "
               f"la lecture moi-même.{retenu}")
