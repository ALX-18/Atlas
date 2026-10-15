# Memory Runbook — F4 Mémoire Long Terme (v6.0)

## Vue d'ensemble

Atlas dispose d'une mémoire long terme vectorielle (ChromaDB) partitionnée, avec
embeddings multilingues (e5-base, 768 dim) pour un retrieval FR/EN de qualité.

```
collections ChromaDB
├── atlas_memory          # legacy (habits/preferences/corrections) — embedder par défaut
├── atlas_conversations   # échanges user/assistant (FIFO 10k) — e5
├── atlas_documents       # documents ingérés (.txt/.md/.pdf) — e5
└── atlas_errors          # ARCHIVE : écrite nulle part, lue nulle part (voir ci-dessous) — e5
```

> **Apprentissage 2 (15/10/2026).** `atlas_context_apps` et `atlas_habits` (déclarées, jamais
> utilisées) et `atlas_apprentissage` sont retirées de la configuration et de la mémoire, après une
> sauvegarde vérifiée. Ce qu'Atlas apprend (corrections, méthodes, refus, habitudes écartées) est
> dans **`data/apprentissage.db`** (SQLite, `core/apprentissage_store.py`), lu par identifiant
> exact ; `scripts/backup_memory.py` le sauvegarde, le vérifie et le restaure avec `habits.db`.
> `atlas_errors` garde les 20 entrées des sessions d'Alexis : plus aucun code ne la lit ni ne
> l'écrit depuis le sprint Apprentissage 1, elle reste dans les sauvegardes comme archive.

## Prérequis

- **ChromaDB** (Docker) sur `localhost:8001` — `docker-compose up -d`
- **Modèle d'embedding** : `intfloat/multilingual-e5-base` (~280 MB, téléchargé au 1er usage, caché dans `~/.cache/huggingface`)
- **pypdf** (ingestion PDF) : `pip install pypdf`

Si le modèle e5 ne charge pas → dégradation gracieuse vers l'embedder ChromaDB par
défaut (les nouvelles partitions fonctionnent quand même, qualité FR moindre).

## Configuration (`config/settings.json` → `memory`)

```json
"embedding_model": "intfloat/multilingual-e5-base",
"retrieval_top_k": 3,
"retrieval_min_score": 0.5,
"conversations": { "max_entries": 10000 },
"collections": { ... noms des partitions ... }
```

## Pipelines

### Ingestion conversations (automatique)
À chaque échange conversationnel `/api/chat`, le tuple (user, assistant) est embeddé
et stocké dans `atlas_conversations` avec metadata (intent_category, success).
Rotation FIFO à 10 000 entrées (`memory.conversations.max_entries`).

### Ingestion documents (manuelle)
```
POST /api/memory/ingest
{ "path": "C:\\chemin\\vers\\doc.pdf" }
```
Extraction → chunking récursif (512 chars, overlap 64) → embeddings e5 → `atlas_documents`.
Formats : `.txt`, `.md`, `.pdf`.

### Retrieval (automatique)
À chaque génération LLM, `recall_for_prompt(query)` croise documents + conversations +
mémoire legacy, filtre par score (≥ 0.5), dédoublonne, injecte top-6 dans le system prompt.
Injection silencieuse si rien au-dessus du seuil.

### Apprentissage par les erreurs
- **Sur échec** (`status=error/replan_required/verification_failed`) : signature
  `intent=… cible=… app=…` + cause normalisée stockée dans `atlas_errors`.
- **Avant action** (`ui_click_element`) : lookup d'un échec similaire (cosine ≥ 0.85).
  Si trouvé → mitigation : `skip_layer` (saute la couche grounding qui avait échoué),
  `confirm` (demande confirmation) ou `reformulate`.
- **Limite honnête** : retrieval + règles, PAS du reinforcement learning.

## Endpoints

| Méthode | Path | Rôle |
|---|---|---|
| POST | `/api/memory/ingest` | Ingérer un document |
| GET | `/api/memory/stats` | Stats (inclut compteurs partitions) |
| GET | `/api/memory/recall?query=…` | Recherche legacy |
| POST | `/api/memory/reconnect` | Reconnexion ChromaDB |

## Diagnostic

| Symptôme | Cause probable | Action |
|---|---|---|
| Retrieval vide en permanence | ChromaDB down | `docker ps`, `/api/memory/reconnect` |
| Latence 1ère requête élevée | Chargement modèle e5 | normal (~3-5s au 1er appel, puis chaud) |
| Ingestion PDF échoue | pypdf absent | `pip install pypdf` |
| Qualité retrieval FR faible | modèle e5 non chargé (mode legacy) | vérifier logs `[atlas.embeddings]` |

## Tests

```bash
pytest tests/test_memory_v60.py -q     # 33 tests (unit + live ChromaDB)
```
Les tests live se skippent automatiquement si ChromaDB est indisponible.
