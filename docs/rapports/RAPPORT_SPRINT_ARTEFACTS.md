# RAPPORT SPRINT — ARTEFACTS : Atlas rédige des documents Word et PDF
Date: 17/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_ARTEFACTS.md`. Branche **`sprint-artefacts`**, issue de `main` @ `b8380d9` (Index des fichiers fusionné). Commits non poussés.
> Le modèle rédige, le moteur produit et rend compte : `tools/documents.py` (déterministe), `core/artefacts.py` (orchestration).

---

## Tableau de tête

### AR1 — Fenêtres homonymes, avant / après (rejeu réel, « AtlasEssai Rapport A » et « B »)

| Demande | Avant (code de `main`) | Après (ce sprint) |
|---|---|---|
| « ferme AtlasEssai Rapport » | confirmation sur « atlasessai rapport » ; acceptée → **B fermée**, la première trouvée | « Plusieurs fenêtres correspondent… 1. « AtlasEssai Rapport B » (python.exe) 2. « AtlasEssai Rapport A » (python.exe). Laquelle ? » — **rien n'est fermé** |
| « ferme AtlasEssai Rapport B » | confirmation sur « atlasessai rapport b » ; B fermée | confirmation qui montre **« AtlasEssai Rapport B » (python.exe)** ; acceptée → **seule B** est fermée |
| « réduis AtlasEssai Rapport » | **B réduite**, au hasard | « Laquelle ? » — rien n'est réduit |
| « réduis AtlasEssai Rapport A » | A réduite | A réduite (par son hwnd) |

### Banc de 6 demandes réelles (modèle local `qwen2.5:7b`, Word et PDF produits, relus)

| # | Demande | Temps | Pages (PDF) | Structure | Faits inventés détectés |
|---|---|---|---|---|---|
| 1 | rapport : la photosynthèse | 33,1 s | 3 | valide, 6 sections | — (rapport) |
| 2 | rapport : l'histoire de l'imprimerie | 29,6 s | 2 | valide, 6 sections | — |
| 3 | rapport : les énergies renouvelables en France | 32,5 s | 3 | valide, 6 sections | — |
| 4 | résumé : rapport de stage (test, 1 015 caractères) | 11,5 s | 1 | valide, 3 sections | 0 |
| 5 | résumé : notes de réunion (test, 696 caractères) | 9,8 s | 1 | valide, 4 sections | **2** (retirées) |
| 6 | résumé : document **long** (test, 43 371 caractères, 8 morceaux, plus grand que le contexte) | 59,5 s | 1 | valide, 3 sections | 0 |

**Sur les 10 résumés mesurés** (4, 3 et 3 sur les trois documents de test) :
- **2 faits inventés détectés**, tous deux dans un résumé de la réunion : « 20 novembre 2026 », alors que la source dit seulement « le 20 novembre » (l'année a été ajoutée). Les 2 phrases ont été retirées.
- **0 fait absent de la source** dans les 10 documents livrés (second contrôle).

Les rapports du banc ont été écrits avant d'allonger les sections (2 à 3 pages). Avec la consigne actuelle, le rapport du rejeu réel fait **environ 4 pages en 51 s**.

### Les deux documents laissés à Alexis pour qu'il les juge (dans `Documents\Atlas\`)

1. **`L'intelligence artificielle dans la vie quotidienne impacts - 2026-10-17.docx`** : rapport.
   - « fais-moi un rapport sur l'intelligence artificielle dans la vie quotidienne » ;
   - annoncé « environ 49 secondes », prêt en 51 s ;
   - 6 sections, environ 4 pages, ouvert par Atlas.
2. **`Stage chez Nexalia - 2026-10-17.docx`** : résumé du document de test « AtlasEssai rapport de stage.docx » (fictif), trouvé par l'index.
   - « résume mon rapport de stage AtlasEssai dans un Word » ;
   - prêt en 9 s, ouvert par Atlas.

**À Alexis de dire s'ils sont présentables pour la démo.**

---

## 1. Résumé exécutif

**Statut global : VALIDÉ** (sous réserve du jugement d'Alexis sur les deux documents).

**Runtime :**
- Ollama 0.40.5, `qwen2.5:7b`, `num_ctx` 8 192 ;
- python-docx 1.2.0 et fpdf2 2.8.9 ajoutés, sans Word ni LibreOffice requis ;
- mémoire réelle, journal et habitudes inchangés (§6.4).

**Chiffres :**
- **AR1 :** fermer, réduire, agrandir et ancrer agissent sur la fenêtre exacte. Des homonymes donnent une question, la confirmation montre le titre exact et le programme. Les recherches par morceau de nom du §4.6 d'Index sont corrigées (§4.1).
- **AR2 :** rapports, résumés et comptes rendus, en Word, en PDF ou les deux.
  - rangés dans `Documents\Atlas`, sans écrasement ;
  - relus avant « j'ai créé », puis ouverts et indexés ;
  - l'attente est annoncée dès la réponse, et la fin par la fenêtre, une notification et la voix.
- **AR3 :** le contrôle « rien d'inventé » est mesuré sur 10 résumés réels.
- **Corpus de routes :** **332 / 333 (99,7 %)**, 0 action à tort, dont 34 demandes d'artefact (34 / 34) et 12 négatifs.
- **GB1 :** 0 / 34, identique au sprint précédent.
- **Suites :** avec Ollama **1 282 passés, 0 ignoré** ; sans Ollama **1 279 passés, 3 ignorés justifiés**.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| AR0 — base, suite verte | `main` = Index des fichiers fusionné, plus le brief. | PASS |
| AR1 — fermer, réduire, agrandir, ancrer : fenêtre résolue avant la confirmation, homonymes → question, confirmation avec le titre exact et le programme, ce hwnd fermé | Rouge d'abord (5 échecs, 6 erreurs). Réel : tableau de tête. Avant d'agir sur un hwnd, la fenêtre est revérifiée : si elle a changé de titre ou n'existe plus, rien n'est fait. | PASS |
| AR1 — `find_window`, `take_window_screenshot`, `_focus_and_verify` | Fenêtres correspondantes ; capture de la fenêtre résolue ; vérification du premier plan par hwnd (sinon le titre exact). | PASS |
| AR1 — grounding sur la fenêtre résolue, `title_re` échappé | `_find_candidate_windows` : la fenêtre résolue ; des homonymes ne passent que si l'un est au premier plan, sinon « précise laquelle », aucun clic. `_try_uia` : `window(handle=…)`, sinon `re.escape`. | PASS |
| AR1 — `_is_app_running`, `apparu_depuis` : nom de processus exact | `steamwebhelper.exe` ne fait plus croire Steam lancé. Testé (5 cas). | PASS |
| AR1 — test rouge des deux fenêtres, rejeu réel | Tests et rejeu (tableau de tête). | PASS |
| AR2.1 — reconnaître la demande, mot de document requis ; corpus ≥ 30 et 10 négatifs | 34 demandes et 12 négatifs, 99,7 %, 0 à tort. « résume-moi la révolution française » reste une conversation. | PASS |
| AR2.2 — informations manquantes demandées | Sujet d'un rapport ; fichier à résumer (absent → « aucun fichier », ambigu → « lequel ? ») ; date et participants d'un compte rendu. Testé, et vu en réel (compte rendu). | PASS |
| AR2.3 — contenu structuré validé, une nouvelle tentative, puis l'échec dit | JSON imposé par schéma (Ollama `format`). `valider_contenu` vérifie champs, longueurs et français. Une nouvelle tentative avec la raison, puis « Je n'ai pas pu… Aucun fichier n'a été créé ». | PASS |
| AR2.4 — documents longs section par section ; temps d'un rapport de 3 à 5 pages | Plan, puis un appel par section. Réel : environ 4 pages en 51 s. | PASS |
| AR2.5 — résumé d'un fichier, découpage, synthèse | Texte extrait comme l'index, morceaux de 6 000 caractères coupés aux paragraphes, points par morceau, puis synthèse. Mesuré sur 43 371 caractères (8 morceaux). | PASS |
| AR2.6 — Word (styles, sommaire, listes, pied) ; PDF (accents, titres, numéros) ; formats | Word : `Title`, `Heading 1`, champ `TOC`, `List Bullet`, pied de page avec champ `PAGE`. PDF : Arial de Windows (accents, `œ`, `—`), signets, « Page n/N ». Word par défaut, PDF, ou les deux. | PASS |
| AR2.7 — rangement, jamais d'écrasement, indexé tout de suite | `Documents\Atlas\<titre court> - <date>.docx`, puis ` (2)`… Le dossier Documents réel est lu dans le registre. `indexer_un_fichier`. | PASS |
| AR2.8 — ouverture après vérification ; dit où | Testé ; réel (les deux documents se sont ouverts). | PASS |
| AR3 — contrôle « rien d'inventé », mesuré sur ≥ 10 résumés ; un fait absent n'est pas livré tel quel | 10 résumés : 2 détections, phrases **retirées** et dites (« J'ai retiré N phrases… »). Choix justifié au §4.3. | PASS |
| AR3 — banc de 6 demandes | Tableau de tête. | PASS |
| AR3 — deux documents laissés à Alexis | Tableau de tête. | PASS |
| AR3 — GB1 0 / 34 ; jamais « j'ai créé » sur un échec | GB1 identique. « J'ai créé » n'est écrit que par le moteur, après relecture (tests d'échec : contenu invalide, fichier vide, bibliothèque absente). | PASS |
| AR4 — versions fixes, `doctor.py --composants`, bascule ; sans Word ni LibreOffice | `python-docx==1.2.0`, `fpdf2==2.8.9`. Deux lignes dans `--composants`. Bascule `documents` dite (testée). | PASS |
| AR5 — rapport, suites, corpus, C3 | Ce document. | PASS |

---

## 3. Architecture projet mise à jour

```
api/routes.py                     GET /api/annonces
config/settings.json              (inchangé)
core/
  annonces.py                     ← NOUVEAU : ce qu'Atlas annonce de lui-même (fenêtre, notification, voix)
  artefacts.py                    ← NOUVEAU : demander ce qui manque, rédiger (plan, sections, morceaux), produire, annoncer
  file_indexer.py                 indexer_un_fichier
  intent_classifier.py            _regles_artefacts (en premier) ; « ferme la fenêtre #hwnd »
  intent_engine.py                fenêtre résolue avant la confirmation (fermer, réduire, agrandir) ; artefact_creer
  propositions.py                 un complément de texte libre (« sur quel sujet ? »)
  validator.py                    route artefact ; processus exacts ; vérification du premier plan sur LA fenêtre
core_conversational/degradations.py   bascule « documents »
desktop/atlas_desktop.py          relève /api/annonces
requirements.txt                  python-docx==1.2.0, fpdf2==2.8.9
scripts/
  doctor.py                       --composants : python-docx, fpdf2
  banc_artefacts.py               ← NOUVEAU
  rejeu_artefacts.py              ← NOUVEAU
  rejeu_fenetres.py               ← NOUVEAU
tools/
  documents.py                    ← NOUVEAU : valider, Word, PDF, relire, ranger, rien d'inventé
  window_controller.py            fenetres_correspondantes, _cible_exacte, _agir_sur_hwnd ; plus de « titre qui contient »
  grounding.py                    fenêtre résolue ; title_re échappé
  app_launcher.py                 apparu_depuis : processus exact
tests/
  test_artefacts.py               ← NOUVEAU (48 tests)
  fixtures/corpus_routes.json     +43
  conftest.py                     aucune notification Windows pendant les tests
  test_action_safety_b1_bis.py, test_apprentissage.py, test_index_fichiers.py   doubles adaptés (§5.3)
```

---

## 4. Détail des implémentations

### 4.1 AR1 — la fenêtre exacte

- **`fenetres_correspondantes(nom)`** (`window_controller`) : même règle que `resolve_app_window` (GB4). Le titre exact unique l'emporte ; sinon, les fenêtres dont le titre contient le nom ou dont le programme porte ce nom. « #123 » désigne un hwnd (choix dans une liste).
- **Moteur :** pour `window_close`, `window_minimize` et `window_maximize`, la fenêtre est résolue **avant** la confirmation :
  - plusieurs → la question et un choix (« la 2 » → « ferme la fenêtre #202 ») ;
  - une → `title`, `hwnd` et `processus` sont figés dans les paramètres, et la confirmation affiche « « titre » (programme) ».
- **Outils :** `_cible_exacte` revérifie la fenêtre au moment d'agir (encore ouverte, même titre), puis `_agir_sur_hwnd` (WM_CLOSE, SW_MINIMIZE, SW_MAXIMIZE, MoveWindow). `window_snap` refuse des homonymes.
- **Défaut trouvé en chemin :** la vérification « fenêtre visible » après « mets X au premier plan » cherchait la cible de l'intention, souvent **vide**. Une recherche vide renvoyait toutes les fenêtres, donc la vérification était toujours vraie. Elle porte maintenant sur le titre nommé.

### 4.2 AR2 — rédiger et produire

- **Classifieur** (`_regles_artefacts`, placé en tête, car « écris un rapport sur… » partait en frappe dans une fenêtre) :
  - il faut un mot de document ; « dossier » et « note de synthèse » n'en sont pas (brief) : conversation ;
  - formats retirés de la phrase (« en PDF », « dans un Word et en PDF ») ;
  - trois formes : résumé (source si la cible ressemble à un fichier, sinon un rapport sur ce sujet), rapport ou document, compte rendu.
- **`core/artefacts.creer`** :
  - ce qui manque → une question, et la réponse complète la demande (`propositions.completer`) ;
  - sinon, le travail part dans un fil, et la réponse dit tout de suite « Je rédige …, environ N secondes ». Estimation mesurée : 7 s par section, 6 s par morceau ; réel 49 / 51 s et 13 / 9 s ;
  - un seul travail à la fois.
- **Rédaction :**
  - rapport : plan (schéma), puis chaque section séparément ;
  - résumé : points factuels par morceau, puis synthèse ;
  - compte rendu : idem, plus une section « Date et participants » écrite **depuis la réponse d'Alexis**, pas par le modèle ;
  - une seule nouvelle tentative avec la raison de l'invalidité.
- **`produire`** : écriture, relecture `verifier_fichier` (existe, non vide, se relit, contient du texte et des titres), indexation, puis ouverture. L'annonce ne dit « J'ai créé « titre » : chemin » qu'**après** cette relecture.

### 4.3 AR3 — rien d'inventé

- **`faits_absents(résumé, source)`** :
  - **dates** (jour, mois, année facultative) cherchées telles quelles dans la source ;
  - **nombres**, normalisés (« 12 000 » = « 12000 », « 15 % » = 15) ;
  - **noms propres** (mots à majuscule hors début de phrase, hors civilités et mots-outils), sans accents ni casse.
- **`retirer_faits_inventes`** retire chaque **phrase** qui cite un fait absent, ou chaque point. Un titre inventé devient « Résumé ».
- **Pourquoi retirer plutôt que signaler :** un document qu'Alexis présente ne doit pas contenir de fait faux, même balisé. Atlas dit combien de phrases il a retirées (« J'ai retiré 1 phrase qui citait des éléments absents du document source »).

### 4.4 Fichiers

- **Word :** police Calibri, langue fr-FR, titre `Title`, sections `Heading 1`, champ `TOC \o "1-2"` (avec `updateFields` : Word le calcule à l'ouverture), listes `List Bullet`, pied de page avec champ `PAGE`.
- **PDF (fpdf2) :** Arial, Arial gras et italique de `C:\Windows\Fonts` pour les accents. Sans ces polices, repli latin-1. Signets par section, pied « … — Page n/N ».
- **Choix de fpdf2 :** pur Python, léger, et il produit les accents avec les polices de Windows. reportlab ferait de même, mais il est bien plus lourd.

---

## 5. Résultats des tests

### 5.1 Suites complètes (code final)

```
.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider
```

| Contexte | Résultat | Code |
|---|---|---|
| Ollama 0.40.5 lancé | **1 282 passed in 373.52s**, « tests ignorés : 0 » | 0 |
| Ollama arrêté (API muette vérifiée) | **1 279 passed, 3 skipped in 396.18s**, les 3 justifiés habituels | 0 |

Ollama a été relancé ensuite ; il répond en 0.40.5.

### 5.2 Mesures

| Mesure | Résultat |
|---|---|
| Corpus de routes | **332 / 333 — 99,7 %**, 0 action à tort ; artefacts 34 / 34 ; seul écart : l'horoscope, connu depuis Fiabilité |
| GB1 | 0 affirmation sur 34, 0 différence avec Index ; 0 question ordinaire bloquée ; aucune réponse ne dit « j'ai créé » |
| Banc | `scripts/banc_artefacts.py` (tableau de tête) |
| Rejeux réels | `scripts/rejeu_fenetres.py` (avant : worktree de `main`), `scripts/rejeu_artefacts.py` |

### 5.3 Rouge d'abord, et tests modifiés

**Rouges d'abord :**
- AR1 : 5 échecs et 6 erreurs ;
- moteur de documents (AR2, AR3) : 10 échecs ;
- orchestration : 6 échecs et 11 erreurs (les négatifs passaient déjà) ;
- bascule « documents » : écrite avant l'interception d'`ImportError`, elle a passé une fois celle-ci ajoutée.

**Tests existants adaptés :**
- `test_action_safety_b1_bis.FakeDesktop` : son faux `focus_window` rend maintenant le titre exact, comme le vrai. La vérification ne se contente plus d'« un alias contenu dans le titre ».
- `test_apprentissage` : deux doubles ajoutent leur fenêtre simulée à la liste des fenêtres, car la vérification « fenêtre visible » regarde vraiment la liste (le défaut de la cible vide est corrigé, §4.1).
- `test_index_fichiers::test_ix4_fenetre_fermee…` : même propriété (le titre est rendu), mais avec le nouveau mécanisme (fenêtre résolue, hwnd).
- Dans `test_artefacts` lui-même : le faux modèle du test long répond selon la consigne, et la synthèse simulée est assez longue pour la validation.

---

## 6. Comportement observé en scénarios utilisateur réels

### 6.1 AR1

Voir le tableau de tête.

```
python scripts/rejeu_fenetres.py --out … [--racine <worktree de main>]
```

Arrêts propres ; fenêtres de test refermées.

### 6.2 Documents, par Atlas réel

```
python scripts/rejeu_artefacts.py --out …
```

| ID | Commande | Réponse immédiate | Annonce de fin | Statut |
|---|---|---|---|---|
| D1 | « fais-moi un rapport sur l'intelligence artificielle dans la vie quotidienne » | « Je rédige le rapport sur … (Word), environ 49 secondes. Je te préviens quand il est prêt, et je l'ouvre. » (0,3 s) | « J'ai créé « L'intelligence artificielle dans la vie quotidienne : impacts et perspectives » : …\Documents\Atlas\…docx. Je l'ouvre. (49 s) » ; ouvert | PASS |
| D2 | « résume mon rapport de stage AtlasEssai dans un Word » | « Je rédige le résumé de « AtlasEssai rapport de stage.docx » (Word), environ 13 secondes… » | « J'ai créé « Stage chez Nexalia » : …. Je l'ouvre. (8 s) » ; ouvert | PASS |
| D3 | « rédige un compte rendu de mes notes de réunion AtlasEssai » | « Pour le compte rendu : quelle était la date, et qui participait ? Je ne veux pas l'inventer. » | — | PASS |
| D4 | « laisse tomber » | « D'accord, je n'y touche pas. » ; rien n'est rédigé | — | PASS |

L'index a vu le document de test en 613 s : c'est le passage incrémental de démarrage, à 25 % d'un cœur. Les deux documents produits sont dans l'index. Le document source de test est supprimé et sorti de l'index : il reste 0 entrée « AtlasEssai ».

### 6.3 Relecture humaine de trois résumés du banc (au-delà du contrôle automatique)

- **Les noms, dates et chiffres sont justes** (Nexalia, Lyon, 12 personnes, 27 %, 8 500 euros ; 80 %, 45 000 sur 60 000, 2 décembre 2026 ; les chapitres du document long).
- **Glissements non détectés :**
  - « Sofia Benali le relance cette semaine » devient « a relancé » (le temps change) ;
  - « un serveur de test » devient « l'acquisition d'un serveur de test » ;
  - le résumé de la réunion omet les décisions et les actions.
- Ce sont les limites du contrôle (§7, risque 1).

### 6.4 Règle C3

| Élément | Avant | Après |
|---|---|---|
| Mémoire (memory_e5 / memory / errors / conversations / documents) | 276 / 489 / 20 / 19 / 8 | identique |
| `data/habits.db` | 142 lignes | 142 lignes (les rejeux écrivent dans une copie) |
| `data/atlas_actions.jsonl` | 757 lignes | 757 lignes |
| `data/apprentissage.db` | absent | absent |
| `Documents\Atlas` | n'existait pas | **les 2 documents laissés à Alexis**, rien d'autre |
| Documents de test du banc (13 × Word et PDF) | — | produits dans un dossier temporaire, **supprimés** |
| Document source de test du rejeu | — | supprimé ; sorti de l'index |

---

## 7. Limites et risques identifiés

1. **Le contrôle « rien d'inventé » ne voit que les nombres, les dates et les noms propres.**
   - Sévérité : **Moyen**.
   - Un changement de sens (temps d'un verbe, « acquisition ») ou une omission (décisions absentes) passe. Un nom propre en début de phrase n'est pas contrôlé.
   - Mitigation : le pied de page dit « à relire » ; contrôler aussi les verbes d'action ; demander au modèle les décisions et actions par une consigne dédiée pour les comptes rendus.
2. **Le contrôle est strict sur les dates.**
   - Sévérité : **Faible**.
   - Les 2 détections du banc sont une année ajoutée à « 20 novembre ». La phrase, plausible, a été retirée. C'est voulu : mieux vaut perdre une phrase qu'inventer.
3. **Un rapport vient d'un modèle 7B local.**
   - Sévérité : **Moyen**.
   - Le français est parfois approximatif (« la Cyclicale ») et des affirmations peuvent être fausses. Le pied de page le dit. C'est à Alexis de juger les deux documents.
4. **La fenêtre web (`ui/app.js`) ne relève pas `/api/annonces`.**
   - Sévérité : **Faible**.
   - La fin d'un document y passe par la notification Windows seulement. La fenêtre de bureau et la voix l'annoncent.
5. **Les informations connues par la mémoire ne sont pas encore utilisées** (« s'il le sait par sa mémoire, il peut s'en servir »).
   - Sévérité : **Faible**.
   - Atlas demande toujours : rien n'est inventé, mais il peut redemander ce qu'il sait déjà.
6. **Le sommaire Word se met à jour à l'ouverture.**
   - Sévérité : **Faible**.
   - Word demande s'il faut mettre à jour les champs ; sinon, le texte provisoire explique comment faire.
7. **Grounding avec des homonymes dont aucun n'est au premier plan :** Atlas ne clique pas et demande de préciser.
   - Sévérité : **Faible**. C'est un changement de comportement voulu.
8. **Un seul document à la fois.**
   - Sévérité : **Faible**. Le deuxième demandé reçoit « je rédige déjà … ».
9. **Annonce vocale de fin non rejouée au micro.**
   - Sévérité : **Faible**.
   - `_speak_sync` n'est appelé que si la demande venait de la voix et que le moteur vocal tourne.

---

## 8. Checklist de validation

- [x] Fermer, réduire, agrandir, ancrer : sur la fenêtre exacte ; homonymes → question ; confirmation qui montre le titre exact ; rejeu réel (tableau de tête)
- [x] `title_re` échappé ; noms de processus exacts (§4.1, tests AR1)
- [x] Rapports structurés et résumés produits en Word et en PDF, rangés sans écrasement, ouverts, indexés (§6.2, tests AR2)
- [x] « J'ai créé » dit seulement après vérification du fichier (tests d'échec, §4.2)
- [x] Informations manquantes demandées, jamais inventées (D3, tests AR2)
- [x] Contrôle « rien d'inventé » sur les résumés, mesuré sur au moins 10 résumés (tableau de tête)
- [x] Banc de 6 demandes ; 2 documents laissés à Alexis (tableau de tête)
- [x] Corpus ≥ 99,7 %, 0 action à tort ; GB1 à 0 (§5.2)
- [x] Dépendances fixées, visibles dans `doctor.py --composants`, sans Word ni LibreOffice requis (AR4)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5.1)

---

## 9. Recommandations pour le sprint suivant

**À faire par Alexis :** ouvrir les deux documents de `Documents\Atlas` et dire s'ils sont présentables pour la démo.

**P1 — fiabilité**
- Contrôle des faits au-delà des nombres, dates et noms : verbes d'action et temps, noms en début de phrase (risque 1).
- Comptes rendus : consigne dédiée « décisions » et « actions » (risque 1).

**P2 — robustesse**
- La fenêtre web relève `/api/annonces` (risque 4).
- Se servir des faits retenus (« retiens que… ») pour ne pas redemander (risque 5).

**P3 — qualité**
- Lettres, listes, Excel, présentations, HTML (décision d'Alexis : plus tard).
- Relecture du français des rapports, par exemple une passe de correction.

**Hors du brief, ajouté et justifié :**
- `/api/annonces` et `core/annonces.py`, nécessaires : la fenêtre attend 60 s au plus une réponse, un rapport en prend 50 ;
- la correction de la vérification « fenêtre visible » à cible vide (§4.1).
