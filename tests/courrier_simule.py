"""
Sprint Compétences 2 — un serveur IMAP et un serveur SMTP SIMULÉS, sur 127.0.0.1, pour les tests.

Jamais un vrai compte : les tests branchent l'adaptateur `tools/courrier_imap.py` sur ces serveurs (sans TLS).
Ce sont de vrais serveurs réseau : `imaplib` et `smtplib` tournent pour de bon, et l'état des mails est suivi
(le drapeau \\Seen change si un client lit par BODY[] au lieu de BODY.PEEK[]). Seul le sous-ensemble du
protocole dont Atlas se sert est pris en charge ; le reste répond BAD.
"""

from __future__ import annotations

import base64
import email
import re
import socketserver
import threading
import time
from email import policy
from email.utils import parsedate_to_datetime

_MOIS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _jetons(ligne: str) -> list[str]:
    sortie, i = [], 0
    while i < len(ligne):
        c = ligne[i]
        if c == " ":
            i += 1
        elif c == '"':
            j, buf = i + 1, []
            while j < len(ligne) and ligne[j] != '"':
                if ligne[j] == "\\" and j + 1 < len(ligne):
                    j += 1
                buf.append(ligne[j])
                j += 1
            sortie.append("".join(buf))
            i = j + 1
        elif c == "(":
            prof, j = 0, i
            while j < len(ligne):
                prof += {"(": 1, ")": -1}.get(ligne[j], 0)
                if prof == 0:
                    break
                j += 1
            sortie.append(ligne[i:j + 1])
            i = j + 1
        else:
            j = i
            while j < len(ligne) and ligne[j] != " ":
                if ligne[j] == "[":
                    j = ligne.index("]", j)
                j += 1
            sortie.append(ligne[i:j])
            i = j
    return sortie


class Boite:
    def __init__(self):
        self.utilisateur, self.mot_de_passe = "atlastestia@gmail.com", "abcdefghijklmnop"
        self.dossiers = {"INBOX": {"uidvalidity": 7, "suivant": 1, "mails": []},
                         "[Gmail]/Drafts": {"uidvalidity": 9, "suivant": 1, "mails": [], "marque": "\\Drafts"},
                         "[Gmail]/Sent Mail": {"uidvalidity": 11, "suivant": 1, "mails": [], "marque": "\\Sent"}}
        self.commandes: list[str] = []
        self.verrou = threading.Lock()

    def deposer(self, brut: bytes, dossier: str = "INBOX", lu: bool = False, quand: float | None = None) -> int:
        with self.verrou:
            d = self.dossiers[dossier]
            uid = d["suivant"]
            d["suivant"] += 1
            if quand is None:
                try:
                    quand = parsedate_to_datetime(email.message_from_bytes(brut, policy=policy.default)["Date"]).timestamp()
                except Exception:
                    quand = time.time()
            d["mails"].append({"uid": uid, "flags": {"\\Seen"} if lu else set(), "brut": brut, "quand": quand})
            return uid

    def drapeaux(self, dossier: str = "INBOX") -> dict[int, set]:
        return {m["uid"]: set(m["flags"]) for m in self.dossiers[dossier]["mails"]}


class _ImapHandler(socketserver.StreamRequestHandler):
    def ecrire(self, texte):
        self.wfile.write(texte if isinstance(texte, bytes) else texte.encode("utf-8"))

    def handle(self):
        b: Boite = self.server.boite
        self.ecrire("* OK Serveur IMAP simulé prêt\r\n")
        connecte, dossier, lecture_seule = False, None, True
        while True:
            ligne = self.rfile.readline()
            if not ligne:
                return
            ligne = ligne.decode("utf-8", errors="replace").rstrip("\r\n")
            m = re.match(r"(\S+) (\S+)(?: (.*))?$", ligne)
            if not m:
                continue
            tag, cmd, reste = m.group(1), m.group(2).upper(), m.group(3) or ""
            with b.verrou:
                b.commandes.append(f"{cmd} {reste}" if cmd != "LOGIN" else "LOGIN ***")
            if cmd == "CAPABILITY":
                self.ecrire(f"* CAPABILITY IMAP4rev1 SPECIAL-USE\r\n{tag} OK CAPABILITY fait\r\n")
            elif cmd == "NOOP":
                self.ecrire(f"{tag} OK\r\n")
            elif cmd == "LOGOUT":
                self.ecrire(f"* BYE\r\n{tag} OK LOGOUT\r\n")
                return
            elif cmd == "LOGIN":
                j = _jetons(reste)
                if len(j) == 2 and j[0] == b.utilisateur and j[1] == b.mot_de_passe:
                    connecte = True
                    self.ecrire(f"{tag} OK LOGIN fait\r\n")
                else:
                    self.ecrire(f"{tag} NO [AUTHENTICATIONFAILED] Invalid credentials (Failure)\r\n")
            elif not connecte:
                self.ecrire(f"{tag} BAD non connecté\r\n")
            elif cmd == "LIST":
                for nom, d in b.dossiers.items():
                    marque = (" " + d["marque"]) if d.get("marque") else ""
                    self.ecrire(f'* LIST (\\HasNoChildren{marque}) "/" "{nom}"\r\n')
                self.ecrire(f"{tag} OK LIST fait\r\n")
            elif cmd in ("SELECT", "EXAMINE"):
                nom = _jetons(reste)[0]
                if nom not in b.dossiers:
                    self.ecrire(f"{tag} NO dossier inconnu\r\n")
                    continue
                dossier, lecture_seule = nom, cmd == "EXAMINE"
                d = b.dossiers[nom]
                self.ecrire(f"* {len(d['mails'])} EXISTS\r\n* OK [UIDVALIDITY {d['uidvalidity']}] UIDs\r\n"
                            f"{tag} OK [{'READ-ONLY' if lecture_seule else 'READ-WRITE'}] {cmd} fait\r\n")
            elif cmd == "APPEND":
                j = _jetons(reste)
                n = int(re.search(r"\{(\d+)\}$", reste).group(1))
                self.ecrire("+ prêt\r\n")
                brut = self.rfile.read(n)
                self.rfile.readline()
                nom = j[0]
                if nom not in b.dossiers:
                    self.ecrire(f"{tag} NO dossier inconnu\r\n")
                    continue
                uid = b.deposer(brut, nom, lu="\\Seen" in reste)
                with b.verrou:
                    b.dossiers[nom]["mails"][-1]["flags"] |= {f for f in ("\\Draft", "\\Seen") if f in reste}
                self.ecrire(f"{tag} OK [APPENDUID {b.dossiers[nom]['uidvalidity']} {uid}] APPEND fait\r\n")
            elif cmd == "UID" and dossier:
                self._uid(tag, reste, b, dossier, lecture_seule)
            else:
                self.ecrire(f"{tag} BAD commande non prise en charge\r\n")

    def _uid(self, tag, reste, b, dossier, lecture_seule):
        sous, _, args = reste.partition(" ")
        sous = sous.upper()
        d = b.dossiers[dossier]
        if sous == "SEARCH":
            j = _jetons(args)
            mails = list(d["mails"])
            k = 0
            while k < len(j):
                c = j[k].upper()
                if c == "UNSEEN":
                    mails = [m for m in mails if "\\Seen" not in m["flags"]]
                elif c == "SEEN":
                    mails = [m for m in mails if "\\Seen" in m["flags"]]
                elif c == "SINCE":
                    jj, mm, aa = j[k + 1].split("-")
                    seuil = time.mktime((int(aa), _MOIS.index(mm) + 1, int(jj), 0, 0, 0, 0, 0, -1))
                    mails = [m for m in mails if m["quand"] >= seuil]
                    k += 1
                elif c == "FROM":
                    cle = j[k + 1].lower()
                    mails = [m for m in mails if cle in str(email.message_from_bytes(m["brut"])["From"]).lower()]
                    k += 1
                k += 1
            self.ecrire(f"* SEARCH {' '.join(str(m['uid']) for m in mails)}\r\n{tag} OK SEARCH fait\r\n")
        elif sous == "FETCH":
            ensemble, _, quoi = args.partition(" ")
            voulus = set()
            for morceau in ensemble.split(","):
                if ":" in morceau:
                    a, z = morceau.split(":")
                    voulus |= set(range(int(a), (int(z) if z != "*" else 10 ** 9) + 1))
                else:
                    voulus.add(int(morceau))
            q = quoi.upper()
            for seq, m in enumerate(d["mails"], 1):
                if m["uid"] not in voulus:
                    continue
                if "BODY[]" in q.replace("BODY.PEEK[]", "") and not lecture_seule:
                    m["flags"].add("\\Seen")          # BODY[] (sans PEEK) marque comme lu, comme un vrai serveur
                elif "BODY[]" in q.replace("BODY.PEEK[]", "") and lecture_seule:
                    pass                              # en EXAMINE, un vrai serveur ne change pas non plus le drapeau
                morceaux = [f"UID {m['uid']}"]
                if "FLAGS" in q:
                    morceaux.append(f"FLAGS ({' '.join(sorted(m['flags']))})")
                corps = None
                mh = re.search(r"BODY(?:\.PEEK)?\[HEADER\.FIELDS \(([^)]*)\)\]", q)
                if mh:
                    msg = email.message_from_bytes(m["brut"], policy=policy.compat32)
                    champs = mh.group(1).split()
                    corps = b"".join(f"{k}: {msg[k]}\r\n".encode("utf-8", errors="replace")
                                     for k in msg.keys() if k.upper() in champs) + b"\r\n"
                    morceaux.append(f"BODY[HEADER.FIELDS ({mh.group(1)})] {{{len(corps)}}}")
                elif "BODY.PEEK[]" in q or "BODY[]" in q:
                    corps = m["brut"]
                    morceaux.append(f"BODY[] {{{len(corps)}}}")
                tete = f"* {seq} FETCH (" + " ".join(morceaux)
                if corps is None:
                    self.ecrire(tete + ")\r\n")
                else:
                    self.ecrire(tete.encode("utf-8") + b"\r\n" + corps + b")\r\n")
            self.ecrire(f"{tag} OK FETCH fait\r\n")
        else:
            self.ecrire(f"{tag} BAD UID {sous} non pris en charge\r\n")


class _SmtpHandler(socketserver.StreamRequestHandler):
    def handle(self):
        s = self.server
        self.wfile.write(b"220 smtp simule\r\n")
        expediteur, destinataires, authentifie = None, [], False
        while True:
            ligne = self.rfile.readline()
            if not ligne:
                return
            l = ligne.decode("utf-8", errors="replace").rstrip("\r\n")
            cmd = l.split(" ", 1)[0].upper()
            if cmd in ("EHLO", "HELO"):
                self.wfile.write(b"250-simule\r\n250-AUTH PLAIN LOGIN\r\n250 8BITMIME\r\n")
            elif cmd == "AUTH":
                parts = l.split()
                if parts[1].upper() == "PLAIN":
                    jeton = parts[2] if len(parts) > 2 else None
                    if jeton is None:
                        self.wfile.write(b"334 \r\n")
                        jeton = self.rfile.readline().decode().strip()
                    _, u, p = base64.b64decode(jeton).decode().split("\0")
                else:
                    self.wfile.write(b"334 VXNlcm5hbWU6\r\n")
                    u = base64.b64decode(self.rfile.readline().strip()).decode()
                    self.wfile.write(b"334 UGFzc3dvcmQ6\r\n")
                    p = base64.b64decode(self.rfile.readline().strip()).decode()
                if (u, p) == (s.boite.utilisateur, s.boite.mot_de_passe):
                    authentifie = True
                    self.wfile.write(b"235 ok\r\n")
                else:
                    self.wfile.write(b"535 5.7.8 Username and Password not accepted\r\n")
            elif cmd == "MAIL":
                if not authentifie:
                    self.wfile.write(b"530 auth requise\r\n")
                    continue
                expediteur = l
                self.wfile.write(b"250 ok\r\n")
            elif cmd == "RCPT":
                adresse = re.search(r"<([^>]*)>", l).group(1)
                if s.mode == "refuse_destinataire":
                    self.wfile.write(b"550 5.1.1 adresse inconnue\r\n")
                else:
                    destinataires.append(adresse)
                    self.wfile.write(b"250 ok\r\n")
            elif cmd == "DATA":
                self.wfile.write(b"354 go\r\n")
                lignes = []
                while True:
                    x = self.rfile.readline()
                    if x in (b".\r\n", b".\n", b""):
                        break
                    lignes.append(x)
                s.tentatives += 1
                if s.mode == "coupe":
                    return                          # coupure après la transmission, sans réponse : doute
                if s.mode == "refuse_message":
                    self.wfile.write(b"554 5.7.1 message refuse\r\n")
                    continue
                s.recus.append({"de": expediteur, "a": list(destinataires), "brut": b"".join(lignes)})
                self.wfile.write(b"250 2.0.0 OK accepte\r\n")
            elif cmd == "RSET":
                destinataires = []
                self.wfile.write(b"250 ok\r\n")
            elif cmd == "QUIT":
                self.wfile.write(b"221 bye\r\n")
                return
            else:
                self.wfile.write(b"250 ok\r\n")


class _Serveur(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = True


class ServeursSimules:
    """Démarre un IMAP et un SMTP simulés ; `conf` se branche dans BoiteImap(conf=…)."""

    def __init__(self):
        self.boite = Boite()
        self.imap = _Serveur(("127.0.0.1", 0), _ImapHandler)
        self.imap.boite = self.boite
        self.smtp = _Serveur(("127.0.0.1", 0), _SmtpHandler)
        self.smtp.boite, self.smtp.mode, self.smtp.recus, self.smtp.tentatives = self.boite, "accepte", [], 0
        for srv in (self.imap, self.smtp):
            threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.conf = {"nom": "Gmail", "imap": ("127.0.0.1", self.imap.server_address[1], False),
                     "smtp": ("127.0.0.1", self.smtp.server_address[1], "clair")}

    def arreter(self):
        for srv in (self.imap, self.smtp):
            srv.shutdown()
            srv.server_close()


def mail(de: str, objet: str, texte: str = "", html: str | None = None, date: str = "Tue, 03 Nov 2026 09:12:00 +0100",
         a: str = "atlastestia@gmail.com", message_id: str | None = None, reply_to: str | None = None,
         pieces: list[tuple[str, bytes]] = ()) -> bytes:
    from email.message import EmailMessage

    m = EmailMessage()
    m["From"], m["To"], m["Subject"], m["Date"] = de, a, objet, date
    m["Message-ID"] = message_id or f"<{abs(hash((de, objet, date)))}@simule>"
    if reply_to:
        m["Reply-To"] = reply_to
    m.set_content(texte or "(texte)")
    if html is not None:
        m.add_alternative(html, subtype="html")
    for nom, contenu in pieces:
        m.add_attachment(contenu, maintype="application", subtype="octet-stream", filename=nom)
    return m.as_bytes()
