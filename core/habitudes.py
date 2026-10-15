"""
Sprint Apprentissage 2 / AQ4 — tes habitudes. Atlas PROPOSE, il n'exécute jamais de lui-même.

Calcul déterministe, à partir du journal des actions réelles d'Alexis (`data/atlas_actions.jsonl`,
entrées dont l'origine est celle d'Alexis — bureau, fenêtre, voix ; une entrée sans origine, écrite
avant ce sprint ou par un script, ne compte pas) :

- **enchaînement** : l'application B ouverte dans les N minutes qui suivent A, au moins K fois, sur
  au moins D jours différents ;
- **heure** : une application ou un mode ouvert dans la même tranche horaire, au moins K fois, sur
  au moins D jours différents.

N, K, D, la tranche et la limite horaire sont dans `config/settings.json`
(`apprentissage.habitudes`) ; valeurs et justification dans `docs/CONFIGURATION.md`.

Ce qu'Atlas en fait : après une réponse, il peut ajouter UNE question à la fin (« Tu ouvres
souvent Discord après Steam. Je l'ouvre ? »). Un « oui » route la demande par le chemin normal,
avec ses confirmations. Au plus une proposition par habitude et par jour, au plus X par heure
au total. « arrête de me proposer ça » écarte l'habitude (un enregistrement, listable et
effaçable) ; « arrête les suggestions » / « reprends les suggestions » : interrupteur global.
Aucun modèle de langue ici (invariant 3).
"""

from __future__ import annotations

import hashlib
import json
import logging
import pathlib
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("atlas.habitudes")

_SETTINGS = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json"


def _charger_config() -> dict:
    try:
        config = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Habitudes : configuration illisible (%s) — valeurs par défaut", e)
        return {}
    return dict(config.get("apprentissage", {}).get("habitudes", {}))


_CFG = _charger_config()

OUTILS_OUVERTURE = {"launch_app": "app", "window_focus": "app", "workflow_run": "mode"}
RESULTATS_OK = {"success", "retry_success"}


def _seuils() -> dict:
    return {
        "n_min": float(_CFG.get("enchainement_minutes", 10)),
        "k": int(_CFG.get("occurrences_min", 3)),
        "d": int(_CFG.get("jours_min", 3)),
        "tranche": max(1, int(_CFG.get("tranche_minutes", 60))),
        "par_heure": int(_CFG.get("max_propositions_par_heure", 2)),
    }


def _maintenant() -> datetime:
    return datetime.now()


def nom_app(nom: str) -> str:
    """La clé d'une application : normalisée, tirets en espaces (« bloc-notes » = « bloc notes »)."""
    from core.apprentissage import normaliser

    return " ".join(normaliser(nom).replace("-", " ").split())


def _id(prefixe: str, cle: str) -> str:
    return f"{prefixe}_{hashlib.sha1(cle.encode('utf-8')).hexdigest()[:16]}"


# --------------------------------------------------------------------------- #
#  Le journal → les ouvertures faites par Alexis
# --------------------------------------------------------------------------- #

def evenements(chemin: Optional[pathlib.Path] = None, toutes_origines: bool = False) -> list[dict]:
    """Ouvertures réussies, dans l'ordre : {quand, app, sorte (app|mode), phrase}.

    toutes_origines=True : lecture du journal d'avant ce sprint (sans origine), pour le rapport
    seulement — jamais pour proposer.
    """
    from core import atlas_logger
    from core.apprentissage import ORIGINES_ALEXIS

    chemin = pathlib.Path(chemin or atlas_logger.LOG_FILE)
    if not chemin.exists():
        return []
    out = []
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            try:
                e = json.loads(ligne)
            except ValueError:
                continue
            outil = e.get("tool")
            if outil not in OUTILS_OUVERTURE or e.get("result") not in RESULTATS_OK:
                continue
            if not toutes_origines and e.get("origine") not in ORIGINES_ALEXIS:
                continue
            if outil == "window_focus" and not str(e.get("intent", "")).endswith("/open"):
                continue          # « mets X au premier plan » n'est pas une ouverture
            if str(e.get("user_input") or "").startswith(("workflow:", "automation:")):
                continue          # étape d'un mode ou d'une automatisation : le mode compte, pas ses étapes
            app = nom_app(str(e.get("target") or ""))
            if not app:
                continue
            try:
                quand = datetime.fromisoformat(e["timestamp"])
            except (KeyError, ValueError):
                continue
            out.append({"quand": quand, "app": app, "sorte": OUTILS_OUVERTURE[outil],
                        "phrase": e.get("user_input") or f"ouvre {app}"})
    out.sort(key=lambda x: x["quand"])
    return out


def detecter(evts: Optional[list[dict]] = None) -> list[dict]:
    """Les habitudes du journal, triées (déterministe : mêmes événements → même liste)."""
    s = _seuils()
    evts = evenements() if evts is None else evts
    derniere_phrase = {e["app"]: e["phrase"] for e in evts}
    sorte = {e["app"]: e["sorte"] for e in evts}
    habitudes = []

    # Enchaînement A → B : chaque ouverture de A compte une fois pour B si B suit dans N minutes.
    paires: dict[tuple[str, str], list] = defaultdict(list)
    for i, a in enumerate(evts):
        vus = set()
        for b in evts[i + 1:]:
            if b["quand"] - a["quand"] > timedelta(minutes=s["n_min"]):
                break
            if b["app"] != a["app"] and b["app"] not in vus:
                vus.add(b["app"])
                paires[(a["app"], b["app"])].append(a["quand"].date())
    for (a, b), dates in sorted(paires.items()):
        if len(dates) >= s["k"] and len(set(dates)) >= s["d"]:
            habitudes.append({"sorte": "enchainement", "a": a, "b": b, "fois": len(dates), "jours": len(set(dates)),
                              "phrase": derniere_phrase[b], "cible": b, "type_cible": sorte[b],
                              "cle": f"enchainement|{a}|{b}"})

    # Heure : même tranche horaire.
    tranches: dict[tuple[str, int], list] = defaultdict(list)
    for e in evts:
        t = (e["quand"].hour * 60 + e["quand"].minute) // s["tranche"]
        tranches[(e["app"], t)].append(e["quand"].date())
    for (app, t), dates in sorted(tranches.items()):
        if len(dates) >= s["k"] and len(set(dates)) >= s["d"]:
            habitudes.append({"sorte": "horaire", "app": app, "tranche": t, "heure": t * s["tranche"] // 60,
                              "fois": len(dates), "jours": len(set(dates)), "phrase": derniere_phrase[app],
                              "cible": app, "type_cible": sorte[app], "cle": f"horaire|{app}|{t}"})
    return habitudes


def decrire(h: dict) -> str:
    verbe = "lances souvent le mode" if h["type_cible"] == "mode" else "ouvres souvent"
    if h["sorte"] == "enchainement":
        return f"tu {verbe} {h['b']} après {h['a']}"
    return f"tu {verbe} {h['app']} vers {h['heure']} h"


# --------------------------------------------------------------------------- #
#  Écartées par Alexis (« arrête de me proposer ça », « oublie… »)
# --------------------------------------------------------------------------- #

def _ecartees() -> set[str]:
    from core import apprentissage

    return {r["details"].get("cle") for r in apprentissage.lister_enregistrements() if r["type"] == "habitude_ecartee"}


def actives() -> list[dict]:
    from core import apprentissage

    if apprentissage.neutralise():
        return []
    ecartees = _ecartees()
    return [h for h in detecter() if h["cle"] not in ecartees]


def ecarter(h: dict, origine: Optional[str], confirme: bool = False) -> bool:
    """confirme=True : « oublie… », passé par la confirmation d'Alexis (dialogue à l'écran)."""
    from core import apprentissage

    if apprentissage.neutralise() or (not confirme and origine not in apprentissage.ORIGINES_ALEXIS):
        return False
    libelle = f"Habitude écartée : {decrire(h)} — je ne la propose plus"
    return apprentissage._ecrire(_id("habx", h["cle"]), libelle,
                                 {"type": "habitude_ecartee", "cle": h["cle"], "origine": origine})


def comme_enregistrements() -> list[dict]:
    """Les habitudes actives, présentées comme ce qui est appris (listables, « oubliables »)."""
    return [{"id": _id("hab", h["cle"]), "type": "habitude",
             "libelle": f"Habitude : {decrire(h)} ({h['fois']} fois sur {h['jours']} jours)",
             "details": {"cle": h["cle"]}, "depuis": ""} for h in actives()]


def oublier_virtuelles(ids: list[str]) -> list[str]:
    """« Oublier » une habitude calculée (après la confirmation d'Alexis) : l'écarter."""
    if not any(str(i).startswith("hab_") for i in ids):
        return []
    par_id = {_id("hab", h["cle"]): h for h in actives()}
    faits = []
    for i in ids:
        if i in par_id and ecarter(par_id[i], None, confirme=True):
            faits.append(i)
    return faits


# --------------------------------------------------------------------------- #
#  Proposer, après une réponse
# --------------------------------------------------------------------------- #

_derniere: Optional[dict] = None      # la dernière habitude proposée (pour « arrête de me proposer ça »)


def suggestions_actives() -> bool:
    from core import apprentissage_store as store

    try:
        return store.etat("suggestions", "on") != "off"
    except Exception:
        return False


def proposition(outil: Optional[str], params: Optional[dict], reussi: bool, origine: Optional[str]) -> Optional[str]:
    """La question à ajouter à la fin de la réponse, ou None. Enregistre la proposition."""
    global _derniere
    from core import apprentissage, propositions
    from core import apprentissage_store as store

    if apprentissage.neutralise() or origine not in apprentissage.ORIGINES_ALEXIS:
        return None
    if propositions.en_attente() or not suggestions_actives():
        return None                     # une seule question à la fois ; interrupteur global
    s = _seuils()
    maintenant = _maintenant()
    try:
        if store.propositions_depuis(time.time() - 3600) >= s["par_heure"]:
            return None
        habitudes = actives()
        if not habitudes:
            return None
        evts = evenements()
        ouvert = None
        if reussi and outil in OUTILS_OUVERTURE:
            p = params or {}
            ouvert = nom_app(str(p.get("name") or p.get("title") or p.get("workflow_id") or ""))
        recents = {e["app"] for e in evts if maintenant - e["quand"] <= timedelta(minutes=s["n_min"])}
        aujourdhui = {e["app"] for e in evts if e["quand"].date() == maintenant.date()}
        if ouvert:
            recents.add(ouvert)
            aujourdhui.add(ouvert)
        tranche = (maintenant.hour * 60 + maintenant.minute) // s["tranche"]
        candidates = [h for h in habitudes if h["sorte"] == "enchainement" and h["a"] == ouvert
                      and h["b"] not in recents]
        candidates += [h for h in habitudes if h["sorte"] == "horaire" and h["tranche"] == tranche
                       and h["app"] not in aujourdhui]
        debut_du_jour = datetime.combine(maintenant.date(), datetime.min.time()).timestamp()
        for h in candidates:
            if store.propositions_depuis(debut_du_jour, cle=h["cle"]):
                continue                # au plus une fois par habitude et par jour
            store.noter_proposition(h["cle"])
            propositions.proposer(h["phrase"], "habitude", origine, cle=h["cle"])
            _derniere = {**h, "quand": time.monotonic()}
            question = "Je le lance ?" if h["type_cible"] == "mode" else "Je l'ouvre ?"
            texte = decrire(h)
            logger.info("[HABITUDE] proposée : %s", texte)
            return f"{texte[0].upper()}{texte[1:]}. {question}"
    except Exception as e:
        logger.warning("Habitudes : proposition impossible (%s)", e)
        apprentissage._signaler_indisponible(f"habitudes illisibles ({e})")
    return None


# --------------------------------------------------------------------------- #
#  Commandes d'Alexis (déterministes, sur la phrase normalisée)
# --------------------------------------------------------------------------- #

_ARRETER_CA = {"arrete de me proposer ca", "arrete de me le proposer", "ne me propose plus ca", "arrete de proposer ca",
               "ne me le propose plus", "arrete avec ca", "arrete de me proposer ca stp"}
_ARRETER_TOUT = {"arrete les suggestions", "arrete tes suggestions", "plus de suggestions", "stop suggestions",
                 "desactive les suggestions", "coupe les suggestions"}
_REPRENDRE = {"reprends les suggestions", "reprend les suggestions", "active les suggestions",
              "remets les suggestions", "relance les suggestions"}


def commande(phrase: str, origine: Optional[str]) -> Optional[str]:
    """Réponse directe à « arrête de me proposer ça » / « arrête les suggestions » / « reprends… »."""
    global _derniere
    from core import apprentissage, propositions
    from core import apprentissage_store as store

    n = apprentissage.normaliser(phrase).replace("'", " ").strip(" !.?,")
    if origine not in apprentissage.ORIGINES_ALEXIS or n not in _ARRETER_CA | _ARRETER_TOUT | _REPRENDRE:
        return None
    if n in _ARRETER_TOUT:
        store.fixer_etat("suggestions", "off")
        propositions.fermer()
        return "D'accord : plus de suggestions. Dis « reprends les suggestions » pour les retrouver."
    if n in _REPRENDRE:
        store.fixer_etat("suggestions", "on")
        return "D'accord : les suggestions reprennent."
    h = _derniere if _derniere and time.monotonic() - _derniere["quand"] <= propositions.DUREE_S else None
    if not h:
        return "Je ne t'ai rien proposé récemment."
    propositions.fermer()
    _derniere = None
    if not ecarter(h, origine):
        return "Je ne peux pas le retenir pour le moment."
    return f"D'accord, je ne te proposerai plus ça ({decrire(h)})."
