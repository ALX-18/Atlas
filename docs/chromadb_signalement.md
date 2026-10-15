# Signalement préparé pour ChromaDB (non publié)

Sprint Apprentissage 1 / AP0. **Rien n'est publié** : publier un ticket sur GitHub est une action
au nom d'Alexis ; c'est lui qui décide de l'envoyer. Le texte ci-dessous est prêt, en anglais,
pour `https://github.com/chroma-core/chroma/issues`.

Reproduction : `scripts/repro_chroma.py` (autonome, ne dépend que de chromadb). Mesures du
15/10/2026, Windows 11, Python 3.12.3, 100 ouvertures par version :

| Version | Échecs sur 100 ouvertures |
|---|---|
| 1.4.1 | 20 |
| 1.5.1 (épinglée dans Atlas) | 7 |
| 1.5.5 | 12 |
| 1.5.9 (la plus récente) | 6 |

---

**Title:** `InternalError: Error creating hnsw segment reader: Nothing found on disk` when reading a freshly written persistent collection (Windows, 1.4.1 → 1.5.9)

**Environment:** Windows 11 Pro (10.0.26200), Python 3.12.3, `chromadb` installed from PyPI (1.4.1, 1.5.1, 1.5.5, 1.5.9 tested), `PersistentClient`, default settings except `anonymized_telemetry=False`.

**What happens:** a process writes a small persistent database (4 collections × 12 records, explicit embeddings, `hnsw:space=cosine`) and exits. Another process opens the folder with `PersistentClient`, then, for each collection, calls `get(limit=1, include=["embeddings"])` and `count()`, then `query(query_embeddings=..., n_results=3)`. On a fraction of fresh databases, one collection fails with:

```
chromadb.errors.InternalError: Error executing plan: Internal error: Error creating hnsw segment reader: Nothing found on disk
```

For that client, the failure is persistent: retrying the same call for 5 seconds keeps failing. The four HNSW files (`header.bin`, `data_level0.bin`, `length.bin`, `link_lists.bin`) are present in the segment folder. When `query` is the first read on each collection, no failure was observed in 80 openings (1.5.1). Opening a new client (after `SharedSystemClient.clear_system_cache()`) and querying again usually works, but not always.

**Frequency (100 fresh databases per version):** 1.4.1: 20 · 1.5.1: 7 · 1.5.5: 12 · 1.5.9: 6.

**Minimal reproduction:** the attached `repro_chroma.py` (`python repro_chroma.py fraiche --n 100 --out res.json`) writes each database in a subprocess, then reads it in the order above and counts failures.

**Expected:** reading a collection never fails because of a previous `get`/`count` on the same or another collection.
