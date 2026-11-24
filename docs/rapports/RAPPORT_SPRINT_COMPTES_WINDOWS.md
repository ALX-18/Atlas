# RAPPORT SPRINT — COMPTES WINDOWS (IF7) : un Atlas ne sert qu'au compte qui l'a lancé

**Développeur :** CHAT6 (Claude Opus, Claude Code Windows)
**Brief :** `docs/briefs/BRIEF_SPRINT_INSTALLEUR_FIN.md`, §6 (décisions du 23/11, mises à jour le 24/11) ; conclusion de la Réunion n° 3, version du 24/11 (`docs/reunions/REUNION_ATLAS_03_COMPTES_WINDOWS.md`)
**Branche :** `sprint-comptes-windows`, partie de `main` (`8e23174`)
**Date :** 24 novembre 2026

> IF7 passe avant le parcours sur `AtlasTest`. Ce rapport couvre ce qui se fait et se mesure **depuis un seul compte**, sur le PC d'Alexis. **Ce qui exige deux comptes n'est pas encore mesuré** : lire le propriétaire d'un processus d'un autre compte sans droits d'administrateur, deux comptes sur le même port, et les cinq critères d'envoi. La fiche `docs/beta/FICHE_COMPTE_NEUF.md` dit comment les mesurer, à l'étape 0 et après le relevé n° 2. C'est marqué **À MESURER** partout.

---

## 1. Résumé exécutif

- **Statut : PARTIELLEMENT VALIDÉ.** Les points 1 à 8 de la conclusion, et la clé minimale, sont faits et testés depuis un compte. Les mesures à deux comptes, sur `AtlasTest`, attendent Alexis.
- **Ce qui change pour Atlas :**
  - **le propriétaire de ce qui écoute est vérifié** sur 8550 (Atlas) et 11434 (Ollama), à chaque point de connexion : le diagnostic, l'installeur avant tout téléchargement, le lanceur, la fenêtre à chaque demande, et le serveur avant chaque échange avec Ollama. Un propriétaire illisible compte comme « pas à moi » ;
  - **une clé locale par installation** : toute demande à l'API la porte, et seule la fenêtre native l'a. Elle ne l'envoie qu'après avoir vérifié le serveur ;
  - **l'interface web est coupée**, chez Alexis aussi (sa décision du 24/11) : « Ouvrir » ouvre la fenêtre native ;
  - **le pont navigateur** lit son réglage et refuse tout ce qui n'est pas l'extension. Le paquet testeur le ferme, même lors d'une mise à jour qui garde les réglages ;
  - **« Quitter » est un arrêt ordonné.** L'Ollama lancé par Atlas est arrêté, et lui seul ;
  - l'installeur ne touche plus qu'aux processus du compte courant ;
  - `doctor.py` n'avale plus d'erreur, dit un refus de clé, et n'envoie pas sa clé à l'Atlas d'un autre compte.
- **Tests :** 105 tests nouveaux dans `tests/test_comptes_windows.py`, plus 1 dans `test_checkup.py`.
  - **103 vus rouges** avant le code. Les 3 autres étaient verts dès le départ : 2 garde-fous, et 1 mesure avec un vrai uvicorn, écrite après le code.
  - Suite complète avec Ollama, 2e passage : **1 804 réussis, 1 échec**, celui de `config/searxng/`. Au 1er passage : **1 802 réussis, 2 échecs** (§5) :
    - l'un venait de fichiers pas encore ajoutés à git. Il passe une fois les fichiers indexés ;
    - l'autre vient d'un dossier `config/searxng/` qui n'est pas de moi. Alexis demande de le laisser (§7).
  - Suite sans Ollama : **1 801 réussis, 3 ignorés justifiés** (les mêmes trois qu'avant), et le seul échec est celui de `config/searxng/`.
- **Mesuré pour de vrai sur ce PC, depuis un compte :**
  - un Atlas d'essai, lancé par `main.py` sur des données jetables : sans clé, **401** sur les 6 demandes, y compris `/api/memory/ingest` et `/api/confirm` ; avec la clé, 200 ;
  - la clé a **une seule autorisation**, pour le compte courant, et aucune héritée ;
  - le pont : page web et absence d'origine **refusées (403)**, l'extension acceptée ;
  - arrêt propre en 0,9 s, port libéré ;
  - **aucun fichier de `data/` n'a changé**, sauf `atlas.lock`, qui l'était déjà avant IF7 ;
  - le vrai diagnostic lit le propriétaire d'Ollama : « lancé par ce compte ».

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief §6, conclusion du 24/11) | Résultat réel | Statut |
|---|---|---|
| Point 1 — Pont : le serveur **lit** `browser_bridge.enabled` ; le paquet le force à `false`, y compris lors d'une mise à jour | `main.pont_actif` et `config/paquet.json`, remplacé à chaque installation. `construire.regler_paquet` ferme le pont dans `settings.json` et dans `paquet.json`. `verifier_paquet` refuse un pont ouvert. | PASS (tests) ; **À MESURER** sur `AtlasTest` (aucune écoute sur 9999, après une installation neuve et après une mise à jour) |
| Point 1 — Le pont refuse toute `Origin` http(s) : seule `chrome-extension://` passe | `origine_acceptee`, vérifiée dès la poignée de main WebSocket (`process_request`), donc avant d'enregistrer le client. Un vrai pont et de vrais clients dans les tests : page web refusée, absence d'origine refusée, extension acceptée. | PASS |
| Point 2 — Propriétaire vérifié dans le lanceur, avant d'ouvrir la fenêtre | `lancer.demarrer_atlas` : Ollama, puis Atlas, puis pendant l'attente du serveur (tour 2 : le serveur d'un autre pris pour le sien) | PASS (tests) |
| Point 2 — … dans la fenêtre, à chaque connexion et reconnexion | `desktop/connexion.py` : chaque demande revérifie qui écoute, en ~2 ms. Si ce n'est pas le compte, la connexion est **coupée** : plus rien ne part. | PASS (tests) ; **À MESURER** à deux comptes (critère 3) |
| Point 2 — … dans le serveur, avant de parler à Ollama, au démarrage et à chaque reconnexion | `proprietaire.garde_ollama()` dans les 12 appels du serveur à Ollama. Un test recense tous les fichiers qui parlent à Ollama, comme CM0 pour `data/`. Un refus est une bascule, dite dans la conversation. | PASS (tests) |
| Point 2 — … dans l'installeur, **avant tout téléchargement**, avec le diagnostic à l'étape 1 | `precheck_atlas.ps1` lit le propriétaire (`Get-NetTCPConnection` puis `GetOwner`). L'installeur Inno a son propre message. `etapes.verifier_comptes` s'exécute avant les dépendances, à chaque lancement, et chaque appel à Ollama de l'installeur revérifie. | PASS (tests) ; propriétaire lu « ce compte » sur ce PC (§6) ; **À MESURER** pour un autre compte |
| Point 2 — Propriétaire illisible = « pas à moi » | Partout : `Verdict("illisible")` refuse, dans le Python comme dans le PowerShell | PASS |
| Point 2 — Le comportement réel sans droits d'administrateur, mesuré sur `AtlasTest` avant toute phrase | `scripts/mesure_comptes.ps1` et `.bat`, étape 0 de la fiche | **À MESURER** |
| Point 3 — `apps_ollama()` et `balayer()` filtrés par compte | `apps_ollama` ne rend que les applications Ollama du compte courant. Un compte illisible n'est jamais touché. | PASS |
| Point 4 — Atlas arrête à sa fermeture l'Ollama qu'il a lancé, par son PID ; jamais un Ollama trouvé en marche | `core/ollama_lance.py`. Le lanceur et l'installeur notent l'Ollama qu'ils lancent (PID et heure de démarrage). À l'arrêt, il n'est arrêté que si l'heure, le nom et le compte concordent. Seul le vrai Atlas l'arrête, pas un Atlas d'essai. | PASS (tests) ; **À MESURER** (critère 2) |
| Point 4 complété — « Quitter » : arrêt ordonné ; `os._exit(0)` seulement en dernier recours, après un délai, noté au journal | `core/arret.py` : `should_exit` sur le serveur uvicorn gardé. Un dernier recours après 20 s, noté au journal. Testé avec un vrai uvicorn. | PASS (tests) ; **pas cliqué pour de vrai** (§7) |
| Point 5 — Le message de refus, en deux versions, avec une vraie sortie, [Réessayer] et [Fermer] ; refus au démarrage avec Windows noté puis dit | `proprietaire.message_refus` nomme le composant et ne dit que ce qui a été vérifié. Le nom de l'autre compte n'apparaît que s'il a été lu. `lancer.FenetreRefus` a les deux boutons. Au démarrage avec Windows, le refus va dans le journal et dans `data/logs/refus_demarrage.json`, puis il est dit à la première ouverture. | PASS (tests) ; **fenêtre de refus pas vue à l'écran** (§7) |
| Point 6 — `doctor.py` n'avale plus d'exception | `_atlas_health` rend un état : éteint, ok, clé refusée, autre compte, ou erreur avec son type | PASS |
| Point 7 — Un test par cas de refus, rouge d'abord | 103 tests vus rouges avant le code, dont un par cas de refus : Atlas d'un autre compte, Ollama d'un autre compte, propriétaire illisible, serveur étranger sur 8550 pendant que la fenêtre interroge, origine web sur le pont (§5) | PASS |
| Point 8 — Une note dans le guide à distance | `GUIDE_INSTALLATION_A_DISTANCE.md`, nouvelle section « Si d'autres personnes ont un compte Windows sur cet ordinateur » | PASS |
| B minimal — Clé par installation, dans le dossier d'Atlas du compte, vérifiée dans le seul middleware | `core/cle_locale.py` ; `data/cle_locale`, restreint au compte par `icacls`. Le middleware `_seul_atlas` vérifie la clé partout, sauf la page `/`. | PASS (tests) ; restriction mesurée sur un vrai fichier (§6) |
| B minimal — La fenêtre vérifie l'identité du serveur **avant** d'envoyer la clé, y compris après une reconnexion | `ConnexionAtlas._verifier_serveur` avant chaque envoi | PASS (tests) |
| B minimal — Clé absente ou illisible : une erreur qui dit comment réparer | `CleIntrouvable` : « quittez Atlas… puis relancez-le : il en crée une nouvelle » | PASS |
| B minimal — Après un changement de clé, on la relit, sans rejouer d'action | Une lecture est redemandée une fois avec la nouvelle clé. Une action n'est **jamais** renvoyée : « rien n'a été fait ». | PASS |
| B minimal — Web coupé dans le paquet ; « Ouvrir » mène à la fenêtre native ; extension non livrée ; `doctor.py` dit un 401 | Web coupé **partout**, décision d'Alexis du 24/11 : `/` dit que l'interface est coupée, et `/static` n'est plus servi. L'extension n'est déjà pas dans `INCLUS`. `doctor` dit « clé refusée (401) ». | PASS |
| Critères d'envoi de GPT, mesurés sur `AtlasTest` avec deux comptes standard | Fiche prête (§ « Les critères d'envoi ») | **À MESURER** |
| Petit point accepté — CK4 affiche la fin de la sortie d'erreur | `_fin_des_sorties` dans les trois tests CK4, avec un test rouge d'abord | PASS |
| Petit point accepté — `C:\Users\Public\AtlasTest` effacé après le parcours | Inscrit dans la fiche (« Après », point 5) | **À FAIRE** après le parcours |
| Pas d'envoi aux testeurs avant que tous les critères soient mesurés | Aucun lien envoyé, aucun partage créé | PASS |

---

## 3. Architecture projet mise à jour

```
core/
├── proprietaire.py            ← NOUVEAU IF7 : à qui appartient ce qui écoute ; Garde ; message de refus
├── cle_locale.py              ← NOUVEAU IF7 : la clé locale par installation
├── arret.py                   ← NOUVEAU IF7 : « Quitter » en arrêt ordonné, dernier recours noté
├── ollama_lance.py            ← NOUVEAU IF7 : l'Ollama lancé par Atlas, noté, arrêté lui seul
├── donnees_reelles.py         (ollama_lance.py dans ECRIVAINS_HORS_GARDE, avec sa raison)
├── ollama_client.py           (garde_ollama avant le préchauffage et chaque conversation)
├── artefacts.py, courrier.py, modele_local.py   (garde_ollama avant chaque appel)
core_conversational/
├── degradations.py            (bascule « ollama_autre_compte »)
├── llm_client.py              (garde_ollama)
tools/
├── browser_bridge.py          (origine_acceptee, refus à la poignée de main)
├── grounding.py, web_reader.py                   (garde_ollama)
api/
├── routes.py                  (garde_ollama dans /health ; refus d'Ollama dit tel quel dans /chat)
desktop/
├── connexion.py               ← NOUVEAU IF7 : ConnexionAtlas, vérifier puis porter la clé
├── atlas_desktop.py           (toutes les demandes par ConnexionAtlas ; coupure dite une fois)
installeur/
├── lancer.py                  (vérification du propriétaire, FenetreRefus, refus au démarrage noté, Ollama noté)
├── etapes.py                  (verifier_comptes avant tout téléchargement ; apps_ollama par compte ; Ollama noté)
├── construire.py              (regler_paquet, paquet.json, _fautes_du_pont)
├── atlas.iss                  (message « autre compte » distinct)
scripts/
├── precheck_atlas.ps1         (propriétaire de 11434 et 8550 ; ligne autre_compte=)
├── mesure_comptes.ps1/.bat    ← NOUVEAU IF7 : la mesure de l'étape 0, sur AtlasTest
├── rejeu_comptes.py           ← NOUVEAU IF7 : le rejeu réel, Atlas d'essai sur données jetables
├── doctor.py                  (_atlas_health sans exception avalée ; clé ; propriétaire)
├── checkup_dynamique.py, rejeu_artefacts.py, rejeu_competences.py, rejeu_sur_mesure.py,
│   rejeu_courrier.py, mesure_ressources.py      (clé jetable de leur Atlas d'essai)
main.py                        (clé au démarrage, middleware, web coupé, pont lu, Ouvrir, Quitter, arrêt)
tests/
├── test_comptes_windows.py    ← NOUVEAU IF7
├── conftest.py                (clé jetable de la suite)
├── test_beta_safety_g.py, test_metrics_grounding_v52.py, test_stabilisation_v31.py, test_v53_migration.py,
│   test_installeur.py, test_checkup.py          (la clé de la fenêtre ; voir §5)
docs/beta/
├── FICHE_COMPTE_NEUF.md       (étape 0, critères d'envoi)
├── GUIDE_INSTALLATION_A_DISTANCE.md             (note « plusieurs comptes »)
docs/rapports/
└── RAPPORT_SPRINT_COMPTES_WINDOWS.md            ← NOUVEAU
```

---

## 4. Détail des implémentations

### `core/proprietaire.py` (nouveau)
- `ecouteur(port)` : le processus qui recevrait une connexion à `127.0.0.1:port`. Il préfère un écouteur sur `127.0.0.1` exact à un `0.0.0.0`, comme Windows. Il lit `psutil.net_connections(kind="tcp4")`, en ~1,8 ms mesurées.
- `verifier(port)` rend un `Verdict` : `libre`, `a_moi`, `autre` ou `illisible`. Le compte est comparé sans tenir compte des majuscules. Un numéro de processus absent, ou un compte illisible (`AccessDenied`), donne `illisible`.
- `Garde` : vérifie à chaque appel. Si c'est le même processus qu'au dernier contrôle réussi, même numéro **et** même heure de démarrage, le compte n'est pas relu. Sinon, il l'est. Pas à moi : `AutreCompte`, et rien n'est envoyé.
- `garde_ollama()` : utilisé par le serveur et par l'installeur. Un refus signale la bascule `ollama_autre_compte`, et une vérification réussie la lève.
- `message_refus(composant, verdict, sortie=…, rien_envoye=…)` :
  - nomme le composant, et ne dit « un autre compte » que si c'est vérifié. Sinon, il dit « Atlas n'a pas pu vérifier à qui appartient… » ;
  - ne nomme l'autre compte que s'il a été lu ;
  - donne la sortie : se déconnecter (« Changer d'utilisateur » ne suffit pas), ou redémarrer le PC, puis Réessayer, relancer l'installation ou relancer Atlas.

### `core/cle_locale.py` (nouveau)
- `preparer()` : au démarrage du serveur, relit la clé, ou en crée une, une seule fois. Elle est tirée par `secrets.token_urlsafe(32)`, écrite par un fichier temporaire puis `os.replace`, et restreinte par `icacls /inheritance:r /grant:r <compte>:(F)`.
- La création passe par la garde BM0 (`verifier_ecriture`) : un Atlas d'essai ne la crée jamais dans les vraies données.
- `ATLAS_CLE_LOCALE` redirige la clé. La suite de tests a la sienne, jetable, et les scripts d'essai aussi (`pour_essai()`).
- `lire()` : clé absente, vide ou abîmée → `CleIntrouvable`, avec le message de réparation.
- `acceptee()` compare en temps constant (`secrets.compare_digest`).

### `main.py`
- **Démarrage :** la clé est préparée juste après le verrou. Si c'est impossible, Atlas **refuse de démarrer** et le dit au journal : il ne tourne pas ouvert aux autres comptes.
- **Middleware `_seul_atlas` :** d'abord le contrôle d'origine de G1 (403), puis la clé (401), partout sauf `/`. Le journal dit « clé absente » ou « clé fausse ».
- **Interface web :** `/` rend une page qui dit qu'elle est coupée, et `/static` n'est plus monté.
- **Pont :** `pont_actif(CONFIG, _lire_paquet())`. Un `paquet.json` illisible ferme le pont, par prudence.
- **« Ouvrir »** → `ouvrir_fenetre_native()`, avec `pythonw` à côté de `python`.
- **« Quitter »** → `arret.arret_ordonne(liberer=…, arreter_ollama=…)`.
- **Fin du lifespan :** `_arreter_ollama_lance()`, qui ne fait rien si ce n'est pas le vrai Atlas (`autorise()`), puis le verrou.
- **Lancement :** `uvicorn.Server` gardé dans `core.arret.SERVEUR`. `uvicorn.run` reste pour le mode rechargement.

### `core/arret.py`, `core/ollama_lance.py` (nouveaux)
- `arret_ordonne` arme un minuteur, en fil démon, de 20 s, puis demande l'arrêt : `SERVEUR.should_exit = True`, ou `SIGINT` en mode rechargement.
- `arret_force` : le dernier recours. Il le note au journal, arrête l'Ollama d'Atlas, libère le verrou, puis arrête le processus.
- `ollama_lance.noter(pid, debut, par)` écrit dans `data/ollama_lance.json`.
- `ollama_lance.arreter()` rend :
  - `aucun`, s'il n'y a pas de note ;
  - `arrete` : Ollama et ses sous-processus, d'abord `terminate`, puis `kill` après 5 s ;
  - `parti` ;
  - `pas_le_sien` : heure de démarrage, nom ou compte différents, et la note périmée est retirée.

### `desktop/connexion.py` (nouveau) et `desktop/atlas_desktop.py`
- `ConnexionAtlas.requete(...)` :
  1. elle vérifie le serveur, et coupe s'il n'est pas au compte ;
  2. elle relit la clé ;
  3. elle envoie ;
  4. sur un 401, elle relit la clé : une lecture (`get`) est redemandée une fois, une action (`post`) lève `CleChangee` : « rien n'a été fait. Renvoie ta demande ».
- Rien n'écoute : `ServeurAbsent`, et rien ne part.
- `atlas_desktop.py` : les six usages de `httpx.Client` passent par `self.atlas`.
  - La coupure est dite une fois, puis le suivi de la voix s'arrête.
  - Un refus de confirmation dit que rien n'est parti, au lieu de « je ne sais pas si l'action a été faite ».

### Le serveur et Ollama
- `garde_ollama()` est placé avant chacun des 12 appels : préchauffage, conversation en flux et complète, artefacts, courrier, `modele_local` (étiquettes, modèles chargés, déchargement), grounding (étiquettes, vision), `web_reader`, `/api/health`, et `LLMClient`.
- Dans `/api/chat`, `_erreur_modele` rend `ERR_OLLAMA_AUTRE_COMPTE`, avec le message de refus, au lieu de « Le modèle local est indisponible ».

### `tools/browser_bridge.py`
- `origine_acceptee(origine)` : `chrome-extension://` suivi d'un identifiant, sinon rien.
- `_verifier_origine` est branché en `process_request` de `websockets.serve` : refus 403 à la poignée de main, avant d'enregistrer le client.

### L'installeur
- **`lancer.py` :**
  - `verdict_atlas` et `verdict_ollama` ;
  - `assurer_ollama` rend aussi `autre` ou `illisible` (compatible avec l'ancien `ecoute=`) et note l'Ollama qu'il lance ;
  - `demarrer_atlas` ; `main(ui=…)` avec la boucle [Réessayer] ;
  - `FenetreRefus` (Tk) ; `_ecrire_refus_demarrage` et `_lire_refus_demarrage`.
- **`etapes.py` :**
  - `verifier_comptes()` en tête de `_lancer`, hors de la reprise : il n'est jamais « déjà fait » ;
  - `_api` et `tirer_modele` appellent `garde_ollama()` ;
  - `attendre_ollama` ne confond plus un refus avec une lenteur ;
  - `apps_ollama` filtre par compte ;
  - `demarrer_ollama_sans_fenetre` note l'Ollama lancé.
- **`construire.py` :**
  - `regler_paquet` : mails en simulation, prénom vide, pont fermé dans `settings.json`, et `paquet.json` ;
  - `_fautes_du_pont` dans `verifier_paquet`.
- **`atlas.iss` :** les lignes `autre_compte=` du diagnostic donnent leur propre message, « Atlas ne peut pas s'installer pour vous pour l'instant… rien n'a été installé ni téléchargé ». Ce n'est pas « cette machine ne convient pas ».
- **`precheck_atlas.ps1` :**
  - `Proprietaire-Port` : `Get-NetTCPConnection`, puis `Win32_Process.GetOwner`. Si `Get-NetTCPConnection` reste muet alors que quelqu'un écoute, c'est « illisible » ;
  - le mode `-Simuler` prend `ports` ;
  - les messages sont en ASCII, comme les autres messages du diagnostic.

### `scripts/doctor.py`
- `_atlas_health()` rend `{"etat": eteint | ok | cle_refusee | autre_compte | erreur, …}`.
- Le propriétaire est vérifié **avant** d'envoyer la clé.
- `check_bascules` dit l'erreur telle quelle.

### Scripts d'essai
- `checkup_dynamique` pose une clé jetable (`cle_locale.pour_essai()`), et `req()` et `attendre()` la portent.
- Les rejeux qui en dépendent la portent donc aussi.
- `rejeu_artefacts`, `rejeu_competences`, `rejeu_sur_mesure`, `rejeu_courrier` et `mesure_ressources` l'ajoutent à leurs propres appels.
- Un test recense les scripts qui appellent l'API.

---

## 5. Résultats des tests

**Commande :** `.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider`. Le même fichier est lancé seul pendant le travail : `-m pytest tests/test_comptes_windows.py -q`.

**Tests rouges d'abord.** Premier passage de `tests/test_comptes_windows.py`, avant tout code : **102 échecs, 2 réussis**, ces deux-là étant des garde-fous :
- `test_if7_le_depot_garde_le_pont_d_alexis` : le dépôt n'a pas de `paquet.json` ;
- le cas « personne d'autre » du diagnostic, qui doit rester vert.

Ensuite :
- `test_ck4_un_echec_du_pytest_isole_montre_la_fin_des_deux_sorties` : vu rouge (`NameError`), puis vert ;
- `test_if7_quitter_declenche_vraiment_le_nettoyage_d_un_vrai_serveur_uvicorn` : écrit **après** le code, vert dès le départ. C'est une mesure du mécanisme, pas un test rouge.
- Fichier seul, à la fin : **105 réussis**.

**Tests existants modifiés, et pourquoi :**

| Fichier | Changement | Raison |
|---|---|---|
| `test_beta_safety_g.py` | Le client porte la clé. `test_g1_la_fenetre_atlas_et_l_interface_web_fonctionnent` devient `…_fonctionne_et_l_interface_web_est_coupee`. | Décision d'Alexis du 24/11 : l'ancienne interface web, même origine mais sans clé, reçoit 401 et n'exécute rien. La fenêtre passe toujours. |
| `test_metrics_grounding_v52.py`, `test_stabilisation_v31.py`, `test_v53_migration.py` | Leur `TestClient` porte la clé (`_cle_fenetre()`) | Ce sont des appels de la fenêtre |
| `test_installeur.py` | `test_if1_le_lanceur_s_assure_d_ollama_avant_de_demarrer_atlas` simule `verdict_atlas` et interdit `demarrer_serveur` | Le lanceur demande désormais à qui est l'Atlas qui écoute. Sans ce changement, le test aurait lancé un vrai serveur. |
| `test_checkup.py` | CK2 : `_atlas_health` rend un état, plus `None`. CK4 : les messages d'échec montrent la fin des deux sorties. | Point 6 de la conclusion ; petit point accepté |
| `conftest.py` | `ATLAS_CLE_LOCALE` vers une clé jetable | Aucun test ne lit la vraie clé : un test le vérifie |

**Suites complètes du 24/11 :**

| Passage (branche `sprint-comptes-windows`) | Résultat | Code |
|---|---|---|
| Avec Ollama, 1er passage, fichiers nouveaux pas encore indexés | **1 802 réussis, 2 échecs** (10 min 56) | 1 |
| Sans Ollama (fichiers indexés) | **1 801 réussis, 3 ignorés justifiés, 1 échec** : `test_sd4_…`, le dossier `config/searxng/` (10 min 58). Ollama relancé ensuite (0.40.6 répond). | 1 |
| Avec Ollama, 2e passage, fichiers indexés | **1 804 réussis, 0 ignoré, 1 échec** : `test_sd4_…`, le dossier `config/searxng/` (10 min 34) | 1 |

**Les deux échecs du 1er passage :**
1. `test_pre_beta.py::test_pb2_import_de_main_sans_dossier_logs` copie les fichiers **suivis par git** (`git ls-files`) dans un dossier neuf, puis importe `main`. Mes nouveaux modules n'étaient pas encore ajoutés : `ModuleNotFoundError: core.proprietaire`. Une fois les fichiers indexés (`git add`), il passe : **1 réussi**.
2. `test_sans_docker.py::test_sd4_docker_compose_et_searxng_retires` : le dossier `config/searxng/` existe sur ce PC. Il n'est pas suivi par git et n'est pas de moi : un `settings.yml` de 67 Ko, daté du 24/11 à 13:38, déjà là à mon premier `git status` du jour. **Alexis demande de le laisser** (« on verra avec l'autre instance ») : ce test reste rouge sur ce PC tant qu'il est là (§7, point 1).

**Non-régression :** toutes les autres suites du dépôt passent dans les passages complets ci-dessus. Cela comprend le recensement des écrivains de `data/` (CM0, `core/ollama_lance.py` y est déclaré avec sa raison) et celui des bascules (CK2 : `ollama_autre_compte` est au catalogue et signalée).

---

## 6. Comportement observé en scénarios réels

**Tout est mesuré depuis le compte d'Alexis, seul.** Les mesures à deux comptes sont à l'étape 0 de la fiche et dans « Les critères d'envoi ».

### 6.1 Le rejeu réel : `scripts/rejeu_comptes.py`, le 24/11 à 15:20

- C'est un vrai `main.py`, lancé comme les autres rejeux.
- La mémoire, le journal, l'apprentissage, les habitudes, les rappels, l'index et la clé sont dans un dossier jetable.
- Aucune phrase n'est envoyée au modèle. API prête en 15,2 s.

| ID | Demande | Attendu | Observé | Statut |
|---|---|---|---|---|
| R1 | Démarrage d'un Atlas neuf | Clé créée dans le fichier jetable, journal « Clé locale prête » | 43 caractères ; journal : oui ; aucune clé créée dans `data/` | PASS |
| R2 | Droits de la clé (`icacls`) | Une seule autorisation, au compte courant, sans héritage | 1 règle, au compte courant ; 0 héritée | PASS |
| R3 | `GET /api/health` sans clé, puis avec une fausse clé | 401, 401 | 401, 401 | PASS |
| R4 | `GET /api/memory/recall`, `GET /api/confirmations` sans clé | 401 | 401, 401 | PASS |
| R5 | `POST /api/memory/ingest` (phrase inventée), `POST /api/confirm` sans clé | 401, rien d'écrit ni d'exécuté | 401, 401 | PASS |
| R6 | `GET /api/health` avec la clé | 200 | 200 | PASS |
| R7 | `GET /` ; `GET /static/app.js` avec la clé | 200 et la page dit « coupée » ; 404 | 200, « coupée » ; 404 | PASS |
| R8 | Pont 9999 (actif chez Alexis) : page web ; sans origine ; extension | 403 ; 403 ; acceptée | refusée (403) ; refusée (403) ; acceptée | PASS |
| R9 | La fenêtre native (`ConnexionAtlas`) : `/api/health` | serveur vérifié « à ce compte », 200 | 8550 : a_moi ; 11434 : a_moi ; 200 | PASS |
| R10 | Arrêt (Ctrl+Pause, comme les autres rejeux) | Arrêt propre, port libéré ; un Atlas d'essai n'arrête pas l'Ollama | propre, 0,9 s ; port libéré ; journal « Atlas arrêt propre. » ; Ollama toujours là | PASS |
| R11 | Les 198 fichiers de `data/`, avant et après | Identiques, sauf le verrou | Seul `atlas.lock` diffère. Il contient le numéro du processus, et `main` l'écrivait déjà ainsi pour tout Atlas : ce n'est pas IF7. | PASS |

### 6.2 Le diagnostic et la mesure de l'étape 0, sur ce PC

| ID | Commande | Attendu | Observé | Statut |
|---|---|---|---|---|
| D1 | `precheck_atlas.ps1 -Sortie …`, la vraie lecture, avec l'Ollama d'Alexis lancé | Ollama « lancé par ce compte » ; verdict inchangé | « Ollama : lance par ce compte », « Atlas : pas lance » ; verdict ok, `qwen2.5:7b` sur la carte ; aucune ligne `autre_compte` ; 7,9 s | PASS |
| D2 | `mesure_comptes.ps1` (essai à blanc, un seul compte) | Le script tourne, lit les propriétaires, n'écrit que son rapport | Ollama : « ce compte » ; 8550 et 9999 libres ; Ollama `/api/version` 200 ; sur 11434, la liaison est refusée sans SO_REUSEADDR (10048) **et avec** (10013), même depuis le même compte | PASS (essai) ; **la vraie mesure est sur `AtlasTest`** |

### 6.3 Ce qui n'a pas été vu pour de vrai

Tout cela est dit en §7 :
- « Quitter » cliqué dans l'icône ;
- la fenêtre de refus du lanceur à l'écran ;
- le message « autre compte » de l'installeur Inno ;
- la coupure de la fenêtre quand le serveur change.

---

## 7. Limites et risques identifiés

1. **`config/searxng/`, un dossier qui n'est pas de moi, fait échouer `test_sd4_…`.** Il n'est pas suivi par git : un `settings.yml` de 67 Ko, daté du 24/11 à 13:38.
   - Sévérité : **Faible** pour IF7. Mais la règle « code 0 » n'est pas tenue sur ce PC tant qu'il est là.
   - Mitigation : décision d'Alexis, « ne le fait pas partir, on verra avec l'autre instance ». Il est laissé en place et n'est pas commité.
2. **Rien n'est encore mesuré à deux comptes.** Que lit Windows, sans droits d'administrateur, du processus d'un autre compte ? Un second compte peut-il prendre un port tenu par le premier ? Les cinq critères d'envoi ?
   - Sévérité : **Élevé** tant que ce n'est pas mesuré : c'est la condition d'envoi.
   - Mitigation : l'étape 0 et « Les critères d'envoi » de la fiche, avec `mesure_comptes.bat`. **Pas d'envoi avant.**
   - Si Windows rend le propriétaire **lisible** pour un autre compte, le refus dit « un autre compte » au lieu de « illisible ». Les deux refusent.
3. **Ollama reste sans authentification.** C'est un logiciel tiers. Un programme d'un autre compte peut se servir de l'Ollama d'Alexis pendant que sa session est ouverte, comme l'a mesuré D2 (`/api/version` répond à tous).
   - Atlas, lui, ne se sert jamais d'un Ollama qui n'est pas au compte.
   - Sévérité : **Moyen**, et dit dans le guide à distance.
   - Mitigation : aucune dans Atlas. Ollama ne garde pas les conversations.
4. **« Quitter » n'a pas été cliqué pour de vrai.** Le mécanisme est testé avec un vrai uvicorn, et l'arrêt par Ctrl+Pause est mesuré (R10). Le clic dans l'icône, et l'arrêt de l'Ollama lancé par Atlas, se mesurent au critère 2 sur `AtlasTest`.
   - Sévérité : **Moyen**.
5. **La fenêtre de refus du lanceur et le message Inno n'ont pas été vus à l'écran.** Pour qu'ils s'affichent, il faut un autre compte.
   - Sévérité : **Faible**. Le texte est testé ; la mise en page reste à voir à l'étape 0, point 6, et au critère 4.
6. **L'Ollama installé par Atlas sur un compte neuf peut se relancer à l'ouverture de session.** IF1 a relevé que l'application Ollama pose, à son premier lancement, un raccourci dans le dossier Démarrage. Un Ollama relancé ainsi n'a pas été lancé par Atlas : « Quitter » ne l'arrête pas, à raison, et un autre compte reste bloqué jusqu'à la déconnexion.
   - Sévérité : **Moyen** sur un PC familial.
   - Mitigation : le message de refus donne la sortie (se déconnecter, ou redémarrer). Retirer ce raccourci quand Atlas a installé Ollama serait une décision du superviseur : **non fait**.
7. **L'interface web est coupée chez Alexis aussi** (sa décision). `scripts/manual/*`, des scripts de développement à la main, appellent l'API sans clé : ils recevront 401.
   - Sévérité : **Faible**.
   - Mitigation : les rejeux et les mesures portent leur clé jetable. Le recensement IF7 les vérifie ; `scripts/manual/` n'en fait pas partie.
8. **La clé n'est pas un secret pour un administrateur du PC**, ni pour un programme du même compte, qui peut lire `data/cle_locale`. C'est la frontière annoncée par la Réunion n° 3 : la clé sépare les comptes, pas les programmes d'un même compte.
   - Sévérité : **Faible**.
9. **La vérification de la fenêtre se fait juste avant chaque connexion**, pas sur la connexion elle-même. Entre les deux, environ 2 ms, un autre compte qui prendrait le port recevrait une demande.
   - Sévérité : **Faible**. Il recevrait la clé du compte, mais une clé ne sert qu'à l'Atlas de ce compte, et l'autre compte n'a pas d'Atlas à qui la présenter. Il pourrait aussi renvoyer une fausse réponse à cette demande.
   - Mitigation possible, non faite : vérifier le processus à l'autre bout de la connexion TCP déjà ouverte.
10. **Changement de comportement :** un Atlas qui ne peut ni lire ni créer sa clé **refuse de démarrer**. Avant, il démarrait toujours.
    - Sévérité : **Faible**. C'est le choix « pas de repli silencieux ». Le journal dit pourquoi.

---

## 8. Checklist de validation

- [x] Branche `sprint-comptes-windows` partie de `main` à jour (`8e23174`)
- [x] Points 1 à 8 de la conclusion, et B minimal, codés — §2, §4
- [x] Tests rouges d'abord : 103 vus rouges — §5
- [x] Rejeu réel, un compte : clé, refus sans clé, page coupée, pont, fenêtre, arrêt, `data/` inchangé — §6.1
- [x] Diagnostic réel : propriétaire lu — §6.2
- [x] Fiche `AtlasTest` mise à jour (étape 0, critères d'envoi) ; note du guide à distance
- [x] CK4 : fin des deux sorties
- [ ] `python -m pytest tests/ -q` → code 0, avec et sans Ollama — **non tenu sur ce PC** à cause de `config/searxng/` (§7, point 1) ; tout le reste réussit (§5)
- [ ] Étape 0 sur `AtlasTest` — **À MESURER (Alexis)**
- [ ] Les cinq critères d'envoi — **À MESURER (Alexis)**
- [ ] `C:\Users\Public\AtlasTest` effacé — **après le parcours**
- [x] Aucun lien envoyé aux testeurs

---

## 9. Prochaines étapes

- **P1 :**
  - fusionner `sprint-comptes-windows` ;
  - Alexis relance son Atlas une fois, qui crée sa clé, puis vérifie la fenêtre et « Ouvrir » avec une vraie question ;
  - je refais la sauvegarde de `data/` et je reconstruis l'installeur depuis `main` ;
  - je recopie dans `C:\Users\Public\AtlasTest` l'installeur, le diagnostic, `mesure_comptes.bat` et `.ps1`, `relever_journaux.bat` et les fiches.
- **P1 :** l'étape 0 sur `AtlasTest`, ta session ouverte. Puis le parcours, avec les critères d'envoi. Puis la lecture des relevés et des mesures, avec un test rouge d'abord pour chaque écart.
- **P2, à décider par le superviseur :**
  - retirer le démarrage automatique d'Ollama quand Atlas l'a installé lui-même (§7, point 6) ;
  - vérifier le processus à l'autre bout de la connexion (§7, point 9).
- **Ensuite seulement :** IF6, l'envoi, quand tous les critères sont mesurés.
