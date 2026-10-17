"""
Sprint Artefacts / AR3 — banc réel : le vrai modèle local rédige, le moteur produit et relit.

    python scripts/banc_artefacts.py --out <dossier>

- 3 rapports sur des sujets différents ;
- 10 résumés de 3 documents de TEST (fictifs, écrits ici), dont un plus long que le contexte du
  modèle (num_ctx 8 192) : 4 + 3 + 3 résumés.
Pour chacun : temps, pages (PDF produit), structure (valide, sections, titres Word), faits
inventés DÉTECTÉS (phrases retirées), et un second contrôle sur le document livré (doit être 0).
Les fichiers sont produits dans <dossier>/documents (jamais dans Documents\\Atlas) : ce sont des
documents de test.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

STAGE = [
    "Rapport de stage — Développement d'outils internes chez Nexalia",
    "Le stage s'est déroulé chez Nexalia, à Lyon, du 6 janvier au 30 mai 2026, au sein de l'équipe outils, qui "
    "compte 12 personnes. Il était encadré par M. Bertrand Lefèvre, responsable technique.",
    "La mission principale consistait à remplacer des scripts de traitement de fichiers par une application unique. "
    "Trois applications ont été livrées : un tableau de bord de suivi, un outil d'import et un module d'export.",
    "Le travail a réduit de 27 % le temps de traitement des fichiers clients. Le budget du projet était de 8 500 "
    "euros, principalement consacré aux licences et à un serveur de test.",
    "Les difficultés ont surtout concerné la qualité des données d'origine : environ 4 % des fichiers contenaient "
    "des erreurs de format, qu'il a fallu corriger avant tout traitement automatique.",
    "Le stage a permis d'acquérir des compétences en Python, en bases de données et en conduite de projet. Une "
    "soutenance est prévue le 18 juin 2026 devant un jury de 3 personnes.",
]
REUNION = """Comité projet Orion — notes de réunion du 14 octobre 2026
Participants : Claire Martin, Hugo Petit, Sofia Benali.
1. Avancement : la maquette est terminée à 80 %. Hugo Petit présente les écrans validés.
2. Budget : 45 000 euros engagés sur 60 000 prévus. Pas de dépassement attendu.
3. Calendrier : le lancement est fixé au 2 décembre 2026. Une recette aura lieu le 20 novembre.
4. Risques : retard possible du prestataire de traduction ; Sofia Benali le relance cette semaine.
Décisions : la version mobile est reportée à 2027. Claire Martin rédige le plan de communication.
Actions : Hugo Petit corrige les 6 anomalies ouvertes avant le 31 octobre. Sofia Benali envoie le compte rendu.
"""
CHAPITRES = [
    ("La fondation", 1987, "Jeanne Morel", 14, "un ancien hangar de la péniche Marguerite"),
    ("Les premières fêtes du canal", 1991, "Paul Granger", 300, "le quai de Bercy"),
    ("La crue", 1994, "Lucie Fabre", 42, "l'écluse numéro 7"),
    ("La rénovation des berges", 1998, "Marc Dupuis", 1200, "la ville de Montargis"),
    ("Le festival", 2003, "Inès Roussel", 5000, "le parc des Prés"),
    ("Les classes de découverte", 2009, "Karim Haddad", 860, "les écoles du canton"),
    ("La crise financière", 2013, "Élodie Garnier", 18, "le conseil départemental"),
    ("Le musée des bateliers", 2017, "Thomas Leclerc", 7400, "l'ancienne maison éclusière"),
    ("La pandémie", 2020, "Nadia Belkacem", 65, "les adhérents isolés"),
    ("Le quarantième anniversaire", 2027, "Julien Marchand", 400, "la mairie de Montargis"),
]


def _long() -> str:
    """Un document bien plus long que le contexte du modèle (environ 40 000 caractères)."""
    blocs = ["Histoire de l'association Les Amis du Canal"]
    for titre, annee, nom, nombre, lieu in CHAPITRES:
        blocs.append(f"{titre} ({annee})")
        for k in range(1, 7):
            blocs.append(f"En {annee}, {nom} a coordonné l'action de l'association autour de {lieu}. "
                         f"Le chapitre « {titre} » réunit {nombre} participants selon les registres de l'époque. "
                         f"Ce passage {k} décrit les réunions, les choix de l'équipe et l'entretien régulier des "
                         f"berges, des écluses et des bateaux, avec le soutien constant des bénévoles du canal. " * 2)
    return "\n\n".join(blocs)


def _docx_source(chemin: pathlib.Path, paragraphes: list[str]) -> None:
    corps = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphes)
    with zipfile.ZipFile(chemin, "w") as z:
        z.writestr("word/document.xml", f'<w:document xmlns:w="w"><w:body>{corps}</w:body></w:document>')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    from core import artefacts as ar
    from core import file_indexer as fi
    from tools import documents as d

    dossier = pathlib.Path(a.out)
    (dossier / "sources").mkdir(parents=True, exist_ok=True)
    sortie = dossier / "documents"
    sortie.mkdir(exist_ok=True)
    d.dossier_atlas = lambda: sortie                      # documents de test : jamais Documents\Atlas
    sources = {"stage": dossier / "sources" / "AtlasEssai rapport de stage.docx",
               "reunion": dossier / "sources" / "AtlasEssai notes de réunion.txt",
               "long": dossier / "sources" / "AtlasEssai histoire longue.txt"}
    _docx_source(sources["stage"], STAGE)
    sources["reunion"].write_text(REUNION, encoding="utf-8")
    sources["long"].write_text(_long(), encoding="utf-8")
    plan = ([("rapport", s) for s in ("la photosynthèse", "l'histoire de l'imprimerie",
                                      "les énergies renouvelables en France")] +
            [("resume", "stage")] * 4 + [("resume", "reunion")] * 3 + [("resume", "long")] * 3)
    res = []
    for k, (nature, quoi) in enumerate(plan, 1):
        t0 = time.perf_counter()
        ligne = {"n": k, "nature": nature, "sujet_ou_source": quoi}
        retirees = []
        if nature == "rapport":
            contenu, raison = ar.rediger_rapport(quoi)
            pied = d.PIED_RAPPORT
        else:
            texte = fi.extraire_texte(str(sources[quoi]), sources[quoi].suffix.lower(), 400_000)
            ligne["source_caracteres"] = len(texte)
            ligne["morceaux"] = len(ar._morceaux(texte))
            contenu, raison, retirees = ar.rediger_resume(texte, sources[quoi].name)
            pied = d.PIED_RESUME
        ligne["redaction_s"] = round(time.perf_counter() - t0, 1)
        if not contenu:
            ligne.update({"ok": False, "raison": raison, "faits_inventes_detectes": len(retirees)})
            res.append(ligne)
            print(json.dumps(ligne, ensure_ascii=False), flush=True)
            continue
        faits, raison = ar.produire(contenu, ["docx", "pdf"], pied)
        ligne["total_s"] = round(time.perf_counter() - t0, 1)
        ligne["ok"] = not raison and len(faits) == 2
        ligne["raison"] = raison
        ligne["titre"] = contenu["titre"]
        ligne["sections"] = len(contenu["sections"])
        ligne["structure_valide"] = d.valider_contenu(contenu)[0]
        for f in faits:
            ok, _, info = d.verifier_fichier(f)
            if f.suffix == ".pdf":
                ligne["pages_pdf"] = info.get("pages")
            else:
                ligne["titres_word"] = info.get("titres")
        ligne["faits_inventes_detectes"] = len(retirees)
        ligne["faits_retires"] = [r["faits"] for r in retirees]
        if nature == "resume":
            texte_livre = " ".join(" ".join(s["paragraphes"] + (s.get("points") or [])) for s in contenu["sections"])
            src = fi.extraire_texte(str(sources[quoi]), sources[quoi].suffix.lower(), 400_000)
            ligne["faits_absents_dans_le_livre"] = len(d.faits_absents(texte_livre, src))
        res.append(ligne)
        print(json.dumps({x: v for x, v in ligne.items() if x != "faits_retires"}, ensure_ascii=False), flush=True)
    (dossier / "banc.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
