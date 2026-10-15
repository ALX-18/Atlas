# RAPPORT SPRINT APPRENTISSAGE 2 — Tes refus, tes habitudes, et un seul clic
Date: 15/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_APPRENTISSAGE_2.md`. Branche **`sprint-apprentissage-2`**, issue de `main` @ `b45cb75` (Apprentissage 1 fusionné). Commits non poussés.
> Rejeux réels sur **copies** : mémoire (`ATLAS_CHROMA_PATH`), apprentissage (`ATLAS_APPRENTISSAGE_DB`), journal des actions (`ATLAS_ACTIONS_LOG`, historique synthétique). La mémoire réelle et le journal d'Alexis n'ont pas changé (§6.5).

---

## Tableau de tête

### AQ1 — Clics reçus par une fenêtre de test qui les compte (rejeu réel)

| Fenêtre de test | Avant (code de `main`, worktree) | Après (ce sprint) |
|---|---|---|
| **« Envoyer »**, devient « Envoyé » une fois cliqué (la vérification ne le retrouve plus) | **2 clics** reçus ; message « Clic OCR sur 'envoyer' à (318, 428), confiance=96%. » | **1 clic** ; « J'ai cliqué sur « envoyer », mais je n'ai pas pu vérifier que ça a marché. Si rien ne s'est passé, tu veux que je réessaie ? » |
| Sombre, « Magasin » (celle du rejeu d'Apprentissage 1) | 1 clic : la vérification a réussi ce jour-là | 1 clic ; la vérification a échoué ce jour-là, et Atlas l'a dit (même phrase) |

### AQ3 — Un refus enregistré puis rappelé (rejeu réel, fenêtre AtlasEssaiRefus)

| # | Ce qui se passe | Réponse d'Atlas |
|---|---|---|
| 1 | « ferme AtlasEssaiRefus » → Annuler | « Confirmation requise : fermer une fenêtre… » ; puis « Action annulée. Je retiens que tu l'as annulée. » La fenêtre reste ouverte. |
| 2 | même chose | idem |
| — | *Atlas arrêté puis relancé* | |
| 3 | « ferme AtlasEssaiRefus » | « **Les deux dernières fois, tu as annulé « ferme AtlasEssaiRefus ». Je te le propose quand même ; si tu voulais autre chose, dis « non, je voulais… ».** Confirmation requise : … ». La confirmation reste affichée. |
| 3 bis | Confirmer | La fenêtre est **fermée**. |
| 4 | Apprentissage neutralisé : « ferme AtlasEssaiRefus » | « Confirmation requise : … », sans rappel. |

### AQ4 — Les habitudes détectées dans le **vrai** journal d'Alexis (lecture seule, rien écrit)

| Lecture | Ouvertures retenues | Habitudes détectées |
|---|---|---|
| **Règle du sprint : origine d'Alexis seulement** | **0** (aucune entrée d'avant ce sprint ne porte d'origine) | **aucune** : Atlas ne proposera rien tant qu'Alexis n'aura pas lui-même ouvert ses applications avec Atlas, plusieurs jours |
| Pour information : toutes origines, sans les étapes de modes (82 ouvertures, du 13/03 au 15/10) | 82 | une seule : « tu ouvres souvent **notepad vers 18 h** » (7 fois sur 3 jours) |

**À Alexis de dire si elle est juste.** Je pense que non : ce sont des « ouvre notepad » tapés en série, les jours où d'autres essais tournaient. Avant d'exclure les étapes de modes, deux autres « habitudes » apparaissaient (« notepad après lancer steam », dans les deux sens, 27 et 28 fois) : c'étaient les étapes du « Mode Gaming ». Elles sont maintenant écartées (§4.4).

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.** AQ1, AQ3, AQ4 et AQ5 sont faits et prouvés en réel. AQ2 est fait dans le code et dans les tests, **sauf le retrait des trois collections vides de la mémoire réelle**. La sauvegarde a été faite deux fois, mais sa vérification n'a pas réussi :
- la première vérification a trouvé 7 requêtes sur 40 dans un ordre différent (fichiers identiques octet pour octet) ;
- la seconde a buté sur le défaut connu de ChromaDB.

Je n'ai rien retiré, et je demande à Alexis (§7, risque 1).

**Runtime :**
- Ollama 0.40.4 et ChromaDB 1.5.1 ;
- la mémoire réelle a seulement été lue et sauvegardée (deux sauvegardes) ;
- `data/apprentissage.db` réel n'existe pas : rien n'a été appris des essais.

**Chiffres :**
- Suite : **1 197 passés, 0 ignoré**, code 0 avec Ollama ; **1 194 passés et 3 ignorés justifiés**, code 0 sans Ollama.
- Corpus de routes, mémoire d'apprentissage vide : **234 / 235 (99,6 %)**, 0 action à tort. GB1 : 0 affirmation sur 34, identique au sprint précédent demande par demande.
- AQ1 : 2 clics → **1** sur le bouton « Envoyer ».
- AQ3 : refus rappelé au 2ᵉ, confirmation gardée.
- AQ4 : proposé, « oui » fait par le chemin normal, « arrête » respecté.
- AQ5 : lancement appris et ordre du premier plan rejoués en réel.

**Trouvé en chemin :**
- **les rejeux des sprints précédents écrivaient dans le vrai journal des actions** (source des habitudes) : corrigé et protégé par un test ;
- le premier plan peut viser la mauvaise fenêtre (§7, risque 3).

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| AQ0 — `sprint-apprentissage-1` fusionnée, suite verte | `main` @ `b45cb75` = commit `69efa2c` (suite 1 149 / 0 ignoré au sprint 1) + le brief seul (vérifié : `git diff 69efa2c b45cb75` ne touche que le brief). | PASS |
| AQ1 — test rouge : fenêtre qui compte les clics, aujourd'hui 2 | `test_aq1_un_clic_non_verifie_n_est_jamais_refait` : **rouge**, « 2 clics reçus : ['cache', 'easyocr'] ». | PASS |
| AQ1 — après : 1 clic, jamais 2, et c'est dit | Plus de second clic automatique. Le message dit « je n'ai pas pu vérifier ». Réel : 2 → 1. | PASS |
| AQ1 — une nouvelle tentative passe par une question | « tu veux que je réessaie ? » : un « oui » refait la demande par le chemin normal, un « non » ferme la question. Testé ; non rejoué en réel. | PASS |
| AQ1 — rejeu réel, fenêtre sombre, clics comptés | Fait : 1 clic avant comme après (la vérification a réussi avant et échoué après : l'OCR varie). La preuve du 2 → 1 vient de la fenêtre « Envoyer » (§6.1). | PASS |
| AQ2 — `data/apprentissage.db`, mêmes fonctions | `core/apprentissage_store.py`. `preparer`, `noter_methodes`, `lister`, `oublier`… sont inchangés en signature. | PASS |
| AQ2 — écritures atomiques, verrou « un seul Atlas » | Une transaction par écriture. Verrou du système pris sur `apprentissage.db` (même mécanisme que `data/chromadb`). Second processus : refusé (test). | PASS |
| AQ2 — sauvegarde : `apprentissage.db` et `habits.db` sauvegardés, vérifiés, restaurés | API de sauvegarde SQLite, empreinte, décomptes, `integrity_check`. `restore` met de côté puis remet. Tests de bout en bout, altération refusée. | PASS |
| AQ2 — `atlas_apprentissage` retirée de la configuration et supprimée après sauvegarde vérifiée | Retirée de la configuration et du code. **Pas supprimée de la mémoire réelle** : aucune vérification réussie. Script prêt et testé. | FAIL (en attente d'Alexis) |
| AQ2 — `atlas_habits`, `atlas_context_apps` : même chemin ; CK3 vert | Retirées de la configuration et du code, CK3 vert. Pas supprimées de la mémoire réelle (même raison). | PARTIEL |
| AQ2 — `atlas_errors` archive, documentée | Lue et écrite nulle part ; documentée dans `docs/CONFIGURATION.md` et `docs/memory_runbook.md`. | PASS |
| AQ2 — les 39 tests d'Apprentissage 1 passent sur SQLite | 39 / 39. Un seul a changé de **moyen** (rendre l'apprentissage indisponible), pas de vérification (§5.3). | PASS |
| AQ3 — Annuler compte, l'expiration non, origine obligatoire | Testé (expiration ×3 : rien ; origine absente : rien). Réel : 2 Annuler retenus. | PASS |
| AQ3 — au 2ᵉ refus, Atlas le dit avant de proposer ; la confirmation reste | Testé et réel (tableau de tête). | PASS |
| AQ3 — interdit : sauter une confirmation, refuser d'exécuter | 5 refus puis confirmer : exécuté. Une acceptation remet le compte à zéro. | PASS |
| AQ3 — listable et effaçable | « Refus : « ferme AtlasEssaiRefus » annulé 2 fois d'affilée » dans la liste ; « oublie… » efface avec confirmation. | PASS |
| AQ4 — calcul déterministe, N/K/D en configuration, lus (CK3) | `core/habitudes.py`, `apprentissage.habitudes` (10 min, 3 fois, 3 jours, tranche 60 min, 2 par heure), justifiés dans `docs/CONFIGURATION.md`. | PASS |
| AQ4 — proposer, jamais exécuter ; « oui » par le chemin normal | Testé et réel (« ouvre steam » → « Tu ouvres souvent discord après steam. Je l'ouvre ? » → « oui » → Discord). | PASS |
| AQ4 — une par habitude et par jour, X par heure | Testé, et vu en réel (pas de reproposition le même jour). | PASS |
| AQ4 — « arrête de me proposer ça » ; interrupteur global | Testé. Réel : « D'accord, je ne te proposerai plus ça », puis plus proposée et listée « Habitude écartée ». Interrupteur testé, pas rejoué en réel. | PASS |
| AQ4 — voix : la proposition n'interrompt jamais une réponse | Elle est ajoutée **après** la réponse (test). Non rejoué au micro. | PASS |
| AQ4 — habitudes du vrai journal, listées pour Alexis, rien écrit | Tableau de tête ; journal identique avant et après. | PASS |
| AQ4 — rejeu réel : historique synthétique sur copie, proposition, « oui », « arrête » | §6.3. | PASS |
| AQ5 — rejeu réel du lancement appris et de l'ordre du premier plan | §6.4. Lancement appris : « lancé par le chemin qui avait marché ». Premier plan : pygetwindow en premier après apprentissage, pywinauto en premier neutralisé. | PASS |
| AQ5 — formulations de correction élargies, négatifs élargis | +8 positives (« tu t'es trompé, c'était… », « je parlais de… », « pas ça, … », « non c'était… ») et +11 négatives. Rouge d'abord : 7 échecs. | PASS |
| AQ5 — GB1 isole l'état du monde comme `mesure_routes.py` | `tests/gb1_mesure.py` met de côté la dernière action pour chaque demande. | PASS |
| AQ6 — tests avant / après / neutralisé (refus, habitudes) sur `/api/chat` | `test_aq3_avant_apres_neutralise…`, `test_aq4_avant_apres_neutralise…`. | PASS |
| AQ6 — corpus ≥ 99,6 %, GB1 0, suites code 0, C3 | §5. | PASS |

---

## 3. Architecture projet mise à jour

```
api/routes.py                   réponse directe (« non », commandes d'habitude) ; proposition en fin de réponse ;
                                refus retenu à l'Annuler ; rappel dans la confirmation ; save_rejection retiré
config/settings.json            + apprentissage.habitudes ; memory.collections : conversations, documents, errors
core/
  apprentissage.py              stockage SQLite ; refus (AQ3) ; liste et oubli des habitudes ; formulations AQ5
  apprentissage_store.py        ← NOUVEAU : data/apprentissage.db (SQLite), verrou, transactions
  habitudes.py                  ← NOUVEAU : calcul, proposition, « arrête »
  propositions.py               ← NOUVEAU : une question d'Atlas en attente d'un oui / non
  atlas_logger.py               champ « origine » ; ATLAS_ACTIONS_LOG
  intent_engine.py              plus de second clic ; confirmation : demande, origine, rappel ; acceptation → refus remis à zéro
  memory_manager.py             partitions apprentissage / habits / context_apps retirées ; méthodes Chroma d'apprentissage retirées
  voice_engine.py               même chemin (réponse directe, rappel, proposition après la réponse)
desktop/atlas_desktop.py        le rappel des refus dans le dialogue de confirmation
docs/
  CONFIGURATION.md              apprentissage.habitudes (valeurs justifiées) ; atlas_errors = archive
  memory_runbook.md             collections retirées, apprentissage.db, archive
  rapports/RAPPORT_SPRINT_APPRENTISSAGE_2.md   ← NOUVEAU
scripts/
  backup_memory.py              apprentissage.db et habits.db : sauvegarde, vérification, restauration
  retirer_collections_vides.py  ← NOUVEAU (refuse sans verify réussi, refuse une collection non vide)
  rejeu_apprentissage_2.py      ← NOUVEAU
  rejeu_apprentissage.py, rejeu_fiabilite.py, checkup_dynamique.py, mesure_ressources.py
                                journal des actions et apprentissage redirigés vers la copie
tests/
  test_apprentissage_2.py       ← NOUVEAU (48 tests)
  test_apprentissage.py         1 test : moyen de l'indisponibilité (SQLite)
  test_memory_v60.py            partitions retirées vérifiées absentes
  conftest.py                   apprentissage.db de test
  gb1_mesure.py                 écritures SQLite comptées ; état du monde isolé
  o_mesure_ollama.py            save_rejection retiré
```

---

## 4. Détail des implémentations

### 4.1 AQ1 — un clic non vérifié n'est jamais refait (`core/intent_engine.py`, `core/propositions.py`)

**Avant.** Si la vérification après clic échouait (l'OCR ne retrouvait pas le libellé), le moteur relançait la recherche en excluant la couche utilisée, **recliquait**, revérifiait, puis rendait `replan_required`. Le message gardait celui du premier clic (« Clic OCR sur… confiance=96% »), comme si c'était sûr.

**Après.**
- Le clic est fait **une fois**. Une vérification ratée donne `click_verified=False` et `verification_failed=True`, et le message devient : « J'ai cliqué sur « X », mais je n'ai pas pu vérifier que ça a marché. Si rien ne s'est passé, tu veux que je réessaie ? ».
- La demande est retenue comme **question en attente** (`propositions.proposer`, 120 s, une seule à la fois, même origine).
- `apprentissage.preparer` regarde d'abord si le message répond à cette question. La réponse est une forme courte et fermée, comparée sur la phrase normalisée :
  - « oui », « vas-y », « réessaie »… : la demande est routée par le chemin normal (classifieur, validateur, confirmations) ;
  - « non », « laisse tomber »… : « D'accord, je n'y touche pas. » ;
  - toute autre phrase ferme la question : un « oui » tardif ne déclenche rien.
- Aucun modèle de langue dans ce chemin.

### 4.2 AQ2 — SQLite (`core/apprentissage_store.py`, `scripts/backup_memory.py`)

- **Tables :**
  - `appris(id, type, libelle, meta JSON, cree, maj)` : corrections, méthodes, refus, habitudes écartées ;
  - `propositions(cle, quand)` : limites de fréquence ;
  - `etat(cle, valeur)` : interrupteur des suggestions.
- **Écritures atomiques :** une transaction par écriture (`with conn:`), journal SQLite par défaut, `synchronous=FULL`.
- **Verrou :** `acquire_memory_lock` sur le fichier, le même verrou que `data/chromadb`. Un second processus lève `Indisponible`. Atlas continue sans apprentissage, et la bascule « apprentissage » est dite.
- **Chemin :** `ATLAS_APPRENTISSAGE_DB` (rejeux sur copie). Les tests ont leur propre fichier (`conftest.py`). `vider_pour_test()` refuse le vrai fichier.
- **Sauvegarde** (`backup_memory.py`) :
  - `backup` copie `apprentissage.db` et `habits.db` (voisins de `data/chromadb`) par l'API de sauvegarde de SQLite, dans `<sauvegarde>/sqlite/` ;
  - le manifeste reçoit l'empreinte, les décomptes par table et `integrity_check` ;
  - `verify` rouvre chaque base sur une copie jetable et compare ;
  - `restore` met de côté le fichier en place (`.avant_restauration_<horodatage>`) puis le remet ;
  - le verrou d'`apprentissage.db` est pris : Atlas lancé, le script refuse.
- **Collections :** `atlas_apprentissage`, `atlas_habits` et `atlas_context_apps` sont retirées de `PARTITIONS` et de `settings.json`, et ne sont donc plus créées. `scripts/retirer_collections_vides.py` les supprime de la mémoire :
  - plan seulement sans `--oui` ;
  - refus sans verify réussi ;
  - refus si l'une d'elles n'est pas vide.

  **Pas lancé avec `--oui` sur la mémoire réelle** (§7, risque 1).
- **`atlas_errors`** reste une archive, documentée.

### 4.3 AQ3 — tes refus (`core/apprentissage.py`, `core/intent_engine.py`, `api/routes.py`)

- **La confirmation porte la demande et son origine :** `request_confirmation` les met dans l'attente (`demande`, `origine`) et calcule le **rappel**.
- **Annuler** (`/api/confirm`, `accepted=false`) :
  - `noter_refus(demande, outil, cible, origine)` ne retient que l'origine d'Alexis et une confirmation **non expirée** ;
  - enregistrement `refus`, clé = outil + demande normalisée, compteur « d'affilée ».
- **Expiration :** rien n'est retenu (le dialogue se ferme sans rien envoyer ; le serveur purge).
- **Rappel** : à partir du 2ᵉ refus d'affilée, `rappel_refus` renvoie « Les deux dernières fois, tu as annulé « … ». Je te le propose quand même ; si tu voulais autre chose, dis « non, je voulais… ». ». Il est placé :
  - en tête du message de confirmation (`/api/chat`, flux) ;
  - dans le dialogue du bureau ;
  - dans l'annonce vocale.

  La confirmation est toujours demandée, et l'action toujours exécutable.
- **Acceptation :** `accepte()` efface le refus, car Alexis a changé d'avis.
- **Retiré :** `save_rejection`. Il écrivait en mémoire Chroma « L'utilisateur a refusé… Ne pas reproduire », **quelle que soit l'origine** : c'est le mécanisme de la fausse « correction » de G-bis.
- **Effet utile supplémentaire (proposé, non fait) :** voir §9 P2. La stratégie `confirm` d'Apprentissage 1 n'est pas réintroduite : le rappel est l'effet observable demandé.

### 4.4 AQ4 — tes habitudes (`core/habitudes.py`)

- **Événements :**
  - ouvertures réussies : `launch_app`, `window_focus` venu d'une demande d'ouverture, `workflow_run` ;
  - seules comptent les entrées dont l'**origine** est celle d'Alexis. Ce champ est écrit au journal à partir de ce sprint (`log_action(origine=…)`) ;
  - les étapes d'un mode ou d'une automatisation (`user_input` « workflow:… », « automation:… ») sont écartées : le mode compte, pas ses étapes ;
  - nom d'application normalisé, tirets en espaces (« bloc-notes » = « bloc notes », trouvé au rejeu).
- **Calcul :**
  - enchaînement A → B (chaque ouverture de A compte une fois pour B si B suit dans N minutes) ;
  - tranche horaire ;
  - K occurrences sur D jours.

  Résultat trié, mêmes entrées → même liste.
- **Proposition** (`_avec_proposition`, en fin de réponse, sur `/api/chat`, le flux et la voix). Une seule question, choisie dans cet ordre :
  1. un enchaînement dont A vient d'être ouvert et B pas dans les N dernières minutes ;
  2. sinon une habitude horaire de la tranche actuelle, si l'application n'a pas été ouverte aujourd'hui.

  Pas de proposition :
  - pendant une confirmation, une désambiguïsation ou une autre question en attente ;
  - si les suggestions sont coupées ;
  - si l'apprentissage est neutralisé ;
  - pour une demande qui ne vient pas d'Alexis.
- **Limites :** une fois par habitude et par jour, X par heure au total (table `propositions`).
- **« arrête de me proposer ça »** (formes fermées) : écarte la dernière habitude proposée (enregistrement `habitude_ecartee`, listé). **« arrête les suggestions » / « reprends les suggestions »** : interrupteur dans `etat`.
- **Liste et oubli :** les habitudes actives apparaissent dans « qu'est-ce que tu as appris ? ». « Oublier » une habitude calculée l'écarte (on n'efface pas le journal d'Alexis) ; effacer l'écartée la rend de nouveau proposable.

### 4.5 AQ5 et protections

- Trois formes de correction en plus, et des négatifs (`_VOULU_VIDE` : « toi », « moi », « ça », « du tout », « pour rire »…).
- `tests/gb1_mesure.py` isole l'état du monde comme `mesure_routes.py`, et compte les écritures SQLite comme des écritures.
- **Hors du brief, ajouté et justifié :** les scripts qui lancent un Atlas réel (`rejeu_*`, `checkup_dynamique`, `mesure_ressources`) redirigent le journal et l'apprentissage vers leur copie. Un test permanent le vérifie. **Constaté :** les rejeux des sprints Check-up, Fiabilité et Apprentissage 1 ont écrit dans le vrai `data/atlas_actions.jsonl`, par exemple 28 lignes AtlasEssai… et des « ouvre la calculatrice » le 15/10 (§7, risque 2).

---

## 5. Résultats des tests

### 5.1 Suite complète (code final)

```
.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider
```

| Contexte | Résultat | Code |
|---|---|---|
| Ollama 0.40.4 lancé | **1 197 passed in 382.23s**, « tests ignorés : 0 » | 0 |
| Ollama arrêté (API muette vérifiée) | **1 194 passed, 3 skipped in 403.49s**, 3 justifiés et 0 fautif | 0 |

Ollama a été relancé ensuite ; il répond en 0.40.4.

Les 3 tests ignorés sans Ollama sont les mêmes qu'aux sprints précédents :
- `test_honesty_gbis.py::test_gb1_vrai_modele_aucune_affirmation_transmise` ;
- `test_sprint_kimi_understanding_v51.py::test_grounding_layer_order_steam_includes_heuristic` ;
- `test_vision_parsers.py::TestGroundingTimeoutEnforced::test_layer_timeout_aborts_slow_layer`.

### 5.2 Suites touchées

| Suite | Résultat |
|---|---|
| `tests/test_apprentissage_2.py` (nouvelle) | 48 passés |
| `tests/test_apprentissage.py` (Apprentissage 1, sur SQLite) | 39 passés |
| `tests/test_sans_docker.py` (SD3, sauvegarde) | passe, avec les nouveaux tests SQLite |
| `tests/test_checkup.py` (CK3, configuration lue) | passe |
| `tests/test_memory_v60.py` | passe |
| Corpus de routes (`scripts/mesure_routes.py`, apprentissage vide sur fichier jetable) | **234 / 235 — 99,6 %**, 0 action à tort (seul écart : l'horoscope, connu depuis Fiabilité) |
| GB1 (`tests/gb1_mesure.py`, Ollama 0.40.4) | 34 / 34 actions routées vers un outil, 0 affirmation ; 0 question ordinaire bloquée sur 20 ; **0 différence** avec la mesure du sprint 1, demande par demande |

### 5.3 Rouge d'abord : ce qui l'a suivi, ce qui ne l'a pas suivi

**Rouges d'abord :**
- AQ1 : 3 tests, « 2 clics reçus » ;
- AQ2 : sauvegarde, vérification, restauration, altération, verrou de sauvegarde (3 échecs) ;
- AQ3 : 2 tests positifs rouges ; les 4 négatifs passaient déjà, comme attendu ;
- AQ4 : 9 tests rouges, puis 2 rouges trouvés au rejeu : tiret, étapes de modes ;
- AQ5 : 7 rouges.

**Écrits après le code (passés du premier coup), et dits ici :**
- les 3 tests du stockage (dans SQLite, écriture ratée, second Atlas refusé) ;
- les 2 tests de `retirer_collections_vides.py` ;
- le test qui interdit à un script d'essai d'écrire dans le journal d'Alexis : écrit après avoir corrigé les scripts.

**Modifiés :**
- `test_ap2_memoire_indisponible…` (Apprentissage 1) : l'indisponibilité est maintenant produite sur SQLite au lieu de couper ChromaDB ; ce qu'il vérifie n'a pas changé ;
- `test_memory_v60::test_partitions_created` : les partitions retirées sont vérifiées **absentes** ;
- `test_aq4_habitude_horaire` : l'assertion attend le nom normalisé (« bloc notes ») depuis la correction du tiret.

---

## 6. Comportement observé en scénarios utilisateur réels

```
.venv/Scripts/python.exe scripts/rejeu_apprentissage_2.py --out <dossier temporaire>/aq_apres --neutralise
.venv/Scripts/python.exe scripts/rejeu_apprentissage_2.py --out <dossier temporaire>/aq_avant --racine <worktree de main @ b45cb75> --parties aq1
```

Le rejeu lance Atlas réel quatre fois : trois avec l'apprentissage, une neutralisée. Il tourne sur une copie de la mémoire, un `apprentissage.db` neuf et un journal synthétique :
- Steam puis Discord, trois jours ;
- Bloc-notes puis Calculatrice, trois jours.

« Le lendemain » est simulé entre deux lancements en vidant la table `propositions` **de la copie**. Arrêts : 4 sur 4 « propre ».

### 6.1 AQ1

| ID | Commande | Attendu | Observé avant | Observé après | Statut |
|---|---|---|---|---|---|
| R1 | « clique sur Envoyer dans AtlasEssaiEnvoi » | 1 clic, dit honnêtement | **2 clics** ; « Clic OCR … confiance=96% » | **1 clic** ; « … je n'ai pas pu vérifier… tu veux que je réessaie ? » | PASS |
| R2 | « clique sur Magasin dans AtlasEssaiSombre » | 1 clic | 1 clic (vérification réussie) | 1 clic (vérification ratée, dite) | PASS |

Le résultat de la vérification sur la fenêtre sombre varie d'une exécution à l'autre : sur 4 exécutions aujourd'hui, l'OCR a lu « Magasin » à 96 % ou a échoué. La fenêtre « Envoyer » est le cas qui se reproduit à coup sûr.

### 6.2 AQ3 : voir le tableau de tête

Les 5 étapes sont conformes, et la fenêtre a bien été fermée à la confirmation. Le message après confirmation est « Fenêtre '' fermée. » (titre vide) : défaut d'affichage antérieur (§7, risque 6).

### 6.3 AQ4

| ID | Lancement | Commande | Observé | Statut |
|---|---|---|---|---|
| H1 | 1 | « ouvre steam » | « Steam était déjà lancé : je ramène sa fenêtre… » puis « **Tu ouvres souvent discord après steam. Je l'ouvre ?** » ; rien d'autre n'est ouvert | PASS |
| H2 | 1 | « oui » | Discord ramené au premier plan (déjà lancé), par le chemin normal | PASS |
| H3 | 1 | « ouvre le bloc-notes » | Bloc-notes lancé, puis « Tu ouvres souvent calculatrice après bloc notes. Je l'ouvre ? » ; personne ne répond, la Calculatrice n'est pas ouverte | PASS |
| H4 | 2 (lendemain) | « ouvre steam » | pas de proposition : Discord avait été ouvert moins de 10 minutes avant (règle « B pas ouvert dans les N dernières minutes ») | PASS |
| H5 | 2 | « ouvre le bloc-notes » puis « arrête de me proposer ça » | proposée, puis « D'accord, je ne te proposerai plus ça (tu ouvres souvent calculatrice après bloc notes). » | PASS |
| H6 | 3 (lendemain) | « ouvre le bloc-notes » ; « qu'est-ce que tu as appris ? » | plus de proposition ; la liste montre « Habitude écartée : tu ouvres souvent calculatrice après bloc notes — je ne la propose plus » | PASS |
| H7 | 4 (neutralisé) | « ouvre steam », « ouvre le bloc-notes » | aucune proposition | PASS |

Steam et Discord étaient déjà ouverts sur le PC : Atlas n'a fait que les ramener au premier plan. Le Bloc-notes ouvert par le rejeu a été refermé (PID notés avant et après).

### 6.4 AQ5

| ID | Lancement | Commande | Observé | Statut |
|---|---|---|---|---|
| L1 | 1 | « ouvre le bloc-notes » | résolu par le nom (`known_exact`), lancé, puis refermé par le rejeu | PASS |
| L2 | 2 | « ouvre le bloc-notes » | `resolved_by=appris`, « … (appris : lancé par le chemin qui avait marché) » | PASS |
| L3 | 4 (neutralisé) | « ouvre le bloc-notes » | `known_exact`, comme L1 | PASS |
| P1 | 1 | « mets AtlasEssaiPyw au premier plan » (une 2ᵉ fenêtre « AtlasEssaiPyw outils » rend pywinauto ambigu) | pywinauto ✗ → pygetwindow ✓ | PASS (ordre) |
| P2 | 2 | idem | **pygetwindow ✓ seul**, « (appris : méthode « pygetwindow » d'abord) » | PASS (ordre) |
| P3 | 4 (neutralisé) | idem | pywinauto ✗ → pygetwindow ✗ → win32 ✗ (×3) : « Aucune fenêtre trouvée » | ordre PASS ; premier plan FAIL |

**Ce que montrent P1 à P3 :**
- L'ordre appris est appliqué et neutralisable.
- Mais pygetwindow a mis au premier plan « AtlasEssaiPyw **outils** », pas la fenêtre demandée (§7, risque 3).
- Au lancement neutralisé, les trois méthodes ont échoué : Windows refuse parfois le premier plan à un processus d'arrière-plan. C'était déjà observé au rejeu précédent (P2 en échec complet au 2ᵉ passage), et c'est sans lien avec l'apprentissage (§7, risque 4).

### 6.5 Mémoire réelle et données d'Alexis (règle C3)

| Élément | Avant | Après |
|---|---|---|
| atlas_memory_e5 / atlas_memory / atlas_errors / atlas_conversations / atlas_documents | 276 / 489 / 20 / 19 / 8 | 276 / 489 / 20 / 19 / 8 |
| atlas_apprentissage / atlas_habits / atlas_context_apps | 0 / 0 / 0 | 0 / 0 / 0 (**non retirées**, §7, risque 1) |
| `data/apprentissage.db` | absent | **absent** (rien appris des essais) |
| `data/atlas_actions.jsonl` | 1 069 lignes | 1 069 lignes (empreinte identique après chaque rejeu) |
| `data/habits.db` | empreinte | identique (remis en état après chaque rejeu) |
| Sauvegardes faites | — | deux, dans le dossier de sauvegardes habituel (horodatées 17:50:13 et 17:51:58) ; rien n'a été effacé |

Rien n'a été écrit dans la mémoire réelle, donc la règle C3 n'avait rien à retirer.

---

## 7. Limites et risques identifiés

1. **La vérification des sauvegardes n'est pas fiable sur ChromaDB 1.5.1.**
   - Sévérité : **Élevé**.
   - Sur une sauvegarde dont les fichiers sont identiques octet pour octet, trois relevés successifs des 40 requêtes donnent deux résultats différents.
   - Dans le manifeste, un élément (`action_history_04b9b3642a7a`) manquait de 7 résultats où il revient ensuite, jusqu'en 1ʳᵉ position (distance 0,1956). Il manquait de la lecture, pas de la sauvegarde.
   - La seconde sauvegarde n'a pas pu être vérifiée : « hnsw segment reader: Nothing found on disk ».
   - Conséquence : **les trois collections vides n'ont pas été supprimées**. La règle « après une sauvegarde vérifiée » n'est pas remplie, et je ne l'ai pas contournée (ni nouvelle tentative jusqu'au succès, ni assouplissement du contrôle).
   - Mitigation, **à décider par Alexis ou le superviseur** :
     - (a) accepter une vérification qui compare les ensembles de résultats plutôt que l'ordre exact, en plus des empreintes déjà identiques ;
     - (b) relancer `verify` plusieurs fois et exiger une majorité ;
     - (c) laisser les collections vides en place (elles ne sont plus ouvertes par Atlas).

     Une fois la vérification acceptée, le script est prêt :
     ```
     python scripts/retirer_collections_vides.py --sauvegarde <dossier> --oui
     ```
2. **Le vrai journal des actions contient des traces d'essais.**
   - Sévérité : **Moyen**.
   - Rejeux des sprints Check-up, Fiabilité et Apprentissage 1, tests anciens, étapes de modes. Exemple : 28 lignes AtlasEssai… le 15/10.
   - Il n'est plus pollué : redirection et test permanent.
   - Il ne sert pas aux habitudes, puisque seules les entrées avec l'origine d'Alexis comptent, et aucune ancienne n'en a.
   - **Faut-il retirer ces lignes ?** C'est un journal d'Alexis : je demande, je ne fais rien.
3. **Le premier plan peut viser la mauvaise fenêtre.**
   - Sévérité : **Moyen**. Défaut antérieur, pas introduit par ce sprint.
   - `_premier_plan_pygetwindow` prend la première fenêtre dont le titre **contient** le nom : « AtlasEssaiPyw » a ramené « AtlasEssaiPyw outils ».
   - `resolve_app_window` avait pourtant trouvé la fenêtre exacte : il faudrait passer son `hwnd` aux méthodes.
4. **Windows refuse parfois le premier plan.**
   - Sévérité : **Moyen**. Antérieur.
   - Les trois méthodes échouent quand Atlas n'a pas reçu la dernière entrée (règle de Windows sur le premier plan). C'est vu au rejeu neutralisé, et déjà au rejeu d'Apprentissage 1.
   - Mitigation : technique `AttachThreadInput` ou touche Alt simulée, à mesurer.
5. **La vérification après clic dépend de l'OCR.**
   - Sévérité : **Moyen**.
   - Sur la fenêtre sombre, elle réussit ou échoue d'une exécution à l'autre. Elle ne reclique plus, mais elle peut dire « je n'ai pas pu vérifier » alors que le clic a marché.
   - Le message dit l'incertitude, sans prétendre à l'échec.
6. **« Fenêtre '' fermée. »**
   - Sévérité : **Faible**. Antérieur.
   - Le message de `window_close` confirmé perd le titre.
7. **Les habitudes affichent le nom normalisé** (« bloc notes », « discord »).
   - Sévérité : **Faible**.
8. **Les réponses « oui » / « non » et les commandes d'habitude sont des listes fermées.**
   - Sévérité : **Faible**.
   - Une forme absente (« carrément ») ferme la question sans rien faire. C'est voulu : rien ne s'exécute sur une réponse incertaine.
9. **Fermer le dialogue de confirmation par la croix compte comme Annuler.**
   - Sévérité : **Faible**.
   - C'est un geste explicite d'Alexis, et c'est le comportement existant du bureau (`WM_DELETE_WINDOW` → annuler).
10. **Non rejoués en réel :** la question « tu veux que je réessaie ? » suivie d'un « oui », l'interrupteur global des suggestions, la voix au micro.
    - Sévérité : **Faible**. Couverts par des tests sur le vrai chemin.

---

## 8. Checklist de validation

- [x] Un clic non vérifié : 1 clic, jamais 2, et c'est dit ; prouvé avec une fenêtre qui compte les clics (tableau de tête, §6.1)
- [ ] Ce qui est appris est dans SQLite ; sauvegarde et restauration l'incluent ; **collections vides retirées après une sauvegarde vérifiée** ; `atlas_errors` documentée comme archive → tout est fait **sauf le retrait des collections dans la mémoire réelle** : aucune vérification n'a réussi (§7, risque 1). Retirées de la configuration et du code ; script prêt et testé.
- [x] Refus : Annuler compte, l'expiration non ; au 2ᵉ refus, la réponse change ; aucune confirmation sautée (§6.2, tests AQ3)
- [x] Habitudes : calcul déterministe, configuration lue ; proposer sans jamais exécuter ; limites de fréquence ; « arrête » respecté (§6.3)
- [x] Habitudes détectées dans le vrai journal listées pour Alexis, rien écrit (tableau de tête)
- [x] Lancement appris et ordre du premier plan rejoués en réel (§6.4 ; le premier plan lui-même a des défauts antérieurs, §7, risques 3 et 4)
- [x] Corpus ≥ 99,6 % ; GB1 à 0 ; suite code 0 avec et sans Ollama (§5)

---

## 9. Recommandations pour le sprint suivant

**À décider par Alexis :**
1. La vérification des sauvegardes (§7, risque 1) : (a), (b) ou (c). Puis le retrait des trois collections vides.
2. Les lignes d'essais dans `data/atlas_actions.jsonl` (§7, risque 2) : les garder ou les retirer (après sauvegarde).
3. L'habitude « notepad vers 18 h » trouvée dans son journal (toutes origines) : juste ou non ? Elle ne sera proposée de toute façon que si elle se reproduit avec son origine.

**P1 — fiabilité**
- Premier plan : utiliser le `hwnd` de la fenêtre résolue dans les trois méthodes (risque 3) ; mesurer une technique contre le refus de premier plan de Windows (risque 4).
- Rendre la vérification des sauvegardes robuste à la lecture non déterministe de ChromaDB, sans l'affaiblir. Par exemple : empreintes, décomptes, et ensembles de résultats stables sur trois lectures.

**P2 — robustesse**
- Refus : un effet plus utile serait de **proposer la correction apprise** quand Alexis a annulé puis corrigé (« non, je voulais… ») juste après. Aujourd'hui, la correction s'apprend déjà par AP2 ; le lien explicite refus → correction n'est pas fait. À justifier par des sessions réelles.
- Vérification après clic : une seconde lecture (EasyOCR) avant de dire « je n'ai pas pu vérifier » sur une cible sombre (risque 5).

**P3 — qualité**
- Noms d'applications lisibles dans les habitudes (risque 7) ; titre dans « Fenêtre '' fermée » (risque 6).
- Rejouer en réel « tu veux que je réessaie ? » → « oui », et l'interrupteur des suggestions.

**Hors scope ajouté (§4.5) :**
- la redirection du journal et de l'apprentissage dans tous les scripts qui lancent Atlas, avec le test permanent ;
- le champ `origine` du journal.

Les deux étaient nécessaires pour que les habitudes ne viennent que d'Alexis.
