import pytest
from src.indexing.vector_service import VectorService
from src.ingestion.async_ingestor import AsyncIngestor
from llama_index.core.schema import Document
from llama_index.core import Settings
from llama_index.core.embeddings import MockEmbedding

@pytest.fixture
def mock_settings():
    Settings.embed_model = MockEmbedding(embed_dim=1536)
    yield

@pytest.mark.asyncio
async def test_async_ingestion_pipeline(mock_settings):
    # Pour ce test, on utilise :memory: 
    # Attention: en mode local, aclient est None dans notre implementation actuelle
    # On va forcer un aclient pour le test ou mocker
    
    service = VectorService(storage_path=":memory:")
    # On injecte manuellement un aclient pour le test si possible
    from qdrant_client import AsyncQdrantClient
    service.aclient = AsyncQdrantClient(":memory:")
    service.vector_store._aclient = service.aclient # Update the vector store internal client
    
    ingestor = AsyncIngestor(vector_service=service)
    
    docs = [
        Document(text=f"Ceci est le document numéro {i}", metadata={"index": i})
        for i in range(5)
    ]
    
    # Exécution de l'ingestion
    nodes = await ingestor.run_ingestion(docs, show_progress=False)
    
    assert len(nodes) > 0
    # Vérification de la présence d'embeddings (PBI-024 Correctif)
    for node in nodes:
        assert node.embedding is not None
        assert len(node.embedding) == 1536
    
    # Vérification de la persistance réelle dans le vector store
    # On utilise le client asynchrone pour scroller les points
    points, _ = await service.aclient.scroll(
        collection_name=service.collection_name,
        with_payload=True,
        with_vectors=True,
    )
    assert len(points) > 0
    assert len(points[0].vector) == 1536
    
    await service.aclient.close()
    service.close()
