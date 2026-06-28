# core_conversational

Cœur conversationnel **cross-platform** partagé entre **Atlas** (Windows) et
**Compagnon** (Mac M). Décision Réunion Atlas #6.

## Règle absolue

**Zéro dépendance Windows.** Interdits : `pywin32`, `pywinauto`, `comtypes`, `pycaw`,
`wmi`, `pygetwindow`, et tout import des outils Atlas Windows (`grounding`,
`window_controller`, `app_launcher`…).

Dépendances autorisées : `httpx`, `chromadb`, `sentence-transformers`.

## Modules

| Module | Rôle |
|---|---|
| `identity.py` | `IdentityCard` + persona overlay + identité Atlas + contrainte langue |
| `llm_client.py` | `LLMClient` Ollama (httpx) + garde linguistique anti-dérive |
| `memory_core.py` | embeddings e5 + `ConversationalMemory` (partitions vectorielles) |
| `intent_minimal.py` | `MinimalClassifier` conversationnel (sans routage Windows) |

## Usage — Atlas (défaut)

```python
from core_conversational import atlas_identity, LLMClient

card = atlas_identity()                      # identité Atlas, sans overlay
client = LLMClient(model="qwen2.5:7b")
answer = await client.complete(card.build_system_prompt(), "qui es-tu ?")
```

## Usage — Compagnon (persona overlay)

```python
from core_conversational import IdentityCard, ATLAS_BASE_IDENTITY, LLMClient

COMPAGNON_PERSONA = '''Tu es Compagnon, l'assistante chaleureuse d'Camille.
Tu la tutoies, tu l'appelles "ma star", tu es douce et encourageante.
Alexis (son fils) t'a créée comme cadeau.'''

# Compagnon peut repartir d'une base neutre OU d'ATLAS_BASE_IDENTITY
card = IdentityCard(base_identity="Tu es une assistante personnelle conversationnelle.",
                    persona_overlay=COMPAGNON_PERSONA)
client = LLMClient(model="qwen2.5:7b")
answer = await client.complete(card.build_system_prompt(), "bonjour")
```

## Mémoire (ingestion 100 entrées Camille pour Compagnon)

```python
from core_conversational import ConversationalMemory

mem = ConversationalMemory(host="localhost", port=8001)
mem.add("documents", "Camille adore les orchidées et le thé vert.",
        {"source": "souvenirs_camille"})
hits = mem.retrieve("qu'est-ce qu'aime Camille ?", partition="documents", min_score=0.5)
```

## Garde linguistique

`LLMClient.complete()` détecte automatiquement une dérive non-latine (chinois,
japonais, coréen, cyrillique, arabe), retry une fois en FR strict, puis fallback.

## Tests cross-platform

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r ../../requirements-core-conversational.txt   # depuis core_conversational/
python -m pytest tests/test_core_conversational.py -v
```
