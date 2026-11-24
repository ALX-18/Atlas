"""
Brief Installeur — fin, IF7 — rejeu réel : un Atlas d'essai lancé pour de vrai (main.py), sur des données JETABLES.

    python scripts/rejeu_comptes.py --out <dossier>

Ce qui est mesuré, sur ce PC, depuis le compte courant :
1. la clé locale : créée au démarrage dans un fichier jetable (ATLAS_CLE_LOCALE), restreinte au compte (icacls) ;
2. l'API : sans clé ou avec une fausse clé → refus (401), sans rien lire ni exécuter ; avec la clé → 200 ;
   la page « / » dit que l'interface web est coupée ; /static/app.js n'est plus servi ;
3. le pont navigateur (s'il est actif dans les réglages) : une page web ou un programme sans Origin → 403 ;
   l'extension (Origin chrome-extension://) → acceptée ;
4. la fenêtre native (desktop/connexion.py) : le serveur vérifié comme « à ce compte », la clé portée, 200 ;
5. l'arrêt : Ctrl+Pause (comme les autres rejeux) → arrêt propre, port libéré ; un Atlas d'essai n'arrête aucun Ollama.

Garde-fous : refus si Atlas tourne déjà ; mémoire, journal, apprentissage, habitudes, rappels et index redirigés
vers un dossier jetable ; aucune phrase n'est envoyée au modèle ; les empreintes de TOUS les fichiers de data/ sont
comparées avant et après. Le démarrage d'Atlas charge le modèle sur la carte graphique (préchauffage) : environ
deux minutes de carte graphique.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
TRAVAIL = pathlib.Path(tempfile.mkdtemp(prefix="atlas_rejeu_comptes_"))
os.environ["ATLAS_CLE_LOCALE"] = str(TRAVAIL / "cle_locale")       # avant checkup_dynamique (pour_essai)
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))
from checkup_dynamique import API, DATA, PY, attendre  # noqa: E402
from core import cle_locale, proprietaire  # noqa: E402


def _empreintes() -> dict:
    return {f.relative_to(DATA).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(DATA.rglob("*")) if f.is_file()}


def _ecoute(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _http(chemin: str, entetes: dict | None = None, corps: dict | None = None) -> tuple[int, str]:
    import urllib.error
    import urllib.request

    donnees = json.dumps(corps).encode() if corps is not None else None
    r = urllib.request.Request(API.rsplit("/api", 1)[0] + chemin, data=donnees,
                               headers={"Content-Type": "application/json", **(entetes or {})},
                               method="POST" if corps is not None else "GET")
    try:
        with urllib.request.urlopen(r, timeout=20) as rep:
            return rep.status, rep.read().decode("utf-8", "replace")[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:400]


def _pont(origine: str | None) -> str:
    import asyncio

    import websockets

    async def go():
        try:
            async with websockets.connect("ws://127.0.0.1:9999", origin=origine, open_timeout=5):
                return "acceptée"
        except websockets.exceptions.InvalidStatus as e:
            return f"refusée ({e.response.status_code})"
        except Exception as e:
            return f"erreur ({type(e).__name__})"
    return asyncio.run(go())


def _acl(chemin: pathlib.Path) -> dict:
    r = subprocess.run(["icacls", str(chemin)], capture_output=True, text=True, encoding="oem", errors="replace")
    lignes = [l.strip() for l in r.stdout.splitlines()[:-2] if l.strip()]
    moi = proprietaire.compte_courant().lower()
    regles = [l.replace(str(chemin), "").strip() for l in lignes]
    return {"regles": len(regles), "toutes_au_compte_courant": all(moi in x.lower() for x in regles),
            "heritees": sum("(I)" in x for x in regles)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    if _ecoute(8550):
        raise SystemExit("Refus : Atlas tourne déjà (port 8550). Rien n'est lancé.")
    pont_libre_avant = not _ecoute(9999)
    avant = _empreintes()
    res: dict = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "fichiers_data_avant": len(avant),
                 "pont_libre_avant": pont_libre_avant}
    env = {**os.environ, "ATLAS_MEMORY": "real", "ATLAS_CHROMA_PATH": str(TRAVAIL / "chromadb"),
           "PYTHONIOENCODING": "utf-8", "ATLAS_ACTIONS_LOG": str(TRAVAIL / "atlas_actions.jsonl"),
           "ATLAS_APPRENTISSAGE_DB": str(TRAVAIL / "apprentissage.db"), "ATLAS_HABITS_DB": str(TRAVAIL / "habits.db"),
           "ATLAS_RAPPELS_DB": str(TRAVAIL / "rappels.db"), "ATLAS_FILE_INDEX_DB": str(TRAVAIL / "file_index.db")}
    journal_f = dossier / "atlas_stdout.log"
    journal = open(journal_f, "w", encoding="utf-8")
    t0 = time.perf_counter()
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas d'essai : pas de réponse en 300 s")
        res["api_prete_s"] = round(time.perf_counter() - t0, 1)

        # 1. La clé
        cle_f = TRAVAIL / "cle_locale"
        res["cle"] = {"creee": cle_f.exists(), "longueur": len(cle_f.read_text(encoding="utf-8").strip()),
                      "droits": _acl(cle_f)}
        res["cle_reelle_creee_dans_data"] = (DATA / "cle_locale").exists() and "cle_locale" not in avant

        # 2. L'API
        bonne = cle_locale.entetes()
        res["api"] = {
            "health_sans_cle": _http("/api/health")[0],
            "health_fausse_cle": _http("/api/health", {cle_locale.ENTETE: "x" * 43})[0],
            "health_avec_cle": _http("/api/health", bonne)[0],
            "rappel_memoire_sans_cle": _http("/api/memory/recall?q=essai")[0],
            "confirmations_sans_cle": _http("/api/confirmations")[0],
            "ingest_sans_cle": _http("/api/memory/ingest", corps={"text": "phrase d'essai IF7, inventée"})[0],
            "confirm_sans_cle": _http("/api/confirm", corps={"confirmation_id": "essai-if7", "accepted": False})[0],
            "page_d_accueil": _http("/"),
            "app_js_avec_cle": _http("/static/app.js", bonne)[0],
        }
        res["api"]["page_d_accueil"] = {"code": res["api"]["page_d_accueil"][0],
                                        "dit_coupee": "coupée" in res["api"]["page_d_accueil"][1]}

        # 3. Le pont
        res["pont_ecoute"] = _ecoute(9999)
        if res["pont_ecoute"]:
            res["pont"] = {"page_web": _pont("https://exemple.invalid"), "sans_origine": _pont(None),
                           "extension": _pont("chrome-extension://abcdefghijklmnopabcdefghijklmnop")}

        # 4. La fenêtre native
        from desktop.connexion import ConnexionAtlas

        c = ConnexionAtlas("http://127.0.0.1:8550", 8550)
        r = c.get("/api/health", timeout=20)
        res["fenetre"] = {"code": r.status_code, "verdict_8550": proprietaire.verifier(8550).etat,
                          "verdict_11434": proprietaire.verifier(11434).etat}
    finally:
        t1 = time.perf_counter()
        try:
            os.kill(atlas.pid, signal.CTRL_BREAK_EVENT)
            atlas.wait(60)
            res["arret"] = {"mode": "propre", "duree_s": round(time.perf_counter() - t1, 1)}
        except Exception as e:
            atlas.kill()
            res["arret"] = {"mode": f"forcé ({type(e).__name__})"}
        journal.close()
        time.sleep(2)
        texte = journal_f.read_text(encoding="utf-8", errors="replace")
        res["arret"].update({"port_libere": not _ecoute(8550), "journal_arret_propre": "Atlas arrêt propre." in texte,
                             "journal_cle_prete": "Clé locale prête" in texte,
                             "ollama_toujours_la": _ecoute(11434)})
        apres = _empreintes()
        res["data_identique"] = apres == avant
        res["data_differences"] = sorted(k for k in set(avant) | set(apres) if avant.get(k) != apres.get(k))
        shutil.rmtree(TRAVAIL, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1, default=str),
                                            encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
