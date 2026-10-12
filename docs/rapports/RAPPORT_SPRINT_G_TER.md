# RAPPORT SPRINT G-TER — La première impression d'un testeur
Date: 11/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_G_TER.md`. Références : `docs/rapports/BILAN_SESSION_ALEXIS_20261011.md`, rapport G-bis.
> Branche **`sprint-g-ter`**, issue de `main` @ `4a80fdd`. 3 commits, plus celui de ce rapport, **non poussés**.
> Séance de nuit en autonomie, sur autorisation d'Alexis.

---

> **La beta peut-elle commencer ? Oui**, dès la validation de ce rapport. G7 a été fait par Alexis, et tous les critères de G-ter sont tenus.
>
> Deux réserves à connaître :
> - **La transcription de commandes très courtes.** Rejouées avec une voix de synthèse, 3 phrases sur 6 ont été mal transcrites. Quand la transcription est juste, la réponse vocale est identique à celle du clavier.
> - **Mode Gaming et Nettoyage Système sont désactivés** depuis B1-ter, donc « lance le mode gaming » ne le lance pas, et Atlas le dit (§4.2).

---

## 1. Résumé exécutif

**Statut global : VALIDÉ**, sous réserve de la validation du superviseur. Les sept tâches sont faites et prouvées : par les tests avec les phrases exactes de la session d'Alexis, par le vrai modèle, et par un rejeu réel au clavier et à la voix.

| Tâche | Avant | Après | Preuve |
|---|---|---|---|
| **GT0** fusion | — | `g-bis-suivi` dans `main` ; 927 passés / 4 ignorés | suite sur `main` |
| **GT1** « tu peux faire quoi ? » | le modèle ne citait que la planification, et niait qu'Atlas sait agir | réponse fixe **construite depuis le registre des outils** ; « toi fais le » → réponse fixe qui ne nie pas | 16 tests, dont la cohérence avec le registre ; garde GB1 : **0 affirmation sur 34** (vrai modèle) |
| **GT2** question sur un mode | « il consiste à quoi le mode gaming ? » proposait de le **lancer** | décrit depuis son fichier, sans le modèle ni rien lancer ; mode inexistant ou désactivé jamais proposé | 10 tests ; rejeu réel |
| **GT3** verbe dans la cible | « Fermes, Steam. » → cible « fermes, steam » | cible « steam » | 8 tests ; rejeu réel |
| **GT4** « ouvre steam » quand Steam tourne | « déjà lancé », rien ne revenait | fenêtre principale ramenée ; Steam rappelé par `steam://open/main`, sans second exemplaire | 6 tests ; **rejeu réel avec Steam** |
| **GT5** message GPU | « aucun GPU CUDA détecté » alors que la voix tourne sur GPU | « transcription sur GPU (CTranslate2) ; torch processeur : EasyOCR et embeddings seulement » | démarrage réel |
| **GT6** mémoire | — | `conv_f8b7b5aab1a9` retirée, seule ; `atlas_conversations` 20 → 19 | sauvegarde vérifiée |
| **GT7** guide, rejeu, tests | — | guide à jour ; rejeu clavier et voix ; **970 passés, 4 ignorés** | §5, §6 |

**Le rejeu réel a démasqué deux défauts que les tests simulés ne voyaient pas**, tous deux corrigés et revérifiés en réel :
1. « ouvre steam » répondait « je ramène sa fenêtre » en ramenant la **liste de contacts** de Steam. La fenêtre principale ne revenait pas. Cause : les fenêtres de Steam appartiennent à `steamwebhelper.exe`, et la première trouvée n'était pas la principale.
2. Même avec la consigne corrigée, le vrai modèle répondait encore 3 fois sur 5 « je ne peux pas effectuer cette action pour vous » à « toi fais le ». Cette phrase reçoit maintenant une réponse fixe.

**Ma faute, signalée :** un essai à blanc lancé sans neutraliser la mémoire a écrit `err_7297b690157e` dans `atlas_errors` à 02 h 44 (§7, annexe). Je ne l'ai pas retiré : GT6 limitait le retrait à un seul élément.

**État au moment du rapport :**
- **Atlas :** arrêté.
- **Mémoire :** `atlas_memory_e5` 276, `atlas_conversations` 19, `atlas_errors` 21, `atlas_memory` 489. Sauvegarde vérifiée `chromadb_20261011_025948`, état d'avant GT6.
- **Docker, Ollama et VS Code** sont fermés à la fin de la séance, comme demandé (§8).

---

## 2. Objectifs vs réalisation

| Objectif (brief) | Résultat réel | Statut |
|---|---|---|
| GT0 — fusionner `g-bis-suivi`, suite verte | déjà fusionnée (PR #8) ; 927 / 4 sur `main` | PASS |
| GT1.1 — réponse fixe construite depuis les outils réellement exécutés | `capabilities_reply()` parcourt TOOL_HANDLERS ∩ INTENT_CATEGORIES ; libellés par outil | PASS |
| GT1.2 — courte, lisible, par familles, confirmations dites | 6 familles + voix ; « * demande votre confirmation à l'écran » ; aucun jargon (testé) ; environ 1 250 caractères | PASS |
| GT1.3 — six formes reconnues, sans rejeu (GB2) | 7 formes testées, dont la phrase exacte d'Alexis | PASS |
| GT1.4 — test de cohérence avec le registre | annoncé ⊆ moteur ; exposé ⊆ annoncé ; `window_restore` (absent du moteur) non annoncé | PASS |
| GT1.5 — le modèle ne nie plus qu'Atlas sait agir ; garde GB1 entière | consigne corrigée, et réponse fixe pour « toi fais le » (§4.1) ; GB1 : 0 / 34 | PASS |
| GT2 — question sur un mode → description, rien lancé | depuis le fichier, sans le modèle | PASS |
| GT2 — « lance le mode … » le lance, avec confirmation | **oui pour Mode Travail et Démarrage Matin** ; Mode Gaming et Nettoyage Système désactivés depuis B1-ter, Atlas le dit (§4.2) | PASS (avec écart signalé) |
| GT2 — mode inexistant jamais proposé | « je ne connais pas… », modes utilisables cités | PASS |
| GT3 — la cible ne garde ni le verbe ni la ponctuation | fermer, ouvrir, réduire, premier plan ; transcription réelle | PASS |
| GT4 — fenêtre ramenée, sans seconde instance, message vrai, rejeu réel Steam | §4.4, §6.2 | PASS |
| GT5 — message GPU exact au démarrage et dans doctor | démarrage réel ; doctor cohérent | PASS |
| GT6 — `conv_f8b7b5aab1a9` seule, après sauvegarde vérifiée | 20 → 19 ; les 2 corrections d'Alexis intactes | PASS |
| GT7.1 — guide à jour, chaque phrase vraie | exemples rejoués à blanc | PASS |
| GT7.2 — rejeu réel au clavier et à la voix | fait (§6) ; voix : 3 transcriptions fausses sur 6 avec une voix de synthèse | PASS (réserve) |
| GT7.3 — `pytest tests/ -q` → code 0 | 970 passés, 4 ignorés | PASS |

---

## 3. Architecture projet mise à jour

```
core/intent_engine.py      ← GT1 (TOOL_CAPABILITIES, capability_tools, capabilities_reply, __capabilities__,
                             __followup__) ; GT2 (workflow_describe, confirmation qui montre le mode) ;
                             GT4 (idempotence : bring_running_app)
core/intent_classifier.py  ← GT1 (formes d'aide, « toi fais le ») ; GT2 (question sur un mode) ; GT3 (cible)
core/validator.py          ← GT1 (catégorie help) ; GT2 (mode inconnu ou désactivé jamais lancé)
core/ollama_client.py      ← GT1.5 (consigne : liste des capacités tirée du registre, plus de déni)
tools/app_launcher.py      ← GT4 (bring_running_app, fenêtres de steamwebhelper, steam://open/main)
main.py                    ← GT5 (_voice_gpu_status d'après CTranslate2)
scripts/doctor.py          ← GT5 (texte de l'avertissement torch)
docs/beta/GUIDE_TESTEUR.md ← GT7.1
tests/test_gter.py         ← NOUVEAU (43 tests)
tests/test_final_v50.py, tests/test_voice_v40.py ← adaptés (§5)
```

---

## 4. Détail des implémentations

### 4.1 GT1 — « tu peux faire quoi ? »

**Une seule source de vérité.** `capability_tools()` retient les outils que le moteur exécute (`TOOL_HANDLERS`) **et** qu'une demande peut atteindre (`INTENT_CATEGORIES`). Chacun porte une famille et un libellé dans `TOOL_CAPABILITIES`, et `capabilities_reply()` les parcourt. Les confirmations viennent de `CONFIRMATION_POLICY` ; les modes cités et la ligne sur la voix viennent du moteur de workflows et de la configuration. Le test de cohérence échoue si un outil exposé n'a pas de libellé, ou si un libellé désigne un outil absent.

**Trouvé en le construisant :** `window_restore` est annoncé par le classifieur mais **absent du moteur**. « Restaure la fenêtre » aboutirait à « outil inconnu ». Il n'est pas annoncé. Le corriger sort du périmètre (§9).

**L'excès inverse (GT1.5).** La consigne reçoit maintenant la même liste et dit qu'Atlas sait agir par ses outils. Elle interdit « je ne peux pas effectuer d'action sur votre ordinateur ». Mesuré sur le vrai modèle, avec le contexte exact de la session (« met steam en premier plan », puis « toi fais le ») : plus aucune réponse ne nie en général, mais **3 sur 5** commencent encore par « Je ne peux pas effectuer cette action pour vous ». Une réponse juste ne repose pas sur une probabilité : « toi fais le », « fais-le », « vas-y fais-le » et « tu peux le faire ? » reçoivent une réponse fixe. L'action précédente n'est pas retenue, Atlas invite à la redire directement (« mets Steam au premier plan »).

**La garde GB1 tient** avec la nouvelle consigne : mesure refaite sur la liste G-bis, **0 affirmation transmise sur 34**, et 0 question ordinaire bloquée sur 20.

### 4.2 GT2 — une question n'est jamais un ordre

- **Question sur un mode** (« c'est quoi… », « il consiste à quoi… », « que fait… », « qu'est-ce qu'il y a dans… », ou une phrase en « ? » qui ne commence pas par un impératif) : l'outil `workflow_describe` lit le fichier du mode. Il en donne le nom, la description et les étapes, sans le modèle et sans rien lancer.
- **Mode inexistant** (« active le mode sombre », « active le mode avion ») : jamais proposé. Atlas répond « Je ne connais pas de mode « sombre ». Modes utilisables : … ». C'est une réponse honnête, rendue comme un succès pour que l'apprentissage par les erreurs n'écrive rien.
- **La confirmation d'un lancement montre le mode et ses étapes.** « nettoie mon bureau » demandait de confirmer « nettoyage_systeme ». On voit maintenant ce que ce mode ferait (vider la corbeille…).
- **Écart avec le brief : les modes désactivés.** Mode Gaming (il arrête `teams.exe`) et Nettoyage Système (il vide la corbeille) sont **désactivés depuis B1-ter** : une action à confirmation n'a pas sa place dans un mode. « lance le mode gaming » demandait une confirmation, puis répondait « Workflow désactivé ». Le lancer vraiment rouvrirait B1-ter. J'ai donc choisi la réponse honnête : un mode désactivé est décrit avec sa raison et jamais proposé au lancement, et la liste des capacités ne cite que les modes utilisables. « lance le mode travail » est confirmé puis lancé. **À valider par le superviseur.**

### 4.3 GT3 — la cible

Les formes **exactes** des verbes d'action sont retirées de la tête de la cible (fermes, fermez, fermer, ferme-moi, ouvres, réduis, mets…), ainsi que la ponctuation. Ce sont des formes exactes, pas un préfixe : « lanceur » ou « fermette » ne sont pas des verbes.

### 4.4 GT4 — « ouvre X » quand X tourne déjà

`bring_running_app` applique trois cas :
1. **Une fenêtre de l'application existe** : elle est ramenée au premier plan, après vérification qu'elle est bien devant. Pour une application rappelable, il faut sa **fenêtre principale**, celle qui porte son nom.
2. **Aucune fenêtre principale, et l'application ne tourne qu'en un seul exemplaire** : elle est rappelée par son propre moyen. Pour Steam, c'est `steam://open/main`, un protocole qui s'adresse au Steam déjà lancé. Jamais un second exemplaire. Le succès n'est annoncé que si la fenêtre principale revient.
3. **Sinon** : rien n'est relancé, pour ne pas ouvrir un second exemplaire, et Atlas le dit.

**Constaté :** les fenêtres de Steam appartiennent à `steamwebhelper.exe`, pas à `steam.exe`.

### 4.5 GT5 — le message GPU

`_voice_gpu_status` juge d'après **CTranslate2**, qui fait la transcription, et non plus d'après torch, qui ne sert qu'à EasyOCR et aux embeddings. `doctor.py` ne dit plus que le message de `main.py` est faux.

### 4.6 GT6 — mémoire

Sauvegarde `chromadb_20261011_025948`, puis `verify` (restauration prouvée), `plan-ids` et `apply-ids --yes`. `atlas_conversations` passe de **20 à 19**, seul `conv_f8b7b5aab1a9` étant retiré (« D'accord, je vais me fermer. »). Les corrections d'Alexis, `correction_9aeae03d6a0d` et `correction_b83c78b56bd6`, sont intactes. Rapport des suppressions : `Atlas_backups\memoire\gt6_suppression_20261011.json`.

---

## 5. Résultats des tests

### État rouge

```
première série   30 failed, 3 passed
   GT1  AttributeError: module 'core.intent_engine' has no attribute 'capabilities_reply'   (rouge faible)
   GT2  « il consiste à quoi le mode gaming ? » propose de lancer le mode : {'status': 'confirmation_required', …}
   GT3  'Fermes, Steam.' → cible 'fermes, steam'
   GT4  AttributeError: … 'bring_running_app'                                                (rouge faible)
   GT5  assert 'warning' … / « faux 'aucun GPU CUDA' » toujours dans doctor.py
rejeu réel → nouveaux tests
   GT4  2 failed  (fenêtres de steamwebhelper.exe)  ;  2 failed  (liste de contacts ramenée à la place de la fenêtre principale)
   GT1  5 failed  « toi fais le » → réponse du modèle
   GT2  3 failed  mode désactivé proposé au lancement ; Mode Gaming dans la liste
```

**Les 3 tests verts de la première série sont des témoins** : deux formes de cible déjà propres, et le non-rejeu de GB2.

**Deux anciens tests adaptés**, avec la même intention :
- `test_final_v50::test_04` simule désormais le rappel de fenêtre. **Sans cela, il pouvait agir sur une vraie fenêtre de la machine** : il simulait « notepad tourne » mais laissait la recherche de fenêtres réelle.
- `test_voice_v40::test_10` vérifie l'alerte quand la transcription ne voit aucun GPU.

### Suite complète

```
.venv\Scripts\python.exe -m pytest tests/ -q -rs
SKIPPED [4] tests\test_action_safety_b1_bis.py:433: un nouvel onglet vide est légitime (« ouvre un nouvel onglet » : pas de clé url)
970 passed, 4 skipped in 238.28s (0:03:58)
exit=0
```

Écart avec `main` (927) : +43 tests G-ter.

---

## 6. Comportement observé en scénarios réels

### 6.1 Méthode du rejeu

Les phrases exactes de la session ont été rejouées en processus par le vrai code :
- **Clavier** : la route `/api/chat`, le vrai modèle et les **vrais outils** (Steam réellement fermé puis ramené).
- **Voix** : la phrase est prononcée par Piper (voix française d'Atlas), puis passe par la **vraie transcription sur GPU** et le **vrai pipeline vocal**. Pas de micro : Alexis dormait, et je ne parle pas.
- **Mémoire** en lecture seule : rien n'a été écrit (décomptes inchangés).
- **Confirmations** validées comme le ferait le bouton. Le dialogue lui-même a été vu par Alexis (G7).

### 6.2 Résultats (code final)

| Phrase | Clavier | Voix (transcrit → réponse) |
|---|---|---|
| « tu peux faire quoi ? » | liste des capacités | « Tu peux faire quoi ? » → la même liste |
| « toi fais le » | « Je ne retiens pas l'action dont on parlait. Dites-la-moi directement, par exemple « mets Steam au premier plan »… » | « Poi-Failer. » → demande de précision (**transcription fausse**) |
| « il consiste à quoi le mode gaming ? » | description du mode, désactivé, sans rien lancer | transcription exacte → la même description |
| « Fermes, Steam. » | confirmation, **cible « steam »** ; confirmé → fenêtre « Steam » fermée | « Firm Steam » → « Ouvre Steam. » (**transcription fausse** ; aucune action) |
| « ouvre steam », fenêtre fermée | « Steam tournait en arrière-plan : je l'ai rappelé, sa fenêtre principale est revenue. » → **fenêtre « Steam » de retour** | « Oversteam. » → « Ouvre Steam. » (**transcription fausse** ; aucune action) |
| « ok tu peux te fermer » | « Action refusée : fenêtre à fermer non précisée… » | transcription exacte → la même réponse |

**Lecture :** au clavier, les six phrases donnent la bonne réponse. À la voix, quand la transcription est juste, la réponse est identique à celle du clavier. Les trois échecs vocaux viennent de la transcription de phrases très courtes, prononcées par une **voix de synthèse**. Ce n'est pas représentatif d'une voix humaine : lors de sa session, Alexis a été transcrit « Fermes, Steam. », la forme que GT3 traite désormais. Diction ralentie : je l'ai tentée, sans résultat probant.

**Version intermédiaire, avant la correction de GT4 :** « ouvre steam » répondait « Steam était déjà lancé : je ramène sa fenêtre. », mais la fenêtre principale n'est pas revenue (seule la « Liste de contacts » était devant). Corrigé, puis revérifié en réel.

### 6.3 Démarrage réel (GT5)

```
[atlas] INFO — Atlas Voice : transcription sur GPU (1 périphérique(s) CUDA vu(s) par CTranslate2)
               (torch est en version processeur : seuls EasyOCR et les embeddings tournent sur le processeur).
[atlas.voice] INFO — [VOIX] Transcription préchauffée en 1.2s (device=cuda)
```

Aucune connexion non locale du processus Atlas pendant 40 s (GB5 toujours tenu).

---

## 7. Limites et risques identifiés

| Risque | Sévérité | Remarque |
|---|---|---|
| Transcription des commandes très courtes | Moyen | 3 phrases sur 6 mal transcrites avec une voix de synthèse. À mesurer avec des voix humaines (sprint voix) |
| Mode Gaming et Nettoyage Système non lançables | Faible | désactivés depuis B1-ter ; Atlas le dit. Décision à prendre sur ces deux modes |
| `window_restore` annoncé par le classifieur, absent du moteur | Faible | non annoncé dans la réponse fixe ; la demande aboutirait à « outil inconnu » |
| La réponse fixe « tu peux faire quoi ? » est longue à voix haute | Faible | environ 1 250 caractères, près d'une minute lue |
| La consigne au modèle reste probabiliste | Faible | « toi fais le » a sa réponse fixe ; d'autres tournures du même genre passent par le modèle |
| Rappel « un seul exemplaire » vérifié pour Steam seulement | Faible | les autres applications ne sont pas relancées sans fenêtre, et Atlas le dit |
| `err_7297b690157e` écrit par mon essai à blanc | Faible | annexe ; à décider par Alexis |

---

## 8. Checklist de validation

- [x] `g-bis-suivi` fusionnée, suite verte
- [x] « tu peux faire quoi ? » et ses variantes → réponse fixe construite depuis le registre, testée en cohérence
- [x] Le modèle ne nie plus qu'Atlas sait agir (réponse fixe pour « toi fais le ») ; garde GB1 : 0 / 34
- [x] Question sur un mode → description depuis sa définition, rien lancé ; « lance le mode travail » marche (Mode Gaming désactivé, §4.2)
- [x] Un mode inexistant n'est jamais proposé au lancement
- [x] La cible ne contient plus le verbe ni la ponctuation
- [x] « ouvre X » ramène sa fenêtre sans seconde instance ; prouvé avec Steam
- [x] Message GPU exact au démarrage et dans `doctor.py`
- [x] `conv_f8b7b5aab1a9` retirée seule, après sauvegarde vérifiée
- [x] Guide à jour ; phrases de la session rejouées au clavier et à la voix
- [x] `python -m pytest tests/ -q` → code 0 (970 / 4)
- [x] Docker, Ollama et VS Code fermés en fin de séance

---

## 9. Recommandations pour le sprint suivant

### P1
1. **Voix** : la latence (11 à 22 s par cycle, reportée par le superviseur) et la transcription des commandes très courtes, mesurées avec de vraies voix.
2. **Mode Gaming et Nettoyage Système** : les réécrire sans action à confirmation, ou décider qu'ils restent désactivés.

### P2
3. `window_restore` : l'ajouter au moteur, ou le retirer du classifieur.
4. Une version courte de « tu peux faire quoi ? » pour la voix.

---

## Annexe — trace écrite par mon essai à blanc

`atlas_errors / err_7297b690157e`, écrit le 11/10 à 02:44:14 : « intent=automation cible= app= ». Je vérifiais le texte d'un mode inconnu par un essai qui n'avait **pas** neutralisé la mémoire. À ce moment, le mode inconnu était encore rendu comme un échec, d'où l'écriture par l'apprentissage par les erreurs. Il est désormais rendu comme un succès. **Non retiré : à décider par Alexis.**
