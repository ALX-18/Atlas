"""
Sprint Installeur / IN2.8 — le premier lancement guidé : ce qu'il faut savoir avant de parler à Atlas.

Une fenêtre, une seule fois (data/premier_lancement_vu) : « Hey Atlas » à l'anglaise, les confirmations à
l'écran, ce qu'Atlas sait faire et ce qu'il ne sait pas faire. Puis Atlas démarre (installeur/lancer.py).
Chaque phrase est vraie et rejouée (rapport du sprint Installeur, §6).
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
VU = ROOT / "data" / "premier_lancement_vu"

TITRE = "Bienvenue dans Atlas"
PARTIES = [
    ("Pour lui parler",
     "Dites « Hey Atlas », prononcé à l'anglaise (« Hé Atlasse »), puis votre demande. Le mot d'éveil n'est pas "
     "parfait : s'il ne réagit pas, redites-le. Vous pouvez aussi écrire dans la fenêtre d'Atlas, ce qui marche "
     "à tous les coups."),
    ("Les confirmations",
     "Avant une action importante (fermer une fenêtre, arrêter un programme, envoyer un mail, ajouter un "
     "rendez-vous…), Atlas affiche ce qu'il va faire et attend que vous cliquiez sur « Confirmer ». Sans votre "
     "clic, il ne fait rien."),
    ("Ce qu'il sait faire",
     "Ouvrir et ranger vos applications et fenêtres ; régler le son, la luminosité et la musique ; donner l'heure, "
     "mettre des minuteurs et des rappels ; retenir ce que vous lui dites ; rédiger un document en Word ou en PDF ; "
     "retrouver vos fichiers ; chercher sur internet. Si vous le connectez à Gmail : lire et résumer vos mails, "
     "préparer une réponse ; et lire votre agenda Google."),
    ("Ce qu'il ne sait pas encore faire",
     "Écrire un mail à quelqu'un de nouveau, transférer ou effacer des mails, se connecter à Outlook ou à iCloud, "
     "lire un mois entier d'agenda. Quand il ne sait pas, il le dit. Les envois de mails sont simulés tant que "
     "vous ne changez pas ce réglage : Atlas montre ce qui partirait, et n'envoie rien."),
    ("Ce qui reste chez vous",
     "Atlas comprend et répond sur cet ordinateur : votre voix et vos demandes ne partent vers aucune intelligence "
     "artificielle en ligne. Seules passent par internet les recherches que vous lui demandez et, si vous le "
     "connectez, votre Gmail et votre agenda Google."),
]


def fenetre() -> None:
    import tkinter as tk

    sys.path.insert(0, str(ROOT))
    from core import utilisateur

    r = tk.Tk()
    r.title(TITRE)
    r.geometry("620x690")
    tk.Label(r, text=TITRE, font=("Segoe UI", 16, "bold")).pack(pady=(16, 8))
    for titre, texte in PARTIES:
        tk.Label(r, text=titre, font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x", padx=28, pady=(8, 0))
        tk.Label(r, text=texte, font=("Segoe UI", 10), wraplength=560, justify="left", anchor="w").pack(fill="x", padx=28)
    # Sprint Installeur : le prénom de la personne (facultatif) — sinon Atlas ne donne aucun prénom
    tk.Label(r, text="Votre prénom (facultatif) : Atlas vous appellera ainsi.", font=("Segoe UI", 10, "bold"),
             anchor="w").pack(fill="x", padx=28, pady=(12, 2))
    champ = tk.Entry(r, font=("Segoe UI", 11), width=30)
    champ.insert(0, utilisateur.prenom() or "")
    champ.pack(anchor="w", padx=28)
    erreur = tk.StringVar(value="")
    tk.Label(r, textvariable=erreur, fg="#a00", font=("Segoe UI", 9)).pack(anchor="w", padx=28)

    def demarrer():
        texte = champ.get().strip()
        if texte and utilisateur.enregistrer(texte) is None:
            erreur.set("Un prénom seulement : des lettres, sans chiffres (40 caractères au plus).")
            return
        r.destroy()
    tk.Button(r, text="Démarrer Atlas", font=("Segoe UI", 11), width=18, command=demarrer).pack(pady=14)
    champ.focus_set()
    r.mainloop()


def main() -> int:
    if not VU.exists():
        fenetre()
        VU.parent.mkdir(parents=True, exist_ok=True)
        VU.write_text("vu\n", encoding="utf-8")
    subprocess.Popen([sys.executable, str(ROOT / "installeur" / "lancer.py")], cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
