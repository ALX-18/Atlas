"""
Memory Core — Embeddings e5 + mémoire conversationnelle vectorielle (cross-platform).

Dépendances : chromadb + sentence-transformers uniquement. Aucune dépendance Windows.
Source de vérité des embeddings (Atlas core/embeddings.py re-exporte d'ici).
"""

import logging
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger("atlas.memory_core")

DEFAULT_EMBED_MODEL = "intfloat/multilingual-e5-base"
EMBED_DIM = 768

_model = None
_model_name: Optional[str] = None
_load_attempted = False
_load_lock = threading.Lock()

# Sprint Performance / PF3 — moteur d'exécution des embeddings. « sentence-transformers »
# (torch) par défaut ; « onnx » exécute le MÊME modèle, aux mêmes poids float32, avec ONNX
# Runtime, sans importer torch. Choisi par Atlas (core/embeddings.py, depuis settings.json).
_backend = "sentence-transformers"
_onnx_dir: Optional[str] = None


def set_embedding_backend(backend: str, onnx_dir: Optional[str] = None) -> None:
    """À appeler avant le premier embedding. Un moteur ONNX introuvable retombe sur torch."""
    global _backend, _onnx_dir
    _backend = backend
    _onnx_dir = onnx_dir


def embedding_backend() -> str:
    """Le moteur réellement chargé (ou qui le sera)."""
    if _model is not None:
        return "onnx" if isinstance(_model, _OnnxE5) else "sentence-transformers"
    return _backend


class _OnnxE5:
    """e5 sur ONNX Runtime : mêmes étapes que sentence-transformers pour ce modèle —
    tokenisation (512 jetons au plus), dernier état caché, moyenne sur les jetons réels,
    normalisation L2."""

    def __init__(self, folder: str):
        import pathlib

        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer

        self._np = np
        d = pathlib.Path(folder)
        self._tok = Tokenizer.from_file(str(d / "tokenizer.json"))
        self._tok.enable_truncation(max_length=512)
        self._tok.enable_padding(pad_id=1, pad_token="<pad>")
        # Poids enregistrés à part (model_ext.onnx + .data) : ONNX Runtime les projette en mémoire,
        # et seules les lignes utilisées de la table de vocabulaire (250 000 jetons, ~770 Mo)
        # deviennent résidentes — 590 Mo au lieu de 1 324 (mesuré).
        model = d / "model_ext.onnx" if (d / "model_ext.onnx").exists() else d / "model.onnx"
        self._sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])

    def encode(self, texts, normalize_embeddings=True, show_progress_bar=False, batch_size=32):
        np = self._np
        out = []
        for i in range(0, len(texts), batch_size):
            encs = self._tok.encode_batch(list(texts[i:i + batch_size]))
            ids = np.array([e.ids for e in encs], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
            hidden = self._sess.run(None, {"input_ids": ids, "attention_mask": mask})[0]
            m = mask[..., None].astype(hidden.dtype)
            pooled = (hidden * m).sum(axis=1) / np.clip(m.sum(axis=1), 1e-9, None)
            if normalize_embeddings:
                pooled = pooled / np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
            out.append(pooled)
        return np.concatenate(out, axis=0)


# --------------------------------------------------------------------------- #
#  Embeddings e5 (préfixes query:/passage:)
# --------------------------------------------------------------------------- #

def _load_model(model_name: str = DEFAULT_EMBED_MODEL):
    global _model, _model_name, _load_attempted
    if _model is not None or _load_attempted:
        return _model
    with _load_lock:
        if _model is not None or _load_attempted:
            return _model
        _load_attempted = True
        if _backend == "onnx" and _onnx_dir:
            try:
                logger.info("Chargement embedding '%s' (ONNX Runtime, sans torch)...", model_name)
                _model = _OnnxE5(_onnx_dir)
                _model_name = model_name
                return _model
            except Exception as e:
                logger.warning("Embedding ONNX indisponible (%s) — repli sentence-transformers.", e)
                _model = None
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Chargement embedding '%s'...", model_name)
            _model = SentenceTransformer(model_name)
            _model_name = model_name
        except Exception as e:
            logger.warning("Embedding '%s' indisponible (%s) — mode legacy.", model_name, e)
            _model = None
    return _model


def embeddings_available() -> bool:
    return _load_model() is not None


def embed_passages(texts: list[str]) -> Optional[list[list[float]]]:
    model = _load_model()
    if model is None or not texts:
        return None
    vecs = model.encode([f"passage: {t}" for t in texts],
                        normalize_embeddings=True, show_progress_bar=False)
    return [v.tolist() for v in vecs]


def embed_query(text: str) -> Optional[list[float]]:
    model = _load_model()
    if model is None or not text:
        return None
    vec = model.encode([f"query: {text}"], normalize_embeddings=True, show_progress_bar=False)
    return vec[0].tolist()


# --------------------------------------------------------------------------- #
#  Mémoire conversationnelle vectorielle
# --------------------------------------------------------------------------- #

class ConversationalMemory:
    """
    Mémoire vectorielle partitionnée (conversations / documents / errors).
    Cross-platform : ChromaDB intégré (un dossier, sans serveur) + embeddings e5.
    """

    def __init__(self, path: str = "data/chromadb", partitions: Optional[dict] = None):
        self.path = path
        self._partitions_cfg = partitions or {
            "conversations": "atlas_conversations",
            "documents": "atlas_documents",
            "errors": "atlas_errors",
        }
        self._client = None
        self._colls: dict[str, Any] = {}
        self._connected = False
        self.connect()

    def connect(self):
        try:
            import chromadb
            from chromadb.config import Settings

            # Sans Docker : un dossier. Un seul processus à la fois sur ce dossier.
            self._client = chromadb.PersistentClient(path=self.path, settings=Settings(anonymized_telemetry=False))
            self._colls = {
                key: self._client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})
                for key, name in self._partitions_cfg.items()
            }
            self._connected = True
            logger.info("ConversationalMemory connectée (%d partitions).", len(self._colls))
        except Exception as e:
            self._connected = False
            logger.warning("ConversationalMemory indisponible (%s).", e)

    def is_connected(self) -> bool:
        return self._connected

    @staticmethod
    def _sanitize(meta: Optional[dict]) -> dict:
        out: dict[str, Any] = {}
        for k, v in (meta or {}).items():
            if v is None:
                continue
            out[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
        return out

    def add(self, partition: str, content: str, metadata: Optional[dict] = None) -> Optional[str]:
        if not self._connected or partition not in self._colls:
            return None
        doc_id = f"{partition[:4]}_{uuid.uuid4().hex[:12]}"
        meta = self._sanitize(metadata)
        meta.setdefault("created_at", time.time())
        meta.setdefault("timestamp", datetime.now().isoformat())
        try:
            vecs = embed_passages([content])
            if vecs is not None:
                self._colls[partition].add(ids=[doc_id], documents=[content],
                                           metadatas=[meta], embeddings=vecs)
            else:
                self._colls[partition].add(ids=[doc_id], documents=[content], metadatas=[meta])
            return doc_id
        except Exception as e:
            logger.error("Add partition '%s' échec : %s", partition, e)
            return None

    def retrieve(self, query: str, partition: str = "conversations",
                 top_k: int = 3, min_score: float = 0.5) -> list[dict]:
        if not self._connected or partition not in self._colls:
            return []
        coll = self._colls[partition]
        try:
            qvec = embed_query(query)
            res = (coll.query(query_embeddings=[qvec], n_results=top_k) if qvec is not None
                   else coll.query(query_texts=[query], n_results=top_k))
        except Exception as e:
            logger.error("Retrieve '%s' échec : %s", partition, e)
            return []
        hits = []
        if res and res.get("documents") and res["documents"][0]:
            for i, doc in enumerate(res["documents"][0]):
                dist = res["distances"][0][i] if res.get("distances") else 0.0
                score = round(1 - dist, 3)
                if score < min_score:
                    continue
                meta = res["metadatas"][0][i] if res.get("metadatas") else {}
                hits.append({"id": res["ids"][0][i], "content": doc,
                             "score": score, "metadata": meta})
        return hits
