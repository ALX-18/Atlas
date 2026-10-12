"""
Sprint G-bis / GB1 — banc de mesure sur le VRAI modèle (pas un test pytest : nom sans « test_ »).

Joue chaque phrase par la vraie route /api/chat (chat_endpoint, en processus), avec :
  - les outils remplacés par des enregistreurs : rien n'est exécuté sur la machine ;
  - la mémoire en LECTURE SEULE : rappels réels (comme en usage), aucune écriture —
    la mémoire d'Alexis vient d'être nettoyée (GB7), on ne la resalit pas.

    .venv\\Scripts\\python.exe tests\\gb1_mesure.py SORTIE.json

Chaque ligne de sortie : phrase, type de réponse, message transmis, outils exécutés,
et si l'échange aurait été enregistré dans atlas_conversations.
"""

import asyncio
import json
import os
import pathlib
import sys
import time

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
# Dépôt + Ollama / C3 : hors de main.py, la vraie mémoire est neutralisée. Ce banc la branche
# VOLONTAIREMENT, pour des rappels réels ; ReadOnlyMemory ci-dessous en bloque les écritures.
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

WRITE_METHODS = {"save", "ingest_conversation", "ingest_document_chunks", "store_error", "forget",
                 "forget_category", "_add_to_partition"}


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


def main(out_path: str, phrases=None) -> None:
    import core.intent_engine as ie
    import core.memory_manager as mm
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    mem = ReadOnlyMemory(mm.get_memory_manager())
    mm._instance = mem
    executed = []
    for name in list(ie.TOOL_HANDLERS):
        ie.TOOL_HANDLERS[name] = (lambda n: lambda args: executed.append(n)
                                  or {"success": True, "message": f"[simulé] {n}"})(name)
    ie._save_action_to_memory = lambda *a, **k: None
    ie.save_rejection = lambda *a, **k: None

    rows = []
    for kind, liste in (("action", ACTIONS), ("ordinaire", ORDINAIRES)):
        for phrase in (phrases or liste):
            if phrases and phrase not in liste:
                continue
            executed.clear()
            mem.writes.clear()
            t0 = time.monotonic()
            r = asyncio.run(chat_endpoint(ChatRequest(message=phrase, history=[])))
            ie.purge_expired_confirmations()
            from core import confirmation
            confirmation._pending.clear()
            rows.append({
                "kind": kind, "phrase": phrase, "type": r.get("type"),
                "message": r.get("message") or "", "tools": list(executed),
                "ingested": any(w[0] == "ingest_conversation" for w in mem.writes),
                "seconds": round(time.monotonic() - t0, 1),
            })
            print(f"[{rows[-1]['seconds']:5.1f}s] {kind:9} {phrase!r:48} → {rows[-1]['type']:22} "
                  f"outils={executed} « {rows[-1]['message'][:110]} »", flush=True)
    pathlib.Path(out_path).write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{len(rows)} réponses → {out_path}")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main(sys.argv[1])
