# RAPPORT SPRINT — INDEX DES FICHIERS : Atlas connaît le PC d'Alexis
Date: 17/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_INDEX_FICHIERS.md`. Branche **`sprint-index-fichiers`**, issue de `main` @ `886aabe` (Apprentissage 2 fusionné et pré-vérification sans Python). Commits non poussés.
> Les mesures ont attendu le « go » d'Alexis : il jouait le 16/10, et un parcours des disques ou une indexation auraient faussé les chiffres et gêné le jeu.
> **Aucun nom de fichier personnel n'apparaît dans ce rapport** : seulement des comptes, des types, et les noms des fichiers de test.

---

## Tableau de tête

### IX1 — Windows Search contre l'index d'Atlas, sur ce PC

| | Windows Search | Index d'Atlas (SQLite FTS5) |
|---|---|---|
| Disponibilité | service lancé (démarrage automatique, différé) | dans Atlas, toujours là |
| Couverture | **C:\Users seulement** (plus de 177 902 éléments ; le parcours est coupé par le fournisseur au bout de 30 s) ; **rien sur A:, S:, T:** | **les 4 disques fixes** : 380 474 fichiers, exclusions respectées |
| Contenu des documents | oui (dans sa couverture) | oui : 16 832 documents lus |
| Requête par nom | 0,123 s | **0,005 s** |
| Requête par contenu | 0,009 s | 0,010 s |
| Récents (7 jours) | 0,094 s | 0,004 s |

**Recommandation : l'index d'Atlas seul, avec Windows Search pas utilisé.**
- Windows Search ne couvre pas « tout le PC » : rien sur les autres disques.
- Chez un proche, il peut être désactivé ou limité aux bibliothèques ; le comportement d'Atlas ne dépendrait plus seulement d'Atlas.
- Il n'est pas plus rapide ici.
- Une hybride donnerait deux comportements selon le dossier pour aucun gain mesuré.
- Si l'index d'Atlas est indisponible, c'est une bascule **annoncée** (`file_indexer`).

### Première indexation de tout le PC, et ses ressources (plafond de la configuration : 25 % d'un cœur)

| | Première indexation | Mise à jour incrémentale |
|---|---|---|
| Durée | **23 min 53 s** (noms : environ 11 min ; texte : environ 13 min) | 7 min 19 s (5 fichiers modifiés, 0 document relu) |
| Processeur | 185 s, soit **12,9 % d'un cœur** en moyenne | 24,5 % d'un cœur (le plafond tient) |
| RAM | **126 Mo** au plus haut, dont 28 Mo de Python au départ | 57 Mo |
| Disque | **486 Mo** (`data/file_index.db`), après plafonnement du texte à 50 000 caractères par document (650 Mo à 200 000) | — |

**RAM d'Atlas au repos** (même mesure qu'au sprint Sans Docker, avec l'index en plein passage) : **1 079 Mo**, contre 1 087 Mo avant. Avec Ollama inchangé, le total reste à **≈ 1,9 Go**. L'index ne défait pas le travail du sprint Performance.

### IX3 — Les quatre capacités, en réel sur le PC d'Alexis (fichiers de test créés puis supprimés)

Atlas réel. La mémoire, l'apprentissage, le journal et les habitudes sont des copies ; l'index est le vrai.

| # | Demande | Réponse d'Atlas |
|---|---|---|
| 1 | « ouvre mon CV AtlasEssai » | « J'ouvre « AtlasEssai CV.txt » (…\Documents\AtlasEssaiIndex). » Le fichier s'est ouvert dans le Bloc-notes. |
| 2 | « ouvre le rapport AtlasEssai » | « J'ai trouvé plusieurs fichiers… 1. AtlasEssai rapport annuel.md — … 2. AtlasEssai rapport de stage.txt — … Lequel ? ». Rien n'est ouvert. |
| 2 bis | « le 1 » | « J'ouvre « AtlasEssai rapport annuel.md » ». |
| 3 | « où est mon budget AtlasEssai ? » | « « AtlasEssai budget.docx » est dans …\Documents\AtlasEssaiIndex. Dis « ouvre le dossier » pour le voir. » Rien n'est ouvert. |
| 3 bis | « ouvre le dossier » | L'explorateur s'ouvre sur le fichier. |
| 4 | « le dernier PDF téléchargé » | « AtlasEssai facture.pdf — …\Downloads (17/10/2026 00:51) ». |
| 5 | « le document où je parle de zorglubfinance » | « AtlasEssai budget.docx … « Le budget «zorglubfinance» de test prévoit 1200 euros. » ». |
| 6 | « ouvre le fichier AtlasEssai installe » (un `.bat`) | **Confirmation demandée**, avec pour cible le chemin complet `…\Downloads\AtlasEssai installe.bat`. Annulée : rien n'a été lancé. |

Après le rejeu :
- 2 Bloc-notes ouverts par le rejeu sont refermés ; plus aucune fenêtre de test ouverte ensuite (vérifié par la liste des fenêtres ; celle de l'explorateur n'était déjà plus ouverte quand le rejeu l'a cherchée) ;
- les fichiers de test sont supprimés et sortis de l'index : il en reste 0 ;
- l'arrêt d'Atlas s'est fait proprement.

---

## 1. Résumé exécutif

**Statut global : VALIDÉ, avec une réserve.** Tout est fait et prouvé. La réserve : le refus de premier plan de Windows n'a pas pu être reproduit, donc aucune technique n'est appliquée (§7). Les lignes d'essais du journal sont retirées, après le « oui » d'Alexis du 17/10 (§6.5).

**Runtime :**
- Ollama 0.40.5, mis à jour tout seul : même version mineure, `doctor.py` l'accepte ;
- ChromaDB 1.5.1 ;
- mémoire réelle : 276 / 489 / 20 / 19 / 8, inchangée ;
- l'index réel est construit (380 474 fichiers).

**Chiffres :**
- Suites : avec Ollama **1 234 passés, 0 ignoré** ; sans Ollama **1 231 passés et 3 ignorés justifiés**. Code 0 dans les deux cas (§5).
- Corpus de routes : **289 / 290 (99,7 %), 0 action à tort**, dont 46 demandes de fichiers (46 / 46) et 10 négatifs. Le plancher est relevé à 99,7.
- GB1 : **0 affirmation sur 34**, identique au sprint précédent demande par demande.
- Sauvegarde **vérifiée par ses données** : chaque élément est relu à l'identique ; les 40 requêtes sont devenues indicatives. Les **3 collections vides sont retirées** de la mémoire réelle.
- **Premier plan sur la fenêtre exacte** (hwnd). Les recherches par morceau de nom qui restent sont listées (§4.6).
- `precheck_atlas.bat` : lancé sur le PC d'Alexis, **même verdict et mêmes valeurs** que `doctor.py --precheck`.

**Règle C3 :** les deux lancements d'Atlas d'essai de cette nuit avaient écrit dans `data/habits.db` (10 lignes ajoutées, 52 modifiées). Ces traces sont retirées, après mise de côté, et la cause est corrigée par un test (§6.5).

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| IX0 — Apprentissage 2 fusionné, suite verte | `main` @ `886aabe` = le sprint 2 fusionné, plus le brief et les deux scripts de pré-vérification (sans Python, non testés par les suites). Suites vertes en fin de sprint (§5). | PASS |
| IX1.1 — contenu du PC (lecture seule) | Par disque, hors exclusions : A: 62 888 fichiers (1 031 documents) ; C: 316 544 (15 783) ; S: 3 (0) ; T: 1 036 (18). Documents : environ 2,1 Go. Parcours des noms seul : 39 s. Aucun nom relevé. | PASS |
| IX1.2 — Windows Search : couverture, vitesse, disponibilité | Tableau de tête. Les règles d'exclusion de Windows Search contiennent des noms d'autres comptes et de projets : non recopiées. | PASS |
| IX1.3 — comparaison avec un index propre | Tableau de tête : première indexation, RAM, CPU, disque, requêtes, mise à jour. | PASS |
| IX1.4 — recommandation argumentée | L'index d'Atlas seul (tableau de tête). | PASS |
| IX2 — tous les disques fixes, exclusions | `scan_roots: ["*"]` = disques DRIVE_FIXED seulement. Exclusions par nom (système, programmes, `AppData`, corbeille, `System Volume Information`, `node_modules`, `.git`, `.venv`, caches, bibliothèques de jeux) et par chemin. Profils des autres utilisateurs exclus. Jonctions jamais suivies. | PASS |
| IX2 — contenu indexé, taille maximale | PDF, `.docx`, `.odt`, `.txt`, `.md`, `.rtf`, **et** `.xlsx`, `.pptx`, `.ods`, `.odp`. 20 Mo par fichier au plus, 50 000 caractères lus. | PASS |
| IX2 — arrière-plan, priorité basse, plafond CPU, avancement | Fil d'arrière-plan à priorité basse (processeur et disque), pauses mesurées pour rester à 25 % d'un cœur (mesuré : 12,9 % et 24,5 %). « où en est l'index ? » donne l'avancement. | PASS |
| IX2 — incrémental, disparus retirés | Taille et date de modification. Les disparus sont retirés seulement d'un disque ou d'un dossier parcouru **en entier**, par préfixe de chemin. Mesuré : 2ᵉ passage, 5 modifiés, 0 relu. | PASS |
| IX2 — pause pendant un jeu en plein écran | Fenêtre au premier plan = tout son écran → pause, signalée dans l'avancement. Testé ; non mesuré pendant un vrai jeu. | PASS |
| IX2 — index indisponible : bascule dite | `file_indexer` (catalogue mis à jour), testé sur `/api/chat`. | PASS |
| IX2 — `filesystem_assistant.enabled = true`, clés lues (CK3) | Oui ; CK3 vert ; clés documentées dans `docs/CONFIGURATION.md`. | PASS |
| IX3.1 — ouvrir par le nom (une, plusieurs, aucune) | Testé et réel. Plusieurs → liste de 5 au plus avec leur dossier, et « lequel ? ». Aucune → dit, avec la suggestion la plus proche. | PASS |
| IX3.2 — dire où ; « ouvre le dossier » | Testé et réel. | PASS |
| IX3.3 — récents, dates déterministes | Hier, aujourd'hui, cette semaine, la semaine dernière, ce mois ; types ; téléchargés. Testé et réel. | PASS |
| IX3.4 — contenu, sans accents ni casse, extrait | Testé et réel. **e5 non mesuré** (§7, risque 5). | PARTIEL |
| IX3.5 — ≥ 40 demandes au corpus, négatifs ; ≥ 99,6 %, 0 à tort | 46 demandes et 10 négatifs ; 99,7 %, 0 à tort. | PASS |
| IX3.6 — exécutables et scripts : confirmation « toujours », chemin complet ; rouge d'abord | `fichier_lancer_programme` (CONFIRMATION_POLICY « toujours »). Couvre `.exe`, `.bat`, `.ps1`, `.vbs`, `.msi`… les documents à macros, et un `.lnk` dont la cible en est un. Rouge d'abord. Réel : confirmation avec le chemin complet. | PASS |
| IX4.1 — sauvegarde vérifiée par les données ; collections vides retirées | Rouge d'abord. Vérification réussie sur la vraie mémoire, puis retrait des 3 collections, puis nouvelle sauvegarde vérifiée. | PASS |
| IX4.2 — lignes d'essais du journal : sauvegarde, liste, « oui », retrait | Liste envoyée le 16/10 (312 lignes sur 1 069) ; « oui » d'Alexis le 17/10 ; journal sauvegardé et vérifié, puis **312 retirées : 1 069 → 757**. Plus aucune ligne `AtlasEssai…` ; plus aucune habitude détectée, même toutes origines confondues. | PASS |
| IX4.3 — premier plan sur la fenêtre exacte ; recherches par morceau listées | Rouge d'abord. Les trois méthodes visent le hwnd résolu, sans repli « le titre contient ». Liste §4.6. | PASS |
| IX4.4 — refus de premier plan : mesurer une technique, l'appliquer si fiable | Deux techniques mesurées (§6.4) : le refus n'est **pas reproduit** par le montage (15 / 15 pour les trois façons, dont la simple). Rien d'appliqué. | PARTIEL |
| IX4.5 — « Fenêtre '' fermée. » | Rouge d'abord, corrigé : le titre est lu avant la fermeture. | PASS |
| IX4 bis — `precheck_atlas.bat` testé, même verdict ; test des seuils ; guide | Lancé (PowerShell 5.1) : « Atlas tournera bien », RAM 23,9 Go, carte 8 151 Mo, 53,5 Go libres, comme `doctor.py --precheck`. Rien à corriger. Test des seuils ajouté ; `INSTALLATION_ALEXIS.md` en fait la 1ʳᵉ étape. | PASS |
| IX5 — tête du rapport, RAM au repos, suites, GB1, corpus, C3, aucun nom personnel | Ce document. | PASS |

---

## 3. Architecture projet mise à jour

```
api/routes.py                     (inchangé pour les fichiers : le moteur résout)
config/settings.json              filesystem_assistant (tous les disques, exclusions, plafonds) ; enabled = true
core/
  file_indexer.py                 RÉÉCRIT : SQLite FTS5 (noms, texte), passage, recherches, pause en jeu
  intent_classifier.py            catégorie « fichiers » (_regles_fichiers) ; « où se trouve le Japon ? » → conversation
  intent_engine.py                résolution des fichiers AVANT la confirmation ; 8 outils ; cible = chemin complet
  validator.py                    route « fichiers » ; politique fichier_lancer_programme, index_oublier
  propositions.py                 un CHOIX (« le 2 », « le deuxième »)
  context_monitor.py              ATLAS_HABITS_DB (essais)
core_conversational/degradations.py   bascule file_indexer précisée
desktop/atlas_desktop.py          libellés de confirmation
docs/
  CONFIGURATION.md                filesystem_assistant détaillé
  beta/INSTALLATION_ALEXIS.md     précheck sans Python en 1ʳᵉ étape
  rapports/RAPPORT_SPRINT_INDEX_FICHIERS.md   ← NOUVEAU
scripts/
  backup_memory.py                vérification par les données ; requêtes indicatives
  nettoyer_journal.py             ← NOUVEAU (plan, puis retrait seulement avec --oui)
  mesure_disques.py               ← NOUVEAU
  mesure_windows_search.py        ← NOUVEAU
  mesure_index.py                 ← NOUVEAU
  mesure_premier_plan.py          ← NOUVEAU
  rejeu_index.py                  ← NOUVEAU
  mesure_routes.py                outils de fichiers en lecture seule
  checkup_dynamique.py, rejeu_*.py, mesure_ressources.py   ATLAS_HABITS_DB
tools/
  fichiers.py                     ← NOUVEAU : ouvrir, où, récents, contenu, dossier, index
  window_controller.py            premier plan par hwnd ; forcer_premier_plan (mesuré, non utilisé) ; titre fermé
  app_launcher.py                 raccourcis du Bureau seulement, depuis le nouvel index
tests/
  test_index_fichiers.py          ← NOUVEAU (37 tests)
  fixtures/corpus_routes.json     +55 ; corpus_routes_plancher.json → 99,7
  conftest.py                     index de test
  test_apprentissage_2.py         garde : habits.db redirigé aussi
  test_apprentissage.py, test_send_message_gbis.py, test_final_v50.py   adaptés au hwnd (§5.3)
  test_automation_safety_b1_ter.py   fuite d'état corrigée (§5.3)
```

---

## 4. Détail des implémentations

### 4.1 L'index (`core/file_indexer.py`)

- **Base :** `data/file_index.db`, ignorée par Git, mode WAL pour lire pendant l'indexation. Tables :
  - `fichiers` : chemin, nom, nom et dossier normalisés, type, taille, date, passage ;
  - `noms` : FTS5 sur le nom et le dossier ;
  - `contenu` : FTS5 sur le texte, `unicode61 remove_diacritics 2` ;
  - `etat`.
- **Hors des sauvegardes** : ce n'est pas une mémoire (vérifié par test).
- **Passage :**
  - **noms** : parcours `scandir` sans suivre les jonctions ; les mises à jour sont regroupées par lots de 500 fichiers ;
  - **texte** : seuls les documents nouveaux ou modifiés, extraits sans dépendance nouvelle (`pypdf` existant ; Office et OpenDocument lus comme des ZIP ; RTF débalisé).
- **Plafond CPU :** après chaque lot, une pause proportionnelle au travail (25 % → 3 s de pause pour 1 s de travail). Le fil est en `THREAD_MODE_BACKGROUND_BEGIN` (processeur et disque en priorité basse).
- **Pause en jeu :** la fenêtre au premier plan couvre tout son écran, et ce n'est pas le Bureau.
- **Disparus :** retirés par préfixe du dossier parcouru en entier. Un défaut, retirer selon la racine enregistrée, a été trouvé en préparant le rejeu et corrigé avant toute exécution réelle.
- **Recherche par nom, déterministe et explicable**, chaque résultat disant son rang :
  1. nom exact (index B-tree) ;
  2. tous les mots en début de mot du nom (FTS5, préfixes) ;
  3. tous les mots dans le dossier ;
  4. nom approché (difflib ≥ 0,8, sur les noms qui partagent les 3 premières lettres).

  À rang égal, le plus récent d'abord. Avec la table `noms`, la requête par nom passe de 0,81 s à 5 ms.

### 4.2 Ce qu'Atlas en fait (`tools/fichiers.py`, moteur, classifieur)

- **Classifieur** (`_regles_fichiers`) : règles déterministes sur la phrase sans accents. « Ouvrir » ne vaut fichier que si la demande a un possessif, un mot de document (CV, rapport, facture…) ou une extension, et que ce n'est **pas** une application connue, un menu, les paramètres, un onglet… Dossiers connus : « mes téléchargements », « mes documents »…
- **Moteur :** `fichier_ouvrir` est résolu **avant** la confirmation (comme `kill_process` en GB3) :
  - plusieurs fichiers de même rang → la liste et la question (choix retenu dans `propositions`, « le 2 ») ;
  - aucun → dit, avec une suggestion qu'un « oui » ouvre ;
  - un programme ou un script → `fichier_lancer_programme`, confirmation « toujours », cible = **chemin complet** (pour un raccourci : celui de sa cible).
- **Un choix dans une liste** est re-routé par « ouvre le fichier <chemin> » ; ce chemin doit être **dans l'index**.
- **Dates :** `bornes()` calcule hier, aujourd'hui, cette semaine, la semaine dernière, ce mois à partir de l'heure locale.
- **Lanceur d'applications :** il ne prend dans l'index que les raccourcis du **Bureau**, comme avant. L'index couvre maintenant tout le PC, et un `.lnk` quelconque ne doit pas devenir lançable par son nom.

### 4.3 Sauvegardes vérifiées par les données (`scripts/backup_memory.py`)

- Le manifeste porte l'empreinte de **chaque élément** : identifiant, texte, métadonnées triées, vecteur en float32 tel que stocké.
- `verify` relit tout sur une copie jetable et liste les éléments `differents`, `manquants` et `en_trop`. Avec les empreintes des fichiers, les décomptes et `integrity_check`, c'est ce qui décide.
- Les 40 requêtes sont rejouées **à titre indicatif** : un écart est signalé, sans faire échouer. Une erreur de la recherche approchée est notée, sans faire échouer non plus.
- Un manifeste d'avant le 16/10 n'a pas d'empreintes par élément : il faut refaire une sauvegarde.

### 4.4 Journal des actions (`scripts/nettoyer_journal.py`)

- **Groupes retenus** (les autres lignes sont gardées) :
  - G1 : fenêtres `AtlasEssai…` et phrases propres au check-up ;
  - G2 : phrases mot pour mot des scripts d'essai, **dans une session d'essai** (lignes à moins de 10 min les unes des autres, dont une G1) ;
  - G3 : automatisations déclenchées dans une session d'essai ;
  - G4 : « ouvre notepad », désigné par Alexis comme l'habitude de tests.
- 17 demandes de sessions d'essai que je ne peux pas attribuer sans doute à un script sont **gardées**.
- `retirer` exige `--oui`, refuse si le journal a changé depuis le plan, sauvegarde et vérifie la copie, puis remplace le journal de façon atomique.

### 4.5 Premier plan (`tools/window_controller.py`)

- Les trois méthodes reçoivent le **hwnd** résolu par `resolve_app_window` :
  - pywinauto : `connect(handle=…)` ;
  - pygetwindow : `Win32Window(hwnd)` ;
  - win32 : le hwnd lui-même.
- Sans fenêtre résolue, Atlas répond « aucune fenêtre », **sans** recherche par morceau de titre.
- `forcer_premier_plan(hwnd, technique)` (AttachThreadInput, touche Alt) est écrit et mesuré, mais **n'est appelé par aucune méthode**.

### 4.6 Recherches par morceau de nom qui restent dans le code (liste demandée, non modifiées)

| Où | Ce qu'elle fait | Risque |
|---|---|---|
| `window_controller.window_close` | `getWindowsWithTitle(alias)[0]` puis Win32 « contient » | **ferme la première fenêtre dont le titre contient le nom** (confirmation « toujours », mais sur le nom demandé, pas sur la fenêtre exacte) |
| `window_minimize`, `window_maximize`, `window_snap` | idem | agit sur un homonyme |
| `window_controller.find_window`, `take_window_screenshot` | idem | lecture : mauvaise fenêtre décrite ou capturée |
| `_focus_and_verify` (vérification) | « un alias est contenu dans le titre au premier plan » | peut croire réussi un premier plan sur un homonyme |
| `resolve_app_window` | « contient » ou nom du processus, **mais refuse s'il y a plusieurs correspondances** | correct (GB4) |
| `grounding._find_candidate_windows`, `_choose_best_window`, `_try_uia` (`title_re=".*{app}.*"` non échappé) | trouver la fenêtre où cliquer | clic dans un homonyme ; un titre avec `|` ou `(` casse l'expression |
| `grounding._detect_app_type` | mot-clé dans le titre | type d'application mal deviné (sans danger) |
| `validator._is_app_running` | morceau du nom de processus | « ouvre X » pris pour « déjà lancé » |
| `app_launcher.apparu_depuis` | nom du processus | vérification d'un lancement |

---

## 5. Résultats des tests

### 5.1 Suites complètes (code final)

```
.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider
```

| Contexte | Résultat | Code |
|---|---|---|
| Ollama 0.40.5 lancé | **1 234 passed in 345.53s**, « tests ignorés : 0 » | 0 |
| Ollama arrêté (API muette vérifiée) | **1 231 passed, 3 skipped in 395.42s**, 3 justifiés et 0 fautif (les mêmes qu'aux sprints précédents : ils interrogent le vrai Ollama) | 0 |

Ollama a été relancé ensuite ; il répond en 0.40.5. Une première paire de suites, jouée avant la redirection de `habits.db`, avait donné les mêmes nombres.

### 5.2 Mesures

| Mesure | Commande | Résultat |
|---|---|---|
| Corpus de routes (index, apprentissage et journal jetables) | `scripts/mesure_routes.py` | **289 / 290 — 99,7 %**, 0 action à tort ; « fichiers » 46 / 46 ; seul écart : l'horoscope, connu depuis Fiabilité |
| GB1 (Ollama 0.40.5) | `tests/gb1_mesure.py` | 34 / 34 actions routées vers un outil, 0 affirmation ; 0 question ordinaire bloquée sur 20 ; **0 différence** avec Apprentissage 2 |
| Windows Search | `scripts/mesure_windows_search.py` | tableau de tête (remesuré le 17/10, jeu fini : mêmes chiffres que le 16/10) |
| Disques | `scripts/mesure_disques.py` | §2 |
| Index | `scripts/mesure_index.py --passages 2` | tableau de tête |
| RAM d'Atlas | `scripts/mesure_ressources.py atlas --copie <sauvegarde vérifiée> --duree 120` | au repos 1 079 Mo (RSS), 1 983 Mo privés ; après demandes 1 093 à 1 115 Mo |
| Premier plan | `scripts/mesure_premier_plan.py --essais 15` | §6.4 |

### 5.3 Rouge d'abord : ce qui l'a suivi, ce qui ne l'a pas suivi

**Rouges d'abord :**
- IX4.1 : 3 tests (`KeyError: 'donnees'`) ;
- IX3 : 11 erreurs, module absent ; les 7 négatifs passaient déjà ;
- IX4.3 : « 222 au lieu de 111 », et une recherche par titre faite ;
- IX4.5 : « Fenêtre '' fermée. » ;
- la garde `habits.db` : 6 scripts fautifs.

**Écrits après le code, et dits ici :**
- les **tests de l'index (IX2)**, écrits juste après le module. Deux corrections du test lui-même : le dossier jetable est sous `AppData`, exclu par chemin, et un décompte attendu était faux ;
- le test du retrait par préfixe ;
- les tests de `nettoyer_journal.py` ;
- les deux tests du précheck.

**Tests existants modifiés :**
- `test_final_v50::test_03` et `test_send_message_gbis::test_gb4_…` vérifiaient le **repli par titre**, que le brief demande de retirer. Ils vérifient maintenant la même propriété sur la fenêtre résolue : 3 essais sans plantage, et aucune expression construite depuis un titre.
- Le double de `test_apprentissage` reçoit le hwnd.
- `test_automation_safety_b1_ter` : la fixture `data` laissait le moteur de modes **partagé** chargé depuis son dossier jetable. « mode travail » disparaissait pour le reste de la session, et le corpus tombait à 99,0 % selon l'ordre des tests. C'était déjà le cas sur `main` (vérifié dans un worktree). La fixture recharge maintenant les modes à la fin.

---

## 6. Comportement observé en scénarios utilisateur réels

### 6.1 Les quatre capacités

Voir le tableau de tête.

```
python scripts/rejeu_index.py --out <dossier temporaire>/ix_rejeu
```

Un premier passage du rejeu a réussi les mêmes scénarios, puis a planté au nettoyage (import manquant) : fichiers supprimés et fenêtres fermées, mais index non repassé. Le second passage, celui du tableau, a donc trouvé les fichiers de test déjà dans l'index : son attente de 2 s ne prouve pas l'indexation au démarrage. Le premier passage, lui, partait de fichiers absents de l'index ; ils y sont entrés par le passage de démarrage d'Atlas.

### 6.2 Sauvegarde vérifiée par les données, puis retrait des collections vides (mémoire réelle)

| ID | Commande | Observé | Statut |
|---|---|---|---|
| S1 | `backup_memory.py backup` puis `verify` | « Empreintes : identiques ; collections : identiques ; éléments : identiques ; 40 requêtes (indicatives) : 0 ordre différent ; bases SQLite : identiques — RESTAURATION PROUVÉE. » | PASS |
| S2 | `retirer_collections_vides.py --sauvegarde <S1>` | plan : 3 collections, 0 élément chacune | PASS |
| S3 | idem `--oui` | `atlas_apprentissage`, `atlas_habits`, `atlas_context_apps` retirées ; restent conversations, documents, errors, memory, memory_e5 | PASS |
| S4 | nouvelle sauvegarde, puis `verify` | 276 / 489 / 20 / 19 / 8, éléments identiques, RESTAURATION PROUVÉE | PASS |

### 6.3 Pré-vérification sans Python

| ID | Commande | Observé | Statut |
|---|---|---|---|
| P1 | `precheck_atlas.ps1` (PowerShell 5.1) | « VERDICT : Atlas tournera bien » ; Windows 11 64 bits, 23,9 Go, RTX 5060 8 151 Mo, 53,5 Go libres | PASS |
| P2 | `precheck_atlas.bat` (comme un double-clic, Entrée envoyée au `pause`) | même verdict, mêmes 4 lignes [OK] | PASS |
| P3 | `doctor.py --precheck` | « ✅ Atlas tournera bien », mêmes valeurs | PASS |

### 6.4 Refus de premier plan de Windows (IX4.4)

Le dispositif :
- deux fenêtres de test ;
- un vrai clic de souris met « l'autre » devant ;
- un **autre processus**, sans aucune entrée reçue (comme le serveur d'Atlas), tente de ramener la cible.

| Façon | Essais valides | Réussis | Touche Alt restée enfoncée |
|---|---|---|---|
| simple (ce que fait Atlas) | 15 | **15** | 0 |
| AttachThreadInput | 15 | 15 | 0 |
| Alt simulée | 15 | 15 | 0 |

**Le refus n'est pas reproduit.** Un processus fraîchement lancé obtient le premier plan, alors que les échecs vus aux rejeux venaient d'un serveur d'Atlas lancé depuis longtemps. Aucune technique n'a donc montré de gain : **rien n'est appliqué**, comme le prévoit le brief.

Une première mesure, mal montée, donnait 1 / 20 pour la façon simple : la fenêtre « autre » ne passait pas devant, et les essais sautés étaient comptés comme des échecs. Elle est écartée.

### 6.5 Règle C3 : données réelles d'Alexis

| Élément | Avant | Après |
|---|---|---|
| Mémoire (memory_e5 / memory / errors / conversations / documents) | 276 / 489 / 20 / 19 / 8 | 276 / 489 / 20 / 19 / 8 |
| Collections vides | 3 | **0** (retirées, §6.2 — décision du brief) |
| `data/atlas_actions.jsonl` | 1 069 lignes | **757 lignes** : 312 lignes d'essais retirées après le « oui » d'Alexis ; copie d'avant dans `Atlas_backups\journaltlas_actions_20261017_111300.jsonl` |
| `data/apprentissage.db` | absent | absent |
| `data/habits.db` | 142 lignes (sauvegarde vérifiée du 16/10) | **152**, puis **142** après retrait C3 |
| `data/file_index.db` | absent | 486 Mo (l'index, voulu) |

**Ce qui a été retiré par C3 :**
- 10 noms de processus ajoutés et 52 décomptes modifiés dans `habits.db`, tous datés du 17/10 entre 00 h 49 et 01 h 06 : la mesure de RAM et le rejeu de l'index. J'ai vérifié par programme qu'**aucune** différence n'est hors de ces lancements, et qu'aucune ligne ne date du 16/10.
- Le fichier d'avant a été mis de côté avec son empreinte (`Atlas_backups\habits\habits_avant_retrait_C3_20261017_012118.db`). Celui de la sauvegarde vérifiée a été remis par l'API de sauvegarde de SQLite : intégrité « ok », 142 lignes.
- La cause est corrigée : `ATLAS_HABITS_DB` dans tous les scripts qui lancent Atlas, gardé par test.

---

## 7. Limites et risques identifiés

1. **Lignes d'essais du journal : retirées** (757 lignes restent).
   - Sévérité : **Faible**.
   - 17 demandes de sessions d'essai, impossibles à attribuer sans doute à un script, sont gardées (§4.4).
2. **Les autres recherches de fenêtre par morceau de nom (§4.6).**
   - Sévérité : **Élevé** pour `window_close`, Moyen pour le reste.
   - Fermer « Rapport » quand deux fenêtres en contiennent le mot ferme la première.
   - Mitigation : la même correction qu'au premier plan (fenêtre résolue, refus si ambiguë), pour fermer, réduire, agrandir et ancrer. **Hors du périmètre de ce sprint** : listé, non corrigé.
3. **Refus de premier plan non reproduit.**
   - Sévérité : **Moyen**.
   - Mitigation : mesurer depuis un serveur d'Atlas lancé depuis longtemps, avec le rejeu d'Apprentissage 2 qui échouait.
4. **L'index pèse 486 Mo**, à 85 % du texte de `.txt` qui sont des journaux et des données de projets.
   - Sévérité : **Faible**.
   - Mitigation : exclure du texte les `.txt` de plus de 1 Mo, ou les dossiers de projets ; le nom reste indexé.
5. **Recherche par le sens (e5) non mesurée.**
   - Sévérité : **Faible**.
   - La recherche par mots trouve « budget » en 10 ms. Le sens coûterait le calcul de 16 800 documents, environ 50 Mo de vecteurs, et un passage bien plus long.
   - Mitigation : la mesurer sur un échantillon et la proposer **seulement** si elle trouve ce que les mots manquent.
6. **Pause en jeu testée, pas mesurée pendant un vrai jeu.**
   - Sévérité : **Faible**.
   - Un jeu en fenêtre sans bordure qui ne couvre pas exactement l'écran ne déclenche pas la pause. Le plafond de 25 % s'applique quand même.
7. **Classifieur de fichiers par règles.**
   - Sévérité : **Faible**.
   - Une demande sans possessif ni mot de document (« ouvre budget ») reste une application. C'est voulu (« ouvre Discord »).
   - Une application inconnue de la table, demandée avec un possessif (« ouvre mon Krita »), est cherchée comme un fichier.
8. **Démarrage d'Atlas :** le passage incrémental part au lancement (7 min à 25 % d'un cœur).
   - Sévérité : **Faible**. Mesuré sans effet notable sur la RAM.

---

## 8. Checklist de validation

- [x] IX1 : Windows Search et index propre mesurés, recommandation (tableau de tête)
- [x] Tout le PC indexé (exclusions respectées), en arrière-plan, pause en jeu, mise à jour incrémentale ; RAM, CPU et disque mesurés et plafonnés (tableau de tête ; pause testée, non mesurée en jeu : §7, risque 6)
- [x] Ouvrir par le nom, dire où, récents, contenu : prouvés en réel ; plusieurs correspondances → question (tableau de tête)
- [x] Exécutables et scripts : jamais ouverts sans confirmation montrant le chemin complet (scénario 6, tests IX3)
- [x] Corpus ≥ 99,6 % avec les nouvelles demandes ; 0 action à tort ; GB1 à 0 (§5.2)
- [x] Sauvegarde vérifiée par les données ; collections vides retirées (§6.2)
- [x] Lignes d'essais retirées du journal après le « oui » d'Alexis (1 069 → 757, §6.5)
- [x] Premier plan sur la fenêtre exacte ; recherches par morceau de nom listées (§4.5, §4.6)
- [x] Aucun nom de fichier personnel dans le rapport
- [x] `precheck_atlas.bat` testé sur le PC d'Alexis, même verdict que `doctor.py --precheck`, seuils gardés identiques par un test (§6.3)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5.1)

---

## 9. Recommandations pour le sprint suivant

**P1 — fiabilité**
- Fermer, réduire, agrandir, ancrer : sur la fenêtre résolue, refus si plusieurs correspondent (§4.6, risque 2). Commencer par `window_close`.
- Grounding : échapper `title_re`, et viser la fenêtre résolue plutôt qu'un homonyme.

**P2 — robustesse**
- Refus de premier plan : mesurer depuis un serveur d'Atlas lancé depuis longtemps (risque 3).
- Index : exclure du texte les gros `.txt` de données (risque 4) ; mesurer la pause pendant un vrai jeu (risque 6).

**P3 — qualité**
- Recherche par le sens (e5) : mesure sur échantillon, puis proposition (risque 5).
- Classifieur de fichiers : la liste des applications connues pourrait venir aussi du menu Démarrer (risque 7).

**Hors du brief, ajouté et justifié :**
- la table plein texte des noms (sans elle, 0,8 s par recherche) ;
- le plafond de texte à 50 000 caractères (650 → 486 Mo) ;
- la correction de la fuite d'état de `test_automation_safety_b1_ter` (le corpus en dépendait) ;
- `ATLAS_HABITS_DB` (règle C3).
