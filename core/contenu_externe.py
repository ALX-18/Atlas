"""
Sprint Compétences 2 — un mail est une donnée NON FIABLE, jamais une instruction (Réunion n° 2, §9).

Ce module ne fait qu'analyser, sans réseau et sans modèle :
- le HTML est réduit à du texte : scripts, styles, images distantes et cadres retirés ; le texte CACHÉ
  (blanc sur blanc, taille 0, display:none…) est retiré et compté ; rien n'est chargé ni suivi ;
- les liens sont relevés (texte affiché, adresse réelle), numérotés, jamais ouverts ; un lien dont le texte
  affiche une autre adresse que la vraie, une adresse « javascript: », un domaine en caractères trompeurs
  (xn--, non ASCII) ou un « @ » piégé est marqué trompeur ;
- les caractères invisibles et les inversions de sens (U+202E…) sont retirés et signalés ;
- les SIGNAUX sont calculés par des règles (demande de secret, consignes adressées à un assistant, faux
  message « système », expéditeur affiché trompeur, pièces jointes) : ces alertes viennent du code, pas du
  modèle, et s'affichent même si le résumé du modèle les tait ;
- le contenu donné au modèle est encadré par des délimiteurs à jeton aléatoire, que le contenu ne peut pas
  imiter (toute occurrence est neutralisée).
"""

from __future__ import annotations

import re
import secrets as _aleatoire
import unicodedata
from dataclasses import dataclass, field
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from typing import Optional
from urllib.parse import urlsplit

MENTION = "Contenu externe"
TEXTE_MAX_MODELE = 6000

_INVISIBLES = re.compile("[­؜᠎​-‏‪-‮⁠-⁤⁦-⁩﻿]")
_URL = re.compile(r"\b(?:https?://|www\.)[^\s<>\"'«»]+", re.IGNORECASE)
_DOMAINE_AFFICHE = re.compile(r"^(?:https?://)?(?:www\.)?((?:[\w-]+\.)+[a-z]{2,})(?:[/:?#].*)?$", re.IGNORECASE)


@dataclass
class Lien:
    numero: int
    texte: str
    adresse: str
    trompeur: bool = False
    raison: str = ""


@dataclass
class Analyse:
    texte: str
    liens: list[Lien] = field(default_factory=list)
    cache: int = 0              # caractères de texte caché retirés
    texte_cache: str = ""       # ce texte caché : jamais donné au modèle, lu seulement par les règles des alertes
    invisibles: int = 0         # caractères invisibles ou d'inversion retirés
    images: int = 0             # images (jamais chargées)


def sans_invisibles(texte: str) -> tuple[str, int]:
    n = len(_INVISIBLES.findall(texte or ""))
    return _INVISIBLES.sub("", texte or ""), n


# --------------------------------------------------------------------------- #
#  Un secret tapé dans la conversation (il ne doit jamais y passer)
# --------------------------------------------------------------------------- #

_APP_PASSWORD = re.compile(r"(?<![\w-])(?:[a-z]{4}[ -][a-z]{4}[ -][a-z]{4}[ -][a-z]{4}|[a-z]{16}|"
                           r"[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4})(?![\w-])", re.IGNORECASE)
_ICAL_PRIVE = re.compile(r"calendar\.google\.com/calendar/ical/[^\s]+/private-[0-9a-f]{16,}", re.IGNORECASE)
_PARLE_SECRET = re.compile(r"mot\s+de\s+passe|mdp|password|code\s+d'application|app\s+password", re.IGNORECASE)
REFUS_SECRET = ("Ne me donne jamais un mot de passe ou une adresse secrète ici : la conversation n'est pas faite pour "
                "ça. Je ne l'ai ni gardé ni noté. Dis « connecte mon Gmail » (ou « connecte mon agenda Google ») : une "
                "fenêtre d'Atlas s'ouvre, avec un champ masqué. Par précaution, tu peux aussi révoquer ce mot de passe "
                "chez Google et en créer un autre.")


def ressemble_a_un_secret(message: str) -> bool:
    """Un mot de passe d'application (16 lettres, par groupes de 4) annoncé comme tel, ou une adresse iCal privée."""
    t = message or ""
    if _ICAL_PRIVE.search(t):
        return True
    if not _PARLE_SECRET.search(t):
        return False
    return any(len(set(m.group(0).lower().replace(" ", "").replace("-", ""))) >= 6 for m in _APP_PASSWORD.finditer(t))


# --------------------------------------------------------------------------- #
#  Liens
# --------------------------------------------------------------------------- #

def _hote(adresse: str) -> str:
    try:
        return (urlsplit(adresse if "://" in adresse else "http://" + adresse).hostname or "").lower()
    except ValueError:
        return ""


def _meme_domaine(a: str, b: str) -> bool:
    a, b = a.removeprefix("www."), b.removeprefix("www.")
    return a == b or a.endswith("." + b) or b.endswith("." + a)


def juger_lien(texte: str, adresse: str) -> tuple[bool, str]:
    """(trompeur ?, pourquoi) — règles seulement."""
    adresse = (adresse or "").strip()
    schema = adresse.split(":", 1)[0].lower() if ":" in adresse else ""
    if schema and schema not in ("http", "https", "mailto"):
        return True, f"adresse de type « {schema}: », qui n'est pas une page web"
    if schema == "mailto":
        return False, ""
    try:
        parts = urlsplit(adresse if "://" in adresse else "http://" + adresse)
    except ValueError:
        return True, "adresse illisible"
    hote = (parts.hostname or "").lower()
    if parts.username or "@" in parts.netloc:
        return True, f"l'adresse contient un « @ » : le vrai site est {hote or '?'}"
    if "xn--" in hote or any(ord(c) > 127 for c in hote):
        return True, "le nom du site contient des caractères trompeurs"
    if re.fullmatch(r"[\d.]+|\[[0-9a-f:]+\]", hote or "x"):
        return True, "le site est désigné par une adresse IP"
    m = _DOMAINE_AFFICHE.match((texte or "").strip())
    if m and hote and not _meme_domaine(m.group(1).lower(), hote):
        return True, f"le texte affiche « {m.group(1)} » mais le lien mène à {hote}"
    return False, ""


def _lien(numero: int, texte: str, adresse: str) -> Lien:
    trompeur, raison = juger_lien(texte, adresse)
    return Lien(numero, texte, adresse, trompeur, raison)


# --------------------------------------------------------------------------- #
#  HTML → texte
# --------------------------------------------------------------------------- #

_CACHE_STYLE = re.compile(
    r"display\s*:\s*none|visibility\s*:\s*hidden|opacity\s*:\s*0(?:\.0+)?\s*(?:;|$)|font-size\s*:\s*0(?:\.0+)?\s*"
    r"(?:px|pt|em|rem|%)?\s*(?:;|$)|(?:max-)?height\s*:\s*0(?:px)?\s*(?:;|$)|(?:max-)?width\s*:\s*0(?:px)?\s*(?:;|$)|"
    r"text-indent\s*:\s*-\d{3,}|(?:left|top)\s*:\s*-\d{3,}px|clip\s*:\s*rect\(\s*0", re.IGNORECASE)
_BLANC = re.compile(r"(?<![-\w])color\s*:\s*(?:#fff(?:fff)?\b|white\b|rgba?\(\s*255\s*,\s*255\s*,\s*255)", re.IGNORECASE)
_FOND_SOMBRE = re.compile(r"background(?:-color)?\s*:\s*(?:#(?:0|1|2|3)[0-9a-f]{2,5}\b|black\b|rgb\(\s*\d{1,2}\s*,)",
                          re.IGNORECASE)


def _est_cache(el) -> bool:
    if el.has_attr("hidden"):
        return True
    style = el.get("style") or ""
    if _CACHE_STYLE.search(style):
        return True
    couleur = (el.get("color") or "").lower()
    if el.name == "font" and (couleur in ("#fff", "#ffffff", "white") or (el.get("size") or "") in ("0", "-10")):
        return True
    if _BLANC.search(style):
        # blanc sur blanc : du texte blanc sans fond sombre, ni sur lui ni sur ses parents
        for x in [el, *el.parents]:
            if getattr(x, "get", None) and (_FOND_SOMBRE.search(x.get("style") or "")
                                            or (x.get("bgcolor") or "").lower() in ("#000", "#000000", "black")):
                return False
        return True
    return False


def html_en_texte(html: str) -> Analyse:
    from bs4 import BeautifulSoup, Comment

    soup = BeautifulSoup(html or "", "html.parser")
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    for t in soup.find_all(["script", "style", "head", "noscript", "template", "iframe", "frame", "object", "embed",
                            "svg", "link", "meta", "base", "audio", "video", "source"]):
        t.decompose()
    images = len(soup.find_all("img"))
    for t in soup.find_all("img"):
        t.decompose()
    cache, caches = 0, []
    for el in soup.find_all(True):
        if getattr(el, "decomposed", False):
            continue
        try:
            if _est_cache(el):
                t = el.get_text(" ", strip=True)
                cache += len(t)
                caches.append(t)
                el.decompose()
        except Exception:
            continue
    liens = []
    for a in soup.find_all("a"):
        adresse = (a.get("href") or "").strip()
        texte = a.get_text(" ", strip=True)
        if not adresse or adresse.startswith("#"):
            a.unwrap()
            continue
        l = _lien(len(liens) + 1, texte, adresse)
        liens.append(l)
        a.replace_with(f"{texte} [lien {l.numero}]" if texte else f"[lien {l.numero}]")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for bloc in soup.find_all(["p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "table"]):
        bloc.insert_before("\n")
        bloc.insert_after("\n")
    texte, invisibles = sans_invisibles(soup.get_text(""))
    texte = re.sub(r"[ \t ]+", " ", texte)
    texte = re.sub(r"\s*\n\s*", "\n", texte).strip()
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    return Analyse(texte=texte, liens=liens, cache=cache, texte_cache=sans_invisibles("\n".join(caches))[0],
                   invisibles=invisibles, images=images)


def texte_brut(texte: str) -> Analyse:
    texte, invisibles = sans_invisibles(texte or "")
    liens = []

    def remplacer(m):
        url = m.group(0).rstrip(".,;:!?)")
        l = _lien(len(liens) + 1, url, url if "://" in url else "http://" + url)
        liens.append(l)
        return f"{url} [lien {l.numero}]" + m.group(0)[len(url):]

    texte = _URL.sub(remplacer, texte)
    return Analyse(texte=re.sub(r"\n{3,}", "\n\n", texte.strip()), liens=liens, invisibles=invisibles)


# --------------------------------------------------------------------------- #
#  Le mail lu
# --------------------------------------------------------------------------- #

@dataclass
class MailLu:
    expediteur_nom: str
    expediteur_adresse: str
    objet: str
    date: Optional[object]
    message_id: str
    references: str
    reply_to: str
    a: list[str]
    cc: list[str]
    analyse: Analyse
    pieces_jointes: list[str]
    alertes: list[str]


def _adresses(valeur) -> list[tuple[str, str]]:
    return [(sans_invisibles(n)[0].strip(), a.strip().lower()) for n, a in getaddresses([str(valeur or "")]) if a]


def analyser_mail(brut: bytes) -> MailLu:
    msg: EmailMessage = BytesParser(policy=policy.default).parsebytes(brut)
    exp = (_adresses(msg.get("From")) or [("", "")])[0]
    objet, inv_objet = sans_invisibles(str(msg.get("Subject") or "").replace("\r", " ").replace("\n", " "))
    try:
        date = parsedate_to_datetime(str(msg.get("Date"))) if msg.get("Date") else None
    except Exception:
        date = None
    html, plain, pieces = None, None, []
    for part in msg.walk():
        if part.is_multipart():
            continue
        nom = part.get_filename()
        dispo = (part.get_content_disposition() or "").lower()
        ctype = part.get_content_type()
        if nom or dispo == "attachment" or not ctype.startswith("text/"):
            if nom or dispo == "attachment":
                pieces.append(sans_invisibles(nom or f"(sans nom, {ctype})"))
            continue
        try:
            contenu = part.get_content()
        except Exception:
            contenu = (part.get_payload(decode=True) or b"").decode("utf-8", errors="replace")
        if ctype == "text/html" and html is None:
            html = contenu
        elif ctype == "text/plain" and plain is None:
            plain = contenu
    analyse = html_en_texte(html) if html is not None else texte_brut(plain or "")
    analyse.invisibles += inv_objet
    noms_pj = [n for n, _ in pieces]
    if any(k for _, k in pieces):
        analyse.invisibles += sum(k for _, k in pieces)
    mail = MailLu(expediteur_nom=exp[0], expediteur_adresse=exp[1], objet=objet.strip(), date=date,
                  message_id=str(msg.get("Message-ID") or "").strip(), references=str(msg.get("References") or ""),
                  reply_to=", ".join(a for _, a in _adresses(msg.get("Reply-To"))),
                  a=[a for _, a in _adresses(msg.get("To"))], cc=[a for _, a in _adresses(msg.get("Cc"))],
                  analyse=analyse, pieces_jointes=noms_pj, alertes=[])
    mail.alertes = alertes(mail)
    return mail


# --------------------------------------------------------------------------- #
#  Les signaux (règles, jamais le modèle)
# --------------------------------------------------------------------------- #

_SECRET = re.compile(
    r"mots?\s+de\s+passe|password|passcode|identifiants?\s+(?:de\s+connexion|bancaires?)|code\s+(?:de\s+)?(?:v[ée]rification|"
    r"confirmation|s[ée]curit[ée]|validation|connexion|à\s+\d|re[çc]u|pin|secret)|code\s+pin|\bcvv\b|\bcvc\b|"
    r"num[ée]ro\s+de\s+(?:carte|compte)|carte\s+(?:bancaire|bleue|de\s+cr[ée]dit)|\biban\b|\bbic\b|"
    r"adresse\s+(?:secr[èe]te|priv[ée]e)\s+(?:au\s+format\s+)?ical|cl[ée]\s+(?:api|secr[èe]te)|\btoken\b|jeton|"
    r"seed\s+phrase|phrase\s+de\s+r[ée]cup[ée]ration|\b2fa\b|double\s+authentification",
    re.IGNORECASE)
# Une INTERPELLATION : en tête de ligne ou de phrase, après « : », « > » (citation), « bonjour »… — pas une simple
# mention (rejeu du 04/11 : « si vous n'avez pas généré ce mot de passe pour Atlas, quelqu'un… », un vrai mail de Google)
_A_L_ASSISTANT = re.compile(
    r"(?:^|[.!?:>«\"\]]\s*|\b(?:bonjour|salut|hey|h[ée]|cher|ch[èe]re|dear|hi|hello|ok|alors)\s+)"
    r"(?:atlas|assistant(?:e)?(?:\s+(?:ia|virtuel(?:le)?|personnel(?:le)?))?|ia|intelligence\s+artificielle|chatgpt|"
    r"claude|copilot|gemini|ai\s+assistant|language\s+model|llm|mod[èe]le\s+de\s+langue)\b\s*[,:;!-]",
    re.IGNORECASE | re.MULTILINE)
_ORDRE = re.compile(
    r"\bignore[rz]?\s+(?:tes|vos|les|toutes?\s+(?:tes|vos|les))\s+(?:r[èe]gles|instructions|consignes)|"
    r"\bignore\s+(?:all\s+|any\s+)?(?:previous|prior|above)\s+instructions|\bdisregard\b|"
    r"\b(?:system\s+prompt|consigne\s+syst[èe]me|instruction\s+syst[èe]me|developer\s+mode|mode\s+d[ée]veloppeur|jailbreak)|"
    r"\b(?:transf[èe]re[rz]?|forward|redirige[rz]?|r[ée]exp[ée]die[rz]?)\b[^.\n]{0,60}\b(?:mails?|messages?|courriels?|"
    r"e-mails?|emails?|bo[îi]te|contacts?)|"
    r"\b(?:envoie[rz]?|send)\b[^.\n]{0,40}\b(?:tous|toutes|all|ce\s+mail|ces\s+mails|mes|ses|tes|vos)\b|"
    r"\b(?:supprime[rz]?|efface[rz]?|delete)\b[^.\n]{0,40}\b(?:mails?|messages?|fichiers?|courriels?|emails?)|"
    r"<\s*/?\s*(?:system|assistant|tool|instructions?)\s*>|\[\s*(?:system|syst[èe]me|inst)\s*\]|"
    r"<<<|>>>|\bnouvelles?\s+(?:consignes?|instructions?|r[èe]gles)\b|\bnew\s+instructions?\b|"
    r"\b(?:appelle|appeler|utilise|utiliser|call|use)\s+l?'?(?:outil|tool|fonction|function)\b",
    re.IGNORECASE)
_FAUX_SYSTEME = re.compile(
    r"^\s*(?:\[|\*\*|#+\s*)?(?:message\s+syst[èe]me|system\s+message|syst[èe]me|system|admin(?:istrateur)?|"
    r"notification\s+atlas|atlas\s+(?:security|s[ée]curit[ée]|system|syst[èe]me|support)|mise\s+à\s+jour\s+de\s+s[ée]curit[ée])"
    r"\s*(?:\]|\*\*)?\s*[:\-—]", re.IGNORECASE | re.MULTILINE)
_ADRESSE_DANS_NOM = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def alertes(mail: MailLu) -> list[str]:
    a = mail.analyse
    texte = f"{mail.objet}\n{a.texte}\n{a.texte_cache}\n" + "\n".join(mail.pieces_jointes)
    sortie = []
    m = _ADRESSE_DANS_NOM.search(mail.expediteur_nom or "")
    if m and m.group(0).lower() != mail.expediteur_adresse:
        sortie.append(f"⚠ Expéditeur trompeur : le nom affiché contient « {m.group(0)} », mais le mail vient de "
                      f"{mail.expediteur_adresse}.")
    if mail.reply_to and mail.reply_to != mail.expediteur_adresse:
        sortie.append(f"⚠ Une réponse partirait vers {mail.reply_to}, pas vers l'expéditeur ({mail.expediteur_adresse}) : "
                      "je réponds à l'expéditeur.")
    if _SECRET.search(texte):
        sortie.append("⚠ Ce mail parle d'un mot de passe, d'un code ou de coordonnées : ne les donne pas sans vérifier "
                      "l'expéditeur par un autre moyen. Atlas ne donne jamais les siens.")
    if _A_L_ASSISTANT.search(texte) or _ORDRE.search(texte) or _FAUX_SYSTEME.search(texte):
        sortie.append("⚠ Ce mail contient des consignes adressées à un assistant ou se fait passer pour un message "
                      "système : je ne les suis pas, ce n'est pas toi qui parles.")
    trompeurs = [l for l in a.liens if l.trompeur]
    for l in trompeurs[:3]:
        sortie.append(f"⚠ Lien {l.numero} trompeur : {l.raison}.")
    if a.liens:
        sortie.append(f"Ce mail contient {len(a.liens)} lien{'s' if len(a.liens) > 1 else ''} : je ne les ouvre jamais "
                      "seul ; « ouvre le lien 1 du mail » me fait d'abord montrer l'adresse complète.")
    if a.cache:
        sortie.append(f"⚠ J'ai retiré {a.cache} caractères de texte caché (invisible dans Gmail, mais lisible par une machine).")
    if a.invisibles:
        sortie.append("⚠ J'ai retiré des caractères invisibles ou qui inversent le sens du texte.")
    if mail.pieces_jointes:
        sortie.append("Pièces jointes, jamais ouvertes par Atlas : " + ", ".join(f"« {n} »" for n in mail.pieces_jointes)
                      + ".")
    return sortie


# --------------------------------------------------------------------------- #
#  Ce que le modèle reçoit : des délimiteurs que le contenu ne peut pas imiter
# --------------------------------------------------------------------------- #

def bloc_delimite(mail: MailLu, texte_max: int = TEXTE_MAX_MODELE) -> tuple[str, str]:
    jeton = _aleatoire.token_hex(6)
    ouvre, ferme = f"<<<MAIL_NON_FIABLE_{jeton}>>>", f"<<<FIN_MAIL_NON_FIABLE_{jeton}>>>"

    def neutre(t: str) -> str:
        return re.sub(r"<<<|>>>", "«‹", unicodedata.normalize("NFKC", t or ""))

    corps = neutre(mail.analyse.texte)[:texte_max]
    bloc = (f"{ouvre}\nDe : {neutre(mail.expediteur_nom)} <{mail.expediteur_adresse}>\nObjet : {neutre(mail.objet)}\n\n"
            f"{corps}\n{ferme}")
    return bloc, jeton
