"""
Sprint Compétences 2 / CM1 — la fenêtre de connexion d'Atlas (Gmail, Google Agenda).

Lancée par Atlas (« connecte mon Gmail ») dans un processus à part :
    python -m desktop.fenetre_connexion gmail | agenda_google

- elle explique en clair comment créer un mot de passe d'application (ou trouver l'adresse iCal privée), avec
  un bouton vers la page du fournisseur ;
- l'adresse et le secret se saisissent ICI, dans un champ masqué — jamais dans la conversation ni à la voix ;
- la connexion est vérifiée (IMAP, ou lecture de l'agenda) ; seul un succès est enregistré, dans le
  Gestionnaire d'identification de Windows ;
- la sortie (une ligne JSON lue par Atlas) dit l'issue et l'adresse du compte, JAMAIS le secret.
"""

from __future__ import annotations

import json
import pathlib
import sys
import threading

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TEXTES = {
    "gmail": {
        "titre": "Connecter ton Gmail à Atlas",
        "etapes": (
            "C'est facultatif : Atlas marche entièrement sans. Connecté, il lit tes mails seulement quand tu le "
            "demandes, les traite sur ce PC, et ne fait rien partir sans ta confirmation.\n\n"
            "1. La validation en deux étapes doit être activée sur ton compte Google.\n"
            "2. Ouvre la page « Mots de passe des applications » de Google (bouton ci-dessous).\n"
            "3. Crée un mot de passe nommé « Atlas » : Google affiche 16 lettres.\n"
            "4. Colle-les ci-dessous, avec ton adresse Gmail.\n\n"
            "« Déconnecte mon Gmail » supprime ce mot de passe de ce PC. Tu peux aussi le révoquer à tout moment "
            "sur la même page de Google."),
        "bouton": "Ouvrir la page de Google",
        "champ_id": "Adresse Gmail",
        "champ_secret": "Mot de passe d'application (16 lettres)",
    },
    "agenda_google": {
        "titre": "Connecter ton agenda Google à Atlas",
        "etapes": (
            "C'est facultatif. Atlas lit ton agenda seulement quand tu le demandes, sur ce PC. Pour créer un "
            "rendez-vous, il ouvre Google Agenda pré-rempli : c'est toi qui enregistres.\n\n"
            "1. Sur un ordinateur, ouvre Google Agenda, puis Paramètres (bouton ci-dessous).\n"
            "2. À gauche, sous « Paramètres de mes agendas », clique sur ton agenda.\n"
            "3. Section « Intégrer l'agenda » : copie l'« Adresse secrète au format iCal ».\n"
            "4. Colle-la ci-dessous.\n\n"
            "Cette adresse est un secret : quiconque la connaît lit ton agenda. Si elle fuit, Google permet de la "
            "réinitialiser. « Déconnecte mon agenda Google » la supprime de ce PC."),
        "bouton": "Ouvrir les paramètres de Google Agenda",
        "champ_id": None,
        "champ_secret": "Adresse secrète au format iCal",
    },
}


def connecter_service(service: str, identifiant: str, secret: str) -> dict:
    """Vérifie, puis enregistre seulement en cas de succès. {"etat": connecte|refuse|injoignable, ...}."""
    from core import coffre
    from core.courrier import SERVICES, adresse_valide

    if service == "agenda_google":
        from core import agenda

        adresse = (secret or "").strip()
        if not adresse.startswith("https://calendar.google.com/calendar/ical/") or not adresse.endswith(".ics"):
            return {"etat": "refuse", "detail": "Ce n'est pas une adresse iCal privée de Google Agenda (elle commence "
                    "par https://calendar.google.com/calendar/ical/ et finit par .ics)."}
        try:
            agenda.telecharger(adresse)
        except agenda.AdresseRefusee as e:
            return {"etat": "refuse", "detail": f"Google refuse cette adresse ({e})."}
        except agenda.Injoignable:
            return {"etat": "injoignable"}
        coffre.enregistrer(service, "Google Agenda", adresse)
        return {"etat": "connecte", "adresse": "Google Agenda"}
    identifiant = (identifiant or "").strip().lower()
    secret = (secret or "").replace(" ", "").strip()
    if not adresse_valide(identifiant):
        return {"etat": "refuse", "detail": "Cette adresse n'est pas valide."}
    if not secret:
        return {"etat": "refuse", "detail": "Le mot de passe d'application est vide."}
    from core import courrier
    from tools.courrier_imap import Injoignable, RefusConnexion

    boite = courrier.fabrique_boite(service, identifiant, lambda: secret)
    try:
        boite.verifier()
    except RefusConnexion:
        return {"etat": "refuse", "detail": f"{SERVICES[service]['nom']} refuse cette adresse ou ce mot de passe "
                "d'application (vérifie les 16 lettres, et que la validation en deux étapes est activée)."}
    except Injoignable:
        return {"etat": "injoignable"}
    coffre.enregistrer(service, identifiant, secret)
    return {"etat": "connecte", "adresse": identifiant}


def fenetre(service: str) -> dict:
    import tkinter as tk
    import webbrowser
    from tkinter import ttk

    from core.courrier import SERVICES

    t = TEXTES[service]
    issue = {"etat": "annule"}
    root = tk.Tk()
    root.title(f"Atlas — {t['titre']}")
    root.resizable(False, False)
    root.attributes("-topmost", True)
    root.after(1500, lambda: root.attributes("-topmost", False))
    cadre = ttk.Frame(root, padding=16)
    cadre.pack(fill="both")
    ttk.Label(cadre, text=t["titre"], font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(cadre, text=t["etapes"], wraplength=480, justify="left").pack(anchor="w", pady=(8, 8))
    ttk.Button(cadre, text=t["bouton"], command=lambda: webbrowser.open(SERVICES[service]["aide"], new=2)).pack(anchor="w")
    champ_id = None
    if t["champ_id"]:
        ttk.Label(cadre, text=t["champ_id"]).pack(anchor="w", pady=(12, 0))
        champ_id = ttk.Entry(cadre, width=48)
        champ_id.pack(anchor="w")
    ttk.Label(cadre, text=t["champ_secret"]).pack(anchor="w", pady=(8, 0))
    champ_secret = ttk.Entry(cadre, width=48, show="•")         # champ masqué
    champ_secret.pack(anchor="w")
    etat = ttk.Label(cadre, text="", wraplength=480, justify="left", foreground="#a33")
    etat.pack(anchor="w", pady=(8, 0))
    boutons = ttk.Frame(cadre)
    boutons.pack(anchor="w", pady=(10, 0))

    def essayer():
        ident = champ_id.get() if champ_id else ""
        secret = champ_secret.get()
        b_ok.state(["disabled"])
        etat.config(text="Vérification de la connexion…", foreground="#555")

        def travail():
            try:
                r = connecter_service(service, ident, secret)
            except Exception as e:
                r = {"etat": "refuse", "detail": f"Erreur ({type(e).__name__})."}
            root.after(0, lambda: fin(r))

        threading.Thread(target=travail, daemon=True).start()

    def fin(r):
        if r["etat"] == "connecte":
            issue.clear()
            issue.update(r)
            champ_secret.delete(0, "end")
            root.destroy()
            return
        b_ok.state(["!disabled"])
        etat.config(text=r.get("detail") or "Le fournisseur ne répond pas : réessaie dans un moment.", foreground="#a33")
        issue.clear()
        issue.update({"etat": r["etat"], "detail": r.get("detail", "")})

    def annuler():
        if issue.get("etat") not in ("refuse", "injoignable"):
            issue.clear()
            issue.update({"etat": "annule"})
        root.destroy()

    b_ok = ttk.Button(boutons, text="Se connecter", command=essayer)
    b_ok.pack(side="left")
    ttk.Button(boutons, text="Annuler", command=annuler).pack(side="left", padx=8)
    root.protocol("WM_DELETE_WINDOW", annuler)
    (champ_id or champ_secret).focus_force()
    root.mainloop()
    return issue


def main(argv: list[str]) -> int:
    service = argv[0] if argv else "gmail"
    if service not in TEXTES:
        print(json.dumps({"etat": "annule", "detail": "service inconnu"}))
        return 2
    r = fenetre(service)
    print(json.dumps({k: v for k, v in r.items() if k in ("etat", "adresse", "detail")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
