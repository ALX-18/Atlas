# BRIEF SPRINT G-TER — La première impression d'un testeur

**Destinataire :** CHAT6 (Claude Opus, Claude Code Windows)
**Émetteur :** Superviseur technique Atlas
**Date d'émission :** 11 octobre 2026
**Durée visée :** une demi-journée
**Statut :** dernier passage avant la beta. G7 est fait.
**Références :** `docs/rapports/BILAN_SESSION_ALEXIS_20261011.md` (points 4 à 7, « moins grave », §5), rapport G-bis

---

## 1. Décisions

**Le bilan du 11/10 est validé**, y compris les trois corrections de la garde (branche `g-bis-suivi`). Le trou « D'accord, je vais me fermer. » est la limite acceptée avec réserve en G-bis : la garde repose sur une liste, et la session réelle d'Alexis l'a trouvé avant les testeurs. Bonne prise.

**Décisions d'Alexis :**
- G-ter est fait **avant** toute installation chez un proche.
- « tu peux faire quoi ? » reçoit une **réponse fixe**, construite à partir des outils réels.
- Mémoire : seule `conv_f8b7b5aab1a9` est retirée. Le reste de sa session, c'est son vrai usage.

**Décisions du superviseur :** points 6 et 7 corrigés ; l'avertissement GPU faux est corrigé ; la latence vocale (11 à 22 s) attend le sprint suivant.

---

## 2. Périmètre

**Autorisé :** `core/intent_classifier.py`, `core/intent_engine.py`, `core/validator.py`, `core/ollama_client.py` (consignes), `api/routes.py`, `tools/window_controller.py`, `tools/app_launcher.py` (ou le fichier qui gère « ouvre X »), le message de démarrage GPU (`main.py` et `scripts/doctor.py` si concerné), `docs/beta/`, `tests/`, la mémoire pour GT6.

**Interdit :** la latence, l'heure (L4), la recherche web brute, les applications UWP, les modes au sens du futur sprint, le grounding.

**Méthode inchangée :** test rouge d'abord, sortie brute consignée, aucun effet réel dans les tests. **Les phrases exactes de la session d'Alexis servent de tests.**

---

## 3. Tâches

### GT0 — Fusion

Fusionner `g-bis-suivi` dans `main` (927 passés / 4 ignorés attendus), puis travailler sur une branche `sprint-g-ter`.

### GT1 — « Tu peux faire quoi ? »

1. **Réponse fixe, construite automatiquement** à partir de la liste des outils que le moteur exécute réellement. Pas de texte écrit à la main dans un coin, qui finira par dire autre chose que le code : c'est le défaut récurrent du projet (une couche annonce ce qu'une autre n'applique pas).
2. Courte, lisible par un non-informaticien, regroupée par familles (applications et fenêtres, écrire ailleurs, système, mémoire, modes, voix…). Elle dit aussi ce qui demande une confirmation.
3. Formes à reconnaître, au moins : « tu peux faire quoi ? », « tu sais faire quoi ? », « qu'est-ce que tu sais faire ? », « qu'est-ce que tu peux faire ? », « aide », « tes capacités ». « qu'est-ce que tu sais faire ? » ne doit toujours pas rejouer une action (GB2).
4. **Test de cohérence** : tout ce que la réponse annonce existe dans le registre d'outils, et chaque famille d'outils exposée y figure.
5. **L'excès inverse.** Le modèle répond « je ne peux pas effectuer d'action sur votre ordinateur » (« toi fais le »). Corriger la consigne : il n'a pas agi **pendant cette conversation**, mais Atlas sait agir par ses outils, et il peut le dire. La garde GB1 reste entière.

### GT2 — Une question sur un mode n'est pas un ordre

« il consiste à quoi le mode gaming ? » propose aujourd'hui de **lancer** le mode.

- Une question sur un mode ou un workflow (« c'est quoi… », « il consiste à quoi… », « que fait… », « qu'est-ce qu'il y a dans… ») **décrit** le mode à partir de sa définition : la liste de ses étapes, lue dans le fichier, sans le modèle. Rien n'est lancé.
- « lance le mode gaming » le lance toujours, avec sa confirmation.
- **Un mode qui n'existe pas n'est jamais proposé au lancement** (« active le mode sombre », « active le mode avion » au rapport G-bis). Atlas dit qu'il ne connaît pas ce mode et cite ceux qui existent.

### GT3 — La cible ne garde pas le verbe

« Fermes, Steam. » (transcription) → confirmation pour la fenêtre « fermes, steam ». Retirer de la cible les formes du verbe d'action (fermes, fermez, fermé, ferme-moi…) et la ponctuation. Tests sur plusieurs verbes (fermer, ouvrir, réduire, mettre au premier plan) et sur des variantes de transcription réelles.

### GT4 — « Ouvre Steam » quand Steam tourne déjà

Steam tourne en arrière-plan, sa fenêtre fermée : « ouvre steam » répond « déjà lancé » et rien ne revient.

- Si une fenêtre de l'application existe, la ramener au premier plan (restaurée si réduite).
- Si l'application tourne sans fenêtre (zone de notification), trouver la manière fiable de la faire réapparaître, et ne jamais ouvrir une seconde instance d'une application qui ne le supporte pas. Dire ce qui a été choisi et pourquoi.
- Le message dit ce qui s'est passé (« Steam était déjà lancé, je ramène sa fenêtre »), et seulement si c'est vrai.
- Rejeu réel avec Steam.

### GT5 — L'avertissement GPU

Au démarrage, « aucun GPU CUDA détecté » est affiché alors que la voix tourne sur le GPU (torch en version processeur, CTranslate2 sur CUDA). C'est un message qui ment. Il doit refléter ce que la transcription utilise réellement. Vérifier la même chose dans `doctor.py`. Preuve : un démarrage réel.

### GT6 — Mémoire

Sauvegarde, `verify`, puis retrait de **`conv_f8b7b5aab1a9`** seul, par `plan-ids` / `apply-ids --yes`. Décomptes avant et après. Rien d'autre n'est touché, notamment les 2 corrections d'Alexis.

### GT7 — Guide, vérification, rapport

1. `docs/beta/GUIDE_TESTEUR.md` : ce que GT1 à GT4 changent, chaque phrase vraie.
2. **Rejeu réel, au clavier et à la voix**, des phrases exactes de la session : « tu peux faire quoi ? », « toi fais le », « il consiste à quoi le mode gaming ? », « Fermes, Steam. », « ouvre steam » après fermeture de la fenêtre, « ok tu peux te fermer ».
3. `python -m pytest tests/ -q` → code 0.
4. Rapport conforme à `docs/RAPPORT_RULES.md` dans `docs/rapports/RAPPORT_SPRINT_G_TER.md`. Une ligne en tête : **la beta peut-elle commencer, oui ou non ?**

---

## 4. Critères de validation

- [ ] `g-bis-suivi` fusionnée, suite verte
- [ ] « tu peux faire quoi ? » et ses variantes → réponse fixe, construite à partir du registre d'outils, testée en cohérence
- [ ] Le modèle ne nie plus qu'Atlas sait agir ; la garde GB1 tient toujours (0 affirmation sur la liste G-bis)
- [ ] Question sur un mode → description depuis sa définition, rien lancé ; « lance le mode » marche
- [ ] Un mode inexistant n'est jamais proposé au lancement
- [ ] La cible ne contient plus le verbe ni la ponctuation
- [ ] « ouvre X » sur une application déjà lancée ramène sa fenêtre, sans seconde instance ; prouvé avec Steam
- [ ] Message GPU exact au démarrage et dans `doctor.py`
- [ ] `conv_f8b7b5aab1a9` retirée seule, après sauvegarde vérifiée
- [ ] Guide à jour ; phrases de la session rejouées au clavier et à la voix
- [ ] `python -m pytest tests/ -q` → code 0

## 5. Rappels

- Une seule source de vérité pour les capacités : le registre d'outils.
- Une question n'est jamais un ordre.
- En cas de doute sur Docker ou la mémoire : ne pas exécuter, demander.
