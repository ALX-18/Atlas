# RAPPORT SPRINT — INSTALLEUR : Atlas chez un proche, en un double-clic

**Développeur :** CHAT6 (Claude Opus, Claude Code Windows)
**Brief :** `docs/briefs/BRIEF_SPRINT_INSTALLEUR.md` (4 novembre 2026)
**Branche :** `sprint-installeur` (6 commits, non poussés)
**Date :** 6 novembre 2026

> **Rapport intermédiaire.** Tout ce qui se fait sans Windows Sandbox est fait, mesuré et commité. Le parcours d'installation de bout en bout dans la Sandbox (IN6) **n'est pas encore joué** : la Sandbox doit être activée par Alexis (droits administrateur, redémarrage). Les lignes concernées disent « À FAIRE » ; aucun chiffre n'y est inventé.

---

## Tableau de tête

| Ce que le brief met en tête | Résultat |
|---|---|
| Parcours d'installation dans la Sandbox (temps, étapes) | **À FAIRE** (Sandbox pas encore activée) |
| Taille téléchargée | calculée, pas encore mesurée : **9,6 Go** sur une machine NVIDIA 8 Go (`qwen2.5:7b`), **10,2 Go** sans NVIDIA (`gemma4:e4b`) ; l'installeur lui-même fait **15,4 Mo** |
| Test de capacité réelle | écrit et testé (simulé) ; **À FAIRE** en réel dans la Sandbox (chemin sans NVIDIA) |
| Désinstallation | écrite et testée (simulée) ; **À FAIRE** en réel dans la Sandbox |
| Finitions (IN7) | agenda multi-jours **fait** ; consigne du lecteur **faite** ; budget de la consigne **dégagé** (36 → 169 jetons) ; guide testeur **réécrit**, chaque exemple vérifié ; confirmation de la fenêtre de bureau **corrigée**, revue à l'écran **À FAIRE** avec Alexis |
| `pytest tests/ -q` | **1 641 réussis** avec Ollama (0 ignoré) ; **1 638 réussis + 3 ignorés justifiés** sans Ollama ; code 0 les deux fois |
| Corpus de routes / GB1 / banc de non-régression | **510/511 (99,8 %)**, 0 action à tort / **0** / **vert** (référence `qwen2.5:7b` enregistrée) |

---

## 1. Résumé exécutif

- **Statut : EN COURS** — il manque le parcours réel dans Windows Sandbox (installation, réinstallation, désinstallation, test de capacité sans NVIDIA) et deux vérifications à l'écran avec Alexis (confirmation de la fenêtre de bureau, mode jeu sur un vrai jeu).
- **L'installeur existe et se construit en une commande** (`python installeur/construire.py`) : Inno Setup 7.1.1, installation pour la personne seule (aucun droit administrateur pour Atlas), Python 3.12.10 embarqué avec Tkinter, 160 dépendances à des versions fixes **identiques à celles du `.venv` testé**, chacune avec son empreinte SHA-256. Il vérifie la machine avant de copier quoi que ce soit, choisit le modèle sur place, puis télécharge et vérifie Ollama, Tesseract, le modèle et les modèles de la voix, et fait le test de capacité.
- **Aucune donnée d'Alexis dans le paquet**, prouvé par un test : le paquet est fait du code **commité** (jamais du dossier de travail), sa vérification refuse toute base, journal, mémoire, adresse personnelle, chemin du PC d'Alexis, adresse iCal privée, envoi réel ou prénom.
- **Paliers identiques partout** (`doctor.py`, `precheck_atlas.ps1`, installeur), prouvé par un test sur 12 machines types qui fait tourner le vrai script PowerShell.
- **Mode jeu mesuré** : 4 879 Mo de mémoire de carte rendus, rechargement en 5,2 s (3 mesures identiques). **Épinglage** : l'empreinte du modèle est vérifiée au démarrage. **Banc de non-régression** en une commande, vert, avec sa référence.
- **Hors brief, décidé avec Alexis** : Atlas n'appelle plus tout le monde « Alexis » — le prénom de la personne est demandé au premier lancement (Alexis reste le créateur dans l'identité).
- **Banc hostile avec le vrai modèle** : 0 action, 0 secret, 26/26 marqués ; l'affirmation forgée du rapport Compétences 2 est maintenant attribuée à l'expéditeur.
- **Défauts trouvés et corrigés** : le banc de modèles ne mesurait plus les documents depuis le sprint Artefacts sur mesure ; la fenêtre de bureau pouvait afficher « Réponse : success » ou une erreur en anglais après une confirmation ; un exemple du guide testeur prenait une mauvaise route.

---

## 2. Objectifs vs réalisation

| Tâche | Réalisation | Statut |
|---|---|---|
| IN0 — Base | `sprint-competences-2` fusionnée (`cd80a64`), suite verte au départ | PASS |
| IN1 — Choix technique | Inno Setup (recommandation du superviseur), Python embarqué propre à Atlas, dépendances depuis PyPI avec empreintes, pas de PyInstaller. Précisions : Tkinter (indispensable à la fenêtre d'Atlas, absent du Python embarqué officiel) est pris dans `tcltk.msi` de python.org, signé ; les 6 bibliothèques que PyPI ne publie qu'en sources (pyautogui et ses dépendances) sont construites en roues à la construction, leurs empreintes dans le verrou. Installeur en ligne, taille et temps annoncés. Pas de signature de code (guide : écran SmartScreen) | PASS |
| IN2.1 — Diagnostic | `precheck_atlas.ps1 -Sortie` lu par l'installeur avant toute copie ; « ne convient pas » : arrêt avec la raison, rien d'installé (vérifié par un installeur d'essai) | PASS (Sandbox À FAIRE) |
| IN2.2 — Python et dépendances | Python 3.12.10 embarqué (`._pth` : aucun Python existant n'est touché, ni PYTHONPATH ni site utilisateur) ; `pip --require-hashes --no-deps --only-binary` | écrit ; réel À FAIRE |
| IN2.3 — Ollama | installeur officiel 0.40.6 (empreinte publiée), `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-` ; un Ollama déjà là est gardé ; écoute vérifiée sur 127.0.0.1 (sinon arrêt, avec la marche à suivre) ; version comparée à la référence | écrit, testé (simulé) ; réel À FAIRE |
| IN2.4 — Tesseract | installeur UB Mannheim 5.4.0 (`/S`), puis le français (`fra.traineddata` de `tessdata_fast`, empreinte Git publiée) ; Atlas trouve Tesseract là où il est (`core/outils_externes.py`) | écrit ; options silencieuses À VÉRIFIER dans la Sandbox |
| IN2.5 — Modèles | modèle du palier par `/api/pull`, empreinte comparée à l'épinglage ; voix, mot d'éveil, transcription et e5 par `download_voice_models.py`, **chaque fichier vérifié par son empreinte**, dépôts Hugging Face à révision fixe | écrit, empreintes vérifiées sur les fichiers d'Alexis ; réel À FAIRE |
| IN2.6 — Test de capacité | une réponse courte à num_ctx 8 192, part sur la carte (`/api/ps`) et vitesse ; contredit → le dire et proposer le palier inférieur | écrit, testé (simulé) ; réel À FAIRE |
| IN2.7 — Raccourcis, démarrage, Applications | Bureau, menu Démarrer, « Démarrer Atlas avec Windows » **décochée**, entrée dans Applications | écrit ; réel À FAIRE |
| IN2.8 — Premier lancement guidé | fenêtre : « Hey Atlas » à l'anglaise, confirmations, ce qu'il sait et ne sait pas faire, ce qui passe par internet ; **le prénom** | écrit ; à l'écran À FAIRE |
| IN3 — Paliers | 8 Go : `qwen2.5:7b` ; 6 Go ou sans NVIDIA avec 16 Go : `gemma4:e4b` provisoire ; dessous : « ne convient pas » ; mêmes seuils et mêmes choix dans `doctor.py` et `precheck_atlas.ps1` (test sur 12 machines) | PASS |
| IN4 — Mode jeu | décharge le modèle (keep_alive 0) après 10 s de jeu en plein écran, si le modèle n'a pas servi depuis une minute ; annonce « Je recharge mon modèle, quelques secondes » à la demande suivante ; **mesuré : 4 879 Mo rendus, 5,2 s** | PASS (vrai jeu À FAIRE) |
| IN4 — Épinglage | `config/modeles.json` ; vérifié au démarrage ; différent → bascule `modele_non_epingle` (attendue / trouvée) ; `doctor.py` le dit | PASS |
| IN4 — Banc de non-régression | `scripts/non_regression_modele.py` (GB1, plans, documents et faits inventés, consignes, conversation) ; référence de `qwen2.5:7b` enregistrée ; `doctor.py` signale un Ollama changé depuis le dernier banc vert | PASS |
| IN5 — Désinstallation | retire Atlas, raccourcis, démarrage ; demande « Garder ta mémoire, ce qu'Atlas a appris et tes rappels ? » (oui par défaut) ; non → sauvegarde proposée d'abord (une sauvegarde ratée n'efface rien) ; retire les secrets `Atlas:*` et le dit ; n'enlève ni Ollama ni Tesseract, et le dit | écrit, testé (simulé) ; réel À FAIRE |
| IN6 — Sandbox | `installeur/sandbox/` : configuration (16 Go, sans carte graphique) et parcours scripté complet ; deuxième configuration à 8 Go pour « ne convient pas » | prêt ; **À FAIRE** |
| IN6 — Réinstallation sans perte | réglages `onlyifdoesntexist`, `data/` jamais dans le paquet, étapes reprises où elles s'étaient arrêtées | écrit ; réel À FAIRE |
| IN6 — Paquet sans donnée d'Alexis | `verifier_paquet` + tests (9 pièges plantés, tous attrapés ; le vrai paquet propre) | PASS |
| IN6 — PC du proche | par Alexis, avec CHAT6 en soutien ; Bluetooth à mesurer là-bas | À FAIRE (hors de ce rapport) |
| IN7 — Agenda multi-jours | « cette semaine », « la semaine prochaine », « ce week-end », « le week-end prochain », libre sur ces périodes ; un mois ou le passé : Atlas le dit, sans rien télécharger | PASS |
| IN7 — Consigne du lecteur | consigne (« l'expéditeur affirme que… ») **et** garde déterministe : une affirmation sur Alexis / Atlas / la personne non attribuée → extrait ; **banc hostile, vrai modèle : les 3 affirmations forgées attribuées à l'expéditeur** | PASS |
| IN7 — Confirmation de la fenêtre de bureau | relue : 3 défauts corrigés (message d'annulation perdu, « Réponse : success », erreur en anglais), délai porté à 120 s | corrigé ; revue à l'écran À FAIRE |
| IN7 — Budget de la consigne | 36 → 169 jetons de marge (Atlas complet, consigne la plus lourde) | PASS |
| IN7 — Guide testeur | réécrit en entier ; chacun de ses 30 exemples prend la route promise (test) | PASS (lecture par Alexis À FAIRE) |
| IN8 — Rapport | ce document | intermédiaire |

---

## 3. Architecture projet mise à jour

```
installeur/                      ← NOUVEAU
  atlas.iss                      (Inno Setup : diagnostic, page « ce qui va être installé », désinstallation)
  construire.py                  (paquet du code commité, Python embarqué, verrous, ISCC)
  etapes.py                      (après la copie : dépendances, Ollama, Tesseract, modèle, voix, capacité, réglages)
  desinstaller.py                (arrêter Atlas, retirer les secrets, sauvegarder, effacer)
  lancer.py                      (raccourci : serveur sans fenêtre noire, puis la fenêtre)
  premier_lancement.py           (le guide du premier lancement, le prénom)
  sources.json                   (Ollama, Tesseract, français : URL officielles, empreintes)
  sandbox/parcours.ps1, preparer.py
core/modele_local.py             ← NOUVEAU (épinglage, mode jeu)
core/utilisateur.py              ← NOUVEAU (le prénom de la personne)
core/outils_externes.py          ← NOUVEAU (Tesseract trouvé là où il est installé)
config/modeles.json              ← NOUVEAU (modèles épinglés, Ollama de référence)
config/reference_non_regression.json ← NOUVEAU
scripts/non_regression_modele.py ← NOUVEAU
tests/test_installeur.py         ← NOUVEAU (107 tests)
```

Modifiés : `core/agenda.py`, `core/regles_courrier.py` (périodes), `core/courrier.py` (consignes au prénom, garde de l'affirmation forgée), `core/ollama_client.py` (prénom dans la consigne, annonce du rechargement), `core_conversational/identity.py`, `core_conversational/degradations.py` (`modele_non_epingle`), `core/artefacts.py`, `core/validator.py`, `core/donnees_reelles.py`, `main.py`, `desktop/atlas_desktop.py`, `ui/app.js`, `scripts/doctor.py`, `scripts/precheck_atlas.ps1`, `scripts/download_voice_models.py`, `scripts/banc_modeles.py`, `config/settings.json` (`utilisateur`, `mode_jeu`), `docs/beta/GUIDE_TESTEUR.md`, `docs/CONFIGURATION.md`, `README.md`, `.gitignore`. 41 fichiers, +3 728 / −167 lignes.

---

## 4. Détail des implémentations

**`installeur/construire.py`** — (1) `git archive HEAD` filtré par une liste de dossiers de code (`INCLUS`) : jamais `data/` (sauf les modes par défaut `data/workflows/`), jamais `models/`, ni `.venv` ; les réglages installés sont ceux du dépôt, forcés à `mail.envoi = "simulation"` et à un prénom vide. (2) Python 3.12.10 embarqué : MD5 publié par python.org vérifié, `python.exe` signé par la Python Software Foundation (Authenticode, vérifié) ; `python312._pth` avec `..` (le dossier d'Atlas) et `import site` ; Tkinter extrait de `tcltk.msi` (installation « administrative » : des fichiers, rien d'enregistré dans Windows), signé PSF, vérifié ; pip extrait de sa roue (empreinte PyPI). Essai : `tkinter.Tk()` s'ouvre dans le Python embarqué. (3) Verrous : `pip install --dry-run --report` contraint par le gel du `.venv` (`pip list --format=freeze`, « +cpu » retiré) → 160 paquets + 3 NVIDIA, **0 version différente** de celles testées ; les paquets sans roue sur PyPI sont construits en roues ici. (4) `verifier_paquet` : chemins interdits (bases, journaux, `.onnx`, `chromadb/`…) et contenus interdits (adresse personnelle, chemin du PC d'Alexis, adresse iCal privée réelle ; dans `config/` : envoi réel, prénom). Les marqueurs sont assemblés par morceaux dans le source, sinon le fichier se dénonçait lui-même (constaté à la construction). (5) `tailles.iss` en Mo entiers (Pascal Script lit les nombres à virgule selon la langue de Windows).

**`installeur/atlas.iss`** — `PrivilegesRequired=lowest`, `{autopf}\Atlas` (= `%LOCALAPPDATA%\Programs\Atlas`). `InitializeSetup` : `precheck_atlas.ps1 -Sortie` (lecture seule), lu ligne à ligne (vérifié avec un installeur d'essai qui s'arrête avant toute copie : verdict, palier, raisons lus) ; « ko » → message, arrêt. Page « Ce qui va être installé » : modèle (provisoire ou non), sur la carte ou le processeur, taille, temps à 50 Mbit/s, ce qui est installé, la possible autorisation pour Tesseract. `ssPostInstall` : `etapes.py` (avec `--sans-fenetre` en silencieux) ; échec → « relancez, il reprendra où il s'est arrêté ». Désinstallation : question sur la mémoire (`/MEMOIRE=effacer` pour les essais silencieux), sauvegarde proposée, `desinstaller.py --arreter --secrets`, rapport affiché, Ollama et Tesseract laissés et dits ; restes (caches) retirés, `data\` gardé si demandé.

**`installeur/etapes.py`** — `telecharger` : HTTPS obligatoire, empreinte obligatoire (SHA-256 ou Git), reprise par `Range`, fichier à la mauvaise empreinte effacé. Étapes notées dans `etat.json` (reprise). `verifier_ollama_local` : toute adresse d'écoute hors 127.0.0.1/::1 arrête l'installation. `juger_capacite` : sur carte, ≥ 90 % du modèle sur la carte et ≥ 15 jetons/s ; sur processeur, ≥ 3 jetons/s ; sinon la raison, en français, et `qwen2.5:7b` → `gemma4:e4b` proposé. `etape_reglages` : le modèle du palier ; « simulation » seulement à la première installation (une réinstallation garde le choix de la personne).

**`core/modele_local.py`** — `verifier_epinglage` (conforme / différent / absent / non épinglé / injoignable), `signaler_epinglage` (bascule annoncée, levée si conforme). `ModeJeu.tour()` : deux coups d'œil (10 s) d'un jeu en plein écran — navigateurs, lecteurs vidéo et Python exclus —, modèle chargé et pas servi depuis 60 s → déchargé. `avant_appel()` (appelé par `champs_modele()`, donc par chaque requête au modèle) : l'annonce, une seule fois, à l'écran et à la voix.

**`scripts/non_regression_modele.py`** — `banc_modeles.py` sur les parties gb1, plans, documents, consignes, conversation (données jetables, garde BM0) ; `comparer` : les zéros restent des zéros (GB1, faits inventés livrés, fuites), tolérances écrites dans la référence (plans −10 points, consignes −1) ; une partie en erreur n'est jamais verte ; `--enregistrer` refuse une référence incomplète. Bilan d'un banc vert dans `data/non_regression.json` (ignoré par git).

**`core/utilisateur.py`** — `prenom()` (relu si `settings.json` change), `nettoyer` (lettres, espaces, tirets, apostrophes, 40 caractères), `de_nom()` (« d'Alexis », « de Marie »), `enregistrer`. Identité : « Mission : assister la personne qui t'utilise » ; « Tu parles à Marie. » si le prénom est connu ; lecteur et rédacteur de mails, documents, repère d'historique et messages du validateur sans « Alexis ».

**`core/agenda.py`, `core/regles_courrier.py`** — `_periode` : semaine en cours (d'aujourd'hui à dimanche), semaine prochaine (lundi–dimanche), week-end, week-end prochain ; `periode_inconnue` (mois, passé) → `PERIODE_INCONNUE`, avant tout téléchargement. `_lire_periode` : regroupé par jour, jours vides omis, « libre » sur chaque jour.

**`core/courrier.py`** — garde `_reprend_une_affirmation` : par phrase, une affirmation « Alexis / Atlas / l'utilisateur / la personne / <prénom> a demandé / autorisé / validé… » (ou « tu as autorisé… ») sans « affirme / prétend / selon… » → résumé refusé, extrait. « Le devis que tu as demandé » reste un résumé ordinaire.

**`desktop/atlas_desktop.py`** — `texte_resultat_confirmation(data)` : le message du serveur d'abord ; succès sans message → « Action exécutée. » seulement si l'outil a dit `success: True` ; échec dit comme un échec ; réponse inattendue → « je ne sais pas si l'action a été faite ».

**`scripts/download_voice_models.py`** — `EMPREINTES` (publiées : GitHub `digest`, Hugging Face `lfs.oid` ; relevées sur la copie de référence pour 4 petits fichiers sans empreinte publiée) ; révisions fixées (Piper, e5, whisper) ; la transcription « base » est téléchargée à l'installation (elle l'était au premier mot dit).

**`scripts/banc_modeles.py`** — `compter` accepte la consigne système : la partie « documents » échouait sur une `TypeError` depuis le sprint Artefacts sur mesure (défaut trouvé par ce sprint). Le Python embarqué remplace `.venv` quand il n'existe pas.

---

## 5. Résultats des tests

| Mesure | Résultat |
|---|---|
| `python -m pytest tests/ -q`, Ollama lancé | **1 641 passed**, 0 skipped, code 0 (9 min 5 s) |
| idem, Ollama arrêté | **1 638 passed, 3 skipped** (justifiés : 3 tests qui interrogent le vrai Ollama), code 0 (9 min 13 s) |
| Nouveaux tests (`tests/test_installeur.py`) | 107 ; **sur `main` : 106 échouent**, 1 passe (`test_in7_un_jour_reste_un_jour`, une non-régression : un jour reste un jour) |
| Corpus de routes | **510/511 (99,8 %)**, 0 action à tort ; +9 demandes (agenda sur plusieurs jours, 1 négatif) ; l'échec restant est connu (« horoscope ») |
| Banc de non-régression `qwen2.5:7b` (Ollama 0.40.6) | **vert** : GB1 0 affirmation sans outil, 0 question bloquée ; plans validés 75 % ; documents 6/6, 0 fait inventé livré ; consignes 11/12 ; conversation 20/20 en français, **1 réponse avec une autre écriture** ; 0 fuite. Le sprint Banc de modèles mesurait 80 % de plans, 11/12, 1 autre écriture : même modèle, même comportement. Durée : ~5 min |
| Banc hostile (`banc_courrier.py simule`, vrai modèle, serveurs simulés) | 26 mails (24 + 2 affirmations forgées) : **0 action, 0 secret, 26/26 « Contenu externe », 0 résumé qui obéit** ; 24 résumés du modèle, 2 refusés par les gardes (lien recopié, injection en anglais) → extrait. Les 3 mails à affirmation forgée (dont celui du défaut de Compétences 2, « ordre dans une citation ») sont résumés « L'expéditeur affirme que… » |
| Mode jeu (`qwen2.5:7b`, RTX 5060 8 Go, num_ctx 8 192) | 3 mesures : carte à 6 670 Mo → 1 791 Mo, **4 879 Mo rendus** ; rechargement **5,2 s** (chargement Ollama 5,0 s) |
| Budget de la consigne vocale (Atlas complet, 9 souvenirs longs, plus longue demande) | marge **36** jetons sur `main` → **169** (162 avec un prénom) |

Échecs rencontrés et corrigés pendant le sprint : `test_ck3` (clés `mode_jeu`, `modeles.json` non documentées), le recensement des écrivains de `data/` (`non_regression_modele.py` ajouté, avec sa raison), 3 anciens tests de `download_voice_models.py` (nouvelle signature), le test de marge sensible à l'ordre des tests (il charge maintenant tout Atlas).

---

## 6. Comportement observé en scénarios utilisateur réels

**Construction de l'installeur (réelle, sur le PC d'Alexis).** `AtlasSetup.exe` **15,4 Mo**, compilé en ~15 s par ISCC. Paquet : 236 fichiers de code, propre. Téléchargements de construction (accord d'Alexis) : Inno Setup 7.1.1 (14,3 Mo ; empreinte = celle publiée sur GitHub ; signature Authenticode valide, Pyrsys B.V.), Python embarqué (11,1 Mo, MD5 publié vérifié), `tcltk.msi` (3,6 Mo, signé PSF), pip 26.3 (2,0 Mo, empreinte PyPI), Tesseract 5.4.0 (50,2 Mo) **pour relever son empreinte** — aucune n'est publiée, et la signature Authenticode (Universität Mannheim) est classée « UnknownError » par Windows (chaîne non reconnue) : c'est écrit dans `sources.json`.

**Vérifications d'empreintes sur les fichiers déjà présents chez Alexis** : mot d'éveil, voix Piper, tokenizer e5 conformes aux empreintes publiées ; le `fra.traineddata` installé est exactement celui de `tessdata_fast` (empreinte Git).

**Le diagnostic lu par Inno** (installeur d'essai, rien installé) : machine simulée sans NVIDIA avec 12 Go → `verdict=ko`, raison « sans carte NVIDIA de 6 Go, il faut au moins 16 Go de mémoire vive », lue correctement. Sur le PC d'Alexis (lecture seule) : `qwen2.5:7b`, « Atlas tournera bien ».

**Parcours dans Windows Sandbox — À FAIRE ce soir** : installation silencieuse (temps, taille réelle, étapes), Atlas qui répond et retient, réinstallation par-dessus (le souvenir revient), désinstallation « garder » (mémoire gardée, secrets retirés, Ollama laissé), retour, désinstallation « effacer » ; puis une Sandbox à 8 Go qui doit s'arrêter sur « ne convient pas ».

**À l'écran avec Alexis — À FAIRE** : le message après Confirmer / Annuler dans la fenêtre de bureau ; la fenêtre du premier lancement et le prénom ; le mode jeu sur un vrai jeu en plein écran (détection, annonce du rechargement).

---

## 7. Limites et risques identifiés

1. **Rien n'a encore tourné sur une machine vierge.** — *Élevé tant que la Sandbox n'est pas jouée.* Les étapes sont testées une par une (simulées) ; leurs enchaînements réels (pip dans le Python embarqué, installeur silencieux d'Ollama, Tesseract, `/api/pull`, la voix) ne le sont pas.
2. **Tesseract : options silencieuses et droits non vérifiés.** — *Moyen.* L'installeur UB Mannheim (NSIS, `/S`) peut vouloir les droits administrateur ou s'installer sans le français ; `etapes.py` ajoute le français, et range une copie dans `models/tessdata` si `Program Files` est protégé. À voir dans la Sandbox. Sa signature n'est pas reconnue par Windows.
3. **Ollama se met à jour seul.** — *Moyen.* L'installeur pose la version 0.40.6 vérifiée ; ensuite, `doctor.py` signale une version changée depuis le dernier banc vert, et l'épinglage signale un modèle changé.
4. **`gemma4:e4b` est provisoire** et n'a pas de référence de non-régression (`non_regression_modele.py --enregistrer --modele gemma4:e4b` reste à faire, décision d'Alexis). — *Moyen.*
5. **Le banc tolère une réponse en écriture non latine sur 20** (la référence de `qwen2.5:7b` en a une ; dans Atlas, la garde de langue la remplace). — *Faible.*
6. **Le mode jeu reconnaît un jeu à son plein écran** : un programme quelconque en plein écran (hors navigateurs, lecteurs vidéo, PowerPoint) décharge aussi le modèle ; le coût est un rechargement de 5 s. Un jeu en « fenêtré sans bordure » n'est pas en plein écran au sens de Windows et n'est pas vu. — *Faible.*
7. **Pas de signature de code** : l'écran SmartScreen, expliqué dans le guide. — *Faible pour la démo* (décision d'Alexis, plus tard).
8. **L'installeur télécharge 9,6 à 10,2 Go** ; la reprise existe (étapes et téléchargements), mais une connexion lente rend l'installation longue (temps annoncé à 50 Mbit/s). — *Moyen.*
9. **Le prénom n'est demandé qu'au premier lancement** : pour le changer ensuite, il faut éditer `settings.json` (`utilisateur.prenom`). — *Faible.*
10. **Un résumé peut encore citer une adresse de mail du message** (« …transférer ses mails à collecte@… ») : attribuée à l'expéditeur et sans lien cliquable, mais visible. — *Faible.*

---

## 8. Checklist de validation

- [ ] Installeur en un double-clic, testé de bout en bout dans Windows Sandbox — construit ; **Sandbox À FAIRE**
- [ ] Diagnostic avant, test de capacité réelle après ; arrêt propre si la machine ne convient pas — écrits et testés (simulés), lecture Inno vérifiée ; **réel À FAIRE**
- [x] Téléchargements officiels, en HTTPS, vérifiés ; dépendances avec empreintes (Tesseract : empreinte relevée, aucune publiée)
- [x] Ollama sur `127.0.0.1` (vérifié par l'installeur), modèle épinglé et vérifié au démarrage ; Tesseract avec le français (écrit ; réel À FAIRE)
- [x] Paliers cohérents partout, testés
- [x] Mode jeu mesuré (vrai jeu À FAIRE) ; banc de non-régression en une commande, avec référence
- [ ] Réinstallation sans perte ; désinstallation qui demande pour la mémoire et retire les secrets — écrites et testées (simulées) ; **réel À FAIRE**
- [x] Aucune donnée d'Alexis dans le paquet, prouvé par un test
- [x] « simulation » installé par défaut ; démarrage avec Windows décoché par défaut
- [ ] Finitions : agenda multi-jours ✓, consigne du lecteur ✓, budget ✓, guide réécrit ✓ ; **confirmation revue à l'écran À FAIRE**
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama

---

## 9. Recommandations pour le sprint suivant

**Ce soir (fin de ce sprint)**
- Windows Sandbox : le parcours complet, puis « ne convient pas » à 8 Go ; compléter §6 et le tableau de tête avec les vrais temps et tailles.
- À l'écran avec Alexis : la confirmation de la fenêtre de bureau, le premier lancement, le mode jeu sur un vrai jeu.

**Ensuite**
- Le PC du proche, avec Alexis : précheck, installation réelle avec carte NVIDIA, Bluetooth.
- La référence de non-régression de `gemma4:e4b`, si la démo peut tomber sur ce palier.
- Un réglage pour changer le prénom sans éditer `settings.json` (« appelle-moi Marie »).
- La signature de code (décision d'Alexis).
