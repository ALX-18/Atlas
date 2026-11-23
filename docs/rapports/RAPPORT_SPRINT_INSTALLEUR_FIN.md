# RAPPORT SPRINT — INSTALLEUR, FIN : la fenêtre d'Ollama, la sécurité de la veille, la préparation du parcours chez le proche

**Développeur :** CHAT6 (Claude Opus, Claude Code Windows)
**Brief :** `docs/briefs/BRIEF_SPRINT_INSTALLEUR_FIN.md` (IF0 à IF5 ; §5 du 11/11 au soir : IF3 bis et IF6)
**Branche :** `sprint-installeur-fin`, partie de `main` après la fusion de la PR 16 (`5b1253b`)
**Dates :** 10 novembre 2026 en soirée, 11 novembre (vérification demandée par le superviseur), et 23 novembre (IF3 bis : préparation du compte neuf ; IF6 : préparation de l'envoi). Branche du 23/11 : `sprint-installeur-compte-neuf`, partie de `main` (`d706b67`)

> Ce rapport couvre ce qui se fait sur le PC d'Alexis :
> - IF0, la base ;
> - IF1, la fenêtre d'Ollama ;
> - IF2, les deux points de sécurité de la veille ;
> - la préparation d'IF3 : la fiche, le relevé des journaux, l'installeur à construire depuis `main`.
>
> **Le parcours chez le proche (IF3) et les vérifications à l'écran (IF4) ne sont pas encore joués.** Ils sont marqués **À FAIRE** partout, et ce rapport sera complété au retour, avec les journaux. Rien n'est extrapolé.

---

## Tableau de tête

| Ce que le brief met en tête | Résultat |
|---|---|
| Le parcours chez le proche : palier, temps, taille, test de capacité | **À FAIRE** (sur place, par Alexis). La fiche et le relevé anonymisé des journaux sont prêts (§4). |
| Atlas répond et retient | **À FAIRE** (étape 5 de la fiche) |
| Réinstallation et désinstallation « garder » | **À FAIRE** (étapes 6 et 7 de la fiche) |
| IF2 — CVE-2026-45833 (ChromaDB) | **Version concernée, chemin d'attaque absent dans Atlas.** La 1.5.1 est dans la plage touchée (`>= 0.4.17, <= 1.5.9`), sans version corrigée. L'attaque passe par l'API HTTP d'un serveur Chroma. Atlas n'utilise que le client intégré : pas de serveur, pas de port, aucune configuration de collection venue d'ailleurs. Un test le verrouille (§6.2). |
| IF2 — fuite mémoire et de consignes sur Ollama | **Pas concerné, pour les deux fuites recensées en 2026 par le NVD** : CVE-2026-7482, corrigée en 0.17.1, et CVE-2026-5757, touchant jusqu'à 0.13.5. Ollama 0.40.6 est postérieure aux deux. **Non vérifiable** que ce soit bien la faille de l'article de la veille : l'article refuse la lecture automatique (HTTP 403). |
| Le mode jeu sur un vrai jeu | **À FAIRE** (IF4, avec Alexis) |
| 23/11 — IF3 bis, avant : où l'installeur écrit sur un compte neuf, et le compte d'Alexis est-il touché ? | **Non touché, à une condition : Alexis complètement déconnecté.** Atlas, Ollama et le modèle vont dans le profil d'`AtlasTest`. Tesseract est déjà installé pour toute la machine et gardé, rien n'est écrit dans `Program Files`. Mais `127.0.0.1` est commun aux sessions : une session d'Alexis restée ouverte prêterait son Ollama, et son Atlas, à `AtlasTest` (§6.5). Sauvegarde de `data/` faite et vérifiée par empreintes. |
| 23/11 — Installeur construit depuis `main` | **Fait** : `d706b67`, `AtlasSetup.exe` 15,8 Mo, SHA-256 `b4186856c191dac47fc49cd25498d81ff1e7c16478a0f9c2e19f083a94f5aa4e`. Paquet vérifié : aucune faute, mails en `simulation`, prénom vide, relevé corrigé du 11/11 identique à `main`. |
| Vérification du superviseur (11/11) : des noms ou chemins de fichiers du proche dans `atlas_serveur.log` ? | **Oui.** Pas par l'index des fichiers, qui n'en écrit aucun au niveau INFO, mais par les arguments des outils, les cibles des confirmations, les titres de fenêtre, les exceptions, les transcriptions et le souvenir recopié par la mémoire. **Le relevé les retire désormais**, avec 25 tests rouges d'abord. Essayé sur le vrai journal d'un Atlas d'essai : aucune phrase dite, aucun souvenir, aucun chemin personnel restant (§6.3). |

---

## 1. Résumé exécutif

- **Statut : PARTIELLEMENT VALIDÉ.** IF0, IF1 et IF2 sont faits, et la préparation d'IF3 est prête. Le parcours chez le proche (IF3) et les vérifications à l'écran (IF4) attendent Alexis.
- **IF1 : la fenêtre d'Ollama est fermée.** L'installeur ferme l'application qu'il vient d'installer, chaque fois qu'elle apparaît, jusqu'à la fin de l'installation. Le serveur tourne sans fenêtre, sur 127.0.0.1. Au démarrage, le lanceur d'Atlas démarre Ollama sans fenêtre s'il ne tourne pas, et le note dans son journal. **Rien n'est changé chez Ollama.** Son installeur ne pose aucun démarrage avec Windows. C'est l'application qui pose, à son premier lancement, un raccourci dans le dossier Démarrage, et ce raccourci la relance **cachée** (code d'Ollama 0.40.6, §4) : il n'y a rien à retirer.
- **IF2 :** voir le tableau de tête. **Le point ChromaDB est à trancher par le superviseur** avant la démo : la version est touchée, mais le chemin d'attaque n'existe pas dans l'usage d'Atlas.
- **IF3 :** une fiche d'une page pour Alexis, et un relevé des journaux qui remplace la session Windows, le nom de l'ordinateur, le prénom et les adresses. Essayé sur les vrais journaux de la Sandbox : 2 400 remplacements, aucun nom de session restant.
- **23/11 (§5 du brief : compte neuf, puis envoi à distance) :**
  - **IF3 bis, avant : fait.** Où l'installeur écrit sur `AtlasTest` est relevé, et la confirmation est écrite : le compte d'Alexis n'est pas touché, **s'il est complètement déconnecté**. Sa mémoire est sauvegardée, et `data/` est copié et vérifié fichier par fichier.
  - **L'installeur est construit depuis `main`.**
  - **Un écart corrigé :** l'installeur ne disait pas que Tesseract était déjà là.
  - **IF6 est préparé, rien n'est envoyé.**
  - **Le parcours sur `AtlasTest` attend Alexis.**
- **Tests :** `pytest tests/ -q` : **1 669 réussis** avec Ollama (0 ignoré) ; **1 666 réussis + 3 ignorés justifiés** sans lui ; code 0 les deux fois. **17 tests nouveaux.** Le 11/11, après la vérification du superviseur : **1 694** avec Ollama, **1 691 + 3 ignorés justifiés** sans, code 0, avec **25 tests nouveaux**.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| IF0 — `sprint-installeur-sandbox` fusionnée, suite verte, nouvelle branche | PR 16 fusionnée par Alexis (`a97c418`). `sprint-installeur-fin` part de `origin/main` (`5b1253b`). Suite sur `main` avec Ollama : **1 652 réussis, code 0**. | PASS |
| IF1 — Relever ce que fait l'installeur officiel d'Ollama | Lu dans `app/ollama.iss` et `app/cmd/app/*.go`, version v0.40.6 (§4). Vu aussi sur le PC d'Alexis : `Startup\Ollama.lnk` lance `ollama app.exe`, et il n'y a rien dans les clés `Run`. | PASS |
| IF1 — L'installeur ferme l'application Ollama ; serveur sur 127.0.0.1 seulement | `GardeAppOllama` ; `verifier_ollama_local` (déjà là) ; 4 tests | PASS (tests) ; **à voir chez le proche** |
| IF1 — Au démarrage d'Atlas, serveur lancé sans fenêtre s'il ne tourne pas, et dit dans le journal | `lancer.assurer_ollama` ; 5 tests ; chargement par son chemin vérifié avec le vrai Python embarqué | PASS (tests) ; **à voir chez le proche** |
| IF1 — Démarrage avec Windows qui ouvrirait la fenêtre : proposer avant de retirer | L'installeur d'Ollama n'en pose pas. Le raccourci que pose l'application la relance cachée. Rien n'est retiré, donc rien n'est proposé. | PASS (lu dans le code ; **pas observé** sur une session neuve) |
| IF1 — Test rouge d'abord ; le guide testeur ne parle plus de la fenêtre | 9 tests rouges vus avant le code. Le guide n'en parlait déjà pas : un test le garde. | PASS |
| IF2 — CVE-2026-45833 (ChromaDB) | Version dans la plage touchée ; mode intégré sans le chemin d'attaque ; sources §6.2 ; test de garde | PASS (tranché : **version concernée, non exposée**) |
| IF2 — Fuite mémoire et de consignes sur Ollama | Les deux fuites de 2026 au NVD sont corrigées avant 0.40.6 ; l'article de la veille n'a pas pu être lu | PARTIEL (pas concerné pour ce qui est identifiable ; l'article est **non vérifiable**) |
| IF3 — Installeur construit depuis `main` après IF1, suite verte | 23/11 : construit depuis `main` (`d706b67`), paquet vérifié, SHA-256 `b4186856…aa4e` (§6.5) | PASS |
| IF3 bis — Avant : relever où l'installeur écrit, confirmer par écrit que l'installation et les données d'Alexis ne sont pas touchées ; dans le doute, sauvegarde de `data/` vérifiée par les données | Relevé et confirmation écrite dans `docs/beta/FICHE_COMPTE_NEUF.md` et au §6.5, avec la condition de la déconnexion complète. Sauvegarde de la mémoire, et copie complète de `data/` vérifiée fichier par fichier. | PASS |
| IF3 bis — On attend Tesseract « déjà là » : reconnu, rien d'écrasé, **et dit** | Reconnu et gardé, oui. **Mais l'installeur ne le disait pas** : une clé `tesseract_deja_la` dans son journal, rien à l'écran. Corrigé sur la branche, avec 5 tests (4 vus rouges d'abord, un garde-fou vert dès le départ) : une ligne au journal et une phrase dans le message de fin. **Pas encore dans l'installeur construit depuis `main`.** | PASS (code et tests) ; installeur **à reconstruire** après fusion |
| IF3 bis — Pendant et après, sur `AtlasTest` | **À FAIRE** (Alexis) | FAIL (pas encore) |
| IF6 — Partage Drive, empreinte par un autre canal, guide du testeur seul, retour des relevés, aide à distance | Préparé : `docs/beta/GUIDE_INSTALLATION_A_DISTANCE.md` (pour le testeur) et `docs/beta/ENVOI_TESTEURS.md` (pour Alexis). Dossier `build/installeur/cle_usb` assemblé. **Aucun lien envoyé** : la règle l'interdit avant le passage sur `AtlasTest`. | PARTIEL (prêt, pas envoyé) |
| IF3 — Fiche d'une page : quoi faire, quoi noter, quels journaux copier, que faire en cas d'échec | `docs/beta/FICHE_PARCOURS_PROCHE.md` ; relevé `installeur/relever_journaux.bat` et `.py` | PASS |
| IF3 — Parcours sur place, étapes 1 à 9 | **À FAIRE** (Alexis, sur place) | FAIL (pas encore) |
| IF3 — Au retour : lire les journaux, corriger avec un test rouge, reconstruire | **À FAIRE** | FAIL (pas encore) |
| IF4 — Résultat d'une confirmation dans la fenêtre de bureau | **À FAIRE** (avec Alexis) | FAIL (pas encore) |
| IF4 — Mode jeu sur un vrai jeu, sans Parsec | **À FAIRE** (avec Alexis) | FAIL (pas encore) |
| Décision du 11/11 — `atlas_serveur.log` contient-il des noms ou chemins de fichiers du proche ? Si oui, le relevé les retire (test rouge d'abord) avant de construire l'installeur | Oui : relevé corrigé (§4, §6.3) ; installeur à reconstruire depuis `main` après la fusion de `sprint-installeur-fin-releve` | PASS (relevé) ; installeur **à reconstruire** |
| IF5 — Rapport, pytest code 0 avec et sans Ollama, règle C3 et garde BM0 | Ce document ; §5 ; §6.4 | PARTIEL (rapport à compléter au retour) |

---

## 3. Architecture projet mise à jour

```
installeur/
  etapes.py                 (garde de l'application Ollama ; serveur sans fenêtre ; arrêt de la garde à la fin ;
                             23/11 : Ollama et Tesseract déjà là, dits dans le journal et le message de fin)
  lancer.py                 (Ollama assuré sans fenêtre avant Atlas ; journal du lanceur)
  relever_journaux.py       ← NOUVEAU (relevé anonymisé des journaux, IF3)
  relever_journaux.bat      ← NOUVEAU (le relevé lancé depuis la clé USB, avec le Python d'Atlas)
docs/beta/
  FICHE_PARCOURS_PROCHE.md  ← NOUVEAU (la fiche d'une page)
  FICHE_COMPTE_NEUF.md      ← NOUVEAU 23/11 (IF3 bis : où l'installeur écrit, avant, pendant, après)
  GUIDE_INSTALLATION_A_DISTANCE.md  ← NOUVEAU 23/11 (IF6 : le testeur seul, du lien au relevé renvoyé)
  ENVOI_TESTEURS.md         ← NOUVEAU 23/11 (IF6 : le partage Drive, l'empreinte, le retour des relevés)
docs/rapports/
  RAPPORT_SPRINT_INSTALLEUR_FIN.md  ← NOUVEAU (ce document)
tests/
  test_installeur.py        (IF1 : 11 tests, IF2 : 1, IF3 : 5)
```

---

## 4. Détail des implémentations

### Ce que fait l'installeur officiel d'Ollama (relevé IF1)

Lu dans le dépôt officiel, à l'étiquette `v0.40.6` :

- `app/ollama.iss`, section `[Run]` :
  - une seule entrée : `"{app}\ollama app.exe"`, lancé par `cmd` ;
  - drapeaux `postinstall nowait runhidden`, **sans `skipifsilent`** : l'application est lancée même en installation silencieuse ;
  - `runhidden` ne cache que la fenêtre de `cmd`, pas celle de l'application. C'est la fenêtre vue dans la Sandbox : accueil, puis invitation à se connecter à un compte.
- `[Icons]` : le menu Démarrer, et `{app}\lib\Ollama.lnk`. **Aucune entrée `{userstartup}`.** Pas de section `[Tasks]`, aucune clé `Run` dans `[Registry]`.
- `[UninstallDelete]` retire `{userstartup}\Ollama.lnk`.
- `app/cmd/app/app_windows.go`, `createLoginShortcut()` :
  - au **premier** lancement, l'application copie `lib\Ollama.lnk` dans le dossier Démarrage ;
  - elle ne le refait plus ensuite, « pour respecter la suppression du lien par l'utilisateur ».
- `osRun()` : lancée par un raccourci dont le titre contient `Startup`, l'application démarre **cachée** (`startHidden`). `runInitialWindowsUI()` n'ouvre alors aucune fenêtre.
- **Conclusion :**
  - le démarrage avec Windows existe, mais il n'ouvre pas de fenêtre ;
  - il est posé par l'application elle-même, pas par l'installeur ;
  - on n'y touche pas.
- **Limite :** c'est lu dans le code, pas observé sur une session Windows neuve. Chez le proche, l'étape 2 de la fiche demande de noter toute fenêtre d'Ollama, et le relevé rapporte `app.log` d'Ollama.
- **Vu sur le PC d'Alexis :** `Startup\Ollama.lnk` (créé le 24/02/2026) lance `ollama app.exe` sans argument, et il n'y a rien dans `HKCU`/`HKLM\...\Run`.

### `installeur/etapes.py`

- **`APP_OLLAMA`, `apps_ollama()`** : les processus `ollama app.exe`, par psutil.
- **`demarrer_ollama_sans_fenetre(exe, journal)`** :
  - c'est celui du lanceur, chargé **par son chemin** (`importlib.util.spec_from_file_location`) ;
  - le `python312._pth` du Python embarqué ne met que la racine d'Atlas sur le chemin, donc `import lancer` y échoue. C'est vérifié avec le vrai Python embarqué construit.
- **`GardeAppOllama`** :
  - `balayer()` ferme chaque `ollama app.exe` présent et le note au journal (« application Ollama fermée (ouverte par son installeur) : son serveur tourne sans fenêtre ») ;
  - si le serveur ne répond plus après la fermeture, `balayer()` le relance sans fenêtre et le dit ;
  - `attendre_fermeture(s)` attend la fenêtre. Elle apparaît quand le serveur répond : dans la Sandbox, environ 2 min 45 après le lancement de l'installeur d'Ollama ;
  - `demarrer()` lance un fil qui balaie chaque seconde. `arreter()` l'arrête et balaie une dernière fois.
- **`etape_ollama`** :
  - Ollama absent : après son installeur, le serveur est lancé sans fenêtre **avant** celui de l'application (s'il ne répond pas encore). La garde démarre ; on attend le serveur, puis la fenêtre (90 s au plus), puis de nouveau le serveur ; enfin on vérifie `127.0.0.1`. La mesure `application_ollama_fermee` compte les fermetures.
  - Ollama déjà là : **son application n'est jamais fermée** (elle est à la personne). S'il ne tourne pas, son serveur est lancé sans fenêtre.
- **`Deroule.lancer`** : `arreter_garde_app_ollama()` dans un `finally`. La garde s'arrête à la fin de l'installation, réussie ou non.

### `installeur/lancer.py`

- **`assurer_ollama()`**, appelé par `main` avant de démarrer Atlas, rend l'un de ces trois résultats :
  - « tourne » : Ollama écoute sur 127.0.0.1:11434, rien n'est fait ;
  - « lance » : le serveur est démarré sans fenêtre, et le journal d'Atlas dit « Ollama ne tournait pas : son serveur est lancé sans fenêtre, sur 127.0.0.1:11434 » ;
  - « absent » : le journal dit « Ollama introuvable… ».
- **`demarrer_ollama_sans_fenetre`** :
  - lance `ollama serve` avec `CREATE_NO_WINDOW` ;
  - force `OLLAMA_HOST=127.0.0.1:11434` pour ce seul processus, quel que soit l'environnement ;
  - envoie la sortie vers `data/logs/ollama_serveur.log`.
- **`noter`** : les lignes `[lanceur]` dans `data/logs/atlas_serveur.log`.
- Placé dans le lanceur et **pas dans `main.py`** : chaque test qui démarre Atlas lancerait sinon Ollama, y compris pendant la suite « sans Ollama ».

### `installeur/relever_journaux.py` et `relever_journaux.bat` (IF3)

- **Ce qui est copié**, dans `releves\releve_<date>` sur la clé :
  - `installeur/installation.log`, `etat.json`, `ollama_serveur.log` ;
  - `data/logs/*.log` ;
  - le journal d'Inno Setup qui parle d'Atlas (`%TEMP%\Setup Log …`) ;
  - `%LOCALAPPDATA%\Ollama\server*.log` et `app*.log` ;
  - le diagnostic `precheck_atlas.ps1 -Sortie`.
- **Ce qui n'est jamais copié :** la mémoire, les actions, les réglages, les secrets. De `settings.json`, seules deux clés sont lues : `utilisateur.prenom` (pour le remplacer) et `mail.envoi`, recopié dans `RELEVE.txt` pour l'étape 9.
- **`anonymiser`** remplace :
  - les adresses mail, par `<adresse>` ;
  - la session Windows et le dossier du profil, par `<session>` ;
  - le nom de l'ordinateur, par `<ordinateur>` ;
  - le prénom, par `<prénom>`.

  Le remplacement ne touche que des mots entiers, en ignorant la casse. Une valeur de moins de deux lettres n'est pas remplacée.
- **`RELEVE.txt`** : ce qui a été pris ou manquait, et le nombre de remplacements. Il ne redit jamais les valeurs remplacées.
- **`nettoyer_contenu(texte, racines)`** a été ajouté après la décision du superviseur du 11/11. Il passe avant `anonymiser`, sur chaque fichier copié, et applique trois règles dans cet ordre :
  1. **Liste blanche des modules.** Une ligne au format d'Atlas (`date [module] NIVEAU — message`) ne garde son message que si le module est technique : `atlas`, `atlas.ollama`, `atlas.modele_local`, `atlas.memory`, `atlas.memory_core`, `atlas.voice`, `atlas.systray`, `atlas.diagnostics`, `atlas.donnees_reelles`, `atlas.file_indexer`. Pour tout autre module, y compris un module ajouté plus tard, il reste `date [module] NIVEAU — <contenu retiré>`.
     - Même dans un module technique, ce qui suit un début de message « dit » est retiré : `[VOIX] Transcription (…)`, `[VOIX] «`, `Phrase dite`, `Souvenir sauvegardé`, `Ingestion document`, `[AUTOMATION]`…
  2. **Chemins.** Tout chemin hors des dossiers techniques devient `<chemin>`. Les dossiers techniques sont : Atlas, Ollama, `.ollama`, le cache de Hugging Face, Program Files, Windows, et le dossier temporaire de l'installeur.
     - Sous Atlas, `data\` n'est gardé que pour `logs`, `chromadb`, `voices` et `workflows`. Les documents et les captures portent des noms qui appartiennent à la personne.
  3. **Noms, adresses, recherches.**
     - Un nom de document seul devient `<fichier>`, sauf quelques noms techniques (`requirements-*.txt`, `precheck.txt`…).
     - Une adresse web non technique devient `<url>`. Restent lisibles : 127.0.0.1, GitHub, Ollama, Hugging Face, PyPI, python.org, Microsoft.
     - La recherche d'une requête HTTP (`?q=…`) devient `<retiré>`.
- **Le `.bat`** :
  - il est en ASCII, parce que `cmd` le lit dans la page de code de la console ;
  - il lance le Python d'Atlas (`%LOCALAPPDATA%\Programs\Atlas\python\python.exe`) ;
  - si Atlas n'est pas installé, il le dit.

---

## 5. Résultats des tests

**Commande exacte :**

```
.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider        # avec Ollama 0.40.6
.venv/Scripts/python.exe -m pytest tests/ -q -p no:cacheprovider -rs    # Ollama arrêté (Stop-Process), puis relancé
```

| Passage | Résultat | Code |
|---|---|---|
| `main` avant le sprint (IF0), avec Ollama | 1 652 réussis, 0 ignoré (11 min 20) | 0 |
| Branche, avec Ollama | **1 669 réussis, 0 ignoré** (10 min 00) | 0 |
| Branche, sans Ollama | **1 666 réussis, 3 ignorés justifiés** (10 min 25) | 0 |

**Les 3 tests ignorés sans Ollama** sont les mêmes qu'aux sprints précédents :
- `test_honesty_gbis.py:252` (Ollama injoignable) ;
- `test_sprint_kimi_understanding_v51.py:47` (lit les modèles installés) ;
- `test_vision_parsers.py:276` (sonde de port fermé).

Compteur du dépôt : « 3 justifié(s), 0 fautif(s) ».

**Les 17 nouveaux tests**, dans `tests/test_installeur.py`, tous vus rouges avant le code sauf deux (voir après la liste) :

- **IF1 :**
  - `test_if1_l_installeur_ferme_l_application_ollama_qu_il_vient_d_installer`
  - `test_if1_un_ollama_deja_installe_n_est_pas_touche`
  - `test_if1_si_fermer_l_application_emporte_le_serveur_il_est_relance_sans_fenetre`
  - `test_if1_la_garde_est_arretee_a_la_fin_de_l_installation_meme_en_echec`
  - `test_if1_le_serveur_ollama_demarre_sans_fenetre_et_sur_127_0_0_1`
  - `test_if1_au_demarrage_atlas_lance_ollama_sans_fenetre_s_il_ne_tourne_pas` ×3 (tourne / lance / absent)
  - `test_if1_le_lanceur_s_assure_d_ollama_avant_de_demarrer_atlas`
  - `test_if1_le_guide_testeur_ne_parle_pas_de_la_fenetre_d_ollama` (garde-fou, vert dès le départ)
  - `test_if1_l_installeur_trouve_le_lanceur_par_son_chemin`
- **IF2 :**
  - `test_if2_atlas_n_ouvre_aucun_chemin_vers_cve_2026_45833` (garde-fou, vert sur le code actuel)
- **IF3 :**
  - `test_if3_l_anonymisation_retire_session_ordinateur_prenom_et_adresses`
  - `test_if3_un_prenom_trop_court_ou_absent_ne_ravage_pas_le_journal`
  - `test_if3_le_releve_copie_les_journaux_et_rien_d_autre`
  - `test_if3_le_releve_sans_atlas_installe_garde_ce_qui_reste`
  - `test_if3_le_lanceur_du_releve_prend_le_python_d_atlas`

Les deux garde-fous verts dès le départ sont marqués dans la liste. S'y ajoute l'assertion « mails : simulation » (§7, point 7).

`tests/test_installeur.py` seul : **135 réussis**.

**11/11 : la vérification du superviseur (§6.3).** 25 nouveaux tests, **tous vus rouges** avant le code :
- `test_if3_le_releve_retire_noms_et_chemins_de_fichiers` ×9 : outil exécuté, titre de fenêtre, confirmation, transcription, phrase entendue pendant une confirmation, exception, document d'Atlas, nom de fichier et adresse web, requête HTTP ;
- `test_if3_le_releve_garde_ce_qui_sert_au_diagnostic` ×9 ;
- `test_if3_un_module_inconnu_ne_dit_que_son_heure_et_son_niveau` ;
- `test_if3_le_releve_nettoie_les_journaux_d_atlas_pour_de_vrai` ;
- `test_if3_les_modeles_et_les_voix_d_atlas_restent_lisibles` ×3, trouvé par l'essai sur les journaux de la Sandbox ;
- `test_if3_la_memoire_ne_recopie_pas_ses_souvenirs_dans_le_releve` ×2, trouvé par l'essai sur un vrai journal d'Atlas.

`tests/test_installeur.py` seul : **160 réussis**.

| Passage du 11/11 (branche `sprint-installeur-fin-releve`) | Résultat | Code |
|---|---|---|
| Avec Ollama | **1 694 réussis, 0 ignoré** (10 min 28) | 0 |
| Sans Ollama | **1 691 réussis, 3 ignorés justifiés**, les mêmes trois (10 min 18) | 0 |

**Non-régression :** les autres suites du dépôt passent toutes dans les deux passages complets ci-dessus, dont le recensement des écrivains de `data/` (CM0), toujours vert.

**23/11 : IF3 bis, Tesseract « déjà là » dit.** 5 nouveaux tests :
- `test_if3bis_tesseract_deja_la_est_garde_sans_rien_telecharger_et_le_journal_le_dit` : vu rouge, il n'y avait pas de ligne au journal ;
- `test_if3bis_la_fin_dit_ce_qui_etait_deja_la_et_garde` ×4 :
  - Tesseract seul, Ollama seul, les deux : les trois cas vus rouges ;
  - aucun des deux : garde-fou, vert dès le départ.

`tests/test_installeur.py` seul : **165 réussis**.

| Passage du 23/11 (branche `sprint-installeur-compte-neuf`) | Résultat | Code |
|---|---|---|
| Avec Ollama, 1er passage | **1 698 réussis, 1 échec** : `test_checkup.py::test_ck4_une_sonde_qui_ment_fait_echouer_la_suite` (10 min 32) | **1** |
| Avec Ollama, 2e passage | **1 699 réussis, 0 ignoré** (10 min 01) | 0 |
| Sans Ollama | **1 696 réussis, 3 ignorés justifiés**, les mêmes trois (10 min 32) ; Ollama relancé ensuite (0.40.6 répond) | 0 |

**L'échec du 1er passage :**
- Le test lance un pytest à part, dans un dossier temporaire. Ce pytest s'est arrêté **au chargement** (« 1 error during collection »), sur un message tronqué par l'assertion : « …st introuvabl… ».
- C'est probablement un « Le fichier spécifié est introuvable » ou « Le chemin d'accès spécifié est introuvable » de Windows. **La cause n'est pas établie.**
- Le test passe seul (3 sur 3 pour CK4), puis dans le 2e passage complet.
- Le changement du jour, l'installeur et ses tests, ne touche ni `tests/conftest.py` ni `test_checkup.py`.
- Je ne l'ai **pas** relancé jusqu'à passer : un seul nouveau passage complet, qui est vert.
- **Instable, à surveiller** (§7, point 13).

---

## 6. Comportement observé en scénarios réels

| ID | Commande / action | Résultat attendu | Résultat observé | Statut |
|---|---|---|---|---|
| R1 | Raccourcis de démarrage d'Ollama sur le PC d'Alexis (lecture seule) | ce que pose l'installation d'Ollama | `Startup\Ollama.lnk` vers `ollama app.exe` sans argument ; aucune clé `Run` | PASS |
| R2 | Le vrai Python embarqué (`build/installeur/paquet/python`) charge le lanceur | `import lancer` impossible, chargement par le chemin possible | « import lancer : impossible (attendu avec le ._pth) », chargement par le chemin réussi | PASS |
| R3 | `demarrer_ollama_sans_fenetre` lancé pour de vrai alors qu'Ollama tournait déjà (**involontaire**, §7) | le serveur demandé sur 127.0.0.1 | journal : « listen tcp 127.0.0.1:11434: bind: Only one usage… » : le serveur visait bien 127.0.0.1, port déjà pris, il s'est arrêté seul ; l'Ollama d'Alexis intact (mêmes processus, 0.40.6) | PASS (voir §7) |
| R4 | Relevé sur les vrais journaux de l'essai Sandbox 8 (session `WDAGUtilityAccount`) | rien du nom de session ; journaux complets | 4 fichiers pris (installation 44 Ko, Inno 803 Ko, état, serveur Ollama), 2 400 remplacements, **0** nom de session restant | PASS |
| R5 | Le parcours chez le proche (fiche, étapes 1 à 9) | — | **À FAIRE** | — |
| R6 | IF4 : confirmation à l'écran, mode jeu sur un vrai jeu | — | **À FAIRE** | — |

### 6.2 IF2 — les deux points de sécurité de la veille

**CVE-2026-45833 (ChromaDB)**

- **Source officielle :** avis GitHub **GHSA-36p7-vc44-83pf** (« GitHub Reviewed », publié le 12/06/2026, mis à jour le 24/08/2026).
  - Injection de code, CVSS 4.0 : 9,4.
  - Paquet `chromadb` (pip). Versions touchées **`>= 0.4.17, <= 1.5.9`**. Versions corrigées : **aucune**.
  - L'attaque : un attaquant **authentifié**, avec la permission `UPDATE_COLLECTION`, envoie au point d'entrée HTTP `/api/v2/tenants/…/collections/{collection_id}` un dépôt de modèle piégé avec `trust_remote_code` à vrai.
  - L'onglet « Security » du dépôt Chroma ne publie aucun avis. Les pages NVD et CVE.org se sont affichées vides à la lecture automatique.
- **Lu dans chromadb 1.5.1 installé :**
  - la configuration d'une collection reconstruit sa fonction d'embedding (`build_from_config`) ;
  - `SentenceTransformerEmbeddingFunction` passe ses `kwargs` tels quels à `SentenceTransformer(...)`. C'est par là que `trust_remote_code` arrive.
- **Dans Atlas :**
  - `chromadb.PersistentClient(path=…)` seulement : aucun serveur Chroma, aucun port ;
  - les collections sont ouvertes par `get_or_create_collection(name, metadata)`, sans `configuration` ni `embedding_function` ; les vecteurs e5 sont fournis par Atlas ;
  - aucun appel à `modify`.
  - Pour poser une configuration piégée, il faudrait déjà pouvoir écrire dans `data/chromadb` : on aurait alors déjà la main sur la session.
  - Sur le PC d'Alexis, Docker est éteint et rien n'écoute sur 8000/8001.
- **Conclusion : version concernée, chemin d'attaque absent dans l'usage d'Atlas.**
  - `test_if2_atlas_n_ouvre_aucun_chemin_vers_cve_2026_45833` échoue si un client HTTP Chroma, `chroma run`, `.modify(`, `configuration=`, `embedding_function=` ou `trust_remote_code` apparaît dans le code d'Atlas.
  - À revoir quand une version corrigée paraîtra.

**Fuite mémoire et de consignes sur Ollama**

- L'article cité par la veille n'a pas pu être lu (HTTP 403). La faille qu'il décrit n'est donc **pas identifiée avec certitude**.
- **Sources officielles (NVD, API REST) :**
  - **CVE-2026-7482** :
    - lecture hors limites dans le chargeur GGUF ;
    - la mémoire fuitée « peut inclure des variables d'environnement, des clés d'API, des consignes système » ;
    - touche « Ollama before 0.17.1 » ; corrigée en 0.17.1 (commit et PR cités par le NVD) ;
    - attaque par `/api/create` avec un GGUF piégé.
  - **CVE-2026-5757** :
    - lecture de la mémoire du serveur par le moteur de quantification ;
    - versions touchées : jusqu'à 0.13.5.
- `v0.40.6` existe dans les versions publiées d'Ollama : elle est postérieure aux deux.
- **Conclusion : pas concerné pour les deux fuites identifiables. Non vérifiable que ce soit la faille de l'article.**
- Chez le proche, Ollama n'écoute que sur 127.0.0.1, vérifié par l'installeur. N'y sont tirés que les modèles épinglés, dont l'empreinte est vérifiée.

### 6.3 Vérification du superviseur (11/11) : des noms ou chemins de fichiers dans `atlas_serveur.log` ?

**Réponse : oui, avant cette correction.**

**Ce que j'ai fait :**
- Relevé dans le code d'Atlas : 99 appels de journal peuvent porter un chemin, un nom ou un titre.
- **L'index des fichiers n'écrit aucun nom au niveau INFO**, seulement « démarré » et « arrêté ». Ses messages d'erreur peuvent toutefois citer un chemin.
- Les autres sources de noms et de contenu :
  - `Tool '…' executed: {'path': …}` (atlas.intent_engine) ;
  - les cibles des confirmations ;
  - les titres de fenêtre (atlas.grounding, atlas.window_controller) : nom du document ou de la page ;
  - les messages d'exception ;
  - les transcriptions (atlas.voice) ;
  - **le souvenir recopié** : `Souvenir sauvegardé [user_fact] : …` et `Ingestion document '…'` (atlas.memory).

**Essai réel :**
- Un Atlas d'essai, lancé depuis le dépôt sur des **données entièrement vides** : mémoire neuve, index, journal des actions, habitudes, apprentissage et rappels dans un dossier jetable. **Rien n'a été copié de la mémoire d'Alexis.**
- Il a reçu deux messages, « Quelle heure est-il ? » et la phrase de la fiche « Retiens que la clé de la cabane est sous le pot bleu. », puis il a été arrêté proprement.
- Son vrai journal (70 lignes, 21 modules) est passé au nettoyage. Le brut a été effacé, et seul le nettoyé a été lu.

| Essai | Phrase dite ou souvenir dans le nettoyé | Chemins hors dossiers techniques restants | Retraits |
|---|---|---|---|
| 1 (relevé de la veille, sans `Souvenir sauvegardé`) | **« cabane », « pot bleu » encore là**, par `atlas.memory` | 0 | 29 |
| 2 (après la correction, test rouge d'abord) | **aucun** | 0 | 30 |

**Lignes gardées par le nettoyage, qui suffisent au diagnostic :**
- le démarrage et le modèle ;
- Tesseract (version, français) ;
- l'état de la mémoire ;
- la voix (GPU ou processeur, préchauffage en 2,6 s) ;
- l'échec ou la réussite du préchauffage d'Ollama ;
- l'index démarré ou arrêté ;
- les requêtes HTTP sans leur contenu ;
- l'arrêt propre.

**Sur les journaux de l'essai Sandbox 8**, les voix (`data\voices`) et le modèle de transcription (cache de Hugging Face) étaient masqués à tort. C'est corrigé, avec un test rouge d'abord.

### 6.4 Données réelles (règle C3, garde BM0)

- **`data/` (règle C3) :** **aucun fichier modifié** par le sprint. Les 198 fichiers ont été relevés après chacune des deux suites complètes, et aucun n'est plus récent que le début du sprint (17:30). La mémoire réelle n'a été ni ouverte ni écrite, donc il n'y avait rien à retirer et aucune sauvegarde n'était nécessaire.
- **Garde BM0 :**
  - aucun nouvel écrivain de `data/` dans le code d'Atlas ;
  - le lanceur (`installeur/lancer.py`) écrivait déjà `data/logs/atlas_serveur.log`. Il y ajoute ses lignes `[lanceur]` et `data/logs/ollama_serveur.log`. C'est Atlas lui-même, installé, qui démarre : rien ne tourne sur les vraies données pendant les tests, où `noter` et `demarrer` sont remplacés ;
  - le relevé (`relever_journaux.py`) **lit** des journaux et deux clés de réglages, et **n'écrit que sur la clé USB**.
- **Les essais du relevé** ont tourné sur des copies des journaux de la Sandbox, dans le dossier jetable de la session. **Jamais sur les journaux ni les réglages d'Alexis.**
- **Les deux Atlas d'essai du 11/11 (§6.3) :**
  - les six redirections `ATLAS_*` pointaient vers un dossier jetable et vide, donc le garde BM0 a interdit les données réelles (« Atlas d'essai (…) : données réelles interdites ») ;
  - **seul `data/atlas.lock` a été réécrit**. C'est le verrou qui empêche deux Atlas de tourner ensemble : il est pris au démarrage et libéré à l'arrêt ;
  - aucun autre fichier de `data/` n'est plus récent que le repère posé juste avant les essais ;
  - le journal de développement `logs/atlas.log`, à la racine du dépôt et hors de `data/`, a reçu les **112 lignes** des deux essais, comme pour les rejeux précédents ;
  - le dossier jetable a été effacé, et le journal brut aussi.
- **Ollama d'Alexis :**
  - arrêté puis relancé pour chaque suite « sans Ollama », comme à chaque sprint (0.40.6 répond) ;
  - un `ollama serve` lancé par erreur s'est arrêté seul (R3, §7) ;
  - **le 11/11 au matin, il était arrêté sans que je l'aie arrêté.** Le premier essai l'a montré (« Préchauffage du modèle impossible »). Son journal s'arrête au 10/11 à 18:24, quand je l'avais relancé, sans ligne d'arrêt. Le PC n'a pas redémarré et `ollama.exe` n'a pas changé. La cause n'est pas établie. Je l'ai relancé (0.40.6 répond).
- **Configuration :** `config/settings.json` local d'Alexis en `"reel"` (son choix), jamais commité ; le dépôt reste en `"simulation"`.
- **23/11 :**
  - **aucun fichier de `data/` n'a changé.** Après les trois passages complets, les 198 fichiers ont été comparés un à un aux empreintes SHA-256 de la copie de 08:57 : 0 différence ;
  - la mémoire réelle n'a été **ouverte qu'en lecture**, par `backup_memory.py`, pour la sauvegarde et sa vérification, Atlas arrêté ;
  - aucun Atlas d'essai n'a été lancé ;
  - le diagnostic `precheck_atlas.ps1` est en lecture seule, et sa sortie a été effacée de `%TEMP%` ;
  - **hors du dépôt**, j'ai créé `C:\Users\Public\AtlasTest`, pour le compte neuf, et deux sauvegardes dans `%USERPROFILE%\Atlas_backups`.

### 6.5 IF3 bis, avant (23/11) : où l'installeur écrit sur un compte neuf

**Relevé sur le PC d'Alexis, en lecture seule :**
- les variables de la machine et de son compte (noms seulement) ;
- les dossiers de Tesseract et d'Ollama ;
- les entrées « Applications » ;
- les comptes locaux ;
- les ports à l'écoute ;
- les droits de `C:\Users\Public`.

**Lu aussi dans le code :**
- `atlas.iss` ;
- `etapes.py` (Ollama, Tesseract) ;
- `desinstaller.py` ;
- `lancer.py` ;
- `core/file_indexer.py` (racines, exclusions) ;
- `core/memory_manager.py`.

| Quoi | Où, sur `AtlasTest` | Preuve |
|---|---|---|
| Atlas, son Python, ses données | `%LOCALAPPDATA%\Programs\Atlas` d'`AtlasTest` | `PrivilegesRequired=lowest`, `DefaultDirName={autopf}\Atlas` ; mémoire en `PersistentClient` dans `data/chromadb` du dossier d'Atlas |
| Raccourcis, démarrage avec Windows, désinstallation | menu Démarrer, Bureau, `HKCU` d'`AtlasTest` | `{autoprograms}`, `{autodesktop}`, `Root: HKCU` |
| Ollama | **un Ollama neuf pour `AtlasTest`** : `%LOCALAPPDATA%\Programs\Ollama` et `%USERPROFILE%\.ollama` d'`AtlasTest` | Celui d'Alexis (0.40.6) est dans son profil, et son dossier est dans son PATH **utilisateur** (entrée `HKCU`). `ollama_exe()` ne le trouve donc pas depuis `AtlasTest`. |
| Tesseract | **déjà là, gardé** : `C:\Program Files\Tesseract-OCR`, 5.5.0.20241111, dans le PATH **machine**, avec `fra.traineddata` | `tesseract_exe()` le trouve ; le français est présent, donc aucune copie (`francais_ajoute` faux) |
| Secrets | le coffre de Windows d'`AtlasTest` | `win32cred`, propre à chaque compte |
| Index des fichiers | **lecture** des disques fixes ; les autres profils (`C:\Users\<compte d'Alexis>`) sont exclus | `Exclusions.exclu` : « les profils des AUTRES utilisateurs, jamais le sien » |
| Désinstallation « effacer » | seulement les Python du dossier d'Atlas d'`AtlasTest`, ses secrets `Atlas:`, son `data` | `desinstaller.arreter` filtre sur `ROOT` ; `effacer_donnees` sur `ROOT / "data"` |

- Aucune variable `OLLAMA_*`, `TESS*`, `ATLAS*` ou `PYTHON*` n'est définie pour la machine.
- Il reste 50,8 Go libres sur C:.
- `C:\Users\Public` donne la modification à `INTERACTIF`, hérité : `C:\Users\Public\AtlasTest` est lisible et inscriptible depuis les deux comptes.
- Le diagnostic (`precheck_atlas.ps1`, lecture seule) donne `verdict=ok`, `modele=qwen2.5:7b`, `sur=carte`, non provisoire.

**Confirmation écrite :** l'installation et les données d'Alexis ne sont pas touchées par le parcours sur `AtlasTest`, **à condition qu'Alexis soit déconnecté de sa session**.
- **Pourquoi la condition :** `127.0.0.1` est commun à toutes les sessions ouvertes.
- **Avec la session d'Alexis encore ouverte, et son Ollama qui écoute sur 11434 :**
  - l'installeur d'`AtlasTest` installe bien son propre Ollama, mais il le trouve « déjà à l'écoute » et ne le démarre pas ;
  - le modèle est alors tiré **dans les fichiers d'Alexis** ;
  - le serveur d'`AtlasTest`, lui, ne peut pas prendre le port.
- **Avec, en plus, l'Atlas d'Alexis qui tourne sur 8550 :** `lancer.py` sur `AtlasTest` ouvre sa fenêtre sur **cet** Atlas. La phrase de la cabane irait dans **la mémoire d'Alexis**.
- **Dans la fiche :** la déconnexion complète (pas « changer d'utilisateur »), et un contrôle dans le Gestionnaire des tâches, onglet Utilisateurs.

**Sauvegarde dans le doute, faite avant tout essai :**
- **`backup_memory.py backup`** → `%USERPROFILE%\Atlas_backups\memoire\chromadb_20261123_085718`.
  - Les empreintes de la copie sont identiques à l'original.
  - Collections relevées : 489, 276, 20, 19 et 8 éléments, et `habits.db` avec 144 habitudes.
  - **`verify` a échoué une fois** sur « Error creating hnsw segment reader: Nothing found on disk ». C'est le défaut connu de ChromaDB 1.5.1, déjà noté aux sprints précédents. Il n'a **pas** été relancé jusqu'à passer : c'est la règle.
- **Copie complète de `data/`**, Atlas arrêté (rien sur 8550) → `%USERPROFILE%\Atlas_backups\data_complet_20261123_085754`.
  - **198 fichiers, chacun avec la même empreinte SHA-256 que l'original**, et la source n'a pas bougé pendant la copie.
  - Le fichier `SHA256SUMS` est joint.
  - C'est la vérification « par les données » que demande le brief.

**L'installeur construit depuis `main` (`d706b67`) :**
- `construire.py --ref origin/main` : code 0. Inno Setup a compilé en 20,8 s.
- `AtlasSetup.exe` fait 15 786 811 octets. SHA-256 : `b4186856c191dac47fc49cd25498d81ff1e7c16478a0f9c2e19f083a94f5aa4e`.
- `verifier_paquet` ne trouve **aucune faute**. Dans les réglages installés : `mail.envoi = "simulation"`, `prenom = ""`.
- `relever_journaux.py` du paquet est **identique** à celui de `main`, avec `nettoyer_contenu` du 11/11.
- Les fichiers sont copiés dans deux dossiers :
  - `build/installeur/cle_usb`, pour Drive : l'installeur, les deux `precheck`, `relever_journaux.bat`, `GUIDE_INSTALLATION_A_DISTANCE.md` et `GUIDE_TESTEUR.md` ;
  - `C:\Users\Public\AtlasTest`, pour le compte neuf : les mêmes scripts, avec les deux fiches.
- Le même SHA-256 est relevé dans les deux dossiers.

**Écart trouvé avant l'essai :**
- La §5 attend que l'installeur reconnaisse Tesseract déjà là, n'écrase rien, **et le dise**.
- Il le reconnaissait et n'écrasait rien. Mais il ne le disait pas : une clé `tesseract_deja_la` dans `installation.log`, rien à l'écran.
- **Corrigé**, avec 5 tests : 4 vus rouges d'abord, et un garde-fou vert dès le départ (rien de déjà là, aucune phrase ajoutée) :
  - une ligne « Tesseract déjà installé (…) : gardé tel quel » dans le journal ;
  - le message de fin dit ce qui était déjà là : Ollama, Tesseract, ou les deux.
- Cette correction est sur la branche. **L'installeur de `main` du 23/11 ne la contient pas** : il sera reconstruit après la fusion, avant l'essai si Alexis le souhaite.

---

## 7. Limites et risques identifiés

1. **IF3 et IF4 ne sont pas joués.**
   - Sévérité : **Élevé**.
   - La fermeture de la fenêtre d'Ollama, le lanceur et le relevé sont prouvés par des tests et par des essais partiels. Ils ne l'ont pas été sur une installation neuve complète.
   - Mitigation : l'étape 2 de la fiche note toute fenêtre d'Ollama ; le relevé rapporte `installation.log` (lignes « application Ollama fermée ») et `app.log` d'Ollama.
2. **ChromaDB 1.5.1 est dans la plage touchée par CVE-2026-45833**, sans version corrigée.
   - Sévérité : **Moyen**. Le chemin d'attaque n'existe pas dans Atlas, mais la version est touchée.
   - Mitigation : le test de garde, et une montée de version dès qu'un correctif paraît.
   - **Décision du superviseur attendue** avant la démo (le brief dit de s'arrêter si un point est concerné).
3. **La faille Ollama de l'article n'est pas identifiée.**
   - Sévérité : **Faible**.
   - Mitigation : les deux fuites de 2026 sont corrigées dans 0.40.6. Ollama n'écoute que sur 127.0.0.1, avec des modèles épinglés.
4. **Le démarrage caché de l'application Ollama par son raccourci est lu dans le code, pas observé.**
   - Sévérité : **Faible**.
   - Mitigation : noté chez le proche (fiche, étape 2) et dans `app.log`.
5. **Si l'application Ollama apparaît après la fin de l'installation**, plus rien ne la ferme. Dans la Sandbox, elle est apparue avant la fin de l'étape Ollama, et 6 à 20 minutes d'installation suivent.
   - Sévérité : **Faible**.
   - Mitigation : la garde balaie jusqu'à la fin de l'installation, et une dernière fois en s'arrêtant.
6. **Un `ollama serve` a été lancé pour de vrai sur le PC d'Alexis** (R3).
   - Sévérité : **Faible**.
   - Mon script de vérification remplaçait `Popen` **après** le chargement du lanceur, et la valeur par défaut était déjà liée. Le serveur s'est arrêté seul : son port était pris.
   - Mitigation : le test `test_if1_l_installeur_trouve_le_lanceur_par_son_chemin` remplace `Popen` avant le chargement.
7. **Une assertion n'a pas été vue rouge.** La ligne « mails : simulation » du relevé a été écrite dans le même envoi que son code.
   - Sévérité : **Faible**.
8. **Le relevé et le contenu du proche.**
   - **Ce qui était vrai au premier rapport :** le relevé ne remplaçait que des valeurs connues (session, ordinateur, prénom, adresses). Le superviseur l'a relevé, et c'est corrigé le 11/11 (§6.3) :
     - liste blanche des modules ;
     - chemins hors des dossiers techniques et noms de documents retirés ;
     - phrases dites et souvenirs retirés.
   - **Ce qui reste :** un module technique qui ajouterait demain une ligne de contenu, sous un début qui n'est pas dans la liste `DITS`, la laisserait passer.
   - Sévérité : **Faible**.
   - Mitigation : la fiche donne des phrases d'essai inventées ; le parcours est mené par Alexis ; les modules non techniques sont retirés par défaut.
9. **23/11 — Une session d'Alexis restée ouverte pendant le parcours sur `AtlasTest`** prêterait son Ollama, et son Atlas, au compte neuf : `127.0.0.1` est commun aux sessions (§6.5).
   - Sévérité : **Élevé** si cela arrive : la phrase d'essai irait dans la vraie mémoire d'Alexis.
   - Mitigation :
     - la fiche impose la déconnexion complète, contrôlée dans le Gestionnaire des tâches ;
     - la sauvegarde de `data/` est faite et vérifiée par empreintes ;
     - après le parcours, une vraie question est posée sur le compte d'Alexis, et on vérifie que « cabane » n'est pas dans sa mémoire.
   - **Non fait, à décider :** un garde dans `lancer.py` et `etapes.py` qui refuserait un Atlas ou un Ollama à l'écoute **lancé par un autre compte**. Aujourd'hui, les deux s'y attachent sans regarder à qui il appartient. Ce serait une ligne de défense dans le code, en plus de la fiche. Je ne l'ai pas ajouté : ce n'est pas dans la §5.
10. **23/11 — `verify` de la sauvegarde mémoire a échoué** (hnsw, ChromaDB 1.5.1).
    - Sévérité : **Faible**.
    - Mitigation : la copie complète de `data/` est vérifiée fichier par fichier. La sauvegarde de `backup_memory.py` a des empreintes identiques.
11. **23/11 — IF6 : le Contrôle intelligent des applications** d'un Windows 11 installé à neuf peut bloquer `AtlasSetup.exe`, qui n'est pas signé, sans bouton pour continuer.
    - Sévérité : **Moyen** pour les testeurs à distance : c'est un arrêt net.
    - Mitigation : le guide dit de s'arrêter et de ne pas désactiver ce contrôle. Seule une signature de l'installeur réglerait ça.
    - Non mesuré : ni le PC d'Alexis ni la Sandbox n'ont ce contrôle actif.
12. **23/11 — Le `GUIDE_TESTEUR.md` existant a été écrasé par erreur** par mon premier brouillon du guide à distance, puis aussitôt restauré depuis git (`git checkout`), avant tout commit.
    - Sévérité : **Faible** : aucune perte, `git diff` est vide sur ce fichier.
    - Le guide à distance a pris son propre nom, `GUIDE_INSTALLATION_A_DISTANCE.md`.
13. **23/11 — `test_ck4_une_sonde_qui_ment_fait_echouer_la_suite` a échoué une fois** dans une suite complète : un pytest à part s'est arrêté au chargement sur « …introuvable… » (§5).
    - Sévérité : **Faible**. Il passe seul, puis dans le passage complet suivant.
    - Mitigation, à décider : faire afficher à ce test la fin de la sortie d'erreur, et pas seulement le début, pour que la cause soit lisible la prochaine fois. Non fait : ce n'est pas dans la §5.

---

## 8. Checklist de validation

- [ ] La fenêtre d'Ollama n'apparaît plus ; le serveur est sur `127.0.0.1` ; rien ne change chez Ollama sans accord — **code et tests faits, rien n'est changé chez Ollama ; pas encore vu sur une installation neuve (IF3)**
- [x] IF2 : les deux points tranchés, sources à l'appui — §6.2 (ChromaDB : version concernée, non exposée ; Ollama : pas concerné pour les fuites identifiables, article non vérifiable)
- [x] Fiche d'une page pour Alexis, prête avant le départ — `docs/beta/FICHE_PARCOURS_PROCHE.md`, relevé `installeur/relever_journaux.bat` (l'installeur reste à construire depuis `main`)
- [ ] Parcours complet sur le PC du proche : precheck, installation, test de capacité mesuré, premier lancement guidé — **À FAIRE**
- [ ] Atlas répond, retient, le souvenir survit à une réinstallation et à une désinstallation « garder » — **À FAIRE**
- [ ] Aucune donnée personnelle du proche dans ce qui est rapporté ; Atlas laissé installé, mails en `simulation` — **relevé prêt, corrigé après la vérification du superviseur et essayé sur un vrai journal d'Atlas (R4, §6.3) ; à constater au retour**
- [ ] Mode jeu mesuré sur un vrai jeu ; confirmation revue à l'écran — **À FAIRE (IF4)**
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama — §5 (1 669 ; 1 666 + 3 ignorés justifiés)
- [x] 23/11 — IF3 bis, avant : où l'installeur écrit relevé, confirmation écrite, sauvegarde de `data/` vérifiée par les données — §6.5, `docs/beta/FICHE_COMPTE_NEUF.md`
- [x] 23/11 — Installeur construit depuis `main`, paquet vérifié, SHA-256 noté — §6.5
- [x] 23/11 — `python -m pytest tests/ -q` → code 0 avec Ollama (2e passage : 1 699 ; le 1er : 1 échec instable, §5) et sans (1 696 + 3 ignorés justifiés)
- [ ] 23/11 — IF3 bis, pendant et après, sur `AtlasTest` — **À FAIRE (Alexis)**
- [ ] 23/11 — IF6 : partage, guide, retour des relevés — **préparé** (`docs/beta/GUIDE_INSTALLATION_A_DISTANCE.md`, `docs/beta/ENVOI_TESTEURS.md`) ; **aucun lien envoyé**, comme la règle le demande

---

## 9. Recommandations pour le sprint suivant

- **P1, au 23/11 :**
  - fusionner `sprint-installeur-compte-neuf` (Tesseract « déjà là » dit à l'écran), puis reconstruire l'installeur depuis `main` et le recopier dans `C:\Users\Public\AtlasTest` et `cle_usb` ;
  - jouer IF3 bis sur `AtlasTest` (`docs/beta/FICHE_COMPTE_NEUF.md`), puis lire les deux relevés, corriger avec un test rouge d'abord, reconstruire ;
  - décider du garde « Atlas ou Ollama d'un autre compte » (§7, point 9) ;
  - ensuite seulement, IF6 : le partage Drive et l'empreinte par message (`docs/beta/ENVOI_TESTEURS.md`).
- **P1, au 11/11 :**
  - fusionner cette branche ;
  - construire l'installeur depuis `main` ;
  - jouer la fiche chez le proche, puis lire les deux relevés et compléter ce rapport ;
  - **trancher le point ChromaDB** (superviseur) ;
  - IF4 avec Alexis.
- **P2 :**
  - monter ChromaDB dès qu'une version corrigée de CVE-2026-45833 paraît, puis rejouer la mémoire (sauvegarde vérifiée d'abord) ;
  - revoir les mises à jour de sécurité de la bibliothèque C++ copiée avec Atlas (décision d'Alexis du 10/11 : après la démo).
- **P3 :**
  - observer sur une session Windows neuve que le raccourci de démarrage d'Ollama la relance bien cachée ;
  - retirer de `parcours.ps1` la fermeture d'Ollama propre à la Sandbox si l'installeur suffit.
