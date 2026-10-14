"""
Test d'intégration ChromaDB — Sprint v1.2

Cible : une base ChromaDB intégrée JETABLE (dossier temporaire ; jamais la production).
Sprint Sans Docker : plus de serveur, la base est un dossier.
Lancer avec :
    python -m pytest tests/test_chroma_integration.py -v
"""

import pathlib
import tempfile
import time
import uuid

import chromadb
import pytest

# --------------------------------------------------------------------------- #
#  Config — doit correspondre à settings.json
# --------------------------------------------------------------------------- #

BASE = pathlib.Path(tempfile.mkdtemp(prefix="atlas_test_integration_")) / "chromadb"
TEST_COLLECTION = f"atlas_test_{uuid.uuid4().hex[:8]}"


# --------------------------------------------------------------------------- #
#  Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def chroma_client():
    """Base intégrée jetable, réutilisée pour tout le module."""
    client = chromadb.PersistentClient(path=str(BASE))
    yield client


# --------------------------------------------------------------------------- #
#  Tests
# --------------------------------------------------------------------------- #

class TestChromaIntegration:
    """Série de tests d'intégration ChromaDB (< 5s total)."""

    def test_01_heartbeat(self, chroma_client):
        """ChromaDB répond au heartbeat."""
        hb = chroma_client.heartbeat()
        assert hb is not None

    def test_02_la_base_est_un_dossier(self, chroma_client):
        """Sans serveur : la base vit dans un fichier SQLite du dossier."""
        chroma_client.get_or_create_collection(name=TEST_COLLECTION)
        assert (BASE / "chroma.sqlite3").exists()

    def test_03_create_collection(self, chroma_client):
        """Créer une collection de test."""
        col = chroma_client.get_or_create_collection(name=TEST_COLLECTION)
        assert col is not None
        assert col.name == TEST_COLLECTION

    def test_04_insert_and_query(self, chroma_client):
        """Insérer un document et le retrouver par similarité."""
        col = chroma_client.get_or_create_collection(name=TEST_COLLECTION)

        doc_id = f"test_{uuid.uuid4().hex[:8]}"
        col.add(
            ids=[doc_id],
            documents=["L'utilisateur lance souvent Discord le soir"],
            metadatas=[{"category": "habit", "timestamp": time.time()}],
        )

        # Recherche par similarité
        results = col.query(
            query_texts=["Discord habitude soir"],
            n_results=1,
        )

        assert results is not None
        assert len(results["ids"]) > 0
        assert len(results["ids"][0]) > 0
        assert results["ids"][0][0] == doc_id

    def test_05_cleanup_collection(self, chroma_client):
        """Supprimer la collection de test."""
        chroma_client.delete_collection(name=TEST_COLLECTION)
        # Vérifier qu'elle n'existe plus
        collections = [c.name for c in chroma_client.list_collections()]
        assert TEST_COLLECTION not in collections
