"""
Sprint Artefacts sur mesure — rejeu réel par Atlas : consignes, retouches, lettre et faits retenus,
« tu peux faire quoi ? », annonces relevées comme la fenêtre web les relève.

    python scripts/rejeu_sur_mesure.py --out <dossier> [--garder 900]

Atlas réel démarre sur des COPIES : mémoire VIDE (les faits retenus sont ceux du rejeu, fictifs),
apprentissage, journal, habitudes, rappels jetables, index des fichiers copié. Documents\\Atlas : le
vrai, mais chaque document produit par le rejeu y est supprimé à la fin (documents de test).

1. « raccourcis » sans document récent : pas une action ;
2. « tu peux faire quoi ? » (court), puis le détail d'une famille ;
3. une fiche avec consignes (tableau, sans sommaire, Word et PDF) : fichiers relus par ce script ;
4. retouches sur ce dernier document : « raccourcis-le », « change le titre en … » → v2, v3, les
   anciennes restent ;
5. faits retenus fictifs, puis une lettre : le nom n'est pas redemandé, et sa source est citée ;
6. un document Word EXTERNE (fictif, mis en forme, posé dans Documents\\AtlasEssaiSurMesure) :
   « rajoute une partie sur … au rapport de stage AtlasEssai » → v2 à côté, perte de mise en forme dite ;
7. Atlas reste ouvert --garder secondes (ou jusqu'au fichier <out>/fin) pour essayer la fenêtre web.
Les annonces sont relevées sur /api/annonces?depuis=N, comme ui/app.js.
"""

from __future__ import annotations

import argparse
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
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from checkup_dynamique import API, DATA, PY, ROOT, attendre, req  # noqa: E402


def _get(chemin: str) -> dict:
    with urllib.request.urlopen(API + chemin, timeout=10) as r:
        return json.loads(r.read().decode("utf-8"))


def _docx_externe(chemin: pathlib.Path) -> None:
    """Un rapport de stage fictif, mis en forme comme par une personne : gras, couleur, police, centré."""
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import RGBColor

    doc = docx.Document()
    t = doc.add_heading("Rapport de stage AtlasEssai", level=0)
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    parties = {
        "Introduction": "Ce stage de cinq mois s'est déroulé chez Nexalia, une entreprise fictive de logistique, du "
                        "6 janvier au 30 mai 2026. Il portait sur l'automatisation des bons de livraison.",
        "Les missions": "La mission principale consistait à écrire un outil qui lit les bons scannés et remplit le "
                        "tableau de suivi. Le budget du projet était de 8 500 euros.",
        "Le bilan": "Le temps de traitement d'un bon a baissé de 27 %. L'équipe utilise l'outil chaque jour.",
    }
    for titre, texte in parties.items():
        doc.add_heading(titre, level=1)
        p = doc.add_paragraph()
        r = p.add_run(texte.split(".")[0] + ".")
        r.bold = True
        r.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        r.font.name = "Georgia"
        p.add_run(" " + ".".join(texte.split(".")[1:]).strip())
    doc.save(str(chemin))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--garder", type=int, default=0, help="secondes d'Atlas ouvert à la fin (fenêtre web)")
    a = ap.parse_args(argv)
    with socket.socket() as s:
        if s.connect_ex(("127.0.0.1", 8550)) == 0:
            raise SystemExit("Refus : Atlas tourne déjà (port 8550).")
    from tools import documents as d

    dossier = pathlib.Path(a.out)
    dossier.mkdir(parents=True, exist_ok=True)
    essai = d.dossier_documents() / "AtlasEssaiSurMesure"
    essai.mkdir(exist_ok=True)
    externe = essai / "AtlasEssai rapport de stage.docx"   # posé APRÈS le démarrage : l'index est passif
    atlas_docs = d.dossier_atlas()
    avant = set(atlas_docs.glob("*")) if atlas_docs.exists() else set()
    travail = pathlib.Path(tempfile.mkdtemp(prefix="atlas_sm_"))
    (travail / "chromadb").mkdir()
    if (DATA / "habits.db").exists():
        shutil.copy2(DATA / "habits.db", travail / "habits.db")
    if (DATA / "file_index.db").exists():
        shutil.copy2(DATA / "file_index.db", travail / "file_index.db")
    env = {**os.environ, "ATLAS_MEMORY": "real", "PYTHONIOENCODING": "utf-8",
           "ATLAS_CHROMA_PATH": str(travail / "chromadb"), "ATLAS_APPRENTISSAGE_DB": str(travail / "apprentissage.db"),
           "ATLAS_ACTIONS_LOG": str(travail / "atlas_actions.jsonl"), "ATLAS_HABITS_DB": str(travail / "habits.db"),
           "ATLAS_RAPPELS_DB": str(travail / "rappels.db"), "ATLAS_FILE_INDEX_DB": str(travail / "file_index.db")}
    res = {"debut": time.strftime("%Y-%m-%d %H:%M:%S"), "scenarios": []}
    journal = open(dossier / "atlas.log", "w", encoding="utf-8")
    atlas = subprocess.Popen([PY, "main.py"], cwd=ROOT, stdout=journal, stderr=subprocess.STDOUT, env=env,
                             creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    vue = {"n": 0}

    def chat(phrase):
        out, _ = req("/chat", {"message": phrase, "history": [], "origine": "fenetre"})
        return out

    def annonces_nouvelles():
        r = _get(f"/annonces?depuis={vue['n']}")
        vue["n"] = r.get("dernier") or vue["n"]
        return r.get("annonces", [])

    def scenario(id_, phrase, attendre_annonce=True, limite=900):
        annonces_nouvelles()
        t0 = time.perf_counter()
        r = chat(phrase)
        ligne = {"id": id_, "phrase": phrase, "reponse": r.get("message") or "", "reponse_s": round(time.perf_counter() - t0, 2)}
        if attendre_annonce:
            while time.perf_counter() - t0 < limite:
                ann = annonces_nouvelles()
                if ann:
                    ligne["annonce"] = ann[0]["message"]
                    ligne["total_s"] = round(time.perf_counter() - t0, 1)
                    break
                time.sleep(2)
        res["scenarios"].append(ligne)
        print(json.dumps(ligne, ensure_ascii=False)[:700], flush=True)
        return ligne

    def nouveaux():
        return sorted(set(atlas_docs.glob("*")) - avant, key=lambda p: p.stat().st_mtime) if atlas_docs.exists() else []

    try:
        if not attendre(API + "/health", 300):
            raise RuntimeError("Atlas n'a pas répondu")
        time.sleep(20)
        _docx_externe(externe)
        t0 = time.time()
        while time.time() - t0 < 1800:
            if "AtlasEssai rapport de stage" in (chat("où est mon rapport de stage AtlasEssai ?").get("message") or ""):
                break
            time.sleep(15)
        res["attente_index_s"] = round(time.time() - t0)

        l = scenario("R1", "raccourcis", attendre_annonce=False)
        time.sleep(3)
        l["fichiers_crees"] = [p.name for p in nouveaux()]
        scenario("R2", "tu peux faire quoi ?", attendre_annonce=False)
        scenario("R3", "que sais-tu faire avec les documents ?", attendre_annonce=False)

        l = scenario("R4", "fais une fiche de révision sur le cycle de l'eau avec un tableau, sans sommaire, en Word et en PDF")
        fichiers = nouveaux()
        l["fichiers"] = [p.name for p in fichiers]
        docx_ = next((p for p in fichiers if p.suffix == ".docx"), None)
        if docx_:
            import docx

            doc = docx.Document(str(docx_))
            l["relu"] = {"tableaux_word": len(doc.tables),
                         "sommaire": any("TOC" in (x.text or "") for x in doc.element.body.iter() if x.tag.endswith("instrText")),
                         "pdf": any(p.suffix == ".pdf" for p in fichiers)}
            pdf = next((p for p in fichiers if p.suffix == ".pdf"), None)
            if pdf:
                import pypdf

                l["relu"]["pdf_pages"] = len(pypdf.PdfReader(str(pdf)).pages)

        l = scenario("R5", "raccourcis-le")
        l["fichiers"] = [p.name for p in nouveaux()]
        l = scenario("R6", "change le titre en Le voyage de l'eau", attendre_annonce=False)
        time.sleep(3)
        l["fichiers"] = [p.name for p in nouveaux()]

        scenario("R7a", "retiens que je m'appelle Camille Martin", attendre_annonce=False)
        scenario("R7b", "retiens que mon adresse est 3 rue des Tilleuls, Nantes", attendre_annonce=False)
        l = scenario("R7", "rédige une lettre formelle pour mon propriétaire pour signaler une fuite")
        lettre = next((p for p in reversed(nouveaux()) if p.suffix == ".docx" and p.name.startswith("Lettre")), None)
        if lettre:
            import docx

            textes = [p.text for p in docx.Document(str(lettre)).paragraphs]
            l["relu"] = {"nom": "Camille Martin" in textes, "adresse": "3 rue des Tilleuls" in textes}

        l = scenario("R8", "rajoute une partie sur les limites au rapport de stage AtlasEssai")
        l["versions_externes"] = sorted(p.name for p in essai.glob("*.docx"))
        v2 = essai / "AtlasEssai rapport de stage (v2).docx"
        if v2.exists():
            import docx

            l["relu"] = {"titres": [p.text for p in docx.Document(str(v2)).paragraphs if p.style.name.startswith("Heading")],
                         "original_intact": externe.exists()}

        res["documents_produits"] = [p.name for p in nouveaux()]
        if a.garder:
            print(f"PRÊT POUR LA FENÊTRE WEB ({a.garder} s, ou fichier {dossier / 'fin'})", flush=True)
            t0 = time.time()
            while time.time() - t0 < a.garder and not (dossier / "fin").exists():
                time.sleep(2)
            res["documents_produits"] = [p.name for p in nouveaux()]
    finally:
        try:
            os.kill(atlas.pid, signal.CTRL_BREAK_EVENT)
            atlas.wait(60)
            res["arret"] = "propre"
        except Exception as e:
            atlas.kill()
            res["arret"] = f"forcé ({e!r})"
        journal.close()
        for p in nouveaux():                                 # documents de test : supprimés
            try:
                p.unlink(missing_ok=True)
            except OSError:                                  # ouvert par Atlas dans une visionneuse : dit, pas caché
                pass
        res["documents_de_test_restants"] = [p.name for p in nouveaux()]
        shutil.rmtree(essai, ignore_errors=True)
        res["source_de_test_supprimee"] = not essai.exists()
        shutil.rmtree(travail, ignore_errors=True)
        (dossier / "rejeu.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
