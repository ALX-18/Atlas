"""
Memory Manager — Couche mémoire RAG via ChromaDB.

Gère deux types de mémoire :
  - Court terme : conversation en cours (RAM, réinitialisée à la fermeture)
  - Long terme  : habitudes, préférences, historique d'actions, corrections (ChromaDB)
"""

import hashlib
import json
import logging
import os
import pathlib
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

logger = logging.getLogger("atlas.memory")

# --------------------------------------------------------------------------- #
#  Config
# --------------------------------------------------------------------------- #

def _load_memory_config() -> dict:
    import pathlib
    cfg_path = pathlib.Path(__file__).resolve().parent.parent / "config" / "settings.json"
    with open(cfg_path, encoding="utf-8") as f:
        return json.load(f).get("memory", {})

_cfg = _load_memory_config()

# Sprint Sans Docker / SD2 : la mémoire est un DOSSIER ouvert par ChromaDB intégré
# (PersistentClient), sans serveur ni réseau. ATLAS_CHROMA_PATH le déplace (tests jetables,
# mesures sur une copie).
_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_CHROMA_PATH: str = str(_ROOT / _cfg.get("chroma_path", "data/chromadb"))
CHROMA_PATH: str = os.environ.get("ATLAS_CHROMA_PATH") or DEFAULT_CHROMA_PATH
COLLECTION_NAME: str = _cfg.get("collection_name", "atlas_memory")

# Catégories valides (mémoire legacy)
# G4 : « user_fact » = ce que l'utilisateur a demandé de retenir (« retiens que… »). Seule
# catégorie que « oublie… » peut effacer : jamais l'historique ni les corrections.
CATEGORIES = {"habit", "preference", "action_history", "correction", "user_fact"}

# --- F4 v6.0 : partitionnement + retrieval ---
_COLL_CFG = _cfg.get("collections", {})
PARTITIONS = {
    "conversations": _COLL_CFG.get("conversations", "atlas_conversations"),
    "documents": _COLL_CFG.get("documents", "atlas_documents"),
    # Archive (Apprentissage 2) : écrite nulle part, lue nulle part, gardée dans les sauvegardes.
    "errors": _COLL_CFG.get("errors", "atlas_errors"),
}
# Apprentissage 2 / AQ2 : atlas_apprentissage, atlas_habits et atlas_context_apps sont retirées.
# Ce qu'Atlas apprend (corrections, méthodes, refus, habitudes) est dans data/apprentissage.db
# (core/apprentissage_store.py) : lu par identifiant exact, sans base vectorielle.
RETRIEVAL_TOP_K: int = int(_cfg.get("retrieval_top_k", 3))
RETRIEVAL_MIN_SCORE: float = float(_cfg.get("retrieval_min_score", 0.5))
CONVERSATIONS_MAX: int = int(_cfg.get("conversations", {}).get("max_entries", 10000))


# --------------------------------------------------------------------------- #
#  SD2 — un seul processus sur la base
#
#  Deux processus ChromaDB intégrés sur le même dossier se corrompent l'un l'autre. Un verrou
#  du système d'exploitation est pris à l'ouverture, sur <dossier>.lock, et gardé toute la vie
#  du processus : il est rendu automatiquement à sa fin, même brutale. Le fichier contient le
#  numéro du processus qui tient la base, pour le dire.
# --------------------------------------------------------------------------- #

_LOCK_OFFSET = 1 << 20          # octet verrouillé loin du contenu : le numéro reste lisible
_LOCKS: dict[str, Any] = {}
_CLIENTS: dict[str, Any] = {}


def acquire_memory_lock(path: str) -> tuple[bool, str]:
    """(pris ?, explication). Idempotent dans un même processus."""
    key = str(pathlib.Path(path).resolve())
    if key in _LOCKS:
        return True, ""
    lock_path = pathlib.Path(key + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+b")
    try:
        if sys.platform == "win32":
            import msvcrt

            fh.seek(_LOCK_OFFSET)
            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        try:
            fh.seek(0)
            holder = fh.read(64).decode("ascii", "ignore").strip() or "?"
        except Exception:
            holder = "?"
        fh.close()
        return False, (f"la mémoire ({key}) est déjà ouverte par un autre processus (n° {holder}) : "
                       "un autre Atlas, ou un script de sauvegarde ou de nettoyage, tourne déjà")
    fh.seek(0)
    fh.truncate()
    fh.write(str(os.getpid()).encode("ascii"))
    fh.flush()
    _LOCKS[key] = fh
    return True, ""


def open_client(path: str):
    """Le client ChromaDB intégré de ce dossier — un seul par processus, verrou pris."""
    key = str(pathlib.Path(path).resolve())
    if key in _CLIENTS:
        return _CLIENTS[key]
    ok, why = acquire_memory_lock(key)
    if not ok:
        raise MemoryLockedError(why)
    from chromadb.config import Settings

    _CLIENTS[key] = chromadb.PersistentClient(path=key, settings=Settings(anonymized_telemetry=False,
                                                                          allow_reset=False))
    return _CLIENTS[key]


class MemoryLockedError(RuntimeError):
    """La base est tenue par un autre processus."""


def _content_hash(category: str, content: str) -> str:
    """Empreinte d'un souvenir (D5). Même texte + même catégorie = même souvenir."""
    return hashlib.sha1(f"{category}\x00{content}".encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
#  MemoryManager
# --------------------------------------------------------------------------- #

class MemoryManager:
    """
    Interface unifiée pour la mémoire court terme (RAM) et long terme (ChromaDB).
    """

    def __init__(self):
        # -- Court terme (session) --
        self._short_term: list[dict] = []

        # -- Long terme (ChromaDB intégré) --
        self._client = None
        self._status: dict[str, str] = {"etat": "en_panne", "detail": "pas encore ouverte"}
        self._collection = None
        self._partitions: dict[str, Any] = {}   # F4 — collections partitionnées
        self._connected = False
        self._connect()

    # ------------------------------------------------------------------ #
    #  Connexion ChromaDB
    # ------------------------------------------------------------------ #

    def _connect(self):
        """Tente de se connecter à ChromaDB. Fail silencieux si indisponible."""
        # Dépôt + Ollama / C3 : la vraie mémoire n'est branchée que pour Atlas lui-même
        # (main.py pose ATLAS_MEMORY=real). Un essai lancé à part — un `python -c` qui importe
        # le moteur — avait écrit dans atlas_errors (G-ter) : il trouve désormais la mémoire
        # neutralisée, comme si ChromaDB était absent. Les scripts de maintenance
        # (backup_memory, memory_cleanup…) ouvrent leur propre client et ne sont pas concernés.
        if os.environ.get("ATLAS_MEMORY") != "real":
            self._connected = False
            self._status = {"etat": "neutralisee", "detail": "processus hors d'Atlas (ATLAS_MEMORY≠real)"}
            logger.warning("Mémoire long terme neutralisée : processus hors d'Atlas (ATLAS_MEMORY≠real).")
            return
        try:
            self._client = open_client(CHROMA_PATH)
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            # F4 v6.0 — collections partitionnées (embeddings e5 fournis explicitement)
            self._partitions = {}
            for key, coll_name in PARTITIONS.items():
                self._partitions[key] = self._client.get_or_create_collection(
                    name=coll_name,
                    metadata={"hnsw:space": "cosine"},
                )
            self._connected = True
            self._status = {"etat": "ok", "detail": CHROMA_PATH}
            logger.info(
                "Mémoire ouverte — %s — collection '%s' + %d partitions",
                CHROMA_PATH, COLLECTION_NAME, len(self._partitions),
            )
        except MemoryLockedError as e:
            self._connected = False
            self._status = {"etat": "verrouillee", "detail": str(e)}
            logger.error("Mémoire long terme indisponible : %s", e)
        except Exception as e:
            self._connected = False
            self._status = {"etat": "en_panne", "detail": f"{type(e).__name__}: {e}"}
            logger.warning("Mémoire indisponible (%s). Mémoire long terme désactivée.", e)

    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------ #
    #  Sprint Fiabilité — lire malgré le défaut de ChromaDB 1.5.1
    # ------------------------------------------------------------------ #

    def _rouvrir(self) -> None:
        """Rouvre le client de la mémoire (le verrou reste tenu). Lecture seule."""
        from chromadb.api.client import SharedSystemClient

        _CLIENTS.pop(str(pathlib.Path(CHROMA_PATH).resolve()), None)
        SharedSystemClient.clear_system_cache()
        self._connect()

    def _interroger(self, collection, methode: str = "query", **kwargs):
        """`collection()` donne la collection à jour ; une seule reprise, client rouvert.

        ChromaDB 1.5.1 cesse parfois de lire l'index d'une collection (« hnsw segment reader:
        Nothing found on disk ») pour toute la vie du client, à l'ouverture comme en cours de
        session ; un client rouvert le relit. Si la reprise échoue aussi : bascule signalée.
        """
        try:
            return getattr(collection(), methode)(**kwargs)
        except Exception as e:
            if "hnsw segment reader" not in str(e):
                raise
            logger.warning("Mémoire : index illisible (%s) — client rouvert, nouvel essai.", str(e)[:120])
            self._rouvrir()
            try:
                return getattr(collection(), methode)(**kwargs)
            except Exception as e2:
                from core_conversational.degradations import signaler

                signaler("memoire_partielle", f"lecture en échec après réouverture : {str(e2)[:160]}")
                raise

    def status(self) -> dict[str, str]:
        """SD2 : « ok », « neutralisee », « verrouillee » ou « en_panne », sans les confondre."""
        return dict(self._status)

    def reconnect(self):
        """Retente la connexion à ChromaDB."""
        self._connect()

    # ------------------------------------------------------------------ #
    #  Mémoire court terme (session)
    # ------------------------------------------------------------------ #

    def add_to_session(self, role: str, content: str):
        """Ajoute un message à la conversation en cours."""
        self._short_term.append({
            "role": role,
            "content": content,
            "timestamp": time.time(),
        })

    def get_session_history(self, last_n: int = 20) -> list[dict]:
        """Retourne les N derniers messages de la session."""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._short_term[-last_n:]
        ]

    def clear_session(self):
        """Réinitialise la conversation en cours."""
        self._short_term.clear()

    # ------------------------------------------------------------------ #
    #  Mémoire long terme — SAVE
    # ------------------------------------------------------------------ #

    def save(
        self,
        category: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str | None:
        """
        Sauvegarde un souvenir dans ChromaDB.

        category : "habit" | "preference" | "action_history" | "correction"
        content  : description textuelle du souvenir
        metadata : données additionnelles (timestamp, contexte, app, etc.)

        Retourne l'ID du souvenir créé, ou None si échec.
        """
        if not self._connected:
            logger.debug("ChromaDB non connecté — souvenir non sauvegardé")
            return None

        if category not in CATEGORIES:
            logger.warning("Catégorie invalide : '%s'. Valides : %s", category, CATEGORIES)
            return None

        # D5 — déduplication à l'écriture. 219 copies exactes s'étaient accumulées dans
        # atlas_memory : nettoyer périodiquement ne sert à rien si l'écriture recopie.
        content_hash = _content_hash(category, content)
        existing_id = self._find_by_hash(content_hash)
        if existing_id:
            logger.debug("Souvenir déjà présent [%s] : %s", category, content[:60])
            return existing_id

        memory_id = f"{category}_{uuid.uuid4().hex[:12]}"

        meta = {
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "created_at": time.time(),
            "content_hash": content_hash,
        }
        if metadata:
            # ChromaDB ne supporte que str/int/float/bool dans les métadonnées
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    meta[k] = v
                else:
                    meta[k] = str(v)

        # D4 — cause racine : sans embeddings, ChromaDB vectorisait avec son modèle par
        # défaut (all-MiniLM-L6-v2, anglophone, 384 dimensions) du contenu français, alors
        # que les partitions utilisent e5 multilingue en 768. Un seul modèle, partout.
        from core import embeddings as emb

        vecs = emb.embed_passages([content])
        if vecs is None:
            logger.error(
                "Modèle e5 indisponible — souvenir NON sauvegardé [%s] : %s. "
                "Écrire avec un autre modèle mélangerait deux espaces vectoriels.",
                category, content[:60],
            )
            return None

        try:
            self._collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[meta],
                embeddings=vecs,
            )
            logger.info("Souvenir sauvegardé [%s] : %s", category, content[:80])
            return memory_id
        except Exception as e:
            logger.error("Erreur sauvegarde mémoire : %s", e)
            return None

    # ------------------------------------------------------------------ #
    #  Mémoire long terme — RECALL
    # ------------------------------------------------------------------ #

    def _find_by_hash(self, content_hash: str) -> Optional[str]:
        """Identifiant d'un souvenir déjà écrit avec cette empreinte, s'il existe (D5)."""
        try:
            found = self._interroger(lambda: self._collection, "get", where={"content_hash": content_hash}, limit=1)
            ids = found.get("ids") or []
            return ids[0] if ids else None
        except Exception as e:
            logger.debug("Recherche d'empreinte impossible : %s", e)
            return None

    def recall(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        min_score: Optional[float] = None,
    ) -> list[dict]:
        """
        Recherche les souvenirs les plus pertinents par rapport à une requête.

        D4 : la requête est vectorisée par e5, comme à l'écriture.
        D8 : les résultats sous le seuil sont écartés. Sans seuil, ce chemin renvoyait
        toujours quelque chose — un souvenir à 0,04 de similarité finissait injecté dans
        le prompt (symptôme C07).

        Retourne une liste de dicts : {"id": str, "content": str, "category": str, "score": float}
        """
        if not self._connected:
            return []
        from core import embeddings as emb

        threshold = RETRIEVAL_MIN_SCORE if min_score is None else min_score
        qvec = emb.embed_query(query)
        if qvec is None:
            logger.warning("Modèle e5 indisponible — rappel impossible pour : %s", query[:60])
            return []

        try:
            where_filter = {"category": category} if category else None

            results = self._interroger(
                lambda: self._collection,
                query_embeddings=[qvec],
                n_results=top_k,
                where=where_filter,
            )

            memories = []
            if results and results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if results["distances"] else 0
                    score = round(1 - distance, 3)  # cosine → similarity
                    if score < threshold:
                        continue
                    memories.append({
                        "id": results["ids"][0][i],
                        "content": doc,
                        "category": meta.get("category", "unknown"),
                        "score": score,
                        "timestamp": meta.get("timestamp", ""),
                    })

            return memories
        except Exception as e:
            logger.error("Erreur recall mémoire : %s", e)
            return []

    def recall_texts(self, query: str, top_k: int = 5) -> list[str]:
        """Version simplifiée de recall — retourne juste les textes."""
        memories = self.recall(query, top_k)
        return [m["content"] for m in memories]

    def recall_for_prompt(self, query: str) -> list[str]:
        """
        F4 v6.0 — Retrieval combiné pour injection dans le system prompt.
        Croise la mémoire legacy + partitions conversations/documents, filtre par
        score, dédoublonne. Vide si rien au-dessus du seuil (injection silencieuse).
        """
        if not self._connected:
            return []
        out: list[str] = []
        seen: set[str] = set()

        # Partitions sémantiques (e5) — documents puis conversations
        for partition in ("documents", "conversations"):
            for hit in self.retrieve(query, partition=partition,
                                     top_k=RETRIEVAL_TOP_K, min_score=RETRIEVAL_MIN_SCORE):
                txt = hit["content"]
                key = txt[:120]
                if key not in seen:
                    seen.add(key)
                    out.append(txt)

        # Mémoire legacy (habitudes/préférences/corrections) — complément
        for txt in self.recall_texts(query, top_k=3):
            key = txt[:120]
            if key not in seen:
                seen.add(key)
                out.append(txt)

        return out[:6]

    # ------------------------------------------------------------------ #
    #  Mémoire long terme — FORGET
    # ------------------------------------------------------------------ #

    def forget(self, memory_id: str) -> bool:
        """Supprime un souvenir spécifique."""
        if not self._connected:
            return False
        try:
            self._collection.delete(ids=[memory_id])
            logger.info("Souvenir supprimé : %s", memory_id)
            return True
        except Exception as e:
            logger.error("Erreur suppression mémoire : %s", e)
            return False

    def forget_category(self, category: str) -> int:
        """Supprime tous les souvenirs d'une catégorie."""
        if not self._connected:
            return 0
        try:
            # Récupérer les IDs de la catégorie
            results = self._collection.get(
                where={"category": category},
            )
            if results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info("Supprimé %d souvenirs de catégorie '%s'", len(results["ids"]), category)
                return len(results["ids"])
            return 0
        except Exception as e:
            logger.error("Erreur suppression catégorie : %s", e)
            return 0

    # ------------------------------------------------------------------ #
    #  F4 v6.0 — Partitions : helpers embeddings
    # ------------------------------------------------------------------ #

    def _sanitize_meta(self, metadata: Optional[dict]) -> dict:
        """ChromaDB n'accepte que str/int/float/bool en métadonnée."""
        meta: dict[str, Any] = {}
        for k, v in (metadata or {}).items():
            if v is None:
                continue
            meta[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
        return meta

    def _add_to_partition(
        self,
        partition: str,
        doc_id: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> bool:
        """Ajoute un document à une partition, embeddings e5 si dispo."""
        if not self._connected or partition not in self._partitions:
            return False
        from core import embeddings as emb

        meta = self._sanitize_meta(metadata)
        meta.setdefault("created_at", time.time())
        meta.setdefault("timestamp", datetime.now().isoformat())
        try:
            vecs = emb.embed_passages([content])
            if vecs is not None:
                self._partitions[partition].add(
                    ids=[doc_id], documents=[content],
                    metadatas=[meta], embeddings=vecs,
                )
            else:
                # Dégradation : embedder ChromaDB par défaut
                self._partitions[partition].add(
                    ids=[doc_id], documents=[content], metadatas=[meta],
                )
            return True
        except Exception as e:
            logger.error("Erreur ajout partition '%s' : %s", partition, e)
            return False

    def retrieve(
        self,
        query: str,
        partition: str = "conversations",
        top_k: int = RETRIEVAL_TOP_K,
        min_score: float = RETRIEVAL_MIN_SCORE,
    ) -> list[dict]:
        """
        Recherche dans une partition. Retourne les hits avec score >= min_score.
        Format : {"id", "content", "score", "metadata"}.
        """
        if not self._connected or partition not in self._partitions:
            return []
        from core import embeddings as emb

        coll = lambda: self._partitions[partition]       # noqa: E731 — à jour après réouverture
        try:
            qvec = emb.embed_query(query)
            if qvec is not None:
                results = self._interroger(coll, query_embeddings=[qvec], n_results=top_k)
            else:
                results = self._interroger(coll, query_texts=[query], n_results=top_k)
        except Exception as e:
            logger.error("Erreur retrieve partition '%s' : %s", partition, e)
            return []

        hits: list[dict] = []
        if results and results.get("documents") and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                dist = results["distances"][0][i] if results.get("distances") else 0.0
                score = round(1 - dist, 3)
                if score < min_score:
                    continue
                meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                hits.append({
                    "id": results["ids"][0][i],
                    "content": doc,
                    "score": score,
                    "metadata": meta,
                })
        return hits

    # ------------------------------------------------------------------ #
    #  F4 — Ingestion conversations (async-friendly, FIFO)
    # ------------------------------------------------------------------ #

    def ingest_conversation(
        self,
        user_msg: str,
        assistant_response: str,
        intent_category: str = "unknown",
        success: bool = True,
    ) -> Optional[str]:
        """Stocke un échange (user, assistant) dans la partition conversations."""
        if not self._connected or not user_msg:
            return None
        conv_id = f"conv_{uuid.uuid4().hex[:12]}"
        content = f"Utilisateur: {user_msg}\nAtlas: {assistant_response}"
        ok = self._add_to_partition(
            "conversations", conv_id, content,
            {"intent_category": intent_category, "success": bool(success),
             "user_msg": user_msg[:500]},
        )
        if not ok:
            return None
        self._fifo_rotate("conversations", CONVERSATIONS_MAX)
        return conv_id

    def _fifo_rotate(self, partition: str, max_entries: int):
        """Supprime les plus anciennes entrées au-delà de max_entries (FIFO)."""
        if not self._connected or partition not in self._partitions:
            return
        coll = self._partitions[partition]
        try:
            total = coll.count()
            if total <= max_entries:
                return
            to_remove = total - max_entries
            # Récupère tout avec created_at, trie, supprime les plus vieux
            alld = coll.get(include=["metadatas"])
            ids = alld.get("ids", [])
            metas = alld.get("metadatas", []) or []
            paired = sorted(
                zip(ids, [m.get("created_at", 0) for m in metas]),
                key=lambda p: p[1],
            )
            old_ids = [pid for pid, _ in paired[:to_remove]]
            if old_ids:
                coll.delete(ids=old_ids)
                logger.info("FIFO rotation '%s' : %d entrées supprimées", partition, len(old_ids))
        except Exception as e:
            logger.debug("FIFO rotation '%s' échec : %s", partition, e)

    # ------------------------------------------------------------------ #
    #  F4 — Ingestion documents (chunks)
    # ------------------------------------------------------------------ #

    def ingest_document_chunks(
        self,
        chunks: list[str],
        source: str,
        mime_type: str = "text/plain",
    ) -> int:
        """Stocke des chunks de document dans la partition documents. Retourne le nb stockés."""
        if not self._connected or not chunks:
            return 0
        stored = 0
        ingested_at = datetime.now().isoformat()
        for idx, chunk in enumerate(chunks):
            if not chunk.strip():
                continue
            doc_id = f"doc_{uuid.uuid4().hex[:12]}"
            ok = self._add_to_partition(
                "documents", doc_id, chunk,
                {"source": source, "mime_type": mime_type,
                 "chunk_index": idx, "ingested_at": ingested_at},
            )
            if ok:
                stored += 1
        logger.info("Ingestion document '%s' : %d/%d chunks stockés", source, stored, len(chunks))
        return stored

    # ------------------------------------------------------------------ #
    #  Stats
    # ------------------------------------------------------------------ #

    def stats(self) -> dict[str, Any]:
        """Retourne des statistiques sur la mémoire."""
        result = {
            "connected": self._connected,
            "session_messages": len(self._short_term),
        }
        if self._connected:
            try:
                count = self._collection.count()
                result["total_memories"] = count

                # Compter par catégorie
                for cat in CATEGORIES:
                    try:
                        cat_results = self._interroger(lambda: self._collection, "get", where={"category": cat})
                        result[f"count_{cat}"] = len(cat_results["ids"])
                    except Exception:
                        result[f"count_{cat}"] = 0

                # F4 — compteurs partitions
                partitions_count = {}
                for key, coll in self._partitions.items():
                    try:
                        partitions_count[key] = coll.count()
                    except Exception:
                        partitions_count[key] = -1
                result["partitions"] = partitions_count
            except Exception:
                result["total_memories"] = -1
        return result


# --------------------------------------------------------------------------- #
#  Singleton
# --------------------------------------------------------------------------- #

_instance: Optional[MemoryManager] = None


def get_memory_manager() -> MemoryManager:
    """Retourne l'instance singleton du MemoryManager."""
    global _instance
    if _instance is None:
        _instance = MemoryManager()
    return _instance
