"""
Embeddings — Façade Atlas vers core_conversational.memory_core (v6.0.1).

La logique d'embedding e5 est désormais dans le package cross-platform
core_conversational. Ce module conserve l'API historique (is_available,
embed_query, embed_passages, model_info) pour compatibilité Atlas.
"""

import json
import pathlib

from core_conversational.memory_core import (
    embed_query, embed_passages, embeddings_available as is_available,
    EMBED_DIM, DEFAULT_EMBED_MODEL as DEFAULT_MODEL, embedding_backend, set_embedding_backend,
)

# Sprint Performance / PF3 : moteur des embeddings, depuis config/settings.json
# (memory.embedding_backend : "sentence-transformers" par défaut, ou "onnx").
_ROOT = pathlib.Path(__file__).resolve().parent.parent
try:
    _mem_cfg = json.loads((_ROOT / "config" / "settings.json").read_text(encoding="utf-8")).get("memory", {})
except Exception:
    _mem_cfg = {}
set_embedding_backend(_mem_cfg.get("embedding_backend", "sentence-transformers"),
                      str(_ROOT / _mem_cfg.get("embedding_onnx_dir", "models/embeddings/multilingual-e5-base")))

__all__ = ["embed_query", "embed_passages", "is_available", "model_info",
           "EMBED_DIM", "DEFAULT_MODEL"]


def model_info() -> dict:
    """Infos diagnostic (compat Atlas)."""
    return {
        "available": is_available(),
        "model": DEFAULT_MODEL,
        "dim": EMBED_DIM,
        "backend": embedding_backend(),
    }
