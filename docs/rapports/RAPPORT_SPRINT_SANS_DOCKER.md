# RAPPORT SPRINT SANS DOCKER — La mémoire dans Atlas, l'installation simplifiée
Date: 14/10/2026
Agent: Claude Opus 5.5 (CHAT6, Claude Code Windows)

> Brief : `docs/briefs/BRIEF_SPRINT_SANS_DOCKER.md`. Branche **`sprint-sans-docker`**, issue de `main` @ `6e7e949` (PR n° 2 et Performance fusionnées : SD0). Commits non poussés.
> Accords d'Alexis, dans la conversation : migrer la vraie mémoire (« 1 oui »), télécharger l'export ONNX officiel (« tu peux le télécharger seul ? »), quitter Docker Desktop pour le démarrage réel (« yes »).

---

## Tableau de tête

| | Avant le sprint Performance | Après Performance (Docker) | **Après ce sprint (sans Docker)** |
|---|---|---|---|
| **RAM du processus Atlas**, au repos | 1 310 Mo | 1 298 Mo | **1 087 Mo** |
| RAM d'Ollama (hors modèle sur la carte) | 1 551 Mo | 820 Mo | 821 Mo |
| RAM de Docker (VM WSL + conteneurs) | 1 387 Mo | 1 432 Mo | **0** (VM éteinte) |
| **RAM attribuable à Atlas, au total** | ≈ 4,25 Go | ≈ 3,55 Go | **≈ 1,9 Go** |
| VRAM (modèle 8 192 + transcription) | 5,1 Go (à la 1re demande) | 5,1 Go (dès le démarrage) | 5,1 Go (dès le démarrage) |
| API prête après le lancement | 34,7 s | 16,3 s | **10,7 à 13,8 s** |
| Première demande, posée **dès** que l'API répond | — | 19,6 s | **5,3 s** |
| Première demande, posée 20 s après | 8,3 s | 1,7 s | **1,45 s** |
| Chargement des embeddings | 15,8 s | 15,8 s | **1,5 s** |

Machine minimale pour la même qualité : **16 Go de RAM et une NVIDIA de 8 Go** (12 Go et 6 Go « justes »), désormais vérifiée par `doctor.py`.

---

## 1. Résumé exécutif

**Statut global : VALIDÉ** (sous réserve du superviseur).

**Runtime :** Docker Desktop **arrêté** pendant les mesures et les scénarios réels (VM WSL éteinte d'elle-même) ; Ollama 0.40.3 sur `127.0.0.1`. La vraie mémoire vit dans `data/chromadb/` ; le volume Docker `atlas_chromadb_data` est **intact** (jamais modifié ni supprimé), repli.

**Chiffres :**
- **SD1** : copie puis vraie mémoire migrée de ChromaDB 1.4.1 (Docker) vers 1.5.1 intégré : 7 collections, identifiants, documents, métadonnées identiques, vecteurs à 2e-8, **40 requêtes identiques** (120 listes, 0 différence).
- **SD2** : un dossier, un client par processus, **aucun appel réseau** ; verrou : un second processus trouve la base « verrouillée », Atlas refuse de démarrer et dit pourquoi.
- **SD3** : `backup` / `verify` / `restore` sans Docker, de bout en bout ; `memory_cleanup` sur la nouvelle base.
- **SD4** : SearXNG et `docker-compose.yml` retirés ; DuckDuckGo direct, un échec dit ; aucun appel restant à `:8001` ou `:8888` (recherche dans le code, testée).
- **SD5** : **export ONNX officiel** téléchargé et préparé par `download_voice_models.py` (aucun export à la main) ; 40 requêtes identiques sur la mémoire migrée ; **torch absent du processus Atlas** (prouvé par les DLL chargées), présent seulement dans le processus OCR.
- **SD6** : `keep_alive` 5 min ; `doctor.py` 16 Go / 12 juste, NVIDIA 8 Go / 6 juste, plus de Docker ni de virtualisation.
- **Une régression du sprint Performance trouvée en réel et corrigée** : le premier usage d'EasyOCR échouait toujours (§7.1).
- **Tests** : avec Ollama **1 017 passés, 4 ignorés** ; sans Ollama **1 014 passés, 7 ignorés** ; code 0, Docker arrêté. GB1 : **0 affirmation sur 34** ; **1 question ordinaire bloquée sur 20** (faux positif de la garde, §7.2).
- **Mémoire réelle** : décomptes identiques avant et après le sprint ; **aucune trace**.

---

## 2. Objectifs vs réalisation

| Objectif (brief) | Résultat réel | Statut |
|---|---|---|
| SD0 — PR pré-beta et Performance fusionnées, suite verte | fusionnées (`ec02b91`) ; suite verte | PASS |
| SD1 — compatibilité 1.4.1 → 1.5.1 ; version épinglée | copie et vraie mémoire ouvertes par 1.5.1 sans erreur, tout identique ; `chromadb==1.5.1` déjà épinglé dans `requirements.txt` | PASS |
| SD1 — copie migrée : décomptes, ids, métadonnées, vecteurs, 40 requêtes | identiques (§6.1) | PASS |
| SD1 — vraie mémoire migrée après le « oui » ; volume Docker intact | migrée après « 1 oui » ; contrôle identique ; `atlas_chromadb_data` listé intact | PASS |
| SD2 — `PersistentClient`, un client, aucun réseau | `open_client()` ; test qui fait échouer tout `HttpClient` | PASS |
| SD2 — un seul Atlas sur la base, testé | verrou OS à l'ouverture (`<dossier>.lock`, rendu à la fin du processus) ; `main.py` refuse sur « verrouillee » | PASS |
| SD2 — tests sur une mémoire jetable, jamais `data/chromadb` ; garde `ATLAS_MEMORY` | `conftest` : dossier temporaire ; `PersistentClient` refuse la vraie base ; `HttpClient` lève | PASS |
| SD2 — `/api/health` distingue ok / neutralisée / en panne | `services.memoire.etat` ∈ ok, neutralisee, verrouillee, en_panne | PASS |
| SD3 — `backup` cohérent (verrou), `verify` (décomptes + 40 requêtes), `restore` testé, `memory_cleanup` | de bout en bout sur copie ; refus si la base est tenue ; sauvegarde altérée refusée | PASS |
| SD4 — DuckDuckGo direct, échec dit ; compose retiré ; doctor sans Docker, vérifie le dossier ; aucun appel restant ; démarrage réel Docker arrêté | tout fait ; démarrage réel et 11 scénarios Docker arrêté (§6.3) | PASS |
| SD5 — ONNX par défaut, sans export manuel ; 40 requêtes ; mesures ; torch seulement dans l'OCR | voie (b) : export officiel ; tout prouvé (§6.2, §6.4) | PASS |
| SD6 — `keep_alive` 5 min partout ; seuils doctor | `settings.json`, `ollama_client`, `LLMClient` ; seuils testés | PASS |
| SD7 — documentation sans Docker, chaque phrase vraie, désinstallation | README, INSTALLATION_ALEXIS, install_checklist, GUIDE_TESTEUR | PASS |
| SD8 — tableau, démarrage réel, suites avec / sans Ollama, GB1, C3 | ce document | PASS (GB1 : §7.2) |

---

## 3. Architecture projet mise à jour

```
core/memory_manager.py              ← SD2 : CHROMA_PATH, acquire_memory_lock, open_client, status()
core_conversational/memory_core.py  ← SD2 : ConversationalMemory sur un dossier ; LLMClient keep_alive 5 min
core_conversational/llm_client.py   ← SD6 : keep_alive 5 min
core/ollama_client.py               ← SD6 : KEEP_ALIVE par défaut 5 min
main.py                             ← SD2 : refus de démarrer sur une base verrouillée
api/routes.py                       ← SD2/SD4 : /api/health → services.memoire ; plus de sonde SearXNG
tools/web_search.py                 ← SD4 : DuckDuckGo direct, échec dit
tools/grounding.py                  ← régression corrigée : _layer_timeout (premier chargement d'EasyOCR)
config/settings.json                ← memory.chroma_path, embedding_backend "onnx", keep_alive "5m" ; plus de chroma_host/port ni searxng
scripts/
├── migrer_memoire.py               ← NOUVEAU (SD1)
├── backup_memory.py                ← SD3 : réécrit (dossier, verrou, manifeste, verify, restore)
├── memory_cleanup.py, memory_inventory.py, reencode_memory.py   ← SD3 : base intégrée, verrou
├── download_voice_models.py        ← SD5 : download_e5_onnx (export officiel, poids à part)
├── doctor.py                       ← SD4/SD6 : check_memory ; seuils ; plus de Docker ni de virtualisation
├── mesure_ressources.py            ← base intégrée, copie par ATLAS_CHROMA_PATH
└── export_e5_onnx.py               ← RETIRÉ (remplacé par l'export officiel)
docker-compose.yml, config/searxng/ ← RETIRÉS
tests/
├── test_sans_docker.py             ← NOUVEAU : 24 tests
├── conftest.py                     ← SD2 : mémoire jetable par dossier ; gardes
├── test_backup_memory_guard.py, test_compose_config.py   ← RETIRÉS (52 tests sur Docker)
└── test_chroma_integration, test_memory_v60, test_memory_quality_d, test_isolation, test_final_v50,
    test_web_v20, test_doctor_verdict_g, test_v53_migration, test_performance   ← adaptés (§5)
README.md, docs/beta/INSTALLATION_ALEXIS.md, docs/beta/GUIDE_TESTEUR.md, docs/install_checklist.md   ← SD7
```
Hors dépôt : `data/chromadb/` (la mémoire, ignorée par Git), `models/embeddings/multilingual-e5-base/` (ONNX préparé, ignoré).

---

## 4. Détail des implémentations

### 4.1 SD1 — migration
`scripts/migrer_memoire.py` : la source est **toujours** une sauvegarde vérifiée (`data/` + rapport `verify_*.json`, sinon refus). `essai` copie dans un dossier jetable ; `vraie --oui` copie vers `data/chromadb/` (refus si le dossier existe et n'est pas vide). Contrôle contre la mémoire dans Docker, **lue** seulement (HTTP) : collections, décomptes, identifiants, documents, métadonnées, métadonnées de collection, vecteurs (écart max), puis les 40 requêtes avec les mêmes vecteurs des deux côtés. Code de sortie 1 au moindre écart. La migration est une simple copie du dossier de persistance : ChromaDB 1.5.1 ouvre sans erreur le format écrit par 1.4.1.

### 4.2 SD2 — ChromaDB intégré
- `CHROMA_PATH` = `memory.chroma_path` (défaut `data/chromadb`), ou `ATLAS_CHROMA_PATH` (tests, mesures sur copie).
- `acquire_memory_lock(path)` : verrou du système (`msvcrt.locking` sous Windows, `flock` ailleurs) sur `<dossier>.lock`, octet verrouillé loin du contenu pour que le numéro du processus reste lisible, gardé toute la vie du processus, rendu automatiquement à sa fin.
- `open_client(path)` : un `PersistentClient` par dossier et par processus, verrou pris, télémétrie coupée, `allow_reset=False`.
- `MemoryManager.status()` : `ok`, `neutralisee` (`ATLAS_MEMORY≠real`), `verrouillee` (un autre processus tient la base : message avec son numéro), `en_panne` (ouverture impossible).
- `main.py` : base verrouillée → refus de démarrer, avec la raison. `/api/health` → `services.memoire`.

### 4.3 SD3 — sauvegarde sans Docker
`backup_memory.py` réécrit (l'ancienne version Docker, 566 lignes, reste dans l'historique) :
- `backup` : prend le verrou (refus si Atlas tourne), copie horodatée, empreintes avant / après / source (refus si la base a bougé), `SHA256SUMS`, `manifest.json` (collections, décomptes, dimensions, résultats des 40 requêtes relevés sur une copie jetable).
- `verify` : empreintes, puis copie jetable : collections et 40 requêtes comparées au manifeste ; rapport `verify_*.json`.
- `restore … --oui` : exige un `verify` réussi ; la base en place est **mise de côté** (`<dossier>.avant_restauration_<horodatage>`), jamais effacée ; revérifiée sur place.
- `memory_cleanup.py`, `memory_inventory.py`, `reencode_memory.py` : `--path` (défaut `data/chromadb`), même verrou.

### 4.4 SD4 — SearXNG et Docker retirés
`web_search.search` : DuckDuckGo ; échec ou zéro résultat → un résultat unique « La recherche sur internet a échoué (…) : je n'ai rien pu vérifier sur le web… », source `fallback_link`. `docker-compose.yml` et `config/searxng/` supprimés ; `settings.json` sans `chroma_host`, `chroma_port`, `searxng_*`. `doctor.py` : `check_memory` (dossier, 2 Go libres au moins, `ddgs`), plus de `check_virtualization` ni `check_docker_services`.

### 4.5 SD5 — ONNX par défaut, sans export manuel
**Voie (b) choisie** : l'export ONNX **officiel** existe dans le dépôt même du modèle (`intfloat/multilingual-e5-base`, `onnx/model.onnx`, float32, 1 059 Mo), publié par ses auteurs. `download_voice_models.download_e5_onnx()` le télécharge (avec `onnx/tokenizer.json`) et le réenregistre **avec ses poids à part** par ONNX Runtime lui-même (`optimized_model_external_initializers_*`, aucun paquet en plus) : poids projetés en mémoire, ~600 Mo de RAM au lieu de ~1,3 Go. Idempotent. **Pourquoi (b) plutôt que (a)** : (a) exigeait torch, transformers et le paquet `onnx` à l'installation — `onnx` n'a pu s'installer ici que dans un environnement à part et à un chemin court (fichiers de test aux chemins trop longs pour Windows) ; (b) n'utilise que ce que l'installation fournit déjà. `memory.embedding_backend` = `onnx` ; repli sentence-transformers si le modèle manque. L'ancien `scripts/export_e5_onnx.py` est retiré.

### 4.6 SD6 et documentation
`keep_alive` "5m" dans `settings.json`, défaut de `ollama_client` et de `LLMClient`. Seuils de `doctor.py` (16 Go / 12 juste / ❌ en dessous ; NVIDIA 8 Go / 6 juste ; disque 20 Go). Documentation : plus de virtualisation, de WSL2 ni de Docker ; la mémoire est un dossier, avec sa sauvegarde ; désinstallation ; temps de démarrage mesurés.

### 4.7 Régression corrigée (EasyOCR)
`grounding._layer_timeout("easyocr")` = 4 s + `EASYOCR_FIRST_LOAD_S` (15 s) tant que le lecteur n'est pas chargé ; 4 s ensuite.

---

## 5. Résultats des tests

### État rouge
`tests/test_sans_docker.py` avant le code : **18 échoués sur 18**. Rouges forts (13) : chemin, base ouverte, verrou, refus de démarrer, états, santé, retrait de compose et de SearXNG, appels restants, recherche (DuckDuckGo appelé deux fois), ONNX par défaut, installation ONNX, `keep_alive`, seuils (5). Rouges faibles (5) : nom ou clé absente (`CHROMA_PATH`, `chroma_path`, `status`, sorties de sous-processus vides).
- **Pas rouges d'abord — à signaler** : les **5 tests de SD3** (sauvegarde) ont été écrits **après** la réécriture de `backup_memory.py`.
- Régression EasyOCR : test **rouge d'abord** (`_layer_timeout` absent), puis vert, puis vérifié en réel.

### Anciens tests
- **Retirés (52 tests, 2 fichiers)** : `test_backup_memory_guard.py` (liste blanche des commandes `docker` du script de sauvegarde : il n'y en a plus) et `test_compose_config.py` (`docker-compose.yml` retiré). Ce qu'ils protégeaient est désormais couvert par les tests de SD2, SD3 et SD4.
- **Retiré (1)** : `test_web_v20::test_01_searxng_heartbeat_under_3s`.
- **Adaptés**, en gardant ce qu'ils protégeaient : `test_chroma_integration` (base intégrée jetable), sondes de `test_memory_v60` et `test_memory_quality_d` (elles sondaient par le réseau : **27 tests s'ignoraient tout seuls** avant l'adaptation — ils tournent de nouveau), `test_isolation` (la vraie base et le réseau sont interdits), `test_final_v50` (santé `memoire`, recherche), `test_web_v20` (DuckDuckGo, échec dit), `test_doctor_verdict_g` (seuils mesurés, 12 Go et 6 Go « justes »), `test_v53_migration` (`keep_alive` 5 min), `test_performance` (PF1 : `ATLAS_CHROMA_PATH`).
- Compte : 1 049 avant − 52 − 1 + 24 nouveaux + 1 cas de seuil = **1 021**.

### Suites complètes (Docker Desktop arrêté)
```
.\.venv\Scripts\python.exe -m pytest tests/ -q -p no:cacheprovider
Avec Ollama : 1017 passed, 4 skipped in 148.35s (0:02:28)
Sans Ollama : 1014 passed, 7 skipped in 167.58s (0:02:47)   (Ollama arrêté puis relancé)
```

---

## 6. Comportement observé en scénarios réels

### 6.1 SD1 — migration (sauvegarde `chromadb_20261014_060740`, vérifiée)

| Collection | Docker 1.4.1 | Intégré 1.5.1 | ids / docs / métadonnées | Vecteurs (écart max) |
|---|---|---|---|---|
| atlas_memory | 489 | 489 | identiques | 2,0e-8 |
| atlas_memory_e5 | 276 | 276 | identiques | 2,1e-8 |
| atlas_errors | 20 | 20 | identiques | 2,1e-8 |
| atlas_conversations | 19 | 19 | identiques | 1,9e-8 |
| atlas_documents | 8 | 8 | identiques | 1,7e-8 |
| atlas_habits, atlas_context_apps | 0 | 0 | — | — |

40 requêtes : 120 listes, **0 différence d'ordre**, écart 1e-6. Mêmes résultats sur l'essai et sur la vraie migration. Les écarts de 2e-8 viennent de l'arrondi du transport HTTP de l'ancien serveur.

### 6.2 SD5 — embeddings ONNX officiels
- Vecteurs contre sentence-transformers : écart max **2,5e-7**, cosinus ≥ 0,99999994 (dont un texte long tronqué à 512 jetons).
- 40 requêtes sur la **mémoire migrée** : sentence-transformers contre ONNX officiel : 120 listes, **0 différence**, écart 1e-6 ; chargement **15,9 → 1,49 s** ; rappel 54,7 → 38,9 ms.
- RAM du modèle ONNX (poids à part) : +605 Mo.

### 6.3 Démarrage réel, Docker Desktop arrêté (Atlas sur une copie de la mémoire migrée)

| ID | Demande | Attendu | Observé | Statut |
|---|---|---|---|---|
| R1 | « tu peux faire quoi ? » | liste complète | liste (0,29 s) | PASS |
| R2 | « toi fais le » | réponse fixe | idem (0,10 s) | PASS |
| R3 | « il consiste à quoi le mode gaming ? » | mode décrit | décrit, désactivé | PASS |
| R4 | « que sais-tu faire avec les fenêtres ? » | une famille | idem | PASS |
| R5 | « baisse le volume » | réponse fixe | « Je ne sais pas encore faire ça. » | PASS |
| R6 | « tu te souviens de Discord ? » (rappel) | rappel sur la base intégrée | « Je n'ai rien retenu à ce sujet » (aucun fait retenu sur Discord) (0,15 s) | PASS |
| R7 | 12 000 caractères | refus | refus poli (0,00 s) | PASS |
| R8 | « cherche sur internet la météo à Paris » | DuckDuckGo, sans SearXNG | Météo-France en tête (2,59 s) | PASS |
| R9 | « restaure AtlasEssaiRestaure » | restaurée | restaurée, premier plan (3,07 s) | PASS |
| R10 | « ferme AtlasEssaiRestaure » | confirmation | demandée, **annulée par moi** | PASS |
| R11 | « clique sur Bibliothèque dans AtlasEssaiOCR » | clic OCR | Tesseract, confiance 96 % (3,55 s) | PASS |

Pendant la mesure en scénarios (même jour, plus tôt), le clic avait **échoué** : Tesseract lisait des fragments sans rapport (« WH », « cu », « op »…) à l'emplacement de ma fenêtre, recouverte par une autre ; EasyOCR prenait alors le relais et révélait la régression du §7.1. Fenêtre de test maintenue au premier plan, le clic réussit.

### 6.4 torch hors d'Atlas (DLL chargées, Atlas réel)
- Processus Atlas après une demande et un rappel : **torch non chargé**, ONNX Runtime chargé.
- Après un passage par EasyOCR : **torch toujours absent d'Atlas** ; présent dans le processus OCR (541 Mo), et seulement là.

### 6.5 Mesures (Atlas complet sur copie, Docker arrêté)

| Scénario | RSS (Atlas et ses enfants) | VRAM machine |
|---|---|---|
| Au repos après démarrage | **1 087 Mo** | 5 720 Mo (modèle préchauffé) |
| Après une demande écrite (1,57 s) | 1 098 Mo | 5 732 |
| Après un rappel (0,22 s) | 1 098 Mo | 5 732 |
| Après le clic (fenêtre recouverte : EasyOCR lancé) | 1 365 Mo | 5 749 |
| Pic sur 10 min mêlées (106 demandes) | 1 589 Mo (dont le processus OCR, ~500 Mo, arrêté après 10 min d'inactivité) | 5 764 |
| Ollama (`llama-server` + `ollama` + application) | 821 Mo | — |
| VM WSL / conteneurs | **aucun** | — |

Première demande (modèle déchargé au départ) : API prête en 10,7 s ; demande posée aussitôt **5,34 s** ; 20 s après **1,45 s** ; les suivantes 0,7 à 0,8 s.

### 6.6 `doctor.py`
Seuils testés : 15,8 Go et 32 Go → ✅ ; 12 Go → ⚠️ ; 8 Go → ❌ ; carte 6 Go → ⚠️ « juste » ; 4 Go → ⚠️ « trop petite » ; aucune raison ne parle de Docker ni de virtualisation.

### 6.7 Règle C3
Décomptes de la vraie mémoire (`data/chromadb`) après tous les essais : 276 / 489 / 20 / 19 / 8 / 0 / 0, **identiques** à la migration. Scénarios sur copies ; banc GB1 en lecture seule (18 écritures interceptées, aucune faite). **Aucune trace à retirer.**

---

## 7. Limites et risques identifiés

| # | Description | Sévérité | Mitigation |
|---|---|---|---|
| 1 | **Régression du sprint Performance, trouvée ici en réel et corrigée** : le premier usage d'EasyOCR échouait toujours (chargement ~10 s coupé par le délai de 4 s de sa couche). Elle aurait touché tout clic sur un libellé que Tesseract ne trouve pas, jusqu'au second essai. | Moyen (corrigé) | test de régression ; vérifié en réel : 12,5 s au premier usage (annoncé), 1,1 s ensuite |
| 2 | **GB1 : 1 question ordinaire bloquée sur 20** (« quelle est la différence entre la RAM et le disque dur ? »). La réponse du modèle contenait « fichiers sont enregistrés » (explication), pris pour une action prétendue. Le modèle varie d'un tirage à l'autre ; cette tournure est apparue cette fois. **0 affirmation transmise sur 34.** | Moyen | ne pas desserrer la garde à l'aveugle (« vos fichiers sont enregistrés » après « enregistre mes fichiers » est une vraie fausse affirmation) : sprint dédié sur la garde, avec un corpus de tournures explicatives |
| 3 | Le volume Docker `atlas_chromadb_data` n'a **pas** été rouvert depuis la migration (Docker arrêté) : il est intact par construction, mais n'est plus vérifié. | Faible | décision d'Alexis sur sa suppression ; d'ici là, ne pas relancer d'ancien Atlas sur Docker (deux bases divergeraient) |
| 4 | Un clic par OCR **échoue si la fenêtre visée est recouverte** (vu en mesure). Comportement d'avant ce sprint. | Faible | à traiter avec le grounding (amener la fenêtre au premier plan avant la capture) |
| 5 | Les anciennes sauvegardes (format Docker) ne passent pas par `verify` / `restore` : elles passent par `migrer_memoire.py`. | Faible | documenté dans `backup_memory.py` et la checklist |
| 6 | La recherche web affiche encore ses résultats de façon brute (liste) — déjà dit dans le guide. | Faible | — |
| 7 | Le modèle ONNX occupe ~2,1 Go sur le disque (cache Hugging Face + version préparée). | Faible | le cache peut être vidé après préparation (non fait) |
| 8 | Pas de séance au micro ce sprint. | Moyen | Alexis |

---

## 8. Checklist de validation

- [x] Compatibilité 1.4.1 → 1.5.1 vérifiée ; version pip épinglée
- [x] Copie migrée : décomptes, identifiants, métadonnées, vecteurs et 40 requêtes identiques
- [x] Vraie mémoire migrée seulement après le « oui » d'Alexis ; volume Docker intact
- [x] Verrou : un seul Atlas sur la base, testé
- [x] Sauvegarde, `verify`, `restore` et `memory_cleanup` fonctionnent sans Docker
- [x] SearXNG et `docker-compose.yml` retirés ; aucun appel restant ; Atlas complet démarre Docker arrêté
- [x] ONNX par défaut, sans export manuel ; 40 requêtes identiques ; torch absent d'Atlas
- [x] `keep_alive` 5 min ; seuils de `doctor.py` à jour
- [x] Documentation sans Docker, chaque phrase vraie
- [x] `python -m pytest tests/ -q` → code 0, avec et sans Ollama ; GB1 à 0 / 34 (et 1 / 20 ordinaire bloquée, §7.2)

---

## 9. Recommandations

1. **Supprimer le volume Docker et désinstaller Docker Desktop** : décision d'Alexis, quand il aura utilisé Atlas sans Docker quelques jours. Avant : une sauvegarde de `data/chromadb` (`backup_memory.py backup` + `verify`).
2. **Garde GB1** : un petit sprint avec un corpus de réponses explicatives (« les fichiers sont enregistrés sur le disque… ») contre de vraies fausses affirmations, pour réduire les faux positifs sans en laisser passer.
3. **Grounding** : amener la fenêtre visée au premier plan avant la capture OCR.
4. Séance au micro, pour mesurer le cycle vocal après les sprints pré-beta, Performance et Sans Docker.
