# RAPPORT SPRINT FIABILITÉ — La bonne route, une seule fois
Date: 15/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_FIABILITE.md`. Branche **`sprint-fiabilite`**, issue de `main` @ `dd6ad21` (Check-up fusionné). Commits non poussés.
> Accords d'Alexis (brief, 15/10) : télécharger torch CUDA dans un environnement jetable ; supprimer `qwen2.5:14b`, `mistral` et DialoGPT, garder `minicpm-v`.

---

## Tableau de tête

| | Avant | Après |
|---|---|---|
| **Bonnes routes** sur le corpus (232 demandes) | **183 / 232 — 78,9 %** | **231 / 232 — 99,6 %** |
| **Routes vers une action à tort** | **7** | **0** |
| Contrôle « hors corpus » : 40 demandes écrites après les corrections, jamais vues | — | 35 / 40 au premier passage (87,5 %) ; 39 / 40 après correction générale |
| **« ouvre la calculatrice »** : instances ouvertes | **3** (Check-up, D26) | **1** ; redemandée : ramenée, toujours 1 |
| Suite `pytest tests/` | 1 062 passés | **1 114 passés, 0 ignoré** ; sans Ollama 1 111 + 3 ignorés justifiés |
| GB1 (34 demandes d'action) | 0 affirmation, 28 réponses fixes | **0 affirmation, 32 réponses fixes** |

---

## 1. Résumé exécutif

**Statut global : VALIDÉ** (sous réserve du superviseur). **FI6** : les suppressions ont été refusées par le classifieur de sécurité de la session ; je ne l'ai pas contourné, **Alexis les a lancées lui-même** (§6.7).

**Runtime :** Ollama 0.40.3, **mis à jour tout seul en 0.40.4** au redémarrage pendant la suite « sans Ollama » (GB1 mesuré en 0.40.3) ; mémoire réelle jamais ouverte par Atlas (copies) ; deux écrans 1920 × 1080 à 100 %.

**Chiffres :**
- **FI1/FI2** : corpus permanent de **232 demandes** (11 familles, 12 à 38 par famille) ; **78,9 % → 99,6 %**, **7 → 0 actions à tort** ; le taux est un plancher qui ne peut que monter. Le classifieur reste déterministe.
- **FI3** : un lancement n'est **jamais rejoué** ; la vérification reconnaît les applications Windows modernes ; un échec est dit. Rejeu réel : Calculatrice 1 instance, puis ramenée ; Bloc-notes 1 fenêtre.
- **FI4** : limites des déclencheurs lues dans la configuration et appliquées **partout** (elles n'étaient appliquées qu'à la création — le rapport Check-up disait à tort « aucune limite »).
- **FI5** : EasyOCR GPU **mesuré avec le modèle chargé** : fenêtre 0,12 s (processeur 0,79 s), écran 1080p 1,78 s (10,0 s), mais **+1,63 Go de VRAM** (carte à 7,7 / 8,15 Go). Environnement jetable supprimé : **4,7 Go libérés**.
- **FI7** : faster-whisper absent → bascule annoncée au démarrage.
- **FI7 bis** : écrans relevés ; le **x = −1482 expliqué** (ancienne disposition, écran à gauche, prouvé par le journal du 10/04) ; lecture et clic justes sur l'écran 1, l'écran 2 et à cheval.
- **Trouvés en chemin et corrigés** : ChromaDB 1.5.1 qui refuse de lire une collection (filet, pas une correction — §7.2) ; « ouvre les paramètres » qui cliquait dans l'application au premier plan ; « mets X au premier plan » qui visait la fenêtre de l'action précédente ; un clic en cache sans fenêtre visée ; deux caractères de contrôle dans le code.

---

## 2. Objectifs vs réalisation

| Objectif (brief) | Résultat réel | Statut |
|---|---|---|
| FI0 — Check-up fusionné, suite verte | fusionné ; suite : 1 061 + **1 échec intermittent** (`test_sd3_…alteree`), cause trouvée (ChromaDB, §4.1) | PASS |
| FI1 — corpus ≥ 150, ≥ 10 par famille, variantes (possessifs, accents, fautes, politesse, voix) | 232 demandes, 11 familles (min. 12) ; `tests/fixtures/corpus_routes.json` | PASS |
| FI1 — phrases obligatoires (5 du Check-up, 2 de G-bis, sessions d'Alexis, demandes impossibles) | toutes présentes (test) ; 38 demandes « réponse honnête » | PASS |
| FI1 — ligne de base par famille, liste des erreurs | 183 / 232, par famille §6.1, 49 erreurs listées (`fi1_base_final.json`) | PASS |
| FI2 — les 5 règles du Check-up | URL d'abord ; « … en cours » → processus ; « tâches » → planification ; « rappelle-moi de… à 15 h » → planifier (confirmé) ; question sur un fait → rappel | PASS |
| FI2 — le reste du corpus ; déterministe ; règles tenues sur les variantes | 99,6 % ; règles sur texte sans accents ; contrôle hors corpus 35/40 puis 39/40 | PASS |
| FI2 — ≥ 95 %, **aucune action à tort**, gravité dite, test permanent, taux qui ne peut que monter | 99,6 %, 0 ; plancher `corpus_routes_plancher.json` | PASS |
| FI3 — jamais de relance ; applications modernes reconnues ; échec dit | tests ; rejeu réel §6.3 | PASS |
| FI3 — rejeu : Calculatrice, Bloc-notes, Paramètres, application déjà ouverte | fait ; Paramètres déjà ouvert chez Alexis : ramené ou refus dit, jamais rouvert (§6.3) | PASS |
| FI4 — limites appliquées, déterministes ; dans la configuration, lues (CK3) ; blocage journalisé et visible | création, chargement, réactivation, évaluation ; `report_automation_block` (journal, journal d'actions, notification) | PASS |
| FI5 — torch cu128 dans un environnement jetable ; mesures avec le modèle chargé ; rafales 10 fenêtres et 10 écrans ; VRAM ; RAM ; taille | tout mesuré (§6.5) ; **torch 2.11.0+cu128** (l'index cu128 ne publie pas 2.12.1) | PASS |
| FI5 — trois options chiffrées, recommandation, choix inchangé ; environnement supprimé, place dite | §6.5 ; 4,7 Go libérés | PASS |
| FI6 — `qwen2.5:14b`, `mistral`, DialoGPT supprimés ; `minicpm-v` gardé ; avant/après | liste avant (15,1 Go) ; suppression refusée à la session, **lancée par Alexis** ; après : `ollama list` = `qwen2.5:7b`, `minicpm-v` ; `doctor.py --composants` inchangé pour Atlas (§6.7) | PASS |
| FI7 — faster-whisper absent : bascule annoncée, test rouge d'abord | `stt_absent`, vérifiée au démarrage du moteur vocal et à la première phrase | PASS |
| FI7 bis — disposition relevée ; x = −1482 expliqué ; capture limitée à la fenêtre ; rejeu écran 1, écran 2, à cheval | §6.4 | PASS |
| FI8 — rapport, suites, GB1, C3, bascules, rejeu réel | ce rapport | PASS |

---

## 3. Architecture projet mise à jour

```
core/
├── intent_classifier.py      ← FI2 : règles prioritaires (processus, tâches, rappel, fait retenu, « comment »),
│                                accents facultatifs, déclencheurs courts en mot entier, URL avant l'écran,
│                                lire sans URL → conversation, réglages système → réponse honnête,
│                                « nettoie » limité au système, paramètres sans premier plan, raccourci sans fenêtre
├── validator.py              ← premier plan : la dernière fenêtre ne remplace plus une fenêtre nommée
├── intent_engine.py          ← FI3 : _verifier_lancement (jamais de relance), LANCEMENT_ATTENTE_S
├── trigger_engine.py         ← FI4 : limites lues dans la configuration, appliquées partout
├── memory_manager.py         ← FI0 : lecture avec reprise (client rouvert) et bascule signalée
└── voice_engine.py           ← FI7 : verifier_transcription()
core_conversational/degradations.py ← bascules memoire_partielle, stt_absent
tools/
├── app_launcher.py           ← FI3 : processus et titres des applications modernes, instantane(), apparu_depuis()
├── window_controller.py      ← FI3 : la fenêtre de contenu hébergée (CoreWindow) n'est plus un doublon
├── grounding.py              ← FI7 bis : pas de clic en cache sans fenêtre visée trouvée
└── browser_bridge.py         ← caractère de contrôle littéral remplacé par son échappement
config/settings.json          ← automation.max_active_triggers, min_cooldown_seconds (lues)
scripts/
├── mesure_routes.py          ← NOUVEAU : route d'une demande sans rien exécuter ; mesure du corpus
├── rejeu_fiabilite.py        ← NOUVEAU : rejeu réel (phrases, applications, deux écrans)
├── ecrans.py                 ← NOUVEAU : disposition des écrans et conscience DPI
├── mesure_easyocr.py         ← modèle chargé, rafales, VRAM, le modèle reste-t-il sur la carte
├── backup_memory.py          ← relevé refait avec un client neuf si ChromaDB refuse de lire
└── doctor.py                 ← transcription : bascule stt_absent
tests/
├── test_fiabilite.py         ← NOUVEAU : 52 tests
├── fixtures/corpus_routes.json, corpus_routes_plancher.json ← NOUVEAUX
├── test_sans_docker.py       ← fixture SD3 : base relue avant le test de sauvegarde
└── test_v601_patches.py      ← paramètres : plus de premier plan (changement de décision, §7.4)
docs/CONFIGURATION.md         ← clés d'automatisation revenues ; correction du rapport Check-up
docs/rapports/RAPPORT_SPRINT_FIABILITE.md ← NOUVEAU
```

---

## 4. Détail des implémentations

### 4.1 FI0 — l'échec intermittent, et ce qu'il cachait
La suite de base a échoué une fois sur `test_sd3_une_sauvegarde_alteree_est_refusee` : « hnsw segment reader: Nothing found on disk ». Reproduit hors test : **ChromaDB 1.5.1 refuse parfois de lire une collection d'une base fraîchement écrite**, selon l'ordre des lectures (environ 1 ouverture sur 10 ; une requête seule n'a jamais échoué sur 80 ouvertures ; un `get` ou un `count` d'abord, si). **Atlas l'a subi le 14/10** : 11 erreurs « retrieve partition 'conversations' » au journal, une session entière sans rappel des conversations.
- Ce qui n'a **pas** marché, mesuré : sonder à l'ouverture (la sonde déclenchait le défaut), une passe de « réparation » par requêtes (7 échecs sur 80). Retiré.
- Ce qui reste : `MemoryManager._interroger` — toute lecture (`query`, `get`) en échec « hnsw segment reader » rouvre le client et recommence **une fois** ; si la reprise échoue, bascule `memoire_partielle` signalée (journal, health, doctor, dite). `backup_memory.summarize` refait son relevé avec un client neuf (3 essais). Le test SD3 part d'une base que ChromaDB relit (il teste la sauvegarde, pas ChromaDB).
- **Ce n'est pas une correction du défaut** : c'est un filet. P1 en §9.

### 4.2 FI1 — `scripts/mesure_routes.py` et le corpus
`route(phrase)` suit le chemin d'`/api/chat` (classifieur → conversation | plan | validateur → outil) avec un contexte fixe, sans rien exécuter. Routes : outil, conversation, honnête, fixe, refus, plan. `gravite()` : **« action à tort »** = un outil **qui agit** (ou un plan) quand on attendait une conversation, une réponse honnête, fixe ou un refus. Un outil de **lecture seule** (rappel, description de mode, listes, diagnostic, lecture d'écran) sur une mauvaise route reste une erreur, de gravité ordinaire — définition dite ici parce qu'elle compte dans le « 0 ».

### 4.3 FI2 — le classifieur (déterministe)
- **Texte sans accents** pour les règles et la table des verbes (« demarre », « reduis », « taches »).
- **Déclencheurs de 4 lettres ou moins en mot entier** : « lis » n'est plus trouvé dans « liste » (cause de 3 erreurs du Check-up).
- **Règles prioritaires** (`_regles_fiabilite`) : « comment … » → conversation ; processus (« liste/montre/quels … programmes/applications … en cours/ouverts/tournent ») ; tâches (« liste/montre/quelles … tâches », sans verbe d'ajout) ; **« rappelle-moi de … »** → planifier, avec ses paramètres : **une notification à l'heure dite** (avant : la tâche planifiée **lançait Steam toutes les 24 h**, quelle que soit la demande) ; **question sur un fait** (« quel est / c'est quoi / c'est quand … mon/ma/mes … », sauf ce qui concerne l'ordinateur) → rappel.
- **URL** : passe avant la lecture d'écran ; « ouvre / va sur … URL » → ouvrir, « … onglet » → onglet, sinon lire.
- **Lire ou résumer sans URL** → conversation (« résume l'histoire de Rome »).
- **Réglages, extinction, redémarrage, veille** → réponse honnête : aucune phrase n'en donne les paramètres, `system_config` les recevait vides ; **« éteins l'écran » éteignait le PC** (avec confirmation).
- **« nettoie »** ne lance le nettoyage que pour le système (« nettoie mon bureau » → honnête).
- **Raccourci** : « appuie sur ctrl+s » prenait « ctrl+s » pour une fenêtre → refus, comme toute frappe sans fenêtre nommée.
- **« ouvre les paramètres »** sans application nommée → paramètres de Windows, **jamais l'application au premier plan** (§7.4).
- `validator.py` : « mets X au premier plan » ne prend plus la fenêtre de l'action précédente quand X est nommé.

### 4.4 FI3 — un lancement, une instance
`ExecutionEngine._verifier_lancement` : instantané (processus, fenêtres) avant le lancement ; ensuite on attend (8 s au plus) une **nouvelle fenêtre ou un nouveau processus** de l'application ; sans trace : « J'ai lancé Calculatrice, mais je ne vois pas sa fenêtre. », `verification_failed`, **aucune relance**. `app_launcher` connaît les processus (`CalculatorApp`, `SystemSettings`, `notepad`) et titres (« Calculatrice », « Paramètres ») des applications modernes ; `_is_process_running` et `_app_windows` (chemin GT4) s'en servent. `window_controller._list_visible_windows` ignore la fenêtre de contenu `Windows.UI.Core.CoreWindow`, que son cadre `ApplicationFrameWindow` porte déjà au même titre (deux « Paramètres » faisaient refuser le premier plan).

### 4.5 FI4 — limites des déclencheurs
`MAX_ACTIVE_TRIGGERS` et `MIN_COOLDOWN_SECONDS` lus dans `automation` (20 et 60). Appliqués : à la **création** (existait) ; au **chargement** de `triggers.json` (au-delà du maximum : bloqué, signalé, fichier intact) ; à la **réactivation** (refusée au-delà du maximum) ; à **chaque évaluation** (jamais sous le délai minimum, même si le fichier dit 0). Tout blocage passe par `report_automation_block` : journal, ligne `ERR_AUTOMATION_BLOCKED` du journal d'actions, notification.

### 4.6 FI7 — faster-whisper absent
`voice_engine.verifier_transcription()` au démarrage du moteur vocal (avant l'annonce des bascules) et `_transcribe` à la première phrase : bascule `stt_absent`, vécue, dite (« Ma transcription (faster-whisper) est absente… »). `doctor.py --composants` la montre.

### 4.7 FI7 bis — deux écrans
`scripts/ecrans.py` (API Windows). Cache de clics : fenêtre visée introuvable ou erreur → **pas de clic** (avant : clic aux coordonnées gardées) ; point hors bureau virtuel → pas de clic. La capture (Tesseract, EasyOCR, lecture d'écran) prend le bureau virtuel entier puis **ne garde que la fenêtre visée** (`_capture_window_screenshot`) — vérifié correct, inchangé.

### 4.8 Garde ajoutée
`test_aucun_caractere_de_controle_dans_le_code` : deux retours arrière (`\x08`) s'étaient glissés dans le classifieur à la place de `\b` (le premier désactivait la règle « comment » en silence), et un `\x01` littéral dormait dans `browser_bridge.py` depuis le 19/09 (remplacé par son échappement, docstring identique).

---

## 5. Résultats des tests

### 5.1 Commandes et résultats (version finale)
```
.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
```
```
Avec Ollama : 1114 passed in 277.65s (0:04:37) — atlas: tests ignorés : 0 — code 0
Sans Ollama : 1111 passed, 3 skipped in 289.90s (0:04:49) — 3 justifiés, 0 fautif — code 0
```
Les 3 ignorés sans Ollama : `test_honesty_gbis::test_gb1_vrai_modele…` (vrai modèle), `test_sprint_kimi…::test_grounding_layer_order_steam…` (modèles installés), `test_vision_parsers::…test_layer_timeout_aborts_slow_layer` (sonde du port fermé). Avant le sprint : 1 062. Écart : +52 (`test_fiabilite.py`) ; `test_checkup.py` inchangé (45).

### 5.2 Non-régression
Les 50 fichiers `test_*.py` passent dans les deux runs. Modifiés : `test_sans_docker.py` (fixture SD3, §4.1) ; `test_v601_patches.py::test_settings_via_foreground_when_app_implicit` — **décision inversée** (§7.4). Une suite intermédiaire (après FI2, sans `test_fiabilite`) : 1 062 passés, aucune régression des tests existants par les règles du classifieur.

### 5.3 Rouge d'abord
Chaque test de `test_fiabilite.py` a été lancé rouge avant le code (FI0 lecture, FI2, FI3, FI4, FI7, FI7 bis, premier plan, applications modernes, paramètres). **Exceptions, dites :**
- les 3 tests du corpus lui-même (`test_fi1_*`) sont passés dès leur écriture : ils vérifient le fichier de données, écrit juste avant ;
- `test_aucun_caractere_de_controle_dans_le_code` a été écrit **après** la découverte du défaut (c'est une garde) ;
- trois tests d'ouverture « saine » de ChromaDB, rouges puis verts, ont été **retirés** avec le code qu'ils testaient (sonde nuisible, §4.1).

---

## 6. Comportement observé en scénarios réels

### 6.1 Corpus, par famille (232 demandes, contexte fixe)
| Famille | Demandes | Avant | Après |
|---|---|---|---|
| aide | 14 | 13 (92,9 %) | 14 (100 %) |
| applications | 19 | 17 (89,5 %) | 19 (100 %) |
| conversation | 29 | 25 (86,2 %) | 28 (96,6 %) |
| écran | 12 | 12 (100 %) | 12 (100 %) |
| écrire ailleurs | 17 | 16 (94,1 %) | 17 (100 %) |
| fenêtres | 22 | 19 (86,4 %) | 22 (100 %) |
| réponse honnête | 38 | 32 (84,2 %) | 38 (100 %) |
| internet | 20 | 14 (70,0 %) | 20 (100 %) |
| mémoire | 22 | 14 (63,6 %) | 22 (100 %) |
| modes et planification | 23 | 12 (52,2 %) | 23 (100 %) |
| système | 16 | 9 (56,2 %) | 16 (100 %) |
| **Total** | **232** | **183 (78,9 %)** | **231 (99,6 %)** |

**Les 7 actions à tort d'avant** : « appuie sur ctrl+s », « résume l'histoire de Rome » (×2 variantes), « règle la luminosité au maximum », **« éteins l'écran »** (extinction du PC), « ajoute du lait à ma liste de courses » (lecture d'une « URL » inventée), « résume-moi la révolution française ».
**L'erreur restante** : « c'est quoi mon horoscope du jour ? » → rappel mémoire (lecture seule : « Je n'ai rien retenu à ce sujet »), attendu en conversation.
**Surapprentissage, mesuré** : les 40 demandes hors corpus, écrites après les corrections, donnaient 35/40 ; les 5 échecs (« c'est quand mon anniversaire », « le mot de passe de mon wifi », « qu'est ce que tu sais faire » sans trait d'union, « comment je peux voir les processus », l'horoscope) ont été corrigés par des règles générales, et les 40 ajoutées au corpus.

### 6.2 Rejeu réel au clavier — les 7 phrases (Atlas réel, copie de la mémoire)
| ID | Demande | Attendu | Observé | Statut |
|---|---|---|---|---|
| R1 | « quel est le numéro de mon essai de check-up ? » | rappel | `memory_recall` (« rien retenu », copie sans ce fait) | PASS |
| R2 | « résume la page https://example.com » | lecture de la page | `read_url` : « Résumé de 'Example Domain' prêt » | PASS |
| R3 | « liste les programmes en cours » | processus | `list_processes` | PASS |
| R4 | « liste mes tâches planifiées » | planification | `schedule_list` : 2 tâches | PASS |
| R5 | « rappelle-moi de boire de l'eau tous les jours à 15h » | planifier, confirmation | confirmation demandée, **annulée par moi** | PASS |
| R6 | « ajoute du lait à ma liste de courses » | réponse honnête | « Je ne sais pas encore faire ça. » | PASS |
| R7 | « résume l'histoire de Rome » | conversation | résumé par le modèle, aucun outil | PASS |

### 6.3 FI3 — applications, instances comptées après chaque demande
| Demande | Avant (Check-up) | Observé | Statut |
|---|---|---|---|
| « ouvre la calculatrice » | 3 instances | 1 processus `CalculatorApp`, 1 fenêtre | PASS |
| « ouvre la calculatrice » (déjà ouverte) | — | « Calculatrice était déjà lancé : je ramène sa fenêtre » ; toujours 1 | PASS |
| « ouvre les paramètres » (Paramètres **déjà ouvert** chez Alexis) | — | 1er rejeu : refus « plusieurs fenêtres » (cadre + contenu) ; corrigé ; 2e rejeu : une seule fenêtre vue, **Windows a refusé le premier plan**, dit ; **jamais rouvert** | PASS (avec limite §7.5) |
| « ouvre le bloc-notes » (aucun Bloc-notes ouvert avant) | — | 1 fenêtre (2 processus `notepad.exe` : lanceur et application de Windows 11) | PASS |

Fenêtres ouvertes par le rejeu (1 Calculatrice, 1 Bloc-notes) fermées par le script ; rien d'autre touché.

### 6.4 FI7 bis — deux écrans
**Disposition réelle** (`scripts/ecrans.py`) : écran principal `DISPLAY2` à (0, 0), 1920 × 1080, 100 % ; écran secondaire `DISPLAY1` à **(1920, 0) : à droite**, 1920 × 1080, 100 %. Même mise à l'échelle : pas de cas « échelles différentes » à tester. Atlas est « conscient du DPI système » (pyautogui le règle à l'import) : coordonnées physiques.

**Le x = −1482** : 9 souvenirs `action_history` du **10/04** (« Clic heuristique Steam 'bibliothèque' à (−1482, 80) », puis le cache). Le journal du même jour donne la fenêtre de Steam à **rect = (−1928, −7, 1936, 1096)** : agrandie sur un écran dont le bord gauche était à x = −1920. **Il y avait alors un écran à gauche du principal** : ancienne disposition, pas une erreur de conversion ni de mise à l'échelle. Vérification : l'heuristique place y = haut + 8 % de la hauteur = −7 + 87,7 → **80**, exactement ; x correspond à 23 % de la largeur (−1482,7), le code d'aujourd'hui dit 22 % (−1502) — changement antérieur au début de l'historique git (17/09), non vérifiable.

| Fenêtre de test | Position | « lis l'écran » | « clique sur Bibliothèque » | Clic reçu par la fenêtre | Statut |
|---|---|---|---|---|---|
| écran 1 | (300, 300) | « Bibliothèque » lu | OCR, 96 % | (538, 418) | PASS |
| écran 2 | (2300, 300) | « Bibliothèque » lu | OCR, 96 % | **(2538, 418)** | PASS |
| à cheval (1690–2166) | (1690, 600) | 1er rejeu : lu ; 2e : le modèle dit le texte « mal lu » | OCR, 96 % | **(1928, 718)**, au-delà de la frontière | PASS (lecture variable) |

Une fenêtre à cheval est capturée sur ses deux moitiés (le bureau virtuel couvre les deux écrans) ; le clic tombe juste ; la lecture de la petite fenêtre a varié d'un passage à l'autre.

### 6.5 FI5 — EasyOCR sur GPU contre processeur, modèle de langue chargé
`scripts/mesure_easyocr.py`, images synthétiques, `qwen2.5:7b` chargé (4,76 Go, entier sur la carte avant et après dans les deux cas).

| | Processeur (torch 2.12.1, venv d'Atlas) | GPU (torch 2.11.0+cu128, venv jetable) |
|---|---|---|
| Premier usage : démarrage + 1re lecture | 11,7 s + 0,8 s | **19,1 s + 15,0 s** ; 2e lancement : 11,1 s + 15,1 s (compilation CUDA à chaque redémarrage du processus) |
| 10 fenêtres d'affilée (460 × 220) | médiane **0,79 s**, total 8,3 s | médiane **0,12 s**, total 1,2 s |
| 10 écrans 1080p d'affilée | médiane **10,0 s**, total 100 s | médiane **1,78 s**, total 19,1 s |
| VRAM ajoutée | 16 Mo (bruit) | **+1 627 Mo** — carte à **7 689 / 8 151 Mo** |
| Le modèle de langue reste entier sur la carte | oui | oui, **sans la transcription d'Atlas** (+~0,2 Go en usage vocal) |
| RAM du processus OCR | 0,55 Go (fenêtres), **2,7 Go** après les écrans 1080p | 1,2 à 1,3 Go |
| Installation | ~0,8 Go (torch 526 Mo + OpenCV, scikit-image…) | venv jetable **4,7 Go** (téléchargement ~3 Go) |

| Option | Gain | Coût | Pour un usage fréquent (lectures en rafale) |
|---|---|---|---|
| (a) GPU | 6 à 7 fois plus rapide | **~0,25 Go de VRAM restants** une fois la voix active : le moindre autre usage de la carte (jeu, navigateur) ferait déborder le modèle de langue sur le processeur ; 26 à 34 s à chaque premier usage ; +4 Go installés ; rien chez un proche sans NVIDIA | rapide, mais sur une carte de 8 Go, la marge n'existe pas |
| (b) processeur (aujourd'hui) | aucune VRAM ; marche partout | 0,8 s par fenêtre ; 10 s par écran entier ; jusqu'à 2,7 Go de RAM | **acceptable** : la décision d'Alexis (fenêtre visée seulement) rend le cas courant 0,8 s, pas 10 s |
| (c) retiré, avec torch | ~0,84 Go de venv, pas de RAM d'OCR | 17 % des clics réels réussis perdus (Discord) ; lecture d'écran sans repli ; repli des embeddings perdu | **à exclure** si la lecture d'écran devient centrale |

**Recommandation : (b) maintenant** ; **(a) seulement avec une carte de 12 Go ou plus**. Avec 8 Go, le gain de vitesse se paierait en fiabilité du modèle de langue. **Aucun changement de choix.** Environnement jetable supprimé : **4,7 Go libérés** (40 → 45 Go libres). Le cache de pip (8,8 Go, dont ~3 Go de ce téléchargement) n'est pas touché : il sert à tous les projets Python d'Alexis (`pip cache purge` s'il le veut).

### 6.6 GB1, bascules, règle C3
- **GB1** (vrai modèle 0.40.3, mémoire en lecture seule) : 34 demandes d'action, **0 affirmation**, 32 réponses fixes, 2 descriptions de mode inconnu (« active le mode avion / sombre » : « Je ne connais pas de mode… », lecture seule) ; 20 questions ordinaires, **0 bloquée**.
- **Aucune bascule silencieuse** : 2 nouvelles bascules au catalogue (`memoire_partielle`, `stt_absent`), branchées et testées ; `/api/health` : aucune bascule active pendant les deux rejeux.
- **C3** : mémoire réelle 276 / 489 / 20 / 19 / 8 / 0 / 0, **identique** ; scénarios sur copies ; GB1 en lecture seule ; recherche du x = −1482 en lecture seule. `data/habits.db` remis tel quel après chaque rejeu ; autres fichiers de `data/` inchangés. **Aucune trace à retirer.**

### 6.7 FI6 — ménage décidé par Alexis
| | Avant | Après |
|---|---|---|
| Modèles Ollama | `qwen2.5:7b` 4,7 Go, `minicpm-v` 5,5 Go, `qwen2.5:14b` 9,0 Go, `mistral` 4,4 Go | `qwen2.5:7b`, `minicpm-v` |
| Cache Hugging Face | `faster-whisper-base`, `multilingual-e5-base`, `DialoGPT-medium` 1,7 Go | `faster-whisper-base`, `multilingual-e5-base` |
| Place libre sur C: | 45 Go | **59 Go** |

Commandes refusées à la session, lancées par Alexis (`ollama rm` ×2, `Remove-Item` du dossier DialoGPT). `doctor.py --composants` après : inchangé pour Atlas (Ollama : `minicpm-v`, `qwen2.5:7b`).

---

## 7. Limites et risques identifiés

| # | Description | Sévérité | Mitigation |
|---|---|---|---|
| 1 | Les suppressions de FI6 ont été refusées par le classifieur de sécurité de la session ; Alexis les a lancées lui-même. | Faible | Fait (§6.7). |
| 2 | **ChromaDB 1.5.1** refuse parfois de lire une collection d'une base fraîchement écrite (~1 ouverture sur 10, selon l'ordre des lectures). Filet en place (reprise, bascule signalée), **pas de correction**. | Élevé | P1 : tester une version plus récente de ChromaDB sur une copie, ou signaler le défaut en amont. |
| 3 | Le corpus a servi à écrire les règles : 99,6 % dessus ; **87,5 % sur 40 demandes neuves** au premier passage. Le vrai taux sur des phrases inconnues est entre les deux. | Moyen | Continuer d'ajouter au corpus les phrases réelles mal routées ; le plancher empêche de reculer. |
| 4 | **Changement de décision** : « ouvre les paramètres » avec Discord au premier plan ouvrait les paramètres de Discord (v6.0.1, P1) ; il ouvre désormais ceux de Windows. Raison : au rejeu, la même phrase cliquait dans VS Code ; même règle que B1-bis (« jamais le premier plan »). À la voix, l'ancien comportement pouvait être voulu. | Moyen | Validation du superviseur demandée ; « paramètres de Discord » reste un clic dans Discord. |
| 5 | Ramener une fenêtre au premier plan peut être refusé par Windows (verrou du premier plan) : Paramètres au 2e rejeu. Dit honnêtement, jamais rouvert. | Faible | Connu de GT4 ; à suivre si fréquent. |
| 6 | Un arrêt propre sur 5 (2e rejeu) a dépassé 60 s après « Shutting down » d'uvicorn (connexion restée ouverte ?) ; arrêt forcé, aucun processus orphelin, fichiers remis en état. | Faible | P2 : borner l'attente d'uvicorn (`timeout_graceful_shutdown`). |
| 7 | Ollama s'est mis à jour seul en 0.40.4 au redémarrage ; `doctor.py` a 0.40.3 pour référence (avertissement). | Faible | Remesurer GB1 en 0.40.4 au prochain sprint ; relever la référence. |
| 8 | « c'est quoi mon horoscope du jour ? » va au rappel mémoire (lecture seule) au lieu de la conversation. | Faible | Laissé en erreur visible dans le corpus. |
| 9 | Le rapport Check-up disait « aucune limite appliquée » aux déclencheurs : faux, elles l'étaient à la création (20, 60, en dur). Corrigé ici et dans `docs/CONFIGURATION.md`. | Faible | — |
| 10 | La lecture d'une petite fenêtre à cheval sur deux écrans a varié d'un passage à l'autre (clic toujours juste). | Faible | Observer en usage réel. |

---

## 8. Checklist de validation

- [x] Corpus de 150 demandes ou plus, ligne de base par famille (§6.1)
- [x] ≥ 95 % de bonnes routes ; aucune route vers une action à tort ; le corpus est un test permanent (99,6 %, 0 ; `test_fi2_*`, plancher)
- [x] Les 5 phrases du Check-up et les 2 de G-bis passent, en réel (§6.2)
- [x] Une seule instance par demande ; échec de vérification dit, sans relance (§4.4, §6.3, `test_fi3_*`)
- [x] Limites d'automatisation appliquées et testées (`test_fi4_*`)
- [x] EasyOCR GPU mesuré avec le modèle chargé ; trois options chiffrées ; environnement jetable supprimé (§6.5)
- [x] `qwen2.5:14b`, `mistral` et DialoGPT supprimés ; `minicpm-v` gardé (par Alexis, la session ayant refusé ; §6.7)
- [x] faster-whisper absent : bascule annoncée (`test_fi7_*`)
- [x] Deux écrans : disposition relevée ; le x = −1482 expliqué ; lecture et clic justes sur l'écran 1 et l'écran 2, limités à la fenêtre visée (§6.4)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; GB1 à 0 (§5.1, §6.6)

---

## 9. Recommandations pour le sprint suivant

**P1 — fiabilité**
- ChromaDB 1.5.1 (§7.2) : essayer une version plus récente sur une copie de la mémoire (les 40 requêtes du garde-fou, `backup` / `verify`) ; sinon signaler le défaut en amont.
- Valider ou annuler le changement de décision sur « ouvre les paramètres » (§7.4).
- Ajouter au corpus chaque phrase réelle mal routée (journaux des sessions d'Alexis).

**P2 — robustesse**
- Borner l'arrêt d'uvicorn (§7.6).
- Planification : jours de la semaine et « dans 10 minutes » (aujourd'hui : heure fixe chaque jour, sinon toutes les 24 h).
- Remesurer GB1 sur Ollama 0.40.4 ; mettre à jour la référence de `doctor.py`.

**P3 — performance**
- EasyOCR : garder (b) ; reconsidérer (a) sur une carte de 12 Go ou plus.
- `pip cache purge` (8,8 Go) si Alexis veut la place.
