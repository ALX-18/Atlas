# RAPPORT SPRINT CHECK-UP — Chaque composant sert-il vraiment, et comme on le croit ?
Date: 14/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_CHECKUP.md`. Branche **`sprint-checkup`**, issue de `main` @ `76a6c56`. Commits non poussés.
> Annexe : `docs/rapports/RAPPORT_SPRINT_CHECKUP_ANNEXE.md` (les 151 paquets, un par ligne).

---

## Tableau de tête

| Composants inventoriés | Inventoriés | **Utilisés** (prouvé en exécution) | Repli seulement | Jamais chargés, expliqués | **Inutiles** |
|---|---|---|---|---|---|
| Paquets Python du venv | 156 | 113 | 4 (sentence-transformers et 3 dépendances) | 34 (7 outils de test et pip, 27 dépendances indirectes) | **5, retirés** |
| Programmes externes (Ollama, Tesseract, pilote NVIDIA, CUDA 12 pip, CUDA 13 d'Ollama) | 5 | 5 | — | — | 0 |
| Fichiers de modèles (`models/`, cache Hugging Face, voix, EasyOCR) | 8 | 6 | 1 (e5 au format sentence-transformers) | — | 1 (DialoGPT, 1,7 Go : décision d'Alexis) |
| Modèles Ollama | 4 | 1 (`qwen2.5:7b`) | — | — | 3 (18,8 Go : décision d'Alexis) |
| **Total** | **173** | **125** | **5** | **34** | **9** (5 retirés, 4 à décider) |

| Bascules (replis) | Avant le sprint | Après |
|---|---|---|
| Recensées au niveau composant | 20 | 20, toutes au catalogue (`core_conversational/degradations.py`) |
| **Silencieuses** (au moins un manque : journal unique avec cause, `/api/health`, `doctor.py`, dite par Atlas si vécue) | **20** | **0** |
| Repli cassé sans que personne le voie | 1 (lecture d'écran par EasyOCR, régression du sprint Performance) | 0 (corrigé, test) |

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ** — un seul critère reste ouvert : la mesure d'EasyOCR sur **GPU** (CK5) demande de télécharger torch CUDA (~3 Go, depuis download.pytorch.org, dans un venv à part). Je ne l'ai pas fait sans l'accord d'Alexis. Le reste est fait et prouvé.

**Runtime :** Ollama 0.40.3 sur `127.0.0.1` (arrêté puis relancé pour la suite « sans Ollama ») ; mémoire réelle `data/chromadb` jamais ouverte par Atlas pendant les essais (copies) ; Docker absent.

**Chiffres :**
- **CK1** : 173 composants ; mesure statique (imports) croisée avec la mesure dynamique (modules et DLL de 4 processus réels : Atlas, processus OCR, chaîne vocale, ingestion) ; 27 scénarios réels couvrant toutes les familles. **torch n'est chargé que par le processus OCR** ; sentence-transformers par aucun processus.
- **CK2** : 20 bascules recensées, **20 silencieuses avant, 0 après** : journal unique, `/api/health` (`bascules`), `doctor.py`, et dites par Atlas (notification au démarrage + première réponse, écrite et vocale).
- **CK3** : 29 clés de configuration lues par personne ; 13 retirées ou passées en commentaire, 16 gardées dans une exception justifiée (`steam_games` : la section et ses 15 jeux) ; test permanent.
- **CK4** : 15 conditions d'abandon ; tout lancé, **0 test ignoré** (4 avant) ; un test ignoré sans raison, ou dont la sonde ment, fait échouer la suite.
- **CK5** : 5 clics réels sur 30 réussis ont eu besoin d'EasyOCR (tous dans Discord, le 27/06) ; 0 clic réel la dernière semaine. EasyOCR sur processeur mesuré ; GPU **non mesuré** (accord demandé).
- **CK6** : `doctor.py --composants` (3,6 s).
- **Tests** : avec Ollama **1 062 passés, 0 ignoré** ; sans Ollama **1 059 passés, 3 ignorés justifiés** ; code 0. GB1 : **0 / 34**. Mémoire réelle : décomptes identiques, aucune trace.

---

## 2. Objectifs vs réalisation

| Objectif (brief) | Résultat réel | Statut |
|---|---|---|
| CK1 — inventaire : paquets déclarés, orphelins du venv, programmes externes, modèles, modèles Ollama | 173 composants (§4.1, annexe) | PASS |
| CK1 — colonnes : déclaré où, version, importé par, utilisé (scénario), matériel, si absent, utile ? | tableau §4.1 pour les composants déclarés et externes ; annexe pour les 151 paquets (déclaré où, version, importé par, chargé par) | PASS |
| CK1 — statique × dynamique croisés ; Atlas réel sur copie ; toutes les familles ; modules et DLL d'Atlas, du processus OCR, d'Ollama | `inventaire_composants.py` + `checkup_dynamique.py` ; 27 scénarios (§6.1) ; DLL des 5 processus (§6.4) | PASS |
| CK1 — voix au micro si Alexis est là, sinon par fichier audio | Alexis absent : par fichier audio (phrase synthétisée par la voix d'Atlas, transcrite, traitée, prononcée) (§6.2) ; le mot d'éveil, lui, écoutait le vrai micro | PASS |
| CK2 — recenser chaque repli : déclencheur, perte, qui le voit | 20 bascules de composant (§4.2) ; 320 `except` passés en revue par script ; les cascades de couches et les erreurs dites à l'utilisateur classées à part | PASS |
| CK2 — aucune dégradation silencieuse : journal une fois, health, doctor, dite si vécue | registre `degradations` ; tests sur chaque bascule ; garde permanente (catalogue ↔ appels, `except ImportError`) | PASS |
| CK3 — test permanent : chaque clé lue ; exceptions justifiées ; clé lue absente = défaut documenté | `test_ck3_*` ; `docs/CONFIGURATION.md` | PASS |
| CK4 — lister skip/skipif et leurs sondes ; nombre connu et justifié tout lancé ; skip sans raison = échec ; sondes qui ne mentent pas | 15 conditions (§4.4) ; 0 ignoré tout lancé ; garde dans `tests/conftest.py` (raison écrite ET condition réunie) | PASS |
| CK5 — journaux réels : clics Tesseract vs EasyOCR, et pourquoi | §6.5 : historique complet et dernière semaine | PASS |
| CK5 — EasyOCR CUDA contre processeur : premier usage, lecture, VRAM, taille | processeur mesuré ; **CUDA non mesuré** (téléchargement de ~3 Go sans accord) | **PARTIEL** |
| CK5 — trois options chiffrées ; aucun changement de choix | §6.6 ; (a) incomplète faute de mesure GPU ; choix inchangé | PARTIEL |
| CK5 — doctor vérifie Tesseract et `fra` ; Atlas dit au démarrage s'il manque | doctor le faisait déjà (sprint A) ; Atlas le dit désormais (notification + première réponse) et `/api/health` donne `fra` | PASS |
| CK6 — `doctor.py --composants` | présent, version, matériel, bascule, pour 13 composants ; `--json` | PASS |
| CK7 — retirer l'inutile ; rendre visibles les bascules ; relier ou retirer les clés mortes ; justifier ou rétablir les tests ignorés | 5 paquets retirés, 2 déclarés, outils de test dans `requirements-dev.txt` ; 20 bascules visibles ; 13 clés retirées, 1 exception ; 4 conditions d'abandon supprimées ou rétablies, 3 sondes Ollama unifiées | PASS |
| CK7 — `reencode_memory.py` suit `embedding_backend` | et `migrer_memoire.py`, même défaut ; test | PASS |
| CK7 — `doctor.py` : sentence-transformers en repli | rôle « repli », plus critique ; test | PASS |
| CK7 — ce qui touche une fonction : listé, pas corrigé | §7 et §9 (15 points) ; **une exception** : la régression de lecture d'écran (§4.2, §7) | PASS |
| CK8 — rapport, suites avec et sans Ollama, GB1, C3, tests rouges d'abord | §5, §6.7, §6.8 ; une exception à « rouge d'abord » (§5.3) | PASS |

---

## 3. Architecture projet mise à jour

```
core_conversational/
├── degradations.py                 ← NOUVEAU Check-up : catalogue des 20 bascules, signaler(), actives(), a_dire()
└── memory_core.py                  ← repli ONNX → sentence-transformers et « aucun moteur » signalés
core/
├── context_monitor.py              ← pywin32, pycaw, instantané des processus signalés ; repli WMI mort retiré
├── ollama_client.py                ← liste des capacités indisponible signalée
└── voice_engine.py                 ← transcription sur processeur, Piper → SAPI, muet : signalés ; la voix dit les bascules
tools/
├── grounding.py                    ← tesseract_etat() (Tesseract + fra) ; UIA, Tesseract, EasyOCR, notifications signalés
├── screen_reader.py                ← régression corrigée (EasyOCR) ; Tesseract absent signalé
├── ocr_worker.py                   ← liste de ses modules (ATLAS_MODULES_DUMP), écrite avant chaque réponse
├── window_controller.py            ← pywin32, pywinauto signalés
├── notifier.py, systray.py         ← notifications et icône indisponibles signalées
api/routes.py                       ← /api/health : bascules, tesseract fra ; /chat et /chat/stream disent les bascules
main.py                             ← _dump_modules ; tesseract_etat au démarrage ; mémoire, voix, pont, index signalés ; annonce
config/settings.json                ← 13 clés mortes retirées ou passées en commentaire
requirements.txt                    ← − aiosqlite, pydantic-settings, wmi ; + easyocr, pypdf
requirements-dev.txt                ← NOUVEAU Check-up : pytest, pytest-asyncio, pytest-cov
scripts/
├── inventaire_composants.py        ← NOUVEAU Check-up : statique, croise, markdown
├── checkup_dynamique.py            ← NOUVEAU Check-up : Atlas réel sur copie, 27 scénarios, voix par fichier, arrêt propre
├── mesure_easyocr.py               ← NOUVEAU Check-up : premier usage, lecture, mémoire, VRAM (CK5)
├── doctor.py                       ← --composants ; check_bascules ; sentence-transformers en repli ; paquets morts retirés
├── reencode_memory.py, migrer_memoire.py ← vectorisent par core.embeddings (ONNX)
tests/
├── test_checkup.py                 ← NOUVEAU Check-up : 45 tests
├── conftest.py                     ← CK4 (justification des abandons) ; registre des bascules vierge à chaque test
├── test_action_safety_b1_bis.py, test_final_v50.py, test_pre_beta.py, test_web_v20.py ← abandons rétablis
└── test_honesty_gbis.py, test_sprint_kimi_understanding_v51.py, test_vision_parsers.py ← sonde Ollama commune
docs/
├── CONFIGURATION.md                ← NOUVEAU Check-up : clés, exception, clés retirées, défauts
├── install_checklist.md            ← dépendances à jour, doctor --composants
└── rapports/RAPPORT_SPRINT_CHECKUP.md, RAPPORT_SPRINT_CHECKUP_ANNEXE.md ← NOUVEAU
```

Venv : `duckduckgo-search`, `pvporcupine`, `aiosqlite`, `pydantic-settings`, `wmi` désinstallés (`pip check` : aucune dépendance cassée).

---

## 4. Détail des implémentations

### 4.1 CK1 — l'inventaire

**Méthode.**
- *Statique* (`scripts/inventaire_composants.py statique`) : chaque distribution du venv, sa provenance (déclarée, dépendance de quel paquet déclaré — extras compris —, ou orpheline), et les fichiers qui l'importent (arbre syntaxique de tout le code, imports dans les fonctions compris).
- *Dynamique* : Atlas écrit, à sa fermeture **propre**, la liste de ses modules Python (`ATLAS_MODULES_DUMP`, `main._dump_modules`) ; le processus OCR l'écrit avant chaque réponse. `scripts/checkup_dynamique.py` lance Atlas réel sur une copie de la mémoire, joue 27 scénarios, relève les DLL de chaque processus (`psutil.memory_maps`), puis l'arrête par Ctrl+Pause sur son groupe de processus (uvicorn exécute la fermeture ; un `terminate()` tue sans fermeture). `croise` rapporte les modules chargés aux paquets.

**Composants déclarés et externes** (les 151 paquets : annexe) :

| Composant | Déclaré où | Installé | Importé ou appelé par | Réellement utilisé (scénario) | Matériel | Si absent | Utile ? |
|---|---|---|---|---|---|---|---|
| fastapi, uvicorn, starlette | requirements | 0.115.6 / 0.34.0 | `main.py`, `api/` | tout scénario (Atlas) | — | plantage au démarrage | oui |
| pydantic, httpx | requirements | 2.10.4 / 0.28.1 | `api/`, `core/` | tout scénario | — | plantage au démarrage | oui |
| psutil | requirements | 6.1.1 | 10 fichiers | « liste les processus », contexte | processeur | plantage au démarrage | oui |
| pywin32 | requirements | 308 | 6 imports, tous sous try | fenêtres, saisie, contexte | — | **bascule annoncée** (`win32`) | oui |
| comtypes | requirements | 1.4.8 | (aucun import direct) | chargé par pywinauto et pycaw | — | UIA et pycaw tombent → bascules annoncées | oui (indirect) |
| pycaw | requirements | 20240210 | `core/context_monitor.py` (try) | contexte (applications qui jouent du son) | — | bascule annoncée (`pycaw`, non vécue) | oui |
| chromadb | requirements | 1.5.1 | 9 fichiers | rappel, retenir, ingestion | disque | paquet absent : plantage au démarrage ; dossier en panne : bascule annoncée (`memoire`) | oui |
| sentence-transformers | requirements | 3.3.1 | `memory_core` (try) | **jamais** (repli si ONNX manque) | processeur (torch) | aucun repli d'embeddings si ONNX manque aussi | repli |
| onnxruntime | requirements | 1.24.3 | 3 fichiers | rappel (embeddings), mot d'éveil, voix Piper | processeur | bascule annoncée (`embeddings_onnx`) | oui |
| beautifulsoup4, lxml | requirements | 4.14.3 / 6.0.2 | `tools/web_reader.py` | « lis https://example.com » | — | bs4 : plantage au démarrage (import au niveau du module) ; lxml : lecture de page en erreur, dite | oui |
| ddgs | requirements | 9.11.3 | `tools/web_search.py` | « cherche sur internet la météo à Paris » | réseau | paquet absent : plantage au démarrage ; réseau absent : erreur dite | oui |
| playwright | requirements | 1.58.0 | `tools/browser_controller.py` | chargé (non exercé : navigateur piloté hors scénarios) | — | plantage au démarrage (import au niveau du module) | à examiner (§9) |
| pyautogui, pygetwindow, pyperclip | requirements | 0.9.54 / 0.0.9 / 1.11.0 | `tools/` | clic, saisie, fenêtres | — | plantage au démarrage | oui |
| pywinauto | requirements | 0.6.9 | 2 fichiers (try) | couche UIA de chaque clic | — | bascules annoncées (`uia`, `pywinauto_fenetres`) | oui |
| websockets | requirements | 16.0 | `tools/browser_bridge.py` | pont démarré (port 9999) | — | paquet absent : plantage au démarrage ; pont qui ne démarre pas : bascule annoncée (`browser_bridge`) | oui |
| pytesseract + **Tesseract 5.5.0** (eng, fra, osd) | requirements / installeur | 0.3.13 | 4 fichiers (try) | « clique sur Bibliothèque… » (96 %), « lis l'écran » | processeur | **bascule annoncée** (`tesseract`, `tesseract_fra`) | oui |
| easyocr (+ torch, torchvision, opencv, scikit-image…) | **non déclaré → déclaré** | 1.7.2 | `tools/ocr_worker.py` | « clique sur Introuvable… » (processus OCR) | **processeur** (torch 2.12.1, build CPU) | bascule annoncée (`easyocr`) | oui, 5 clics réels sur 30 (§6.5) |
| pypdf | **non déclaré → déclaré** | 6.14.2 | `tools/memory_ingest.py` (try) | ingestion d'un PDF (§6.3) | — | erreur dite à l'ingestion | oui |
| apscheduler, pyyaml | requirements | 3.11.2 / 6.0.3 | `core/` | « liste les tâches planifiées », modes | — | plantage au démarrage | oui |
| plyer | requirements | 2.1.0 | 3 fichiers (try) | notification « je prépare la lecture de l'écran » | — | bascule annoncée (`notifications`) | oui |
| openwakeword | requirements | 0.6.0 | `core/voice_engine.py` (try) | écoute du micro (scores calculés, aucun mot dit) | processeur (ONNX) | bascule annoncée (`voix`) | oui |
| faster-whisper (+ ctranslate2, av) | requirements | 1.2.1 | `core/voice_engine.py` | transcription du fichier audio | **GPU** (cuBLAS 12 chargé) | GPU en échec : bascule annoncée (`stt_gpu`) ; paquet absent : chaque phrase en erreur (journal, icône en erreur), non dite (§9) | oui |
| nvidia-cublas-cu12, nvidia-cudnn-cu12 | requirements | 12.9.2.10 / 9.26.0.51 | `import nvidia` | DLL chargées par ctranslate2 | GPU | transcription sur processeur, annoncée | oui |
| piper-tts | requirements | 1.4.1 | `core/voice_engine.py` | réponse prononcée | processeur | bascule annoncée (`tts_piper`) | oui |
| pyttsx3 | requirements | 2.99 | `core/voice_engine.py` | chargé ; repli SAPI non déclenché | — | bascule annoncée (`tts_muet`) | repli |
| pystray | requirements | 0.19.5 | `tools/systray.py` (try) | icône d'Atlas | — | bascule annoncée (`systray`) | oui |
| sounddevice | requirements | 0.5.5 | `core/voice_engine.py` | micro (mot d'éveil), haut-parleur | — | bascule annoncée (`voix`) | oui |
| numpy | requirements | 2.4.3 | 5 fichiers | partout | processeur | plantage | oui |
| aiosqlite, pydantic-settings, wmi | requirements | — | aucun (wmi : un repli mort) | **jamais** | — | — | **non → retirés** |
| duckduckgo-search, pvporcupine | orphelins | — | aucun | **jamais** | — | — | **non → retirés** |
| **Ollama** | installeur | 0.40.3 | `core/ollama_client.py` (HTTP) | conversation, voix | **GPU** (`ggml-cuda`, CUDA 13 fourni par Ollama) | dit à chaque demande | oui |
| Pilote NVIDIA | Windows | 616.92 (RTX 5060, 8 Go) | Ollama, ctranslate2 | conversation, transcription | GPU | modèle et transcription sur processeur | oui |
| Modèle `qwen2.5:7b` | `ollama.model` | 4,7 Go | Ollama | conversation | GPU | dit | oui |
| Modèles `qwen2.5:14b`, `mistral`, `minicpm-v` | — | 9,0 / 4,4 / 5,5 Go | aucun (vision désactivée) | **jamais** | — | — | **non : à décider par Alexis** |
| e5 ONNX (`models/embeddings/…`, 1,1 Go) | `embedding_onnx_dir` | export officiel | `memory_core` | rappel | processeur | bascule annoncée | oui |
| e5 sentence-transformers (cache HF, 2,1 Go dont la source de l'export ONNX) | — | — | `memory_core` (repli) | jamais chargé | — | — | repli |
| `hey_atlas.onnx`, faster-whisper `base`, voix `fr_FR-siwis-medium`, EasyOCR `craft` + `latin_g2` | config / scripts | — | voix, OCR | écoute, transcription, voix, OCR | — | bascules annoncées | oui |
| DialoGPT-medium (cache HF, 1,7 Go) | — | — | aucun | **jamais** (déjà signalé au sprint C) | — | — | **non : à décider par Alexis** |

**Les 38 paquets jamais chargés, expliqués :** le repli sentence-transformers (sentence-transformers, transformers, safetensors, regex) ; 7 outils (pip, pytest, pytest-asyncio, pytest-cov, coverage, pluggy, iniconfig) ; 16 dépendances de ChromaDB qui servent à son mode serveur (kubernetes, bcrypt, typer…) ; 6 d'EasyOCR et torch que nos lectures n'ont pas sollicitées (jinja2, markupsafe, networkx, ninja, pyclipper, shapely) ; 5 autres dépendances indirectes (flatbuffers, fsspec, pycparser, pypiwin32, python-dotenv). Aucune n'est retirable sans casser `pip check`.

**Un composant chargé qui ne travaille pas :** OpenCV (`cv2`, 109 Mo) est chargé dans Atlas par `pyscreeze` (dépendance de pyautogui), qu'aucun code d'Atlas n'appelle pour la reconnaissance d'image (§9, P3).

### 4.2 CK2 — les bascules (`core_conversational/degradations.py`)
- `CATALOGUE` : 20 bascules, chacune avec son composant, son déclencheur, ce que l'utilisateur perd, si elle est **vécue**, et la phrase qu'Atlas dira.
- `signaler(clé, cause)` : journal **une fois** en avertissement avec la cause ; une clé hors catalogue lève `KeyError`. `actives()` pour `/api/health` (`bascules`) et doctor. `a_dire()` / `avec_avertissements()` : la phrase de chaque bascule vécue est ajoutée **une fois** à la réponse suivante (`/api/chat`, `/api/chat/stream` dans le message du résultat, voix). `a_annoncer()` : notification Windows au démarrage (`main._annoncer_bascules`).

| Clé | Déclencheur | Perte | Vécue | Avant : qui le voyait |
|---|---|---|---|---|
| `embeddings_onnx` | modèle ONNX absent/illisible | sentence-transformers : 1er rappel ~15 s, +700 Mo, torch dans Atlas | oui | journal seulement |
| `embeddings_absents` | aucun moteur ne charge | rappels par mots-clés seulement | oui | journal seulement |
| `memoire` | dossier en panne ou tenu ailleurs | rien n'est retenu | oui | journal, health ; jamais dit |
| `tesseract` | binaire introuvable | chaque clic par EasyOCR (~20× plus lent) ; vérification après clic sautée | oui | bandeau au démarrage, health, doctor ; jamais dit ; au clic : debug |
| `tesseract_fra` | pas de langue française | libellés accentués mal lus | oui | journal, doctor ; ni health ni dit |
| `easyocr` | processus OCR ne démarre pas | libellé non lu par Tesseract = clic impossible | oui | journal seulement |
| `uia` | pywinauto ne s'importe pas | chaque clic par l'OCR | oui | journal à chaque clic |
| `pywinauto_fenetres` | pywinauto ne s'importe pas | un moyen de focus en moins | non | **rien** |
| `win32` | pywin32 ne s'importe pas | contexte du PC vide | oui | journal |
| `pycaw` | pycaw ne s'importe pas | sons non détectés dans le contexte | non | journal |
| `instantane_processus` | NtQuerySystemInformation échoue | échantillonnage par psutil, plus lent | non | debug |
| `stt_gpu` | transcription non chargeable sur GPU | ~5 s par phrase au lieu de 0,1 s | oui | journal, health, doctor ; jamais dit |
| `tts_piper` | Piper ne parle pas | voix de Windows | oui | journal, health |
| `tts_muet` | ni Piper ni SAPI | Atlas muet | oui | journal, health |
| `voix` | moteur vocal ne démarre pas | on ne peut plus parler à Atlas | oui | journal, health partiel |
| `browser_bridge` | WebSocket ne démarre pas | extension navigateur déconnectée | oui | journal |
| `file_indexer` | indexation ne démarre pas | fichiers récents introuvables | oui | journal |
| `systray` | pystray/Pillow absent | pas d'icône (état d'écoute, menu) | oui | journal |
| `notifications` | plyer absent ou refusé | avertissements à l'écran perdus | oui | journal |
| `prompt_capacites` | liste des capacités non construite | le modèle ne connaît pas les capacités | non | **rien** |

**Déjà annoncés avant le sprint (non comptés comme bascules silencieuses)** : Ollama injoignable (dit à chaque demande, health, doctor), recherche web en échec (dite), mémoire indisponible lors d'un « retiens » (dit), premier usage d'EasyOCR (notification), confirmation impossible à la voix (affichée).
**Pas des bascules, classés à part** : la cascade des couches de clic (UIA → cache → Tesseract → EasyOCR → heuristiques) est le fonctionnement prévu, et chaque résultat liste les couches tentées ; l'historique raccourci au contexte (journalisé à chaque fois, non dit : §9) ; la vision désactivée (choix de configuration) ; la charge GPU à -1 sans nvidia-smi (valeur de contexte). Les 320 `except` du code ont été passés en revue par un script ; les autres sont des erreurs renvoyées à l'utilisateur, des nettoyages ou des lectures défensives.

**Régression trouvée et corrigée (exception assumée au « fonction = plus tard ») :** depuis le sprint Performance, la lecture d'écran appelait `reader.readtext(image, detail=0)` sur le processus OCR, qui ne prend pas `detail` : l'erreur était avalée en debug, et le repli EasyOCR de « lis l'écran » ne marchait plus du tout. Test rouge, puis corrigé (le texte est pris dans les triplets renvoyés). C'est une régression de notre fait, pas une fonction nouvelle.

### 4.3 CK3 — la configuration
- `test_ck3_chaque_cle_de_settings_est_lue_par_le_code` : chaque clé (hors commentaires `_…`) doit apparaître dans une lecture `.get("clé"…)` ou `["clé"]` du code, chacune de ses clés parentes aussi.
- `test_ck3_une_cle_lue_mais_absente_a_un_defaut_documente` : une lecture sur un objet de configuration d'une clé absente du fichier doit avoir un défaut, documenté dans `docs/CONFIGURATION.md` (aujourd'hui : aucune).
- **29 clés mortes trouvées** : `assistant.*` (5 : `confirm_destructive`, `power_user_mode`… laissaient croire qu'on réglait les confirmations), `protection_rules.idle_timeout_minutes`, `memory.recall_top_k`, `memory.embedding_model`, `memory.collection_name_previous`, `automation.max_active_triggers` et `min_cooldown_seconds` (**limites annoncées, jamais appliquées**), `grounding.vision_model`, et les 15 entrées de `steam_games`.
- Retirées, ou passées en commentaire quand elles documentent (`_embedding_model`, `_collection_name_previous`) ; **exception justifiée** : `steam_games` (table de jeux d'Alexis, gardée pour le sprint qui reliera `launch_steam_game`, fonction jamais appelée).

### 4.4 CK4 — les tests ignorés (`tests/conftest.py`)
- `SKIPS_JUSTIFIES` : motif de la raison, justification, **condition** qui doit être vraie (Ollama vraiment injoignable, `ATLAS_TEST_NO_CHROMA=1`, fichier vraiment absent, pas Windows, cuBLAS pip vraiment absent).
- Hooks `pytest_runtest_logreport` / `pytest_collectreport` : chaque abandon est classé ; sans raison connue, ou condition non réunie (« la sonde est tombée sur une autre cause »), il est **fautif** et `pytest_sessionfinish` met le code de sortie à 1. Le résumé compte et liste chaque test ignoré.
- **Les 15 conditions d'avant** et leur sort :

| Où | Raison | Sonde | Sort |
|---|---|---|---|
| `test_action_safety_b1_bis` (×4) | nouvel onglet vide légitime | paramètre | **supprimé** : le cas n'est plus généré (4 abandons en moins) |
| `test_final_v50` | Atlas déjà lancé | verrou… dans un dossier temporaire, jamais tenu | **supprimé** (sonde impossible) |
| `test_pre_beta` | instantané Windows indisponible | `_process_snapshot() is None` | **rétabli** : sous Windows, c'est une assertion (l'abandon cachait un repli silencieux) |
| `test_web_v20` | `importorskip("playwright")` | import | **rétabli** : playwright est déclaré, son absence est une panne |
| `test_honesty_gbis` | Ollama injoignable | `urlopen` + `except Exception` (toute erreur = « injoignable ») | sonde commune (connexion au port, `ATLAS_TEST_NO_OLLAMA`) |
| `test_sprint_kimi…`, `test_vision_parsers` | Ollama absent | connexion au port | sonde commune |
| `test_memory_v60`, `test_memory_quality_d`, `test_beta_safety_g` | ChromaDB de test indisponible | variable `ATLAS_TEST_CHROMA_PATH` / connexion | justifié **seulement** si `ATLAS_TEST_NO_CHROMA=1` |
| `test_voice_chain_e`, `test_voice_followup_f` | modèle d'éveil / voix Piper absents | fichier | justifié seulement si le fichier manque |
| `test_doctor_verdict_g` (×2) | Windows uniquement ; cuBLAS pip absent | `os.name`, fichier | justifiés seulement si vrais |

### 4.5 CK5 — Tesseract au démarrage
`tools/grounding.tesseract_etat()` : version, langues, `fra` ; signale `tesseract` ou `tesseract_fra` ; résultat gardé (sondé au démarrage, lu par `/api/health`). Remplace l'ancienne sonde de `main.py` (`_check_tesseract`, journal seulement) et la sonde à chaque `/api/health` (`tesseract --version`, sans les langues). `doctor.py` vérifiait déjà Tesseract et `fra` (critiques) depuis le sprint A.

### 4.6 CK6 — `doctor.py --composants`
13 lignes : Ollama (version, modèles, VRAM occupée), Tesseract (fra), EasyOCR et torch (build lue dans `torch/version.py` sans importer torch), embeddings ONNX, sentence-transformers (repli), mémoire, transcription (GPU si cuBLAS chargeable **et** CTranslate2 voit un GPU, importé sans torch), Piper, mot d'éveil, pilote NVIDIA, cuBLAS/cuDNN, recherche web. Colonne « bascule » : `aucune`, ce qui arriverait si le composant manque, ou `ACTIVE : cause` si Atlas tourne (lu dans `/api/health`). `--json` pour un installeur. Et `check_bascules()` dans le diagnostic complet.

### 4.7 CK7 — corrections
- `requirements.txt` : − `aiosqlite`, `pydantic-settings`, `wmi` ; + `easyocr==1.7.2`, `pypdf>=4.0.0` (utilisés, jamais déclarés). `requirements-dev.txt` pour les tests. Venv : 5 paquets désinstallés.
- `core/context_monitor.py` : le « repli WMI » de la charge GPU ne lisait rien (boucle vide, toujours -1) : retiré avec `wmi`, sans changer le résultat.
- `reencode_memory.py` et `migrer_memoire.py` vectorisent par `core.embeddings` : ONNX, comme Atlas (avant : torch).
- `doctor.py` : sentence-transformers « repli des embeddings si le modèle ONNX manque » (avertissement, plus critique) ; onnxruntime critique (il porte les embeddings) ; rôles mis à jour.
- `docs/install_checklist.md` mis à jour.

---

## 5. Résultats des tests

### 5.1 Commandes et résultats (sur la version finale)
```
.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
```
```
Avec Ollama : 1062 passed in 205.89s (0:03:25) — atlas: tests ignorés : 0 (0 justifié(s), 0 fautif(s)) — code 0
Sans Ollama : 1059 passed, 3 skipped in 219.96s (0:03:39) — atlas: tests ignorés : 3 (3 justifié(s), 0 fautif(s)) — code 0   (Ollama arrêté puis relancé)
```
Les 3 ignorés sans Ollama, justifiés un par un :
- `test_honesty_gbis::test_gb1_vrai_modele_aucune_affirmation_transmise` : interroge le vrai modèle.
- `test_sprint_kimi_understanding_v51::test_grounding_layer_order_steam_includes_heuristic` : lit les modèles installés dans Ollama.
- `test_vision_parsers::TestGroundingTimeoutEnforced::test_layer_timeout_aborts_slow_layer` : chaque sonde du port fermé coûte 2 s.

Avant le sprint : 1 017 passés et 4 ignorés avec Ollama. Écart : +45 tests Check-up, −4 abandons structurels qui ne sont plus générés (1 017 + 4 − 4 + 45 = 1 062).

### 5.2 Non-régression, suite par suite
Toutes les suites de `tests/` sont passées dans les deux runs ci-dessus (49 fichiers `test_*.py`, aucune exclusion). Fichiers modifiés et toujours verts : `test_action_safety_b1_bis` (même couverture, sans les 4 cas ignorés), `test_final_v50`, `test_pre_beta`, `test_web_v20`, `test_honesty_gbis`, `test_sprint_kimi_understanding_v51`, `test_vision_parsers`.

### 5.3 Rouge d'abord
- Tous les tests de `test_checkup.py` ont été écrits avant le code, et lancés rouges : CK1 (`AttributeError`, puis « aucun fichier ») ; CK2 à CK7 (16 échecs et 21 erreurs au premier lancement) ; les bascules ajoutées en cours de route (instantané des processus, icône, notifications) ont chacune eu leur test rouge d'abord.
- **Exception, dite :** `test_ck3_les_exceptions_sont_justifiees_et_existent` est passé dès son premier lancement : il vérifie la liste d'exceptions écrite dans le test lui-même ; rien à implémenter pour lui.
- **Un défaut trouvé par un test vert devenu rouge :** `test_ck1_le_processus_ocr_ecrit_ses_modules_meme_tue` a échoué une fois sur la suite sans Ollama : le processus OCR écrivait sa liste **après** sa réponse, le parent pouvait le tuer au milieu de l'écriture. Corrigé (écrit avant de répondre, par fichier temporaire puis renommage), 5 passages d'affilée, puis les deux suites complètes relancées.

---

## 6. Comportement observé en scénarios réels

### 6.1 Atlas réel, copie de la mémoire, toutes les familles (`checkup_dynamique.py`, version finale)
API prête en 11,6 s ; arrêt **propre** (Ctrl+Pause) ; bascules au départ et à la fin : **aucune** ; Tesseract 5.5, `fra` : oui.

| ID | Famille | Demande | Attendu | Observé | Statut |
|---|---|---|---|---|---|
| D1 | écrit | « tu peux faire quoi ? » | réponse fixe | liste complète (0,32 s) | PASS |
| D2 | écrit | « quelle est la capitale de l'Italie ? » | Ollama | « Rome » (0,94 s) | PASS |
| D3 | rappel | « tu te souviens de Discord ? » | rappel e5 ONNX | « rien retenu » (0,21 s) | PASS |
| D4 | rappel | « retiens que mon essai… porte le numéro 7 » | écrit dans la copie | noté (0,23 s) | PASS |
| D5 | rappel | « quel est le numéro de mon essai de check-up ? » | rappel | **diagnostic système** (mauvaise route) | FAIL (§7) |
| D6 | recherche | « cherche sur internet la météo à Paris » | DuckDuckGo | Météo-France en tête (1,73 s) | PASS |
| D7 | recherche | « résume la page https://example.com » | lecture de la page | **lecture de l'écran** à la place | FAIL (§7) |
| D8 | recherche | « lis https://example.com » | lecture de la page | « Example Domain » résumé (2,24 s) | PASS |
| D9 | système | « quel est l'état de mon ordinateur ? » | état | réponse du modèle avec le contexte (2,25 s) | PASS |
| D10 | système | « liste les programmes en cours » | processus | **`read_url` sur cette phrase**, erreur | FAIL (§7) |
| D11 | système | « liste les processus » | processus | liste (5,59 s) | PASS |
| D12 | fenêtres | « liste les fenêtres ouvertes » | liste | liste | PASS |
| D13 | fenêtres | « restaure AtlasEssaiRestaure » | restaurée | restaurée, premier plan (3,23 s) | PASS |
| D14 | fenêtres | « ferme AtlasEssaiRestaure » | confirmation | demandée, **annulée par moi** | PASS |
| D15 | OCR Tesseract | « clique sur Bibliothèque dans AtlasEssaiOCR » | Tesseract | clic, confiance 96 % (3,47 s) | PASS |
| D16 | OCR EasyOCR | « clique sur Introuvable dans AtlasEssaiOCR » | Tesseract échoue → EasyOCR | EasyOCR lancé (premier usage annoncé), introuvable dit (12,9 s) | PASS |
| D17 | fenêtres | « mets AtlasEssaiOCR au premier plan » | premier plan | déjà active | PASS |
| D18 | écran | « lis l'écran » | lecture | « la fenêtre affiche Bibliothèque » (1,87 s) | PASS |
| D19 | saisie | « écris bonjour checkup dans AtlasEssaiSaisie » | texte arrivé | « bonjour checkup » lu dans ma fenêtre | PASS |
| D20 | modes | « il consiste à quoi le mode gaming ? » | décrit | décrit, rien lancé | PASS |
| D21 | modes | « lance le mode travail » | confirmation | demandée, **annulée** | PASS |
| D22 | planification | « liste mes tâches planifiées » | liste | **`read_url`**, erreur | FAIL (§7) |
| D23 | planification | « liste les tâches planifiées » | liste | 2 tâches | PASS |
| D24 | planification | « rappelle-moi de boire de l'eau tous les jours à 15h » | planifier | **rappel mémoire** à la place | FAIL (§7) |
| D25 | planification | « planifie de boire de l'eau tous les jours à 15h » | confirmation | demandée, **annulée** | PASS |
| D26 | applications | « ouvre la calculatrice » | lancée | lancée… **3 fois** (relances quand la vérification échoue) ; fermées par le script | FAIL (§7) |
| D27 | écrit (flux) | « dis bonjour en trois mots » | `/chat/stream` | « Salut tout le monde. » (1,03 s) | PASS |

Les FAIL sont des **défauts de fonction** trouvés par l'inventaire, listés pour un sprint ultérieur (CK7 : « tout ce qui touche à une fonction est listé ») ; chaque famille a aussi un scénario qui passe par son outil.

### 6.2 Voix par fichier audio (Alexis absent)
Phrase « Quelle est la capitale de l'Espagne ? » synthétisée par la voix d'Atlas (Piper), passée à la chaîne d'Atlas (processus séparé démarré comme Atlas, même copie de la mémoire) :
- transcription exacte en **2,08 s** (premier usage, chargement compris), **sur GPU** (`device_used: cuda`, `cublas64_12.dll` chargée) ;
- pipeline : « La capitale de l'Espagne est Madrid. » (2,81 s) ;
- réponse prononcée par Piper (5,19 s, durée de la phrase).

Le mot d'éveil, lui, a écouté le vrai micro pendant tout le §6.1 (modèle chargé, scores calculés, aucun mot dit).

### 6.3 Ingestion d'un PDF (preuve de pypdf)
PDF d'une page ingéré dans une copie de la mémoire par le chemin d'`/api/memory/ingest` : « 1/1 chunks ingérés », pypdf chargé.

### 6.4 Modules et DLL des processus (Atlas en fin de scénarios)
| Processus | RSS | Ce qu'il charge (preuve) |
|---|---|---|
| Atlas | 1 137 Mo | ONNX Runtime, ctranslate2, cuDNN 9, chromadb, PortAudio, PyAV ; **ni torch ni sentence-transformers** |
| Processus OCR | 587 Mo | `torch_cpu.dll`, `c10.dll`, torchvision, easyocr (build processeur) |
| Ollama `llama-server` | 754 Mo | `ggml-cuda.dll`, `cublas64_13.dll` (CUDA 13 fourni par Ollama) : GPU |
| Ollama `ollama.exe`, application | 57 / 46 Mo | — |
| Chaîne vocale (fichier audio) | — | ctranslate2 + **cuBLAS 12** + cuDNN 9, Piper (`espeakbridge`), ONNX Runtime ; **sans torch** |

Première mesure de la chaîne vocale : torch y apparaissait. C'était mon harnais : il n'importait pas `ctranslate2` comme `main.py` (en lui cachant torch). Corrigé (`import main` en tête), torch a disparu.

### 6.5 CK5 — combien de clics passent par quelle couche (`data/atlas_actions.jsonl`)
- **Dernière semaine (07 → 14/10)** : **0 clic réel** d'Alexis ; les 10 clics de la semaine sont mes fenêtres de test.
- **Tout l'historique (26/03 → 14/10)**, hors mes fenêtres de test : 76 demandes de clic. Réussis avec couche connue : **Tesseract 21, EasyOCR 5, cache 3, heuristique Electron 1** (13 autres réussis sans couche journalisée, format ancien ; 33 échecs).
- **Les 5 passages par EasyOCR** : tous dans **Discord, le 27/06** (thème sombre, libellés courts, noms de contacts, l'icône des paramètres) : Tesseract n'avait rien trouvé, EasyOCR a réussi (11 à 14 s par demande). Steam (Bibliothèque, Magasin, Communauté) passe par Tesseract (3,5 à 6,5 s).

### 6.6 CK5 — EasyOCR : mesures et trois options
Mesures `scripts/mesure_easyocr.py` (images synthétiques, aucune capture de l'écran d'Alexis), torch 2.12.1 build processeur :

| | Processeur (mesuré) | GPU (CUDA) |
|---|---|---|
| Premier usage (lancement du processus et du lecteur) | **9,7 s** (annoncé) | **non mesuré** |
| Lecture d'une fenêtre 460 × 220 | **0,56 s** | non mesuré |
| Lecture d'un écran 1920 × 1080 | **8,7 s** | non mesuré |
| Mémoire du processus OCR | 584 Mo après lectures de fenêtres (CK1) ; **2,8 Go** après lectures d'écran 1080p ; rendue après 10 min d'inactivité | non mesuré |
| VRAM ajoutée | 0 | **non mesurée — le chiffre décisif** : Atlas occupe déjà 5,1 Go sur 8 |
| Installation | torch 526 Mo + OpenCV 109 + scikit-image 25 + networkx 18 + torchvision 15 + easyocr 16 + petits (~10) ; modèles EasyOCR 94 Mo | torch CUDA : téléchargement d'environ 3 Go (wheel cu128, exigée par la RTX 5060) |

| Option | Gain | Coût | Ce qui change pour Alexis |
|---|---|---|---|
| **(a) EasyOCR sur GPU** | lectures plus rapides (à mesurer) | ~3 Go de téléchargement, plusieurs Go installés ; **VRAM ajoutée inconnue** sur une carte déjà occupée à 5,1/8 Go ; chez un proche sans NVIDIA, retour au processeur | les 17 % de clics difficiles plus rapides, si la VRAM tient |
| **(b) EasyOCR sur processeur** (aujourd'hui) | rien à faire ; marche sur toute machine | ~0,8 Go installés ; 10 s au premier usage (annoncé) ; 0,6 s par fenêtre, 8,7 s par écran 1080p ; jusqu'à 2,8 Go de RAM tant que le processus vit | Discord et les cas difficiles marchent, lentement |
| **(c) EasyOCR retiré, et torch avec lui** | ~0,84 Go de venv en moins (+ 94 Mo de modèles) ; installation plus simple ; plus aucune RAM d'OCR | **5 clics réels sur 30 réussis (17 %, Discord) auraient échoué** ; « lis l'écran » sans repli ; et **le repli des embeddings disparaît** (sentence-transformers exige torch) | clics dans Discord en échec, dits ; mémoire sans repli si l'ONNX manque |

**Aucun changement de choix** dans ce sprint : (b) reste en place. Recommandation : décider après la mesure GPU (VRAM surtout).

### 6.7 GB1 (banc `tests/gb1_mesure.py`, vrai modèle, mémoire en lecture seule)
34 demandes d'action : **0 affirmation transmise** sans outil (28 réponses fixes « Je ne sais pas encore faire ça. »). 20 questions ordinaires : **0 bloquée** (1 au sprint Sans Docker : variance du modèle, la garde n'a pas changé).

### 6.8 Règle C3
- Mémoire réelle (`data/chromadb`), après tous les essais : 276 / 489 / 20 / 19 / 8 / 0 / 0 : **identique** au sprint Sans Docker. Tous les scénarios sur des copies ; banc GB1 en lecture seule. **Aucune trace à retirer.**
- Hors mémoire : `data/habits.db` modifié par chaque passage d'Atlas réel (trace de mes essais) : **remis tel quel** par le script (empreinte vérifiée identique après) ; `schedules.json`, `triggers.json`, `workflows/`, `file_index.json` : inchangés. Les Calculatrices ouvertes par Atlas (D26) : fermées. Journaux (`logs/atlas.log`, `data/atlas_actions.jsonl`) : mes lignes restent, reconnaissables (« AtlasEssai… »).

---

## 7. Limites et risques identifiés

| # | Description | Sévérité | Mitigation |
|---|---|---|---|
| 1 | **EasyOCR sur GPU non mesuré** (CK5 a) : il faut télécharger torch CUDA (~3 Go) dans un venv à part ; pas fait sans accord. | Moyen | Accord d'Alexis ; `scripts/mesure_easyocr.py` lancé avec l'interpréteur de ce venv donne le même tableau ; le venv est jetable. |
| 2 | **Phrasés naturels mal routés** (D5, D7, D10, D22, D24) : « résume la page <url> » lit l'écran ; « liste les programmes en cours » et « liste mes tâches planifiées » partent en `read_url` ; « rappelle-moi de… à 15h » devient un rappel mémoire ; « quel est le numéro de… » un diagnostic. | Moyen | Fonctions (classifieur) : sprint ultérieur, P1. |
| 3 | **`launch_app` relance quand sa vérification échoue** : 2 puis 3 Calculatrices ouvertes pour une demande (`retry_count` 2). | Moyen | Fonction : P1. |
| 4 | Régression de la lecture d'écran (EasyOCR) **corrigée dans ce sprint** alors qu'elle touche une fonction (écart au brief, assumé : régression de notre fait, silencieuse). | Faible | Test ; le superviseur peut demander de la sortir. |
| 5 | `doctor.py` ne voit les bascules **en cours** que si Atlas tourne (il lit `/api/health`) ; hors Atlas, il vérifie les conditions (ONNX, EasyOCR, UIA, Piper, Tesseract, cuBLAS…). | Faible | Documenté ; c'est le seul endroit où elles existent. |
| 6 | Le test CK3 reconnaît une lecture de configuration au nom de la variable ; une lecture par une variable au nom quelconque lui échappe. | Faible | Limite écrite dans `docs/CONFIGURATION.md`. |
| 7 | La phrase d'une bascule vécue s'ajoute à la **réponse suivante**, quelle qu'elle soit (une fois). | Faible | Voulu (« au moins à la première occurrence ») ; registre remis à zéro à chaque test. |
| 8 | 3 modèles Ollama inutilisés (18,8 Go) et DialoGPT (1,7 Go, déjà signalé au sprint C) : pas supprimés (« rien ne s'efface sans l'accord d'Alexis »). | Faible | Décision d'Alexis : `ollama rm qwen2.5:14b mistral minicpm-v` ; dossier `models--microsoft--DialoGPT-medium`. |
| 9 | Voix testée par fichier, pas au micro (Alexis absent) ; mot d'éveil chargé et à l'écoute, jamais déclenché. | Faible | Séance au micro quand Alexis est là. |
| 10 | Clés `automation.max_active_triggers` / `min_cooldown_seconds` retirées : ces limites **n'ont jamais été appliquées** ; aucune limite n'existe aujourd'hui. | Moyen | Fonction : P2. |
| 11 | `requirements-mac-compagnon.txt` liste encore `aiosqlite` et `pydantic-settings` (autre produit, hors périmètre). | Faible | À vérifier au sprint du compagnon. |

---

## 8. Checklist de validation

- [x] Tableau CK1 complet, statique et dynamique croisés, chaque ligne prouvée par un scénario (§4.1, annexe, §6.1 à §6.4)
- [x] Toutes les bascules recensées ; aucune silencieuse restante (journal, health, doctor, et Atlas quand c'est vécu) (§4.2, tests `test_ck2_*`)
- [x] Test permanent des clés de configuration (`test_ck3_*`)
- [x] Tests ignorés comptés et justifiés un par un ; un test ignoré sans raison fait échouer la suite (§4.4, §5.1, `test_ck4_*`)
- [ ] torch / EasyOCR / Tesseract : trois options chiffrées, aucun changement de choix — **choix inchangé, options présentées ; (a) non chiffrée faute de mesure GPU** (§6.6, §7.1)
- [x] `doctor.py --composants` (§4.6, `test_ck6_doctor_composants_json`)
- [x] Composants inutiles retirés ; ce qui touche une fonction listé pour la suite (§4.7, §7, §9)
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; GB1 à 0 (§5.1, §6.7)

---

## 9. Recommandations pour le sprint suivant

**P1 — fiabilité**
- Mesurer EasyOCR sur GPU (accord pour ~3 Go), puis trancher (a), (b) ou (c) ; c'est la VRAM qui décide.
- Classifieur : les 5 phrasés du §6.1 (URL avant « résume la page », « liste … en cours », « tâches » accentué, « rappelle-moi de … à 15h » vers la planification, questions sur un fait retenu vers le rappel).
- `launch_app` : ne pas relancer une application dont la vérification a échoué (instances multiples).

**P2 — robustesse**
- Appliquer, ou décider de ne pas avoir, les limites d'automatisation (`max_active_triggers`, `min_cooldown_seconds`).
- Relier `steam_games` à `launch_steam_game` (« lance Elden Ring »), ou retirer les deux.
- Historique raccourci au contexte : le dire à l'utilisateur quand il l'est (aujourd'hui : journal seulement).
- faster-whisper absent : la voix échoue à chaque phrase sans le dire ; en faire une bascule annoncée au démarrage.
- `playwright` (navigateur piloté) : chargé au démarrage, jamais exercé dans les scénarios ; vérifier son usage réel.

**P3 — performance, ménage**
- OpenCV (109 Mo) chargé dans Atlas par `pyscreeze` sans servir.
- Cache Hugging Face d'e5 (2,1 Go) : la source ONNX y double l'export de `models/` ; à nettoyer si le repli sentence-transformers reste.
- Modèles Ollama et DialoGPT inutilisés (§7.8), à la décision d'Alexis.
