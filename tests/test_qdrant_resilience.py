import pytest
import unittest.mock as mock
from src.indexing.vector_service import VectorService
from src.generation.rag_engine import RAGEngine

@pytest.mark.asyncio
async def test_vector_service_resilience_when_qdrant_down():
    """
    Test que VectorService ne crashe pas si Qdrant est injoignable.
    """
    # Mock QdrantClient pour qu'il lève une erreur de connexion
    with mock.patch("src.indexing.vector_service.QdrantClient", side_effect=Exception("Connection refused")):
        vs = VectorService(storage_path="invalid_path")
        assert vs.available is False
        assert vs.vector_store is None
        assert vs.ping() is False

@pytest.mark.asyncio
async def test_rag_engine_degraded_mode():
    """
    Test que RAGEngine gère le mode dégradé proprement.
    """
    # Mock VectorService pour qu'il soit indisponible
    with mock.patch("src.generation.rag_engine.VectorService") as mock_vs_class:
        mock_vs = mock_vs_class.return_value
        mock_vs.available = False
        mock_vs.ping.return_value = False
        mock_vs.list_collections.return_value = []
        
        engine = RAGEngine()
        themes = engine.get_available_themes()
        assert themes == []
        
        response = await engine.aask("Quelle est la capitale de la France?")
        # On vérifie que le message d'erreur amical est présent dans la réponse
        assert "inaccessible" in str(response.response)
