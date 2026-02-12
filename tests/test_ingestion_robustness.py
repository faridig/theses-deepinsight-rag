import os
import pytest
from src.indexing.vector_service import VectorService
from src.ingestion.async_ingestor import AsyncIngestor
from llama_index.core.schema import Document

@pytest.mark.asyncio
async def test_async_ingestor_local_fallback(tmp_path):
    """Vérifie que l'ingesteur ne crashe pas en mode local (sans aclient)."""
    # Use MockEmbedding to avoid API key issues
    from llama_index.core.embeddings.mock_embed_model import MockEmbedding
    from llama_index.core import Settings
    Settings.embed_model = MockEmbedding(embed_dim=1536)

    # Force local mode by ensuring QDRANT_URL is not set
    if "QDRANT_URL" in os.environ:
        del os.environ["QDRANT_URL"]
    
    storage_path = str(tmp_path / "qdrant_test")
    vector_service = VectorService(storage_path=storage_path, collection_name="test-local")
    
    # Verify we are in local mode
    assert vector_service.aclient is None
    
    ingestor = AsyncIngestor(vector_service=vector_service)
    
    doc = Document(text="Ceci est un test pour le mode local.", metadata={"titre": "Test Local"})
    
    # This should NOT crash and should use pipeline.run internally
    nodes = await ingestor.run_ingestion([doc])
    
    assert len(nodes) > 0
    assert nodes[0].text == "Ceci est un test pour le mode local."

@pytest.mark.asyncio
async def test_ingestion_cache_persistence(tmp_path):
    """Vérifie que le cache d'ingestion est correctement persisté."""
    from llama_index.core.embeddings.mock_embed_model import MockEmbedding
    from llama_index.core import Settings
    Settings.embed_model = MockEmbedding(embed_dim=1536)

    storage_path = str(tmp_path / "qdrant_cache_test")
    cache_path = str(tmp_path / "cache.json")
    
    vector_service = VectorService(storage_path=storage_path, collection_name="test-cache")
    ingestor = AsyncIngestor(vector_service=vector_service, cache_path=cache_path)
    
    doc = Document(text="Contenu unique pour le cache.", metadata={"id": "123"})
    
    # First ingestion
    await ingestor.run_ingestion([doc])
    
    assert os.path.exists(cache_path)
    
    # Second ingestion - should use cache
    # On peut vérifier les logs ou le comportement, mais ici on vérifie surtout la non-erreur de persistence
    nodes = await ingestor.run_ingestion([doc])
    assert len(nodes) > 0
