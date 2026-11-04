"""
Sprint Artefacts — le moteur DÉTERMINISTE des documents.

Le modèle de langue rédige un contenu STRUCTURÉ ; ce module, sans modèle :
- le valide (`valider_contenu`) : champs présents, longueurs raisonnables, français ;
- produit le fichier : Word (`ecrire_docx`, python-docx : vrais styles de titre, sommaire Word,
  listes, pied de page numéroté) ou PDF (`ecrire_pdf`, fpdf2 : polices TrueType de Windows pour
  les accents, titres, numéros de page) — sans Word ni LibreOffice installés ;
- le RELIT (`verifier_fichier`) : Atlas ne dit « j'ai créé » qu'après cette relecture ;
- le range (`chemin_libre`) : Documents\\Atlas\\<titre court> - <date>.<ext>, jamais d'écrasement ;
- vérifie qu'un résumé n'invente rien (`faits_absents`, `retirer_faits_inventes`) : nombres,
  dates et noms propres du résumé doivent figurer dans la source.

Structure attendue :
    {"titre": str, "sections": [{"titre": str, "paragraphes": [str, ...], "points": [str, ...]}],
     "points_cles": [str, ...]}         (points, points_cles : facultatifs)
"""

from __future__ import annotations

import copy
import os
import pathlib
import re
import time
import unicodedata
from typing import Any, Optional

PIED_RAPPORT = "Rédigé par Atlas avec un modèle local — à relire"
PIED_RESUME = "Résumé rédigé par Atlas avec un modèle local, vérifié contre le document source — à relire"
SOMMAIRE_MOTS_MIN = 800      # Jugement d'Alexis : un sommaire sur 300 mots ne sert à rien

_MOTS_FR = {"le", "la", "les", "de", "des", "du", "et", "est", "un", "une", "en", "que", "qui", "pour", "dans",
            "par", "sur", "au", "aux", "ce", "cette", "il", "elle", "sont", "avec", "pas", "plus", "ou", "se",
            "son", "sa", "ses", "leur", "leurs", "on", "nous", "vous", "mais", "comme", "être", "été"}


# --------------------------------------------------------------------------- #
#  Validation du contenu rédigé par le modèle
# --------------------------------------------------------------------------- #

def _textes(contenu: dict) -> list[str]:
    out = [contenu.get("titre", "")]
    for s in contenu.get("sections", []):
        out.append(s.get("titre", ""))
        out += list(s.get("paragraphes", [])) + list(s.get("points", []) or [])
    out += list(contenu.get("points_cles", []) or [])
    return [t for t in out if isinstance(t, str)]


def est_francais(texte: str) -> bool:
    mots = re.findall(r"[a-zàâäéèêëîïôöùûüç']+", texte.lower())
    if len(mots) < 8:
        return True                       # trop court pour juger
    fr = [m for m in mots if m in _MOTS_FR]
    return len(set(fr)) >= 3 and len(fr) / len(mots) >= 0.08


def _tableau_valide(tab: Any) -> str:
    """Raison du refus d'un tableau (Artefacts sur mesure), ou ""."""
    if not isinstance(tab, dict):
        return "tableau mal formé"
    cols, lignes = tab.get("colonnes"), tab.get("lignes")
    if not isinstance(cols, list) or not (1 <= len(cols) <= 8) or not all(isinstance(c, str) and c.strip() for c in cols):
        return "tableau : de 1 à 8 colonnes nommées"
    if not isinstance(lignes, list) or not (1 <= len(lignes) <= 40):
        return "tableau : de 1 à 40 lignes"
    for ligne in lignes:
        if not isinstance(ligne, list) or len(ligne) != len(cols) or not all(isinstance(c, (str, int, float)) for c in ligne):
            return "tableau : chaque ligne a autant de cases que de colonnes"
    return ""


def valider_contenu(contenu: Any, langue: str = "fr") -> tuple[bool, str]:
    """(valide ?, raison). La raison dit ce qui manque : elle est renvoyée au modèle une fois.
    langue (Artefacts sur mesure) : « en », « es »… pour un document demandé dans une autre langue."""
    if not isinstance(contenu, dict):
        return False, "structure : un objet JSON était attendu"
    titre = contenu.get("titre")
    if not isinstance(titre, str) or not (3 <= len(titre.strip()) <= 150):
        return False, "titre absent ou de longueur anormale (3 à 150 caractères)"
    sections = contenu.get("sections")
    if not isinstance(sections, list) or not (1 <= len(sections) <= 15):
        return False, "sections absentes (de 1 à 15 attendues)"
    for k, s in enumerate(sections, 1):
        if not isinstance(s, dict) or not isinstance(s.get("titre"), str) or not s["titre"].strip():
            return False, f"section {k} : titre de section absent"
        paras = s.get("paragraphes")
        if not isinstance(paras, list) or not paras or not all(isinstance(p, str) and 15 <= len(p.strip()) <= 4000
                                                                for p in paras):
            return False, f"section {k} : paragraphes absents ou de longueur anormale (15 à 4000 caractères)"
        points = s.get("points", [])
        if points is not None and (not isinstance(points, list) or not all(isinstance(p, str) and len(p) <= 400
                                                                            for p in points)):
            return False, f"section {k} : liste de points mal formée"
        if s.get("tableau") is not None:
            raison = _tableau_valide(s["tableau"])
            if raison:
                return False, f"section {k} : {raison}"
    pc = contenu.get("points_cles", [])
    if pc is not None and (not isinstance(pc, list) or not all(isinstance(p, str) for p in pc)):
        return False, "points clés mal formés"
    tout = " ".join(_textes(contenu))
    from core.ollama_client import contains_non_latin_script

    if contains_non_latin_script(tout):
        return False, "le texte ne doit contenir aucun caractère chinois, cyrillique ou arabe"
    if langue == "fr" and not est_francais(tout):
        return False, "le texte doit être rédigé en français"
    if len(tout) < 150:
        return False, "contenu trop court"
    return True, ""


# --------------------------------------------------------------------------- #
#  Word
# --------------------------------------------------------------------------- #

def _champ(paragraphe, instruction: str, texte_provisoire: str = "") -> None:
    """Un champ Word (sommaire, numéro de page) : Word le calcule à l'ouverture."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def run_avec(el):
        r = OxmlElement("w:r")
        r.append(el)
        paragraphe._p.append(r)

    debut = OxmlElement("w:fldChar")
    debut.set(qn("w:fldCharType"), "begin")
    run_avec(debut)
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = instruction
    run_avec(instr)
    sep = OxmlElement("w:fldChar")
    sep.set(qn("w:fldCharType"), "separate")
    run_avec(sep)
    if texte_provisoire:
        t = OxmlElement("w:t")
        t.text = texte_provisoire
        run_avec(t)
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    run_avec(fin)


def _tableau_docx(doc, tab: dict) -> None:
    t = doc.add_table(rows=1, cols=len(tab["colonnes"]))
    t.style = "Table Grid"
    for k, c in enumerate(tab["colonnes"]):
        cell = t.rows[0].cells[k]
        cell.text = str(c)
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for ligne in tab["lignes"]:
        cells = t.add_row().cells
        for k, v in enumerate(ligne):
            cells[k].text = str(v)
    doc.add_paragraph()


def _lettre_docx(doc, contenu: dict) -> None:
    """Une lettre : expéditeur, destinataire, lieu et date, objet, corps sans titres, signature."""
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    for ligne in contenu.get("expediteur") or []:
        doc.add_paragraph(ligne)
    for ligne in contenu.get("destinataire") or []:
        doc.add_paragraph(ligne).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if contenu.get("lieu_date"):
        doc.add_paragraph(contenu["lieu_date"]).alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if contenu.get("objet"):
        p = doc.add_paragraph()
        p.add_run("Objet : ").bold = True
        p.add_run(contenu["objet"])
    for s in contenu["sections"]:
        for para in s["paragraphes"]:
            doc.add_paragraph(para.strip())
        for pt in s.get("points") or []:
            doc.add_paragraph(pt.strip(), style="List Bullet")
    if contenu.get("signature"):
        doc.add_paragraph()
        doc.add_paragraph(contenu["signature"]).alignment = WD_ALIGN_PARAGRAPH.RIGHT


def ecrire_docx(contenu: dict, chemin: pathlib.Path, pied: str = PIED_RAPPORT, sommaire: Optional[bool] = None) -> dict:
    """Écrit le Word ; rend ce que le MOTEUR a écrit : {"sommaire": bool, "tableaux": n}.
    sommaire (Artefacts sur mesure) : None → 3 sections ou plus ET un texte long ; False → jamais ; True → toujours."""
    import docx
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt

    doc = docx.Document()
    styles = doc.styles
    styles["Normal"].font.name = "Calibri"
    styles["Normal"].font.size = Pt(11)
    # Langue française (correcteur), et le sommaire mis à jour à l'ouverture.
    rpr = styles["Normal"].element.get_or_add_rPr()
    lang = OxmlElement("w:lang")
    lang.set(qn("w:val"), "fr-FR")
    rpr.append(lang)
    maj = OxmlElement("w:updateFields")
    maj.set(qn("w:val"), "true")
    doc.settings.element.append(maj)
    doc.core_properties.title = contenu["titre"]
    doc.core_properties.author = "Atlas"
    doc.core_properties.language = "fr-FR"

    lettre = contenu.get("genre") == "lettre"
    assez_long = len(contenu["sections"]) >= 3 and len(" ".join(_textes(contenu)).split()) >= SOMMAIRE_MOTS_MIN
    avec_sommaire = False if lettre else (assez_long if sommaire is None else bool(sommaire))
    tableaux = 0
    if lettre:
        _lettre_docx(doc, contenu)
    else:
        doc.add_heading(contenu["titre"], level=0)
        if avec_sommaire:
            doc.add_paragraph("Sommaire").runs[0].bold = True
            _champ(doc.add_paragraph(), 'TOC \\o "1-2" \\h \\z \\u',
                   "Le sommaire se met à jour à l'ouverture (sinon : clic droit, « Mettre à jour les champs »).")
        for s in contenu["sections"]:
            doc.add_heading(s["titre"], level=1)
            for p in s["paragraphes"]:
                doc.add_paragraph(p.strip())
            for pt in s.get("points") or []:
                doc.add_paragraph(pt.strip(), style="List Bullet")
            if (s.get("tableau") or {}).get("lignes"):
                _tableau_docx(doc, s["tableau"])
                tableaux += 1
        if contenu.get("points_cles"):
            doc.add_heading("Points clés", level=1)
            for pt in contenu["points_cles"]:
                doc.add_paragraph(pt.strip(), style="List Bullet")
    pied_p = doc.sections[0].footer.paragraphs[0]
    pied_p.text = f"{pied} — page "
    _champ(pied_p, "PAGE", "1")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(chemin))
    return {"sommaire": avec_sommaire, "tableaux": tableaux}


# --------------------------------------------------------------------------- #
#  PDF
# --------------------------------------------------------------------------- #

_POLICES = {"": "arial.ttf", "B": "arialbd.ttf", "I": "ariali.ttf"}


def ecrire_pdf(contenu: dict, chemin: pathlib.Path, pied: str = PIED_RAPPORT, sommaire: Optional[bool] = None) -> dict:
    """Écrit le PDF (signets par section, pas de page de sommaire) ; rend {"sommaire": False, "tableaux": n}."""
    from fpdf import FPDF

    fonts = pathlib.Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    unicode_ok = all((fonts / f).exists() for f in _POLICES.values())

    def t(texte: str) -> str:            # sans police TrueType : latin-1 seulement (repli)
        return texte if unicode_ok else texte.replace("—", "-").replace("’", "'").replace("œ", "oe") \
            .encode("latin-1", "replace").decode("latin-1")

    class Doc(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_font(police, "I", 8)
            self.set_text_color(110)
            self.cell(0, 8, t(f"{pied} — Page {self.page_no()}/{{nb}}"), align="C")

    pdf = Doc(format="A4")
    if unicode_ok:
        for style, f in _POLICES.items():
            pdf.add_font("Arial", style, str(fonts / f))
        police = "Arial"
    else:
        police = "Helvetica"
    pdf.set_title(contenu["titre"])
    pdf.set_author("Atlas")
    pdf.set_lang("fr-FR")
    pdf.set_auto_page_break(True, margin=20)
    pdf.set_margins(20, 18, 20)
    pdf.add_page()
    lettre = contenu.get("genre") == "lettre"
    tableaux = 0

    def paragraphes(s):
        pdf.set_font(police, "", 11)
        for p in s["paragraphes"]:
            pdf.multi_cell(0, 6, t(p.strip()), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
        for pt in s.get("points") or []:
            pdf.multi_cell(0, 6, t(f"•  {pt.strip()}"), new_x="LMARGIN", new_y="NEXT")

    if lettre:
        pdf.set_font(police, "", 11)
        for ligne in contenu.get("expediteur") or []:
            pdf.multi_cell(0, 6, t(ligne), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        for ligne in (contenu.get("destinataire") or []) + ([contenu["lieu_date"]] if contenu.get("lieu_date") else []):
            pdf.multi_cell(0, 6, t(ligne), align="R", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        if contenu.get("objet"):
            pdf.set_font(police, "B", 11)
            pdf.multi_cell(0, 6, t(f"Objet : {contenu['objet']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        for s in contenu["sections"]:
            paragraphes(s)
        if contenu.get("signature"):
            pdf.ln(6)
            pdf.multi_cell(0, 6, t(contenu["signature"]), align="R", new_x="LMARGIN", new_y="NEXT")
        chemin.parent.mkdir(parents=True, exist_ok=True)
        pdf.output(str(chemin))
        return {"sommaire": False, "tableaux": 0}
    pdf.set_font(police, "B", 20)
    pdf.multi_cell(0, 10, t(contenu["titre"]), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    for s in contenu["sections"]:
        pdf.start_section(t(s["titre"]))           # signet (sommaire du lecteur PDF)
        pdf.set_font(police, "B", 14)
        pdf.multi_cell(0, 8, t(s["titre"]), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)
        paragraphes(s)
        tab = s.get("tableau") or {}
        if tab.get("lignes"):
            pdf.ln(2)
            pdf.set_font(police, "", 10)
            with pdf.table(text_align="LEFT") as table:
                entete = table.row()
                for c in tab["colonnes"]:
                    entete.cell(t(str(c)))
                for ligne in tab["lignes"]:
                    r = table.row()
                    for v in ligne:
                        r.cell(t(str(v)))
            tableaux += 1
        pdf.ln(3)
    if contenu.get("points_cles"):
        pdf.set_font(police, "B", 14)
        pdf.multi_cell(0, 8, t("Points clés"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(police, "", 11)
        for pt in contenu["points_cles"]:
            pdf.multi_cell(0, 6, t(f"•  {pt.strip()}"), new_x="LMARGIN", new_y="NEXT")
    chemin.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(chemin))
    return {"sommaire": False, "tableaux": tableaux}


# --------------------------------------------------------------------------- #
#  Relecture : Atlas ne dit « j'ai créé » qu'après elle
# --------------------------------------------------------------------------- #

def verifier_fichier(chemin: pathlib.Path, exige_titres: bool = True) -> tuple[bool, str, dict]:
    """(bon ?, raison, infos). Le fichier existe, n'est pas vide, se relit et contient du texte.
    exige_titres=False pour une lettre (pas de titres de section)."""
    chemin = pathlib.Path(chemin)
    if not chemin.exists():
        return False, "le fichier n'existe pas", {}
    if chemin.stat().st_size == 0:
        return False, "le fichier est vide", {}
    try:
        if chemin.suffix.lower() == ".docx":
            import docx

            doc = docx.Document(str(chemin))
            textes = [p.text for p in doc.paragraphs if p.text.strip()]
            titres = [p.text for p in doc.paragraphs if p.style.name.startswith("Heading")]
            if not textes or (exige_titres and not titres):
                return False, "le document relu ne contient pas de texte ou de titres", {}
            car = sum(len(x) for x in textes)
            return True, "", {"paragraphes": len(textes), "titres": len(titres), "caracteres": car,
                              "tableaux": len(doc.tables), "pages_estimees": max(1, round(car / 2600 + 0.5))}
        if chemin.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            r = PdfReader(str(chemin))
            texte = " ".join((p.extract_text() or "") for p in r.pages)
            if not r.pages or len(texte.strip()) < 20:
                return False, "le PDF relu ne contient pas de texte", {}
            return True, "", {"pages": len(r.pages), "caracteres": len(texte)}
    except Exception as e:
        return False, f"le fichier ne se relit pas ({type(e).__name__})", {}
    return False, f"format inattendu : {chemin.suffix}", {}


# --------------------------------------------------------------------------- #
#  Artefacts sur mesure / AS2 — relire un Word (créé par Atlas ou non) pour le retoucher
# --------------------------------------------------------------------------- #

def lire_docx(chemin: pathlib.Path) -> tuple[dict, dict]:
    """(contenu, mise_en_forme). Le contenu suit la structure d'Atlas : titre (style Title, sinon le
    premier titre), sections (Heading 1/2), paragraphes, puces (styles « List »), tableaux.
    mise_en_forme : ce que la retouche ne saura PAS garder, compté (images, styles propres, gras,
    italique, couleurs, polices, en-têtes et pieds de page, alignements)."""
    import docx
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph

    doc = docx.Document(str(chemin))
    contenu: dict = {"titre": "", "sections": []}
    courante = None
    tables = iter(doc.tables)                  # dans l'ordre du document, comme les éléments w:tbl
    corps = doc.element.body
    for el in corps.iterchildren():
        if el.tag == qn("w:tbl"):
            t = next(tables, None)
            if t is None:
                continue
            lignes = [[c.text.strip() for c in r.cells] for r in t.rows]
            if lignes:
                if courante is None:
                    courante = {"titre": "Texte", "paragraphes": [], "points": []}
                    contenu["sections"].append(courante)
                courante["tableau"] = {"colonnes": lignes[0] or ["Colonne"], "lignes": lignes[1:] or [[""] * len(lignes[0])]}
            continue
        if el.tag != qn("w:p"):
            continue
        p = Paragraph(el, doc)
        texte = p.text.strip()
        if not texte:
            continue
        style = p.style.name if p.style is not None else ""
        if style == "Title" and not contenu["titre"]:
            contenu["titre"] = texte
        elif style.startswith("Heading"):
            courante = {"titre": texte, "paragraphes": [], "points": []}
            contenu["sections"].append(courante)
        elif texte == "Sommaire" or texte.startswith("Le sommaire se met à jour"):
            continue
        else:
            if courante is None:
                courante = {"titre": "Texte", "paragraphes": [], "points": []}
                contenu["sections"].append(courante)
            (courante["points"] if style.startswith("List") else courante["paragraphes"]).append(texte)
    if not contenu["titre"]:
        contenu["titre"] = (doc.core_properties.title or "").strip() or pathlib.Path(chemin).stem
    for s in contenu["sections"]:
        if not s["paragraphes"] and s["points"]:
            s["paragraphes"], s["points"] = [" ".join(s["points"])], []
    contenu["sections"] = [s for s in contenu["sections"] if s["paragraphes"] or s.get("tableau")]
    for s in contenu["sections"]:
        if not s["paragraphes"]:
            s["paragraphes"] = ["(tableau)"]
    runs = [r for p in doc.paragraphs for r in p.runs]
    styles_propres = {p.style.name for p in doc.paragraphs if p.style is not None} - {
        "Normal", "Title", "Heading 1", "Heading 2", "List Bullet", "List Number", "List Paragraph"}
    mise_en_forme = {
        "sommaire": "TOC " + chr(92) + "o" in doc.element.xml or any(p.text.strip() == "Sommaire" for p in doc.paragraphs),
        "images": len(doc.inline_shapes),
        "tableaux": len(doc.tables),
        "styles_propres": sorted(styles_propres),
        "gras_italique": sum(1 for r in runs if r.bold or r.italic),
        "couleurs": sum(1 for r in runs if r.font.color is not None and r.font.color.rgb is not None),
        "polices": sorted({r.font.name for r in runs if r.font.name}),
        "entetes_pieds": sum(1 for s in doc.sections for x in (s.header, s.footer)
                             if any(p.text.strip() for p in x.paragraphs)),
        "alignements": sum(1 for p in doc.paragraphs if p.alignment not in (None, 0)),
    }
    return contenu, mise_en_forme


def perte_de_mise_en_forme(mf: dict) -> list[str]:
    """Ce qui ne sera pas gardé dans la nouvelle version, en mots simples."""
    out = []
    if mf.get("images"):
        out.append(f"{mf['images']} image(s)")
    if mf.get("styles_propres"):
        out.append("les styles " + ", ".join(f"« {s} »" for s in mf["styles_propres"][:4]))
    if mf.get("gras_italique"):
        out.append(f"le gras et l'italique ({mf['gras_italique']} passage(s))")
    if mf.get("couleurs"):
        out.append(f"les couleurs de texte ({mf['couleurs']})")
    if mf.get("polices"):
        out.append("les polices " + ", ".join(mf["polices"][:3]))
    if mf.get("entetes_pieds"):
        out.append("l'en-tête et le pied de page d'origine")
    if mf.get("alignements"):
        out.append(f"les alignements ({mf['alignements']} paragraphe(s))")
    return out


def chemin_version(chemin: pathlib.Path) -> pathlib.Path:
    """« Rapport - 2026-10-24.docx » → « … (v2).docx », puis (v3)… Jamais un fichier existant."""
    chemin = pathlib.Path(chemin)
    m = re.match(r"^(?P<base>.*?)(?: \(v(?P<n>\d+)\))?$", chemin.stem)
    base, n = m.group("base"), int(m.group("n") or 1)
    while True:
        n += 1
        cand = chemin.with_name(f"{base} (v{n}){chemin.suffix}")
        if not cand.exists():
            return cand


# --------------------------------------------------------------------------- #
#  Rangement : Documents\Atlas, jamais d'écrasement
# --------------------------------------------------------------------------- #

def dossier_documents() -> pathlib.Path:
    """Le dossier Documents réel (il peut être déplacé, par exemple dans OneDrive)."""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as k:
            v = os.path.expandvars(winreg.QueryValueEx(k, "Personal")[0])
            if v and os.path.isdir(v):
                return pathlib.Path(v)
    except Exception:
        pass
    return pathlib.Path(os.path.expandvars("%USERPROFILE%")) / "Documents"


def dossier_atlas() -> pathlib.Path:
    return dossier_documents() / "Atlas"


def titre_court(titre: str, longueur: int = 60) -> str:
    t = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", titre or "Document")
    t = " ".join(t.split()).strip(" .")
    if len(t) > longueur:
        t = t[:longueur].rsplit(" ", 1)[0]
    return t or "Document"


def chemin_libre(titre: str, ext: str, date: Optional[str] = None) -> pathlib.Path:
    dossier = dossier_atlas()
    dossier.mkdir(parents=True, exist_ok=True)
    base = f"{titre_court(titre)} - {date or time.strftime('%Y-%m-%d')}"
    chemin = dossier / f"{base}{ext}"
    n = 2
    while chemin.exists():
        chemin = dossier / f"{base} ({n}){ext}"
        n += 1
    return chemin


# --------------------------------------------------------------------------- #
#  Rien d'inventé : chiffres, dates, noms propres du résumé présents dans la source
# --------------------------------------------------------------------------- #

_MOIS = "janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|septembre|octobre|novembre|decembre|décembre"
_DATE = re.compile(rf"\b(?:1er|\d{{1,2}})\s+(?:{_MOIS})(?:\s+\d{{4}})?\b", re.IGNORECASE)
_NOMBRE = re.compile(r"(?<![\w])\d+(?:[ \u00a0\u202f]\d{3})*(?:[.,]\d+)?(?![\w])")
_PAS_DES_NOMS = {"mme", "mlle", "m", "mr", "dr", "pr", "le", "la", "les", "un", "une", "il", "elle", "ils", "elles",
                 "ce", "cette", "ces", "en", "au", "aux", "du", "de", "des", "et", "or", "mais", "puis", "ainsi",
                 "enfin", "ensuite", "lors", "selon", "pour", "par", "sur", "dans", "avec", "sans", "chez", "on",
                 "nous", "vous", "je", "tu", "son", "sa", "ses", "leur", "leurs", "notre", "votre", "points", "point"}


def _plat(texte: str) -> str:
    t = unicodedata.normalize("NFD", (texte or "").lower())
    return " ".join("".join(c for c in t if unicodedata.category(c) != "Mn").split())


def _nombre_norm(n: str) -> str:
    n = re.sub(r"[ \u00a0\u202f]", "", n).replace(",", ".")
    return n[:-2] if n.endswith(".0") else n


def _noms_propres(texte: str) -> list[str]:
    """Mots à majuscule qui ne commencent pas une phrase (« Airbus », « Toulouse », « Durand »)."""
    out = []
    for phrase in re.split(r"(?<=[.!?;:])\s+|\n+", texte):
        mots = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ][\w'’-]*", phrase)
        for k, m in enumerate(mots):
            if k == 0:
                continue                   # début de phrase : majuscule de grammaire
            if m[0].isupper() and m.lower().strip("'’") not in _PAS_DES_NOMS and len(m) > 1:
                out.append(m.strip("'’"))
    return out


def faits_absents(resume: str, source: str) -> list[str]:
    """Les faits du résumé (dates, nombres, noms propres) qui ne sont PAS dans la source."""
    src = _plat(source)
    nombres_src = {_nombre_norm(n) for n in _NOMBRE.findall(source)}
    absents = []
    reste = resume
    for d in _DATE.findall(resume):
        if _plat(d) not in src:
            absents.append(d)
        reste = reste.replace(d, " ")
    for n in _NOMBRE.findall(reste):
        if _nombre_norm(n) not in nombres_src:
            absents.append(n.strip())
    mots_src = set(re.findall(r"[\w'’-]+", src))
    for nom in _noms_propres(reste):
        if _plat(nom) not in mots_src and _plat(nom) not in src:
            absents.append(nom)
    return list(dict.fromkeys(absents))


def _phrases(texte: str) -> list[str]:
    return [p for p in re.split(r"(?<=[.!?])\s+", texte.strip()) if p]


def retirer_faits_inventes(contenu: dict, source: str) -> tuple[dict, list[dict]]:
    """Retire du résumé chaque PHRASE qui cite un fait absent de la source. Retourne le contenu
    nettoyé et la liste des phrases retirées (dites à Alexis). Un paragraphe vidé disparaît ;
    un point inventé aussi. Le titre inventé devient « Résumé », un titre de partie inventé « Partie N »."""
    propre = copy.deepcopy(contenu)
    retirees = []
    if faits_absents(propre.get("titre", ""), source):
        propre["titre"] = "Résumé"
    for i, s in enumerate(propre.get("sections", []), 1):
        f = faits_absents(s.get("titre", ""), source)
        if f:
            # Compétences 2 / CM0 (risque 10 du rapport Artefacts sur mesure) : un titre de partie inventé
            # aussi est retiré, et dit
            retirees.append({"phrase": s["titre"], "faits": f})
            s["titre"] = f"Partie {i}"
        paras = []
        for p in s.get("paragraphes", []):
            gardees = []
            for ph in _phrases(p):
                f = faits_absents(ph, source)
                if f:
                    retirees.append({"phrase": ph, "faits": f})
                else:
                    gardees.append(ph)
            if gardees:
                paras.append(" ".join(gardees))
        s["paragraphes"] = paras
        pts = []
        for pt in s.get("points") or []:
            f = faits_absents(pt, source)
            if f:
                retirees.append({"phrase": pt, "faits": f})
            else:
                pts.append(pt)
        if "points" in s:
            s["points"] = pts
    propre["sections"] = [s for s in propre.get("sections", []) if s.get("paragraphes") or s.get("points")]
    pc = []
    for pt in propre.get("points_cles") or []:
        f = faits_absents(pt, source)
        if f:
            retirees.append({"phrase": pt, "faits": f})
        else:
            pc.append(pt)
    if "points_cles" in propre:
        propre["points_cles"] = pc
    return propre, retirees
