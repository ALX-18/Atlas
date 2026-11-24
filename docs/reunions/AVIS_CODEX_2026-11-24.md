# Revue d'amélioration d'Atlas par Codex (24/11/2026)

**Demandée par :** Alexis.

**Conditions :** lecture seule, sans `data/`, `logs/` ni `config/settings.json`, avec les invariants en cadre.

**Vérification du superviseur (24/11) :** 7 affirmations ont été contrôlées dans le code. **Les 7 sont exactes** :

1. La désinstallation efface `{app}` même quand la sauvegarde a échoué. Le code de retour de Python est ignoré (`installeur/atlas.iss` l.237 et l.258, `installeur/desinstaller.py` l.103-108).
2. `replan()` ne passe pas par `_validate_plan` (`core/planner.py` l.94-117).
3. Une étape non résolue est envoyée directement à `execute_tool` (`core/intent_engine.py` l.1516-1524).
4. Après une confirmation, le résultat est toujours enveloppé dans `"status": "success"`, et l'action est enregistrée en mémoire comme exécutée (`core/intent_engine.py` l.2200-2209).
5. Le lecteur web réessaie avec `verify=False` (`tools/web_reader.py` l.69-74).
6. `maintenance_cleanup_temp` est autorisé en automatisation, et il appelle `shutil.rmtree` d'après l'âge du dossier seul (`core/validator.py` l.434-440, `core/intent_engine.py` l.1101-1125).
7. Un échec de rappel de la mémoire rend une liste vide, que rien ne distingue de « rien retenu » (`core/memory_manager.py` l.398-431).

Le reste sera vérifié par CHAT6, avec un test rouge d'abord pour chaque point.

**Décision d'Alexis (24/11) :** **tout réparer avant l'envoi aux testeurs**, sans rien couper. Le brief est `docs/briefs/BRIEF_SPRINT_REVUE_CODEX.md`.

---

## Texte de l'avis (tel que rendu par Codex)

### 1. Les cinq améliorations les plus utiles, classées

Les coûts sont des estimations de Codex, en jours de développement et de vérification ciblée. Les quatre premières devraient entrer dans les critères d'envoi du paquet testeur.

**1. Terminer l'isolation entre comptes Windows, et la vérifier sur le paquet livré.**
- **Constat :** décision du 24/11 validée, mais le code est encore en amont.
  - Le lanceur reconnaît Atlas et Ollama au seul fait que leur port répond (`installeur/lancer.py` l.39).
  - Le middleware vérifie l'origine, sans authentifier le compte (`main.py` l.654).
  - Le pont démarre sans lire son réglage (`main.py` l.511).
- **Critère :** deux comptes standard, une reconnexion fenêtre ouverte, une installation neuve et une mise à jour.
- **Pour Ollama :** vérifier le propriétaire avant les téléchargements et avant l'envoi de données. L'API d'Ollama reste une frontière distincte.
- **Coût : 3 à 5 j.** Risque : des refus quand Windows ne laisse pas lire le propriétaire. Il faut afficher le motif et tester le retour à la normale.

**2. Faire de la sauvegarde vérifiée une vraie condition de l'effacement.**
- **Constat :**
  - si la sauvegarde échoue, Python annonce que la mémoire est conservée et rend un code d'échec ; Inno ignore ce code et peut effacer le dossier (`installeur/desinstaller.py` l.103, `installeur/atlas.iss` l.235 et l.258) ;
  - le désinstalleur copie sans lancer la vérification de restauration (`scripts/backup_memory.py` l.242) ;
  - le dernier rapport signale justement un échec de cette vérification.
- **Gain :** une sauvegarde invérifiable laisse la mémoire en place. Une seule couche décide de l'effacement.
- **Test :** sur le désinstalleur compilé, avec une destination inaccessible et une sauvegarde illisible.
- **Coût : 1 à 2 j**, plus la cause de l'échec de Chroma. Risque : une désinstallation partielle ; le bilan doit dire précisément ce qui reste.

**3. Appliquer la même validation à toutes les voies d'exécution.**
- **Constat :**
  - le plan initial passe par le validateur, mais le plan de remplacement est seulement décodé (`core/planner.py` l.85 et l.109) ;
  - les étapes non résolues sont exécutées directement (`core/intent_engine.py` l.1516). Ce chemin applique bien la confirmation « toujours » (l.1934), mais saute la validation de l'intention, des paramètres et de la cible ;
  - les routes de rangement et d'annulation déplacent des fichiers hors du circuit de confirmation (`api/routes.py` l.944).
- **Gain :** la même règle s'applique quand Atlas reprend un plan, lance un mode ou reçoit une demande directe. Chaque confirmation est liée à la cible et à l'effet montrés, et le résultat réel remonte jusqu'à la réponse.
- **Coût : 3 à 5 j.** Risque : des modes aujourd'hui tolérés seront refusés. Le refus doit dire quelle étape bloque, et lesquelles ont déjà été faites.

**4. Retirer le contenu personnel des journaux et du relevé.**
- **Constat :**
  - la voix journalise la transcription **avant** le contrôle des secrets, et le début de la réponse (`core/voice_engine.py` l.431, l.453 et l.799). Le refus dit pourtant « Je ne l'ai ni gardé ni noté » (`core/contenu_externe.py` l.67) ;
  - la mémoire journalise une partie du souvenir, retours à la ligne compris (`core/memory_manager.py` l.355) ;
  - le nettoyeur du relevé garde les lignes sans en-tête reconnu (`installeur/relever_journaux.py` l.119).
- **Gain :** le contrôle des secrets passe avant la journalisation et l'apprentissage, et le relevé est construit à partir de **champs autorisés**. Test : des phrases fictives, sur plusieurs lignes.
- **Coût : 2 à 4 j.** Risque : un relevé plus pauvre. Il faut garder l'étape, le moteur et la catégorie d'erreur.

**5. Rendre la voix réactive, et son état fiable, sur 16 Go de RAM et 8 Go de VRAM.**
- **Constat :**
  - la transcription est déclarée asynchrone, mais le chargement et la lecture des segments tournent sur la boucle de l'API (`core/voice_engine.py` l.534 et l.705) ;
  - le repli sur le processeur couvre le chargement, pas un échec CUDA pendant l'inférence ;
  - le test de capacité ne fait qu'une courte réponse texte (`installeur/etapes.py` l.525) ;
  - le banc a tourné sur 24 Go (`docs/reunions/REUNION_ATLAS_01_MODELE.md` l.26).
- **Gain :** un seul fil de travail pour Whisper, une bascule sur le processeur annoncée, et l'état réel publié. Mesurer sur la machine cible, à froid et à chaud.
- **Coût : 3 à 5 j.** Risque : une capture qui reste active, ou deux modèles chargés.

### 2. Les défauts que Codex voit

- **Nettoyage des fichiers temporaires :**
  - autorisé en automatisation, et absent de la table des confirmations ;
  - il supprime un dossier entier d'après l'âge du dossier seul ;
  - il compte les erreurs mais rend un succès ;
  - l'historique du rangement est écrit **après** les déplacements (`core/validator.py` l.434 et l.145, `core/intent_engine.py` l.1101, `core/file_organizer.py` l.83).
- **Des résultats annoncés sans être établis :**
  - un plan illisible devient un plan vide, puis « C'est fait » (`core/planner.py` l.124, `core/voice_engine.py` l.877) ;
  - un `success: false` confirmé est enveloppé dans un succès, puis enregistré en mémoire (`core/intent_engine.py` l.2200 et l.2241) ;
  - l'envoi par frappe ignore le retour de la touche Entrée (`tools/window_controller.py` l.713) ;
  - le mode jeu note « mémoire de la carte rendue » après une erreur HTTP (`core/modele_local.py` l.128).
- **Ce qui est exécuté peut différer de ce qui a été confirmé :**
  - la fenêtre est résolue de nouveau au moment de l'envoi, alors que le titre peut rester le même (`core/intent_engine.py` l.196, `tools/window_controller.py` l.700) ;
  - pour Gmail, le mode simulation ou réel est relu à l'exécution et n'est pas dans l'empreinte confirmée (`core/courrier.py` l.178, l.645 et l.655).
- **« Voix OFF » peut s'afficher alors que le micro enregistre encore** : une capture déjà lancée tourne sur un autre flux (`tools/systray.py` l.107, `core/voice_engine.py` l.177 et l.486).
- **L'index des fichiers :**
  - la désactivation ne couvre ni la reconstruction par l'API ni l'indexation des documents produits ;
  - une racine retirée garde ses extraits ;
  - il faut laisser la personne choisir ses dossiers (`core/file_indexer.py` l.323 et l.442, `api/routes.py` l.922, `core/artefacts.py` l.644).
  - Premier parcours mesuré : 23 min 53 s et 486 Mo.
- **Une panne de rappel passe pour une mémoire vide** (`core/memory_manager.py` l.392 et l.428, `core/intent_engine.py` l.1023).
- **L'installation peut finir sur un verdict trompeur** : une mesure absente n'est pas contredite, et si le modèle léger échoue lui aussi, l'installeur dit quand même « installé » (`installeur/etapes.py` l.507, l.608 et l.648).
- **Le lecteur web abaisse la vérification HTTPS en silence** (`tools/web_reader.py` l.66).
- **L'agenda et le changement d'heure :**
  - le décalage du jour courant est appliqué à des dates futures ;
  - une récurrence illisible est réduite à sa première occurrence, avec un avertissement visible seulement dans le journal (`core/agenda.py` l.52, l.417 et l.179).

### 3. Ce qui coûtera cher dans six mois

- **Des règles dupliquées entre les entrées** (voix, API, plans, automatisations). Il faudrait une seule frontière d'exécution, un seul résultat commun, et un tableau de tests par entrée : annulation, échec, simulation, résultat inconnu (`core/voice_engine.py` l.830, `api/routes.py` l.309, `core/intent_engine.py` l.2195).
- **Un paquet qu'on ne peut pas reproduire :**
  - `--ref` fixe le code, mais les dépendances viennent de l'environnement du poste qui construit, et le script Inno du dossier courant (`installeur/construire.py` l.63, l.257 et l.349) ;
  - la reprise saute des étapes déjà cochées sans vérifier l'état installé (`installeur/etapes.py` l.577).
- **L'écart entre les tests Python et le comportement de Windows :**
  - le test Inno lit le texte du script, sans le faire tourner ;
  - la CI est inactive ;
  - la Sandbox a planté (`tests/test_installeur.py` l.673, `docs/proposition_ci/tests-windows.yml`).
- **Des tâches programmées qui peuvent disparaître** : la tâche est gardée en mémoire avant l'écriture JSON, et son identifiant est rendu même si l'écriture échoue (`core/scheduler.py` l.117 et l.293).
- **Le README est en retard** : l'heure, les rappels et le volume y sont marqués absents (`README.md` l.116).

### 4. Ce que Codex ne ferait pas

- **Changer de modèle, ou passer EasyOCR sur la carte graphique par défaut.** Le banc donne environ 1,2 Go de VRAM de plus pour `qwen3:8b`. EasyOCR sur la carte montait à 7 689 Mo sur 8 151.
- **Ajouter une confirmation vocale**, ou laisser le modèle juger qu'une confirmation est inutile.
- **Étendre les connecteurs, ou présenter les documents générés comme vérifiés.** La note humaine est de 3,0/5, et des erreurs factuelles ont été relevées. La démo s'en tient aux brouillons et aux résumés de sources fournies.

### 5. Ce que Codex n'a pas pu vérifier

- Le paquet final sur Windows : deux comptes, la mise à jour avec le pont actif, l'arrêt d'Ollama, l'échec de sauvegarde avec le désinstalleur compilé.
- La fréquence et l'effet réels des défauts : aucune mesure du délai vocal ni des pics de mémoire sur la machine cible.
- L'état installé et les données de la personne : rien n'a été ouvert.
