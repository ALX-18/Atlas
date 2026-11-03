# RAPPORT SPRINT — ARTEFACTS SUR MESURE : le document que la personne demande, pas un modèle de document
Date: 03/11/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_ARTEFACTS_SUR_MESURE.md`. Branche **`sprint-artefacts-sur-mesure`**, issue de `main` @ `3e4a3f1`. Commit non poussé.
> Atlas reste sur `qwen2.5:7b`, décision d'Alexis pour la démo. `BRIEF_SPRINT_BASCULE_MODELE.md` n'est pas exécuté.

---

## Tableau de tête

| Mesure | Résultat | Objectif | Statut |
|---|---|---|---|
| Consignes vérifiables respectées (20 demandes) | **46/47 (97,9 %)**, tolérance de longueur ±10 % ; écart restant dit (279 mots pour 275 au plus). 47/47 avec l'ancienne tolérance de ±20 % | ≥ 90 % | PASS |
| Consignes non vérifiables par programme | ton (3), public (3) : **non comptées** | — | Limite (§7) |
| Retouches (10) | **10/10** au passage final ; versions précédentes intactes 10/10 ; « dit sans être fait » 0 | faites, ancienne gardée, changement dit | PASS |
| Chiffres, dates et noms conservés dans les résumés | **52 % → 68,5 %** (passage 2) ; 52 % → 70,6 % (passage 1) | conservés | PASS, gain inégal (§6.2) |
| Faits inventés livrés, nouvelle consigne | **0** sur 9 résumés | 0 | PASS |
| **Alexis, première grille (6 documents)** | **2,2/5** (3, 2, 1, 1, 3, 3) ; « il a suivi ma demande » : **5 oui, 1 non** | 4/5 et oui partout | **FAIL** |
| **Alexis, seconde grille, après correctifs** | **3,0/5** (3, 3, 3, 2, 3, 4) ; **5 oui, 1 non** (A : 240 mots pour 300) | 4/5 et oui partout | **FAIL** |
| Corpus de routes | 437/438 (99,8 %), 0 action à tort | ≥ 99,8 %, 0 | PASS |
| GB1 | 0 affirmation sans outil, 0 question remplacée | 0 | PASS |

**À retenir : le contrôle automatique donne 98 à 100 %, le jugement d'Alexis 2,2 puis 3,0/5.** Le programme vérifie la forme (longueur, parties, tableau, sommaire). Il ne vérifie ni la justesse des faits, ni la qualité du texte.

---

## 1. Résumé exécutif

- **Statut : PARTIELLEMENT VALIDÉ.** Tous les critères mesurables par programme passent. Le jugement d'Alexis progresse (2,2 puis 3,0/5) mais reste sous l'objectif de 4/5, avec un « non » à chaque grille.
- **Runtime :** Atlas réel rejoué sur des copies (§6.1), `qwen2.5:7b`, Ollama actif.
- **Tests :** `python -m pytest tests/ -q` : **1 471 passés, 0 ignoré (7 min 39)** avec Ollama ; **1 468 passés, 3 ignorés justifiés** sans Ollama. Code 0 dans les deux cas, au second passage sans Ollama (le premier : 1 échec instable, §5).
- **Première grille :** elle a révélé des fautes de code (sommaire réintroduit par une retouche, partie mal placée, régénération qui dégradait un document), corrigées et testées, et des erreurs de fond du modèle (dates et faits faux), **non corrigées**.
- **Risque principal pour la démo :** une fiche d'histoire reste fausse par endroits. `qwen3:8b`, essayé à titre d'indication, en produit aussi (§6.4).
- **Trouvé au contrôle C3 :** un Atlas d'essai a réécrit le vrai `data/triggers.json`, hors de la garde BM0. Trace retirée, faille fermée (§6.5).
- **Incidents :** le PC a planté le 02/11 pendant un banc, cause non établie ; le 03/11, le banc s'est figé 14 min juste avant une retouche, probablement sur l'ouverture d'un fichier. L'ouverture ne bloque plus le travail (§6.6).

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| AS0 — Base : Banc de modèles fusionné, suite verte | `main` @ `3e4a3f1` | PASS |
| AS1.1 — Consignes extraites | `core/specification.py`, extraction déterministe, sans modèle | PASS |
| AS1.2 — Document générique, structure venue de la demande | lettre, fiche, plan de cours, note, document ; parties imposées tenues par le moteur | PASS |
| AS1.3 — Vérification, une régénération, écart dit | fait, lettres comprises ; ne remplace que si la régénération fait mieux ; un nombre de mots tient à ±10 % | PASS |
| AS1.4 — Tableaux Word et PDF | relus sur fichier en rejeu (R4) | PASS |
| AS2 — Retouches, nouvelle version, changement dit | 8 opérations ; v2, v3 ; Word externe (R8) | PASS |
| AS2 — Perte de mise en forme mesurée | gras, couleurs, polices, alignements, images, en-têtes, comptés et dits | PASS |
| AS3 — Résumés : garder, ne rien ajouter | conservation en hausse, 0 inventé ; pas de gain net sur les notes de réunion | PARTIEL |
| AS4 — « tu peux faire quoi ? » court | 573 caractères au rejeu, familles puis détail sur demande | PASS |
| AS4 — La fenêtre web relève les annonces | vu en direct dans le navigateur (R9) | PASS |
| AS4 — Faits retenus utilisés et cités | R7 | PASS |
| AS5 — ≥ 90 % de consignes | 46/47 (97,9 %) | PASS |
| AS5 — 10 retouches | 10/10 | PASS |
| AS5 — Jugement d'Alexis 4/5 et oui partout | 2,2/5 puis 3,0/5, un « non » à chaque grille | **FAIL** |
| AS5 — Routes et GB1 | 99,8 %, 0 action à tort, GB1 à 0 | PASS |
| AS6 — Erreurs distinguées | génération 0, validation 4, exécution 0 (§5) | PASS |
| AS6 — Suites vertes avec et sans Ollama | §5 | PASS |
| AS6 — C3 et garde BM0 | une fuite trouvée, retirée, fermée (§6.5) | PASS après correction |
| AS6 — Documents de test supprimés, sauf les 6 | supprimés ; 3 PDF verrouillés le 02/11, supprimés le 03/11 | PASS |

---

## 3. Architecture projet mise à jour

```
api/routes.py                          /api/annonces?depuis=N
core/annonces.py                       historique numéroté, depuis(n)
core/artefacts.py                      document générique, lettres, retouches, résumés
core/intent_classifier.py              règles de genres et de retouches
core/intent_engine.py                  artefact_retoucher, réponse courte, capabilities_detail
core/ollama_client.py                  prompt du modèle : capabilities_detail
core/scheduler.py                      garde BM0 (hors brief, §4)
core/specification.py                  ← NOUVEAU
core/trigger_engine.py                 garde BM0 (hors brief, §4)
core/validator.py                      artefact/retoucher
core/workflow_engine.py                garde BM0 (hors brief, §4)
desktop/atlas_desktop.py               annonces par numéro
tools/documents.py                     tableaux, lettres, lecture Word, versions, seuil du sommaire
ui/app.js                              relève des annonces
scripts/banc_sur_mesure.py             ← NOUVEAU
scripts/rejeu_sur_mesure.py            ← NOUVEAU
tests/test_artefacts_sur_mesure.py     ← NOUVEAU (56 tests)
tests/fixtures/corpus_routes.json      +20 demandes
tests/test_artefacts.py, test_banc_modeles.py, test_competences_1.py, test_gter.py   adaptés
```

---

## 4. Détail des implémentations

**`core/specification.py` (nouveau).** `extraire(phrase)` donne le genre, les formats, la longueur (mots à ±10 %, ou pages à 420 mots par page), la langue, le ton, le public, les parties, tableau, sommaire, conclusion, introduction, puces, titre. `verifier(contenu, spec, rendu)` rend les écarts en phrases. `appliquer()` tient ce que le moteur peut tenir seul : titre imposé, puces fondues, partie interdite retirée.

**`core/artefacts.py`.**
- `rediger_document` et `rediger_lettre` : vérification, une régénération (demande × cible / obtenu), écarts rendus pour être dits.
- `_plus_proche` : une régénération ne remplace que si elle réduit les écarts ou se rapproche de la longueur. Avant, 380 mots pour 300, régénérés en 155, étaient remplacés.
- `CONSIGNES_DE_GENRE` et `_budget` : une fiche ou un plan de cours sans longueur demandée reste court ; le plan de cours est écrit pour l'enseignant (objectif, durée, matériel, déroulé).
- `_destinataire` et bloc « [nom et adresse à compléter] » : le destinataire n'est jamais inventé.
- Retouches : `_cible_retouche` relit un document nommé et en déduit ses consignes (sommaire, puces, langue) ; `_appliquer_retouche` place les causes, origines ou le contexte en tête ; « corriger » sans faute trouvée n'écrit pas de nouvelle version.
- « Raccourcir » : consigne recalibrée à 70 % de la partie, parce que le modèle rend moins que demandé.
- AS3 : `CONSIGNE_FAITS_RESUME` (garder tels quels, n'en ajouter aucun), `faits_conserves`.
- Seconde grille : la lettre formelle a toujours sa formule de politesse (ajoutée par le moteur si le modèle l'oublie) ; le destinataire inconnu devient « [nom et adresse de mon voisin à compléter] ».
- « Corriger » refuse une correction qui change la longueur de plus de 10 % (« Je n'ai gardé aucune correction… »), et « corriger » ou « ton » gardent les points de liste que le modèle omet.
- `_ouvrir` : l'ouverture des fichiers produits se fait dans un fil d'exécution ; au-delà de 5 s, le travail continue sans elle.

**`tools/documents.py`.** Tableaux Word et PDF, mise en page de lettre, `lire_docx` (contenu et mise en forme), `perte_de_mise_en_forme`, `chemin_version`. Sommaire automatique seulement à partir de 3 parties **et** 800 mots.

**Fenêtres.** `/api/annonces?depuis=N` ne vide plus la file : les deux fenêtres lisent les mêmes annonces.

**Ajouts hors brief :**
- garde BM0 sur `triggers.json`, `schedules.json` et les workflows, à cause de la fuite du §6.5 ;
- avertissement `_avertissement_faits` : un document rédigé de mémoire qui contient des chiffres ou des dates fait dire à Atlas de les vérifier, à cause de la première grille ;
- lecture du destinataire dans la phrase.

Justification au §9. Le superviseur peut les refuser.

---

## 5. Résultats des tests

```
python -m pytest tests/ -q
```

| Exécution | Résultat | Code |
|---|---|---|
| Ollama actif | **1 471 passés, 0 ignoré (7 min 39)** | 0 |
| Ollama arrêté, 1er passage | 1 échec, 1 467 passés, 3 ignorés justifiés | 1 |
| Ollama arrêté, 2e passage | **1 468 passés, 3 ignorés justifiés** (7 min 43) | 0 |

**Échec du 1er passage sans Ollama :** `test_apprentissage_2.py::test_aq2_backup_verify_restore_incluent_apprentissage_et_habits`, `PermissionError` [WinError 32] dans le dossier temporaire de pytest, pendant la restauration : un fichier tenu par un autre processus. Ni ce test ni `backup_memory.py` ne sont touchés par le sprint ; relancé seul, il passe 3 fois sur 3, puis dans le 2e passage complet. Classé instable, non corrigé (§7).

Ignorés sans Ollama : `test_gb1_vrai_modele_aucune_affirmation_transmise`, `test_grounding_layer_order_steam_includes_heuristic`, `test_layer_timeout_aborts_slow_layer`.

**Preuve rouge :** sur `main`, les 34 premiers tests du sprint échouaient (13 échecs, 21 erreurs, dans une copie de travail séparée). Les tests issus de la grille ont d'abord échoué sur la branche : 10 échecs sur 11 avant correctifs. Le 11e, sur le placement « avant la conclusion », décrit un comportement déjà en place. Les 2 derniers tests (`test_jugement_une_regeneration_plus_loin…`, `test_jugement_rien_a_corriger…`) ont été écrits avec leur correctif, sans preuve rouge séparée. Les tests de la seconde grille et des incidents ont tous échoué avant leur correctif : tolérance et politesse (4 échecs), correction qui réécrit (1, avec l'ancienne tolérance remise), points de liste (2).

**Non-régression, suite par suite (nombre de tests, tous passés avec Ollama) :**
test_action_safety_b1 (20), test_action_safety_b1_bis (146), test_app_resolver_v51 (5), test_apprentissage (39), test_apprentissage_2 (48), test_artefacts (48), test_artefacts_sur_mesure (56), test_automation_safety_b1_ter (83), test_automation_v30 (15), test_banc_modeles (19), test_beta_safety_g (32), test_checkup (45), test_chroma_integration (5), test_competences_1 (114), test_confirmation_f (22), test_core_conversational (15), test_depot_ollama (30), test_doctor_verdict_g (15), test_fiabilite (52), test_file_indexer_v51 (2), test_file_organizer_v51 (3), test_final_v50 (10), test_gter (43), test_honesty_gbis (102), test_identity_v60 (8), test_index_fichiers (37), test_interaction_v22 (10), test_isolation (5), test_kill_exact_gbis (13), test_labels_gbis (2), test_memory_cleanup_guard_e (5), test_memory_cleanup_ids_gbis (5), test_memory_quality_d (11), test_memory_v60 (26), test_metrics_grounding_v52 (7), test_orchestrator_v60 (14), test_performance (18), test_pre_beta (30), test_real_e2e_kimi_v51 (2), test_redo_gbis (31), test_redo_heuristics_v52 (22), test_sans_docker (24), test_send_message_gbis (24), test_session_alexis_gbis (16), test_sprint_kimi_understanding_v51 (14), test_stabilisation_v31 (5), test_v53_migration (17), test_v601_patches (25), test_vision_parsers (45), test_vision_v60 (24), test_voice_chain_e (12), test_voice_followup_f (10), test_voice_v40 (12), test_voice_v602 (17), test_web_v20 (9), test_whisper_offline_gbis (2).

**Tests anciens modifiés, à vérifier par le superviseur :**
- `test_artefacts.py` : `sommaire=True` passé explicitement à `test_ar2_…`, parce que le sommaire n'est plus automatique sur un texte court ; « document Word sur les volcans » est maintenant de type document.
- `test_competences_1.py` et `test_gter.py` : format court de « tu peux faire quoi ? » (limite redevenue courte, demandée par le brief).
- Corpus de routes : « note de synthèse » devient une action, parce qu'une note doit sortir d'une demande claire (brief AS1.2).

**Corpus de routes :** `python scripts/mesure_routes.py` : 437/438 (99,8 %), 0 action à tort. L'échec restant : « c'est quoi mon horoscope du jour ? » part vers un rappel de mémoire.

**GB1 :** `python tests/gb1_mesure.py SORTIE.json` : 34 demandes d'action, 0 affirmation sans outil, 0 question remplacée, 0 annonce différente de l'état relu.

**Erreurs distinguées (banc final du 03/11, 20 demandes et 10 retouches) :**

| Sorte | Nombre | Détail |
|---|---|---|
| Génération (le modèle ne rend rien d'exploitable) | 0 | — |
| Validation (rendu refusé par le moteur, puis réessayé) | 4 | 2 « paragraphes absents ou de longueur anormale », 2 « le texte doit être rédigé en français » |
| Exécution (fichier non produit) | 0 | — |

Aucune de ces erreurs n'a empêché un document de sortir.

---

## 6. Comportement observé en scénarios utilisateur réels

### 6.1 Rejeu par Atlas réel

`python scripts/rejeu_sur_mesure.py --out <dossier> --garder 1200`. Atlas réel sur des copies : mémoire vide, apprentissage, journal, habitudes, rappels jetables, index copié. Noms et adresses fictifs. Les fichiers sont relus par le script, pas par Atlas.

| ID | Commande utilisateur | Résultat attendu | Résultat observé | Statut |
|---|---|---|---|---|
| R1 | raccourcis (aucun document récent) | pas une action | conversation, aucun fichier créé | PASS |
| R2 | tu peux faire quoi ? | familles, puis détail sur demande | liste courte des familles, 2 s | PASS |
| R3 | que sais-tu faire avec les documents ? | détail de la famille | réponse fixe, 0,14 s | PASS |
| R4 | fais une fiche de révision sur le cycle de l'eau avec un tableau, sans sommaire, en Word et en PDF | tableau, pas de sommaire, 2 formats | relu : 1 tableau Word, pas de sommaire, PDF de 2 pages, 26,7 s | PASS |
| R5 | raccourcis-le | v2, ancienne gardée, changement dit | 676 → 332 mots, 4 parties gardées, 12,4 s | PASS |
| R6 | change le titre en Le voyage de l'eau | v3, ancienne gardée | v3 Word et PDF, 1,2 s | PASS |
| R7 | retiens mon nom et mon adresse (fictifs), puis une lettre formelle pour mon propriétaire | pas redemandés, source citée | relu : nom et adresse présents ; « J'ai repris ce que tu m'avais dit… », 6,5 s | PASS |
| R8 | rajoute une partie sur les limites au rapport de stage AtlasEssai (Word externe mis en forme) | v2 à côté, original intact, perte dite | titres relus + « Les limites » ; original intact ; perte dite : gras et italique (3), couleurs (3), police, alignement (1) | PASS |
| R9 | écris un texte de 100 mots sur la pluie, tapé dans la fenêtre web | l'annonce arrive seule | vue en direct, 6 s, sans toucher à la page | PASS |

Premier passage du rejeu : R8 avait échoué, parce que l'index passif ne voit pas un fichier posé avant le démarrage. Le script pose maintenant le fichier après. Un second défaut est visible et corrigé : « quand il est prêt » pour une fiche ou une lettre.

### 6.2 Conservation des faits dans les résumés (3 sources × 3 essais × 2 consignes)

| Source | Passage 1 : avant → après | Passage 2 : avant → après |
|---|---|---|
| Rapport de stage (17 clés) | 33 % → 67 % | 37 % → 61 % |
| Notes de réunion (23 clés) | 40 % → 56 % | 55 % → **46 %** |
| Document long (53 clés) | 63 % → 78 % | 55 % → 80 % |
| **Moyenne du banc** | **52 % → 70,6 %** | **52 % → 68,5 %** |

- **Gain net sur le stage et le document long.** Sur les notes de réunion, le résultat varie d'un essai à l'autre (43 à 74 %) : aucun gain établi.
- **Phrases retirées par le contrôle anti-invention (passage 2) :** 5 avec l'ancienne consigne, 0 avec la nouvelle.
- **Faits inventés livrés :** 0 avec la nouvelle consigne. Avec l'ancienne, 4 signalés dans un seul résumé : des mots de titres avec majuscule (« Encadrement », « Missions »…), donc pas des faits.
- **Erreur de mesure corrigée :** le passage 1 annonçait 41 « inventés », parce que le banc recollait les textes et prenait un titre de partie pour un nom propre. Le chiffre est écarté et la mesure se fait désormais texte par texte. Le taux de conservation du passage 1 reste valable.

### 6.3 Jugement à l'aveugle d'Alexis — première grille

| Doc. | Demande | Note | A suivi ? | Commentaire résumé |
|---|---|---|---|---|
| A | 300 mots sur la lecture, sans puces | 3/5 | oui | contrat tenu ; générique, répétitif, un mot inventé ; sommaire inutile |
| B | plan de cours sur les fractions, 3 parties | 2/5 | oui | pas un vrai plan de cours ; exemple d'addition faux ; fautes ; inutilisable en classe |
| C | retouche de D : partie sur les causes | 1/5 | **non** | placée à la fin ; a remis le sommaire interdit par D |
| D | fiche Seconde Guerre mondiale, tableau, sans sommaire | 1/5 | oui | forme tenue ; **dates et faits faux**, « dangereux pour réviser » ; trop longue |
| E | retouche de A : plus simple | 3/5 | oui | simplification timide ; une faute introduite ; sommaire inutile |
| F | lettre formelle au voisin, demi-page | 3/5 | oui | ton correct ; demande noyée ; pas de bloc destinataire |

**Moyenne : 13/6 = 2,2/5. Objectif non atteint.**

| Ce que dit la grille | Origine | Suite |
|---|---|---|
| C remet le sommaire ; document nommé relu sans ses consignes | **Mon code** | corrigé, testé |
| Partie « causes » à la fin | **Mon code** | corrigé, testé (par mots-clés) |
| Sommaire sur 300 mots | **Mon code** | corrigé, testé |
| Fiche de 4 pages ; plan de cours sans objectifs ni durée | **Mon code** (genre passé comme simple mot) | consignes de genre ; à rejuger |
| Lettre vague, sans destinataire | **Mon code** | consigne et bloc « à compléter » ; à rejuger |
| Dates fausses, « Atomium », calculs faux | **Modèle** | **non corrigé** ; avertissement ajouté |
| Mots inventés, fautes, répétitions | **Modèle** | **non corrigé** |

Pendant les correctifs, un document de 300 mots est sorti avec 166 mots, écart dit. La cause était ma règle de régénération, corrigée par `_plus_proche`.

### 6.3 bis Seconde grille (jeu produit le 02/11 sur le code corrigé)

| Doc. | Note | A suivi ? | Commentaire résumé |
|---|---|---|---|
| A | 3/5 | **non** | plus de sommaire, plus propre ; **240 mots pour 300** ; pas de conclusion |
| B | 3/5 | oui | vrai format de plan de cours (objectif, durée, matériel, déroulé) ; **plus aucun contenu mathématique** ; matériel discutable ; durées déséquilibrées |
| C | 3/5 | oui | causes placées en tête, sommaire non remis ; contenu faible (ni Versailles ni 1929) ; erreurs de D toujours là |
| D | 2/5 | oui | vrai tableau, 2 pages ; erreurs encore gênantes (Norvège « et Suède », dates de début de guerre), Pacifique absent, chronologie en désordre, anglicismes |
| E | 3/5 | oui | introduction simplifiée, le reste peu ; une faute ajoutée ; ≈ 200 mots |
| F | 4/5 | oui | demande claire, destinataire à compléter, demi-page ; **formule de politesse finale absente** |

**Moyenne : 18/6 = 3,0/5** (2,2 à la première grille). Objectif de 4/5 non atteint, un « non ».

| Ce que dit la seconde grille | Origine | Suite |
|---|---|---|
| A : 240 mots pour 300, accepté | **Mon code** : tolérance ±20 % | resserrée à ±10 %, testé ; le banc donne alors 46/47 |
| F : pas de formule de politesse | **Mon code** : rien ne la garantissait | ajoutée par le moteur si absente, testé |
| F : « Mon voisin » au-dessus de l'adresse | **Mon code** | une seule ligne « [nom et adresse de mon voisin à compléter] », testé |
| F : expéditeur « Camille Martin » non signalé | **Le banc** : signature fictive fournie par le script, Atlas demande le nom en usage | rien à corriger dans Atlas |
| B : plan sans contenu mathématique | **Modèle**, poussé par ma consigne « vérifie chaque calcul » | **non corrigé**, non rejugé |
| D, C : erreurs historiques | **Modèle** | **non corrigé** |
| E : simplification timide, texte raccourci | **Modèle** | **non corrigé** |

Les trois correctifs de la seconde grille ne sont pas rejugés par Alexis.

### 6.4 Indication : `qwen3:8b` sur la fiche et le plan de cours

Essai unique, non aveugle, jugé par moi et non par Alexis. **Ce n'est pas une mesure**, et Atlas ne change pas de modèle.

- **Fiche :** erreurs aussi (l'Allemagne installée « dans le Maghreb », l'OTAN créée avec l'ONU à la fin de la guerre, l'URSS « envahie » en 1940).
- **Plan de cours :** durées plausibles et cohérentes, mais contenu pauvre.

Changer de modèle ne suffit donc pas à garantir des faits justes sans source.

### 6.5 Règle C3 et garde BM0

**Fuite trouvée au contrôle de fin :** `data/triggers.json` avait été réécrit le 24/10 à 21:02, pendant mon rejeu. Le déclencheur « GPU over 90 » s'est déclenché dans un Atlas d'essai, qui a mis à jour le vrai fichier. Le nom de ce fichier n'était pas couvert par la garde BM0.

Le compteur était à 9 (dernier déclenchement le 27/06) le 19/09. Le fichier n'a ensuite été réécrit que le 17/10 à 13:08 (rejeu Artefacts, même minute que ses documents) et le 24/10 à 21:02. Les deux passages à 10 et 11 sont donc des traces de mes essais.

| Donnée | Avant mes essais | Après mes essais | Après le retrait |
|---|---|---|---|
| `triggers.json`, compteur | 9 | 11 | **9** |
| `triggers.json`, dernier déclenchement | 27/06/2026 15:56:54 | 24/10/2026 21:02:41 | **27/06/2026 15:56:54** |
| Journal des actions | 757 lignes | 757 | 757 |
| `schedules.json` | 16/09 | inchangé | inchangé |
| Mémoire | — | aucune écriture | aucune écriture |

- **Copie avant retrait :** `Atlas_backups\triggers\triggers_20261102_avant_retrait.json`. Pas de sauvegarde de mémoire, puisque la mémoire n'est pas touchée.
- **Correction :** `verifier_ecriture` ajouté à `triggers.json`, `schedules.json` et aux workflows. Vérifié en réel : le fichier n'a plus bougé après le rejeu du 02/11.
- **Notification :** l'Atlas d'essai a pu afficher une vraie notification « GPU high ». Voir §7.

**Documents de test :**
- bancs : dans le dossier temporaire, hors de `Documents\Atlas` ;
- rejeux : Word et dossier `AtlasEssaiSurMesure` supprimés ;
- 3 PDF « Cycle de l'eau Fiche de révision », verrouillés le 02/11 par la visionneuse qu'Atlas avait ouverte, supprimés le 03/11 ;
- restent les 6 documents d'Alexis, dans `Jugement_sur_mesure` ;
- la grille renvoyait à des numéros internes (« document 2 ») : corrigé, elle renvoie à la lettre.


### 6.6 Incidents : crash du PC et banc figé

- **02/11, 11:52 : arrêt brutal du PC** (Kernel-Power 41, sans écran bleu enregistré), pendant le banc, carte graphique chargée par le modèle. Le banc n'avait rien écrit depuis 11:28 : le PC était peut-être déjà figé. Aucune erreur système avant. **Cause non établie.** Après redémarrage : code intact, données d'Alexis intactes (journal 757 lignes, `triggers.json` et `habits.db` inchangés).
- **03/11 : température relevée pendant les bancs suivants.** 68,5 °C au plus, à 145 W (limite de la carte) ; pas de nouvel arrêt.
- **03/11, 12:20 : banc figé 14 min** juste avant la retouche « titre », au même endroit que le silence d'avant le crash, carte au repos. Relancé, il est passé. **Cause probable, non prouvée :** l'ouverture automatique du fichier (`os.startfile`), qui attend l'application quand Word est occupé. Correctif : l'ouverture ne bloque plus (5 s au plus), testé ; le banc n'ouvre plus de fenêtres. Le banc final est passé sans blocage.

---

## 7. Limites et risques identifiés

1. **Le jugement humain reste sous l'objectif** : 3,0/5 à la seconde grille, un « non ». Les derniers correctifs (tolérance, politesse, destinataire, correction, points) ne sont pas rejugés.
   - Sévérité : **Élevé** au regard du brief.
   - Mitigation : une troisième grille, ou une décision du superviseur sur la barre de 4/5 avec `qwen2.5:7b`.
2. **Faits faux dans un document rédigé de mémoire.**
   - Sévérité : **Élevé** pour la démo et les testeurs. Dates, noms et calculs faux, présentés avec assurance.
   - Mitigation : avertissement dans l'annonce et pied de page « à relire ». Éviter les fiches d'histoire ou de maths dans la démo. Ni le contrôle anti-invention (résumés seulement) ni `qwen3:8b` ne règlent ce point.
3. **Le 100 % de consignes ne mesure que la forme.**
   - Sévérité : **Moyen**. Il ne dit rien de la qualité : 2,2/5 pour les mêmes critères à 100 %.
   - Mitigation : garder le jugement humain comme critère ; présenter les deux chiffres ensemble.
4. **Ton et public ne sont pas vérifiés** (6 consignes sur 53).
   - Sévérité : **Moyen**. Ils sont transmis au modèle, sans contrôle.
5. **Correctifs de genre jugés une fois, contenu toujours faible.** À la seconde grille, le plan de cours a le bon format mais plus aucun contenu mathématique ; la fiche est plus courte mais encore fausse par endroits.
   - Sévérité : **Moyen**. Mitigation : exemples imposés dans la consigne de plan de cours, à mesurer.
6. **Fautes et répétitions du modèle** (mots inventés, accords, termes anglais comme « Surrender »).
   - Sévérité : **Moyen**. Aucune relecture orthographique automatique.
7. **Résumés de notes de réunion :** pas de gain établi, 46 à 56 % conservés.
   - Sévérité : **Moyen**. Des faits de la source peuvent manquer.
8. **Un Atlas d'essai exécute encore les vrais déclencheurs et tâches planifiées** ; il ne peut plus les réécrire, mais leurs actions partent (notification « GPU high »).
   - Sévérité : **Moyen**. Mitigation proposée : les désactiver dans un Atlas d'essai.
9. **Garde BM0 incomplète :** `file_reorg_history.jsonl` et `audit_log.jsonl` n'y passent pas. Ces fichiers n'ont pas bougé pendant ce sprint.
   - Sévérité : **Moyen**. Mitigation : les ajouter, et lister tout écrivain de `data/` dans un test.
10. **Les titres de parties d'un résumé ne sont pas filtrés** par `retirer_faits_inventes` : un nom inventé dans un titre passerait.
   - Sévérité : **Moyen**. Aucun cas de fait inventé observé.
11. **Variabilité du modèle :** pour une même demande de longueur, une partie va de 54 à 182 mots. « Raccourcir » coupe de 47 à 62 %. Avec la tolérance à ±10 %, plus d'écarts de longueur sont dits (1 sur 20 au banc final).
    - Sévérité : **Faible**. L'écart restant est dit ; une seule régénération par document.
12. **« Corriger » est peu fiable :** une fois il n'a rien trouvé, une fois il a « corrigé » en perdant les points de liste (corrigé depuis). Aucune mesure sur des fautes injectées.
    - Sévérité : **Moyen**.
13. **Index passif :** un Word déposé pendant qu'Atlas tourne a été trouvé après 643 s ; un fichier déposé avant le démarrage n'a pas été trouvé en 30 minutes. La retouche d'un document nommé tout récent peut répondre « je ne trouve pas ».
    - Sévérité : **Moyen**. Limite déjà connue de l'index, pas de ce sprint.
14. **Durée annoncée trop longue pour un texte court :** « environ 49 secondes » pour 6 s réelles.
    - Sévérité : **Faible**. Mitigation : estimer selon la longueur demandée.
15. **Une nouvelle fenêtre web réaffiche les annonces de la session** (jusqu'à 100).
    - Sévérité : **Faible**.
16. **Les documents ouverts par Atlas verrouillent leurs fichiers,** et une visionneuse PDF restée ouverte a empêché le nettoyage.
    - Sévérité : **Faible**. Le rejeu le dit dans `documents_de_test_restants`.
17. **Retouche sur un document nommé :** seules les consignes visibles dans le fichier sont retrouvées (sommaire, puces, langue). Ton et longueur d'origine sont perdus. Le placement par mots-clés ne couvre que quelques cas.
    - Sévérité : **Faible**.
18. **Le dernier document n'est retenu qu'en mémoire vive** (2 h) : après un redémarrage, il faut le nommer.
    - Sévérité : **Faible**.
19. **Crash du PC du 02/11 non expliqué** (§6.6). Une charge GPU prolongée en est contemporaine, sans preuve de lien.
    - Sévérité : **Moyen** (machine de démo).
    - Mitigation : surveiller la température et le journal système lors des prochains longs bancs.
20. **Test de sauvegarde instable sous Windows** (`test_aq2_backup_verify_restore…`) : un verrou de fichier temporaire l'a fait échouer une fois sur trois passages complets.
    - Sévérité : **Faible**. Mitigation : réessayer la suppression du dossier temporaire dans le test.
21. **Une ouverture de fichier bloquée laisse un fil d'exécution en attente** : le travail continue, mais la fenêtre peut s'ouvrir tard ou pas du tout.
    - Sévérité : **Faible**.

---

## 8. Checklist de validation

- [x] Consignes extraites en spécification validée ; structure venue de la demande, pas d'un gabarit (§4, R4, 47/47)
- [x] Document vérifié contre la spécification ; écart régénéré une fois puis dit (§4, tests `test_lettre_*`, `test_jugement_*`)
- [x] Tableaux produits en Word et en PDF (R4, relu)
- [x] Retouches sur le dernier document ou un document nommé, nouvelle version, changement dit ; document Word externe retouché, avec la limite de mise en forme mesurée (R5, R6, R8, 10/10)
- [x] Résumés : chiffres de la source conservés, aucun inventé (§6.2 : 52 % → 68,5 %, 0 livré ; gain non établi sur les notes de réunion)
- [x] « tu peux faire quoi ? » court à l'écrit ; annonces dans la fenêtre web ; faits retenus utilisés et cités (R2, R3, R7, R9)
- [ ] ≥ 90 % de consignes respectées ; Alexis : 4/5 et « il a suivi ma demande » partout — **consignes : oui (97,9 %). Alexis : non (2,2/5 puis 3,0/5, un « non » à chaque grille)**
- [x] Corpus ≥ 99,8 %, 0 action à tort ; GB1 à 0 (§5)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5)

---

## 9. Recommandations pour le sprint suivant

**P1 — fiabilité**
- Décider de la barre de 4/5 avec `qwen2.5:7b` (deux grilles : 2,2 puis 3,0), et s'il faut une troisième grille sur les derniers correctifs.
- Décider du périmètre de la démo : montrer ce qui ne dépend pas de faits de mémoire (lettre, résumé d'un fichier, retouches) et éviter fiches d'histoire et de maths.
- Lors de la bascule de modèle, mesurer la justesse des faits, sur un corpus de réponses connues. La Réunion n° 1 demandait déjà 4/5 sur les résumés de `qwen3:8b`. Le banc ne mesure pas les faits.
- Compléter la garde BM0 (risque 8) et couper déclencheurs et tâches dans un Atlas d'essai (risque 7).

**P2 — robustesse**
- Vérifier ton et public par un moyen déterministe, ou dire qu'ils ne sont pas vérifiés.
- Filtrer les titres de parties dans `retirer_faits_inventes`.
- Mesurer « corriger » sur des fautes injectées, et envisager un correcteur orthographique local.
- Reprendre les résumés de notes de réunion, source par source.

**P3 — qualité**
- Durée annoncée selon la longueur demandée.
- Ne pas réafficher les annonces anciennes à l'ouverture de la fenêtre.
- Retrouver l'intégralité des consignes d'un document Atlas (par exemple dans ses propriétés Word).

**Ajouts hors brief, à valider :**
- la garde sur `triggers.json`, `schedules.json` et les workflows : une vraie donnée a été modifiée, et la règle C3 l'exige ;
- l'avertissement sur les faits : réponse minimale à « dangereux pour réviser », sans changer de modèle ;
- la lecture du destinataire : demandée par le commentaire sur F.
