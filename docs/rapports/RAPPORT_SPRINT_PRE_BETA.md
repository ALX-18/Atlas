# RAPPORT SPRINT PRÉ-BETA — Ce qui casserait chez un proche
Date: 13/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_PRE_BETA.md`. Références : rapport Dépôt + Ollama (§6.5, §7, §9).
> Branche **`sprint-pre-beta`**, issue de `main` @ `2475168` (nouveau dépôt, historique réécrit). Commits non poussés au moment de la rédaction.

---

> **La beta peut-elle commencer ? Oui**, dès la validation de ce rapport. Les cinq défauts du brief sont corrigés et prouvés en réel :
> - chez un testeur réglé sur 4 096, la plus longue conversation n'est plus coupée ;
> - un clone neuf démarre ;
> - une demande ne perd plus 2 s ;
> - `doctor.py` voit un Ollama exposé, sa version et le modèle ;
> - la suite passe avec et sans Ollama.
>
> **Une réserve.** Une demande seule assez longue pour dépasser le contexte, environ 18 000 caractères collés d'un coup, n'est pas raccourcie : la garde ne touche que l'historique (§7).

---

## 1. Résumé exécutif

**Statut global : VALIDÉ** (sous réserve du superviseur).

**Runtime :** Ollama 0.40.3, qui n'écoute plus que sur `127.0.0.1:11434` après le geste d'Alexis, vérifié. Docker (ChromaDB, SearXNG) en marche.

**Chiffres :**
- **PB1 :** Ollama réglé sur 4 096. Avant : la conversation de 20 messages avec mémoire est **coupée** (5 261 → 4 064 jetons, `truncated = 1`). Après : `n_ctx = 8192`, **5 258 jetons, `truncated = 0`**.
  - 8 192 contre 32 768 : **4 873 contre 6 073 Mio** de mémoire vidéo, 100 % carte contre 8 % processeur, chargement 5,9 contre 7,3 s.
- **PB3 :** `collect_context` passe de **2,07 s à 0,0185 s** (médianes). Le fil d'arrière-plan coûte 0,55 % d'un cœur. La route `/api/chat` passe de **3,5 à 1,5 s** (médianes).
- **Suite :**
  - avec Ollama : **1 027 passés, 4 ignorés** ;
  - sans Ollama : **1 024 passés, 7 ignorés**, code 0 dans les deux cas ;
  - 27 nouveaux tests, 26 rouges avant correction, dont 19 seulement sur un nom absent.
- **Mémoire réelle :** décomptes **identiques** avant et après le sprint, **aucune trace** à retirer.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| PB1 — `num_ctx` unique, dans la configuration, dans toutes les requêtes | `ollama.context_window` (8 192), **déjà présent dans `settings.json` mais lu par rien**, est désormais envoyé par la conversation, le flux, la planification, la voix, le résumé web, la vision et le client partagé | PASS |
| PB1 — garde de dépassement : l'historique est raccourci, jamais la consigne | `fit_messages` retire les plus anciens messages ; consigne et demande intactes ; testé | PASS |
| PB1 — prouvé en réel à 4 096 ; réglage d'Alexis remis | avant `truncated = 1`, après `truncated = 0` ; application Ollama relancée, configuration identique | PASS |
| PB1 — mémoire vidéo et chargement, 8 192 contre 32 768 | 4 873 contre 6 073 Mio ; 5,9 contre 7,3 s ; cache KV 448 contre 1 792 Mio | PASS |
| PB2 — un clone neuf démarre sans `mkdir logs` | clone de la branche : `logs\` absent, Atlas démarre, `/api/health` répond, `logs\atlas.log` créé | PASS |
| PB3 — `collect_context` sous 0,2 s, mesuré avant et après ; coût du fil mesuré | 2,07 → 0,0185 s ; fil : 0,33 s de CPU en 60 s (0,55 % d'un cœur) ; arrêté à la fin d'Atlas | PASS |
| PB3 — remesurer `/api/chat` | 3,5 → 1,5 s (médianes) | PASS |
| PB4 — `doctor.py` : Ollama exposé, version, modèle ; Ollama d'Alexis sur 127.0.0.1 | trois contrôles ; chez Alexis : `127.0.0.1` seulement, 0.40.3, `qwen2.5:7b` présent | PASS |
| PB5 — les deux tests de grounding ignorés sans Ollama | ignorés, avec leur raison ; testé en simulant l'absence et vérifié Ollama arrêté | PASS |
| README et installation à jour (0.40.3, logs, tests) | README, `INSTALLATION_ALEXIS.md`, `install_checklist.md` | PASS |
| `pytest` → code 0, avec et sans Ollama | 1 027 / 4 et 1 024 / 7 | PASS |
| Règle C3 : traces des essais retirées et listées | **aucune** : décomptes identiques avant et après (§6.6) | PASS |

---

## 3. Architecture projet mise à jour

```
main.py                                   ← PB2 : logs\ créé ; PB3 : start_sampler / stop_sampler
core/
├── context_monitor.py                    ← PB3 : instantané en un appel système, échantillonneur
└── ollama_client.py                      ← PB1 : NUM_CTX, ollama_options(), build_messages()
core_conversational/llm_client.py         ← PB1 : DEFAULT_NUM_CTX, estimate_*, fit_messages ; LLMClient(num_ctx)
tools/
├── grounding.py                          ← PB1 : _vision_payload (num_ctx)
└── web_reader.py                         ← PB1 : options et keep_alive communs
scripts/doctor.py                         ← PB4 : exposition réseau, version de référence 0.40.3
README.md, docs/beta/INSTALLATION_ALEXIS.md, docs/install_checklist.md   ← 0.40.3, logs, tests
tests/
├── test_pre_beta.py                      ← NOUVEAU : 27 tests (PB1-PB5)
├── o_mesure_ollama.py                    ← mode « pb1 » (banc, pas un test pytest)
├── test_sprint_kimi_understanding_v51.py ← PB5 : ignoré sans Ollama
└── test_vision_parsers.py                ← PB5 : ignoré sans Ollama
docs/rapports/RAPPORT_SPRINT_PRE_BETA.md  ← NOUVEAU
```

---

## 4. Détail des implémentations

### 4.1 PB1 — taille de contexte explicite
- **La valeur :** `config/settings.json` → `ollama.context_window` = **8 192**. Elle y était déjà, mais rien ne la lisait : c'était encore une valeur annoncée qu'aucune couche n'appliquait.
  - `core/ollama_client.py` la lit (`NUM_CTX`) et l'envoie par `ollama_options()` dans toutes ses requêtes.
  - `tools/web_reader.py` et `tools/grounding.py` (`_vision_payload`) utilisent la même.
  - `LLMClient` reçoit `num_ctx`, par défaut `DEFAULT_NUM_CTX` = 8 192, et un test vérifie que c'est la valeur de la configuration.
  - **Pourquoi une valeur unique :** une valeur qui change d'une requête à l'autre force le rechargement du modèle.
- **Pourquoi 8 192 :**
  - le pire cas mesuré fait 5 261 jetons (web, 20 messages, 6 souvenirs), soit 1,56 fois de marge ;
  - le résumé web plafonne à 8 000 caractères, environ 2 700 jetons ;
  - à 8 192, le modèle tient **entièrement sur la carte** (29/29 couches) ; à 32 768, une couche passe sur le processeur.
- **La garde,** `core_conversational/llm_client.py` :
  - `estimate_messages_tokens` compte de façon **pessimiste** : 3 caractères par jeton (mesuré : environ 3,4 en français), plus 4 jetons par message. Sur le cas réel, l'estimation fait 6 017, pour 5 261 vrais jetons ;
  - `fit_messages(messages, num_ctx, réserve=1024)` retire l'historique du plus ancien au plus récent, et garde un historique qui commence par une question. Il ne touche jamais au premier message (`system`, la consigne) ni au dernier (la demande) ;
  - `core/ollama_client.build_messages` l'applique, et journalise le nombre de messages retirés.

### 4.2 PB2 — `logs\`
Dans `main.py`, `(…/"logs").mkdir(exist_ok=True)` est appelé juste avant `logging.basicConfig`. La ligne `mkdir logs` est retirée du README et de `INSTALLATION_ALEXIS.md`. `install_checklist.md` §12 est marqué « plus rien à faire ».

### 4.3 PB3 — `collect_context`
**Ce qui coûtait :**
- `psutil.process_iter` avec `cpu_percent` et `memory_percent` : **1,47 s de calcul pur** pour environ 400 processus. Ce n'était pas de l'attente : sous Windows, psutil reconstitue une photo du système **pour chaque processus**, soit environ 3,3 ms chacun ;
- 0,3 s d'échantillonnage bloquant du CPU ;
- 0,08 s pour `nvidia-smi`.

**Méthode retenue, mesurée contre deux autres :**
- psutil sans le CPU coûte autant (1,45 s) ;
- un échantillonnage psutil en arrière-plan toutes les 5 s aurait occupé environ 30 % d'un cœur.

1. **`_process_snapshot()` :** un seul `NtQuerySystemInformation(SystemProcessInformation)` donne nom, mémoire et temps CPU de **tous** les processus, en **7 ms**, sans temps processeur mesurable.
   - Comparé à psutil sur 405 processus : 2 noms diffèrent (des pseudo-processus système), et une mémoire a changé entre les deux lectures.
   - Hors Windows ou en cas d'échec, l'ancien calcul psutil sert de repli, dans le fil seulement.
2. **Fil `atlas-context-sampler` :**
   - c'est un fil « daemon », donc incapable de survivre au processus ; un seul fil, même si on le démarre plusieurs fois ;
   - il relève toutes les 2 s le CPU global (`cpu_percent(interval=None)`, non bloquant, sur l'intervalle) et les processus, avec un CPU par processus calculé sur l'écart entre deux instantanés ;
   - il relève le GPU toutes les 10 s ;
   - `main.py` le démarre au début de `lifespan` et l'arrête (`stop_sampler`) à la fermeture ;
   - `collect_context` le démarre aussi s'il ne tourne pas : scripts, banc, voix en processus.
3. **`collect_context` :**
   - il lit le dernier échantillon : processus, CPU et GPU, au plus 2 s d'âge (10 s pour le GPU) ;
   - la **fenêtre active**, la mémoire vive, les disques, l'audio et le réseau restent lus **à l'instant de la demande**.

**Ce qui change dans le contenu :**
- les clés sont identiques ;
- le CPU global couvre au plus les 2 dernières secondes, au lieu de 0,3 s ;
- « System Idle Process » (pid 0) n'est plus dans la liste : il y figurait en tête avec « 828 % », valeur sans sens ;
- le CPU par processus vient de l'écart entre deux instantanés. Avant, c'était le cache de psutil (0 au premier appel).

**Pour le modèle :** il reçoit toujours la fenêtre active, le CPU et la RAM, avec le même format.

### 4.4 PB4 — `doctor.py`
- **`_ollama_listen_addresses()`** : les adresses qui écoutent le port 11434, via `psutil.net_connections`, avec un repli sur `netstat`.
- **`ollama_exposure_check()`** : avertit si une adresse n'est pas locale (`0.0.0.0`, `::`, une adresse du réseau), et donne le geste : désactiver « Expose Ollama to the network », ou retirer `OLLAMA_HOST`.
- **`ollama_version_check()`** : compare à `OLLAMA_REFERENCE_VERSION = "0.40.3"`, avec un avertissement en cas d'écart.
- **`check_ollama()`** : ajoute ces deux contrôles. La présence du modèle y était déjà.

### 4.5 PB5
`_ollama_absent()` (sonde du port, 0,5 s au plus, ou `ATLAS_TEST_NO_OLLAMA=1`, sur le modèle de `ATLAS_TEST_NO_CHROMA`) conditionne un `skipif` sur chacun des deux tests, avec sa raison.

---

## 5. Résultats des tests

### État rouge
`tests/test_pre_beta.py`, écrit avant tout code : **24 échoués, 2 en erreur, 1 passé.**
- **Rouges forts (7) :**
  - `num_ctx` absent des requêtes : flux, planification et voix, résumé web, client partagé ;
  - `import main` sans `logs\` → `FileNotFoundError` ;
  - `main.py` sans échantillonneur ;
  - `ATLAS_TEST_NO_OLLAMA=1` sans effet : « 2 passed » au lieu de « 2 skipped ».
- **Rouges faibles (19) :** un nom absent (`AttributeError` ou `ImportError`). Le rouge fort de la garde de dépassement est la preuve réelle, `truncated = 1` (§6.1).
- **Passé dès le départ :** une conversation qui tient n'est pas touchée. C'est une garde de non-régression.

### Suite complète
```
.\.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
Avec Ollama  : 1027 passed, 4 skipped in 159.35s (0:02:39)
Sans Ollama  : 1024 passed, 7 skipped in 162.41s (0:02:42)    (Ollama arrêté, puis relancé)
```
- Sans Ollama, les 3 tests ignorés en plus sont les 2 de grounding (PB5) et le test du vrai modèle de `test_honesty_gbis` (déjà conditionnel).
- La suite est passée de 4 min à 2 min 40 : `collect_context` y est appelé souvent.

### Non-régression
Aucune suite existante n'a échoué : `test_gter`, `test_depot_ollama`, `test_beta_safety_g`, `test_confirmation_f`, `test_core_conversational`, `test_voice_*`, `test_memory_*`, `test_automation_*`, etc. Les tests qui remplacent `collect_context` (`test_confirmation_f`, `test_automation_safety_b1_ter`) passent sans changement.

---

## 6. Comportement observé en scénarios réels

### 6.1 PB1 — Ollama réglé comme chez un testeur (contexte par défaut 4 096)

Mon propre `ollama serve`, lancé avec `OLLAMA_CONTEXT_LENGTH=4096`, joue le banc d'Atlas (code réel, outils simulés, mémoire en lecture seule). L'application d'Alexis est relancée ensuite.

| ID | Requête | Avant (sans `num_ctx`) | Après |
|---|---|---|---|
| R1 | conversation, fenêtre Atlas | `n_ctx` 4 096, 1 060 jetons, `truncated = 0` | `n_ctx` **8 192**, 1 060 jetons, `truncated = 0` |
| R2 | conversation web, 20 messages, mémoire | `n_ctx` 4 096, **4 064 jetons (sur ~5 261), `truncated = 1`** | `n_ctx` **8 192**, **5 258 jetons, `truncated = 0`** |

| `num_ctx` (même serveur) | Cache KV | Couches sur la carte | Mémoire vidéo (chargé − déchargé) | Chargement |
|---|---|---|---|---|
| 8 192 | 448 Mio | 29/29 (100 %) | 4 873 Mio | 5,9 s |
| 32 768 | 1 792 Mio | 28/29 (8 % processeur) | 6 073 Mio | 7,3 s |

### 6.2 PB2 — clone neuf
`git clone -b sprint-pre-beta`, sans `logs\`. Atlas est lancé (`main.py`, mémoire coupée) :
- `/api/health` répond (statut `degraded` : mémoire coupée et modèles vocaux absents du clone) ;
- `logs\atlas.log` est créé (3 773 octets) ;
- Atlas a été arrêté ensuite.

### 6.3 PB3 — vraie machine (404 processus, 12 cœurs logiques)

| Mesure | Avant (module de `main`) | Après |
|---|---|---|
| `collect_context`, médiane | **2,07 s** (de 1,94 à 2,28) | **0,0185 s** (de 0,0175 à 0,0248) |
| Première demande (démarre le fil) | — | 0,36 s |
| Fil d'arrière-plan, 60 s sans demande | — | 0,33 s de CPU, soit 0,55 % d'un cœur et 0,05 % de la machine |
| Fil après `stop_sampler` | — | aucun |
| Route `/api/chat`, 10 demandes, modèle chaud, médiane | 3,5 s (sprint Dépôt + Ollama) | **1,5 s** |
| Premier mot, médiane | 0,41 s | 0,32 s (modèle 100 % carte à 8 192) |

- **Premières demandes après le démarrage :** le maximum de la route (30,6 s) est la première demande. Elle cumule le chargement des embeddings (19 s, hors périmètre) et le rechargement du modèle, de 32 768 à 8 192 (6,3 s). Ce rechargement n'arrive qu'une fois : ensuite, toutes les requêtes demandent 8 192.
- **Contenu :** pour le CPU global, 27,8 % avant et 29,0 % après ; pour le GPU, 10 % puis 13 %. Ce sont deux instants différents. Les 5 premiers processus après sont des processus réels ; « System Idle Process » n'y est plus.

### 6.4 PB4 — `doctor.py` sur la machine d'Alexis
```
[OK] Modèle configuré 'qwen2.5:7b' présent
[OK] Version de référence (0.40.3)
[OK] Ollama n'écoute pas sur le réseau
```
`netstat` le confirme : `TCP 127.0.0.1:11434 LISTENING`, et rien sur `0.0.0.0`. C'est vérifié après le geste d'Alexis, puis à nouveau après chacune de mes relances de son application.

### 6.5 PB5 — Ollama arrêté
- Les deux tests apparaissent en « SKIPPED », avec leur raison (« Ollama absent : … »).
- La suite passe : 1 024 passés, 7 ignorés.

### 6.6 Règle C3 — mémoire réelle
Décomptes lus (lecture seule) avant le sprint et après tous les essais :

| Collection | Avant | Après |
|---|---|---|
| `atlas_memory_e5` | 276 | 276 |
| `atlas_memory` | 489 | 489 |
| `atlas_conversations` | 19 | 19 |
| `atlas_errors` | 20 | 20 |
| `atlas_documents` | 8 | 8 |
| `atlas_habits` | 0 | 0 |
| `atlas_context_apps` | 0 | 0 |

**Aucune trace à retirer.**
- Le banc tourne avec la mémoire en lecture seule : les écritures sont interceptées.
- Les lancements réels d'Atlas se font avec `ATLAS_MEMORY=off`.
- `/api/health` n'a pas été appelé avec la mémoire branchée.

---

## 7. Limites et risques identifiés

| # | Description | Sévérité | Mitigation |
|---|---|---|---|
| 1 | **Une demande seule trop longue n'est pas raccourcie.** Au-delà d'environ 18 000 caractères (consigne de ~4 500 + demande, pour un budget de 7 168 jetons estimés), la garde n'a plus d'historique à retirer. Ollama couperait alors le début, c'est-à-dire la consigne. Un texte collé d'un bloc peut le faire. | Moyen | refuser poliment une demande trop longue, ou la tronquer **elle**, de façon déterministe ; au sprint suivant |
| 2 | L'estimation des jetons est une heuristique (3 caractères par jeton). Elle est pessimiste sur le français mesuré (+14 %), mais n'est pas vérifiée sur du code ni sur des langues à caractères larges. | Faible | la remplacer par un compte exact (tokenizer du modèle) si un cas réel la met en défaut |
| 3 | **Première demande après le démarrage :** jusqu'à 30 s, entre le chargement des embeddings (19 s) et le premier chargement du modèle à 8 192. | Moyen | sprint latence : préchauffage au démarrage (hors périmètre ici) |
| 4 | `_process_snapshot` lit une structure du noyau Windows (`SYSTEM_PROCESS_INFORMATION`), stable depuis Vista, mais pas une API documentée pour les applications. | Faible | repli psutil automatique si l'appel échoue ; un test compare l'instantané à psutil sur la vraie machine |
| 5 | **PB5 ignore les deux tests au lieu de les rendre indépendants d'Ollama**, comme le demande le brief. Sans Ollama, ils ne vérifient donc rien. | Faible | les faire tourner avec un faux `_list_ollama_models` ; changement de quelques lignes |
| 6 | Le réglage de contexte de l'application Ollama d'Alexis reste à 262 144. Il ne s'applique plus à Atlas, qui impose 8 192, mais s'appliquerait à un autre programme. | Faible | rien à faire pour Atlas |
| 7 | `web_reader` envoie désormais aussi `keep_alive` = 10 min, au lieu des 5 min par défaut d'Ollama. C'est voulu, pour la cohérence, mais c'est un changement de comportement. | Faible | — |
| 8 | Toujours pas de séance au micro : l'effet de PB3 sur le cycle vocal (environ 2 s de « réflexion » en moins attendus) est déduit, pas mesuré à la voix. | Moyen | séance au micro d'Alexis |

---

## 8. Checklist de validation

- [x] `num_ctx` unique, dans la configuration, présent dans toutes les requêtes
- [x] Garde de dépassement : l'historique est raccourci, jamais la consigne
- [x] Prouvé en réel avec Ollama réglé sur 4 096 : `truncated = 0` ; réglage d'Alexis remis
- [x] Mémoire vidéo et chargement mesurés, 8 192 contre 32 768
- [x] Un clone neuf démarre sans `mkdir logs`
- [x] `collect_context` sous 0,2 s (0,0185 s), mesuré avant et après ; coût du fil mesuré (0,55 % d'un cœur)
- [x] `doctor.py` signale Ollama exposé au réseau, sa version et le modèle ; Ollama d'Alexis sur `127.0.0.1` seulement
- [x] Les deux tests de grounding ignorés sans Ollama
- [x] README et installation à jour (0.40.3, logs, tests)
- [x] `python -m pytest tests/ -q` → code 0, avec (1 027 / 4) et sans Ollama (1 024 / 7)
- [x] C3 : aucune trace dans la mémoire réelle (décomptes identiques)

---

## 9. Recommandations pour le sprint suivant

### P1 — avant ou pendant la beta
- **Limite n° 1 :** une demande trop longue, refusée ou tronquée elle-même, de façon déterministe, avec un message clair.
- **Séance au micro** pour mesurer le cycle vocal après PB3.

### P2 — sprint latence (inchangé, chiffres en main)
- **Ordre de la consigne,** partie fixe d'abord : environ 270 ms par requête courte.
- **Préchauffage** des embeddings et du modèle au démarrage : jusqu'à 30 s pour la première demande.
- **Cache KV en `q8_0`.** À 8 192, le modèle tient déjà sur la carte ; le gain serait surtout de la mémoire vidéo libérée.
- **`keep_alive`.**
- Les deux tests de grounding rendus indépendants d'Ollama.
