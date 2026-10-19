# RAPPORT SPRINT — BANC DE MODÈLES : quel modèle pour Atlas, sur 8 Go et en dessous ?
Date: 19/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_BANC_MODELES.md`. Branche **`sprint-banc-modeles`**, issue de `main` @ `081a09f` (Compétences 1 fusionné, plus le brief). Commit non poussé.
> Sprint de **mesure** : Atlas ne change pas de modèle (`config/settings.json` : toujours `qwen2.5:7b`). Le banc passe le modèle par `ATLAS_MODELE`. La décision revient à une Réunion Atlas, puis à Alexis.

---

## Tableau de tête — un modèle par ligne

Mesuré sur le PC d'Alexis : i5-10400F, RTX 8 Go (8 151 Mo), num_ctx 8 192, transcription faster-whisper « base » chargée sur le GPU comme dans Atlas (≈ 1,3 Go avec le bureau). Tous les modèles en **Q4_K_M** (niveau par défaut d'Ollama), tous sous **licence Apache 2.0** (fichier de licence du manifeste Ollama, relu le 19/10). Réflexion coupée (`think: false`) pour les 8 modèles qui l'ont.

| Modèle | Palier | VRAM réelle | Sur la carte | Jetons/s | 1er mot (chaud) | GB1 (affirm. / bloquées) | Plans JSON / validés | Documents (1er coup) | Faits inventés | Consignes | Conversation FR / autre écriture / s | Processeur seul | **Aveugle** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `qwen2.5:7b` (actuel) | std | 4,75 Go | 100 % | 74,1 | 0,36 s | 0 / 0 | 100 / 80 % | 6/6 (97 %) | 0 | 11/12 | 20/20 / **1** / 2,1 s | — | **2,67** |
| `qwen3:8b` | std | 5,92 Go | 100 % | 70,1 | 0,36 s | 0 / 0 | 100 / **90 %** | 6/6 (100 %) | 0 | **12/12** | 20/20 / 0 / 2,9 s | — | **3,67** |
| `qwen3.5:9b` | std | 5,65 Go | **85 %** | 27,2 | 0,73 s | 0 / 0 | 100 / 80 % | 6/6 (97 %) | 0 | **12/12** | 20/20 / 0 / 9,0 s | — | **4,00** |
| `granite4.2:8b` | std | 5,95 Go | 91 % | 37,6 | 0,47 s | 0 / 0 | 80 / 70 % | 6/6 (100 %) | 0 | 11/12 | 20/20 / 0 / 11,3 s | — | **3,00** |
| `ministral-3:8b` | std | 5,92 Go | 82 % | **12,6** | 0,73 s | 0 / 0 | 100 / 75 % | 6/6 (97 %) | 0 | 11/12 | 20/20 / 0 / **33,2 s** | — | non présélectionné |
| `gemma4:e4b` | léger | 4,64 Go | 100 % | 99,4 | **6,8 s** (§7) | 0 / 0 | 100 / 75 % | 6/6 (100 %) | 0 | 11/12 | 20/20 / 0 / 3,9 s | **15,1 j/s, 11,6 s** | **3,33** |
| `granite4.2:3b` | léger | 2,84 Go | 100 % | **128,4** | 0,35 s | 0 / 0 | 100 / 80 % | 6/6 (100 %) | 0 | 10/12 | 20/20 / 0 / 2,1 s | 9,0 j/s, 5,9 s | **2,67** |
| `qwen3.5:4b` | léger | 3,90 Go | 100 % | 85,9 | 0,49 s | 0 / 0 | 100 / 70 % | 6/6 (100 %) | 0 | 9/12 | 20/20 / 0 / 3,5 s | 5,5 j/s, 8,2 s | non présélectionné |
| `ministral-3:3b` | léger | 3,90 Go | 100 % | 124,2 | 0,36 s | 0 / 0 | 85 / **45 %** | 6/6 (97 %) | 0 | 10/12 | 20/20 / 0 / 3,9 s | 8,3 j/s, 14,1 s | non présélectionné |
| `qwen3:4b` | léger | 3,85 Go | 100 % | 104,5 | 0,53 s | 0 / 0 | **0 / 0 %** | 6/6 (100 %) | 0 | **4/12** | **1/20** / 0 / 9,5 s | 7,0 j/s, 28,8 s | **disqualifié** (réflexion qui fuit) |

**Note à l'aveugle** : moyenne de 3 productions notées de 1 à 5 par Alexis (conversation / section de rapport / résumé), sans savoir de quel modèle elles venaient :
- `qwen3.5:9b` 4 / 5 / 3 ;
- `qwen3:8b` **5** / 3 / 3 ;
- `gemma4:e4b` 4 / 4 / 2 ;
- `granite4.2:8b` 4 / 3 / 2 ;
- `granite4.2:3b` 2 / 2 / 4 ;
- `qwen2.5:7b` **1** (bascule en chinois) / 2 / **5**.

### Recommandation (pour la Réunion Atlas)

- **Palier standard (8 Go) : `qwen3:8b`.** Meilleur partout aux mesures et 2e à l'aveugle ; il tient entièrement sur la carte avec la transcription.
  - **Gagné** par rapport à `qwen2.5:7b` :
    - aucune bascule en chinois (0/20 contre 1/20 ; conversation notée 5 contre 1) ;
    - plans validés 90 % contre 80 % ;
    - documents valides du premier coup 100 % contre 97 % ;
    - consignes 12/12 contre 11/12 ;
    - rapport en **50 s** contre 117 s.
  - **Perdu** :
    - +1,2 Go de VRAM (5,9 contre 4,75 Go) : il reste environ 1 Go libre sur une carte de 8 Go ;
    - un résumé noté 3 contre 5 ;
    - conversation un peu plus lente (2,9 s contre 2,1 s) ;
    - 5,2 Go à télécharger.
- **Option pour une carte de plus de 8 Go : `qwen3.5:9b`**, le mieux noté à l'aveugle (4,0) et 12/12 aux consignes. Sur 8 Go, il déborde (85 % sur la carte, 27 jetons/s, 9 s par réponse) : écarté pour ce palier.
- **Palier léger (moins de 8 Go, ou sans NVIDIA) : `gemma4:e4b`**, 3e à l'aveugle (devant `granite4.2:3b`).
  - le plus rapide sur le **processeur seul** (15 jetons/s, une réponse courte en 11,6 s) ;
  - 11/12 consignes ; plans validés 75 %.
  - **Réserves** :
    - 4,6 Go de VRAM : il convient aux cartes de 6 Go, pas de 4 ;
    - chargement de 28 s et premier mot à 6,8 s à remesurer (§7) ;
    - un résumé noté 2 (chiffres « gommés », §6.3).
- **Cartes de 4 Go : `granite4.2:3b`, en dernier recours.**
  - le plus petit et le plus rapide (2,8 Go, 128 jetons/s), plans validés 80 % ;
  - mais un français faible à l'aveugle (conversation et rapport notés 2).
- **Écartés :**
  - `qwen3:4b` : la réflexion fuit malgré `think: false`, en anglais, dans 19 réponses sur 20 ;
  - `ministral-3:8b` : 12,6 jetons/s, soit 33 s par réponse ;
  - `ministral-3:3b` : 45 % de plans validés ;
  - `qwen3.5:4b` : 9/12 consignes ; dominé par `gemma4:e4b` et `granite4.2:3b`.

---

## 1. Résumé exécutif

**Statut global : VALIDÉ** — sprint de mesure ; aucune décision de modèle prise ici.

**Runtime :**
- Ollama 0.40.5 ;
- 9 modèles téléchargés pour le banc (40,7 Go annoncés avant, accord d'Alexis) ;
- Atlas inchangé côté modèle (`qwen2.5:7b`).

**Chiffres :**
- **BM0 :** un seul garde. Seul `main.py`, et seulement sans redirection `ATLAS_*`, peut écrire dans les données réelles. Rouge d'abord : sur `main`, un script sans redirection écrit 4 fichiers dans le dossier réel (simulé) ; avec le garde, 0. 13 tests.
- **BM2 :** 10 modèles × 7 parties, par le code d'Atlas (GB1, planificateur, `core/artefacts.py`, consigne de conversation).
  - GB1 parfait pour les 10 (0 affirmation, 0 question bloquée) ;
  - aucun fait inventé dans les documents livrés ;
  - 1 modèle disqualifié (réflexion qui fuit).
- **BM3 :** 18 productions notées à l'aveugle par Alexis (6 modèles × 3) ; correspondance gardée hors du dossier, révélée après.
- **Suites :** avec Ollama **1 411 passés, 0 ignoré** ; sans Ollama **1 408 passés, 3 ignorés justifiés**.
- **C3 :** aucune écriture dans `data/` pendant tout le sprint (journal 757, `habits.db` 142, mémoire non ouverte, aucun fichier de `data/` modifié le 19/10).

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| BM0 — seul Atlas (`main.py`) écrit dans les données réelles ; tout autre processus refusé, même sans redirection, erreur claire ; test rouge d'abord | `core/donnees_reelles.py`. Branché sur le journal (atlas_logger, validator), `apprentissage.db`, `rappels.db`, `habits.db`, l'index, la mémoire. Un Atlas d'essai (redirections posées) n'est jamais autorisé. Rouge sur `main` (§5.3). | PASS |
| BM0 — les bancs tournent sous ce garde | GB1, banc O, banc de modèles : copies jetables (`tests/banc_donnees.py`). | PASS |
| BM1 — tags vérifiés, quantification dite | Les 10 existent (manifestes du registre Ollama, 19/10), tous Q4_K_M. | PASS |
| BM1 — réflexion coupée, sans fuite vérifiée | `think: false` pour les 8 modèles qui ont la capacité. Fuites mesurées : **qwen3:4b fuit** (raisonnement en anglais dans la réponse), granite4.2:8b une fois (un plan), les autres 0. | PASS (fuite constatée et dite) |
| BM1 — bonsai-2 noté, pas intégré | Présent au registre (`bonsai-2:latest`, famille qwen35, 9 B, quantification **Q2_0** ternaire, 3,18 Go, fichier de licence Apache 2.0). Aucune source officielle de son éditeur cherchée ni trouvée : pas intégré. | PASS |
| BM1 — licences et implications | Toutes Apache 2.0 (§4.4). | PASS |
| BM1 — taille annoncée avant ; 20 Go libres gardés ; qwen2.5:7b et minicpm-v gardés | 40,7 Go annoncés, accord d'Alexis ; 124 → 78,9 Go libres ; les deux gardés. | PASS |
| BM2.1 — ressources (VRAM, GPU/CPU, RAM, chargement, 1er mot, jetons/s) avec la transcription | Tableau de tête. VRAM réelle prise sur la carte (nvidia-smi) : le chiffre d'Ollama est faux pour gemma4 (0,37 Go annoncés, 4,64 réels). | PASS |
| BM2.2 — GB1 avec le vrai modèle, 0 affirmation non relue, 0 question bloquée | Les 10 : 0 et 0 (12/34 actions outillées, 0 annonce ≠ relu). | PASS |
| BM2.3 — ≥ 20 plans : JSON valide, étapes validées | 20 demandes composées, planificateur d'Atlas. | PASS |
| BM2.4 — documents : 3 rapports, 3 résumés (dont le long) ; 1er coup, temps, faits inventés | 6/6 pour les 10 ; 0 fait inventé détecté. | PASS |
| BM2.5 — ≥ 10 consignes vérifiables par programme | 12 consignes (§4.3). | PASS |
| BM2.6 — 20 questions : langue, longueur, temps | Tableau de tête. Seul `qwen2.5:7b` bascule en chinois (1/20, garde L7-7 d'Atlas mis à part). | PASS |
| BM2 — palier léger sur le processeur seul | `num_gpu 0`, une réponse courte, pour les 5 légers. | PASS |
| BM3 — présélection (3 std + 2 légers + qwen2.5:7b) ; 3 tâches ; dossier anonymisé ; grille ; ≤ 18 ; correspondance hors du dossier, révélée après | `qwen3:8b`, `qwen3.5:9b`, `granite4.2:8b` ; `gemma4:e4b`, `granite4.2:3b` ; `qwen2.5:7b`. `Documents\Atlas\Banc_aveugle\` (18 + grille + document source). Notes : tableau de tête. | PASS |
| BM4 — tableau de tête, recommandation pour les deux paliers, aucun changement de modèle | Ci-dessus. `settings.json` : `qwen2.5:7b`. | PASS |
| BM4 — suites code 0 avec et sans Ollama ; garde testé ; C3 ; rapport | §5, §6.4. | PASS |

---

## 3. Architecture projet mise à jour

```
core/
  donnees_reelles.py              ← NOUVEAU : le garde unique (autoriser_atlas, verifier_ecriture, lecture_seule)
  atlas_logger.py                 journal : garde
  validator.py                    journal des automatisations bloquées : garde
  apprentissage_store.py          _connexion(ecriture) : lecture seule hors d'Atlas, écritures refusées
  rappels.py                      idem
  context_monitor.py              habits.db : garde
  file_indexer.py                 index : lecture seule hors d'Atlas ; passage, ajout, oubli refusés
  memory_manager.py               la vraie mémoire n'est ouverte que par Atlas (même avec ATLAS_MEMORY=real)
  ollama_client.py                ATLAS_MODELE, ATLAS_MODELE_REFLEXION, champs_modele()
  artefacts.py                    champs_modele()
tools/web_reader.py               champs_modele()
main.py                           autoriser_atlas() au lancement seulement
scripts/
  banc_modeles.py                 ← NOUVEAU : le banc (un processus par modèle)
  banc_aveugle.py                 ← NOUVEAU : préparer / révéler l'évaluation à l'aveugle
tests/
  banc_donnees.py                 ← NOUVEAU : copies jetables pour les bancs
  test_banc_modeles.py            ← NOUVEAU : 15 tests (BM0, BM3)
  gb1_mesure.py, o_mesure_ollama.py   sur des copies
  test_confirmation_f.py          isolé des vraies fenêtres (§5.4)
```

---

## 4. Détail des implémentations

### 4.1 BM0 — `core/donnees_reelles.py`
- `DOSSIER` = `data/` du projet. `autoriser_atlas()` (appelé par `main.py` dans `__main__`, avant `uvicorn.run`) pose `ATLAS_DONNEES=reelles` **sauf** si une redirection `ATLAS_*` est posée : un rejeu qui en oublie une n'écrit pas pour autant dans les vraies données. Importer `main` (tests) n'autorise rien.
- `verifier_ecriture(chemin, quoi)` lève `DonneesReellesInterdites` (message : quoi, où, comment travailler sur une copie) ; `lecture_seule(chemin)` ouvre un SQLite réel existant en `mode=ro` (ni création, ni verrou).
- Branchements :
  - journal (`log_action`, `log_orchestration_step`, automatisations bloquées) ;
  - `apprentissage.db` et `rappels.db` (lectures possibles, écritures refusées, rendues comme `Indisponible` pour l'apprentissage) ;
  - `habits.db` ;
  - index (lecture seule ; passage, ajout et oubli refusés) ;
  - mémoire : `ATLAS_MEMORY=real` ne suffit plus, la vraie base n'est ouverte que par Atlas.
- **Hors du garde, à dessein** : les outils de maintenance (`backup_memory`, `memory_cleanup`, `memory_inventory`, `reencode_memory`, `retirer_collections_vides`, `nettoyer_journal`) ouvrent leurs propres accès et exigent `--oui` / `--yes`. À valider par le superviseur (§9).

### 4.2 Le banc — `scripts/banc_modeles.py`
- Un processus par modèle (`ATLAS_MODELE` lu à l'import de `ollama_client`) ; réflexion coupée si `/api/show` annonce la capacité « thinking ». Tout décharger entre deux modèles.
- **Ressources** : un appel à froid (chargement, premier mot), un à chaud (premier mot, jetons/s) ; `/api/ps` et `nvidia-smi` avant/après.
- **GB1** : `tests/gb1_mesure.py` tel quel (matériel simulé, mémoire copiée).
- **Plans** : 20 demandes composées → `get_planner().plan()` ; JSON valide = plan lu ; plan validé = chaque étape résolue par le validateur, non refusée, vers un outil du moteur.
- **Documents** : `rediger_rapport` / `rediger_resume` d'Atlas, avec un compteur du « premier coup » sur chaque appel `_essayer`.
- **Consignes et conversation** : la consigne de conversation d'Atlas (`_chat_full_raw`, sans le garde linguistique de `chat_full`, pour mesurer le modèle brut).
- **Processeur** : `num_gpu 0`, une réponse courte.

### 4.3 Les 12 consignes
5 lignes exactement ; 3 parties numérotées ; en anglais ; sans liste ; moins de 120 mots ; première ligne « Titre : … » ; une seule phrase ; exactement 4 puces ; finir par une question ; sans le mot « pluie » ; commencer par « Bonjour » ; un haïku de 3 lignes.

**Limite :** la consigne « en anglais » contredit la consigne d'Atlas (« Répondre en français ») ; elle mesure donc aussi l'obéissance à Atlas. La plupart des modèles répondent en français (compté comme non respecté).

### 4.4 Licences
Les 10 candidats sont sous **Apache 2.0** d'après le fichier de licence de leur manifeste Ollama, `gemma4:e4b` compris (les générations précédentes de Gemma avaient leurs propres conditions). Pour un installeur qui télécharge le modèle chez des proches, puis pour un dépôt public : redistribution et usage commercial permis ; conserver la licence et les notices ; les poids ne sont pas dans le dépôt (téléchargés par Ollama). À faire confirmer sur la fiche de l'éditeur avant le choix final.

### 4.5 BM3 — `scripts/banc_aveugle.py`
- `preparer` : les 18 productions reçoivent chacune une lettre tirée au hasard (aucun lien entre deux productions d'un même modèle), puis sont écrites dans `Documents\Atlas\Banc_aveugle\` avec la grille et le document source du résumé.
- La correspondance est écrite hors de ce dossier (refus sinon, testé) ; aucune production ne nomme son modèle (vérifié).
- `reveler` lit la grille remplie.

---

## 5. Résultats des tests

### 5.1 Suites complètes
```
.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
```
- **Avec Ollama** (premier passage) : **4 failed, 1 407 passed**. Les 4 échecs sont dans `test_confirmation_f.py` (§5.4), qui est corrigé ; ce fichier seul : 22 passed. Passage final (Ollama 0.40.6) : **1 411 passed, 0 ignoré**, code 0, 436 s.
- **Sans Ollama** : premier passage **invalide**, avec 1 408 passed et 3 skipped « fautifs » selon conftest. Ma commande `ollama list`, lancée pendant la suite, avait redémarré Ollama (22 h 32), si bien que la condition « Ollama absent » n'était plus vraie : la vérification CK4 l'a vu. Second passage, Ollama arrêté de bout en bout : **1 408 passed, 3 skipped** (justifiés : les 3 interrogent le vrai Ollama), code 0, 490 s.
- Ollama s'est mis à jour seul en redémarrant (0.40.5 → **0.40.6**) : le banc a tourné en 0.40.5, la suite finale avec Ollama en 0.40.6.
- Nouveau : `tests/test_banc_modeles.py`, **15 tests**.

### 5.2 Le banc
```
.venv\Scripts\python.exe scripts\banc_modeles.py --out <dossier>
.venv\Scripts\python.exe scripts\banc_aveugle.py preparer --banc <dossier> --modeles … --cle <hors du dossier>
.venv\Scripts\python.exe scripts\banc_aveugle.py reveler --cle … --grille …
```
Interrompu une fois à la demande d'Alexis (jeu) après `qwen2.5:7b`. `qwen3.5:9b`, interrompu en cours de route, a été refait en entier.

### 5.3 BM0, rouge d'abord
- Les 13 tests de BM0, joués sur une copie de `main` : 13 rouges (module absent).
- Le même scénario sans le garde, sur `main`, dans un faux dossier : **écrit `apprentissage.db`, `apprentissage.db.lock`, `atlas_actions.jsonl`, `habits.db`**. Avec le garde : 0 fichier.

### 5.4 Trouvé : un test qui dépendait des vraies fenêtres
`test_confirmation_f.py` (4 tests) : depuis AR1, « ferme le bloc-notes » résout la vraie fenêtre avant la confirmation. Un Bloc-notes ouvert chez Alexis changeait la cible attendue. Le test ne passait que si aucun Bloc-notes n'était ouvert (aucune fenêtre fermée : ce n'était qu'une demande de confirmation). Isolé : `fenetres_correspondantes` simulée.

---

## 6. Comportement observé en scénarios utilisateur réels

### 6.1 Le banc, sur le vrai modèle et le vrai PC

| ID | Scénario | Attendu | Observé | Statut |
|---|---|---|---|---|
| R1 | 10 modèles, transcription chargée sur le GPU | mesures comparables | tableau de tête ; la VRAM réelle se lit sur la carte (Ollama se trompe pour gemma4) | PASS |
| R2 | « Tu me conseilles quoi pour mieux dormir ? » (qwen2.5:7b, sans le garde linguistique) | français | la réponse **bascule en chinois** au 3e conseil (L7-7 toujours là) | constaté |
| R3 | les 20 questions, qwen3:4b (réflexion « coupée ») | réponses en français | « Okay, the user is asking… » : il raisonne en anglais dans la réponse, 19 fois sur 20 | constaté (disqualifié) |
| R4 | 20 plans, ministral-3:8b | étapes valides | raccourcis inventés (« Maj », touches absentes) refusés par le validateur | constaté |
| R5 | palier léger, sans GPU | une réponse courte | gemma4:e4b 11,6 s ; granite4.2:3b 5,9 s ; ministral-3:3b 14,1 s ; qwen3.5:4b 8,2 s | PASS |

### 6.2 L'évaluation à l'aveugle par Alexis
18 productions, 20 minutes environ, notées de 1 à 5 ; correspondance révélée après la notation (tableau de tête). Commentaires d'Alexis, résumés :
- conversation : la meilleure (5) « concise, chaque conseil justifié » ;
- rapport : le meilleur (5) « français soigné, contenu riche et nuancé », avec quelques exagérations ;
- résumé : le meilleur (5) « le plus complet et fidèle » ;
- relevé chez plusieurs modèles : coquilles, calques de l'anglais, contresens médicaux, affirmations non étayées.

### 6.3 Trouvé pour « Artefacts sur mesure »
Deux résumés (notés 2) « gomment les chiffres » : « budget fixé à un certain montant », « un établissement spécialisé » au lieu du nom. La consigne de synthèse (« aucun nom, date ou chiffre qui n'y soit pas ») rend certains modèles trop prudents : ils retirent des faits pourtant présents. À régler avec le modèle retenu.

### 6.4 Règle C3
Le garde BM0 a tenu : journal 757 lignes, `habits.db` 142, aucun `apprentissage.db` ni `rappels.db` réels, aucun fichier de `data/` (mémoire comprise) modifié le 19/10. Les copies jetables des bancs sont effacées.

---

## 7. Limites et risques identifiés

| Limite | Sévérité | Mitigation |
|---|---|---|
| Une seule machine (RTX 8 Go, i5-10400F) : le palier léger n'est pas mesuré sur une vraie carte de 4 ou 6 Go, ni sur un vrai PC sans NVIDIA (seulement `num_gpu 0`). | **Élevé** | Mesurer sur le PC du proche de la démo et sur un portable sans NVIDIA. |
| gemma4:e4b : premier mot « à chaud » à 6,8 s et chargement de 28 s, alors que ses réponses font 3,9 s en moyenne ; la cause n'est pas établie (réflexion cachée ? second chargement ?). | Moyen | Remesurer, et vérifier `think` sur gemma4. |
| Les mesures sur processeur des 3 derniers modèles ont pu se faire pendant une vidéo d'Alexis (Firefox autorisé après gemma4) : un peu pessimistes. | Faible | Refaire si l'un d'eux est retenu. |
| Une seule passe par modèle (température d'Atlas) : écarts de quelques points non significatifs (plans, consignes). | Moyen | Plusieurs passes sur les deux finalistes. |
| La consigne « en anglais » mesure aussi l'obéissance à Atlas (§4.3). | Faible | La retirer ou la déplacer dans un banc sans consigne système. |
| Conversation mesurée sans le garde linguistique d'Atlas : le garde réessaierait la réponse en chinois de qwen2.5:7b. | Faible | Dit ; c'est le modèle brut qui est comparé. |
| Licences lues dans les manifestes Ollama, pas sur les fiches des éditeurs. | Moyen | Vérifier avant le choix. |
| Maintenance hors du garde (§4.1). | Moyen | Décision du superviseur. |

---

## 8. Checklist de validation

- [x] Garde unique : aucun processus autre qu'Atlas ne peut écrire dans les données réelles, prouvé par un test (§5.3, `test_banc_modeles.py`)
- [x] Candidats vérifiés sur la bibliothèque, réflexion coupée et sans fuite, licences relevées, taille des téléchargements annoncée avant (§2 ; fuite de qwen3:4b constatée et dite)
- [x] Pour chaque modèle : ressources, GB1, plans, documents, faits inventés, consignes, conversation (tableau de tête)
- [x] Palier léger mesuré aussi sur le processeur seul (R5)
- [x] Évaluation à l'aveugle préparée (18 productions), correspondance hors du dossier, révélée après la notation (§6.2)
- [x] Recommandation pour les deux paliers ; aucun changement de modèle dans Atlas
- [x] Liste des modèles téléchargés pour décision d'Alexis (§9)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5.1)

---

## 9. Recommandations pour le sprint suivant

- **P1** — Réunion Atlas : choisir entre `qwen3:8b` (standard) et le statu quo ; `gemma4:e4b` (léger, 6 Go et sans NVIDIA) ; `granite4.2:3b` (4 Go). Puis « Artefacts sur mesure » sur le modèle retenu (consignes de résumé : §6.3).
- **P1** — Mesurer le palier léger sur une vraie machine sans NVIDIA ou avec 4 à 6 Go de VRAM (le PC de la démo).
- **P2** — gemma4:e4b : comprendre le premier mot à 6,8 s.
- **P2** — Garde BM0 : décider du statut des outils de maintenance (sous le garde avec une autorisation explicite, ou hors du garde comme aujourd'hui).
- **P3** — Plusieurs passes sur les finalistes.

**Modèles téléchargés pour ce banc — à toi, Alexis, de décider lesquels supprimer** (`qwen2.5:7b` et `minicpm-v` gardés, comme demandé) :

| Modèle | Taille | Note |
|---|---|---|
| `qwen3:8b` | 5,2 Go | recommandé (standard) |
| `gemma4:e4b` | 6,6 Go | recommandé (léger) |
| `granite4.2:3b` | 2,2 Go | 4 Go de VRAM, dernier recours |
| `qwen3.5:9b` | 6,6 Go | option pour une carte > 8 Go |
| `granite4.2:8b` | 5,3 Go | — |
| `qwen3.5:4b` | 3,3 Go | — |
| `ministral-3:8b` | 6,0 Go | écarté (lent) |
| `ministral-3:3b` | 3,0 Go | écarté (plans) |
| `qwen3:4b` | 2,5 Go | disqualifié |
