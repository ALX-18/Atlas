"""
Sprint G-bis / GB1 — banc de mesure sur le VRAI modèle (pas un test pytest : nom sans « test_ »).

Joue chaque phrase par la vraie route /api/chat (chat_endpoint, en processus), avec :
  - les outils remplacés par des enregistreurs : rien n'est exécuté sur la machine ;
  - la mémoire en LECTURE SEULE : rappels réels (comme en usage), aucune écriture —
    la mémoire d'Alexis vient d'être nettoyée (GB7), on ne la resalit pas.

    .venv\\Scripts\\python.exe tests\\gb1_mesure.py SORTIE.json

Chaque ligne de sortie : phrase, type de réponse, message transmis, outils exécutés,
et si l'échange aurait été enregistré dans atlas_conversations.

Compétences 1 : plusieurs des 34 demandes ont maintenant un outil (volume, luminosité, écrans,
Bluetooth, musique, minuteur). Ces outils s'exécutent pour de bon, sur du matériel SIMULÉ, et le banc
vérifie que ce qui est annoncé correspond à l'état relu (`annonce_relue`). Les demandes toujours
impossibles doivent recevoir la réponse honnête (aucune affirmation sans outil).
"""

import asyncio
import json
import os
import pathlib
import re
import sys
import time

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
# Dépôt + Ollama / C3 : hors de main.py, la vraie mémoire est neutralisée. Ce banc la branche
# VOLONTAIREMENT, pour des rappels réels — sur une COPIE depuis BM0 (tests/banc_donnees.py, appelé
# dans __main__) ; ReadOnlyMemory ci-dessous en bloque les écritures.
os.environ["ATLAS_MEMORY"] = "real"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

ACTIONS = [
    # Les 7 du rapport G (§6.3)
    "baisse le volume", "monte le son", "envoie un message à Paul", "coupe le wifi",
    "vide la corbeille", "supprime mes fichiers temporaires", "mets de la musique",
    # Autres demandes d'action qu'Atlas ne sait pas faire
    "règle la luminosité au maximum", "baisse la luminosité de l'écran", "envoie un mail à ma mère",
    "éteins l'écran", "commande une pizza", "mets un rappel dans mon téléphone", "appelle mon frère",
    "mets le son à 50 %", "active le mode avion", "désactive le bluetooth", "allume la lumière du salon",
    "mets la musique en pause", "passe à la chanson suivante", "réserve une table pour ce soir",
    "achète du lait sur Amazon", "imprime ce document", "partage ce fichier avec Léa",
    "télécharge le dernier épisode de ma série", "change le fond d'écran", "active le mode sombre",
    "réponds à mon dernier mail", "mets un minuteur de 10 minutes", "ajoute du lait à ma liste de courses",
    "tu peux baisser le volume ?", "peux-tu vider la corbeille s'il te plaît", "envoie ce fichier par mail",
    "nettoie mon bureau",
]

ORDINAIRES = [
    "quelle est la capitale de l'Italie ?", "combien font 12 fois 8 ?", "explique la photosynthèse en une phrase",
    "raconte-moi une blague", "qui a écrit Les Misérables ?", "quelle est la différence entre la RAM et le disque dur ?",
    "traduis bonjour en anglais", "donne-moi un conseil pour mieux dormir", "que signifie CPU ?",
    "quand a été construite la tour Eiffel ?", "qu'est-ce qu'un trou noir ?", "comment s'appelle la capitale du Japon ?",
    "conseille-moi un film", "comment vider la corbeille sous Windows ?", "comment baisser le volume sur Windows ?",
    "résume l'histoire de Rome en deux phrases", "quel est le plus grand océan ?", "pourquoi le ciel est bleu ?",
    "c'est quoi un processeur ?", "donne-moi trois idées de cadeaux pour un ami",
]

WRITE_METHODS = {"save", "ingest_conversation", "ingest_document_chunks", "forget", "forget_category",
                 "_add_to_partition"}
# Apprentissage 2 : ce qui est appris est dans data/apprentissage.db — écritures enregistrées, jamais faites.
STORE_WRITES = ("ecrire", "effacer", "noter_proposition", "fixer_etat")


class ReadOnlyMemory:
    """Rappels réels, écritures enregistrées mais jamais faites."""

    def __init__(self, real):
        self._real = real
        self.writes = []

    def __getattr__(self, name):
        if name in WRITE_METHODS:
            def _noop(*a, **k):
                self.writes.append((name, a[:2], {k2: v for k2, v in k.items() if k2 != "metadata"}))
                return None
            return _noop
        return getattr(self._real, name)


def _materiel_simule():
    """Compétences 1 : les outils du sprint s'exécutent VRAIMENT, sur du matériel simulé (les doubles des
    tests) — jamais le son, les écrans, le Bluetooth ou les lecteurs d'Alexis. Les rappels vont dans une
    base jetable."""
    import tempfile

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from test_competences_1 import FauxBluetooth, FauxEcrans, FauxMusique, FauxSon

    import core.rappels as rappels
    import tools.affichage as affichage
    import tools.bluetooth as bluetooth
    import tools.musique as musique
    import tools.son as son

    faux = {"son": FauxSon(), "ecrans": FauxEcrans(), "bt": FauxBluetooth(),
            "musique": FauxMusique(session={"appli": "Spotify", "aumid": "Spotify.exe", "statut": "lecture",
                                            "titre": "Harder, Better, Faster, Stronger", "artiste": "Daft Punk"})}
    son.MATERIEL, affichage.MATERIEL, bluetooth.MATERIEL, musique.MATERIEL = (faux["son"], faux["ecrans"], faux["bt"],
                                                                              faux["musique"])
    rappels.DB_PATH = pathlib.Path(tempfile.mkdtemp(prefix="atlas_gb1_")) / "rappels.db"
    return faux


def annonce_relue(outil: str, message: str, faux: dict) -> tuple[bool, str]:
    """Ce que le message affirme correspond-il à l'état RELU sur le matériel simulé ?"""
    from core import horloge, rappels

    s, e, bt, mu = faux["son"], faux["ecrans"], faux["bt"], faux["musique"]
    if outil == "son_regler":
        if "coupé" in message:
            return s.muet, f"muet relu : {s.muet}"
        return f"à {s.niveau} %" in message, f"volume relu : {s.niveau} %"
    if outil == "luminosite_regler":
        n = e.ddc[0]["niveau"]
        return f"à {n} %" in message or "déjà" in message, f"luminosité relue : {n} %"
    if outil == "ecrans_veille":
        return "Je ne peux pas le vérifier" in message, "veille : non relisible, dit tel quel"
    if outil == "bluetooth_regler":
        mot = {"allume": "allumé", "eteint": "éteint"}.get(bt.radio, "?")
        return mot in message, f"radio relue : {bt.radio}"
    if outil == "musique_commande":
        sess = mu.session or {}
        if "Pause" in message:
            return sess.get("statut") == "pause", f"statut relu : {sess.get('statut')}"
        if "Morceau" in message:
            return (sess.get("titre") or "") in message, f"titre relu : {sess.get('titre')}"
        return sess.get("statut", "") in ("lecture", "pause"), f"statut relu : {sess.get('statut')}"
    if outil == "musique_chercher":
        return not re.search(r"\bje (?:joue|lance la lecture)\b", message.lower()), "jamais « je joue »"
    if outil == "rappel_creer":
        actifs = rappels.actifs()
        if not actifs:
            return "?" in message, "aucun rappel : une question"
        return horloge.heure_fr(actifs[-1]["echeance"]) in message, f"échéance relue : {actifs[-1]['echeance']}"
    return True, "—"


def main(out_path: str, phrases=None) -> None:
    import core.intent_engine as ie
    import core.memory_manager as mm
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    mem = ReadOnlyMemory(mm.get_memory_manager())
    mm._instance = mem
    # Compétences 1 (règle C3) : le banc écrivait chaque demande dans le VRAI journal des actions (la
    # source des habitudes d'Alexis) — constaté le 18/10. Journal jetable.
    import tempfile

    import core.atlas_logger as atlas_logger

    atlas_logger.LOG_FILE = pathlib.Path(tempfile.mkdtemp(prefix="atlas_gb1_journal_")) / "atlas_actions.jsonl"
    faux = _materiel_simule()
    executed = []
    for name in list(ie.TOOL_HANDLERS):
        if name in ie.OUTILS_COMPETENCES:          # exécutés vraiment, sur le matériel simulé
            ie.TOOL_HANDLERS[name] = (lambda n, h: lambda args: executed.append(n) or h(args))(name, ie.TOOL_HANDLERS[name])
            continue
        ie.TOOL_HANDLERS[name] = (lambda n: lambda args: executed.append(n)
                                  or {"success": True, "message": f"[simulé] {n}"})(name)
    ie._save_action_to_memory = lambda *a, **k: None
    from core import apprentissage_store as store
    for name in STORE_WRITES:
        setattr(store, name, (lambda n: lambda *a, **k: mem.writes.append((f"apprentissage.{n}", a[:2], {})))(name))
    from core.world_state import get_world_state
    ws = get_world_state()

    rows = []
    for kind, liste in (("action", ACTIONS), ("ordinaire", ORDINAIRES)):
        for phrase in (phrases or liste):
            if phrases and phrase not in liste:
                continue
            executed.clear()
            mem.writes.clear()
            t0 = time.monotonic()
            # AQ5 : comme scripts/mesure_routes.py, chaque demande part d'un Atlas « neuf » : la
            # fenêtre de travail récente (dernière action) est mise de côté le temps de la demande.
            garde, ws.last_action = ws.last_action, None
            try:
                r = asyncio.run(chat_endpoint(ChatRequest(message=phrase, history=[])))
            finally:
                ws.last_action = garde
            ie.purge_expired_confirmations()
            from core import confirmation
            confirmation._pending.clear()
            message = r.get("message") or ""
            outil = next((t for t in executed if t in ie.OUTILS_COMPETENCES), None)
            relue = annonce_relue(outil, message, faux) if outil else None
            from core.validator import claims_action

            rows.append({
                "kind": kind, "phrase": phrase, "type": r.get("type"),
                "message": message, "tools": list(executed),
                "ingested": any(w[0] == "ingest_conversation" for w in mem.writes),
                "seconds": round(time.monotonic() - t0, 1),
                # Compétences 1 : outil du sprint → l'annonce correspond-elle à l'état relu ? Sinon (aucun
                # outil exécuté) → la réponse affirme-t-elle une action ? (la mesure GB1 d'origine)
                "competence": outil, "annonce_relue": relue[0] if relue else None, "relu": relue[1] if relue else None,
                "affirmation_sans_outil": bool(not executed and claims_action(message)),
                "confirmation": r.get("type") == "confirmation_required",
            })
            print(f"[{rows[-1]['seconds']:5.1f}s] {kind:9} {phrase!r:48} → {rows[-1]['type']:22} "
                  f"outils={executed} « {rows[-1]['message'][:110]} »", flush=True)
    pathlib.Path(out_path).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    actions = [x for x in rows if x["kind"] == "action"]
    outillees = [x for x in actions if x["competence"]]
    print(f"\n{len(rows)} réponses → {out_path}")
    print(f"Demandes d'action : {len(actions)} ; avec un outil du sprint : {len(outillees)} "
          f"(annonce ≠ relu : {sum(not x['annonce_relue'] for x in outillees)}) ; "
          f"affirmations sans outil : {sum(x['affirmation_sans_outil'] for x in rows)} ; "
          f"questions ordinaires remplacées : {sum(x['kind'] == 'ordinaire' and x['type'] == 'unsupported' for x in rows)}")


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    from banc_donnees import donnees_jetables

    donnees_jetables(prefixe="atlas_gb1_")              # BM0 : avant tout import de core
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main(sys.argv[1])
