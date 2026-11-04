"""
Sprint Compétences 2 — l'adaptateur IMAP/SMTP (Gmail, puis iCloud), avec un mot de passe d'application.

Un adaptateur remplaçable derrière l'interface commune (`core/courrier.py`) : si Google retire un jour les
mots de passe d'application, seul ce fichier change.

- Lecture SANS EFFET : la boîte est ouverte en lecture seule (EXAMINE) et le contenu lu par BODY.PEEK —
  rien n'est marqué comme lu, rien n'est déplacé.
- Un mail est désigné par son identifiant IMAP (UIDVALIDITY + UID) ; si la boîte a été renumérotée
  (UIDVALIDITY changé), il n'est plus lu : on ne devine pas lequel c'est.
- Un brouillon est ajouté (APPEND) au dossier marqué \\Drafts : il se voit dans Gmail.
- Envoi : une seule tentative, étape par étape. Une erreur AVANT la transmission du message = rien n'est
  parti ; une coupure PENDANT ou après = résultat inconnu, et jamais de second envoi.
- Le secret est demandé au coffre au moment de la connexion (fonction `secret`), utilisé, puis oublié.
"""

from __future__ import annotations

import imaplib
import logging
import re
import smtplib
import socket
import ssl
import time
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from email.utils import getaddresses, parsedate_to_datetime
from typing import Callable, Optional

from core.contenu_externe import sans_invisibles

logger = logging.getLogger("atlas.courrier.imap")

DELAI_S = 20.0

FOURNISSEURS = {
    "gmail": {"nom": "Gmail", "imap": ("imap.gmail.com", 993, True), "smtp": ("smtp.gmail.com", 465, "ssl")},
    "icloud": {"nom": "iCloud", "imap": ("imap.mail.me.com", 993, True), "smtp": ("smtp.mail.me.com", 587, "starttls")},
}


class RefusConnexion(Exception):
    """Le fournisseur refuse l'adresse ou le mot de passe d'application."""


class Injoignable(Exception):
    """Le fournisseur ne répond pas (réseau, délai)."""


class MailIntrouvable(Exception):
    """Le mail désigné n'existe plus à cet identifiant."""


@dataclass(frozen=True)
class RefMail:
    fournisseur: str
    dossier: str
    uidvalidity: str
    uid: str


@dataclass
class Entete:
    ref: RefMail
    expediteur_nom: str
    expediteur_adresse: str
    objet: str
    date: Optional[datetime]
    lu: bool
    message_id: str = ""


@dataclass
class ResultatEnvoi:
    etat: str            # "accepte" | "echec" | "inconnu"
    detail: str = ""
    refuses: tuple = ()


def _q(nom: str) -> str:
    return '"' + nom.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _mois_imap(d: date) -> str:
    return f"{d.day:02d}-{['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][d.month - 1]}-{d.year}"


class BoiteImap:
    def __init__(self, fournisseur: str, adresse: str, secret: Callable[[], str], conf: Optional[dict] = None):
        self.fournisseur = fournisseur
        self.adresse = adresse
        self._secret = secret
        self.conf = conf or FOURNISSEURS[fournisseur]

    # ------------------------------------------------------------------ connexion

    def _imap(self) -> imaplib.IMAP4:
        hote, port, tls = self.conf["imap"]
        try:
            c = (imaplib.IMAP4_SSL(hote, port, ssl_context=ssl.create_default_context(), timeout=DELAI_S) if tls
                 else imaplib.IMAP4(hote, port, timeout=DELAI_S))
        except (OSError, imaplib.IMAP4.error) as e:
            raise Injoignable(f"{self.conf['nom']} ne répond pas ({type(e).__name__})") from None
        try:
            c.login(self.adresse, self._secret())
        except imaplib.IMAP4.error as e:
            try:
                c.logout()
            except Exception:
                pass
            texte = str(e)
            if re.search(r"AUTHENTICATIONFAILED|Invalid credentials|LOGIN failed|authentication failed|"
                         r"Application-specific password required|Web login required", texte, re.IGNORECASE):
                raise RefusConnexion(f"{self.conf['nom']} refuse l'adresse ou le mot de passe d'application") from None
            raise Injoignable(f"{self.conf['nom']} a répondu de façon inattendue à la connexion") from None
        except OSError as e:
            raise Injoignable(f"{self.conf['nom']} ne répond pas ({type(e).__name__})") from None
        return c

    def verifier(self) -> None:
        c = self._imap()
        try:
            c.logout()
        except Exception:
            pass

    @staticmethod
    def _fermer(c) -> None:
        try:
            c.logout()
        except Exception:
            pass

    def _examiner(self, c, dossier: str = "INBOX") -> str:
        typ, _ = c.select(_q(dossier), readonly=True)          # EXAMINE : lecture seule
        if typ != "OK":
            raise Injoignable(f"la boîte « {dossier} » ne s'ouvre pas")
        r = c.untagged_responses.get("UIDVALIDITY") or [b""]
        return (r[-1] or b"").decode() if isinstance(r[-1], bytes) else str(r[-1])

    # ------------------------------------------------------------------ lecture

    def lister(self, *, non_lus: bool = False, depuis: Optional[date] = None, qui: Optional[str] = None,
               limite: int = 10, fenetre: int = 200) -> tuple[list[Entete], int]:
        """Les `limite` derniers mails de la boîte de réception qui correspondent, et leur nombre total.
        `qui` cherche dans le nom et l'adresse de l'expéditeur, et dans l'objet (sans accents ni casse)."""
        c = self._imap()
        try:
            uidvalidity = self._examiner(c)
            criteres = []
            if non_lus:
                criteres.append("UNSEEN")
            if depuis:
                criteres += ["SINCE", _mois_imap(depuis)]
            typ, data = c.uid("SEARCH", *(criteres or ["ALL"]))
            if typ != "OK":
                raise Injoignable("la recherche dans la boîte a échoué")
            uids = (data[0] or b"").split()
            total = len(uids)
            uids = uids[-(fenetre if qui else limite):]
            entetes = self._entetes(c, uids, uidvalidity)
        finally:
            self._fermer(c)
        if depuis:
            entetes = [e for e in entetes if not e.date or e.date.date() >= depuis]
        if qui:
            from core.horloge import plat

            cle = plat(qui.lower())
            entetes = [e for e in entetes if cle in plat(f"{e.expediteur_nom} {e.expediteur_adresse} {e.objet}".lower())]
            total = len(entetes)
        entetes.sort(key=lambda e: (e.date or datetime.min).timestamp() if e.date else 0, reverse=True)
        return entetes[:limite], total

    def _entetes(self, c, uids: list[bytes], uidvalidity: str) -> list[Entete]:
        if not uids:
            return []
        typ, data = c.uid("FETCH", b",".join(uids).decode(),
                          "(UID FLAGS BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])")
        if typ != "OK":
            raise Injoignable("la lecture des en-têtes a échoué")
        from email import policy
        from email.parser import BytesHeaderParser

        sortie = []
        for item in data:
            if not isinstance(item, tuple):
                continue
            meta, brut = item[0].decode(errors="replace"), item[1]
            uid = re.search(r"UID (\d+)", meta)
            flags = re.search(r"FLAGS \(([^)]*)\)", meta)
            if not uid:
                continue
            h = BytesHeaderParser(policy=policy.default).parsebytes(brut)
            (nom, adr), = getaddresses([str(h.get("From") or "")])[:1] or [("", "")]
            try:
                quand = parsedate_to_datetime(str(h.get("Date"))) if h.get("Date") else None
                if quand and quand.tzinfo is None:
                    quand = quand.astimezone()
            except Exception:
                quand = None
            sortie.append(Entete(ref=RefMail(self.fournisseur, "INBOX", uidvalidity, uid.group(1)),
                                 expediteur_nom=sans_invisibles(nom)[0].strip(), expediteur_adresse=adr.strip().lower(),
                                 objet=sans_invisibles(str(h.get("Subject") or "").replace("\n", " "))[0].strip(),
                                 date=quand, lu="\\Seen" in (flags.group(1) if flags else ""),
                                 message_id=str(h.get("Message-ID") or "").strip()))
        return sortie

    def lire(self, ref: RefMail) -> bytes:
        """Le mail brut, désigné par son identifiant — sans le marquer comme lu."""
        c = self._imap()
        try:
            uidvalidity = self._examiner(c, ref.dossier)
            if uidvalidity != ref.uidvalidity:
                raise MailIntrouvable("la boîte a été renumérotée depuis la liste : redemande la liste")
            typ, data = c.uid("FETCH", ref.uid, "(BODY.PEEK[])")
            brut = next((x[1] for x in (data or []) if isinstance(x, tuple)), None)
            if typ != "OK" or brut is None:
                raise MailIntrouvable("ce mail n'est plus dans la boîte de réception")
            return brut
        finally:
            self._fermer(c)

    # ------------------------------------------------------------------ brouillons et envoi

    def _dossier(self, c, marque: str, noms: tuple[str, ...]) -> str:
        typ, data = c.list('""', '"*"')
        trouves = []
        for ligne in data or []:
            if not isinstance(ligne, bytes):
                continue
            m = re.match(rb'\((?P<f>[^)]*)\) (?:"[^"]*"|NIL) (?P<n>"(?:[^"\\]|\\.)*"|\S+)', ligne)
            if not m:
                continue
            nom = m.group("n").decode()
            nom = nom[1:-1].replace('\\"', '"').replace("\\\\", "\\") if nom.startswith('"') else nom
            if marque.encode() in m.group("f"):
                return nom
            trouves.append(nom)
        for n in noms:
            if n in trouves:
                return n
        raise Injoignable(f"je ne trouve pas le dossier {marque} du compte")

    def creer_brouillon(self, msg: EmailMessage) -> str:
        c = self._imap()
        try:
            dossier = self._dossier(c, "\\Drafts", ("[Gmail]/Drafts", "[Gmail]/Brouillons", "Drafts", "Brouillons"))
            typ, _ = c.append(_q(dossier), "(\\Draft \\Seen)", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
            if typ != "OK":
                raise Injoignable("le fournisseur n'a pas enregistré le brouillon")
            return dossier
        finally:
            self._fermer(c)

    def envoyer(self, msg: EmailMessage, destinataires: list[str]) -> ResultatEnvoi:
        """UNE tentative. Jamais de nouvel essai ici ni ailleurs : un doute vaut « inconnu »."""
        hote, port, mode = self.conf["smtp"]
        etape = "connexion"
        s = None
        try:
            if mode == "ssl":
                s = smtplib.SMTP_SSL(hote, port, timeout=DELAI_S, context=ssl.create_default_context())
            else:
                s = smtplib.SMTP(hote, port, timeout=DELAI_S)
                if mode == "starttls":
                    s.starttls(context=ssl.create_default_context())
            s.ehlo()
            etape = "authentification"
            s.login(self.adresse, self._secret())
            etape = "expediteur"
            code, rep = s.mail(self.adresse)
            if code != 250:
                return ResultatEnvoi("echec", f"le fournisseur refuse l'expéditeur ({code})")
            etape = "destinataires"
            refuses = []
            for d in destinataires:
                code, rep = s.rcpt(d)
                if code not in (250, 251):
                    refuses.append(d)
            if refuses:
                try:
                    s.rset()
                except Exception:
                    pass
                return ResultatEnvoi("echec", "le fournisseur refuse " + ", ".join(refuses) + " : rien n'est parti",
                                     tuple(refuses))
            etape = "transmission"                # à partir d'ici, une coupure laisse un doute
            code, rep = s.data(msg.as_bytes())
            if code == 250:
                return ResultatEnvoi("accepte", rep.decode(errors="replace")[:120] if isinstance(rep, bytes) else "")
            return ResultatEnvoi("echec", f"le fournisseur a refusé le message ({code})")
        except smtplib.SMTPAuthenticationError:
            return ResultatEnvoi("echec", f"{self.conf['nom']} refuse le mot de passe d'application : rien n'est parti")
        except smtplib.SMTPResponseException as e:
            # le serveur a RÉPONDU par un refus (code) : le message n'est pas accepté
            return ResultatEnvoi("echec", f"le fournisseur a refusé le message ({e.smtp_code})")
        except (smtplib.SMTPException, OSError, socket.timeout) as e:
            if etape == "transmission":
                return ResultatEnvoi("inconnu", f"la connexion s'est coupée pendant la transmission ({type(e).__name__})")
            return ResultatEnvoi("echec", f"{self.conf['nom']} ne répond pas à l'étape « {etape} » "
                                          f"({type(e).__name__}) : rien n'est parti")
        finally:
            if s is not None:
                try:
                    s.quit()
                except Exception:
                    pass
