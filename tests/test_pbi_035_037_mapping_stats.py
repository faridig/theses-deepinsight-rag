import pytest
import os
from src.indexing.vector_service import VectorService
from src.generation.rag_engine import RAGEngine
from llama_index.core.schema import TextNode
from llama_index.core import Settings
from llama_index.core.embeddings import MockEmbedding

@pytest.fixture
def mock_settings():
    Settings.embed_model = MockEmbedding(embed_dim=1536)
    yield

@pytest.mark.asyncio
async def test_dynamic_collection_mapping(tmp_path, mock_settings, monkeypatch):
    """
    Test PBI-035 : Détection dynamique des collections.
    """
    monkeypatch.setenv("QDRANT_URL", "") # Force le mode local
    storage_path = str(tmp_path / "qdrant_mapping")
    
    # 1. Créer plusieurs collections
    vs = VectorService(storage_path=storage_path, collection_name="default")
    await vs.create_collection_if_not_exists("ia-theses")
    await vs.create_collection_if_not_exists("bio-theses")
    await vs.create_collection_if_not_exists("test") # Devrait être filtré
    
    # 2. Utiliser RAGEngine avec le MÊME VectorService partagé
    engine = RAGEngine(storage_path=storage_path)
    engine._shared_vector_service = vs # On injecte le service déjà ouvert
    
    themes = engine.get_available_themes()
    
    assert "ia-theses" in themes
    assert "bio-theses" in themes
    assert "test" not in themes 
    assert "default" not in themes 
    
    vs.close()
    
@pytest.mark.asyncio
async def test_collection_stats(tmp_path, mock_settings, monkeypatch):
    """
    Test PBI-037 : Statistiques de collection.
    """
    monkeypatch.setenv("QDRANT_URL", "") # Force le mode local
    storage_path = str(tmp_path / "qdrant_stats")
    collection_name = "theses-stats"
    
    vs = VectorService(storage_path=storage_path, collection_name=collection_name)
    await vs.create_collection_if_not_exists(collection_name)
    
    nodes = [
        TextNode(text="Node 1", metadata={"titre": "T1"}),
        TextNode(text="Node 2", metadata={"titre": "T2"})
    ]
    vs.index_nodes(nodes)
    
    engine = RAGEngine(storage_path=storage_path)
    engine._shared_vector_service = vs # Injection
    
    stats = engine.get_theme_stats(collection_name)
    
    assert stats["points_count"] == 2
    assert "green" in stats["status"].lower()
    
    vs.close()
