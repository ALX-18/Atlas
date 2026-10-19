"""
Sprint Banc de modèles / BM2 — chaque candidat mesuré par le code d'Atlas, sans changer Atlas.

    python scripts/banc_modeles.py --out <dossier> [--modeles qwen2.5:7b,qwen3:8b] [--parties …]

Un processus par modèle (`--un`) : le modèle est passé par ATLAS_MODELE, la réflexion coupée par
ATLAS_MODELE_REFLEXION=off pour les modèles qui l'ont (capacité « thinking » d'Ollama). Les données
sont des copies (tests/banc_donnees.py, garde BM0). Parties :

- ressources : à num_ctx 8 192, transcription (faster-whisper « base », GPU) chargée comme dans Atlas —
  VRAM, part GPU/CPU, RAM, chargement, premier mot, jetons/s ; fuite de réflexion ;
- gb1 : tests/gb1_mesure.py (34 actions, 20 questions), processus à part ;
- plans : 20 demandes composées → le planificateur d'Atlas ; JSON valide, chaque étape validée ;
- documents : 3 rapports, 3 résumés (dont le long) par core/artefacts.py ; valides du premier coup,
  temps, faits inventés détectés ;
- consignes : 12 consignes vérifiables par programme ;
- conversation : 20 questions en français courant ; langue, longueur, temps ;
- processeur : (palier léger) une réponse courte sans GPU (num_gpu 0) ;
- aveugle : les 3 productions de l'évaluation à l'aveugle (conversation, section de rapport, résumé).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
OLLAMA = "http://127.0.0.1:11434"
STANDARD = ["qwen2.5:7b", "qwen3.5:9b", "qwen3:8b", "ministral-3:8b", "granite4.2:8b"]
LEGER = ["qwen3.5:4b", "gemma4:e4b", "ministral-3:3b", "granite4.2:3b", "qwen3:4b"]
PARTIES = ["ressources", "gb1", "plans", "documents", "consignes", "conversation", "processeur", "aveugle"]

# --------------------------------------------------------------------------- #
#  Les demandes
# --------------------------------------------------------------------------- #

PLANS = [
    "ouvre le bloc-notes et écris bonjour", "lance Steam puis mets-le au premier plan",
    "ouvre la calculatrice et réduis le bloc-notes", "ouvre Discord puis ouvre Spotify",
    "ferme le bloc-notes et ouvre la calculatrice", "ouvre le navigateur et va sur wikipedia.org",
    "ouvre l'explorateur puis agrandis-le", "lance le mode travail puis ouvre le bloc-notes",
    "ouvre le bloc-notes, écris liste de courses et enregistre avec ctrl+s",
    "mets Steam au premier plan et ensuite réduis Discord", "ouvre Paint puis la calculatrice",
    "ouvre un nouvel onglet et cherche la météo de Lyon", "ouvre le gestionnaire des tâches et liste les fenêtres",
    "lance Spotify et après mets-le en plein écran", "ouvre le bloc-notes puis tape merci",
    "ouvre la calculatrice, puis le bloc-notes, puis Paint", "ferme Discord puis relance-le",
    "ouvre wikipedia.org dans un nouvel onglet puis lis la page", "ouvre Word et écris le titre Rapport",
    "réduis toutes les fenêtres puis ouvre le bloc-notes",
]
SUJETS_RAPPORT = ["la photosynthèse", "l'histoire de l'imprimerie", "les énergies renouvelables en France"]
QUESTIONS = [
    "C'est quoi la différence entre un virus et une bactérie ?", "Tu peux m'expliquer simplement comment marche un frigo ?",
    "Pourquoi on a le hoquet ?", "Donne-moi une idée de repas rapide pour ce soir.",
    "Comment je fais pour rester concentré quand je révise ?", "C'est quoi un taux d'intérêt ?",
    "Qui était Marie Curie ?", "Pourquoi la mer est salée ?", "Tu me conseilles quoi pour mieux dormir ?",
    "Comment on fait une pâte à crêpes ?", "C'est quoi la RAM dans un ordi ?", "Pourquoi les feuilles tombent en automne ?",
    "Donne-moi trois idées de sortie pour un dimanche pluvieux.", "Comment marche le vote en France ?",
    "C'est quoi la différence entre la météo et le climat ?", "Pourquoi le ciel est bleu ?",
    "Comment je peux économiser un peu chaque mois ?", "Explique-moi ce qu'est un trou noir.",
    "Quels sont les signes d'une bonne nuit de sommeil ?", "C'est quoi l'intelligence artificielle, en deux phrases ?",
]


def _lignes(t):
    return [l for l in t.strip().splitlines() if l.strip()]


def _mots(t):
    return re.findall(r"\b[\wàâäéèêëîïôöùûüç'-]+\b", t)


def _puces(t):
    return [l for l in _lignes(t) if re.match(r"^\s*(?:[-*•]|\d+[.)])\s", l)]


_ANGLAIS = {"the", "and", "is", "are", "of", "to", "in", "it", "that", "with", "for", "this", "you", "your", "be"}


def anglais(t):
    m = [x.lower() for x in _mots(t)]
    return len(m) >= 8 and sum(x in _ANGLAIS for x in m) / len(m) >= 0.08


CONSIGNES = [
    ("Explique ce qu'est la photosynthèse en exactement 5 lignes, une phrase par ligne.", lambda t: len(_lignes(t)) == 5),
    ("Présente les avantages du vélo en ville en 3 parties numérotées (1., 2., 3.).",
     lambda t: [int(x) for x in re.findall(r"(?m)^\s*\**(\d)[.)]", t)] == [1, 2, 3]),
    ("Explain in English, in two sentences, what a computer is.", lambda t: anglais(t)),
    ("Décris une journée à la plage, sans aucune liste à puces ni numérotation.", lambda t: not _puces(t)),
    ("Raconte l'histoire de la tour Eiffel en moins de 120 mots.", lambda t: 0 < len(_mots(t)) < 120),
    ("Écris un court texte sur l'automne. Il commence par la ligne « Titre : Les couleurs de l'automne ».",
     lambda t: bool(_lignes(t)) and "titre : les couleurs de l'automne" in _lignes(t)[0].lower().replace("**", "")),
    ("Réponds en une seule phrase : pourquoi faut-il boire de l'eau ?",
     lambda t: len(re.findall(r"[.!?](?:\s|$)", t.strip())) == 1),
    ("Donne exactement 4 conseils pour économiser l'énergie, sous forme de liste à puces.", lambda t: len(_puces(t)) == 4),
    ("Termine ta réponse par une question. Sujet : les vacances d'été.", lambda t: t.strip().endswith("?")),
    ("Explique le cycle de l'eau sans jamais employer le mot « pluie ».", lambda t: "pluie" not in t.lower()),
    ("Commence ta réponse par le mot « Bonjour » et présente le système solaire en 3 phrases.",
     lambda t: t.strip().lstrip("*# ").lower().startswith("bonjour")),
    ("Écris un haïku en français (3 lignes).", lambda t: len(_lignes(t)) == 3),
]

# --------------------------------------------------------------------------- #
#  Ollama
# --------------------------------------------------------------------------- #


def _post(chemin, corps, timeout=600):
    import httpx

    r = httpx.post(OLLAMA + chemin, json=corps, timeout=timeout)
    r.raise_for_status()
    return r.json()


def decharger_tout():
    import httpx

    for m in httpx.get(OLLAMA + "/api/ps", timeout=10).json().get("models", []):
        httpx.post(OLLAMA + "/api/generate", json={"model": m["name"], "keep_alive": 0}, timeout=60)
    for _ in range(30):
        if not httpx.get(OLLAMA + "/api/ps", timeout=10).json().get("models"):
            return
        time.sleep(1)


def capacites(modele) -> list[str]:
    return _post("/api/show", {"model": modele}).get("capabilities", [])


def _flux(modele, messages, options, coupee, keep_alive="10m"):
    """Une réponse en flux : temps jusqu'au premier mot, texte, réflexion éventuelle, dernier morceau."""
    import httpx

    corps = {"model": modele, "messages": messages, "stream": True, "keep_alive": keep_alive, "options": options}
    if coupee:
        corps["think"] = False
    t0 = time.perf_counter()
    premier, texte, reflexion, fin = None, "", "", {}
    with httpx.stream("POST", OLLAMA + "/api/chat", json=corps, timeout=600) as r:
        r.raise_for_status()
        for ligne in r.iter_lines():
            if not ligne.strip():
                continue
            c = json.loads(ligne)
            msg = c.get("message", {})
            if msg.get("content"):
                premier = premier or time.perf_counter() - t0
                texte += msg["content"]
            reflexion += msg.get("thinking") or ""
            if c.get("done"):
                fin = c
    return {"premier_mot_s": round(premier or 0, 2), "total_s": round(time.perf_counter() - t0, 2), "texte": texte,
            "reflexion": reflexion, "fin": fin}


def _fuite(texte, reflexion):
    return bool(reflexion.strip()) or bool(re.search(r"<think>|</think>|^\s*Thinking\.\.\.", texte, re.I | re.M))


# --------------------------------------------------------------------------- #
#  Les parties (dans le processus d'un modèle)
# --------------------------------------------------------------------------- #

def p_ressources(modele, coupee):
    import httpx
    import psutil

    from core.ollama_client import ollama_options

    decharger_tout()
    def vram_utilisee():
        try:
            o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                               capture_output=True, text=True, timeout=10).stdout.split(",")
            return int(o[0]), int(o[1])
        except Exception:
            return None, None
    vram_avant, vram_totale = vram_utilisee()
    froid = _flux(modele, [{"role": "user", "content": "Bonjour, présente-toi en une phrase."}], ollama_options(), coupee)
    chaud = _flux(modele, [{"role": "user", "content": "Explique en un paragraphe ce qu'est un ordinateur."}],
                  ollama_options(), coupee)
    ps = next((m for m in httpx.get(OLLAMA + "/api/ps", timeout=10).json().get("models", []) if m["name"] == modele), {})
    vram_apres, _ = vram_utilisee()
    rss = sum(p.info["memory_info"].rss for p in psutil.process_iter(["name", "memory_info"])
              if (p.info["name"] or "").lower().startswith("ollama"))
    f = chaud["fin"]
    taille, sur_gpu = ps.get("size", 0), ps.get("size_vram", 0)
    return {
        "chargement_s": round(froid["fin"].get("load_duration", 0) / 1e9, 2),
        "premier_mot_froid_s": froid["premier_mot_s"], "premier_mot_chaud_s": chaud["premier_mot_s"],
        "jetons_par_s": round(f.get("eval_count", 0) / (f.get("eval_duration", 1) / 1e9), 1) if f.get("eval_duration") else None,
        "modele_charge_go": round(taille / 1e9, 2), "sur_gpu_go": round(sur_gpu / 1e9, 2),
        "part_gpu_pct": round(100 * sur_gpu / taille) if taille else None,
        "vram_carte_mo": {"avant": vram_avant, "apres": vram_apres, "totale": vram_totale},
        "ram_processus_ollama_go": round(rss / 1e9, 2),
        "fuite_reflexion": _fuite(froid["texte"], froid["reflexion"]) or _fuite(chaud["texte"], chaud["reflexion"]),
        "texte_exemple": chaud["texte"][:400],
    }


def p_gb1(modele, coupee, dossier):
    sortie = dossier / "gb1.json"
    env = {**os.environ}
    r = subprocess.run([PY, "-u", str(ROOT / "tests" / "gb1_mesure.py"), str(sortie)], cwd=ROOT, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    if not sortie.exists():
        return {"erreur": (r.stderr or r.stdout)[-800:]}
    rows = json.loads(sortie.read_text(encoding="utf-8"))
    actions = [x for x in rows if x["kind"] == "action"]
    return {"actions": len(actions), "outillees": sum(bool(x["competence"]) for x in actions),
            "annonce_non_relue": sum(bool(x["competence"]) and not x["annonce_relue"] for x in actions),
            "affirmations_sans_outil": sum(x["affirmation_sans_outil"] for x in rows),
            "ordinaires_bloquees": sum(x["kind"] == "ordinaire" and x["type"] == "unsupported" for x in rows),
            "ordinaires_s_moyen": round(sum(x["seconds"] for x in rows if x["kind"] == "ordinaire") /
                                        max(1, sum(x["kind"] == "ordinaire" for x in rows)), 1)}


def p_plans(modele, coupee):
    import core.ollama_client as oc
    import core.intent_engine as ie
    from core.intent_classifier import IntentResult
    from core.planner import get_planner

    brut = {}
    vraie = oc.chat_full

    async def capter(*a, **k):
        brut["r"] = await vraie(*a, **k)
        return brut["r"]

    oc.chat_full = capter
    lignes = []
    try:
        for p in PLANS:
            brut.clear()
            t0 = time.perf_counter()
            intent = IntentResult(category="conversation", verb="plan", target=None, params={}, confidence=0.9,
                                  is_complex=True, raw_input=p)
            plan = asyncio.run(get_planner().plan(intent, {}))
            r = brut.get("r") or ""
            try:
                json.loads(r.strip()[r.find("{"):r.rfind("}") + 1] if "{" in r else r)
                json_ok = plan.goal != "parse_failed"
            except Exception:
                json_ok = False
            etapes_ok = bool(plan.steps) and json_ok and all(
                getattr(s, "resolved", None) is not None and not s.resolved.rejected and s.resolved.tool in ie.TOOL_HANDLERS
                for s in plan.steps)
            lignes.append({"demande": p, "json_valide": json_ok, "etapes_validees": etapes_ok, "etapes": len(plan.steps),
                           "s": round(time.perf_counter() - t0, 1), "fuite_reflexion": _fuite(r, "")})
    finally:
        oc.chat_full = vraie
    n = len(lignes)
    return {"n": n, "json_valide_pct": round(100 * sum(x["json_valide"] for x in lignes) / n),
            "plans_valides_pct": round(100 * sum(x["etapes_validees"] for x in lignes) / n),
            "s_moyen": round(sum(x["s"] for x in lignes) / n, 1), "fuites": sum(x["fuite_reflexion"] for x in lignes),
            "detail": lignes}


def _documents_sources():
    sys.path.insert(0, str(ROOT / "scripts"))
    from banc_artefacts import REUNION, STAGE, _long

    return {"stage": ("AtlasEssai rapport de stage.docx", "\n".join(STAGE)),
            "reunion": ("AtlasEssai notes de réunion.txt", REUNION),
            "long": ("AtlasEssai histoire longue.txt", _long())}


def p_documents(modele, coupee):
    from core import artefacts as ar
    from tools import documents as d

    essais = []
    vraie = ar._essayer

    def compter(consigne, schema, valide):
        r = ar._generer_json(ar.SYSTEME, consigne, schema)
        ok, raison = valide(r) if r is not None else (False, "vide")
        essais.append(ok)
        if ok:
            return r, ""
        r = ar._generer_json(ar.SYSTEME, f"{consigne}\n\nTa réponse précédente était invalide : {raison}. Corrige-la.", schema)
        ok2, raison2 = valide(r) if r is not None else (False, "vide")
        return (r, "") if ok2 else (None, raison2 or raison)

    ar._essayer = compter
    lignes = []
    try:
        for s in SUJETS_RAPPORT:
            essais.clear()
            t0 = time.perf_counter()
            contenu, raison = ar.rediger_rapport(s)
            lignes.append({"nature": "rapport", "sujet": s, "ok": bool(contenu), "raison": raison,
                           "premier_coup": sum(essais), "appels_valides_attendus": len(essais),
                           "s": round(time.perf_counter() - t0, 1)})
        for cle, (nom, texte) in _documents_sources().items():
            essais.clear()
            t0 = time.perf_counter()
            contenu, raison, retirees = ar.rediger_resume(texte, nom)
            livre = " ".join(" ".join(x["paragraphes"] + (x.get("points") or [])) for x in contenu["sections"]) if contenu else ""
            lignes.append({"nature": "resume", "sujet": cle, "ok": bool(contenu), "raison": raison,
                           "premier_coup": sum(essais), "appels_valides_attendus": len(essais),
                           "faits_inventes_detectes": len(retirees),
                           "faits_absents_livres": len(d.faits_absents(livre, texte)) if contenu else None,
                           "s": round(time.perf_counter() - t0, 1)})
    finally:
        ar._essayer = vraie
    appels = sum(x["appels_valides_attendus"] for x in lignes)
    return {"ok": sum(x["ok"] for x in lignes), "n": len(lignes),
            "premier_coup_pct": round(100 * sum(x["premier_coup"] for x in lignes) / appels) if appels else None,
            "faits_inventes_detectes": sum(x.get("faits_inventes_detectes") or 0 for x in lignes),
            "rapport_s_moyen": round(sum(x["s"] for x in lignes if x["nature"] == "rapport") / 3, 1),
            "resume_s": {x["sujet"]: x["s"] for x in lignes if x["nature"] == "resume"}, "detail": lignes}


def _repondre(question):
    from core.ollama_client import _chat_full_raw

    t0 = time.perf_counter()
    r = asyncio.run(_chat_full_raw(question, {}))
    return r, round(time.perf_counter() - t0, 1)


def p_consignes(modele, coupee):
    lignes = []
    for consigne, verif in CONSIGNES:
        r, s = _repondre(consigne)
        try:
            ok = bool(verif(r))
        except Exception:
            ok = False
        lignes.append({"consigne": consigne, "respectee": ok, "s": s, "reponse": r[:600], "fuite_reflexion": _fuite(r, "")})
    return {"n": len(lignes), "respectees": sum(x["respectee"] for x in lignes),
            "fuites": sum(x["fuite_reflexion"] for x in lignes), "detail": lignes}


def p_conversation(modele, coupee):
    from core.ollama_client import contains_non_latin_script
    from tools.documents import est_francais

    lignes = []
    for q in QUESTIONS:
        r, s = _repondre(q)
        lignes.append({"question": q, "s": s, "caracteres": len(r), "francais": est_francais(r) and not anglais(r),
                       "ecriture_non_latine": contains_non_latin_script(r), "fuite_reflexion": _fuite(r, ""),
                       "reponse": r[:500]})
    n = len(lignes)
    return {"n": n, "francais": sum(x["francais"] for x in lignes),
            "non_latin": sum(x["ecriture_non_latine"] for x in lignes), "fuites": sum(x["fuite_reflexion"] for x in lignes),
            "s_moyen": round(sum(x["s"] for x in lignes) / n, 1),
            "caracteres_moyen": round(sum(x["caracteres"] for x in lignes) / n), "detail": lignes}


def p_processeur(modele, coupee):
    from core.ollama_client import ollama_options

    decharger_tout()
    r = _flux(modele, [{"role": "user", "content": "Quelle est la capitale de l'Italie ? Réponds en une phrase."}],
              ollama_options(num_gpu=0), coupee, keep_alive=0)
    f = r["fin"]
    return {"total_s": r["total_s"], "premier_mot_s": r["premier_mot_s"],
            "chargement_s": round(f.get("load_duration", 0) / 1e9, 2),
            "jetons_par_s": round(f.get("eval_count", 0) / (f.get("eval_duration", 1) / 1e9), 1) if f.get("eval_duration") else None,
            "texte": r["texte"][:200]}


def p_aveugle(modele, coupee):
    from core import artefacts as ar

    conv, _ = _repondre("Donne-moi trois conseils pour mieux dormir, en quelques phrases.")
    section, _ = ar._essayer(
        "Rapport « Les bienfaits de la marche à pied ». Rédige UNIQUEMENT la section « Les effets sur la santé » : "
        "3 paragraphes de 120 à 180 mots chacun, et si utile 2 à 4 points courts. Pas de titre. "
        "N'invente ni chiffre précis ni citation.", ar.SCHEMA_SECTION, ar._section_valide)
    nom, texte = _documents_sources()["stage"]
    resume, raison, _ = ar.rediger_resume(texte, nom)

    def en_texte(c):
        if not c:
            return "(échec)"
        out = [f"# {c['titre']}"] if c.get("titre") else []
        for s in c.get("sections", []):
            out += [f"\n## {s['titre']}"] + s["paragraphes"] + [f"- {p}" for p in s.get("points") or []]
        return "\n".join(out)

    sec = "(échec)" if not section else "\n\n".join(section["paragraphes"] + [f"- {p}" for p in section.get("points") or []])
    return {"conversation": conv, "rapport_section": sec, "resume": en_texte(resume)}


def un_modele(modele, dossier, parties):
    coupee = os.environ.get("ATLAS_MODELE_REFLEXION") == "off"
    res = {"modele": modele, "reflexion_coupee": coupee, "debut": time.strftime("%H:%M:%S")}
    whisper = None
    if "ressources" in parties:
        try:
            from faster_whisper import WhisperModel

            from core.voice_engine import ensure_cuda_libraries

            ensure_cuda_libraries()
            whisper = WhisperModel("base", device="cuda", compute_type="float16")    # comme Atlas
            res["transcription"] = "chargée (faster-whisper base, GPU)"
        except Exception as e:
            res["transcription"] = f"non chargée : {type(e).__name__}: {e}"
    fonctions = {"ressources": p_ressources, "gb1": lambda m, c: p_gb1(m, c, dossier), "plans": p_plans,
                 "documents": p_documents, "consignes": p_consignes, "conversation": p_conversation,
                 "processeur": p_processeur, "aveugle": p_aveugle}
    for p in parties:
        if p == "processeur" and modele not in LEGER:
            continue
        t0 = time.perf_counter()
        try:
            res[p] = fonctions[p](modele, coupee)
        except Exception as e:
            import traceback

            res[p] = {"erreur": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
        res[p + "_duree_s"] = round(time.perf_counter() - t0)
        (dossier / "resultat.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
        print(f"[{modele}] {p} ({res[p + '_duree_s']} s)", flush=True)
    del whisper
    decharger_tout()
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--modeles", default=",".join(STANDARD + LEGER))
    ap.add_argument("--parties", default=",".join(PARTIES))
    ap.add_argument("--un")
    a = ap.parse_args(argv)
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    parties = a.parties.split(",")
    if a.un:
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT / "tests"))
        from banc_donnees import donnees_jetables

        donnees_jetables(prefixe="atlas_banc_modeles_")       # BM0 : avant tout import de core
        un_modele(a.un, dossier, parties)
        return 0
    for modele in a.modeles.split(","):
        sous = dossier / modele.replace(":", "_").replace("/", "_")
        sous.mkdir(exist_ok=True)
        coupee = "thinking" in capacites(modele)
        env = {**os.environ, "ATLAS_MODELE": modele, "PYTHONIOENCODING": "utf-8",
               **({"ATLAS_MODELE_REFLEXION": "off"} if coupee else {})}
        env.pop("ATLAS_DONNEES", None)
        print(f"=== {modele} (réflexion {'coupée' if coupee else 'absente'}) ===", flush=True)
        decharger_tout()
        with open(sous / "journal.txt", "w", encoding="utf-8") as j:
            subprocess.run([PY, "-u", str(pathlib.Path(__file__)), "--un", modele, "--out", str(sous), "--parties",
                            ",".join(parties)], cwd=ROOT, env=env, stdout=j, stderr=subprocess.STDOUT)
        print(f"=== {modele} : fini ===", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
