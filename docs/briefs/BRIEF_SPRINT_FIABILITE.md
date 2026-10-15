# BRIEF SPRINT FIABILITÉ — La bonne route, une seule fois

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 15 octobre 2026
**Durée visée :** une journée
**Références :** rapport Check-up (§6.1, §6.6, §7, §9), rapports G et G-bis (outils choisis à tort, relances)

---

## 1. Décisions

**Le rapport Check-up est validé.** La correction de la lecture d'écran (§4.2) est acceptée : c'était une régression silencieuse de notre fait.

**Décisions d'Alexis (15/10) :**
- **Mesurer EasyOCR sur GPU** : accord pour télécharger torch CUDA (~3 Go) dans un environnement jetable.
- **Supprimer `qwen2.5:14b`, `mistral` et DialoGPT ; garder `minicpm-v`.**
- **La fiabilité passe avant l'apprentissage par les erreurs.** Apprendre d'erreurs de routage qu'on sait corriger à la main n'a pas de sens.

**Pourquoi ce sprint compte pour la démo :** 5 demandes sur 27 vont au mauvais outil, et « ouvre la calculatrice » en ouvre trois. C'est la première chose que verrait un spectateur.

---

## 2. Tâches

### FI0 — Base

`sprint-checkup` fusionnée dans `main`, suite verte (1 062 passés, 0 ignoré).

### FI1 — Un corpus de demandes naturelles

Le Check-up a trouvé 5 erreurs de route **en 27 scénarios**. Il y en a donc d'autres.

1. Constituer `tests/fixtures/corpus_routes.json` : **au moins 150 demandes en français courant**, avec la route attendue (catégorie, outil, cible). Au moins 10 par famille d'outils, avec des variantes réalistes :
   - possessifs (« mes », « mon ») ;
   - accents et absence d'accents ;
   - fautes de frappe courantes ;
   - politesse (« tu peux… », « stp ») ;
   - transcriptions vocales (minuscules, sans ponctuation).
2. Y mettre **obligatoirement** :
   - les 5 phrases du Check-up (D5, D7, D10, D22, D24) ;
   - « ajoute du lait à ma liste de courses » et « résume l'histoire de Rome » (G-bis, Sans Docker) ;
   - les phrases des sessions d'Alexis (`tests/test_session_alexis_gbis.py`, `test_gter.py`) ;
   - **des demandes qu'Atlas ne sait pas faire**, dont la route attendue est la réponse honnête.
3. **Ligne de base :** taux de bonnes routes avant correction, par famille, avec la liste des erreurs.

### FI2 — Corriger les routes

- Les 5 du Check-up, avec ces règles :
  - une **URL** dans la phrase donne priorité à la lecture de cette page ;
  - « liste… en cours » mène aux processus ;
  - « tâches », avec ou sans accent et avec possessif, mène à la planification ;
  - « rappelle-moi de… à 15 h » mène à **planifier**, avec sa confirmation ;
  - une question sur un fait retenu (« quel est le numéro de… ») mène au **rappel mémoire**.
- Puis le reste des erreurs du corpus.
- **Le classifieur reste déterministe** : des règles, pas de modèle. Une règle ajoutée pour une phrase doit tenir sur ses variantes du corpus.
- **Objectif :** au moins 95 % de bonnes routes sur le corpus, **et aucune demande qui part vers une action alors qu'elle était attendue en conversation ou en réponse honnête.** Une mauvaise route vers une action est plus grave qu'une mauvaise route vers une conversation : le dire dans la mesure.
- Le corpus devient un **test permanent**. Le taux ne peut que monter.

### FI3 — Une application ouverte une seule fois

« ouvre la calculatrice » ouvre 3 calculatrices. `launch_app` relance quand sa vérification échoue (`retry_count` 2).

- **Ne jamais relancer** une application dont un processus ou une fenêtre est apparu depuis le premier lancement, même si la vérification échoue.
- Les applications Windows modernes (Calculatrice, Paramètres…) ont un processus hôte (`ApplicationFrameHost`) et un nom de fenêtre localisé : la vérification doit les reconnaître.
- Quand la vérification échoue vraiment, Atlas **le dit**, sans relancer : « J'ai lancé la Calculatrice, mais je ne vois pas sa fenêtre. »
- Rejeu réel : Calculatrice, Bloc-notes, Paramètres, une application déjà ouverte (le chemin GT4 tient toujours). Nombre d'instances compté après chaque demande.

### FI4 — Les limites des automatisations, jamais appliquées

`max_active_triggers` et `min_cooldown_seconds` étaient annoncés dans la configuration, mais rien ne les appliquait : Atlas n'a aujourd'hui **aucune limite** sur ses déclencheurs. Un déclencheur mal réglé pourrait tourner en boucle.

- Les **appliquer**, de façon déterministe : un nombre maximum de déclencheurs actifs, un délai minimum entre deux exécutions d'un même déclencheur.
- Les remettre dans la configuration, maintenant lues (le test CK3 le vérifie).
- Tests rouges d'abord. Un déclencheur bloqué par une limite est journalisé et visible.

### FI5 — Mesure d'EasyOCR sur GPU (accord d'Alexis)

**Pourquoi Alexis le veut :** la lecture d'écran va devenir centrale, quand Atlas pilotera davantage d'applications. Le passé (5 clics sur 30) n'est donc pas le bon critère. La recommandation doit raisonner sur un **usage fréquent** : plusieurs lectures d'écran complètes par minute, en rafale.

- torch CUDA (wheel `cu128`) dans un **environnement jetable à part**, jamais dans le venv d'Atlas.
- `scripts/mesure_easyocr.py`, **avec le modèle de langue chargé en même temps**, comme en vrai :
  - premier usage ;
  - lecture d'une fenêtre ;
  - lecture d'un écran 1080p ;
  - **10 lectures de fenêtre d'affilée** (le cas réel, décision d'Alexis), puis **10 lectures d'écran 1080p** comme pire cas, temps de chacune (usage en rafale) ;
  - **VRAM ajoutée** (le chiffre décisif), et si le modèle de langue reste entièrement sur la carte à côté ;
  - RAM ;
  - taille installée.
- Compléter le tableau des trois options du Check-up, avec une recommandation.
- **Aucun changement de choix** : Alexis décide. Supprimer l'environnement jetable après la mesure, et dire la place libérée.

### FI6 — Ménage décidé par Alexis

- `ollama rm qwen2.5:14b` et `ollama rm mistral`. **Garder `minicpm-v`.**
- Supprimer le cache Hugging Face de DialoGPT-medium.
- Avant : lister ce qui va être supprimé, avec la taille. Après : `ollama list`, et `doctor.py --composants` inchangé pour Atlas.

### FI7 — faster-whisper absent : une bascule annoncée

Aujourd'hui, si faster-whisper manque, chaque phrase vocale échoue sans que rien ne le dise (Check-up §9). En faire une bascule du catalogue, annoncée au démarrage. Test rouge d'abord.

### FI7 bis — Deux écrans

Alexis a **deux écrans**, a priori tous les deux en 1920×1080, le secondaire **à droite** du principal (à vérifier). **Décision d'Alexis :** pour lire ou cliquer, Atlas regarde **la fenêtre visée seulement**, sur l'écran où elle se trouve, jamais l'écran entier par défaut.

1. **Relever la vraie disposition** par l'API Windows : écrans, résolutions, positions, mise à l'échelle (DPI) de chacun. La consigner dans le rapport.
2. **Une incohérence à expliquer :** la mémoire contient un clic d'Atlas à **x = −1482**. Une coordonnée négative suppose un écran **à gauche** du principal, alors qu'Alexis le place à droite. Ancienne disposition, erreur de conversion des coordonnées, ou mise à l'échelle mal prise en compte ? À trouver, pas à supposer.
3. **La capture se limite à la fenêtre visée**, sur l'écran 1 comme sur l'écran 2. Vérifier les couches Tesseract, EasyOCR et le cache de clics.
4. **Rejeu réel sur l'écran secondaire :** une fenêtre de test placée sur l'écran 2, « lis » puis « clique sur… ». Le clic tombe au bon endroit. Même chose sur l'écran 1. Si les deux écrans n'ont pas la même mise à l'échelle, tester aussi ce cas.
5. Une fenêtre à cheval sur deux écrans : dire ce qui se passe.

### FI8 — Rapport

- **En tête :** le taux de bonnes routes, avant et après, et le nombre d'instances ouvertes par « ouvre la calculatrice », avant et après.
- `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; 0 test ignoré tout lancé.
- GB1 : 0 / 34. Règles C3 et « aucune bascule silencieuse ».
- Rejeu réel au clavier des 5 phrases du Check-up et des applications de FI3.
- `docs/rapports/RAPPORT_SPRINT_FIABILITE.md`, conforme à `docs/RAPPORT_RULES.md`.

---

## 3. Critères de validation

- [ ] Corpus de 150 demandes ou plus, ligne de base par famille
- [ ] ≥ 95 % de bonnes routes ; aucune route vers une action à tort ; le corpus est un test permanent
- [ ] Les 5 phrases du Check-up et les 2 de G-bis passent, en réel
- [ ] Une seule instance par demande ; échec de vérification dit, sans relance
- [ ] Limites d'automatisation appliquées et testées
- [ ] EasyOCR GPU mesuré avec le modèle chargé ; trois options chiffrées ; environnement jetable supprimé
- [ ] `qwen2.5:14b`, `mistral` et DialoGPT supprimés ; `minicpm-v` gardé
- [ ] faster-whisper absent : bascule annoncée
- [ ] Deux écrans : disposition relevée ; le x = −1482 expliqué ; lecture et clic justes sur l'écran 1 et l'écran 2, limités à la fenêtre visée
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; GB1 à 0

## 4. Rappels

- Le classifieur reste déterministe.
- Une mauvaise route vers une action est la plus grave.
- En cas de doute sur la mémoire : ne pas exécuter, demander.
