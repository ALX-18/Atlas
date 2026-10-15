"""
Sprint Dépôt + Ollama / O1-O3 — banc de mesure sur le VRAI modèle (pas un test pytest).

Joue les chemins qui appellent le modèle, par le code réel d'Atlas :
  - conversation depuis la fenêtre Atlas (sans historique) ;
  - conversation depuis l'interface web, avec 20 messages d'historique (ui/app.js en envoie 20) ;
  - conversation avec la mémoire la plus chargée (jusqu'à 9 souvenirs injectés) ;
  - planification d'une demande composée ;
  - voix (generate_speech_response, par le chemin vocal réel).
Rien n'est exécuté sur la machine (outils remplacés par des enregistreurs), et la mémoire est
en LECTURE SEULE (rappels réels, aucune écriture), comme tests/gb1_mesure.py.

Pour chaque appel au modèle : la taille de la consigne, et ce qu'Ollama renvoie dans le dernier
morceau du flux : prompt_eval_count, prompt_eval_duration, eval_count, load_duration,
total_duration, et le temps jusqu'au premier mot.

    .venv\\Scripts\\python.exe tests\\o_mesure_ollama.py SORTIE.json [o1|o3|o2chaud|o2froid]
"""

import asyncio
import json
import os
import pathlib
import sys
import time

os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
# Branchée VOLONTAIREMENT pour des rappels réels ; ReadOnlyMemory en bloque les écritures.
os.environ["ATLAS_MEMORY"] = "real"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import httpx  # noqa: E402

from gb1_mesure import ReadOnlyMemory  # noqa: E402

CALLS: list[dict] = []
_real_stream = httpx.AsyncClient.stream


class _Capture:
    """Enveloppe client.stream(...) : garde la requête, le premier jeton et le morceau final."""

    def __init__(self, client, method, url, **kw):
        self._cm = _real_stream(client, method, url, **kw)
        self.payload = kw.get("json") or {}
        self.url = url

    async def __aenter__(self):
        self.t0 = time.perf_counter()
        resp = await self._cm.__aenter__()
        record = {"url": str(self.url), "t_premier_mot": None, "final": None}
        if "/api/chat" in str(self.url):
            msgs = self.payload.get("messages", [])
            record.update({
                "options": self.payload.get("options"),
                "consigne_caracteres": len(msgs[0]["content"]) if msgs and msgs[0]["role"] == "system" else 0,
                "historique_messages": max(0, len(msgs) - 2),
                "caracteres_total": sum(len(m["content"]) for m in msgs),
                "consigne": msgs[0]["content"] if msgs else "",
                "souvenirs_injectes": _souvenirs(msgs[0]["content"]) if msgs else 0,
            })
            CALLS.append(record)
        original = resp.aiter_lines
        t0 = self.t0

        async def aiter_lines():
            async for line in original():
                try:
                    chunk = json.loads(line)
                except Exception:
                    yield line
                    continue
                if record["t_premier_mot"] is None and chunk.get("message", {}).get("content"):
                    record["t_premier_mot"] = round(time.perf_counter() - t0, 3)
                if chunk.get("done"):
                    record["final"] = {k: chunk.get(k) for k in (
                        "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration",
                        "load_duration", "total_duration", "done_reason")}
                    record["t_total"] = round(time.perf_counter() - t0, 3)
                yield line

        resp.aiter_lines = aiter_lines
        return resp

    async def __aexit__(self, *exc):
        return await self._cm.__aexit__(*exc)


def _souvenirs(consigne: str) -> int:
    if "MÉMOIRE :" not in consigne:
        return 0
    bloc = consigne.split("MÉMOIRE :", 1)[1].split("CE QU'ATLAS", 1)[0]
    return sum(1 for l in bloc.splitlines() if l.startswith("- ") and "Aucun souvenir" not in l)


def _install():
    httpx.AsyncClient.stream = lambda client, method, url, **kw: _Capture(client, method, url, **kw)
    import core.intent_engine as ie
    import core.memory_manager as mm

    mem = ReadOnlyMemory(mm.get_memory_manager())
    mm._instance = mem
    for name in list(ie.TOOL_HANDLERS):
        ie.TOOL_HANDLERS[name] = (lambda n: lambda args: {"success": True, "message": f"[simulé] {n}"})(name)
    ie._save_action_to_memory = lambda *a, **k: None
    return mem


# Historique de l'interface web : 10 échanges, réponses longues (le maximum envoyé est 20 messages).
_REPONSE_LONGUE = (
    "Voici une explication détaillée. La photosynthèse est le processus par lequel les plantes, "
    "les algues et certaines bactéries convertissent l'énergie lumineuse en énergie chimique. "
    "Elle se déroule dans les chloroplastes, grâce à la chlorophylle, et produit du glucose et de "
    "l'oxygène à partir de dioxyde de carbone et d'eau. On distingue la phase lumineuse, qui a lieu "
    "dans les thylakoïdes et produit de l'ATP et du NADPH, et le cycle de Calvin, qui fixe le "
    "carbone dans le stroma. Ce mécanisme est à la base de presque toutes les chaînes alimentaires "
    "et a façonné la composition de l'atmosphère terrestre depuis des milliards d'années. "
)
HISTORIQUE_20 = []
for i in range(10):
    HISTORIQUE_20.append({"role": "user", "content": f"explique-moi encore un point, le numéro {i + 1}, en détail"})
    HISTORIQUE_20.append({"role": "assistant", "content": _REPONSE_LONGUE * 2})


async def _chat(message, history=None):
    from api.models import ChatRequest
    from api.routes import chat_endpoint

    return await chat_endpoint(ChatRequest(message=message, history=history or []))


async def _voix(message):
    from core.voice_engine import VoiceEngine

    moteur = VoiceEngine.__new__(VoiceEngine)
    return await moteur._run_text_pipeline(message)


def _ligne(nom, before):
    rows = []
    for c in CALLS[before:]:
        f = c.get("final") or {}
        rows.append({
            "cas": nom,
            "consigne_caracteres": c.get("consigne_caracteres"),
            "historique_messages": c.get("historique_messages"),
            "souvenirs_injectes": c.get("souvenirs_injectes"),
            "caracteres_total": c.get("caracteres_total"),
            "prompt_eval_count": f.get("prompt_eval_count"),
            "prompt_eval_ms": round((f.get("prompt_eval_duration") or 0) / 1e6, 1),
            "eval_count": f.get("eval_count"),
            "load_ms": round((f.get("load_duration") or 0) / 1e6, 1),
            "total_ms": round((f.get("total_duration") or 0) / 1e6, 1),
            "t_premier_mot_s": c.get("t_premier_mot"),
            "t_total_s": c.get("t_total"),
            "options": c.get("options"),
        })
    return rows


async def o1(mem):
    rows = []
    cas = [
        ("conversation fenêtre", lambda: _chat("quelle est la capitale de l'Italie ?")),
        ("conversation mémoire chargée", lambda: _chat("que penses-tu de Discord et de Steam ?")),
        ("conversation web 20 messages", lambda: _chat("donne-moi un résumé de notre conversation", HISTORIQUE_20)),
        ("conversation web 20 messages + mémoire", lambda: _chat("que penses-tu de Discord et de Steam ?", HISTORIQUE_20)),
        ("planification", lambda: _chat("ouvre le bloc-notes puis écris bonjour dedans")),
        ("voix", lambda: _voix("explique-moi la photosynthèse en une phrase")),
        ("voix mémoire chargée", lambda: _voix("que penses-tu de Discord et de Steam ?")),
    ]
    for nom, fn in cas:
        before = len(CALLS)
        await fn()
        rows += _ligne(nom, before)
    return rows


async def o3(mem):
    """Deux requêtes successives : la même question, puis une autre. Combien de jetons réévalués ?"""
    rows = []
    for nom, msg in [("o3 question A", "quelle est la capitale de l'Italie ?"),
                     ("o3 question A (bis)", "quelle est la capitale de l'Italie ?"),
                     ("o3 question B", "combien font 12 fois 8 ?")]:
        before = len(CALLS)
        await _chat(msg)
        rows += _ligne(nom, before)
    # Les deux consignes : où diffèrent-elles ?
    c1, c2 = CALLS[-3]["consigne"], CALLS[-2]["consigne"]
    k = next((i for i, (a, b) in enumerate(zip(c1, c2)) if a != b), min(len(c1), len(c2)))
    rows.append({"cas": "o3 première différence entre deux consignes", "position_caractere": k,
                 "consigne_caracteres": len(c1), "avant": c1[max(0, k - 80):k], "apres_1": c1[k:k + 60],
                 "apres_2": c2[k:k + 60]})
    return rows


async def o2(mem, etiquette):
    rows = []
    questions = ["quelle est la capitale de l'Italie ?", "combien font 12 fois 8 ?", "qui a écrit Les Misérables ?",
                 "que signifie CPU ?", "quel est le plus grand océan ?", "pourquoi le ciel est bleu ?",
                 "traduis bonjour en anglais", "c'est quoi un processeur ?", "quand a été construite la tour Eiffel ?",
                 "qu'est-ce qu'un trou noir ?"]
    for i, q in enumerate(questions):
        if etiquette == "froid":
            # Décharger le modèle avant chaque demande : chaque mesure part d'un modèle froid.
            async with httpx.AsyncClient(timeout=60) as c:
                await c.post("http://127.0.0.1:11434/api/generate", json={"model": "qwen2.5:7b", "keep_alive": 0})
            await asyncio.sleep(2)
        before = len(CALLS)
        t0 = time.perf_counter()
        await _chat(q)
        r = _ligne(f"o2 {etiquette} {i + 1}", before)
        for x in r:
            x["t_route_s"] = round(time.perf_counter() - t0, 3)
        rows += r
    return rows


async def o2session(mem):
    """Session vocale de 20 min avec des pauses (O2) : combien de rechargements du modèle ?
    Atlas envoie keep_alive=10m : une pause plus longue décharge le modèle."""
    instants = [0, 60, 180, 420, 1140, 1200]   # secondes ; 1140 - 420 = 12 min de pause
    rows, debut = [], time.monotonic()
    for i, t in enumerate(instants):
        attente = t - (time.monotonic() - debut)
        if attente > 0:
            await asyncio.sleep(attente)
        before = len(CALLS)
        await _voix("explique-moi en une phrase ce qu'est un processeur")
        r = _ligne(f"session t={t // 60} min", before)
        for x in r:
            x["recharge"] = (x.get("load_ms") or 0) > 1000
        rows += r
    return rows


async def pb1(mem):
    """Pré-beta / PB1 : le pire cas mesuré (web, 20 messages, mémoire) et une question courte."""
    rows = []
    for nom, fn in [("pb1 conversation fenêtre", lambda: _chat("quelle est la capitale de l'Italie ?")),
                    ("pb1 web 20 messages + mémoire",
                     lambda: _chat("que penses-tu de Discord et de Steam ?", HISTORIQUE_20))]:
        before = len(CALLS)
        await fn()
        rows += _ligne(nom, before)
    return rows


def main(out_path, mode="o1"):
    import logging

    logging.disable(logging.WARNING)
    mem = _install()
    if mode == "o1":
        rows = asyncio.run(o1(mem))
    elif mode == "o3":
        rows = asyncio.run(o3(mem))
    elif mode == "pb1":
        rows = asyncio.run(pb1(mem))
    elif mode == "o2session":
        rows = asyncio.run(o2session(mem))
    elif mode in ("o2chaud", "o2froid"):
        rows = asyncio.run(o2(mem, mode[2:]))
    else:
        raise SystemExit(f"mode inconnu : {mode}")
    for r in rows:
        r.pop("consigne", None)
    pathlib.Path(out_path).write_text(json.dumps({"mode": mode, "ecritures_bloquees": len(mem.writes), "lignes": rows},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(rows)} lignes -> {out_path} ; écritures mémoire bloquées : {len(mem.writes)}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "o1")
