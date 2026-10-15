# RAPPORT SPRINT APPRENTISSAGE 1 — Atlas retient tes corrections et ses échecs
Date: 15/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_APPRENTISSAGE_1.md`. Branche **`sprint-apprentissage-1`**, issue de `main` @ `90e61f9` (Fiabilité fusionné). Commits non poussés.
> Rejeux réels faits sur une **copie** de la mémoire (`ATLAS_CHROMA_PATH`) : la mémoire réelle n'a rien appris pendant le sprint (§6.4).

---

## Tableau de tête

### AP1 — Couches tentées, rejeu réel final (Atlas réel, fenêtres de test, même copie de mémoire, Atlas relancé entre les passes)

| Fenêtre de test | Passe 1 (rien d'appris) | Passe 2 (après la passe 1, Atlas relancé) | Passe 3 (apprentissage neutralisé) |
|---|---|---|---|
| Claire (« Bibliothèque », 20 pt) | uia ✗ 827 ms → cache ✗ → **ocr ✓** — **4,18 s** | **ocr ✓** seul — **2,96 s** (−1,22 s), « (appris : je commence par « ocr ») » | uia ✗ → cache ✗ → ocr ✓ — 3,65 s |
| Sombre (« Magasin », 10 pt gris sur gris) | uia ✗ 687 ms → cache ✗ → ocr ✗ 765 ms → **easyocr ✓** — **19,99 s** | **easyocr ✓** seul — **17,56 s** (−2,43 s), « (appris : je commence par « easyocr ») » | uia ✗ → cache ✗ → ocr ✗ → easyocr ✓ — 18,90 s |

Le clic est arrivé dans la fenêtre à chacune des 6 demandes. Un premier rejeu, fait avec le code d'avant la correction du §5.3, donne les mêmes couches et des gains de −0,94 s et −2,52 s (§6.1).

### AP2 — Une correction apprise puis appliquée (rejeu réel, origine « fenêtre », sur copie)

| # | Ce qui est tapé | Réponse d'Atlas |
|---|---|---|
| 1 | « mets le témoin devant » | « Je ne sais pas encore faire ça. » (mauvaise route) |
| 2 | « non, je voulais mets AtlasEssaiTemoin au premier plan » | « D'accord : « mets le témoin devant », c'était « mets AtlasEssaiTemoin au premier plan ». Je le retiens. » + fenêtre mise au premier plan |
| — | *Atlas arrêté puis relancé* | |
| 3 | « mets le témoin devant » | « **Comme tu me l'as appris**, je comprends « mets AtlasEssaiTemoin au premier plan ». » + fenêtre au premier plan |
| 4 | « qu'est-ce que tu as appris ? » | la correction, les 2 clics, le premier plan |
| 5 | « oublie ce que tu as appris sur mets le témoin devant » | **confirmation demandée** ; acceptée → « C'est oublié (1 élément(s)) » |
| 6 | « mets le témoin devant » | « Je ne sais pas encore faire ça. » : le comportement d'avant |

### AP0 — ChromaDB : échecs de lecture sur 100 ouvertures, par version

| Version | Base neuve à chaque ouverture (100) | Copie de la mémoire réelle (50) |
|---|---|---|
| 1.4.1 (la version qui tournait dans Docker) | **20** | — |
| **1.5.1 (épinglée, gardée)** | **7** | **0** |
| 1.5.5 | **12** | — |
| 1.5.9 (la plus récente) | **6** | **0** |

**Aucune version n'atteint 0 sur 100.** La 1.5.1 reste épinglée, le filet est gardé, et un signalement en amont est prêt mais n'est pas publié (`docs/chromadb_signalement.md`).

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.** AP1 à AP4 sont faits et prouvés en réel. AP0 se termine sur l'issue prévue par le brief quand aucune version ne passe : l'échec est dit, le filet est gardé, le signalement est prêt. Le critère « une version à 0/100 » n'est pas atteint.

**Runtime :**
- Ollama 0.40.4, la version installée ;
- ChromaDB 1.5.1 en paquet ;
- mémoire réelle seulement lue (décomptes) ;
- les rejeux tournent sur copie, et `habits.db` est remis en état après chaque rejeu.

**Chiffres :**
- **Suite (code final) :** 1 149 passés, 0 ignoré, code 0 avec Ollama ; sans Ollama, 1 146 passés et 3 ignorés justifiés, code 0 (§5.5).
- **AP1 :** les couches tentées changent entre la passe 1 et la passe 2, et la passe 3 neutralisée retrouve la passe 1. Gain mesuré sur deux rejeux réels : −0,94 à −1,22 s (−25 à −29 %) sur la fenêtre claire, −2,43 à −2,52 s (−12 à −13 %) sur la sombre. Les 4 défauts du rapport D sont corrigés. Ce qui est appris va au-delà du clic : premier plan et restauration de fenêtre, lancement d'application.
- **Trouvé par le rejeu et corrigé :** un ordre appris n'était pas annoncé quand la vérification après clic échouait (fenêtre sombre). **Trouvé et non corrigé, car hors du périmètre :** cette vérification ratée fait cliquer Atlas une **deuxième fois** (§7, risque 2).
- **AP2 :** correction reconnue, avec 8 formulations positives et 11 négatives testées. Elle est exécutée, retenue, appliquée et dite après redémarrage, listée, puis oubliée après confirmation.
- **AP3 :** corpus de routes à 234/235 (99,6 %) avec une mémoire d'apprentissage vide, 0 action à tort. GB1 : 0 affirmation sur 34 sous Ollama 0.40.4.
- **Retiré :** `core/error_learning.py`, l'ancien mécanisme F4 qui n'a jamais changé le comportement.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| Décision : « ouvre les paramètres » → paramètres de Windows | Fait au sprint Fiabilité. Ce sprint n'y touche pas ; il reste couvert par le corpus de routes, à 100 % sur la famille « système ». | PASS |
| Décision : `doctor.py` accepte 0.40.x sans avertir | `ollama_version_check` compare la version **mineure**, avec la référence 0.40.4. Test paramétré : 0.40.3 et 0.40.9 → OK ; 0.41.0 et 0.39.9 → avertissement. | PASS |
| Décision : remesurer GB1 sur la version installée | 0.40.4 : **0/34** affirmations, 32 réponses fixes, 0 question ordinaire bloquée sur 20. | PASS |
| Décision : dépôt renommé `Atlas`, toute mention mise à jour | Seule mention hors historique : le runbook `core_conversational`, mis à jour. Le changement du `remote` local m'a été **refusé** par la session, et je ne l'ai pas contourné : la commande à lancer est en §9. | PARTIEL |
| AP0.1 — script de reproduction, 100 ouvertures, `get`/`count` puis `query` | `scripts/repro_chroma.py`, autonome, avec deux modes : `fraiche` (base neuve) et `copie --source` (refuse la vraie `data/chromadb`). | PASS |
| AP0.2 — 1.4.1, la plus récente et une intermédiaire, sur copie | 1.4.1, 1.5.1, 1.5.5 et 1.5.9 sur bases neuves (100 chacune). 1.5.1 et 1.5.9 aussi sur copie de la mémoire (50 chacune). Chaque version a tourné dans un environnement jetable, supprimé ensuite. | PASS |
| AP0.3 — version retenue : 0/100, 40 requêtes du garde-fou identiques, backup/verify/restore | **Aucune version à 0/100** (minimum : 6, en 1.5.9). Il n'y a donc pas de version retenue, et les étapes « garde-fou » et « restore » de la nouvelle version n'ont pas lieu d'être. | FAIL |
| AP0.4 / AP0.5 — épingler, ou dire l'échec, garder le filet, signalement | 1.5.1 reste épinglée. Le filet est gardé : reprise dans `MemoryManager._interroger`, nouvel essai dans `backup_memory.summarize`, bascule `memoire_partielle`. Signalement prêt en anglais avec la reproduction, **non publié** : c'est à Alexis de l'envoyer. | PASS |
| AP1 — test de bout en bout, rouge d'abord, passes 1 / 2 / 3 | `test_ap1_bout_en_bout_…` sur le vrai `chat_endpoint`. Premier lancement du fichier : **26 échecs et 11 erreurs**. Il est vert ensuite. | PASS |
| AP1.1 — la couche enregistrée est une vraie couche | Ce qui est retenu vient de `layer_attempts` (uia, cache, ocr, easyocr…), jamais de `all_failed` ni de `global_timeout`. Test dédié. | PASS |
| AP1.2 — la cause est bien classée | `classify_cause` part des vrais messages. « Aucune couche n'a réussi » donne `not_found` (le rapport D le trouvait en `other`). 5 messages réels testés. | PASS |
| AP1.3 — les trois stratégies appliquées, ou retirées | `skip_layer` devient « méthodes à éviter, tentées en dernier ». `reformulate` devient « 2ᵉ échec complet : la réponse change et demande le nom exact ». `confirm` est **retiré** (§4.2). | PASS |
| AP1.4 — au-delà du clic | Premier plan et restauration : la méthode qui marche (pywinauto, pygetwindow ou win32) est tentée en premier. Lancement : le chemin qui a marché est repris directement. Chaque mécanisme a son test ; le premier plan a aussi été vu en réel. | PASS |
| AP1 — apprendre des réussites, gain mesuré | Gagnante en premier : −1,22 s et −2,43 s en réel (tableau de tête) ; −0,94 s et −2,52 s au premier rejeu. | PASS |
| AP1 — C3 sur les 3 entrées `err_…` d'anciens tests | Les 3 sont **déjà absentes**. Les 20 entrées restantes de `atlas_errors` viennent des sessions d'Alexis et ne sont pas touchées. Rien n'a été retiré, donc il n'a pas fallu de sauvegarde. | PASS |
| AP2.1 — reconnaître une correction (corpus avec négatifs) | 8 formulations positives, dont « pas X, Y » et « je t'ai demandé… », et 11 négatives, dont « non merci », « non c'est bon » et « non je voulais juste savoir ». Une correction n'est reconnue que s'il y a un échange précédent de moins de 180 s. | PASS |
| AP2.2 / AP2.3 — route voulue, exécutée avec ses confirmations, enregistrée | La partie voulue repasse par le classifieur et le validateur comme une demande normale. Ce qui est enregistré : demande d'origine normalisée → phrase voulue. | PASS |
| AP2.4 — la fois suivante : bonne route, et c'est dit | « Comme tu me l'as appris, je comprends … », vu en réel après redémarrage. | PASS |
| AP2.5 — conflit avec le corpus journalisé ; corpus 99,6 % avec mémoire vide | Le conflit est journalisé et la correction prime (test ajouté après coup, §5.3). Corpus à 234/235. | PASS |
| AP2.6 — correction vers une action destructive : confirmation à chaque fois | Test : « dégage le témoin » appris comme « ferme AtlasTemoin » demande confirmation la 1ʳᵉ fois **et** la 2ᵉ. | PASS |
| AP2.7 — lister, oublier avec confirmation et libellé lisible | Vu en réel. `CONFIRMATION_POLICY["apprentissage_oublier"]` vaut « toujours », et le bureau affiche « Oublier ce que j'ai appris ». | PASS |
| AP2 — rejeu réel | Tableau de tête, demande fabriquée sur une fenêtre de test. | PASS |
| AP3 — avant/après/neutralisé permanent pour AP1 et AP2 sur `/api/chat` | `tests/test_apprentissage.py`, 39 tests, inclus dans la suite. | PASS |
| AP3 — aucune bascule silencieuse | Si la mémoire d'apprentissage est indisponible, Atlas fait la bonne demande et la bascule « apprentissage » est signalée et dite. Test dédié. | PASS |
| AP3 — suites code 0 avec et sans Ollama, 0 ignoré tout lancé | Code final : avec Ollama 1 149 / 0 ignoré ; sans Ollama 1 146 + 3 ignorés justifiés. | PASS |
| AP3 — C3 : décomptes avant/après, rien appris des essais | Décomptes identiques et `atlas_apprentissage` vide dans la mémoire réelle (§6.4). | PASS |
| AP4 — rapport avec la tête demandée | Ce document. | PASS |

---

## 3. Architecture projet mise à jour

```
api/
  models.py                     ChatRequest.origine
  routes.py                     preparer → _chat → noter_echange ; annonce ; origine dans le contexte
config/settings.json            memory.collections.apprentissage = "atlas_apprentissage"
core/
  apprentissage.py              ← NOUVEAU (Apprentissage 1)
  error_learning.py             ← SUPPRIMÉ (F4, sans effet — rapport D §4.1)
  intent_classifier.py          catégorie « apprentissage » : lister / oublier
  intent_engine.py              ordre appris avant exécution ; leçon après ; outils lister / oublier
  memory_manager.py             partition apprentissage (écrire / lire / effacer) ; store_error et query_errors retirés
  validator.py                  apprentissage_oublier (confirmation « toujours »)
  voice_engine.py               même chemin pour la voix (origine « voix »)
core_conversational/degradations.py   bascule « apprentissage »
desktop/atlas_desktop.py        origine « bureau » ; libellé de confirmation
docs/
  chromadb_signalement.md       ← NOUVEAU (non publié)
  core_conversational_runbook.md  nouveau nom du dépôt
  rapports/RAPPORT_SPRINT_APPRENTISSAGE_1.md  ← NOUVEAU
scripts/
  doctor.py                     version mineure d'Ollama ; référence 0.40.4
  mesure_routes.py              état du monde mis de côté pendant la mesure
  repro_chroma.py               ← NOUVEAU
  rejeu_apprentissage.py        ← NOUVEAU
tests/
  test_apprentissage.py         ← NOUVEAU (39 tests)
  test_memory_v60.py            tests F4 retirés ; classify_cause importé du nouveau module
  test_pre_beta.py              test de version paramétré (règle 0.40.x)
  gb1_mesure.py                 écritures d'apprentissage comptées comme écritures
  fixtures/corpus_routes.json   +3 demandes (« qu'est-ce que tu as appris ? » …)
tools/
  app_launcher.py               chemin_appris
  grounding.py                  find_and_click(appris=…)
  window_controller.py          méthodes de premier plan séparées, ordre appris, tentatives rendues
ui/app.js                       origine « fenetre »
```

---

## 4. Détail des implémentations

### 4.1 `core/apprentissage.py` (nouveau)

Tout ce qui est appris est un **enregistrement explicite** dans la partition ChromaDB `atlas_apprentissage`. Chaque enregistrement est lu **par identifiant** (sha1 de la clé), jamais par voisinage sémantique : la correspondance est déterministe.

- **Normalisation** (`normaliser`) : minuscules, sans accents ni ponctuation, sans politesse (« stp », « s'il te plaît », « merci »…), sans « tu peux / est-ce que tu peux » en tête. « Mets le témoin devant, stp » et « mets le temoin devant » donnent la même clé.
- **Qui peut apprendre** : seulement les origines `bureau`, `fenetre` et `voix`, portées par `ChatRequest.origine` et posées par l'application de bureau, la fenêtre web et le moteur vocal. Une demande sans origine ne laisse rien : c'est le cas des tests, des scripts et de `curl`. Le cas de G-bis, où les refus du développeur ont été pris pour ceux d'Alexis, ne peut donc pas se reproduire. `ATLAS_APPRENTISSAGE=off` neutralise tout : rien n'est lu, rien n'est écrit.
- **Corrections** :
  - `detecter_correction(phrase, precedente)` applique d'abord les négatifs (`_PAS_UNE_CORRECTION`, `_VOULU_VIDE`), puis trois formes : « non, je voulais (dire) … », « c'est pas ça … » et « je t'ai demandé (de) … » ; puis « pas X, Y », qui reprend le verbe de la demande précédente.
  - Il faut un échange précédent de moins de `FENETRE_SUITE_S` = 180 s.
  - `apprendre_correction` retourne `appris`, `neutralise`, `non_alexis`, `ignore` ou `indisponible`. Il journalise un conflit si la demande d'origine est dans le corpus de routes.
  - `preparer(phrase, origine)` est appelé avant le routage. Il renvoie la phrase à router et l'annonce à dire.
- **Méthodes** (clic, premier plan, lancement) :
  - `noter_methodes(outil, app, cible, tentatives, origine, chemin)` reçoit les **vraies** tentatives : la couche ou la méthode, et son résultat.
  - Sur une réussite, il retient la gagnante (`premiere`) et les méthodes qui ont échoué avant elle (`eviter`).
  - Sur un échec complet, il compte les échecs d'affilée et oublie une gagnante qui vient d'échouer, parce que l'écran a changé.
  - `appliquer_ordre` met la gagnante en premier et les méthodes à éviter **en dernier**, sans les retirer.
- **Contrôle d'Alexis** : `lister`, `chercher`, `oublier` et `texte_liste`. Les libellés sont lisibles, par exemple « Clic sur « magasin » dans « atlasessaisombre » : commencer par « easyocr » ».

### 4.2 Les quatre défauts du rapport D

1. **Couche enregistrée.** `_apprendre_du_resultat` (`core/intent_engine.py`) lit `layer_attempts` pour un clic. Pour le premier plan et la restauration, il lit `tentatives`, que `focus_window` rend désormais. Pour un lancement, il lit `resolved_by` et le chemin. L'issue globale n'est jamais enregistrée comme une couche.
2. **Cause.** `classify_cause` part des messages réellement produits par les outils et rend `not_found`, `timeout`, `app_not_found`, `ambiguous`, `permission_denied` ou `other`.
3. **Stratégies.**
   - `skip_layer` → **« éviter »** : la méthode qui a échoué avant la gagnante est tentée **en dernier**, pas retirée. Une fenêtre qui change (thème, taille) peut lui redonner raison. Effet observable : en passe 2, uia et cache ne sont plus tentés avant ocr.
   - `reformulate` → au **2ᵉ échec complet** d'affilée sur la même application et la même cible, la réponse commence par « Deuxième fois que je n'y arrive pas… dis-moi le nom exact ». Effet observable : la réponse change (test `test_ap1_deux_echecs_totaux_la_reponse_change`).
   - `confirm` → **retiré.** Demander une confirmation après un échec technique ne change pas ce qu'Atlas fait ; c'était une réponse aux refus, et les refus sont l'objet du sprint Apprentissage 2. La règle du brief s'applique : une stratégie sans effet observable est retirée.
4. **Au-delà du clic.**
   - `tools/window_controller.py` : les trois méthodes de premier plan sont séparées (`_premier_plan_pywinauto`, `_premier_plan_pygetwindow`, `_premier_plan_win32`) et essayées dans l'ordre appris. `window_restore` passe par le même chemin.
   - `tools/app_launcher.py` : `chemin_appris` lance directement le fichier qui a marché, s'il existe encore (`resolved_by="appris"`).

**Ancien mécanisme retiré :** `core/error_learning.py` (voisins sémantiques sur `atlas_errors`) avec `store_error` / `query_errors` et ses tests. Il n'a jamais changé le comportement (rapport D §4.1). Les 20 entrées de `atlas_errors` restent en mémoire : ce sont les sessions d'Alexis, et elles ne sont plus lues.

**Annonce.**
- Le suffixe « (appris : …) » est ajouté dès que l'ordre appris a servi, **quelle que soit l'issue** (succès, vérification ratée, échec).
- Pour un lancement, il est ajouté seulement si le chemin appris a réellement servi (`resolved_by == "appris"`).
- Au premier rejeu, il ne l'était qu'en cas de succès : le clic de la fenêtre sombre, terminé en `replan_required`, appliquait l'apprentissage sans le dire.

### 4.3 Intégration dans le pipeline

- `/api/chat` (`api/routes.py`, `chat_endpoint`) :
  - `preparer`, puis le routage normal (`_chat`) ;
  - `noter_echange`, sauf si le message était lui-même une correction ;
  - enfin l'annonce, préfixée une fois.
- `/api/chat/stream` : l'annonce est émise avant le flux.
- La voix (`_run_text_pipeline`) prend le même chemin avec l'origine `voix`.
- **Rien ne contourne :**
  - la phrase apprise repasse par le classifieur, puis par `resolve` du validateur, puis par `CONFIRMATION_POLICY` ;
  - l'ordre des couches ne change que l'ordre d'essai, pas ce qui est cliqué ;
  - aucun appel au modèle de langue n'entre dans la reconnaissance ou la confirmation (invariant 3).
- **Voix « oublie »** : classifieur, catégorie `apprentissage`, puis le validateur (`apprentissage_oublier`, cible lisible), puis confirmation « toujours ». Sans élément correspondant, c'est la liste qui est rendue.

### 4.4 AP0 — `scripts/repro_chroma.py`, `docs/chromadb_signalement.md`

- Mode `fraiche` : chaque ouverture écrit une petite base (4 collections × 12 enregistrements) dans un sous-processus. Un autre processus la relit ensuite dans l'ordre `get(limit=1)` / `count()` puis `query`, et compte les `Nothing found on disk`.
- Mode `copie` : part d'une copie de la mémoire réelle (le script refuse `data/chromadb` lui-même) et y ajoute 3 éléments par ouverture.
- Chaque version a tourné dans un environnement virtuel jetable du dossier temporaire, supprimé ensuite. L'environnement d'Atlas n'a pas changé de version.
- **Choix : garder 1.5.1.** L'écart 7 contre 6 sur 100 n'est pas significatif. Changer de version demanderait la preuve complète (garde-fou, `backup` / `verify` / `restore`) sans gain démontré.

### 4.5 Autres changements

- `scripts/doctor.py` : `_mineure()` ; avertissement seulement si la version mineure diffère de la référence 0.40.4.
- `scripts/mesure_routes.py` : `route()` met `world_state.last_action` de côté pendant la mesure. Sans cela, la fenêtre de travail laissée par un test précédent faisait varier la mesure (constaté pendant le sprint : le corpus échouait quand il tournait après les tests d'apprentissage).
- `tests/gb1_mesure.py` : `apprentissage_ecrire` et `apprentissage_effacer` sont comptés comme des écritures mémoire.
- `docs/core_conversational_runbook.md` : `cd ~/Projet/Atlas` et la nouvelle adresse du dépôt.

---

## 5. Résultats des tests

### 5.1 Suite complète

```
.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider
```

| Contexte | Résultat | Code |
|---|---|---|
| Ollama 0.40.4 lancé | **1 147 passed in 305.81s**, « tests ignorés : 0 » | 0 |
| Ollama arrêté (`ollama app` et `ollama` arrêtés, API muette vérifiée) | **1 144 passed, 3 skipped in 346.05s**, 3 justifiés et 0 fautif (ci-dessous) | 0 |

Ollama a été relancé ensuite ; il répond en 0.40.4.

Les 3 tests ignorés sans Ollama interrogent tous le vrai Ollama :
- `test_honesty_gbis.py::test_gb1_vrai_modele_aucune_affirmation_transmise` ;
- `test_sprint_kimi_understanding_v51.py::test_grounding_layer_order_steam_includes_heuristic` ;
- `test_vision_parsers.py::TestGroundingTimeoutEnforced::test_layer_timeout_aborts_slow_layer`.

Ces deux suites complètes ont été jouées **avant** les trois tests et la correction d'annonce de fin de sprint (§5.3). La suite complète a été rejouée ensuite, avec Ollama, sur le code final (§5.5).

### 5.2 Fichiers par fichier

Toutes les suites existantes (`tests/*.py`) sont incluses dans la commande ci-dessus. Aucune n'est exclue et aucun test n'a été marqué ignoré pour passer. Celles touchées par le sprint :

| Suite | Résultat |
|---|---|
| `tests/test_apprentissage.py` (nouvelle) | 39 passés |
| `tests/test_fiabilite.py` + `test_apprentissage.py` ensemble (fuite d'état du monde vérifiée) | 89 passés (avant l'ajout des 2 derniers tests) |
| `tests/test_memory_v60.py` | passe dans la suite complète (tests F4 retirés avec le module) |
| `tests/test_pre_beta.py` (version d'Ollama) | passe |
| Corpus de routes (`scripts/mesure_routes.py`, mémoire d'apprentissage vide) | **234 / 235 — 99,6 %**, 0 action à tort |

Le seul écart du corpus vient de l'ensemble « hors corpus » de Fiabilité : « c'est quoi mon horoscope du jour ? » part vers `memory_recall`. Il était connu avant ce sprint.

### 5.3 Ordre « rouge d'abord » : ce qui ne l'a pas suivi

- **Premier lancement de `tests/test_apprentissage.py`** : 26 échecs et 11 erreurs, avant le code. Rouge d'abord respecté pour AP1 et AP2.
- **Trois exceptions, dites ici :**
  - `test_pre_beta.py` : le test de version a été **modifié**, pas écrit rouge. La règle a changé (0.40.x accepté), et le test est maintenant paramétré sur 4 versions.
  - Une **assertion** de `test_ap2_correction_appliquee…` attendait la forme sans accent « mets le temoin devant ». Or la liste montre légitimement la phrase telle qu'Alexis l'a tapée, avec « témoin ». C'est l'assertion qui a été corrigée.
  - Deux vérifications ont été ajoutées **après** le code, en relisant le rejeu, et ont passé du premier coup :
    - le libellé sans cible (« Premier plan de « atlastemoin » » au lieu de « Premier plan de «  » dans … », vu dans le rejeu et corrigé avant ce test) ;
    - le conflit avec le corpus journalisé.
- **Correction de l'annonce, rouge d'abord :** `test_ap1_l_apprentissage_est_dit_meme_si_la_verification_du_clic_echoue` a d'abord échoué. Le message était « Clic easyocr sur 'bibliothèque'. », sans « appris », avec le statut `replan_required` : c'est le cas du rejeu réel. Le test passe après la correction (§4.2).

### 5.4 GB1 (Ollama 0.40.4 installé)

```
.venv/Scripts/python.exe tests/gb1_mesure.py --out <dossier temporaire>/ap_gb1.json
```

Résultats sur 54 réponses :
- **0 affirmation sur 34** demandes d'action ;
- 32 réponses fixes ;
- 0 question ordinaire bloquée sur 20.

### 5.5 Suite complète finale (code final)

Même commande, sur le code commité :

| Contexte | Résultat | Code |
|---|---|---|
| Ollama 0.40.4 lancé | **1 149 passed in 320.31s**, « tests ignorés : 0 » | 0 |
| Ollama arrêté (API muette vérifiée) | **1 146 passed, 3 skipped in 357.91s**, les 3 mêmes tests justifiés qu'au §5.1, 0 fautif | 0 |

Ollama a été relancé ensuite ; il répond en 0.40.4.

---

## 6. Comportement observé en scénarios utilisateur réels

```
.venv/Scripts/python.exe scripts/rejeu_apprentissage.py --out <dossier temporaire>/ap_rejeu
```

Le rejeu lance Atlas réel **trois fois** sur la **même copie** de la mémoire, avec de vraies fenêtres tkinter de test. Les demandes portent l'origine « fenetre », c'est-à-dire Alexis au clavier. Atlas est arrêté proprement par `CTRL_BREAK` : 3 arrêts « propre » sur 3.

### 6.1 AP1 — clics

Le rejeu a été joué deux fois. Le premier rejeu tournait sur le code d'avant la correction de l'annonce, le second sur le code final.

| ID | Commande | Attendu | Rejeu 1 | Rejeu 2 (final) | Statut |
|---|---|---|---|---|---|
| R1 | « clique sur Bibliothèque dans AtlasEssaiClair » (passe 1) | clic, couches tardives | uia ✗, cache ✗, ocr ✓ — 3,76 s | uia ✗, cache ✗, ocr ✓ — 4,18 s | PASS |
| R2 | « clique sur Magasin dans AtlasEssaiSombre » (passe 1) | clic, couches tardives | uia ✗, cache ✗, ocr ✗, easyocr ✓ — 18,98 s | idem — 19,99 s | PASS |
| R3 | R1 après relance | ocr en premier, annoncé | ocr ✓ seul — 2,82 s, annoncé | ocr ✓ seul — 2,96 s, annoncé | PASS |
| R4 | R2 après relance | easyocr en premier, annoncé | easyocr ✓ seul — 16,46 s, **pas annoncé** | easyocr ✓ seul — 17,56 s, « (appris : je commence par « easyocr ») » | PASS (rejeu 2) |
| R5 | R1, apprentissage neutralisé | comme la passe 1 | uia ✗, cache ✗, ocr ✓ — 3,33 s | idem — 3,65 s | PASS |
| R6 | R2, apprentissage neutralisé | comme la passe 1 | uia ✗, cache ✗, ocr ✗, easyocr ✓ — 17,93 s | idem — 18,90 s | PASS |

Le clic a été reçu par la fenêtre de test dans les 12 cas.

**R4 au rejeu 1 — cause relevée dans le journal d'Atlas.** Sur la fenêtre sombre, la vérification après clic relit « magasin » avec une confiance de 53 % et conclut que le clic n'est pas vérifié. Le moteur refait alors le clic par le cache, puis rend `replan_required`. Or l'annonce n'était ajoutée qu'en cas de succès. C'est corrigé (§4.2) et confirmé au rejeu 2.

Le même journal montre que cette **vérification ratée provoque un deuxième clic**, dans les 3 passes, apprentissage ou pas (§7, risque 2).

### 6.2 AP2 — correction

Le déroulé est dans le tableau de tête (lignes 1 à 6). Les 6 étapes sont conformes et identiques dans les deux rejeux. La demande corrigée a mis la vraie fenêtre AtlasEssaiTemoin au premier plan, deux fois par rejeu.

### 6.3 Premier plan appris

Au lancement 2, « mets le témoin devant » se termine par « (appris : méthode « pywinauto » d'abord) ». Dans ce cas, pywinauto marchait déjà en premier : l'ordre ne change pas et il n'y a pas de gain à mesurer. Le changement d'ordre (win32 en premier après l'échec de pywinauto et pygetwindow) est prouvé par le test `test_ap1_premier_plan_…`, pas en réel. Le **lancement d'application appris** est, lui aussi, prouvé par test seulement (§7, risque 3).

### 6.4 Mémoire réelle (règle C3)

| Collection | Avant le sprint | Après le sprint |
|---|---|---|
| atlas_memory_e5 | 276 | 276 |
| atlas_memory | 489 | 489 |
| atlas_errors | 20 | 20 |
| atlas_conversations | 19 | 19 |
| atlas_documents | 8 | 8 |
| atlas_habits / atlas_context_apps | 0 / 0 | 0 / 0 |
| atlas_apprentissage | — | **0** (collection créée vide, rien appris) |

- Les 3 entrées `err_d6824758fa78`, `err_0888b88f2bbf` et `err_4cd2a3a29cd7` étaient **déjà absentes** au début du sprint : rien n'a été retiré.
- Les rejeux ont modifié `data/habits.db` ; le fichier a été remis en état à la fin et son empreinte est identique avant et après.

---

## 7. Limites et risques identifiés

1. **ChromaDB : aucune version à 0 échec.**
   - Sévérité : **Élevé**.
   - Sur des bases neuves, 6 à 20 échecs sur 100 ouvertures selon la version. Sur une copie de la mémoire réelle, 0 sur 50 en 1.5.1 et en 1.5.9.
   - Le défaut semble lié aux collections fraîchement écrites. L'apprentissage, qui écrit dans une collection jeune, y est donc exposé.
   - Mitigation :
     - le filet est gardé (réouverture, puis bascule `memoire_partielle`) ;
     - un apprentissage indisponible est dit, et Atlas fait quand même la bonne demande ;
     - le signalement en amont est prêt.
2. **Un clic non vérifié est refait : deux clics sur la même cible.**
   - Sévérité : **Moyen**.
   - Ce défaut existait avant le sprint et n'est pas lié à l'apprentissage ; il se produit dans les 3 passes.
   - Mécanisme : sur une cible peu lisible (10 pt, gris sur gris), la vérification après clic échoue (OCR à 53 %). Le moteur relance le grounding et **reclique** (couche cache, 156 ms), puis rend `replan_required`. Le message affiché dit quand même « Clic EasyOCR sur 'magasin' ».
   - Risque : sur un bouton à bascule ou un bouton « envoyer », deux clics ne valent pas un.
   - Mitigation proposée : sur un clic non vérifié, demander à Alexis s'il a bien eu lieu plutôt que de recliquer. C'est hors du périmètre de ce sprint : non corrigé.
3. **Lancement appris et changement d'ordre du premier plan prouvés par tests seulement**, sans rejeu réel.
   - Sévérité : **Moyen**.
   - Mitigation : les ajouter à `rejeu_apprentissage.py` (une fenêtre qui refuse pywinauto ; une application dont le nom se résout lentement).
4. **Reconnaissance des corrections par motifs.**
   - Sévérité : **Moyen**.
   - Des formulations hors des 3 formes et de « pas X, Y » ne sont pas reconnues, par exemple « tu t'es trompé, c'était … ».
   - Un faux positif est limité, parce que la phrase voulue repasse par le validateur et par les confirmations.
   - Mitigation : élargir le corpus de formulations sur les vraies sessions d'Alexis.
5. **« Éviter » ne retire jamais une couche.**
   - Sévérité : **Faible**.
   - Après un échec de la gagnante, les couches lentes restent tentées, en dernier. C'est voulu (l'écran peut changer), mais le temps maximal d'une demande ne baisse pas.
6. **Clé de méthode exacte** (application, cible).
   - Sévérité : **Faible**.
   - « Magasin » et « le magasin » font deux apprentissages. C'est voulu (déterministe).
7. **`remote` git encore sur l'ancienne adresse.**
   - Sévérité : **Faible**.
   - GitHub redirige, mais la commande de mise à jour m'a été refusée.
   - Mitigation : commande en §9.

---

## 8. Checklist de validation

- [ ] ChromaDB : une version à 0 échec sur 100 ouvertures, garde-fou identique, épinglée ; **ou bien l'échec dit, avec le filet gardé** → **seconde branche tenue** : l'échec est dit, le filet est gardé et le signalement est prêt (tableau de tête, §4.4). La première branche n'est pas atteinte : je ne coche pas, et je laisse le superviseur trancher.
- [x] Test de bout en bout AP1 : rouge d'abord, puis couches différentes en passe 2, identiques à la passe 1 quand la mémoire est neutralisée (§5.3, §6.1)
- [x] Les quatre défauts du rapport D corrigés ; stratégies sans effet retirées ; au-delà du clic (§4.2 ; preuves réelles du lancement en §7, risque 3)
- [x] Une couche qui réussit est tentée en premier la fois suivante ; gain mesuré : −1,22 s et −2,43 s au rejeu final, −0,94 s et −2,52 s au premier (§6.1)
- [x] Corrections : reconnues (corpus avec négatifs), appliquées, dites, listables, effaçables avec confirmation (tableau de tête, §5.2)
- [x] Rien d'appris ne contourne le validateur ni une confirmation (`test_ap2_une_correction_vers_une_action_a_confirmer_reste_confirmee`, §4.3)
- [x] Rien d'appris des tests ni des essais : origine obligatoire, `atlas_apprentissage` réel vide (§6.4)
- [x] Corpus de routes ≥ 99,6 % avec mémoire vide (234/235) ; GB1 à 0 (§5.4)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5.1, §5.5)

---

## 9. Recommandations pour le sprint suivant

**À faire par Alexis :**
- mettre à jour le `remote` local :
  ```
  git remote set-url origin https://github.com/ALX-18/Atlas.git
  ```
- s'il le souhaite, publier `docs/chromadb_signalement.md` sur `https://github.com/chroma-core/chroma/issues`, en joignant `scripts/repro_chroma.py`.

**P1 — fiabilité**
- Clic non vérifié : ne pas recliquer, demander ou le dire (risque 2). Avec un test sur `/api/chat` et une fenêtre de test qui compte les clics reçus.
- Rejouer `scripts/repro_chroma.py` à chaque nouvelle version de ChromaDB, et suivre les ouvertures réelles d'Atlas sur plusieurs jours (journal du filet) avant d'envisager de retirer le filet.

**P2 — robustesse**
- Rejeu réel du lancement appris et du changement d'ordre du premier plan (risque 3).
- Sprint Apprentissage 2 (refus et habitudes) : réutiliser les enregistrements explicites, l'origine obligatoire et la liste/l'oubli de ce sprint. La stratégie `confirm` retirée ici y trouve sa place, si un effet observable est défini.
- Élargir le corpus de formulations de correction à partir des sessions réelles d'Alexis (risque 4).

**P3 — qualité**
- Décider du sort des 20 entrées de `atlas_errors`, que plus rien ne lit : elles appartiennent à Alexis, donc on lui demande.
- Dette : `scripts/mesure_routes.py` isole maintenant l'état du monde. Les autres mesures (GB1) pourraient faire de même.

**Hors scope ajouté :** l'isolation de l'état du monde dans `mesure_routes.py` (§4.5). Elle était nécessaire pour que le corpus mesure la même chose quel que soit l'ordre des tests.
