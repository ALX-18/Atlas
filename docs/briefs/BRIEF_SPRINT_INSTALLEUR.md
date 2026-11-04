# BRIEF SPRINT INSTALLEUR — Atlas chez un proche, en un double-clic

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 4 novembre 2026
**Durée visée :** deux à trois journées
**Références :** rapport Compétences 2 (§7, §9), brief `BRIEF_SPRINT_BASCULE_MODELE.md` (statut : reporté ; ses éléments utiles à `qwen2.5:7b` passent ici), Réunion Atlas n° 1 (paliers, épinglage, banc de non-régression, test de capacité réelle), `scripts/precheck_atlas.ps1`, `doctor.py`

---

## 1. Décisions

**Le rapport Compétences 2 est validé.** Les cinq ajouts hors brief sont acceptés, en particulier l'échappement HTML de l'interface web, qui corrige une vraie faille. iCloud est reporté, et Outlook aussi, par décision d'Alexis.

**Le choix local d'Alexis** (`mail.envoi` = `"reel"` sur son PC) est le sien. **L'installeur installe toujours en `"simulation"`.**

**Décisions d'Alexis (04/11) :**
- `precheck_atlas.bat` **n'a pas encore été lancé** sur le PC du proche de la démo. L'installeur doit donc choisir le modèle **selon ce qu'il trouve sur place**.
- **Démarrage avec Windows :** une case à cocher pendant l'installation, **décochée par défaut**.

**C'est le dernier sprint avant la démo.** Les finitions vues aux sprints précédents y entrent (IN7).

---

## 2. Principes

- **Une personne qui n'est pas informaticienne double-clique, et Atlas marche.** Chaque étape qui demande un geste explique pourquoi, en français simple.
- **L'installeur vérifie avant d'installer** : la machine (diagnostic), puis la **capacité réelle** une fois le modèle téléchargé (Réunion n° 1).
- **Ce qui est téléchargé vient de sources officielles, en HTTPS, et est vérifié** (empreinte ou signature quand l'éditeur en publie). Les dépendances Python sont installées avec leurs empreintes (`--require-hashes`), à des versions fixes.
- **Rien d'existant n'est écrasé.** Une réinstallation garde la mémoire, l'apprentissage, les rappels et l'index. La désinstallation **demande** si elle doit garder la mémoire.
- **Aucune donnée d'Alexis ne part dans l'installeur.** Ni mémoire, ni journal, ni configuration locale, ni secret. Un test le vérifie sur le paquet produit.
- **Le moins de droits possible.** Les droits administrateur ne sont demandés que pour ce qui l'exige vraiment, et c'est dit.

---

## 3. Tâches

### IN0 — Base

`sprint-competences-2` fusionnée dans `main`, suite verte.

### IN1 — Le choix technique

- **Recommandation du superviseur : Inno Setup**, avec un **Python embarqué** propre à Atlas (sans toucher à un Python déjà présent), et les dépendances installées pendant l'installation, depuis PyPI, avec leurs empreintes. **Pas de PyInstaller** (fragilité avec ctranslate2 et ONNX, fausses alertes des antivirus).
- Installeur **en ligne** : les modèles (7 à 9 Go) se téléchargent de toute façon. Annoncer la taille totale et le temps estimé avant de commencer.
- **Signature de code : pas pour la démo.** Le guide explique l'écran « Windows a protégé votre ordinateur » et le lien « Exécuter quand même ». La décision sur un certificat revient à Alexis, plus tard.
- Si CHAT6 voit une meilleure voie, la proposer, chiffres et raisons à l'appui, **avant** de la construire.

### IN2 — Les étapes de l'installation

1. **Diagnostic de la machine** (la logique de `precheck_atlas.ps1`) : Windows 10/11 64 bits, RAM, carte, VRAM, disque. Sur « ne convient pas », l'installation s'arrête proprement, avec la raison.
2. **Python embarqué et dépendances**, avec leurs empreintes.
3. **Ollama** par son installeur officiel, en mode silencieux (options exactes **à vérifier** dans sa documentation), puis vérification :
   - Ollama n'écoute que sur `127.0.0.1` ;
   - la version est relevée et comparée à la référence.
4. **Tesseract** (avec la langue française) par son installeur officiel, en mode silencieux si c'est possible (à vérifier).
5. **Les modèles** :
   - le modèle de langue, selon le palier (IN3), **épinglé par empreinte** ;
   - la transcription, la voix, le mot d'éveil, l'ONNX d'e5 (`download_voice_models.py`).
6. **Test de capacité réelle** : charger le modèle, générer une courte réponse, relever la part sur la carte et le temps. Si le résultat contredit le palier choisi, le dire et proposer le palier inférieur.
7. **Raccourcis** (Bureau, menu Démarrer), la case « démarrer avec Windows » (décochée), et l'entrée dans « Applications » de Windows pour la désinstallation.
8. **Premier lancement guidé** : « Dites "Hey Atlas" (prononcé à l'anglaise) », la confirmation à l'écran, ce qu'Atlas sait et ne sait pas faire.

### IN3 — Les paliers, pour `qwen2.5:7b`

- **8 Go ou plus : `qwen2.5:7b`** (le modèle de la démo).
- **6 Go, ou sans NVIDIA avec assez de RAM : `gemma4:e4b`**, annoncé **provisoire**. Le mesurer sur la machine pendant le test de capacité (IN2.6).
- **En dessous : « Cette machine ne convient pas à Atlas »**, avec la raison.
- Mettre `doctor.py --precheck` et `precheck_atlas.ps1` d'accord avec ces paliers. Un test garde les seuils identiques partout.

### IN4 — Repris du brief Bascule (utile avec `qwen2.5:7b`)

- **Mode jeu :** pendant un jeu en plein écran, Atlas décharge le modèle et rend la VRAM. À la demande suivante, il le recharge et le dit (« Je recharge mon modèle, quelques secondes »). Mesurer la VRAM rendue et le temps de rechargement.
- **Épinglage :** Atlas vérifie au démarrage que le modèle installé a bien l'empreinte attendue. Sinon, c'est une bascule annoncée, avec l'empreinte attendue et celle trouvée.
- **Banc de non-régression en une commande** (`scripts/non_regression_modele.py`) : GB1, plans, documents et faits inventés, consignes, conversation en français. La référence de `qwen2.5:7b` est enregistrée. `doctor.py` signale si Ollama a changé de version depuis le dernier banc réussi.

### IN5 — La désinstallation

- Retire Atlas, ses raccourcis et son démarrage automatique.
- **Demande** : « Garder ta mémoire, ce qu'Atlas a appris et tes rappels ? » (oui par défaut). Si non : une sauvegarde est proposée avant l'effacement.
- Supprime les secrets du coffre de Windows (`Atlas:*`), et le dit.
- **Ne désinstalle pas Ollama ni Tesseract sans le demander** : ils peuvent servir à autre chose.

### IN6 — Les tests

- **Sur une machine vierge : Windows Sandbox** (disponible sur Windows 11 Pro, la version d'Alexis), pour le parcours complet d'installation et de désinstallation. Il n'y a pas de GPU dans la Sandbox : le chemin « sans NVIDIA » y est donc testé aussi.
- **Réinstallation par-dessus** une installation existante : rien n'est perdu.
- **Le paquet produit** ne contient aucune donnée d'Alexis (test automatique sur son contenu).
- **Sur le PC du proche** : par Alexis, avec CHAT6 en soutien. C'est là que le **Bluetooth** sera mesuré pour de vrai (radio, confirmation clavier et souris), si la machine en a.

### IN7 — Les finitions avant la démo

- **Agenda sur plusieurs jours** : « cette semaine », « ce week-end ». À défaut, Atlas dit « je ne sais lire qu'un jour à la fois » au lieu de répondre pour aujourd'hui.
- **Consigne du lecteur de mails** : ne jamais reprendre à son compte une affirmation du mail sur Alexis ou sur Atlas. Mesuré au banc hostile.
- **Revoir de visu** l'affichage du résultat d'une confirmation dans la fenêtre de bureau.
- **Budget de la consigne vocale** : il est presque plein. Le dégager (consigne plus courte, ou liste des capacités résumée), mesuré.
- **Le guide testeur, réécrit en entier** pour la démo :
  - ce qu'Atlas sait faire (Compétences 1 et 2, documents, fichiers, apprentissage) ;
  - ce qu'il ne sait pas faire ;
  - « Hey Atlas » à l'anglaise ;
  - les confirmations ;
  - l'écran SmartScreen ;
  - la connexion facultative aux mails ;
  - comment arrêter, désinstaller et donner son avis.

  Chaque phrase vraie, rejouée.

### IN8 — Rapport

- **En tête :**
  - le parcours d'installation, en temps et en étapes, dans la Sandbox ;
  - la taille téléchargée ;
  - le résultat du test de capacité ;
  - la désinstallation ;
  - l'état des finitions.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama, 0 ignoré tout lancé. Corpus ≥ 99,8 %, GB1 à 0, banc de non-régression vert.
- Règle C3 et garde BM0.
- `docs/rapports/RAPPORT_SPRINT_INSTALLEUR.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 4. Critères de validation

- [ ] Installeur en un double-clic, testé de bout en bout dans Windows Sandbox
- [ ] Diagnostic avant, test de capacité réelle après le téléchargement du modèle ; arrêt propre si la machine ne convient pas
- [ ] Téléchargements officiels, en HTTPS, vérifiés ; dépendances avec empreintes
- [ ] Ollama sur `127.0.0.1`, modèle épinglé et vérifié au démarrage ; Tesseract avec le français
- [ ] Paliers cohérents partout (installeur, `doctor.py`, `precheck_atlas.ps1`), testés
- [ ] Mode jeu mesuré ; banc de non-régression en une commande, avec référence
- [ ] Réinstallation sans perte ; désinstallation qui demande pour la mémoire et retire les secrets
- [ ] Aucune donnée d'Alexis dans le paquet, prouvé par un test
- [ ] `"simulation"` installé par défaut pour les mails ; démarrage avec Windows décoché par défaut
- [ ] Finitions : agenda multi-jours (ou dit), consigne du lecteur, confirmation revue, budget de la consigne dégagé, guide testeur réécrit et vrai
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

## 5. Rappels

- Une personne qui n'est pas informaticienne doit y arriver seule.
- Rien d'Alexis dans le paquet.
- En cas de doute sur la mémoire ou les données : ne pas exécuter, demander.
