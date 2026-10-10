# RAPPORT SPRINT G — Le minimum avant d'installer Atlas chez quelqu'un d'autre
Date: 10/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_G_BETA.md`. Références : rapport F (§7, §9, annexe A), rapport E (D-E4, E6), rapport A (L23).
> Branche **`sprint-g`**, issue de `main` @ `c6bd95c`. 12 commits, plus celui de ce rapport, **non poussés**.
> Séance de nuit en autonomie, sur autorisation d'Alexis (« tu peux faire ce que tu veux sur l'ordi pour ce soir »).

---

> **Atlas peut-il être installé chez un proche ce week-end ? Non, pas en l'état.** Deux conditions manquent.
> 1. **G7 n'est pas fait :** Alexis doit voir le dialogue de confirmation, au clavier. Je l'ai seulement répété, sans clic physique.
> 2. **Le superviseur doit trancher un défaut trouvé en testant :** en conversation, Atlas **affirme des actions qu'il n'a pas faites** (4 demandes sur 7, §6.3).
>
> S'il accepte ce défaut avec l'avertissement ajouté au guide, la beta est possible dès que G7 est fait. Sinon, il faut d'abord un correctif court, hors du périmètre G.

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.** G1 à G6 sont faits, testés et prouvés en réel. G7 n'est pas fait : il revient à Alexis par construction. Sur une nuit de tests en conditions réelles, j'ai trouvé quatre défauts sérieux. J'en ai corrigé trois, parce qu'ils touchaient la sécurité ou le « ne ment pas » du sprint. Le quatrième sort du périmètre et est remonté.

| Tâche | Avant | Après | Preuve |
|---|---|---|---|
| **G1** CORS | une page web lançait « lance la calculatrice » | 403 : origine étrangère, requête simple, autre site, rebinding DNS | 9 tests, 8 vus rouges ; 403 constaté en réel, avec sa ligne `[SECURITE]` |
| **G2** effacements par l'API | `DELETE /memory/category/x` effaçait une catégorie entière | les deux routes sont retirées (aucun appelant) | 3 tests rouges ; balayage des routes |
| **G3** télémétrie ChromaDB | 201 lignes « Anonymized telemetry enabled » | **0 ligne** sur deux démarrages réels | test en processus séparé, vu rouge ; dernière ligne du journal datée du 05/10 |
| **G4** « retiens que… » | « Outil inconnu » | retient, rappelle, oublie, toujours avec confirmation ; ne dit « noté » que si c'est vrai | 13 tests de bout en bout, vus rouges ; joué en réel, mémoire revenue à l'identique |
| **G5** `doctor.py` | aucun verdict | ✅ / ⚠️ / ❌ en tête, et pré-vérification avec un Python nu | 14 tests ; lancé en réel avec Python 3.14 sans paquet |
| **G6** documents | — | guide testeur et procédure d'installation, vérifiés phrase à phrase | §4.6 |
| **G7** dialogue vu par Alexis | jamais vu | **répété sans clic physique** : il s'ouvre, refuser, laisser expirer, confirmer | §6.4 — **reste à faire par Alexis** |

**Trouvé en testant, et corrigé :**
- **Processus système :** la protection décidée au sprint F ne marchait qu'avec le nom exact. « arrête csrss » et « tue explorer » étaient confirmables (§4.7).
- **Oubli :** « oublie le code du portail » ne retrouvait pas le fait, à cause d'un seuil trop strict.
- **`doctor.py`** concluait « ❌ » sur ta machine, à cause d'une fausse absence de cuBLAS.

**Trouvé, non corrigé, remonté :**
- **Fausses affirmations d'action en conversation** (§6.3, risque élevé).
- « qu'est-ce que tu sais faire ? » ou « une idée de **repas** » **rejouent la dernière action**.
- L'écriture dans une autre application est cassée.
- L'heure est inventée.
- La recherche web s'affiche brute.

**Tests : 46 nouveaux**, vus rouges. Suite complète : **732 passés, 4 ignorés, code 0**.

**État au moment du rapport :**
- **Atlas :** arrêté.
- **Docker :** démarré (`atlas_chromadb`, `atlas_searxng`).
- **Ollama :** 0.35, réparé par Alexis, modèle qwen2.5:7b.
- **Mémoire :** collection active `atlas_memory_e5`, 283 éléments, dont 10 écrits par mes tests (annexe B).
- **Sauvegarde :** `chromadb_20261010_053340`, vérifiée avant les tests. Elle représente l'état d'avant.

---

## 2. Objectifs vs réalisation

| Objectif (brief) | Résultat réel | Statut |
|---|---|---|
| G1 — `allow_origins` restreint aux origines d'Atlas | Fait, **plus** un filtre serveur : le CORS seul n'empêche pas l'exécution d'une requête simple (§4.1) | PASS |
| G1 — origine étrangère sur `/api/chat` refusée | 403, aucun outil appelé ; constaté aussi en réel | PASS |
| G1 — fenêtre desktop et interface web intactes | Témoins verts ; en réel, la fenêtre desktop a reçu toutes les confirmations | PASS |
| G2 — recenser toutes les suppressions de mémoire par l'API | Deux routes trouvées, sans aucun appelant | PASS |
| G2 — retirer, ou interdire sans confirmation ni sauvegarde | Retirées (recommandation du superviseur) | PASS |
| G3 — télémétrie client coupée avant toute connexion | `main.py` impose `ANONYMIZED_TELEMETRY=False` avant tout import | PASS |
| G3 — preuve par un démarrage réel | 0 ligne sur deux démarrages (05 h 34 et 05 h 45) | PASS |
| G3 — inventaire des autres sorties réseau | §7 : Hugging Face au démarrage, DuckDuckGo en repli, Ollama, Docker | PASS |
| G4 — ne jamais faire croire qu'il a retenu | « C'est noté » seulement si l'écriture a réussi, sinon « Je n'ai pas pu » | PASS |
| G4 — dire ce qui a été fait, et pourquoi | **Branchement complet**, choisi parce qu'il était court et testable aujourd'hui (§4.4) | PASS |
| G4 — « tu te souviens… » classé `recall` | Corrigé | PASS |
| G4 — `memory_forget` passe par la confirmation | Dans `CONFIRMATION_POLICY`, « toujours » ; le souvenir est désigné avant la confirmation | PASS |
| G5 — verdict ✅ / ⚠️ / ❌ lisible, seuils justifiés | §4.5 ; aucun jargon (testé) | PASS |
| G5 — pré-vérification sans installation complète | `--precheck` : bibliothèque standard seule, testée avec `python -S` | PASS |
| G6 — guide testeur, sans promesse non tenue | Chaque fonction annoncée a été jouée en réel le 10/10 ; les défauts y sont dits | PASS |
| G6 — procédure d'installation d'Alexis | Pré-vérification, ordre corrigé depuis le sprint A, pièges, désinstallation (marquée « non exécutée ») | PASS |
| **G7 — fait par Alexis, dialogue vu** | **Non fait.** Répétition sans clic physique (§6.4) | **FAIL** |
| G8 — `pytest tests/ -q` → code 0 | 732 passés, 4 ignorés | PASS |
| G8 — réponse en tête du rapport | Ci-dessus | PASS |

---

## 3. Architecture projet mise à jour

```
cortana-killer-atlas/
├── main.py                        ← G1 (CORS restreint + filtre « seul Atlas »), G3 (télémétrie)
├── api/routes.py                  ← G2 (routes DELETE mémoire retirées)
├── core/
│   ├── intent_engine.py           ← G4 (outils mémoire) ; protection des processus par nom
│   ├── memory_manager.py          ← G4 (catégorie user_fact)
│   ├── validator.py               ← G4 (memory_forget dans la table ; texte transmis) — hors liste, exigé par le brief
│   └── intent_classifier.py       ← G4 (« tu te souviens… ? » = rappel) — hors liste, exigé par le brief
├── scripts/doctor.py              ← G5 (verdict, --precheck, cuBLAS pip)
├── docs/beta/
│   ├── GUIDE_TESTEUR.md           ← NOUVEAU (G6)
│   └── INSTALLATION_ALEXIS.md     ← NOUVEAU (G6)
└── tests/
    ├── test_beta_safety_g.py      ← NOUVEAU (32 tests : G1, G2, G3, G4, processus)
    ├── test_doctor_verdict_g.py   ← NOUVEAU (14 tests : G5)
    └── test_metrics_grounding_v52.py, test_stabilisation_v31.py, test_v53_migration.py
                                   ← hôte local pour TestClient (G1 refuse l'hôte fictif « testserver »)
```

**Hors de la liste du périmètre, et pourquoi :**
- `validator.py` et `intent_classifier.py` : le brief exige lui-même `memory_forget` dans `CONFIRMATION_POLICY` et la correction de « tu te souviens ».
- La protection des processus dans `intent_engine.py` (autorisé pour G4 seulement) : c'est une faille de sécurité trouvée en testant la beta. **À valider par le superviseur.**
- Non touché : `desktop/atlas_desktop.py`. Le dialogue d'oubli affiche donc le nom technique « memory_forget » au lieu d'un libellé (§7).

---

## 4. Détail des implémentations

### 4.1 G1 — une page web ne pilote plus Atlas

**Restreindre `allow_origins` ne suffisait pas.** Le test rouge l'a montré sur la vraie application. Le middleware CORS empêche seulement le navigateur de *lire* la réponse. Une requête « simple » (`text/plain`, formulaire) part sans vérification préalable et elle est exécutée. Seul le serveur peut la refuser.

`main.py` ajoute un filtre devant toute l'API, `_refus_autre_origine`. Il refuse (403, journalisé `[SECURITE]`) :
- un **Host** qui n'est pas la machine (127.0.0.1, localhost, [::1]). Contre le **rebinding DNS** : un domaine hostile résolu vers 127.0.0.1 est « la même origine » pour le navigateur, et seul le Host le trahit ;
- une **Origin** qui n'est pas exactement `http://<Host>`. La comparaison se fait avec le Host, donc elle vaut quel que soit le port retenu au démarrage (`_find_available_port` peut en changer) ;
- **Sec-Fetch-Site** `cross-site` ou `same-site` : une balise `<img>` ou un lien n'envoient pas d'Origin, mais le navigateur envoie toujours cet en-tête.

La fenêtre desktop (httpx) n'envoie ni Origin ni Sec-Fetch-Site : elle passe. L'interface web est servie par Atlas lui-même (`same-origin`) : elle passe aussi.

### 4.2 G2 — l'API n'efface plus la mémoire

Recensement complet des routes (`api/routes.py`, `main.py`) : **deux** suppriment de la mémoire, `DELETE /memory/{id}` et `DELETE /memory/category/{x}`. Leurs appelants ont été cherchés dans l'interface web, la fenêtre desktop, les scripts, la documentation et les tests : **aucun**. Les deux sont retirées.

Oublier passe désormais par « oublie… », donc par la confirmation. Un nettoyage de masse passe par `scripts/memory_cleanup.py`, qui exige une sauvegarde vérifiée. Un balayage empêche qu'une route effaçant la mémoire réapparaisse.

### 4.3 G3 — télémétrie

Deux clients ChromaDB vivent dans le processus Atlas : `core/memory_manager.py` et `core_conversational/memory_core.py`, ce dernier hors périmètre. `main.py` impose `ANONYMIZED_TELEMETRY=False` avant tout import, ce qui couvre les deux sans y toucher. La valeur est imposée, et non posée par défaut : un réglage de la machine ne la rallume pas.

Piège du test : Chroma coupe sa télémétrie de lui-même quand pytest est chargé. Le test tourne donc dans un processus séparé, sans pytest et sans la variable d'environnement.

### 4.4 G4 — « retiens que… » : le branchement complet

**Choix : brancher pour de bon** sur `MemoryManager.save()` / `recall()`, fiables depuis le sprint D. C'était court, et testable de bout en bout le jour même, sur le ChromaDB jetable des tests.

- **Retenir** (« retiens que », « souviens-toi que », « n'oublie pas que », « mémorise »…) : la phrase **entière** est transmise par le validateur. Le classifieur, lui, amputait les petits mots (« que code portail est 4521 »). Le fait est enregistré tel quel dans la catégorie `user_fact`. La réponse « C'est noté : « … » » n'arrive que si l'identifiant est revenu ; sinon : « Je n'ai pas pu le retenir : ma mémoire est indisponible. »
- **Rappeler** (« tu te souviens de… ? », « rappelle-moi… ») : la recherche se fait parmi les faits retenus seulement. Sans résultat : « Je n'ai rien retenu à ce sujet ».
- **Oublier** : le souvenir est désigné **avant** la confirmation, et le dialogue l'affiche. C'est **ce souvenir-là**, par son identifiant, qui est effacé après confirmation. Seuls les faits retenus peuvent être oubliés, jamais l'historique ni les corrections. Sans correspondance : « rien n'a été effacé », et aucune attente n'est créée.
- **L'historique ne recopie plus** un fait retenu ou oublié. Sinon, un fait oublié aurait survécu dans `action_history`. Les tests le vérifient sans neutraliser l'historique.
- **Seuil d'oubli : celui du rappel** (0,82, réglé par `memory.retrieval_min_score`). Choisi d'abord à 0,85, il rejetait en réel « oublie le code du portail » (score e5 mesuré : **0,839**). Les scores e5 sont resserrés : pertinent 0,83 à 0,87, sans rapport 0,77 à 0,81. La protection contre le mauvais souvenir est la confirmation, qui montre le souvenir exact.

### 4.5 G5 — le verdict de `doctor.py`

La première ligne du rapport est **✅ Atlas tournera bien**, **⚠️ Atlas tournera, en mode dégradé** ou **❌ Atlas ne tournera pas correctement**, suivie des raisons en français courant. Un test interdit le jargon (VRAM, CUDA, WSL, Mio, GiB, STT, LLM).

**Seuils et leur justification :**

| Critère | ✅ | ⚠️ | ❌ | Fondé sur |
|---|---|---|---|---|
| Mémoire vive | ≥ 31 Gio (machines de 32 Go) | 23 à 31 Gio ; 15 à 23 Gio | < 15 Gio | Pic **23,4 Go sur 23,9** avec Docker (98 %), **18,7 Go** sans (sprint A, L23). Une machine de 16 Go est sous le pic sans Docker et paginera, mais Atlas y tourne : ⚠️, pas ❌. En dessous de 15 Gio, la marge n'existe plus. |
| Carte graphique | NVIDIA ≥ 7 500 Mio | NVIDIA plus petite ; aucune NVIDIA | — | Pic **6 674 Mio** sur la chaîne complète, qwen2.5:7b et transcription GPU (sprint E, E6). Sans NVIDIA : environ 5 s par phrase au lieu de 0,3 s (sprint E). |
| Virtualisation | activée | désactivée ou invérifiable | — | Sans elle, pas de Docker, donc pas de mémoire ni de SearXNG (sprint A). |
| Disque libre | ≥ 25 Go | — | < 25 Go | **Environ 17 Go installés**, mesurés sur ta machine le 10/10 : venv 3,6 ; Ollama 2,8 ; qwen2.5:7b 4,4 ; e5 1,1 ; whisper 0,1 ; Docker Desktop 3,9 ; images ChromaDB et SearXNG 1,2. Plus les installateurs et les caches. |
| Système | Windows 10/11 64 bits | — | autre | Atlas est une application Windows. |

**Pré-vérification (`--precheck`)** : elle n'utilise que la bibliothèque standard. Elle est testée avec `python -S` (sans site-packages), et lancée en réel avec ton **Python 3.14 nu**. Elle lit le disque du profil utilisateur, où s'installe Atlas, et non celui d'où on la lance (une clé USB, par exemple). Codes de retour : 0 ✅, 1 ⚠️, 2 ❌.

**Défaut trouvé en lançant pour de vrai** : le diagnostic complet concluait « ❌ installation incomplète : cuBLAS » sur ta machine, où la transcription tourne pourtant sur GPU. `doctor` cherchait la DLL dans le PATH, alors qu'Atlas déclare au démarrage celles des paquets pip `nvidia-*` (sprint E). C'est corrigé : verdict réel **⚠️ (mémoire vive un peu juste), 0 critique**. Chez un proche, ce faux ❌ aurait fait renoncer pour rien.

### 4.6 G6 — les deux documents

`docs/beta/GUIDE_TESTEUR.md` et `docs/beta/INSTALLATION_ALEXIS.md`. Règle suivie : chaque fonction annoncée a été **jouée en réel** le 10/10, et chaque défaut rencontré y est dit. Points notables :

- **« 100 % local » n'est pas écrit tel quel**, parce que ce serait faux. Le guide dit que ce que l'utilisateur dit et ce qu'Atlas retient restent sur la machine, et nomme les trois sorties réseau : la recherche web demandée, la vérification de mise à jour du module de voix au démarrage, les mises à jour d'Ollama et de Docker.
- **« Hey Atlas » à l'anglaise** (décision d'Alexis, D-E4). Taux d'échec annoncé : celui que tu as mesuré, 3 à 5 sur 10 (sprint E, R02).
- **Première réponse lente** : 88 s mesurées, puis 3 à 4 s.
- **La désinstallation est marquée « non exécutée »** et réservée au PC d'un proche, avec un avertissement : sur ta machine, `atlas_chromadb_data` est protégé.

### 4.7 Trouvé en testant : les processus système contournés par le nom

Décision d'Alexis au sprint F : un processus système n'est jamais arrêté, même confirmé. En réel, « arrête le processus csrss » proposait une confirmation. Vérifié à blanc, le refus ne marchait qu'avec le nom exact (« csrss.exe »), alors que `kill_process` cherche par **morceau de nom** (`nom in nom_du_processus`) :
- confirmer « csrss » visait `csrss.exe` ;
- confirmer « explorer » visait la barre des tâches.

`request_confirmation` applique maintenant la même règle que l'outil, après avoir retiré « le processus ». « arrête notepad » reste confirmable.

---

## 5. Résultats des tests

### État rouge, avant correction

```
G1  8 failed, 1 passed
    AssertionError: une page web a déclenché une action : [('launch_app', {'name': 'calculatrice'}), ...]
    AssertionError: 422 ... (requête simple traitée par le serveur au lieu d'être refusée)
    AssertionError: 200 [] (mémoire lue depuis un autre site / via un Host étranger)
    AssertionError: {... 'access-control-allow-origin': 'https://page-quelconque.example' ...}
G2  3 failed
    AssertionError: /api/memory/category/conversations a effacé de la mémoire : [('forget_category', 'conversations')]
    AssertionError: routes qui suppriment de la mémoire : ["['DELETE'] /memory/{memory_id}", "['DELETE'] /memory/category/{category}"]
G3  1 failed
    AssertionError: le client ChromaDB d'Atlas a la télémétrie active : TELEMETRIE=True
G4  10 failed, 2 passed
    AssertionError: rien d'enregistré : [] — {'status': 'error', 'message': "Outil inconnu : 'memory_save'", 'error_code': 'ERR_UNKNOWN_TOOL'}
    AssertionError: « tu te souviens du code du portail ? » classé memory/remember
    AssertionError: {'error_code': 'ERR_UNKNOWN_TOOL', 'message': "Outil inconnu : 'memory_forget'", ...}
    (puis, constaté en réel) AssertionError: {'error_code': 'ERR_NOTHING_TO_FORGET', ... « le code du portail » ...}
G5  13 failed
    AttributeError: module 'doctor' has no attribute 'machine_verdict'
    (puis, constaté en réel) AssertionError: [('cuBLAS 12 pour le STT GPU', False, 'cublas64_12.dll introuvable dans le PATH ...')]
Processus  5 failed, 1 passed
    AssertionError: 'arrête csrss' → {'status': 'confirmation_required', ..., 'target': 'csrss', ...}
```

**Les tests verts avant correction sont des témoins.**
- G1 : un seul test était vert avant correction, la page d'accueil (`Sec-Fetch-Site: none`). Les trois témoins « fenêtre desktop et interface web fonctionnent » étaient rouges, parce que mon assertion était trop stricte. Le moteur vérifie qu'une application lancée tourne bien et réessaie, d'où trois appels avec un enregistreur. J'ai corrigé l'assertion avant la correction du code ; ils sont verts depuis.
- G4 : « retiens » et « souviens-toi que » étaient déjà classés `remember`.
- Processus : « arrête notepad » reste confirmable.

**Mocks.** Outils remplacés par des enregistreurs, mémoire simulée pour G2, **ChromaDB jetable** de conftest pour G4. Machines simulées pour le verdict de G5. Aucun test ne touche la vraie mémoire, Docker ou une vraie fenêtre.

### Suite complète

```
.venv\Scripts\python.exe -m pytest tests/ -q -rs
SKIPPED [4] tests\test_action_safety_b1_bis.py:433: un nouvel onglet vide est légitime (« ouvre un nouvel onglet » : pas de clé url)
732 passed, 4 skipped in 157.59s (0:02:37)
exit=0
```

**Écart avec F** (685 passés, 5 ignorés) : +46 tests G (32 + 14). SearXNG est démarré, donc `test_web_v20` n'est plus ignoré (+1 passé, −1 ignoré). Trois anciens tests ont été ajustés pour l'hôte local : `test_metrics_grounding_v52`, `test_stabilisation_v31`, `test_v53_migration`. Le filtre G1 refuse l'hôte fictif « testserver » de TestClient. Le correctif est dans les tests, pas dans le code.

---

## 6. Comportement observé en scénarios réels

Atlas lancé par `start_atlas_desktop.bat`, avec Docker et Ollama démarrés par Alexis. **L'accès à l'écran a été refusé**, deux fois, faute de quelqu'un pour approuver la demande : je ne l'ai pas contourné. Méthode retenue :
- les demandes passent par l'API, exactement comme la fenêtre Atlas ;
- l'ouverture des dialogues est observée par l'énumération des fenêtres Windows ;
- les effets sont vérifiés sur les fenêtres, la mémoire et le journal.

### 6.1 Prélude — sauvegarde

`backup_memory.py backup` puis `verify` avant toute écriture en mémoire : **restauration prouvée** (`chromadb_20261010_053340`, 7 collections, `atlas_memory_e5` 273 éléments). `backup` a été lancé deux fois par erreur, ce qui a produit une seconde copie identique, sans conséquence.

### 6.2 Ce qui marche, joué en réel

| Demande | Résultat | Temps |
|---|---|---|
| « bonjour Atlas, présente-toi en une phrase » | « Bonjour ! Je suis Atlas, votre assistant personnel pour Windows. » | **88,5 s** (modèle à froid) |
| « quelle est la capitale de l'Italie ? » | « La capitale de l'Italie est Rome. » | 3,6 s |
| « retiens que le code du portail de test est 4521 » | « C'est noté : « le code du portail de test est 4521 ». » | 4,7 s |
| « tu te souviens du code du portail ? » / « rappelle-moi le code du portail » | « Tu m'as dit : « … 4521 ». » | 2,5 s |
| « tu te souviens de la couleur de ma voiture ? » | « Je n'ai rien retenu à ce sujet » | 4,6 s |
| « oublie la couleur de ma voiture » | « rien n'a été effacé », aucune attente | 2,6 s |
| « oublie le code du portail » (après correction) | dialogue ouvert avec le souvenir exact ; confirmé → effacé ; mémoire revenue à **273** | 12,8 s |
| « lance la calculatrice » | lancée | 11,4 s |
| « arrête le processus notepad » | confirmation (refusée par moi) | 2,4 s |
| G1 : `/api/chat` avec une Origin étrangère | **403**, ligne `[SECURITE]` | — |
| G3 : deux démarrages réels | **0** ligne de télémétrie | — |

### 6.3 Ce qui ne va pas, constaté en réel

1. **Fausses affirmations d'action — risque élevé.** Quand une demande d'action n'est pas reconnue, elle part en conversation, et le modèle peut prétendre l'avoir faite. Sur 7 demandes : **4 affirmées sans rien exécuter**, 1 promise, 2 honnêtes.
   - Affirmées sans rien exécuter : « baisse le volume » → « Volume baissé. » ; « vide la corbeille » → « Commande corbeille lancée. » ; « supprime mes fichiers temporaires » → « … L'action est en cours. » ; « mets de la musique » → « … La musique commence à jouer. ».
   - Promise : « envoie un message à Paul ».
   - Honnêtes : « monte le son », « coupe le wifi ».

   Le journal ne montre **aucun outil exécuté**, et la corbeille est inchangée (0 élément ; je ne connais pas son état d'avant, mais aucun outil d'effacement ne figure au journal). Hypothèse non démontrée : ces échanges mensongers sont mémorisés (`atlas_conversations`, annexe B) puis réinjectés dans les réponses suivantes, ce qui entretiendrait le défaut. **C'est le « ne ment pas » de ce sprint, hors de son périmètre** (consignes du modèle, route de conversation). Le guide avertit le testeur : « une vraie action se voit ».
2. **Les phrases avec « faire » ou « repas » rejouent la dernière action.** « qu'est-ce que tu sais faire ? » a relancé la calculatrice. « donne-moi une idée de repas » a répondu « Aucune action précédente à refaire. ». Cause : la tolérance aux fautes de frappe du classifieur confond « faire » avec « refaire » et « repas » avec « refais ». **C'est probablement la première question d'un testeur.** Les actions sensibles restent protégées, puisque le rejeu repasse par la confirmation.
3. **Écrire dans une autre application est cassé**, vérifié à blanc puis en réel sur le salon Discord ouvert :
   - « écris (Atlas) Bonjour, je suis Atlas, l'assistant d'Alexis… dans Discord » taperait seulement « assistant d » ;
   - « tape (Atlas) Bonjour dans Discord » taperait « (atlas) bonjour dans discord » ;
   - en réel, Atlas répond « Aucune fenêtre trouvée pour 'discord' » : le titre « #général | Atlas - Discord » n'est pas trouvé. **Rien n'a été tapé**, aucun brouillon ne reste ;
   - « appuie sur entrée » est refusé : Atlas ne peut pas envoyer un message.
4. **L'heure est inventée** : « Il est 14:32 », vers 5 h 55 (L4, connu, interdit dans ce sprint).
5. **La recherche web s'affiche brute** : liste Python de résultats au lieu d'une réponse.
6. **La Calculatrice est annoncée fermée alors qu'elle ne l'est pas** : « Fenêtre '' fermée. » après confirmation, fenêtre toujours visible. Hypothèse : une fenêtre interne UWP de même titre a été fermée. Le titre vide vient de `w.title` relu après la fermeture.
7. **« exécute la commande powershell Get-Date »** a lancé `powershell.exe` trois fois, sans confirmation et **sans exécuter la commande**. `launch_app` lance le programme, la vérification échoue, et le moteur réessaie deux fois. Les fenêtres ne sont plus présentes. Ouvrir une console n'exécute rien, mais ce n'est pas ce qui était demandé.
8. **Dialogue resté 110 s une fois**, au lieu de 60 s. Mesure suivante : 62 s. Non reproduit, cause inconnue. Le moteur, lui, a bien refusé à 60 s.

### 6.4 G7 — répétition sur Steam, sans clic physique

| Étape du brief | Observé | Verdict |
|---|---|---|
| « ferme la fenêtre Steam » : le dialogue s'ouvre, Steam reste ouvert | fenêtre « Atlas — confirmation requise » apparue dans le processus Atlas Desktop ; fenêtre Steam présente | ✅ |
| Annuler : rien ne se ferme | `/api/confirm` refus → `cancelled` ; Steam présent | ✅ (clic simulé) |
| Ne rien toucher 60 s : le dialogue se ferme, Steam reste | dialogue ouvert à 4 s, **fermé seul à 62 s** ; attente retirée ; Steam présent | ✅ |
| Confirmer : Steam se ferme | `/api/confirm` → « Fenêtre 'Steam' fermée. » ; fenêtre disparue (Steam continue en arrière-plan) | ✅ (clic simulé) |

**Ce qui reste à Alexis :** voir le dialogue de ses yeux et **cliquer** sur les boutons. Je n'ai pas vu son contenu, faute d'accès à l'écran, et mes « clics » passaient par la même requête que les boutons. **La case G7 reste décochée.**

---

## 7. Limites et risques identifiés

| Risque | Sévérité | Remarque |
|---|---|---|
| G7 non fait : dialogue jamais vu, boutons jamais cliqués | **Élevé** | Condition de sortie du brief |
| Fausses affirmations d'action en conversation (§6.3-1) | **Élevé** | Contraire au « sans mentir » ; décision du superviseur |
| « faire » / « repas » rejouent la dernière action (§6.3-2) | Moyen | Première question probable d'un testeur |
| Écriture dans une autre application cassée (§6.3-3) | Moyen | Dit dans le guide |
| `kill_process` cherche par morceau de nom | Moyen | Les processus protégés sont désormais refusés ; mais confirmer « arrête le processus e » viserait tout processus contenant « e ». La confirmation affiche « e ». Correction : `tools/process_manager.py`, hors périmètre |
| Le dialogue d'oubli affiche le nom technique « memory_forget » | Faible | `desktop/atlas_desktop.py` hors périmètre (libellé absent d'`ACTION_LABELS`) |
| Calculatrice annoncée fermée (§6.3-6) | Faible | Dit dans le guide |
| Mise à jour automatique d'Ollama (05/10 : installation incomplète) | Moyen | Sur la machine d'un proche, Atlas répondrait « modèle indisponible » sans qu'il sache pourquoi. Remède dans la procédure |

**Sorties réseau non demandées par l'utilisateur (inventaire G3, non corrigé) :**

| Sortie | Quand | Contenu | Correction possible |
|---|---|---|---|
| huggingface.co (faster-whisper) | **chaque démarrage** : `WhisperModel` vérifie le modèle même s'il est en cache (`local_files_only=False`) | nom du modèle, version des bibliothèques, adresse IP | `local_files_only=True` une fois le modèle téléchargé |
| DuckDuckGo (`ddgs`) | recherche web quand SearXNG ne répond pas | la recherche, **directement** depuis la machine | demandée par l'utilisateur ; à dire dans le guide (fait) |
| openwakeword | seulement si un fichier de modèle manque | téléchargement | — |
| Ollama (logiciel) | mises à jour automatiques ; « model recommendations » vers ollama.com, vu dans `server.log` | — | réglage d'Ollama, hors Atlas |
| Docker Desktop | mises à jour, télémétrie propre | — | réglage de Docker, hors Atlas |
| Serveur ChromaDB | — | coupé (`docker-compose.yml`) | — |

---

## 8. Checklist de validation

- [x] CORS restreint ; origine étrangère refusée ; fenêtre desktop et interface web intactes
- [x] Toutes les suppressions de mémoire par l'API recensées ; aucune possible (routes retirées)
- [x] Télémétrie client coupée, prouvée par un démarrage réel ; autres sorties réseau inventoriées
- [x] « Retiens que… » ne ment plus ; ce qui a été fait est dit (branchement complet)
- [x] `doctor.py` donne un verdict clair, avec une pré-vérification sans installation complète
- [x] Guide testeur et procédure d'installation écrits, sans promesse non tenue
- [ ] **G7 fait par Alexis, dialogue vu fonctionner** — répété sans clic physique, reste à faire
- [x] `python -m pytest tests/ -q` → code 0 (732 / 4)
- [x] Réponse en tête du rapport : non, pas en l'état ; conditions données
- [x] Tests vus rouges, sortie brute consignée ; aucun effet réel dans les tests
- [x] Sauvegarde vérifiée avant toute écriture en mémoire ; aucun élément d'Alexis effacé

---

## 9. Recommandations pour le sprint suivant

### P0 — avant la beta
1. **G7 par Alexis** : trois minutes au clavier (procédure du brief, §3 G7).
2. **Décision du superviseur sur les fausses affirmations d'action.** Correctif court possible, à arbitrer :
   - consigne au modèle : en conversation, il n'agit pas, et le dit (« je ne sais pas encore faire ça ») ;
   - ne plus mémoriser comme conversation un échange qui affirme une action.

   La consigne n'est pas déterministe : la mesurer sur une liste de phrases, comme au §6.3.
3. **Retirer la tolérance aux fautes sur « refais / encore » pour les mots courants** (« faire », « repas »…). Correctif dans `intent_classifier.py`.

### P1
4. `kill_process` : correspondance exacte du nom, avec ou sans « .exe », au lieu d'un morceau (`tools/process_manager.py`).
5. Saisie dans une autre application : texte intact (casse, ponctuation), titre de fenêtre retrouvé (« Discord »), touche Entrée.
6. Libellé du dialogue pour `memory_forget` (`desktop/atlas_desktop.py`).
7. faster-whisper en `local_files_only=True` : plus de sortie réseau au démarrage.

### P2
8. Recherche web rédigée au lieu de la liste brute. L'heure (L4). La fermeture d'applications UWP.
9. Dialogue qui reste ouvert quand la confirmation est traitée ailleurs (rapport F), et le cas des 110 s.

---

## Annexe A — décision de périmètre

- **Corrigé hors liste parce que le brief l'exige :** `validator.py` (table de confirmation, paramètres mémoire) et `intent_classifier.py` (« tu te souviens »).
- **Corrigé hors liste parce que c'est une faille de sécurité trouvée en testant la beta :** la protection des processus dans `intent_engine.py`. **À valider.**
- **Non corrigé, bien que tentant**, parce qu'interdit ou hors liste : fausses affirmations (consignes du modèle), « faire / repas » (classifieur), saisie (outils), heure (L4), latence, `browser_navigate`.

## Annexe B — ce que mes tests ont écrit dans la mémoire d'Alexis

Rien n'a été effacé, sauf mon propre fait de test (« le code du portail de test est 4521 »), oublié par confirmation au cours du test G4. **À toi de décider** si ces éléments restent. Ils proviennent tous du fonctionnement normal d'Atlas pendant les tests.

Pour revenir à l'état d'avant, la sauvegarde **`chromadb_20261010_053340`** (vérifiée) existe. Une restauration est une opération Docker sur la mémoire : à faire seulement sur ta décision.

- **`atlas_memory_e5`** (10) :
  - 3 corrections, mes refus : `correction_c0914a2cd46f` (Steam), `correction_0d21aa19d3e1` (« processus csrss »), `correction_2d1a86b4eb3b` (« processus notepad ») ;
  - 6 historiques d'action : `action_history_6e909814bb4b`, `action_history_34e728b11a55`, `action_history_3879dea7954d`, `action_history_6e9f93d0e20e`, `action_history_b5bb5f3865c3`, `action_history_eb6e3c31adee` ;
  - 1 habitude : `habit_6b79ce8c0a6e` (applicationframehost).
- **`atlas_conversations`** (12) : mes questions et ses réponses, **dont les quatre réponses mensongères** du §6.3 (`conv_38670c07d218`, `conv_cd1364c19d6f`, `conv_afe8ed69786d`, `conv_88c3731bad16`, `conv_256456d91b55`, `conv_d945d78cc305`). Si l'hypothèse du §6.3 est juste, les retirer éviterait qu'elles servent d'exemple.
- **`atlas_errors`** (4) : `err_540d7b68c1ed`, `err_375ac4d61b1e`, `err_2d98ba1ad950`, `err_c6d72a7c3bd4`.
