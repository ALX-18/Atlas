# Inventaire R1 — ce qui est personnel dans le dépôt (arbre et historique)

Sprint Dépôt + Ollama, 12/10/2026. **Rien n'a été supprimé.** Ce document sert de base de décision : Alexis tranche chaque ligne avant R2.

Ce document ne cite que des fichiers et des **codes de motifs**. La liste exacte des motifs (les chaînes à remplacer) est gardée **hors du dépôt**, à côté de la sauvegarde miroir, pour ne pas les republier ici.

## Méthode

- **Arbre** : `git grep` sur les 214 fichiers suivis.
- **Historique** : `git grep` sur chacun des **92 commits** de toutes les branches (`git rev-list --all`), et liste des **221 chemins** ayant jamais été suivis (`git log --all --diff-filter=A`).
- **Secrets** : motifs de jetons GitHub, OpenAI, Slack, AWS et Google, `client_secret`, `refresh_token`, `access_token`, clés privées `BEGIN … PRIVATE`, `api_key = "…"` et `password = "…"`, plus les noms de fichiers `oauth`, `token`, `.env`, `secret` et `credential`.

## Codes des motifs

| Code | Nature |
|---|---|
| M1 | nom du persona du fork Mac (une proche réelle) |
| M2 | prénom réel de cette proche |
| M3 | nom de famille d'Alexis |
| M4 | chemin du profil Windows (`C:\Users\<nom>…`) |
| M5 | nom du PC |
| M6 | adresse e-mail d'école, dans l'**auteur** de 82 commits (pas dans les fichiers) |

## Inventaire et propositions

| # | Élément | Où | Contenu (sans le citer) | Proposition |
|---|---|---|---|---|
| 1 | `docs/rapports/INVENTAIRE_MEMOIRE_D.md` | arbre + historique | extraits de la **mémoire réelle** (≈ 120 identifiants avec leur texte), M3, M5 | **retirer** de l'arbre et de l'historique ; `.gitignore` sur `docs/rapports/INVENTAIRE_MEMOIRE_*.md` (c'est la sortie par défaut de `scripts/memory_inventory.py`) |
| 2 | `cleanup_ids.json` (racine) | arbre + historique | fichier de travail du nettoyage mémoire : identifiants et raisons | **retirer** de l'arbre et de l'historique ; `.gitignore` sur `cleanup_ids*.json` |
| 3 | `assistant-bureau/data/` (4 fichiers : journal d'actions, index de fichiers, historique de rangement, `habits.db`) | arbre + historique | **artefacts de tests**, écrits le 19/09 par la suite lancée sur le Mac (chemins `pytest-of-<utilisateur Mac>`) ; `habits.db` vide | **retirer** de l'arbre (c'est tout ce qui reste d'`assistant-bureau/`) ; historique : retirer aussi (sans enjeu, mais rien à garder) |
| 4 | Persona M1/M2 : `core_conversational/README.md`, `docs/core_conversational_runbook.md`, `requirements-mac-compagnon.txt`, docstrings de `core_conversational/{__init__,identity,intent_minimal,llm_client}.py`, `tests/test_core_conversational.py` (un test), `docs/rapports/RAPPORT_V602.md`, `docs/rapports/RAPPORT_SPRINT_C.md`, ce brief | arbre + historique | le nom du persona, le prénom de la proche, l'exemple de persona et l'ingestion de « ses souvenirs » | **anonymiser** : « fork Mac » et un persona d'exemple neutre ; renommer `requirements-mac-compagnon.txt` → `requirements-mac.txt` ; historique : remplacement de texte (`filter-repo --replace-text`) et renommage de chemin |
| 5 | M3 dans la **consigne réelle du modèle** (`core_conversational/identity.py`, `ATLAS_BASE_IDENTITY`) et dans `tests/test_identity_v60.py`, `tests/test_core_conversational.py` | arbre + historique | le nom complet du créateur | **décision d'Alexis** : (a) garder le prénom seul (« Créateur : Alexis ») — la consigne change d'un mot ; (b) garder tel quel |
| 6 | M4 : 12 documents (`docs/PROTOCOLE_VALIDATION_VOCALE_E.md`, `docs/v51_brief.md`, briefs M-bis et Dépôt, rapports A, B-minimal, B1-ter, C, D, M, M-bis, `DIAGNOSTIC_V22`) et 3 tests (`test_app_resolver_v51`, `test_automation_safety_b1_ter`, `test_backup_memory_guard`) | arbre + historique | chemins d'installation, de sauvegarde, de téléchargement | **anonymiser** en `C:\Users\<utilisateur>` (arbre et historique). Les tests ne dépendent pas du nom (vérifié à R2 par la suite) |
| 7 | M5 | historique seulement, dans l'élément 1 | nom du PC | réglé par le retrait de l'élément 1 |
| 8 | Citation d'une vraie conversation et d'une vraie recherche dans `docs/rapports/RAPPORT_SPRINT_M.md` (§ sauvegarde, 2 lignes) | arbre + historique | une phrase réelle d'Alexis à Atlas | **anonymiser** les deux citations (garder les identifiants et la preuve « lu après restauration ») |
| 9 | M6, adresse d'école dans l'auteur des commits | métadonnées de 82 commits | adresse e-mail | **décision d'Alexis** : réécrire l'auteur vers l'adresse `…@users.noreply.github.com` déjà utilisée par 10 commits (`filter-repo --mailmap`), ou garder |
| 10 | Prénom « Alexis » (≈ 60 fichiers : commentaires, rapports, briefs, tests) | arbre | product owner, décisions (« décision d'Alexis ») | **garder** : c'est le propriétaire du dépôt, et ces mentions montrent qui tranche — la méthode |
| 11 | Phrases de la session de test d'Alexis (`tests/test_gter.py`, `tests/test_session_alexis_gbis.py`, `BILAN_SESSION_ALEXIS_20261011.md`) | arbre | commandes de test tapées (« ferme steam »…) | **garder** : aucune donnée de vie privée |
| 12 | Données de test inventées : `tests/test_beta_safety_g.py` (une sœur fictive, un code fictif), `tests/test_memory_quality_d.py` (habitudes de jeu et d'applications) | arbre | phrases d'exemple | **garder**, ou neutraliser `test_memory_quality_d.py` si ces habitudes sont réelles (Alexis le sait, pas moi) |
| 13 | Titres de fenêtres Discord dans les rapports B1, B1-bis, G, G-bis | arbre + historique | déjà anonymisés (« ★ conversation privée - Discord », « @★ … ») dans **toutes** les versions | **garder** |
| 14 | `tests/fixtures/*.wav` (5) ; `test_kokoro_rori.wav`, `petite_image.png` (historique seulement) | arbre / historique | voix de synthèse (Piper, Kokoro) ; découpe d'un écran de jeu pour l'OCR | **garder** |
| 15 | Secrets | arbre + historique | **aucun trouvé**. `config/oauth_tokens/` et `.env` n'ont jamais été suivis. La seule « clé » est le modèle `atlas_secret_key_change_me` de SearXNG (service lié à 127.0.0.1, commentaire déjà présent dans `docker-compose.yml`) | **garder** ; à remplacer le jour où SearXNG sort de 127.0.0.1 |
| 16 | Branches : 12 branches distantes (`sprint-*`, `g-bis-suivi`) | dépôt | **toutes fusionnées** : aucune n'a de commit absent de `main` (`git rev-list --count origin/main..<branche>` = 0 pour les 12) | **les supprimer** avant R3 (le brief demande « aucune branche ouverte ») ; elles restent dans la sauvegarde miroir — à confirmer |

## Décisions d'Alexis (12/10/2026, dans la conversation)

| # | Décision | Où c'est appliqué |
|---|---|---|
| 1, 2, 3 | comme proposé : retirer, compléter `.gitignore` | R2 (arbre), R3 (historique) |
| 4 | comme proposé : persona anonymisé (« Compagnon », proche fictive « Camille »), fichier de dépendances renommé `requirements-mac-compagnon.txt` | R2, R3 |
| 5 | **garder** le nom complet | rien |
| 6 | comme proposé : `C:\Users\utilisateur` | R2, R3 |
| 7 | réglé par la ligne 1 | — |
| 8 | comme proposé : les deux citations remplacées | R2, R3 |
| 9 | d'abord « réécrire » (12/10), puis **garder** (13/10 : « c'est pas bien grave ») | rien : pas de `--mailmap` |
| 10, 11, 13, 14, 15 | garder | rien |
| 12 | **garder** : ce sont des phrases d'exemple écrites dans un test, pas des habitudes détectées chez un testeur | rien |
| 16 | **supprimer** les 12 branches distantes | avant la publication de R3, après la sauvegarde miroir |

Alexis a tranché les points signalés comme à décider (5, 9, 12, 16). Les autres lignes sont appliquées comme proposé.
