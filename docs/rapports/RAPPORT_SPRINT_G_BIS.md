# RAPPORT SPRINT G-BIS — Atlas ne prétend plus agir, et sait écrire ailleurs
Date: 10/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_G_BIS.md`. Références : rapport G (§6.3, §7, §9, annexe B).
> Branche **`sprint-g-bis`**, issue de `main` @ `1e92619`. 7 commits, plus celui de ce rapport, **non poussés**.

---

> **La beta est-elle possible ? Oui, dès que G7 est fait par Alexis**, au clavier, en trois minutes. C'est la seule case du brief qui reste ouverte, et personne ne peut la cocher à sa place. Tout le reste est fait, testé, et prouvé sur le vrai modèle ou en réel.

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.** Les huit tâches sont faites, sauf G7, qui revient à Alexis par construction.

| Tâche | Avant | Après | Preuve |
|---|---|---|---|
| **GB1** fausses affirmations | **15 demandes d'action sur 34** affirmées ou promises sans aucun outil (vrai modèle) | **0 sur 34** transmise ; 0 faux positif sur 20 questions ordinaires | mesure avant / après sur le vrai modèle ; 102 tests, dont 41 sur ses vraies réponses étiquetées |
| **GB2** « faire » / « repas » | 13 phrases ordinaires sur 14 rejouaient la dernière action | 0 ; « refais », « refoit », « encore une fois » marchent toujours | 31 tests |
| **GB3** arrêt de processus | « e » visait tout processus contenant un « e » | nom exact ; la confirmation nomme les PID ; rien proposé sans correspondance | 13 tests, processus simulés |
| **GB4** écrire ailleurs | texte coupé, minuscules, fenêtre introuvable, pas d'Entrée | texte intact, fenêtre retrouvée, envoi **confirmé** avec texte et fenêtre | 24 tests ; **rejeu réel** sur une fenêtre de test |
| **GB5** réseau au démarrage | connexion HTTPS vers huggingface.co à 24,6 s | **aucune** connexion non locale pendant 70 s | démarrage réel, connexions TCP relevées toutes les 150 ms |
| **GB6** libellés | « memory_forget » affiché | « Oublier ce souvenir », « Envoyer le message » | un test exige un libellé pour chaque action confirmable |
| **GB7** traces du sprint G | 26 éléments écrits par mes tests | **25 retirés**, 1 gardé (doute, §4.7) | sauvegarde vérifiée ; décomptes revenus à l'état d'avant |
| **GB8** guide, tests | — | guide à jour, chaque exemple rejoué ; **911 passés, 4 ignorés** | §5 |
| **G7** dialogue vu par Alexis | — | **non fait** | reste à Alexis |

**La cause racine de GB1 était écrite dans les consignes du modèle :**
- « Si l'utilisateur donne une INSTRUCTION d'action → **confirmer brièvement**. Le système exécutera l'action. » ;
- « Être proactif : si l'utilisateur semble vouloir une action, **déduis-la** ».

Or ce chemin n'est emprunté que si le système n'a reconnu aucune action. Le modèle obéissait. Les consignes sont corrigées, mais la correction qui compte est déterministe (§4.1).

**Trouvé en testant, et corrigé :**
- la voix disait « **C'est fait.** » pour une action refusée par le validateur ;
- la ponctuation tapée dépendait du clavier de la machine : « (Atlas) » arrivait « 5Atlas° » sur un clavier AZERTY.

**État au moment du rapport :**
- **Atlas :** arrêté.
- **Docker :** démarré.
- **Ollama :** 0.40.2.
- **Mémoire :** `atlas_memory_e5` 278 éléments (274 après GB7, plus 4 écrits par le rejeu GB4, annexe B), `atlas_conversations` 12, `atlas_errors` 20, `atlas_memory` 489 (inchangée).
- **Sauvegardes vérifiées :** `chromadb_20261010_180247`, l'état d'avant GB7.

---

## 2. Objectifs vs réalisation

| Objectif (brief) | Résultat réel | Statut |
|---|---|---|
| GB1.1 — ligne de base, ≥ 30 demandes, vrai modèle | 34 demandes d'action + 20 questions, par la vraie route, outils simulés, mémoire en lecture seule | PASS |
| GB1.2 — garde déterministe, justifiée, limites dites | deux gardes, l'une avant le modèle, l'autre après (§4.1) ; limites au §7 | PASS |
| GB1.3 — réponse fixe | « Je ne sais pas encore faire ça. », sans appel au modèle | PASS |
| GB1.4 — consigne au modèle | consignes fautives retirées ; règle « tu n'agis jamais » ; « comment faire » reste expliqué | PASS |
| GB1.5 — pas de mémorisation | un échange bloqué n'est ni ingéré ni gardé en session | PASS |
| GB1.6 — mesure après : aucune affirmation transmise | **0 / 34**, vrai modèle | PASS |
| GB1 — la voix non plus | garde dans la réponse parlée ; « C'est fait » sur refus corrigé ; testé sur le vrai pipeline vocal (micro simulé) | PASS |
| GB2 — « faire » / « repas » ; « refais » marche | 14 phrases ordinaires, 17 formes de rejeu | PASS |
| GB3 — nom exact ; plusieurs nommées ; aucune → rien ; système refusé | fait ; PID vérifiés à l'exécution | PASS |
| GB4.1 — texte intact | casse, ponctuation, guillemets, apostrophes ; **et la disposition du clavier** | PASS |
| GB4.2 — fenêtre retrouvée ; plusieurs → demander | par titre ou par programme ; ambiguïté → question | PASS |
| GB4.3 — Entrée, dernière touche, règles B1 / B1-bis | Entrée seulement si la fenêtre est toujours devant ; 155 tests B1-bis verts | PASS |
| GB4.4 — envoyer = confirmation texte + fenêtre, dans la table | `window_send_message`, « toujours » ; fenêtre résolue avant la confirmation ; interdit aux automatisations | PASS |
| GB4 — rejeu réel sur une conversation de test | fenêtre « Atlas — salon de test » créée pour l'occasion (§6.2). **Discord non utilisé** : il affichait une conversation privée réelle | PASS |
| GB5 — `local_files_only=True`, téléchargement au premier lancement, prouvé en réel | fait ; avant / après mesuré | PASS |
| GB6 — libellés de l'oubli et de l'envoi | fait | PASS |
| GB7 — sauvegarde, verify, retirer exactement l'annexe B, rien d'autre | 25 retirés, 1 gardé par doute ; décomptes avant / après au §4.7 | PASS |
| GB8.1 — guide à jour, sans promesse non tenue | chaque exemple rejoué à blanc | PASS |
| **GB8.2 — G7 par Alexis** | **non fait** | **FAIL** |
| GB8.3 — `pytest tests/ -q` → code 0 | 911 passés, 4 ignorés | PASS |
| GB8.4 — rapport, réponse en tête | ci-dessus | PASS |

---

## 3. Architecture projet mise à jour

```
cortana-killer-atlas/
├── core/
│   ├── validator.py          ← GB1 (claims_action, honest_reply, UNSUPPORTED_REPLY) ; GB4 (verbe send,
│   │                           window_send_message dans la table et exclu des automatisations)
│   ├── intent_classifier.py  ← GB1 (actions sans outil) ; GB2 (rejeu) ; GB4 (analyse de la saisie)
│   ├── intent_engine.py      ← GB1 (réponse fixe ; refus rendu comme résultat) ; GB3 (PID désignés) ;
│   │                           GB4 (fenêtre résolue avant la confirmation)
│   ├── ollama_client.py      ← GB1 (consignes corrigées ; garde dans la réponse parlée)
│   └── voice_engine.py       ← GB5 uniquement (chargement hors ligne)
├── api/routes.py             ← GB1 (garde sur /api/chat et /api/chat/stream, flux mis en tampon)
├── tools/
│   ├── process_manager.py    ← GB3 (nom exact, PID vérifiés)
│   └── window_controller.py  ← GB4 (fenêtre par titre ou programme, ambiguïté, envoi, presse-papiers)
├── desktop/atlas_desktop.py  ← GB6 (deux libellés)
├── scripts/memory_cleanup.py ← GB7 (identifiants explicites, garde-fous)
├── docs/beta/                ← GB8 (guide, installation)
└── tests/
    ├── test_honesty_gbis.py, fixtures/gb1_reponses_reelles.json, gb1_mesure.py   (GB1)
    ├── test_redo_gbis.py (GB2) · test_kill_exact_gbis.py (GB3) · test_send_message_gbis.py (GB4)
    ├── test_whisper_offline_gbis.py (GB5) · test_labels_gbis.py (GB6) · test_memory_cleanup_ids_gbis.py (GB7)
    └── test_confirmation_f.py, test_beta_safety_g.py ← un Bloc-notes simulé (GB3)
```

**Note de périmètre :** `core/ollama_client.py` contient les consignes du modèle et la réponse parlée. Le brief autorise « la route de conversation et ses consignes » : j'ai compris ce fichier comme inclus. C'était aussi le seul moyen de garder la voix sans toucher à `voice_engine.py`, ouvert seulement pour GB5.

---

## 4. Détail des implémentations

### 4.1 GB1 — deux gardes déterministes

**Ligne de base.** Banc de mesure `tests/gb1_mesure.py`. Il joue chaque phrase par la vraie route (`chat_endpoint`), avec le vrai classifieur et le vrai modèle. Les outils sont remplacés par des enregistreurs. La mémoire est en lecture seule : les rappels sont réels, et aucune écriture n'a lieu dans la mémoire qu'on venait de nettoyer. Étiquetage à la main des 34 demandes d'action :

| Réponse | Nombre | Exemples réels |
|---|---|---|
| Affirme avoir agi | **10** | « Volume baissé. » · « Le Bluetooth est désactivé. » · « Le minuteur de 10 minutes a été mis en place. » · « D'accord, je baisse la luminosité de l'écran. » |
| Promet d'agir | **5** | « D'accord, je vais imprimer le document. » · « D'accord, la corbeille sera vidée. » · « D'accord, j'envoie un mail à votre mère. » |
| Laisse croire qu'il peut le faire | 5 | demande des précisions pour réserver, partager, télécharger, répondre à un mail |
| Invente un état | 1 | « Le son est déjà au maximum » |
| Honnête | 6 | « Je ne peux pas couper le Wi-Fi… » |
| Passe par un outil | 7 | dont 3 workflows et 1 lecture de page web choisis à tort (§7) |

**Garde amont (classifieur), quand aucune catégorie n'a reconnu la phrase.** Un impératif d'action en tête de phrase, ou « peux-tu / tu peux » suivi de l'infinitif, reçoit la catégorie `unsupported`. Le validateur la mène à la réponse fixe, et le moteur la rend comme résultat. **Le modèle n'est pas appelé.** Ce qui a un outil garde son outil. Les tournures de conversation qui empruntent ces verbes sont exclues : « appelle-moi Alex », « réponds-moi », « envoie-moi une blague », « passe une bonne journée », « mets-toi à ma place », « change de sujet ».

**Garde aval (`validator.claims_action`).** Elle s'applique à toute réponse produite sans outil exécuté, sur quatre chemins : `/api/chat` (conversation, et repli quand le validateur refuse), `/api/chat/stream`, et la réponse vocale. Elle cherche une liste d'expressions :
- première personne au passé, au présent ou au futur proche, sur une liste de verbes d'action (« j'ai baissé », « je vais envoyer », « je baisse », « j'envoie ») ;
- « c'est fait » ;
- une phrase courte qui constate (« Volume baissé. ») ;
- un passif sur un objet de l'ordinateur (« le Bluetooth est désactivé », « la corbeille sera vidée ») ;
- « commande… lancée », « l'action est en cours », « le système passe… », « la musique commence ».

Un passage est ignoré si sa phrase commence par une hypothèse ou une proposition (« si… », « voulez-vous que je… »). Ces deux cas de faux positifs ont été trouvés sur les réponses réelles. Une réponse détectée est **remplacée** par la réponse fixe, et l'échange n'est **ni ingéré dans `atlas_conversations` ni gardé en session**.

**Le flux web ne diffuse plus mot à mot.** Une affirmation aurait été affichée avant qu'on puisse la garder. La réponse est mise en tampon, gardée, puis émise d'un bloc. Le temps total est inchangé, mais l'affichage progressif est perdu.

**Voix.** `generate_speech_response` passe par la même garde. Le moteur rend maintenant le message d'un refus du validateur comme résultat (`result.message`). Auparavant, la voix ne trouvait rien à résumer et prononçait son repli, « C'est fait. », pour une action refusée (« écris bonjour » sans fenêtre). Le test vocal a vu ce défaut rouge.

**Consigne au modèle.** Il n'agit jamais. Il dit qu'il ne sait pas faire quand on lui demande de faire, et il explique quand on lui demande comment faire. La première version rendait le modèle muet sur « comment baisser le volume ? » : corrigé et revérifié sur le vrai modèle.

### 4.2 GB2 — le rejeu

Deux chemins rejouaient à tort :
- **La tolérance aux fautes** (distance ≤ 2 avec « refais ») attrapait « faire », « fait » et « repas ». Elle ne joue plus que pour une phrase de deux mots au plus, et jamais sur un mot courant (liste `_REDO_FUZZY_STOPWORDS`).
- **Les mots de rejeu étaient cherchés n'importe où** (« encore », « refaire »), y compris par la table des verbes. Ils ne comptent plus qu'en tête de phrase, après « atlas » ou une formule de politesse. « encore », « à nouveau » et « again » comptent seuls ou presque (5 mots au plus, politesse finale retirée).

### 4.3 GB3 — arrêter un processus

`find_processes_by_name` cherche une correspondance exacte, avec ou sans « .exe ». `request_confirmation` désigne les processus **avant** de demander. La confirmation montre « notepad.exe (2 processus : PID 10, 11) ». S'il n'y a aucune correspondance, aucune confirmation n'est proposée. Après confirmation, `kill_process(pids=…)` n'arrête que ces PID, et seulement s'ils portent toujours ce nom : un PID réattribué entre-temps est épargné. La protection des processus système du sprint G reste active et testée.

### 4.4 GB4 — écrire, et envoyer, ailleurs

- **Texte.** `_parse_typing` travaille sur la phrase d'origine. Il respecte les guillemets « » et " ", et l'apostrophe n'ouvre plus de citation. Sans guillemets, il coupe au **dernier** « dans / sur ». Il comprend aussi « dans X, écris … » et « … et envoie ».
- **Clavier.** Constaté au rejeu réel : la frappe simulée suit un clavier américain, et sur un clavier AZERTY, « ( » donnait « 5 ». Seuls les lettres et les espaces sont tapés touche par touche. Tout le reste est collé par le presse-papiers, restauré ensuite.
- **Fenêtre.** `resolve_app_window` cherche par le nom dans le titre (sans tenir compte de la casse) ou par le nom du programme. **Plusieurs correspondances : Atlas demande laquelle.** L'expression pywinauto est échappée et insensible à la casse : le « | » d'un titre devenait une alternative.
- **Envoi.** L'outil `window_send_message` tape le texte, revérifie que la fenêtre est toujours devant, puis presse Entrée.
  - **Confirmation** : `CONFIRMATION_POLICY`, « toujours ». La fenêtre est résolue avant la confirmation, et le dialogue montre « « texte » dans « titre exact » ». C'est dans cette fenêtre-là que le message part.
  - **Fenêtre nommée obligatoire** : sans elle, rien n'est envoyé, jamais par héritage de la fenêtre récente.
  - **Automatisations** : l'envoi leur est interdit.

### 4.5 GB5 — hors ligne au démarrage

`_load_whisper` charge le modèle avec `local_files_only=True`. Sur `LocalEntryNotFoundError` (vérifiée sur la vraie bibliothèque), il annonce le téléchargement et le fait : premier lancement seulement. Le repli processeur suit la même règle.

### 4.6 GB6 — libellés

Ajout de « Oublier ce souvenir » et « Envoyer le message ». Un test lit `ACTION_LABELS` dans le source et exige un libellé lisible pour **chaque** action de `CONFIRMATION_POLICY`.

### 4.7 GB7 — retrait des traces du sprint G

1. **Outil.** `memory_cleanup.py` gagne `plan-ids` / `apply-ids --ids FICHIER` :
   - `atlas_memory` est intouchable ;
   - un seul identifiant introuvable ou dont le texte diffère, et rien n'est supprimé ;
   - le décompte doit baisser d'exactement le nombre prévu ;
   - `--yes` est exigé.

   Les règles automatiques du sprint E protègent toujours `atlas_conversations`.
2. **Sauvegarde** `chromadb_20261010_180247`, puis `verify` : restauration prouvée.
3. **Inventaire avec texte et horodatage.** Les 12 conversations, toutes nommées ici, correspondent à la seconde près à mes tests du 10/10 (05 h 42 à 06 h 07) :
   - `conv_4342ded731e6` « présente-toi » ;
   - `conv_dc18b10e5abb` « capitale de l'Italie » ;
   - `conv_85a2b1ddaf52` « quelle heure » ;
   - `conv_38670c07d218` et `conv_afe8ed69786d` « baisse le volume » ;
   - `conv_18de383cd3fc` « monte le son » ;
   - `conv_a0e804ab5a30` « message à Paul » ;
   - `conv_334f9b1132c1` « coupe le wifi » ;
   - `conv_cd1364c19d6f` et `conv_88c3731bad16` « vide la corbeille » ;
   - `conv_256456d91b55` « fichiers temporaires » ;
   - `conv_d945d78cc305` « musique ».
4. **Doute, donc gardé :** `habit_6b79ce8c0a6e`, « le processus applicationframehost.exe est détecté actif de manière récurrente (3+ sessions) ». Elle a été écrite pendant mon test de la Calculatrice, mais c'est une **habitude déduite de plusieurs sessions**, et ce processus héberge aussi les applications Windows d'Alexis. Elle peut refléter son usage réel. **Signalé, non retiré.**
5. **Retrait** de 25 éléments :

| Collection | Avant | Après | Retirés |
|---|---|---|---|
| `atlas_memory_e5` | 283 | 274 | 9 : 3 corrections (`correction_c0914a2cd46f`, `correction_0d21aa19d3e1`, `correction_2d1a86b4eb3b`), 6 historiques (`action_history_6e909814bb4b`, `…34e728b11a55`, `…3879dea7954d`, `…6e9f93d0e20e`, `…b5bb5f3865c3`, `…eb6e3c31adee`) |
| `atlas_conversations` | 24 | 12 | 12 (ci-dessus) |
| `atlas_errors` | 24 | 20 | 4 : `err_540d7b68c1ed`, `err_375ac4d61b1e`, `err_2d98ba1ad950`, `err_c6d72a7c3bd4` |
| `atlas_memory` | 489 | 489 | 0 |

Les décomptes reviennent exactement à l'état d'avant mes tests G, plus l'habitude gardée. Rapport des suppressions : `%USERPROFILE%\Atlas_backups\memoire\gb7_suppressions_20261010.json`.

---

## 5. Résultats des tests

### État rouge, avant correction

```
GB7  4 failed, 1 passed      ImportError: cannot import name 'apply_ids_plan'
GB2  13 failed, 18 passed    « qu'est-ce que tu sais faire ? », « je suis encore fatigué », « j'ai fait une erreur hier »… rejouaient
GB1  76 failed, 26 passed    assert 'conversation' != 'conversation'  (28 actions parties en conversation)
                             - Je ne sais pas encore faire ça. / + Le Bluetooth est désactivé.
                             assert 'fait' not in "c'est fait."   (voix, action refusée)
                             assert "D'accord, la...e sera vidée." == 'Je ne sais p...'   (VRAI modèle)
GB3  7 failed, 6 passed      « e » a arrêté [notepad.exe ×2, notepad++.exe, steam.exe, steamwebhelper.exe, explorer.exe, Discord.exe]
                             un PID réattribué était arrêté
GB4  13 failed, 3 passed, 4 errors   textes, fenêtres, envoi, confirmation
     (rejeu réel) 3 failed, 1 passed  frappé touche par touche : ['(Atlas) Bonjour']
GB6  2 failed                le dialogue afficherait le nom technique de : ['memory_forget', 'window_send_message']
GB5  2 failed                chargement en ligne : [{'device': 'cpu', 'local_files_only': False}]
```

**Honnêteté sur les rouges faibles :**
- Les 4 rouges de GB7 et les 26 tests GB1 de faux positifs ont échoué sur un `ImportError` : la fonction n'existait pas encore. Un tel rouge ne prouve rien (leçon du sprint B1). Ces tests ont depuis été exercés sur les 26 réponses réelles ordinaires ou honnêtes, et la garde y a commis deux faux positifs, corrigés avant d'être verts.
- Les 26 tests GB1 « une question reste une question » étaient verts avant : la catégorie `unsupported` n'existait pas. Ce sont des témoins.
- En GB3, « aucune correspondance » était vert avant, mais pour une autre raison : « e » est un morceau de « explorer.exe », donc la protection du sprint G le refusait déjà.

### Suite complète

```
.venv\Scripts\python.exe -m pytest tests/ -q -rs
SKIPPED [4] tests\test_action_safety_b1_bis.py:433: un nouvel onglet vide est légitime (« ouvre un nouvel onglet » : pas de clé url)
911 passed, 4 skipped in 236.55s (0:03:56)
exit=0
```

**Écart avec G** (732 passés) : +179 tests G-bis. Le test GB1 « vrai modèle » demande Ollama ; il est ignoré si Ollama ne répond pas. Deux anciens tests (`test_confirmation_f`, `test_beta_safety_g`) reçoivent un Bloc-notes simulé : depuis GB3, une confirmation ne vise plus un processus qui ne tourne pas. Le code n'a pas été adapté à ces tests.

---

## 6. Comportement observé en scénarios réels

### 6.1 GB1 — mesure après, sur le vrai modèle (même liste)

- **34 demandes d'action : 0 affirmation transmise.**
  - 27 reçoivent « Je ne sais pas encore faire ça. » sans appel au modèle ;
  - 5 passent par une confirmation (luminosité et écran → configuration système ; « active le mode avion », « active le mode sombre », « nettoie mon bureau » → lancer un workflow, à tort, §7) ;
  - 1 passe par un outil choisi à tort (§7) ;
  - aucune n'est mémorisée.
- **20 questions ordinaires : aucune bloquée**, mémorisées normalement. Une seule (« résume l'histoire de Rome ») part sur un outil choisi à tort.
- **Contrôles complémentaires** :
  - « comment baisser le volume / vider la corbeille / activer le Bluetooth sur Windows ? » sont expliqués ;
  - « le volume est trop fort » et « j'aimerais un peu de musique » ne donnent aucune affirmation.
  - Une réponse à « comment changer le fond d'écran ? » a été remplacée : la garde y a vu « j'ai configuré », dans une réponse produite après une relance pour dérive de langue. Trois essais bruts de la même question n'ont donné aucune affirmation. C'est probablement une vraie affirmation arrêtée, non démontré.

### 6.2 GB4 — rejeu réel sur une conversation de test

Discord n'a pas servi : sa fenêtre affichait une **conversation privée réelle** (« @★ … - Discord »), et le brief l'interdit. J'ai créé une fenêtre « Atlas — salon de test » qui consigne le contenu de son champ et chaque message envoyé avec Entrée. Atlas a été lancé par `start_atlas_desktop.bat`, et les demandes sont passées par l'API comme le fait la fenêtre Atlas.

| Étape | Résultat |
|---|---|
| « écris (Atlas) Bonjour, je suis Atlas, l'assistant d'Alexis. Message de test. dans salon de test » | Avant le correctif du clavier : « **5Atlas°** Bonjour… ». **Après : texte arrivé à l'identique**, rien envoyé |
| « envoie (Atlas) Ceci est un message de test, envoyé après confirmation ! dans salon de test » | dialogue « Atlas — confirmation requise » ouvert ; cible : « « (Atlas) Ceci est … ! » dans « Atlas — salon de test » » |
| Annuler | rien tapé, rien envoyé |
| Même demande, Confirmer | **un message envoyé, identique au caractère près** |

### 6.3 GB5 — démarrage réel

| | API prête | Connexions non locales du processus Atlas (70 s) |
|---|---|---|
| Avant | 24,7 s | `2600:9000:2912:6a00:…:443` à 24,6 s, **une adresse de huggingface.co** (résolue au même moment) |
| Après | 22,4 s | **aucune** ; transcription préchauffée sur GPU en 6,2 s |

---

## 7. Limites et risques identifiés

| Risque | Sévérité | Remarque |
|---|---|---|
| **G7 non fait** | **Élevé** | Condition de sortie : dialogue vu, Annuler, Confirmer, expiration, par Alexis |
| La garde aval repose sur une liste de verbes et de tournures | Moyen | Une affirmation formulée autrement passe. Mesuré : 0 sur 34. Un passif explicatif sur un appareil peut être bloqué (aucun cas sur 26 réponses réelles ordinaires) |
| Le flux web n'affiche plus la réponse mot à mot | Faible | Prix de la garde ; temps total inchangé |
| Outils choisis à tort | Moyen | « ajoute du lait à ma liste » et « résume l'histoire de Rome » → lecture de page web ; « active le mode avion », « active le mode sombre », « nettoie mon bureau » → lancer un workflow (confirmation). Rien n'est dangereux, mais c'est faux |
| Capacité sous-entendue, état inventé | Faible | « j'aimerais un peu de musique » → « Quel genre ? » ; « Le son est déjà au maximum » (ligne de base). Pas une affirmation d'action, mais pas exact |
| Écriture dans Discord non vérifiée en réel | Moyen | Vérifiée sur une fenêtre de test ; le guide le dit |
| Traces du rejeu GB4 dans la mémoire (annexe B) | Faible | Dont une fausse « correction » : c'est moi qui refusais |
| Hors périmètre, inchangés | — | heure (L4), recherche web brute, fermeture des applications UWP, latence |

---

## 8. Checklist de validation

- [x] Ligne de base mesurée sur au moins 30 demandes, sur le vrai modèle (34)
- [x] Garde déterministe : aucune affirmation d'action non exécutée transmise, par écrit comme à voix haute
- [x] Faux positifs mesurés : les réponses ordinaires passent (0 / 20, et 0 / 26 sur les réponses réelles étiquetées)
- [x] Ces échanges ne sont plus mémorisés
- [x] « faire » / « repas » ne rejouent plus rien ; « refais » marche toujours
- [x] `kill_process` sur le nom exact ; plusieurs correspondances nommées ; processus système toujours refusés
- [x] Saisie intacte dans une autre application, fenêtre retrouvée, Entrée possible
- [x] Envoyer un message demande une confirmation qui montre le texte et la fenêtre
- [x] Aucune requête vers Hugging Face au démarrage, prouvé en réel
- [x] Libellés lisibles pour l'oubli et l'envoi
- [x] Traces de test retirées de la mémoire, sauvegarde vérifiée d'abord, rien d'autre touché (une gardée par doute)
- [x] Guide testeur à jour, sans promesse non tenue
- [ ] **G7 fait par Alexis**
- [x] `python -m pytest tests/ -q` → code 0 (911 / 4)

---

## 9. Recommandations pour le sprint suivant

### P0
1. **G7 par Alexis**, avant toute installation chez un proche.

### P1
2. **Outils choisis à tort :** « ajoute … à ma liste » et « résume … » ne doivent pas lire une page web ; « active le mode X » ne doit pas lancer un workflow sans workflow de ce nom.
3. **Écriture dans Discord en réel**, sur un salon de test créé pour l'occasion.
4. **Garde aval :** élargir la liste à partir des retours des testeurs, en mesurant les faux positifs à chaque ajout, comme ici.

### P2
5. La fausse « correction » enregistrée quand c'est un test qui refuse : `save_rejection` ne sait pas qui refuse.
6. Hors périmètre, toujours ouverts : l'heure (L4), la recherche web brute, les applications UWP.

---

## Annexe A — sorties du banc GB1

- **Réponses réelles avant**, avec étiquettes : `tests/fixtures/gb1_reponses_reelles.json` (47 réponses en texte).
- **Mesures brutes** : `gb1_avant.json`, `gb1_apres.json` (dossier de travail de la session ; reproductibles par `python tests\gb1_mesure.py SORTIE.json`).

## Annexe B — ce que le rejeu GB4 a écrit dans la mémoire d'Alexis

Non retiré : la décision GB7 ne couvrait que les traces du sprint G. **À toi de décider.**

| Identifiant | Contenu |
|---|---|
| `action_history_d9c753fee453` | « Action 'window_type' exécutée … « (Atlas) Bonjour, je suis Atlas … » » (essai avant le correctif du clavier) |
| `action_history_064554008341` | idem, après le correctif |
| `correction_1faff6dadedf` | « L'utilisateur a refusé l'action 'window_send_message' … » — **fausse** : c'est moi qui refusais |
| `action_history_cf934ada424c` | « Action 'window_send_message' exécutée … » |
