# RAPPORT SPRINT — COMPÉTENCES 1 : le son, la lumière, le Bluetooth, le temps, la musique
Date: 18/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_COMPETENCES_1.md`. Branche **`sprint-competences-1`**, issue de `main` @ `888e362` (Artefacts fusionné, plus le brief). Commit non poussé.
> Règle du sprint : **agir, relire, dire.** Chaque message est construit sur l'état relu (volume, luminosité, radio, session multimédia, rappel en base), jamais sur la valeur demandée. Ce qui ne peut pas être relu est dit tel quel.

---

## Tableau de tête — une ligne par compétence

| Compétence | Verdict | Matériel mesuré | Ce qui est relu après l'action |
|---|---|---|---|
| Heure et date (CP1) | **marche** | horloge du PC | calcul déterministe (horloge figée en test) ; jamais le modèle |
| Minuteurs et rappels (CP2) | **marche** | PC d'Alexis | le rappel relu dans `rappels.db` ; échéance donnée par notification, fenêtre, voix ; manqué annoncé au redémarrage (réel) |
| Volume général (CP3) | **marche** | sortie audio par défaut (pycaw) | niveau et sourdine relus — et relus une 2e fois par le rejeu, indépendamment |
| Volume d'un programme (CP3) | **marche** | session audio de Discord (réel) | niveau de la session relu |
| Luminosité (CP4) | **marche** (DDC/CI) ; **non** sur WMI | les 2 écrans d'Alexis : DDC/CI accepté ; WMI « non pris en charge » (PC fixe) | luminosité de chaque écran relue (DDC/CI) |
| Veille des écrans (CP4) | **marche** (non relisible) | les 2 écrans | rien : dit tel quel (« Je ne peux pas le vérifier ») ; aucun chemin vers l'extinction du PC (test) |
| Bluetooth on/off (CP5) | **partiel** : code et tests ; **réel : PC sans Bluetooth** | aucune radio Bluetooth sur le PC d'Alexis (confirmé par lui) | état de la radio relu (testé sur double) ; réel : « pas de Bluetooth utilisable » dit |
| Connecter un appareil (CP5) | **reporté honnêtement** | — | Windows n'offre pas d'API propre (§4.6) : Atlas le dit et ouvre les paramètres Bluetooth |
| Musique, commandes universelles (CP6) | **marche** (Spotify) | Spotify, sessions multimédia de Windows (SMTC) | statut et titre relus ; « suivant » une fois sans changement de titre : dit tel quel |
| Musique, chercher par service (CP6) | **marche** : Spotify, Deezer, YouTube Music ; **non** : Apple Music | les 4 services sont installés sur le PC d'Alexis | ouverture seulement (« J'ai ouvert la recherche… ») ; jamais « je joue » |

**Avant (sur `main`)** : les demandes de volume, luminosité, écran, Bluetooth, musique et minuteur recevaient « Je ne sais pas encore faire ça. » (route honnête du corpus) ; « quelle heure est-il ? » allait au modèle (défaut L4) ; « rappelle-moi de… » créait une tâche planifiée **quotidienne** quel que soit le moment dit (P2). Les 114 tests du sprint, joués sur une copie de `main` : **100 rouges** (10 échecs, 90 erreurs), 9 verts (les négatifs, déjà justes).

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.** Raison : le Bluetooth n'a pas pu être mesuré en réel (le PC d'Alexis n'en a pas) ; le reste est mesuré en réel.

**Runtime :** Ollama 0.40.5 ; 7 paquets WinRT 3.2.1 ajoutés (radios, Bluetooth, sessions multimédia) ; pycaw déjà présent ; mémoire, journal, habitudes d'Alexis inchangés après nettoyage C3 (§6.4).

**Chiffres :**
- **Rejeu réel** (§6) : 31 demandes, chaque annonce égale à l'état relu par le rejeu ; rappel manqué annoncé au redémarrage ; volume et luminosité d'origine remis.
- **Corpus de routes :** **417 / 418 (99,8 %)**, **0 action à tort**, 85 demandes nouvelles (dont négatifs). Plancher relevé à 99,8.
- **GB1 :** 34 demandes d'action — **12 ont maintenant un outil, 0 annonce différente de l'état relu** ; 22 toujours impossibles, toutes à la réponse honnête ; 0 affirmation sans outil ; 0 question ordinaire bloquée.
- **Suites :** sans Ollama **1 393 passés, 3 ignorés justifiés** ; avec Ollama **1 396 passés, 0 ignoré**.
- **Trouvés en chemin :** un plantage natif du son (violation d'accès, §4.3), un défaut de route ancien (« à quelle heure ferme la poste ? » → fermer une fenêtre), « Documents » et « Fichiers » absents de « tu peux faire quoi ? », deux scripts de mesure qui écrivaient dans les vraies données (§6.4).

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| CP0 — base, suite verte | `main` @ `888e362`. | PASS |
| CP1 — heure, jour, « quelle date dans 3 semaines ? » par le moteur, corpus, test à horloge figée | `core/horloge.py` ; 13 tests (horloge figée), aucun appel au modèle permis ; l'heure dite n'entre pas dans la mémoire (elle reviendrait périmée). Réel : « Il est 17 h 45. » = horloge du PC. | PASS |
| CP2 — minuteur, « dans N minutes », « demain à 9 h », « tous les lundis à 8 h » | `core/rappels.py` + `horloge.moment/recurrence`. Testé (8 formes de moment, répétition reprogrammée). Réel : minuteur de 1 min annoncé à 62 s. | PASS |
| CP2 — notification Windows et voix si active | `annonces.publier(…, parole=…)` : notification, fenêtre (`/api/annonces`), voix si le moteur vocal tourne (quelle que soit l'origine). Réel : notification et annonce relevée. | PASS |
| CP2 — lister, annuler (confirmation si plusieurs) | « quels sont mes rappels ? » ; « annule le rappel du linge » : plusieurs → choix « le 1, le 2 » ; un seul → annulé et relu. | PASS |
| CP2 — persistants ; manqué annoncé au démarrage | `data/rappels.db` (SQLite), inclus dans les sauvegardes. **Réel :** Atlas arrêté avant l'heure, redémarré après → « Tu avais un rappel à 17 h 47 que je n'ai pas pu te donner : … ». | PASS |
| CP2 — heure ambiguë → question | « à 8 h » dit à 15 h → « À 20 h ce soir, ou à 8 h demain matin ? » ; pas encore passée → aujourd'hui, sans question. Sans moment → « Quand ? ». | PASS |
| CP3 — volume : monter, baisser, N %, couper, rétablir, relu et dit | Réel : 5 demandes, annonce = relecture indépendante (§6). Windows qui ignore l'ordre : « mais il est toujours à 50 % » (testé). | PASS |
| CP3 — volume d'un programme si fiable avec pycaw | Fait : sessions audio par nom de processus, relues. Réel : Discord 100 → 90 %. | PASS |
| CP3 — pas sans valeur dans la configuration | `config/settings.json` → `competences.pas_volume` (10), `pas_luminosite` (20). | PASS |
| CP4 — luminosité portable (WMI) et externes (DDC/CI), mesurée sur les 2 écrans d'Alexis ; refus dit, visible dans doctor | Les 2 écrans d'Alexis acceptent DDC/CI (réel : 50 %, puis 70 %, relus). WMI : « non pris en charge » sur ce PC fixe (**portable non mesuré**, §7). Refus d'un écran dit, écran par écran (testé). `doctor.py --composants` : ligne « Luminosité ». | PASS (WMI : code et test seulement) |
| CP4 — « éteins l'écran » = veille de l'affichage, rien d'autre ; test sans chemin vers l'extinction | `SC_MONITORPOWER` seul (test sur le message envoyé) ; 9 phrases d'extinction ou de veille du PC → aucun outil exécuté (test) ; aucun appel d'extinction dans les modules (test sur le texte). Réel : mise en veille envoyée. | PASS |
| CP5 — allumer / éteindre, état relu | Code (WinRT `Windows.Devices.Radios`) et tests sur double. **Réel impossible : pas de radio Bluetooth** (Alexis : « pas de bluetooth sur mon pc »). Réel mesuré : le cas sans Bluetooth. | PARTIEL |
| CP5 — confirmation si clavier ou souris Bluetooth connecté, appareil nommé | Le moteur décide AVANT d'agir ; message « « X » (clavier) sera déconnecté : tu pourrais perdre la main sur ton PC ». Testé (accepté, refusé). Détection : classe d'appareil (classique) et apparence (BLE). Non mesuré en réel. | PARTIEL |
| CP5 — connecter un appareil appairé, ou reporté honnêtement | Reporté honnêtement (§4.6) : Atlas le dit, ouvre les paramètres Bluetooth. | PASS (report) |
| CP5 — PC sans Bluetooth : dit | Réel : « Ce PC n'a pas de Bluetooth utilisable : Windows ne voit aucune radio Bluetooth… ». | PASS |
| CP6.1 — commandes universelles par SMTC, mesurées en réel ; quels lecteurs publient | Réel avec Spotify : « qu'est-ce qui passe ? », pause, reprise, précédent relus ; « suivant » : titre inchangé à 2,3 s, dit tel quel. Opera GX publie aussi sa session (vu en lecture seule au début). Apple Music et Deezer : non mesurés comme lecteurs (§7). | PARTIEL |
| CP6.2 — service demandé une fois, retenu, modifiable ; ouvert par son moyen propre ; mesuré : recherche ou lecture | Demandé une fois, retenu (`apprentissage.db`, clé `musique.service`), « j'utilise Deezer maintenant ». Réel : **Spotify, Deezer : ouvrent la recherche** ; **YouTube Music : recherche dans le navigateur** ; **Apple Music : ne s'ouvre pas** (§4.7). Aucun ne lance la lecture. | PARTIEL (Apple Music) |
| CP6.2 — Atlas dit ce qu'il a fait, jamais « je joue » | « J'ai ouvert la recherche « Daft Punk » dans Spotify. À toi de choisir le morceau : je ne lance pas la lecture moi-même. » (test : aucun « je joue »). | PASS |
| CP6.3 — aucun service, ou non installé : dit, navigateur proposé | Non installé → « n'a pas l'air installé… navigateur ? » ; ne s'ouvre pas → idem ; service inconnu → YouTube Music proposé dans le navigateur. Testé. | PASS |
| CP7 — corpus ≥ 60 nouvelles (10 par compétence) et négatifs ; ≥ 99,7 %, 0 à tort | 85 nouvelles : heure 13, rappels 21, son 15, écrans 13, Bluetooth 11, musique 15, et 21 négatifs. **417 / 418, 0 à tort.** | PASS |
| CP7 — GB1 change de nature ; annoncé = relu ; impossible = honnête | Banc refait (§5.2) : 12 / 34 outillées, 0 écart ; 22 honnêtes. | PASS |
| CP7 — « tu peux faire quoi ? » depuis le registre | 4 nouvelles familles, et « Documents », « Fichiers » qui manquaient (test rouge sur `main`). | PASS |
| CP8 — dépendances fixes, doctor, sans outil tiers ; precheck signale le Bluetooth | 7 paquets `winrt-*==3.2.1` ; 4 lignes dans `--composants` ; `precheck_atlas.ps1` : ligne « Bluetooth », hors verdict. | PASS |
| CP9 — rejeu réel avec Alexis (son, écrans, Bluetooth demandé avant, musique) | §6. Bluetooth : demandé, pas de radio. | PASS |
| CP9 — suites code 0 avec et sans Ollama, GB1, corpus, C3, rapport | §5, §6.4, ce document. | PASS (voir §5.1) |

---

## 3. Architecture projet mise à jour

```
config/settings.json              « competences » : pas_volume, pas_luminosite
core/
  horloge.py                      ← NOUVEAU : heure, date, durées, moments, répétitions (déterministe)
  rappels.py                      ← NOUVEAU : minuteurs et rappels (rappels.db), surveillance, manqués
  competences.py                  ← NOUVEAU : agir, relire, dire — les 12 outils du sprint
  regles_competences.py           ← NOUVEAU : les règles du classifieur pour ces demandes
  annonces.py                     voix_active() ; publier(…, parole=…)
  intent_classifier.py            appel des règles en tête ; catégorie « competence » ; « à quelle heure… ? » = question ; ancien « rappelle-moi » (P2) retiré ; familles d'aide
  intent_engine.py                12 outils ; confirmation Bluetooth avant d'agir ; familles ; l'heure hors de la mémoire
  validator.py                    route « competence »
core_conversational/degradations.py   bascule « rappels »
main.py                           rappels.demarrer() / arreter()
requirements.txt                  winrt-* 3.2.1 (7 paquets)
tools/
  son.py                          ← NOUVEAU : pycaw, un seul fil COM, QueryInterface
  affichage.py                    ← NOUVEAU : DDC/CI, WMI, SC_MONITORPOWER
  bluetooth.py                    ← NOUVEAU : radios et appareils appairés (WinRT)
  musique.py                      ← NOUVEAU : sessions multimédia (WinRT), services, AssocQueryString
scripts/
  doctor.py                       --composants : son, luminosité, Bluetooth, musique
  precheck_atlas.ps1              ligne Bluetooth (hors verdict)
  backup_memory.py                rappels.db dans SQLITE_FICHIERS
  mesure_routes.py                données jetables quand lancé seul (C3)
  rejeu_competences.py            ← NOUVEAU : rejeu réel avec relecture indépendante
  checkup_dynamique.py, mesure_ressources.py, rejeu_apprentissage.py, rejeu_apprentissage_2.py,
  rejeu_artefacts.py, rejeu_fenetres.py, rejeu_fiabilite.py, rejeu_index.py    ATLAS_RAPPELS_DB
tests/
  test_competences_1.py           ← NOUVEAU : 114 tests
  conftest.py                     rappels.db jetable ; le vrai matériel INTERDIT (MaterielInterdit)
  gb1_mesure.py                   matériel simulé, annonce = relu, journal jetable (C3)
  fixtures/corpus_routes.json     +85 demandes ; attentes GB1 et rappels mises à jour
  fixtures/corpus_routes_plancher.json   99,8
  test_fiabilite.py, test_gter.py, test_honesty_gbis.py, test_checkup.py, test_apprentissage_2.py   adaptés (§5.3)
```

---

## 4. Détail des implémentations

### 4.1 `core/horloge.py` — le temps, sans modèle
- `maintenant()` lit `_horloge` (les tests la figent). `heure_fr`, `date_fr`, `quand_fr`, `duree_fr` écrivent en français (« 15 h 07 », « dimanche 18 octobre 2026 », « demain à 9 h », « 1 h 30 »).
- `duree()` : « 10 minutes », « 1 h 30 », « une heure et demie », « un quart d'heure ». `moment()` : « dans N », « demain à 9 h », « lundi à 8 h », « ce soir à 8 h », « le 25 octobre à 9 h » ; rend `{"quand"}`, ou `{"question", "options"}` pour une heure ambiguë, ou `{"jour_sans_heure"}`. `recurrence()` / `prochaine()` : tous les jours, en semaine, le week-end, des jours nommés.
- `question()` / `repondre()` : heure, date, date relative (« dans 3 semaines », « dans 2 mois »), « quel jour tombe le 25 décembre ? » ; l'heure d'un autre pays n'est pas inventée.

### 4.2 `core/rappels.py` — persistants
- Table `rappels` (sorte, texte, échéance, répétition JSON, origine, état actif/donné/manqué/annulé), une transaction par écriture. `ATLAS_RAPPELS_DB` pour un Atlas d'essai.
- Un fil `atlas-rappels` dort jusqu'à la prochaine échéance (30 s au plus, réveillé à chaque ajout). `verifier(au_demarrage)` : en retard de plus de 90 s au démarrage → « manqué ». **L'état est changé avant l'annonce** (trouvé au rejeu : pendant la voix, la liste montrait « il reste 0 seconde »).

### 4.3 `tools/son.py` — et le plantage trouvé au rejeu
- `regler`, `regler_programme`, `trouver_programme` : agir puis relire. Monter ou régler un volume coupé le rétablit (comme les touches du clavier).
- **Plantage natif trouvé :** le premier rejeu mourait sans trace juste après le démarrage d'Atlas. Cause, reproduite avec `faulthandler` : `ctypes.cast` sur l'interface de volume (l'exemple de la documentation de pycaw) crée un second pointeur COM sans AddRef ; les deux sont libérés → double Release → violation d'accès au ramasse-miettes. Atlas lui-même aurait pu mourir après un réglage du son. Correction : `QueryInterface`, et un seul fil COM qui ne se ferme pas ; test qui empêche le retour du motif.

### 4.4 `tools/affichage.py` — luminosité et veille
- DDC/CI : `GetPhysicalMonitorsFromHMONITOR`, `Get/SetMonitorBrightness` ; relecture jusqu'à 6 fois à 0,25 s (un écran met quelques dixièmes à appliquer). WMI par `Get-CimInstance` / `Invoke-CimMethod`.
- Veille : `PostMessageW(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)`, une seconde après la réponse (la touche Entrée relâchée ne rallume pas l'écran).

### 4.5 `core/competences.py` et `core/regles_competences.py`
- Les règles exigent l'objet de la demande (son, volume, écran, luminosité, bluetooth, musique, minuteur, rappel) : « lance discord », « mets Steam au premier plan » restent aux applications (testé). Négatifs : « éteins la lumière », « baisse le son de ta voix », « mets un rappel dans mon téléphone » → réponse honnête.
- Ce qui manque est demandé par `propositions` : durée du minuteur, moment du rappel, service de musique (réponse libre), choix (heure ambiguë, rappel à annuler).

### 4.6 Bluetooth — ce que Windows permet
- Radio : `Radio.RequestAccessAsync`, `SetStateAsync`, état relu. Claviers et souris connectés : classe d'appareil (majeur 5, mineur clavier/pointeur) et apparence BLE (15, sous-catégorie 1/2).
- **Connecter un appareil appairé : pas de moyen propre.** Les API WinRT énumèrent et décrivent les appareils, mais n'exposent pas de « connecter » pour un casque ou une enceinte depuis un programme de bureau ; le seul détour connu (`BluetoothSetServiceState`, désactiver puis réactiver un service audio) modifie l'installation des pilotes de l'appareil : écarté. Atlas le dit et ouvre `ms-settings:bluetooth`. Non vérifié sur un vrai adaptateur (le PC d'Alexis n'en a pas).

### 4.7 Musique — services
- Installé ou non : `AssocQueryStringW` (qui ouvre ce lien ?). Une clé de registre ne suffit pas : sur le PC d'Alexis, `itmss` est déclaré sans programme (« choisir une application »).
- Mesuré : `spotify:search:…` (Spotify, application de bureau) et `deezer://www.deezer.com/search/…` (Deezer, application du Store) ouvrent la recherche ; YouTube Music s'ouvre dans le navigateur. **Apple Music** (application du Store) déclare `music://` dans son manifeste, Windows l'y associe, mais ni `os.startfile`, ni l'Explorateur, ni `Start-Process` ne l'ouvrent (« fichier introuvable ») ; `cmd /c start` est resté bloqué (arrêté). Atlas dit « Je n'arrive pas à ouvrir l'application Apple Music sur ce PC » et propose `music.apple.com` dans le navigateur.

### 4.8 Ajouts hors brief (justifiés)
- Liste des capacités : « Documents » et « Fichiers » y manquaient depuis deux sprints ; un test l'exige désormais.
- « à quelle heure / quand / pourquoi … ? » : une question, jamais un ordre (trouvé par un négatif du corpus : « à quelle heure ferme la poste ? » → `window_close`).
- `mesure_routes.py` et `gb1_mesure.py` : données jetables (§6.4).

---

## 5. Résultats des tests

### 5.1 Suites complètes
```
.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
```
- **Sans Ollama** (arrêté par `Get-Process ollama*, "ollama app" | Stop-Process -Force`) : **1 393 passed, 3 skipped** (justifiés, conftest : les 3 interrogent le vrai Ollama), code 0, 593 s.
- **Avec Ollama** (0.40.5, relancé) : premier passage **3 failed, 1 393 passed** (§5.3), corrigés ; passage final : **1 396 passed, 0 ignoré**, code 0, 701 s.
- Nouveau fichier : `tests/test_competences_1.py`, **114 tests**, tous verts ; sur `main` : 100 rouges, 9 verts (négatifs).

### 5.2 Corpus de routes et GB1
```
.venv\Scripts\python.exe scripts\mesure_routes.py
.venv\Scripts\python.exe tests\gb1_mesure.py <sortie.json>
```

| Mesure | Résultat |
|---|---|
| Corpus de routes | **417 / 418 — 99,8 %**, 0 action à tort ; seul écart : « c'est quoi mon horoscope du jour ? » (connu depuis Fiabilité) |
| Familles nouvelles du corpus | heure 13/13, rappels 21/21, son 15/15, écrans 13/13, Bluetooth 11/11, musique 15/15 |
| GB1 — 34 demandes d'action | 12 avec un outil du sprint, **0 annonce ≠ état relu** ; 22 impossibles → « Je ne sais pas encore faire ça. » (sauf « active le mode avion / sombre » → description d'un mode, comme avant) |
| GB1 — affirmations sans outil | 0 |
| GB1 — 20 questions ordinaires | 0 remplacée |

Les 12 de GB1 qui ont un outil : baisse le volume, monte le son, mets le son à 50 %, tu peux baisser le volume ?, mets de la musique, règle la luminosité au maximum, baisse la luminosité de l'écran, éteins l'écran, désactive le bluetooth, mets la musique en pause, passe à la chanson suivante, mets un minuteur de 10 minutes.

### 5.3 Tests existants adaptés (comportement changé par le brief, ou trouvé)
- `test_fiabilite.py` : « rappelle-moi de boire de l'eau tous les jours à 15h » attendait `schedule_add` confirmé (P2) → `rappel_creer`, répétition quotidienne, sans confirmation.
- `test_honesty_gbis.py` : « baisse le volume » servait d'exemple d'action impossible → « coupe le wifi ».
- `test_gter.py` : **contrat changé, à valider par le superviseur.** La réponse « tu peux faire quoi ? » était plafonnée à 1 400 caractères (6 familles). Elle en fait 2 018 avec 12 familles, libellés raccourcis. Nouveau garde : chaque ligne < 300 caractères, total < 2 200. La version vocale reste < 400 (356).
- `test_checkup.py` : `comtypes` n'est plus une dépendance indirecte (importé par `tools/son.py`) → exception retirée.
- `test_apprentissage_2.py` : le garde des scripts d'essai exige aussi `ATLAS_RAPPELS_DB`.

---

## 6. Comportement observé en scénarios utilisateur réels

Atlas réel (`scripts/rejeu_competences.py`), sur des copies (mémoire, apprentissage, journal, habitudes, rappels jetables). « Relu » = lu par le rejeu lui-même, dans son propre processus, après la réponse d'Atlas.

| ID | Commande utilisateur | Résultat attendu | Résultat observé | Statut |
|---|---|---|---|---|
| R1 | quelle heure est-il ? | heure du PC | « Il est 17 h 45. » (horloge : 17 h 45) | PASS |
| R2 | on est quel jour ? / quelle date dans 3 semaines ? | calculées | « …dimanche 18 octobre 2026. » / « …dimanche 8 novembre 2026. » | PASS |
| R3 | mets un minuteur de 1 minute | lancé, puis annoncé | « …il sonnera à 17 h 46. » ; annonce « Minuteur terminé (1 minute). » à 62,2 s, notification Windows | PASS |
| R4 | rappelle-moi dans 1 minute de vérifier le rejeu AtlasEssai, puis Atlas arrêté avant l'heure | manqué annoncé au redémarrage | redémarrage 2 min 30 plus tard : « Tu avais un rappel à 17 h 47 que je n'ai pas pu te donner : vérifier le rejeu AtlasEssai. » | PASS |
| R5 | quels sont mes rappels ? (juste après la sonnerie du minuteur) | le minuteur n'y est plus | « minuteur : il reste 0 seconde » encore listé (la voix parlait) → **corrigé** (état avant l'annonce), testé | FAIL → corrigé |
| R6 | mets le son à 20 % / monte le son / baisse le volume | relu | « Volume à 20 % » (relu 20) / « 30 % » (relu 30) / « 20 % » (relu 20) | PASS |
| R7 | coupe le son / remets le son | relu | « Son coupé (le volume reste à 20 %). » (relu muet) / « Son rétabli : volume à 20 %. » (relu actif) | PASS |
| R8 | baisse le son de Discord | session relue | « …Discord est maintenant à 90 % (il était à 100 %). » ; remis à 100 % par le rejeu | PASS |
| R9 | baisse le son de ta voix | réponse honnête | « Je ne sais pas encore faire ça. » | PASS |
| R10 | mets la luminosité à 50 % | les 2 écrans, relus | « écran 1 à 50 % (il était à 100 %) ; écran 2 à 50 % (il était à 70 %). » (2,9 s) ; relu 50 / 50 | PASS |
| R11 | augmente la luminosité / quelle est la luminosité ? | +20, relu | 70 % et 70 % ; « écran 1 à 70 %, écran 2 à 70 %. » | PASS |
| R12 | éteins l'écran | veille des 2 écrans, dit non relisible | « J'envoie la mise en veille des écrans dans une seconde. Je ne peux pas le vérifier… » ; **vu par Alexis : les deux écrans se sont mis en veille et rallumés à la souris** | PASS |
| R13 | est-ce que le bluetooth est activé ? / connecte mon casque | pas de radio : dit | « Ce PC n'a pas de Bluetooth utilisable… » (les deux) | PASS |
| R14 | qu'est-ce qui passe ? (Spotify en pause) | titre et état relus | « En ce moment dans Spotify : « … » — … (en pause). » | PASS |
| R15 | mets la musique en pause (déjà en pause) | « déjà en pause » | « Pause dans Spotify : … » (vrai, mais pas « déjà ») → **corrigé**, testé | PARTIEL → corrigé |
| R16 | reprends la musique | lecture relue | « Lecture reprise dans Spotify : … » (relu : lecture) | PASS |
| R17 | passe à la chanson suivante | nouveau titre relu | « J'ai demandé le morceau suivant à Spotify, mais le titre affiché n'a pas changé (…). » — relu identique par le rejeu : honnête | PARTIEL |
| R18 | chanson précédente | nouveau titre relu | « Morceau précédent dans Spotify : « … » » (relu : ce titre) | PASS |
| R19 | mets du Daft Punk → « Spotify » | question une fois, puis recherche | « Quel service de musique utilises-tu… ? » → « J'ai ouvert la recherche « Daft Punk » dans Spotify… Je retiens Spotify… » | PASS |
| R20 | mets du Daft Punk sur Deezer | recherche Deezer | « J'ai ouvert la recherche « Daft Punk » dans Deezer… » ; processus Deezer présents ensuite ; page de recherche vue par Alexis | PASS |
| R21 | mets du Daft Punk sur Apple Music | ouvert, ou dit | 1er rejeu : message système brut (« [WinError 2]… ») → **corrigé** ; 2e : « Je n'arrive pas à ouvrir l'application Apple Music sur ce PC. Je peux ouvrir la recherche dans ton navigateur : tu veux ? » | FAIL → corrigé (Apple Music non ouvert) |
| R22 | mets du Daft Punk sur YouTube Music | recherche dans le navigateur | « J'ai ouvert la recherche « Daft Punk » dans ton navigateur sur YouTube Music… » ; page vue par Alexis | PASS |
| R23 | fin du rejeu | état d'origine | volume 100 %, non coupé ; écrans 100 % et 70 % (relus) ; Atlas arrêté proprement | PASS |

### 6.4 Règle C3 — traces de mes essais dans les vraies données

Trouvé au contrôle de fin : deux scripts de mesure, lancés hors de pytest, écrivaient dans `data/`.
- `scripts/mesure_routes.py` (4 lancements, 15 h 33–15 h 35) : **8 lignes** « automation:workflow » au journal (les modes chargés pour décrire une route) et un **`data/apprentissage.db` vide** (3 tables, 0 ligne).
- `tests/gb1_mesure.py` (18 h 12) : **16 lignes** au journal (chaque demande du banc ; probablement aussi lors des sprints précédents — les lignes « active le mode sombre » du 15/10 en ont l'allure, **non touchées**).

Retrait : sauvegarde `backup_memory.py backup` → `verify` : « RESTAURATION PROUVÉE » (`Atlas_backups\memoire\chromadb_20261018_181342`) ; journal par `nettoyer_journal.py retirer --plan … --oui` avec un plan **exact** (les 24 lignes datées du 18/10, toutes de ces deux fenêtres ; empreinte de chaque ligne) — copie du journal avant : `Atlas_backups\journal\atlas_actions_20261018_181449.jsonl` ; `apprentissage.db` vide supprimé.

| Donnée | Avant le sprint | Après mes essais | Après le retrait |
|---|---|---|---|
| Journal des actions | 757 lignes | 781 | **757** |
| `data/apprentissage.db` | absent | présent, vide | **absent** |
| Mémoire (e5 / memory / errors / conversations / documents) | 276 / 489 / 20 / 19 / 8 | identique | identique |
| `habits.db` | 142 | 142 | 142 |
| `data/rappels.db` | absent | absent | absent (tous les rappels d'essai étaient dans des bases jetables) |

Causes corrigées : les deux scripts redirigent maintenant journal et bases vers un dossier jetable (vérifié : `mesure_routes.py` relancé, journal 765 → 765).

---

## 7. Limites et risques identifiés

| Limite | Sévérité | Mitigation |
|---|---|---|
| Bluetooth jamais mesuré sur un vrai adaptateur (PC d'Alexis sans Bluetooth) : allumer/éteindre, relecture, détection des claviers et souris. | **Élevé** | Code et tests sur double ; à mesurer sur le PC d'un testeur qui a du Bluetooth (CP5 en entier). |
| Connecter un appareil appairé : reporté (pas d'API propre). | Moyen | Paramètres Bluetooth ouverts ; revoir si une API apparaît. |
| Apple Music ne s'ouvre pas depuis Atlas (`music://` sans effet depuis un programme de bureau). | Moyen | Navigateur proposé ; piste : activation d'application du Store (`IApplicationActivationManager`) — non essayée. |
| Lecteurs Apple Music et Deezer : non mesurés comme sessions multimédia (rien n'y jouait). | Moyen | À mesurer avec un morceau en cours dans chacun. |
| « suivant » sur Spotify : une fois, titre inchangé à 2,3 s (dit honnêtement) ; cause non établie (fin de file ? délai ?). | Faible | Mesurer davantage ; allonger l'attente si c'est un délai. |
| Luminosité WMI (portable) : code et test seulement, PC fixe. | Moyen | Mesurer sur un portable de testeur. |
| Veille des écrans : non relisible par nature ; un écran peut ignorer `SC_MONITORPOWER`. | Faible | Dit à chaque fois. |
| La liste des capacités grandit avec le registre (2 018 caractères) ; le plafond du test GT1 a été changé (§5.3). | Faible | Décision du superviseur ; piste : version écrite par familles, détail sur demande (comme la voix). |
| Heure d'un autre pays : non calculée (dit). | Faible | Fuseaux (`zoneinfo` + `tzdata`) si demandé. |
| Les rappels créés pendant qu'Atlas est éteint ne sont pas possibles (ils passent par Atlas). | Faible | — |

---

## 8. Checklist de validation

- [x] Heure et date par le moteur, jamais par le modèle (§2, R1-R2, tests sans modèle)
- [x] Minuteurs et rappels : dans N minutes, à une heure, jours de la semaine ; persistants ; manqués annoncés ; liste et annulation (§2, R3-R5)
- [x] Volume relu et dit ; volume par application fait ou honnêtement reporté (R6-R8 : fait)
- [x] Luminosité mesurée sur les deux écrans d'Alexis ; refus dit ; écrans en veille sans aucun chemin vers l'extinction du PC (R10-R12, tests CP4)
- [ ] Bluetooth allumé / éteint, relu ; confirmation si un clavier ou une souris Bluetooth est connecté ; connexion d'un appareil faite ou honnêtement reportée — **code et tests seulement : aucun adaptateur Bluetooth pour le mesurer** ; connexion : reportée honnêtement ; cas sans Bluetooth : mesuré (R13)
- [x] Musique : commandes universelles mesurées ; service préféré demandé une fois ; Atlas dit ce qu'il a vraiment fait (R14-R22 ; Apple Music non ouvert, dit)
- [x] Corpus ≥ 99,7 %, 0 action à tort ; GB1 mis à jour, aucune affirmation non relue (§5.2)
- [x] Rejeu réel avec Alexis pour le son, les écrans, le Bluetooth et la musique (§6 ; Bluetooth : demandé, absent)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama (§5.1)

---

## 9. Recommandations pour le sprint suivant

- **P1** — Mesurer le Bluetooth sur un PC qui en a (testeur) : allumer, éteindre, relecture, confirmation avec un vrai clavier ou une vraie souris Bluetooth.
- **P1** — Artefacts sur mesure (décision d'Alexis, sprint suivant prévu).
- **P2** — Apple Music : essayer l'activation d'application du Store ; mesurer Apple Music et Deezer comme lecteurs (SMTC).
- **P2** — Liste des capacités : décider du format écrit (plafond GT1 changé ici).
- **P2** — Tous les scripts de mesure lancés hors de pytest : un garde commun (comme `ATLAS_*` pour les rejeux) — deux écrivaient dans les vraies données.
- **P3** — « suivant » sur Spotify : mesurer le délai de publication du titre.
- **P3** — Heure d'autres fuseaux, si les testeurs la demandent.
