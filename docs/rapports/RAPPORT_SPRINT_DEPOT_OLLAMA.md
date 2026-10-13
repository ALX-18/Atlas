# RAPPORT SPRINT DÉPÔT + MESURES OLLAMA — Un dépôt montrable, et des chiffres avant d'optimiser
Date: 12/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_DEPOT_OLLAMA.md`. Inventaire : `docs/rapports/INVENTAIRE_DEPOT_R1.md`.
> Branche **`sprint-depot-ollama`**, issue de `main` @ `5a9ef3e` (G-ter déjà fusionnée par la PR #9). Commits **non poussés**.
> Séance de jour, Alexis présent : décisions R1 et accord pour redémarrer Ollama donnés dans la conversation.

---

> **Le dépôt peut-il redevenir public ? Oui** (mis à jour le 13/10). Le nouveau dépôt `ALX-18/cortana-killer-atlas` contient l'historique réécrit, vérifié depuis GitHub : **0 motif dans ses 96 commits**, deux branches, aucune référence de PR. Il est **privé** : c'est à Alexis de le passer en public.
> L'ancien dépôt, avec ses 9 PR et l'ancien historique, est renommé `cortana-killer-atlas-archive` et reste **privé pour toujours** (option A, décision d'Alexis du 13/10). Détail au §10.

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.**
- **Fait :**
  - les restes de G-ter (C1, C2, C3) ;
  - l'inventaire, le nettoyage de l'arbre, la sauvegarde miroir vérifiée et l'essai de réécriture sur copie (R1 à R3) ;
  - le README (R4), les dossiers anciens (R5), les propositions de licence et de CI (R6) ;
  - les mesures O1 à O4.
- **Reste ouvert :**
  - la publication de R3 (attend le « oui » d'Alexis et une décision côté GitHub) ;
  - le retrait de `err_7297b690157e` : la commande a été **refusée par la protection des suppressions** de ma session, et je ne l'ai pas contournée ;
  - le choix de la licence ;
  - l'activation de la CI.

**Runtime :**
- Docker (ChromaDB, SearXNG) et Ollama tournent.
- Ollama s'est mis à jour **tout seul en 0.40.3** pendant la séance (14 h 26) ; la référence notée était 0.40.2.
- Sa configuration a été remise à l'identique après O4.

**Chiffres :**
- **Suite :** 1 000 passés, 4 ignorés, code 0 (970 + 30 nouveaux tests). 28 tests rouges avant correction, dont 11 seulement sur un `AttributeError`.
- **O1 :** la plus longue requête fait **5 261 jetons**, pour un contexte appliqué de **32 768**. Rien n'est coupé (`truncated = 0`). `num_ctx` n'a donc pas été touché.
- **O3 :** **une seule requête sur deux réutilise moins de la moitié de la consigne.** Même avec la même question, 497 jetons sur 1 063 sont réévalués, parce que le pourcentage de CPU, placé au milieu de la consigne, change à chaque requête.
- **O4 :**
  - flash attention active ;
  - cache KV en **f16 : 1 792 Mio**, une couche du modèle sur le processeur ;
  - en **q8_0 : 952 Mio**, **100 % sur la carte**, demande chaude **0,36 s → 0,21 s**.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| `sprint-g-ter` fusionnée dans `main`, suite verte (970 / 4) | déjà fusionnée (PR #9) ; suite de référence au départ : 966 passés, 2 échoués, 6 ignorés **avec Ollama et Docker fermés** (les 2 échecs dépendent d'Ollama, §7). Avec les services : 1 000 / 4 après ce sprint | PASS |
| C3 — `err_7297b690157e` retirée après sauvegarde vérifiée | sauvegarde `chromadb_20261012_140134` + `verify` (restauration prouvée) ; `plan-ids` ne vise qu'elle. **`apply-ids --yes` refusé par la protection de ma session** : pas retirée | **FAIL** (bloqué, §7) |
| C3 — règle inscrite dans `RAPPORT_RULES.md` | inscrite (« Traces de test dans la mémoire réelle ») ; test | PASS |
| C3 — garde-fou contre l'écriture par oubli | **fait, pas seulement proposé** : la vraie mémoire n'est branchée que si `ATLAS_MEMORY=real`, posé par `main.py`. Prouvé en réel (§6.4) | PASS |
| C1 — version vocale courte, même registre, cohérence testée | 280 caractères, **16,4 s** lue par Piper (contre **75 s**) ; le « détail d'une famille » qu'elle propose existe vraiment ; tests de cohérence | PASS |
| C2 — `window_restore` dans le moteur ou plus annoncé | **ajouté au moteur**, mêmes règles que `window_focus` ; « restaure » compris ; prouvé en réel | PASS |
| R1 — inventaire complet, arbre et historique, secrets compris ; décisions consignées | `INVENTAIRE_DEPOT_R1.md` : 16 lignes ; 92 commits et 221 chemins parcourus ; aucun secret ; décisions d'Alexis consignées | PASS |
| R2 — arbre nettoyé, `.gitignore` complété, suite verte | 6 fichiers retirés, 1 renommé, 25 anonymisés ; 3 règles `.gitignore` ; 1 000 / 4 | PASS |
| R3 — sauvegarde miroir vérifiée **avant** toute réécriture ; essai sur copie ; aucun motif restant | miroir GitHub + bundle local ; le miroir se clone et sa suite passe (966 / 8) ; essai `filter-repo` : **0 motif dans 94 commits**, auteurs réécrits, arbre final identique à R2 | PASS |
| R3 — `push --force` uniquement après le « oui » d'Alexis | **pas fait** : attend le « oui », et la décision sur les références de PR (§9) | en attente |
| R4 — README vrai, phrase par phrase | réécrit ; chaque affirmation vérifiée dans le code ; une erreur trouvée en vérifiant (`mkdir logs` oublié), corrigée | PASS |
| R5 — dossiers anciens, prouvé | `ui/` servi par `main.py` ; `atlas-extension/` client du pont WebSocket que `main.py` démarre ; `assistant-bureau/` ne contenait que 4 artefacts de test, retirés | PASS |
| R6 — licence et CI : options, rien activé | deux licences présentées ; CI proposée dans `docs/proposition_ci/` (inactive) | PASS |
| O1 — le message tient-il dans le contexte ? | oui : 5 261 jetons au plus, contexte 32 768, `truncated = 0` partout | PASS |
| O2 — latence chaud / froid ; rechargements sur 20 min ; répartition du cycle vocal | chaud 0,41 s au premier mot ; froid 7,5 s ; 1 rechargement (+8,9 s) après 12 min de pause ; cycle : écoute 30 %, parole 31 %, réflexion 17 %, transcription 2 % | PARTIEL (session simulée, pas au micro) |
| O3 — réutilisation du cache | prouvée insuffisante ; cause localisée au caractère près | PASS |
| O4 — flash attention, f16 contre q8_0, configuration remise | mesuré ; configuration identique après | PASS |
| `python -m pytest tests/ -q` → code 0 | 1 000 passés, 4 ignorés | PASS |
| Rapport avec la ligne de tête | ce document | PASS |

---

## 3. Architecture projet mise à jour

```
.gitignore                                   ← R2 : inventaire mémoire, cleanup_ids, assistant-bureau/
README.md                                    ← R4 : réécrit
main.py                                      ← C3 : ATLAS_MEMORY=real
requirements-mac-compagnon.txt               ← R2 : renommé (ancien nom : persona réel)
core/
├── intent_classifier.py                     ← C1 : détail d'une famille ; C2 : « restaure »
├── intent_engine.py                         ← C1 : capabilities_reply(family), capabilities_reply_voice ; C2 : window_restore
├── memory_manager.py                        ← C3 : mémoire neutralisée hors d'Atlas
├── validator.py                             ← C1 : famille transmise ; C2 : exclu des automatisations
└── voice_engine.py                          ← C1 : la voix prononce la version « spoken »
core_conversational/{README.md, __init__, identity, intent_minimal, llm_client}.py   ← R2 : persona anonymisé
tools/window_controller.py                   ← C2 : window_restore, _restore_hwnd
scripts/{backup_memory, check_ollama_config, compare_ocr_engines, doctor,
         download_voice_models, profile_minicpm}.py   ← R2 : docstrings (plus de « cd assistant-bureau »)
docs/
├── RAPPORT_RULES.md                         ← C3 : règle des traces de test
├── proposition_ci/tests-windows.yml         ← NOUVEAU (R6, inactif)
├── rapports/INVENTAIRE_DEPOT_R1.md          ← NOUVEAU (R1)
├── rapports/RAPPORT_SPRINT_DEPOT_OLLAMA.md  ← NOUVEAU (ce rapport)
└── 12 documents anonymisés (chemins, persona, deux citations)            ← R2
tests/
├── test_depot_ollama.py                     ← NOUVEAU : 30 tests (C1, C2, C3)
├── o_mesure_ollama.py                       ← NOUVEAU : banc de mesure O1-O3 (pas un test pytest)
├── conftest.py                              ← C3 : ATLAS_MEMORY=real vers le Chroma JETABLE
├── gb1_mesure.py                            ← C3 : branche la mémoire volontairement (lecture seule)
├── test_gter.py                             ← C2 : un ancien test adapté (§5)
└── test_app_resolver_v51, test_automation_safety_b1_ter, test_backup_memory_guard,
    test_core_conversational                 ← R2 : chemins et persona anonymisés
Retirés : docs/rapports/INVENTAIRE_MEMOIRE_D.md, cleanup_ids.json, assistant-bureau/data/ (4 fichiers)
```

---

## 4. Détail des implémentations

### 4.1 C1 — « tu peux faire quoi ? » à la voix
- **`core/intent_engine.py` :**
  - `capabilities_reply(family=None)` rend la liste complète, ou une seule famille.
  - `capabilities_reply_voice(family=None)` en est la version parlée : les familles qui ont au moins un outil, l'offre du détail avec un exemple qui existe, la mention des confirmations. Pas d'astérisque, pas de liste.
  - Les deux parcourent le **même** registre (`capability_tools()`, `TOOL_CAPABILITIES`). Si on retire du registre les outils d'une famille, elle disparaît des deux, et un test le vérifie.
  - Le moteur renvoie `message` (écran) et `spoken` (voix).
- **`core/voice_engine.py` :** le chemin vocal prononce `spoken` quand il existe. L'écran garde la version complète.
- **`core/intent_classifier.py` :**
  - `HELP_FAMILY_WORDS` et `_HELP_FAMILY_RE` reconnaissent « que sais-tu faire avec les fenêtres ? », « tu peux faire quoi sur internet ? », « détaille la famille mémoire ».
  - Seuls des mots de famille connus sont reconnus : « tu peux faire quoi avec Photoshop ? » reste une conversation.
  - Sans ce détail, la version courte aurait proposé quelque chose qu'aucune couche n'applique. C'est le défaut récurrent que le brief cite pour C2.
- **`core/validator.py` :** le verbe `capabilities_family` transmet la famille au moteur.

### 4.2 C2 — `window_restore` ajouté, pas retiré
**Pourquoi l'ajouter :** c'était court et sûr, car le contrôleur de fenêtres avait déjà toutes les briques (`check_window_title`, `resolve_app_window`, `_focus_and_verify`).

**`tools/window_controller.py`, `window_restore(title)` :**
- refuse un titre vide ;
- si plusieurs fenêtres correspondent, demande laquelle (même message que `window_focus`) ;
- remet la fenêtre à sa taille normale (`SW_RESTORE`) ;
- puis **vérifie le premier plan** : si Windows ne le cède pas, le message le dit et `success` vaut `False`.

**Autres changements :**
- `TOOL_HANDLERS` et `TOOL_CAPABILITIES` (« restaurer une fenêtre à sa taille normale ») ;
- exclu des automatisations, comme réduire et agrandir ;
- « restaure » et « restaurer » ajoutés au classifieur. Seul « restore », en anglais, y menait.

### 4.3 C3 — règle et garde-fou
- **`docs/RAPPORT_RULES.md` :** les traces des tests et essais du développeur sont retirées sans redemander, après sauvegarde vérifiée, et listées dans le rapport. Ce qu'écrivent les sessions d'Alexis reste à lui. En cas de doute, on demande.
- **`core/memory_manager.py` :**
  - `_connect` ne se connecte que si `ATLAS_MEMORY == "real"`. Sinon, la mémoire se comporte comme si ChromaDB était absent : toutes les écritures (`save`, `ingest_*`, `store_error`, `forget`…) testent déjà `_connected`.
  - `main.py` pose `ATLAS_MEMORY=real` avant ses imports, par `setdefault` : on peut donc lancer Atlas mémoire coupée, ce que j'ai fait au §6.
  - `tests/conftest.py` le pose aussi, puisque toute connexion y va au serveur jetable.
  - `tests/gb1_mesure.py` et `tests/o_mesure_ollama.py` le posent volontairement, protégés par `ReadOnlyMemory`.
  - Les scripts de maintenance ouvrent leur propre client et ne sont pas concernés.

### 4.4 R1 à R3 — dépôt
- **Inventaire et décisions :** `INVENTAIRE_DEPOT_R1.md`. Alexis a tranché :
  - **5** : garder son nom ;
  - **9** : réécrire l'adresse d'école ;
  - **12** : garder (phrases de test) ;
  - **16** : supprimer les branches.
  
  Le reste est appliqué comme proposé.
- **Remplacements :** une seule liste de 11 règles littérales, gardée **hors du dépôt** (`…/scratchpad/r3/replacements.txt`, et à copier à côté de la sauvegarde). Elle sert à l'arbre (R2) et à l'historique (R3). Le persona devient « Compagnon », la proche fictive « Camille », et le profil Windows `C:\Users\utilisateur`.
- **Sauvegarde, `%USERPROFILE%\Atlas_backups\depot\` :**
  - `miroir_20261012_151447.git` (`git clone --mirror` de GitHub : 22 références, 92 commits) ;
  - `local_20261012_151447.bundle` (`git bundle --all` du dépôt local, vérifié).
  - Le miroir se clone, et sa suite y passe : 966 passés, 8 ignorés, après avoir créé `logs\` comme l'exige l'installation (§7).
- **Essai sur copie, `git-filter-repo` a40bce548d2c, dans un environnement à part :**
  - `--invert-paths` sur les 6 fichiers ;
  - `--path-rename` sur le fichier de dépendances, aux deux emplacements historiques ;
  - `--replace-text` et `--replace-message` ;
  - `--mailmap`, pour l'adresse d'école → `148252959+ALX-18@users.noreply.github.com`.
  
  Résultat :
  - 94 commits parcourus : **aucun motif** dans les contenus, chemins, messages ou auteurs ;
  - 94 auteurs et committers sur l'adresse `noreply` ;
  - l'arbre réécrit de `sprint-depot-ollama` est **identique**, à l'empreinte près (`3f97345`), à celui de R2.

### 4.5 R4 à R6
- **README :** pile et versions réelles, installation renvoyant à `INSTALLATION_ALEXIS.md`, architecture, tests, méthode avec un lien vers le rapport G-ter, limites reprises du guide testeur.
  - Vérifiées dans le code : la liste des confirmations, la validation de chaque étape d'un plan (`planner._validate_plan`), ce que télécharge `download_voice_models.py`.
  - Une affirmation retirée parce que fausse : « les tests qui demandent Ollama sont ignorés proprement ». Deux échouent.
- **R5 :** les preuves sont dans le tableau du §2.
- **R6, licence (rien d'ajouté) :**
  - **MIT** : chacun peut réutiliser le code en citant l'auteur ;
  - **tous droits réservés** : le code est lisible, mais aucune réutilisation n'est permise.
- **R6, CI :** `docs/proposition_ci/tests-windows.yml`, runner Windows, Python 3.12.
  - Le ChromaDB jetable vient du paquet pip, donc la suite n'a pas besoin de Docker.
  - Les deux tests qui échouent sans Ollama y sont désélectionnés et nommés.
  - Estimation : environ 966 tests exécutés (état du clone neuf, Ollama présent ; sans Ollama, 2 de moins, désélectionnés). **Jamais lancée sur GitHub.**

---

## 5. Résultats des tests

### État rouge
`tests/test_depot_ollama.py`, écrit avant tout code : **28 échoués, 2 passés.**
- **Rouges forts (17) :**
  - « restaure le bloc-notes » partait en `__conversation__` ;
  - le détail d'une famille renvoyait une conversation ;
  - `window_restore` absent de `TOOL_HANDLERS` ;
  - la vraie mémoire contactée par un `MemoryManager()` lancé à part (`connexions = [{'host': '127.0.0.1', 'port': 62885}]`) ;
  - `main.py` sans `ATLAS_MEMORY` ;
  - la règle absente de `RAPPORT_RULES.md`.
- **Rouges faibles (11) :** `AttributeError`, sur `capabilities_reply_voice` (4) et `_restore_hwnd` (7).
- **Les 2 qui passaient déjà :** une question sur un mode précis n'était pas une demande de famille (garde de non-régression) ; et la phrase anglaise « restore notepad », déjà comprise.

### Ancien test adapté
`tests/test_gter.py::test_gt1_la_reponse_n_annonce_que_des_outils_reels_et_les_annonce_tous` exigeait `"window_restore" not in annonces` : annoncé par le classifieur, l'outil n'existait pas dans le moteur. Il exige désormais **plus fort** : aucun outil exposé par le classifieur ne manque au moteur, et `window_restore` est annoncé.

### Suite complète
```
.\.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
1000 passed, 4 skipped in 242.19s (0:04:02)      ← après C1-C3, puis à nouveau après R2
```
- Le dernier passage, avec le README et le banc, est donné au §8.
- Au départ, Ollama et Docker étaient fermés : 966 passés, **2 échoués**, 6 ignorés. Les deux échecs sont `test_grounding_layer_order_steam_includes_heuristic` (il attend `minicpm-v` dans Ollama) et `test_layer_timeout_aborts_slow_layer` (7,0 s pour une limite de 6 s : interroger Ollama port fermé coûte 2 s sous Windows).

### Non-régression par suite
Toutes les suites de `tests/` sont dans le passage complet : `test_gter` (43), `test_session_alexis_gbis`, `test_honesty_gbis`, `test_send_message_gbis`, `test_beta_safety_g`, `test_confirmation_f`, `test_voice_*`, `test_memory_*`, `test_core_conversational`, `test_identity_v60`, etc. Aucune n'a échoué avec les services lancés. `test_core_conversational` et `test_identity_v60` passent avec le persona anonymisé et le nom gardé.

---

## 6. Comportement observé en scénarios réels

### 6.1 Atlas lancé pour de vrai, mémoire coupée (`ATLAS_MEMORY=off`)
`/api/health` répond `chromadb: false` (neutralisée), alors que le conteneur tourne. Ollama, SearXNG et la voix sont « ok ».

| ID | Commande | Attendu | Observé | Statut |
|---|---|---|---|---|
| S1 | « tu peux faire quoi ? » | liste complète, avec la restauration | 6 familles, « restaurer une fenêtre à sa taille normale », modes utilisables (3,8 s) | PASS |
| S2 | « que sais-tu faire avec les fenêtres ? » | la seule famille fenêtres | 8 libellés de la famille, « * demande votre confirmation » (1,9 s) | PASS |
| S3 | « détaille la famille mémoire » | la seule famille mémoire | 4 libellés (1,9 s) | PASS |
| S4 | « tu peux faire quoi avec Photoshop ? » | conversation, pas de famille | le modèle dit que Photoshop n'est pas dans ses outils… mais suggère « charge l'image.png dans Photoshop », qu'Atlas ne sait pas faire (§7) | PARTIEL |
| S5 | « restaure AtlasEssaiRestaure » (fenêtre Tk à moi, **réduite**) | restaurée et au premier plan | avant : réduite, pas au premier plan ; après : **non réduite, au premier plan** (Windows) ; « Fenêtre 'AtlasEssaiRestaure' restaurée et mise au premier plan. » | PASS |
| S6 | « restaure une fenêtre qui n'existe pas du tout » | rien n'est touché | « Aucune fenêtre trouvée pour 'qui n'existe pas tout'. » | PASS (la cible perd « du », cosmétique) |

### 6.2 C1 à voix haute (Piper, `fr_FR-siwis-medium`, synthèse sans lecture)
| Texte | Caractères | Durée lue |
|---|---|---|
| Réponse écrite complète | 1 197 | **75,0 s** |
| Version vocale | 280 | **16,4 s** |
| Détail « fenêtres » | — | 19,8 s |

Le chemin vocal (`_run_text_pipeline`) prononce la version courte, ce que prouve un test. Pas de séance au micro (§7).

### 6.3 C2 — voir S5 et S6.

### 6.4 C3 — garde-fou, en réel (ChromaDB en marche)
```
python -c (import du moteur, MemoryManager)      → connecté = False
après « import main »                            → ATLAS_MEMORY = real ; connecté = True
```

### 6.5 Mesures Ollama (0.40.3, qwen2.5:7b, RTX 5060 8 Go)

**O1 — taille des requêtes.** Banc `tests/o_mesure_ollama.py` : code réel, outils simulés, mémoire en lecture seule (aucune écriture : 6 écritures interceptées). Totaux lus dans `task.n_tokens` du journal du serveur.

| Chemin | Consigne (car.) | Historique | Souvenirs | Jetons | Coupé ? |
|---|---|---|---|---|---|
| conversation, fenêtre Atlas | 3 731 | 0 | 0 | 1 063 | non |
| conversation, mémoire chargée | 4 507 | 0 | 6 | 1 280 | non |
| conversation web, 20 messages | 4 276 | 20 | 4 | 5 201 | non |
| conversation web, 20 messages + mémoire | 4 507 | 20 | 6 | **5 261** | non |
| planification | 1 432 | 0 | — | 456 | non |
| voix | 4 271 | 0 | 4 | 1 235 | non |
| voix, mémoire chargée | 4 348 | 0 | 5 | 1 260 | non |

- **Contexte appliqué :** 32 768 (`ollama ps` et `n_ctx = 32768` dans le journal).
- **D'où vient cette valeur :** le réglage de l'application Ollama (`OLLAMA_CONTEXT_LENGTH:262144`), ramené à 32 768 par le modèle (`n_ctx_train`).
- **Débordement :** `truncated = 0` à chaque requête. **Aucun débordement prouvé : `num_ctx` n'est pas modifié**, comme le prévoit le brief.

**O2 — latence.**
- **Modèle chaud, 10 demandes :**
  - premier mot : médiane **0,41 s** (de 0,34 à 0,55) ;
  - réponse du modèle : 0,90 s.
- **Modèle déchargé avant chaque demande, 10 demandes :**
  - chargement : **6,8 s** (de 6,7 à 8,0) ;
  - premier mot : **7,5 s**.
- **Hors du modèle :** la route `/api/chat` complète prend **3,5 s** en médiane, dont environ **2,0 s dans `collect_context`**. `_get_top_processes` y pèse **1,6 s** à lui seul (`psutil.process_iter` avec le CPU de chaque processus), plus 0,3 s d'échantillonnage du CPU. Le premier rappel mémoire après le démarrage prend 19,3 s (chargement du modèle d'embeddings), puis 0,28 s.
- **Session vocale de 20 min, simulée** par le chemin vocal réel. Demandes à 0, 1, 3, 7, 19 et 20 min : **1 rechargement**, à 19 min, après 12 min de pause, qui coûte **8,9 s**. `keep_alive` vaut 10 min.
- **Cycle vocal,** 29 cycles réels du journal (24/09 et 11/10), en médianes :

  | Étape | Médiane | Part |
  |---|---|---|
  | Écoute | 4,9 s | 30 % |
  | Transcription | 0,3 s | 2 % |
  | Réflexion (classification, contexte, modèle) | 2,7 s | 17 % |
  | Parole (synthèse et lecture) | 5,0 s | 31 % |
  | **Total** | **16,3 s** (de 6,9 à 62,8) | |

  La réflexion inclut les ~2 s de `collect_context`.

**O3 — cache entre deux requêtes.**

| Requête | Jetons | Repris du cache | Réévalués |
|---|---|---|---|
| question A | 1 063 | 566 | 497 |
| la même question A, aussitôt | 1 063 | **566** | **497** |
| question B | 1 062 | 565 | 497 |

- **Cause :** la consigne diverge au **caractère 2 086**, dans « CONTEXTE DU PC : … CPU: 14.8% » contre « 18.2% ».
- **Conséquence :** tout ce qui suit est réévalué à chaque requête, soit environ 270 ms : la mémoire, la liste des capacités (environ 1 200 caractères) et les règles.
- **Même constat sur les requêtes longues :** le préfixe commun s'arrête aussi vers le jeton 565.

**O4 — flash attention et cache KV,** à contexte égal (32 768), sur un `ollama serve` lancé pour la mesure :

| | Cache KV | Couches sur la carte | Mémoire vidéo (chargé − déchargé) | Demande chaude |
|---|---|---|---|---|
| f16 (actuel) | **1 792 Mio** (1 728 carte + 64 processeur) | **28/29**, 8 % processeur | 6 073 Mio | 0,34 à 0,37 s |
| q8_0 | **952 Mio** | **29/29**, 100 % carte | 5 403 Mio | 0,20 à 0,22 s |

- **Flash attention :** active dans les deux cas. Le journal affiche `flash_attn = auto` puis « Flash Attention enabled », bien que `OLLAMA_FLASH_ATTENTION` vaille `false` dans la configuration.
- **Premier chargement :** 8,9 s en f16 et 20,7 s en q8_0 ; un seul essai de chaque, à ne pas surinterpréter.
- **Remise à l'identique :**
  - aucune variable persistante créée ;
  - l'application Ollama a été relancée ;
  - son journal montre la même configuration qu'avant : contexte 262 144, `OLLAMA_HOST 0.0.0.0`, `KV_CACHE_TYPE` vide.

---

## 7. Limites et risques identifiés

| # | Description | Sévérité | Mitigation |
|---|---|---|---|
| 1 | **Les 9 références de PR sur GitHub gardent l'ancien historique.** Un `push --force` ne les touche pas, et toutes atteignent les fichiers retirés. Les anciens commits restent aussi consultables par empreinte. | **Élevé** pour le passage en public | nouveau dépôt avec l'historique réécrit (recommandé), ou purge par le support GitHub (§9) |
| 2 | **`err_7297b690157e` n'est pas retirée.** `apply-ids --yes` a été refusé par la protection des suppressions de ma session. La sauvegarde vérifiée et le plan sont prêts. | Faible | Alexis lance la commande (donnée dans la conversation), ou autorise `memory_cleanup.py apply-ids` |
| 3 | **`user.email` du dépôt local** est encore l'adresse d'école : tout nouveau commit la réintroduirait. | Moyen | `git config user.email 148252959+ALX-18@users.noreply.github.com` dans le dépôt (Alexis, ou moi avec son accord) ; même chose sur le Mac |
| 4 | **Ollama écoute sur `0.0.0.0:11434`** (réglage « exposer au réseau » de l'application) : le modèle est joignable depuis le réseau local, sans authentification. Atlas n'en a pas besoin. | Moyen | désactiver ce réglage dans l'application Ollama (décision d'Alexis ; non touché) |
| 5 | **Ollama s'est mis à jour seul en 0.40.3** pendant la séance ; la référence était 0.40.2. Les mesures sont faites en 0.40.3. | Faible | noter 0.40.3 comme référence, ou couper les mises à jour automatiques avant la beta |
| 6 | **Le contexte dépend du réglage de l'application Ollama** (ici 262 144, ramené à 32 768). Chez un testeur réglé sur 4 096, la conversation web à 20 messages (5 261 jetons) **serait coupée**, consignes comprises. Pas prouvé ici, donc pas corrigé. | Moyen | sprint latence : fixer `num_ctx` partout (8 192 suffirait : × 1,5 sur le pire cas mesuré) |
| 7 | **Session vocale simulée**, pas au micro. Les chiffres du cycle viennent des cycles réels du journal, dont mes rejeux de G-ter à la voix de synthèse. | Moyen | séance de 20 min au micro par Alexis |
| 8 | **Deux tests échouent au lieu d'être ignorés** sans Ollama (grounding). | Faible | les faire dépendre d'un `skipif` ou d'un faux Ollama (désélectionnés dans la CI proposée) |
| 9 | **Un clone neuf plante à l'import de `main.py`** sans `logs\` (déjà dans `install_checklist.md`). Mon README l'oubliait : trouvé en vérifiant le miroir, et corrigé. | Faible | créer `logs\` dans `main.py` (une ligne), au prochain sprint |
| 10 | `/api/health` dit `chromadb: false` quand la mémoire est neutralisée, comme si ChromaDB était en panne. | Faible | distinguer « neutralisée » dans `health` |
| 11 | S4 : sur « tu peux faire quoi avec Photoshop ? », le modèle suggère « charge l'image.png dans Photoshop », commande qu'Atlas ne sait pas exécuter. Ce n'est pas une affirmation d'action (la garde GB1 ne le vise pas), mais une promesse implicite. | Faible | consigne : ne proposer que des formulations de la liste |
| 12 | Vu en mesurant : « parle-moi de Discord, de Steam et d'Opera… » et « résume tout ce qu'on s'est dit » sont classées `web/read`, pas en conversation. | Faible | à examiner (classifieur), hors périmètre |
| 13 | La CI proposée n'a **jamais tourné sur GitHub** : le temps d'installation (torch et les modèles via pip) n'est pas mesuré. | Faible | premier lancement manuel après accord |

---

## 8. Checklist de validation

- [x] `err_7297b690157e` retirée — par Alexis le 13/10 (bloquée de mon côté par la protection de ma session, §7.2, §10) ; [x] règle C3 inscrite
- [x] `sprint-g-ter` fusionnée dans `main` (PR #9), suite verte
- [x] C1 : version vocale courte, même registre, cohérence testée
- [x] C2 : `window_restore` existe dans le moteur
- [x] Inventaire R1 complet, arbre et historique, secrets compris ; décisions d'Alexis consignées
- [x] Arbre nettoyé, `.gitignore` complété, suite verte
- [x] Sauvegarde miroir vérifiée avant toute réécriture ; essai sur copie ; aucun motif dans aucun commit
- [x] Publication après le « oui » d'Alexis (13/10, option A) : nouveau dépôt, pas de `push --force` sur l'ancien (§10)
- [x] README vrai, phrase par phrase
- [x] Dossiers anciens : utilisés ou non, prouvé
- [x] Licence et tests GitHub : options présentées, rien activé
- [x] O1 à O4 mesurés ; configuration d'Ollama remise à l'identique ; `num_ctx` non modifié (aucun dépassement)
- [x] `python -m pytest tests/ -q` → code 0 : **1 000 passés, 4 ignorés** (237,84 s), après le README et le banc

---

## 9. Recommandations pour le sprint suivant

### Pour finir ce sprint (décisions d'Alexis)
1. **Publication de R3. Je recommande l'option A** :
   - **A.** Renommer l'actuel dépôt GitHub (par exemple `cortana-killer-atlas-archive`), le **garder privé pour toujours** avec ses PR et leurs discussions, et pousser l'historique réécrit dans un **nouveau** dépôt `cortana-killer-atlas`, qui pourra devenir public. Rien n'est supprimé.
   - **B.** `push --force` sur le dépôt actuel, puis demander au support GitHub de supprimer les références de PR et les vues en cache. Le résultat dépend du support.
2. **Ordre de la publication, après le « oui » :**
   1. Fusionner `sprint-depot-ollama` dans `main`, pour qu'il ne reste qu'une branche.
   2. Réécrire avec la commande essayée.
   3. Supprimer les 12 branches distantes (déjà fusionnées).
   4. Publier.
   5. Sur ce PC et sur le Mac : **recloner**. Ne pas faire de `pull` dans l'ancienne copie, qui réintroduirait l'ancien historique. Puis poser `user.email` sur l'adresse `noreply`.
3. Choisir la licence ; dire si la CI s'active.

### P1 — sprint latence (les chiffres sont là)
- **`collect_context` : environ 2 s** par demande, dont 1,6 s pour `_get_top_processes`. C'est le gain le plus gros et le plus simple, et il vaut pour l'écrit comme pour la voix.
- **Ordre de la consigne :** déplacer ce qui change (contexte du PC, souvenirs) **après** la partie fixe (identité, règles, capacités). Environ 270 ms par requête courte (497 jetons sur 1 063) ; bien plus sur les requêtes longues, où le préfixe commun s'arrête aussi vers 565 jetons.
- **Cache KV `q8_0`** et **`num_ctx` explicite**, au même endroit pour toutes les requêtes. Le modèle tiendrait entièrement sur la carte (29/29), et la demande chaude passerait de 0,36 à 0,21 s. Fixer `num_ctx` retire aussi le risque n° 6.
- **`keep_alive`** au-delà de 10 min, ou un préchauffage au mot d'éveil : une pause de plus de 10 min coûte 8,9 s.
- **Préchauffer les embeddings** au démarrage : le premier rappel prend 19 s.

### P2
- Un `skipif` Ollama pour les deux tests de grounding ; `logs\` créé par `main.py` ; `health` qui distingue une mémoire « neutralisée ».
- Classifieur : « résume tout ce qu'on s'est dit » ne devrait pas être une lecture web.

---

## 10. Suite du 13/10 — décisions d'Alexis et publication

**Décisions, dans la conversation :**
- **Adresse des commits :** finalement **gardée** (« c'est pas bien grave »). La réécriture se fait **sans `--mailmap`**, et le risque n° 3 du §7 disparaît.
- **Licence :** **tous droits réservés**, dans `LICENSE` et dans une section du README.
- **Tests automatiques sur GitHub :** **pas pour le moment**. La proposition reste inactive dans `docs/proposition_ci/`.
- **Publication :** **option A** (« car y'a des données perso dedans »).

**Ce qui a été fait, dans l'ordre :**
1. **Vérification de départ :** `main` sur GitHub n'avait pas bougé depuis la sauvegarde (`5a9ef3e`). L'ancien dépôt était bien privé, sans PR ouverte.
2. **Nouvelle sauvegarde :** `local_20261013_095616.bundle` (vérifié), en plus de celles du 12/10.
3. **Réécriture d'une copie** limitée à `main` et `sprint-depot-ollama`, les 12 anciennes branches étant écartées. Mêmes commandes que l'essai, sans `--mailmap`. Contrôles :
   - 96 commits, aucun motif dans les contenus, les chemins ou les messages ;
   - arbre de `sprint-depot-ollama` identique au dépôt local (`9ccbb02`).
4. **`gh repo rename` :** l'ancien dépôt devient `cortana-killer-atlas-archive`, **privé**, avec la description « ARCHIVE PRIVÉE — … contient des données personnelles. Ne jamais rendre public. ».
5. **`gh repo create ALX-18/cortana-killer-atlas --private`,** puis poussée de `main` (`358c5c3`) et de `sprint-depot-ollama` (`0ead8e0`).
6. **Vérification depuis GitHub :** clone miroir du nouveau dépôt. Deux références seulement, 96 commits, **0** fichier contenant un motif, dans aucun commit.
7. **Ce PC :**
   - la copie de travail est rebranchée sur le nouveau dépôt (`origin`), et `main` et `sprint-depot-ollama` sont recalées sur l'historique réécrit ;
   - les 12 anciennes branches locales sont supprimées (elles sont dans la sauvegarde) ;
   - l'arbre de travail n'a pas changé, et les fichiers non versionnés (`.venv`, modèles, voix, données) sont intacts ;
   - les anciens objets restent dans le stockage interne de Git de ce PC, sans aucune référence qui y mène.

**Reste à faire, par Alexis :**
- Passer `cortana-killer-atlas` en **public**, quand il le souhaite.
- **Sur le Mac :** recloner `cortana-killer-atlas`. Ne **pas** faire de `pull` ni de `push` depuis l'ancienne copie : elle vise maintenant l'archive (redirection de GitHub) et contient l'ancien historique.
- ~~`err_7297b690157e`~~ : **retirée par Alexis le 13/10**, avec la commande PowerShell donnée (sa première tentative utilisait la syntaxe bash). Constaté ensuite par `plan-ids`, qui ne touche à rien : « err_7297b690157e introuvable ».
- La PR de ce sprint sur le nouveau dépôt, quand il la demande.
