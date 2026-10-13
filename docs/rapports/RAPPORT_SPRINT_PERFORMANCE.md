# RAPPORT SPRINT PERFORMANCE — Atlas sur une machine ordinaire, sans perdre en qualité
Date: 13/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_PERFORMANCE.md`. Branche **`sprint-performance`**, issue de la tête de `sprint-pre-beta` (PR n° 2 ouverte, pas encore fusionnée au moment du sprint : PF0, voir §7). Commits non poussés.
> Toutes les mesures en scénario tournent sur une **copie** de la mémoire (sauvegarde du 12/10) ; la mémoire réelle n'est que lue (décomptes, requêtes de PF4).

---

## Tableau de tête — ce qu'Atlas coûte

**RAM attribuable à Atlas** (mesurée en usage, Atlas complet, 10 min d'usage mêlé) :

| | Processus Atlas | Ollama (hors modèle sur la carte) | Docker (VM WSL + conteneurs) | **Total** |
|---|---|---|---|---|
| **Avant ce sprint** | 1 310 Mo (pic 1 322) | 1 551 Mo | 1 387 Mo | **≈ 4,25 Go** |
| **Après ce sprint** | 1 298 Mo (pic 1 314) | **820 Mo** | 1 432 Mo | **≈ 3,55 Go** |
| **Projection sans Docker** (PF4) | ≈ 1 310 Mo | 820 Mo | — | **≈ 2,1 Go** |
| **Projection sans Docker, embeddings ONNX** (PF3, non appliqué) | ≈ 1 100 Mo | 820 Mo | — | **≈ 1,9 Go** |

**VRAM :** modèle de langue 4 873 Mo (`qwen2.5:7b`, `num_ctx` 8 192, 100 % carte) + transcription 213 Mo ≈ **5,1 Go**, inchangé (le cache KV `q8_0` en retirerait 211 Mo ; non appliqué, PF5.4).

**Machine minimale estimée, même qualité :** **16 Go de RAM** et une **carte NVIDIA de 8 Go** (6 Go est juste : 5,1 Go pour Atlas plus ~0,4 Go pour le bureau Windows). Calcul §6.7. La décision « pas de démo tant qu'Atlas demande 32 Go » reposait sur le sprint A : machine à 98 % de 24 Go, dont **8,3 Go** pour la VM de Docker ; elle en occupe aujourd'hui **1,4 Go**, et Atlas tout compris ≈ 3,6 Go.

---

## 1. Résumé exécutif

**Statut global : PARTIELLEMENT VALIDÉ.** Toutes les tâches sont faites et mesurées, mais deux réductions de mémoire ne sont **pas** appliquées, par la règle même du brief : les embeddings ONNX (résultats identiques, gain 253 Mo < 500 Mo exigés) et la sortie de Docker (mesure seulement). Elles attendent une décision (§9).

**Runtime :** Ollama 0.40.3 sur `127.0.0.1` ; Docker (ChromaDB, SearXNG) lancé ; Atlas lancé seulement pour les mesures, sur des copies de la mémoire.

**Chiffres :**
- **Mesure (PF1)** : tableau « qui consomme quoi » ; la somme cumulée (1 350 Mo) retombe sur Atlas observé (1 310 Mo) à **3 %** près.
- **Ce qui a vraiment baissé** : la RAM d'**Ollama**, 1 551 → 820 Mo, par la consigne réordonnée (PF5.1 : son cache de consignes n'enregistre plus d'état à chaque demande) ; **EasyOCR** ne reste plus en mémoire après usage (processus à part : 0 Mo après arrêt, contre 415 Mo gardés à vie avant).
- **Latence** : consigne évaluée en **28 ms au lieu de 270** (1 012 jetons sur 1 060 repris du cache au lieu de 566) ; première demande après démarrage **8,3 → 1,7 s** ; API prête en **16,3 s au lieu de 34,7**.
- **Qualité** : GB1 **0 affirmation sur 34**, **0 question ordinaire bloquée sur 20** (vrai modèle, consigne réordonnée) ; rappels mémoire **identiques** sur 40 requêtes (ONNX, et ChromaDB intégré) ; transcriptions **identiques** avec et sans torch.
- **Tests** : avec Ollama **1 045 passés, 4 ignorés** ; sans Ollama **1 042 passés, 7 ignorés** ; code 0. Mémoire réelle : décomptes identiques, **aucune trace**.

---

## 2. Objectifs vs réalisation

| Objectif attendu (brief) | Résultat réel | Statut |
|---|---|---|
| PF0 — `sprint-pre-beta` fusionnée dans `main`, suite verte | PR n° 2 ouverte (Alexis : « fait une PR et reprend comme d'hab ») ; branche partie de sa tête ; suite verte | PARTIEL (fusion à faire par Alexis) |
| PF1 — tableau complet, somme à 10 % du total | composants isolés, cumul dans l'ordre d'Atlas, services hors Atlas, Atlas complet en 5 scénarios ; somme 1 350 Mo pour 1 310 observés (3 %) | PASS |
| PF1 — scénario « après un cycle vocal » | **non mesuré** : un cycle ne se déclenche qu'au micro (pas d'entrée d'audio, et je n'en ajoute pas) ; modèles vocaux mesurés comme composants | PARTIEL |
| PF2 — composants rares chargés à la demande, libérés, premier usage annoncé | EasyOCR : déjà chargé au premier usage ; **libéré dans Atlas, il ne rendait rien** (mesuré) → **processus à part**, lancé au premier usage (annoncé : « Je prépare la lecture de l'écran… »), arrêté après 10 min : 0 Mo restant. torch n'est plus importé au démarrage | PASS |
| PF3 — torch / embeddings : mesuré ; appliqué seulement si identique et gain > 500 Mo | ONNX (même modèle, float32) : **40 requêtes identiques** (120 listes, écart 1e-6) ; gain **253 Mo** < 500 → **non appliqué**, code livré désactivé | PASS (règle respectée) |
| PF4 — prototype sans Docker sur copie ; SearXNG contre DuckDuckGo ; recommandation ; rien migré | ChromaDB intégré : +101 Mo, rappel 17 ms (149 en Docker), 40 requêtes identiques ; SearXNG : **0 résultat sur 15** (moteurs suspendus), DuckDuckGo 15/15 ; recommandation §9 ; rien migré | PASS |
| PF5.1 — consigne réordonnée, gain mesuré, GB1 à 0 | 497 → 37-48 jetons réévalués ; 270 → 28 ms ; GB1 0/34, 0/20 bloquées | PASS |
| PF5.2 — première demande avant / après | 8,3 → 1,7 s (20 s après démarrage) ; 19,6 s si posée dès que l'API répond (au lieu de ~30) | PASS |
| PF5.3 — `keep_alive` proposé, justifié | proposition : 5 min (§9) ; non appliqué | PASS |
| PF5.4 — `q8_0` mesuré à 8 192, appliqué seulement si justifié | −211 Mo de VRAM, latence égale, modèle déjà 100 % carte → **non appliqué** | PASS |
| PF6 — demande trop longue traitée sans couper la consigne | refus poli au-delà de **11 004 caractères**, avant toute classification, tout appel au modèle, toute écriture ; écrit, flux, voix | PASS |
| PF7 — rapport, machine minimale, suites, GB1, rejeu clavier, C3 | ce document ; 16 Go + NVIDIA 8 Go ; suites vertes ; rejeu 10/10 ; aucune trace | PASS |
| Cycle vocal au micro | pas de séance (Alexis absent du micro) | FAIL (dépend d'Alexis) |

---

## 3. Architecture projet mise à jour

```
main.py                         ← PF2 : ctranslate2 importé sans torch ; message GPU sans torch
                                  PF5.2 : prewarm() ; arrêt du processus OCR à la fermeture
config/settings.json            ← grounding.easyocr_idle_unload_s (600) ; memory.embedding_backend
                                  ("sentence-transformers") et embedding_onnx_dir
api/routes.py                   ← PF6 : refus d'une demande trop longue (écrit et flux)
core/
├── ollama_client.py            ← PF5.1 consigne réordonnée (extra_fixed) ; PF5.2 prewarm() ;
│                                 PF6 MAX_REQUEST_CHARS, too_long_reply()
├── voice_engine.py             ← PF6 : refus à la voix
├── memory_manager.py           ← PF1 : ATLAS_CHROMA_PORT (mesurer sur une copie)
└── embeddings.py               ← PF3 : moteur choisi depuis la configuration
core_conversational/memory_core.py  ← PF3 : _OnnxE5, set_embedding_backend() (désactivé)
tools/
├── grounding.py                ← PF2 : EasyOCR via processus, annonce, arrêt après inactivité
└── ocr_worker.py               ← NOUVEAU : EasyOCR dans un processus à part
scripts/
├── mesure_ressources.py        ← NOUVEAU : PF1 (machine, composants, cumul, Atlas en scénarios)
├── export_e5_onnx.py           ← NOUVEAU : PF3, export local du modèle e5
├── garde_fou_rappels.py        ← NOUVEAU : 40 rappels comparés (PF3, PF4)
└── prototype_sans_docker.py    ← NOUVEAU : PF4 (ChromaDB intégré, SearXNG / DuckDuckGo)
tests/test_performance.py       ← NOUVEAU : 18 tests
README.md                       ← nombre de tests
docs/rapports/RAPPORT_SPRINT_PERFORMANCE.md   ← NOUVEAU
```
Hors dépôt (`models/`, non versionné) : `models/embeddings/multilingual-e5-base/` (export ONNX, 1,06 Go ×2 : `model.onnx` et `model_ext.onnx(.data)`).

---

## 4. Détail des implémentations

### 4.1 PF1 — mesure
`scripts/mesure_ressources.py`, rejouable, sans rien modifier :
- `machine` : RAM/VRAM, Ollama (`ollama.exe`, `llama-server.exe`), VM WSL (`vmmemWSL`), `docker stats --no-stream` ;
- `composants` : chaque composant chargé **seul** dans un processus jetable (RSS du processus **et de ses enfants** — le `python.exe` d'un venv est un lanceur ; ma première mesure, fausse à 4 Mo partout, l'a révélé) ;
- `cumul` : un seul processus charge les composants **dans l'ordre d'Atlas** ; chaque ligne est ce qu'elle **ajoute** (rien compté deux fois) ;
- `atlas --copie` : un ChromaDB jetable sur une copie de la sauvegarde, Atlas lancé contre lui (`ATLAS_CHROMA_PORT`, ajouté pour cela), cinq scénarios et 10 min d'usage mêlé.

### 4.2 PF2 — torch et EasyOCR
- **torch au démarrage** : deux chemins l'importaient sans s'en servir. (1) Le message GPU (`torch.cuda.is_available()`) : remplacé par la lecture de `torch/version.py` (`_torch_has_cuda_build`). (2) **`ctranslate2`** (le moteur de la transcription) importe torch « au cas où » (`specs/model_spec.py`, pour **convertir** des modèles) : `main.py` l'importe dès son chargement, seul fil actif, en lui cachant torch (`_import_ctranslate2_without_torch`). Garde-fou : **transcriptions identiques** avec et sans torch sur les 5 enregistrements de test.
- **EasyOCR** : `tools/ocr_worker.py` le fait tourner dans un **processus à part** (`python -m tools.ocr_worker`, messages préfixés par leur longueur sur l'entrée/sortie standard). `grounding._ensure_easyocr()` : premier usage → annonce (notification Windows) et lancement hors de la boucle d'Atlas ; chaque usage réarme une minuterie ; après `easyocr_idle_unload_s` (600 s) → arrêt du processus ; `main.py` l'arrête à la fermeture. **Valeur de 10 min** : les clics sur un libellé viennent par rafales ; une rafale ne recharge pas (10 s) ; même durée que le `keep_alive` du modèle.

### 4.3 PF3 — embeddings sans torch (livré, désactivé)
- `scripts/export_e5_onnx.py` : export **local** du modèle déjà en cache (aucun téléchargement de modèle), float32, puis poids enregistrés **à part** (`model_ext.onnx` + `.data`). Le paquet `onnx`, nécessaire au seul export, a été installé dans un environnement **à part** (hors du venv d'Atlas).
- `memory_core._OnnxE5` : tokenisation `tokenizers` (512 jetons), ONNX Runtime (déjà présent pour le mot d'éveil), moyenne sur les jetons réels, normalisation — les étapes de sentence-transformers pour ce modèle. Choisi par `memory.embedding_backend` ; un moteur ONNX introuvable retombe sur sentence-transformers.
- **Résultat** : vecteurs identiques (écart 2,8e-7) ; 40 rappels identiques ; chargement **15,8 → 1,5 s** ; mais RAM au repos **1 343 → 1 097 Mo** seulement (−246 à −253 Mo selon la mesure). Avec les poids dans le fichier ONNX, c'était **pire** (+1 324 Mo contre +831) : ONNX Runtime charge toute la table de vocabulaire (250 000 jetons, ~770 Mo), là où torch ne rend résidentes que les lignes lues ; avec les poids à part, ils sont projetés en mémoire (+590 Mo). Réglages d'arène et d'optimisation essayés : sans effet.

### 4.4 PF4 — sans Docker (prototype)
`scripts/prototype_sans_docker.py` : les 40 requêtes vectorisées une fois, jouées avec les **mêmes vecteurs** sur ChromaDB intégré (copie) et sur le ChromaDB de Docker (mémoire réelle, **lecture seule**). Écritures mesurées sur la copie seulement. Recherche : `_search_searxng` et `_search_duckduckgo` sur 15 requêtes réelles.

### 4.5 PF5 — latence
- **5.1** `SYSTEM_PROMPT_TEMPLATE` : identité, rôle, travail, capacités, règles, `{extra_fixed}` (la consigne vocale), **puis** contexte du PC et souvenirs. `build_system_prompt(..., extra_fixed=)` ; la voix passe `VOICE_RESPONSE_SUFFIX` dans la partie fixe (avant, elle était ajoutée à la fin, après le contexte).
- **5.2** `ollama_client.prewarm()` : tâche d'arrière-plan qui charge le modèle (`/api/generate`, **même `num_ctx`** et `keep_alive` que les demandes) puis les embeddings (dans un fil) ; `main.py` la lance au démarrage, sans l'attendre.
- **5.3 / 5.4** : mesurés, non appliqués (§6.4).

### 4.6 PF6 — demande trop longue
`MAX_REQUEST_CHARS = (num_ctx − 1 024 − 3 500) × 3 = 11 004` caractères : le contexte, moins la réponse, moins la consigne la plus lourde (voix + 9 souvenirs longs, ~3 500 jetons estimés). `too_long_reply()` est appelée **en premier** par `/api/chat`, `/api/chat/stream` et le chemin vocal : « Votre demande est trop longue pour moi : N caractères, je peux en lire 11004 au plus. Raccourcissez-la, ou envoyez-la en plusieurs fois. » Rien n'est classé, exécuté, envoyé au modèle ni mémorisé. Un test vérifie que la plus longue demande admise + la consigne la plus lourde tient dans le budget.

---

## 5. Résultats des tests

### État rouge
`tests/test_performance.py` avant le code : **11 échoués, 2 en erreur, 3 passés** (16 tests à ce moment).
- **Rouges forts (4)** : `ATLAS_CHROMA_PORT` ignoré (`localhost 8001`, lancé seul avant) ; torch chargé par le message GPU (`True` au lieu de `False`) ; « RÈGLES » après la partie variable ; `main.py` sans préchauffage.
- **Rouges faibles (10)** : nom absent (`MAX_REQUEST_CHARS` ×5, `_announce` ×2, `extra_fixed`, `EASYOCR_IDLE_UNLOAD_S`, `prewarm`).
- **Pas rouges d'abord — à signaler** : les 2 tests du moteur ONNX (`_OnnxE5` écrit avant ses tests) passaient dès leur écriture ; les 2 tests du **processus OCR** (`test_pf2_le_vrai_processus_ocr…`, `test_pf2_atlas_n_importe_ni_torch…`) ont été écrits **après** le code, quand la mesure a montré que la libération dans le processus ne rendait rien.

### Suites complètes
```
.\.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
Avec Ollama : 1045 passed, 4 skipped in 164.16s (0:02:44)
Sans Ollama : 1042 passed, 7 skipped in 172.74s (0:02:52)   (Ollama arrêté, puis relancé)
```
Non-régression : aucune suite existante en échec (`test_pre_beta`, `test_depot_ollama`, `test_gter`, `test_honesty_gbis`, `test_beta_safety_g`, `test_confirmation_f`, `test_voice_*`, `test_memory_*`, `test_vision_parsers`, etc.).

---

## 6. Comportement observé en scénarios réels

### 6.1 PF1 — composants isolés (RSS, chacun seul dans son processus)

| Composant | RSS | Privée | VRAM | Chargement |
|---|---|---|---|---|
| Python nu | 14 Mo | 7 | 0 | 0,1 s |
| Atlas sans modèles (`import main`) | 132 Mo | 486 | 0 | 3,8 s |
| Fenêtre Atlas (tkinter) | 52 Mo | 31 | 0 | 1,0 s |
| torch (import seul) | 195 Mo | 560 | ~0 | 4,4 s |
| Embeddings e5 (sentence-transformers + torch) | **969 Mo** | 2 439 | ~0 | 19,8 s |
| EasyOCR (torch compris) | 457 Mo | 1 260 | ~0 | 10,1 s |
| faster-whisper base (GPU) | 439 Mo | 1 008 | **213** | 9,9 s |
| Piper | 136 Mo | 500 | 0 | 3,0 s |
| openWakeWord | 170 Mo | 880 | 0 | 3,0 s |
| Client ChromaDB | 88 Mo | 450 | 0 | 3,3 s |
| Tesseract (programme externe, pendant une lecture) | pic 43 Mo | — | — | 0,7 s |

### 6.2 PF1 — cumul dans l'ordre d'Atlas (ce que chaque étape **ajoute**)

| Étape | Avant | Après (sentence-transformers) | Après (ONNX, non appliqué) |
|---|---|---|---|
| Python | 18 | 18 | 17 |
| torch au démarrage | **175** | — | — |
| Atlas sans modèles | 83 | 115 | 114 |
| Transcription | 238 | 187 | 187 |
| Voix Piper | 94 | 95 | 96 |
| Mot d'éveil | 95 | 98 | 98 |
| Embeddings e5 | 647 | **831** (torch y revient) | **584** |
| **Total au repos** | **1 350** | **1 343** | **1 097** |
| EasyOCR, au premier clic non trouvé par Tesseract | +166 (dans Atlas, à vie) | **0 dans Atlas** (processus à part, 864 Mo pendant l'usage, 0 après) | idem |

**Somme et total** : cumul « avant » **1 350 Mo** ; Atlas complet observé au repos **1 310 Mo** : écart **3 %** (< 10 %). L'éviction de torch au démarrage ne fait rien gagner tant que sentence-transformers le recharge aussitôt (les embeddings se chargent ~5 s après le démarrage, par une écriture d'habitude).

### 6.3 PF1 — Atlas complet (copie de la mémoire), avant / après

| Scénario | Avant : RSS / VRAM machine | Après : RSS / VRAM machine |
|---|---|---|
| Au repos après démarrage | 1 310 Mo / 1 276 Mo | 1 298 Mo / **6 177 Mo** (modèle préchauffé) |
| Après une demande écrite | 1 311 / 6 164 (**8,31 s**) | 1 294 / 6 201 (**1,74 s**) |
| Après un rappel | 1 311 / 6 164 (0,24 s) | 1 294 / 6 188 (0,25 s) |
| Après un clic sur un libellé (Tesseract) | 1 326 / 6 172 (4,16 s) | 1 309 / 6 186 (3,77 s) |
| Pic sur 10 min mêlées | 1 322 / 6 189 | 1 314 / 6 187 |
| API prête après lancement | 34,7 s | **16,3 s** |
| `llama-server` (Ollama), en fin de mesure | **1 455 Mo** | **719 Mo** |
| VM WSL (Docker) | 1 387 Mo | 1 432 Mo |

**Pourquoi Ollama a baissé** : le journal d'Ollama montre **16 états** enregistrés dans son cache de consignes (~62 Mo chacun) pendant la mesure « avant », et **0** pendant « après » : la consigne réordonnée commence par une longue partie commune, Ollama réutilise son emplacement au lieu d'enregistrer un nouvel état. Cause établie par les journaux, sur une mesure de chaque.

### 6.4 PF5 — latence, sur le vrai modèle

| Mesure | Avant | Après |
|---|---|---|
| Jetons de consigne réévalués (même question deux fois) | 497 / 1 063 | **37 à 48 / 1 060** |
| Temps d'évaluation de la consigne | 270 ms | **28 ms** |
| Premier mot, modèle chaud | 0,32-0,41 s | **0,10 s** |
| Première demande, 20 s après démarrage | 8,31 s | **1,74 s** |
| Première demande, dès que l'API répond | (~30 s mesurés au pré-beta) | 19,6 s (préchauffage en cours ; embeddings 16 s) |
| `q8_0` à 8 192 : cache KV / VRAM / demande | 448 Mio / 4 873 Mo / 0,19 s | 238 Mio / 4 662 Mo / 0,20 s → **non appliqué** |

GB1 sur le vrai modèle, consigne réordonnée : **0 affirmation transmise sur 34**, **0 question ordinaire bloquée sur 20**. Les outils déclenchés (3 descriptions de mode, 2 lectures web) viennent du **classifieur**, pas du modèle : inchangés par la consigne (§7).

### 6.5 PF4 — sans Docker

| | ChromaDB dans Docker (mémoire réelle, lecture) | ChromaDB intégré (copie) |
|---|---|---|
| RAM | VM WSL 1,39 Go + conteneur 43 Mo | **+101 Mo** (client compris) |
| Rappel, 3 collections | 149 ms | **17 ms** |
| Écriture | — (non mesurée sur la vraie) | 26 ms |
| Ouverture + première requête | 0,22 s (serveur déjà ouvert) | 2,66 s |
| 40 requêtes | — | **identiques** à Docker (120 listes, écart 1e-6) |

| Recherche (15 requêtes réelles) | SearXNG (Docker) | DuckDuckGo |
|---|---|---|
| Réponses | **0 / 15** | **15 / 15** |
| Temps médian | 0,62 s (vide) | 1,46 s |
| Cause | les 5 moteurs suspendus : Google « access denied », DuckDuckGo et Startpage « CAPTCHA », Brave et Wikipédia « too many requests » ; déjà « 0 résultat » au journal le 24/09 et le 10/10 | — |
| Qualité (lue) | — | pertinente : Wikipédia (Canberra, photosynthèse), support Microsoft, sites officiels |

**Installation sans Docker** : plus de virtualisation à activer dans le BIOS (checklist §0), plus de WSL2 ni de Docker Desktop (§8), plus de `docker volume create` / `docker compose up` ; la mémoire devient un dossier (`data/chromadb`), sauvegardé par copie, Atlas arrêté (`backup_memory.py` perd `docker cp` et le conteneur jetable de `verify`, au profit d'un `PersistentClient` sur la copie).

### 6.6 Rejeu réel au clavier (Atlas sur copie, fenêtres de test à moi)

| ID | Phrase | Attendu | Observé | Statut |
|---|---|---|---|---|
| R1 | « tu peux faire quoi ? » | liste complète | liste des 6 familles, avec la restauration | PASS |
| R2 | « toi fais le » | réponse fixe | « Je ne retiens pas l'action… » (0,19 s) | PASS |
| R3 | « il consiste à quoi le mode gaming ? » | décrit, désactivé, rien lancé | étapes décrites, désactivé | PASS |
| R4 | « que sais-tu faire avec les fenêtres ? » | une famille | famille « Applications et fenêtres » | PASS |
| R5 | « baisse le volume » | réponse fixe | « Je ne sais pas encore faire ça. » | PASS |
| R6 | « tu te souviens de Discord ? » | rappel (copie) | « Je n'ai rien retenu à ce sujet » (aucun fait retenu sur Discord dans la copie) | PASS |
| R7 | 12 000 caractères | refus poli | « …12000 caractères, je peux en lire 11004 au plus… » (0,02 s) | PASS |
| R8 | « restaure AtlasEssaiRestaure » (réduite) | restaurée, premier plan | non réduite, au premier plan (Windows) | PASS |
| R9 | « ferme AtlasEssaiRestaure » | confirmation | « Confirmation requise… » ; **annulée** par moi ; fenêtre toujours là | PASS |
| R10 | « clique sur Bibliothèque dans AtlasEssaiOCR » | clic OCR | « Clic OCR sur 'bibliothèque'… confiance=96 % » | PASS |
| — | cycle vocal | — | **non fait** : pas de séance au micro | FAIL |

EasyOCR, mesuré seul (vrai modèle, processus à part) : premier usage **9,7 s, annoncé** ; lectures suivantes ~1,1 s ; Atlas 56 → 59 Mo ; processus OCR 864 Mo pendant, **0 après arrêt** ; torch jamais chargé dans Atlas.

### 6.7 Machine minimale

- **Atlas tout compris aujourd'hui** : ≈ 3,6 Go de RAM (≈ 2,1 Go sans Docker) et ≈ 5,1 Go de VRAM.
- **Windows 11 et un usage ordinaire** (navigateur, messagerie) occupent couramment 5 à 8 Go ; la machine d'Alexis, chargée (Opera GX, Discord, Steam, Wallpaper Engine…), occupe 16,3 Go sans Atlas.
- **RAM : 16 Go** pour la même qualité (8 Go + 3,6 Go d'Atlas laisserait trop peu à Windows). Avec Docker retiré : 16 Go confortables.
- **Carte : NVIDIA 8 Go** ; **6 Go juste** (5,1 Go d'Atlas + ~0,4 Go pour l'affichage), possible avec `q8_0` (−0,2 Go). Sans NVIDIA : transcription sur processeur, environ 5 s par phrase (rapport G).

### 6.8 Règle C3
Décomptes de la mémoire réelle (lecture seule) avant le sprint et après tous les essais : `atlas_memory_e5` 276, `atlas_memory` 489, `atlas_conversations` 19, `atlas_errors` 20, `atlas_documents` 8, `atlas_habits` 0, `atlas_context_apps` 0 — **identiques**. **Aucune trace à retirer** : tous les scénarios ont tourné sur des copies (`ATLAS_CHROMA_PORT`), les bancs en lecture seule.

---

## 7. Limites et risques identifiés

| # | Description | Sévérité | Mitigation |
|---|---|---|---|
| 1 | **Le préchauffage occupe 4,9 Go de VRAM dès le démarrage d'Atlas** (avant : à la première demande). Si Atlas démarre avec Windows et qu'Alexis lance un jeu aussitôt, le jeu n'a que ~2 Go pendant 10 min (`keep_alive`). | Moyen | `keep_alive` à 5 min (§9) ; à terme, ne pas préchauffer si un jeu plein écran tourne |
| 2 | **La RAM au repos d'Atlas ne baisse pas** (1 310 → 1 298 Mo) tant que sentence-transformers recharge torch. Le gain du sprint est côté Ollama (−0,7 Go) et EasyOCR. | Moyen | décision sur ONNX (§9) |
| 3 | **PF0 non achevé** : la PR n° 2 (`sprint-pre-beta`) n'était pas fusionnée ; cette branche part de sa tête. Une fusion sans changement de `main` entre-temps n'apporte aucun conflit. | Faible | fusionner la PR n° 2, puis celle-ci |
| 4 | Le scénario « après un cycle vocal » et la séance au micro ne sont pas faits. | Moyen | séance au micro d'Alexis |
| 5 | Première demande posée **dès** que l'API répond : 19,6 s (les embeddings se chargent en 16 s). | Moyen | ONNX ramène ce chargement à 1,5 s ; ou charger modèle et embeddings en parallèle |
| 6 | **Le cache de consignes d'Ollama** grossit de ~62 Mo par consigne différente, plafonné par `num_ctx` (8 192 jetons, ~0,5 Go). Mesuré à 16 états avant PF5.1, 0 après ; une consigne qui changerait souvent son début le referait grossir. | Faible | garder la partie fixe en tête (test de PF5.1) |
| 7 | **SearXNG ne rend rien** (moteurs suspendus) : chaque recherche passe déjà par DuckDuckGo. Mes 15 recherches ont pu prolonger certaines suspensions. | Faible | §9 |
| 8 | Le processus OCR communique par `pickle` sur ses tubes : sûr ici (enfant lancé par Atlas lui-même), à ne jamais ouvrir à un autre processus. | Faible | documenté dans `tools/ocr_worker.py` |
| 9 | Le classifieur envoie encore « ajoute du lait à ma liste de courses » et « résume l'histoire de Rome » vers une **lecture web** (vu au GB1 ; déjà noté au sprint Dépôt + Ollama). | Faible | sprint classifieur |
| 10 | GB1 « ordinaires » : une réponse inexacte (« baisser le volume avec F10 ») — exactitude du modèle, sans rapport avec la consigne. | Faible | — |
| 11 | L'export ONNX demande `onnx`, installé dans un environnement à part, et 2 × 1,06 Go dans `models/`. Si ONNX est adopté, l'installation chez un proche demande cette étape (ou un fichier fourni). | Faible | décision §9 |
| 12 | `num_ctx` 8 192 : la plus longue demande admise est **11 004 caractères** ; au-delà, refus. | Faible | voulu (PF6) |

---

## 8. Checklist de validation

- [x] Tableau PF1 complet, somme cohérente avec le total à 10 % près (3 %)
- [x] Composants rares chargés à la demande et libérés ; premier usage mesuré (9,7 s) et annoncé
- [x] torch / embeddings : mesuré ; **non appliqué** (résultats identiques, mais gain 253 Mo < 500)
- [x] Prototype sans Docker mesuré sur une copie ; SearXNG contre DuckDuckGo comparé ; recommandation ; **rien migré**
- [x] Consigne réordonnée, gain mesuré (270 → 28 ms), GB1 toujours à 0
- [x] Première demande après démarrage mesurée avant (8,3 s) et après (1,7 s)
- [x] `keep_alive` et `q8_0` mesurés ; non appliqués (justifié)
- [x] Demande trop longue refusée sans couper la consigne
- [x] Machine minimale estimée : 16 Go de RAM, NVIDIA 8 Go (6 Go juste)
- [x] `python -m pytest tests/ -q` → code 0, avec (1 045 / 4) et sans Ollama (1 042 / 7)
- [ ] Cycle vocal au micro — non fait (Alexis)
- [ ] PF0 — fusion de la PR n° 2 (Alexis)

---

## 9. Recommandations — décisions à prendre

1. **Sortir de Docker** (décision d'Alexis, « mesurer d'abord ») — **je recommande oui**, dans un sprint dédié :
   - gain ≈ **1,4 Go de RAM** (la VM), rappel **9× plus rapide** (17 ms contre 149), mêmes résultats sur les 40 requêtes ;
   - installation chez un proche nettement plus simple : ni virtualisation, ni WSL2, ni Docker Desktop ;
   - SearXNG n'apporte rien aujourd'hui (0/15) ; DuckDuckGo direct (15/15) suffit ;
   - à préparer : migration de la vraie mémoire sur une copie d'abord (ChromaDB 1.5.1 en pip contre 1.4.1 dans l'image : la copie a été ouverte sans erreur, à vérifier par `verify`), nouvelle procédure de sauvegarde, et la règle « jamais deux Atlas sur la même base ».
2. **Embeddings ONNX** — le garde-fou passe (résultats identiques), mais le gain RAM (253 Mo) est sous le seuil du brief. Autres effets : chargement **15,8 → 1,5 s** (la première demande « dès le démarrage » passerait, **estimation non mesurée**, de ~20 s à ~8 s : chargement du modèle 5,7 s + embeddings 1,5 s + la demande), torch plus jamais chargé dans Atlas. **À trancher par le superviseur** : le seuil de 500 Mo visait la RAM ; le gain de temps n'y était pas.
3. **`keep_alive` : 5 min** au lieu de 10. Pendant une pause, le modèle garde **4,9 Go de VRAM** : sur une carte de 8 Go, un jeu lancé pendant ce temps n'a que ~2 Go. 5 min couvrent les pauses mesurées en session (1 à 4 min) ; une pause de 5 à 10 min coûterait un rechargement de **5,5 à 6,5 s**. Non appliqué : proposition.
4. **`doctor.py`** : le seuil « ✅ à partir de 32 Go » ne correspond plus à la mesure ; proposer **16 Go**.
5. Séance au micro de 20 min pour mesurer le cycle vocal après ce sprint et le pré-beta.
