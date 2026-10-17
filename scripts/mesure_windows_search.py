"""
Sprint Index des fichiers / IX1.2 — Windows Search sur ce PC (LECTURE SEULE, aucun nom relevé).

    python scripts/mesure_windows_search.py --out <fichier.json>

- le service WSearch : état, démarrage ;
- les emplacements inclus et exclus (registre, CrawlScopeManager) — chemins génériques seulement
  (le nom d'utilisateur est remplacé par <utilisateur>) ;
- par disque : nombre d'éléments que l'index rend (plafonné), et si le CONTENU est indexé ;
- vitesse de requête : par nom, par contenu, par date (moyenne de 5).
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

PLAFOND = 300_000


def _anonyme(chemin: str) -> str:
    u = os.environ.get("USERNAME", "")
    return chemin.replace(u, "<utilisateur>") if u else chemin


def service() -> dict:
    out = subprocess.run(["sc", "query", "WSearch"], capture_output=True, text=True).stdout
    conf = subprocess.run(["sc", "qc", "WSearch"], capture_output=True, text=True).stdout
    etat = next((l.split(":", 1)[1].strip() for l in out.splitlines() if "STATE" in l or "ÉTAT" in l.upper()), "?")
    demarrage = next((l.split(":", 1)[1].strip() for l in conf.splitlines() if "START_TYPE" in l or "DEMARRAGE" in l.upper()), "?")
    return {"etat": etat, "demarrage": demarrage}


def regles() -> list[dict]:
    import winreg

    base = r"SOFTWARE\Microsoft\Windows Search\CrawlScopeManager\Windows\SystemIndex"
    out = []
    for sous in ("WorkingSetRules", "DefaultRules"):
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"{base}\\{sous}")
        except OSError:
            continue
        i = 0
        while True:
            try:
                nom = winreg.EnumKey(k, i)
            except OSError:
                break
            i += 1
            try:
                r = winreg.OpenKey(k, nom)
                url = winreg.QueryValueEx(r, "URL")[0]
                inclus = winreg.QueryValueEx(r, "Include")[0]
                out.append({"source": sous, "url": _anonyme(url), "inclus": bool(inclus)})
            except OSError:
                continue
    return out


def _connexion():
    import win32com.client

    c = win32com.client.Dispatch("ADODB.Connection")
    c.Open("Provider=Search.CollatorDSO;Extended Properties='Application=Windows';")
    return c


def _compter(c, sql: str) -> tuple[int, float]:
    import win32com.client

    t = time.perf_counter()
    rs = win32com.client.Dispatch("ADODB.Recordset")
    n = 0
    try:
        rs.Open(sql, c)
        while not rs.EOF and n < PLAFOND:
            n += 1
            rs.MoveNext()
        rs.Close()
    except Exception as e:              # le fournisseur coupe parfois un parcours long : compté jusque-là
        print(f"  (arrêt du fournisseur après {n} éléments : {str(e)[:80]})", flush=True)
        n = -n if n else -1
    return n, round(time.perf_counter() - t, 3)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--disques", default="A:,C:,S:,T:")
    a = ap.parse_args(argv)
    res = {"service": service(), "regles": regles(), "disques": {}, "requetes": {}}
    try:
        c = _connexion()
    except Exception as e:
        res["erreur"] = f"Windows Search injoignable : {type(e).__name__}: {e}"
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(res, ensure_ascii=False, indent=1))
        return 0
    for d in a.disques.split(","):
        scope = f"file:{d}/"
        n, s = _compter(c, f"SELECT System.ItemUrl FROM SystemIndex WHERE SCOPE='{scope}'")
        n_docs, s_docs = _compter(c, f"SELECT System.ItemUrl FROM SystemIndex WHERE SCOPE='{scope}' AND "
                                     "(System.FileExtension='.pdf' OR System.FileExtension='.docx' OR "
                                     "System.FileExtension='.txt' OR System.FileExtension='.md')")
        res["disques"][d] = {"elements": n, "plafond_atteint": n >= PLAFOND, "duree_s": s,
                             "documents_pdf_docx_txt_md": n_docs}
        print(d, res["disques"][d], flush=True)
    for nom, sql in {
        "nom (« rapport »)": "SELECT System.ItemUrl FROM SystemIndex WHERE System.FileName LIKE '%rapport%'",
        "contenu (« budget »)": "SELECT System.ItemUrl FROM SystemIndex WHERE CONTAINS('\"budget\"')",
        "récents (7 jours)": "SELECT System.ItemUrl FROM SystemIndex WHERE System.DateModified >= '"
                             + time.strftime("%Y-%m-%d", time.localtime(time.time() - 7 * 86400)) + "'",
    }.items():
        mesures = [_compter(c, sql) for _ in range(5)]
        res["requetes"][nom] = {"resultats": mesures[0][0], "duree_moyenne_s": round(sum(m[1] for m in mesures) / 5, 3)}
        print(nom, res["requetes"][nom], flush=True)
    Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
